"""Tests for BSSSession — the bridge between BSS protocol and model inference."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bss.blink_file import BlinkFile, write as write_blink, read as read_blink
from bss.environment import BSSEnvironment
from bss.identifier import generate
from bss.roster import RosterEntry, update_roster


@pytest.fixture
def env(tmp_path):
    """Create a BSS environment with a roster."""
    e = BSSEnvironment.init(tmp_path)

    # Write roster
    entries = [
        RosterEntry(sigil="A", model_id="Qwen3-4B", role="primary", scope_ceiling="global", notes=""),
        RosterEntry(sigil="B", model_id="Qwen3-8B", role="reviewer", scope_ceiling="local", notes=""),
    ]
    update_roster(e, entries)

    # Write an origin blink
    origin_id = generate(
        sequence=1,
        author="U",
        action_energy="~", action_valence="~",
        relational="^",
        confidence="!", cognitive="!",
        domain="^", subdomain=";",
        scope="!", maturity=",",
        priority="=", sensitivity=".",
    )
    origin = BlinkFile(
        blink_id=origin_id,
        born_from=["Origin"],
        summary="BSS environment initialized for testing. Ready for coordination.",
        lineage=[origin_id],
        links=[],
    )
    write_blink(origin, e.active_dir)
    return e


@pytest.fixture
def mock_model_manager():
    """Create a mock ModelManager that returns predictable responses."""
    mm = MagicMock()
    mm.available_models = {
        "A": {"name": "Qwen3-4B", "color": "#64B5F6"},
        "B": {"name": "Qwen3-8B", "color": "#FF8F00"},
    }
    mm.infer.return_value = (
        "I have reviewed the relay state. There are no pending handoffs. The system is ready for work.",
        42,
        1.5,
    )
    mm.chat.return_value = (
        "Continuing from previous context. The analysis is progressing well. Next steps are identified.",
        38,
        1.2,
    )
    mm.load.return_value = True
    mm.is_loaded.return_value = False
    return mm


class TestBSSSession:
    def test_intake_builds_system_prompt(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        prompt = session.intake()

        assert "BSS Model Configuration" in prompt
        assert "Author sigil: A" in prompt
        assert "Qwen3-4B" in prompt
        assert "primary" in prompt

    def test_intake_includes_roster(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        prompt = session.intake()

        # Should include both roster members
        assert "A:" in prompt or "A: Qwen3-4B" in prompt
        assert "B:" in prompt or "B: Qwen3-8B" in prompt

    def test_intake_includes_relay_context(self, env, mock_model_manager):
        """If there are blinks in /relay/, they appear in the system prompt."""
        from integrations.session import BSSSession
        from bss.relay import handoff

        # Write a handoff blink to relay
        handoff(env, "Previous model completed analysis of the codebase. Key findings documented.", author="B")

        session = BSSSession(env, "A", mock_model_manager)
        prompt = session.intake()

        assert "Relay Queue" in prompt
        assert "Previous model completed analysis" in prompt

    def test_invoke_calls_model_infer(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        session.intake()

        response, tokens, elapsed = session.invoke("Hello, what do you see?")

        mock_model_manager.infer.assert_called_once()
        assert response == "I have reviewed the relay state. There are no pending handoffs. The system is ready for work."
        assert tokens == 42
        assert elapsed == 1.5

    def test_invoke_without_message_uses_default(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        session.intake()

        session.invoke()

        # Should have been called with the default prompt
        call_args = mock_model_manager.infer.call_args
        assert "relay state" in call_args[0][2].lower() or "review" in call_args[0][2].lower()

    def test_invoke_uses_chat_for_subsequent_calls(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        session.intake()

        # First call uses infer
        session.invoke("First message")
        assert mock_model_manager.infer.call_count == 1

        # Second call uses chat (has history)
        session.invoke("Second message")
        assert mock_model_manager.chat.call_count == 1

    def test_handoff_writes_to_relay(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        session.intake()

        blink = session.handoff("Completed analysis of relay state. No action items found. Returning to dormancy.")

        assert blink.blink_id is not None
        assert len(blink.blink_id) == 17
        assert blink.blink_id[5] == "A"  # Author sigil
        assert blink.blink_id[6:8] == "~!"  # Handoff action state

        # Verify file exists in relay
        filepath = env.find_blink(blink.blink_id)
        assert filepath is not None
        assert "relay" in str(filepath)

    def test_write_blink_to_active(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        session.intake()

        blink = session.write_blink(
            "Produced analysis document covering key findings. Results are actionable.",
            action="~.",
        )

        assert blink.blink_id[5] == "A"
        assert blink.blink_id[6:8] == "~."  # Completed

        filepath = env.find_blink(blink.blink_id)
        assert filepath is not None
        assert "active" in str(filepath)

    def test_write_blink_chains_lineage(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        session.intake()

        blink1 = session.write_blink("First output created. Initial analysis complete.")
        blink2 = session.write_blink("Second output builds on first. Further refinement applied.")

        # Second blink should be born from first
        read2 = read_blink(env.find_blink(blink2.blink_id))
        assert blink1.blink_id in read2.born_from

    def test_handoff_then_dormancy(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session = BSSSession(env, "A", mock_model_manager)
        session.intake()
        session.invoke("Do some work")
        session.handoff("Session complete. Passing relay to next model. No issues found.")

        # Session should be in dormancy
        assert session._session.phase.value == "dormancy"

    def test_intake_with_no_roster(self, tmp_path, mock_model_manager):
        """Session should still work without a roster."""
        from integrations.session import BSSSession

        env = BSSEnvironment.init(tmp_path / "no_roster")
        session = BSSSession(env, "A", mock_model_manager)
        prompt = session.intake()

        assert "BSS relay member" in prompt
        assert "A" in prompt

    def test_different_sigils(self, env, mock_model_manager):
        from integrations.session import BSSSession

        session_a = BSSSession(env, "A", mock_model_manager)
        session_b = BSSSession(env, "B", mock_model_manager)

        prompt_a = session_a.intake()
        prompt_b = session_b.intake()

        assert "Author sigil: A" in prompt_a
        assert "Author sigil: B" in prompt_b
