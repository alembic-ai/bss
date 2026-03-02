# BSS Artifact Integration — Reference Implementation Convention

## Status

This document defines the artifact integration pattern for the BSS reference implementation. Artifacts are NOT part of the BSS core specification (Modules 0-9). They are a reference implementation convention that demonstrates how work products integrate with the blink coordination layer.

The BSS spec stays clean. This is a companion pattern.

---

## 1 — What Is an Artifact?

A **blink** is coordination metadata — it records what happened, why it mattered, and where it sits in the graph.

An **artifact** is a work product — code files, documents, reports, images, configs, data exports. The tangible output of a model's work session.

Blinks answer: *what was the state of mind?*
Artifacts answer: *what was produced?*

Every artifact is born from a blink. Not every blink produces an artifact.

---

## 2 — Who Does What

### The Models (Relay Members)

Models are the participants. They think, they work, they coordinate. In a BSS environment, models:

- **Read blinks** during intake and triage — filenames first, then selectively open files
- **Assess their own state** — confidence, cognitive mode, and all sigil dimensions are self-reported by the model, not assigned by the CLI
- **Write blinks** — the model composes the blink ID (with CLI assistance for sequence assignment and validation), writes the summary, maintains lineage and links
- **Produce artifacts** — the actual work output (code, text, analysis, etc.)
- **Decide artifact naming** — the model chooses the descriptive slug for any artifact it produces

The model's self-assessment is the honesty layer. A model encoding `~` (low confidence) or `%` (frustration) is meaningful because the model said it about itself. This cannot be outsourced to a script.

### The CLI (Infrastructure)

The CLI is plumbing. It doesn't think, it facilitates. The CLI:

- **Manages the environment** — creates directories, enforces structure
- **Assigns sequence numbers** — scans all directories, determines next available, prevents collisions
- **Validates blinks** — checks that what the model wrote conforms to the 17-character grammar before committing to the filesystem
- **Enforces immutability** — prevents modification, renaming, or deletion of existing blinks
- **Injects protocol context** — provides the model with BSS instructions per Module 5.8 (directory structure, sigil grammar, its author sigil, current relay state)
- **Tracks generations** — warns when convergence is needed, enforces the 7-generation cap
- **Manages artifacts** — handles the filesystem operations for artifact storage and naming
- **Presents information** — `bss status`, `bss log`, `bss triage`, `bss tree`, `bss describe`

### The Boundary

The model says: "I'm writing a handoff blink, I'm highly confident, I had a breakthrough, this is about work + making, regional scope, in progress, high priority."

The CLI says: "Your sequence number is 0002F, your author sigil is A, the grammar is valid, the file has been written, the artifact has been stored."

The model owns the semantics. The CLI owns the mechanics.

---

## 3 — Artifact Naming Convention

### Format

```
{sequence}{author}-{slug}.{ext}
```

### Components

| Component | Source | Example |
|-----------|--------|---------|
| `sequence` | 5-char base-36 from the parent blink (positions 1-5) | `00030` |
| `author` | Single char from the parent blink (position 6) | `A` |
| `-` | Literal dash separator | `-` |
| `slug` | Human-readable descriptor, lowercase, hyphens for spaces | `identifier-parser` |
| `.ext` | Standard file extension | `.py` |

### Examples

```
00030A-identifier-parser.py
00035B-api-schema.json
00042U-launch-brief.md
0004CA-test-results.txt
00050A-roster-migration.sql
00061B-error-log-analysis.md
```

### Rules

- The `{sequence}{author}` prefix MUST match the parent blink exactly.
- One blink MAY produce zero or one artifact.
- One artifact belongs to exactly one blink.
- If a session produces multiple files, each file is a separate artifact with its own parent blink.
- The slug MUST be lowercase alphanumeric with hyphens only. No spaces, no underscores, no special characters.
- The slug SHOULD be descriptive enough to understand the artifact without opening it.
- The file extension MUST match the actual file type.

### Compound Artifacts

If a single logical output consists of multiple files (e.g., a module with a main file and a test file), the model writes one blink per file, or groups them under a single blink with a directory artifact:

```
00030A-identifier-module/
├── parser.py
├── sigils.py
└── __init__.py
```

The parent blink references the directory, not individual files. This should be rare — BSS favors small, atomic units.

---

## 4 — Artifact Directory Structure

### Location

```
bss-environment/
├── relay/
├── active/
├── profile/
├── archive/
│   └── foundation/
└── artifacts/              ← all work products live here
    ├── 00030A-identifier-parser.py
    ├── 00035B-api-schema.json
    ├── 00042U-launch-brief.md
    └── ...
```

### Rules

- The `/artifacts/` directory sits at the BSS environment root, alongside the four protocol directories.
- Artifacts are NOT blinks. They do not follow the 17-character grammar. They are not subject to immutability constraints (artifacts can be iterated on — the blink that produced them is the immutable record).
- Artifacts are NOT organized into subdirectories by default. The base-36 prefix provides natural chronological ordering.
- Implementations MAY subdivide `/artifacts/` for large environments (e.g., by sequence range or domain), following the same pattern as archive subdivision.

### Artifact Mutability

Unlike blinks, artifacts CAN be modified. However:

- The original artifact at the time of blink creation is the canonical version associated with that blink.
- If an artifact is significantly revised, a new blink SHOULD be written (with a new sequence number) and a new artifact version stored.
- Implementations MAY use versioned artifact names: `00030A-identifier-parser.py` → `00055A-identifier-parser.py` (new version, new blink, new sequence).
- The blink graph tracks the evolution. The artifacts directory holds the current state. Git tracks the change history.

---

## 5 — Blink-Artifact Reference Pattern

### In the Summary

The blink's summary references the artifact in natural language. Per Module 4.3 (layer separation), no structured artifact paths appear in the summary — just a natural mention:

```markdown
Born from: 00025A.!+!=#!-~~=

Built the first working version of the identifier parser. All base-36 encoding,
positional sigil extraction, and full grammar validation are implemented. The
nine test cases from Module 8.1 all pass. Artifact produced: the parser module.

Lineage: 00001U~~^!!^;!,=. → 00005A.!+!=#!-,^= → ... → 00030A.!+!=#!=~^=

Links:
```

The artifact's filename carries the blink's sequence + author prefix, so the association is always recoverable by convention without embedding file paths in the blink.

### Lookup Pattern

To find a blink's artifact:
```
Given blink: 00030A.!+!=#!=~^=
Search /artifacts/ for files starting with: 00030A-
Result: 00030A-identifier-parser.py
```

To find an artifact's blink:
```
Given artifact: 00030A-identifier-parser.py
Extract prefix: 00030A
Search all blink directories for files starting with: 00030A
Result: 00030A.!+!=#!=~^=.md (in /active/)
```

This bidirectional lookup requires no index, no database, and no additional metadata. The naming convention IS the link.

---

## 6 — CLI Integration

### New Commands

```
bss artifacts                — List all artifacts with parent blink info
bss artifact <sequence>      — Show artifact details and parent blink
bss produce <file>           — Register an existing file as an artifact (interactive blink creation)
```

### Enhanced Existing Commands

`bss log` shows artifacts inline:

```
$ bss log --last 5

  00042  U  ..  +  System + Doc    "Wrote launch brief"       → 00042U-launch-brief.md
  00030  A  .!  +  Work + Making   "Built identifier parser"  → 00030A-identifier-parser.py
  0002F  A  ~!  }  Work + Making   "Validator complete"
  0002E  A  .!  +  Work + Fixing   "Fixed base36 edge case"   → 0002EA-base36-fix.py
  0002D  B  ~.  +  Learn + Explore "Researched CLI frameworks"
```

Blinks without artifacts show no arrow. The presence or absence of an artifact is visible at a glance.

`bss status` includes artifact count:

```
$ bss status

  ...
  Artifacts: 12 files (3 .py, 4 .md, 2 .json, 3 .txt)
  Latest: 00042U-launch-brief.md
```

`bss tree` marks artifact-producing blinks:

```
$ bss tree 00030A.!+!=#!=~^=

  00001U~~^!!^;!,=.  (Origin)
    └─+ 00005A.!+!=#!-,^=  "Identifier module started"
      └─+ 0000AA.!+!=#!-~~=  "Parser core logic"  [artifact]
        ├─} 0000FA~!}!^#!=~^=  "Validator branched"  [artifact]
        └─+ 00015A.!+!=#!=~~=  "Generator added"  [artifact]
          └─+ 00030A.!+!=#!=~^=  ← YOU ARE HERE  [artifact]
```

---

## 7 — Model Instruction Additions

When the CLI injects BSS protocol context into a model's prompt (per Module 5.8), the following artifact guidance is included:

```
ARTIFACTS

When your work produces a tangible output (code, document, data, etc.),
it will be stored as an artifact.

- Suggest a descriptive slug for the artifact (lowercase, hyphens, no spaces).
- The CLI will handle naming and storage.
- Reference the artifact naturally in your blink summary.
- Do not embed file paths in the summary.
- One artifact per blink maximum. Multiple outputs = multiple blinks.
```

This keeps the model informed without requiring it to manage filesystem operations for artifacts.

---

## 8 — Foundation Archive Artifacts

During the BSS self-build (Level 0-5 of the Build Plan), artifacts produced include:

- Source code modules (parser, validator, file writer, environment manager, relay engine, CLI)
- Test files
- Configuration files
- Documentation drafts

These artifacts ship with the repo alongside the foundation blinks:

```
bss/
├── archive/
│   └── foundation/          ← the blinks that tell the story
├── artifacts/
│   ├── 00030A-identifier-parser.py    ← early parser version
│   ├── 00055A-identifier-parser.py    ← later parser version
│   └── ...                            ← the trail of what was built
├── src/
│   └── bss/                 ← the final, polished source code
└── ...
```

Note: The `/artifacts/` directory contains the raw outputs as they were produced during development. The `/src/` directory contains the final, cleaned-up implementation. They are parallel records — artifacts show the build process, src shows the shipped product. Both trace back to the blink graph.

---

## 9 — What This Is NOT

This artifact integration is NOT:

- **Part of the BSS specification.** The spec (Modules 0-9) defines blinks only. Artifacts are a reference implementation pattern.
- **Required for BSS compliance.** A BSS-compliant implementation can ignore artifacts entirely.
- **A replacement for version control.** Git tracks code evolution. Blinks track cognitive evolution. Artifacts track output evolution. Three parallel histories.
- **A file storage system.** Artifacts are lightweight references, not a managed repository. Large binary files, databases, and deployment artifacts belong in their own systems.

This IS:

- **A convention** for linking work products to the coordination graph.
- **A pattern** that other implementations can adopt, adapt, or ignore.
- **A demonstration** of how BSS integrates with real development workflows.

---

## 10 — Implementation Notes

### Build Plan Integration

Add to **Level 2** (The File Engine):
- Add `artifacts/` to the `BSSEnvironment.init()` method.
- Add `find_artifact(sequence: str, author: str) -> Path | None` to the environment module.
- Add `register_artifact(blink_id: str, filepath: Path, slug: str) -> Path` to handle naming and storage.

Add to **Level 4** (The CLI):
- Add `bss artifacts`, `bss artifact <seq>`, and `bss produce` commands.
- Integrate artifact display into `bss log`, `bss status`, and `bss tree`.

Add to **Level 5** (Integration & Polish):
- Verify bidirectional blink-artifact lookup across the entire foundation archive.
- Ensure all foundation artifacts are properly prefixed and traceable.

### Dependencies

No additional dependencies required. Artifact management is pure filesystem operations — `pathlib`, `shutil`, nothing external.

---

*Artifact integration for the BSS Reference Implementation.*
*Alembic AI — distilling AI coordination to its purest form.*
