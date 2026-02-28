"""Blink identifier parser, validator, and generator for BSS."""

from __future__ import annotations

from dataclasses import dataclass

from src.bss.sigils import (
    VALID_ACTION_COMPOUNDS,
    VALID_CHARS,
)

BLINK_ID_LENGTH = 17
BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class BlinkMetadata:
    """Parsed metadata from a 17-character blink identifier."""

    sequence: str           # Positions 1-5
    sequence_decimal: int   # Decimal value of the base-36 sequence
    author: str             # Position 6
    action_energy: str      # Position 7
    action_valence: str     # Position 8
    relational: str         # Position 9
    confidence: str         # Position 10
    cognitive: str          # Position 11
    domain: str             # Position 12
    subdomain: str          # Position 13
    scope: str              # Position 14
    maturity: str           # Position 15
    priority: str           # Position 16
    sensitivity: str        # Position 17


def base36_encode(n: int, width: int = 5) -> str:
    """Encode a non-negative integer to a zero-padded base-36 string."""
    if n < 0:
        raise ValueError("Cannot encode negative numbers")
    if n == 0:
        return "0" * width
    chars = []
    while n > 0:
        n, remainder = divmod(n, 36)
        chars.append(BASE36_CHARS[remainder])
    result = "".join(reversed(chars))
    return result.zfill(width)


def base36_decode(s: str) -> int:
    """Decode a base-36 string to an integer."""
    return int(s, 36)


def parse(blink_id: str) -> BlinkMetadata:
    """Parse a 17-character blink ID into its component fields.

    Raises ValueError if the blink ID is not exactly 17 characters.
    Does NOT validate sigil values — use validate() for that.
    """
    if len(blink_id) != BLINK_ID_LENGTH:
        raise ValueError(
            f"Blink ID must be exactly {BLINK_ID_LENGTH} characters, "
            f"got {len(blink_id)}"
        )

    sequence = blink_id[0:5]
    return BlinkMetadata(
        sequence=sequence,
        sequence_decimal=base36_decode(sequence),
        author=blink_id[5],
        action_energy=blink_id[6],
        action_valence=blink_id[7],
        relational=blink_id[8],
        confidence=blink_id[9],
        cognitive=blink_id[10],
        domain=blink_id[11],
        subdomain=blink_id[12],
        scope=blink_id[13],
        maturity=blink_id[14],
        priority=blink_id[15],
        sensitivity=blink_id[16],
    )


def validate(blink_id: str) -> tuple[bool, list[str]]:
    """Validate a blink identifier against the BSS grammar.

    Returns (is_valid, list_of_violations).
    """
    violations: list[str] = []

    # Rule 1: Exactly 17 characters
    if len(blink_id) != BLINK_ID_LENGTH:
        violations.append(
            f"Length must be exactly {BLINK_ID_LENGTH}, got {len(blink_id)}"
        )
        return False, violations

    # Rule 2: Positions 1-5 must be base-36 uppercase
    seq = blink_id[0:5]
    for i, ch in enumerate(seq):
        if ch not in VALID_CHARS["sequence"]:
            violations.append(
                f"Position {i + 1} (sequence): '{ch}' is not valid base-36 "
                f"(must be 0-9 or A-Z uppercase)"
            )

    # Check for reserved sequence 00000
    if seq == "00000":
        violations.append("Sequence 00000 is reserved and must not be used")

    # Rule 3: Position 6 must be a valid author
    author = blink_id[5]
    if author not in VALID_CHARS["author"]:
        violations.append(
            f"Position 6 (author): '{author}' is not valid (must be A-Z or 0-9)"
        )

    # Rule 4: Positions 7-8 must form a valid action state compound
    action = blink_id[6:8]
    if action not in VALID_ACTION_COMPOUNDS:
        violations.append(
            f"Positions 7-8 (action state): '{action}' is not a valid "
            f"action compound"
        )

    # Rule 5: Each remaining position must be in its valid set
    position_checks = [
        (8, "relational", "9"),
        (9, "confidence", "10"),
        (10, "cognitive", "11"),
        (11, "domain", "12"),
        (12, "subdomain", "13"),
        (13, "scope", "14"),
        (14, "maturity", "15"),
        (15, "priority", "16"),
        (16, "sensitivity", "17"),
    ]

    for idx, field_name, pos_label in position_checks:
        ch = blink_id[idx]
        if ch not in VALID_CHARS[field_name]:
            violations.append(
                f"Position {pos_label} ({field_name}): '{ch}' is not valid"
            )

    return len(violations) == 0, violations


def generate(
    sequence: int | str,
    author: str,
    action_energy: str = "~",
    action_valence: str = "~",
    relational: str = "+",
    confidence: str = ".",
    cognitive: str = "=",
    domain: str = "#",
    subdomain: str = ".",
    scope: str = "-",
    maturity: str = "~",
    priority: str = "=",
    sensitivity: str = "=",
) -> str:
    """Build a blink ID from keyword arguments.

    Args:
        sequence: Integer or 5-char base-36 string.
        author: Single character (A-Z or 0-9).
        All other args: single-character sigils with sensible defaults.

    Returns:
        A 17-character blink identifier string.

    Raises:
        ValueError: If the generated ID fails validation.
    """
    if isinstance(sequence, int):
        seq_str = base36_encode(sequence)
    else:
        seq_str = sequence.upper().zfill(5)

    blink_id = (
        seq_str
        + author
        + action_energy
        + action_valence
        + relational
        + confidence
        + cognitive
        + domain
        + subdomain
        + scope
        + maturity
        + priority
        + sensitivity
    )

    valid, violations = validate(blink_id)
    if not valid:
        raise ValueError(
            f"Generated invalid blink ID '{blink_id}': {', '.join(violations)}"
        )

    return blink_id


def next_sequence(current_highest: str) -> str:
    """Increment a base-36 sequence string by 1.

    Args:
        current_highest: The current highest 5-char base-36 sequence.

    Returns:
        The next sequence value as a 5-char base-36 string.

    Raises:
        ValueError: If the sequence space is exhausted (ZZZZZ).
    """
    current_val = base36_decode(current_highest)
    if current_val >= base36_decode("ZZZZZ"):
        raise ValueError("Sequence space exhausted (max ZZZZZ reached)")
    return base36_encode(current_val + 1)
