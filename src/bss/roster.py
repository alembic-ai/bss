"""BSS roster management — model registry in /profile/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.bss.blink_file import BlinkFile, read as read_blink, write as write_blink
from src.bss.environment import BSSEnvironment
from src.bss.identifier import generate, parse as parse_id

VALID_ROLES = {"primary", "reviewer", "specialist", "architect"}
VALID_CEILINGS = {"atomic", "local", "regional", "global"}

SCOPE_CEILING_RANK = {
    "atomic": 0,  # .
    "local": 1,   # -
    "regional": 2,  # =
    "global": 3,  # !
}

SCOPE_SIGIL_TO_CEILING = {
    ".": "atomic",
    "-": "local",
    "=": "regional",
    "!": "global",
}


@dataclass
class RosterEntry:
    """A single entry in the roster."""
    sigil: str
    model_id: str
    role: str
    scope_ceiling: str
    notes: str


@dataclass
class Roster:
    """The model registry for a BSS environment."""
    entries: list[RosterEntry]
    blink_id: str | None = None

    def get_entry(self, sigil: str) -> RosterEntry | None:
        """Get a roster entry by author sigil."""
        for entry in self.entries:
            if entry.sigil == sigil:
                return entry
        return None

    def get_scope_ceiling(self, author: str) -> str | None:
        """Get the scope ceiling for an author sigil."""
        entry = self.get_entry(author)
        return entry.scope_ceiling if entry else None


def read_roster(env: BSSEnvironment) -> Roster | None:
    """Find and parse the current roster blink in /profile/.

    Returns the most recent roster blink (highest sequence with 'S' author).
    """
    profile_blinks = env.scan("profile")

    # Find roster blinks (system-authored with ROSTER in summary)
    roster_blinks = []
    for blink in profile_blinks:
        try:
            meta = parse_id(blink.blink_id)
            if meta.author == "S" and "ROSTER" in blink.summary:
                roster_blinks.append(blink)
        except ValueError:
            continue

    if not roster_blinks:
        return None

    # Use the one with the highest sequence (most recent)
    roster_blinks.sort(
        key=lambda b: parse_id(b.blink_id).sequence_decimal,
        reverse=True,
    )
    roster_blink = roster_blinks[0]

    return _parse_roster(roster_blink)


def _parse_roster(blink: BlinkFile) -> Roster:
    """Parse a roster blink's summary into a Roster object."""
    entries: list[RosterEntry] = []
    lines = blink.summary.split("\n") if "\n" in blink.summary else blink.summary.split("  ")

    # Try to parse pipe-delimited roster entries
    # Format: SIGIL | model_id | role | scope_ceiling | notes
    for line in lines:
        line = line.strip()
        if not line or line == "ROSTER":
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            entry = RosterEntry(
                sigil=parts[0].strip(),
                model_id=parts[1].strip(),
                role=parts[2].strip(),
                scope_ceiling=parts[3].strip(),
                notes=parts[4].strip() if len(parts) > 4 else "",
            )
            entries.append(entry)

    return Roster(entries=entries, blink_id=blink.blink_id)


def update_roster(
    env: BSSEnvironment,
    new_entries: list[RosterEntry],
    old_roster_id: str | None = None,
) -> BlinkFile:
    """Write a new roster blink and archive the old one.

    Args:
        env: The BSS environment.
        new_entries: The updated roster entries.
        old_roster_id: Previous roster blink ID (moved to archive).

    Returns:
        The new roster BlinkFile.
    """
    seq = env.next_sequence()

    blink_id = generate(
        sequence=seq,
        author="S",
        action_energy="~",
        action_valence="~",
        relational="+" if old_roster_id else "^",
        confidence="!",
        cognitive="!",
        domain="^",  # System
        subdomain=";",  # Documenting
        scope="!",  # Global (affects all)
        maturity="!",  # Complete
        priority="=",
        sensitivity=".",
    )

    # Build roster summary
    roster_lines = ["ROSTER", ""]
    for entry in new_entries:
        roster_lines.append(
            f"{entry.sigil} | {entry.model_id} | {entry.role} | "
            f"{entry.scope_ceiling} | {entry.notes}"
        )

    summary = "\n".join(roster_lines)

    if old_roster_id:
        born_from = [old_roster_id]
        lineage = [old_roster_id, blink_id]
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

    write_blink(blink, env.profile_dir)

    # Move old roster to archive
    if old_roster_id:
        try:
            env.move_blink(old_roster_id, "archive")
        except FileNotFoundError:
            pass  # Old roster already moved or doesn't exist

    return blink


def check_scope_compliance(
    roster: Roster, author: str, blink: BlinkFile
) -> bool:
    """Check if a model is within its scope ceiling.

    Args:
        roster: The current roster.
        author: The author sigil to check.
        blink: The blink being written.

    Returns:
        True if the model is within its scope ceiling.
    """
    entry = roster.get_entry(author)
    if entry is None:
        return True  # Unknown author, no ceiling to enforce

    try:
        meta = parse_id(blink.blink_id)
    except ValueError:
        return True

    blink_scope = SCOPE_SIGIL_TO_CEILING.get(meta.scope)
    if blink_scope is None:
        return True

    ceiling_rank = SCOPE_CEILING_RANK.get(entry.scope_ceiling, 99)
    blink_rank = SCOPE_CEILING_RANK.get(blink_scope, 0)

    return blink_rank <= ceiling_rank
