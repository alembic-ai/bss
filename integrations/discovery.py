"""BSS auto-discovery — detect available model backends and endpoints.

Scans for local GGUF files, probes network endpoints (Ollama, LM Studio,
vLLM, TGI), and checks environment variables for API keys.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field


@dataclass
class DiscoveryResult:
    """A single discovered backend or endpoint."""
    backend: str       # "gguf" | "openai" | "anthropic" | "gemini" | "huggingface"
    source: str        # "scan" | "env_var" | "endpoint"
    label: str         # e.g. "Ollama (localhost:11434)"
    available: bool
    details: dict = field(default_factory=dict)


def _mask_key(key: str) -> str:
    """Mask an API key for display, showing only last 4 chars."""
    if len(key) > 4:
        return "****" + key[-4:]
    return "****"


@dataclass
class DiscoveryReport:
    """Aggregated discovery results."""
    results: list[DiscoveryResult] = field(default_factory=list)
    elapsed: float = 0.0


# ── Scanning functions (moved from setup.py) ────────────────


def scan_gguf_files(search_dirs: list[str] | None = None) -> list[str]:
    """Scan directories for .gguf files. Returns sorted list of absolute paths.

    Default search locations:
        - ./mind/  (BSS convention: models live next to the environment)
        - ~/mind/
    """
    if search_dirs is None:
        search_dirs = [
            os.path.join(os.getcwd(), "mind"),
            os.path.expanduser("~/mind"),
        ]

    found: list[str] = []
    seen: set[str] = set()

    for d in search_dirs:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            continue
        for path in sorted(glob.glob(os.path.join(d, "**", "*.gguf"), recursive=True)):
            real = os.path.realpath(path)
            if real not in seen:
                seen.add(real)
                found.append(path)

    return found


def list_ollama_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Query Ollama for available models. Returns list of model names."""
    try:
        req = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception as exc:
        logging.getLogger("bss.discovery").warning(
            "list_ollama_models failed for %s: %s", base_url, exc,
        )
        return []


def check_endpoint(base_url: str, api_key: str | None = None) -> bool:
    """Check if an OpenAI-compatible endpoint is reachable."""
    try:
        req = urllib.request.Request(f"{base_url.rstrip('/')}/models")
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req, timeout=5):
            pass
        return True
    except Exception as exc:
        logging.getLogger("bss.discovery").debug(
            "check_endpoint unreachable %s: %s", base_url, exc,
        )
        return False


def format_gguf_size(path: str) -> str:
    """Human-readable file size."""
    size = os.path.getsize(path)
    if size >= 1_073_741_824:
        return f"{size / 1_073_741_824:.1f} GB"
    elif size >= 1_048_576:
        return f"{size / 1_048_576:.0f} MB"
    else:
        return f"{size / 1024:.0f} KB"


# ── Per-backend discovery ────────────────────────────────────


def discover_gguf(search_dirs: list[str] | None = None) -> list[DiscoveryResult]:
    """Scan for local GGUF model files."""
    found = scan_gguf_files(search_dirs)
    results = []
    for path in found:
        name = os.path.basename(path)
        try:
            size = format_gguf_size(path)
        except OSError:
            size = "?"
        results.append(DiscoveryResult(
            backend="gguf",
            source="scan",
            label=f"{name} ({size})",
            available=True,
            details={"path": path, "name": name, "size": size},
        ))
    return results


def discover_ollama(base_url: str = "http://localhost:11434") -> list[DiscoveryResult]:
    """Probe Ollama for available models."""
    models = list_ollama_models(base_url)
    if not models:
        return []

    results = []
    for model_name in models:
        results.append(DiscoveryResult(
            backend="openai",
            source="endpoint",
            label=f"Ollama: {model_name} ({base_url})",
            available=True,
            details={
                "base_url": f"{base_url.rstrip('/')}/v1",
                "model": model_name,
                "server": "ollama",
            },
        ))
    return results


def discover_openai_endpoints() -> list[DiscoveryResult]:
    """Probe common OpenAI-compatible endpoints (LM Studio, vLLM, TGI)."""
    endpoints = [
        ("http://localhost:1234/v1", "LM Studio"),
        ("http://localhost:8000/v1", "vLLM"),
        ("http://localhost:8080/v1", "TGI"),
    ]

    results = []
    for base_url, server_name in endpoints:
        if check_endpoint(base_url):
            results.append(DiscoveryResult(
                backend="openai",
                source="endpoint",
                label=f"{server_name} ({base_url})",
                available=True,
                details={"base_url": base_url, "server": server_name.lower().replace(" ", "_")},
            ))
    return results


def discover_anthropic() -> list[DiscoveryResult]:
    """Check for Anthropic API key in environment."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        masked = _mask_key(key)
        return [DiscoveryResult(
            backend="anthropic",
            source="env_var",
            label=f"Anthropic API ({masked})",
            available=True,
            details={"env_var": "ANTHROPIC_API_KEY", "model": "claude-opus-4-6"},
        )]
    return []


def discover_gemini() -> list[DiscoveryResult]:
    """Check for Google/Gemini API key in environment."""
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    env_var = "GOOGLE_API_KEY" if os.environ.get("GOOGLE_API_KEY") else "GEMINI_API_KEY"
    if key:
        masked = _mask_key(key)
        return [DiscoveryResult(
            backend="gemini",
            source="env_var",
            label=f"Gemini API ({masked})",
            available=True,
            details={"env_var": env_var, "model": "gemini-2.5-flash"},
        )]
    return []


def discover_huggingface() -> list[DiscoveryResult]:
    """Check for Hugging Face token in environment."""
    key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    env_var = "HF_TOKEN" if os.environ.get("HF_TOKEN") else "HUGGING_FACE_HUB_TOKEN"
    if key:
        masked = _mask_key(key)
        return [DiscoveryResult(
            backend="huggingface",
            source="env_var",
            label=f"Hugging Face ({masked})",
            available=True,
            details={"env_var": env_var, "model": "mistralai/Mistral-7B-Instruct-v0.3"},
        )]
    return []


# ── Aggregate discovery ──────────────────────────────────────


def discover_all(gguf_dirs: list[str] | None = None, ollama_url: str = "http://localhost:11434") -> DiscoveryReport:
    """Run all discovery checks and return aggregated report."""
    start = time.time()

    results: list[DiscoveryResult] = []
    results.extend(discover_gguf(gguf_dirs))
    results.extend(discover_ollama(ollama_url))
    results.extend(discover_openai_endpoints())
    results.extend(discover_anthropic())
    results.extend(discover_gemini())
    results.extend(discover_huggingface())

    elapsed = round(time.time() - start, 2)
    return DiscoveryReport(results=results, elapsed=elapsed)
