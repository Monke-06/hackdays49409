"""
backend/claims/__init__.py
"""
from backend.claims.checker import check_claim
from backend.claims.cascade import evaluate_claim_cascade

__all__ = ["check_claim", "evaluate_claim_cascade"]
