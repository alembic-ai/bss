"""BSS Setup Screen — integrated Textual wizard for model configuration.

Multi-step onboarding flow that replaces the pre-TUI typer.prompt wizard.
Launched on first run (no config) or via /setup command mid-session.
"""

from __future__ import annotations

import os
import re

import yaml

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Input, Button
from textual.containers import Vertical, Horizontal, Center
from textual.worker import Worker
from rich.text import Text


from integrations.discovery import (
    discover_all,
    DiscoveryReport,
    DiscoveryResult,
)

# ── Constants ───────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "integrations", "config.yaml")

STEPS = ["DISCOVERY", "BACKEND_SELECT", "BACKEND_CONFIG", "COMMON_CONFIG", "REVIEW", "SUMMARY"]

BACKENDS = [
    ("gguf", "Local GGUF file (llama-cpp-python)"),
    ("openai", "Ollama / OpenAI-compatible API"),
    ("anthropic", "Anthropic (Claude)"),
    ("gemini", "Google Gemini"),
    ("huggingface", "Hugging Face Inference API"),
]

DEFAULT_COLORS = [
    "#64B5F6",  # blue
    "#FF8F00",  # amber
    "#CE93D8",  # purple
    "#81C784",  # green
    "#FF7043",  # deep orange
    "#4DD0E1",  # cyan
]

DEFAULT_SIGILS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

CSS = """
SetupScreen { background: #0A0A0A; }
#setup-container { width: 80; height: auto; margin: 2 0; padding: 1 2; background: #111111; border: heavy #3A3A3A; }
#setup-title { text-align: center; color: #64B5F6; text-style: bold; padding: 1 0; }
#setup-subtitle { text-align: center; color: #6B6B6B; padding: 0 0 1 0; }
#step-content { height: auto; padding: 1 2; }
#nav-bar { height: 3; padding: 0 2; layout: horizontal; align: center middle; }
#nav-bar Button { margin: 0 1; min-width: 12; }
.step-label { color: #9E9E9E; padding: 0 0 1 0; }
.result-line { padding: 0 0; }
.available { color: #81C784; }
.unavailable { color: #6B6B6B; }
.backend-btn { width: 100%; margin: 0 0 1 0; min-height: 3; }
.backend-btn.-selected { border: heavy #64B5F6; }
.field-label { color: #9E9E9E; margin: 1 0 0 0; }
.field-input { margin: 0 0 0 0; }
.review-line { color: #F5F5F5; padding: 0 0; }
.model-card { border: heavy #3A3A3A; padding: 1 2; margin: 0 0 1 0; background: #0A0A0A; }
.error-text { color: #B71C1C; }
"""


# ── SetupScreen ─────────────────────────────────────────────


class SetupScreen(Screen):
    """Multi-step wizard for configuring BSS model backends."""

    DEFAULT_CSS = CSS
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        config_path: str | None = None,
        existing_config: dict | None = None,
        name: str | None = None,
        id: str | None = None,
    ):
        super().__init__(name=name, id=id)
        self._config_path = config_path or CONFIG_PATH
        self._existing_config = existing_config or {}
        self._models: dict[str, dict] = dict(self._existing_config.get("models", {}))
        self._step = 0  # index into STEPS
        self._report: DiscoveryReport | None = None
        self._selected_backend: str | None = None
        self._current_model_config: dict = {}
        self._model_index = len(self._models)

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="setup-container"):
                yield Static("BSS RELAY — Model Setup", id="setup-title")
                yield Static("Configure your inference backends", id="setup-subtitle")
                yield Vertical(id="step-content")
                with Horizontal(id="nav-bar"):
                    yield Button("Back", id="btn-back", variant="default")
                    yield Button("Next", id="btn-next", variant="primary")
                    yield Button("Cancel", id="btn-cancel", variant="error")

    def on_mount(self) -> None:
        self._render_step()

    # ── Step rendering ──────────────────────────────────────

    def _render_step(self) -> None:
        step_name = STEPS[self._step]
        content = self.query_one("#step-content", Vertical)
        content.remove_children()

        btn_back = self.query_one("#btn-back", Button)
        btn_next = self.query_one("#btn-next", Button)

        btn_back.disabled = self._step == 0

        if step_name == "DISCOVERY":
            self._render_discovery(content)
            btn_next.label = "Next"
        elif step_name == "BACKEND_SELECT":
            self._render_backend_select(content)
            btn_next.label = "Next"
        elif step_name == "BACKEND_CONFIG":
            self._render_backend_config(content)
            btn_next.label = "Next"
        elif step_name == "COMMON_CONFIG":
            self._render_common_config(content)
            btn_next.label = "Review"
        elif step_name == "REVIEW":
            self._render_review(content)
            btn_next.label = "Confirm"
        elif step_name == "SUMMARY":
            self._render_summary(content)
            btn_next.label = "Save & Launch"

    def _render_discovery(self, container: Vertical) -> None:
        container.mount(Static("Scanning for available backends...", classes="step-label"))
        container.mount(Static("", id="discovery-results"))
        self._run_discovery()

    def _run_discovery(self) -> None:
        self.run_worker(self._discover_worker, thread=True)

    def _discover_worker(self) -> DiscoveryReport:
        return discover_all()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name == "_discover_worker" and event.worker.is_finished:
            if event.worker.result is not None:
                self._report = event.worker.result
                self._show_discovery_results()

    def _show_discovery_results(self) -> None:
        try:
            results_widget = self.query_one("#discovery-results", Static)
        except Exception:
            return

        t = Text()
        if not self._report or not self._report.results:
            t.append("\n  No backends auto-detected.\n", style="#6B6B6B")
            t.append("  You can still configure backends manually.\n\n", style="#6B6B6B")
        else:
            t.append(f"\n  Found {len(self._report.results)} backend(s) ", style="#9E9E9E")
            t.append(f"({self._report.elapsed}s)\n\n", style="#6B6B6B")
            for r in self._report.results:
                marker = "[green]✓[/green]" if r.available else "[red]✗[/red]"
                t.append(f"  {marker}  ", style="bold")
                t.append(f"{r.label}\n", style="#81C784" if r.available else "#6B6B6B")
            t.append("\n")

        results_widget.update(t)

    def _render_backend_select(self, container: Vertical) -> None:
        container.mount(Static("Select a backend:", classes="step-label"))

        for backend_id, label in BACKENDS:
            # Check if this backend was discovered
            available = False
            if self._report:
                available = any(r.backend == backend_id and r.available for r in self._report.results)

            indicator = " [green]● detected[/green]" if available else ""
            btn = Button(f"{label}{indicator}", id=f"backend-{backend_id}", classes="backend-btn")
            container.mount(btn)

    def _render_backend_config(self, container: Vertical) -> None:
        backend = self._selected_backend
        container.mount(Static(f"Configure {backend} backend:", classes="step-label"))

        # Pre-populate from discovery results
        discovery_details = {}
        if self._report:
            for r in self._report.results:
                if r.backend == backend and r.available:
                    discovery_details = r.details
                    break

        if backend == "gguf":
            container.mount(Static("Path to .gguf file:", classes="field-label"))
            container.mount(Input(
                value=discovery_details.get("path", ""),
                placeholder="~/mind/model.gguf",
                id="field-path",
                classes="field-input",
            ))
            container.mount(Static("Context window (n_ctx):", classes="field-label"))
            container.mount(Input(value="4096", id="field-n_ctx", classes="field-input"))
            container.mount(Static("CPU threads:", classes="field-label"))
            container.mount(Input(value="4", id="field-threads", classes="field-input"))

        elif backend == "openai":
            container.mount(Static("Base URL:", classes="field-label"))
            container.mount(Input(
                value=discovery_details.get("base_url", "http://localhost:11434/v1"),
                placeholder="http://localhost:11434/v1",
                id="field-base_url",
                classes="field-input",
            ))
            container.mount(Static("Model name:", classes="field-label"))
            container.mount(Input(
                value=discovery_details.get("model", ""),
                placeholder="qwen3:8b",
                id="field-model",
                classes="field-input",
            ))
            container.mount(Static("API key (optional):", classes="field-label"))
            container.mount(Input(
                value="",
                placeholder="Leave blank if not required",
                id="field-api_key",
                password=True,
                classes="field-input",
            ))

        elif backend == "anthropic":
            container.mount(Static("API key:", classes="field-label"))
            container.mount(Input(
                value="",
                placeholder="sk-ant-... (or set ANTHROPIC_API_KEY env var)",
                id="field-api_key",
                password=True,
                classes="field-input",
            ))
            container.mount(Static("Model:", classes="field-label"))
            container.mount(Input(
                value=discovery_details.get("model", "claude-sonnet-4-20250514"),
                id="field-model",
                classes="field-input",
            ))

        elif backend == "gemini":
            container.mount(Static("API key:", classes="field-label"))
            container.mount(Input(
                value="",
                placeholder="AIza... (or set GOOGLE_API_KEY env var)",
                id="field-api_key",
                password=True,
                classes="field-input",
            ))
            container.mount(Static("Model:", classes="field-label"))
            container.mount(Input(
                value=discovery_details.get("model", "gemini-2.0-flash"),
                id="field-model",
                classes="field-input",
            ))

        elif backend == "huggingface":
            container.mount(Static("API token:", classes="field-label"))
            container.mount(Input(
                value="",
                placeholder="hf_... (or set HF_TOKEN env var)",
                id="field-api_key",
                password=True,
                classes="field-input",
            ))
            container.mount(Static("Model:", classes="field-label"))
            container.mount(Input(
                value=discovery_details.get("model", "mistralai/Mistral-7B-Instruct-v0.3"),
                id="field-model",
                classes="field-input",
            ))

    def _render_common_config(self, container: Vertical) -> None:
        container.mount(Static("Common settings:", classes="step-label"))

        default_sigil = DEFAULT_SIGILS[self._model_index] if self._model_index < 26 else "?"
        default_color = DEFAULT_COLORS[self._model_index % len(DEFAULT_COLORS)]

        # Derive a display name
        default_name = self._current_model_config.get("model", f"Model-{default_sigil}")
        if self._selected_backend == "gguf" and "path" in self._current_model_config:
            stem = os.path.basename(self._current_model_config["path"]).replace(".gguf", "")
            parts = stem.rsplit("-", 1)
            if len(parts) == 2 and parts[1][:1].upper() == "Q":
                default_name = parts[0]
            else:
                default_name = stem

        container.mount(Static("Sigil (A-Z):", classes="field-label"))
        container.mount(Input(value=default_sigil, id="field-sigil", classes="field-input"))
        container.mount(Static("Display name:", classes="field-label"))
        container.mount(Input(value=default_name, id="field-name", classes="field-input"))
        container.mount(Static("Max tokens:", classes="field-label"))
        container.mount(Input(value="1024", id="field-max_tokens", classes="field-input"))
        container.mount(Static("Temperature:", classes="field-label"))
        container.mount(Input(value="0.7", id="field-temperature", classes="field-input"))
        container.mount(Static("Color (hex):", classes="field-label"))
        container.mount(Input(value=default_color, id="field-color", classes="field-input"))

    def _render_review(self, container: Vertical) -> None:
        container.mount(Static("Review model configuration:", classes="step-label"))

        t = Text()
        cfg = self._current_model_config
        sigil = cfg.get("_sigil", "?")
        color = cfg.get("color", "#F5F5F5")

        t.append(f"\n  {sigil}  ", style=f"bold {color}")
        t.append(f"{cfg.get('name', 'Model')}\n", style=f"bold {color}")
        t.append("  " + "─" * 40 + "\n", style="#3A3A3A")
        t.append(f"  Backend:      {cfg.get('backend', '?')}\n", style="#F5F5F5")

        if cfg.get("backend") == "gguf":
            t.append(f"  Path:         {cfg.get('path', '?')}\n", style="#F5F5F5")
            t.append(f"  Context:      {cfg.get('n_ctx', '?')}\n", style="#F5F5F5")
            t.append(f"  Threads:      {cfg.get('threads', '?')}\n", style="#F5F5F5")
        elif cfg.get("backend") == "openai":
            t.append(f"  Base URL:     {cfg.get('base_url', '?')}\n", style="#F5F5F5")
            t.append(f"  Model:        {cfg.get('model', '?')}\n", style="#F5F5F5")
            if cfg.get("api_key"):
                t.append(f"  API key:      ***\n", style="#F5F5F5")
        else:
            t.append(f"  Model:        {cfg.get('model', '?')}\n", style="#F5F5F5")
            if cfg.get("api_key"):
                t.append(f"  API key:      ***\n", style="#F5F5F5")

        t.append(f"  Max tokens:   {cfg.get('max_tokens', '?')}\n", style="#F5F5F5")
        t.append(f"  Temperature:  {cfg.get('temperature', '?')}\n", style="#F5F5F5")
        t.append(f"  Color:        {cfg.get('color', '?')}\n", style="#F5F5F5")
        t.append("\n")

        container.mount(Static(t, id="review-card"))

    def _render_summary(self, container: Vertical) -> None:
        container.mount(Static(
            f"Configured {len(self._models)} model(s):", classes="step-label"
        ))

        t = Text()
        for sigil, cfg in self._models.items():
            color = cfg.get("color", "#F5F5F5")
            name = cfg.get("name", sigil)
            backend = cfg.get("backend", "gguf")
            t.append(f"\n  {sigil}  ", style=f"bold {color}")
            t.append(f"{name}", style=f"bold {color}")
            t.append(f"  [{backend}]\n", style="#6B6B6B")

        t.append("\n")
        container.mount(Static(t, id="summary-models"))

        btn_row = Horizontal(id="summary-actions")
        btn_row.styles.height = 3
        btn_row.styles.align = ("center", "middle")
        container.mount(btn_row)
        btn_row.mount(Button("Add Another", id="btn-add-another", variant="default"))

    # ── Validation ──────────────────────────────────────────

    def _validate_backend_config(self) -> str | None:
        """Validate backend-specific fields. Returns error message or None."""
        backend = self._selected_backend

        if backend == "gguf":
            path = self._get_field("field-path")
            if not path:
                return "Path is required"

        elif backend == "openai":
            base_url = self._get_field("field-base_url")
            model = self._get_field("field-model")
            if not base_url:
                return "Base URL is required"
            if not model:
                return "Model name is required"

        elif backend in ("anthropic", "gemini"):
            api_key = self._get_field("field-api_key")
            model = self._get_field("field-model")
            if not api_key:
                # Check env vars
                if backend == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
                    return "API key is required (or set ANTHROPIC_API_KEY env var)"
                if backend == "gemini" and not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
                    return "API key is required (or set GOOGLE_API_KEY env var)"
            if not model:
                return "Model name is required"

        elif backend == "huggingface":
            model = self._get_field("field-model")
            if not model:
                return "Model name is required"

        return None

    def _validate_common_config(self) -> str | None:
        """Validate common fields. Returns error message or None."""
        sigil = self._get_field("field-sigil")
        name = self._get_field("field-name")
        max_tokens = self._get_field("field-max_tokens")
        temperature = self._get_field("field-temperature")
        color = self._get_field("field-color")

        if not sigil or not sigil.strip().isalpha() or len(sigil.strip()) != 1:
            return "Sigil must be a single letter A-Z"
        if not name or not name.strip():
            return "Display name is required"
        try:
            int(max_tokens)
        except (ValueError, TypeError):
            return "Max tokens must be a number"
        try:
            float(temperature)
        except (ValueError, TypeError):
            return "Temperature must be a number"
        if not re.match(r"^#[0-9A-Fa-f]{6}$", color.strip()):
            return "Color must be hex format (#RRGGBB)"

        return None

    # ── Field helpers ───────────────────────────────────────

    def _get_field(self, field_id: str) -> str:
        try:
            return self.query_one(f"#{field_id}", Input).value
        except Exception:
            return ""

    def _collect_backend_config(self) -> dict:
        """Collect backend-specific config from form fields."""
        cfg = {"backend": self._selected_backend}

        if self._selected_backend == "gguf":
            cfg["path"] = self._get_field("field-path")
            cfg["n_ctx"] = int(self._get_field("field-n_ctx") or "4096")
            cfg["threads"] = int(self._get_field("field-threads") or "4")

        elif self._selected_backend == "openai":
            cfg["base_url"] = self._get_field("field-base_url").rstrip("/")
            cfg["model"] = self._get_field("field-model")
            api_key = self._get_field("field-api_key")
            if api_key:
                cfg["api_key"] = api_key

        elif self._selected_backend in ("anthropic", "gemini", "huggingface"):
            cfg["model"] = self._get_field("field-model")
            api_key = self._get_field("field-api_key")
            if api_key:
                cfg["api_key"] = api_key

        return cfg

    def _collect_common_config(self) -> dict:
        """Collect common config from form fields."""
        return {
            "_sigil": self._get_field("field-sigil").strip().upper(),
            "name": self._get_field("field-name").strip(),
            "max_tokens": int(self._get_field("field-max_tokens") or "1024"),
            "temperature": float(self._get_field("field-temperature") or "0.7"),
            "color": self._get_field("field-color").strip(),
        }

    # ── Navigation ──────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        step_name = STEPS[self._step]

        if btn_id == "btn-cancel":
            self.dismiss(None)
            return

        if btn_id and btn_id.startswith("backend-"):
            self._selected_backend = btn_id.replace("backend-", "")
            # Auto-advance after selection
            self._step = STEPS.index("BACKEND_CONFIG")
            self._render_step()
            return

        if btn_id == "btn-add-another":
            self._step = STEPS.index("BACKEND_SELECT")
            self._selected_backend = None
            self._current_model_config = {}
            self._render_step()
            return

        if btn_id == "btn-back":
            if self._step > 0:
                self._step -= 1
                self._render_step()
            return

        if btn_id == "btn-next":
            self._handle_next(step_name)
            return

    def _handle_next(self, step_name: str) -> None:
        if step_name == "DISCOVERY":
            self._step = STEPS.index("BACKEND_SELECT")
            self._render_step()

        elif step_name == "BACKEND_SELECT":
            if not self._selected_backend:
                self._show_error("Please select a backend")
                return
            self._step = STEPS.index("BACKEND_CONFIG")
            self._render_step()

        elif step_name == "BACKEND_CONFIG":
            error = self._validate_backend_config()
            if error:
                self._show_error(error)
                return
            self._current_model_config = self._collect_backend_config()
            self._step = STEPS.index("COMMON_CONFIG")
            self._render_step()

        elif step_name == "COMMON_CONFIG":
            error = self._validate_common_config()
            if error:
                self._show_error(error)
                return
            common = self._collect_common_config()
            self._current_model_config.update(common)
            self._step = STEPS.index("REVIEW")
            self._render_step()

        elif step_name == "REVIEW":
            # Commit this model
            sigil = self._current_model_config.pop("_sigil", "?")
            cfg = dict(self._current_model_config)
            self._models[sigil] = cfg
            self._model_index = len(self._models)
            self._current_model_config = {}
            self._selected_backend = None
            self._step = STEPS.index("SUMMARY")
            self._render_step()

        elif step_name == "SUMMARY":
            self._save_and_dismiss()

    def _show_error(self, message: str) -> None:
        content = self.query_one("#step-content", Vertical)
        # Remove existing error if any
        for widget in content.query(".error-text"):
            widget.remove()
        content.mount(Static(f"[red]{message}[/red]", classes="error-text"))

    def _save_and_dismiss(self) -> None:
        """Write config.yaml and dismiss screen."""
        config = {"models": self._models}

        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        with open(self._config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        self.dismiss(self._config_path)

    def action_cancel(self) -> None:
        self.dismiss(None)
