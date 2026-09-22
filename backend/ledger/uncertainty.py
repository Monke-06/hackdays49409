"""
backend/ledger/uncertainty.py

Monte Carlo uncertainty propagation for the lifecycle ledger.

All output ranges are labeled "under stated assumptions". Every assumption
is documented in the MonteCarloConfig dataclass. Changing any single
assumption can move results outside the stated range -- this is expected
and is why the assumptions block is surfaced in the UI alongside every number.

Method:
    1. For each uncertain input parameter, draw N samples from its assumed
       distribution (see parameter_distributions below).
    2. Run the deterministic computation (Green Algorithms equation, SCI) on
       each sample.
    3. Report p5 as 'low', p50 as 'value', p95 as 'high'.

Parameter distributions (all documented):
    - TDP: Uniform(TDP * 0.85, TDP * 1.15)
      Rationale: manufacturer TDP tolerance is typically +/-10-15%.
    - PUE: Uniform(pue * 0.90, pue * 1.10)
      Rationale: PUE varies with ambient temperature and load.
      For well-known facilities (e.g. Jean Zay PUE=1.2), the range is narrower.
    - Grid intensity: Uniform(intensity * 0.80, intensity * 1.20)
      Rationale: annual average vs marginal/hourly spread; year-to-year variation.
    - Utilization: fixed at the stated value (no randomness unless measured range
      is provided). Set utilization_low and utilization_high to add variation.
    - Embodied (GPU): Uniform(boavizta_min, boavizta_max)
      Rationale: Boavizta API confidence bounds (model uncertainty in LCA).

Random seed is always recorded in the output for reproducibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from backend.ledger.green_algorithms import (
    GreenAlgorithmsInputs,
    compute_energy_kwh,
    compute_carbon_kgco2e,
)


@dataclass
class MonteCarloConfig:
    """
    Full set of assumptions for one Monte Carlo run.

    Every field is documented with its unit and the rationale for
    the chosen distribution. This block is serialized into every
    LifecycleLedger so users can audit what was assumed.
    """
    # --- Compute inputs ---
    runtime_hours: float
    "Total runtime of the workload in hours."

    n_cores_or_gpus: int
    "Number of parallel processors (GPUs or CPU cores)."

    tdp_w: float
    "Nominal TDP per processor in Watts (point estimate)."

    tdp_tolerance_frac: float = 0.15
    "TDP uncertainty: +/- this fraction of tdp_w. Default 15% (manufacturer spec spread)."

    utilization: float = 1.0
    "Fraction of TDP drawn during the workload [0,1]. Default 1.0 (conservative: full load)."

    utilization_low: float | None = None
    "Lower bound for utilization. If None, utilization is fixed."

    utilization_high: float | None = None
    "Upper bound for utilization. If None, utilization is fixed."

    memory_gb: float = 0.0
    "Allocated memory in GB."

    # --- Grid intensity ---
    grid_intensity_gco2_per_kwh: float = 472.94
    "Point estimate of grid carbon intensity (gCO2/kWh). Default: World average (Ember 2024)."

    grid_intensity_low: float | None = None
    "Lower bound. If None, -20% of grid_intensity_gco2_per_kwh is used."

    grid_intensity_high: float | None = None
    "Upper bound. If None, +20% of grid_intensity_gco2_per_kwh is used."

    # --- PUE ---
    pue: float = 1.67
    "Nominal PUE of the datacenter. Default 1.67 (global average, Lannelongue et al. 2021)."

    pue_low: float | None = None
    "Lower bound. If None, pue * 0.90 is used."

    pue_high: float | None = None
    "Upper bound. If None, pue * 1.10 is used."

    # --- Embodied carbon ---
    embodied_nominal_kgco2eq: float = 0.0
    "Nominal amortized embodied carbon (kgCO2eq) for this workload."

    embodied_low_kgco2eq: float = 0.0
    "Lower bound from Boavizta confidence interval."

    embodied_high_kgco2eq: float = 0.0
    "Upper bound from Boavizta confidence interval."

    # --- Monte Carlo parameters ---
    n_samples: int = 1_000
    "Number of Monte Carlo samples. Increase to 10_000 for smoother tails."

    seed: int = 42
    "Random seed for reproducibility. Always recorded in output."


@dataclass(frozen=True)
class MCResult:
    """
    Output of one Monte Carlo run.

    'value' is the p50 (median) of the sample distribution.
    'low' is p5, 'high' is p95.
    All ranges are labeled 'under stated assumptions'.
    """
    value: float     # p50 median
    low: float       # p5
    high: float      # p95
    mean: float
    std: float
    n_samples: int
    seed: int
    unit: str
    uncertainty_label: str = (
        "under stated assumptions -- see LedgerAssumptions for the full list. "
        "Changing any assumption can move results outside this range."
    )


def run_energy_mc(cfg: MonteCarloConfig) -> MCResult:
    """
    Monte Carlo for energy consumption (kWh).

    Samples over TDP, PUE, and optionally utilization.
    Returns MCResult in kWh.
    """
    rng = np.random.default_rng(cfg.seed)

    # TDP samples: Uniform(tdp*(1-tol), tdp*(1+tol))
    tdp_samples = rng.uniform(
        cfg.tdp_w * (1.0 - cfg.tdp_tolerance_frac),
        cfg.tdp_w * (1.0 + cfg.tdp_tolerance_frac),
        cfg.n_samples,
    )

    # PUE samples
    pue_low = cfg.pue_low if cfg.pue_low is not None else cfg.pue * 0.90
    pue_high = cfg.pue_high if cfg.pue_high is not None else cfg.pue * 1.10
    # PUE must be >= 1.0
    pue_low = max(pue_low, 1.01)
    pue_samples = rng.uniform(pue_low, pue_high, cfg.n_samples)

    # Utilization samples
    if cfg.utilization_low is not None and cfg.utilization_high is not None:
        u_samples = rng.uniform(cfg.utilization_low, cfg.utilization_high, cfg.n_samples)
    else:
        u_samples = np.full(cfg.n_samples, cfg.utilization)

    # Compute energy for each sample
    compute_power_w = cfg.n_cores_or_gpus * tdp_samples * u_samples
    memory_power_w = cfg.memory_gb * 0.3725
    energy_wh = cfg.runtime_hours * (compute_power_w + memory_power_w) * pue_samples
    energy_kwh_samples = energy_wh / 1000.0

    return MCResult(
        value=float(np.percentile(energy_kwh_samples, 50)),
        low=float(np.percentile(energy_kwh_samples, 5)),
        high=float(np.percentile(energy_kwh_samples, 95)),
        mean=float(np.mean(energy_kwh_samples)),
        std=float(np.std(energy_kwh_samples)),
        n_samples=cfg.n_samples,
        seed=cfg.seed,
        unit="kWh",
    )


def run_carbon_mc(cfg: MonteCarloConfig) -> MCResult:
    """
    Monte Carlo for carbon emissions (kgCO2e).

    Samples over TDP, PUE, grid intensity, and optionally utilization.
    Returns MCResult in kgCO2e.
    """
    rng = np.random.default_rng(cfg.seed)

    # TDP samples
    tdp_samples = rng.uniform(
        cfg.tdp_w * (1.0 - cfg.tdp_tolerance_frac),
        cfg.tdp_w * (1.0 + cfg.tdp_tolerance_frac),
        cfg.n_samples,
    )

    # PUE samples
    pue_low = cfg.pue_low if cfg.pue_low is not None else cfg.pue * 0.90
    pue_high = cfg.pue_high if cfg.pue_high is not None else cfg.pue * 1.10
    pue_low = max(pue_low, 1.01)
    pue_samples = rng.uniform(pue_low, pue_high, cfg.n_samples)

    # Grid intensity samples
    gi_low = cfg.grid_intensity_low if cfg.grid_intensity_low is not None else cfg.grid_intensity_gco2_per_kwh * 0.80
    gi_high = cfg.grid_intensity_high if cfg.grid_intensity_high is not None else cfg.grid_intensity_gco2_per_kwh * 1.20
    gi_samples = rng.uniform(gi_low, gi_high, cfg.n_samples)

    # Utilization samples
    if cfg.utilization_low is not None and cfg.utilization_high is not None:
        u_samples = rng.uniform(cfg.utilization_low, cfg.utilization_high, cfg.n_samples)
    else:
        u_samples = np.full(cfg.n_samples, cfg.utilization)

    # Energy per sample
    compute_power_w = cfg.n_cores_or_gpus * tdp_samples * u_samples
    memory_power_w = cfg.memory_gb * 0.3725
    energy_kwh_samples = cfg.runtime_hours * (compute_power_w + memory_power_w) * pue_samples / 1000.0

    # Carbon = energy * intensity / 1000 (g -> kg)
    carbon_samples = energy_kwh_samples * gi_samples / 1000.0

    return MCResult(
        value=float(np.percentile(carbon_samples, 50)),
        low=float(np.percentile(carbon_samples, 5)),
        high=float(np.percentile(carbon_samples, 95)),
        mean=float(np.mean(carbon_samples)),
        std=float(np.std(carbon_samples)),
        n_samples=cfg.n_samples,
        seed=cfg.seed,
        unit="kgCO2e",
    )


def run_embodied_mc(cfg: MonteCarloConfig) -> MCResult:
    """
    Monte Carlo for amortized embodied carbon (kgCO2e).

    Samples uniformly between Boavizta confidence bounds.
    Returns MCResult in kgCO2e.
    """
    rng = np.random.default_rng(cfg.seed + 1)  # different seed from energy runs

    if cfg.embodied_nominal_kgco2eq == 0.0:
        return MCResult(
            value=0.0, low=0.0, high=0.0, mean=0.0, std=0.0,
            n_samples=cfg.n_samples, seed=cfg.seed, unit="kgCO2e",
        )

    samples = rng.uniform(cfg.embodied_low_kgco2eq, cfg.embodied_high_kgco2eq, cfg.n_samples)

    return MCResult(
        value=float(np.percentile(samples, 50)),
        low=float(np.percentile(samples, 5)),
        high=float(np.percentile(samples, 95)),
        mean=float(np.mean(samples)),
        std=float(np.std(samples)),
        n_samples=cfg.n_samples,
        seed=cfg.seed,
        unit="kgCO2e",
    )
