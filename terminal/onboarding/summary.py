"""Summary Screen - Final onboarding summary."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Static, Label
from textual.screen import Screen

from bss.environment import BSSEnvironment
from bss.roster import read_roster


class SummaryScreen(Screen):
    """Setup complete summary and quick-reference card."""

    CSS = """
    SummaryScreen {
        align: center middle;
        background: $surface;
    }

    #summary-container {
        width: 90;
        height: auto;
        border: solid $accent;
        background: $boost;
        padding: 2 4;
    }

    #content {
        height: auto;
        width: 100%;
        overflow: auto;
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

    def __init__(self, step_num: int = 9, total_steps: int = 9, env_path: Path = None):
        super().__init__()
        self.step_num = step_num
        self.total_steps = total_steps
        self.env_path = env_path or Path.cwd()
        self.env = BSSEnvironment(self.env_path)

    def compose(self) -> ComposeResult:
        with Container(id="summary-container"):
            yield Static(f"[bold]Step {self.step_num}/{self.total_steps}: Setup Complete! 🎉[/bold]")
            with Vertical(id="content"):
                yield Label("[green]✓ All setup steps completed successfully![/green]")
                yield Label("")
                yield Label("[bold cyan]What was created:[/bold cyan]")
                yield Label("  [dim]✓ /relay/ — Handoff queue[/dim]")
                yield Label("  [dim]✓ /active/ — Working threads[/dim]")
                yield Label("  [dim]✓ /profile/ — Roster and identity[/dim]")
                yield Label("  [dim]✓ /archive/ — Completed work[/dim]")
                yield Label("  [dim]✓ /artifacts/ — Work products[/dim]")

                roster = read_roster(self.env)
                if roster and roster.entries:
                    yield Label("")
                    yield Label("[bold cyan]Your Roster:[/bold cyan]")
                    for entry in roster.entries:
                        yield Label(
                            f"  [dim]{entry.sigil}[/dim] {entry.model_id:20s} "
                            f"[dim]{entry.role:12s} ceiling: {entry.scope_ceiling}[/dim]"
                        )

                yield Label("")
                yield Label("[bold cyan]Quick Reference - Essential Commands:[/bold cyan]")
                yield Label("  [yellow]bss status[/yellow]        Show environment overview")
                yield Label("  [yellow]bss triage[/yellow]        See prioritized relay queue")
                yield Label("  [yellow]bss log[/yellow]           Timeline of recent blinks")
                yield Label("  [yellow]bss write[/yellow]         Create a new blink interactively")
                yield Label("  [yellow]bss relay[/yellow]         Launch the classic TUI")
                yield Label("  [yellow]bss gateway[/yellow]       Reopen this dashboard")
                yield Label("")
                yield Label("[bold cyan]Next Steps:[/bold cyan]")
                yield Label("  1. Launch the gateway dashboard → visualize your environment")
                yield Label("  2. Try 'bss status' → see what was created")
                yield Label("  3. Try 'bss write' → create your first blink")
                yield Label("  4. Read the docs → https://github.com/alembic-ai/bss")
                yield Label("")
                yield Label("[dim]Welcome to the Blink Sigil System! 🌟[/dim]")

            with Container(id="buttons"):
                yield Button("Launch Dashboard", id="dashboard-btn", variant="primary")
                yield Button("Exit", id="quit-btn", variant="default")

    def action_quit(self) -> None:
        self._mark_complete()
        self.dismiss("quit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "dashboard-btn":
            self._mark_complete()
            self.dismiss("launch_dashboard")
        elif event.button.id == "quit-btn":
            self._mark_complete()
            self.dismiss("quit")

    def _mark_complete(self) -> None:
        """Mark onboarding as complete."""
        marker_file = self.env_path / ".bss_v2_setup_complete"
        marker_file.touch()
