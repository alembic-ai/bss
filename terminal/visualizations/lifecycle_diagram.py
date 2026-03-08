"""Lifecycle Diagram Widget - Shows the 5-phase BSS session cycle."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Static


class LifecycleDiagramWidget(Static):
    """Displays the 5-phase BSS session lifecycle with reactive active phase."""

    DEFAULT_CSS = """
    LifecycleDiagramWidget {
        width: 100%;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    active_phase = reactive("INTAKE")

    PHASES = [
        ("INTAKE", "Read /relay/, /active/, /profile/"),
        ("TRIAGE", "Sort by priority, sensitivity, scope"),
        ("WORK", "Run inference, write working blinks"),
        ("OUTPUT", "Write handoff to /relay/"),
        ("DORMANCY", "Session ends, state released"),
    ]

    PHASE_COLORS = {
        "INTAKE": "blue",
        "TRIAGE": "cyan",
        "WORK": "green",
        "OUTPUT": "yellow",
        "DORMANCY": "magenta",
    }

    def render(self) -> str:
        """Render the lifecycle diagram."""
        lines = []
        lines.append("[bold]BSS 5-Phase Session Lifecycle[/bold]")
        lines.append("")

        # Phase boxes
        phase_line = ""
        for i, (phase_name, _) in enumerate(self.PHASES):
            color = self.PHASE_COLORS.get(phase_name, "white")
            if phase_name == self.active_phase:
                # Highlight active phase
                box = f"[bold {color}]█ {phase_name} █[/]"
            else:
                box = f"[dim {color}]  {phase_name}  [/]"
            phase_line += box
            if i < len(self.PHASES) - 1:
                phase_line += " → "

        lines.append(phase_line)
        lines.append("")

        # Description of active phase
        active_idx = next((i for i, (p, _) in enumerate(self.PHASES) if p == self.active_phase), 0)
        phase_name, phase_desc = self.PHASES[active_idx]
        lines.append(f"[bold]{phase_name}:[/bold] {phase_desc}")

        # Phase details
        details = {
            "INTAKE": "[dim]Reads:[/dim] /relay/, /active/, /profile/\n[dim]Writes:[/dim] (nothing yet)",
            "TRIAGE": "[dim]Reads:[/dim] relay queue\n[dim]Writes:[/dim] (nothing yet)",
            "WORK": "[dim]Reads:[/dim] /relay/, /active/\n[dim]Writes:[/dim] working blinks to /active/",
            "OUTPUT": "[dim]Reads:[/dim] working blinks\n[dim]Writes:[/dim] handoff blink to /relay/",
            "DORMANCY": "[dim]Reads:[/dim] (nothing)\n[dim]Writes:[/dim] (nothing)\nState released, next model wakes.",
        }
        lines.append("")
        lines.append(details.get(phase_name, ""))

        return "\n".join(lines)


class SteppedLifecycleDiagramWidget(Static):
    """Interactive lifecycle diagram with step-through mode for onboarding."""

    DEFAULT_CSS = """
    SteppedLifecycleDiagramWidget {
        width: 100%;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    current_step = reactive(0)

    PHASES = [
        {
            "name": "INTAKE",
            "title": "Phase 1: INTAKE — Read the Current State",
            "description": "When a model wakes up, it first reads all the current state:",
            "details": [
                "• /relay/ — What handoffs are waiting from other models?",
                "• /active/ — What work threads are ongoing?",
                "• /profile/ — Who's in the roster? What are my scope limits?",
            ],
            "key_insight": "Each model starts with the complete context from the previous session.",
        },
        {
            "name": "TRIAGE",
            "title": "Phase 2: TRIAGE — Prioritize the Work",
            "description": "Sort all relay blinks by priority and urgency:",
            "details": [
                "• CRITICAL — errors marked !! or blocking issues",
                "• URGENT — high-priority handoffs marked ~!",
                "• NORMAL — regular work marked ~.",
                "• LOW — informational (~.) and idle (~~) blinks",
            ],
            "key_insight": "No locking needed — the relay queue is a simple file-system queue.",
        },
        {
            "name": "WORK",
            "title": "Phase 3: WORK — Process the Highest Priority Item",
            "description": "Run your model's inference and write results to /active/:",
            "details": [
                "• Read the top relay blink (context)",
                "• Call your model with that context",
                "• Write working blinks to /active/ (immutable, named, auto-sequenced)",
                "• Continue until done or blocked",
            ],
            "key_insight": "All thinking is recorded as blinks — audit trail is automatic.",
        },
        {
            "name": "OUTPUT",
            "title": "Phase 4: OUTPUT — Handoff to the Next Model",
            "description": "Signal completion and pass work to the next model:",
            "details": [
                "• Write final blink to /relay/ (marked ~! for handoff)",
                "• Copy summary into the blink",
                "• Reference any /active/ blinks in lineage",
                "• Mark as complete",
            ],
            "key_insight": "Handoff is explicit — next model reads /relay/, not guessing.",
        },
        {
            "name": "DORMANCY",
            "title": "Phase 5: DORMANCY — Release and Rest",
            "description": "Session ends, your model's state is released:",
            "details": [
                "• Session ends cleanly (no zombie processes)",
                "• Model state memory is freed",
                "• Blinks remain in environment (immutable forever)",
                "• Next model in roster wakes and starts at INTAKE",
            ],
            "key_insight": "Stateless design — each model is a clean slate, context from blinks.",
        },
    ]

    def render(self) -> str:
        """Render the current step."""
        phase = self.PHASES[self.current_step]

        lines = []
        lines.append(f"[bold cyan]Step {self.current_step + 1}/{len(self.PHASES)}[/bold cyan]")
        lines.append("")
        lines.append(f"[bold {self.PHASE_COLORS[phase['name']]}]{phase['title']}[/bold {self.PHASE_COLORS[phase['name']]}]")
        lines.append("")
        lines.append(phase["description"])
        lines.append("")
        for detail in phase["details"]:
            lines.append(detail)
        lines.append("")
        lines.append(f"[dim]💡 {phase['key_insight']}[/dim]")
        lines.append("")
        lines.append("[dim]Press [bold]SPACE[/bold] to continue or [bold]Q[/bold] to skip[/dim]")

        return "\n".join(lines)

    PHASE_COLORS = {
        "INTAKE": "blue",
        "TRIAGE": "cyan",
        "WORK": "green",
        "OUTPUT": "yellow",
        "DORMANCY": "magenta",
    }

    def advance(self) -> bool:
        """Move to next step. Returns True if there are more steps."""
        if self.current_step < len(self.PHASES) - 1:
            self.current_step += 1
            return True
        return False
