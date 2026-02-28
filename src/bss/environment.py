"""BSS environment manager — wraps a BSS directory structure."""

from __future__ import annotations

import hashlib
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

    def _list_blink_files(self, directory: Path) -> list[Path]:
        """List all .md blink files in a directory."""
        if not directory.exists():
            return []
        return sorted(directory.glob("*.md"))

    def _list_blink_files_recursive(self, directory: Path) -> list[Path]:
        """List all .md blink files in a directory and subdirectories."""
        if not directory.exists():
            return []
        return sorted(directory.rglob("*.md"))

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
            except Exception:
                pass  # Skip unparseable files
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

    def next_sequence(self) -> str:
        """Get the next available sequence number.

        Returns:
            The next 5-char base-36 sequence.
        """
        current = self.highest_sequence()
        if current == "00000":
            return "00001"
        return next_sequence(current)

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
            if path.exists():
                return path

        # Search archive recursively (including subdirectories)
        archive_path = self.archive_dir
        if archive_path.exists():
            matches = list(archive_path.rglob(filename))
            if matches:
                return matches[0]

        return None

    def move_blink(self, blink_id: str, to_directory: str) -> Path:
        """Move a blink between directories.

        Enforces immutability: filename and content are unchanged.

        Args:
            blink_id: The blink identifier to move.
            to_directory: Target directory name.

        Returns:
            New path of the moved blink.

        Raises:
            FileNotFoundError: If the blink doesn't exist.
            ValueError: If immutability check fails.
        """
        source = self.find_blink(blink_id)
        if source is None:
            raise FileNotFoundError(f"Blink '{blink_id}' not found")

        # Read content before move for integrity check
        content_before = source.read_bytes()

        dest_dir = self.root / to_directory
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name

        # Move the file
        source.rename(dest)

        # Verify content unchanged
        content_after = dest.read_bytes()
        if content_before != content_after:
            raise ValueError(
                f"Immutability violation: content changed during move of '{blink_id}'"
            )

        return dest

    def _record_integrity(self, blink_id: str, filepath: Path) -> None:
        """Record a hash of a blink's content for integrity checking."""
        if blink_id not in self._integrity_hashes:
            content = filepath.read_bytes()
            self._integrity_hashes[blink_id] = hashlib.sha256(content).hexdigest()

    def check_immutability(self, blink_id: str) -> bool:
        """Verify a blink hasn't been tampered with since first read.

        Args:
            blink_id: The blink identifier to check.

        Returns:
            True if the blink is unchanged, False if modified.

        Raises:
            FileNotFoundError: If the blink doesn't exist.
            KeyError: If the blink was never read (no recorded hash).
        """
        if blink_id not in self._integrity_hashes:
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
        """
        sequence = blink_id[:5]
        author = blink_id[5]
        ext = filepath.suffix
        artifact_name = f"{sequence}{author}-{slug}{ext}"

        self.artifacts_dir.mkdir(exist_ok=True)
        dest = self.artifacts_dir / artifact_name

        import shutil
        shutil.copy2(filepath, dest)
        return dest


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
