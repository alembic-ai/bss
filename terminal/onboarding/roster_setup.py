"""Roster Setup Screen - Configure models."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Static, Input, Label, Select
from textual.screen import Screen

from bss.environment import BSSEnvironment
from bss.roster import RosterEntry, Roster, update_roster, read_roster


class RosterSetupScreen(Screen):
    """Configure the BSS roster (model list)."""

    CSS = """
    RosterSetupScreen {
        align: center middle;
        background: $surface;
    }

    #roster-container {
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

    Input, Select {
        margin: 1 0;
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

    def __init__(self, step_num: int = 5, total_steps: int = 9, env_path: Path = None):
        super().__init__()
        self.step_num = step_num
        self.total_steps = total_steps
        self.env_path = env_path or Path.cwd()
        self.env = BSSEnvironment(self.env_path)

    def compose(self) -> ComposeResult:
        with Container(id="roster-container"):
            yield Static(f"[bold]Step {self.step_num}/{self.total_steps}: Model Roster[/bold]")
            with Vertical(id="content"):
                yield Label("[bold]Add your first model to the roster[/bold]")
                yield Label("")
                yield Label("[cyan]Sigil:[/cyan] (A-Z, auto-suggested: A)")
                yield Input(value="A", id="sigil-input")
                yield Label("")
                yield Label("[cyan]Display Name:[/cyan] (e.g., 'GPT-4', 'Claude-3', 'Llama')")
                yield Input(placeholder="Model name", id="name-input")
                yield Label("")
                yield Label("[cyan]Role:[/cyan]")
                yield Select(
                    [
                        ("Primary (orchestrates the relay)", "primary"),
                        ("Reviewer (evaluates work)", "reviewer"),
                        ("Specialist (domain expert)", "specialist"),
                        ("Architect (system design)", "architect"),
                    ],
                    value="primary",
                    allow_blank=False,
                    id="role-select",
                )
                yield Label("")
                yield Label("[cyan]Scope Ceiling:[/cyan]")
                yield Select(
                    [
                        ("Atomic (single blink)", "atomic"),
                        ("Local (working thread)", "local"),
                        ("Regional (multi-thread)", "regional"),
                        ("Global (full relay)", "global"),
                    ],
                    value="global",
                    allow_blank=False,
                    id="ceiling-select",
                )
                yield Label("")
                yield Label("[cyan]Notes:[/cyan] (optional)")
                yield Input(placeholder="Any notes about this model", id="notes-input")

            with Container(id="buttons"):
                yield Button("Add Model & Continue →", id="continue-btn", variant="primary")
                yield Button("Skip", id="skip-btn", variant="default")
                yield Button("Quit", id="quit-btn", variant="default")

    def action_quit(self) -> None:
        self.dismiss("quit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "continue-btn":
            self._save_roster()
        elif event.button.id == "skip-btn":
            self.dismiss("next")
        elif event.button.id == "quit-btn":
            self.dismiss("quit")

    def _save_roster(self) -> None:
        """Save roster entry."""
        try:
            sigil = self.query_one("#sigil-input", Input).value or "A"
            name = self.query_one("#name-input", Input).value or f"Model-{sigil}"
            role = self.query_one("#role-select", Select).value or "primary"
            ceiling = self.query_one("#ceiling-select", Select).value or "global"
            notes = self.query_one("#notes-input", Input).value or ""

            entry = RosterEntry(
                sigil=sigil.upper(),
                model_id=name,
                role=role,
                scope_ceiling=ceiling,
                notes=notes,
            )

            roster = read_roster(self.env) or Roster(entries=[])
            roster.entries.append(entry)
            update_roster(self.env, roster)

            self.dismiss("next")
        except Exception as e:
            # Show error but continue
            print(f"Error saving roster: {e}")
            self.dismiss("next")
