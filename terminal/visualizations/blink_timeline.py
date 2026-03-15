"""Blink Timeline Widget - Shows chronological feed of blinks."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from datetime import datetime

from textual.reactive import reactive
from textual.widgets import Static
from textual.containers import ScrollableContainer

from bss.environment import BSSEnvironment
from bss.identifier import parse as parse_id


class BlinkTimelineWidget(ScrollableContainer):
    """Displays a chronological timeline of all blinks."""

    DEFAULT_CSS = """
    BlinkTimelineWidget {
        width: 100%;
        height: 100%;
        border: solid $accent;
        background: $surface;
        padding: 0 1;
        overflow: auto;
    }
    """

    env_path = reactive(Path.cwd())
    filter_sigil = reactive("")
    refresh_count = reactive(0)

    def __init__(self, env: Optional[BSSEnvironment] = None, **kwargs):
        super().__init__(**kwargs)
        self.env = env
        if env:
            self.env_path = env.root

    def render(self) -> str:
        """Render the blink timeline."""
        if not self.env or not self.env.is_valid():
            return "[dim]No environment loaded[/dim]"

        try:
            # Scan all blinks
            all_blinks = self.env.scan()
            if not all_blinks:
                return "[dim]No blinks found[/dim]"

            # Filter by sigil if set
            if self.filter_sigil:
                filtered = []
                for blink_path, blink_id in all_blinks:
                    try:
                        meta = parse_id(blink_id)
                        if meta.author == self.filter_sigil:
                            filtered.append((blink_path, blink_id))
                    except ValueError:
                        pass
                all_blinks = filtered

            # Sort newest first
            all_blinks.reverse()

            # Sigil colors
            sigil_colors = {
                "A": "blue",
                "B": "cyan",
                "C": "green",
                "D": "yellow",
                "E": "magenta",
                "F": "red",
                "G": "blue",
                "H": "cyan",
                "U": "white",
            }

            # Action state symbols
            action_symbols = {
                "~!": "⬆",   # handoff
                ".!": "⏳",   # WIP
                "~.": "✓",   # completed
                "!!": "✗",   # error
                "..": "ℹ",   # informational
                "~~": "—",   # idle
                "!~": "⛔",   # blocked
                "!.": "❓",   # decision
                ".~": "⏸",   # awaiting input
                "!#": "×",   # cancelled
            }

            lines = []
            lines.append(f"[bold]BLINK TIMELINE{' (filtered)' if self.filter_sigil else ''}[/bold]")
            lines.append("")

            # Show up to 50 most recent
            for blink_path, blink_id in all_blinks[:50]:
                try:
                    from bss.blink_file import read as read_blink
                    blink = read_blink(blink_path)
                    meta = parse_id(blink_id)

                    color = sigil_colors.get(meta.author, "white")
                    action_code = meta.action_energy + meta.action_valence
                    action_sym = action_symbols.get(action_code, "•")

                    # Summary (truncate)
                    summary = blink.summary.replace("\n", " ")
                    if len(summary) > 50:
                        summary = summary[:50] + "…"

                    # Get file modification time (rough timestamp)
                    mtime = blink_path.stat().st_mtime
                    delta = datetime.now().timestamp() - mtime
                    if delta < 60:
                        time_str = f"{int(delta)}s ago"
                    elif delta < 3600:
                        time_str = f"{int(delta / 60)}m ago"
                    elif delta < 86400:
                        time_str = f"{int(delta / 3600)}h ago"
                    else:
                        time_str = f"{int(delta / 86400)}d ago"

                    line = (
                        f"[dim]{blink_id[:5]}[/dim] "
                        f"[{color}]{meta.author}[/{color}] "
                        f"{action_sym} "
                        f"{summary:50s} "
                        f"[dim]{time_str}[/dim]"
                    )
                    lines.append(line)

                except Exception:
                    lines.append(f"[red]Error rendering[/red] {blink_id}")

            if len(all_blinks) > 50:
                lines.append(f"[dim]... and {len(all_blinks) - 50} more[/dim]")

            return "\n".join(lines)

        except Exception as e:
            return f"[red]Error loading timeline:[/red] {str(e)}"

    def update_env(self, env: BSSEnvironment):
        """Update environment and refresh."""
        self.env = env
        self.env_path = env.root
        self.refresh_count += 1

    def filter_by_sigil(self, sigil: str):
        """Filter timeline by author sigil."""
        self.filter_sigil = sigil
