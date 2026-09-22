"""
backend/ledger/green_algorithms.py

Implements the Green Algorithms energy equation.

Reference:
    Lannelongue, L., Grealey, J., and Inouye, M. (2021).
    "Green Algorithms: Quantifying the Carbon Footprint of Computation."
    Advanced Science, 8(12), 2100707.
    DOI: https://doi.org/10.1002/advs.202100707

Equation (from the paper):
    E_kWh = t * (n_c * P_c * u_c + n_m * P_m) * PUE / 1000

Where:
    t        = runtime in hours
    n_c      = number of cores (or GPUs, treated as 1 core each)
    P_c      = power draw per core/GPU in Watts (TDP or measured)
    u_c      = usage/utilization factor [0, 1] (default 1.0)
    n_m      = memory allocated in GB
    P_m      = memory power draw per GB = 0.3725 W/GB
               (from Micron DDR4 SDRAM specification, cited in the paper)
    PUE      = Power Usage Effectiveness of the datacenter (>= 1.0)
    /1000    = converts Wh to kWh

License note: The Green Algorithms web calculator is CC-BY-4.0.
The core equation is from the published paper (open access, CC-BY).
CPU TDP data in the paper's data tables is CC-BY-NC-SA; we use
GPU TDP from manufacturer spec sheets and our own reference data.

Uncertainty model:
    - TDP has +/-15% manufacturer tolerance. For GPU TDP, applied as
      uniform distribution over [TDP * 0.85, TDP * 1.15].
    - PUE is sampled uniformly over [pue_low, pue_high] when ranges
      are provided. Default range: [pue * 0.9, pue * 1.1].
    - Utilization defaults to 1.0 (100% load) when not measured.
      Users should override with measured values if available.
"""
from __future__ import annotations

from dataclasses import dataclass

# Memory power per GB (W/GB) -- from Micron DDR4 SDRAM data sheet,
# as cited in Lannelongue et al. (2021).
MEMORY_POWER_PER_GB_W: float = 0.3725


@dataclass(frozen=True)
class GreenAlgorithmsInputs:
    """
    Inputs to the Green Algorithms energy equation.

    All fields correspond directly to variables in the paper's equation.
    Document the source of each value when constructing this object.
    """
    runtime_hours: float          # t: total runtime
    n_cores_or_gpus: int          # n_c: number of parallel processors
    tdp_per_unit_w: float         # P_c: TDP per core or per GPU (Watts)
    utilization: float = 1.0      # u_c: fraction of peak power drawn [0,1]
    memory_gb: float = 0.0        # n_m: allocated memory in GB
    pue: float = 1.67             # PUE (default = global average from paper)

    def __post_init__(self) -> None:
        if self.runtime_hours <= 0:
            raise ValueError("runtime_hours must be positive.")
        if self.n_cores_or_gpus <= 0:
            raise ValueError("n_cores_or_gpus must be positive.")
        if self.tdp_per_unit_w <= 0:
            raise ValueError("tdp_per_unit_w must be positive.")
        if not (0.0 < self.utilization <= 1.0):
            raise ValueError("utilization must be in (0, 1].")
        if self.memory_gb < 0:
            raise ValueError("memory_gb must be non-negative.")
        if self.pue < 1.0:
            raise ValueError("PUE must be >= 1.0.")


def compute_energy_kwh(inputs: GreenAlgorithmsInputs) -> float:
    """
    Compute energy consumption in kWh using the Green Algorithms equation.

    E_kWh = t * (n_c * P_c * u_c + n_m * P_m) * PUE / 1000

    Args:
        inputs: GreenAlgorithmsInputs with all equation parameters.

    Returns:
        Energy in kWh (float).
    """
    compute_power_w = inputs.n_cores_or_gpus * inputs.tdp_per_unit_w * inputs.utilization
    memory_power_w = inputs.memory_gb * MEMORY_POWER_PER_GB_W
    total_power_w = compute_power_w + memory_power_w
    energy_wh = inputs.runtime_hours * total_power_w * inputs.pue
    return energy_wh / 1000.0


def compute_carbon_kgco2e(energy_kwh: float, grid_intensity_gco2_per_kwh: float) -> float:
    """
    Convert energy to carbon emissions.

    C = E_kWh * I   (where I is in gCO2/kWh)

    Returns carbon in kg CO2e.
    """
    return energy_kwh * grid_intensity_gco2_per_kwh / 1000.0


def compute_energy_and_carbon(
    inputs: GreenAlgorithmsInputs,
    grid_intensity_gco2_per_kwh: float,
) -> tuple[float, float]:
    """
    Convenience wrapper. Returns (energy_kwh, carbon_kgco2e).
    """
    energy = compute_energy_kwh(inputs)
    carbon = compute_carbon_kgco2e(energy, grid_intensity_gco2_per_kwh)
    return energy, carbon
