"""OpenAI-compatible API provider — works with Ollama, LM Studio, vLLM, OpenAI, etc.

Uses only stdlib (urllib.request + json) — no new dependencies.
Any endpoint that serves /v1/chat/completions works.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

from integrations.providers import Provider

logger = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    """Hit any OpenAI-compatible chat/completions endpoint."""

    def __init__(self):
        self._base_url: str | None = None
        self._api_key: str | None = None
        self._model: str | None = None
        self._probe_timeout: int = 5
        self._inference_timeout: int = 120

    def load(self, config: dict) -> bool:
        self._base_url = config.get("base_url", "").rstrip("/")
        self._api_key = config.get("api_key")
        self._model = config.get("model")
        self._probe_timeout = int(config.get("probe_timeout", 5))
        self._inference_timeout = int(config.get("inference_timeout", 120))

        if not self._base_url or not self._model:
            return False

        if self._api_key and self._base_url.startswith("http://"):
            hostname = urlparse(self._base_url).hostname or ""
            if hostname not in ("localhost", "127.0.0.1", "::1"):
                raise ValueError(
                    f"Refusing to send API key over unencrypted HTTP to "
                    f"remote host '{hostname}'. Use HTTPS or remove the API key."
                )

        # Verify the endpoint is reachable with a lightweight models list
        try:
            req = urllib.request.Request(f"{self._base_url}/models")
            if self._api_key:
                req.add_header("Authorization", f"Bearer {self._api_key}")
            with urllib.request.urlopen(req, timeout=self._probe_timeout):
                pass
            return True
        except Exception as exc:
            # Endpoint might not support /models but still work for chat.
            # Accept the config optimistically.
            logger.debug("OpenAI /models probe failed (proceeding optimistically): %s", exc)
            return True

    def unload(self) -> None:
        self._base_url = None
        self._api_key = None
        self._model = None

    def is_loaded(self) -> bool:
        return self._base_url is not None and self._model is not None

    def _request(self, messages: list[dict], config: dict) -> tuple[str, int, float]:
        """Send a chat completion request and parse the response."""
        url = f"{self._base_url}/chat/completions"

        body = {
            "model": self._model,
            "messages": messages,
            "max_tokens": config.get("max_tokens", 1024),
            "temperature": config.get("temperature", 0.7),
            "stream": False,
        }

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if self._api_key:
            req.add_header("Authorization", f"Bearer {self._api_key}")

        start = time.time()

        try:
            with urllib.request.urlopen(req, timeout=config.get("inference_timeout", self._inference_timeout)) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            elapsed = round(time.time() - start, 2)
            response = result["choices"][0]["message"]["content"].strip()
            tokens = result.get("usage", {}).get("completion_tokens", 0)
            return (response, tokens, elapsed)

        except urllib.error.HTTPError as e:
            elapsed = round(time.time() - start, 2)
            try:
                detail = e.read().decode("utf-8", errors="replace")[:200]
            except Exception:
                detail = str(e)
            return (f"[API error {e.code}: {detail}]", 0, elapsed)

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            return (f"[request error: {e}]", 0, elapsed)

    def infer(self, system_prompt: str, user_prompt: str, config: dict) -> tuple[str, int, float]:
        messages = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ]
        return self._request(messages, config)

    def chat(self, system_prompt: str, history: list[dict], user_msg: str, config: dict) -> tuple[str, int, float]:
        messages = [
            {"role": "system", "content": system_prompt.strip()},
        ]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_msg.strip()})
        return self._request(messages, config)
