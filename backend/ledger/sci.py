"""
backend/ledger/sci.py

Software Carbon Intensity (SCI) calculator.

Standard: ISO/IEC 21031:2024 (Green Software Foundation SCI specification).
Reference: https://sci-guide.greensoftware.foundation/

Formula:
    SCI = ((E * I) + M) / R

Where:
    E = energy consumed by the software (kWh) per R
    I = carbon intensity of electricity (gCO2eq/kWh), location-based
    M = embodied carbon, amortized per R (kgCO2eq)
    R = functional unit (e.g. per request, per 1000 requests, per user-day)

Important constraints from the SCI spec:
    1. SCI MUST be expressed as a rate (per R). Absolute values are not SCI.
    2. Carbon offsets, RECs, PPAs may NOT reduce E, I, or M in the SCI score.
       SCI is an architectural efficiency metric, not a net-zero accounting tool.
    3. If M is unavailable, it may be set to 0 but the omission must be disclosed.
    4. I should be location-based (average grid intensity). Market-based is allowed
       only with explicit disclosure and parallel reporting of location-based.

Result unit: kgCO2eq per R (where R is the chosen functional unit).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FunctionalUnit(str, Enum):
    per_request = "per_request"
    per_1000_requests = "per_1000_requests"
    per_user_day = "per_user_day"
    per_token = "per_token"
    per_training_run = "per_training_run"


@dataclass(frozen=True)
class SCIInputs:
    """
    Inputs to the SCI formula for one software system boundary.

    All energy and carbon values are for the measurement period defined
    by the system boundary. R normalises them to the functional unit rate.
    """
    energy_kwh: float
    "Total energy consumed by the software system (kWh) in the measurement period."

    grid_intensity_gco2_per_kwh: float
    "Location-based average grid carbon intensity (gCO2eq/kWh)."

    embodied_kgco2eq: float
    "Amortized embodied carbon for the hardware used (kgCO2eq). 0 if unavailable (must disclose)."

    r_count: float
    "Number of functional units in the measurement period (e.g. total requests)."

    functional_unit: FunctionalUnit = FunctionalUnit.per_request

    boundary_includes_training: bool = False
    "Whether training energy/carbon is included in E."

    boundary_includes_embodied: bool = False
    "Whether M is included. If False, embodied_kgco2eq must be 0 and omission disclosed."

    accounting_method: str = "location"
    "One of: 'location', 'market'. SCI spec prefers location-based."


@dataclass(frozen=True)
class SCIResult:
    """
    SCI score and its component breakdown.
    """
    sci_kgco2eq_per_r: float
    "SCI score: kgCO2eq per functional unit R."

    e_times_i_kgco2eq: float
    "Operational carbon component: E * I / 1000 (kgCO2eq) -- for all R units."

    m_kgco2eq: float
    "Embodied carbon component (kgCO2eq) -- for all R units."

    total_kgco2eq: float
    "Total carbon = E*I + M (kgCO2eq) -- for all R units."

    r_count: float
    functional_unit: FunctionalUnit
    boundary_includes_training: bool
    boundary_includes_embodied: bool
    accounting_method: str

    embodied_omitted: bool
    "True if embodied was set to 0 because data was unavailable."

    notes: list[str]
    "Audit trail: any spec constraints or disclosures that apply."


def compute_sci(inputs: SCIInputs) -> SCIResult:
    """
    Compute the SCI score from the given inputs.

    SCI = ((E * I) + M) / R

    - E * I converts kWh * gCO2/kWh to gCO2, divided by 1000 to kgCO2eq.
    - M is already in kgCO2eq.
    - Division by R gives per-functional-unit rate.

    Returns SCIResult.
    """
    if inputs.r_count <= 0:
        raise ValueError("r_count must be positive (SCI is a rate metric).")

    # E * I: operational carbon (kgCO2eq) for all R
    e_times_i_kg = inputs.energy_kwh * inputs.grid_intensity_gco2_per_kwh / 1000.0

    # M: embodied carbon (kgCO2eq) for all R
    m_kg = inputs.embodied_kgco2eq

    total_kg = e_times_i_kg + m_kg
    sci = total_kg / inputs.r_count

    # Multiplied-unit adjustment for per_1000_requests
    if inputs.functional_unit == FunctionalUnit.per_1000_requests:
        sci = sci * 1000.0

    notes: list[str] = []

    if inputs.accounting_method == "market":
        notes.append(
            "Accounting method is market-based (RECs/PPAs applied). "
            "SCI spec requires parallel location-based reporting. "
            "Carbon offsets do not reduce the SCI score."
        )

    embodied_omitted = not inputs.boundary_includes_embodied or m_kg == 0.0
    if embodied_omitted and inputs.embodied_kgco2eq == 0.0:
        notes.append(
            "Embodied carbon (M) is zero or omitted. "
            "Per SCI spec, omission must be disclosed and boundary documented."
        )

    if not inputs.boundary_includes_training:
        notes.append(
            "Training energy/carbon is NOT included in E. "
            "This is an inference-only boundary."
        )

    return SCIResult(
        sci_kgco2eq_per_r=round(sci, 8),
        e_times_i_kgco2eq=round(e_times_i_kg, 6),
        m_kgco2eq=round(m_kg, 6),
        total_kgco2eq=round(total_kg, 6),
        r_count=inputs.r_count,
        functional_unit=inputs.functional_unit,
        boundary_includes_training=inputs.boundary_includes_training,
        boundary_includes_embodied=inputs.boundary_includes_embodied,
        accounting_method=inputs.accounting_method,
        embodied_omitted=embodied_omitted,
        notes=notes,
    )
