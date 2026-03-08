"""Welcome Screen - Introduction to BSS."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Static, Label
from textual.screen import Screen


class WelcomeScreen(Screen):
    """Welcome screen with BSS introduction."""

    CSS = """
    WelcomeScreen {
        align: center middle;
        background: $surface;
    }

    #welcome-container {
        width: 80;
        height: auto;
        border: solid $accent;
        background: $boost;
        padding: 2 4;
    }

    #sigil-art {
        dock: top;
        height: auto;
        text-align: center;
        color: $accent;
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

    def compose(self) -> ComposeResult:
        with Container(id="welcome-container"):
            yield Static(self.render_sigil(), id="sigil-art")
            with Vertical(id="content"):
                yield Label("[bold]Welcome to the Blink Sigil System (BSS)[/bold]")
                yield Label("")
                yield Label("[cyan]What is BSS?[/cyan]")
                yield Label("")
                yield Label(
                    "[dim]BSS is a file-based coordination protocol for stateless AI agents.[/dim]"
                )
                yield Label("")
                yield Label(
                    "[dim]Instead of locking shared memory or queuing messages, BSS agents:[/dim]"
                )
                yield Label("[dim]  • Read the current state from immutable files (blinks)[/dim]")
                yield Label("[dim]  • Write their results as new blinks (audit trail)[/dim]")
                yield Label("[dim]  • Hand off cleanly to the next model in the relay[/dim]")
                yield Label("")
                yield Label("[yellow]✨ Key Features:[/yellow]")
                yield Label("[dim]  ✓ Immutable audit trail — every thought is recorded[/dim]")
                yield Label("[dim]  ✓ No locking, no race conditions — file system is slow but safe[/dim]")
                yield Label("[dim]  ✓ Multi-backend support — swap models without code changes[/dim]")
                yield Label("[dim]  ✓ Self-documenting — blinks contain all context[/dim]")
                yield Label("")
                yield Label(
                    "[cyan]This gateway will walk you through a comprehensive setup of BSS,[/cyan]"
                )
                yield Label(
                    "[cyan]covering everything from protocol concepts to launching your first swarm.[/cyan]"
                )
            with Container(id="buttons"):
                yield Button("Begin Setup →", id="begin-btn", variant="primary")
                yield Button("Quit", id="quit-btn", variant="default")

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "begin-btn":
            self.dismiss("next")
        elif event.button.id == "quit-btn":
            self.dismiss("quit")

    @staticmethod
    def render_sigil() -> str:
        """Render ASCII BSS sigil art."""
        return """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║         ██████╗ ███████╗███████╗                             ║
║         ██╔══██╗██╔════╝██╔════╝                             ║
║         ██████╔╝███████╗███████╗                             ║
║         ██╔══██╗╚════██║╚════██║                             ║
║         ██████╔╝███████║███████║                             ║
║         ╚═════╝ ╚══════╝╚══════╝                             ║
║                                                               ║
║        Blink Sigil System — V2 Gateway Setup                 ║
║         File-based coordination for AI agents                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
        """
