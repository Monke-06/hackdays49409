"""
backend/llm/gemini_client.py

Google GenAI SDK wrapper for Gemini models.
Provides resilient API calling with exponential backoff and structured output.
Gracefully degrades when GEMINI_API_KEY is not configured.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.5-flash-lite"


class GeminiClient:
    """Wrapper around google-genai Client with retry and structured output support."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self._client: Any = None
        self._cache: dict[str, str] = {}

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize Google GenAI Client: %s", e)
                self._client = None

    @property
    def is_available(self) -> bool:
        """Returns True if the client is initialized with an active API key."""
        return self._client is not None

    def generate_structured(
        self,
        prompt: str,
        json_schema: dict[str, Any],
        system_instruction: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any] | None:
        """
        Call Gemini with structured JSON output enforcing json_schema.
        Returns parsed JSON dict, or None on failure / missing API key.
        """
        if not self.is_available:
            logger.info("Gemini API key not configured; skipping LLM structured call.")
            return None

        # Check cache
        cache_key = f"{self.model}:{hash(prompt)}"
        if cache_key in self._cache:
            try:
                return json.loads(self._cache[cache_key])
            except Exception:
                pass

        from google.genai import types

        config_kwargs: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_json_schema": json_schema,
            "temperature": 0.0,
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_kwargs)

        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                raw_text = response.text
                if not raw_text:
                    return None
                parsed = json.loads(raw_text)
                self._cache[cache_key] = raw_text
                return parsed
            except Exception as exc:
                logger.warning(
                    "Gemini API attempt %d/%d failed: %s", attempt, max_retries, exc
                )
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2.0
                else:
                    return None

        return None
