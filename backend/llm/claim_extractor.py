"""
backend/llm/claim_extractor.py

Extracts structured Claim instances from natural language text using Gemini.
Provides a deterministic rule-based fallback when Gemini API key is unavailable.
"""
from __future__ import annotations

import re
from typing import Any
from backend.llm.gemini_client import GeminiClient
from backend.schemas import (
    BoundaryStated,
    Claim,
    ClaimToLedgerMapping,
    ReasonStep,
    Verdict,
    VerdictLabel,
)


SYSTEM_INSTRUCTION = """
You are an expert auditor for AI sustainability claims.
Your job is to extract structured efficiency claims from model cards, marketing blogs, or papers.
Extract only the factual statements present in the text.
Never invent or guess boundary information:
- If embodied carbon or manufacturing is not explicitly mentioned, leave includes_embodied as null.
- If retraining is not mentioned, leave includes_retraining as null.
- If training vs inference is not distinguished, leave includes_training as null.
- Set accounting to 'location', 'market', or 'unspecified'.
"""


def _fallback_heuristic_extraction(text: str) -> Claim:
    """Deterministic regex heuristic extractor when Gemini is not configured."""
    lower = text.lower()

    # Metric detection
    metric = "carbon"
    if "energy" in lower or "kwh" in lower or "mwh" in lower or "joule" in lower:
        metric = "energy"
    elif "latency" in lower or "speed" in lower or "throughput" in lower or "ms" in lower:
        metric = "latency"
    elif "cost" in lower or "dollar" in lower or "$" in lower:
        metric = "cost"

    # Percentage detection
    change_pct: float | None = None
    pct_match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
    if pct_match:
        change_pct = float(pct_match.group(1))
        # If text says "cuts 70%" or "reduced by 70%", treat as -70%
        if any(w in lower for w in ["cut", "cuts", "reduc", "save", "lower", "drop"]):
            change_pct = -abs(change_pct)

    # Boundary detection
    includes_emb = True if "embodied" in lower or "manufacturing" in lower else None
    includes_retrain = True if "retrain" in lower or "continuous learning" in lower else None
    includes_train = True if "training" in lower else (False if "inference only" in lower else None)

    return Claim(
        claim_text=text,
        metric=metric,
        claimed_change_pct=change_pct,
        baseline_ref="standard baseline",
        subject_ref="optimized system",
        boundary_stated=BoundaryStated(
            includes_training=includes_train,
            includes_embodied=includes_emb,
            includes_retraining=includes_retrain,
            accounting="unspecified",
        ),
        accuracy_change_reported=("accuracy" in lower or "eval" in lower),
        source_type="unknown",
        extraction_source="rules_fallback",
    )


def extract_claim_from_text(
    text: str,
    client: GeminiClient | None = None,
) -> Claim:
    """
    Extract a structured Claim object from free text.
    Uses Gemini when available, falls back to deterministic parsing.
    """
    if client and client.is_available:
        prompt = f"Extract a structured efficiency claim from the following text:\n\n{text}"
        schema = Claim.model_json_schema()
        # Remove description fields that might cause schema issues
        res = client.generate_structured(
            prompt=prompt,
            json_schema=schema,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        if res:
            try:
                claim = Claim.model_validate(res)
                claim.extraction_source = "gemini"
                return claim
            except Exception:
                pass

    return _fallback_heuristic_extraction(text)


def evaluate_claim_with_llm(
    mapping: ClaimToLedgerMapping,
    client: GeminiClient,
) -> Verdict | None:
    """Tier 3 LLM auditor for ambiguous claims."""
    if not client or not client.is_available:
        return None

    prompt = (
        f"Audit this AI efficiency claim against the following computed numbers:\n"
        f"Claim: '{mapping.claim.claim_text}'\n"
        f"Claimed change: {mapping.claim.claimed_change_pct}%\n"
        f"Baseline operational carbon: {mapping.baseline_ledger.total_carbon.value} kgCO2e\n"
        f"Subject operational carbon: {mapping.subject_ledger.total_carbon.value} kgCO2e\n"
        f"Baseline full lifecycle carbon: {mapping.baseline_ledger.total_carbon.value + mapping.baseline_ledger.embodied_hardware.value} kgCO2e\n"
        f"Subject full lifecycle carbon: {mapping.subject_ledger.total_carbon.value + mapping.subject_ledger.embodied_hardware.value} kgCO2e\n\n"
        f"Determine if the claim is 'supported', 'contradicted', 'suspicious_boundary_shift', or 'insufficient_evidence'."
    )

    schema = Verdict.model_json_schema()
    res = client.generate_structured(prompt=prompt, json_schema=schema)
    if res:
        try:
            verdict = Verdict.model_validate(res)
            verdict.resolved_by = "llm"
            return verdict
        except Exception:
            pass

    return None
