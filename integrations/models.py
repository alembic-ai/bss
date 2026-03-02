"""BSS ModelManager — single-model-at-a-time inference via pluggable providers.

Config keyed by BSS roster sigil. Backend field selects the provider
(default: "gguf" for backwards compatibility).
"""

from __future__ import annotations

import os
import re
import time
import threading

import yaml

from integrations.providers import Provider, get_provider


def _load_config(config_path: str | None = None) -> dict:
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if not os.path.exists(config_path):
        return {"models": {}}
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {"models": {}}


class ModelManager:
    """Manages model loading and inference, one model at a time.

    Models are keyed by BSS roster sigil (A, B, etc.).
    Backend is determined by the `backend` field in config (default: "gguf").
    Thread-safe: all model operations are locked.
    """

    def __init__(self, config_path: str | None = None):
        self._config = _load_config(config_path)
        self._provider: Provider | None = None
        self._model_sigil: str | None = None
        self._lock = threading.Lock()

    def _get_model_config(self, sigil: str) -> dict:
        return self._config.get("models", {}).get(sigil, {})

    @property
    def available_models(self) -> dict[str, dict]:
        """Return {sigil: config} for all configured models."""
        return dict(self._config.get("models", {}))

    @property
    def loaded_sigil(self) -> str | None:
        return self._model_sigil

    def load(self, sigil: str) -> bool:
        """Load a model by sigil. Unloads current model first if different."""
        with self._lock:
            if self._model_sigil == sigil and self._provider is not None and self._provider.is_loaded():
                return True

            if self._provider is not None:
                self._provider.unload()
                self._provider = None
                self._model_sigil = None

            cfg = self._get_model_config(sigil)
            if not cfg:
                return False

            backend = cfg.get("backend", "gguf")

            try:
                provider = get_provider(backend)
            except (ValueError, ImportError):
                return False

            if not provider.load(cfg):
                return False

            self._provider = provider
            self._model_sigil = sigil
            return True

    def is_loaded(self, sigil: str) -> bool:
        return self._model_sigil == sigil and self._provider is not None and self._provider.is_loaded()

    def unload(self) -> None:
        with self._lock:
            if self._provider is not None:
                self._provider.unload()
                self._provider = None
                self._model_sigil = None

    @staticmethod
    def _strip_think(response: str) -> str:
        """Remove <think> blocks from Qwen3 responses."""
        response = re.sub(r"<think>.*?</think>\s*", "", response, flags=re.DOTALL).strip()
        if "<think>" in response and "</think>" not in response:
            response = response.split("<think>")[0].strip()
        return response

    def infer(self, sigil: str, system_prompt: str, user_prompt: str) -> tuple[str, int, float]:
        """Single-turn inference. Returns (response_text, tokens, elapsed_seconds)."""
        if not self.load(sigil):
            cfg = self._get_model_config(sigil)
            name = cfg.get("name", sigil) if cfg else sigil
            return (f"[{name} could not be loaded]", 0, 0.0)

        cfg = self._get_model_config(sigil)

        with self._lock:
            response, tokens, elapsed = self._provider.infer(system_prompt, user_prompt, cfg)

        response = self._strip_think(response)
        return (response, tokens, elapsed)

    def chat(self, sigil: str, system_prompt: str, history: list[dict], user_msg: str) -> tuple[str, int, float]:
        """Multi-turn chat. history is list of {"role": ..., "content": ...}.

        Returns (response_text, tokens, elapsed_seconds).
        """
        if not self.load(sigil):
            cfg = self._get_model_config(sigil)
            name = cfg.get("name", sigil) if cfg else sigil
            return (f"[{name} could not be loaded]", 0, 0.0)

        cfg = self._get_model_config(sigil)

        with self._lock:
            response, tokens, elapsed = self._provider.chat(system_prompt, history, user_msg, cfg)

        response = self._strip_think(response)
        return (response, tokens, elapsed)

    def reload(self, config_path: str | None = None) -> None:
        """Unload current model and re-read config from disk."""
        self.unload()
        self._config = _load_config(config_path)

    def status(self) -> dict:
        return {
            "loaded": self._model_sigil,
            "available": list(self._config.get("models", {}).keys()),
        }
