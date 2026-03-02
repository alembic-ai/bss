"""GGUF provider — local model inference via llama-cpp-python.

Extracted from the original ModelManager implementation.
llama-cpp-python is only imported when this provider is used.
"""

from __future__ import annotations

import time

from integrations.providers import Provider


class GGUFProvider(Provider):
    """Run inference on local GGUF files using llama-cpp-python."""

    def __init__(self):
        self._model = None

    def load(self, config: dict) -> bool:
        import os

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python is required for the gguf backend. "
                "Install it with: pip install llama-cpp-python"
            )

        model_path = os.path.expanduser(config["path"])
        if not os.path.exists(model_path):
            return False

        try:
            self._model = Llama(
                model_path=model_path,
                n_ctx=config.get("n_ctx", 4096),
                n_threads=config.get("threads", 4),
                verbose=False,
            )
            return True
        except Exception:
            self._model = None
            return False

    def unload(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None

    def is_loaded(self) -> bool:
        return self._model is not None

    def infer(self, system_prompt: str, user_prompt: str, config: dict) -> tuple[str, int, float]:
        suffix = config.get("system_suffix", "")
        messages = [
            {"role": "system", "content": system_prompt.strip() + suffix},
            {"role": "user", "content": user_prompt.strip()},
        ]

        start = time.time()

        try:
            output = self._model.create_chat_completion(
                messages=messages,
                max_tokens=config.get("max_tokens", 1024),
                temperature=config.get("temperature", 0.7),
            )

            elapsed = round(time.time() - start, 2)
            response = output["choices"][0]["message"]["content"].strip()
            tokens = output.get("usage", {}).get("completion_tokens", 0)
            return (response, tokens, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[inference error: {e}]", 0, elapsed)

    def chat(self, system_prompt: str, history: list[dict], user_msg: str, config: dict) -> tuple[str, int, float]:
        suffix = config.get("system_suffix", "")
        messages = [
            {"role": "system", "content": system_prompt.strip() + suffix},
        ]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_msg.strip()})

        start = time.time()

        try:
            output = self._model.create_chat_completion(
                messages=messages,
                max_tokens=config.get("max_tokens", 1024),
                temperature=config.get("temperature", 0.7),
            )

            elapsed = round(time.time() - start, 2)
            response = output["choices"][0]["message"]["content"].strip()
            tokens = output.get("usage", {}).get("completion_tokens", 0)
            return (response, tokens, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[chat error: {e}]", 0, elapsed)
