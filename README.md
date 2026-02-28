# BSS — Blink Sigil System

A file-based coordination protocol for stateless AI models. Each "blink" is a Markdown file whose 17-character filename encodes structured metadata — author, action state, confidence, scope, and more — while the file body carries a natural-language summary and lineage graph. No database, no API, no shared memory. Just files.

## Install

```bash
pip install -e .
```

Requires Python 3.11+.

## Quickstart

```bash
# Initialize a BSS environment
bss init

# View environment status
bss status

# Decode a blink identifier
bss describe 00001U~~^!!^;!!=.

# Read a blink file
bss read 00001U~~^!!^;!!=.

# Write a new blink (interactive wizard)
bss write

# View the blink timeline
bss log

# View lineage tree for a blink
bss tree 00009A~~>!.^;!!=.

# Triage relay blinks by urgency
bss triage

# Validate a blink identifier
bss validate 00001U~~^!!^;!!=.

# View model roster
bss roster
```

## This Repo Built Itself

The `/archive/foundation/` directory contains the blinks written *during* the construction of this very implementation. Each level of the build — identifier engine, file engine, relay protocol, CLI — produced blinks that tracked decisions, breakthroughs, and bugs as they happened.

Start exploring:
- `bss read 00007A~~>!.^;!!=.` — How the identifier engine was built
- `bss read 00008A~~>!.^;!!=.` — How the relay protocol was implemented
- `bss read 00009A~~>!.^;!!=.` — How the CLI was designed

Trace the full lineage: `bss tree 00009A~~>!.^;!!=.`

## Directory Structure

```
bss/
├── relay/        # Handoff & error blinks between sessions
├── active/       # Current work blinks
├── profile/      # Model roster and identity blinks
├── archive/      # Completed work, organized by thread
│   └── foundation/  # The build archive that ships with this repo
├── artifacts/    # Files linked to blinks
└── bss_spec/     # Protocol specification
```

## Specification

The full BSS specification is in `bss_spec/BSS_SPEC_v3.0.md`. Key concepts:

- **17-character positional grammar** — Every blink ID encodes sequence, author, action state, relational type, confidence, cognitive state, domain, subdomain, scope, maturity, priority, and sensitivity
- **Four directories** — `/relay/`, `/active/`, `/profile/`, `/archive/`
- **Immutable blinks** — Never modified, renamed, or deleted
- **7-generation cap** — Threads converge after 7 continuations
- **Five-phase session lifecycle** — INTAKE, TRIAGE, WORK, OUTPUT, DORMANCY
- **Triage ordering** — Urgency, then recency, then scope

## License

Code: MIT
Specification: CC BY 4.0
