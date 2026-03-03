# Changelog

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
