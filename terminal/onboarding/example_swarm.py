"""Example Swarm Screen - Choose and launch example."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Static, Label, RadioButton, RadioSet
from textual.screen import Screen


class ExampleSwarmScreen(Screen):
    """Choose and launch an example swarm."""

    CSS = """
    ExampleSwarmScreen {
        align: center middle;
        background: $surface;
    }

    #example-container {
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

    RadioSet {
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

    def __init__(self, step_num: int = 8, total_steps: int = 9, env_path: Path = None):
        super().__init__()
        self.step_num = step_num
        self.total_steps = total_steps
        self.env_path = env_path or Path.cwd()

    def compose(self) -> ComposeResult:
        with Container(id="example-container"):
            yield Static(f"[bold]Step {self.step_num}/{self.total_steps}: Example Swarm[/bold]")
            with Vertical(id="content"):
                yield Label("[bold]Launch an example to see BSS in action?[/bold]")
                yield Label("")
                with RadioSet(id="example-radio"):
                    yield RadioButton("Skip example for now", value=True, id="skip-radio")
                    yield RadioButton("Single Model Demo", value=False, id="single-radio")
                    yield RadioButton("3-Model Research Swarm", value=False, id="research-radio")
                yield Label("")
                yield Label("[dim]Skip if you want to explore manually.[/dim]")
                yield Label("[dim]Demos write sample blinks to /relay/ for hands-on learning.[/dim]")

            with Container(id="buttons"):
                yield Button("Continue →", id="continue-btn", variant="primary")
                yield Button("Quit", id="quit-btn", variant="default")

    def action_quit(self) -> None:
        self.dismiss("quit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "continue-btn":
            self.dismiss("next")
        elif event.button.id == "quit-btn":
            self.dismiss("quit")
