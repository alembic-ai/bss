"""Tests for BSS structured logging module."""

import logging
from pathlib import Path

import pytest

import src.bss.bss_logger as bss_logger
from src.bss.bss_logger import get_logger, configure


@pytest.fixture(autouse=True)
def reset_logger(monkeypatch):
    """Reset logging state between tests."""
    monkeypatch.setattr(bss_logger, "_configured", False)
    root = logging.getLogger("bss")
    root.handlers.clear()
    root.setLevel(logging.WARNING)
    yield
    root.handlers.clear()


class TestGetLogger:
    def test_returns_bss_namespace(self):
        logger = get_logger("environment")
        assert logger.name == "bss.environment"

    def test_no_name_returns_root(self):
        logger = get_logger()
        assert logger.name == "bss"

    def test_none_returns_root(self):
        logger = get_logger(None)
        assert logger.name == "bss"

    def test_child_inherits_handlers(self, tmp_path):
        configure(log_dir=tmp_path)
        child = get_logger("relay")
        assert child.parent.name == "bss"


class TestConfigure:
    def test_creates_audit_log(self, tmp_path):
        configure(log_dir=tmp_path)
        assert (tmp_path / "audit.log").exists()

    def test_idempotent(self, tmp_path):
        configure(log_dir=tmp_path)
        root = logging.getLogger("bss")
        handler_count = len(root.handlers)
        configure(log_dir=tmp_path)
        assert len(root.handlers) == handler_count

    def test_respects_env_var(self, tmp_path, monkeypatch):
        env_dir = tmp_path / "custom_log"
        monkeypatch.setenv("BSS_LOG_PATH", str(env_dir))
        configure(log_dir=tmp_path / "ignored")
        assert (env_dir / "audit.log").exists()
        assert not (tmp_path / "ignored" / "audit.log").exists()

    def test_falls_through_on_bad_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("BSS_LOG_PATH", "/nonexistent/readonly/path")
        # Should not raise
        configure()

    def test_file_handler_captures_debug(self, tmp_path):
        configure(log_dir=tmp_path)
        logger = get_logger("test")
        logger.debug("debug message for test")
        # Flush handlers
        for h in logging.getLogger("bss").handlers:
            h.flush()
        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "debug message for test" in content

    def test_console_handler_level_warning(self, tmp_path):
        configure(log_dir=tmp_path)
        root = logging.getLogger("bss")
        console_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) == 1
        assert console_handlers[0].level == logging.WARNING

    def test_audit_log_format(self, tmp_path):
        configure(log_dir=tmp_path)
        logger = get_logger("test")
        logger.warning("format check")
        for h in logging.getLogger("bss").handlers:
            h.flush()
        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        # Format: timestamp  LEVEL     bss.name  message
        assert "WARNING" in content
        assert "bss.test" in content
        assert "format check" in content

    def test_default_log_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("BSS_LOG_PATH", raising=False)
        configure()
        assert (tmp_path / ".bss" / "audit.log").exists()
