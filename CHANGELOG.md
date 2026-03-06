# Changelog

## v1.1.0 — Immutability Enforcement & Cross-Platform Fixes

### Features
- `bss init --defaults` non-interactive mode for CI/scripting
- Blink immutability enforced at write time (FileExistsError on overwrite)

### Fixes
- Python 3.11 compatibility: f-string backslash in CLI
- Windows compatibility: UTF-8 encoding for roster config round-trip
- Textual tests gracefully skipped when dependency not installed
- pyyaml moved to `[dev]` extras (no longer needs separate install in CI)

### Infrastructure
- CI now passes on all 9 matrix targets (3 OS x 3 Python versions)
- Test count: 498 → 499
- Version bump: 1.0.0 → 1.1.0

## v1.0.1 — Security Hardening & Relay Fix

### Fixes
- Configurable summary sentence minimum for relay mode (fixes #1)
- Artifact slug sanitization prevents path traversal attacks
- Symlink rejection in all filesystem scan and lookup operations
- Born-from parent IDs validated with full grammar check, not just length
- Circular lineage detection in blink validation
- CLI `bss write` validates parent blink ID format before writing
- HTTP credential transmission warning for OpenAI-compatible providers

### Infrastructure
- CI workflow fix: integration tests now run correctly
- Added CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- Added SECURITY.md (vulnerability disclosure process)
- Test count: 487 → 498

## v1.0.0 — Initial Release

### Protocol
- BSS Specification v1.0 (stable)
- 17-character positional blink identifier grammar
- Four-directory filesystem architecture (relay, active, profile, archive)
- Immutable blinks with snapshot semantics
- 7-generation cap with forced convergence
- Five-phase session lifecycle (INTAKE → TRIAGE → WORK → OUTPUT → DORMANCY)
- Three-level triage ordering (priority → sensitivity → recency)
- Three compliance levels: BSS Core, BSS Relay, BSS Graph
- Canonical test suite (Module 8) — 9 validation, 17 relay, 21 graph tests

### Implementation
- Full CLI: init, status, describe, read, write, log, tree, triage, validate
- Roster management: roster, roster-add, roster-update, roster-remove, roster-config
- Artifact system: artifacts, artifact, produce
  - Slug-based naming convention (`{sequence}{author}-{slug}.{ext}`)
  - Bidirectional blink-artifact lookup via filename convention
  - Artifact display integrated into `bss log`, `bss status`, `bss tree`
- Relay terminal TUI with 6 model backends:
  - Local GGUF (via llama-cpp-python)
  - Ollama
  - OpenAI-compatible APIs
  - Anthropic (Claude)
  - Google Gemini
  - Hugging Face
- Integrated setup wizard with auto-discovery
- Cross-platform support: Linux, macOS, Windows
- 487 tests passing

### Documentation
- Full specification with 10 modules and appendices (CC BY 4.0)
- Artifact integration spec (reference implementation convention)
- Per-OS install guides with prerequisites and troubleshooting
- Architecture overview with system diagram and relay walkthrough
- Integration guide for other languages (compliance levels, test requirements)
- Blink pattern recipes (task relay, code review, research, error escalation)
- Contributing guide
