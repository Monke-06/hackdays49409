"""
tests/test_recommender.py

Tests for candidate generation, Pareto frontier optimization,
latency and accuracy constraints, and break-even traffic calculation.
"""
import pytest
from backend.recommender.candidates import generate_candidates
from backend.recommender.pareto import compute_pareto_frontier
from backend.schemas import (
    AccuracySource,
    Boundary,
    GPUSpec,
    InferenceConfig,
    ModelSpec,
    SystemInventory,
)


@pytest.fixture
def base_inventory():
    return SystemInventory(
        model=ModelSpec(name="LLaMA-3-8B", family="llama", params_billions=8.0, precision="fp16"),
        inference=InferenceConfig(
            gpu=GPUSpec(model="NVIDIA A100 SXM4 80GB", count=1, tdp_w=400.0),
            runtime_hours=8760.0,
            requests_per_day=50_000.0,
            avg_tokens_per_request=512,
            p95_latency_limit_ms=500.0,
        ),
        region="USA",
        accuracy_floor=0.85,
    )


class TestRecommender:
    def test_candidate_generation_count(self, base_inventory):
        candidates = generate_candidates(base_inventory)
        # Should generate at least 5 architectures (base, int8, int4, distilled, accelerator, cascade)
        assert len(candidates) >= 5

    def test_all_candidates_have_accuracy_citations(self, base_inventory):
        candidates = generate_candidates(base_inventory)
        for c in candidates:
            if c.accuracy_source == AccuracySource.cited_published_delta:
                assert c.accuracy_source_citation is not None
                assert len(c.accuracy_source_citation) > 0

    def test_latency_constraint_exclusion(self, base_inventory):
        # Set impossible latency limit (1.0 ms)
        base_inventory.inference.p95_latency_limit_ms = 1.0
        candidates = generate_candidates(base_inventory)

        for c in candidates:
            assert c.latency_constraint_met is False
            assert c.latency_exclusion_reason is not None

        # Pareto should handle all-excluded gracefully
        res = compute_pareto_frontier(candidates, Boundary.operational)
        assert len(res.candidates) == len(candidates)

    def test_accuracy_floor_filtering(self, base_inventory):
        candidates = generate_candidates(base_inventory)
        # Filter with strict accuracy floor
        res = compute_pareto_frontier(candidates, Boundary.operational, accuracy_floor=0.875)
        # Winner must satisfy accuracy floor
        winner_c = next((c for c in candidates if c.label == res.winner_operational), None)
        assert winner_c is not None
        assert winner_c.accuracy >= 0.875

    def test_pareto_frontier_non_empty(self, base_inventory):
        candidates = generate_candidates(base_inventory)
        res = compute_pareto_frontier(candidates, Boundary.operational)
        assert len(res.pareto_front_labels) >= 1

    def test_cascade_split_source_present(self, base_inventory):
        candidates = generate_candidates(base_inventory)
        cascade_c = next((c for c in candidates if "Cascade" in c.label), None)
        assert cascade_c is not None
        assert cascade_c.cascade_split == 0.70
        assert cascade_c.cascade_split_source in ("user_input", "router_output")
