"""Tests for BSS environment manager."""

import pytest
from pathlib import Path

from src.bss.environment import BSSEnvironment, sort_by_triage
from src.bss.blink_file import BlinkFile, write as write_blink
from src.bss.identifier import generate


@pytest.fixture
def bss_env(tmp_path) -> BSSEnvironment:
    """Create a fresh BSS environment for testing."""
    return BSSEnvironment.init(tmp_path)


def _make_blink(sequence: int, author: str = "A", **kwargs) -> BlinkFile:
    """Helper to create a valid blink with specific attributes."""
    defaults = dict(
        action_energy="~", action_valence="!",
        relational="+", confidence=".", cognitive="=",
        domain="#", subdomain="!", scope="-",
        maturity="~", priority="=", sensitivity="=",
    )
    defaults.update(kwargs)

    if sequence == 1 and defaults.get("relational") == "+":
        defaults["relational"] = "^"

    blink_id = generate(sequence=sequence, author=author, **defaults)

    if defaults["relational"] == "^":
        born_from = ["Origin"]
        lineage = [blink_id]
    else:
        # Simple parent reference
        parent_id = generate(sequence=sequence - 1, author=author,
                             relational="^" if sequence == 2 else "+",
                             action_energy="~", action_valence="~",
                             confidence="!", cognitive="!",
                             domain="^", subdomain=";", scope="!",
                             maturity=",", priority="=", sensitivity=".")
        born_from = [parent_id]
        lineage = [parent_id, blink_id]

    return BlinkFile(
        blink_id=blink_id,
        born_from=born_from,
        summary="Working on a task in the environment. Making steady progress forward.",
        lineage=lineage,
        links=[],
    )


# ============================================================
# Init Tests
# ============================================================


class TestInit:
    """BSSEnvironment.init() tests."""

    def test_creates_required_directories(self, tmp_path):
        env = BSSEnvironment.init(tmp_path)
        assert (tmp_path / "relay").is_dir()
        assert (tmp_path / "active").is_dir()
        assert (tmp_path / "profile").is_dir()
        assert (tmp_path / "archive").is_dir()

    def test_creates_artifacts_directory(self, tmp_path):
        env = BSSEnvironment.init(tmp_path)
        assert (tmp_path / "artifacts").is_dir()

    def test_is_valid(self, bss_env):
        assert bss_env.is_valid()

    def test_idempotent(self, tmp_path):
        """init() can be called multiple times without error."""
        BSSEnvironment.init(tmp_path)
        BSSEnvironment.init(tmp_path)
        assert (tmp_path / "relay").is_dir()


# ============================================================
# Sequence Tests
# ============================================================


class TestSequence:
    """highest_sequence() and next_sequence() tests."""

    def test_empty_environment(self, bss_env):
        assert bss_env.highest_sequence() == "00000"
        assert bss_env.next_sequence() == "00001"

    def test_after_one_blink(self, bss_env):
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.active_dir)
        assert bss_env.highest_sequence() == "00001"
        assert bss_env.next_sequence() == "00002"

    def test_scans_all_directories(self, bss_env):
        """highest_sequence scans relay, active, profile, archive."""
        b1 = _make_blink(1, relational="^")
        b5 = _make_blink(5)
        b10 = _make_blink(10)

        write_blink(b1, bss_env.relay_dir)
        write_blink(b5, bss_env.active_dir)
        write_blink(b10, bss_env.profile_dir)

        assert bss_env.highest_sequence() == "0000A"  # 10 in base-36
        assert bss_env.next_sequence() == "0000B"


# ============================================================
# Find Tests
# ============================================================


class TestFind:
    """find_blink() tests."""

    def test_find_in_active(self, bss_env):
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.active_dir)
        found = bss_env.find_blink(blink.blink_id)
        assert found is not None
        assert found.parent == bss_env.active_dir

    def test_find_in_relay(self, bss_env):
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.relay_dir)
        found = bss_env.find_blink(blink.blink_id)
        assert found is not None
        assert found.parent == bss_env.relay_dir

    def test_find_in_archive_subdirectory(self, bss_env):
        """find_blink resolves across archive subdirectories."""
        subdir = bss_env.archive_dir / "2026-Q1"
        subdir.mkdir()
        blink = _make_blink(1, relational="^")
        write_blink(blink, subdir)
        found = bss_env.find_blink(blink.blink_id)
        assert found is not None
        assert "2026-Q1" in str(found)

    def test_find_nonexistent(self, bss_env):
        found = bss_env.find_blink("99999Z~~+.=#.-~..")
        assert found is None


# ============================================================
# Move Tests
# ============================================================


class TestMove:
    """move_blink() tests."""

    def test_move_preserves_filename(self, bss_env):
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.active_dir)
        new_path = bss_env.move_blink(blink.blink_id, "archive")
        assert new_path.name == f"{blink.blink_id}.md"

    def test_move_preserves_content(self, bss_env):
        blink = _make_blink(1, relational="^")
        filepath = write_blink(blink, bss_env.active_dir)
        original_content = filepath.read_text()
        new_path = bss_env.move_blink(blink.blink_id, "archive")
        assert new_path.read_text() == original_content

    def test_move_removes_from_source(self, bss_env):
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.active_dir)
        bss_env.move_blink(blink.blink_id, "archive")
        assert not (bss_env.active_dir / f"{blink.blink_id}.md").exists()

    def test_move_nonexistent_raises(self, bss_env):
        with pytest.raises(FileNotFoundError):
            bss_env.move_blink("99999Z~~+.=#.-~..", "archive")


# ============================================================
# Triage Ordering Tests (Module 8.2.3 - 8.2.5)
# ============================================================


class TestTriageOrdering:
    """Triage ordering matches Module 8.2.3-8.2.5 test cases."""

    def test_urgency_ordering(self, bss_env):
        """Module 8.2.3: Urgency-based triage ordering.

        Three blinks with different urgency levels:
        - Seq 5: priority ^ (High), sensitivity = (Whenever)  → ^=
        - Seq 3: priority ! (Critical), sensitivity ! (Blocking) → !!
        - Seq 7: priority ! (Critical), sensitivity ^ (Soon)   → !^

        Expected order: !! → !^ → ^=
        """
        b5 = _make_blink(5, priority="^", sensitivity="=")
        b3 = _make_blink(3, priority="!", sensitivity="!")
        b7 = _make_blink(7, priority="!", sensitivity="^")

        write_blink(b5, bss_env.relay_dir)
        write_blink(b3, bss_env.relay_dir)
        write_blink(b7, bss_env.relay_dir)

        triaged = bss_env.triage("relay")
        assert len(triaged) == 3
        # First: Critical + Blocking (seq 3)
        assert triaged[0].blink_id == b3.blink_id
        # Second: Critical + Soon (seq 7)
        assert triaged[1].blink_id == b7.blink_id
        # Third: High + Whenever (seq 5)
        assert triaged[2].blink_id == b5.blink_id

    def test_recency_tiebreak(self, bss_env):
        """Module 8.2.4: When urgency is tied, recency breaks the tie.

        Two blinks with identical urgency (^=):
        - Seq 10
        - Seq 25

        Expected: Seq 25 first (more recent).
        """
        b10 = _make_blink(10, priority="^", sensitivity="=")
        b25 = _make_blink(25, priority="^", sensitivity="=")

        write_blink(b10, bss_env.relay_dir)
        write_blink(b25, bss_env.relay_dir)

        triaged = bss_env.triage("relay")
        assert triaged[0].blink_id == b25.blink_id
        assert triaged[1].blink_id == b10.blink_id

    def test_scope_tiebreak(self, bss_env):
        """Module 8.2.5: Scope as third tiebreaker after urgency + recency.

        Two blinks with identical urgency (^=) and adjacent sequences:
        - Seq 10: scope = (Regional)
        - Seq 11: scope ! (Global)

        Expected: Seq 11 first (recency takes precedence over scope).
        """
        b10 = _make_blink(10, priority="^", sensitivity="=", scope="=")
        b11 = _make_blink(11, priority="^", sensitivity="=", scope="!")

        write_blink(b10, bss_env.relay_dir)
        write_blink(b11, bss_env.relay_dir)

        triaged = bss_env.triage("relay")
        assert triaged[0].blink_id == b11.blink_id  # Recency wins


# ============================================================
# Immutability Tests
# ============================================================


class TestImmutability:
    """Immutability checking tests."""

    def test_unchanged_blink_passes(self, bss_env):
        blink = _make_blink(1, relational="^")
        filepath = write_blink(blink, bss_env.active_dir)
        # First read records hash
        bss_env.scan("active")
        assert bss_env.check_immutability(blink.blink_id) is True

    def test_modified_blink_fails(self, bss_env):
        blink = _make_blink(1, relational="^")
        filepath = write_blink(blink, bss_env.active_dir)
        # First read records hash
        bss_env.scan("active")
        # Tamper with the file
        filepath.write_text("Tampered content", encoding="utf-8")
        assert bss_env.check_immutability(blink.blink_id) is False

    def test_no_hash_raises(self, bss_env):
        with pytest.raises(KeyError):
            bss_env.check_immutability("99999Z~~+.=#.-~..")


# ============================================================
# Relay Backlog Tests
# ============================================================


class TestRelayBacklog:
    """Relay hygiene tests."""

    def test_backlog_warning(self, bss_env):
        """Module 8.2.7: Warning when relay exceeds 10 blinks."""
        for i in range(1, 12):  # 11 blinks
            blink = _make_blink(i, relational="^" if i == 1 else "+")
            write_blink(blink, bss_env.relay_dir)

        with pytest.warns(UserWarning, match="exceeding"):
            bss_env.check_relay_backlog()

    def test_no_warning_under_threshold(self, bss_env):
        for i in range(1, 6):  # 5 blinks
            blink = _make_blink(i, relational="^" if i == 1 else "+")
            write_blink(blink, bss_env.relay_dir)

        result = bss_env.check_relay_backlog()
        assert result is False


# ============================================================
# Artifact Tests
# ============================================================


class TestArtifacts:
    """Artifact management tests."""

    def test_find_artifact(self, bss_env):
        # Create a fake artifact
        (bss_env.artifacts_dir / "00001A-test-module.py").write_text("# test")
        result = bss_env.find_artifact("00001", "A")
        assert result is not None
        assert result.name == "00001A-test-module.py"

    def test_find_artifact_not_found(self, bss_env):
        result = bss_env.find_artifact("99999", "Z")
        assert result is None

    def test_register_artifact(self, bss_env, tmp_path):
        # Create a source file
        source = tmp_path / "mycode.py"
        source.write_text("print('hello')")

        blink_id = generate(sequence=1, author="A", relational="^",
                            action_energy="~", action_valence="~",
                            confidence="!", cognitive="!",
                            domain="^", subdomain=";", scope="!",
                            maturity=",", priority="=", sensitivity=".")

        result = bss_env.register_artifact(blink_id, source, "my-code")
        assert result.exists()
        assert result.name == "00001A-my-code.py"
        assert result.read_text() == "print('hello')"


# ============================================================
# Find By Prefix Tests
# ============================================================


class TestFindByPrefix:
    """find_blink_by_prefix() tests."""

    def test_find_by_6char_prefix(self, bss_env):
        """Find a blink by sequence+author prefix."""
        blink = _make_blink(1, author="A", relational="^")
        write_blink(blink, bss_env.active_dir)
        found = bss_env.find_blink_by_prefix("00001A")
        assert found is not None
        assert found.name.startswith("00001A")

    def test_find_by_5char_prefix(self, bss_env):
        """Find a blink by sequence-only prefix."""
        blink = _make_blink(1, author="B", relational="^")
        write_blink(blink, bss_env.active_dir)
        found = bss_env.find_blink_by_prefix("00001")
        assert found is not None
        assert found.name.startswith("00001")

    def test_find_in_relay(self, bss_env):
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.relay_dir)
        found = bss_env.find_blink_by_prefix("00001")
        assert found is not None
        assert found.parent == bss_env.relay_dir

    def test_find_in_archive_recursive(self, bss_env):
        """find_blink_by_prefix searches archive subdirectories."""
        subdir = bss_env.archive_dir / "2026-Q1"
        subdir.mkdir()
        blink = _make_blink(1, relational="^")
        write_blink(blink, subdir)
        found = bss_env.find_blink_by_prefix("00001")
        assert found is not None
        assert "2026-Q1" in str(found)

    def test_prefix_not_found(self, bss_env):
        found = bss_env.find_blink_by_prefix("ZZZZZ")
        assert found is None

    def test_search_order_relay_first(self, bss_env):
        """Relay is searched before active."""
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.relay_dir)
        write_blink(blink, bss_env.active_dir)
        found = bss_env.find_blink_by_prefix("00001")
        assert found.parent == bss_env.relay_dir


# ============================================================
# List Artifacts Tests
# ============================================================


class TestListArtifacts:
    """list_artifacts() tests."""

    def test_empty_artifacts(self, bss_env):
        assert bss_env.list_artifacts() == []

    def test_lists_artifact_files(self, bss_env):
        (bss_env.artifacts_dir / "00001A-module.py").write_text("# code")
        (bss_env.artifacts_dir / "00002B-data.json").write_text("{}")
        result = bss_env.list_artifacts()
        assert len(result) == 2
        assert result[0].name == "00001A-module.py"
        assert result[1].name == "00002B-data.json"

    def test_excludes_directories(self, bss_env):
        (bss_env.artifacts_dir / "subdir").mkdir()
        (bss_env.artifacts_dir / "00001A-module.py").write_text("# code")
        result = bss_env.list_artifacts()
        assert len(result) == 1

    def test_sorted_output(self, bss_env):
        (bss_env.artifacts_dir / "00003C-last.py").write_text("")
        (bss_env.artifacts_dir / "00001A-first.py").write_text("")
        result = bss_env.list_artifacts()
        assert result[0].name == "00001A-first.py"
        assert result[1].name == "00003C-last.py"


# ============================================================
# Symlink rejection tests
# ============================================================


class TestSymlinkRejection:
    """Verify that symlinks are rejected in blink file listing."""

    def test_symlink_in_relay_ignored(self, bss_env, tmp_path):
        """Symlinks in /relay/ are not returned by scan."""
        # Write a real blink
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.relay_dir)

        # Create a symlink to a file outside BSS root
        external = tmp_path / "external_dir" / "fake.md"
        external.parent.mkdir()
        external.write_text("Born from: Origin\n\nFake blink.\n\nLineage: FAKE\n")
        symlink = bss_env.relay_dir / "SYMLINKED_FAKE__.md"
        try:
            symlink.symlink_to(external)
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        files = bss_env._list_blink_files(bss_env.relay_dir)
        # Only the real blink should be returned
        assert len(files) == 1
        assert files[0].name == f"{blink.blink_id}.md"

    def test_symlink_in_archive_ignored(self, bss_env, tmp_path):
        """Symlinks in /archive/ are not returned by recursive listing."""
        external = tmp_path / "outside.md"
        external.write_text("dangerous")
        symlink = bss_env.archive_dir / "evil.md"
        try:
            symlink.symlink_to(external)
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        files = bss_env._list_blink_files_recursive(bss_env.archive_dir)
        assert len(files) == 0


class TestRecursiveDepthLimit:
    """_list_blink_files_recursive respects depth limits."""

    def test_deeply_nested_files_excluded(self, bss_env):
        """Files beyond max_depth are not returned."""
        deep = bss_env.archive_dir / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "deep.md").write_text(
            "Born from: Origin\n\nDeep file. Very deep.\n\nLineage: X\n",
            encoding="utf-8",
        )
        files = bss_env._list_blink_files_recursive(
            bss_env.archive_dir, max_depth=3
        )
        assert len(files) == 0

    def test_within_depth_files_included(self, bss_env):
        """Files within max_depth are returned."""
        shallow = bss_env.archive_dir / "2026-Q1"
        shallow.mkdir()
        blink = _make_blink(99, relational="^")
        write_blink(blink, shallow)
        files = bss_env._list_blink_files_recursive(
            bss_env.archive_dir, max_depth=3
        )
        assert len(files) == 1


# ============================================================
# Sequence Locking Tests
# ============================================================


class TestSequenceLocking:
    """File-based locking for next_sequence()."""

    def test_lock_file_created(self, bss_env):
        """next_sequence() creates a .bss.lock file."""
        bss_env.next_sequence()
        assert (bss_env.root / ".bss.lock").exists()

    def test_sequential_calls_increment(self, bss_env):
        """Two sequential next_sequence() calls return consecutive values."""
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.active_dir)

        seq1 = bss_env.next_sequence()
        # Write a blink with seq1 so next call sees it
        b2 = _make_blink(2)
        write_blink(b2, bss_env.active_dir)

        seq2 = bss_env.next_sequence()
        assert seq1 != seq2


# ============================================================
# Register Artifact TOCTOU Tests
# ============================================================


class TestRegisterArtifactTOCTOU:
    """Atomic artifact registration prevents TOCTOU races."""

    def test_symlink_at_dest_rejected(self, bss_env, tmp_path):
        """register_artifact rejects symlinks at destination."""
        source = tmp_path / "code.py"
        source.write_text("print('hello')")

        blink_id = generate(sequence=1, author="A", relational="^",
                            action_energy="~", action_valence="~",
                            confidence="!", cognitive="!",
                            domain="^", subdomain=";", scope="!",
                            maturity=",", priority="=", sensitivity=".")

        # Create a symlink at the artifact destination
        dest = bss_env.artifacts_dir / "00001A-evil.py"
        target = tmp_path / "target.py"
        target.write_text("malicious")
        try:
            dest.symlink_to(target)
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        with pytest.raises(ValueError):
            bss_env.register_artifact(blink_id, source, "evil")

    def test_duplicate_artifact_rejected(self, bss_env, tmp_path):
        """register_artifact rejects overwrite of existing artifact."""
        source = tmp_path / "code.py"
        source.write_text("print('hello')")

        blink_id = generate(sequence=1, author="A", relational="^",
                            action_energy="~", action_valence="~",
                            confidence="!", cognitive="!",
                            domain="^", subdomain=";", scope="!",
                            maturity=",", priority="=", sensitivity=".")

        # First registration succeeds
        bss_env.register_artifact(blink_id, source, "module")

        # Second registration with same slug fails
        with pytest.raises(ValueError, match="already exists"):
            bss_env.register_artifact(blink_id, source, "module")


# ============================================================
# Persistent Manifest Tests
# ============================================================


class TestPersistentManifest:
    """Integrity manifest persists across BSSEnvironment instances."""

    def test_manifest_created_on_scan(self, bss_env):
        """Scanning creates .bss_manifest.json."""
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.active_dir)
        bss_env.scan("active")
        assert (bss_env.root / ".bss_manifest.json").exists()

    def test_manifest_survives_new_instance(self, bss_env):
        """A new BSSEnvironment reads hashes from manifest."""
        blink = _make_blink(1, relational="^")
        write_blink(blink, bss_env.active_dir)
        bss_env.scan("active")

        # Create a fresh environment instance (simulates new session)
        env2 = BSSEnvironment(bss_env.root)
        # Should pass immutability check via manifest, no KeyError
        assert env2.check_immutability(blink.blink_id) is True

    def test_tampering_detected_across_sessions(self, bss_env):
        """Tampering detected even with a new BSSEnvironment instance."""
        blink = _make_blink(1, relational="^")
        filepath = write_blink(blink, bss_env.active_dir)
        bss_env.scan("active")

        # Tamper with the file
        filepath.write_text("Tampered!", encoding="utf-8")

        # New instance detects tampering via manifest
        env2 = BSSEnvironment(bss_env.root)
        assert env2.check_immutability(blink.blink_id) is False
