"""BSS Relay Terminal — Textual TUI for relay visualization and model interaction.

Adapted from Athanor v2 interface.py. Stripped down and BSS-themed.
"""

from __future__ import annotations

import threading
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Input, RichLog, Static, Footer
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.reactive import reactive
from rich.text import Text

from src.bss.environment import BSSEnvironment
from src.bss.identifier import parse as parse_id, base36_decode
from src.bss.roster import read_roster, update_roster, RosterEntry
from src.bss.sigils import ACTION_STATES

from integrations.models import ModelManager
from integrations.runner import RelayRunner
from integrations.setup import has_config
from terminal.setup_screen import SetupScreen

# ── COLOURS ──────────────────────────────────────────────────

C = {
    "blue":     "#64B5F6",
    "amber":    "#FF8F00",
    "white":    "#F5F5F5",
    "dim":      "#6B6B6B",
    "silver":   "#9E9E9E",
    "border":   "#3A3A3A",
    "success":  "#2E7D32",
    "warn":     "#F57F17",
    "danger":   "#B71C1C",
    "manual":   "#64B5F6",
    "auto":     "#CE93D8",
    "user":     "#81C784",
}

THINKING = ["●○○", "●●○", "●●●", "○●●", "○○●", "○○○"]


# ── STATE ────────────────────────────────────────────────────

class RelayState:
    def __init__(self):
        self.messages: list[dict] = []
        self.active_sigil: str | None = None
        self.thinking: bool = False
        self.think_frame: int = 0
        self.mode: str = "manual"  # manual | auto
        self.current_round: int = 0
        self.max_rounds: int = 10
        self.last_active: str = "A"
        # Model status tracking
        self.model_status: dict[str, str] = {}  # sigil -> "rest" | "thinking" | "loaded"


# ── INPUT WIDGET ─────────────────────────────────────────────

class RelayInput(Input):
    DEFAULT_CSS = """
    RelayInput { background: #0A0A0A; border: none; color: #64B5F6; height: 3; padding: 0 1; }
    RelayInput:focus { border: none; color: #64B5F6; background: #111111; }
    RelayInput>.input--placeholder { color: #3A3A3A; }
    RelayInput>.input--cursor      { color: #64B5F6; background: #1A2A3A; }
    """


# ── CSS ──────────────────────────────────────────────────────

CSS = """
Screen { background: #0A0A0A; }
#header { height: 3; background: #111111; border: heavy #3A3A3A; content-align: center middle; color: #64B5F6; text-style: bold; }
#body { height: 1fr; }
#dashboard { width: 32; border: heavy #3A3A3A; background: #0A0A0A; padding: 1 1; }
#chat-panel { border: heavy #3A3A3A; background: #0A0A0A; padding: 0 1; }
#chat-log { height: 1fr; background: #0A0A0A; scrollbar-color: #3A3A3A; scrollbar-background: #0A0A0A; }
#input-bar { height: auto; max-height: 5; border-top: solid #3A3A3A; background: #0A0A0A; padding: 0 1; }
Footer { background: #111111; color: #3A3A3A; height: 1; }
"""


# ── DASHBOARD ────────────────────────────────────────────────

class Dashboard(Static):
    frame = reactive(0)

    def __init__(self, env: BSSEnvironment, model_manager: ModelManager, state: RelayState, **kwargs):
        super().__init__(**kwargs)
        self.env = env
        self.model_manager = model_manager
        self.state = state

    def on_mount(self):
        self.set_interval(0.3, self.tick)

    def tick(self):
        if self.state.thinking:
            self.state.think_frame += 1
        self.frame = self.state.think_frame
        self.refresh()

    def render(self) -> Text:
        t = Text()

        # Mode indicator
        mode_col = C["manual"] if self.state.mode == "manual" else C["auto"]
        t.append(f"  {self.state.mode.upper()}\n", style=f"bold {mode_col}")
        t.append("  " + "─" * 24 + "\n\n", style=C["dim"])

        # Relay
        t.append("  RELAY\n", style=f"bold {C['silver']}")
        t.append("  " + "─" * 24 + "\n", style=C["dim"])
        relay_count = self.env.relay_count()
        t.append(f"  blinks    {relay_count}\n", style=C["blue"] if relay_count else C["dim"])

        # Latest relay blink summary
        triaged = self.env.triage("relay")
        if triaged:
            latest = triaged[0]
            summary = latest.summary.replace("\n", " ")[:40]
            try:
                meta = parse_id(latest.blink_id)
                t.append(f"  latest    {meta.author} · {latest.blink_id[6:8]}\n", style=C["dim"])
            except ValueError:
                pass
            t.append(f"  \"{summary}\"\n", style=C["dim"])

        # Models
        t.append("\n  MODELS\n", style=f"bold {C['silver']}")
        t.append("  " + "─" * 24 + "\n", style=C["dim"])
        models = self.model_manager.available_models
        for sigil, cfg in models.items():
            color = cfg.get("color", C["white"])
            name = cfg.get("name", sigil)
            is_thinking = self.state.active_sigil == sigil and self.state.thinking

            t.append(f"  {sigil}  ", style=f"bold {color}")
            t.append(f"{name:<12}", style=color)

            if is_thinking:
                frame = THINKING[self.state.think_frame % len(THINKING)]
                t.append(f" {frame}\n", style=f"bold {color}")
            elif self.model_manager.is_loaded(sigil):
                t.append(" ● loaded\n", style=C["success"])
            else:
                t.append(" ○ rest\n", style=C["dim"])

        # Environment
        t.append("\n  ENVIRONMENT\n", style=f"bold {C['silver']}")
        t.append("  " + "─" * 24 + "\n", style=C["dim"])
        for dirname in ["relay", "active", "profile", "archive"]:
            count = len(list((self.env.root / dirname).glob("*.md")))
            t.append(f"  /{dirname}/  {count}\n", style=C["dim"])
        t.append(f"  next seq  {self.env.next_sequence()}\n", style=C["dim"])

        # Auto mode info
        if self.state.mode == "auto" and self.state.thinking:
            t.append("\n  " + "─" * 24 + "\n", style=C["dim"])
            t.append(f"  round {self.state.current_round}/{self.state.max_rounds}\n", style=C["warn"])

        # Keys
        t.append("\n  " + "─" * 24 + "\n", style=C["dim"])
        t.append("  Ctrl+X · interrupt\n", style=C["dim"])
        t.append("  Ctrl+E · exit\n", style=C["dim"])
        t.append("  /help  · commands\n", style=C["dim"])

        return t


# ── APP ──────────────────────────────────────────────────────

class BSSRelayApp(App):
    CSS = CSS
    BINDINGS = [
        Binding("ctrl+e", "exit_app",  "Exit",      show=True),
        Binding("ctrl+x", "interrupt", "Interrupt",  show=True),
    ]

    def __init__(self, path: Path | None = None, config_path: str | None = None, force_setup: bool = False):
        super().__init__()
        self.env = BSSEnvironment(path or Path.cwd())
        self._config_path = config_path
        self._no_models = not has_config(config_path)
        self._force_setup = force_setup
        self.model_manager = ModelManager(config_path)
        self.runner = RelayRunner(self.env, self.model_manager)
        self.state = RelayState()
        self._lmc = 0

        # Populate model status
        for sigil in self.model_manager.available_models:
            self.state.model_status[sigil] = "rest"

    def compose(self) -> ComposeResult:
        yield Static("BSS  ·  RELAY TERMINAL", id="header")
        with Horizontal(id="body"):
            yield Dashboard(self.env, self.model_manager, self.state, id="dashboard")
            with Vertical(id="chat-panel"):
                yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
                with Vertical(id="input-bar"):
                    yield RelayInput(placeholder="relay ›", id="relay-input")
        yield Footer()

    def on_mount(self):
        self.query_one("#relay-input").focus()
        if self._force_setup or self._no_models:
            self._open_setup()
        else:
            self._welcome()
        self.set_interval(0.5, self._poll)

    def _welcome(self):
        log = self.query_one("#chat-log", RichLog)
        t = Text()
        t.append("\n  BSS Relay Terminal\n", style=f"bold {C['blue']}")
        t.append("  " + "─" * 50 + "\n\n", style=C["dim"])

        if self._no_models:
            t.append("  No models configured.\n", style=f"bold {C['warn']}")
            t.append("  Run [bold]/setup[/bold] to add models.\n\n", style=C["silver"])

        # Show available models
        models = self.model_manager.available_models
        for sigil, cfg in models.items():
            color = cfg.get("color", C["white"])
            name = cfg.get("name", sigil)
            t.append(f"  {sigil}  {name}  · ", style=f"bold {color}")
            t.append("ready\n", style=C["dim"])

        t.append("\n", style=C["dim"])

        # Show roster if available
        roster = read_roster(self.env)
        if roster:
            for entry in roster.entries:
                sigil_color = models.get(entry.sigil, {}).get("color", C["white"])
                t.append(f"  {entry.sigil}  ", style=f"bold {sigil_color}")
                t.append(f"{entry.model_id} · {entry.role} · {entry.scope_ceiling}\n", style=C["silver"])
            t.append("\n", style=C["dim"])

        # Show environment state
        relay_count = self.env.relay_count()
        if relay_count > 0:
            t.append(f"  /relay/ has {relay_count} blink(s) pending.\n\n", style=C["blue"])

        # Commands
        t.append("  [type]         → message to last active model\n", style=C["silver"])
        t.append("  /invoke        → list available models\n", style=C["silver"])
        t.append("  /invoke <S>    → wake model S\n", style=C["silver"])
        t.append("  /chat <S> msg  → direct message to model S\n", style=C["silver"])
        t.append("  /auto          → start auto relay\n", style=C["silver"])
        t.append("  /stop          → interrupt auto mode\n", style=C["silver"])
        t.append("  /status        → environment dashboard\n", style=C["silver"])
        t.append("  /relay         → show relay contents\n", style=C["silver"])
        t.append("  /log           → recent blink timeline\n", style=C["silver"])
        t.append("  /setup         → model setup wizard\n", style=C["silver"])
        t.append("  /help          → all commands\n\n", style=C["silver"])
        t.append("  " + "─" * 50 + "\n", style="#2A2A2A")
        log.write(t)

    def _poll(self):
        """Poll for new messages from background threads."""
        log = self.query_one("#chat-log", RichLog)
        if len(self.state.messages) > self._lmc:
            for msg in self.state.messages[self._lmc:]:
                self._render_message(log, msg)
            self._lmc = len(self.state.messages)
            log.scroll_end(animate=False)

    def _render_message(self, log: RichLog, msg: dict):
        t = Text()
        role = msg["role"]
        colour = msg.get("colour", C["white"])
        sigil = msg.get("sigil", "·")
        name = msg.get("name", "")

        t.append(f"\n  {sigil}  ", style=f"bold {colour}")
        if name:
            t.append(f"{name}  ", style=f"bold {colour}")
        t.append("· ", style=C["dim"])
        t.append(f"{msg['text']}\n", style=C["blue"] if role == "user" else C["white"])
        if role != "user":
            t.append("  " + "─" * 50 + "\n", style="#2A2A2A")
        log.write(t)

    # ── COMMANDS ──

    def _help(self):
        log = self.query_one("#chat-log", RichLog)
        t = Text()
        t.append("\n  COMMANDS\n", style=f"bold {C['blue']}")
        t.append("  " + "─" * 50 + "\n\n", style=C["dim"])
        t.append("  INVOKE\n", style=f"bold {C['silver']}")
        t.append("  [just type]       → message to last active model\n", style=C["white"])
        t.append("  /invoke           → list available models\n", style=C["white"])
        t.append("  /invoke <sigil>   → wake a model (reads relay, responds)\n", style=C["white"])
        t.append("  /chat <S> <msg>   → direct message to model S\n\n", style=C["white"])
        t.append("  AUTO\n", style=f"bold {C['silver']}")
        t.append("  /auto             → start auto relay alternation\n", style=C["white"])
        t.append("  /auto 5           → auto mode, max 5 rounds\n", style=C["white"])
        t.append("  /stop             → interrupt auto mode\n\n", style=C["white"])
        t.append("  INFO\n", style=f"bold {C['silver']}")
        t.append("  /status           → environment dashboard\n", style=C["white"])
        t.append("  /relay            → show triaged relay contents\n", style=C["white"])
        t.append("  /log              → recent blink timeline\n", style=C["white"])
        t.append("  /setup            → model setup wizard\n", style=C["white"])
        t.append("  /help             → this screen\n", style=C["white"])
        t.append("  /clear            → clear chat\n\n", style=C["white"])
        t.append("  CONTROLS\n", style=f"bold {C['silver']}")
        t.append("  Ctrl+X  → interrupt    Ctrl+E  → exit\n\n", style=C["white"])
        t.append("  " + "─" * 50 + "\n", style="#2A2A2A")
        log.write(t)

    def _show_status(self):
        log = self.query_one("#chat-log", RichLog)
        t = Text()
        t.append("\n  ENVIRONMENT\n", style=f"bold {C['blue']}")
        t.append("  " + "─" * 50 + "\n\n", style=C["dim"])
        t.append(f"  Root     · {self.env.root}\n", style=C["white"])
        t.append(f"  Valid    · {self.env.is_valid()}\n\n", style=C["white"])

        for dirname in ["relay", "active", "profile", "archive"]:
            count = len(list((self.env.root / dirname).glob("*.md")))
            t.append(f"  /{dirname}/  {count} blinks\n", style=C["white"])

        t.append(f"\n  Next sequence: {self.env.next_sequence()}\n", style=C["white"])

        ms = self.model_manager.status()
        t.append(f"\n  Loaded model: {ms['loaded'] or 'none'}\n", style=C["white"])
        t.append(f"  Available: {', '.join(ms['available'])}\n\n", style=C["white"])
        t.append("  " + "─" * 50 + "\n", style="#2A2A2A")
        log.write(t)

    def _show_relay(self):
        log = self.query_one("#chat-log", RichLog)
        triaged = self.env.triage("relay")
        t = Text()
        t.append("\n  RELAY\n", style=f"bold {C['blue']}")
        t.append("  " + "─" * 50 + "\n\n", style=C["dim"])

        if not triaged:
            t.append("  /relay/ is empty. No handoffs pending.\n\n", style=C["dim"])
        else:
            t.append(f"  {len(triaged)} blink(s) in triage order:\n\n", style=C["silver"])
            for i, blink in enumerate(triaged, 1):
                try:
                    meta = parse_id(blink.blink_id)
                    action = blink.blink_id[6:8]
                    action_label = ACTION_STATES.get(action, "?")
                    summary = blink.summary.replace("\n", " ")
                    if len(summary) > 60:
                        summary = summary[:57] + "..."

                    models = self.model_manager.available_models
                    color = models.get(meta.author, {}).get("color", C["white"])
                    t.append(f"  {i}. ", style=C["dim"])
                    t.append(f"{meta.author} ", style=f"bold {color}")
                    t.append(f"{action} ", style=C["white"])
                    t.append(f"{action_label}\n", style=C["silver"])
                    t.append(f"     \"{summary}\"\n\n", style=C["dim"])
                except ValueError:
                    t.append(f"  {i}. {blink.blink_id} (parse error)\n\n", style=C["dim"])

        t.append("  " + "─" * 50 + "\n", style="#2A2A2A")
        log.write(t)

    def _show_log(self, count: int = 10):
        log = self.query_one("#chat-log", RichLog)
        t = Text()
        t.append("\n  BLINK LOG\n", style=f"bold {C['blue']}")
        t.append("  " + "─" * 50 + "\n\n", style=C["dim"])

        # Collect all blinks
        all_blinks = []
        for dirname in ["relay", "active", "profile"]:
            for blink in self.env.scan(dirname):
                all_blinks.append((dirname, blink))

        all_blinks.sort(
            key=lambda x: base36_decode(x[1].blink_id[:5]) if len(x[1].blink_id) >= 5 else 0,
            reverse=True,
        )

        shown = all_blinks[:count]
        if not shown:
            t.append("  No blinks found.\n\n", style=C["dim"])
        else:
            for dirname, blink in shown:
                try:
                    meta = parse_id(blink.blink_id)
                    action = blink.blink_id[6:8]
                    summary = blink.summary.replace("\n", " ")[:45]

                    models = self.model_manager.available_models
                    color = models.get(meta.author, {}).get("color", C["silver"])

                    t.append(f"  {meta.sequence} ", style=C["dim"])
                    t.append(f"{meta.author} ", style=f"bold {color}")
                    t.append(f"{action} ", style=C["white"])
                    t.append(f"/{dirname}/ ", style=C["dim"])
                    t.append(f"\"{summary}\"\n", style=C["dim"])
                except ValueError:
                    t.append(f"  {blink.blink_id[:5]} ? ?? \"{blink.summary[:30]}\"\n", style=C["dim"])

        t.append("\n  " + "─" * 50 + "\n", style="#2A2A2A")
        log.write(t)

    # ── SETUP ──

    def _open_setup(self):
        """Push the SetupScreen for model configuration."""
        existing = {"models": dict(self.model_manager.available_models)}
        screen = SetupScreen(
            config_path=self._config_path,
            existing_config=existing,
        )
        self.push_screen(screen, callback=self._on_setup_complete)

    def _on_setup_complete(self, config_path: str | None) -> None:
        """Callback when SetupScreen is dismissed."""
        if config_path:
            self._config_path = config_path
            self.model_manager.reload(config_path)
            self.runner = RelayRunner(self.env, self.model_manager)
            self._no_models = False

            # Auto-sync roster with configured models
            self._sync_roster()

            # Refresh model status
            self.state.model_status.clear()
            for sigil in self.model_manager.available_models:
                self.state.model_status[sigil] = "rest"

            log = self.query_one("#chat-log", RichLog)
            log.clear()
            self._welcome()

    def _sync_roster(self) -> None:
        """Ensure all configured model sigils exist in the BSS roster."""
        models = self.model_manager.available_models
        if not models:
            return

        roster = read_roster(self.env)
        existing_sigils = {e.sigil for e in roster.entries} if roster else set()
        old_entries = list(roster.entries) if roster else []
        old_id = roster.blink_id if roster else None

        new_entries = list(old_entries)
        added = []

        for sigil, cfg in models.items():
            if sigil not in existing_sigils:
                is_first = len(new_entries) == 0
                entry = RosterEntry(
                    sigil=sigil,
                    model_id=cfg.get("name", sigil),
                    role="primary" if is_first else "reviewer",
                    scope_ceiling="global" if is_first else "local",
                    notes=f"{cfg.get('backend', 'unknown')} backend",
                )
                new_entries.append(entry)
                added.append(sigil)

        if added:
            update_roster(self.env, new_entries, old_roster_id=old_id)

    # ── INPUT HANDLING ──

    def on_input_submitted(self, event: Input.Submitted):
        raw = event.value.strip()
        event.input.value = ""
        if not raw:
            return

        if raw.lower() == "/setup":
            self._open_setup()
            return
        if raw.lower() == "/help":
            self._help()
            return
        if raw.lower() == "/clear":
            log = self.query_one("#chat-log", RichLog)
            log.clear()
            self._welcome()
            return
        if raw.lower() == "/status":
            self._show_status()
            return
        if raw.lower() == "/relay":
            self._show_relay()
            return
        if raw.lower().startswith("/log"):
            parts = raw.split()
            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
            self._show_log(count)
            return
        if raw.lower() == "/stop":
            self.runner.stop()
            self.state.thinking = False
            self.state.active_sigil = None
            self.state.mode = "manual"
            self.state.messages.append({
                "role": "system", "text": "[auto mode stopped]",
                "sigil": "·", "colour": C["dim"],
            })
            return

        if self.state.thinking:
            log = self.query_one("#chat-log", RichLog)
            log.write(Text("\n  Working — wait or Ctrl+X\n", style=C["warn"]))
            return

        # Parse commands
        if raw.lower() == "/invoke" or raw.lower().startswith("/invoke "):
            parts = raw.split()
            if len(parts) >= 2:
                sigil = parts[1].upper()
                self._invoke_model(sigil)
            else:
                # Show available models to pick from
                log = self.query_one("#chat-log", RichLog)
                models = self.model_manager.available_models
                t = Text()
                t.append("\n  Available models:\n", style=f"bold {C['blue']}")
                for sigil, cfg in models.items():
                    color = cfg.get("color", C["white"])
                    name = cfg.get("name", sigil)
                    t.append(f"    /invoke {sigil}  ", style=f"bold {color}")
                    t.append(f"— {name}\n", style=C["silver"])
                t.append("\n", style=C["dim"])
                log.write(t)
            return

        if raw.lower().startswith("/chat "):
            parts = raw.split(maxsplit=2)
            if len(parts) >= 3:
                sigil = parts[1].upper()
                message = parts[2]
                self._invoke_model(sigil, message)
            else:
                log = self.query_one("#chat-log", RichLog)
                log.write(Text("\n  Usage: /chat A message\n", style=C["warn"]))
            return

        if raw.lower().startswith("/auto"):
            parts = raw.split()
            max_rounds = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
            self._start_auto(max_rounds)
            return

        # Default: message to last active model
        self.state.messages.append({
            "role": "user", "text": raw,
            "sigil": "·", "name": "you", "colour": C["user"],
        })
        self._invoke_model(self.state.last_active, raw)

    def _invoke_model(self, sigil: str, user_message: str | None = None):
        """Invoke a model in a background thread."""
        models = self.model_manager.available_models
        if sigil not in models:
            self.state.messages.append({
                "role": "system",
                "text": f"Unknown model sigil: {sigil}. Available: {', '.join(models.keys())}",
                "sigil": "·", "colour": C["warn"],
            })
            return

        cfg = models[sigil]
        self.state.thinking = True
        self.state.active_sigil = sigil
        self.state.last_active = sigil

        def _run():
            try:
                result = self.runner.invoke(sigil, user_message)
                self.state.messages.append({
                    "role": "model",
                    "text": result["response"],
                    "sigil": sigil,
                    "name": cfg.get("name", sigil),
                    "colour": cfg.get("color", C["white"]),
                })
            except Exception as e:
                self.state.messages.append({
                    "role": "error",
                    "text": f"Error: {e}",
                    "sigil": "!", "colour": C["danger"],
                })
            finally:
                self.state.thinking = False
                self.state.active_sigil = None

        threading.Thread(target=_run, daemon=True).start()

    def _start_auto(self, max_rounds: int = 10):
        """Start auto relay mode."""
        sigils = list(self.model_manager.available_models.keys())
        if len(sigils) < 2:
            self.state.messages.append({
                "role": "system",
                "text": "Auto mode requires at least 2 models.",
                "sigil": "·", "colour": C["warn"],
            })
            return

        self.state.mode = "auto"
        self.state.thinking = True
        self.state.max_rounds = max_rounds
        self.state.messages.append({
            "role": "system",
            "text": f"Auto relay started. Models: {', '.join(sigils)}. Max rounds: {max_rounds}.",
            "sigil": "·", "colour": C["auto"],
        })

        def _callback(event):
            if event["type"] == "round_start":
                self.state.current_round = event["round"]
                self.state.active_sigil = event["sigil"]
            elif event["type"] == "round_end":
                sigil = event["sigil"]
                cfg = self.model_manager.available_models.get(sigil, {})
                self.state.messages.append({
                    "role": "model",
                    "text": event["response"],
                    "sigil": sigil,
                    "name": cfg.get("name", sigil),
                    "colour": cfg.get("color", C["white"]),
                })
            elif event["type"] == "idle":
                self.state.messages.append({
                    "role": "system",
                    "text": f"Model {event['sigil']} signaled idle. Auto mode ending.",
                    "sigil": "·", "colour": C["dim"],
                })
            elif event["type"] == "complete":
                self.state.thinking = False
                self.state.active_sigil = None
                self.state.mode = "manual"
                self.state.messages.append({
                    "role": "system",
                    "text": f"Auto relay complete. {event['rounds']} rounds.",
                    "sigil": "·", "colour": C["auto"],
                })

        self.runner.auto_run(sigils, max_rounds=max_rounds, callback=_callback)

    # ── ACTIONS ──

    def action_exit_app(self):
        self.model_manager.unload()
        self.exit()

    def action_interrupt(self):
        self.runner.stop()
        self.state.thinking = False
        self.state.active_sigil = None
        self.state.mode = "manual"
        self.state.messages.append({
            "role": "system", "text": "[interrupted]",
            "sigil": "·", "colour": C["dim"],
        })


# ── ENTRY POINT ──────────────────────────────────────────────

def run(path: Path | None = None, config_path: str | None = None, force_setup: bool = False):
    BSSRelayApp(path, config_path=config_path, force_setup=force_setup).run()


if __name__ == "__main__":
    run()
