"""
backend/main.py

FastAPI production server for Sustainable AI Lifecycle Auditor.
Exposes REST endpoints for lifecycle ledger calculations, claim checking,
and Pareto architecture recommendations.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.claims.cascade import evaluate_claim_cascade
from backend.claims.checker import check_claim
from backend.ledger.engine import compute_ledgers, LedgerEngineConfig
from backend.ledger.grid_intensity import list_available_regions
from backend.llm.claim_extractor import extract_claim_from_text
from backend.llm.gemini_client import GeminiClient
from backend.recommender.candidates import generate_candidates
from backend.recommender.pareto import compute_pareto_frontier
from backend.schemas import (
    Boundary,
    Claim,
    ClaimToLedgerMapping,
    LifecycleLedger,
    ParetoResult,
    SystemInventory,
    Verdict,
)

# App state container
state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager: initializes services on startup."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    state["gemini_client"] = GeminiClient(api_key=gemini_key, model=gemini_model)
    state["available_regions"] = list_available_regions()
    yield
    state.clear()


app = FastAPI(
    title="Sustainable AI Lifecycle Auditor API",
    description="Estimates lifecycle energy, carbon, and hardware footprint of AI systems.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class LedgerResponse(BaseModel):
    operational: LifecycleLedger
    full_lifecycle: LifecycleLedger


class LedgerRequest(BaseModel):
    inventory: SystemInventory
    config: LedgerEngineConfig | None = None


class RecommendRequest(BaseModel):
    inventory: SystemInventory
    boundary: Boundary = Boundary.operational
    accuracy_floor: float | None = Field(default=None, ge=0.0, le=1.0)


class ExtractClaimRequest(BaseModel):
    text: str


class HealthResponse(BaseModel):
    status: str
    version: str
    gemini_available: bool
    gemini_model: str
    regions_count: int


class ModelPreset(BaseModel):
    name: str
    family: str
    params_billions: float
    precision: str = "fp16"


class HardwareOption(BaseModel):
    model: str
    tdp_w: float
    vram_gb: int | None = None


class RegionOption(BaseModel):
    code: str
    name: str
    intensity_gco2_per_kwh: float
    year: int


class PresetScenario(BaseModel):
    id: str
    name: str
    description: str
    inventory: SystemInventory


class MetadataResponse(BaseModel):
    models: list[ModelPreset]
    hardware: list[HardwareOption]
    regions: list[RegionOption]
    preset_scenarios: list[PresetScenario]


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Service health and capability reporting."""
    client: GeminiClient = state.get("gemini_client")
    is_avail = client.is_available if client else False
    model_name = client.model if client else "unconfigured"
    regions: list = state.get("available_regions", [])

    return HealthResponse(
        status="ok",
        version="1.0.0",
        gemini_available=is_avail,
        gemini_model=model_name,
        regions_count=len(regions),
    )


@app.get("/api/v1/regions", response_model=list[str])
async def get_regions():
    """List all supported geographical and cloud regions for grid carbon intensity."""
    return state.get("available_regions", list_available_regions())


@app.get("/api/v1/meta", response_model=MetadataResponse)
@app.get("/api/v1/presets", response_model=MetadataResponse)
async def get_metadata_and_presets():
    """
    Returns available models, hardware options, geographical regions,
    and preset scenarios (inputs only) so the frontend hardcodes nothing.
    """
    from pathlib import Path
    import json
    from backend.schemas import GPUSpec, InferenceConfig, ModelSpec, TrainingConfig

    ref_dir = Path(__file__).parent.parent / "data" / "reference"

    # 1. Models
    models = [
        ModelPreset(name="LLaMA-3-8B", family="llama", params_billions=8.0, precision="fp16"),
        ModelPreset(name="LLaMA-3-70B", family="llama", params_billions=70.0, precision="fp16"),
        ModelPreset(name="Mistral-7B-v0.3", family="mistral", params_billions=7.0, precision="fp16"),
        ModelPreset(name="Phi-3-Mini-3.8B", family="phi", params_billions=3.8, precision="fp16"),
        ModelPreset(name="BLOOM-176B", family="bloom", params_billions=176.0, precision="fp16"),
        ModelPreset(name="GPT-3-175B", family="gpt", params_billions=175.0, precision="fp16"),
    ]

    # 2. Hardware
    hardware: list[HardwareOption] = []
    gpu_file = ref_dir / "gpu_embodied.json"
    if gpu_file.exists():
        try:
            with open(gpu_file, "r", encoding="utf-8") as f:
                gpu_data = json.load(f)
            tdp_table = gpu_data.get("tdp_reference_w", {})
            for hw_name, spec in tdp_table.items():
                if not hw_name.startswith("_"):
                    hardware.append(
                        HardwareOption(
                            model=hw_name,
                            tdp_w=float(spec.get("tdp_w", 300)),
                            vram_gb=spec.get("vram_gb"),
                        )
                    )
        except Exception:
            pass

    # 3. Regions
    regions: list[RegionOption] = []
    grid_file = ref_dir / "grid_intensity.json"
    if grid_file.exists():
        try:
            with open(grid_file, "r", encoding="utf-8") as f:
                grid_data = json.load(f)
            entries = grid_data.get("entries", {})
            for code, data in entries.items():
                if not code.startswith("_"):
                    regions.append(
                        RegionOption(
                            code=code,
                            name=data.get("country_or_region", code),
                            intensity_gco2_per_kwh=float(data.get("emissions_intensity_gco2_per_kwh", 400.0)),
                            year=int(data.get("year", 2024)),
                        )
                    )
        except Exception:
            pass

    # 4. Preset Scenarios (Input-only SystemInventory specifications)
    scenarios = [
        PresetScenario(
            id="bloom_training",
            name="BLOOM-176B Training Reproduction",
            description="384x NVIDIA A100 SXM4 80GB, 118 calendar days in France (Jean Zay cluster, PUE 1.2).",
            inventory=SystemInventory(
                model=ModelSpec(name="BLOOM-176B", family="bloom", params_billions=176.0, precision="fp16"),
                training=TrainingConfig(
                    gpu=GPUSpec(model="NVIDIA A100 SXM4 80GB", count=384, tdp_w=400.0),
                    duration_hours=2832.0,
                    pue=1.2,
                    region="FRA",
                ),
                region="FRA",
                accuracy_floor=0.70,
            ),
        ),
        PresetScenario(
            id="enterprise_chatbot",
            name="Enterprise RAG Chatbot Serving",
            description="Single A100 80GB serving 50,000 queries/day in US East datacenter.",
            inventory=SystemInventory(
                model=ModelSpec(name="LLaMA-3-8B", family="llama", params_billions=8.0, precision="fp16"),
                inference=InferenceConfig(
                    gpu=GPUSpec(model="NVIDIA A100 SXM4 80GB", count=1, tdp_w=400.0),
                    runtime_hours=8760.0,
                    requests_per_day=50000.0,
                    avg_tokens_per_request=512,
                    p95_latency_limit_ms=450.0,
                ),
                region="USA",
                accuracy_floor=0.85,
            ),
        ),
        PresetScenario(
            id="edge_serving",
            name="High-Efficiency Edge/Local Inference",
            description="NVIDIA L4 72W accelerator running a compact 3.8B model in Germany.",
            inventory=SystemInventory(
                model=ModelSpec(name="Phi-3-Mini-3.8B", family="phi", params_billions=3.8, precision="int8"),
                inference=InferenceConfig(
                    gpu=GPUSpec(model="NVIDIA L4", count=1, tdp_w=72.0),
                    runtime_hours=8760.0,
                    requests_per_day=15000.0,
                    avg_tokens_per_request=256,
                    p95_latency_limit_ms=250.0,
                ),
                region="DEU",
                accuracy_floor=0.80,
            ),
        ),
        PresetScenario(
            id="datacenter_batch",
            name="High-Throughput Datacenter Batch Processing",
            description="4x H100 SXM5 GPUs processing 250,000 requests/day in Norway (low-carbon grid).",
            inventory=SystemInventory(
                model=ModelSpec(name="LLaMA-3-70B", family="llama", params_billions=70.0, precision="int4"),
                inference=InferenceConfig(
                    gpu=GPUSpec(model="NVIDIA H100 SXM5 80GB", count=4, tdp_w=700.0),
                    runtime_hours=8760.0,
                    requests_per_day=250000.0,
                    avg_tokens_per_request=512,
                    p95_latency_limit_ms=600.0,
                ),
                region="NOR",
                accuracy_floor=0.85,
            ),
        ),
    ]

    return MetadataResponse(
        models=models,
        hardware=hardware,
        regions=regions,
        preset_scenarios=scenarios,
    )


@app.post("/api/v1/ledger", response_model=LedgerResponse)
async def calculate_ledger(request: LedgerRequest):
    """
    Compute dual lifecycle ledgers (operational and full_lifecycle)
    for a given AI system inventory.
    """
    try:
        cfg = request.config or LedgerEngineConfig()
        op, full = compute_ledgers(request.inventory, cfg)
        return LedgerResponse(operational=op, full_lifecycle=full)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/claims/check", response_model=Verdict)
async def check_efficiency_claim(mapping: ClaimToLedgerMapping):
    """
    Audit an efficiency claim against baseline and subject ledgers
    using the deterministic multi-tier verification cascade.
    """
    client: GeminiClient | None = state.get("gemini_client")
    try:
        return evaluate_claim_cascade(mapping, allow_llm=True, gemini_client=client)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/claims/extract", response_model=Claim)
async def extract_claim(request: ExtractClaimRequest):
    """
    Extract a structured Claim object from free-text marketing copy,
    research papers, or model cards.
    """
    client: GeminiClient | None = state.get("gemini_client")
    try:
        return extract_claim_from_text(request.text, client)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/recommend", response_model=ParetoResult)
async def recommend_architectures(request: RecommendRequest):
    """
    Generate alternative architectures, evaluate full lifecycle ledgers,
    filter constraints, and compute Pareto frontier.
    """
    try:
        candidates = generate_candidates(request.inventory)
        result = compute_pareto_frontier(
            candidates=candidates,
            boundary=request.boundary,
            accuracy_floor=request.accuracy_floor,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
