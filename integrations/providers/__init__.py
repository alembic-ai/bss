"""BSS Provider abstraction — pluggable model inference backends.

Each provider implements load/unload/infer/chat for a specific backend.
ModelManager dispatches to the active provider based on config.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Provider(ABC):
    """Base class for model inference backends."""

    @abstractmethod
    def load(self, config: dict) -> bool:
        """Load a model from config. Returns True on success."""
        ...

    @abstractmethod
    def unload(self) -> None:
        """Unload the current model and free resources."""
        ...

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return True if a model is currently loaded."""
        ...

    @abstractmethod
    def infer(self, system_prompt: str, user_prompt: str, config: dict) -> tuple[str, int, float]:
        """Single-turn inference.

        Returns (response_text, token_count, elapsed_seconds).
        """
        ...

    @abstractmethod
    def chat(self, system_prompt: str, history: list[dict], user_msg: str, config: dict) -> tuple[str, int, float]:
        """Multi-turn chat inference.

        history is a list of {"role": ..., "content": ...} dicts.
        Returns (response_text, token_count, elapsed_seconds).
        """
        ...


def get_provider(backend: str) -> Provider:
    """Instantiate a provider by backend name.

    Supported backends:
        - "gguf": Local GGUF files via llama-cpp-python
        - "openai": OpenAI-compatible API (Ollama, LM Studio, vLLM, OpenAI, etc.)
        - "anthropic": Anthropic Claude models
        - "gemini": Google Gemini models
        - "huggingface": Hugging Face Inference API
    """
    if backend == "gguf":
        from integrations.providers.gguf import GGUFProvider
        return GGUFProvider()
    elif backend == "openai":
        from integrations.providers.openai_compat import OpenAIProvider
        return OpenAIProvider()
    elif backend == "anthropic":
        from integrations.providers.anthropic import AnthropicProvider
        return AnthropicProvider()
    elif backend == "gemini":
        from integrations.providers.gemini import GeminiProvider
        return GeminiProvider()
    elif backend == "huggingface":
        from integrations.providers.huggingface import HuggingFaceProvider
        return HuggingFaceProvider()
    else:
        raise ValueError(f"Unknown backend: {backend!r}. Supported: gguf, openai, anthropic, gemini, huggingface")
