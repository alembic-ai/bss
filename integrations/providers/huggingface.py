"""Hugging Face provider — inference via the Hugging Face Inference API.

Uses huggingface_hub's InferenceClient. Only imported when this provider is used.
"""

from __future__ import annotations

import os
import time

from integrations.providers import Provider


class HuggingFaceProvider(Provider):
    """Run inference via the Hugging Face Inference API."""

    def __init__(self):
        self._client = None
        self._model: str | None = None

    def load(self, config: dict) -> bool:
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            raise ImportError(
                "huggingface-hub is required for the huggingface backend. "
                "Install it with: pip install huggingface-hub"
            )

        api_key = (
            config.get("api_key")
            or os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        )

        self._model = config.get("model", "mistralai/Mistral-7B-Instruct-v0.3")

        try:
            self._client = InferenceClient(
                model=self._model,
                token=api_key,
            )
            return True
        except Exception as exc:
            import logging
            logging.getLogger("bss.provider.huggingface").error(
                "Failed to initialize HuggingFace client: %s", exc,
            )
            self._client = None
            self._model = None
            return False

    def unload(self) -> None:
        self._client = None
        self._model = None

    def is_loaded(self) -> bool:
        return self._client is not None and self._model is not None

    def infer(self, system_prompt: str, user_prompt: str, config: dict) -> tuple[str, int, float]:
        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ]

        start = time.time()

        try:
            response = self._client.chat_completion(
                messages=messages,
                max_tokens=config.get("max_tokens", 1024),
                temperature=config.get("temperature", 0.7),
            )

            elapsed = round(time.time() - start, 2)
            text = response.choices[0].message.content.strip()
            tokens = response.usage.completion_tokens
            return (text, tokens, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[inference error: {e}]", 0, elapsed)

    def chat(self, system_prompt: str, history: list[dict], user_msg: str, config: dict) -> tuple[str, int, float]:
        messages = [
            {"role": "system", "content": system_prompt.strip()},
        ]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_msg.strip()})

        start = time.time()

        try:
            response = self._client.chat_completion(
                messages=messages,
                max_tokens=config.get("max_tokens", 1024),
                temperature=config.get("temperature", 0.7),
            )

            elapsed = round(time.time() - start, 2)
            text = response.choices[0].message.content.strip()
            tokens = response.usage.completion_tokens
            return (text, tokens, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[chat error: {e}]", 0, elapsed)
