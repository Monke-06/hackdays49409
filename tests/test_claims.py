"""
tests/test_claims.py

Unit and integration tests for the deterministic claim verification engine and cascade.
"""
import pytest
from backend.claims.checker import check_claim, resolve_verdict_label, compute_paired_relative_change_mc
from backend.claims.cascade import evaluate_claim_cascade
from backend.ledger.engine import compute_ledgers, LedgerEngineConfig
from backend.schemas import (
    Boundary,
    BoundaryStated,
    Claim,
    ClaimToLedgerMapping,
    GPUSpec,
    InferenceConfig,
    ModelSpec,
    Quantity,
    SystemInventory,
    VerdictLabel,
)


@pytest.fixture
def sample_inventory_pair():
    """Create baseline and optimized subject inventories for testing."""
    base_inv = SystemInventory(
        model=ModelSpec(name="Base-7B", family="llama", params_billions=7.0, precision="fp16"),
        inference=InferenceConfig(
            gpu=GPUSpec(model="NVIDIA A100 SXM4 80GB", count=1, tdp_w=400.0),
            runtime_hours=1000.0,
            requests_per_day=10_000.0,
            avg_tokens_per_request=512,
        ),
        region="USA",
    )

    # Subject: 50% power reduction (e.g. quantized/efficient)
    subj_inv = SystemInventory(
        model=ModelSpec(name="Opt-7B", family="llama", params_billions=7.0, precision="int8"),
        inference=InferenceConfig(
            gpu=GPUSpec(model="NVIDIA A100 SXM4 80GB", count=1, tdp_w=200.0),
            runtime_hours=1000.0,
            requests_per_day=10_000.0,
            avg_tokens_per_request=512,
        ),
        region="USA",
    )

    cfg = LedgerEngineConfig()
    base_op, base_full = compute_ledgers(base_inv, cfg)
    subj_op, subj_full = compute_ledgers(subj_inv, cfg)

    return base_op, subj_op, base_full, subj_full


class TestClaimChecker:
    def test_supported_claim_operational(self, sample_inventory_pair):
        base_op, subj_op, _, _ = sample_inventory_pair

        # Claim: cuts energy by 50%
        claim = Claim(
            claim_text="Our optimization cuts energy consumption by 50%.",
            metric="energy",
            claimed_change_pct=-50.0,
            boundary_stated=BoundaryStated(
                includes_training=False,
                includes_embodied=False,
                includes_retraining=False,
            ),
            accuracy_change_reported=True,
            accuracy_change_pct=-0.1,
        )

        mapping = ClaimToLedgerMapping(
            claim=claim,
            baseline_ledger=base_op,
            subject_ledger=subj_op,
        )

        verdict = check_claim(mapping)
        assert verdict.label == VerdictLabel.supported
        assert verdict.resolved_by == "rules"
        assert len(verdict.reason_chain) >= 3

    def test_contradicted_claim_direction(self, sample_inventory_pair):
        base_op, subj_op, _, _ = sample_inventory_pair

        # Claim asserts energy increased or stayed same when it decreased
        claim = Claim(
            claim_text="Our system increases throughput and consumes 50% more energy.",
            metric="energy",
            claimed_change_pct=50.0,
            boundary_stated=BoundaryStated(),
        )

        mapping = ClaimToLedgerMapping(
            claim=claim,
            baseline_ledger=base_op,
            subject_ledger=subj_op,
        )

        verdict = check_claim(mapping)
        assert verdict.label == VerdictLabel.contradicted
        assert any(step.result == "fail" for step in verdict.reason_chain)

    def test_insufficient_evidence_when_unquantified(self, sample_inventory_pair):
        base_op, subj_op, _, _ = sample_inventory_pair

        claim = Claim(
            claim_text="Our system is significantly greener and more sustainable.",
            metric="carbon",
            claimed_change_pct=None,
            boundary_stated=BoundaryStated(),
        )

        mapping = ClaimToLedgerMapping(
            claim=claim,
            baseline_ledger=base_op,
            subject_ledger=subj_op,
        )

        verdict = check_claim(mapping)
        assert verdict.label == VerdictLabel.insufficient_evidence

    def test_suspicious_boundary_shift_detection(self):
        """
        When a claim states 50% carbon reduction, but subject uses massive embodied hardware
        that reverses savings under full lifecycle.
        """
        # Create a synthetic boundary shift ledger pair
        base_inv = SystemInventory(
            inference=InferenceConfig(
                gpu=GPUSpec(model="NVIDIA A100 SXM4 80GB", count=1, tdp_w=400.0),
                runtime_hours=100.0,
                requests_per_day=1_000.0,
            ),
            region="FRA",
        )
        # Subject has tiny runtime (low operational), but uses 16 H100 GPUs (huge embodied)
        subj_inv = SystemInventory(
            inference=InferenceConfig(
                gpu=GPUSpec(model="NVIDIA H100 SXM5 80GB", count=16, tdp_w=700.0),
                runtime_hours=20.0,
                requests_per_day=1_000.0,
            ),
            region="FRA",
        )
        cfg = LedgerEngineConfig()
        _, base_full = compute_ledgers(base_inv, cfg)
        _, subj_full = compute_ledgers(subj_inv, cfg)

        claim = Claim(
            claim_text="Cuts carbon footprint by 60% with accelerated cluster deployment.",
            metric="carbon",
            claimed_change_pct=-60.0,
            boundary_stated=BoundaryStated(includes_embodied=True),
        )

        mapping = ClaimToLedgerMapping(
            claim=claim,
            baseline_ledger=base_full,
            subject_ledger=subj_full,
        )

        verdict = check_claim(mapping)
        # Should be contradicted or suspicious_boundary_shift because subject has much higher full carbon
        assert verdict.label in (VerdictLabel.contradicted, VerdictLabel.suspicious_boundary_shift)

    def test_cascade_returns_decisive_tier1(self, sample_inventory_pair):
        base_op, subj_op, _, _ = sample_inventory_pair
        claim = Claim(
            claim_text="Saves 50% energy.",
            metric="energy",
            claimed_change_pct=-50.0,
            boundary_stated=BoundaryStated(),
        )
        mapping = ClaimToLedgerMapping(
            claim=claim,
            baseline_ledger=base_op,
            subject_ledger=subj_op,
        )
        verdict = evaluate_claim_cascade(mapping, allow_llm=False)
        assert verdict.label == VerdictLabel.supported
        assert verdict.resolved_by == "rules"

    def test_truth_table_all_12_cases(self):
        """
        Verify all 12 combinations of stated boundary vs match result.
        Stated: operational, full_lifecycle, unspecified (3)
        Match: both, operational_only, full_only, neither (4)
        Total: 3 * 4 = 12 cells.
        """
        cases = [
            # (says_op, says_full, op_match, full_match, expected_verdict)
            # 1. Stated = operational
            (True, False, True, True, VerdictLabel.supported),
            (True, False, True, False, VerdictLabel.supported),
            (True, False, False, True, VerdictLabel.contradicted),
            (True, False, False, False, VerdictLabel.contradicted),
            # 2. Stated = full_lifecycle
            (False, True, True, True, VerdictLabel.supported),
            (False, True, True, False, VerdictLabel.contradicted),  # Crucial rule: claim stating full matching only op MUST be contradicted!
            (False, True, False, True, VerdictLabel.supported),
            (False, True, False, False, VerdictLabel.contradicted),
            # 3. Stated = unspecified
            (False, False, True, True, VerdictLabel.supported),
            (False, False, True, False, VerdictLabel.suspicious_boundary_shift),  # Boundary shift detected!
            (False, False, False, True, VerdictLabel.supported),
            (False, False, False, False, VerdictLabel.contradicted),
        ]
        assert len(cases) == 12
        for says_op, says_full, op_match, full_match, expected in cases:
            res = resolve_verdict_label(
                says_operational=says_op,
                says_full=says_full,
                op_matches=op_match,
                full_matches=full_match,
            )
            assert res == expected, f"Failed for {says_op=}, {says_full=}, {op_match=}, {full_match=}: got {res}, expected {expected}"

    def test_paired_monte_carlo_2x_tight_range(self, sample_inventory_pair):
        """
        Paired Monte Carlo sampling: shared draws for grid, PUE, lifetime.
        Subject with 2x baseline workload produces a tight range around +100% (e.g. [93%, 107%]),
        not an uncorrelated wide range like [+20%, +233%].
        """
        base_op, _, _, _ = sample_inventory_pair
        q_base = Quantity(value=100.0, low=90.0, high=110.0, unit="kgCO2e", tier="modeled", source="test", method_note="")
        q_subj = Quantity(value=200.0, low=180.0, high=220.0, unit="kgCO2e", tier="modeled", source="test", method_note="")

        point, low, high = compute_paired_relative_change_mc(
            baseline_q=q_base,
            subject_q=q_subj,
            base_assumptions=base_op.assumptions,
            subj_assumptions=base_op.assumptions,  # identical grid, PUE, lifetime
            n_samples=2000,
            seed=42,
        )
        assert point == 100.0
        # Assert tight uncertainty bounds around +100%: within [90%, 110%]
        assert 92.0 <= low <= 96.0
        assert 104.0 <= high <= 108.0
        assert high - low < 20.0  # Tight range span < 20%

    def test_carbon_metric_claim(self, sample_inventory_pair):
        """
        Test a claim asserting carbon footprint savings across operational and full lifecycle boundaries.
        """
        base_op, subj_op, base_full, subj_full = sample_inventory_pair
        claim = Claim(
            claim_text="Reduces operational carbon footprint by 50%.",
            metric="carbon",
            claimed_change_pct=-50.0,
            boundary_stated=BoundaryStated(
                includes_training=False,
                includes_embodied=False,
            ),
        )
        mapping = ClaimToLedgerMapping(
            claim=claim,
            baseline_ledger=base_op,
            subject_ledger=subj_op,
            baseline_ledger_full=base_full,
            subject_ledger_full=subj_full,
        )
        verdict = check_claim(mapping)
        assert verdict.label == VerdictLabel.supported
        assert "carbon" in verdict.reason_chain[0].evidence
        assert len(verdict.reason_chain) >= 4
        boundary_step = [s for s in verdict.reason_chain if "Dual-boundary comparison" in s.check][0]
        assert boundary_step.result == "pass"

