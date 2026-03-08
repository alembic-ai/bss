"""BSS Relay — interactive model setup wizard.

Called when no config.yaml exists, or via `bss relay --setup`.
Walks the user through configuring model backends and writes config.yaml.
"""

from __future__ import annotations

import os

import yaml
from rich.console import Console
from rich.panel import Panel

import typer

from integrations.discovery import (
    scan_gguf_files,
    list_ollama_models,
    check_endpoint,
    format_gguf_size,
)


console = Console()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

DEFAULT_COLORS = [
    "#64B5F6",  # blue
    "#FF8F00",  # amber
    "#CE93D8",  # purple
    "#81C784",  # green
    "#FF7043",  # deep orange
    "#4DD0E1",  # cyan
]


# Backward-compatible private aliases — existing tests import these names.
_scan_gguf_files = scan_gguf_files
_list_ollama_models = list_ollama_models
_check_endpoint = check_endpoint
_format_gguf_size = format_gguf_size


def _setup_gguf_model() -> dict:
    """Collect config for a local GGUF model.

    Scans mind/ directories for .gguf files and presents them as choices.
    Falls back to manual path entry if none found.
    """
    found = _scan_gguf_files()

    if found:
        console.print(f"\n  Found {len(found)} model(s) in mind/:\n")
        for i, p in enumerate(found, 1):
            name = os.path.basename(p)
            size = _format_gguf_size(p)
            console.print(f"    {i}. {name}  [dim]({size})[/dim]")
        console.print(f"    {len(found) + 1}. Enter path manually")
        console.print()

        choice = typer.prompt("  Select", default=1, type=int)

        if 1 <= choice <= len(found):
            path = found[choice - 1]
        else:
            path = typer.prompt("  Path to .gguf file")
            path = os.path.expanduser(path)
    else:
        console.print("  [dim]No .gguf files found in mind/ — enter path manually[/dim]")
        path = typer.prompt("  Path to .gguf file")
        path = os.path.expanduser(path)

    if not os.path.exists(path):
        console.print(f"  [yellow]Warning: file not found at {path}[/yellow]")
        if not typer.confirm("  Continue anyway?", default=True):
            return {}

    n_ctx = typer.prompt("  Context window (n_ctx)", default=4096, type=int)
    threads = typer.prompt("  CPU threads", default=4, type=int)

    return {
        "backend": "gguf",
        "path": path,
        "n_ctx": n_ctx,
        "threads": threads,
    }


def _setup_ollama_model() -> dict:
    """Collect config for an Ollama model."""
    base_url = typer.prompt("  Ollama URL", default="http://localhost:11434")

    # Try to list available models
    models = _list_ollama_models(base_url)
    if models:
        console.print(f"\n  Available models on {base_url}:")
        for i, name in enumerate(models[:10], 1):
            console.print(f"    {i}. {name}")
        console.print()
        model = typer.prompt("  Model name", default=models[0] if models else "")
    else:
        console.print(f"  [dim]Could not reach {base_url} — enter model name manually[/dim]")
        model = typer.prompt("  Model name (e.g. qwen3:8b)")

    return {
        "backend": "openai",
        "base_url": f"{base_url.rstrip('/')}/v1",
        "model": model,
    }


def _setup_openai_model() -> dict:
    """Collect config for an OpenAI-compatible API."""
    base_url = typer.prompt("  Base URL (e.g. http://localhost:1234/v1)")
    api_key = typer.prompt("  API key (leave blank if none)", default="")

    if _check_endpoint(base_url, api_key or None):
        console.print(f"  [green]Endpoint reachable.[/green]")
    else:
        console.print(f"  [yellow]Could not reach endpoint — continuing anyway.[/yellow]")

    model = typer.prompt("  Model name (as the API expects it)")

    config = {
        "backend": "openai",
        "base_url": base_url.rstrip("/"),
        "model": model,
    }
    if api_key:
        config["api_key"] = api_key

    return config


def setup_models(config_path: str | None = None) -> str:
    """Run the interactive model setup wizard.

    Returns the path to the written config.yaml.
    """
    out_path = config_path or CONFIG_PATH

    console.print()
    console.print(Panel(
        "[bold]BSS RELAY — Model Setup[/bold]\n[dim]Configure your inference backends[/dim]",
        style="blue",
    ))
    console.print()

    models: dict[str, dict] = {}
    default_sigils = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    model_index = 0

    while True:
        if model_index == 0:
            console.print("  No models configured. Let's add one.\n")
        else:
            console.print()

        console.print("  [bold]Backend?[/bold]")
        console.print("    1. Local GGUF file (llama-cpp-python)")
        console.print("    2. Ollama (localhost)")
        console.print("    3. OpenAI-compatible API (LM Studio, vLLM, OpenAI, etc.)")
        console.print()

        choice = typer.prompt("  Select", default=1, type=int)

        if choice == 1:
            model_config = _setup_gguf_model()
        elif choice == 2:
            model_config = _setup_ollama_model()
        elif choice == 3:
            model_config = _setup_openai_model()
        else:
            console.print("  [red]Invalid choice.[/red]")
            continue

        if not model_config:
            continue

        # Common fields
        console.print()
        default_sigil = default_sigils[model_index] if model_index < 26 else "?"
        sigil = typer.prompt("  Sigil (A-Z)", default=default_sigil).upper()

        # Derive a display name: from API model name, or from GGUF filename
        default_name = model_config.get("model", f"Model-{sigil}")
        if model_config.get("backend") == "gguf" and "path" in model_config:
            # "Qwen3-4B-Q4_K_M.gguf" -> "Qwen3-4B"
            stem = os.path.basename(model_config["path"]).replace(".gguf", "")
            # Strip quantization suffix (everything after last hyphen with Q/q)
            parts = stem.rsplit("-", 1)
            if len(parts) == 2 and parts[1][:1].upper() == "Q":
                default_name = parts[0]
            else:
                default_name = stem

        name = typer.prompt("  Display name", default=default_name)

        model_config["name"] = name
        model_config["max_tokens"] = typer.prompt("  Max tokens", default=1024, type=int)
        model_config["temperature"] = typer.prompt("  Temperature", default=0.7, type=float)

        color = typer.prompt("  Color (hex)", default=DEFAULT_COLORS[model_index % len(DEFAULT_COLORS)])
        model_config["color"] = color

        models[sigil] = model_config
        model_index += 1

        console.print(f"\n  [green]Added {sigil} ({name})[/green]")

        if not typer.confirm("\n  Add another model?", default=False):
            break

    # Write config
    config = {"models": models}

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("# WARNING: This file may contain API keys. Keep it private.\n")
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # Restrict config file permissions (owner read/write only)
    import sys
    if sys.platform != "win32":
        os.chmod(out_path, 0o600)

    console.print(f"\n  [green]Config written to {out_path}[/green]")
    console.print(f"  {len(models)} model(s) configured.\n")

    return out_path


def has_config(config_path: str | None = None) -> bool:
    """Check if a valid config.yaml exists with at least one model."""
    path = config_path or CONFIG_PATH
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        return bool(config and config.get("models"))
    except Exception as exc:
        import logging
        logging.getLogger("bss.setup").warning(
            "has_config: malformed config at %s: %s", path, exc,
        )
        return False
