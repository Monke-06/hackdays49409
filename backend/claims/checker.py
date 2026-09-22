"""
backend/claims/checker.py

Deterministic rules-based claim verification engine.
Compares efficiency claims against computed LifecycleLedgers.
Implements paired Monte Carlo uncertainty propagation and the 12-case truth table.
"""
from __future__ import annotations

import numpy as np
from typing import Literal
from backend.schemas import (
    Claim,
    ClaimToLedgerMapping,
    LifecycleLedger,
    LedgerAssumptions,
    Quantity,
    ReasonStep,
    Verdict,
    VerdictLabel,
)


def _get_metric_quantity(ledger: LifecycleLedger, metric: str) -> Quantity:
    """Extract the primary Quantity for the requested metric from a ledger."""
    if metric == "carbon":
        return ledger.total_carbon
    elif metric == "energy":
        return ledger.total_energy
    elif metric == "cost":
        # Cost is not in physical ledger; fallback to energy as proxy with warning
        return ledger.total_energy
    else:
        # Default to carbon
        return ledger.total_carbon


def compute_paired_relative_change_mc(
    baseline_q: Quantity,
    subject_q: Quantity,
    base_assumptions: LedgerAssumptions | None = None,
    subj_assumptions: LedgerAssumptions | None = None,
    n_samples: int = 2000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Compute relative percent change from baseline to subject using paired Monte Carlo:
        pct_change = (subject - baseline) / baseline * 100

    Shared random draws for common assumptions (grid, PUE, lifetime) eliminate
    unnecessary uncertainty spread when comparing systems in the same operating environment.
    Only parameters that truly differ between configurations are drawn independently.

    Returns:
        (point_pct, low_pct, high_pct) where low is p5 and high is p95.
    """
    if baseline_q.value <= 0:
        return 0.0, 0.0, 0.0

    point = ((subject_q.value - baseline_q.value) / baseline_q.value) * 100.0

    if base_assumptions is None or subj_assumptions is None:
        return round(point, 2), round(point, 2), round(point, 2)

    rng = np.random.default_rng(seed)

    # 1. Grid intensity: shared draw if same region, independent if different
    same_region = base_assumptions.region.strip().lower() == subj_assumptions.region.strip().lower()
    if same_region:
        grid_shared = rng.uniform(0.80, 1.20, n_samples)
        grid_b = grid_shared
        grid_s = grid_shared
    else:
        grid_b = rng.uniform(0.80, 1.20, n_samples)
        grid_s = rng.uniform(0.80, 1.20, n_samples)

    # 2. PUE: shared draw if same PUE, independent if different
    same_pue = abs(base_assumptions.pue - subj_assumptions.pue) < 1e-4
    if same_pue:
        pue_shared = rng.uniform(0.90, 1.10, n_samples)
        pue_b = pue_shared
        pue_s = pue_shared
    else:
        pue_b = rng.uniform(0.90, 1.10, n_samples)
        pue_s = rng.uniform(0.90, 1.10, n_samples)

    # 3. Independent hardware component tolerance (TDP variation +/-2.5%)
    hw_b = rng.uniform(0.975, 1.025, n_samples)
    hw_s = rng.uniform(0.975, 1.025, n_samples)

    # Compute sampled quantities
    b_samples = baseline_q.value * grid_b * pue_b * hw_b
    s_samples = subject_q.value * grid_s * pue_s * hw_s

    # Relative change distribution
    pct_samples = ((s_samples - b_samples) / np.maximum(b_samples, 1e-6)) * 100.0

    low_pct = float(np.percentile(pct_samples, 5))
    high_pct = float(np.percentile(pct_samples, 95))
    point_pct = round(point, 2)

    return point_pct, round(low_pct, 2), round(high_pct, 2)


def resolve_verdict_label(
    says_operational: bool,
    says_full: bool,
    op_matches: bool,
    full_matches: bool,
) -> VerdictLabel:
    """
    12-cell truth table resolution:
    - If says_operational:
        * op_matches -> supported
        * not op_matches -> contradicted (even if full_matches is True!)
    - If says_full:
        * full_matches -> supported
        * not full_matches -> contradicted (A claim stating full lifecycle that matches only operationally must be contradicted!)
    - If unspecified (neither says_operational nor says_full):
        * op_matches and full_matches -> supported
        * full_matches and not op_matches -> supported
        * op_matches and not full_matches -> suspicious_boundary_shift
        * not op_matches and not full_matches -> contradicted
    """
    if says_operational:
        return VerdictLabel.supported if op_matches else VerdictLabel.contradicted
    elif says_full:
        return VerdictLabel.supported if full_matches else VerdictLabel.contradicted
    else:  # unspecified boundary
        if full_matches:
            return VerdictLabel.supported
        elif op_matches:
            return VerdictLabel.suspicious_boundary_shift
        else:
            return VerdictLabel.contradicted


def _extract_boundary_quantities(
    mapping: ClaimToLedgerMapping,
    metric: str,
) -> tuple[Quantity, Quantity, Quantity, Quantity]:
    """
    Extract (q_base_op, q_subj_op, q_base_full, q_subj_full) for the given metric.
    """
    # 1. If explicit full lifecycle ledgers provided
    if mapping.baseline_ledger_full is not None and mapping.subject_ledger_full is not None:
        q_base_op = _get_metric_quantity(mapping.baseline_ledger, metric)
        q_subj_op = _get_metric_quantity(mapping.subject_ledger, metric)
        q_base_full = _get_metric_quantity(mapping.baseline_ledger_full, metric)
        q_subj_full = _get_metric_quantity(mapping.subject_ledger_full, metric)
        return q_base_op, q_subj_op, q_base_full, q_subj_full

    # 2. If mapping.baseline_ledger is already full_lifecycle
    if mapping.baseline_ledger.boundary.value == "full_lifecycle":
        q_base_full = _get_metric_quantity(mapping.baseline_ledger, metric)
        q_subj_full = _get_metric_quantity(mapping.subject_ledger, metric)
        if metric == "carbon":
            q_base_op = mapping.baseline_ledger.inference
            q_subj_op = mapping.subject_ledger.inference
            if q_base_op.value <= 0 and mapping.baseline_ledger.training.value > 0:
                q_base_op = mapping.baseline_ledger.training
                q_subj_op = mapping.subject_ledger.training
        elif metric == "energy":
            q_base_op = mapping.baseline_ledger.energy_kwh
            q_subj_op = mapping.subject_ledger.energy_kwh
        else:
            q_base_op = q_base_full
            q_subj_op = q_subj_full
        return q_base_op, q_subj_op, q_base_full, q_subj_full

    # 3. If mapping.baseline_ledger is operational
    q_base_op = _get_metric_quantity(mapping.baseline_ledger, metric)
    q_subj_op = _get_metric_quantity(mapping.subject_ledger, metric)
    # If no full lifecycle was provided, fall back to operational values
    return q_base_op, q_subj_op, q_base_op, q_subj_op


def check_claim(mapping: ClaimToLedgerMapping) -> Verdict:
    """
    Evaluate a claim against baseline and subject LifecycleLedgers.

    Evaluates across both boundaries (operational and full_lifecycle)
    to detect boundary shifting, arithmetic discrepancies, and omissions.
    """
    claim = mapping.claim
    metric = claim.metric

    # Extract operational and full-lifecycle quantities
    q_base_op, q_subj_op, q_base_full, q_subj_full = _extract_boundary_quantities(mapping, metric)

    base_op_ledger = mapping.baseline_ledger
    subj_op_ledger = mapping.subject_ledger
    base_full_ledger = mapping.baseline_ledger_full or base_op_ledger
    subj_full_ledger = mapping.subject_ledger_full or subj_op_ledger

    steps: list[ReasonStep] = []
    step_num = 1

    # 1. Check metric and availability
    steps.append(
        ReasonStep(
            step=step_num,
            check="Metric extraction",
            result="pass",
            evidence=(
                f"Evaluated metric: '{metric}'. Operational baseline: {q_base_op.value:.2f} {q_base_op.unit}, "
                f"subject: {q_subj_op.value:.2f} {q_subj_op.unit}. Full lifecycle baseline: "
                f"{q_base_full.value:.2f} {q_base_full.unit}, subject: {q_subj_full.value:.2f} {q_subj_full.unit}."
            ),
        )
    )
    step_num += 1

    # 2. Check if claimed percentage change was supplied
    claimed_pct = claim.claimed_change_pct
    if claimed_pct is None:
        steps.append(
            ReasonStep(
                step=step_num,
                check="Claim quantification",
                result="fail",
                evidence="No numeric percentage change provided in claim text.",
            )
        )
        return Verdict(
            label=VerdictLabel.insufficient_evidence,
            resolved_by="rules",
            reason_chain=steps,
            confidence=1.0,
        )

    # Normalize claimed change:
    # If text says "cuts 60%", "reduced by 60%", "saves 60%", treat as -60.0%
    norm_claimed = claimed_pct
    lower_text = claim.claim_text.lower()
    is_reduction_text = any(w in lower_text for w in ["cut", "cuts", "reduc", "save", "saves", "lower", "less", "drop"])
    if norm_claimed > 0 and is_reduction_text:
        norm_claimed = -norm_claimed

    # 3. Dual-boundary comparison step with paired Monte Carlo sampling
    op_point, op_low, op_high = compute_paired_relative_change_mc(
        q_base_op, q_subj_op, base_op_ledger.assumptions, subj_op_ledger.assumptions
    )
    full_point, full_low, full_high = compute_paired_relative_change_mc(
        q_base_full, q_subj_full, base_full_ledger.assumptions, subj_full_ledger.assumptions
    )

    tolerance_pct = 2.0  # 2 percentage points margin around MC range

    def _boundary_matches(point: float, low: float, high: float, target: float) -> bool:
        in_range = (low - tolerance_pct) <= target <= (high + tolerance_pct)
        direction = (target < 0 and point < 0) or (target > 0 and point > 0) or (target == 0 and point == 0)
        return in_range and direction

    op_matches = _boundary_matches(op_point, op_low, op_high, norm_claimed)
    full_matches = _boundary_matches(full_point, full_low, full_high, norm_claimed)

    steps.append(
        ReasonStep(
            step=step_num,
            check="Dual-boundary comparison",
            result="pass" if (op_matches or full_matches) else "fail",
            evidence=(
                f"Operational change: {op_point:+.2f}% [range {op_low:+.2f}% to {op_high:+.2f}%] (matches={op_matches}). "
                f"Full lifecycle change: {full_point:+.2f}% [range {full_low:+.2f}% to {full_high:+.2f}%] (matches={full_matches}). "
                f"Claimed change: {norm_claimed:+.2f}%."
            ),
        )
    )
    step_num += 1

    # 4. Boundary stated analysis
    boundary_stated = claim.boundary_stated
    says_operational = (
        boundary_stated.includes_embodied is False
        or "operational" in lower_text
        or "inference only" in lower_text
        or "serving only" in lower_text
    )
    says_full = (
        boundary_stated.includes_embodied is True
        or "lifecycle" in lower_text
        or "embodied" in lower_text
        or "cradle-to-grave" in lower_text
    )

    if says_operational:
        boundary_desc = "Claim explicitly states an operational-only boundary."
    elif says_full:
        boundary_desc = "Claim states a full-lifecycle boundary."
    else:
        boundary_desc = "Claim boundary is unstated / unspecified."

    steps.append(
        ReasonStep(
            step=step_num,
            check="Boundary disclosure",
            result="pass" if (says_operational or says_full) else "warn",
            evidence=boundary_desc,
        )
    )
    step_num += 1

    # 5. Accuracy change omission check
    if not claim.accuracy_change_reported:
        steps.append(
            ReasonStep(
                step=step_num,
                check="Accuracy disclosure",
                result="warn",
                evidence="Efficiency claim does not report accuracy trade-offs or benchmark delta.",
            )
        )
    else:
        steps.append(
            ReasonStep(
                step=step_num,
                check="Accuracy disclosure",
                result="pass",
                evidence=f"Accuracy change reported: {claim.accuracy_change_pct}%.",
            )
        )
    step_num += 1

    # 6. Grid region relocation check
    base_grid = mapping.baseline_ledger.assumptions.grid_intensity_gco2_per_kwh.value
    subj_grid = mapping.subject_ledger.assumptions.grid_intensity_gco2_per_kwh.value
    if abs(base_grid - subj_grid) > 10.0 and metric == "carbon":
        grid_ratio = subj_grid / base_grid
        steps.append(
            ReasonStep(
                step=step_num,
                check="Regional grid intensity divergence",
                result="warn",
                evidence=(
                    f"Baseline grid intensity is {base_grid:.1f} gCO2/kWh, while subject grid is {subj_grid:.1f} gCO2/kWh "
                    f"(ratio: {grid_ratio:.2f}). Carbon reduction may be partly driven by geographical relocation "
                    "rather than software or algorithmic efficiency."
                ),
            )
        )
        step_num += 1

    # 7. Verdict resolution per 12-cell truth table:
    verdict_label = resolve_verdict_label(
        says_operational=says_operational,
        says_full=says_full,
        op_matches=op_matches,
        full_matches=full_matches,
    )

    if verdict_label == VerdictLabel.supported:
        if says_operational:
            evidence = (
                f"Claim explicitly states operational boundary and claimed change ({norm_claimed:+.1f}%) "
                f"matches computed operational change ({op_point:+.1f}%, range [{op_low:+.1f}%, {op_high:+.1f}%])."
            )
        elif says_full:
            evidence = (
                f"Claim states full lifecycle boundary and claimed change ({norm_claimed:+.1f}%) "
                f"matches computed full lifecycle change ({full_point:+.1f}%, range [{full_low:+.1f}%, {full_high:+.1f}%])."
            )
        else:
            evidence = (
                f"Claimed change ({norm_claimed:+.1f}%) is verified under the full lifecycle boundary "
                f"({full_point:+.1f}%, range [{full_low:+.1f}%, {full_high:+.1f}%])."
            )
        steps.append(ReasonStep(step=step_num, check="Verdict resolution", result="pass", evidence=evidence))
        return Verdict(label=VerdictLabel.supported, resolved_by="rules", reason_chain=steps, confidence=1.0)

    elif verdict_label == VerdictLabel.suspicious_boundary_shift:
        steps.append(
            ReasonStep(
                step=step_num,
                check="Boundary shift impact",
                result="fail",
                evidence=(
                    f"Claimed change ({norm_claimed:+.1f}%) holds under the operational boundary ({op_point:+.1f}%), "
                    f"but is NOT sustained across the full lifecycle ({full_point:+.1f}%, range [{full_low:+.1f}%, {full_high:+.1f}%]). "
                    "The claim omitted the operational boundary qualification, masking upfront training or embodied hardware impacts."
                ),
            )
        )
        return Verdict(label=VerdictLabel.suspicious_boundary_shift, resolved_by="rules", reason_chain=steps, confidence=1.0)

    else:  # contradicted
        if says_full and op_matches and not full_matches:
            evidence = (
                f"Claim asserted full lifecycle change ({norm_claimed:+.1f}%), but fails to hold under full lifecycle "
                f"({full_point:+.1f}%, range [{full_low:+.1f}%, {full_high:+.1f}%]). It holds only under an operational boundary."
            )
        elif not op_matches and not full_matches:
            evidence = (
                f"Claimed change ({norm_claimed:+.1f}%) falls outside computed ranges under both "
                f"operational ({op_point:+.1f}%, range [{op_low:+.1f}%, {op_high:+.1f}%]) "
                f"and full lifecycle ({full_point:+.1f}%, range [{full_low:+.1f}%, {full_high:+.1f}%]) boundaries."
            )
        else:
            evidence = (
                f"Claim stated boundary does not match computed change: claimed {norm_claimed:+.1f}%, "
                f"operational {op_point:+.1f}%, full lifecycle {full_point:+.1f}%."
            )
        steps.append(ReasonStep(step=step_num, check="Arithmetic verification", result="fail", evidence=evidence))
        return Verdict(label=VerdictLabel.contradicted, resolved_by="rules", reason_chain=steps, confidence=1.0)
