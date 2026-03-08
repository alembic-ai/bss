# BSS v1 Build Plan — The Protocol That Built Itself

## Overview

Build the BSS reference implementation, a CLI onboarding tool, and dogfood the entire process through BSS itself — producing a foundation archive that ships with the open-source repo.

Each level builds on the last. Don't skip ahead. The blinks you write along the way ARE the product.

---

## LEVEL 0 — GROUND ZERO

**Goal:** Bootstrap the BSS environment that will track its own creation.

### Tasks

0.1 — Create the repo structure:

```
bss/
├── bss_spec/
│   ├── BSS_SPEC_v1.md
│   └── MODULE_8_TESTS.md
├── src/
│   └── bss/
│       └── __init__.py
├── tests/
│   └── __init__.py
├── cli/
│   └── __init__.py
├── relay/
├── active/
├── profile/
├── archive/
│   └── foundation/
├── CLAUDE.md
├── pyproject.toml
├── README.md
└── .gitignore
```

0.2 — Write your CLAUDE.md for the build agent sessions:

```markdown
# BSS Reference Implementation

You are building the reference implementation of the Blink Sigil System.
Read bss_spec/BSS_SPEC_v1.md for the full protocol specification.
Read bss_spec/MODULE_8_TESTS.md for canonical test cases.

## Key Rules
- Blink identifiers are EXACTLY 17 characters. See Module 3.
- 4 directories: /relay/, /active/, /profile/, /archive/
- Blinks are immutable. Never modify, rename, or delete.
- Test with pytest. All Module 8 tests must pass per compliance level.
- Python 3.11+. Minimal external dependencies for core protocol.
- You ARE a BSS relay member. Write blinks to track your own work.

## Your BSS Identity
- Author sigil: A (primary relay member)
- Role: primary
- Scope ceiling: global
- Read /relay/ at session start. Write a handoff blink at session end.
```

0.3 — Hand-write the first two blinks:

**Origin blink** → `/active/00001U~~^!!^;!,=.md`

```markdown
Born from: Origin

The Blink Sigil System reference implementation begins here. This is the
foundation of a protocol that will build itself — every decision, breakthrough,
and dead end recorded in the blinks that emerge during development. The goal is
a working Python implementation with CLI tooling, tested against the canonical
Module 8 test suite, with the build process itself as the first real-world
BSS archive.

Lineage: 00001U~~^!!^;!,=.

Links:
```

Reading: Blink 1, User-authored, idle, origin, high confidence, clarity, system + documenting, global scope, seed maturity, normal + passive urgency.

**Roster blink** → `/profile/00002S~~^!!^;.!=.md`

```markdown
Born from: Origin

ROSTER

A | Agent-A | primary | global | Reference implementation build agent. Full autonomy. Writes blinks at session boundaries.
U | Architect | architect | global | Protocol designer. Reviews, directs, and makes final calls on spec interpretation.

Lineage: 00002S~~^!!^;.!=.

Links: 00001U~~^!!^;!,=.
```

0.4 — `git init`, first commit: "Origin — BSS bootstraps itself"

**Level 0 is complete when:** The repo exists, CLAUDE.md is written, two foundation blinks exist, and git has its first commit.

---

## LEVEL 1 — THE IDENTIFIER ENGINE

**Goal:** Build the blink ID parser, validator, and generator. This is the heart of BSS.

### Tasks

1.1 — `src/bss/identifier.py` — The blink ID module:

- `parse(blink_id: str) -> BlinkMetadata` — Takes a 17-char string, returns a dataclass with every field decoded (sequence, author, action_energy, action_valence, relational, confidence, cognitive, domain, subdomain, scope, maturity, priority, sensitivity).
- `validate(blink_id: str) -> tuple[bool, list[str]]` — Returns validity and a list of specific violations if invalid.
- `generate(**kwargs) -> str` — Builds a blink ID from keyword arguments. Requires sequence and author at minimum. Defaults for everything else (idle, continuation, moderate confidence, flow, work+maintain, local, in-progress, normal+whenever).
- `next_sequence(current_highest: str) -> str` — Increments a base-36 sequence string.
- `base36_encode(n: int) -> str` and `base36_decode(s: str) -> int` — Utility functions.

1.2 — `src/bss/sigils.py` — Sigil lookup tables:

- Every sigil map from the spec as Python dictionaries.
- The 10 valid action state compounds as a frozen set.
- Human-readable labels for all sigils.
- `describe(blink_id: str) -> str` — Produces a plain-English reading of a blink ID (like the annotated example in Section 3.4 of the spec).

1.3 — `tests/test_identifier.py` — Module 8.1 validation tests:

- All four VALID test cases from the spec must parse without error.
- All five INVALID test cases must be rejected with correct violation messages.
- Additional edge cases: sequence 00000 rejected, sequence ZZZZZ accepted, all 10 action compounds accepted individually, all invalid compounds rejected.

1.4 — Write a blink capturing this level's completion.

**Level 1 is complete when:** `pytest tests/test_identifier.py` passes 100%. The parser handles every valid sigil combination and rejects every invalid one.

---

## LEVEL 2 — THE FILE ENGINE

**Goal:** Build blink file creation, reading, parsing, and validation.

### Tasks

2.1 — `src/bss/blink_file.py` — File I/O module:

- `BlinkFile` dataclass: `blink_id`, `born_from` (list of IDs or "Origin"), `summary` (str), `lineage` (list of IDs), `links` (list of IDs, optional).
- `write(blink: BlinkFile, directory: Path)` — Writes a conformant .md file. Enforces: UTF-8 encoding, `→` separator in lineage, `|` separator in born_from and links, summary length 2-5 sentences, total file size under 2000 chars (warn at 1000).
- `read(filepath: Path) -> BlinkFile` — Parses an existing blink file back into the dataclass.
- `validate_file(blink: BlinkFile) -> tuple[bool, list[str]]` — Checks layer separation (no blink IDs in summary, no prose in structural fields), sentence count, size limits, lineage depth ≤ 7.

2.2 — `src/bss/environment.py` — BSS environment manager:

- `BSSEnvironment(root: Path)` — Wraps a BSS directory structure.
- `init(root: Path)` — Creates the four required directories.
- `scan(directory: str) -> list[BlinkFile]` — Lists and parses all blinks in a directory.
- `triage(directory: str) -> list[BlinkFile]` — Returns blinks sorted by triage order (urgency → recency → scope).
- `highest_sequence() -> str` — Scans all directories for the current highest sequence number.
- `find_blink(blink_id: str) -> Path | None` — Searches all directories (including archive subdirectories) for a blink.
- `move_blink(blink_id: str, to_directory: str)` — Moves a blink between directories. Enforces immutability (filename and content unchanged).
- `check_immutability(blink_id: str)` — Verifies a blink hasn't been tampered with (hash check on first read vs current).

2.3 — `tests/test_blink_file.py` — File format tests:

- Round-trip test: write a blink, read it back, verify all fields match.
- Layer separation enforcement: summary containing a blink ID is rejected.
- Size constraint warnings and hard limits.
- Lineage depth truncation at 7.
- Born from "Origin" for origin blinks.
- Multi-parent born_from with pipe separator for convergence blinks.

2.4 — `tests/test_environment.py` — Environment tests:

- `init` creates all four directories.
- `highest_sequence` correctly scans across all directories.
- `find_blink` resolves across directories including archive subdirectories.
- `move_blink` preserves filename and content.
- Triage ordering matches Module 8.2.3-8.2.5 test cases.

2.5 — Write a blink capturing this level's completion.

**Level 2 is complete when:** You can programmatically create a BSS environment, write blinks to it, read them back, validate them, triage them, and move them between directories. All file format tests pass.

---

## LEVEL 3 — THE RELAY ENGINE

**Goal:** Implement the session lifecycle, handoff protocol, error escalation, and generation management.

### Tasks

3.1 — `src/bss/relay.py` — Relay protocol module:

- `Session` class implementing the five-phase lifecycle: INTAKE → TRIAGE → WORK → OUTPUT → DORMANCY.
- `intake(env: BSSEnvironment) -> SessionContext` — Executes the startup sequence (relay → active → profile), returns a context object with triaged state.
- `handoff(env: BSSEnvironment, summary: str, **sigil_kwargs) -> BlinkFile` — Writes a properly formed handoff blink to /relay/ with action state ~!.
- `error_blink(env: BSSEnvironment, summary: str, parent: str | None, confidence: str) -> BlinkFile` — Writes an error blink to /relay/ with action state !!. If parent is provided, chains as escalation.
- `check_escalation(env: BSSEnvironment) -> list[list[BlinkFile]]` — Finds chains of 2+ linked error blinks without intervening resolution. Returns the chains for alerting.

3.2 — `src/bss/generations.py` — Generation tracking and convergence:

- `get_generation(env: BSSEnvironment, blink_id: str) -> int` — Walks the Born from chain to determine which generation a blink is in (1-7).
- `needs_convergence(env: BSSEnvironment, blink_id: str) -> bool` — Returns True if the blink is generation 7 and the next write must converge.
- `converge(env: BSSEnvironment, chain: list[BlinkFile], summary: str) -> BlinkFile` — Writes a convergence blink (relational {) synthesizing the chain. Resets generation to 1. Moves key references to Links.

3.3 — `src/bss/roster.py` — Roster management:

- `Roster` dataclass with entries: sigil, model_id, role, scope_ceiling, notes.
- `read_roster(env: BSSEnvironment) -> Roster` — Finds and parses the current roster blink in /profile/.
- `update_roster(env: BSSEnvironment, new_entries: list[RosterEntry]) -> BlinkFile` — Writes a new roster blink, moves the old one to /archive/.
- `get_scope_ceiling(roster: Roster, author: str) -> str` — Returns the scope ceiling for a given author sigil.
- `check_scope_compliance(roster: Roster, author: str, blink: BlinkFile) -> bool` — Validates that a model isn't exceeding its scope ceiling.

3.4 — `tests/test_relay.py` — Module 8.2 relay tests:

- All 17 test cases from the relay test suite.
- Startup sequence order verification.
- Handoff write location and format.
- Triage ordering across all three tiebreaker levels.
- Relay hygiene (session output limit, backlog warning).
- Error escalation chain detection.
- Generation cap enforcement and convergence.

3.5 — `tests/test_graph.py` — Module 8.3 graph tests:

- All 21 test cases from the graph test suite.
- Born from variants (single, multi, origin).
- Lineage accuracy and truncation.
- Cross-directory link resolution.
- Broken link handling.
- Participation tier enforcement.
- Roster CRUD and immutability.
- Scope ceiling enforcement.
- Dormant reactivation.
- Immutability (reject rename, reject edit, permit move).

3.6 — Write a blink capturing this level's completion.

**Level 3 is complete when:** All Module 8.2 and 8.3 tests pass. The relay engine can manage a full session lifecycle, handle errors, enforce generation caps, and manage the roster. BSS Relay and BSS Graph compliance achieved.

---

## LEVEL 4 — THE CLI

**Goal:** Build an onboarding CLI that makes BSS accessible. A new user should go from zero to a working BSS environment in under 2 minutes.

### Tasks

4.1 — `cli/main.py` — CLI entry point using `click` or `typer`:

```
bss init            — Initialize a new BSS environment
bss status          — Show current environment state
bss read <id>       — Read and display a blink
bss write           — Interactive blink creation wizard
bss triage          — Show triaged relay queue
bss log             — Show recent blinks in sequence order
bss describe <id>   — Plain-English blink ID breakdown
bss validate <id>   — Validate a blink ID with violation report
bss roster          — Display current roster
bss tree <id>       — Show lineage tree for a blink
```

4.2 — `bss init` — The onboarding command:

Interactive setup flow:
```
$ bss init

  ╔══════════════════════════════════════╗
  ║   BLINK SIGIL SYSTEM — v1.0         ║
  ║   Alembic AI                        ║
  ╚══════════════════════════════════════╝

  Initializing BSS environment...

  → Created /relay/
  → Created /active/
  → Created /profile/
  → Created /archive/

  Let's set up your roster.

  How many AI models will participate? [1]: 2

  Model 1:
    Name/identifier: Claude-Sonnet
    Author sigil [A]: A
    Role (primary/reviewer/specialist/architect) [primary]: primary
    Scope ceiling (atomic/local/regional/global) [global]: global
    Notes (optional): General purpose relay lead.

  Model 2:
    Name/identifier: Llama-3.1-70B
    Author sigil [B]: B
    Role [reviewer]: specialist
    Scope ceiling [local]: regional
    Notes: Code generation and structured output.

  → Wrote roster blink to /profile/
  → Wrote origin blink to /active/

  Environment ready. 2 blinks written.
  Run `bss status` to see your environment.
```

4.3 — `bss status` — Environment dashboard:

```
$ bss status

  BSS Environment: /home/cam/projects/my-project
  Spec version: 1.0
  Total blinks: 47

  /relay/   3 blinks  (1 handoff, 1 error, 1 blocked)
  /active/  28 blinks
  /profile/ 4 blinks
  /archive/ 12 blinks

  Next sequence: 00030
  Active threads: 4
  Error chains needing attention: 1

  Latest blink: 0002FA~!}!^#!=~^=
    → Handoff from Model A | Work + Making | High priority
```

4.4 — `bss write` — Interactive blink creation:

Guided wizard that walks through each sigil position with human-readable prompts. No need to memorize the grammar:

```
$ bss write

  Author: You (U) or model? [U]:
  What is this blink about?
    1. Handoff to next model (~!)
    2. Work in progress (.!)
    3. Completed work (~.)
    4. Error (!!)
    5. Information (..)
    ...
  Select [1]: 2

  Relationship to existing work?
    1. New thread (origin)
    2. Continuing existing thread
    3. Branching from existing thread
    4. Merging threads
    ...
  Select [2]: 2
  Parent blink ID: 00015A.!+!=#;!~^=

  [continues through confidence, cognitive, domain, etc.]

  Preview:
    ID: 00030U.!+!=#!=~^=
    Reading: Blink 108, User, in progress, continuation, high confidence,
             clarity, work + making, regional scope, in progress, high + whenever

  Summary (2-5 sentences):
  > Implemented the CLI scaffolding with typer. All core commands are stubbed...

  Write this blink? [Y/n]: Y
  → Written to /active/00030U.!+!=#!=~^=.md
```

4.5 — `bss triage` — Relay queue viewer:

```
$ bss triage

  /relay/ — 3 blinks (triage order):

  1. !! 00028A!!+~%#-=-!!  ERROR | Critical + Blocking
     → "Parser failed on edge case with consecutive special chars..."

  2. ~! 0002FA~!}!^#!=~!^ HANDOFF | Critical + Soon
     → "Validator complete, needs integration with file writer..."

  3. ~! 00025B~!+.=#~=.^= HANDOFF | High + Whenever
     → "Roster reader working but needs multi-roster history support..."
```

4.6 — `bss describe` — Human-readable blink breakdown:

```
$ bss describe 0002FA~!}!^#!=~^=

  Blink ID: 0002FA~!}!^#!=~^=

  Sequence:    0002F (87 in decimal)
  Author:      A (Model A)
  Action:      ~! (Handoff — pick this up)
  Relational:  } (Branch — new thread from existing parent)
  Confidence:  ! (High)
  Cognitive:   ^ (Breakthrough)
  Domain:      # (Work)
  Subdomain:   ! (Making / producing)
  Scope:       = (Regional)
  Maturity:    ~ (In progress)
  Priority:    ^ (High)
  Sensitivity: = (Whenever)

  Plain English: Model A is handing off a branching work thread.
  It had a breakthrough, is highly confident, and the work is
  regional in scope, still in progress. High priority, no hard deadline.
```

4.7 — `bss log` — Sequence timeline:

```
$ bss log --last 5

  00030  U  .!  +  /active/   Work + Making      "Implemented CLI scaffolding..."
  0002F  A  ~!  }  /relay/    Work + Making       "Validator complete, needs..."
  0002E  A  .!  +  /active/   Work + Fixing       "Fixed edge case in base36..."
  0002D  B  ~.  +  /archive/  Learning + Explore  "Research on click vs typer..."
  0002C  A  !!  +  /relay/    Work + Fixing        "Parser failed on consec..."
```

4.8 — `bss tree` — Lineage visualization:

```
$ bss tree 00030U.!+!=#!=~^=

  00001U~~^!!^;!,=.  (Origin — project bootstrap)
    └─+ 00005A.!+!=#!-,^=  (Identifier module started)
      └─+ 0000AA.!+!=#!-~~=  (Parser core logic)
        ├─} 0000FA~!}!^#!=~^=  (Validator branched off)
        └─+ 00015A.!+!=#!=~~=  (Generator added)
          └─+ 00020A.!+!=#!=~^=  (CLI integration)
            └─+ 00030U.!+!=#!=~^=  ← YOU ARE HERE
```

4.9 — Package configuration:

- `pyproject.toml` with `[project.scripts]` entry: `bss = "cli.main:app"`
- `pip install -e .` for local development
- Minimal dependencies: `typer`, `rich` (for terminal formatting)

4.10 — Write a blink capturing this level's completion.

**Level 4 is complete when:** `bss init` creates a fully functional environment with interactive roster setup. All commands work against a real BSS environment. A new user can go from `pip install` to a populated BSS environment in under 2 minutes.

---

## LEVEL 5 — INTEGRATION & POLISH

**Goal:** Wire everything together, harden edge cases, and prepare for release.

### Tasks

5.1 — End-to-end integration tests:

- `tests/test_integration.py` — Full workflow test: init environment → write origin → write 7 continuations → force convergence → verify archive → validate entire graph.
- Simulate a 3-model relay: Model A writes handoff → Model B picks up → Model B writes error → Model A receives escalation → resolution blink written.
- Broken link recovery, metadata-content contradiction handling, oversized relay backlog.

5.2 — Edge case hardening:

- Empty environment cold start (Module 5.9).
- Collision detection and resolution (Module 3.6).
- Archive subdivision and cross-subdirectory link resolution.
- Unicode handling in summaries (accented characters, CJK, but no emoji — enforce rejection).
- File size warnings at 1000 chars, hard reject at 2000.

5.3 — Foundation archive curation:

- Review all blinks generated during Levels 0-4.
- Write 3-5 "map" blinks that serve as guided entry points for newcomers:
  - "Start here: How the identifier engine was built" (links to key parser blinks)
  - "Start here: How the relay protocol was implemented" (links to key relay blinks)
  - "Start here: How the CLI was designed" (links to key CLI blinks)
- Move completed work blinks to `/archive/foundation/`.
- Ensure every foundation blink has clean lineage and resolvable links.

5.4 — README:

- What BSS is (one paragraph).
- Install instructions.
- Quickstart: `bss init` walkthrough.
- "This repo built itself" — explanation of the foundation archive.
- Link to full spec.
- License (CC BY 4.0).

5.5 — Final validation:

- Run ALL Module 8 tests (8.1, 8.2, 8.3) — 100% pass rate.
- Run `bss validate` on every blink in the foundation archive.
- Verify `bss tree` can trace from latest blink back to origin.
- Verify `bss triage` correctly orders any lingering relay blinks.

5.6 — Write the final blink: a convergence blink synthesizing the entire build, placed in `/active/`. This is the last blink before v1 release.

**Level 5 is complete when:** All tests pass, the foundation archive is curated, the README tells the story, and `pip install bss` gives someone a working tool.

---

## LEVEL 6 — SHIP IT

**Goal:** Publish.

### Tasks

6.1 — Final git history review. Clean up any non-blink artifacts but NEVER delete blinks.

6.2 — Tag: `v1.0.0`

6.3 — Push to GitHub. Public repo. The foundation archive is visible to the world.

6.4 — Publish to PyPI: `pip install blink-sigil-system` (or whatever package name is available).

6.5 — Write the launch post. The story writes itself: "We built a coordination protocol for stateless AI. Then we used it to build itself. Here's the archive."

---

## Dogfooding Rules (Apply to ALL Levels)

These rules apply throughout the entire build process:

1. **the build agent writes blinks.** At the end of every the build agent session, a handoff blink is written to `/relay/`. At the start of every session, `/relay/` is read first.

2. **You write blinks.** When you make a design decision, complete a level, or hit a wall — write a blink. Your sigil is `U`.

3. **Errors are blinks.** When something breaks, it becomes an `!!` blink, not just a frustrated git commit message.

4. **Convergence is real.** After 7 sessions on the same thread, force a convergence blink. Synthesize. Reset.

5. **Never delete a blink.** Dead ends get `_` (dormant). Bad ideas get `!#` (cancelled). Nothing disappears.

6. **Git commits include blinks.** Every commit that adds or moves blinks should note it. The git log and the blink log should tell parallel stories.

7. **The archive is sacred.** What lands in `/archive/foundation/` ships with the repo. Treat every blink like it's documentation someone will read.

---

## Recommended the build agent Session Opener

Paste this at the start of each the build agent session:

```
Read CLAUDE.md, then read /relay/ for handoff blinks from last session.
Orient yourself on current state before starting any work.
At the end of this session, write a handoff blink to /relay/ capturing
what you did, where things stand, and what the next session should pick up.
Your author sigil is A.
```

---

*Built by Alembic AI — distilling AI coordination to its purest form.*
