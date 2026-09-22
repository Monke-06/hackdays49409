"""
backend/ledger/grid_intensity.py

Grid electricity carbon intensity lookup.

Data source:
    CO2.js (The Green Web Foundation), which bundles Ember Global Electricity
    Review data. License: CC BY 4.0 (Ember data).
    URL: https://github.com/thegreenwebfoundation/co2.js

The data file at data/reference/grid_intensity.json was fetched directly from
the CO2.js repository on 2026-09-22 and embedded as a versioned snapshot.

BLOOM training validation note:
    France (FRA) grid intensity used in BLOOM paper (Luccioni et al., 2023)
    was 57 gCO2eq/kWh (RTE 2022 actual). Our Ember 2024 value for France
    is 44.18 gCO2eq/kWh. For BLOOM validation we use the paper's value (57)
    as the reference, not our 2024 value, and document the discrepancy.

Uncertainty model:
    Grid intensity varies year-to-year and within-year. We model uncertainty
    as +/-20% around the annual average (uniform distribution), reflecting
    the difference between average and marginal/hourly intensity, and
    year-to-year variation. This is conservative and noted as such.
    Label: 'under stated assumptions'.
"""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

_DATA_FILE = Path(__file__).parent.parent.parent / "data" / "reference" / "grid_intensity.json"

# Cloud region to ISO-3166-1 alpha-3 country code mapping for common cloud providers.
# Sources: AWS, GCP, Azure region documentation.
CLOUD_REGION_TO_ISO3: dict[str, str] = {
    # AWS
    "us-east-1": "USA",
    "us-east-2": "USA",
    "us-west-1": "USA",
    "us-west-2": "USA",
    "eu-west-1": "IRL",
    "eu-west-2": "GBR",
    "eu-west-3": "FRA",
    "eu-central-1": "DEU",
    "eu-north-1": "SWE",
    "eu-south-1": "ITA",
    "ap-southeast-1": "SGP",
    "ap-southeast-2": "AUS",
    "ap-northeast-1": "JPN",
    "ap-northeast-2": "KOR",
    "ap-south-1": "IND",
    "ca-central-1": "CAN",
    "sa-east-1": "BRA",
    "cn-north-1": "CHN",
    "cn-northwest-1": "CHN",
    # GCP
    "us-central1": "USA",
    "us-east1": "USA",
    "us-east4": "USA",
    "us-west1": "USA",
    "us-west2": "USA",
    "us-west3": "USA",
    "us-west4": "USA",
    "europe-west1": "BEL",
    "europe-west2": "GBR",
    "europe-west3": "DEU",
    "europe-west4": "NLD",
    "europe-west6": "CHE",
    "europe-north1": "FIN",
    "asia-east1": "TWN",
    "asia-east2": "HKG",
    "asia-northeast1": "JPN",
    "asia-northeast2": "JPN",
    "asia-southeast1": "SGP",
    "australia-southeast1": "AUS",
    "southamerica-east1": "BRA",
    # Azure
    "eastus": "USA",
    "eastus2": "USA",
    "westus": "USA",
    "westus2": "USA",
    "westus3": "USA",
    "northeurope": "IRL",
    "westeurope": "NLD",
    "uksouth": "GBR",
    "ukwest": "GBR",
    "francecentral": "FRA",
    "germanywestcentral": "DEU",
    "swedencentral": "SWE",
    "norwayeast": "NOR",
    "japaneast": "JPN",
    "japanwest": "JPN",
    "southeastasia": "SGP",
    "eastasia": "HKG",
    "australiaeast": "AUS",
    "brazilsouth": "BRA",
    "centralindia": "IND",
    "southindia": "IND",
    "koreacentral": "KOR",
    "canadacentral": "CAN",
    # Jean Zay (BLOOM training)
    "jean-zay": "FRA",
    "idris": "FRA",
    # Generic
    "global": "World",
}


@lru_cache(maxsize=1)
def _load_data() -> dict:
    """Load grid intensity JSON once and cache it."""
    with open(_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_metadata() -> dict:
    """Return the dataset metadata block."""
    return _load_data()["_metadata"]


def lookup(region: str) -> dict:
    """
    Look up grid carbon intensity for a region identifier.

    Args:
        region: ISO-3166-1 alpha-3 code (e.g. 'FRA'), cloud region name
                (e.g. 'eu-west-3'), or a common alias ('global', 'world').

    Returns:
        dict with keys:
            gco2_per_kwh: float   -- point estimate
            year: int             -- data year
            country_or_region: str
            source: str
            low_gco2_per_kwh: float   -- p5 estimate (value * 0.80)
            high_gco2_per_kwh: float  -- p95 estimate (value * 1.20)
            uncertainty_note: str

    Raises:
        KeyError: if the region cannot be resolved.
    """
    data = _load_data()
    entries = data["entries"]

    # Normalize
    key = region.strip()

    # Direct ISO3 lookup
    if key in entries:
        entry = entries[key]
        return _build_result(entry)

    # Cloud region alias
    if key.lower() in CLOUD_REGION_TO_ISO3:
        iso3 = CLOUD_REGION_TO_ISO3[key.lower()]
        if iso3 in entries:
            entry = entries[iso3]
            return _build_result(entry)

    # Case-insensitive country name search
    key_lower = key.lower()
    for code, entry in entries.items():
        if entry.get("country_or_region", "").lower() == key_lower:
            return _build_result(entry)

    # Try "world" as fallback alias
    if key_lower in ("world", "global", ""):
        entry = entries.get("World") or entries.get("world")
        if entry:
            return _build_result(entry)

    raise KeyError(
        f"Region {region!r} not found in grid intensity database. "
        f"Use an ISO-3166-1 alpha-3 code (e.g. 'FRA') or a cloud region name."
    )


def _build_result(entry: dict) -> dict:
    """Attach uncertainty range and source metadata to a raw entry."""
    meta = get_metadata()
    v = entry["emissions_intensity_gco2_per_kwh"]
    return {
        "gco2_per_kwh": v,
        "low_gco2_per_kwh": round(v * 0.80, 2),   # -20%: annual variation and marginal vs average
        "high_gco2_per_kwh": round(v * 1.20, 2),  # +20%
        "year": entry.get("year"),
        "country_or_region": entry.get("country_or_region"),
        "source": meta["source"],
        "source_url": meta["source_url"],
        "ember_license": meta["ember_license"],
        "uncertainty_note": (
            "Range reflects +/-20% of the annual average intensity, "
            "approximating the spread between average and marginal/hourly grid intensity "
            "and year-to-year variation. Under stated assumptions."
        ),
    }


def list_available_regions() -> list[str]:
    """Return all ISO3 codes in the database."""
    return list(_load_data()["entries"].keys())
