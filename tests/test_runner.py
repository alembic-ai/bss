"""Tests for RelayRunner — orchestrates multi-model relay invocations."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from src.bss.blink_file import BlinkFile, write as write_blink, read as read_blink
from src.bss.environment import BSSEnvironment
from src.bss.identifier import generate
from src.bss.roster import RosterEntry, update_roster


@pytest.fixture
def env(tmp_path):
    """Create a BSS environment with a roster."""
    e = BSSEnvironment.init(tmp_path)

    entries = [
        RosterEntry(sigil="A", model_id="Qwen3-4B", role="primary", scope_ceiling="global", notes=""),
        RosterEntry(sigil="B", model_id="Qwen3-8B", role="reviewer", scope_ceiling="local", notes=""),
    ]
    update_roster(e, entries)

    # Write origin blink
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
        "Continuing from previous context. The analysis looks good. Ready to proceed.",
        38,
        1.2,
    )
    mm.load.return_value = True
    mm.is_loaded.return_value = False
    return mm


class TestRelayRunner:
    def test_invoke_returns_result(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)
        result = runner.invoke("A")

        assert result["sigil"] == "A"
        assert "reviewed the relay state" in result["response"]
        assert result["tokens"] == 42
        assert result["elapsed"] == 1.5
        assert result["blink_id"] is not None
        assert len(result["blink_id"]) == 17

    def test_invoke_writes_handoff_blink(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)
        result = runner.invoke("A")

        # Handoff blink should exist in relay
        filepath = env.find_blink(result["blink_id"])
        assert filepath is not None
        assert "relay" in str(filepath)

        blink = read_blink(filepath)
        assert blink.blink_id[5] == "A"
        assert blink.blink_id[6:8] == "~!"  # Handoff

    def test_invoke_with_user_message(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)
        result = runner.invoke("A", "Please analyze the current state")

        # Model should have been called with the user message
        mock_model_manager.infer.assert_called_once()
        call_args = mock_model_manager.infer.call_args
        assert "analyze the current state" in call_args[0][2]

    def test_invoke_model_b(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)
        result = runner.invoke("B")

        assert result["sigil"] == "B"
        filepath = env.find_blink(result["blink_id"])
        blink = read_blink(filepath)
        assert blink.blink_id[5] == "B"

    def test_sequential_invocations(self, env, mock_model_manager):
        """Invoke A then B. B should see A's handoff in relay."""
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)

        result_a = runner.invoke("A")
        result_b = runner.invoke("B")

        # Both should have unique blink IDs
        assert result_a["blink_id"] != result_b["blink_id"]

        # Both blinks should be in relay
        assert env.find_blink(result_a["blink_id"]) is not None
        assert env.find_blink(result_b["blink_id"]) is not None

    def test_auto_run_alternates_models(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)
        events = []

        def callback(event):
            events.append(event)

        runner.auto_run(["A", "B"], max_rounds=4, callback=callback)

        # Wait for auto mode to complete
        timeout = 30
        start = time.time()
        while runner.is_running and time.time() - start < timeout:
            time.sleep(0.2)

        # Should have alternated: A, B, A, B
        round_starts = [e for e in events if e["type"] == "round_start"]
        assert len(round_starts) == 4
        assert round_starts[0]["sigil"] == "A"
        assert round_starts[1]["sigil"] == "B"
        assert round_starts[2]["sigil"] == "A"
        assert round_starts[3]["sigil"] == "B"

        # Should have completion event
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["rounds"] == 4

    def test_auto_run_stops_on_idle(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        # Model A returns idle signal on first invocation
        mock_model_manager.infer.return_value = (
            "No work to do. System is idle. ~~",
            10,
            0.5,
        )

        runner = RelayRunner(env, mock_model_manager)
        events = []

        runner.auto_run(["A", "B"], max_rounds=10, callback=lambda e: events.append(e))

        timeout = 15
        start = time.time()
        while runner.is_running and time.time() - start < timeout:
            time.sleep(0.2)

        # Should have stopped early due to idle
        idle_events = [e for e in events if e["type"] == "idle"]
        assert len(idle_events) == 1
        assert idle_events[0]["sigil"] == "A"

    def test_stop_interrupts_auto(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        # Make inference slow
        def slow_infer(*args, **kwargs):
            time.sleep(0.5)
            return ("Working on it. Still processing the data.", 20, 0.5)

        mock_model_manager.infer.side_effect = slow_infer

        runner = RelayRunner(env, mock_model_manager)
        runner.auto_run(["A", "B"], max_rounds=20)

        # Let it run briefly then stop
        time.sleep(1.0)
        runner.stop()

        # Wait for thread to finish
        time.sleep(1.0)
        assert not runner.is_running

    def test_extract_summary(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)

        # Normal response
        summary = runner._extract_summary(
            "I analyzed the data. The results show positive trends. We should continue."
        )
        assert len(summary) > 20
        assert "analyzed" in summary

    def test_extract_summary_short_response(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)

        # Short response (under 6 chars) hits fallback; longer ones are kept
        summary = runner._extract_summary("Done.")
        assert len(summary) > 5  # Fallback produces a valid summary
        summary2 = runner._extract_summary("Task is complete.")
        assert "complete" in summary2.lower()

    def test_extract_summary_empty(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)

        summary = runner._extract_summary("")
        assert len(summary) > 10  # Should produce a default summary

    def test_multiple_invocations_create_unique_blinks(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)
        blink_ids = set()

        for _ in range(5):
            result = runner.invoke("A")
            blink_ids.add(result["blink_id"])

        # All blink IDs should be unique
        assert len(blink_ids) == 5

    def test_runner_not_running_initially(self, env, mock_model_manager):
        from integrations.runner import RelayRunner

        runner = RelayRunner(env, mock_model_manager)
        assert not runner.is_running

    def test_stop_joins_thread(self, env, mock_model_manager):
        """stop() joins the auto thread and clears it."""
        from integrations.runner import RelayRunner

        def slow_infer(*args, **kwargs):
            time.sleep(0.3)
            return ("Working on analysis. Making progress.", 15, 0.3)

        mock_model_manager.infer.side_effect = slow_infer

        runner = RelayRunner(env, mock_model_manager)
        runner.auto_run(["A", "B"], max_rounds=20)
        time.sleep(0.5)

        runner.stop()
        assert runner._auto_thread is None
        assert not runner.is_running

    def test_auto_run_exception_handled(self, env, mock_model_manager):
        """Exceptions in auto_run thread are caught and reported via callback."""
        from integrations.runner import RelayRunner

        mock_model_manager.infer.side_effect = RuntimeError("Model crashed")

        runner = RelayRunner(env, mock_model_manager)
        events = []

        runner.auto_run(["A"], max_rounds=5, callback=lambda e: events.append(e))

        timeout = 10
        start = time.time()
        while runner.is_running and time.time() - start < timeout:
            time.sleep(0.2)

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1
        assert "Model crashed" in error_events[0]["error"]
