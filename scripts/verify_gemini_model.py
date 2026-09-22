"""
scripts/verify_gemini_model.py

Live test: verify the configured Gemini model ID supports structured output
via response_mime_type='application/json' and response_json_schema.

Usage:
    python scripts/verify_gemini_model.py [model_id]

If model_id is omitted, reads GEMINI_MODEL from the environment (or .env).
Prints the resolved model ID, round-trip latency, and parsed output.
Exits 0 on success, 1 on failure.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on real env vars


def verify(model_id: str) -> bool:
    """
    Send one structured-output request to Gemini and validate the response.
    Returns True if successful, False otherwise.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set. Cannot run live test.")
        print("Set it in .env or export it before running this script.")
        return False

    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError:
        print("ERROR: google-genai not installed. Run: pip install google-genai")
        return False

    # Schema for the test: a simple extraction to confirm structured output works.
    test_schema = {
        "type": "object",
        "required": ["parsed_number", "unit"],
        "properties": {
            "parsed_number": {"type": "number"},
            "unit": {"type": "string"},
        },
    }

    prompt = (
        "Extract the numeric value and unit from this text as JSON: "
        "'The model used 42.7 kilowatt-hours of electricity during training.'"
    )

    print(f"Testing model: {model_id!r}")
    print(f"API key: {'*' * 8}{api_key[-4:]}")

    client = genai.Client(api_key=api_key)

    t0 = time.perf_counter()
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=test_schema,
                temperature=0,
            ),
        )
        latency_ms = (time.perf_counter() - t0) * 1000
    except Exception as exc:
        print(f"FAIL: API call raised {type(exc).__name__}: {exc}")
        return False

    raw = response.text
    print(f"Raw response: {raw!r}")
    print(f"Latency: {latency_ms:.0f} ms")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"FAIL: Response is not valid JSON: {exc}")
        return False

    if "parsed_number" not in parsed or "unit" not in parsed:
        print(f"FAIL: Required fields missing from response: {parsed}")
        return False

    if abs(parsed["parsed_number"] - 42.7) > 0.01:
        print(f"WARN: parsed_number={parsed['parsed_number']!r} differs from expected 42.7")

    print(f"OK: parsed_number={parsed['parsed_number']}, unit={parsed['unit']!r}")
    print(f"Model {model_id!r} supports structured output. Latency: {latency_ms:.0f} ms")
    return True


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    success = verify(model)
    sys.exit(0 if success else 1)
