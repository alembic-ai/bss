# BSS Security Gaps & Mitigations

## Applied Mitigations (v1.2.0)

### Critical
- **File size guard**: Blink reads reject files exceeding 10 MB, preventing memory exhaustion attacks.
- **Sequence locking**: `next_sequence()` uses file-based locking (`fcntl.flock` / `msvcrt.locking`) to prevent race conditions in concurrent access.

### High
- **HTTP credential rejection**: `OpenAIProvider` raises `ValueError` when an API key would be sent over unencrypted HTTP to a remote host. Localhost is exempted.
- **TOCTOU artifact registration**: `register_artifact()` uses `os.O_CREAT | os.O_EXCL` for atomic file creation, eliminating the check-then-write race window.

### Medium
- **Recursive depth limit**: `_list_blink_files_recursive()` enforces `max_depth=3`, preventing DoS via deeply nested directory structures.
- **Write permissions**: Blink files are written with `0o644` permissions on Unix (world-readable, owner-writable only).
- **Config file permissions**: `config.yaml` (which may contain API keys) is written with `0o600` permissions on Unix.
- **Persistent integrity manifest**: `.bss_manifest.json` persists integrity hashes across sessions, enabling cross-session tampering detection.
- **Lineage validation guards**: All lineage slicing operations validate that `parent_blink.lineage` is a non-empty list before indexing.
- **Generation loop safety**: `get_generation()` uses a bounded loop (max 50 iterations) instead of `while True`.
- **Key masking standardization**: All API key displays use a consistent `_mask_key()` helper that shows only the last 4 characters.
- **Thread-safe reload**: `ModelManager.reload()` inlines unload within the lock to prevent deadlocks.

### Low
- **Thread-safe auto_run**: `RelayRunner.auto_run()` uses `threading.Lock()` around shared `results` list and catches exceptions in the worker thread.
- **Thread join on stop**: `RelayRunner.stop()` joins the auto thread (timeout 10s) and clears the reference.
- **Immutability enforcement at write time**: `write()` raises `FileExistsError` if the blink file already exists.
- **Symlink rejection**: All filesystem scan and lookup operations skip symlinks.
- **Artifact slug sanitization**: Slug validation prevents path traversal via `../` or special characters.

## Known Remaining Gaps

### Scalability (Score: 45/100)

| Gap | Impact | Mitigation Path |
|-----|--------|-----------------|
| O(n) sequence scanning | `highest_sequence()` scans every file in every directory on every call | v2.0: Persistence layer with indexed sequence tracking |
| No caching | `BSSEnvironment` re-reads the filesystem on every operation | v2.0: In-memory cache with filesystem watchers |
| No indexing | Archive `rglob()` traverses everything; no database for lookups | v2.0: SQLite or similar index for O(1) lookups |
| Single-process assumption | Sequence generation now uses file locking (v1.2) but no distributed lock | v2.0: Advisory locking sufficient for single-machine; distributed deployments need coordination service |
| No garbage collection | Archive directories grow without bound | v1.3: Configurable archive rotation / compaction |

### Observability (Score: 20/100)

| Gap | Impact | Mitigation Path |
|-----|--------|-----------------|
| Zero audit logging | No persistent log of file operations, model loads, or errors | v1.3: Structured logging to `.bss/audit.log` |
| No metrics | No counters for blink throughput, inference latency, error rates | v2.0: Metrics endpoint or structured event stream |
| Silent failures | Several `except Exception: pass` patterns swallow errors | v1.3: Replace with specific exception handling and logging |
| No health checks | No way to verify system is operating correctly | v1.3: `bss health` CLI command |

### Network Security

| Gap | Impact | Mitigation Path |
|-----|--------|-----------------|
| No TLS certificate verification | `urllib.request.urlopen` uses default SSL context | v1.3: Optional strict TLS mode with certificate pinning |
| No request timeout configuration | Hardcoded timeouts (5s for health checks, 120s for inference) | v1.3: Configurable timeouts in config.yaml |
| No rate limiting | Unbounded inference requests could overwhelm endpoints | v2.0: Token bucket rate limiter |

### Filesystem Security

| Gap | Impact | Mitigation Path |
|-----|--------|-----------------|
| No disk space checks | Writes can fail silently when disk is full | v1.3: Pre-flight disk space check before write operations |
| Manifest not integrity-protected | `.bss_manifest.json` itself can be tampered with | v2.0: HMAC-signed manifest with per-environment secret |
| No file locking on manifest | Concurrent manifest writes could corrupt JSON | v2.0: File locking on manifest operations |

### Protocol Security

| Gap | Impact | Mitigation Path |
|-----|--------|-----------------|
| No blink signing | Blinks can be forged by any process with filesystem access | v2.0: Optional HMAC or Ed25519 blink signatures |
| No access control | Any process can read/write any directory | v2.0: Optional per-sigil directory permissions |
| Roster not authenticated | Model roster can be modified without authorization | v2.0: Signed roster with admin key |

## Future Work

- **v1.3**: DX improvements, structured logging, health checks, configurable timeouts
- **v2.0**: Persistence layer (SQLite), Gardener daemon, blink signing, metrics, dashboard
