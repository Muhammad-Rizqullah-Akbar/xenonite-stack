# -*- coding: utf-8 -*-
"""Unified cross-platform configuration loader for Xenonite Stack.

Loads environment variables with optional `.env` file support (pure stdlib,
zero mandatory third-party parser dependency).
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _parse_dotenv(env_path: Path) -> dict[str, str]:
    """Parse KEY=VALUE pairs from a `.env` file without mutating existing env."""
    parsed: dict[str, str] = {}
    if not env_path.is_file():
        return parsed
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            if key:
                parsed[key] = val
    except OSError:
        return {}
    return parsed


def load_env_defaults() -> None:
    """Populate `os.environ` from `~/.xenonite/.env` and repo `.env` if unset."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path.home() / ".xenonite" / ".env",
    ]
    for env_path in candidates:
        for key, val in _parse_dotenv(env_path).items():
            if key not in os.environ and val != "":
                os.environ[key] = val


def _env_str(name: str, default: str) -> str:
    val = os.environ.get(name)
    return val.strip() if val is not None and val.strip() != "" else default


def _env_int(name: str, default: int) -> int:
    val = os.environ.get(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    val = os.environ.get(name)
    if val is None or val.strip() == "":
        return default
    try:
        return float(val.strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class XenoniteSettings:
    """Immutable runtime settings resolved from environment variables."""

    memory_backend: str
    qdrant_url: str
    tei_url: str
    qdrant_collection: str
    qdrant_vector_size: int
    qdrant_api_key: str
    sqlite_path: Path
    user_id: str
    agent_id: str
    searxng_url: str
    crawl4ai_url: str
    crawl4ai_token: str
    crawl4ai_max_chars: int
    rg_bin_override: str
    sg_bin_override: str
    madge_bin_override: str
    churn_step_window: int
    churn_time_window_sec: float

    @classmethod
    def load(cls) -> "XenoniteSettings":
        load_env_defaults()
        default_sqlite = Path.home() / ".xenonite" / "memory.db"
        sqlite_raw = os.environ.get("XENONITE_SQLITE_PATH", "").strip()
        sqlite_path = Path(sqlite_raw).expanduser() if sqlite_raw else default_sqlite

        return cls(
            memory_backend=_env_str("XENONITE_MEMORY_BACKEND", "auto").lower(),
            qdrant_url=_env_str("XENONITE_QDRANT_URL", "http://127.0.0.1:6333").rstrip("/"),
            tei_url=_env_str("XENONITE_TEI_URL", "http://127.0.0.1:8080/embed"),
            qdrant_collection=_env_str("XENONITE_QDRANT_COLLECTION", "mem0"),
            qdrant_vector_size=_env_int("XENONITE_QDRANT_VECTOR_SIZE", 1024),
            qdrant_api_key=os.environ.get("XENONITE_QDRANT_API_KEY", "").strip(),
            sqlite_path=sqlite_path,
            user_id=_env_str("XENONITE_USER_ID", "developer"),
            agent_id=_env_str("XENONITE_AGENT_ID", "xenonite-nucleus"),
            searxng_url=_env_str("XENONITE_SEARXNG_URL", "http://127.0.0.1:8888").rstrip("/"),
            crawl4ai_url=_env_str("XENONITE_CRAWL4AI_URL", "http://127.0.0.1:11235").rstrip("/"),
            crawl4ai_token=os.environ.get("XENONITE_CRAWL4AI_TOKEN", "").strip(),
            crawl4ai_max_chars=_env_int("XENONITE_CRAWL4AI_MAX_CHARS", 6000),
            rg_bin_override=os.environ.get("XENONITE_RG_BIN", "").strip(),
            sg_bin_override=os.environ.get("XENONITE_SG_BIN", "").strip(),
            madge_bin_override=os.environ.get("XENONITE_MADGE_BIN", "").strip(),
            churn_step_window=_env_int("XENONITE_CHURN_STEP_WINDOW", 4),
            churn_time_window_sec=_env_float("XENONITE_CHURN_TIME_WINDOW_SEC", 20.0),
        )


def resolve_binary(override: str, *names: str) -> Optional[str]:
    """Resolve an executable path from explicit override or system PATH."""
    if override and Path(override).is_file():
        return override
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def get_gemini_config_dir() -> Path:
    """Return the cross-platform Antigravity/Gemini global config directory."""
    env_dir = os.environ.get("XENONITE_GEMINI_CONFIG_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return (Path.home() / ".gemini" / "config").resolve()


def get_repo_root() -> Path:
    """Return the root directory of the installed xenonite-stack repository."""
    return Path(__file__).resolve().parent.parent
