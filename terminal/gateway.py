"""BSS V2 Gateway - Main application with visualizations and onboarding."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult, App
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static, Input, Button
from textual.binding import Binding

from bss.environment import BSSEnvironment
from terminal.visualizations import (
    RelayStatusWidget,
    BlinkTimelineWidget,
    LifecycleDiagramWidget,
    LineageTreeWidget,
)


class BSSGatewayApp(App):
    """BSS V2 Gateway - Full setup and visualization dashboard."""

    CSS = """
    Screen {
        background: $surface;
        color: $text;
    }

    #main-container {
        width: 1fr;
        height: 1fr;
        layout: vertical;
    }

    #gateway-header {
        dock: top;
        height: 3;
        background: $accent;
        color: $text;
        text-align: center;
        padding: 1;
    }

    #body {
        width: 1fr;
        height: 1fr;
        layout: horizontal;
    }

    #left-panel {
        width: 35%;
        height: 1fr;
        border: solid $accent;
        layout: vertical;
    }

    #right-panel {
        width: 65%;
        height: 1fr;
        border: solid $accent;
        layout: vertical;
    }

    #status-widget {
        height: 50%;
    }

    #timeline-widget {
        height: 50%;
    }

    #lifecycle-widget {
        height: 35%;
    }

    #lineage-widget {
        height: 65%;
        display: none;
    }

    #command-bar {
        dock: bottom;
        height: 3;
        layout: horizontal;
    }

    #command-input {
        width: 1fr;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("ctrl+e", "exit_app", "Exit"),
        ("ctrl+s", "show_setup", "Setup"),
        ("t", "toggle_tree", "Tree"),
    ]

    TITLE = "BSS V2 Gateway"

    # Ordered list of onboarding screen classes
    ONBOARDING_STEPS = [
        "WelcomeScreen",
        "SystemCheckScreen",
        "ProtocolPrimerScreen",
        "EnvInitScreen",
        "RosterSetupScreen",
        "BackendConfigScreen",
        "BlinkGrammarScreen",
        "ExampleSwarmScreen",
        "SummaryScreen",
    ]

    def __init__(self, env_path: Path = None, skip_onboarding: bool = False):
        super().__init__()
        self.env_path = env_path or Path.cwd()
        self.skip_onboarding = skip_onboarding
        self.env = None
        self._onboarding_step = 0

    def compose(self) -> ComposeResult:
        """Compose the gateway layout."""
        yield Header()

        with Container(id="main-container"):
            yield Static(
                f"[bold]BSS V2 GATEWAY[/bold] — {self.env_path}",
                id="gateway-header",
            )

            with Horizontal(id="body"):
                with Vertical(id="left-panel"):
                    yield RelayStatusWidget(self.env, id="status-widget")
                    yield BlinkTimelineWidget(self.env, id="timeline-widget")

                with Vertical(id="right-panel"):
                    yield LifecycleDiagramWidget(id="lifecycle-widget")
                    yield LineageTreeWidget(self.env, id="lineage-widget")

            with Container(id="command-bar"):
                yield Input(
                    placeholder="Type command (/help, /setup, /status)...",
                    id="command-input",
                )
                yield Button("Status", id="btn-status", variant="default")
                yield Button("Tree", id="btn-tree", variant="default")
                yield Button("Help", id="btn-help", variant="default")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the gateway."""
        # Try to load existing environment
        if (self.env_path / "relay").exists():
            self.env = BSSEnvironment(self.env_path)

        # Check if onboarding is needed
        marker = self.env_path / ".bss_v2_setup_complete"
        if not marker.exists() and not self.skip_onboarding:
            self._onboarding_step = 0
            self._push_onboarding_step(0)
            return

        # Go straight to dashboard
        self._init_dashboard()

    def _get_onboarding_screen(self, step: int):
        """Create the onboarding screen for the given step index."""
        from terminal.onboarding import (
            WelcomeScreen,
            SystemCheckScreen,
            ProtocolPrimerScreen,
            EnvInitScreen,
            RosterSetupScreen,
            BackendConfigScreen,
            BlinkGrammarScreen,
            ExampleSwarmScreen,
            SummaryScreen,
        )

        total = len(self.ONBOARDING_STEPS)
        screens = {
            "WelcomeScreen": lambda: WelcomeScreen(),
            "SystemCheckScreen": lambda: SystemCheckScreen(step + 1, total),
            "ProtocolPrimerScreen": lambda: ProtocolPrimerScreen(step + 1, total),
            "EnvInitScreen": lambda: EnvInitScreen(step + 1, total, self.env_path),
            "RosterSetupScreen": lambda: RosterSetupScreen(step + 1, total, self.env_path),
            "BackendConfigScreen": lambda: BackendConfigScreen(step + 1, total, self.env_path),
            "BlinkGrammarScreen": lambda: BlinkGrammarScreen(step + 1, total, self.env_path),
            "ExampleSwarmScreen": lambda: ExampleSwarmScreen(step + 1, total, self.env_path),
            "SummaryScreen": lambda: SummaryScreen(step + 1, total, self.env_path),
        }

        name = self.ONBOARDING_STEPS[step]
        return screens[name]()

    def _push_onboarding_step(self, step: int) -> None:
        """Push the onboarding screen at the given step with a callback."""
        if step >= len(self.ONBOARDING_STEPS):
            # Onboarding complete — init dashboard
            self._init_dashboard()
            return

        self._onboarding_step = step
        screen = self._get_onboarding_screen(step)
        self.push_screen(screen, callback=self._on_onboarding_step_done)

    def _on_onboarding_step_done(self, result: str | None) -> None:
        """Called when an onboarding screen dismisses."""
        if result == "quit":
            self.exit()
            return

        if result == "launch_dashboard":
            # Exit TUI and launch web dashboard
            self.exit(message="launch_dashboard")
            return

        # Move to next step
        self._push_onboarding_step(self._onboarding_step + 1)

    def _init_dashboard(self) -> None:
        """Launch the web dashboard (exits TUI, starts FastAPI server)."""
        self.exit(message="launch_dashboard")

    def action_exit_app(self) -> None:
        """Exit the gateway."""
        self.exit()

    def action_show_setup(self) -> None:
        """Re-run onboarding."""
        self._onboarding_step = 0
        self._push_onboarding_step(0)

    def action_toggle_tree(self) -> None:
        """Toggle lineage tree view."""
        lineage = self.query_one("#lineage-widget")
        lineage.display = not lineage.display

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        if event.input.id != "command-input":
            return

        command = event.input.value.strip()
        event.input.value = ""

        if command.startswith("/"):
            self._handle_command(command)

    def _handle_command(self, command: str) -> None:
        """Handle slash commands."""
        parts = command[1:].split()
        cmd = parts[0] if parts else ""

        if cmd == "help":
            self._show_help()
        elif cmd == "setup":
            self.action_show_setup()
        elif cmd == "status":
            if self.env:
                status = self.query_one("#status-widget", RelayStatusWidget)
                status.update_env(self.env)
        elif cmd == "tree":
            self.action_toggle_tree()

    def _show_help(self) -> None:
        """Show help in the header."""
        header = self.query_one("#gateway-header", Static)
        header.update(
            "[bold]Commands:[/bold] /status /setup /tree /help  |  "
            "[bold]Keys:[/bold] Ctrl+E exit, Ctrl+S setup, T tree"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-status":
            if self.env:
                status = self.query_one("#status-widget", RelayStatusWidget)
                status.update_env(self.env)
        elif event.button.id == "btn-help":
            self._show_help()
        elif event.button.id == "btn-tree":
            self.action_toggle_tree()
