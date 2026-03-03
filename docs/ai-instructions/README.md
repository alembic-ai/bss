# AI Model Instructions

This directory contains model-specific instruction files for AI agents participating in BSS relay sessions. Each file configures a model's identity, rules, and behavior within the Blink Sigil System.

## What These Files Are

When an AI model operates as a BSS relay member, it needs to know its author sigil, role, scope ceiling, and the protocol rules it must follow. These instruction files provide that context in a format each model can consume natively.

For example, `CLAUDE.md` is automatically loaded by Claude Code when working in this repository. Other models have their own conventions for instruction files.

## Generating Configs

The BSS CLI can generate instruction files for any rostered model:

```bash
bss roster-config A            # Print config for model A to stdout
bss roster-config A > CLAUDE.md  # Save to file
```

See `bss roster` to view current roster entries and their sigils.

## Contributing Instruction Files

Contributions of instruction files for other models are welcome:

- **Gemini** — `GEMINI.md`
- **GPT** — `GPT.md`
- **Llama** — `LLAMA.md`
- **Mistral** — `MISTRAL.md`
- Any other model that supports instruction files

Each file should follow the same structure as `CLAUDE.md`: identity block, key rules, and BSS protocol requirements.

## Specification Reference

Model instruction requirements are defined in **Module 5.8** of the [BSS Specification](../../bss_spec/BSS_SPEC_v1.md). Implementations claiming BSS Relay compliance (Level 2) must provide model instructions that satisfy the requirements listed there.
