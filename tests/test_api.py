"""
tests/test_api.py

Integration tests for FastAPI endpoints in backend/main.py.
"""
import pytest
from starlette.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestAPIEndpoints:
    def test_health_check(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert "gemini_available" in data
        assert data["regions_count"] > 100

    def test_get_regions(self, client):
        resp = client.get("/api/v1/regions")
        assert resp.status_code == 200
        regions = resp.json()
        assert isinstance(regions, list)
        assert "FRA" in regions
        assert "USA" in regions
        assert "DEU" in regions

    def test_post_ledger_minimal(self, client):
        payload = {
            "inventory": {
                "inference": {
                    "gpu": {
                        "model": "NVIDIA A100 SXM4 80GB",
                        "count": 1,
                        "tdp_w": 400.0,
                    },
                    "runtime_hours": 100.0,
                    "requests_per_day": 1000.0,
                },
                "region": "FRA",
            }
        }
        resp = client.post("/api/v1/ledger", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "operational" in data
        assert "full_lifecycle" in data
        assert data["operational"]["boundary"] == "operational"
        assert data["full_lifecycle"]["boundary"] == "full_lifecycle"
        assert data["operational"]["total_carbon"]["value"] > 0
        assert data["full_lifecycle"]["total_carbon"]["value"] >= data["operational"]["total_carbon"]["value"]

    def test_post_claims_extract(self, client):
        payload = {"text": "Our new distillation cuts energy consumption by 45% on A100 GPUs."}
        resp = client.post("/api/v1/claims/extract", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["metric"] == "energy"
        assert data["claimed_change_pct"] == -45.0

    def test_post_recommend(self, client):
        payload = {
            "inventory": {
                "model": {
                    "name": "Mistral-7B",
                    "family": "mistral",
                    "params_billions": 7.0,
                    "precision": "fp16",
                },
                "inference": {
                    "gpu": {
                        "model": "NVIDIA A100 SXM4 80GB",
                        "count": 1,
                        "tdp_w": 400.0,
                    },
                    "runtime_hours": 1000.0,
                    "requests_per_day": 50000.0,
                },
                "region": "USA",
            },
            "boundary": "operational",
            "accuracy_floor": 0.85,
        }
        resp = client.post("/api/v1/recommend", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "candidates" in data
        assert len(data["candidates"]) >= 5
        assert "pareto_front_labels" in data
        assert len(data["pareto_front_labels"]) >= 1
        assert data["winner_operational"] is not None

        # Verify Condition 4 & 5: dual boundary rankings and candidate fields
        assert "rankings_operational" in data
        assert "rankings_full_lifecycle" in data
        assert "pareto_points_operational" in data
        assert "pareto_points_full_lifecycle" in data
        assert len(data["rankings_operational"]) >= 5
        assert len(data["rankings_full_lifecycle"]) >= 5

        # Check candidate fields: cascade_split, accuracy_source, distillation_training_cost_method
        distilled = next(c for c in data["candidates"] if "Distilled" in c["label"])
        assert distilled["distillation_training_cost_method"] is not None
        assert "distillation" in distilled["distillation_training_cost_method"].lower()

        cascade = next(c for c in data["candidates"] if "Cascade" in c["label"])
        assert cascade["cascade_split"] == 0.70
        assert cascade["cascade_split_source"] == "user_input"

    def test_get_metadata_and_presets(self, client):
        resp = client.get("/api/v1/meta")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert len(data["models"]) >= 4
        assert "hardware" in data
        assert len(data["hardware"]) >= 5
        assert "regions" in data
        assert len(data["regions"]) > 100
        assert "preset_scenarios" in data
        assert len(data["preset_scenarios"]) >= 4

        # Confirm presets endpoint returns identical payload
        presets_resp = client.get("/api/v1/presets")
        assert presets_resp.status_code == 200
        assert len(presets_resp.json()["preset_scenarios"]) >= 4
