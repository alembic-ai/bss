"""BSSSession — bridge between BSS protocol and model inference.

Reads relay state, builds context, runs inference, writes blinks.
"""

from __future__ import annotations

from src.bss.blink_file import BlinkFile, write as write_blink
from src.bss.environment import BSSEnvironment
from src.bss.identifier import generate, parse as parse_id
from src.bss.relay import Session, handoff as relay_handoff
from src.bss.roster import read_roster, generate_model_config

from integrations.models import ModelManager


class BSSSession:
    """A model's session within the BSS relay.

    Handles the full cycle: read relay -> build context -> run inference -> write blinks.
    """

    def __init__(self, env: BSSEnvironment, sigil: str, model_manager: ModelManager):
        self.env = env
        self.sigil = sigil
        self.model_manager = model_manager
        self._session = Session(env, author=sigil)
        self._system_prompt: str | None = None
        self._last_blink_id: str | None = None
        self._history: list[dict] = []

    def intake(self) -> str:
        """Read relay, roster, active. Build system prompt.

        Returns the full system prompt including relay context.
        """
        ctx = self._session.intake()
        self._session.begin_work()

        # Build system prompt from roster config
        roster = read_roster(self.env)
        if roster:
            self._system_prompt = generate_model_config(roster, self.sigil, self.env)
        else:
            self._system_prompt = (
                f"You are BSS relay member {self.sigil}. "
                "Read the relay context and respond helpfully."
            )

        # Append relay blink summaries as context
        if ctx.triaged_relay:
            relay_context = "\n\n## Relay Queue\n"
            for blink in ctx.triaged_relay:
                try:
                    meta = parse_id(blink.blink_id)
                    action = blink.blink_id[6:8]
                    relay_context += f"\n[{action}] from {meta.author}: {blink.summary}\n"
                except ValueError:
                    relay_context += f"\n[??] {blink.summary}\n"
            self._system_prompt += relay_context

        # Note active blinks for context
        if ctx.active_blinks:
            active_context = "\n\n## Active Work\n"
            for blink in ctx.active_blinks[-5:]:  # Last 5 active blinks
                try:
                    meta = parse_id(blink.blink_id)
                    active_context += f"\n[{meta.author}] {blink.summary[:100]}\n"
                except ValueError:
                    pass
            self._system_prompt += active_context

        return self._system_prompt

    def invoke(self, user_message: str | None = None) -> tuple[str, int, float]:
        """Run one inference cycle.

        Args:
            user_message: Optional user message. If None, model acts on relay context alone.

        Returns:
            (response_text, tokens, elapsed_seconds)
        """
        if self._system_prompt is None:
            self.intake()

        prompt = user_message or "Review the relay state and respond with your analysis and any actions needed."

        if self._history:
            response, tokens, elapsed = self.model_manager.chat(
                self.sigil, self._system_prompt, self._history, prompt
            )
        else:
            response, tokens, elapsed = self.model_manager.infer(
                self.sigil, self._system_prompt, prompt
            )

        # Track conversation
        self._history.append({"role": "user", "content": prompt})
        self._history.append({"role": "assistant", "content": response})

        return response, tokens, elapsed

    def handoff(self, summary: str, min_sentences: int = 2) -> BlinkFile:
        """Write a handoff blink to /relay/ capturing what happened.

        Args:
            summary: Summary of the session.
            min_sentences: Minimum sentence count for validation. Relay mode
                with small models may pass 1.

        Returns:
            The written BlinkFile.
        """
        self._session.begin_output()

        blink = relay_handoff(
            env=self.env,
            summary=summary,
            author=self.sigil,
            parent=self._last_blink_id,
            min_sentences=min_sentences,
        )
        self._last_blink_id = blink.blink_id

        self._session.dormancy()
        return blink

    def write_blink(
        self,
        summary: str,
        action: str = "~.",
        scope: str = "-",
        parent: str | None = None,
        min_sentences: int = 2,
    ) -> BlinkFile:
        """Write a blink to /active/ for work output.

        Args:
            summary: Summary of work output.
            action: 2-char action state (default ~. = completed).
            scope: Scope sigil.
            parent: Parent blink ID, or uses last blink from this session.
            min_sentences: Minimum sentence count for validation.

        Returns:
            The written BlinkFile.
        """
        seq = self.env.next_sequence()
        parent_id = parent or self._last_blink_id

        action_energy = action[0] if len(action) >= 1 else "~"
        action_valence = action[1] if len(action) >= 2 else "."

        blink_id = generate(
            sequence=seq,
            author=self.sigil,
            action_energy=action_energy,
            action_valence=action_valence,
            relational="+" if parent_id else "^",
            confidence=".",
            cognitive="=",
            domain="#",
            subdomain="!",
            scope=scope,
            maturity="~",
            priority="=",
            sensitivity="=",
        )

        if parent_id:
            from src.bss.blink_file import read as read_blink
            born_from = [parent_id]
            parent_path = self.env.find_blink(parent_id)
            if parent_path:
                parent_blink = read_blink(parent_path)
                lineage = parent_blink.lineage[-6:] + [blink_id]
            else:
                lineage = [parent_id, blink_id]
        else:
            born_from = ["Origin"]
            lineage = [blink_id]

        blink = BlinkFile(
            blink_id=blink_id,
            born_from=born_from,
            summary=summary,
            lineage=lineage,
            links=[],
        )

        write_blink(blink, self.env.active_dir, min_sentences=min_sentences)
        self._last_blink_id = blink.blink_id
        return blink
