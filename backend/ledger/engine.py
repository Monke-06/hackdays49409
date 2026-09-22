"""
backend/ledger/engine.py

Main lifecycle ledger engine. Composes green_algorithms, embodied, grid_intensity,
uncertainty, and sci into LifecycleLedger objects.

For any given SystemInventory this engine produces two ledgers:
  1. 'operational' boundary: inference energy + training energy only.
  2. 'full_lifecycle' boundary: adds embodied hardware, retraining, storage, network.

All output Quantity objects carry:
  - value: point estimate (p50 of Monte Carlo)
  - low/high: p5/p95 uncertainty range
  - tier: always 'modeled' unless a live measurement was injected
  - source: traceable string citing the data source and method
  - method_note: short explanation of how the number was derived

Storage and network estimates:
  - Storage: 0.06 kgCO2e/TB/year (IEA 2022 estimate for data center storage).
    Source: IEA, "Data Centres and Data Transmission Networks" (2022).
  - Network: 0.002 kgCO2e/GB transferred (Aslan et al. 2018, fiber network average).
    Source: Aslan, J. et al. (2018). Electricity Intensity of Internet Data Transmission.
    Journal of Industrial Ecology. DOI: 10.1111/jiec.12630.
  - Both are highly uncertain; ranges are +/-50%.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.schemas import (
    Boundary,
    GPUSpec,
    LifecycleLedger,
    LedgerAssumptions,
    Quantity,
    SystemInventory,
    Tier,
    AccountingMethod,
)
from backend.ledger.green_algorithms import GreenAlgorithmsInputs, compute_energy_kwh, compute_carbon_kgco2e
from backend.ledger.embodied import compute_amortized_embodied, get_tdp_w
from backend.ledger.grid_intensity import lookup as lookup_grid
from backend.ledger.uncertainty import MonteCarloConfig, run_energy_mc, run_carbon_mc, run_embodied_mc
from backend.ledger.sci import SCIInputs, FunctionalUnit, compute_sci

# ---------------------------------------------------------------------------
# Storage and network emission factors (modeled, wide uncertainty)
# ---------------------------------------------------------------------------

# kgCO2e per TB per year (data center storage)
# Source: IEA, "Data Centres and Data Transmission Networks" (2022).
# URL: https://www.iea.org/reports/data-centres-and-data-transmission-networks
STORAGE_KGCO2E_PER_TB_YEAR: float = 0.06

# kgCO2e per GB transferred (fiber network)
# Source: Aslan et al. (2018). DOI: 10.1111/jiec.12630
NETWORK_KGCO2E_PER_GB: float = 0.002

# Bytes per request (rough average for LLM response: ~8KB tokens + overhead)
BYTES_PER_REQUEST_GB: float = 8e-6  # 8KB


def _make_quantity(
    value: float,
    low: float,
    high: float,
    unit: str,
    source: str,
    method_note: str,
    tier: Tier = Tier.modeled,
) -> Quantity:
    """Clamp low <= value <= high then build Quantity."""
    low = min(low, value)
    high = max(high, value)
    return Quantity(
        value=round(value, 6),
        low=round(low, 6),
        high=round(high, 6),
        unit=unit,
        tier=tier,
        source=source,
        method_note=method_note,
    )


def _resolve_tdp(gpu: GPUSpec) -> float:
    """Return TDP in Watts: user-supplied > reference table > error."""
    if gpu.tdp_w is not None:
        return gpu.tdp_w
    tdp = get_tdp_w(gpu.model)
    if tdp is not None:
        return tdp
    raise ValueError(
        f"GPU model {gpu.model!r} not found in TDP reference table "
        f"(data/reference/gpu_embodied.json). "
        f"Please supply gpu.tdp_w explicitly."
    )


@dataclass
class LedgerEngineConfig:
    """
    Overridable assumptions for the ledger engine.
    Defaults match the recommended values from their respective sources.
    """
    pue: float | None = None
    "Override PUE. If None, 1.67 (Green Algorithms global average) is used."

    hardware_lifetime_years: float = 4.0
    "Expected hardware lifetime in years. Default 4 (Boavizta generic GPU servers)."

    utilization: float = 1.0
    "Fraction of peak TDP drawn during inference/training. Default 1.0."

    accounting: AccountingMethod = AccountingMethod.location
    "Accounting method for grid intensity. SCI spec prefers location-based."

    n_mc_samples: int = 1_000
    "Number of Monte Carlo samples."

    mc_seed: int = 42
    "Monte Carlo random seed. Must be recorded for reproducibility."

    requests_per_day: float | None = None
    "Override inference traffic. Taken from SystemInventory.inference if None."


def compute_ledgers(
    inventory: SystemInventory,
    cfg: LedgerEngineConfig | None = None,
) -> tuple[LifecycleLedger, LifecycleLedger]:
    """
    Compute operational and full_lifecycle LifecycleLedger for a SystemInventory.

    Returns:
        (ledger_operational, ledger_full_lifecycle)

    All Quantity values are modeled (not measured) unless the caller injects
    live measurements via SystemInventory fields marked with tier='measured'.
    """
    if cfg is None:
        cfg = LedgerEngineConfig()

    # ------------------------------------------------------------------
    # 1. Grid intensity
    # ------------------------------------------------------------------
    region = inventory.region or "global"
    try:
        grid_info = lookup_grid(region)
    except KeyError:
        # Fall back to world average with explicit note
        grid_info = lookup_grid("World")
        grid_info = dict(grid_info)
        grid_info["uncertainty_note"] = (
            f"Region {region!r} not found; using World average (472.94 gCO2/kWh, Ember 2024). "
            "Under stated assumptions."
        )

    gi_value = grid_info["gco2_per_kwh"]
    gi_low = grid_info["low_gco2_per_kwh"]
    gi_high = grid_info["high_gco2_per_kwh"]
    gi_source = grid_info["source_url"]

    grid_qty = _make_quantity(
        value=gi_value,
        low=gi_low,
        high=gi_high,
        unit="gCO2eq/kWh",
        source=gi_source,
        method_note=grid_info.get("uncertainty_note", "Ember CC-BY-4.0 annual average."),
    )

    # Effective PUE
    pue = cfg.pue
    if pue is None:
        # Default 1.67 (Green Algorithms global average)
        pue = 1.67
        pue_source = (
            "Lannelongue et al. (2021) Green Algorithms, Advanced Science 8(12). "
            "Global average default PUE = 1.67."
        )
    else:
        pue_source = "User-supplied override."

    # ------------------------------------------------------------------
    # 2. Training energy and carbon
    # ------------------------------------------------------------------
    training_qty = _make_quantity(0, 0, 0, "kgCO2e", "none", "Training config not provided.")
    training_energy_kwh = 0.0

    if inventory.training is not None:
        tr = inventory.training
        tr_pue = tr.pue if tr.pue is not None else pue
        tr_region = tr.region or region
        try:
            tr_grid = lookup_grid(tr_region)
        except KeyError:
            tr_grid = lookup_grid("World")

        tdp_w = _resolve_tdp(tr.gpu)
        tr_memory_gb = tr.gpu.count * tr.gpu.vram_gb if hasattr(tr.gpu, "vram_gb") else 0.0

        tr_mc = MonteCarloConfig(
            runtime_hours=tr.duration_hours * tr.n_epochs,
            n_cores_or_gpus=tr.gpu.count,
            tdp_w=tdp_w,
            utilization=cfg.utilization,
            memory_gb=tr_memory_gb,
            grid_intensity_gco2_per_kwh=tr_grid["gco2_per_kwh"],
            grid_intensity_low=tr_grid["low_gco2_per_kwh"],
            grid_intensity_high=tr_grid["high_gco2_per_kwh"],
            pue=tr_pue,
            n_samples=cfg.n_mc_samples,
            seed=cfg.mc_seed,
        )
        tr_energy_mc = run_energy_mc(tr_mc)
        tr_carbon_mc = run_carbon_mc(tr_mc)

        training_energy_kwh = tr_energy_mc.value
        training_source = (
            f"Green Algorithms equation (Lannelongue et al. 2021), "
            f"GPU={tr.gpu.model!r}, TDP={tdp_w}W, "
            f"runtime={tr.duration_hours * tr.n_epochs:.1f}h, "
            f"PUE={tr_pue}, grid={tr_grid['gco2_per_kwh']} gCO2/kWh ({tr_region}). "
            f"Ember CC-BY-4.0."
        )
        training_qty = _make_quantity(
            value=tr_carbon_mc.value,
            low=tr_carbon_mc.low,
            high=tr_carbon_mc.high,
            unit="kgCO2e",
            source=training_source,
            method_note=tr_carbon_mc.uncertainty_label,
        )

    # ------------------------------------------------------------------
    # 3. Inference energy and carbon
    # ------------------------------------------------------------------
    inference_qty = _make_quantity(0, 0, 0, "kgCO2e", "none", "Inference config not provided.")
    inference_energy_kwh = 0.0
    requests_per_day = cfg.requests_per_day

    if inventory.inference is not None:
        inf = inventory.inference
        if requests_per_day is None:
            requests_per_day = inf.requests_per_day
        tdp_w = _resolve_tdp(inf.gpu)
        # Inference: TDP per GPU, but batch_size affects utilization.
        # We treat the full GPU as active during serving.
        annual_hours = inf.runtime_hours if getattr(inf, "runtime_hours", None) is not None else 8760.0
        inf_mc = MonteCarloConfig(
            runtime_hours=annual_hours,
            n_cores_or_gpus=inf.gpu.count,
            tdp_w=tdp_w,
            utilization=cfg.utilization,
            grid_intensity_gco2_per_kwh=gi_value,
            grid_intensity_low=gi_low,
            grid_intensity_high=gi_high,
            pue=pue,
            n_samples=cfg.n_mc_samples,
            seed=cfg.mc_seed + 10,
        )
        inf_energy_mc = run_energy_mc(inf_mc)
        inf_carbon_mc = run_carbon_mc(inf_mc)
        inference_energy_kwh = inf_energy_mc.value

        inf_source = (
            f"Green Algorithms equation (Lannelongue et al. 2021), "
            f"GPU={inf.gpu.model!r}, TDP={tdp_w}W, "
            f"annual (8760h), PUE={pue}, "
            f"grid={gi_value} gCO2/kWh ({region}). Ember CC-BY-4.0."
        )
        inference_qty = _make_quantity(
            value=inf_carbon_mc.value,
            low=inf_carbon_mc.low,
            high=inf_carbon_mc.high,
            unit="kgCO2e",
            source=inf_source,
            method_note=inf_carbon_mc.uncertainty_label,
        )

    # ------------------------------------------------------------------
    # 4. Embodied hardware
    # ------------------------------------------------------------------
    embodied_qty = _make_quantity(0, 0, 0, "kgCO2e", "none", "No hardware config provided.")

    gpu_for_embodied = (
        inventory.training.gpu if inventory.training else
        inventory.inference.gpu if inventory.inference else None
    )

    if gpu_for_embodied is not None:
        # Allocate embodied carbon by actual hardware time used:
        # hours of runtime divided by lifetime hours, never 100% to a short run.
        if inventory.training is not None and inventory.inference is not None:
            duration_h = inventory.training.duration_hours + inventory.inference.runtime_hours
        elif inventory.training is not None:
            duration_h = inventory.training.duration_hours
        elif inventory.inference is not None:
            duration_h = inventory.inference.runtime_hours
        else:
            duration_h = 8760.0
        emb = compute_amortized_embodied(
            gpu_model=gpu_for_embodied.model,
            n_gpus=gpu_for_embodied.count,
            duration_hours=duration_h,
            hardware_lifetime_years=cfg.hardware_lifetime_years,
            resource_share=1.0,
            include_chassis=True,
        )
        emb_mc = run_embodied_mc(MonteCarloConfig(
            runtime_hours=duration_h,
            n_cores_or_gpus=gpu_for_embodied.count,
            tdp_w=1.0,  # not used in embodied MC
            embodied_nominal_kgco2eq=emb.total_kgco2eq,
            embodied_low_kgco2eq=emb.low_kgco2eq,
            embodied_high_kgco2eq=emb.high_kgco2eq,
            n_samples=cfg.n_mc_samples,
            seed=cfg.mc_seed + 20,
        ))
        embodied_qty = _make_quantity(
            value=emb_mc.value,
            low=emb_mc.low,
            high=emb_mc.high,
            unit="kgCO2e",
            source=emb.source,
            method_note=emb.uncertainty_note,
        )

    # ------------------------------------------------------------------
    # 5. Retraining
    # ------------------------------------------------------------------
    retraining_qty = _make_quantity(0, 0, 0, "kgCO2e", "none", "No retraining schedule provided.")

    if (
        inventory.training is not None
        and inventory.retraining_frequency_days is not None
        and inventory.retraining_frequency_days > 0
    ):
        # Retraining cost = training cost * (365 / frequency_days) per year
        retrain_multiplier = 365.0 / inventory.retraining_frequency_days
        retraining_qty = _make_quantity(
            value=training_qty.value * retrain_multiplier,
            low=training_qty.low * retrain_multiplier,
            high=training_qty.high * retrain_multiplier,
            unit="kgCO2e",
            source=training_qty.source,
            method_note=(
                f"Retraining: training cost * {retrain_multiplier:.2f} cycles/year "
                f"(every {inventory.retraining_frequency_days} days). "
                "Under stated assumptions."
            ),
        )

    # ------------------------------------------------------------------
    # 6. Storage
    # ------------------------------------------------------------------
    storage_qty = _make_quantity(0, 0, 0, "kgCO2e", "none", "No storage size provided.")

    if inventory.storage_tb is not None and inventory.storage_tb > 0:
        storage_val = inventory.storage_tb * STORAGE_KGCO2E_PER_TB_YEAR
        storage_qty = _make_quantity(
            value=storage_val,
            low=storage_val * 0.5,   # +/-50% -- storage mix (HDD/SSD/tape) varies
            high=storage_val * 1.5,
            unit="kgCO2e",
            source=(
                "IEA, 'Data Centres and Data Transmission Networks' (2022). "
                "https://www.iea.org/reports/data-centres-and-data-transmission-networks. "
                "0.06 kgCO2e/TB/year."
            ),
            method_note="Under stated assumptions. +/-50% range reflects storage media mix uncertainty.",
        )

    # ------------------------------------------------------------------
    # 7. Network
    # ------------------------------------------------------------------
    network_qty = _make_quantity(0, 0, 0, "kgCO2e", "none", "No request traffic provided.")

    rpd = requests_per_day
    if rpd is not None and rpd > 0:
        annual_gb = rpd * 365 * BYTES_PER_REQUEST_GB
        network_val = annual_gb * NETWORK_KGCO2E_PER_GB
        network_qty = _make_quantity(
            value=network_val,
            low=network_val * 0.5,
            high=network_val * 2.0,  # network intensity estimates vary 2x-4x across studies
            unit="kgCO2e",
            source=(
                "Aslan et al. (2018). 'Electricity Intensity of Internet Data Transmission'. "
                "Journal of Industrial Ecology. DOI: 10.1111/jiec.12630. "
                "0.002 kgCO2e/GB (fiber average)."
            ),
            method_note=(
                "Under stated assumptions. Range +50%/-50% reflects network intensity "
                "variation across studies and CDN caching effects."
            ),
        )

    # ------------------------------------------------------------------
    # 8. Total energy
    # ------------------------------------------------------------------
    # If both training and inference are present (e.g. distillation scenario where
    # model was trained and deployed for inference serving), operational energy is
    # the ongoing inference serving energy, while training energy is upfront lifecycle cost.
    # If only training is specified, operational energy of the training run is training_energy_kwh.
    if inventory.inference is not None and inventory.training is not None:
        op_energy_val = inference_energy_kwh
        op_training_qty = _make_quantity(
            0, 0, 0, "kgCO2e", "excluded", "One-time training/distillation excluded from operational serving boundary."
        )
    else:
        op_energy_val = training_energy_kwh + inference_energy_kwh
        op_training_qty = training_qty

    op_energy_qty = _make_quantity(
        value=op_energy_val,
        low=op_energy_val * 0.75,
        high=op_energy_val * 1.25,
        unit="kWh",
        source="Operational inference energy (Green Algorithms equation)." if inventory.inference else "Training energy.",
        method_note="Under stated assumptions.",
    )

    full_energy_val = training_energy_kwh + inference_energy_kwh
    full_energy_qty = _make_quantity(
        value=full_energy_val,
        low=full_energy_val * 0.75,
        high=full_energy_val * 1.25,
        unit="kWh",
        source="Sum of training and inference energy (Green Algorithms equation).",
        method_note="Under stated assumptions.",
    )

    # ------------------------------------------------------------------
    # 9. Per-request carbon
    # ------------------------------------------------------------------
    per_request_qty = _make_quantity(0, 0, 0, "kgCO2e/request", "none", "No request traffic.")

    if rpd is not None and rpd > 0:
        annual_requests = rpd * 365.0
        total_annual_carbon = inference_qty.value  # inference carbon is already annual
        per_req_val = total_annual_carbon / annual_requests
        per_request_qty = _make_quantity(
            value=per_req_val,
            low=inference_qty.low / annual_requests,
            high=inference_qty.high / annual_requests,
            unit="kgCO2e/request",
            source="Annual inference carbon / annual requests.",
            method_note="Under stated assumptions.",
        )

    # ------------------------------------------------------------------
    # 10. Build LedgerAssumptions
    # ------------------------------------------------------------------
    assumptions = LedgerAssumptions(
        grid_intensity_gco2_per_kwh=grid_qty,
        pue=pue,
        pue_source=pue_source,
        utilization=cfg.utilization,
        utilization_source="User-supplied or default 1.0 (conservative: full TDP load).",
        hardware_lifetime_years=cfg.hardware_lifetime_years,
        hardware_lifetime_source="Boavizta default (4 years) or user override.",
        region=region,
        accounting=cfg.accounting,
        monte_carlo_n_samples=cfg.n_mc_samples,
        monte_carlo_seed=cfg.mc_seed,
    )

    # ------------------------------------------------------------------
    # 11. Operational ledger (training + inference only)
    # ------------------------------------------------------------------
    ledger_op = LifecycleLedger(
        boundary=Boundary.operational,
        training=op_training_qty,
        inference=inference_qty,
        embodied_hardware=_make_quantity(0, 0, 0, "kgCO2e", "excluded", "Excluded from operational boundary."),
        retraining=_make_quantity(0, 0, 0, "kgCO2e", "excluded", "Excluded from operational boundary."),
        storage=_make_quantity(0, 0, 0, "kgCO2e", "excluded", "Excluded from operational boundary."),
        network=_make_quantity(0, 0, 0, "kgCO2e", "excluded", "Excluded from operational boundary."),
        energy_kwh=op_energy_qty,
        per_request=per_request_qty,
        assumptions=assumptions,
    )

    # ------------------------------------------------------------------
    # 12. Full lifecycle ledger
    # ------------------------------------------------------------------
    ledger_full = LifecycleLedger(
        boundary=Boundary.full_lifecycle,
        training=training_qty,
        inference=inference_qty,
        embodied_hardware=embodied_qty,
        retraining=retraining_qty,
        storage=storage_qty,
        network=network_qty,
        energy_kwh=full_energy_qty,
        per_request=per_request_qty,
        assumptions=assumptions,
    )

    return ledger_op, ledger_full
