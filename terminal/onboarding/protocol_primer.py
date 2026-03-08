"""Protocol Primer Screen - Interactive walkthrough of BSS concepts."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Static
from textual.screen import Screen

from terminal.visualizations import SteppedLifecycleDiagramWidget


class ProtocolPrimerScreen(Screen):
    """Interactive introduction to BSS protocol concepts."""

    CSS = """
    ProtocolPrimerScreen {
        background: $surface;
    }

    #primer-container {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
        background: $boost;
        padding: 2 4;
    }

    #lifecycle {
        width: 100%;
        height: auto;
    }

    #buttons {
        dock: bottom;
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-top: 2;
    }

    Button {
        margin: 0 2;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, step_num: int = 3, total_steps: int = 9):
        super().__init__()
        self.step_num = step_num
        self.total_steps = total_steps

    def compose(self) -> ComposeResult:
        with Container(id="primer-container"):
            yield Static(f"[bold]Step {self.step_num}/{self.total_steps}: Protocol Concepts[/bold]")
            yield Static("")
            yield SteppedLifecycleDiagramWidget(id="lifecycle")
            with Container(id="buttons"):
                yield Button("Next Step →", id="next-btn", variant="primary")
                yield Button("Skip", id="skip-btn", variant="default")
                yield Button("Quit", id="quit-btn", variant="default")

    def action_quit(self) -> None:
        self.dismiss("quit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        lifecycle = self.query_one(SteppedLifecycleDiagramWidget)

        if event.button.id == "next-btn":
            if lifecycle.advance():
                pass  # Continue stepping through phases
            else:
                self.dismiss("next")

        elif event.button.id == "skip-btn":
            self.dismiss("next")

        elif event.button.id == "quit-btn":
            self.dismiss("quit")
