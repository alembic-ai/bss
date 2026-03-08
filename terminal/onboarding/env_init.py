"""Environment Init Screen - Create BSS directories."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Static, Label
from textual.screen import Screen

from src.bss.environment import BSSEnvironment


class EnvInitScreen(Screen):
    """Initialize the BSS environment and directories."""

    CSS = """
    EnvInitScreen {
        align: center middle;
        background: $surface;
    }

    #env-container {
        width: 80;
        height: auto;
        border: solid $accent;
        background: $boost;
        padding: 2 4;
    }

    #content {
        height: auto;
        width: 100%;
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

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, step_num: int = 4, total_steps: int = 9, env_path: Path = None):
        super().__init__()
        self.step_num = step_num
        self.total_steps = total_steps
        self.env_path = env_path or Path.cwd()
        self.env = None
        self.init_success = False

    def compose(self) -> ComposeResult:
        with Container(id="env-container"):
            yield Static(f"[bold]Step {self.step_num}/{self.total_steps}: Environment Setup[/bold]")
            with Vertical(id="content"):
                yield Label("[bold]Setting up BSS directories...[/bold]")
                yield Label("")
                yield Label("[cyan]The following directories will be created:[/cyan]")
                yield Label("")
                yield Label("[dim]/relay/[/dim]     — Handoff queue between models")
                yield Label("[dim]/active/[/dim]    — Current work in progress")
                yield Label("[dim]/profile/[/dim]   — Roster and identity blinks")
                yield Label("[dim]/archive/[/dim]   — Completed work (read-only)")
                yield Label("[dim]/artifacts/[/dim] — Work product outputs")
                yield Label("")
                yield Label("[yellow]Initializing...[/yellow]", id="status-label")

            with Container(id="buttons"):
                yield Button("Create Directories", id="create-btn", variant="primary")
                yield Button("Quit", id="quit-btn", variant="default")

    def action_quit(self) -> None:
        self.dismiss("quit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "create-btn":
            self._create_environment()
        elif event.button.id == "quit-btn":
            self.dismiss("quit")

    def _create_environment(self) -> None:
        """Create the BSS environment."""
        try:
            self.env = BSSEnvironment.init(self.env_path)
            status = self.query_one("#status-label", Static)
            status.update("[green]✓ Directories created successfully![/green]")
            self.dismiss("next")
        except Exception as e:
            status = self.query_one("#status-label", Static)
            status.update(f"[red]Error: {str(e)}[/red]")
