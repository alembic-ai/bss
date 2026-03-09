"""Blink file creation, reading, parsing, and validation for BSS."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from src.bss.identifier import BLINK_ID_LENGTH, validate as validate_id

# The arrow separator required in Lineage fields
LINEAGE_SEPARATOR = " \u2192 "  # → (U+2192)
# The pipe separator for Born from / Links
PIPE_SEPARATOR = " | "

# Blink ID pattern: 17 characters of allowed sigil chars
BLINK_ID_PATTERN = re.compile(
    r"^[0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z][0-9A-Z]"
    r"[A-Z0-9]"
    r"[!.~][!.~#]"
    r"[\^}{#=_+]"
    r"[!.~,]"
    r"[!~\^%=#.&]"
    r"[@#$&!~%\^+;]"
    r"[!~\^.=&\-+;,]"
    r"[.\-=!]"
    r"[,~.!\-]"
    r"[!\^=.~]"
    r"[!\^=.]$"
)

MAX_FILE_SIZE = 2000
WARN_FILE_SIZE = 1000
MAX_SUMMARY_SENTENCES = 5
MIN_SUMMARY_SENTENCES = 2
MAX_LINEAGE_DEPTH = 7


@dataclass
class BlinkFile:
    """Represents a complete blink file (identifier + content)."""

    blink_id: str
    born_from: list[str]  # List of parent blink IDs, or ["Origin"]
    summary: str
    lineage: list[str]  # Ordered list of ancestor IDs including self
    links: list[str] = field(default_factory=list)

    @property
    def is_origin(self) -> bool:
        return self.born_from == ["Origin"]


def _count_sentences(text: str) -> int:
    """Count sentences in text using a heuristic.

    Splits on sentence-ending punctuation followed by whitespace or end of string,
    excluding common abbreviations and version numbers.
    """
    text = text.strip()
    if not text:
        return 0
    # Replace common abbreviations to avoid false splits
    _abbrevs = r'(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|etc|e\.g|i\.e|v\d)'
    # Split on . ! ? followed by whitespace, but not after abbreviations
    cleaned = re.sub(_abbrevs + r'\.', lambda m: m.group().replace('.', '\x00'), text)
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    # Filter out empty strings
    sentences = [s for s in sentences if s.strip()]
    return len(sentences)


def _contains_blink_id(text: str) -> bool:
    """Check if text contains what looks like a blink identifier.

    A blink ID is exactly 17 characters of the sigil alphabet.
    We look for sequences that match the general shape.
    """
    # Look for 5 base-36 chars followed by specific sigil patterns
    pattern = re.compile(
        r'[0-9A-Z]{5}[A-Z0-9][!.~][!.~#][\^}{#=_+][!.~,][!~\^%=#.&]'
        r'[@#$&!~%\^+;][!~\^.=&\-+;,][.\-=!][,~.!\-][!\^=.~][!\^=.]'
    )
    return bool(pattern.search(text))


def write(
    blink: BlinkFile,
    directory: Path,
    min_sentences: int = MIN_SUMMARY_SENTENCES,
) -> Path:
    """Write a conformant blink .md file to the specified directory.

    Args:
        blink: The BlinkFile to write.
        directory: The directory to write to.
        min_sentences: Minimum sentence count for validation. Defaults to 2
            per spec. Relay mode may pass 1.

    Returns:
        The path to the written file.

    Raises:
        ValueError: If the blink fails validation.
    """
    valid, violations = validate_file(blink, min_sentences=min_sentences)
    if not valid:
        raise ValueError(f"Invalid blink file: {'; '.join(violations)}")

    content = _render(blink)

    # Size checks
    content_size = len(content.encode("utf-8"))
    if content_size > MAX_FILE_SIZE:
        raise ValueError(
            f"Blink file exceeds maximum size ({content_size} > {MAX_FILE_SIZE} bytes)"
        )

    filepath = directory / f"{blink.blink_id}.md"
    if filepath.exists():
        raise FileExistsError(
            f"Blink '{blink.blink_id}' already exists at {filepath}. "
            "Blinks are immutable and cannot be overwritten."
        )
    filepath.write_text(content, encoding="utf-8")

    # Set restrictive permissions (owner rw, group/others read-only)
    # Skip on Windows where os.chmod only controls read-only flag
    if sys.platform != "win32":
        os.chmod(filepath, 0o644)

    return filepath


def _render(blink: BlinkFile) -> str:
    """Render a BlinkFile to its Markdown string representation."""
    lines = []

    # Born from
    if blink.is_origin:
        lines.append("Born from: Origin")
    else:
        lines.append(f"Born from: {PIPE_SEPARATOR.join(blink.born_from)}")

    lines.append("")

    # Summary
    lines.append(blink.summary.strip())

    lines.append("")

    # Lineage
    lines.append(f"Lineage: {LINEAGE_SEPARATOR.join(blink.lineage)}")

    lines.append("")

    # Links
    if blink.links:
        lines.append(f"Links: {PIPE_SEPARATOR.join(blink.links)}")
    else:
        lines.append("Links:")

    lines.append("")  # trailing newline
    return "\n".join(lines)


def read(filepath: Path) -> BlinkFile:
    """Parse an existing blink file back into a BlinkFile dataclass.

    Args:
        filepath: Path to the .md blink file.

    Returns:
        A BlinkFile populated from the file.

    Raises:
        ValueError: If the file cannot be parsed.
    """
    # Can't use Path.stem because it strips the last "." which may be
    # a sigil character. Instead, strip exactly ".md" from the filename.
    name = filepath.name
    if name.endswith(".md"):
        blink_id = name[:-3]
    else:
        blink_id = name
    # Guard against oversized files (DoS prevention)
    try:
        file_size = filepath.stat().st_size
    except OSError as e:
        raise ValueError(f"Cannot stat blink file {filepath}: {e}")
    if file_size > MAX_FILE_SIZE:
        raise ValueError(
            f"Blink file {filepath.name} exceeds maximum size "
            f"({file_size} > {MAX_FILE_SIZE} bytes)"
        )

    content = filepath.read_text(encoding="utf-8")

    return parse_content(blink_id, content)


def parse_content(blink_id: str, content: str) -> BlinkFile:
    """Parse blink file content into a BlinkFile dataclass.

    Args:
        blink_id: The blink identifier (filename without .md).
        content: The raw file content.

    Returns:
        A BlinkFile populated from the content.
    """
    lines = content.strip().split("\n")

    born_from: list[str] = []
    summary_lines: list[str] = []
    lineage: list[str] = []
    links: list[str] = []

    section = "start"

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Born from:"):
            value = stripped[len("Born from:"):].strip()
            if value == "Origin":
                born_from = ["Origin"]
            else:
                # Parse pipe-separated IDs, tolerating whitespace
                born_from = [bid.strip() for bid in value.split("|") if bid.strip()]
            section = "after_born_from"

        elif stripped.startswith("Lineage:"):
            value = stripped[len("Lineage:"):].strip()
            # Parse arrow-separated IDs
            lineage = [lid.strip() for lid in value.split("\u2192") if lid.strip()]
            section = "after_lineage"

        elif stripped.startswith("Links:"):
            value = stripped[len("Links:"):].strip()
            if value:
                links = [lid.strip() for lid in value.split("|") if lid.strip()]
            section = "after_links"

        elif section == "after_born_from" or section == "summary":
            # Include all lines in summary region (empty or not)
            # until we hit Lineage:
            summary_lines.append(stripped)
            section = "summary"

    # Trim leading/trailing empty lines from summary, preserve internal structure
    while summary_lines and not summary_lines[0]:
        summary_lines.pop(0)
    while summary_lines and not summary_lines[-1]:
        summary_lines.pop()

    summary = "\n".join(summary_lines)

    return BlinkFile(
        blink_id=blink_id,
        born_from=born_from,
        summary=summary,
        lineage=lineage,
        links=links,
    )


def validate_file(
    blink: BlinkFile,
    min_sentences: int = MIN_SUMMARY_SENTENCES,
) -> tuple[bool, list[str]]:
    """Validate a BlinkFile against the BSS file format specification.

    Args:
        blink: The BlinkFile to validate.
        min_sentences: Minimum sentence count for summaries. Defaults to
            MIN_SUMMARY_SENTENCES (2) per spec Module 4. Relay mode may
            pass 1 to accommodate terse model outputs.

    Returns (is_valid, list_of_violations).
    """
    violations: list[str] = []

    # Validate blink ID
    id_valid, id_violations = validate_id(blink.blink_id)
    if not id_valid:
        violations.extend(f"Blink ID: {v}" for v in id_violations)

    # Check Born from
    if not blink.born_from:
        violations.append("Born from field is required")
    elif blink.born_from != ["Origin"]:
        for parent in blink.born_from:
            if len(parent) != BLINK_ID_LENGTH:
                violations.append(
                    f"Born from contains invalid blink ID '{parent}' "
                    f"(length {len(parent)}, expected {BLINK_ID_LENGTH})"
                )
            else:
                parent_valid, parent_violations = validate_id(parent)
                if not parent_valid:
                    violations.append(
                        f"Born from contains malformed blink ID '{parent}': "
                        f"{'; '.join(parent_violations)}"
                    )

    # Check relational / born_from consistency
    is_roster = False
    from src.bss.identifier import parse as parse_id
    try:
        meta = parse_id(blink.blink_id)
        is_roster = meta.author == "S"
        if meta.relational == "^" and blink.born_from != ["Origin"]:
            violations.append(
                "Origin blink (relational '^') must have Born from: Origin"
            )
        if blink.born_from == ["Origin"] and meta.relational != "^":
            violations.append(
                "Origin blink (Born from: Origin) must have relational '^'"
            )
        # Note: convergence blinks SHOULD have multiple parents per Section 3.3,
        # but forced convergence from generation cap (Section 5.7) MAY have
        # a single parent (the gen-7 blink). This is not a hard violation.
    except ValueError:
        pass  # Already caught by ID validation

    # Check summary
    # Roster blinks have semi-structured summaries (Section 5.6) —
    # exempt them from sentence count validation.
    if not blink.summary or not blink.summary.strip():
        violations.append("Summary is required")
    elif not is_roster:
        sentence_count = _count_sentences(blink.summary)
        if sentence_count < min_sentences:
            violations.append(
                f"Summary has {sentence_count} sentence(s), "
                f"minimum is {min_sentences}"
            )
        if sentence_count > MAX_SUMMARY_SENTENCES:
            violations.append(
                f"Summary has {sentence_count} sentence(s), "
                f"maximum is {MAX_SUMMARY_SENTENCES}"
            )

        # Layer separation: no blink IDs in summary
        if _contains_blink_id(blink.summary):
            violations.append(
                "Summary must not contain blink identifiers "
                "(layer separation violation)"
            )

    # Check lineage
    if not blink.lineage:
        violations.append("Lineage is required")
    else:
        if blink.lineage[-1] != blink.blink_id:
            violations.append(
                "Lineage must end with this blink's own ID"
            )
        if len(blink.lineage) > MAX_LINEAGE_DEPTH:
            violations.append(
                f"Lineage depth {len(blink.lineage)} exceeds maximum "
                f"of {MAX_LINEAGE_DEPTH}"
            )
        if blink.is_origin and blink.lineage != [blink.blink_id]:
            violations.append(
                "Origin blink lineage must be self-reference only"
            )
        # Check for duplicate entries (circular lineage)
        if len(blink.lineage) != len(set(blink.lineage)):
            violations.append(
                "Lineage contains duplicate entries (circular reference)"
            )

    # Check file size
    rendered = _render(blink)
    size = len(rendered.encode("utf-8"))
    if size > MAX_FILE_SIZE:
        violations.append(
            f"File size {size} bytes exceeds maximum of {MAX_FILE_SIZE}"
        )

    return len(violations) == 0, violations
