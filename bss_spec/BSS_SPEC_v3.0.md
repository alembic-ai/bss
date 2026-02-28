# The Blink Sigil System — Protocol Specification

### Version 2.0 Draft

**Author:** Alembic AI
**Status:** Draft
**License:** CC BY 4.0

---

## Document Structure

This specification is organized into ten modules, a canonical test suite, and appendices. Each module is self-contained and can be referenced independently. Together they define the complete BSS protocol.

- **Modules 0-4** define the foundation: philosophy, terminology, filesystem, identifiers, and file format.
- **Module 5** defines the relay protocol: session lifecycle, handoffs, error escalation, participation tiers, the roster, generation management, and model instruction requirements.
- **Module 6** defines the vocabulary for emergent graph dynamics.
- **Module 7** defines compliance levels for implementations.
- **Module 8** provides the canonical test suite.
- **Module 9** defines versioning and evolution policy.
- **Module 10** documents acknowledged future scope and expansion areas.

The Gardener — an intelligence and maintenance layer for BSS environments — is defined in a separate companion document (BSS-GARDENER-v1.0). It is not required for BSS compliance but is recommended for sustained, high-volume deployments.

---

## Module 0 — Preamble & Philosophy

### 0.1 — Abstract

The Blink Sigil System (BSS) is a file-based coordination protocol for stateless AI models operating in relay. Each unit of coordination is called a blink — a Markdown file whose filename encodes structured metadata sufficient for any incoming model to triage, orient, and act without reading the file's contents.

BSS requires no database, no API, no orchestrator, and no specific model. Coordination emerges from filesystem conventions, folder structure, and a shared symbolic grammar encoded in every filename.

### 0.2 — Scope

BSS is a coordination protocol. It defines how AI agents communicate state, priority, and intent through structured files on a shared filesystem.

BSS is NOT:

- A retrieval system (it does not answer queries against a knowledge base)
- A chat history format (it does not store conversations)
- An orchestration framework (it does not assign tasks or manage workflows)
- A model specification (it does not define agent capabilities or behaviors)

BSS may be used alongside any of these systems. It is designed to complement, not replace, existing AI infrastructure.

### 0.3 — Design Principles

1. **Model independence.** The protocol does not assume any model architecture, size, or capability. A 1B parameter model and a frontier model interact with BSS identically.

2. **Immutable persistence.** Blinks are never deleted and never modified. Once written, a blink is a permanent snapshot. If circumstances change, a new blink is created linking to the original. The complete, unaltered history of the system is always preserved.

3. **Emergent structure.** BSS imposes no schemas, taxonomies, or hierarchies. Structure emerges from the accumulation of blinks and the links between them.

4. **Topological meaning.** A single blink is a data point. The web of connections between blinks is understanding. Meaning lives in the graph, not in individual nodes.

5. **Brevity by design.** Each blink is small. Compound understanding comes from accumulation, not from the size of any individual unit.

6. **Machine-first legibility.** The filename encoding is optimized for machine parsing. Human readability is a secondary concern, supported by reference documentation.

7. **Zero infrastructure.** BSS operates on a standard filesystem. No server, no database, no network connection, and no runtime beyond file I/O are required.

8. **Serial integrity.** The blink sequence is strictly ordered. Only one blink may occupy a given sequence number. A model writing a blink MUST be aware of every blink that existed at the time of writing. Concurrent models operating on different threads still share a single sequence counter, ensuring a total ordering of all activity in the environment.

### 0.4 — Conventions Used in This Document

- The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are used as defined in RFC 2119.
- Filesystem paths use forward-slash notation (`/active/`). Implementations MUST map to the host OS path convention.
- Character positions in filenames are 1-indexed.
- Examples are illustrative, not exhaustive. The canonical test suite (Module 8) provides the authoritative set of valid and invalid cases.

---

## Module 1 — Terminology

### 1.1 — Core Terms

**Blink:** The atomic unit of BSS. A Markdown file (`.md`) with a structured filename encoding metadata and a brief natural-language interior containing context, lineage, and links.

**Blink Identifier (Blink ID):** The filename of a blink, excluding the `.md` extension. A fixed-length string conforming to the positional grammar defined in Module 3.

**Relay:** The process by which one model completes work, writes a blink capturing its state, and yields to the next model. The incoming model reads the outgoing model's blink(s) to orient itself.

**Cold Start:** The process by which a model with no prior context enters a BSS environment and orients itself using only the filesystem.

**Triage:** The act of reading blink filenames (without opening files) to assess the current state of the environment, identify priorities, and determine which blinks require attention.

**Graph:** The directed network of relationships between blinks, formed by parent references (`Born from`) and associative references (`Links`). The graph is implicit — it exists in the file references, not in a separate data structure.

**Sigil:** A symbol occupying a specific position in the blink identifier, encoding a single dimension of metadata.

**Snapshot:** The principle that a blink records a fixed moment in time. All metadata (action state, confidence, cognitive state, etc.) reflects the instant the blink was written. Blinks are never updated to reflect later changes — new blinks are created instead.

**Session:** A single continuous period of model activity, beginning with cold start or relay intake and ending with blink output and dormancy.

### 1.2 — Role Terms

**Author:** The agent that wrote a given blink. Identified by the author sigil in position 6 of the blink identifier.

**Receiver:** The agent that reads a blink during triage or relay intake. Any model entering the environment is a receiver until it writes its own blink.

**Gardener:** An optional maintenance agent (defined in the companion specification BSS-GARDENER) that tends the blink graph over time. Not part of the core protocol.

### 1.3 — State Terms

**Active:** A blink currently relevant to ongoing work. Resides in the `/active/` directory.

**Dormant:** A blink marked with the `_` relational sigil, indicating a dead end or abandoned thread. May reside in any directory.

**Archived:** A blink that has been moved to the `/archive/` directory, typically because its action state indicates completion. Archived blinks are only accessed when referenced by link from an active blink.

---

## Module 2 — Filesystem Architecture

### 2.1 — Required Directories

A conformant BSS environment MUST contain the following four directories at its root:

| Directory | Purpose | Access Pattern |
|-----------|---------|----------------|
| `/relay/` | Model-to-model handoff blinks. Contains blinks intended for the next incoming model. | Read first on every cold start. |
| `/active/` | Ongoing tasks and live threads. Contains blinks related to current work. | Read second, after `/relay/`. |
| `/profile/` | Persistent knowledge about the user, environment, and preferences. | Read third. Updated infrequently. |
| `/archive/` | Completed, dormant, or superseded blinks. Historical record. | Read only when a link in an active or relay blink points here. |

Implementations MAY create additional directories for implementation-specific purposes, but these four MUST exist and MUST follow the access patterns defined above.

### 2.2 — Startup Sequence

When a model enters a BSS environment with no prior context (cold start), it MUST follow this sequence:

```
1. Read /relay/    — orient: what is being handed off?
2. Read /active/   — survey: what is in progress?
3. Read /profile/  — context: who is the user, what are the preferences?
4. Follow links    — as needed, into /archive/ or between directories
```

"Read" in steps 1-3 means triage — reading filenames to assess state — followed by selective file opening based on triage results. A model SHOULD NOT open every file in a directory. It SHOULD open only those blinks whose filename metadata indicates relevance to the current task.

### 2.3 — Write Rules

- A model completing a relay handoff MUST write its blink to `/relay/`.
- A model producing work output (not a handoff) SHOULD write to `/active/`.
- A model updating user knowledge or preferences SHOULD write to `/profile/`.
- A model MUST NOT write directly to `/archive/`. Archival is a maintenance operation.
- A model MUST NOT delete any blink from any directory.
- A model MUST NOT modify the filename or content of any existing blink. If a blink's state has changed, the model creates a new blink linking to the original. See Module 3, Section 3.7.

### 2.4 — Archive Subdivision

Implementations MAY subdivide `/archive/` into epoch-based subdirectories to manage scale. The recommended pattern is:

```
/archive/
├── 2026-Q1/
├── 2026-Q2/
└── ...
```

The subdivision scheme is not mandated by this specification. Implementations MUST ensure that blink IDs remain unique across all archive subdirectories. Links referencing archived blinks MUST remain resolvable regardless of subdivision.

### 2.5 — Profile Directory Conventions

The `/profile/` directory contains persistent configuration and knowledge blinks. Unlike `/relay/` and `/active/`, profile blinks are not task-specific — they provide standing context that every model reads during the startup sequence.

Profile blinks fall into three categories:

**Roster blinks** define the model registry — which author sigils map to which models, their capabilities, and their roles. See Module 5, Section 5.6 for the full roster specification. A BSS environment SHOULD contain exactly one current roster blink. When the roster changes, a new roster blink is written (the previous one is immutable) and the outdated roster is moved to `/archive/`.

**Preference blinks** capture user knowledge — communication style, domain expertise, project context, personal preferences, and any standing instructions that models should always be aware of. These are authored by relay members (based on user interaction) or by the user directly (author sigil `U`).

**Configuration blinks** document system-level settings — the sequence partitioning scheme for multi-device deployments, any custom triage ordering overrides, the spec version in use, and implementation-specific parameters. These are authored with the system sigil (`S`).

A model reading `/profile/` during step 3 of the startup sequence SHOULD read roster and configuration blinks first, then preference blinks. This ensures the model understands its own identity and role before absorbing user context.

---

## Module 3 — The Blink Identifier

### 3.1 — Structure

The blink identifier is a fixed-length string of exactly **17 characters**, forming the filename of a blink file (with `.md` extension appended).

Each character occupies a defined position encoding a specific dimension of metadata. A conformant parser MUST interpret characters strictly by position.

```
Position:  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15  16  17
Category: [ Sequence  ][Au][  Action ][Rl][Cn][Cg][  Thematic  ][Sc][Mt][  Urg  ]
```

### 3.2 — Formal Grammar

```
BLINK_ID      := SEQUENCE AUTHOR ACTION RELATIONAL CONFIDENCE COGNITIVE
                 DOMAIN SUBDOMAIN SCOPE MATURITY URGENCY

SEQUENCE      := BASE36 BASE36 BASE36 BASE36 BASE36
BASE36        := [0-9A-Z]

AUTHOR        := [A-Z0-9]

ACTION        := ENERGY VALENCE
ENERGY        := '!' | '.' | '~'
VALENCE       := '!' | '.' | '~' | '#'

RELATIONAL    := '^' | '>' | '<' | '#' | '=' | '_' | '+'

CONFIDENCE    := '!' | '.' | '~' | ','

COGNITIVE     := '!' | '~' | '^' | '%' | '=' | '#' | '.' | '&'

DOMAIN        := '@' | '#' | '$' | '&' | '!' | '~' | '%' | '^' | '+' | ';'

SUBDOMAIN     := '!' | '~' | '^' | '.' | '=' | '&' | '-' | '+' | ';' | ','

SCOPE         := '.' | '-' | '=' | '!'

MATURITY      := ',' | '~' | '.' | '!' | '-'

URGENCY       := PRIORITY SENSITIVITY
PRIORITY      := '!' | '^' | '=' | '.' | '~'
SENSITIVITY   := '!' | '^' | '=' | '.'
```

### 3.3 — Position Reference

#### Positions 1-5: Sequence

A base-36 counter providing reading order and unique identification within a BSS environment.

- Character set: `0-9, A-Z` (case-insensitive on read, uppercase on write)
- Range: `00001` to `ZZZZZ` (1 to 60,466,175)
- Sequence values MUST be assigned in monotonically increasing order within a single BSS environment.
- Sequence `00000` is RESERVED and MUST NOT be used.
- Implementations MUST zero-pad to five characters.

**Multi-device deployments:** When multiple devices or instances write to the same BSS environment, implementations SHOULD partition the sequence space to prevent collisions. Recommended strategies:

- Prefix allocation: device A uses `00001-FFFFF`, device B uses `G0001-NZZZZ`, etc.
- Interleaving: device A uses odd sequences, device B uses even sequences.
- The partitioning strategy used MUST be documented in a blink in `/profile/`.

#### Position 6: Author

Identifies the agent that wrote this blink.

| Sigil | Meaning |
|-------|---------|
| `A`-`Z` | Model agents. `A` = primary, `B` = secondary, etc. |
| `0`-`9` | Extended model agents (for environments with >26 models). |

Reserved author sigils:

| Sigil | Meaning |
|-------|---------|
| `U` | User-created blink (written by a human, not a model). |
| `S` | System-generated blink (written by the Gardener or other automated processes). |

#### Positions 7-8: Action State

A two-character compound encoding the situation the next model is inheriting.

Position 7 carries the energy signature:
- `!` = urgency / energy / problem
- `.` = stillness / completion / progress
- `~` = neutrality / passivity / waiting

| Compound | Meaning | Receiver Behavior |
|----------|---------|-------------------|
| `~~` | Idle | No action required. |
| `~!` | Handoff | Pick this up. Active task transfer. |
| `~.` | Completed | No action needed. Archival candidate. |
| `!~` | Blocked | Waiting on external dependency. Monitor, do not act. |
| `!!` | Error | Something broke. Investigate and resolve. |
| `!.` | Decision needed | A choice point. Present options or make a judgment call. |
| `.!` | In progress | Partially complete. Continue the work. |
| `..` | Informational | Pure knowledge. No action implied. |
| `.~` | Awaiting user input | Cannot proceed without human response. |
| `!#` | Cancelled | Abandoned intentionally. Do not resume. |

Implementations MUST reject action state combinations not listed above.

**Snapshot semantics:** An action state records the situation at the moment the blink was written. It does not change over time. A blink written with `~!` (handoff) remains a handoff blink permanently — even after the handoff has been processed. The receiving model records the processing in a new blink; it does not modify the original. See Section 3.7 for the full immutability specification.

#### Position 9: Relational Role

Describes this blink's structural position within the graph.

| Sigil | Meaning | Graph Implication |
|-------|---------|-------------------|
| `^` | Origin / seed | Root node. Has no parent. `Born from` field reads "Origin". |
| `>` | Branch / divergence | Creates a new thread from an existing parent. |
| `<` | Convergence / synthesis | Merges insights from multiple parent threads. |
| `#` | Contradiction / conflict | Disagrees with or challenges a parent blink. |
| `=` | Reinforcement / echo | Supports or confirms a related blink. |
| `_` | Dead end / dormant | Thread terminated. No continuation expected. |
| `+` | Continuation | Same thread, next step. The default for sequential work. |

#### Position 10: Confidence

How certain the authoring model was about the content of this blink.

| Sigil | Meaning |
|-------|---------|
| `!` | High — the model is confident in its output. |
| `.` | Moderate — reasonable certainty with some caveats. |
| `~` | Low — the model is unsure and flags this for review. |
| `,` | Speculative — exploratory or hypothetical content. |

#### Position 11: Cognitive State

The mental mode or processing state that produced this blink.

| Sigil | Meaning |
|-------|---------|
| `!` | Clarity / insight — clean understanding achieved. |
| `~` | Confusion / fog — the model struggled with this. |
| `^` | Breakthrough — something significant was discovered. |
| `%` | Frustration / resistance — repeated obstacles encountered. |
| `=` | Flow / momentum — smooth, productive continuation. |
| `#` | Tension / unresolved — competing considerations not yet settled. |
| `.` | Resolution / closure — a previously open question was answered. |
| `&` | Curiosity / opening — a new question or direction emerged. |

#### Position 12: Domain

High-level thematic territory. Answers: what area of concern does this blink belong to?

| Sigil | Meaning |
|-------|---------|
| `@` | Self / identity |
| `#` | Work / craft |
| `$` | Finance / resources |
| `&` | Relationships |
| `!` | Creation / building |
| `~` | Learning / discovery |
| `%` | Health / body |
| `^` | System / meta |
| `+` | Play / joy |
| `;` | Conflict / tension |

#### Position 13: Subdomain

Universal cognitive activity type. Context-independent — the same sigil means the same kind of thinking regardless of which domain it is paired with.

| Sigil | Meaning |
|-------|---------|
| `!` | Making / producing / building |
| `~` | Exploring / researching / learning |
| `^` | Designing / planning / strategizing |
| `.` | Maintaining / sustaining / managing |
| `=` | Communicating / exchanging / sharing |
| `&` | Analyzing / evaluating / reviewing |
| `-` | Fixing / resolving / repairing |
| `+` | Growing / developing / improving |
| `;` | Documenting / recording / logging |
| `,` | Deciding / choosing / committing |

Domain and subdomain combine to form a thematic compound. Examples:

| Compound | Reading |
|----------|---------|
| `#^` | Work + Designing (system architecture, planning) |
| `#-` | Work + Fixing (debugging, problem solving) |
| `$&` | Finance + Analyzing (budget review, auditing) |
| `@&` | Self + Analyzing (introspection, self-reflection) |
| `!+` | Creation + Growing (iterating on a project) |
| `~;` | Learning + Documenting (capturing knowledge, note-taking) |

#### Position 14: Scope

The blast radius of this blink. Tells a receiving model how much surrounding context to gather.

| Sigil | Meaning | Agent Guidance |
|-------|---------|----------------|
| `.` | Atomic — single variable, single fact, one discrete item. | Handle it and move on. |
| `-` | Local — one file, one function, one contained idea. | Solvable in one session. |
| `=` | Regional — multiple connected files or concepts. | May require reading linked blinks for context. |
| `!` | Global — architectural, systemic, crosses multiple domains. | Contribute what you can, document your contribution, hand off. |

**Scope as governance:** A model encountering a global-scope blink SHOULD self-limit. It SHOULD contribute within its competence, write a blink documenting its contribution, and hand off to the next model. No single model should attempt to own a global-scope task.

#### Position 15: Maturity

Where in its lifecycle the subject of this blink currently sits.

| Sigil | Meaning |
|-------|---------|
| `,` | Seed — first encounter, initial idea, raw thought. |
| `~` | In progress — actively evolving, not yet stable. |
| `.` | Near complete — most work done, minor refinements remain. |
| `!` | Complete / stable — finished, reliable, ready for use. |
| `-` | Needs revision — was further along but requires rework. |

#### Positions 16-17: Urgency

A two-character compound encoding priority and time sensitivity.

**Position 16 — Priority:**

| Sigil | Meaning |
|-------|---------|
| `!` | Critical — failure or major impact if not addressed. |
| `^` | High — important, should be addressed soon. |
| `=` | Normal — standard priority. |
| `.` | Low — address when convenient. |
| `~` | Background — ambient knowledge, no action pressure. |

**Position 17 — Time Sensitivity:**

| Sigil | Meaning |
|-------|---------|
| `!` | Blocking — nothing else can proceed until this is handled. |
| `^` | Soon — time-sensitive but not immediately blocking. |
| `=` | Whenever — no deadline. |
| `.` | Passive — no time component at all. |

Urgency compounds:

| Compound | Reading |
|----------|---------|
| `!!` | Critical + Blocking — drop everything. |
| `!^` | Critical + Soon — top priority, act quickly. |
| `^=` | High + Whenever — important but no rush. |
| `=.` | Normal + Passive — routine, background. |
| `..` | Low + Passive — get to it eventually. |
| `~.` | Background + Passive — ambient knowledge. |

### 3.4 — Filename Construction

The complete filename of a blink is:

```
{BLINK_ID}.md
```

Where `BLINK_ID` is exactly 17 characters conforming to the grammar in Section 3.2.

Example:

```
0002FA~!>!^#!=~^=.md
│    │ │ │││  ││ ││
│    │ │ │││  ││ │└─ Position 17: Time Sensitivity (= Whenever)
│    │ │ │││  ││ └── Position 16: Priority (^ High)
│    │ │ │││  │└──── Position 15: Maturity (~ In progress)
│    │ │ │││  └───── Position 14: Scope (= Regional)
│    │ │ ││└──────── Position 13: Subdomain (! Making)
│    │ │ │└───────── Position 12: Domain (# Work)
│    │ │ └────────── Position 11: Cognitive (^ Breakthrough)
│    │ │              Position 10: Confidence (! High)
│    │ └──────────── Position 9:  Relational (> Branch)
│    └────────────── Positions 7-8: Action (~! Handoff)
│                     Position 6:  Author (A)
└─────────────────── Positions 1-5: Sequence (0002F)
```

Plain language: Blink 95 (0002F in base-36), authored by Model A, is a handoff. It branches from an existing thread. The model was highly confident and had a breakthrough. This is about building something in the work domain, at regional scope, still in progress. High priority but no hard deadline.

### 3.5 — Validation Rules

A blink identifier is VALID if and only if:

1. It is exactly 17 characters in length.
2. Positions 1-5 each contain a character in the set `[0-9A-Z]`.
3. Position 6 contains a character in the set `[A-Z0-9]`.
4. Positions 7-8 form one of the ten defined action state compounds (Section 3.3, Position 7-8 table).
5. Each remaining position contains a character from its defined symbol set (Section 3.3).

A parser encountering an invalid blink identifier SHOULD log a warning and SHOULD NOT attempt to interpret the filename. The associated file MAY still be read for its content, but its metadata MUST be treated as unknown.

### 3.6 — Collision Handling

If two blinks are discovered with identical sequence values (positions 1-5):

- The blink with the later filesystem modification timestamp takes precedence for sequencing purposes.
- Implementations SHOULD surface the collision as an error or warning.
- Neither blink is deleted (Principle 2). The collision is resolved by assigning the later blink the next available sequence value.

### 3.7 — Immutability & Snapshot Semantics

A blink identifier and its associated file content are immutable. Once a blink is written, it MUST NOT be modified, renamed, or overwritten. Every blink is a snapshot — a permanent record of a specific moment in the system's history.

**Action states are snapshots, not statuses.** A blink with action state `.!` (in progress) does not become `~.` (completed) when the work finishes. Instead, a new blink is created with action state `~.`, linking back to the original via `Born from`. The original blink permanently records that work was in progress at that moment. The new blink permanently records its completion. Both are true. Neither is modified.

**Dormant blinks are not reactivated by mutation.** A blink with relational sigil `_` (dormant) that becomes relevant again is not changed. A new blink is created in `/active/` with a `Links` reference to the dormant blink, explaining why it has resurfaced. The dormant blink retains its original context, and the new blink captures the reason for reactivation. This produces two pieces of information rather than one.

**Rationale:** Immutability ensures that the blink graph is an honest, auditable record. Any model can trust that a blink it reads reflects the exact state of affairs at the time it was written. If blinks could be modified, a model would need to consider whether the information is current or has been retroactively altered — introducing uncertainty that the protocol is designed to eliminate.

**The only permitted filesystem operations on existing blinks are:**

- **Read** — any agent may read any blink at any time.
- **Move** — a blink may be moved between directories (e.g., from `/active/` to `/archive/`) as part of maintenance operations. The filename and file content MUST NOT change during a move.

**Prohibited operations:**

- Renaming a blink file (changing the blink identifier).
- Editing the content of a blink file.
- Deleting a blink file.
- Overwriting a blink file.

### 3.8 — Serial Write Protocol

The blink sequence is a total ordering of all activity in a BSS environment. This ordering is the foundation of the protocol's integrity guarantees.

**One blink, one sequence number.** Only one blink may occupy a given sequence value. Sequence numbers are assigned at write time, not at task start. A model that has been working for several minutes MUST check the current highest sequence number immediately before writing, not use the number it observed at session start.

**Write-time awareness.** A model writing a blink MUST be aware of every blink that existed at the moment of writing. If another model has written a blink while this model was working, the writing model MUST read the new blink's filename before claiming the next sequence number. This ensures that every blink in the sequence was written with full knowledge of all preceding blinks.

**Practical concurrency.** Multiple models MAY operate simultaneously on different threads within the same BSS environment. However, the act of writing a blink is serialized:

1. The model completes its work.
2. The model scans for the current highest sequence number across all directories.
3. The model claims the next sequence number and writes its blink.
4. If a collision is detected (another model wrote between steps 2 and 3), the model MUST re-scan and re-assign to the next available number. See Section 3.6.

**Invocation-time snapshot.** A model reasons only about the blinks that existed when it was invoked (entered the INTAKE phase). If another model writes blinks during this model's WORK phase, those new blinks do not affect the current model's task execution. They only affect the sequence number assignment during the OUTPUT phase. This ensures that a model's reasoning is internally consistent — it never acts on a partially-observed state.

**Rationale:** Serial integrity means that reading the blink sequence from `00001` to the current head reproduces the complete, ordered history of the environment. No gaps. No parallel writes that contradict each other. No blinks created in ignorance of their predecessors. The filesystem blinks — each entry is a discrete, ordered moment — and the sequence is the timeline.

---

## Module 4 — The Blink File Format

### 4.1 — Structure

Every blink file is a Markdown document (`.md`) containing exactly four sections in this order:

```markdown
Born from: [parent blink ID(s)] or "Origin"

[Summary — 2 to 5 sentences of natural language]

Lineage: [oldest relevant ancestor] → ... → [this blink ID]

Links: [pipe-separated blink IDs of related nodes]
```

### 4.2 — Field Definitions

#### Born from (REQUIRED)

Specifies the parent blink(s) that directly gave rise to this blink.

- For origin blinks (relational sigil `^`): the value MUST be the string `Origin`.
- For all other blinks: the value MUST be one or more valid blink IDs, pipe-separated (`|`) if multiple.
- A blink with relational sigil `<` (convergence) SHOULD have multiple parents.
- A blink with relational sigil `+` (continuation) SHOULD have exactly one parent.

#### Summary (REQUIRED)

A natural-language description of the blink's content and significance.

- MUST be 2 to 5 sentences.
- MUST be written in natural language, never structured data (no JSON, no key-value pairs, no tables).
- MUST NOT contain blink identifiers. References to other blinks are reserved for the `Born from`, `Lineage`, and `Links` fields. The summary is a self-contained narrative — a reader should understand its meaning without resolving any external references.
- SHOULD capture *why this mattered*, not just what happened.
- SHOULD be written as if leaving a note for a future version of the author that has forgotten the context but will understand the significance.
- MAY reference concepts, tasks, or themes from other blinks in natural language (e.g., "continuing the database refactor discussed earlier") without using blink IDs.

#### Lineage (REQUIRED)

A trace from the oldest relevant ancestor to this blink.

- Format: `[ancestor ID] → [intermediate ID] → ... → [this blink ID]`
- Maximum depth: 7 generations. If the true lineage is deeper, begin from the most recent 7 ancestors.
- For origin blinks: `Lineage: [this blink ID]` (self-reference only).

#### Links (OPTIONAL)

References to related blinks that are not parents. These are associative, not hierarchical.

- Format: pipe-separated (`|`) blink IDs.
- Links are directional: the presence of a link in blink A to blink B does not imply a link from B to A.
- There is no maximum number of links, but authors SHOULD keep links curated and relevant rather than exhaustive.
- If no links are relevant, this field MAY be omitted entirely.

### 4.3 — Layer Separation

The blink file format enforces a strict separation between two layers of information:

**The narrative layer** (Summary) contains natural language only. It is human-readable, machine-indexable as free text, and self-contained. It answers the question: *what happened and why did it matter?*

**The structural layer** (Born from, Lineage, Links) contains blink identifiers only. It is machine-parseable, graph-constructible, and referential. It answers the question: *where does this blink sit in the graph?*

These layers MUST NOT contaminate each other. Blink identifiers MUST NOT appear in the summary. Natural-language descriptions MUST NOT appear in the structural fields. This separation ensures that the summary can be indexed as pure text (e.g., by full-text search) without parsing out embedded identifiers, and that the structural fields can be parsed mechanically without natural-language interpretation.

### 4.4 — Encoding & Character Rules

- The file encoding MUST be UTF-8.
- Line endings MAY be LF or CRLF. Implementations MUST accept both.
- Summaries MAY contain any valid UTF-8 text, including accented characters, non-Latin scripts, and punctuation.
- Summaries MUST NOT contain emoji. Emoji introduce encoding variability across platforms and render inconsistently in terminal environments where BSS is commonly used.
- The `→` character (U+2192, rightwards arrow) is the REQUIRED separator in the `Lineage` field. Implementations MUST NOT substitute `->`, `=>`, or other representations.
- The `|` character (U+007C, vertical line) is the REQUIRED separator in the `Links` and `Born from` (multi-parent) fields.
- Whitespace around separators (`→`, `|`) is OPTIONAL on write but MUST be tolerated on read. Implementations SHOULD write with single spaces around separators for readability: `0001A | 0002B` rather than `0001A|0002B`.

### 4.5 — Size Constraints

- A blink file SHOULD NOT exceed 1,000 characters in total length. Blinks are small by design.
- A blink file MUST NOT exceed 2,000 characters. Any implementation encountering a blink exceeding this limit SHOULD log a warning. Oversized blinks indicate a violation of the brevity principle and should be split into multiple linked blinks.
- The `Links` field has no maximum entry count, but implementations SHOULD warn if a single blink links to more than 20 other blinks, as this suggests the blink is functioning as an index rather than a node.

---

## Module 5 — The Relay Protocol

### 5.1 — Session Lifecycle

A model session in a BSS environment follows this lifecycle:

```
INTAKE → TRIAGE → WORK → OUTPUT → DORMANCY
```

**Intake:** The model enters the environment and executes the startup sequence (Module 2, Section 2.2).

**Triage:** The model reads filenames in `/relay/` and `/active/` to assess the current state. It identifies pending handoffs, blocked tasks, active work, and priorities. No files are opened during triage unless the model determines a specific blink requires deeper inspection.

**Work:** The model performs its task. This may involve reading blink contents, creating artifacts, modifying external files, or any other productive activity.

**Output:** The model writes one or more blinks capturing its work, the state it is leaving behind, and any handoff instructions for the next model.

**Dormancy:** The model's session ends. It retains no state. The blinks it wrote are the sole record of its activity.

### 5.2 — Handoff Protocol

When a model completes work that requires continuation by another model:

1. The model MUST write a blink to `/relay/` with action state `~!` (handoff).
2. The blink's summary MUST describe what was done, what state was left, and what needs to happen next.
3. The blink's scope sigil SHOULD accurately reflect the blast radius of the remaining work.
4. The blink's urgency compound SHOULD reflect the priority and time sensitivity of the continuation.

When a model receives a handoff:

1. The receiving model reads `/relay/` first (startup sequence, step 1).
2. If multiple handoff blinks are present, the model SHOULD process them in this default triage order:
   - **First:** Urgency — higher priority and time sensitivity first (`!!` before `!^` before `^=`, etc.)
   - **Second:** Recency — later sequence numbers first (more recent blinks are more likely to reflect current state).
   - **Third:** Scope — broader scope first (global before regional before local) to establish context before details.
3. After processing a handoff blink, the receiving model MAY move it from `/relay/` to `/active/` if the work is ongoing, or leave it in `/relay/` for reference.

Implementations MAY override the default triage order. If they do, the override MUST be documented in a blink in `/profile/`.

### 5.3 — Relay Hygiene

- The `/relay/` directory SHOULD contain no more than 10 blinks at any time. Excess blinks indicate a processing backlog.
- A handoff blink that has been processed SHOULD be moved to `/active/` (if the work continues) or `/archive/` (if the handoff is complete).
- A model SHOULD NOT leave more than 3 blinks in `/relay/` at the end of a single session. If a session produces more than 3 handoffs, the model should consolidate into a single high-scope handoff blink with links to supporting blinks in `/active/`.

### 5.4 — Error Escalation

When a model encounters an error it cannot resolve, the error becomes a blink. Errors are not silent failures — they are first-class entries in the graph.

**Error blink requirements:**

1. The model MUST write a blink with action state `!!` (error).
2. The blink's summary MUST describe what was attempted, what went wrong, and what the model believes would be needed to resolve it.
3. The blink's confidence sigil SHOULD reflect the model's certainty about the diagnosis (e.g., `!` if the error is clear, `~` if the cause is uncertain).
4. The blink MUST be written to `/relay/` as a handoff so the next model encounters it during intake.

**Escalation through the relay:**

If the next model in sequence also cannot resolve the error:

1. It writes its own error blink with `Born from` referencing the previous error blink.
2. Its summary documents its own failed attempt and any additional diagnosis.
3. The chain of error blinks creates a visible escalation trail.

**User alerting:** If an error persists through two or more consecutive relay handoffs without resolution, the implementation SHOULD alert the user. The mechanism of alerting is implementation-specific (notification, UI indicator, log entry), but the trigger condition is defined by the protocol: two or more linked blinks with action state `!!` in sequence, with no intervening non-error blink in that thread.

**Rationale:** Errors in a relay system are uniquely dangerous because no single model retains memory of failure. Without explicit error blinks, a failure can be silently forgotten between sessions. By encoding errors as blinks, the failure persists in the graph, accumulates diagnostic information with each attempt, and eventually escalates to the only agent that can always intervene — the user.

### 5.5 — Participation Tiers

BSS defines two tiers of participation in a relay environment. This distinction preserves the integrity of the blink graph while allowing models of varying capability to contribute.

#### Relay Members

A relay member is a full participant in the BSS coordination protocol. Relay members:

- Execute the startup sequence and triage filenames.
- Read and write blinks to all directories (subject to Module 2 write rules).
- Participate in handoffs as both senders and receivers.
- Are listed in the roster blink (Section 5.6) with an assigned author sigil.
- Are responsible for the correctness of any blinks they author — including accurate sigil encoding, well-formed file format, and honest confidence assessment.

**Capability requirements for relay members:** A model serving as a relay member MUST be capable of:

- Parsing a 17-character blink identifier into its component sigils.
- Following the 4-step startup sequence in order.
- Writing a well-formed blink file with all required fields (Module 4).
- Accurately encoding its own work into the appropriate sigil values for each filename position.
- Reading the roster blink and self-governing according to its stated role and capabilities.

The specification does not mandate a minimum model size. Capability requirements are functional, not architectural. However, implementations SHOULD document which models have been tested and verified as relay-capable.

#### External Workers

An external worker is a model invoked by a relay member to perform a bounded task. External workers:

- Do NOT interact with the BSS filesystem directly.
- Do NOT read or write blinks.
- Do NOT appear in the roster blink.
- Are invoked by a relay member, perform a specific task (translation, summarization, code generation, data extraction, etc.), and return their output to the invoking relay member.

The relay member that invoked the external worker is the author of any resulting blink. The relay member's sigil appears on the filename. The relay member assesses confidence, scope, and all other metadata based on its evaluation of the external worker's output.

**Rationale:** External workers allow small or specialized models to contribute to a BSS environment without risking graph integrity. A 1B model that excels at translation but cannot reliably parse blink identifiers can still be useful — a relay member delegates translation to it, reviews the output, and encodes the result as a proper blink. The small model is a tool; the relay member is the author.

### 5.6 — The Roster Blink

The roster blink is a system-authored blink (`S` author sigil) in `/profile/` that defines the model registry for a BSS environment. Every relay member reads the roster during step 3 of the startup sequence to understand its own identity, the identities of other participants, and the capabilities and roles of each.

#### Roster Blink Format

The roster blink follows the standard blink file format (Module 4) with a structured summary. This is the one context where the summary uses a semi-structured format rather than pure prose, because the roster must be machine-parseable by every relay member.

```markdown
Born from: Origin

ROSTER

A | [model name/identifier] | [role] | [scope ceiling] | [notes]
B | [model name/identifier] | [role] | [scope ceiling] | [notes]
C | [model name/identifier] | [role] | [scope ceiling] | [notes]

Lineage: [this blink ID]

Links:
```

#### Roster Fields

**Author sigil:** The single-character identifier assigned to this model (matches position 6 of blink identifiers this model will write).

**Model identifier:** The name or version of the model (e.g., `Llama-3-70B`, `Mistral-7B-v0.3`, `Claude-Sonnet`). Informational — used for human reference and debugging, not parsed by models.

**Role:** One of the following:

| Role | Meaning |
|------|---------|
| `primary` | The default relay member. Handles general tasks, initiates work, and processes handoffs. |
| `reviewer` | Reviews work produced by other models. Reads and evaluates but primarily produces assessment blinks rather than new work output. |
| `specialist` | Handles tasks in a specific domain or subdomain. The `notes` field SHOULD specify the specialization. |
| `architect` | Handles global-scope tasks and system-level decisions. Trusted with broad context and cross-domain reasoning. |

Implementations MAY define additional roles. Custom roles MUST be documented in the roster blink's notes or in a separate configuration blink in `/profile/`.

**Scope ceiling:** The maximum scope level this model should attempt to handle independently:

| Ceiling | Meaning |
|---------|---------|
| `atomic` | This model should only handle atomic-scope blinks (`.`). |
| `local` | This model handles up to local-scope blinks (`-`). |
| `regional` | This model handles up to regional-scope blinks (`=`). |
| `global` | This model may engage with global-scope blinks (`!`). |

A model encountering a blink whose scope exceeds its ceiling SHOULD contribute what it can within its competence, write a blink documenting its partial contribution, and hand off to a model with a higher ceiling.

**Notes:** Free-text field for additional guidance. May include domain specializations, known limitations, preferred task types, or behavioral instructions. This field is where implementation-specific model guidance lives — keeping it in the roster means the system prompt can remain minimal.

#### Roster Example

```markdown
Born from: Origin

ROSTER

A | Llama-3.1-70B | primary | global | General-purpose relay lead. Trusted for architecture decisions and complex reasoning.
B | Mistral-7B-v0.3 | specialist | local | Fast inference. Best for code generation, structured output, and bounded tasks.
C | Claude-Sonnet | reviewer | regional | Review and quality assessment. Use for evaluating outputs and catching errors.

Lineage: 00001S~~^!!^;.!=.

Links:
```

#### Roster Update Protocol

When the model roster changes (a model is added, removed, or reconfigured):

1. A new roster blink is written to `/profile/` with the updated registry.
2. The new roster's `Born from` field references the previous roster blink ID.
3. The previous roster blink is moved to `/archive/` (immutability preserved — the old configuration is never deleted).
4. The new roster blink's summary section contains the ROSTER table.

This creates a versioned history of system configuration. Debugging performance changes over time can be traced through the roster lineage.

### 5.7 — Generation Cap & Forced Convergence

A lineage chain — a sequence of blinks connected through `Born from` references — MUST NOT exceed 7 generations without a convergence event.

**The generation rule:**

1. An origin blink (`^` relational sigil) is generation 1.
2. Each subsequent continuation (`+`) or branch (`>`) increments the generation count.
3. At generation 7, the next model in the thread MUST write a convergence blink (`<` relational sigil) instead of a continuation.

**What a convergence blink does:**

The convergence blink synthesizes the preceding chain. Its summary captures the cumulative outcome of the last 7 generations — what was accomplished, what the current state is, and what direction the work is heading. It becomes a clean entry point for any future model that encounters this thread.

During convergence, the authoring model SHOULD:

- Review the summaries of the preceding chain (up to 7 blinks).
- Write a synthesis summary that captures the essential trajectory without requiring a reader to walk the full chain.
- Move parent blink references that are still relevant from `Born from` / `Lineage` into the `Links` field. This preserves access to the historical chain without imposing it on the lineage of future blinks.
- Begin a new lineage starting from the convergence blink.

**After convergence:**

The convergence blink becomes generation 1 of a new chain. The cycle repeats. This creates a looping generation system where long-running tasks are periodically synthesized without losing access to their history.

```
Generation:  1 → 2 → 3 → 4 → 5 → 6 → 7 → CONVERGE → 1 → 2 → ...
Relational:  ^   +   +   +   +   +   +      <          +   +   ...
```

**Rationale:** Without forced convergence, lineage chains grow unbounded. A model entering a thread 50 generations deep would need to walk backwards through dozens of blinks to build context. The 7-generation cap ensures that any active thread is at most 7 hops from a synthesis point. The convergence blink acts as a checkpoint — a compressed summary of everything that came before, with links back to the full history for anyone who needs it.

### 5.8 — Model Instruction Requirements

A BSS-compatible implementation MUST provide relay members with sufficient information to follow the protocol. The exact format and verbosity of this instruction is left to the implementation — different models require different levels of detail.

**Required information (MUST be provided to the model):**

- The four-directory structure and their purposes
- The startup sequence (read order)
- The model's own author sigil
- The blink identifier structure and position map
- The action state definitions
- The file format (Born from, Summary, Lineage, Links)

**Recommended information (SHOULD be provided):**

- The Quick Reference Card (Appendix C)
- The roster blink contents (or a summary of it)
- The current state of `/relay/` (filenames at minimum)

**Information that MUST NOT be in the model's system prompt:**

- Behavioral guidance specific to this model's role — this belongs in the roster blink's notes field, not in the prompt. The system prompt orients the model to BSS. The roster blink tells it how to behave.
- Task-specific instructions — these belong in handoff blinks, not in standing instructions.

**Implementation guidance:** Implementations SHOULD adapt instruction verbosity and encoding assistance to the capabilities of the participating model. The protocol defines what a relay member must produce, not how the implementation helps it get there.

**Rationale:** By keeping the system prompt minimal and putting behavioral guidance in the roster, the protocol becomes self-documenting. A model's behavior is governed by the same blink system it participates in, not by hidden prompt engineering. This also means that changing a model's role requires only a new roster blink, not a prompt redesign.

### 5.9 — Edge Cases & Recovery

#### Empty environment

If a model enters a BSS environment where `/relay/`, `/active/`, and `/profile/` are all empty, this is a fresh environment. The model SHOULD:

1. Write an origin blink (`^` relational sigil) to `/active/` documenting the initial state.
2. Write a roster blink to `/profile/` if model registry information is available.
3. Proceed with the user's task.

#### Broken links

If a blink's `Born from`, `Lineage`, or `Links` field references a blink ID that cannot be found in any directory, the model SHOULD:

- Log or note the broken reference.
- Continue processing the blink using the information available (summary, filename metadata).
- NOT treat the entire blink as invalid — the blink's own content remains trustworthy even if a reference is unresolvable.
- If the broken link is critical to understanding context, write a blink noting the missing reference so future models or the Gardener can investigate.

#### Metadata-content contradiction

If a blink's summary appears to contradict its filename metadata (e.g., the summary says "completed successfully" but the action state is `!!` error), the model SHOULD:

- **Trust the filename over the content.** The filename is the triage layer — it determines how the blink is processed, prioritized, and routed. The summary provides context but the filename is authoritative for metadata.
- Note the contradiction in its own output blink if it affects the current task.

**Rationale:** Filename metadata is structural and mechanically validated. Summary text is natural language and inherently ambiguous. When they conflict, the structured layer takes precedence because it is what the protocol's triage, sequencing, and coordination logic depends on.

#### Oversized relay directory

If `/relay/` contains more than 10 blinks, this indicates a backlog. The model SHOULD:

- Process blinks in the standard triage order (Section 5.2).
- If the backlog exceeds the model's capacity to process in a single session, prioritize by urgency and write a handoff blink summarizing the backlog state for the next model.
- NOT attempt to process all backlogged blinks in one session if doing so would compromise quality.

---

## Module 6 — Graph Dynamics

### 6.1 — Overview

Over time, a BSS environment develops emergent structural properties. These are not enforced by the protocol — they arise naturally from the accumulation of blinks and the links between them. This module defines the vocabulary for these phenomena so that implementations, tools, and companion systems (such as the Gardener) can reference them consistently.

### 6.2 — Convergent Evolution

**Definition:** Two or more blinks that share no direct lineage but independently arrive at overlapping conclusions, themes, or outputs.

**Observable indicators:**

- Matching domain + subdomain + cognitive state combinations in blinks with no shared ancestors.
- Summary text with high semantic overlap in blinks from different lineage branches.

**Significance:** Convergent blinks represent emergent insight — the system discovering connections that no single model or session explicitly created.

### 6.3 — Reinforcement Paths

**Definition:** A blink that is referenced in the `Links` field of multiple other blinks across different time periods and lineage branches.

**Observable indicators:**

- A blink ID appearing in the `Links` field of 3 or more other blinks.
- References spanning multiple sequence ranges (indicating importance over time, not just within one session).

**Significance:** Frequently-referenced blinks carry implicit weight. They are important even if their individual summary seems minor.

### 6.4 — Dormant Reactivation

**Definition:** A blink marked with the `_` (dormant) relational sigil that later becomes relevant when a new thread arrives in the same thematic territory.

**Mechanism:** The dormant blink is never modified. A new blink is created in `/active/` with a `Links` reference to the dormant blink. The new blink's summary explains why the dormant thread has resurfaced. The dormant blink retains its original context permanently; the new blink captures the reason for reactivation.

**Observable indicators:**

- A new blink in `/active/` with a `Links` reference to a dormant (`_`) blink in `/archive/`.
- The new blink's domain or subdomain matches the dormant blink's domain or subdomain.

**Significance:** Dormant reactivation is rediscovery — the system surfacing previously abandoned work that has become relevant again. The immutable pairing of original context and reactivation reason creates a richer record than mutation would.

### 6.5 — Lineage Divergence

**Definition:** A single origin blink that spawns multiple branch (`>`) children which evolve in different thematic directions.

**Observable indicators:**

- An origin blink (`^` relational sigil) with 3 or more branch descendants across different domain sigils.

**Significance:** Lineage divergence records how one idea becomes many. The filesystem preserves the shared ancestry even as descendants become unrecognizable.

### 6.6 — Swarm Self-Governance

**Definition:** The emergent coordination behavior where multiple models contribute to a global-scope task sequentially, each self-limiting to their competence and handing off to the next.

**Observable indicators:**

- A sequence of blinks with `!` (global) scope, different author sigils, and `+` (continuation) relational sigils, forming a chain.
- Each blink in the chain addresses a different aspect of the global task.

**Significance:** Coordination without orchestration. The scope sigil is the governance mechanism — it tells each model to contribute, not to own.

### 6.7 — Generation Cycling

**Definition:** The periodic convergence pattern that emerges from the 7-generation cap (Module 5, Section 5.7), creating a rhythm of accumulation and synthesis across long-running threads.

**Observable indicators:**

- Alternating sequences of continuation (`+`) blinks and convergence (`<`) blinks at regular intervals.
- Convergence blinks whose summaries are notably denser and more synthesized than their predecessors.
- `Links` fields on convergence blinks referencing the chain they summarized.

**Significance:** Generation cycling prevents graph sprawl while preserving history. Over time, the convergence blinks form a "highlights reel" of a thread — a model can read just the convergence points to understand the trajectory of a long-running task without walking every step. The pattern is self-organizing: the 7-generation rule creates it automatically without any model needing to decide when to synthesize.

---

## Module 7 — Compliance Levels

### 7.1 — BSS Core

The minimum required for an implementation to be considered BSS-compatible.

An implementation is BSS Core compliant if it:

- Uses the four-directory filesystem architecture (Module 2)
- Generates blink identifiers conforming to the 17-character grammar (Module 3)
- Generates blink files conforming to the file format (Module 4)
- Enforces immutability (Module 3, Section 3.7)
- Enforces serial write protocol (Module 3, Section 3.8)
- Passes the canonical validation test suite (Module 8, Section 8.1)

### 7.2 — BSS Relay

Requires BSS Core, plus:

- Implements the startup sequence (Module 2, Section 2.2)
- Implements the handoff protocol (Module 5, Section 5.2)
- Implements relay hygiene (Module 5, Section 5.3)
- Implements error escalation (Module 5, Section 5.4)
- Supports the full session lifecycle (Module 5, Section 5.1)
- Enforces the 7-generation cap with forced convergence (Module 5, Section 5.7)
- Provides models with required instruction information (Module 5, Section 5.8)
- Passes the canonical relay test suite (Module 8, Section 8.2)

### 7.3 — BSS Graph

Requires BSS Relay, plus:

- Maintains the `Born from` and `Lineage` fields accurately across blink generations
- Supports the `Links` field for associative references
- Can resolve links across directories (including into `/archive/`)
- Supports participation tiers: relay members and external workers (Module 5, Section 5.5)
- Maintains a roster blink in `/profile/` (Module 5, Section 5.6)
- Passes the canonical graph test suite (Module 8, Section 8.3)

---

## Module 8 — Canonical Test Suite

### 8.1 — Validation Tests (BSS Core)

The following blink identifiers are VALID and MUST be parsed correctly by any conformant implementation:

```
00001A~~^!!=~;,~.    — First blink, Model A, idle, origin, high confidence
0002FB~!>!^#!=~^=    — Blink 95, Model B, handoff, branch, breakthrough
00ZZZU..+.=@&.!..    — User blink, informational, continuation, self-analysis
0000SA~.+=.^~-!!!    — System blink, completed, continuation, in-progress learning
```

The following blink identifiers are INVALID and MUST be rejected:

```
0001A~~^!!=~;,~.     — 16 characters (too short, missing 5th sequence digit)
00001A~~^!!=~;,~..   — 18 characters (too long)
00001a~~^!!=~;,~.    — Lowercase in sequence (position 1-5 must be uppercase)
000010~?^!!=~;,~.    — Invalid action state ~? (position 7-8)
00001A~~*!!=~;,~.    — Invalid relational sigil * (position 9)
```

### 8.2 — Relay Tests (BSS Relay)

The following scenarios define the canonical test cases for BSS Relay compliance. Each test specifies a precondition, an action, and an expected outcome. Implementations MUST pass all tests in this section to claim BSS Relay compliance.

#### 8.2.1 — Startup Sequence Order

**Precondition:** A BSS environment with at least one blink in each of `/relay/`, `/active/`, and `/profile/`.

**Test:** A model performs a cold start.

**Expected:** The model reads directories in the order: `/relay/` → `/active/` → `/profile/`. The implementation MUST log or demonstrate that no blink in `/active/` was read before all filenames in `/relay/` were triaged, and no blink in `/profile/` was read before all filenames in `/active/` were triaged.

#### 8.2.2 — Handoff Write Location

**Precondition:** A model completes work requiring continuation.

**Test:** The model writes a handoff blink.

**Expected:** The blink is written to `/relay/`. The blink's action state is `~!`. The blink's summary describes what was done, what state remains, and what the next model should do.

#### 8.2.3 — Triage Ordering (Default)

**Precondition:** `/relay/` contains the following three blinks:

```
00005A~!=.=#~-~^=    — Sequence 5, urgency ^= (High + Whenever)
00003B~!+!=#!==!!    — Sequence 3, urgency !! (Critical + Blocking)
00007A~!>.=^;^~!^    — Sequence 7, urgency !^ (Critical + Soon)
```

**Test:** A model enters the environment and triages `/relay/`.

**Expected:** Processing order is:
1. `00003B~!+!=#!==!!` — Critical + Blocking (highest urgency)
2. `00007A~!>.=^;^~!^` — Critical + Soon (same priority, higher time sensitivity than #3)
3. `00005A~!=.=#~-~^=` — High + Whenever (lower urgency)

#### 8.2.4 — Triage Ordering (Urgency Tie — Recency Tiebreak)

**Precondition:** `/relay/` contains two blinks with identical urgency compounds:

```
00010A~!+!=#!-~^=    — Sequence 10, urgency ^=
00025B~!>!=#!-~^=    — Sequence 25, urgency ^=
```

**Test:** A model triages `/relay/`.

**Expected:** `00025B~!>!=#!-~^=` is processed first (higher sequence number = more recent). Recency is the second tiebreaker after urgency.

#### 8.2.5 — Triage Ordering (Urgency + Recency Tie — Scope Tiebreak)

**Precondition:** `/relay/` contains two blinks with identical urgency and adjacent sequences (identical sequences are impossible under serial write):

```
00010A~!+!=#!=~^=    — Sequence 10, urgency ^=, scope = (Regional)
00011B~!>!=#!!~^=    — Sequence 11, urgency ^=, scope ! (Global)
```

**Test:** A model triages `/relay/`.

**Expected:** Recency takes precedence over scope (second tiebreaker before third). `00011B~!>!=#!!~^=` is processed first. Scope is the third tiebreaker, used only when urgency and recency are equal — which cannot occur under serial write but may occur in edge cases involving collision resolution.

#### 8.2.6 — Relay Hygiene — Session Output Limit

**Precondition:** A model completes a session producing handoff-worthy output for 5 separate threads.

**Test:** The model attempts to write 5 blinks to `/relay/`.

**Expected:** The model consolidates into no more than 3 blinks in `/relay/`. The implementation produces a single high-scope handoff blink with `Links` referencing supporting blinks written to `/active/`. Total blinks in `/relay/` from this session MUST NOT exceed 3.

#### 8.2.7 — Relay Hygiene — Backlog Warning

**Precondition:** `/relay/` already contains 10 blinks.

**Test:** A model writes an additional handoff blink to `/relay/`.

**Expected:** The implementation logs a warning indicating `/relay/` exceeds the recommended 10-blink limit. The write is not blocked — the warning is advisory.

#### 8.2.8 — Error Blink Creation

**Precondition:** A model encounters an unresolvable error during the WORK phase.

**Test:** The model writes an error blink.

**Expected:**
- The blink is written to `/relay/`.
- Action state is `!!` (error).
- The summary describes what was attempted, what failed, and what the model believes is needed to resolve it.
- Confidence sigil reflects diagnostic certainty (not task confidence).

#### 8.2.9 — Error Escalation Chain

**Precondition:** `/relay/` contains an error blink `00050A!!+~%#-=!!` written by Model A. Model B enters, attempts resolution, and also fails.

**Test:** Model B writes its own error blink.

**Expected:**
- Model B's blink has action state `!!`.
- `Born from` references `00050A!!+~%#-=!!`.
- The summary documents Model B's failed attempt and any additional diagnosis.
- Two consecutive linked `!!` blinks now exist — implementation SHOULD trigger user alerting.

#### 8.2.10 — User Alert Trigger

**Precondition:** Two or more blinks with action state `!!` exist in sequence, connected by `Born from` references, with no intervening non-error blink in that thread.

**Test:** The implementation evaluates the error chain.

**Expected:** The implementation triggers a user alert. The alerting mechanism is implementation-specific, but the trigger condition MUST be detected: two or more linked `!!` blinks with no resolution between them.

#### 8.2.11 — Generation Cap Enforcement

**Precondition:** An active thread has reached generation 7:

```
Gen 1: 00001A~~^!!=~;,~.    (origin, ^)
Gen 2: 00005A.!+!=!=;!~^=   (continuation, +)
Gen 3: 00010B.!+!=!=;!~^=   (continuation, +)
Gen 4: 00015A.!+!=!=;!~^=   (continuation, +)
Gen 5: 00020B.!+!=!=;!~^=   (continuation, +)
Gen 6: 00025A.!+!=!=;!~^=   (continuation, +)
Gen 7: 00030B.!+!=!=;!~^=   (continuation, +)
```

**Test:** The next model continues work on this thread.

**Expected:** The model writes a convergence blink (`<` relational sigil), NOT a continuation (`+`). The convergence blink's summary synthesizes the preceding 7 generations. The convergence blink becomes generation 1 of a new chain.

#### 8.2.12 — Convergence Blink Quality

**Precondition:** A convergence is triggered per 8.2.11.

**Test:** The convergence blink is validated.

**Expected:**
- Relational sigil is `<` (convergence).
- `Born from` references the generation 7 blink (and MAY reference earlier blinks).
- Summary synthesizes cumulative outcome — not merely the last generation's summary.
- `Lineage` begins a new chain starting from this blink.
- `Links` field references key blinks from the preceding chain to preserve access to history.

#### 8.2.13 — Post-Convergence Generation Reset

**Precondition:** A convergence blink has been written per 8.2.11-8.2.12.

**Test:** Two more continuation blinks are written in the same thread.

**Expected:** The generation count restarts from the convergence blink. The convergence blink is generation 1. The two continuations are generations 2 and 3. Forced convergence is not triggered again until generation 7 of the new cycle.

#### 8.2.14 — Session Lifecycle Completeness

**Precondition:** A model is invoked in a populated BSS environment.

**Test:** The model completes a full session.

**Expected:** All five lifecycle phases are executed in order: INTAKE → TRIAGE → WORK → OUTPUT → DORMANCY. The model writes at least one blink during OUTPUT. After DORMANCY, the model retains no state — the blinks are the sole record.

#### 8.2.15 — Model Instruction — Required Information

**Precondition:** An implementation initializes a relay member.

**Test:** The information provided to the model is audited.

**Expected:** The model receives, at minimum:
- The four-directory structure and purposes
- The startup sequence (read order)
- The model's own author sigil
- The blink identifier structure and position map
- The action state definitions
- The file format specification

#### 8.2.16 — Empty Environment Cold Start

**Precondition:** A BSS environment where `/relay/`, `/active/`, and `/profile/` are all empty.

**Test:** A model performs a cold start.

**Expected:** The model writes an origin blink (`^` relational sigil) to `/active/`. If roster information is available, a roster blink is written to `/profile/`. The model proceeds with the user's task.

#### 8.2.17 — Oversized Relay Backlog Handling

**Precondition:** `/relay/` contains 15 blinks spanning multiple urgency levels.

**Test:** A model enters and triages.

**Expected:** The model processes blinks in standard triage order. If it cannot process all 15 in one session, it prioritizes by urgency, processes what it can, and writes a handoff blink summarizing the remaining backlog state. It does NOT attempt to force-process all 15 at the cost of quality.

### 8.3 — Graph Tests (BSS Graph)

The following scenarios define the canonical test cases for BSS Graph compliance. Implementations MUST pass all tests in this section to claim BSS Graph compliance.

#### 8.3.1 — Born From — Single Parent

**Precondition:** Blink `00010A.!+!=!=;!~^=` is written as a continuation of `00005A~~^!!=~;,~.`.

**Test:** The `Born from` field is validated.

**Expected:** `Born from: 00005A~~^!!=~;,~.` — exactly one valid blink ID referencing the parent.

#### 8.3.2 — Born From — Multiple Parents (Convergence)

**Precondition:** Blink `00020A.!<!=#!=~^=` is a convergence of threads led by `00010A.!+!=!=;!~^=` and `00015B.!+!=#!-~^=`.

**Test:** The `Born from` field is validated.

**Expected:** `Born from: 00010A.!+!=!=;!~^= | 00015B.!+!=#!-~^=` — pipe-separated, multiple valid blink IDs. The relational sigil is `<` (convergence).

#### 8.3.3 — Born From — Origin

**Precondition:** A blink is written as an origin node.

**Test:** The `Born from` field is validated.

**Expected:** `Born from: Origin` — the literal string "Origin". The relational sigil is `^`.

#### 8.3.4 — Lineage — Depth Accuracy

**Precondition:** A thread 5 generations deep:

```
Gen 1: 00001A~~^!!=~;,~.
Gen 2: 00005A.!+!=!=;!~^=
Gen 3: 00010B.!+!=!=;!~^=
Gen 4: 00015A.!+!=!=;!~^=
Gen 5: 00020B.!+!=!=;!~^=
```

**Test:** The `Lineage` field of the generation 5 blink is validated.

**Expected:** `Lineage: 00001A~~^!!=~;,~. → 00005A.!+!=!=;!~^= → 00010B.!+!=!=;!~^= → 00015A.!+!=!=;!~^= → 00020B.!+!=!=;!~^=`

All ancestors present. Arrow separator is `→` (U+2192).

#### 8.3.5 — Lineage — Maximum Depth Truncation

**Precondition:** A thread 10 generations deep (post-convergence reset, so within protocol rules). Ancestors span generations 1 through 10.

**Test:** The `Lineage` field of the generation 10 blink is validated.

**Expected:** Lineage contains exactly the 7 most recent ancestors (generations 4 through 10), beginning from the most recent 7. Earlier ancestors are omitted per the maximum depth rule.

#### 8.3.6 — Lineage — Origin Self-Reference

**Precondition:** An origin blink `00001A~~^!!=~;,~.` is written.

**Test:** The `Lineage` field is validated.

**Expected:** `Lineage: 00001A~~^!!=~;,~.` — self-reference only.

#### 8.3.7 — Links — Cross-Directory Resolution

**Precondition:** Blink `00050A.!+!=!=;!~^=` in `/active/` has `Links: 00010B~._.=#~;.=.` where the linked blink resides in `/archive/`.

**Test:** The implementation attempts to resolve the link.

**Expected:** The link resolves successfully. The implementation locates `00010B~._.=#~;.=.` in `/archive/` (or its subdirectories). The linked blink's content is accessible.

#### 8.3.8 — Links — Cross-Directory Resolution Into Archive Subdirectories

**Precondition:** `/archive/` is subdivided: `/archive/2026-Q1/` contains blink `00010B~._.=#~;.=.`. Blink `00050A.!+!=!=;!~^=` in `/active/` links to it.

**Test:** The implementation resolves the link.

**Expected:** The implementation searches across archive subdirectories and locates the blink. Links remain resolvable regardless of archive subdivision scheme.

#### 8.3.9 — Links — Broken Link Handling

**Precondition:** Blink `00050A.!+!=!=;!~^=` has `Links: 00099X~!>!^#!=~^=` but no blink with ID `00099X~!>!^#!=~^=` exists in any directory.

**Test:** The implementation attempts to resolve the link.

**Expected:**
- The broken reference is logged or noted.
- The blink `00050A.!+!=!=;!~^=` is NOT treated as invalid.
- The blink's own content (summary, other links, filename metadata) remains usable.
- The implementation does NOT silently ignore the broken reference.

#### 8.3.10 — Participation Tiers — Relay Member Writes Blink

**Precondition:** Model A is a relay member listed in the roster.

**Test:** Model A writes a blink after completing work.

**Expected:** The blink appears in the filesystem with author sigil `A` (position 6). The blink conforms to the full file format. Model A's sigil matches its roster entry.

#### 8.3.11 — Participation Tiers — External Worker Isolation

**Precondition:** Model A (relay member) invokes Model D (external worker, not in roster) to perform a translation task.

**Test:** Model D produces output. Model A encodes the result as a blink.

**Expected:**
- No blink exists with author sigil `D`.
- Model A writes the blink with its own sigil (`A`).
- Model A assesses confidence, scope, and all metadata based on its evaluation of Model D's output.
- Model D has no direct filesystem interaction.

#### 8.3.12 — Participation Tiers — External Worker Not in Roster

**Precondition:** The roster blink lists Models A, B, and C.

**Test:** The roster is audited for external worker entries.

**Expected:** No external workers appear in the roster. External workers are tools, not participants. Only relay members are listed.

#### 8.3.13 — Roster Blink — Format Compliance

**Precondition:** A roster blink exists in `/profile/`.

**Test:** The roster blink is validated.

**Expected:**
- Author sigil is `S` (system).
- `Born from` is `Origin` (for initial roster) or references the previous roster blink.
- Summary contains the ROSTER table with columns: sigil, model identifier, role, scope ceiling, notes.
- Each role is one of: `primary`, `reviewer`, `specialist`, `architect` (or a documented custom role).
- Each scope ceiling is one of: `atomic`, `local`, `regional`, `global`.

#### 8.3.14 — Roster Update — Immutability Preservation

**Precondition:** Roster blink `00001S~~^!!^;.!=.` exists in `/profile/`. A model is added to the environment.

**Test:** The roster is updated.

**Expected:**
- A new roster blink is written to `/profile/` with the updated registry.
- The new roster's `Born from` references `00001S~~^!!^;.!=.`.
- The original roster blink `00001S~~^!!^;.!=.` is moved to `/archive/` — NOT deleted or modified.
- Both the old and new roster blinks exist in the filesystem with their original content intact.

#### 8.3.15 — Scope Ceiling Enforcement

**Precondition:** Model B has scope ceiling `local` in the roster. Model B encounters blink `00050A~!=.=!!=!^=` with scope `!` (global).

**Test:** Model B processes the global-scope blink.

**Expected:** Model B contributes within its competence, writes a blink documenting its partial contribution, and writes a handoff blink for a model with a higher scope ceiling. Model B does NOT attempt to fully own the global-scope task.

#### 8.3.16 — Metadata-Content Contradiction Resolution

**Precondition:** Blink `00050A!!+~%#-=!!` has action state `!!` (error) but its summary reads "Task completed successfully with no issues."

**Test:** A model encounters this blink during triage.

**Expected:** The model trusts the filename metadata (`!!` = error) over the summary content. The blink is processed as an error. The model MAY note the contradiction in its own output blink.

#### 8.3.17 — Dormant Reactivation via Link

**Precondition:** Blink `00010A~._!=#~;.=.` in `/archive/` has relational sigil `_` (dormant). New work arrives in the same thematic territory.

**Test:** A model reactivates the dormant thread.

**Expected:**
- The dormant blink `00010A~._!=#~;.=.` is NOT modified.
- A new blink is written to `/active/` with a `Links` reference to `00010A~._!=#~;.=.`.
- The new blink's summary explains why the dormant thread has resurfaced.
- The dormant blink retains its original content and location (or remains in `/archive/`).

#### 8.3.18 — Immutability — Reject Rename

**Precondition:** Blink `00050A.!+!=!=;!~^=.md` exists in `/active/`.

**Test:** An operation attempts to rename the file to `00050A~.+!=!=;!~^=.md` (changing action state from `.!` to `~.`).

**Expected:** The operation is rejected. The implementation MUST NOT permit renaming blink files. If state has changed, a new blink must be created.

#### 8.3.19 — Immutability — Reject Content Edit

**Precondition:** Blink `00050A.!+!=!=;!~^=.md` exists with a summary.

**Test:** An operation attempts to modify the summary text within the file.

**Expected:** The operation is rejected. The implementation MUST NOT permit editing blink file contents.

#### 8.3.20 — Immutability — Permit Move

**Precondition:** Blink `00050A~.+!=!=;!~^=.md` exists in `/active/`.

**Test:** The blink is moved to `/archive/`.

**Expected:** The move succeeds. The filename is unchanged. The file content is unchanged. The blink is now accessible at its new path in `/archive/`.

#### 8.3.21 — Blink ID Uniqueness Across Archive Subdivisions

**Precondition:** `/archive/2026-Q1/` contains blink `00010B~._.=#~;.=..md`. An attempt is made to write a new blink with identifier `00010B~._.=#~;.=.` to `/archive/2026-Q2/`.

**Test:** The implementation checks for ID uniqueness.

**Expected:** The write is rejected or flagged. Blink IDs MUST be unique across all directories and subdirectories. The collision is surfaced as an error.

---

## Module 9 — Versioning & Evolution

### 9.1 — Spec Versioning

This specification uses semantic versioning (MAJOR.MINOR):

- **MAJOR** version changes indicate breaking changes to the blink identifier grammar, file format, or directory structure. Blinks written under a previous major version may not be parseable by implementations of the new version without migration.
- **MINOR** version changes indicate additions or clarifications that do not break backward compatibility.

### 9.2 — Backward Compatibility

Implementations of a given major version MUST be able to parse blinks written under any minor version of the same major version.

When a major version change occurs, the specification MUST include a migration guide documenting how blinks from the previous version can be updated.

### 9.3 — Blink Version Identification

The specification does not require blinks to indicate their spec version. Implementations that need version identification SHOULD use a system blink in `/profile/` documenting the spec version in use, rather than adding version information to individual filenames.

---

## Module 10 — Future Scope & Expansion

This module documents capabilities and extensions that are intentionally out of scope for BSS v2.0 but are acknowledged as future work. These items have been considered and deferred — they are not oversights.

The core protocol (Modules 0-9) is designed to remain stable as these extensions are developed. BSS's filesystem-native, model-agnostic foundation supports all of the following without requiring changes to the blink identifier grammar or file format.

### 10.1 — The Gardener (Companion Specification)

An intelligence and maintenance layer that watches the blink filesystem, maintains a search index (FTS5/SQLite), detects convergent evolution, creates cross-links, generates map blinks, and manages archive migration. Defined in a separate companion document (BSS-GARDENER). The Gardener is the recommended path for implementations that need semantic retrieval over blink summaries and automated graph maintenance at scale.

### 10.2 — Network-Based Relay

BSS v2.0 assumes a local or shared filesystem. Future extensions may define how the relay protocol operates over network-connected filesystems, cloud storage backends, or peer-to-peer file synchronization. The protocol's file-based nature makes it inherently compatible with any system that can sync files — git repositories, Syncthing, Dropbox, rsync — but formal guidance on conflict resolution, latency tolerance, and distributed sequence coordination is deferred.

### 10.3 — Inter-Environment Merging

Combining two separate BSS environments into one — merging their blink graphs while preserving lineage integrity, resolving sequence collisions, and reconciling separate roster configurations. This is a complex operation with implications for immutability guarantees and graph consistency. Initial exploration suggests a merge blink type (a new relational sigil) that explicitly documents the union of two graphs, but the design is not yet mature enough for specification.

### 10.4 — Chat Interface Integration

BSS does not prescribe where a model does its work — the interface is transient, the blinks are permanent. A model operating through a chat interface, a terminal, a GUI, or an API call produces the same blinks following the same protocol. Future guidance may define patterns for how chat-based interactions are distilled into blinks after a session concludes — capturing the essential outcomes of a conversation without reproducing the full transcript. The core principle applies: the blink records what mattered and why, not what was said.

### 10.5 — Fine-Tuned BSS Models

Small language models (3-7B parameters) fine-tuned specifically for BSS operations — filename parsing, triage decision-making, well-formed blink generation, and protocol compliance. Training data can be generated synthetically from the specification and supplemented with real-world relay logs from production BSS environments. Fine-tuned BSS models could serve as efficient relay members for bounded tasks, reducing the dependency on large general-purpose models for routine coordination work.

### 10.6 — External Worker Protocols

Formal patterns for how relay members invoke, monitor, and evaluate external workers (Module 5, Section 5.5). This may include standardized task delegation formats, output evaluation criteria, and patterns for batching multiple external worker results into a single blink.

### 10.7 — Blink Visualization Standards

Standardized formats for visual representation of the blink graph — force-directed layouts, lineage tree views, domain clustering, timeline projections. While visualization is implementation-specific, shared conventions for graph export (e.g., DOT format, JSON graph format) would enable interoperability between BSS tools.

---

## Appendix A — Filesystem Compatibility

All sigil characters used in blink identifiers are safe for use in filenames on Windows, macOS, and Linux. The following characters are explicitly excluded from the blink identifier symbol set by design:

```
< > : " / \ | ? *
```

**Note on the pipe character (`|`):** The pipe is excluded from *filenames* (blink identifiers) because it is not safe in Windows filenames. However, it IS used as a separator *inside blink file contents* — in the `Born from`, `Links`, and roster fields. This is safe because file contents have no filesystem character restrictions. The pipe was chosen as the internal separator precisely because it cannot appear in a blink identifier, eliminating any parsing ambiguity.

The complete set of characters used by BSS:

```
Alphanumeric:  0-9 A-Z
Symbols:       ~ ! @ # $ % ^ & _ + - = ; , .
```

## Appendix B — Base-36 Sequence Reference

| Decimal | Base-36 | | Decimal | Base-36 |
|---------|---------|---|---------|---------|
| 1 | 00001 | | 1,000 | 000RS |
| 10 | 0000A | | 10,000 | 007PS |
| 36 | 00010 | | 100,000 | 0255S |
| 100 | 0002S | | 1,000,000 | 0LFLS |
| 999 | 000RR | | 60,466,175 | ZZZZZ |

---

## Appendix C — Quick Reference Card

```
THE BLINK SIGIL SYSTEM — v2.0 QUICK REFERENCE

STRUCTURE (17 characters)
[1-5] Sequence (base-36)  [6] Author  [7-8] Action  [9] Relational
[10] Confidence  [11] Cognitive  [12] Domain  [13] Subdomain
[14] Scope  [15] Maturity  [16-17] Urgency

DIRECTORIES
/relay/    Handoffs. Read first.
/active/   Live work. Read second.
/profile/  User knowledge. Read third.
/archive/  History. Follow links only.

AUTHOR       A-Z = Models  |  U = User  |  S = System

ACTION       ~~ Idle      ~! Handoff   ~. Done      !~ Blocked
             !! Error     !. Decide    .! Progress   .. Info
             .~ User      !# Cancelled

RELATIONAL   ^ Origin   > Branch    < Converge   # Conflict
             = Echo     _ Dormant   + Continue

CONFIDENCE   ! High     . Moderate  ~ Low        , Speculative

COGNITIVE    ! Clarity  ~ Confusion ^ Breakthrough % Frustration
             = Flow     # Tension   . Resolution   & Curiosity

DOMAIN       @ Self     # Work      $ Finance    & Relationships
             ! Creation ~ Learning  % Health     ^ System
             + Play     ; Conflict

SUBDOMAIN    ! Make     ~ Explore   ^ Design     . Maintain
             = Communicate  & Analyze  - Fix    + Grow
             ; Document     , Decide

SCOPE        . Atomic   - Local     = Regional   ! Global

MATURITY     , Seed     ~ In progress  . Near complete
             ! Complete    - Needs revision

PRIORITY     ! Critical ^ High  = Normal  . Low  ~ Background
TIME         ! Blocking ^ Soon  = Whenever  . Passive

FILE FORMAT
Born from: [parent ID(s)] or "Origin"
[2-5 sentence summary — capture WHY, not just WHAT]
Lineage: [ancestor] → ... → [this blink]
Links: [related blink IDs, pipe-separated]
```

---

*The Blink Sigil System is an Alembic AI protocol.*
*Distilling AI coordination to its purest form.*

*Specification version 2.0 — Draft*
*This document is licensed under CC BY 4.0.*
