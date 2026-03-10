"""BSS environment manager — wraps a BSS directory structure."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import warnings
from pathlib import Path

from src.bss.blink_file import BlinkFile, read as read_blink
from src.bss.identifier import (
    base36_decode,
    next_sequence,
    parse as parse_id,
    validate as validate_id,
)

REQUIRED_DIRS = ["relay", "active", "profile", "archive"]
OPTIONAL_DIRS = ["artifacts"]
RELAY_WARN_THRESHOLD = 10


class BSSEnvironment:
    """Wraps a BSS directory structure and provides environment operations."""

    def __init__(self, root: Path):
        self.root = root
        self._integrity_hashes: dict[str, str] = {}

    @property
    def relay_dir(self) -> Path:
        return self.root / "relay"

    @property
    def active_dir(self) -> Path:
        return self.root / "active"

    @property
    def profile_dir(self) -> Path:
        return self.root / "profile"

    @property
    def archive_dir(self) -> Path:
        return self.root / "archive"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    @staticmethod
    def init(root: Path) -> "BSSEnvironment":
        """Create a new BSS environment with required directories.

        Args:
            root: The root directory for the BSS environment.

        Returns:
            A BSSEnvironment wrapping the created structure.
        """
        root.mkdir(parents=True, exist_ok=True)
        for dirname in REQUIRED_DIRS:
            (root / dirname).mkdir(exist_ok=True)
        for dirname in OPTIONAL_DIRS:
            (root / dirname).mkdir(exist_ok=True)
        return BSSEnvironment(root)

    def is_valid(self) -> bool:
        """Check if this root contains all required BSS directories."""
        return all((self.root / d).is_dir() for d in REQUIRED_DIRS)

    def _is_within_root(self, path: Path) -> bool:
        """Check that a resolved path stays within the BSS root."""
        try:
            return path.resolve().is_relative_to(self.root.resolve())
        except (OSError, ValueError):
            return False

    def _list_blink_files(self, directory: Path) -> list[Path]:
        """List all .md blink files in a directory.

        Rejects symlinks and paths that resolve outside the BSS root.
        """
        if not directory.exists():
            return []
        return sorted(
            f for f in directory.glob("*.md")
            if not f.is_symlink() and self._is_within_root(f)
        )

    def _list_blink_files_recursive(
        self, directory: Path, max_depth: int = 3
    ) -> list[Path]:
        """List all .md blink files in a directory and subdirectories.

        Rejects symlinks and paths that resolve outside the BSS root.
        Limits recursion to max_depth levels to prevent DoS via deep nesting.
        """
        if not directory.exists():
            return []

        results: list[Path] = []

        def _walk(current: Path, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                entries = sorted(current.iterdir())
            except PermissionError:
                return
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    _walk(entry, depth + 1)
                elif entry.is_file() and entry.suffix == ".md":
                    if self._is_within_root(entry):
                        results.append(entry)

        _walk(directory, 0)
        return sorted(results)

    def scan(self, directory: str) -> list[BlinkFile]:
        """List and parse all blinks in a directory.

        Args:
            directory: One of 'relay', 'active', 'profile', 'archive'.

        Returns:
            List of parsed BlinkFile objects.
        """
        dir_path = self.root / directory
        files = self._list_blink_files(dir_path)
        blinks = []
        for f in files:
            try:
                blink = read_blink(f)
                blinks.append(blink)
                # Store integrity hash on first read
                self._record_integrity(blink.blink_id, f)
            except Exception as exc:
                logging.getLogger("bss.environment").warning(
                    "Skipping unparseable blink file '%s': %s", f, exc,
                )
        return blinks

    def triage(self, directory: str) -> list[BlinkFile]:
        """Return blinks sorted by triage order.

        Triage order (per Module 5.2):
        1. Urgency — higher priority and time sensitivity first
        2. Recency — later sequence numbers first
        3. Scope — broader scope first

        Args:
            directory: Directory name to triage.

        Returns:
            List of BlinkFile sorted by triage order.
        """
        blinks = self.scan(directory)
        return sort_by_triage(blinks)

    def highest_sequence(self) -> str:
        """Scan all directories for the current highest sequence number.

        Returns:
            The highest 5-char base-36 sequence found, or "00000" if empty.
        """
        highest = "00000"
        highest_val = 0

        for dirname in REQUIRED_DIRS:
            dir_path = self.root / dirname
            files = self._list_blink_files_recursive(dir_path)
            for f in files:
                name = f.name
                blink_id = name[:-3] if name.endswith(".md") else name
                if len(blink_id) >= 5:
                    seq = blink_id[:5]
                    try:
                        val = base36_decode(seq)
                        if val > highest_val:
                            highest_val = val
                            highest = seq
                    except ValueError:
                        continue

        return highest

    def peek_next_sequence(self) -> str:
        """Preview the next sequence number without consuming it.

        Unlike next_sequence(), this does not acquire a lock or increment
        any counter. Safe for read-only operations like config generation.

        Returns:
            The next 5-char base-36 sequence (read-only).
        """
        current = self.highest_sequence()
        if current == "00000":
            return "00001"
        return next_sequence(current)

    def _lock_path(self) -> Path:
        """Path to the environment lock file."""
        return self.root / ".bss.lock"

    def next_sequence(self) -> str:
        """Get the next available sequence number.

        Uses file-based locking to prevent race conditions when multiple
        processes access the same BSS environment.

        Returns:
            The next 5-char base-36 sequence.
        """
        lock_path = self._lock_path()
        lock_path.touch(exist_ok=True)

        lock_fd = open(lock_path, "r+")
        try:
            # Acquire platform-appropriate file lock
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(lock_fd.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)

            # Critical section: read highest and increment
            current = self.highest_sequence()
            if current == "00000":
                return "00001"
            return next_sequence(current)
        finally:
            # Release lock
            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()

    def find_blink(self, blink_id: str) -> Path | None:
        """Search all directories for a blink by ID.

        Searches relay, active, profile, then archive (including subdirectories).

        Args:
            blink_id: The blink identifier to find.

        Returns:
            Path to the blink file, or None if not found.
        """
        filename = f"{blink_id}.md"

        # Search in order: relay, active, profile
        for dirname in ["relay", "active", "profile"]:
            path = self.root / dirname / filename
            if path.exists() and not path.is_symlink() and self._is_within_root(path):
                return path

        # Search archive recursively (including subdirectories)
        archive_path = self.archive_dir
        if archive_path.exists():
            matches = [
                m for m in archive_path.rglob(filename)
                if not m.is_symlink() and self._is_within_root(m)
            ]
            if matches:
                return matches[0]

        return None

    def find_blink_by_prefix(self, prefix: str) -> Path | None:
        """Search all directories for a blink whose filename starts with prefix.

        Searches relay → active → profile → archive (recursive) using glob.

        Args:
            prefix: The prefix to match (e.g. "00001A" for 6-char or "00001" for 5-char).

        Returns:
            Path to the first matching blink file, or None if not found.
        """
        pattern = f"{prefix}*.md"

        # Search in order: relay, active, profile
        for dirname in ["relay", "active", "profile"]:
            dir_path = self.root / dirname
            if dir_path.exists():
                matches = sorted(
                    f for f in dir_path.glob(pattern)
                    if not f.is_symlink() and self._is_within_root(f)
                )
                if matches:
                    return matches[0]

        # Search archive recursively
        if self.archive_dir.exists():
            matches = sorted(
                f for f in self.archive_dir.rglob(pattern)
                if not f.is_symlink() and self._is_within_root(f)
            )
            if matches:
                return matches[0]

        return None

    # Directories allowed as move targets
    ALLOWED_MOVE_DIRS = frozenset(REQUIRED_DIRS + OPTIONAL_DIRS)

    def move_blink(self, blink_id: str, to_directory: str) -> Path:
        """Move a blink between directories.

        Enforces immutability: filename and content are unchanged.

        Args:
            blink_id: The blink identifier to move.
            to_directory: Target directory name (must be a known BSS directory).

        Returns:
            New path of the moved blink.

        Raises:
            FileNotFoundError: If the blink doesn't exist.
            ValueError: If to_directory is invalid or immutability check fails.
        """
        # Validate: must be a known BSS directory or subdirectory thereof
        base_dir = to_directory.split("/")[0]
        if base_dir not in self.ALLOWED_MOVE_DIRS:
            raise ValueError(
                f"Invalid target directory '{to_directory}'. "
                f"Must be within: {', '.join(sorted(self.ALLOWED_MOVE_DIRS))}"
            )
        # Reject path traversal attempts
        if ".." in to_directory:
            raise ValueError("Directory path must not contain '..'")

        source = self.find_blink(blink_id)
        if source is None:
            raise FileNotFoundError(f"Blink '{blink_id}' not found")

        # Read content before move for integrity check
        content_before = source.read_bytes()

        dest_dir = self.root / to_directory
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name

        # Verify destination stays within root
        if not self._is_within_root(dest):
            raise ValueError("Target path escapes BSS root")

        # Move the file
        source.rename(dest)

        # Verify content unchanged
        content_after = dest.read_bytes()
        if content_before != content_after:
            raise ValueError(
                f"Immutability violation: content changed during move of '{blink_id}'"
            )

        return dest

    def _manifest_path(self) -> Path:
        """Path to the persistent integrity manifest."""
        return self.root / ".bss_manifest.json"

    def _load_manifest(self) -> dict[str, str]:
        """Load persistent hashes from manifest file, if it exists."""
        path = self._manifest_path()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_manifest(self) -> None:
        """Persist current integrity hashes to manifest file."""
        path = self._manifest_path()
        # Merge with existing manifest (other sessions may have added entries)
        existing = self._load_manifest()
        existing.update(self._integrity_hashes)
        path.write_text(
            json.dumps(existing, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _record_integrity(self, blink_id: str, filepath: Path) -> None:
        """Record a hash of a blink's content for integrity checking."""
        if blink_id not in self._integrity_hashes:
            # Check persistent manifest first
            manifest = self._load_manifest()
            if blink_id in manifest:
                self._integrity_hashes[blink_id] = manifest[blink_id]
            else:
                content = filepath.read_bytes()
                self._integrity_hashes[blink_id] = hashlib.sha256(content).hexdigest()
                self._save_manifest()

    def check_immutability(self, blink_id: str) -> bool:
        """Verify a blink hasn't been tampered with since first read.

        Checks both in-memory hashes and the persistent .bss_manifest.json.

        Args:
            blink_id: The blink identifier to check.

        Returns:
            True if the blink is unchanged, False if modified.

        Raises:
            FileNotFoundError: If the blink doesn't exist.
            KeyError: If the blink was never read (no recorded hash).
        """
        if blink_id not in self._integrity_hashes:
            # Try loading from persistent manifest
            manifest = self._load_manifest()
            if blink_id in manifest:
                self._integrity_hashes[blink_id] = manifest[blink_id]
            else:
                raise KeyError(
                    f"No integrity hash recorded for '{blink_id}'. "
                    "Read the blink first to establish a baseline."
                )

        filepath = self.find_blink(blink_id)
        if filepath is None:
            raise FileNotFoundError(f"Blink '{blink_id}' not found")

        current_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
        return current_hash == self._integrity_hashes[blink_id]

    def relay_count(self) -> int:
        """Count blinks in /relay/."""
        return len(self._list_blink_files(self.relay_dir))

    def check_relay_backlog(self) -> bool:
        """Check if relay directory exceeds the recommended threshold.

        Returns:
            True if backlog warning should be issued.
        """
        count = self.relay_count()
        if count > RELAY_WARN_THRESHOLD:
            warnings.warn(
                f"/relay/ contains {count} blinks, "
                f"exceeding recommended limit of {RELAY_WARN_THRESHOLD}",
                stacklevel=2,
            )
            return True
        return False

    def find_artifact(self, sequence: str, author: str) -> Path | None:
        """Find an artifact by its sequence and author prefix.

        Args:
            sequence: 5-char base-36 sequence.
            author: Single character author sigil.

        Returns:
            Path to the artifact, or None if not found.
        """
        prefix = f"{sequence}{author}-"
        if not self.artifacts_dir.exists():
            return None
        for f in self.artifacts_dir.iterdir():
            if f.name.startswith(prefix) and f.is_file():
                return f
        return None

    def register_artifact(
        self, blink_id: str, filepath: Path, slug: str
    ) -> Path:
        """Register a file as an artifact linked to a blink.

        Args:
            blink_id: The parent blink ID.
            filepath: The source file to register.
            slug: Human-readable descriptor (lowercase, hyphens).

        Returns:
            Path to the stored artifact.

        Raises:
            ValueError: If the slug contains unsafe characters.
        """
        # Sanitize slug to prevent path traversal
        if not re.match(r'^[a-z0-9][a-z0-9-]*$', slug):
            raise ValueError(
                f"Invalid artifact slug '{slug}'. "
                "Use only lowercase letters, digits, and hyphens."
            )

        sequence = blink_id[:5]
        author = blink_id[5]
        ext = filepath.suffix
        artifact_name = f"{sequence}{author}-{slug}{ext}"

        self.artifacts_dir.mkdir(exist_ok=True)
        dest = self.artifacts_dir / artifact_name

        # Verify destination stays within artifacts directory
        if not dest.resolve().is_relative_to(self.artifacts_dir.resolve()):
            raise ValueError("Artifact path escapes artifacts directory")

        # Reject symlinks at destination to prevent TOCTOU attacks
        if dest.exists() or dest.is_symlink():
            raise ValueError(
                f"Artifact '{artifact_name}' already exists or is a symlink"
            )

        # Atomic file creation: O_CREAT | O_EXCL prevents TOCTOU races
        source_bytes = filepath.read_bytes()
        fd = os.open(str(dest), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            os.write(fd, source_bytes)
        finally:
            os.close(fd)

        return dest

    def list_artifacts(self) -> list[Path]:
        """Return sorted list of artifact files in /artifacts/.

        Returns:
            Sorted list of file Paths in the artifacts directory.
        """
        if not self.artifacts_dir.exists():
            return []
        return sorted(f for f in self.artifacts_dir.iterdir() if f.is_file())


# ============================================================
# Triage sorting
# ============================================================

# Priority rank (lower number = higher urgency)
PRIORITY_RANK = {"!": 0, "^": 1, "=": 2, ".": 3, "~": 4}
SENSITIVITY_RANK = {"!": 0, "^": 1, "=": 2, ".": 3}
SCOPE_RANK = {"!": 0, "=": 1, "-": 2, ".": 3}


def _triage_key(blink: BlinkFile) -> tuple[int, int, int, int]:
    """Generate a sort key for triage ordering.

    Order: urgency (priority + sensitivity) → recency (sequence desc) → scope (broader first)
    """
    try:
        meta = parse_id(blink.blink_id)
        priority = PRIORITY_RANK.get(meta.priority, 99)
        sensitivity = SENSITIVITY_RANK.get(meta.sensitivity, 99)
        # Recency: negate sequence so higher sequences sort first
        recency = -base36_decode(meta.sequence)
        scope = SCOPE_RANK.get(meta.scope, 99)
        return (priority, sensitivity, recency, scope)
    except (ValueError, IndexError):
        return (99, 99, 0, 99)


def sort_by_triage(blinks: list[BlinkFile]) -> list[BlinkFile]:
    """Sort blinks by triage order per Module 5.2."""
    return sorted(blinks, key=_triage_key)
