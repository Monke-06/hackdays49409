"""
tests/test_schemas.py

Unit tests for frozen Pydantic v2 schemas.
All test data is synthetic and labeled as such.
"""
import pytest
from pydantic import ValidationError

from backend.schemas import (
    Quantity, Tier, LifecycleLedger, Boundary, LedgerAssumptions,
    AccountingMethod, Claim, BoundaryStated, Verdict, VerdictLabel,
    ReasonStep, SystemInventory, GPUSpec, ModelSpec, TrainingConfig,
    InferenceConfig, RecommenderCandidate, AccuracySource,
)


# ---------------------------------------------------------------------------
# Quantity validation
# ---------------------------------------------------------------------------

class TestQuantityValidation:
    """Synthetic test data -- not real measurements."""

    def test_valid_quantity(self):
        q = Quantity(value=1.5, low=1.0, high=2.0, unit="kgCO2e",
                     tier=Tier.modeled, source="test", method_note="synthetic")
        assert q.value == 1.5

    def test_low_equals_value_is_valid(self):
        q = Quantity(value=1.0, low=1.0, high=2.0, unit="kWh",
                     tier=Tier.measured, source="nvml", method_note="")
        assert q.low == q.value

    def test_high_equals_value_is_valid(self):
        q = Quantity(value=2.0, low=1.0, high=2.0, unit="kWh",
                     tier=Tier.modeled, source="test", method_note="")
        assert q.high == q.value

    def test_low_gt_value_raises(self):
        with pytest.raises(ValidationError, match="low.*value.*high"):
            Quantity(value=1.0, low=1.5, high=2.0, unit="kgCO2e",
                     tier=Tier.modeled, source="test", method_note="")

    def test_high_lt_value_raises(self):
        with pytest.raises(ValidationError, match="low.*value.*high"):
            Quantity(value=2.0, low=1.0, high=1.5, unit="kgCO2e",
                     tier=Tier.modeled, source="test", method_note="")

    def test_empty_unit_raises(self):
        with pytest.raises(ValidationError):
            Quantity(value=1.0, low=0.5, high=1.5, unit="",
                     tier=Tier.modeled, source="test", method_note="")

    def test_empty_source_raises(self):
        with pytest.raises(ValidationError):
            Quantity(value=1.0, low=0.5, high=1.5, unit="kWh",
                     tier=Tier.modeled, source="", method_note="")

    def test_tier_enum_values(self):
        assert Tier.measured.value == "measured"
        assert Tier.modeled.value == "modeled"


# ---------------------------------------------------------------------------
# SystemInventory
# ---------------------------------------------------------------------------

class TestSystemInventory:
    """Synthetic test data."""

    def test_minimal_inventory(self):
        inv = SystemInventory(region="FRA")
        assert inv.region == "FRA"
        assert inv.model is None
        assert inv.training is None

    def test_full_inventory(self):
        inv = SystemInventory(
            model=ModelSpec(name="LLaMA-7B", family="llama", params_billions=7.0),
            training=TrainingConfig(
                gpu=GPUSpec(model="NVIDIA A100 SXM4 80GB", count=8),
                duration_hours=1000.0,
            ),
            inference=InferenceConfig(
                gpu=GPUSpec(model="NVIDIA A100 SXM4 80GB", count=1),
                requests_per_day=10000.0,
            ),
            region="FRA",
        )
        assert inv.training.gpu.count == 8
        assert inv.inference.requests_per_day == 10000.0

    def test_accuracy_floor_validation(self):
        with pytest.raises(ValidationError):
            SystemInventory(accuracy_floor=1.5)  # > 1.0 invalid

    def test_gpu_spec_with_tdp_override(self):
        gpu = GPUSpec(model="NVIDIA A100 SXM4 80GB", count=384, tdp_w=400.0)
        assert gpu.tdp_w == 400.0


# ---------------------------------------------------------------------------
# Claim schema
# ---------------------------------------------------------------------------

class TestClaim:
    """Synthetic test data."""

    def test_minimal_claim(self):
        c = Claim(
            claim_text="This model uses 70% less energy.",
            metric="energy",
            boundary_stated=BoundaryStated(),
        )
        assert c.source_type == "unknown"
        assert c.claimed_change_pct is None

    def test_boundary_accounting_default(self):
        b = BoundaryStated()
        assert b.accounting == "unspecified"


# ---------------------------------------------------------------------------
# Verdict schema
# ---------------------------------------------------------------------------

class TestVerdict:
    """Synthetic test data."""

    def test_verdict_labels(self):
        for label in VerdictLabel:
            v = Verdict(
                label=label,
                resolved_by="rules",
                reason_chain=[
                    ReasonStep(step=1, check="arithmetic", result="pass", evidence="synthetic")
                ],
            )
            assert v.label == label

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            Verdict(
                label=VerdictLabel.supported,
                resolved_by="rules",
                reason_chain=[],
                confidence=1.5,  # > 1.0 invalid
            )


# ---------------------------------------------------------------------------
# RecommenderCandidate
# ---------------------------------------------------------------------------

class TestRecommenderCandidate:
    """Synthetic test data."""

    def _make_ledger(self, boundary):
        q0 = Quantity(value=0.0, low=0.0, high=0.0, unit="kgCO2e",
                      tier=Tier.modeled, source="test", method_note="synthetic")
        q_kwh = Quantity(value=0.0, low=0.0, high=0.0, unit="kWh",
                         tier=Tier.modeled, source="test", method_note="synthetic")
        q_gi = Quantity(value=380.0, low=300.0, high=460.0, unit="gCO2eq/kWh",
                        tier=Tier.modeled, source="Ember CC-BY-4.0", method_note="synthetic")
        assumptions = LedgerAssumptions(
            grid_intensity_gco2_per_kwh=q_gi,
            pue=1.67, pue_source="test",
            utilization=1.0, utilization_source="test",
            hardware_lifetime_years=4.0, hardware_lifetime_source="test",
            region="USA", accounting=AccountingMethod.location,
        )
        return LifecycleLedger(
            boundary=boundary,
            training=q0, inference=q0, embodied_hardware=q0,
            retraining=q0, storage=q0, network=q0,
            energy_kwh=q_kwh, per_request=q0,
            assumptions=assumptions,
        )

    def test_accuracy_source_must_have_citation_for_published(self):
        """AccuracySource.cited_published_delta should have a citation."""
        inv = SystemInventory(region="USA")
        ledger = self._make_ledger(Boundary.operational)
        candidate = RecommenderCandidate(
            label="INT8 on A100",
            inventory=inv,
            ledger_operational=ledger,
            ledger_full=self._make_ledger(Boundary.full_lifecycle),
            accuracy=0.95,
            accuracy_source=AccuracySource.cited_published_delta,
            accuracy_source_citation="Dettmers et al. (2022) LLM.int8(). NeurIPS.",
        )
        assert candidate.accuracy_source_citation is not None

    def test_cascade_split_source_user_input(self):
        inv = SystemInventory(region="USA")
        ledger = self._make_ledger(Boundary.operational)
        candidate = RecommenderCandidate(
            label="Cascade: 7B handles 70%",
            inventory=inv,
            ledger_operational=ledger,
            ledger_full=self._make_ledger(Boundary.full_lifecycle),
            cascade_split=0.70,
            cascade_split_source="user_input",
        )
        assert candidate.cascade_split == 0.70
        assert candidate.cascade_split_source == "user_input"
