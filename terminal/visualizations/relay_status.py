"""Relay Status Widget - Shows live environment status."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.table import Table
from textual.reactive import reactive
from textual.widgets import Static

from src.bss.environment import BSSEnvironment
from src.bss.roster import read_roster


class RelayStatusWidget(Static):
    """Displays the current relay and environment status."""

    DEFAULT_CSS = """
    RelayStatusWidget {
        width: 100%;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    env_path = reactive(Path.cwd())
    refresh_count = reactive(0)

    def __init__(self, env: Optional[BSSEnvironment] = None, **kwargs):
        super().__init__(**kwargs)
        self.env = env
        if env:
            self.env_path = env.root

    def render(self) -> str:
        """Render the relay status."""
        if not self.env or not self.env.is_valid():
            return "[red]Not a valid BSS environment[/red]"

        lines = []
        lines.append("[bold]RELAY STATUS[/bold]")
        lines.append("")

        # Directory counts
        relay_count = len(list(self.env.relay_dir.glob("*.md")))
        active_count = len(list(self.env.active_dir.glob("*.md")))
        profile_count = len(list(self.env.profile_dir.glob("*.md")))
        archive_count = len(list(self.env.archive_dir.glob("*.md")))
        artifact_count = len(list(self.env.artifacts_dir.glob("*"))) if self.env.artifacts_dir.exists() else 0

        lines.append("[bold cyan]Directory Counts:[/bold cyan]")
        lines.append(f"  /relay/     {relay_count:4d} blinks  {'⚠️ ' if relay_count > 100 else ''}")
        lines.append(f"  /active/    {active_count:4d} blinks")
        lines.append(f"  /profile/   {profile_count:4d} blinks")
        lines.append(f"  /archive/   {archive_count:4d} blinks")
        lines.append(f"  /artifacts/ {artifact_count:4d} files")
        lines.append("")

        # Next sequence
        try:
            next_seq = self.env.next_sequence()
            lines.append(f"[bold cyan]Next Sequence:[/bold cyan] {next_seq:05d}")
        except Exception:
            lines.append("[dim]Next Sequence: (unable to determine)[/dim]")

        lines.append("")

        # Roster
        lines.append("[bold cyan]Model Roster:[/bold cyan]")
        try:
            roster = read_roster(self.env)
            if roster and roster.entries:
                for entry in roster.entries:
                    color_map = {
                        "A": "blue",
                        "B": "cyan",
                        "C": "green",
                        "D": "yellow",
                        "E": "magenta",
                    }
                    color = color_map.get(entry.sigil, "white")
                    lines.append(
                        f"  [{color}]{entry.sigil}[/{color}] {entry.model_id:30s} "
                        f"[dim]{entry.role:12s} ceiling: {entry.scope_ceiling}[/dim]"
                    )
            else:
                lines.append("  [dim](no roster configured)[/dim]")
        except Exception as e:
            lines.append(f"  [red]Error reading roster:[/red] {str(e)}")

        lines.append("")

        # Error chains
        try:
            error_blinks = [b for b in list(self.env.active_dir.glob("*.md")) if "!!" in b.name]
            if error_blinks:
                lines.append(f"[bold red]⚠️  Error Chains:[/bold red] {len(error_blinks)} active errors")
            else:
                lines.append("[bold green]✓ No errors[/bold green]")
        except Exception:
            lines.append("[dim]Error chain status: (unable to determine)[/dim]")

        return "\n".join(lines)

    def update_env(self, env: BSSEnvironment):
        """Update the environment and trigger re-render."""
        self.env = env
        self.env_path = env.root
        self.refresh_count += 1
