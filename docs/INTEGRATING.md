# Integration Guide

Building a BSS implementation in another language? This guide covers what you need to implement and how to verify compliance.

## Compliance Levels

BSS defines three compliance levels (Module 7 of the [specification](../bss_spec/BSS_SPEC_v1.md)). Each level builds on the previous one.

### BSS Core (Level 1)

The minimum for a BSS-compatible implementation. Your implementation must support:

- **Four-directory filesystem** — `/relay/`, `/active/`, `/profile/`, `/archive/` (Module 2)
- **17-character ID grammar** — parse, validate, and generate blink identifiers (Module 3)
- **File format** — read and write blink files with Born from, summary, Lineage, and Links (Module 4)
- **Immutability enforcement** — blinks cannot be modified, renamed, or deleted after creation
- **Serial write protocol** — sequence numbers are strictly ordered, no gaps

**Test requirement:** Pass all Module 8.1 validation tests (4 valid + 5 invalid blink IDs).

### BSS Relay (Level 2)

Requires Core, plus:

- **Startup sequence** — read `/relay/` first, then `/active/`, then `/profile/` (Module 2.2)
- **Handoff protocol** — write handoff blinks with action state `~!` to `/relay/` (Module 5.2)
- **Relay hygiene** — limit output volume, warn on backlog (Module 5.3)
- **Error escalation** — detect and handle error chains (Module 5.4)
- **Session lifecycle** — implement INTAKE → TRIAGE → WORK → OUTPUT → DORMANCY (Module 5.1)
- **7-generation cap** — force convergence at generation 7 (Module 5.7)
- **Model instructions** — provide protocol context to models per Module 5.8

**Test requirement:** Pass all Module 8.2 relay tests (17 test scenarios).

### BSS Graph (Level 3)

Requires Relay, plus:

- **Born from & Lineage accuracy** — correct parent tracking and lineage truncation
- **Links field support** — cross-blink references
- **Cross-directory link resolution** — resolve links across `/relay/`, `/active/`, `/profile/`, and `/archive/`
- **Participation tiers** — relay members vs external workers (Module 5.5)
- **Roster management** — CRUD operations on model roster with scope ceiling enforcement (Module 5.6)

**Test requirement:** Pass all Module 8.3 graph tests (21 test scenarios).

## Canonical Test Suite

The test vectors are defined in **Module 8** of the specification. Do not reproduce them here — always reference the spec as the source of truth so your implementation stays current with spec revisions.

The test suite covers:

| Section | Level | Tests | What It Validates |
|---------|-------|-------|-------------------|
| 8.1 | Core | 9 cases | Blink ID parsing — 4 valid, 5 invalid with specific violations |
| 8.2 | Relay | 17 scenarios | Startup order, handoff, triage, error escalation, generation cap |
| 8.3 | Graph | 21 scenarios | Lineage, links, roster, scope enforcement, immutability |

## Implementation Checklist

### Core Essentials

- [ ] Parse 17-character blink IDs into structured metadata
- [ ] Validate IDs against the positional grammar (report specific violations)
- [ ] Generate valid blink IDs from structured input
- [ ] Base-36 encode/decode for 5-character sequence numbers
- [ ] Read/write blink files in the specified Markdown format
- [ ] Create and validate the four-directory structure
- [ ] Enforce immutability (reject modifications to existing blinks)
- [ ] Maintain sequential ordering (no gaps in sequence numbers)

### Relay Essentials

- [ ] Implement the five-phase session lifecycle
- [ ] Read directories in the correct startup order
- [ ] Write handoff blinks to `/relay/`
- [ ] Sort blinks by triage order (priority → sensitivity → recency)
- [ ] Detect relay backlog (warn at 10+ blinks in `/relay/`)
- [ ] Create error blinks and detect escalation chains
- [ ] Track generations and enforce the 7-generation cap
- [ ] Generate model instruction configs

### Graph Essentials

- [ ] Walk Born from chains to compute generation depth
- [ ] Maintain Lineage fields with correct truncation
- [ ] Resolve Links across all directories
- [ ] Enforce scope ceilings per roster
- [ ] Support roster CRUD with immutable roster blinks

## Artifact Support

Artifact integration is optional — it is a reference implementation convention, not a spec requirement. If you want to support artifacts, see the [Artifact Integration Spec](../bss_spec/BSS_ARTIFACT_INTEGRATION.md).

Key points:
- Artifacts use `{sequence}{author}-{slug}.{ext}` naming
- They live in `/artifacts/` at the environment root
- Bidirectional lookup via naming convention (no index needed)
- Unlike blinks, artifacts are mutable

## Submitting Your Implementation

Built a BSS implementation? To get listed in the community table:

1. Open an issue or PR on the [BSS repository](https://github.com/alembic-ai/bss)
2. Include: language, compliance level claimed, link to your repo
3. Describe which Module 8 test sections your implementation passes
4. We'll review and add it to the README

Implementations in any language are welcome — Rust, Go, TypeScript, Ruby, whatever works for your use case.
