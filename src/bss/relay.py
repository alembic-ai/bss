"""BSS relay protocol — session lifecycle, handoff, and error escalation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.bss.blink_file import BlinkFile, write as write_blink, read as read_blink
from src.bss.environment import BSSEnvironment
from src.bss.identifier import generate, parse as parse_id


class SessionPhase(Enum):
    """The five phases of a BSS model session."""
    INTAKE = "intake"
    TRIAGE = "triage"
    WORK = "work"
    OUTPUT = "output"
    DORMANCY = "dormancy"


@dataclass
class SessionContext:
    """Context gathered during the INTAKE and TRIAGE phases."""
    relay_blinks: list[BlinkFile] = field(default_factory=list)
    active_blinks: list[BlinkFile] = field(default_factory=list)
    profile_blinks: list[BlinkFile] = field(default_factory=list)
    triaged_relay: list[BlinkFile] = field(default_factory=list)
    highest_sequence: str = "00000"
    phase: SessionPhase = SessionPhase.INTAKE


class Session:
    """Implements the five-phase BSS session lifecycle.

    INTAKE → TRIAGE → WORK → OUTPUT → DORMANCY
    """

    def __init__(self, env: BSSEnvironment, author: str = "A"):
        self.env = env
        self.author = author
        self.context = SessionContext()
        self.output_blinks: list[BlinkFile] = []

    @property
    def phase(self) -> SessionPhase:
        return self.context.phase

    def intake(self) -> SessionContext:
        """Execute the startup sequence (Module 2.2).

        Reads directories in order: relay → active → profile.
        """
        self.context.phase = SessionPhase.INTAKE

        # Step 1: Read /relay/
        self.context.relay_blinks = self.env.scan("relay")

        # Step 2: Read /active/
        self.context.active_blinks = self.env.scan("active")

        # Step 3: Read /profile/
        self.context.profile_blinks = self.env.scan("profile")

        # Record highest sequence
        self.context.highest_sequence = self.env.highest_sequence()

        # Move to triage
        self.context.phase = SessionPhase.TRIAGE

        # Triage relay blinks
        self.context.triaged_relay = self.env.triage("relay")

        return self.context

    def begin_work(self) -> None:
        """Transition to the WORK phase."""
        self.context.phase = SessionPhase.WORK

    def begin_output(self) -> None:
        """Transition to the OUTPUT phase."""
        self.context.phase = SessionPhase.OUTPUT

    def dormancy(self) -> None:
        """End the session. No state is retained."""
        self.context.phase = SessionPhase.DORMANCY

    def run_full_lifecycle(self) -> SessionContext:
        """Execute a complete lifecycle through all five phases.

        Returns the context after intake/triage for the caller to
        use during the WORK phase.
        """
        ctx = self.intake()
        self.begin_work()
        return ctx


def handoff(
    env: BSSEnvironment,
    summary: str,
    author: str = "A",
    parent: str | None = None,
    relational: str = "+",
    confidence: str = ".",
    cognitive: str = "=",
    domain: str = "#",
    subdomain: str = ".",
    scope: str = "-",
    maturity: str = "~",
    priority: str = "=",
    sensitivity: str = "=",
    min_sentences: int = 2,
) -> BlinkFile:
    """Write a handoff blink to /relay/ with action state ~!.

    Args:
        env: The BSS environment.
        summary: Description of what was done, state left, what's next.
        author: Author sigil.
        parent: Parent blink ID (for Born from). None creates an origin.
        relational: Relational sigil (default: continuation).
        min_sentences: Minimum sentence count for summary validation.
        All other kwargs: sigil values with sensible defaults.

    Returns:
        The written BlinkFile.
    """
    seq = env.next_sequence()

    blink_id = generate(
        sequence=seq,
        author=author,
        action_energy="~",
        action_valence="!",
        relational=relational if parent else "^",
        confidence=confidence,
        cognitive=cognitive,
        domain=domain,
        subdomain=subdomain,
        scope=scope,
        maturity=maturity,
        priority=priority,
        sensitivity=sensitivity,
    )

    if parent:
        born_from = [parent]
        # Build lineage: try to find parent's lineage
        parent_path = env.find_blink(parent)
        if parent_path:
            parent_blink = read_blink(parent_path)
            if parent_blink.lineage and isinstance(parent_blink.lineage, list):
                lineage = parent_blink.lineage[-6:] + [blink_id]  # Max 7
            else:
                lineage = [parent, blink_id]
        else:
            lineage = [parent, blink_id]
    else:
        born_from = ["Origin"]
        lineage = [blink_id]

    blink = BlinkFile(
        blink_id=blink_id,
        born_from=born_from,
        summary=summary,
        lineage=lineage,
        links=[],
    )

    write_blink(blink, env.relay_dir, min_sentences=min_sentences)
    return blink


def error_blink(
    env: BSSEnvironment,
    summary: str,
    author: str = "A",
    parent: str | None = None,
    confidence: str = "~",
    domain: str = "#",
    subdomain: str = "-",
    scope: str = "-",
    min_sentences: int = 2,
) -> BlinkFile:
    """Write an error blink to /relay/ with action state !!.

    Args:
        env: The BSS environment.
        summary: What was attempted, what failed, what's needed to fix.
        author: Author sigil.
        parent: Parent error blink ID for chained escalation.
        confidence: Diagnostic certainty (! clear, ~ uncertain).
        min_sentences: Minimum sentence count for summary validation.

    Returns:
        The written BlinkFile.
    """
    seq = env.next_sequence()

    blink_id = generate(
        sequence=seq,
        author=author,
        action_energy="!",
        action_valence="!",
        relational="+" if parent else "^",
        confidence=confidence,
        cognitive="%",  # Frustration — something broke
        domain=domain,
        subdomain=subdomain,
        scope=scope,
        maturity="-",  # Needs revision
        priority="!",  # Critical
        sensitivity="!",  # Blocking
    )

    if parent:
        born_from = [parent]
        parent_path = env.find_blink(parent)
        if parent_path:
            parent_blink = read_blink(parent_path)
            if parent_blink.lineage and isinstance(parent_blink.lineage, list):
                lineage = parent_blink.lineage[-6:] + [blink_id]
            else:
                lineage = [parent, blink_id]
        else:
            lineage = [parent, blink_id]
    else:
        born_from = ["Origin"]
        lineage = [blink_id]

    blink = BlinkFile(
        blink_id=blink_id,
        born_from=born_from,
        summary=summary,
        lineage=lineage,
        links=[],
    )

    write_blink(blink, env.relay_dir, min_sentences=min_sentences)
    return blink


def check_escalation(env: BSSEnvironment) -> list[list[BlinkFile]]:
    """Find chains of 2+ linked error blinks without intervening resolution.

    Returns a list of error chains, where each chain is a list of
    BlinkFile objects with action state !!.
    """
    # Scan all directories for error blinks
    all_blinks: dict[str, BlinkFile] = {}
    for dirname in ["relay", "active"]:
        for blink in env.scan(dirname):
            all_blinks[blink.blink_id] = blink

    # Find error blinks
    error_blinks = {
        bid: b for bid, b in all_blinks.items()
        if len(bid) >= 8 and bid[6:8] == "!!"
    }

    if not error_blinks:
        return []

    # Build chains: follow Born from links between error blinks
    visited: set[str] = set()
    chains: list[list[BlinkFile]] = []

    for bid, blink in error_blinks.items():
        if bid in visited:
            continue

        # Walk backwards to find chain root
        chain_ids = [bid]
        current = blink
        while True:
            parents = current.born_from
            if parents == ["Origin"] or not parents:
                break
            parent_id = parents[0]
            if parent_id in error_blinks and parent_id not in chain_ids:
                chain_ids.insert(0, parent_id)
                current = error_blinks[parent_id]
            else:
                break

        # Walk forward from root
        # (chain_ids already contains the backward walk)
        # Now check for forward links
        for bid2, blink2 in error_blinks.items():
            if bid2 in chain_ids:
                continue
            if blink2.born_from and blink2.born_from[0] in chain_ids:
                chain_ids.append(bid2)

        if len(chain_ids) >= 2:
            chain = [error_blinks[cid] for cid in chain_ids if cid in error_blinks]
            if len(chain) >= 2:
                chains.append(chain)
                visited.update(chain_ids)

    return chains
