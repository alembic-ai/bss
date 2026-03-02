"""Gemini provider — Google Gemini models via the google-genai SDK.

Uses the google.genai client. Only imported when this provider is used.
"""

from __future__ import annotations

import os
import time

from integrations.providers import Provider


class GeminiProvider(Provider):
    """Run inference via the Google Gemini API."""

    def __init__(self):
        self._client = None
        self._model: str | None = None

    def load(self, config: dict) -> bool:
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-genai is required for the gemini backend. "
                "Install it with: pip install google-genai"
            )

        api_key = (
            config.get("api_key")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        if not api_key:
            return False

        self._model = config.get("model", "gemini-2.0-flash")

        try:
            self._client = genai.Client(api_key=api_key)
            return True
        except Exception:
            self._client = None
            self._model = None
            return False

    def unload(self) -> None:
        self._client = None
        self._model = None

    def is_loaded(self) -> bool:
        return self._client is not None and self._model is not None

    def infer(self, system_prompt: str, user_prompt: str, config: dict) -> tuple[str, int, float]:
        from google.genai import types

        start = time.time()

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt.strip(),
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt.strip(),
                    max_output_tokens=config.get("max_tokens", 1024),
                    temperature=config.get("temperature", 0.7),
                ),
            )

            elapsed = round(time.time() - start, 2)
            text = response.text.strip()
            tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            return (text, tokens, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[inference error: {e}]", 0, elapsed)

    def chat(self, system_prompt: str, history: list[dict], user_msg: str, config: dict) -> tuple[str, int, float]:
        from google.genai import types

        contents = []
        for msg in history:
            role = msg["role"]
            if role == "assistant":
                role = "model"
            elif role != "user":
                role = "user"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])],
            ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_msg.strip())],
        ))

        start = time.time()

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt.strip(),
                    max_output_tokens=config.get("max_tokens", 1024),
                    temperature=config.get("temperature", 0.7),
                ),
            )

            elapsed = round(time.time() - start, 2)
            text = response.text.strip()
            tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            return (text, tokens, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[chat error: {e}]", 0, elapsed)
