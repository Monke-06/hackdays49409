"""
backend/recommender/__init__.py
"""
from backend.recommender.candidates import generate_candidates
from backend.recommender.pareto import compute_pareto_frontier

__all__ = ["generate_candidates", "compute_pareto_frontier"]
