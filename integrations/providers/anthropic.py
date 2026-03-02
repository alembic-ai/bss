"""Anthropic provider — Claude models via the Anthropic API.

Uses the anthropic SDK. Only imported when this provider is used.
"""

from __future__ import annotations

import os
import time

from integrations.providers import Provider


class AnthropicProvider(Provider):
    """Run inference via the Anthropic Messages API."""

    def __init__(self):
        self._client = None
        self._model: str | None = None

    def load(self, config: dict) -> bool:
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic is required for the anthropic backend. "
                "Install it with: pip install anthropic"
            )

        api_key = config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return False

        self._model = config.get("model", "claude-sonnet-4-20250514")

        try:
            self._client = anthropic.Anthropic(api_key=api_key)
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
        start = time.time()

        try:
            response = self._client.messages.create(
                model=self._model,
                system=system_prompt.strip(),
                messages=[{"role": "user", "content": user_prompt.strip()}],
                max_tokens=config.get("max_tokens", 1024),
                temperature=config.get("temperature", 0.7),
            )

            elapsed = round(time.time() - start, 2)
            text = response.content[0].text.strip()
            tokens = response.usage.output_tokens
            return (text, tokens, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[inference error: {e}]", 0, elapsed)

    def chat(self, system_prompt: str, history: list[dict], user_msg: str, config: dict) -> tuple[str, int, float]:
        messages = []
        for msg in history:
            role = msg["role"]
            if role not in ("user", "assistant"):
                role = "user"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": user_msg.strip()})

        start = time.time()

        try:
            response = self._client.messages.create(
                model=self._model,
                system=system_prompt.strip(),
                messages=messages,
                max_tokens=config.get("max_tokens", 1024),
                temperature=config.get("temperature", 0.7),
            )

            elapsed = round(time.time() - start, 2)
            text = response.content[0].text.strip()
            tokens = response.usage.output_tokens
            return (text, tokens, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[chat error: {e}]", 0, elapsed)
