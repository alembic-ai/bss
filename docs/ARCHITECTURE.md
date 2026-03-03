# Architecture Overview

This document bridges the [README](../README.md) and the [full specification](../bss_spec/BSS_SPEC_v1.md). Read this to understand how BSS works before diving into the spec.

## System Diagram

```
                        BSS Environment
    ┌──────────────────────────────────────────────────┐
    │                                                  │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
    │  │ /relay/   │  │ /active/ │  │ /profile/│       │
    │  │          │  │          │  │          │       │
    │  │ Handoffs │  │ Live     │  │ Roster & │       │
    │  │ & errors │  │ work     │  │ identity │       │
    │  └─────┬────┘  └─────┬────┘  └─────┬────┘       │
    │        │             │             │             │
    │        └──────┬──────┘             │             │
    │               │                   │             │
    │        ┌──────┴──────┐            │             │
    │        │  Model A    │◄───────────┘             │
    │        │  Session    │                          │
    │        └──────┬──────┘                          │
    │               │                                  │
    │         writes blinks                            │
    │         & artifacts                              │
    │               │                                  │
    │        ┌──────┴──────┐  ┌────────────┐          │
    │        │ /archive/   │  │ /artifacts/│          │
    │        │             │  │            │          │
    │        │ Completed   │  │ Work       │          │
    │        │ threads     │  │ products   │          │
    │        └─────────────┘  └────────────┘          │
    │                                                  │
    └──────────────────────────────────────────────────┘

    Relay flow:  Model A writes handoff → Model B reads /relay/
                 Model B works → writes handoff → Model C reads
                 ...repeat indefinitely
```

## How a Relay Session Works

Every model session follows a five-phase lifecycle. Here's a concrete example — Model A picks up work from Model B:

### 1. INTAKE

Model A starts a session. It reads the filesystem in order:

1. `/relay/` — finds `0000BA~!+!=#!=~~=.md`, a handoff from Model B
2. `/active/` — sees 3 in-progress blinks
3. `/profile/` — reads the roster, confirms its sigil is `A`, role is `primary`, ceiling is `global`

### 2. TRIAGE

Model A sorts `/relay/` blinks by urgency:
- **Priority** first (critical > high > normal > low > background)
- **Sensitivity** breaks ties (blocking > soon > whenever > passive)
- **Recency** as final tiebreaker (higher sequence = more recent)

The handoff from B is the top priority.

### 3. WORK

Model A reads the handoff blink's summary and lineage, understands the context, and does its work. It might write code, analyze data, or continue a research thread.

### 4. OUTPUT

Model A writes its results:
- A blink to `/active/` recording what it did (action state `.!` = progress)
- Optionally an artifact to `/artifacts/` (code file, document, etc.)
- A handoff blink to `/relay/` (action state `~!`) for the next model

### 5. DORMANCY

Model A's session ends. The handoff sits in `/relay/` until the next model picks it up.

## The Blink Identifier

Every blink filename is exactly 17 characters encoding structured metadata. A model can triage the entire environment by reading filenames alone — no file I/O needed.

```
Position map (from BSS Spec Appendix C):

[1-5] Sequence (base-36)  [6] Author  [7-8] Action  [9] Relational
[10] Confidence  [11] Cognitive  [12] Domain  [13] Subdomain
[14] Scope  [15] Maturity  [16-17] Urgency

AUTHOR       A-Z = Models  |  U = User  |  S = System

ACTION       ~~ Idle      ~! Handoff   ~. Done      !~ Blocked
             !! Error     !. Decide    .! Progress   .. Info
             .~ User      !# Cancelled

RELATIONAL   ^ Origin   } Branch    { Converge   # Conflict
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
SENSITIVITY  ! Blocking ^ Soon  = Whenever  . Passive
```

Example: `00030A.!+!=#!=~^=`
- Sequence 00030 (48 in decimal), Author A, Action `.!` (progress), Relational `+` (continue)
- High confidence, breakthrough, work + making, regional scope, in progress, high priority + whenever

## The Artifact System

Artifacts are work products (code, documents, data) linked to blinks. They are a reference implementation convention, not part of the core BSS spec.

See the full [Artifact Integration Spec](../bss_spec/BSS_ARTIFACT_INTEGRATION.md).

### How It Works

Every artifact's filename encodes its parent blink:

```
{sequence}{author}-{slug}.{ext}

Example: 00030A-identifier-parser.py
         ^^^^^^                       ← matches blink 00030A...
                ^^^^^^^^^^^^^^^^^     ← human-readable slug
```

Lookup is bidirectional — find an artifact from its blink or a blink from its artifact — using filename conventions alone. No index or database.

### Key Rules

- One blink produces zero or one artifact
- Artifacts live in `/artifacts/` at the environment root
- Unlike blinks, artifacts CAN be modified (the blink is the immutable record)
- Slug must be lowercase alphanumeric with hyphens only

### CLI Commands

| Command | Purpose |
|---------|---------|
| `bss artifacts` | List all artifacts with parent blink info |
| `bss artifact <seq>` | Show artifact details and parent blink |
| `bss produce <file>` | Register an existing file as an artifact |

## Key Design Decisions

### Immutability

Blinks are never modified, renamed, or deleted. If circumstances change, write a new blink linking to the original. The complete, unaltered history is always preserved. SHA-256 hashes enforce this at the implementation level.

### 7-Generation Cap

When a thread of continuations reaches generation 7, the model MUST write a convergence blink (relational `{`) that synthesizes the thread. This prevents unbounded chains and forces periodic synthesis.

### Triage Ordering

Models sort blinks by filename alone, using a three-level tiebreaker: priority, then sensitivity, then recency. This means a model can assess the entire environment state by listing filenames — before opening a single file.

### Model Independence

BSS does not assume any model architecture, size, or capability. A 1B parameter model and a frontier model interact with the protocol identically. The blink grammar is the shared language.

### Serial Integrity

Only one blink may occupy a given sequence number. Even concurrent models share a single sequence counter, ensuring total ordering of all activity.

## How BSS Differs from Alternatives

| System | Approach | BSS Difference |
|--------|----------|----------------|
| **MCP** | Tool access protocol — lets models call APIs and tools | BSS is coordination, not tool access. Models coordinate through files, not function calls. |
| **AutoGen / CrewAI** | Multi-agent frameworks requiring an orchestrator process | BSS has no orchestrator. Coordination emerges from filesystem conventions. Models don't need to be online simultaneously. |
| **A2A** | Agent-to-agent communication over network protocols | BSS requires no network. It works on a local filesystem with zero infrastructure. |
| **Shared memory / RAG** | Centralized knowledge stores models read from | BSS has no central store. Each blink is a self-contained snapshot. Structure emerges from accumulation. |

BSS is the only filesystem-native, zero-infrastructure coordination protocol. It works anywhere files work — local disk, shared drive, git repo, USB stick.
