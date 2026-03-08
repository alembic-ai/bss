"""System Check Screen - Verify dependencies."""

from __future__ import annotations

import sys
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Static, Label
from textual.screen import Screen


class SystemCheckScreen(Screen):
    """Check system requirements and dependencies."""

    CSS = """
    SystemCheckScreen {
        align: center middle;
        background: $surface;
    }

    #check-container {
        width: 80;
        height: auto;
        border: solid $accent;
        background: $boost;
        padding: 2 4;
    }

    #title {
        dock: top;
        height: auto;
        text-align: center;
        color: $accent;
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

    def __init__(self, step_num: int = 2, total_steps: int = 9):
        super().__init__()
        self.step_num = step_num
        self.total_steps = total_steps
        self.checks = self._run_checks()
        self.can_proceed = all(check["required"] is False or check["pass"] for check in self.checks)

    def compose(self) -> ComposeResult:
        with Container(id="check-container"):
            yield Static(f"[bold]Step {self.step_num}/{self.total_steps}[/bold]", id="title")
            with Vertical(id="content"):
                yield Label("[bold]System Requirements Check[/bold]")
                yield Label("")

                for check in self.checks:
                    status = "[green]✓[/green]" if check["pass"] else "[red]✗[/red]"
                    required_label = "[red](required)[/red]" if check["required"] else "[yellow](optional)[/yellow]"
                    yield Label(
                        f"{status} {check['name']:25s} {check['version']:20s} {required_label}"
                    )

                yield Label("")

                if not self.can_proceed:
                    yield Label("[red]Some required dependencies are missing.[/red]")
                    yield Label("")
                    yield Label("[yellow]To install, run:[/yellow]")
                    yield Label("[dim]pip install blink-sigil-system[relay][/dim]")
                    yield Label("")
                else:
                    yield Label("[green]All checks passed! Ready to continue.[/green]")

            with Container(id="buttons"):
                if self.can_proceed:
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

    def _run_checks(self) -> list[dict]:
        """Run system checks and return results."""
        checks = []

        # Python version
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        py_pass = sys.version_info >= (3, 11)
        checks.append({
            "name": "Python",
            "version": py_ver,
            "pass": py_pass,
            "required": True,
        })

        # Required packages
        required_packages = ["textual", "rich", "typer"]
        for pkg in required_packages:
            try:
                __import__(pkg)
                checks.append({
                    "name": pkg.capitalize(),
                    "version": "installed",
                    "pass": True,
                    "required": True,
                })
            except ImportError:
                checks.append({
                    "name": pkg.capitalize(),
                    "version": "missing",
                    "pass": False,
                    "required": True,
                })

        # Optional packages
        optional_packages = [
            ("anthropic", "Anthropic API"),
            ("google.genai", "Google Gemini"),
            ("huggingface_hub", "Hugging Face"),
            ("llama_cpp", "llama-cpp-python"),
        ]
        for import_name, display_name in optional_packages:
            try:
                __import__(import_name)
                checks.append({
                    "name": display_name,
                    "version": "installed",
                    "pass": True,
                    "required": False,
                })
            except ImportError:
                checks.append({
                    "name": display_name,
                    "version": "not installed",
                    "pass": False,
                    "required": False,
                })

        return checks
