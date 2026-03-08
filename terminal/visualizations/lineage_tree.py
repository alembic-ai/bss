"""Lineage Tree Widget - Shows blink genealogy."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.tree import Tree
from textual.reactive import reactive
from textual.widgets import Static
from textual.containers import ScrollableContainer

from src.bss.environment import BSSEnvironment
from src.bss.generations import get_chain
from src.bss.identifier import parse as parse_id


class LineageTreeWidget(ScrollableContainer):
    """Displays the lineage tree for a blink or environment."""

    DEFAULT_CSS = """
    LineageTreeWidget {
        width: 100%;
        height: 100%;
        border: solid $accent;
        background: $surface;
        padding: 0 1;
        overflow: auto;
    }
    """

    selected_blink_id = reactive("")
    env_path = reactive(Path.cwd())

    def __init__(self, env: Optional[BSSEnvironment] = None, blink_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.env = env
        self.selected_blink_id = blink_id
        if env:
            self.env_path = env.root

    def render(self) -> str:
        """Render the lineage tree."""
        if not self.env or not self.selected_blink_id:
            return "[dim]No blink selected[/dim]"

        try:
            chain = get_chain(self.env, self.selected_blink_id)
            if not chain:
                return f"[red]Blink not found:[/red] {self.selected_blink_id}"

            # Build tree
            tree = Tree(f"[bold]{chain[0].blink_id}[/bold]")

            # Sigil color mapping (matches TUI colors)
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

            current_node = tree
            for blink in chain[1:]:
                try:
                    meta = parse_id(blink.blink_id)
                    color = sigil_colors.get(meta.author, "white")

                    # Relational symbol
                    rel_symbol_map = {
                        "^": "⁰",  # origin
                        "+": "→",  # continuing
                        "}": "↗",  # branching
                        "{": "↙",  # converging
                        "_": "✗",  # dead-end
                        "=": "≡",  # echoing
                        "#": "⚔",  # contradicting
                    }
                    rel_sym = rel_symbol_map.get(meta.relational, "•")

                    label = f"[{color}]{rel_sym} {blink.blink_id}[/{color}]"

                    # Highlight selected
                    if blink.blink_id == self.selected_blink_id:
                        label += " [green]← YOU[/green]"

                    # First 40 chars of summary
                    summary = blink.summary.replace("\n", " ")
                    if len(summary) > 40:
                        summary = summary[:40] + "..."
                    label += f" [dim]{summary}[/dim]"

                    current_node = current_node.add(label)
                except (ValueError, AttributeError):
                    current_node = current_node.add(blink.blink_id)

            return str(tree)

        except Exception as e:
            return f"[red]Error loading lineage:[/red] {str(e)}"

    def load_blink(self, env: BSSEnvironment, blink_id: str):
        """Load and display lineage for a specific blink."""
        self.env = env
        self.env_path = env.root
        self.selected_blink_id = blink_id
