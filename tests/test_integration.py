"""Level 5 integration tests — full end-to-end BSS workflows."""

import pytest
from pathlib import Path

from src.bss.blink_file import (
    BlinkFile, write as write_blink, read as read_blink,
    validate_file, parse_content, MAX_FILE_SIZE, WARN_FILE_SIZE,
)
from src.bss.environment import BSSEnvironment
from src.bss.relay import (
    Session, SessionPhase, handoff, error_blink, check_escalation,
)
from src.bss.generations import (
    get_generation, needs_convergence, get_chain, converge,
)
from src.bss.roster import (
    Roster, RosterEntry, read_roster, update_roster, check_scope_compliance,
)
from src.bss.identifier import generate, parse as parse_id, validate as validate_id


@pytest.fixture
def env(tmp_path) -> BSSEnvironment:
    return BSSEnvironment.init(tmp_path)


def _make_id(env, author="A", relational="+", **kwargs):
    """Helper to generate a blink ID using the next sequence."""
    defaults = dict(
        action_energy="~", action_valence=".",
        confidence="!", cognitive="!",
        domain="#", subdomain="!", scope="=",
        maturity="~", priority="=", sensitivity=".",
    )
    defaults.update(kwargs)
    defaults["relational"] = relational
    seq = int(env.next_sequence(), 36)
    return generate(sequence=seq, author=author, **defaults)


def _write_origin(env, directory="active", author="A"):
    blink_id = _make_id(env, author=author, relational="^")
    blink = BlinkFile(
        blink_id=blink_id,
        born_from=["Origin"],
        summary="Origin blink for integration testing. This is the starting point.",
        lineage=[blink_id],
        links=[],
    )
    write_blink(blink, env.root / directory)
    return blink


def _write_continuation(env, parent, directory="active", author="A", **kwargs):
    blink_id = _make_id(env, author=author, relational="+", **kwargs)
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
# 5.1 — Full Workflow: Init → Write → Converge → Archive
# ============================================================


class TestFullWorkflow:
    """End-to-end test: init env → write origin → 7 continuations →
    force convergence → verify archive → validate graph."""

    def test_init_to_convergence(self, env):
        """Complete lifecycle from init through generation cap convergence."""
        # 1. Write origin
        origin = _write_origin(env)
        assert get_generation(env, origin.blink_id) == 1

        # 2. Build chain of 6 continuations (reaching generation 7)
        blink = origin
        for i in range(6):
            blink = _write_continuation(env, blink)

        assert get_generation(env, blink.blink_id) == 7
        assert needs_convergence(env, blink.blink_id) is True

        # 3. Force convergence
        chain = get_chain(env, blink.blink_id)
        assert len(chain) == 7

        conv = converge(
            env, chain,
            summary="Synthesizing seven generations of work. Full cycle complete. Reset.",
        )

        # 4. Verify convergence blink
        meta = parse_id(conv.blink_id)
        assert meta.relational == "{"
        assert get_generation(env, conv.blink_id) == 1
        assert conv.lineage == [conv.blink_id]
        assert len(conv.links) == 7  # References all chain members

        # 5. Continue from convergence — generation resets
        post_conv = _write_continuation(env, conv)
        assert get_generation(env, post_conv.blink_id) == 2

        # 6. Validate every blink in the environment
        all_blinks = env.scan("active")
        for b in all_blinks:
            valid, violations = validate_file(b)
            assert valid, f"Blink {b.blink_id} invalid: {violations}"

    def test_full_graph_integrity(self, env):
        """Every Born from reference is resolvable; every lineage is valid."""
        origin = _write_origin(env)
        c1 = _write_continuation(env, origin)
        c2 = _write_continuation(env, c1)
        c3 = _write_continuation(env, c2)

        all_blinks = env.scan("active")
        blink_ids = {b.blink_id for b in all_blinks}

        for b in all_blinks:
            # Born from should be resolvable (or Origin)
            if b.born_from != ["Origin"]:
                for parent in b.born_from:
                    assert parent in blink_ids, (
                        f"Blink {b.blink_id} references unresolvable parent {parent}"
                    )

            # Lineage should end with self
            assert b.lineage[-1] == b.blink_id

            # All lineage entries should be findable
            for lid in b.lineage:
                assert lid in blink_ids, (
                    f"Blink {b.blink_id} lineage references unfindable {lid}"
                )


# ============================================================
# 5.1 — Three-Model Relay Simulation
# ============================================================


class TestMultiModelRelay:
    """Simulate a 3-model relay: A writes handoff → B picks up →
    B writes error → A receives escalation → resolution written."""

    def test_three_model_relay(self, env):
        # Setup roster
        entries = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead agent"),
            RosterEntry("B", "Claude-B", "specialist", "regional", "Parser specialist"),
            RosterEntry("C", "Claude-C", "reviewer", "global", "Review agent"),
        ]
        update_roster(env, entries)

        # Model A starts work
        session_a = Session(env, author="A")
        session_a.intake()
        session_a.begin_work()

        # A writes work blink and handoff
        work = _write_origin(env, author="A")

        session_a.begin_output()
        h1 = handoff(
            env,
            summary="Completed initial parser design. Need B to implement edge case handling.",
            author="A",
            parent=work.blink_id,
        )
        session_a.dormancy()

        # Model B picks up
        session_b = Session(env, author="B")
        ctx_b = session_b.intake()
        assert len(ctx_b.relay_blinks) >= 1  # B sees A's handoff

        session_b.begin_work()

        # B encounters error
        err1 = error_blink(
            env,
            summary="Parser failed on escaped sigils in edge case. Need diagnosis from A.",
            author="B",
            parent=h1.blink_id,
        )

        session_b.begin_output()
        session_b.dormancy()

        # Model A picks up, sees error
        session_a2 = Session(env, author="A")
        ctx_a2 = session_a2.intake()

        # Check escalation — single error, no chain yet
        chains = check_escalation(env)
        assert len(chains) == 0  # Only one error, no chain

        # A writes resolution
        session_a2.begin_work()
        resolution = handoff(
            env,
            summary="Fixed the escaped sigil issue. Parser now handles all edge cases correctly.",
            author="A",
            parent=err1.blink_id,
        )

        session_a2.begin_output()
        session_a2.dormancy()

        # Verify relay has the full exchange
        relay_blinks = env.scan("relay")
        assert len(relay_blinks) >= 3

    def test_error_escalation_chain(self, env):
        """Two consecutive error blinks trigger escalation detection."""
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
        assert len(chains) == 1
        assert len(chains[0]) == 2

    def test_scope_compliance_in_relay(self, env):
        """Authors can't write above their scope ceiling."""
        entries = [
            RosterEntry("A", "Claude-A", "primary", "global", "Full access"),
            RosterEntry("B", "Claude-B", "specialist", "local", "Limited scope"),
        ]
        roster_blink = update_roster(env, entries)
        roster = read_roster(env)

        # B writes a global scope blink (should violate ceiling)
        global_id = _make_id(env, author="B", relational="^", scope="!")
        global_blink = BlinkFile(
            blink_id=global_id,
            born_from=["Origin"],
            summary="Attempting a global action from a local-scoped model. Not allowed.",
            lineage=[global_id],
            links=[],
        )

        assert check_scope_compliance(roster, "B", global_blink) is False

        # B writes a local scope blink (within ceiling)
        local_id = _make_id(env, author="B", relational="^", scope="-")
        local_blink = BlinkFile(
            blink_id=local_id,
            born_from=["Origin"],
            summary="Local action from local-scoped model. This is within bounds.",
            lineage=[local_id],
            links=[],
        )

        assert check_scope_compliance(roster, "B", local_blink) is True


# ============================================================
# 5.1 — Broken Link & Oversized Relay
# ============================================================


class TestBrokenLinks:
    """Broken link recovery and oversized relay handling."""

    def test_broken_born_from_reference(self, env):
        """Blink referencing nonexistent parent still parses but fails graph walk."""
        blink_id = _make_id(env, relational="+")
        blink = BlinkFile(
            blink_id=blink_id,
            born_from=["ZZZZZA~~^!!^;!!=."],  # Nonexistent parent
            summary="This blink references a parent that doesn't exist. Orphan test.",
            lineage=["ZZZZZA~~^!!^;!!=.", blink_id],
            links=[],
        )
        write_blink(blink, env.active_dir)

        # Parsing succeeds
        read_back = read_blink(env.active_dir / f"{blink_id}.md")
        assert read_back.born_from == ["ZZZZZA~~^!!^;!!=."]

        # Chain walk stops at the missing parent
        chain = get_chain(env, blink_id)
        assert len(chain) == 1  # Only the blink itself

    def test_relay_backlog_warning(self, env):
        """Relay exceeding threshold triggers warning."""
        for _ in range(12):
            handoff(
                env,
                summary="Handoff blink to fill the relay. Testing backlog thresholds.",
            )

        assert env.relay_count() == 12
        with pytest.warns(UserWarning, match="exceeding recommended limit"):
            env.check_relay_backlog()


# ============================================================
# 5.2 — Edge Case Hardening
# ============================================================


class TestEdgeCases:
    """Edge case hardening per Module 5.9 and beyond."""

    def test_cold_start_empty_environment(self, env):
        """Empty environment cold start produces empty context."""
        session = Session(env)
        ctx = session.intake()

        assert ctx.relay_blinks == []
        assert ctx.active_blinks == []
        assert ctx.profile_blinks == []
        assert ctx.highest_sequence == "00000"

    def test_archive_subdivision(self, env):
        """Blinks in archive subdirectories are findable."""
        origin = _write_origin(env)

        # Create archive subdirectory
        subdir = env.archive_dir / "foundation"
        subdir.mkdir(parents=True, exist_ok=True)

        # Move blink to archive subdirectory
        env.move_blink(origin.blink_id, "archive/foundation")

        # Should still be findable
        found = env.find_blink(origin.blink_id)
        assert found is not None
        assert "archive" in str(found)
        assert "foundation" in str(found)

    def test_file_size_hard_reject(self, env):
        """Blink exceeding MAX_FILE_SIZE fails validation."""
        blink_id = _make_id(env, relational="^")
        blink = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="X" * 1900 + ". " + "Y" * 100 + ".",
            lineage=[blink_id],
            links=[],
        )
        valid, violations = validate_file(blink)
        assert not valid
        assert any("exceeds maximum" in v.lower() or "size" in v.lower() for v in violations)

    def test_unicode_in_summary(self, env):
        """Unicode characters in summary are valid."""
        blink_id = _make_id(env, relational="^")
        blink = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="Developed the Zusammenfassung module with full Umlaut support: aou. Tested extensively.",
            lineage=[blink_id],
            links=[],
        )
        valid, violations = validate_file(blink)
        assert valid, f"Unicode summary should be valid: {violations}"

        write_blink(blink, env.active_dir)
        read_back = read_blink(env.active_dir / f"{blink_id}.md")
        assert "Zusammenfassung" in read_back.summary

    def test_cjk_in_summary(self, env):
        """CJK characters work in summaries."""
        blink_id = _make_id(env, relational="^")
        blink = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="Testing CJK support. This is valid content.",
            lineage=[blink_id],
            links=[],
        )
        valid, violations = validate_file(blink)
        assert valid

    def test_sequence_wraps_correctly(self, env):
        """Sequences increment correctly through base-36 alphabet."""
        origin = _write_origin(env)
        assert env.highest_sequence() == origin.blink_id[:5]

        cont = _write_continuation(env, origin)
        assert env.highest_sequence() == cont.blink_id[:5]

    def test_double_dot_filename_round_trip(self, env):
        """Blink IDs ending with '.' produce .md files with double dots."""
        blink_id = _make_id(env, relational="^", sensitivity=".")
        assert blink_id.endswith(".")

        blink = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="Testing double-dot filename handling. Critical for sigils ending in dot.",
            lineage=[blink_id],
            links=[],
        )
        path = write_blink(blink, env.active_dir)

        # Filename should have double dot before .md
        assert path.name.endswith("..md")

        # Round-trip: read back should recover full 17-char ID
        read_back = read_blink(path)
        assert read_back.blink_id == blink_id
        assert len(read_back.blink_id) == 17

    def test_immutability_across_move(self, env):
        """Moving a blink preserves its content exactly."""
        origin = _write_origin(env)
        env.scan("active")  # Record integrity hash

        # Move to archive
        env.move_blink(origin.blink_id, "archive")

        # Re-read and validate
        found = env.find_blink(origin.blink_id)
        assert found is not None
        read_back = read_blink(found)
        assert read_back.blink_id == origin.blink_id
        assert read_back.born_from == ["Origin"]

    def test_immutability_detects_tampering(self, env):
        """Tampering with a blink file after read is detected."""
        origin = _write_origin(env)
        env.scan("active")  # Record integrity hash

        # Tamper with file
        path = env.find_blink(origin.blink_id)
        content = path.read_text()
        path.write_text(content + "\nTampered!")

        assert env.check_immutability(origin.blink_id) is False


# ============================================================
# 5.2 — Collision Detection
# ============================================================


class TestCollisionDetection:
    """Sequence collision edge cases."""

    def test_duplicate_id_across_directories(self, env):
        """Same blink ID in two directories is detectable."""
        origin = _write_origin(env)

        # Write same content to profile (simulating a copy)
        write_blink(origin, env.profile_dir)

        # find_blink returns the first match (relay → active → profile)
        found = env.find_blink(origin.blink_id)
        assert found is not None
        # It should find the active/ one first (relay is empty, active is checked before profile)
        assert found.parent == env.active_dir


# ============================================================
# 5.2 — Triage Ordering End-to-End
# ============================================================


class TestTriageEndToEnd:
    """Triage ordering works correctly in a realistic relay."""

    def test_triage_prioritizes_errors_over_handoffs(self, env):
        """Error blinks (priority !) sort before handoffs (priority =)."""
        h1 = handoff(
            env,
            summary="Normal handoff blink. Routine work completed successfully.",
        )
        err = error_blink(
            env,
            summary="Critical error encountered. Needs immediate attention from next agent.",
        )
        h2 = handoff(
            env,
            summary="Another routine handoff. Nothing urgent here at all.",
        )

        triaged = env.triage("relay")
        # Error should be first (priority !)
        assert triaged[0].blink_id == err.blink_id

    def test_triage_recency_within_same_priority(self, env):
        """Within same priority, more recent (higher sequence) comes first."""
        h1 = handoff(
            env,
            summary="First handoff. This one was written earlier in the sequence.",
        )
        h2 = handoff(
            env,
            summary="Second handoff. This one was written later in the sequence.",
        )

        triaged = env.triage("relay")
        # h2 should come first (higher sequence = more recent)
        assert triaged[0].blink_id == h2.blink_id


# ============================================================
# 5.5 — Cross-Directory Operations
# ============================================================


class TestCrossDirectory:
    """Operations spanning multiple directories."""

    def test_generation_tracking_across_directories(self, env):
        """Generation chain works even when parent is in different directory."""
        origin = _write_origin(env, directory="active")

        # Write continuation to relay
        cont = handoff(
            env,
            summary="Handing off from active to relay. The chain should still be trackable.",
            author="A",
            parent=origin.blink_id,
        )

        # Generation should increment correctly
        assert get_generation(env, origin.blink_id) == 1
        assert get_generation(env, cont.blink_id) == 2

    def test_chain_walk_across_archive(self, env):
        """Chain walking works when ancestors are in archive."""
        origin = _write_origin(env)
        c1 = _write_continuation(env, origin)

        # Archive the origin
        env.move_blink(origin.blink_id, "archive")

        # Chain walk should still reach origin through archive
        chain = get_chain(env, c1.blink_id)
        assert len(chain) == 2
        assert chain[0].blink_id == origin.blink_id


# ============================================================
# 5.3 — Roster Operations End-to-End
# ============================================================


class TestRosterEndToEnd:
    """Roster lifecycle from creation through update."""

    def test_roster_create_and_read(self, env):
        entries = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead"),
            RosterEntry("B", "Claude-B", "specialist", "local", "Parser"),
        ]
        roster_blink = update_roster(env, entries)

        roster = read_roster(env)
        assert roster is not None
        assert len(roster.entries) == 2
        assert roster.get_entry("A").model_id == "Claude-A"
        assert roster.get_scope_ceiling("B") == "local"

    def test_roster_update_archives_old(self, env):
        """Updating roster archives the previous version."""
        entries_v1 = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead"),
        ]
        r1 = update_roster(env, entries_v1)

        entries_v2 = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead"),
            RosterEntry("B", "Claude-B", "specialist", "regional", "New member"),
        ]
        r2 = update_roster(env, entries_v2, old_roster_id=r1.blink_id)

        # Old roster should be in archive
        old_path = env.find_blink(r1.blink_id)
        assert old_path is not None
        assert "archive" in str(old_path)

        # New roster should be in profile
        new_path = env.find_blink(r2.blink_id)
        assert new_path is not None
        assert "profile" in str(new_path)

        # read_roster should return the new one
        roster = read_roster(env)
        assert len(roster.entries) == 2


# ============================================================
# 5.5 — Artifact Integration
# ============================================================


class TestArtifactIntegration:
    """Artifact registration and discovery."""

    def test_register_and_find_artifact(self, env):
        origin = _write_origin(env)

        # Create a source file
        src_file = env.root / "temp_test.py"
        src_file.write_text("# test artifact content")

        # Register as artifact
        artifact_path = env.register_artifact(
            origin.blink_id, src_file, "test-module"
        )

        assert artifact_path.exists()
        seq = origin.blink_id[:5]
        author = origin.blink_id[5]
        assert artifact_path.name == f"{seq}{author}-test-module.py"

        # Find it
        found = env.find_artifact(seq, author)
        assert found is not None
        assert found == artifact_path


# ============================================================
# 5.5 — Validate All Blinks in Multi-Blink Environment
# ============================================================


class TestBulkValidation:
    """Validate every blink in a realistic environment."""

    def test_validate_all_blinks_after_workflow(self, env):
        """After a complex workflow, every blink validates."""
        # Create a roster
        entries = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead"),
        ]
        update_roster(env, entries)

        # Write a chain
        origin = _write_origin(env)
        blink = origin
        for _ in range(3):
            blink = _write_continuation(env, blink)

        # Write handoff and error
        handoff(env, summary="Handing off. Everything is stable. Good session.")
        error_blink(env, summary="Error found post-handoff. Edge case in parser. Need fix.")

        # Validate everything
        for dirname in ["relay", "active", "profile"]:
            for b in env.scan(dirname):
                valid, violations = validate_file(b)
                assert valid, f"{b.blink_id} in {dirname}: {violations}"

    def test_tree_trace_from_latest_to_origin(self, env):
        """Lineage traces from latest blink back to origin."""
        origin = _write_origin(env)
        c1 = _write_continuation(env, origin)
        c2 = _write_continuation(env, c1)
        c3 = _write_continuation(env, c2)

        # c3's lineage should trace back
        assert c3.lineage[0] == origin.blink_id
        assert c3.lineage[-1] == c3.blink_id

        # Chain walk should match lineage
        chain = get_chain(env, c3.blink_id)
        assert len(chain) == 4
        assert [b.blink_id for b in chain] == c3.lineage


# ============================================================
# 5.6 — Roster Management End-to-End
# ============================================================


class TestRosterManagementEndToEnd:
    """Full roster lifecycle: create → add → update → config → remove."""

    def test_roster_lifecycle(self, env):
        """Full cycle: create roster, add model, update, generate config, remove."""
        from src.bss.roster import generate_model_config

        # 1. Create initial roster with one model
        entries_v1 = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead agent"),
        ]
        r1 = update_roster(env, entries_v1)
        roster = read_roster(env)
        assert len(roster.entries) == 1

        # 2. Add a second model
        entries_v2 = list(roster.entries) + [
            RosterEntry("B", "Claude-B", "specialist", "local", "Parser module"),
        ]
        r2 = update_roster(env, entries_v2, old_roster_id=roster.blink_id)

        # Old roster archived
        old_path = env.find_blink(r1.blink_id)
        assert old_path is not None
        assert "archive" in str(old_path)

        # New roster in profile
        roster = read_roster(env)
        assert len(roster.entries) == 2

        # 3. Update B's ceiling
        new_entries = []
        for e in roster.entries:
            if e.sigil == "B":
                new_entries.append(RosterEntry("B", e.model_id, e.role, "regional", e.notes))
            else:
                new_entries.append(e)
        r3 = update_roster(env, new_entries, old_roster_id=roster.blink_id)

        roster = read_roster(env)
        assert roster.get_entry("B").scope_ceiling == "regional"

        # 4. Generate config for B
        config = generate_model_config(roster, "B", env)
        assert "Author sigil: B" in config
        assert "regional" in config
        assert "<-- you" in config

        # 5. Scope compliance: B at regional can write regional but not global
        regional_id = _make_id(env, author="B", relational="^", scope="=")
        regional_blink = BlinkFile(
            blink_id=regional_id,
            born_from=["Origin"],
            summary="Regional action from B. This should be within scope ceiling.",
            lineage=[regional_id],
            links=[],
        )
        assert check_scope_compliance(roster, "B", regional_blink) is True

        global_id = _make_id(env, author="B", relational="^", scope="!")
        global_blink = BlinkFile(
            blink_id=global_id,
            born_from=["Origin"],
            summary="Global action from B. This should exceed the scope ceiling.",
            lineage=[global_id],
            links=[],
        )
        assert check_scope_compliance(roster, "B", global_blink) is False

        # 6. Remove B
        final_entries = [e for e in roster.entries if e.sigil != "B"]
        r4 = update_roster(env, final_entries, old_roster_id=roster.blink_id)

        roster = read_roster(env)
        assert len(roster.entries) == 1
        assert roster.get_entry("B") is None
        assert roster.get_entry("A") is not None

        # 7. Validate all blinks
        for dirname in ["relay", "active", "profile"]:
            for b in env.scan(dirname):
                valid, violations = validate_file(b)
                assert valid, f"{b.blink_id} in {dirname}: {violations}"

    def test_artifact_with_roster_integration(self, env):
        """Artifacts work alongside roster management."""
        from src.bss.roster import generate_model_config

        # Setup roster
        entries = [
            RosterEntry("A", "Claude-A", "primary", "global", "Lead"),
        ]
        update_roster(env, entries)

        # Write origin blink
        origin = _write_origin(env)

        # Register an artifact
        src_file = env.root / "temp_code.py"
        src_file.write_text("# artifact content")
        artifact = env.register_artifact(origin.blink_id, src_file, "code-module")
        assert artifact.exists()

        # List artifacts
        artifacts = env.list_artifacts()
        assert len(artifacts) == 1

        # Find parent via prefix
        prefix = artifact.name[:6]
        parent = env.find_blink_by_prefix(prefix)
        assert parent is not None

        # Config should show relay state reflecting the blinks
        roster = read_roster(env)
        config = generate_model_config(roster, "A", env)
        assert "Next sequence" in config
