"""Tests for BSS artifact CLI — find_blink_by_prefix, produce, artifact detail."""

import pytest
from pathlib import Path

from bss.environment import BSSEnvironment
from bss.blink_file import BlinkFile, write as write_blink, read as read_blink
from bss.identifier import generate


@pytest.fixture
def env(tmp_path) -> BSSEnvironment:
    return BSSEnvironment.init(tmp_path)


def _make_blink(sequence: int, author: str = "A", **kwargs) -> BlinkFile:
    """Helper to create a valid blink."""
    defaults = dict(
        action_energy="~", action_valence=".",
        relational="^", confidence="!", cognitive="=",
        domain="#", subdomain="!", scope="-",
        maturity="~", priority="=", sensitivity=".",
    )
    defaults.update(kwargs)
    blink_id = generate(sequence=sequence, author=author, **defaults)
    return BlinkFile(
        blink_id=blink_id,
        born_from=["Origin"],
        summary="Test blink for artifact integration. Created during testing phase.",
        lineage=[blink_id],
        links=[],
    )


# ============================================================
# find_blink_by_prefix integration with artifacts
# ============================================================


class TestArtifactBlinkResolution:
    """Test that artifacts can resolve their parent blinks."""

    def test_artifact_resolves_parent(self, env):
        """Artifact filename prefix maps to parent blink."""
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)

        # Create artifact with matching prefix
        artifact_name = f"00001A-test-module.py"
        (env.artifacts_dir / artifact_name).write_text("# test")

        # Extract prefix and find parent
        prefix = artifact_name[:6]
        parent = env.find_blink_by_prefix(prefix)
        assert parent is not None
        parent_blink = read_blink(parent)
        assert parent_blink.blink_id == blink.blink_id

    def test_artifact_with_different_author(self, env):
        """Artifact from author B resolves correctly."""
        blink = _make_blink(5, author="B")
        write_blink(blink, env.active_dir)

        (env.artifacts_dir / "00005B-parser.py").write_text("# parser")

        parent = env.find_blink_by_prefix("00005B")
        assert parent is not None
        parent_blink = read_blink(parent)
        assert parent_blink.blink_id[5] == "B"

    def test_artifact_parent_not_found(self, env):
        """Graceful handling when artifact's parent blink doesn't exist."""
        (env.artifacts_dir / "ZZZZZX-orphan.py").write_text("# orphan")
        parent = env.find_blink_by_prefix("ZZZZZX")
        assert parent is None


# ============================================================
# _derive_slug Tests
# ============================================================


class TestDeriveSlug:
    """Test the slug derivation helper."""

    def test_simple_filename(self):
        from cli.main import _derive_slug
        assert _derive_slug("my_module.py") == "my-module"

    def test_spaces_and_caps(self):
        from cli.main import _derive_slug
        assert _derive_slug("My Module.py") == "my-module"

    def test_multiple_dots(self):
        from cli.main import _derive_slug
        assert _derive_slug("test.spec.js") == "test-spec"

    def test_already_slugified(self):
        from cli.main import _derive_slug
        assert _derive_slug("already-slug.md") == "already-slug"

    def test_underscores(self):
        from cli.main import _derive_slug
        assert _derive_slug("my_cool_file.txt") == "my-cool-file"


# ============================================================
# Produce flow (unit-level tests)
# ============================================================


class TestProduceArtifact:
    """Test artifact registration via register_artifact()."""

    def test_register_with_slug(self, env, tmp_path):
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)

        source = tmp_path / "output.py"
        source.write_text("print('hello')")

        result = env.register_artifact(blink.blink_id, source, "output-module")
        assert result.exists()
        assert result.name == "00001A-output-module.py"

    def test_register_preserves_content(self, env, tmp_path):
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)

        source = tmp_path / "data.json"
        source.write_text('{"key": "value"}')

        result = env.register_artifact(blink.blink_id, source, "data")
        assert result.read_text() == '{"key": "value"}'

    def test_register_preserves_extension(self, env, tmp_path):
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)

        source = tmp_path / "report.csv"
        source.write_text("a,b,c")

        result = env.register_artifact(blink.blink_id, source, "report")
        assert result.suffix == ".csv"

    def test_multiple_artifacts_same_blink(self, env, tmp_path):
        """Multiple artifacts can reference the same blink prefix."""
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)

        f1 = tmp_path / "a.py"
        f1.write_text("a")
        f2 = tmp_path / "b.py"
        f2.write_text("b")

        r1 = env.register_artifact(blink.blink_id, f1, "module-a")
        r2 = env.register_artifact(blink.blink_id, f2, "module-b")

        artifacts = env.list_artifacts()
        assert len(artifacts) == 2


# ============================================================
# Artifact detail (find by sequence)
# ============================================================


class TestArtifactDetail:
    """Test artifact lookup by sequence prefix."""

    def test_find_by_5char_sequence(self, env):
        (env.artifacts_dir / "00001A-module.py").write_text("# code")
        artifacts = env.list_artifacts()
        matches = [a for a in artifacts if a.name[:5] == "00001"]
        assert len(matches) == 1

    def test_find_by_6char_prefix(self, env):
        (env.artifacts_dir / "00001A-module.py").write_text("# code")
        (env.artifacts_dir / "00001B-other.py").write_text("# other")
        artifacts = env.list_artifacts()
        matches = [a for a in artifacts if a.name.startswith("00001A-")]
        assert len(matches) == 1
        assert matches[0].name == "00001A-module.py"

    def test_no_match(self, env):
        artifacts = env.list_artifacts()
        matches = [a for a in artifacts if a.name[:5] == "ZZZZZ"]
        assert len(matches) == 0


# ============================================================
# Artifact slug sanitization (security)
# ============================================================


class TestArtifactSlugSanitization:
    """Verify that malicious slugs are rejected."""

    def test_path_traversal_rejected(self, env, tmp_path):
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)
        source = tmp_path / "evil.py"
        source.write_text("# evil")

        with pytest.raises(ValueError, match="Invalid artifact slug"):
            env.register_artifact(blink.blink_id, source, "../../../etc/passwd")

    def test_slash_in_slug_rejected(self, env, tmp_path):
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)
        source = tmp_path / "evil.py"
        source.write_text("# evil")

        with pytest.raises(ValueError, match="Invalid artifact slug"):
            env.register_artifact(blink.blink_id, source, "foo/bar")

    def test_dot_dot_rejected(self, env, tmp_path):
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)
        source = tmp_path / "evil.py"
        source.write_text("# evil")

        with pytest.raises(ValueError, match="Invalid artifact slug"):
            env.register_artifact(blink.blink_id, source, "..")

    def test_empty_slug_rejected(self, env, tmp_path):
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)
        source = tmp_path / "evil.py"
        source.write_text("# evil")

        with pytest.raises(ValueError, match="Invalid artifact slug"):
            env.register_artifact(blink.blink_id, source, "")

    def test_valid_slug_accepted(self, env, tmp_path):
        blink = _make_blink(1)
        write_blink(blink, env.active_dir)
        source = tmp_path / "good.py"
        source.write_text("# good")

        result = env.register_artifact(blink.blink_id, source, "my-valid-slug-v2")
        assert result.exists()
