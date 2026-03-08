# BSS — Blink Sigil System

A file-based coordination protocol for stateless AI models. Each "blink" is a Markdown file whose 17-character filename encodes structured metadata — author, action state, confidence, scope, and more — while the file body carries a natural-language summary and lineage graph. No database, no API, no shared memory. Just files.

## Install

Requires **Python 3.11+** and **git**.

<details>
<summary><strong>Linux (Debian / Ubuntu)</strong></summary>

#### Prerequisites

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

Check your version:

```bash
python3 --version  # must be 3.11 or higher
```

> On older releases (e.g. Ubuntu 22.04) the default Python may be 3.10.
> Install a newer version via the [deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa):
> ```bash
> sudo add-apt-repository ppa:deadsnakes/ppa
> sudo apt install python3.12 python3.12-venv
> ```
> Then substitute `python3.12` for `python3` below.

#### Install

```bash
git clone https://github.com/alembic-ai/bss
cd bss
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

#### Verify

```bash
bss --help
bss init
```

#### Troubleshooting

- **`externally-managed-environment` error** — You forgot the venv step. Modern Debian/Ubuntu (PEP 668) blocks system-wide pip installs. Always create and activate a virtual environment first.
- **`python3-venv` not found** — Run `sudo apt install python3-venv`.

</details>

<details>
<summary><strong>macOS</strong></summary>

#### Prerequisites

Install Python 3.11+ via [Homebrew](https://brew.sh):

```bash
brew install python@3.12 git
```

Or download from [python.org](https://www.python.org/downloads/).

Check your version:

```bash
python3 --version  # must be 3.11 or higher
```

> macOS includes Python via Xcode Command Line Tools, but it may be an older version. Use `brew install` to get 3.12+.

#### Install

```bash
git clone https://github.com/alembic-ai/bss
cd bss
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

#### Verify

```bash
bss --help
bss init
```

#### Troubleshooting

- **`python3: command not found`** — Install Xcode CLI tools (`xcode-select --install`) or use Homebrew.
- **Old Python version** — `brew install python@3.12` and use `python3.12` instead of `python3` when creating the venv.

</details>

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

#### Prerequisites

Install Python 3.11+ and git. Using [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/):

```powershell
winget install Python.Python.3.12
winget install Git.Git
```

Or download from [python.org](https://www.python.org/downloads/) and [git-scm.com](https://git-scm.com). During Python install, check **"Add python.exe to PATH"**.

Restart your terminal after installing, then check:

```powershell
python --version  # must be 3.11 or higher
```

#### Install

```powershell
git clone https://github.com/alembic-ai/bss
cd bss
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

#### Verify

```powershell
bss --help
bss init
```

#### Troubleshooting

- **`Activate.ps1 cannot be loaded because running scripts is disabled`** — Run this once as Administrator, then retry:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
- **`python` not found** — Ensure you checked "Add python.exe to PATH" during install, or add it manually. Restart your terminal.
- **`python` opens the Microsoft Store** — Remove the App Execution Alias: Settings > Apps > Advanced app settings > App execution aliases > toggle off "python.exe" and "python3.exe".

</details>

## Quickstart

```bash
# Initialize a BSS environment
bss init

# View environment status
bss status

# Decode a blink identifier
bss describe 00001U~~^!!^;!!=.

# Read a blink file
bss read 00001U~~^!!^;!!=.

# Write a new blink (interactive wizard)
bss write

# View the blink timeline
bss log

# View lineage tree for a blink
bss tree 00009A~~}!.^;!!=.

# Triage relay blinks by urgency
bss triage

# Validate a blink identifier
bss validate 00001U~~^!!^;!!=.

# View model roster
bss roster

# List all artifacts
bss artifacts

# Show artifact details
bss artifact 00001

# Register a file as an artifact
bss produce mycode.py --blink 00001A~~^!!^;!!=. --slug my-module

# Add a model to the roster
bss roster-add B Model-B --role specialist --ceiling regional

# Update a roster entry
bss roster-update B --ceiling global

# Remove a model from the roster
bss roster-remove B

# Generate CLAUDE.md-style config for a model
bss roster-config A --output CLAUDE.md
```

## Relay Terminal

The relay terminal is a TUI that lets models take turns reading the relay, running inference, and writing handoff blinks. It supports 6 backends: local GGUF, Ollama, OpenAI-compatible APIs, Anthropic, Google Gemini, and Hugging Face.

### First Run

```bash
# Launch — auto-detects missing config and opens the setup wizard
bss relay

# Force setup even if config exists
bss relay --setup
```

The integrated setup wizard auto-discovers available backends (scans for GGUF files, probes Ollama/LM Studio endpoints, checks for API keys in env vars), then walks you through configuration. You can re-open it mid-session with `/setup`.

### Model Backends

| Backend | Config | Requires |
|---------|--------|----------|
| **GGUF** | `backend: gguf`, `path: ~/mind/model.gguf` | `llama-cpp-python` |
| **Ollama** | `backend: openai`, `base_url: http://localhost:11434/v1` | Ollama running |
| **OpenAI-compat** | `backend: openai`, `base_url: ...`, `api_key: ...` | API access |
| **Anthropic** | `backend: anthropic`, `model: claude-sonnet-4-20250514` | `anthropic` + API key |
| **Gemini** | `backend: gemini`, `model: gemini-2.0-flash` | `google-genai` + API key |
| **Hugging Face** | `backend: huggingface`, `model: mistralai/Mistral-7B-Instruct-v0.3` | `huggingface-hub` |

Install provider extras as needed:

```bash
pip install -e ".[anthropic]"      # Anthropic only
pip install -e ".[gemini]"         # Gemini only
pip install -e ".[all-providers]"  # Everything
```

See `integrations/config.example.yaml` for full config reference.

### Models Directory

By convention, GGUF files live in a `mind/` directory alongside the BSS environment. The setup wizard scans this location automatically:

```
project/
├── mind/              # Your .gguf model files
│   ├── Qwen3-4B-Q4_K_M.gguf
│   └── Qwen3-8B-Q4_K_M.gguf
├── relay/
├── active/
└── ...
```

## This Repo Built Itself

The `/archive/foundation/` and `/active/` directories contain the blinks written *during* the construction of this very implementation. Each level of the build — identifier engine, file engine, relay protocol, CLI — produced blinks that tracked decisions, breakthroughs, and bugs as they happened.

Start exploring:
- `bss read 00007A~~}!.^;!!=.` — How the identifier engine was built
- `bss read 00008A~~}!.^;!!=.` — How the relay protocol was implemented
- `bss read 00009A~~}!.^;!!=.` — How the CLI was designed

Trace the full lineage: `bss tree 00009A~~}!.^;!!=.`

## Directory Structure

```
bss/
├── relay/        # Handoff & error blinks between sessions
├── active/       # Current work blinks
├── profile/      # Model roster and identity blinks
├── archive/      # Completed work, organized by thread
│   └── foundation/  # The build archive that ships with this repo
├── artifacts/    # Files linked to blinks
└── bss_spec/     # Protocol specification
```

## Specification

The full BSS specification is in `bss_spec/BSS_SPEC_v1.md`. Key concepts:

- **17-character positional grammar** — Every blink ID encodes sequence, author, action state, relational type, confidence, cognitive state, domain, subdomain, scope, maturity, priority, and sensitivity
- **Four directories** — `/relay/`, `/active/`, `/profile/`, `/archive/`
- **Immutable blinks** — Never modified, renamed, or deleted
- **7-generation cap** — Threads converge after 7 continuations
- **Five-phase session lifecycle** — INTAKE, TRIAGE, WORK, OUTPUT, DORMANCY
- **Triage ordering** — Urgency, then recency, then scope
- **Artifact system** — Files linked to blinks via the `artifacts/` directory, with slug-based naming and full lineage tracking (see [Artifact Integration Spec](bss_spec/BSS_ARTIFACT_INTEGRATION.md))

## License

CC BY 4.0 (Creative Commons Attribution 4.0 International)

## Community

### Implementations & Tools

| Project | Language | Type | Compliance | Link |
|---------|----------|------|------------|------|
| *Your project here* | — | — | — | [Submit yours](CONTRIBUTING.md) |

Built something with BSS? Open an issue or PR to get listed.

### Resources

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Integration Guide](docs/INTEGRATING.md)
- [Blink Patterns](docs/PATTERNS.md)
- [Full Specification](bss_spec/BSS_SPEC_v1.md)
- [Artifact Integration Spec](bss_spec/BSS_ARTIFACT_INTEGRATION.md)
