# -*- coding: utf-8 -*-
"""Layer 1: Persistent Memory Engine (Qdrant + TEI with SQLite FTS5 Lite Fallback).

Supports three modes via `XENONITE_MEMORY_BACKEND`:
- `auto`   (default): Uses Qdrant + TEI when reachable, seamlessly falls back to local SQLite FTS5.
- `qdrant`: Strictly queries Qdrant + TEI (auto-creates collection if missing).
- `sqlite`: Runs 100% locally with zero Docker or GPU overhead.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, List, Optional

from xenonite_stack.config import XenoniteSettings


def _qdrant_headers(settings: XenoniteSettings) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.qdrant_api_key:
        headers["api-key"] = settings.qdrant_api_key
    return headers


def _get_embedding(text: str, settings: XenoniteSettings) -> list[float]:
    req = urllib.request.Request(
        settings.tei_url,
        data=json.dumps({"inputs": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if isinstance(res, list) and res and isinstance(res[0], list):
            return res[0]
        if isinstance(res, list):
            return res
        raise ValueError("Unexpected TEI embedding response format")


def ensure_qdrant_collection(settings: XenoniteSettings) -> None:
    """Ensure the configured Qdrant collection exists before read/write."""
    url = f"{settings.qdrant_url}/collections/{settings.qdrant_collection}"
    req = urllib.request.Request(url, headers=_qdrant_headers(settings), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=4):
            return
    except urllib.error.HTTPError as err:
        if err.code != 404:
            raise

    create_body = {
        "vectors": {
            "size": settings.qdrant_vector_size,
            "distance": "Cosine",
        }
    }
    create_req = urllib.request.Request(
        url,
        data=json.dumps(create_body).encode("utf-8"),
        headers=_qdrant_headers(settings),
        method="PUT",
    )
    with urllib.request.urlopen(create_req, timeout=6):
        return


def _format_memory_blob(
    project: str,
    title: str,
    content: str,
    domain: str,
    module: Optional[str],
    tags: List[str],
    files: List[str],
    status: str,
) -> str:
    mod_str = f" | MODULE: {module}" if module else ""
    return (
        f"[PROJECT: {project} | DOMAIN: {domain}{mod_str} | STATUS: {status}]\n"
        f"Title: {title}\n"
        f"Content:\n{content}\n"
        f"Tags: {', '.join(tags) if tags else 'N/A'}\n"
        f"Referenced Files: {', '.join(files) if files else 'N/A'}"
    )


def _deterministic_point_id(project: str, domain: str, module: Optional[str], title: str) -> str:
    mod_part = f"_{module}" if module else ""
    slug = "".join(c if c.isalnum() else "_" for c in title.lower())[:40]
    point_key = f"{project}_{domain}{mod_part}_{slug}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"xenonite.memory.{point_key}"))


# ---------------------------------------------------------------------------
# SQLite FTS5 Lite Backend (Zero-Docker Portable Fallback)
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _open_sqlite(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    module TEXT,
                    title TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    status TEXT NOT NULL,
                    file_references TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id UNINDEXED,
                    project,
                    domain,
                    title,
                    tags,
                    data
                )
                """
            )
            yield conn
    finally:
        conn.close()


def _sqlite_upsert(
    settings: XenoniteSettings,
    point_id: str,
    project: str,
    domain: str,
    module: Optional[str],
    title: str,
    tags: List[str],
    status: str,
    files: List[str],
    formatted_data: str,
    now_iso: str,
) -> None:
    tags_json = json.dumps(tags, ensure_ascii=False)
    files_json = json.dumps(files, ensure_ascii=False)
    with _open_sqlite(settings.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO memories (
                id, project, domain, module, title, tags, status,
                file_references, data, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                project=excluded.project,
                domain=excluded.domain,
                module=excluded.module,
                title=excluded.title,
                tags=excluded.tags,
                status=excluded.status,
                file_references=excluded.file_references,
                data=excluded.data,
                updated_at=excluded.updated_at
            """,
            (
                point_id, project, domain, module, title, tags_json,
                status, files_json, formatted_data, now_iso, now_iso,
            ),
        )
        conn.execute("DELETE FROM memories_fts WHERE id = ?", (point_id,))
        conn.execute(
            "INSERT INTO memories_fts (id, project, domain, title, tags, data) VALUES (?, ?, ?, ?, ?, ?)",
            (point_id, project, domain, title, " ".join(tags), formatted_data),
        )


def _sqlite_search(
    settings: XenoniteSettings,
    query: str,
    project: Optional[str],
    domain: Optional[str],
    limit: int,
) -> list[dict[str, Any]]:
    tokens = [t for t in "".join(c if c.isalnum() else " " for c in query).split() if len(t) >= 2]
    with _open_sqlite(settings.sqlite_path) as conn:
        filters: list[str] = []
        params: list[Any] = []
        if project:
            filters.append("m.project = ?")
            params.append(project)
        if domain:
            filters.append("m.domain = ?")
            params.append(domain)

        if tokens:
            fts_query = " OR ".join(f'"{t}"' for t in tokens[:10])
            where_extra = (" AND " + " AND ".join(filters)) if filters else ""
            sql = f"""
                SELECT m.*, bm25(memories_fts) AS rank
                FROM memories_fts
                JOIN memories m ON m.id = memories_fts.id
                WHERE memories_fts MATCH ? {where_extra}
                ORDER BY rank ASC
                LIMIT ?
            """
            rows = conn.execute(sql, [fts_query, *params, limit]).fetchall()
        else:
            where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""
            sql = f"SELECT m.*, 0.0 AS rank FROM memories m {where_clause} ORDER BY m.updated_at DESC LIMIT ?"
            rows = conn.execute(sql, [*params, limit]).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "score": round(1.0 / (1.0 + abs(float(row["rank"]))), 3),
                "payload": {
                    "project": row["project"],
                    "domain": row["domain"],
                    "module": row["module"],
                    "title": row["title"],
                    "file_references": json.loads(row["file_references"] or "[]"),
                    "data": row["data"],
                },
            }
        )
    return results


def _sqlite_list_projects(settings: XenoniteSettings) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    if not settings.sqlite_path.is_file():
        return summary
    with _open_sqlite(settings.sqlite_path) as conn:
        for row in conn.execute("SELECT project, domain FROM memories").fetchall():
            proj = row["project"] or "unscoped"
            dom = row["domain"] or "general"
            if proj not in summary:
                summary[proj] = {"count": 0, "domains": set()}
            summary[proj]["count"] += 1
            summary[proj]["domains"].add(dom)
    return summary


# ---------------------------------------------------------------------------
# Public Layer 1 Tool Implementations
# ---------------------------------------------------------------------------

def _render_search_results(points: list[dict[str, Any]], backend_label: str, query: str, project: Optional[str]) -> str:
    if not points:
        proj_str = f" for project '{project}'" if project else ""
        return f"No relevant memory found{proj_str} (backend={backend_label}) for query: '{query}'"

    output = [f"=== UNIVERSAL MEMORY SEARCH [{backend_label}] (Total: {len(points)}) ==="]
    for idx, pt in enumerate(points):
        score = pt.get("score", 0.0)
        payload = pt.get("payload", {})
        output.append(
            f"\n[{idx + 1}] Score: {score:.3f} | Project: {payload.get('project', 'general')} "
            f"| Domain: {payload.get('domain', 'general')}"
        )
        output.append(f"Title: {payload.get('title', 'Untitled')}")
        if payload.get("module"):
            output.append(f"Module: {payload.get('module')}")
        if payload.get("file_references"):
            output.append(f"Files: {payload.get('file_references')}")
        output.append(f"Content:\n{payload.get('data')}")
        output.append("-" * 45)
    return "\n".join(output)


def search_memory(
    query: str,
    project: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 4,
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 1] Semantic memory search across Qdrant+TEI or local SQLite FTS5."""
    cfg = settings or XenoniteSettings.load()

    if cfg.memory_backend != "sqlite":
        try:
            ensure_qdrant_collection(cfg)
            vector = _get_embedding(query, cfg)
            must_conditions: list[dict[str, Any]] = []
            if project:
                must_conditions.append({"key": "project", "match": {"value": project}})
            if domain:
                must_conditions.append({"key": "domain", "match": {"value": domain}})

            search_body: dict[str, Any] = {
                "vector": vector,
                "limit": limit,
                "with_payload": True,
            }
            if must_conditions:
                search_body["filter"] = {"must": must_conditions}

            req = urllib.request.Request(
                f"{cfg.qdrant_url}/collections/{cfg.qdrant_collection}/points/search",
                data=json.dumps(search_body).encode("utf-8"),
                headers=_qdrant_headers(cfg),
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            return _render_search_results(res.get("result", []), "qdrant+tei", query, project)
        except Exception as exc:
            if cfg.memory_backend == "qdrant":
                return f"Memory search error (qdrant backend): {exc}"

    try:
        points = _sqlite_search(cfg, query, project, domain, limit)
        return _render_search_results(points, "sqlite-fts5", query, project)
    except Exception as exc:
        return f"Memory search error (sqlite fallback): {exc}"


def remember_context(
    project: str,
    title: str,
    content: str,
    domain: str = "architecture",
    module: Optional[str] = None,
    tags: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    status: str = "active",
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 1] Persist architectural knowledge, decisions, or contracts."""
    cfg = settings or XenoniteSettings.load()
    tag_list = list(tags or [])
    file_list = list(files or [])
    point_id = _deterministic_point_id(project, domain, module, title)
    now_iso = datetime.now(timezone.utc).isoformat()
    formatted_data = _format_memory_blob(
        project=project,
        title=title,
        content=content,
        domain=domain,
        module=module,
        tags=tag_list,
        files=file_list,
        status=status,
    )

    if cfg.memory_backend != "sqlite":
        try:
            ensure_qdrant_collection(cfg)
            vector = _get_embedding(formatted_data, cfg)
            data_hash = hashlib.md5(formatted_data.encode("utf-8")).hexdigest()
            payload = {
                "channel": "xenonite-memory",
                "user_id": cfg.user_id,
                "agent_id": cfg.agent_id,
                "project": project,
                "scope": project,
                "domain": domain,
                "module": module,
                "title": title,
                "tags": tag_list,
                "status": status,
                "file_references": file_list,
                "data": formatted_data,
                "text_lemmatized": formatted_data,
                "hash": data_hash,
                "created_at": now_iso,
                "updated_at": now_iso,
                "attributed_to": "mcp-agent",
            }
            body = {"points": [{"id": point_id, "vector": vector, "payload": payload}]}
            req = urllib.request.Request(
                f"{cfg.qdrant_url}/collections/{cfg.qdrant_collection}/points?wait=true",
                data=json.dumps(body).encode("utf-8"),
                headers=_qdrant_headers(cfg),
                method="PUT",
            )
            with urllib.request.urlopen(req, timeout=8):
                pass
            return f"Saved memory [qdrant+tei] for project '{project}' [{domain}]: '{title}'."
        except Exception as exc:
            if cfg.memory_backend == "qdrant":
                return f"Memory save error (qdrant backend): {exc}"

    try:
        _sqlite_upsert(
            settings=cfg,
            point_id=point_id,
            project=project,
            domain=domain,
            module=module,
            title=title,
            tags=tag_list,
            status=status,
            files=file_list,
            formatted_data=formatted_data,
            now_iso=now_iso,
        )
        return f"Saved memory [sqlite-fts5] for project '{project}' [{domain}]: '{title}'."
    except Exception as exc:
        return f"Memory save error (sqlite fallback): {exc}"


def update_project_progress(
    project: str,
    feature: str,
    status: str,
    note: str,
    files: Optional[List[str]] = None,
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 1] Record real-time milestone or feature progress."""
    return remember_context(
        project=project,
        title=f"Progress Update: {feature}",
        content=note,
        domain="progress",
        module=feature,
        tags=["progress", status, feature],
        files=list(files or []),
        status=status,
        settings=settings,
    )


def list_indexed_projects(settings: Optional[XenoniteSettings] = None) -> str:
    """[LAYER 1] List all projects currently indexed in persistent memory."""
    cfg = settings or XenoniteSettings.load()

    if cfg.memory_backend != "sqlite":
        try:
            ensure_qdrant_collection(cfg)
            req = urllib.request.Request(
                f"{cfg.qdrant_url}/collections/{cfg.qdrant_collection}/points/scroll",
                data=json.dumps({"limit": 250, "with_payload": ["project", "scope", "domain"]}).encode("utf-8"),
                headers=_qdrant_headers(cfg),
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))

            points = res.get("result", {}).get("points", [])
            summary: dict[str, dict[str, Any]] = {}
            for pt in points:
                payload = pt.get("payload", {})
                proj = payload.get("project") or payload.get("scope") or "unscoped"
                dom = payload.get("domain", "general")
                if proj not in summary:
                    summary[proj] = {"count": 0, "domains": set()}
                summary[proj]["count"] += 1
                summary[proj]["domains"].add(dom)
            return _format_project_summary(summary, "qdrant+tei")
        except Exception as exc:
            if cfg.memory_backend == "qdrant":
                return f"Error listing projects (qdrant backend): {exc}"

    try:
        summary = _sqlite_list_projects(cfg)
        return _format_project_summary(summary, "sqlite-fts5")
    except Exception as exc:
        return f"Error listing projects (sqlite fallback): {exc}"


def _format_project_summary(summary: dict[str, dict[str, Any]], backend_label: str) -> str:
    if not summary:
        return f"=== INDEXED PROJECTS [{backend_label}] ===\n(No projects indexed yet)"
    output = [f"=== INDEXED PROJECTS [{backend_label}] ==="]
    for proj, info in sorted(summary.items()):
        domains_list = ", ".join(sorted(info["domains"]))
        output.append(f"- Project: {proj} ({info['count']} entries)")
        output.append(f"  Domains: {domains_list}")
    return "\n".join(output)
