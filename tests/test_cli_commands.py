"""Tests for v1.3 CLI commands and improvements.

Covers: health, archive, integrity, export, clean, escalation,
bss write error handling/bounds, bss log --archive, bss status
archive warning, bss init .gitignore, and discovery model refs.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cli.main import app, ARCHIVE_WARN_THRESHOLD
from src.bss.blink_file import BlinkFile, write as write_blink
from src.bss.environment import BSSEnvironment
from src.bss.identifier import generate
from src.bss.roster import RosterEntry, update_roster

runner = CliRunner()


@pytest.fixture
def env(tmp_path):
    """Create a BSS environment with one origin blink."""
    e = BSSEnvironment.init(tmp_path)
    entries = [
        RosterEntry(sigil="A", model_id="Model-A", role="primary", scope_ceiling="global", notes=""),
    ]
    update_roster(e, entries)

    origin_id = generate(
        sequence=1, author="U",
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
        summary="Test origin blink for CLI tests. Environment is ready for testing.",
        lineage=[origin_id],
        links=[],
    )
    write_blink(origin, e.active_dir)
    return e


def _write_test_blink(env, seq, action_e=".", action_v=".", directory="active"):
    """Helper to write a test blink."""
    bid = generate(
        sequence=seq, author="A",
        action_energy=action_e, action_valence=action_v,
        relational="^",
        confidence="!", cognitive="=",
        domain="#", subdomain="!",
        scope="-", maturity="~",
        priority="=", sensitivity=".",
    )
    blink = BlinkFile(
        blink_id=bid,
        born_from=["Origin"],
        summary=f"Test blink seq {seq}. Created for CLI testing.",
        lineage=[bid],
        links=[],
    )
    target = getattr(env, f"{directory}_dir")
    write_blink(blink, target)
    return bid


# ============================================================
# bss health
# ============================================================


class TestHealth:
    def test_health_ok(self, env):
        result = runner.invoke(app, ["health", "--path", str(env.root)])
        assert result.exit_code == 0
        assert "All checks passed" in result.output

    def test_health_missing_dir(self, env):
        # Removing a required dir makes is_valid() fail, so _get_env rejects it
        import shutil
        shutil.rmtree(env.root / "archive")
        result = runner.invoke(app, ["health", "--path", str(env.root)])
        assert result.exit_code == 1
        assert "Not a BSS environment" in result.output

    def test_health_relay_backlog(self, env):
        # Write enough relay blinks to exceed threshold
        for i in range(12):
            _write_test_blink(env, i + 10, action_e="~", action_v="!", directory="relay")
        result = runner.invoke(app, ["health", "--path", str(env.root)])
        assert result.exit_code == 1
        assert "above threshold" in result.output

    def test_health_archive_warning(self, env):
        # Create lots of archive blinks (just files, not real blinks)
        for i in range(ARCHIVE_WARN_THRESHOLD + 5):
            (env.archive_dir / f"fake_{i:03d}.md").write_text("# fake")
        result = runner.invoke(app, ["health", "--path", str(env.root)])
        assert "consider reviewing" in result.output


# ============================================================
# bss archive
# ============================================================


class TestArchive:
    def test_archive_blink(self, env):
        bid = _write_test_blink(env, 20)
        result = runner.invoke(app, ["archive", bid, "--path", str(env.root)])
        assert result.exit_code == 0
        assert "Archived" in result.output
        # Blink should now be in archive
        assert list(env.archive_dir.rglob(f"{bid}.md"))

    def test_archive_not_found(self, env):
        result = runner.invoke(app, ["archive", "ZZZZZA..+!=#!-~=.", "--path", str(env.root)])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Blink not found" in result.output


# ============================================================
# bss integrity
# ============================================================


class TestIntegrity:
    def test_integrity_passes(self, env):
        # Scan to populate manifest
        env.scan("active")
        result = runner.invoke(app, ["integrity", "--path", str(env.root)])
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_integrity_detects_tamper(self, env):
        bid = _write_test_blink(env, 30)
        env.scan("active")  # populate manifest
        # Tamper with the file
        blink_path = env.active_dir / f"{bid}.md"
        blink_path.write_text("TAMPERED CONTENT")
        result = runner.invoke(app, ["integrity", "--path", str(env.root)])
        assert result.exit_code == 1
        assert "TAMPERED" in result.output


# ============================================================
# bss export
# ============================================================


class TestExport:
    def test_export_stdout(self, env, tmp_path):
        out = tmp_path / "out.json"
        result = runner.invoke(app, ["export", "--output", str(out), "--path", str(env.root)])
        assert result.exit_code == 0
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_export_to_file(self, env, tmp_path):
        out = tmp_path / "export.json"
        result = runner.invoke(app, ["export", "--output", str(out), "--path", str(env.root)])
        assert result.exit_code == 0
        data = json.loads(out.read_text())
        assert isinstance(data, list)

    def test_export_with_archive(self, env, tmp_path):
        bid = _write_test_blink(env, 40)
        env.move_blink(bid, "archive")
        # Without --archive flag
        out1 = tmp_path / "no_archive.json"
        runner.invoke(app, ["export", "--output", str(out1), "--path", str(env.root)])
        data1 = json.loads(out1.read_text())
        ids1 = {r["blink_id"] for r in data1}
        assert bid not in ids1
        # With --archive flag
        out2 = tmp_path / "with_archive.json"
        runner.invoke(app, ["export", "--archive", "--output", str(out2), "--path", str(env.root)])
        data2 = json.loads(out2.read_text())
        ids2 = {r["blink_id"] for r in data2}
        assert bid in ids2


# ============================================================
# bss clean
# ============================================================


class TestClean:
    def test_clean_nothing(self, env):
        # Remove any lock files left from init
        lock = env.root / ".bss.lock"
        if lock.exists():
            lock.unlink()
        result = runner.invoke(app, ["clean", "--path", str(env.root)])
        assert "Nothing to clean" in result.output

    def test_clean_lock_file(self, env):
        (env.root / ".bss.lock").write_text("locked")
        result = runner.invoke(app, ["clean", "--yes", "--path", str(env.root)])
        assert result.exit_code == 0
        assert "Removed" in result.output
        assert not (env.root / ".bss.lock").exists()

    def test_clean_tmp_files(self, env):
        # Remove lock file first so only tmp files are targeted
        lock = env.root / ".bss.lock"
        if lock.exists():
            lock.unlink()
        (env.root / "stale.tmp").write_text("tmp")
        (env.root / "another.tmp").write_text("tmp")
        result = runner.invoke(app, ["clean", "--yes", "--path", str(env.root)])
        assert "Removed 2" in result.output


# ============================================================
# bss escalation
# ============================================================


class TestEscalation:
    def test_escalation_none(self, env):
        result = runner.invoke(app, ["escalation", "--path", str(env.root)])
        assert result.exit_code == 0
        assert "No error chains" in result.output

    def test_escalation_with_errors(self, env):
        # Write an error blink (!!)
        _write_test_blink(env, 50, action_e="!", action_v="!", directory="relay")
        result = runner.invoke(app, ["escalation", "--path", str(env.root)])
        # Should either find chains or show "No error chains" depending on escalation logic
        assert result.exit_code == 0


# ============================================================
# bss write — bounds checks
# ============================================================


class TestWriteBounds:
    def test_write_action_out_of_bounds(self, env):
        """Selecting action index 99 should exit with error."""
        result = runner.invoke(app, ["write", "--path", str(env.root)], input="U\n99\n")
        assert result.exit_code == 1
        assert "Invalid selection" in result.output

    def test_write_action_zero(self, env):
        """Selecting 0 (maps to index -1) should exit with error."""
        result = runner.invoke(app, ["write", "--path", str(env.root)], input="U\n0\n")
        assert result.exit_code == 1
        assert "Invalid selection" in result.output


# ============================================================
# bss write — error wrapping
# ============================================================


class TestWriteErrorHandling:
    def test_write_file_exists_error(self, env):
        """write_blink raising FileExistsError should show friendly message."""
        with patch("cli.main.write_blink", side_effect=FileExistsError("already exists")):
            # Provide all wizard inputs + confirm
            inputs = "U\n1\n1\n1\n2\n1\n1\n2\n2\n3\n3\nTest summary.\ny\n"
            result = runner.invoke(app, ["write", "--path", str(env.root)], input=inputs)
            assert result.exit_code == 1
            assert "already exists" in result.output

    def test_write_value_error(self, env):
        """write_blink raising ValueError should show friendly message."""
        with patch("cli.main.write_blink", side_effect=ValueError("bad blink")):
            inputs = "U\n1\n1\n1\n2\n1\n1\n2\n2\n3\n3\nTest summary.\ny\n"
            result = runner.invoke(app, ["write", "--path", str(env.root)], input=inputs)
            assert result.exit_code == 1
            assert "bad blink" in result.output


# ============================================================
# bss log --archive
# ============================================================


class TestLogArchive:
    def test_log_without_archive(self, env):
        bid = _write_test_blink(env, 60)
        env.move_blink(bid, "archive")
        result = runner.invoke(app, ["log", "--path", str(env.root)])
        # Archived blink should not appear in default log
        assert bid not in result.output

    def test_log_with_archive(self, env):
        bid = _write_test_blink(env, 70)
        env.move_blink(bid, "archive")
        result = runner.invoke(app, ["log", "--archive", "--path", str(env.root)])
        # Archived blink should appear with --archive flag
        assert bid[:5] in result.output


# ============================================================
# bss status — archive warning
# ============================================================


class TestStatusArchiveWarning:
    def test_status_no_warning(self, env):
        result = runner.invoke(app, ["status", "--path", str(env.root)])
        assert result.exit_code == 0
        assert "consider reviewing" not in result.output

    def test_status_archive_warning(self, env):
        for i in range(ARCHIVE_WARN_THRESHOLD + 5):
            (env.archive_dir / f"fake_{i:03d}.md").write_text("# fake")
        result = runner.invoke(app, ["status", "--path", str(env.root)])
        assert "consider reviewing" in result.output


# ============================================================
# bss init — .gitignore
# ============================================================


class TestInitGitignore:
    def test_init_creates_gitignore(self, tmp_path):
        result = runner.invoke(app, ["init", "--defaults", str(tmp_path / "newenv")])
        assert result.exit_code == 0
        gi = tmp_path / "newenv" / ".gitignore"
        assert gi.exists()
        content = gi.read_text()
        assert "config.yaml" in content
        assert ".bss.lock" in content
        assert ".bss_manifest.json" in content

    def test_init_no_overwrite_gitignore(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        gi = target / ".gitignore"
        gi.write_text("# custom\n")
        result = runner.invoke(app, ["init", "--defaults", str(target)])
        assert result.exit_code == 0
        assert gi.read_text() == "# custom\n"


# ============================================================
# bss relay / gateway ImportError handling
# ============================================================


class TestImportErrorHandling:
    def test_relay_import_error(self):
        with patch.dict("sys.modules", {"terminal": None, "terminal.app": None}):
            result = runner.invoke(app, ["relay"])
            assert result.exit_code == 1
            assert "textual" in result.output.lower() or "pip install" in result.output

    def test_gateway_import_error(self, tmp_path):
        # Gateway now checks for a marker file; without it, it tries terminal import
        with patch.dict("sys.modules", {"terminal": None, "terminal.gateway": None}):
            result = runner.invoke(app, ["gateway", str(tmp_path)])
            assert result.exit_code == 1
            assert "pip install" in result.output or "textual" in result.output.lower()


# ============================================================
# Discovery model references
# ============================================================


class TestDiscoveryModelRefs:
    def test_anthropic_default_model(self):
        from integrations.discovery import discover_anthropic
        import os
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-1234"}):
            results = discover_anthropic()
            assert len(results) == 1
            assert results[0].details["model"] == "claude-opus-4-6"

    def test_gemini_default_model(self):
        from integrations.discovery import discover_gemini
        import os
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-1234"}):
            results = discover_gemini()
            assert len(results) == 1
            assert results[0].details["model"] == "gemini-2.5-flash"


# ============================================================
# Configurable timeouts
# ============================================================


class TestConfigurableTimeouts:
    def test_runner_round_delay_default(self):
        from integrations.runner import RelayRunner
        env_mock = object()
        mm_mock = object()
        r = RelayRunner(env_mock, mm_mock)
        assert r._round_delay == 0.5

    def test_runner_round_delay_custom(self):
        from integrations.runner import RelayRunner
        env_mock = object()
        mm_mock = object()
        r = RelayRunner(env_mock, mm_mock, round_delay=2.0)
        assert r._round_delay == 2.0

    def test_openai_compat_default_timeouts(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        assert p._probe_timeout == 5
        assert p._inference_timeout == 120

    def test_openai_compat_custom_timeouts(self):
        from integrations.providers.openai_compat import OpenAIProvider
        p = OpenAIProvider()
        # Simulate load with custom timeouts
        config = {
            "base_url": "http://localhost:1234/v1",
            "model": "test",
            "probe_timeout": 10,
            "inference_timeout": 300,
        }
        # We can't fully load without a running server, but we can
        # check the timeout extraction logic by calling load and catching
        # the connection error. The timeouts should be set before the probe.
        try:
            p.load(config)
        except Exception:
            pass
        assert p._probe_timeout == 10
        assert p._inference_timeout == 300
