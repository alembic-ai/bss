"""Blink Grammar Screen - Interactive ID explorer."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Static, Label
from textual.screen import Screen

from src.bss.identifier import generate, parse as parse_id
from src.bss.sigils import describe as describe_id


class BlinkGrammarScreen(Screen):
    """Interactive exploration of blink ID grammar."""

    CSS = """
    BlinkGrammarScreen {
        align: center middle;
        background: $surface;
    }

    #grammar-container {
        width: 100;
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

    BINDINGS = [("space", "generate", "Generate")]

    def __init__(self, step_num: int = 7, total_steps: int = 9, env_path: Path = None):
        super().__init__()
        self.step_num = step_num
        self.total_steps = total_steps
        self.env_path = env_path or Path.cwd()
        self.sample_id = "0002FA~!}!^#!=~^="

    def compose(self) -> ComposeResult:
        with Container(id="grammar-container"):
            yield Static(f"[bold]Step {self.step_num}/{self.total_steps}: Blink Grammar[/bold]")
            with Vertical(id="content"):
                yield Label("[bold]Understanding Blink IDs[/bold]")
                yield Label("")
                yield Label("[cyan]Every blink has a unique 17-character ID that encodes state:[/cyan]")
                yield Label("")
                yield Static(self._render_sample_id(), id="sample-display")
                yield Label("")
                yield Label("[yellow]💡 Each position in the ID tells you something:[/yellow]")
                yield Label("[dim]  Pos 1-5:  Sequence number (auto-incremented)[/dim]")
                yield Label("[dim]  Pos 6:    Author sigil (A, B, C, ... U for user)[/dim]")
                yield Label("[dim]  Pos 7-8:  Action (energy + valence: ~!, .!, ~., etc)[/dim]")
                yield Label("[dim]  Pos 9:    Relational (^=origin, }=branch, +=continue, etc)[/dim]")
                yield Label("[dim]  Pos 10+:  Confidence, cognitive state, domain, scope, etc[/dim]")
                yield Label("")
                yield Label("[cyan]Press SPACE to generate a random ID and see its breakdown:[/cyan]")
                yield Static("", id="breakdown-display")

            with Container(id="buttons"):
                yield Button("Generate Sample", id="gen-btn", variant="primary")
                yield Button("Continue →", id="continue-btn", variant="primary")
                yield Button("Skip", id="skip-btn", variant="default")
                yield Button("Quit", id="quit-btn", variant="default")

    def action_generate(self) -> None:
        """Generate a new sample ID."""
        sample = generate(
            sequence=42,
            author="A",
            action_energy="~",
            action_valence="!",
            relational="}",
            confidence="!",
            cognitive="=",
            domain="#",
            subdomain="!",
            scope="=",
            maturity="~",
            priority="^",
            sensitivity="=",
        )
        self.sample_id = sample
        self.query_one("#sample-display", Static).update(self._render_sample_id())
        self.query_one("#breakdown-display", Static).update(
            f"[bold cyan]Breakdown:[/bold cyan]\n{describe_id(sample)}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "gen-btn":
            self.action_generate()
        elif event.button.id == "continue-btn":
            self.dismiss("next")
        elif event.button.id == "skip-btn":
            self.dismiss("next")
        elif event.button.id == "quit-btn":
            self.dismiss("quit")

    def _render_sample_id(self) -> str:
        """Render the sample ID with highlighting."""
        id_str = self.sample_id
        parts = [
            f"[bold blue]{id_str[0:5]}[/bold blue]",  # sequence
            f"[bold green]{id_str[5]}[/bold green]",   # author
            f"[bold yellow]{id_str[6:8]}[/bold yellow]",  # action
            f"[bold magenta]{id_str[8]}[/bold magenta]",  # relational
            f"[bold cyan]{id_str[9:]}[/bold cyan]",  # rest
        ]
        return f"[bold]Example ID:[/bold] {''.join(parts)}"
