"""Module 8.2 relay tests — session lifecycle, handoff, error escalation, generations."""

import pytest
from pathlib import Path

from src.bss.relay import (
    Session,
    SessionPhase,
    handoff,
    error_blink,
    check_escalation,
)
from src.bss.generations import (
    get_generation,
    needs_convergence,
    get_chain,
    converge,
)
from src.bss.environment import BSSEnvironment
from src.bss.blink_file import BlinkFile, write as write_blink, read as read_blink
from src.bss.identifier import generate, parse as parse_id


@pytest.fixture
def env(tmp_path) -> BSSEnvironment:
    return BSSEnvironment.init(tmp_path)


def _write_origin(env: BSSEnvironment, directory: str = "active", author: str = "A") -> BlinkFile:
    """Write an origin blink to the specified directory."""
    blink_id = generate(
        sequence=int(env.next_sequence(), 36), author=author,
        action_energy="~", action_valence="~", relational="^",
        confidence="!", cognitive="!",
        domain="^", subdomain=";", scope="!",
        maturity=",", priority="=", sensitivity=".",
    )
    blink = BlinkFile(
        blink_id=blink_id,
        born_from=["Origin"],
        summary="Origin blink for testing. This marks the beginning of a test thread.",
        lineage=[blink_id],
        links=[],
    )
    write_blink(blink, env.root / directory)
    return blink


def _write_continuation(
    env: BSSEnvironment, parent: BlinkFile, directory: str = "active",
    author: str = "A", **kwargs
) -> BlinkFile:
    """Write a continuation blink."""
    defaults = dict(
        action_energy=".", action_valence="!",
        relational="+", confidence=".", cognitive="=",
        domain="#", subdomain="!", scope="-",
        maturity="~", priority="=", sensitivity="=",
    )
    defaults.update(kwargs)

    blink_id = generate(
        sequence=int(env.next_sequence(), 36), author=author, **defaults
    )
    lineage = parent.lineage[-6:] + [blink_id]
    blink = BlinkFile(
        blink_id=blink_id,
        born_from=[parent.blink_id],
        summary="Continuing work on the task. Making progress step by step.",
        lineage=lineage,
        links=[],
    )
    write_blink(blink, env.root / directory)
    return blink


# ============================================================
# 8.2.1 — Startup Sequence Order
# ============================================================


class TestStartupSequence:
    """Verify startup sequence reads directories in correct order."""

    def test_intake_reads_relay_first(self, env):
        _write_origin(env, "relay")
        _write_origin(env, "active")
        _write_origin(env, "profile")

        session = Session(env)
        ctx = session.intake()

        assert len(ctx.relay_blinks) >= 1
        assert len(ctx.active_blinks) >= 1
        assert len(ctx.profile_blinks) >= 1

    def test_phase_transitions(self, env):
        session = Session(env)
        assert session.phase == SessionPhase.INTAKE

        session.intake()
        assert session.phase == SessionPhase.TRIAGE

        session.begin_work()
        assert session.phase == SessionPhase.WORK

        session.begin_output()
        assert session.phase == SessionPhase.OUTPUT

        session.dormancy()
        assert session.phase == SessionPhase.DORMANCY


# ============================================================
# 8.2.2 — Handoff Write Location
# ============================================================


class TestHandoffWriteLocation:
    """Handoff blinks must be written to /relay/ with action state ~!."""

    def test_handoff_goes_to_relay(self, env):
        blink = handoff(
            env,
            summary="Completed the parser module. Next session should integrate with file writer.",
            author="A",
        )
        # Verify it's in /relay/
        found = env.find_blink(blink.blink_id)
        assert found is not None
        assert found.parent == env.relay_dir

    def test_handoff_action_state(self, env):
        blink = handoff(
            env,
            summary="Handing off work to the next model. Integration tests remain.",
            author="A",
        )
        meta = parse_id(blink.blink_id)
        assert meta.action_energy == "~"
        assert meta.action_valence == "!"

    def test_handoff_with_parent(self, env):
        origin = _write_origin(env)
        blink = handoff(
            env,
            summary="Continuing from the origin blink. Parser is now feature-complete.",
            author="A",
            parent=origin.blink_id,
        )
        assert blink.born_from == [origin.blink_id]


# ============================================================
# 8.2.8 — Error Blink Creation
# ============================================================


class TestErrorBlink:
    """Error blinks must go to /relay/ with action state !!."""

    def test_error_goes_to_relay(self, env):
        blink = error_blink(
            env,
            summary="Parser failed on edge case with consecutive special characters. Need to handle escaped sigils.",
            author="A",
        )
        found = env.find_blink(blink.blink_id)
        assert found is not None
        assert found.parent == env.relay_dir

    def test_error_action_state(self, env):
        blink = error_blink(
            env,
            summary="Base-36 encoder crashed on boundary value. The issue is in the carry logic.",
            author="A",
        )
        meta = parse_id(blink.blink_id)
        assert meta.action_energy == "!"
        assert meta.action_valence == "!"

    def test_error_confidence_reflects_diagnosis(self, env):
        blink = error_blink(
            env,
            summary="Something broke but unsure of root cause. Needs investigation.",
            author="A",
            confidence="~",
        )
        meta = parse_id(blink.blink_id)
        assert meta.confidence == "~"


# ============================================================
# 8.2.9 — Error Escalation Chain
# ============================================================


class TestErrorEscalation:
    """Error escalation chain detection."""

    def test_two_error_chain_detected(self, env):
        """Two consecutive error blinks trigger escalation."""
        err1 = error_blink(
            env,
            summary="Parser failed on edge case. Could not handle consecutive sigils.",
            author="A",
        )
        err2 = error_blink(
            env,
            summary="Also failed to resolve the parser issue. Additional diagnosis included.",
            author="B",
            parent=err1.blink_id,
        )

        chains = check_escalation(env)
        assert len(chains) >= 1
        assert len(chains[0]) >= 2

    def test_no_escalation_with_single_error(self, env):
        error_blink(
            env,
            summary="Single error blink, no chain. Should not trigger escalation.",
            author="A",
        )
        chains = check_escalation(env)
        assert len(chains) == 0


# ============================================================
# 8.2.11-13 — Generation Cap & Convergence
# ============================================================


class TestGenerationCap:
    """Generation tracking, cap enforcement, and convergence."""

    def test_origin_is_generation_1(self, env):
        origin = _write_origin(env)
        gen = get_generation(env, origin.blink_id)
        assert gen == 1

    def test_continuation_increments(self, env):
        origin = _write_origin(env)
        cont1 = _write_continuation(env, origin)
        cont2 = _write_continuation(env, cont1)

        assert get_generation(env, cont1.blink_id) == 2
        assert get_generation(env, cont2.blink_id) == 3

    def test_generation_7_needs_convergence(self, env):
        """Module 8.2.11: A thread at generation 7 must converge."""
        blink = _write_origin(env)
        for _ in range(6):  # 6 more = generation 7
            blink = _write_continuation(env, blink)

        assert get_generation(env, blink.blink_id) == 7
        assert needs_convergence(env, blink.blink_id) is True

    def test_generation_6_no_convergence(self, env):
        blink = _write_origin(env)
        for _ in range(5):  # 5 more = generation 6
            blink = _write_continuation(env, blink)

        assert get_generation(env, blink.blink_id) == 6
        assert needs_convergence(env, blink.blink_id) is False

    def test_convergence_blink_format(self, env):
        """Module 8.2.12: Convergence blink has correct format."""
        blink = _write_origin(env)
        for _ in range(6):
            blink = _write_continuation(env, blink)

        chain = get_chain(env, blink.blink_id)
        conv = converge(
            env, chain,
            summary="Synthesizing seven generations of parser development. The engine is now complete with full validation.",
        )

        meta = parse_id(conv.blink_id)
        assert meta.relational == "<"  # Convergence
        assert conv.born_from == [blink.blink_id]
        assert len(conv.lineage) == 1  # New chain starts
        assert conv.lineage[0] == conv.blink_id
        assert len(conv.links) >= 1  # References to chain

    def test_post_convergence_reset(self, env):
        """Module 8.2.13: After convergence, generation resets."""
        blink = _write_origin(env)
        for _ in range(6):
            blink = _write_continuation(env, blink)

        chain = get_chain(env, blink.blink_id)
        conv = converge(
            env, chain,
            summary="Converging the chain. Everything synthesized into one. Moving forward.",
        )

        # Convergence is generation 1
        assert get_generation(env, conv.blink_id) == 1

        # Continuations after convergence increment from 1
        cont1 = _write_continuation(env, conv)
        cont2 = _write_continuation(env, cont1)

        assert get_generation(env, cont1.blink_id) == 2
        assert get_generation(env, cont2.blink_id) == 3

    def test_get_chain(self, env):
        """get_chain walks backwards correctly."""
        origin = _write_origin(env)
        c1 = _write_continuation(env, origin)
        c2 = _write_continuation(env, c1)
        c3 = _write_continuation(env, c2)

        chain = get_chain(env, c3.blink_id)
        assert len(chain) == 4
        assert chain[0].blink_id == origin.blink_id
        assert chain[-1].blink_id == c3.blink_id


# ============================================================
# 8.2.14 — Session Lifecycle Completeness
# ============================================================


class TestSessionLifecycle:
    """Full session lifecycle through all five phases."""

    def test_full_lifecycle(self, env):
        _write_origin(env, "relay")
        _write_origin(env, "active")
        _write_origin(env, "profile")

        session = Session(env, author="A")

        # Full lifecycle
        ctx = session.run_full_lifecycle()
        assert session.phase == SessionPhase.WORK

        # Simulate work, then output
        session.begin_output()
        assert session.phase == SessionPhase.OUTPUT

        session.dormancy()
        assert session.phase == SessionPhase.DORMANCY


# ============================================================
# 8.2.16 — Empty Environment Cold Start
# ============================================================


class TestEmptyEnvironment:
    """Empty environment cold start behavior."""

    def test_cold_start_empty(self, env):
        session = Session(env)
        ctx = session.intake()

        assert ctx.relay_blinks == []
        assert ctx.active_blinks == []
        assert ctx.profile_blinks == []
        assert ctx.highest_sequence == "00000"


# ============================================================
# 8.2.6 — Relay Hygiene Session Output Limit
# ============================================================


class TestRelayHygiene:
    """Session output limits for relay directory."""

    def test_handoff_count_tracking(self, env):
        """Track that relay directory accumulates handoff blinks."""
        h1 = handoff(env, summary="First handoff of the session. Parser module complete.")
        h2 = handoff(env, summary="Second handoff of the session. Validator module complete.")
        h3 = handoff(env, summary="Third handoff of the session. Generator module complete.")

        assert env.relay_count() == 3
