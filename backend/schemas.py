"""
Frozen Pydantic v2 schemas for the Sustainable AI Lifecycle Auditor.

These interfaces are locked. Do not change field names or types without
updating all consumers and bumping the schema_version constant.

Schema version: 1
"""
from __future__ import annotations

from typing import Annotated, Literal
from enum import Enum

from pydantic import BaseModel, Field, model_validator, computed_field


SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Core quantity type -- every number shown in the UI must be a Quantity.
# ---------------------------------------------------------------------------

class Tier(str, Enum):
    """Whether the number came from direct measurement or computation."""
    measured = "measured"
    modeled = "modeled"


class Quantity(BaseModel):
    """
    A single numeric estimate with uncertainty range, provenance, and tier.

    Invariants (enforced):
      - low <= value <= high
      - unit must be a non-empty string
      - source must be a non-empty string
      - tier determines how to display confidence: 'measured' vs 'modeled'

    The range (low, high) is the 5th-to-95th percentile range produced by
    Monte Carlo propagation under stated assumptions (see uncertainty.py).
    All modeled ranges carry the label "under stated assumptions" in the UI.
    """
    value: float
    low: float
    high: float
    unit: str = Field(min_length=1)
    tier: Tier
    source: str = Field(min_length=1)
    method_note: str = Field(
        default="",
        description="Short note on how this number was produced.",
    )

    @model_validator(mode="after")
    def range_is_valid(self) -> "Quantity":
        if not (self.low <= self.value <= self.high):
            raise ValueError(
                f"Quantity invariant violated: low ({self.low}) <= value "
                f"({self.value}) <= high ({self.high}) must hold. "
                f"unit={self.unit!r} source={self.source!r}"
            )
        return self


# ---------------------------------------------------------------------------
# Lifecycle ledger
# ---------------------------------------------------------------------------

class AccountingMethod(str, Enum):
    location = "location"
    market = "market"


class Boundary(str, Enum):
    operational = "operational"
    full_lifecycle = "full_lifecycle"


class LedgerAssumptions(BaseModel):
    """
    Every assumption that can change a number is documented here.
    The UI shows this block alongside any result so the user can audit it.
    """
    grid_intensity_gco2_per_kwh: Quantity
    pue: float = Field(gt=1.0, description="Power Usage Effectiveness (>1.0).")
    pue_source: str = Field(description="Where this PUE value came from.")
    utilization: float = Field(gt=0.0, le=1.0, description="Fraction of peak TDP drawn.")
    utilization_source: str
    hardware_lifetime_years: float = Field(gt=0.0)
    hardware_lifetime_source: str
    region: str
    accounting: AccountingMethod
    monte_carlo_n_samples: int = Field(default=1000, gt=0)
    monte_carlo_seed: int = Field(default=42)
    note: str = Field(
        default=(
            "All ranges labeled 'under stated assumptions'. "
            "Changing any assumption can move results outside this range."
        )
    )


class LifecycleLedger(BaseModel):
    """
    Full or operational carbon/energy ledger for one AI system configuration.

    All component fields are in kg CO2e. energy_kwh is in kWh.
    per_request is in kg CO2e per request.
    """
    boundary: Boundary
    training: Quantity        # kg CO2e
    inference: Quantity       # kg CO2e (annualised at stated traffic)
    embodied_hardware: Quantity  # kg CO2e (amortised over lifetime)
    retraining: Quantity      # kg CO2e
    storage: Quantity         # kg CO2e
    network: Quantity         # kg CO2e
    energy_kwh: Quantity      # kWh total
    per_request: Quantity     # kg CO2e per request
    assumptions: LedgerAssumptions
    schema_version: int = SCHEMA_VERSION

    @computed_field
    @property
    def total_carbon(self) -> Quantity:
        """Total carbon footprint for this boundary in kgCO2e."""
        if self.boundary == Boundary.operational:
            val = self.training.value + self.inference.value
            low = self.training.low + self.inference.low
            high = self.training.high + self.inference.high
            method = "Sum of operational training and inference carbon."
        else:
            val = (
                self.training.value
                + self.inference.value
                + self.embodied_hardware.value
                + self.retraining.value
                + self.storage.value
                + self.network.value
            )
            low = (
                self.training.low
                + self.inference.low
                + self.embodied_hardware.low
                + self.retraining.low
                + self.storage.low
                + self.network.low
            )
            high = (
                self.training.high
                + self.inference.high
                + self.embodied_hardware.high
                + self.retraining.high
                + self.storage.high
                + self.network.high
            )
            method = "Sum of training, inference, embodied, retraining, storage, and network carbon."

        return Quantity(
            value=round(val, 2),
            low=round(low, 2),
            high=round(high, 2),
            unit="kgCO2e",
            tier=self.inference.tier,
            source="Aggregated lifecycle ledger carbon.",
            method_note=method,
        )

    @computed_field
    @property
    def total_energy(self) -> Quantity:
        """Total energy consumption in kWh."""
        return self.energy_kwh


# ---------------------------------------------------------------------------
# System inventory -- what the user tells us about their AI system
# ---------------------------------------------------------------------------

class GPUSpec(BaseModel):
    model: str = Field(description="GPU model string, e.g. 'NVIDIA A100 80GB SXM4'.")
    count: int = Field(gt=0)
    tdp_w: float | None = Field(
        default=None,
        description=(
            "Thermal Design Power in Watts. If None, looked up from reference table. "
            "User-supplied value takes precedence."
        ),
    )


class TrainingConfig(BaseModel):
    gpu: GPUSpec
    duration_hours: float = Field(gt=0.0)
    pue: float | None = Field(default=None, description="Override datacenter PUE for training.")
    region: str | None = Field(default=None, description="Override region for training grid intensity.")
    n_epochs: int = Field(default=1, gt=0)


class InferenceConfig(BaseModel):
    gpu: GPUSpec
    runtime_hours: float = Field(default=8760.0, gt=0.0, description="Operational inference runtime hours (default 8760.0 = 1 year).")
    batch_size: int = Field(default=1, gt=0)
    requests_per_day: float = Field(gt=0.0)
    avg_tokens_per_request: int = Field(default=512, gt=0)
    p95_latency_limit_ms: float | None = Field(
        default=None,
        description="Hard latency constraint. Candidates exceeding this are excluded from Pareto.",
    )


class ModelSpec(BaseModel):
    name: str
    family: str = Field(description="e.g. 'llama', 'gpt', 'mistral'")
    params_billions: float = Field(gt=0.0)
    precision: Literal["fp32", "fp16", "bf16", "int8", "int4"] = "fp16"
    framework: str = Field(default="pytorch")


class SystemInventory(BaseModel):
    """
    Structured description of an AI system to audit.

    Fields not present in a parsed config file stay None and are shown
    to the user as 'please confirm' in the UI.
    """
    model: ModelSpec | None = None
    training: TrainingConfig | None = None
    inference: InferenceConfig | None = None
    region: str = Field(
        default="global",
        description="Primary deployment region. Used for grid intensity lookup.",
    )
    retraining_frequency_days: float | None = Field(
        default=None,
        description="How often the model is retrained. None means no retraining.",
    )
    storage_tb: float | None = Field(
        default=None,
        description="Storage footprint in TB (model weights, data, checkpoints).",
    )
    network_requests_per_day: float | None = Field(
        default=None,
        description="Daily request count for network transfer estimation.",
    )
    accuracy_floor: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable accuracy (0-1). Recommender excludes configs below this.",
    )
    distillation_training_hours: float | None = Field(
        default=None,
        gt=0.0,
        description="Customizable distillation training run hours (default 50.0h).",
    )
    note: str = Field(default="", description="Free-text notes from config parser.")


# ---------------------------------------------------------------------------
# Claim and verdict
# ---------------------------------------------------------------------------

class BoundaryStated(BaseModel):
    includes_training: bool | None = None
    includes_embodied: bool | None = None
    includes_retraining: bool | None = None
    accounting: Literal["location", "market", "unspecified"] = "unspecified"


class Claim(BaseModel):
    """
    A structured efficiency claim extracted from free text or a model card.

    Fields left None mean the information was absent or ambiguous in the source.
    Never guess missing boundary fields: leave them unspecified / None.
    """
    claim_text: str
    metric: Literal["energy", "carbon", "latency", "cost"]
    claimed_change_pct: float | None = None
    baseline_ref: str | None = None
    subject_ref: str | None = None
    boundary_stated: BoundaryStated
    hardware: str | None = None
    region: str | None = None
    accuracy_change_reported: bool = False
    accuracy_change_pct: float | None = None
    source_type: Literal["vendor", "paper", "model_card", "blog", "unknown"] = "unknown"
    source_url: str | None = None
    extraction_source: Literal["gemini", "rules_fallback", "user_specified"] = "user_specified"


class ClaimToLedgerMapping(BaseModel):
    """
    User-supplied mapping that links a Claim to computed LifecycleLedgers.

    Can supply both operational ledgers (baseline_ledger, subject_ledger)
    and full-lifecycle ledgers (baseline_ledger_full, subject_ledger_full).
    If full-lifecycle ledgers are omitted, the checker uses baseline_ledger
    and subject_ledger under their native boundary.
    """
    claim: Claim
    baseline_ledger: LifecycleLedger
    subject_ledger: LifecycleLedger
    baseline_ledger_full: LifecycleLedger | None = None
    subject_ledger_full: LifecycleLedger | None = None


class ReasonStep(BaseModel):
    step: int
    check: str
    result: Literal["pass", "fail", "warn", "skip"]
    evidence: str


class VerdictLabel(str, Enum):
    supported = "supported"
    contradicted = "contradicted"
    suspicious_boundary_shift = "suspicious_boundary_shift"
    insufficient_evidence = "insufficient_evidence"


class Verdict(BaseModel):
    label: VerdictLabel
    resolved_by: Literal["rules", "classifier", "llm"]
    reason_chain: list[ReasonStep]
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence [0,1]. None means the check is deterministic.",
    )
    schema_version: int = SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Recommender
# ---------------------------------------------------------------------------

class AccuracySource(str, Enum):
    """How the accuracy estimate for a candidate was obtained."""
    user_sample_eval = "user_sample_eval"
    cited_published_delta = "cited_published_delta"
    not_available = "not_available"


class RecommenderCandidate(BaseModel):
    """One architecture candidate evaluated by the recommender."""
    label: str = Field(description="Human-readable name, e.g. 'INT8 quantized on A100'.")
    inventory: SystemInventory
    ledger_operational: LifecycleLedger
    ledger_full: LifecycleLedger
    # Accuracy
    accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    accuracy_source: AccuracySource = AccuracySource.not_available
    accuracy_source_citation: str | None = Field(
        default=None,
        description=(
            "DOI, URL, or dataset name if accuracy_source is 'cited_published_delta'. "
            "Dataset split name if 'user_sample_eval'."
        ),
    )
    # Latency
    p95_latency_ms: Quantity | None = None
    latency_constraint_met: bool = True
    latency_exclusion_reason: str | None = None
    # Break-even
    break_even_requests: float | None = Field(
        default=None,
        description=(
            "Requests at which this candidate's full-lifecycle cost drops below "
            "the baseline operational cost. None if no training overhead."
        ),
    )
    # Cascade split
    cascade_split: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of traffic handled by this (small) model in a cascade. "
            "Either user-supplied or router-model output."
        ),
    )
    cascade_split_source: Literal["user_input", "router_output", "not_applicable"] = (
        "not_applicable"
    )
    # Distillation training method and carbon
    distillation_training_cost_method: str | None = Field(
        default=None,
        description="Accounting method and parameters for one-time distillation training run, if applicable.",
    )
    distillation_training_carbon: Quantity | None = Field(
        default=None,
        description="Modeled one-time distillation training carbon with uncertainty range [low, high].",
    )


class ParetoResult(BaseModel):
    """Pareto analysis output for the recommender screen across both boundaries."""
    boundary: Boundary
    candidates: list[RecommenderCandidate]
    pareto_front_labels: list[str]
    break_even_traffic_requests: float | None = None
    winner_operational: str | None = None
    winner_full_lifecycle: str | None = None
    winner_changed: bool = False
    qualifying_candidates_count: int = 0
    binding_constraint: str | None = None
    # Explicit dual-boundary rankings, Pareto points, and break-even
    rankings_operational: list[str] = Field(
        default_factory=list,
        description="Ranked candidate labels sorted by operational carbon (lowest to highest).",
    )
    rankings_full_lifecycle: list[str] = Field(
        default_factory=list,
        description="Ranked candidate labels sorted by full lifecycle carbon (lowest to highest).",
    )
    pareto_points_operational: list[str] = Field(
        default_factory=list,
        description="Non-dominated Pareto frontier labels under operational boundary.",
    )
    pareto_points_full_lifecycle: list[str] = Field(
        default_factory=list,
        description="Non-dominated Pareto frontier labels under full lifecycle boundary.",
    )
    break_even_operational_requests: float | None = Field(
        default=None,
        description="Break-even request volume under operational boundary.",
    )
    break_even_full_lifecycle_requests: float | None = Field(
        default=None,
        description="Break-even request volume under full lifecycle boundary.",
    )
