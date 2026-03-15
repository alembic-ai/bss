"""Tests for BSS roster management — generate_model_config and CLI commands."""

import pytest
from pathlib import Path

from bss.environment import BSSEnvironment
from bss.roster import (
    Roster,
    RosterEntry,
    read_roster,
    update_roster,
    generate_model_config,
    VALID_ROLES,
    VALID_CEILINGS,
)
from bss.blink_file import BlinkFile, write as write_blink
from bss.identifier import generate


@pytest.fixture
def env(tmp_path) -> BSSEnvironment:
    return BSSEnvironment.init(tmp_path)


def _setup_roster(env, entries=None):
    """Helper to create a roster with default or custom entries."""
    if entries is None:
        entries = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead agent"),
            RosterEntry("B", "Claude-B", "specialist", "local", "Parser"),
        ]
    return update_roster(env, entries)


# ============================================================
# generate_model_config Tests
# ============================================================


class TestGenerateModelConfig:
    """Tests for generate_model_config()."""

    def test_basic_config_generation(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        assert "# BSS Model Configuration" in config
        assert "Author sigil: A" in config
        assert "Claude-A" in config
        assert "primary" in config
        assert "global" in config

    def test_config_contains_directory_structure(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        assert "/relay/" in config
        assert "/active/" in config
        assert "/profile/" in config
        assert "/archive/" in config
        assert "/artifacts/" in config

    def test_config_contains_roster(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        assert "A: Claude-A" in config
        assert "B: Claude-B" in config
        assert "<-- you" in config

    def test_config_marks_correct_model(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "B", env)

        # B should be marked, not A
        lines = config.split("\n")
        for line in lines:
            if "B: Claude-B" in line:
                assert "<-- you" in line
            if "A: Claude-A" in line:
                assert "<-- you" not in line

    def test_config_contains_blink_grammar(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        assert "17 characters" in config
        assert "Base-36" in config
        assert "Action state" in config or "Action States" in config

    def test_config_contains_scope_ceiling_rule(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "B", env)

        assert "local" in config
        assert "scope ceiling" in config.lower()

    def test_config_contains_relay_state(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        assert "Relay State" in config
        assert "Next sequence" in config

    def test_unknown_sigil_raises(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        with pytest.raises(ValueError, match="not found"):
            generate_model_config(roster, "Z", env)

    def test_config_contains_action_states(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        assert "Handoff" in config
        assert "Error" in config
        assert "Completed" in config

    def test_config_contains_generation_cap(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        assert "7" in config
        assert "converge" in config.lower() or "Converge" in config


# ============================================================
# Roster Add Tests
# ============================================================


class TestRosterAdd:
    """Tests for adding models to the roster."""

    def test_add_to_empty_roster(self, env):
        """Adding to an environment with no roster creates one."""
        entries = [RosterEntry("A", "Claude-A", "primary", "global", "Lead")]
        update_roster(env, entries)

        roster = read_roster(env)
        assert roster is not None
        assert len(roster.entries) == 1
        assert roster.get_entry("A").model_id == "Claude-A"

    def test_add_second_model(self, env):
        """Adding a second model preserves the first."""
        entries_v1 = [RosterEntry("A", "Claude-A", "primary", "global", "Lead")]
        r1 = update_roster(env, entries_v1)

        entries_v2 = entries_v1 + [
            RosterEntry("B", "Claude-B", "specialist", "local", "Parser"),
        ]
        update_roster(env, entries_v2, old_roster_id=r1.blink_id)

        roster = read_roster(env)
        assert len(roster.entries) == 2
        assert roster.get_entry("A") is not None
        assert roster.get_entry("B") is not None

    def test_add_archives_old_roster(self, env):
        """Adding a model archives the previous roster blink."""
        entries_v1 = [RosterEntry("A", "Claude-A", "primary", "global", "")]
        r1 = update_roster(env, entries_v1)

        entries_v2 = entries_v1 + [RosterEntry("B", "Claude-B", "reviewer", "local", "")]
        update_roster(env, entries_v2, old_roster_id=r1.blink_id)

        old_path = env.find_blink(r1.blink_id)
        assert old_path is not None
        assert "archive" in str(old_path)

    def test_valid_roles(self):
        """All expected roles are in VALID_ROLES."""
        assert "primary" in VALID_ROLES
        assert "reviewer" in VALID_ROLES
        assert "specialist" in VALID_ROLES
        assert "architect" in VALID_ROLES

    def test_valid_ceilings(self):
        """All expected ceilings are in VALID_CEILINGS."""
        assert "atomic" in VALID_CEILINGS
        assert "local" in VALID_CEILINGS
        assert "regional" in VALID_CEILINGS
        assert "global" in VALID_CEILINGS


# ============================================================
# Roster Remove Tests
# ============================================================


class TestRosterRemove:
    """Tests for removing models from the roster."""

    def test_remove_model(self, env):
        _setup_roster(env)
        roster = read_roster(env)

        new_entries = [e for e in roster.entries if e.sigil != "B"]
        update_roster(env, new_entries, old_roster_id=roster.blink_id)

        roster = read_roster(env)
        assert len(roster.entries) == 1
        assert roster.get_entry("B") is None
        assert roster.get_entry("A") is not None

    def test_remove_preserves_others(self, env):
        entries = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead"),
            RosterEntry("B", "Claude-B", "specialist", "local", ""),
            RosterEntry("C", "Claude-C", "reviewer", "regional", ""),
        ]
        r1 = update_roster(env, entries)

        new_entries = [e for e in entries if e.sigil != "B"]
        update_roster(env, new_entries, old_roster_id=r1.blink_id)

        roster = read_roster(env)
        assert len(roster.entries) == 2
        assert roster.get_entry("A") is not None
        assert roster.get_entry("C") is not None

    def test_remove_last_model(self, env):
        """Removing the last model results in empty roster."""
        entries = [RosterEntry("A", "Claude-A", "primary", "global", "")]
        r1 = update_roster(env, entries)

        update_roster(env, [], old_roster_id=r1.blink_id)

        roster = read_roster(env)
        assert roster is not None
        assert len(roster.entries) == 0


# ============================================================
# Roster Update Tests
# ============================================================


class TestRosterUpdate:
    """Tests for updating roster entries."""

    def test_update_role(self, env):
        _setup_roster(env)
        roster = read_roster(env)

        new_entries = []
        for e in roster.entries:
            if e.sigil == "B":
                new_entries.append(RosterEntry("B", e.model_id, "architect", e.scope_ceiling, e.notes))
            else:
                new_entries.append(e)
        update_roster(env, new_entries, old_roster_id=roster.blink_id)

        roster = read_roster(env)
        assert roster.get_entry("B").role == "architect"

    def test_update_ceiling(self, env):
        _setup_roster(env)
        roster = read_roster(env)

        new_entries = []
        for e in roster.entries:
            if e.sigil == "B":
                new_entries.append(RosterEntry("B", e.model_id, e.role, "global", e.notes))
            else:
                new_entries.append(e)
        update_roster(env, new_entries, old_roster_id=roster.blink_id)

        roster = read_roster(env)
        assert roster.get_entry("B").scope_ceiling == "global"

    def test_update_model_id(self, env):
        _setup_roster(env)
        roster = read_roster(env)

        new_entries = []
        for e in roster.entries:
            if e.sigil == "B":
                new_entries.append(RosterEntry("B", "GPT-4o", e.role, e.scope_ceiling, e.notes))
            else:
                new_entries.append(e)
        update_roster(env, new_entries, old_roster_id=roster.blink_id)

        roster = read_roster(env)
        assert roster.get_entry("B").model_id == "GPT-4o"

    def test_update_preserves_unchanged(self, env):
        _setup_roster(env)
        roster = read_roster(env)

        new_entries = []
        for e in roster.entries:
            if e.sigil == "B":
                new_entries.append(RosterEntry("B", e.model_id, e.role, "regional", e.notes))
            else:
                new_entries.append(e)
        update_roster(env, new_entries, old_roster_id=roster.blink_id)

        roster = read_roster(env)
        a = roster.get_entry("A")
        assert a.model_id == "Claude-A"
        assert a.role == "primary"
        assert a.scope_ceiling == "global"


# ============================================================
# Roster Config Output Tests
# ============================================================


class TestRosterConfig:
    """Tests for config generation output."""

    def test_config_is_valid_text(self, env):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        assert isinstance(config, str)
        assert len(config) > 100
        lines = config.split("\n")
        assert lines[0] == "# BSS Model Configuration"

    def test_config_can_be_written_to_file(self, env, tmp_path):
        _setup_roster(env)
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)

        out = tmp_path / "CLAUDE.md"
        out.write_text(config, encoding="utf-8")
        assert out.read_text(encoding="utf-8") == config
