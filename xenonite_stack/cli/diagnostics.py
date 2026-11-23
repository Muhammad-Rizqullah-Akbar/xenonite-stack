# -*- coding: utf-8 -*-
"""Pre-Flight System Audit (`xenonite check`)."""

from __future__ import annotations

import importlib.util
import json
import platform
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Tuple

from xenonite_stack import __version__
from xenonite_stack.config import XenoniteSettings, get_gemini_config_dir, resolve_binary


def _probe_http(url: str, timeout: float = 2.0) -> Tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Xenonite-Check/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except Exception as exc:
        return False, str(exc).splitlines()[0][:60]


def _check_mcp_sdk() -> bool:
    return importlib.util.find_spec("mcp") is not None


def _check_antigravity_install(config_dir: Path) -> Tuple[bool, bool, bool]:
    mcp_ok = False
    hooks_ok = False
    rule_ok = False

    mcp_file = config_dir / "mcp_config.json"
    if mcp_file.is_file():
        try:
            data = json.loads(mcp_file.read_text(encoding="utf-8"))
            mcp_ok = "xenonite-tools" in (data.get("mcpServers") or {})
        except Exception:
            pass

    hooks_file = config_dir / "hooks.json"
    if hooks_file.is_file():
        try:
            data = json.loads(hooks_file.read_text(encoding="utf-8"))
            hooks_ok = (
                "xenonite-4layer-session-anchor" in data
                and "xenonite-4layer-pretool-guard" in data
            )
        except Exception:
            pass

    rules_dir = config_dir / "rules"
    if rules_dir.is_dir():
        rule_ok = any(
            (rules_dir / name).is_file()
            for name in ("xenonite-4layer.md", "mr-robot-xenonite.md")
        )

    return mcp_ok, hooks_ok, rule_ok


def run_diagnostics(config_dir: Path | None = None) -> int:
    """Print a structured Pre-Flight System Audit and return 0 if core is healthy."""
    cfg = XenoniteSettings.load()
    target_cfg = config_dir or get_gemini_config_dir()

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    mcp_sdk_ok = _check_mcp_sdk()

    uv_bin = shutil.which("uv")
    rg_bin = resolve_binary(cfg.rg_bin_override, "rg")
    sg_bin = resolve_binary(cfg.sg_bin_override, "sg", "ast-grep")
    madge_bin = resolve_binary(cfg.madge_bin_override, "madge")
    docker_bin = shutil.which("docker")

    qdrant_ok, qdrant_msg = _probe_http(f"{cfg.qdrant_url}/collections")
    tei_base = cfg.tei_url.rsplit("/embed", 1)[0]
    tei_ok, tei_msg = _probe_http(f"{tei_base}/health")
    searxng_ok, searxng_msg = _probe_http(f"{cfg.searxng_url}/")
    crawl_ok, crawl_msg = _probe_http(f"{cfg.crawl4ai_url}/health")

    mcp_installed, hooks_installed, rule_installed = _check_antigravity_install(target_cfg)

    print("=" * 80)
    print(f"            XENONITE STACK v{__version__} - PRE-FLIGHT SYSTEM AUDIT")
    print("=" * 80)
    print()
    print("[1] CORE PYTHON RUNTIME & MCP SDK:")
    print(f"    |- [{'OK' if py_ok else 'FAIL'}] Python {py_ver} ({platform.system()} {platform.machine()})")
    print(f"    |- [{'OK' if mcp_sdk_ok else 'FAIL'}] MCP Python SDK (`mcp`) : {'installed' if mcp_sdk_ok else 'MISSING - run pip install -e .'}")
    print(f"    +- [{'OK' if uv_bin else 'INFO'}] uv (optional runner)  : {uv_bin or 'not found (venv python will be used)'}")
    print()
    print("[2] LAYER 3 LOCAL CODE INTELLIGENCE BINARIES:")
    print(f"    |- [{'OK' if rg_bin else 'WARN'}] ripgrep (`rg`)        : {rg_bin or 'not found (Python regex fallback active)'}")
    print(f"    |- [{'OK' if sg_bin else 'WARN'}] ast-grep (`sg`)       : {sg_bin or 'not found (optional: npm i -g @ast-grep/cli)'}")
    print(f"    +- [{'OK' if madge_bin else 'WARN'}] madge (`madge`)       : {madge_bin or 'not found (optional: npm i -g madge)'}")
    print()
    print(f"[3] LAYER 1 PERSISTENT MEMORY (mode={cfg.memory_backend}):")
    print(f"    |- [{'OK' if qdrant_ok else 'INFO'}] Qdrant ({cfg.qdrant_url}) : {qdrant_msg if qdrant_ok else 'offline'}")
    print(f"    |- [{'OK' if tei_ok else 'INFO'}] TEI Embedder ({tei_base}) : {tei_msg if tei_ok else 'offline'}")
    print(f"    +- [OK] SQLite FTS5 Fallback  : {cfg.sqlite_path}")
    print()
    print("[4] LAYER 2 SOVEREIGN WEB INTELLIGENCE (OPTIONAL DOCKER):")
    print(f"    |- [{'OK' if docker_bin else 'INFO'}] Docker CLI            : {docker_bin or 'not installed (Lite mode still works)'}")
    print(f"    |- [{'OK' if searxng_ok else 'INFO'}] SearXNG ({cfg.searxng_url}) : {searxng_msg if searxng_ok else 'offline'}")
    print(f"    +- [{'OK' if crawl_ok else 'INFO'}] Crawl4AI ({cfg.crawl4ai_url}) : {crawl_msg if crawl_ok else 'offline'}")
    print()
    print(f"[5] ANTIGRAVITY / GEMINI INTEGRATION ({target_cfg}):")
    print(f"    |- [{'OK' if mcp_installed else 'WARN'}] Global MCP (`xenonite-tools`)  : {'registered' if mcp_installed else 'not installed (run: xenonite install)'}")
    print(f"    |- [{'OK' if hooks_installed else 'WARN'}] Anti-Churn Hooks (`hooks.json`): {'active' if hooks_installed else 'not installed (run: xenonite install)'}")
    print(f"    +- [{'OK' if rule_installed else 'WARN'}] 4-Layer Rules (`rules/*.md`)   : {'present' if rule_installed else 'not installed (run: xenonite install)'}")
    print("=" * 80)

    if qdrant_ok and tei_ok and searxng_ok and crawl_ok:
        tier = "FULL SOVEREIGN STACK (L1 Vector + L2 Web Intel + L3 Code Intel + L4 Atomic)"
    elif qdrant_ok and tei_ok:
        tier = "MEMORY + CODE STACK (L1 Vector + L3 Code Intel + L4 Atomic)"
    else:
        tier = "PORTABLE LITE STACK (L1 SQLite FTS5 + L3 Code Intel + L4 Atomic)"
    print(f"ACTIVE PROFILE: {tier}")
    print("=" * 80)

    return 0 if (py_ok and mcp_sdk_ok) else 1
