"""Backend Config Screen - Configure model backends."""

from __future__ import annotations

import os
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Static, Label
from textual.screen import Screen

from terminal.setup_screen import SetupScreen as TUISetupScreen, CONFIG_PATH


class BackendConfigScreen(Screen):
    """Configure model backends (wraps the existing SetupScreen)."""

    CSS = """
    BackendConfigScreen {
        align: center middle;
        background: $surface;
    }

    #backend-container {
        width: 80;
        height: auto;
        border: solid $accent;
        background: $boost;
        padding: 2 4;
    }

    #buttons {
        dock: bottom;
        width: 100%;
        height: auto;
        layout: horizontal;
    }

    Button {
        margin: 1 2;
    }
    """

    def __init__(self, step_num: int = 6, total_steps: int = 9, env_path: Path = None):
        super().__init__()
        self.step_num = step_num
        self.total_steps = total_steps
        self.env_path = env_path or Path.cwd()

    def compose(self) -> ComposeResult:
        with Container(id="backend-container"):
            yield Static(f"[bold]Step {self.step_num}/{self.total_steps}: Model Backend Configuration[/bold]")
            with Vertical():
                yield Label("")
                yield Label("[cyan]Configure which AI model backends to use.[/cyan]")
                yield Label("")
                yield Label("[dim]This will open the backend setup wizard where you can:[/dim]")
                yield Label("[dim]  - Auto-detect available backends (Ollama, GGUF, APIs)[/dim]")
                yield Label("[dim]  - Configure API keys and endpoints[/dim]")
                yield Label("[dim]  - Set model parameters (temperature, max tokens)[/dim]")
                yield Label("")
            with Container(id="buttons"):
                yield Button("Open Backend Setup", id="setup-btn", variant="primary")
                yield Button("Skip", id="skip-btn", variant="default")
                yield Button("Quit", id="quit-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "setup-btn":
            self._open_setup()
        elif event.button.id == "skip-btn":
            self.dismiss("next")
        elif event.button.id == "quit-btn":
            self.dismiss("quit")

    def _open_setup(self) -> None:
        """Open the TUI setup screen and handle its result."""
        # Load existing config if present
        existing_config = {}
        if os.path.exists(CONFIG_PATH):
            import yaml
            with open(CONFIG_PATH) as f:
                existing_config = yaml.safe_load(f) or {}

        setup = TUISetupScreen(
            config_path=CONFIG_PATH,
            existing_config=existing_config,
        )
        self.app.push_screen(setup, callback=self._on_setup_dismissed)

    def _on_setup_dismissed(self, result: str | None) -> None:
        """Called when the setup screen is dismissed."""
        if result:
            # Config was saved successfully — dismiss this screen too
            self.dismiss("next")
        # If result is None (cancelled), stay on this screen
