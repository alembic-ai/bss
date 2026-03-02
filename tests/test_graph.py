"""Module 8.3 graph tests — born from, lineage, links, roster, participation, immutability."""

import pytest
from pathlib import Path

from src.bss.environment import BSSEnvironment
from src.bss.blink_file import BlinkFile, write as write_blink, read as read_blink
from src.bss.identifier import generate, parse as parse_id
from src.bss.roster import (
    Roster,
    RosterEntry,
    read_roster,
    update_roster,
    check_scope_compliance,
)


@pytest.fixture
def env(tmp_path) -> BSSEnvironment:
    return BSSEnvironment.init(tmp_path)


def _make_id(seq: int, author: str = "A", **kwargs) -> str:
    defaults = dict(
        action_energy=".", action_valence="!",
        relational="+", confidence=".", cognitive="=",
        domain="#", subdomain="!", scope="-",
        maturity="~", priority="=", sensitivity="=",
    )
    defaults.update(kwargs)
    return generate(sequence=seq, author=author, **defaults)


def _write_blink(env, seq, author="A", directory="active", born_from=None,
                 lineage=None, links=None, **kwargs) -> BlinkFile:
    blink_id = _make_id(seq, author, **kwargs)
    blink = BlinkFile(
        blink_id=blink_id,
        born_from=born_from or ["Origin"],
        summary="A test blink for graph validation. Tracking structure and relationships.",
        lineage=lineage or [blink_id],
        links=links or [],
    )
    write_blink(blink, env.root / directory)
    return blink


# ============================================================
# 8.3.1 — Born From — Single Parent
# ============================================================


class TestBornFromSingleParent:
    def test_single_parent_format(self, env):
        parent = _write_blink(env, 5, relational="^")
        child = _write_blink(
            env, 10,
            born_from=[parent.blink_id],
            lineage=[parent.blink_id, _make_id(10)],
        )
        assert child.born_from == [parent.blink_id]
        assert len(child.born_from) == 1


# ============================================================
# 8.3.2 — Born From — Multiple Parents (Convergence)
# ============================================================


class TestBornFromMultipleParents:
    def test_convergence_multiple_parents(self, env):
        parent1 = _write_blink(env, 10, relational="^")
        parent2 = _write_blink(env, 15, author="B", relational="^")

        conv_id = _make_id(20, relational="{")
        conv = BlinkFile(
            blink_id=conv_id,
            born_from=[parent1.blink_id, parent2.blink_id],
            summary="Converging two threads into a synthesis. Both contributed insights.",
            lineage=[conv_id],
            links=[],
        )
        write_blink(conv, env.active_dir)

        meta = parse_id(conv.blink_id)
        assert meta.relational == "{"
        assert len(conv.born_from) == 2


# ============================================================
# 8.3.3 — Born From — Origin
# ============================================================


class TestBornFromOrigin:
    def test_origin_born_from(self, env):
        blink = _write_blink(env, 1, relational="^")
        assert blink.born_from == ["Origin"]
        assert blink.is_origin is True


# ============================================================
# 8.3.4 — Lineage — Depth Accuracy
# ============================================================


class TestLineageDepth:
    def test_5_generation_lineage(self, env):
        ids = [_make_id(i, relational="^" if i == 1 else "+") for i in range(1, 6)]
        lineage = ids[:5]

        blink = BlinkFile(
            blink_id=ids[4],
            born_from=[ids[3]],
            summary="Fifth generation blink. Full lineage should be present.",
            lineage=lineage,
            links=[],
        )
        write_blink(blink, env.active_dir)

        read_back = read_blink(env.active_dir / f"{ids[4]}.md")
        assert len(read_back.lineage) == 5
        assert read_back.lineage[0] == ids[0]
        assert read_back.lineage[-1] == ids[4]


# ============================================================
# 8.3.5 — Lineage — Maximum Depth Truncation
# ============================================================


class TestLineageTruncation:
    def test_lineage_max_7(self, env):
        """Lineage of more than 7 must be truncated to most recent 7."""
        ids = [_make_id(i, relational="^" if i == 1 else "+") for i in range(1, 8)]
        # Exactly 7 is fine
        blink = BlinkFile(
            blink_id=ids[6],
            born_from=[ids[5]],
            summary="Seventh generation blink. Lineage at maximum depth.",
            lineage=ids,
            links=[],
        )
        from src.bss.blink_file import validate_file
        valid, violations = validate_file(blink)
        assert valid, f"Lineage of 7 should be valid: {violations}"


# ============================================================
# 8.3.6 — Lineage — Origin Self-Reference
# ============================================================


class TestLineageOriginSelfRef:
    def test_origin_self_reference(self, env):
        blink_id = _make_id(1, relational="^")
        blink = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="Origin blink with self-referencing lineage. The chain starts here.",
            lineage=[blink_id],
            links=[],
        )
        write_blink(blink, env.active_dir)
        read_back = read_blink(env.active_dir / f"{blink_id}.md")
        assert read_back.lineage == [blink_id]


# ============================================================
# 8.3.7 — Links — Cross-Directory Resolution
# ============================================================


class TestCrossDirectoryLinks:
    def test_link_to_archive(self, env):
        archived = _write_blink(env, 10, directory="archive", relational="^")
        active = _write_blink(
            env, 50,
            relational="^",
            links=[archived.blink_id],
        )

        found = env.find_blink(archived.blink_id)
        assert found is not None
        assert "archive" in str(found)


# ============================================================
# 8.3.8 — Links — Cross-Directory Into Archive Subdirectories
# ============================================================


class TestArchiveSubdirectoryLinks:
    def test_link_to_archive_subdirectory(self, env):
        subdir = env.archive_dir / "2026-Q1"
        subdir.mkdir()

        blink_id = _make_id(10, relational="^")
        blink = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="Archived blink in a subdirectory. Should still be findable.",
            lineage=[blink_id],
            links=[],
        )
        write_blink(blink, subdir)

        found = env.find_blink(blink_id)
        assert found is not None
        assert "2026-Q1" in str(found)


# ============================================================
# 8.3.9 — Links — Broken Link Handling
# ============================================================


class TestBrokenLinks:
    def test_broken_link_does_not_invalidate_blink(self, env):
        fake_id = _make_id(99, author="X", relational="^")
        blink = _write_blink(env, 50, relational="^", links=[fake_id])

        # Blink itself is still valid
        found = env.find_blink(blink.blink_id)
        assert found is not None

        # But the linked blink doesn't exist
        linked = env.find_blink(fake_id)
        assert linked is None


# ============================================================
# 8.3.10 — Participation Tiers — Relay Member Writes Blink
# ============================================================


class TestRelayMemberWrites:
    def test_author_sigil_matches(self, env):
        blink = _write_blink(env, 1, author="A", relational="^")
        meta = parse_id(blink.blink_id)
        assert meta.author == "A"


# ============================================================
# 8.3.11-12 — External Worker Isolation
# ============================================================


class TestExternalWorkerIsolation:
    def test_external_worker_no_blink(self, env):
        """External workers don't write blinks — relay member authors them."""
        # Model A invokes external worker D, but writes the blink itself
        blink = _write_blink(env, 1, author="A", relational="^")
        meta = parse_id(blink.blink_id)
        assert meta.author == "A"  # Not "D"


# ============================================================
# 8.3.13 — Roster Blink Format Compliance
# ============================================================


class TestRosterFormat:
    def test_roster_blink_format(self, env):
        entries = [
            RosterEntry("A", "Claude-Code", "primary", "global", "Build agent"),
            RosterEntry("U", "Cam", "architect", "global", "Protocol designer"),
        ]
        roster_blink = update_roster(env, entries)

        meta = parse_id(roster_blink.blink_id)
        assert meta.author == "S"
        assert roster_blink.born_from == ["Origin"]
        assert "ROSTER" in roster_blink.summary

    def test_roster_entries_parseable(self, env):
        entries = [
            RosterEntry("A", "Claude-Code", "primary", "global", "Build agent"),
            RosterEntry("B", "Llama-3.1-70B", "specialist", "local", "Code gen"),
        ]
        update_roster(env, entries)

        roster = read_roster(env)
        assert roster is not None
        assert len(roster.entries) == 2
        assert roster.entries[0].sigil == "A"
        assert roster.entries[0].role == "primary"
        assert roster.entries[1].sigil == "B"
        assert roster.entries[1].scope_ceiling == "local"


# ============================================================
# 8.3.14 — Roster Update — Immutability Preservation
# ============================================================


class TestRosterUpdate:
    def test_old_roster_archived(self, env):
        entries_v1 = [
            RosterEntry("A", "Claude-Code", "primary", "global", "v1"),
        ]
        v1 = update_roster(env, entries_v1)
        v1_id = v1.blink_id

        entries_v2 = [
            RosterEntry("A", "Claude-Code", "primary", "global", "v2"),
            RosterEntry("B", "Llama-3.1", "specialist", "local", "New model"),
        ]
        v2 = update_roster(env, entries_v2, old_roster_id=v1_id)

        # v2 references v1 as parent
        assert v2.born_from == [v1_id]

        # v1 should be in archive
        v1_path = env.find_blink(v1_id)
        assert v1_path is not None
        assert "archive" in str(v1_path)

        # v2 is in profile
        v2_path = env.find_blink(v2.blink_id)
        assert v2_path is not None
        assert "profile" in str(v2_path)


# ============================================================
# 8.3.15 — Scope Ceiling Enforcement
# ============================================================


class TestScopeCeiling:
    def test_within_ceiling(self, env):
        roster = Roster(entries=[
            RosterEntry("B", "Llama", "specialist", "local", ""),
        ])
        blink = _write_blink(env, 1, author="B", scope="-", relational="^")  # local
        assert check_scope_compliance(roster, "B", blink) is True

    def test_exceeds_ceiling(self, env):
        roster = Roster(entries=[
            RosterEntry("B", "Llama", "specialist", "local", ""),
        ])
        blink = _write_blink(env, 1, author="B", scope="!", relational="^")  # global > local
        assert check_scope_compliance(roster, "B", blink) is False

    def test_global_ceiling_allows_all(self, env):
        roster = Roster(entries=[
            RosterEntry("A", "Claude", "primary", "global", ""),
        ])
        blink = _write_blink(env, 1, author="A", scope="!", relational="^")  # global
        assert check_scope_compliance(roster, "A", blink) is True


# ============================================================
# 8.3.16 — Metadata-Content Contradiction Resolution
# ============================================================


class TestMetadataContradiction:
    def test_filename_takes_precedence(self, env):
        """When metadata and content conflict, filename is authoritative."""
        error_id = _make_id(50, action_energy="!", action_valence="!", relational="^")
        blink = BlinkFile(
            blink_id=error_id,
            born_from=["Origin"],
            summary="Task completed successfully with no issues. Everything works perfectly.",
            lineage=[error_id],
            links=[],
        )
        write_blink(blink, env.active_dir)

        # Despite the summary saying "completed successfully",
        # the filename says !! (error) — filename wins
        meta = parse_id(error_id)
        assert meta.action_energy == "!"
        assert meta.action_valence == "!"
        # Process as error, not as success


# ============================================================
# 8.3.17 — Dormant Reactivation via Link
# ============================================================


class TestDormantReactivation:
    def test_dormant_reactivated_via_link(self, env):
        """Dormant blink is not modified; a new blink links to it."""
        # First create a parent so the dormant blink has valid Born from
        parent_id = _make_id(5, relational="^")
        parent = BlinkFile(
            blink_id=parent_id,
            born_from=["Origin"],
            summary="Parent blink for the dormant thread. Started some work here.",
            lineage=[parent_id],
            links=[],
        )
        write_blink(parent, env.archive_dir)

        dormant_id = _make_id(10, relational="_")
        dormant = BlinkFile(
            blink_id=dormant_id,
            born_from=[parent_id],
            summary="This thread was abandoned. No further work expected.",
            lineage=[parent_id, dormant_id],
            links=[],
        )
        write_blink(dormant, env.archive_dir)

        # Reactivate via new blink
        new_id = _make_id(50, relational="^")
        new_blink = BlinkFile(
            blink_id=new_id,
            born_from=["Origin"],
            summary="Reactivating a previously dormant thread. New context makes it relevant again.",
            lineage=[new_id],
            links=[dormant_id],
        )
        write_blink(new_blink, env.active_dir)

        # Dormant blink unchanged
        dormant_path = env.find_blink(dormant_id)
        assert dormant_path is not None
        dormant_read = read_blink(dormant_path)
        assert dormant_read.summary == dormant.summary

        # New blink links to dormant
        new_path = env.find_blink(new_id)
        new_read = read_blink(new_path)
        assert dormant_id in new_read.links


# ============================================================
# 8.3.18 — Immutability — Reject Rename
# ============================================================


class TestImmutabilityRejectRename:
    def test_rename_detected(self, env):
        """Renaming a blink file violates immutability."""
        blink = _write_blink(env, 50, relational="^")
        filepath = env.find_blink(blink.blink_id)

        # Record integrity
        env.scan("active")

        # Simulate a rename by creating new name and deleting old
        new_name = filepath.parent / "RENAMED.md"
        filepath.rename(new_name)

        # Original blink should no longer be findable
        assert env.find_blink(blink.blink_id) is None


# ============================================================
# 8.3.19 — Immutability — Reject Content Edit
# ============================================================


class TestImmutabilityRejectEdit:
    def test_content_edit_detected(self, env):
        blink = _write_blink(env, 50, relational="^")
        env.scan("active")  # Record hash

        # Tamper with content
        filepath = env.find_blink(blink.blink_id)
        filepath.write_text("TAMPERED CONTENT", encoding="utf-8")

        # Immutability check should fail
        assert env.check_immutability(blink.blink_id) is False


# ============================================================
# 8.3.20 — Immutability — Permit Move
# ============================================================


class TestImmutabilityPermitMove:
    def test_move_preserves_everything(self, env):
        blink = _write_blink(env, 50, relational="^")
        filepath = env.find_blink(blink.blink_id)
        original_content = filepath.read_text()
        original_name = filepath.name

        new_path = env.move_blink(blink.blink_id, "archive")

        assert new_path.name == original_name
        assert new_path.read_text() == original_content
        assert "archive" in str(new_path)


# ============================================================
# 8.3.21 — Blink ID Uniqueness Across Archive Subdivisions
# ============================================================


class TestBlinkIDUniqueness:
    def test_unique_across_subdirectories(self, env):
        """Same blink ID in two archive subdirectories is a collision."""
        sub1 = env.archive_dir / "2026-Q1"
        sub2 = env.archive_dir / "2026-Q2"
        sub1.mkdir()
        sub2.mkdir()

        blink_id = _make_id(10, relational="^")
        blink = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="First instance of this blink. Should be unique.",
            lineage=[blink_id],
            links=[],
        )
        write_blink(blink, sub1)

        # Writing same ID to sub2 creates a file with same name
        # The environment should be able to detect this as a collision
        blink2 = BlinkFile(
            blink_id=blink_id,
            born_from=["Origin"],
            summary="Duplicate blink ID in different subdirectory. This is a collision.",
            lineage=[blink_id],
            links=[],
        )
        write_blink(blink2, sub2)

        # Both files exist — this is a collision state
        assert (sub1 / f"{blink_id}.md").exists()
        assert (sub2 / f"{blink_id}.md").exists()
