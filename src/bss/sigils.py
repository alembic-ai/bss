"""Sigil lookup tables and human-readable descriptions for BSS."""

from __future__ import annotations

# Position 7-8: Action State compounds (energy + valence)
ACTION_STATES: dict[str, str] = {
    "~~": "Idle",
    "~!": "Handoff",
    "~.": "Completed",
    "!~": "Blocked",
    "!!": "Error",
    "!.": "Decision needed",
    ".!": "In progress",
    "..": "Informational",
    ".~": "Awaiting user input",
    "!#": "Cancelled",
}

VALID_ACTION_COMPOUNDS: frozenset[str] = frozenset(ACTION_STATES.keys())

# Position 7: Action Energy
ACTION_ENERGY: dict[str, str] = {
    "!": "Urgency / energy / problem",
    ".": "Stillness / completion / progress",
    "~": "Neutrality / passivity / waiting",
}

# Position 8: Action Valence
ACTION_VALENCE: dict[str, str] = {
    "!": "Urgency",
    ".": "Completion",
    "~": "Neutrality",
    "#": "Cancellation",
}

# Position 9: Relational Role
RELATIONAL: dict[str, str] = {
    "^": "Origin / seed",
    ">": "Branch / divergence",
    "<": "Convergence / synthesis",
    "#": "Contradiction / conflict",
    "=": "Reinforcement / echo",
    "_": "Dead end / dormant",
    "+": "Continuation",
}

# Position 10: Confidence
CONFIDENCE: dict[str, str] = {
    "!": "High",
    ".": "Moderate",
    "~": "Low",
    ",": "Speculative",
}

# Position 11: Cognitive State
COGNITIVE: dict[str, str] = {
    "!": "Clarity / insight",
    "~": "Confusion / fog",
    "^": "Breakthrough",
    "%": "Frustration / resistance",
    "=": "Flow / momentum",
    "#": "Tension / unresolved",
    ".": "Resolution / closure",
    "&": "Curiosity / opening",
}

# Position 12: Domain
DOMAIN: dict[str, str] = {
    "@": "Self / identity",
    "#": "Work / craft",
    "$": "Finance / resources",
    "&": "Relationships",
    "!": "Creation / building",
    "~": "Learning / discovery",
    "%": "Health / body",
    "^": "System / meta",
    "+": "Play / joy",
    ";": "Conflict / tension",
}

# Position 13: Subdomain
SUBDOMAIN: dict[str, str] = {
    "!": "Making / producing / building",
    "~": "Exploring / researching / learning",
    "^": "Designing / planning / strategizing",
    ".": "Maintaining / sustaining / managing",
    "=": "Communicating / exchanging / sharing",
    "&": "Analyzing / evaluating / reviewing",
    "-": "Fixing / resolving / repairing",
    "+": "Growing / developing / improving",
    ";": "Documenting / recording / logging",
    ",": "Deciding / choosing / committing",
}

# Position 14: Scope
SCOPE: dict[str, str] = {
    ".": "Atomic",
    "-": "Local",
    "=": "Regional",
    "!": "Global",
}

# Position 15: Maturity
MATURITY: dict[str, str] = {
    ",": "Seed",
    "~": "In progress",
    ".": "Near complete",
    "!": "Complete / stable",
    "-": "Needs revision",
}

# Position 16: Priority
PRIORITY: dict[str, str] = {
    "!": "Critical",
    "^": "High",
    "=": "Normal",
    ".": "Low",
    "~": "Background",
}

# Position 17: Time Sensitivity
SENSITIVITY: dict[str, str] = {
    "!": "Blocking",
    "^": "Soon",
    "=": "Whenever",
    ".": "Passive",
}

# Valid character sets per position
VALID_CHARS: dict[str, set[str]] = {
    "sequence": set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    "author": set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    "energy": set(ACTION_ENERGY.keys()),
    "valence": set(ACTION_VALENCE.keys()),
    "relational": set(RELATIONAL.keys()),
    "confidence": set(CONFIDENCE.keys()),
    "cognitive": set(COGNITIVE.keys()),
    "domain": set(DOMAIN.keys()),
    "subdomain": set(SUBDOMAIN.keys()),
    "scope": set(SCOPE.keys()),
    "maturity": set(MATURITY.keys()),
    "priority": set(PRIORITY.keys()),
    "sensitivity": set(SENSITIVITY.keys()),
}

# All sigil maps keyed by position name for programmatic access
SIGIL_MAPS: dict[str, dict[str, str]] = {
    "action_state": ACTION_STATES,
    "energy": ACTION_ENERGY,
    "valence": ACTION_VALENCE,
    "relational": RELATIONAL,
    "confidence": CONFIDENCE,
    "cognitive": COGNITIVE,
    "domain": DOMAIN,
    "subdomain": SUBDOMAIN,
    "scope": SCOPE,
    "maturity": MATURITY,
    "priority": PRIORITY,
    "sensitivity": SENSITIVITY,
}


def describe(blink_id: str) -> str:
    """Produce a plain-English reading of a blink ID.

    Returns a multi-line human-readable breakdown of each position,
    similar to the annotated example in Section 3.4 of the spec.
    """
    from src.bss.identifier import parse, validate

    valid, violations = validate(blink_id)
    if not valid:
        return f"Invalid blink ID: {', '.join(violations)}"

    meta = parse(blink_id)
    action_compound = meta.action_energy + meta.action_valence
    urgency_compound = meta.priority + meta.sensitivity

    lines = [
        f"Blink ID: {blink_id}",
        "",
        f"  Sequence:    {meta.sequence} ({meta.sequence_decimal} in decimal)",
        f"  Author:      {meta.author}",
        f"  Action:      {action_compound} ({ACTION_STATES.get(action_compound, 'Unknown')})",
        f"  Relational:  {meta.relational} ({RELATIONAL.get(meta.relational, 'Unknown')})",
        f"  Confidence:  {meta.confidence} ({CONFIDENCE.get(meta.confidence, 'Unknown')})",
        f"  Cognitive:   {meta.cognitive} ({COGNITIVE.get(meta.cognitive, 'Unknown')})",
        f"  Domain:      {meta.domain} ({DOMAIN.get(meta.domain, 'Unknown')})",
        f"  Subdomain:   {meta.subdomain} ({SUBDOMAIN.get(meta.subdomain, 'Unknown')})",
        f"  Scope:       {meta.scope} ({SCOPE.get(meta.scope, 'Unknown')})",
        f"  Maturity:    {meta.maturity} ({MATURITY.get(meta.maturity, 'Unknown')})",
        f"  Priority:    {meta.priority} ({PRIORITY.get(meta.priority, 'Unknown')})",
        f"  Sensitivity: {meta.sensitivity} ({SENSITIVITY.get(meta.sensitivity, 'Unknown')})",
    ]
    return "\n".join(lines)
