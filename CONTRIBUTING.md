# Contributing to BSS

BSS (Blink Sigil System) is a file-based coordination protocol for stateless AI models. It's built by [Alembic AI](https://github.com/alembic-ai), a small indie AI lab. We welcome contributions — whether you're fixing a bug, building a new backend integration, or porting BSS to another language.

## Types of Contributions

### Spec Proposals

The BSS specification (in `bss_spec/`) defines the protocol itself. Changes here are high-stakes — they affect every implementation.

**Process:**
1. Open an issue with the `spec-proposal` label
2. Describe the problem, your proposed change, and which modules are affected
3. Discussion happens in the issue before any PR is opened
4. Spec changes require consensus and careful review

The spec version (v1.0) and implementation version (v1.0.0) are independent — this is stated in the spec. A spec change does not automatically require an implementation change, and vice versa.

### Implementation Contributions

Bug fixes, new CLI commands, backend integrations, test coverage improvements, performance work. These follow normal PR flow.

**Good first contributions:**
- Adding test cases for edge cases
- Improving error messages in the CLI
- Adding a new model backend in `integrations/providers/`
- Fixing issues on specific platforms

### Community Implementations

Ports to other languages, alternative TUIs, visualization tools, Gardener implementations — these are welcome and encouraged. Community implementations are listed in the README and linked, not merged into this repo.

See the [Integration Guide](docs/INTEGRATING.md) for compliance levels and test requirements.

### Documentation

Always welcome, low barrier to entry. Typo fixes, clarifications, better examples, translations — open a PR directly.

## Development Setup

Follow the install instructions in the [README](README.md). The short version:

```bash
git clone https://github.com/alembic-ai/bss
cd bss
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run tests:

```bash
pytest tests/ -v
```

All 498 tests should pass. If any fail on your setup, that's a bug — please report it.

## Code Style

- Python 3.11+
- Follow existing patterns in `src/bss/`. No external linter config exists yet — keep it consistent with what's there.
- Use type hints where the existing code does.
- Keep core protocol code dependency-free (only `pathlib`, `hashlib`, `dataclasses`, etc.). External dependencies belong in CLI, terminal, or integration code.

## PR Process

1. Fork the repo and create a branch from `master`
2. One logical change per PR — don't bundle unrelated fixes
3. Write descriptive commit messages (e.g., `fix: handle base36 overflow in sequence counter`)
4. Reference related issues in the PR description
5. Make sure `pytest tests/ -v` passes before submitting
6. If your change adds a new feature, add tests for it

## Filing Issues

### Bug Reports

Include:
- OS and version (e.g., Ubuntu 24.04, macOS 15, Windows 11)
- Python version (`python3 --version`)
- Output of `bss --help` (confirms install is working)
- Steps to reproduce
- Expected vs actual behavior

### Feature Requests

Explain the use case first, then the proposed solution. If it touches the spec, note that — spec changes need the `spec-proposal` label and a separate discussion.

## BSS Compliance Testing

If you're contributing a new feature, it must not break compliance with the canonical test suite defined in **Module 8** of the spec:

- **Module 8.1** — Blink ID validation (BSS Core)
- **Module 8.2** — Relay protocol tests (BSS Relay)
- **Module 8.3** — Graph operation tests (BSS Graph)

Run `pytest tests/ -v` and confirm all tests pass.

## Artifact System

The artifact system links work products (code, documents, data) to blinks. If you're building artifact-related features, read the [Artifact Integration Spec](bss_spec/BSS_ARTIFACT_INTEGRATION.md) — it defines naming conventions, directory structure, and CLI integration patterns.

Key points:
- Artifacts use `{sequence}{author}-{slug}.{ext}` naming
- They live in `/artifacts/` at the environment root
- The naming convention IS the link — no index or database

## License

- **Code:** MIT
- **Specification:** CC BY 4.0

By contributing, you agree to these terms.

## Community Standards

- Be respectful. Assume good faith.
- Constructive feedback only — explain why, not just what.
- This is a small project. Response times may vary. We read everything.
