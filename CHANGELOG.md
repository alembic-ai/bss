# Changelog

## v1.3.0 — DX & Observability

### New Features
- **Structured logging** (`src/bss/bss_logger.py`): `get_logger()` + `configure()` with file handler (audit.log) and console handler; `BSS_LOG_PATH` env var override
- **6 new CLI commands**: `bss health`, `bss archive`, `bss integrity`, `bss export`, `bss clean`, `bss escalation`
- **`bss log --archive`** flag to include archive blinks in output
- **`bss status`** archive size warning when >50 blinks
- **`bss init`** generates `.gitignore` (config.yaml, .bss.lock, .bss_manifest.json, *.pyc)

### Improvements
- Silent failure fixes: 4 bare `except: pass` blocks replaced with structured logging
- All 5 providers log errors on `load()` failure
- Configurable timeouts: `probe_timeout` and `inference_timeout` for OpenAI-compatible provider
- Configurable `round_delay` for RelayRunner
- `bss write` wizard bounds-checks all 10 menu selections
- `bss write` wraps `write_blink()` in try/except for ValueError/FileExistsError
- `bss relay` / `bss gateway` show friendly error on missing textual dependency
- Discovery defaults updated: Anthropic → `claude-opus-4-6`, Gemini → `gemini-2.5-flash`

### License
- Unified license: entire codebase now CC BY 4.0 (was MIT code + CC BY 4.0 spec)

### Tests
- 561 tests passing (up from 513)
- New test file: `tests/test_cli_commands.py` (34 tests)

---

## v1.2.0 — Security Hardening

### Security
- File size guard on blink reads (rejects files > 10 MB)
- File-based sequence locking (`fcntl.flock` / `msvcrt.locking`) prevents race conditions
- HTTP + API key to remote hosts blocked (`ValueError` raised; localhost exempted)
- Atomic artifact registration with `O_CREAT | O_EXCL` prevents TOCTOU races
- Recursive directory listing depth-limited to 3 levels (DoS prevention)
- Blink files written with `0o644` permissions on Unix
- Config files written with `0o600` permissions on Unix
- Persistent integrity manifest (`.bss_manifest.json`) for cross-session tampering detection
- Lineage validation guards in relay handoff, error blink, and session write
- Generation walk loop bounded to 50 iterations (prevents infinite loops)
- Standardized API key masking via `_mask_key()` helper
- Thread-safe `ModelManager.reload()` (deadlock fix)
- Thread-safe `RelayRunner.auto_run()` with locked results and exception handling
- `RelayRunner.stop()` joins thread and clears reference

### Documentation
- Added `SECURITY_GAPS.md` documenting all mitigations and known remaining gaps
- Scalability gaps documented (score: 45/100) with mitigation paths
- Observability gaps documented (score: 20/100) with mitigation paths

### Infrastructure
- Test count: 499 → 513

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
