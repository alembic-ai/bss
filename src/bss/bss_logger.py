"""BSS structured logging — configures audit file + console handlers."""

from __future__ import annotations

import logging
import os
from pathlib import Path

_LOG_ENV_VAR = "BSS_LOG_PATH"
_DEFAULT_LOG_FILENAME = "audit.log"

_configured = False


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced BSS logger.

    Args:
        name: Optional sub-namespace (e.g. "environment" → "bss.environment").

    Returns:
        A logging.Logger instance.
    """
    return logging.getLogger(f"bss.{name}" if name else "bss")


def configure(
    log_dir: Path | None = None,
    console_level: int = logging.WARNING,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure BSS logging with file + console handlers.

    Idempotent — safe to call multiple times; only configures once.

    Args:
        log_dir: Directory for audit.log. Reads BSS_LOG_PATH env var first,
                 then falls back to log_dir, then <cwd>/.bss/.
        console_level: Minimum level for stderr output (default WARNING).
        file_level: Minimum level for file output (default DEBUG).
    """
    global _configured
    if _configured:
        return

    root = logging.getLogger("bss")
    root.setLevel(logging.DEBUG)

    # Resolve log directory
    env_path = os.environ.get(_LOG_ENV_VAR, "")
    if env_path:
        resolved_dir = Path(env_path)
    elif log_dir:
        resolved_dir = log_dir
    else:
        resolved_dir = Path.cwd() / ".bss"

    # File handler
    try:
        resolved_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(
            resolved_dir / _DEFAULT_LOG_FILENAME,
            encoding="utf-8",
        )
        fh.setLevel(file_level)
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        root.addHandler(fh)
    except OSError:
        pass  # Can't write log dir — fall through to console-only

    # Console handler (WARNING+ — no noise in CLI output)
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(ch)

    _configured = True
