"""RelayRunner — orchestrates multi-model relay invocations.

Supports manual mode (explicit model invocation) and auto mode
(models alternate until interrupted or idle).
"""

from __future__ import annotations

import threading
from typing import Callable

from bss.environment import BSSEnvironment

from integrations.models import ModelManager
from integrations.session import BSSSession


class RelayRunner:
    """Orchestrates model invocations across the BSS relay.

    Manual mode: invoke(sigil) wakes a specific model.
    Auto mode: auto_run(sigils) alternates models automatically.
    """

    def __init__(
        self,
        env: BSSEnvironment,
        model_manager: ModelManager,
        round_delay: float = 0.5,
    ):
        self.env = env
        self.model_manager = model_manager
        self._sessions: dict[str, BSSSession] = {}
        self._running = False
        self._stop_event = threading.Event()
        self._auto_thread: threading.Thread | None = None
        self._round_delay = round_delay

    def _get_session(self, sigil: str) -> BSSSession:
        """Get or create a session for a sigil."""
        if sigil not in self._sessions:
            self._sessions[sigil] = BSSSession(self.env, sigil, self.model_manager)
        return self._sessions[sigil]

    def invoke(self, sigil: str, user_message: str | None = None) -> dict:
        """Single model invocation cycle.

        Wakes the model, reads relay, runs inference, writes handoff.

        Args:
            sigil: Model sigil to invoke (e.g. "A", "B").
            user_message: Optional user message to include.

        Returns:
            dict with keys: sigil, response, tokens, elapsed, blink_id
        """
        session = self._get_session(sigil)

        # Intake: read relay and build context
        session.intake()

        # Invoke: run inference
        response, tokens, elapsed = session.invoke(user_message)

        # Determine if response warrants a handoff blink
        # Generate a summary from the response (first 2-3 sentences)
        summary = self._extract_summary(response)

        # Write handoff blink (relay mode: accept 1-sentence summaries)
        blink = session.handoff(summary, min_sentences=1)

        # Reset session for next invocation
        self._sessions.pop(sigil, None)

        return {
            "sigil": sigil,
            "response": response,
            "tokens": tokens,
            "elapsed": elapsed,
            "blink_id": blink.blink_id,
        }

    def auto_run(
        self,
        sigils: list[str],
        max_rounds: int = 10,
        callback: Callable | None = None,
    ) -> list[dict]:
        """Auto-alternate between models.

        Each model wakes, reads relay (sees previous model's handoff),
        acts, writes handoff, sleeps. Continues until:
        - User interrupts (stop())
        - A model writes an idle blink (response contains "~~" or "[idle]")
        - max_rounds reached

        Args:
            sigils: List of model sigils to alternate (e.g. ["A", "B"]).
            max_rounds: Maximum number of total invocations.
            callback: Optional callback(event_dict) for UI updates.

        Returns:
            List of result dicts from each invocation.
        """
        self._running = True
        self._stop_event.clear()
        results: list[dict] = []
        results_lock = threading.Lock()

        def _run():
            round_num = 0
            try:
                while round_num < max_rounds and not self._stop_event.is_set():
                    sigil = sigils[round_num % len(sigils)]
                    round_num += 1

                    if callback:
                        callback({
                            "type": "round_start",
                            "round": round_num,
                            "sigil": sigil,
                            "max_rounds": max_rounds,
                        })

                    result = self.invoke(sigil)
                    with results_lock:
                        results.append(result)

                    if callback:
                        callback({
                            "type": "round_end",
                            "round": round_num,
                            **result,
                        })

                    # Check for idle signal
                    response_lower = result["response"].lower()
                    if "~~" in response_lower or "[idle]" in response_lower:
                        if callback:
                            callback({"type": "idle", "sigil": sigil, "round": round_num})
                        break

                    # Brief pause between models
                    if not self._stop_event.is_set():
                        self._stop_event.wait(timeout=self._round_delay)
            except Exception as e:
                if callback:
                    callback({"type": "error", "error": str(e), "round": round_num})
            finally:
                self._running = False
                if callback:
                    callback({"type": "complete", "rounds": round_num, "total_results": len(results)})

        self._auto_thread = threading.Thread(target=_run, daemon=True)
        self._auto_thread.start()
        return results

    def stop(self) -> None:
        """Interrupt auto mode and wait for thread to finish."""
        self._stop_event.set()
        self._running = False
        if self._auto_thread is not None:
            self._auto_thread.join(timeout=10)
            self._auto_thread = None

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def _extract_summary(response: str) -> str:
        """Extract a summary from a model response for relay handoff.

        Takes the first few sentences. Single-sentence summaries are valid
        in relay mode (min_sentences=1 is passed to handoff).
        """
        # Split into sentences
        sentences = []
        current = ""
        for char in response:
            current += char
            if char in ".!?" and len(current.strip()) > 5:
                sentences.append(current.strip())
                current = ""
        if current.strip() and len(current.strip()) > 5:
            sentences.append(current.strip())

        if not sentences:
            return "Model completed inference cycle."

        # Take up to 3 sentences for summary
        summary_sentences = sentences[:3]
        summary = " ".join(summary_sentences)

        # Truncate if too long for blink file (keep under ~400 chars)
        if len(summary) > 400:
            summary = summary[:397] + "..."

        return summary
