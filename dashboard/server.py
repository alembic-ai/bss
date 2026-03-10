"""BSS Dashboard — FastAPI server with API endpoints and web frontend."""

from __future__ import annotations

import os
import secrets
import sys
import time
import threading
import webbrowser
import asyncio
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.bss.environment import BSSEnvironment
from src.bss.roster import read_roster
from src.bss.sigils import (
    ACTION_STATES, ACTION_ENERGY, ACTION_VALENCE,
    RELATIONAL, CONFIDENCE, COGNITIVE,
    DOMAIN, SUBDOMAIN, SCOPE, MATURITY, PRIORITY, SENSITIVITY,
    describe,
)
from src.bss.identifier import parse, validate, generate
from src.bss.blink_file import read as read_blink, BlinkFile
from src.bss.generations import get_generation, get_chain, needs_convergence, converge
from src.bss.relay import check_escalation, handoff, SessionPhase


DASHBOARD_DIR = Path(__file__).parent


class ComposeRequest(BaseModel):
    summary: str
    author: str
    action_energy: str = "~"
    action_valence: str = "!"
    domain: str = "#"
    subdomain: str = "."
    scope: str = "-"
    parent: Optional[str] = None


class ConvergeRequest(BaseModel):
    leaf_blink_id: str
    summary: str


class RelayRunRequest(BaseModel):
    sigils: list[str]
    max_rounds: int = 10


class ChatRequest(BaseModel):
    sigil: str
    message: str


class ExportRequest(BaseModel):
    format: str = "markdown"
    sections: list[str] = []
    authors: list[str] = []
    title: str = "BSS Swarm Report"


class SettingsConfigUpdate(BaseModel):
    models: dict


class SettingsTestRequest(BaseModel):
    backend: str
    base_url: str = ""
    api_key: str = ""


def _mask_api_key(key: str) -> str:
    """Mask an API key for display, showing only last 4 characters."""
    if not key:
        return ""
    if len(key) > 4:
        return "****" + key[-4:]
    return "****"


def _mask_config_keys(models: dict) -> dict:
    """Return a copy of the models config dict with API keys masked."""
    masked = {}
    for sigil, cfg in models.items():
        entry = dict(cfg)
        if "api_key" in entry and entry["api_key"]:
            entry["api_key"] = _mask_api_key(entry["api_key"])
        masked[sigil] = entry
    return masked


def create_app(env_path: Path, auth_token: str | None = None, port: int = 8741) -> FastAPI:
    """Create the FastAPI application bound to a BSS environment.

    Args:
        env_path: Path to the BSS environment root.
        auth_token: Bearer token for API authentication. If None, auth is disabled.
        port: Port number (used for CORS origin).
    """
    app = FastAPI(
        title="BSS Dashboard",
        description="Blink Sigil System — Visual Dashboard",
        version="2.0.0",
    )

    # Store auth token on app state
    app.state.auth_token = auth_token

    # Restrict CORS to localhost only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://localhost:{port}",
            f"http://127.0.0.1:{port}",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Authentication middleware ---
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        """Require Bearer token for /api/ endpoints when auth is enabled."""
        path = request.url.path

        # Allow unauthenticated access to static files, index, and docs
        if (
            app.state.auth_token is None
            or not path.startswith("/api/")
            or path == "/api/health"
        ):
            response = await call_next(request)
            return response

        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        # Also accept token as query parameter (needed for EventSource/SSE)
        query_token = request.query_params.get("token", "")

        expected = f"Bearer {app.state.auth_token}"
        if auth_header == expected or query_token == app.state.auth_token:
            response = await call_next(request)
            return response

        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized — provide a valid Bearer token"},
        )

    # --- Security headers middleware ---
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://unpkg.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        return response

    # Serve static files
    static_dir = DASHBOARD_DIR / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # --- Environment helpers ---
    def get_env() -> BSSEnvironment:
        env = BSSEnvironment(env_path)
        if not env.is_valid():
            raise HTTPException(status_code=503, detail="BSS environment not initialized")
        return env

    def scan_all(env: BSSEnvironment, dirs=("relay", "active", "archive", "profile")) -> list:
        """Scan directories including archive subdirs (e.g. archive/foundation/)."""
        blinks = []
        seen = set()
        for d in dirs:
            try:
                for b in env.scan(d):
                    if b.blink_id not in seen:
                        seen.add(b.blink_id)
                        blinks.append(b)
            except Exception:
                pass
            # Also scan subdirectories for archive
            if d == "archive":
                archive_dir = env.root / "archive"
                if archive_dir.exists():
                    for sub in archive_dir.iterdir():
                        if sub.is_dir():
                            try:
                                for f in sorted(sub.glob("*.md")):
                                    try:
                                        b = read_blink(f)
                                        if b.blink_id not in seen:
                                            seen.add(b.blink_id)
                                            blinks.append(b)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
        return blinks

    # ──────────────────────────── HTML ────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def index():
        html_path = DASHBOARD_DIR / "templates" / "index.html"
        html = html_path.read_text(encoding="utf-8")
        # Inject auth token into page so frontend JS can use it
        token_script = ""
        if app.state.auth_token:
            # Token is a safe alphanumeric string from secrets.token_urlsafe
            token_script = f'<script>window.__BSS_TOKEN__="{app.state.auth_token}";</script>'
        html = html.replace("</head>", f"{token_script}</head>", 1)
        return HTMLResponse(html)

    # ──────────────────────── ENVIRONMENT ─────────────────────────

    @app.get("/api/environment/status")
    async def environment_status():
        env = get_env()
        dirs = {}
        for name in ["relay", "active", "profile", "archive", "artifacts"]:
            d = getattr(env, f"{name}_dir")
            count = len(list(d.glob("*.md"))) if d.exists() else 0
            dirs[name] = count

        return {
            "root": str(env.root),
            "valid": True,
            "directories": dirs,
            "next_sequence": env.peek_next_sequence(),
            "highest_sequence": env.highest_sequence(),
            "relay_backlog": env.check_relay_backlog(),
        }

    # ──────────────────────── BLINKS ─────────────────────────────

    @app.get("/api/blinks")
    async def list_blinks(
        directory: str = Query("all", pattern="^(relay|active|profile|archive|all)$"),
        sigil: Optional[str] = Query(None, max_length=1),
        limit: int = Query(100, ge=1, le=500),
    ):
        env = get_env()
        blinks = []

        scan_dirs = ["relay", "active", "profile", "archive"] if directory == "all" else [directory]

        for d in scan_dirs:
            try:
                scanned = env.scan(d)
                for b in scanned:
                    if sigil and len(b.blink_id) >= 6 and b.blink_id[5] != sigil.upper():
                        continue
                    try:
                        meta = parse(b.blink_id)
                        action_key = meta.action_energy + meta.action_valence
                        blinks.append({
                            "blink_id": b.blink_id,
                            "directory": d,
                            "summary": b.summary[:200] if b.summary else "",
                            "born_from": b.born_from,
                            "lineage_depth": len(b.lineage),
                            "author": meta.author,
                            "action_state": ACTION_STATES.get(action_key, "Unknown"),
                            "action_energy": meta.action_energy,
                            "action_valence": meta.action_valence,
                            "domain": DOMAIN.get(meta.domain, "Unknown"),
                            "scope": SCOPE.get(meta.scope, "Unknown"),
                            "priority": PRIORITY.get(meta.priority, "Unknown"),
                            "maturity": MATURITY.get(meta.maturity, "Unknown"),
                            "sequence": meta.sequence,
                            "sequence_decimal": meta.sequence_decimal,
                        })
                    except Exception:
                        blinks.append({
                            "blink_id": b.blink_id,
                            "directory": d,
                            "summary": b.summary[:200] if b.summary else "",
                            "born_from": b.born_from,
                            "lineage_depth": len(b.lineage),
                        })
            except Exception:
                continue

        blinks.sort(key=lambda x: x.get("sequence_decimal", 0), reverse=True)
        return {"blinks": blinks[:limit], "total": len(blinks)}

    @app.get("/api/blinks/{blink_id}")
    async def get_blink(blink_id: str):
        env = get_env()
        path = env.find_blink(blink_id)
        if not path:
            raise HTTPException(status_code=404, detail=f"Blink {blink_id} not found")

        blink = read_blink(path)
        meta = parse(blink_id)
        action_key = meta.action_energy + meta.action_valence

        # Determine which directory
        directory = "unknown"
        for d in ["relay", "active", "profile", "archive"]:
            if str(getattr(env, f"{d}_dir")) in str(path):
                directory = d
                break

        return {
            "blink_id": blink.blink_id,
            "directory": directory,
            "summary": blink.summary,
            "born_from": blink.born_from,
            "lineage": blink.lineage,
            "links": blink.links,
            "metadata": {
                "sequence": meta.sequence,
                "sequence_decimal": meta.sequence_decimal,
                "author": meta.author,
                "action_state": ACTION_STATES.get(action_key, "Unknown"),
                "action_energy": meta.action_energy,
                "action_valence": meta.action_valence,
                "relational": RELATIONAL.get(meta.relational, "Unknown"),
                "confidence": CONFIDENCE.get(meta.confidence, "Unknown"),
                "cognitive": COGNITIVE.get(meta.cognitive, "Unknown"),
                "domain": DOMAIN.get(meta.domain, "Unknown"),
                "subdomain": SUBDOMAIN.get(meta.subdomain, "Unknown"),
                "scope": SCOPE.get(meta.scope, "Unknown"),
                "maturity": MATURITY.get(meta.maturity, "Unknown"),
                "priority": PRIORITY.get(meta.priority, "Unknown"),
                "sensitivity": SENSITIVITY.get(meta.sensitivity, "Unknown"),
            },
            "description": describe(blink_id),
            "immutable": env.check_immutability(blink_id),
        }

    @app.get("/api/blinks/{blink_id}/lineage")
    async def blink_lineage(blink_id: str):
        env = get_env()
        path = env.find_blink(blink_id)
        if not path:
            raise HTTPException(status_code=404, detail=f"Blink {blink_id} not found")

        chain = get_chain(env, blink_id)
        generation = get_generation(env, blink_id)
        convergence_needed = needs_convergence(env, blink_id)

        nodes = []
        for b in chain:
            try:
                meta = parse(b.blink_id)
                action_key = meta.action_energy + meta.action_valence
                nodes.append({
                    "blink_id": b.blink_id,
                    "summary": b.summary[:150] if b.summary else "",
                    "born_from": b.born_from,
                    "author": meta.author,
                    "action_state": ACTION_STATES.get(action_key, "Unknown"),
                    "relational": RELATIONAL.get(meta.relational, "Unknown"),
                    "sequence_decimal": meta.sequence_decimal,
                })
            except Exception:
                nodes.append({
                    "blink_id": b.blink_id,
                    "summary": b.summary[:150] if b.summary else "",
                    "born_from": b.born_from,
                })

        return {
            "blink_id": blink_id,
            "generation": generation,
            "needs_convergence": convergence_needed,
            "chain": nodes,
        }

    # ──────────────────────── ROSTER ─────────────────────────────

    @app.get("/api/roster")
    async def get_roster():
        env = get_env()
        roster = read_roster(env)
        if not roster:
            return {"entries": [], "blink_id": None}

        return {
            "entries": [
                {
                    "sigil": e.sigil,
                    "model_id": e.model_id,
                    "role": e.role,
                    "scope_ceiling": e.scope_ceiling,
                    "notes": e.notes,
                }
                for e in roster.entries
            ],
            "blink_id": roster.blink_id,
        }

    # ──────────────────────── RELAY ──────────────────────────────

    @app.get("/api/relay/queue")
    async def relay_queue():
        env = get_env()
        triaged = env.triage("relay")
        items = []
        for b in triaged:
            try:
                meta = parse(b.blink_id)
                action_key = meta.action_energy + meta.action_valence
                items.append({
                    "blink_id": b.blink_id,
                    "summary": b.summary[:200] if b.summary else "",
                    "author": meta.author,
                    "action_state": ACTION_STATES.get(action_key, "Unknown"),
                    "priority": PRIORITY.get(meta.priority, "Unknown"),
                    "scope": SCOPE.get(meta.scope, "Unknown"),
                    "sequence_decimal": meta.sequence_decimal,
                })
            except Exception:
                items.append({
                    "blink_id": b.blink_id,
                    "summary": b.summary[:200] if b.summary else "",
                })
        return {"queue": items, "count": len(items)}

    @app.get("/api/relay/errors")
    async def relay_errors():
        env = get_env()
        chains = check_escalation(env)
        result = []
        for chain in chains:
            result.append([
                {
                    "blink_id": b.blink_id,
                    "summary": b.summary[:150] if b.summary else "",
                }
                for b in chain
            ])
        return {"error_chains": result, "count": len(result)}

    # ──────────────────────── SIGILS ─────────────────────────────

    @app.get("/api/sigils")
    async def sigils_reference():
        return {
            "action_states": ACTION_STATES,
            "action_energy": ACTION_ENERGY,
            "action_valence": ACTION_VALENCE,
            "relational": RELATIONAL,
            "confidence": CONFIDENCE,
            "cognitive": COGNITIVE,
            "domain": DOMAIN,
            "subdomain": SUBDOMAIN,
            "scope": SCOPE,
            "maturity": MATURITY,
            "priority": PRIORITY,
            "sensitivity": SENSITIVITY,
        }

    @app.get("/api/sigils/describe/{blink_id}")
    async def describe_blink_id(blink_id: str):
        valid, violations = validate(blink_id)
        if not valid:
            raise HTTPException(status_code=400, detail={"valid": False, "violations": violations})

        meta = parse(blink_id)
        action_key = meta.action_energy + meta.action_valence

        return {
            "blink_id": blink_id,
            "valid": True,
            "description": describe(blink_id),
            "positions": {
                "sequence": {"value": meta.sequence, "decimal": meta.sequence_decimal},
                "author": {"value": meta.author},
                "action_energy": {"value": meta.action_energy, "meaning": ACTION_ENERGY.get(meta.action_energy)},
                "action_valence": {"value": meta.action_valence, "meaning": ACTION_VALENCE.get(meta.action_valence)},
                "action_state": ACTION_STATES.get(action_key, "Unknown"),
                "relational": {"value": meta.relational, "meaning": RELATIONAL.get(meta.relational)},
                "confidence": {"value": meta.confidence, "meaning": CONFIDENCE.get(meta.confidence)},
                "cognitive": {"value": meta.cognitive, "meaning": COGNITIVE.get(meta.cognitive)},
                "domain": {"value": meta.domain, "meaning": DOMAIN.get(meta.domain)},
                "subdomain": {"value": meta.subdomain, "meaning": SUBDOMAIN.get(meta.subdomain)},
                "scope": {"value": meta.scope, "meaning": SCOPE.get(meta.scope)},
                "maturity": {"value": meta.maturity, "meaning": MATURITY.get(meta.maturity)},
                "priority": {"value": meta.priority, "meaning": PRIORITY.get(meta.priority)},
                "sensitivity": {"value": meta.sensitivity, "meaning": SENSITIVITY.get(meta.sensitivity)},
            },
        }

    # ──────────────────────── LIFECYCLE ───────────────────────────

    @app.get("/api/lifecycle/phases")
    async def lifecycle_phases():
        return {
            "phases": [
                {
                    "name": "INTAKE",
                    "order": 1,
                    "description": "Read relay queue and active blinks. Absorb context from all directories.",
                    "reads": ["/relay/", "/active/", "/profile/"],
                    "writes": [],
                },
                {
                    "name": "TRIAGE",
                    "order": 2,
                    "description": "Sort relay by urgency, recency, and scope. Identify highest-priority work.",
                    "reads": ["/relay/"],
                    "writes": [],
                },
                {
                    "name": "WORK",
                    "order": 3,
                    "description": "Process triaged items. Generate responses, make decisions, create artifacts.",
                    "reads": ["/relay/", "/active/", "/profile/"],
                    "writes": ["/active/"],
                },
                {
                    "name": "OUTPUT",
                    "order": 4,
                    "description": "Write results as handoff blinks. Archive completed work. Register artifacts.",
                    "reads": ["/active/"],
                    "writes": ["/relay/", "/archive/", "/artifacts/"],
                },
                {
                    "name": "DORMANCY",
                    "order": 5,
                    "description": "Session ends. All state persisted in blinks. Next model can pick up cleanly.",
                    "reads": [],
                    "writes": [],
                },
            ],
        }

    # ──────────────────────── ARTIFACTS ───────────────────────────

    @app.get("/api/artifacts")
    async def list_artifacts():
        env = get_env()
        artifacts = env.list_artifacts()
        return {
            "artifacts": [
                {"path": str(a), "name": a.name, "size": a.stat().st_size if a.exists() else 0}
                for a in artifacts
            ],
            "count": len(artifacts),
        }

    # ──────────────────────── MODELS ─────────────────────────────

    @app.get("/api/models")
    async def list_models():
        try:
            from integrations.models import ModelManager
            mm = ModelManager()
            return {
                "available": mm.available_models,
                "loaded": mm.loaded_sigil,
            }
        except Exception:
            return {"available": {}, "loaded": None, "error": "Model manager not available"}

    # ──────────────────────── GRAPH ──────────────────────────

    @app.get("/api/graph/data")
    async def graph_data():
        """Build node + edge data for the knowledge graph."""
        env = get_env()
        nodes = []
        edges = []
        seen_ids = set()
        blink_cache: dict[str, BlinkFile] = {}

        for d in ["relay", "active", "profile", "archive"]:
            try:
                for b in env.scan(d):
                    if b.blink_id in seen_ids:
                        continue
                    seen_ids.add(b.blink_id)
                    blink_cache[b.blink_id] = b
                    try:
                        meta = parse(b.blink_id)
                        action_key = meta.action_energy + meta.action_valence
                        nodes.append({
                            "id": b.blink_id,
                            "author": meta.author,
                            "domain": DOMAIN.get(meta.domain, "Unknown"),
                            "domain_key": meta.domain,
                            "scope": SCOPE.get(meta.scope, "Unknown"),
                            "relational": RELATIONAL.get(meta.relational, "Unknown"),
                            "relational_code": meta.relational,
                            "action_state": ACTION_STATES.get(action_key, "Unknown"),
                            "summary": (b.summary or "")[:120],
                            "directory": d,
                            "sequence": meta.sequence_decimal,
                            "sequence_decimal": meta.sequence_decimal,
                        })
                    except Exception:
                        nodes.append({
                            "id": b.blink_id,
                            "author": "?",
                            "domain": "Unknown",
                            "scope": "Unknown",
                            "relational": "Unknown",
                            "relational_code": "?",
                            "action_state": "Unknown",
                            "summary": (b.summary or "")[:120],
                            "directory": d,
                            "sequence": 0,
                        })
            except Exception:
                continue

        # Build edges from cached blinks
        edge_set = set()
        for bid, b in blink_cache.items():
            # born_from is a list of parent IDs
            for parent_id in (b.born_from or []):
                if parent_id in seen_ids:
                    key = ("born_from", parent_id, bid)
                    if key not in edge_set:
                        edge_set.add(key)
                        edges.append({"source": parent_id, "target": bid, "type": "born_from"})
            for link in (b.links or []):
                if link in seen_ids:
                    key = ("link", bid, link)
                    if key not in edge_set:
                        edge_set.add(key)
                        edges.append({"source": bid, "target": link, "type": "link"})

        # Error chain edges
        try:
            for chain in check_escalation(env):
                for i in range(len(chain) - 1):
                    key = ("error_chain", chain[i].blink_id, chain[i + 1].blink_id)
                    if key not in edge_set:
                        edge_set.add(key)
                        edges.append({"source": chain[i].blink_id, "target": chain[i + 1].blink_id, "type": "error_chain"})
        except Exception:
            pass

        return {"nodes": nodes, "edges": edges}

    # ──────────────────────── ANALYTICS ───────────────────────

    @app.get("/api/analytics/distributions")
    async def analytics_distributions():
        """Aggregate distribution counts for donut charts."""
        env = get_env()
        domain_counts: Counter = Counter()
        scope_counts: Counter = Counter()
        action_counts: Counter = Counter()
        relational_counts: Counter = Counter()

        for d in ["relay", "active", "profile", "archive"]:
            try:
                for b in env.scan(d):
                    try:
                        meta = parse(b.blink_id)
                        domain_counts[DOMAIN.get(meta.domain, "Unknown")] += 1
                        scope_counts[SCOPE.get(meta.scope, "Unknown")] += 1
                        ak = meta.action_energy + meta.action_valence
                        action_counts[ACTION_STATES.get(ak, "Unknown")] += 1
                        relational_counts[RELATIONAL.get(meta.relational, "Unknown")] += 1
                    except Exception:
                        pass
            except Exception:
                continue

        return {
            "domain": dict(domain_counts),
            "scope": dict(scope_counts),
            "action_state": dict(action_counts),
            "relational": dict(relational_counts),
        }

    @app.get("/api/analytics/authors")
    async def analytics_authors():
        """Per-author stats for the leaderboard."""
        env = get_env()
        authors: dict = defaultdict(lambda: {"count": 0, "errors": 0, "domains": Counter()})

        for d in ["relay", "active", "profile", "archive"]:
            try:
                for b in env.scan(d):
                    try:
                        meta = parse(b.blink_id)
                        ak = meta.action_energy + meta.action_valence
                        a = authors[meta.author]
                        a["count"] += 1
                        if ACTION_STATES.get(ak, "") in ("Fault", "Error", "Stall"):
                            a["errors"] += 1
                        a["domains"][DOMAIN.get(meta.domain, "Unknown")] += 1
                    except Exception:
                        pass
            except Exception:
                continue

        result = []
        for sigil, data in sorted(authors.items(), key=lambda x: x[1]["count"], reverse=True):
            top_domain = data["domains"].most_common(1)[0][0] if data["domains"] else "N/A"
            result.append({
                "sigil": sigil,
                "count": data["count"],
                "error_rate": round(data["errors"] / data["count"] * 100, 1) if data["count"] else 0,
                "top_domain": top_domain,
            })

        return {"authors": result}

    @app.get("/api/analytics/heatmap")
    async def analytics_heatmap():
        """Blink counts by file modification date (day-grouped)."""
        env = get_env()
        day_counts: Counter = Counter()

        for d in ["relay", "active", "profile", "archive"]:
            d_path = getattr(env, f"{d}_dir")
            if not d_path.exists():
                continue
            for f in d_path.glob("*.md"):
                try:
                    mtime = f.stat().st_mtime
                    day = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                    day_counts[day] += 1
                except Exception:
                    pass

        return {"days": dict(sorted(day_counts.items()))}

    # ──────────────────────── SEARCH ─────────────────────────

    @app.get("/api/search")
    async def search_blinks(
        q: str = Query(..., min_length=1),
        limit: int = Query(50, ge=1, le=200),
    ):
        """Full-text search across blink summaries."""
        env = get_env()
        query_lower = q.lower()
        results = []

        for d in ["relay", "active", "profile", "archive"]:
            try:
                for b in env.scan(d):
                    if query_lower in (b.summary or "").lower():
                        try:
                            meta = parse(b.blink_id)
                            ak = meta.action_energy + meta.action_valence
                            results.append({
                                "blink_id": b.blink_id,
                                "summary": (b.summary or "")[:300],
                                "directory": d,
                                "author": meta.author,
                                "action_state": ACTION_STATES.get(ak, "Unknown"),
                                "sequence": meta.sequence_decimal,
                            })
                        except Exception:
                            results.append({
                                "blink_id": b.blink_id,
                                "summary": (b.summary or "")[:300],
                                "directory": d,
                            })
            except Exception:
                continue

        results.sort(key=lambda x: x.get("sequence", 0), reverse=True)
        return {"results": results[:limit], "count": len(results), "query": q}

    # ──────────────────────── COMPOSER ────────────────────────

    @app.post("/api/blinks/compose")
    async def compose_blink(req: ComposeRequest):
        """Create a new blink via the web UI."""
        env = get_env()
        try:
            blink = handoff(
                env,
                summary=req.summary,
                author=req.author,
                parent=req.parent,
                domain=req.domain,
                subdomain=req.subdomain,
                scope=req.scope,
            )
            return {"blink_id": blink.blink_id, "status": "created"}
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Failed to compose blink"})

    # ──────────────────────── CONVERGENCE ─────────────────────

    @app.get("/api/convergence/candidates")
    async def convergence_candidates():
        """Find chains approaching the 7-generation limit."""
        env = get_env()
        candidates = []

        for b in scan_all(env):
            try:
                gen = get_generation(env, b.blink_id)
                if gen >= 6:
                    chain = get_chain(env, b.blink_id)
                    chain_ids = [c.blink_id for c in chain]
                    candidates.append({
                        "leaf_blink_id": b.blink_id,
                        "generation": gen,
                        "summary": (b.summary or "")[:150],
                        "chain_ids": chain_ids,
                    })
            except Exception:
                pass

        candidates.sort(key=lambda x: x["generation"], reverse=True)
        return {"candidates": candidates}

    @app.post("/api/convergence/converge")
    async def do_convergence(req: ConvergeRequest):
        """Trigger convergence on a chain."""
        env = get_env()
        try:
            chain = get_chain(env, req.leaf_blink_id)
            if not chain:
                return JSONResponse(status_code=404, content={"error": "Chain not found"})
            result = converge(env, chain, req.summary)
            return {"blink_id": result.blink_id, "status": "converged"}
        except Exception as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})

    # ──────────────────────── HEALTH ──────────────────────────

    @app.get("/api/health")
    async def health_check():
        """Run health checks on the BSS environment."""
        env = get_env()
        checks = []

        # Immutability check
        try:
            immutable_ok = True
            for d in ["relay", "active", "profile", "archive"]:
                for b in env.scan(d):
                    if not env.check_immutability(b.blink_id):
                        immutable_ok = False
                        break
                if not immutable_ok:
                    break
            checks.append({
                "name": "Immutability",
                "status": "ok" if immutable_ok else "error",
                "detail": "All blinks immutable" if immutable_ok else "Immutability violation detected",
            })
        except Exception as exc:
            checks.append({"name": "Immutability", "status": "error", "detail": str(exc)})

        # Relay backlog
        try:
            backlog_count = env.relay_count()
            status = "ok" if backlog_count < 10 else "warning" if backlog_count < 25 else "error"
            checks.append({
                "name": "Relay Backlog",
                "status": status,
                "detail": f"{backlog_count} blinks in relay queue",
            })
        except Exception as exc:
            checks.append({"name": "Relay Backlog", "status": "error", "detail": str(exc)})

        # Stale blink detection
        try:
            stale_count = 0
            now = time.time()
            for f in env.relay_dir.glob("*.md"):
                if now - f.stat().st_mtime > 86400:  # 24 hours
                    stale_count += 1
            status = "ok" if stale_count == 0 else "warning"
            checks.append({
                "name": "Stale Blinks",
                "status": status,
                "detail": f"{stale_count} relay blinks older than 24h" if stale_count else "No stale blinks",
            })
        except Exception as exc:
            checks.append({"name": "Stale Blinks", "status": "error", "detail": str(exc)})

        # Directory health
        for d in ["relay", "active", "profile", "archive", "artifacts"]:
            d_path = getattr(env, f"{d}_dir")
            checks.append({
                "name": f"/{d}/",
                "status": "ok" if d_path.exists() else "error",
                "detail": "Exists" if d_path.exists() else "Missing",
            })

        return {"checks": checks}

    # ──────────────────── RELAY RUNNER (SSE) ──────────────────

    _runner_events: asyncio.Queue = asyncio.Queue()
    _runner_state = {"active": False, "thread": None}

    @app.post("/api/relay/run/start")
    async def relay_run_start(req: RelayRunRequest):
        if _runner_state["active"]:
            return {"error": "Relay already running"}
        try:
            from integrations.models import ModelManager
            from integrations.runner import RelayRunner

            env = get_env()
            mm = ModelManager()
            runner = RelayRunner(env, mm)
            loop = asyncio.get_event_loop()

            def _callback(event):
                loop.call_soon_threadsafe(_runner_events.put_nowait, event)

            def _run():
                try:
                    runner.auto_run(req.sigils, max_rounds=req.max_rounds, callback=_callback)
                    loop.call_soon_threadsafe(_runner_events.put_nowait, {"type": "done"})
                except Exception as exc:
                    loop.call_soon_threadsafe(
                        _runner_events.put_nowait, {"type": "error", "error": str(exc)}
                    )
                finally:
                    _runner_state["active"] = False

            _runner_state["active"] = True
            # Clear old events
            while not _runner_events.empty():
                try:
                    _runner_events.get_nowait()
                except asyncio.QueueEmpty:
                    break

            t = threading.Thread(target=_run, daemon=True)
            _runner_state["thread"] = t
            t.start()
            return {"status": "started", "sigils": req.sigils, "max_rounds": req.max_rounds}
        except ImportError:
            return JSONResponse(status_code=503, content={"error": "Runner dependencies not available"})
        except Exception as exc:
            return JSONResponse(status_code=500, content={"error": "Internal server error"})

    @app.post("/api/relay/run/stop")
    async def relay_run_stop():
        _runner_state["active"] = False
        await _runner_events.put({"type": "done"})
        return {"status": "stopped"}

    @app.get("/api/relay/run/stream")
    async def relay_run_stream():
        """SSE stream of relay runner events."""
        import json

        async def event_generator():
            while True:
                try:
                    event = await asyncio.wait_for(_runner_events.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # ──────────────────────── CHAT ────────────────────────────

    _chat_sessions: dict = {}
    _chat_lock = threading.Lock()

    @app.post("/api/chat/send")
    async def chat_send(req: ChatRequest):
        """Send a message to a model and get a response."""
        env = get_env()
        try:
            from integrations.models import ModelManager
            from integrations.session import BSSSession

            with _chat_lock:
                if req.sigil not in _chat_sessions:
                    mm = ModelManager()
                    _chat_sessions[req.sigil] = BSSSession(env, req.sigil, mm)
                session = _chat_sessions[req.sigil]

            # Ensure intake has been done
            if session._system_prompt is None:
                session.intake()

            response, tokens, elapsed = session.invoke(req.message)

            # Write handoff blink
            summary = response[:400] if len(response) > 400 else response
            # Ensure at least 1 sentence
            if not any(c in summary for c in '.!?'):
                summary += '.'
            try:
                blink = session.handoff(summary, min_sentences=1)
                blink_id = blink.blink_id
                # Reset session for next message (fresh relay context)
                with _chat_lock:
                    _chat_sessions.pop(req.sigil, None)
            except Exception:
                blink_id = None

            return {
                "response": response,
                "tokens": tokens,
                "elapsed": elapsed,
                "blink_id": blink_id,
                "sigil": req.sigil,
            }
        except ImportError:
            return JSONResponse(status_code=503, content={"error": "Model backends not available. Configure models in the terminal gateway first."})
        except Exception:
            return JSONResponse(status_code=500, content={"error": "Internal server error during chat"})

    @app.post("/api/chat/clear")
    async def chat_clear():
        with _chat_lock:
            _chat_sessions.clear()
        return {"status": "cleared"}

    # ──────────────────────── TASK BOARD ──────────────────────

    @app.get("/api/tasks/board")
    async def task_board():
        """Categorize blinks into kanban columns by action state."""
        env = get_env()
        board = {"queued": [], "in_progress": [], "completed": [], "errors": []}

        for d in ["relay", "active", "archive"]:
            try:
                for b in env.scan(d):
                    try:
                        meta = parse(b.blink_id)
                        ak = meta.action_energy + meta.action_valence
                        state = ACTION_STATES.get(ak, "Unknown")
                        item = {
                            "blink_id": b.blink_id,
                            "summary": (b.summary or "")[:150],
                            "author": meta.author,
                            "action_state": state,
                            "priority": PRIORITY.get(meta.priority, "Normal"),
                            "scope": SCOPE.get(meta.scope, "Unknown"),
                            "domain": DOMAIN.get(meta.domain, "Unknown"),
                            "directory": d,
                            "sequence": meta.sequence_decimal,
                        }

                        if state in ("Error", "Fault", "Stall"):
                            board["errors"].append(item)
                        elif state in ("Completed", "Idle"):
                            board["completed"].append(item)
                        elif state in ("In progress", "Blocked", "Decision needed", "Awaiting user input"):
                            board["in_progress"].append(item)
                        elif state in ("Handoff", "Informational"):
                            board["queued"].append(item)
                        elif d == "relay":
                            board["queued"].append(item)
                        elif d == "archive":
                            board["completed"].append(item)
                        else:
                            board["in_progress"].append(item)
                    except Exception:
                        pass
            except Exception:
                continue

        # Sort each column by sequence (newest first)
        for col in board.values():
            col.sort(key=lambda x: x.get("sequence", 0), reverse=True)

        return board

    # ──────────────────────── CONVERSATIONS ───────────────────

    @app.get("/api/conversations/threads")
    async def conversation_threads():
        """Build conversation threads from lineage chains."""
        env = get_env()
        threads_by_root = {}

        for b in scan_all(env):
            try:
                chain = get_chain(env, b.blink_id)
                if len(chain) < 2:
                    continue
                root_id = chain[0].blink_id
                if root_id in threads_by_root and threads_by_root[root_id]["message_count"] >= len(chain):
                    continue
                participants = set()
                for c in chain:
                    try:
                        m = parse(c.blink_id)
                        participants.add(m.author)
                    except Exception:
                        pass
                gen = get_generation(env, chain[-1].blink_id)
                threads_by_root[root_id] = {
                    "root_id": root_id,
                    "initiator": parse(root_id).author,
                    "participants": sorted(participants),
                    "message_count": len(chain),
                    "preview": (chain[0].summary or "")[:100],
                    "generation": gen,
                }
            except Exception:
                pass

        threads = sorted(threads_by_root.values(), key=lambda x: x["message_count"], reverse=True)
        return {"threads": threads[:30]}

    @app.get("/api/conversations/thread/{root_id}")
    async def conversation_thread(root_id: str):
        """Get a full conversation thread as ordered messages."""
        env = get_env()
        # Collect all blinks including archive subdirs
        all_blinks = {b.blink_id: b for b in scan_all(env)}

        if root_id in all_blinks:
            # Walk forward: find all blinks whose born_from includes a chain member
            chain_ids = {root_id}
            changed = True
            while changed:
                changed = False
                for bid, b in all_blinks.items():
                    if bid not in chain_ids and b.born_from:
                        if any(p in chain_ids for p in b.born_from):
                            chain_ids.add(bid)
                            changed = True
            chain = [all_blinks[bid] for bid in chain_ids]
        else:
            # Root not in scanned dirs — find any blink whose chain includes root_id
            chain = []
            for bid, b in all_blinks.items():
                try:
                    c = get_chain(env, bid)
                    if any(x.blink_id == root_id for x in c):
                        # Use all blinks from this chain that we have
                        for x in c:
                            if x.blink_id in all_blinks and x not in chain:
                                chain.append(x)
                except Exception:
                    pass
            if not chain:
                raise HTTPException(status_code=404, detail="Thread not found")

        # Order by sequence number
        chain.sort(key=lambda b: parse(b.blink_id).sequence_decimal if b.blink_id else 0)

        messages = []
        for b in chain:
            try:
                meta = parse(b.blink_id)
                ak = meta.action_energy + meta.action_valence
                messages.append({
                    "blink_id": b.blink_id,
                    "author": meta.author,
                    "summary": b.summary or "",
                    "action_state": ACTION_STATES.get(ak, "Unknown"),
                    "scope": SCOPE.get(meta.scope, "Unknown"),
                    "sequence": meta.sequence_decimal,
                })
            except Exception:
                messages.append({
                    "blink_id": b.blink_id,
                    "author": "?",
                    "summary": b.summary or "",
                    "action_state": "Unknown",
                    "scope": "Unknown",
                })

        gen = get_generation(env, chain[-1].blink_id) if chain else 1
        return {"messages": messages, "generation": gen, "root_id": root_id}

    # ──────────────────────── ACTIVITY FEED ───────────────────

    @app.get("/api/feed/recent")
    async def feed_recent(
        limit: int = Query(50, ge=1, le=200),
        after: int = Query(0, ge=0),
    ):
        """Recent blink activity as a feed."""
        env = get_env()
        events = []

        for b in scan_all(env):
            try:
                meta = parse(b.blink_id)
                if after and meta.sequence_decimal <= after:
                    continue
                ak = meta.action_energy + meta.action_valence
                state = ACTION_STATES.get(ak, "Unknown")
                evt_type = "normal"
                if state in ("Error", "Fault", "Stall"):
                    evt_type = "error"
                elif RELATIONAL.get(meta.relational, "") == "Convergence":
                    evt_type = "convergence"

                # Determine directory from blink file location
                blink_path = env.find_blink(b.blink_id)
                directory = "unknown"
                if blink_path:
                    try:
                        directory = blink_path.relative_to(env.root).parts[0]
                    except Exception:
                        pass

                events.append({
                    "blink_id": b.blink_id,
                    "author": meta.author,
                    "action_state": state,
                    "summary": (b.summary or "")[:150],
                    "directory": directory,
                    "sequence": meta.sequence_decimal,
                    "type": evt_type,
                })
            except Exception:
                pass

        events.sort(key=lambda x: x.get("sequence", 0), reverse=True)
        return {"events": events[:limit]}

    # ──────────────────────── ARTIFACTS (enhanced) ────────────

    @app.get("/api/artifacts/detailed")
    async def artifacts_detailed():
        """Detailed artifact listing with metadata."""
        env = get_env()
        artifacts = env.list_artifacts()
        result = []
        for a in artifacts:
            try:
                result.append({
                    "path": str(a),
                    "name": a.name,
                    "size": a.stat().st_size if a.exists() else 0,
                    "modified": datetime.fromtimestamp(a.stat().st_mtime).isoformat() if a.exists() else None,
                })
            except Exception:
                pass
        return {"artifacts": result, "count": len(result)}

    @app.get("/api/artifacts/preview")
    async def artifact_preview(path: str = Query(...)):
        """Preview artifact file content (text files only)."""
        env = get_env()
        file_path = Path(path)
        # Security: ensure the file is within artifacts dir
        try:
            file_path.resolve().relative_to(env.artifacts_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        try:
            content = file_path.read_text(encoding="utf-8")[:10000]
            return {"name": file_path.name, "content": content, "truncated": len(content) >= 10000}
        except Exception:
            raise HTTPException(status_code=400, detail="Cannot preview binary files")

    @app.get("/api/artifacts/download/{filename}")
    async def artifact_download(filename: str):
        """Download an artifact file."""
        from fastapi.responses import FileResponse
        env = get_env()
        file_path = env.artifacts_dir / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        try:
            file_path.resolve().relative_to(env.artifacts_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        return FileResponse(str(file_path), filename=filename)

    # ──────────────────────── EXPORT / REPORT ─────────────────

    @app.post("/api/export/generate")
    async def export_generate(req: ExportRequest):
        """Generate a customizable report."""
        env = get_env()
        sections_content = []

        # Gather data based on selected sections
        all_blinks = []
        for d in ["relay", "active", "profile", "archive"]:
            try:
                for b in env.scan(d):
                    try:
                        meta = parse(b.blink_id)
                        ak = meta.action_energy + meta.action_valence
                        if req.authors and meta.author not in req.authors:
                            continue
                        all_blinks.append({
                            "blink_id": b.blink_id,
                            "summary": b.summary or "",
                            "author": meta.author,
                            "action_state": ACTION_STATES.get(ak, "Unknown"),
                            "domain": DOMAIN.get(meta.domain, "Unknown"),
                            "scope": SCOPE.get(meta.scope, "Unknown"),
                            "directory": d,
                            "sequence": meta.sequence_decimal,
                        })
                    except Exception:
                        pass
            except Exception:
                continue

        all_blinks.sort(key=lambda x: x.get("sequence", 0), reverse=True)

        if req.format == "json":
            import json
            report = {"title": req.title, "generated": datetime.now().isoformat()}
            if "summary" in req.sections:
                report["summary"] = {
                    "total_blinks": len(all_blinks),
                    "authors": list(set(b["author"] for b in all_blinks)),
                    "directories": dict(Counter(b["directory"] for b in all_blinks)),
                }
            if "blinks" in req.sections:
                report["blinks"] = all_blinks[:100]
            if "analytics" in req.sections:
                report["analytics"] = {
                    "action_states": dict(Counter(b["action_state"] for b in all_blinks)),
                    "domains": dict(Counter(b["domain"] for b in all_blinks)),
                    "scopes": dict(Counter(b["scope"] for b in all_blinks)),
                }
            if "errors" in req.sections:
                report["errors"] = [b for b in all_blinks if b["action_state"] in ("Error", "Fault", "Stall")]
            if "roster" in req.sections:
                roster = read_roster(env)
                if roster:
                    report["roster"] = [{"sigil": e.sigil, "model_id": e.model_id, "role": e.role, "scope_ceiling": e.scope_ceiling} for e in roster.entries]
            return {"title": req.title, "content": json.dumps(report, indent=2)}

        # Markdown format
        lines = [f"# {req.title}", f"", f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*", ""]

        if "summary" in req.sections:
            authors = sorted(set(b["author"] for b in all_blinks))
            dir_counts = Counter(b["directory"] for b in all_blinks)
            lines += [
                "## Summary", "",
                f"- **Total Blinks:** {len(all_blinks)}",
                f"- **Authors:** {', '.join(authors) or 'None'}",
                f"- **Directories:** {', '.join(f'{k} ({v})' for k, v in dir_counts.items())}",
                "",
            ]

        if "roster" in req.sections:
            roster = read_roster(env)
            if roster:
                lines += ["## Roster", "", "| Sigil | Model | Role | Scope Ceiling |", "|-------|-------|------|---------------|"]
                for e in roster.entries:
                    lines.append(f"| {e.sigil} | {e.model_id} | {e.role} | {e.scope_ceiling} |")
                lines.append("")

        if "analytics" in req.sections:
            action_counts = Counter(b["action_state"] for b in all_blinks)
            domain_counts = Counter(b["domain"] for b in all_blinks)
            lines += [
                "## Analytics", "",
                "### Action States", "",
            ]
            for state, count in action_counts.most_common():
                lines.append(f"- {state}: {count}")
            lines += ["", "### Domains", ""]
            for domain, count in domain_counts.most_common():
                lines.append(f"- {domain}: {count}")
            lines.append("")

        if "blinks" in req.sections:
            lines += ["## Recent Blinks", ""]
            for b in all_blinks[:50]:
                lines.append(f"- **{b['blink_id'][:8]}** [{b['author']}] {b['action_state']} — {b['summary'][:100]}")
            lines.append("")

        if "errors" in req.sections:
            errors = [b for b in all_blinks if b["action_state"] in ("Error", "Fault", "Stall")]
            lines += ["## Errors", ""]
            if errors:
                for b in errors:
                    lines.append(f"- **{b['blink_id'][:8]}** [{b['author']}] {b['summary'][:120]}")
            else:
                lines.append("No errors detected.")
            lines.append("")

        if "health" in req.sections:
            backlog = env.check_relay_backlog()
            lines += [
                "## Health", "",
                f"- Relay Backlog: {backlog}",
                f"- Environment: {env.root}",
                "",
            ]

        content = "\n".join(lines)
        return {"title": req.title, "content": content}

    # ──────────────────────── SETTINGS ──────────────────────────

    @app.get("/api/settings/config")
    async def settings_get_config():
        """Read current model configuration (API keys are masked)."""
        import yaml
        config_path = Path("integrations/config.yaml")
        if not config_path.exists():
            return {"models": {}, "config_path": str(config_path)}
        try:
            raw = config_path.read_text(encoding="utf-8")
            cfg = yaml.safe_load(raw) or {}
            # Mask API keys before sending to frontend
            masked_models = _mask_config_keys(cfg.get("models", {}))
            return {"models": masked_models, "config_path": str(config_path.resolve())}
        except Exception as exc:
            return {"models": {}, "config_path": str(config_path), "error": "Failed to read config"}

    @app.post("/api/settings/config")
    async def settings_update_config(req: SettingsConfigUpdate):
        """Write updated model configuration."""
        import yaml
        config_path = Path("integrations/config.yaml")
        try:
            # Preserve existing API keys when frontend sends masked values
            existing_models = {}
            if config_path.exists():
                try:
                    existing = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                    existing_models = existing.get("models", {})
                except Exception:
                    pass

            # For each model, if the incoming api_key starts with "****",
            # keep the existing key instead
            models = dict(req.models)
            for sigil, cfg in models.items():
                if "api_key" in cfg and isinstance(cfg["api_key"], str):
                    if cfg["api_key"].startswith("****") and sigil in existing_models:
                        existing_key = existing_models[sigil].get("api_key", "")
                        if existing_key:
                            cfg["api_key"] = existing_key
                        else:
                            del cfg["api_key"]

            out = {"models": models}
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                "# WARNING: This file may contain API keys. Keep it private.\n"
                + yaml.dump(out, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
            # Restore restrictive permissions (owner read/write only)
            if sys.platform != "win32":
                os.chmod(str(config_path), 0o600)
            return {"ok": True}
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to save config")

    @app.get("/api/settings/discover")
    async def settings_discover():
        """Scan for available model backends."""
        try:
            from integrations.discovery import discover_all
            report = discover_all()
            results = []
            for r in report.results:
                results.append({
                    "backend": r.backend,
                    "source": r.source,
                    "label": r.label,
                    "available": r.available,
                    "details": r.details,
                })
            return {"results": results, "elapsed": report.elapsed}
        except ImportError:
            return {"results": [], "elapsed": 0, "error": "Discovery module not available"}
        except Exception as exc:
            return {"results": [], "elapsed": 0, "error": str(exc)}

    @app.post("/api/settings/test")
    async def settings_test_connection(req: SettingsTestRequest):
        """Test a backend connection."""
        try:
            if req.backend == "openai":
                from integrations.discovery import check_endpoint
                ok = check_endpoint(req.base_url, req.api_key or None)
                return {"ok": ok, "message": "Endpoint reachable" if ok else "Endpoint unreachable"}
            elif req.backend == "ollama":
                from integrations.discovery import list_ollama_models
                models = list_ollama_models(req.base_url or "http://localhost:11434")
                return {"ok": bool(models), "message": f"Found {len(models)} models" if models else "No models found", "models": models}
            elif req.backend in ("anthropic", "gemini", "huggingface"):
                return {"ok": bool(req.api_key), "message": "API key provided" if req.api_key else "No API key"}
            elif req.backend == "gguf":
                from integrations.discovery import scan_gguf_files
                files = scan_gguf_files()
                return {"ok": bool(files), "message": f"Found {len(files)} GGUF files", "files": files}
            else:
                return {"ok": False, "message": f"Unknown backend: {req.backend}"}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    @app.get("/api/settings/environment")
    async def settings_environment():
        """Environment info for settings panel."""
        env = get_env()
        counts = {}
        for d in ["relay", "active", "archive", "profile", "artifacts"]:
            try:
                counts[d] = len(list(env.scan(d)))
            except Exception:
                counts[d] = 0
        marker = (env.root / ".bss_v2_setup_complete").exists()
        return {
            "path": str(env.root),
            "directories": counts,
            "onboarding_complete": marker,
            "total_blinks": sum(counts.values()),
        }

    @app.post("/api/settings/gateway/launch")
    async def settings_launch_gateway():
        """Launch the terminal gateway in a subprocess."""
        import subprocess
        import sys
        env = get_env()
        try:
            subprocess.Popen(
                [sys.executable, "-m", "cli.main", "gateway", str(env.root)],
                start_new_session=True,
            )
            return {"ok": True, "message": "Gateway launched"}
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to launch gateway")

    return app


def launch_dashboard(
    env_path: Path,
    port: int = 8741,
    host: str = "127.0.0.1",
    open_browser: bool = True,
):
    """Launch the BSS dashboard server.

    Args:
        env_path: Path to the BSS environment root.
        port: Port to bind to.
        host: Host address to bind to (default: 127.0.0.1 for security).
        open_browser: Whether to auto-open the browser.
    """
    import uvicorn

    # Generate auth token for this session
    auth_token = secrets.token_urlsafe(32)
    app = create_app(env_path, auth_token=auth_token, port=port)

    def _open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    if open_browser:
        threading.Thread(target=_open_browser, daemon=True).start()

    print(f"\n  BSS Dashboard running at http://{host}:{port}")
    print(f"  Environment: {env_path}")
    print(f"  Auth token:  {auth_token}")
    if host != "127.0.0.1" and host != "localhost":
        print(f"  WARNING: Server is exposed on {host}. Auth token is required for API access.")
    print(f"  Press Ctrl+C to stop\n")

    uvicorn.run(app, host=host, port=port, log_level="warning")


def launch_dashboard_background(
    env_path: Path,
    port: int = 8741,
    host: str = "127.0.0.1",
    open_browser: bool = True,
):
    """Launch the BSS dashboard in a background daemon thread (non-blocking).

    Args:
        env_path: Path to the BSS environment root.
        port: Port to bind to.
        host: Host address to bind to (default: 127.0.0.1 for security).
        open_browser: Whether to auto-open the browser.
    """
    import uvicorn

    auth_token = secrets.token_urlsafe(32)
    app = create_app(env_path, auth_token=auth_token, port=port)

    def _serve():
        uvicorn.run(app, host=host, port=port, log_level="warning")

    server_thread = threading.Thread(target=_serve, daemon=True)
    server_thread.start()

    if open_browser:
        def _open():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=_open, daemon=True).start()

    print(f"  BSS Dashboard running in background at http://{host}:{port}")
    print(f"  Auth token: {auth_token}")
    return server_thread
