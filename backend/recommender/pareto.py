"""
backend/recommender/pareto.py

Computes the Pareto frontier of accuracy vs carbon/energy under both accounting boundaries.
Detects boundary-dependent winner shifts and calculates break-even traffic.
"""
from __future__ import annotations

from backend.schemas import (
    Boundary,
    ParetoResult,
    RecommenderCandidate,
)


def _get_candidate_cost(candidate: RecommenderCandidate, boundary: Boundary) -> float:
    """Get carbon emissions in kgCO2e for the specified boundary."""
    if boundary == Boundary.operational:
        return candidate.ledger_operational.total_carbon.value
    else:
        return candidate.ledger_full.total_carbon.value


def compute_pareto_frontier(
    candidates: list[RecommenderCandidate],
    boundary: Boundary = Boundary.operational,
    accuracy_floor: float | None = None,
) -> ParetoResult:
    """
    Compute the Pareto-optimal frontier among valid candidates.

    Filters out candidates that violate:
      1. Latency constraint (`latency_constraint_met == False`)
      2. Accuracy floor (`accuracy < accuracy_floor`)

    Identifies non-dominated architectures (minimizing carbon, maximizing accuracy).
    Compares winners between operational and full-lifecycle boundaries.
    """
    # 1. Filter viable candidates
    viable: list[RecommenderCandidate] = []
    for c in candidates:
        if not c.latency_constraint_met:
            continue
        if accuracy_floor is not None and c.accuracy is not None and c.accuracy < accuracy_floor:
            continue
        viable.append(c)

    if not viable:
        # Determine binding constraint that excluded candidates
        latency_failed = [c for c in candidates if not c.latency_constraint_met]
        accuracy_failed = [
            c for c in candidates
            if accuracy_floor is not None and c.accuracy is not None and c.accuracy < accuracy_floor
        ]

        if len(latency_failed) == len(candidates):
            min_lat = min(c.p95_latency_ms.value for c in candidates if c.p95_latency_ms is not None)
            limit_val = (
                candidates[0].inventory.inference.p95_latency_limit_ms
                if candidates[0].inventory and candidates[0].inventory.inference
                else None
            )
            binding_str = (
                f"Latency constraint: p95 latency limit ({limit_val}ms) exceeded by all candidates "
                f"(minimum candidate latency is {min_lat:.1f}ms)."
            )
        elif len(accuracy_failed) == len(candidates):
            max_acc = max(c.accuracy for c in candidates if c.accuracy is not None)
            binding_str = (
                f"Accuracy constraint: accuracy floor ({accuracy_floor}) exceeds all candidate accuracies "
                f"(maximum candidate accuracy is {max_acc:.3f})."
            )
        else:
            binding_str = (
                f"Multiple constraints binding: {len(latency_failed)}/{len(candidates)} candidates exceeded latency limit, "
                f"and {len(accuracy_failed)}/{len(candidates)} failed accuracy floor ({accuracy_floor})."
            )

        return ParetoResult(
            boundary=boundary,
            candidates=candidates,
            pareto_front_labels=[],
            break_even_traffic_requests=None,
            winner_operational=None,
            winner_full_lifecycle=None,
            winner_changed=False,
            qualifying_candidates_count=0,
            binding_constraint=binding_str,
            rankings_operational=[],
            rankings_full_lifecycle=[],
            pareto_points_operational=[],
            pareto_points_full_lifecycle=[],
            break_even_operational_requests=None,
            break_even_full_lifecycle_requests=None,
        )

    # Helper for Pareto calculation
    def _find_pareto(cands: list[RecommenderCandidate], b: Boundary) -> list[str]:
        labels: list[str] = []
        for c1 in cands:
            cost1 = _get_candidate_cost(c1, b)
            acc1 = c1.accuracy or 0.0
            dominated = False
            for c2 in cands:
                if c1.label == c2.label:
                    continue
                cost2 = _get_candidate_cost(c2, b)
                acc2 = c2.accuracy or 0.0
                if (cost2 <= cost1 and acc2 >= acc1) and (cost2 < cost1 or acc2 > acc1):
                    dominated = True
                    break
            if not dominated:
                labels.append(c1.label)
        return labels

    # 2. Pareto points for both boundaries
    pareto_op = _find_pareto(viable, Boundary.operational)
    pareto_full = _find_pareto(viable, Boundary.full_lifecycle)
    target_pareto = pareto_op if boundary == Boundary.operational else pareto_full

    # 3. Full rankings for both boundaries
    ranked_op = [c.label for c in sorted(viable, key=lambda c: _get_candidate_cost(c, Boundary.operational))]
    ranked_full = [c.label for c in sorted(viable, key=lambda c: _get_candidate_cost(c, Boundary.full_lifecycle))]

    winner_op = ranked_op[0] if ranked_op else None
    winner_full = ranked_full[0] if ranked_full else None
    winner_changed = (winner_op != winner_full) if (winner_op and winner_full) else False

    # 4. Break-even traffic
    break_even_full: float | None = None
    break_even_op: float | None = None
    for c in viable:
        if c.break_even_requests is not None and c.break_even_requests > 0:
            if break_even_full is None or c.break_even_requests < break_even_full:
                break_even_full = c.break_even_requests

    return ParetoResult(
        boundary=boundary,
        candidates=candidates,
        pareto_front_labels=target_pareto,
        break_even_traffic_requests=break_even_full,
        winner_operational=winner_op,
        winner_full_lifecycle=winner_full,
        winner_changed=winner_changed,
        qualifying_candidates_count=len(viable),
        binding_constraint=None,
        rankings_operational=ranked_op,
        rankings_full_lifecycle=ranked_full,
        pareto_points_operational=pareto_op,
        pareto_points_full_lifecycle=pareto_full,
        break_even_operational_requests=break_even_op,
        break_even_full_lifecycle_requests=break_even_full,
    )
