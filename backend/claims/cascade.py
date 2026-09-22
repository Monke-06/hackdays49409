"""
backend/claims/cascade.py

Three-tier claim verification cascade:
  Tier 1: Deterministic rules (always runs first, fast, reproducible).
  Tier 2: Machine learning classifier (optional, when trained models available).
  Tier 3: Gemini structured verification (for ambiguous free-text cases).
"""
from __future__ import annotations

from typing import Any
from backend.claims.checker import check_claim
from backend.schemas import (
    ClaimToLedgerMapping,
    ReasonStep,
    Verdict,
    VerdictLabel,
)


def evaluate_claim_cascade(
    mapping: ClaimToLedgerMapping,
    allow_llm: bool = True,
    gemini_client: Any | None = None,
) -> Verdict:
    """
    Run the multi-tier verification cascade.

    Stops at the first decisive tier. Falls back to deterministic rules
    if LLM is unavailable or unconfigured.
    """
    # Tier 1: Deterministic rules
    verdict_t1 = check_claim(mapping)

    # If rules are decisive, return immediately
    if verdict_t1.label in (
        VerdictLabel.supported,
        VerdictLabel.contradicted,
        VerdictLabel.suspicious_boundary_shift,
    ):
        return verdict_t1

    # Tier 2: Classifier (placeholder: currently non-existent or passes through)
    # If a trained classifier is loaded in future iterations, run it here.

    # Tier 3: LLM evaluation (only for ambiguous cases when allowed and available)
    if allow_llm and gemini_client is not None:
        try:
            from backend.llm.claim_extractor import evaluate_claim_with_llm
            llm_verdict = evaluate_claim_with_llm(mapping, gemini_client)
            if llm_verdict is not None:
                return llm_verdict
        except Exception:
            # Graceful degradation to Tier 1 verdict
            pass

    return verdict_t1
