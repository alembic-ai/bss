# BSS Reference Implementation

You are building the reference implementation of the Blink Sigil System.
Read bss_spec/BSS_SPEC_v3.0.md for the full protocol specification.
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
