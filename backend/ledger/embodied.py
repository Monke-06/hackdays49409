"""
backend/ledger/embodied.py

Embodied carbon estimation for AI hardware.

Data source:
    Boavizta BoaviztAPI (https://api.boavizta.org)
    License: AGPL-3.0 (code), Open Data ODbL/CC-BY-SA (datasets)
    Data fetched live on 2026-09-22 and stored in data/reference/gpu_embodied.json.

Methodology:
    Boavizta uses a bottom-up LCA approach. Reported figures represent
    the manufacturing (embodied) phase only. End-of-life is NOT included
    (as noted in API warnings). Values are per GPU, derived from full
    server archetype GWP divided by GPU count in that archetype.

SCI amortization formula (from ISO/IEC 21031 SCI spec):
    M = TE * TS * RS
    where:
        TE = total embodied emissions of hardware (kgCO2eq)
        TS = time-share = time_reserved_hours / expected_lifetime_hours
        RS = resource-share = resources_reserved / total_resources

For a training job:
    TE = n_gpus * embodied_per_gpu + server_chassis_overhead
    TS = training_duration_hours / (hardware_lifetime_years * 8760)
    RS = n_gpus_used / n_gpus_total  (often 1.0 for dedicated training)

BLOOM paper cross-check:
    Luccioni et al. (2023) assumed 150 kgCO2eq per A100 GPU (GPU card only,
    from NVIDIA estimates at the time). Boavizta's generic 80GB GPU archetype
    gives 637.5 kgCO2eq per GPU slot (includes server infrastructure amortised
    per GPU). The difference reflects methodology scope: card-only vs full-server.
    Both are documented in VALIDATION.md. We use Boavizta as our primary source
    and compare against the BLOOM paper's figure as a sensitivity test.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache

_DATA_FILE = Path(__file__).parent.parent.parent / "data" / "reference" / "gpu_embodied.json"

# Default hardware lifetime if not specified.
# 4 years is Boavizta's default for generic GPU servers.
# Jean Zay (BLOOM) assumed 6 years (French national HPC renewal cycle).
DEFAULT_HARDWARE_LIFETIME_YEARS: float = 4.0

# Server chassis overhead per GPU slot (kgCO2eq).
# This is the difference between full-server Boavizta figures and GPU-card-only estimates.
# Derived from: (Generic 80GB server total 6800 - 8x GPU components 4601) / 8
# = (6800 - 4601) / 8 = 274.9 kgCO2eq chassis overhead per GPU slot
SERVER_CHASSIS_OVERHEAD_PER_GPU_KG: float = 274.9


@lru_cache(maxsize=1)
def _load_data() -> dict:
    with open(_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_metadata() -> dict:
    return _load_data()["_metadata"]


def get_gpu_entry(gpu_model: str) -> dict | None:
    """
    Look up a GPU model in the reference data.

    Args:
        gpu_model: GPU model string, e.g. 'NVIDIA A100 SXM4 80GB'.
                   Case-insensitive substring match is tried if exact match fails.

    Returns:
        dict with keys: gwp_kgco2eq_per_gpu, archetype, archetype_note, etc.
        None if not found.
    """
    data = _load_data()
    models = data.get("gpu_models", {})

    # Exact match
    if gpu_model in models:
        return models[gpu_model]

    # Case-insensitive exact
    for k, v in models.items():
        if k.lower() == gpu_model.lower():
            return v

    # Substring match (most specific first)
    gpu_model_lower = gpu_model.lower()
    matches = [(k, v) for k, v in models.items() if gpu_model_lower in k.lower() or k.lower() in gpu_model_lower]
    if matches:
        # Return the most specific (longest key) match
        return max(matches, key=lambda x: len(x[0]))[1]

    return None


def get_tdp_w(gpu_model: str) -> float | None:
    """
    Return TDP in Watts for a GPU model from reference data.
    Returns None if not found.
    """
    data = _load_data()
    tdp_ref = data.get("tdp_reference_w", {})

    if gpu_model in tdp_ref:
        return tdp_ref[gpu_model]["tdp_w"]

    gpu_model_lower = gpu_model.lower()
    for k, v in tdp_ref.items():
        if gpu_model_lower in k.lower() or k.lower() in gpu_model_lower:
            return v["tdp_w"]

    return None


@dataclass(frozen=True)
class EmbodiedResult:
    """
    Amortized embodied carbon for a hardware allocation.
    All values in kgCO2eq. Uncertainty range labeled 'under stated assumptions'.
    """
    total_kgco2eq: float          # point estimate
    low_kgco2eq: float            # p5 (Boavizta min / amortization)
    high_kgco2eq: float           # p95 (Boavizta max / amortization)
    per_gpu_kgco2eq: float        # unamortised per-GPU figure
    gpu_model: str
    n_gpus: int
    hardware_lifetime_years: float
    time_share: float             # TS = duration / lifetime
    resource_share: float         # RS = GPUs used / total GPUs
    source: str
    method_note: str
    uncertainty_note: str = (
        "Range from Boavizta API confidence bounds. "
        "Under stated assumptions: hardware lifetime, time-share, resource-share."
    )


def compute_amortized_embodied(
    gpu_model: str,
    n_gpus: int,
    duration_hours: float,
    hardware_lifetime_years: float = DEFAULT_HARDWARE_LIFETIME_YEARS,
    resource_share: float = 1.0,
    include_chassis: bool = True,
) -> EmbodiedResult:
    """
    Compute amortized embodied carbon for a GPU workload.

    Uses the SCI specification formula:
        M = TE * TS * RS

    Args:
        gpu_model: GPU model string for lookup.
        n_gpus: Number of GPUs used.
        duration_hours: Duration of the workload in hours.
        hardware_lifetime_years: Expected hardware lifespan.
        resource_share: Fraction of the server dedicated to this workload (0,1].
        include_chassis: If True, uses Boavizta full-server figure.
                         If False, uses GPU-card-only (for BLOOM paper comparison).

    Returns:
        EmbodiedResult with amortized totals and uncertainty bounds.
    """
    meta = get_metadata()
    entry = get_gpu_entry(gpu_model)

    if entry is not None:
        gwp = entry["gwp_kgco2eq_per_gpu"]
        per_gpu_val = gwp["value"]
        per_gpu_min = gwp["min"]
        per_gpu_max = gwp["max"]
        archetype = entry.get("archetype", "unknown")
        source = f"Boavizta BoaviztAPI ({meta['source_url']}), archetype={archetype}, fetched {meta['fetch_date']}"
        method_note = entry.get("archetype_note", "")
    else:
        # Fallback: use the default generic GPU component value
        data = _load_data()
        default_entry = data["gpu_models"]["Boavizta default single GPU component"]
        gwp = default_entry["gwp_kgco2eq_per_gpu"]
        per_gpu_val = gwp["value"]
        per_gpu_min = gwp["min"]
        per_gpu_max = gwp["max"]
        source = f"Boavizta default GPU component (model {gpu_model!r} not found in reference data)"
        method_note = f"Fallback to default. GPU model {gpu_model!r} not in database."

    if not include_chassis:
        # GPU-card-only: use card-only lower bound
        per_gpu_val = per_gpu_min
        method_note += " [chassis excluded: GPU card only lower bound, for BLOOM paper comparison]"

    lifetime_hours = hardware_lifetime_years * 8760.0
    time_share = duration_hours / lifetime_hours
    time_share = min(time_share, 1.0)  # cap at 100% of lifetime

    total_raw = per_gpu_val * n_gpus
    total_min = per_gpu_min * n_gpus
    total_max = per_gpu_max * n_gpus

    amortized = total_raw * time_share * resource_share
    amortized_min = total_min * time_share * resource_share
    amortized_max = total_max * time_share * resource_share

    return EmbodiedResult(
        total_kgco2eq=round(amortized, 4),
        low_kgco2eq=round(amortized_min, 4),
        high_kgco2eq=round(amortized_max, 4),
        per_gpu_kgco2eq=per_gpu_val,
        gpu_model=gpu_model,
        n_gpus=n_gpus,
        hardware_lifetime_years=hardware_lifetime_years,
        time_share=round(time_share, 6),
        resource_share=resource_share,
        source=source,
        method_note=method_note,
    )
