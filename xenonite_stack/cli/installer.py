# -*- coding: utf-8 -*-
"""Safe, non-destructive installer & MCP config generator (`xenonite install`)."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from xenonite_stack.config import get_gemini_config_dir, get_repo_root


HOOK_SESSION_KEY = "xenonite-4layer-session-anchor"
HOOK_GUARD_KEY = "xenonite-4layer-pretool-guard"
MCP_SERVER_KEY = "xenonite-tools"


def build_mcp_server_entry(use_uv: bool = False) -> Dict[str, Any]:
    """Generate a portable MCP server entry pointing to the active environment."""
    repo_root = get_repo_root()
    if use_uv:
        uv_bin = shutil.which("uv") or "uv"
        return {
            "command": uv_bin,
            "args": [
                "run",
                "--directory",
                str(repo_root),
                "python",
                "-m",
                "xenonite_stack.mcp.server",
            ],
            "env": {
                "PYTHONIOENCODING": "utf-8",
            },
        }

    return {
        "command": sys.executable,
        "args": [
            "-m",
            "xenonite_stack.mcp.server",
        ],
        "env": {
            "PYTHONIOENCODING": "utf-8",
        },
    }


def build_hooks_entries() -> Dict[str, Any]:
    """Generate cross-platform Antigravity lifecycle & anti-churn hook entries."""
    py = sys.executable
    session_cmd = f'"{py}" -m xenonite_stack.hooks.session_start'
    guard_cmd = f'"{py}" -m xenonite_stack.hooks.pre_tool_guard'

    return {
        HOOK_SESSION_KEY: {
            "enabled": True,
            "SessionStart": [
                {
                    "type": "command",
                    "command": session_cmd,
                    "timeout": 5,
                }
            ],
            "PreInvocation": [
                {
                    "type": "command",
                    "command": session_cmd,
                    "timeout": 5,
                }
            ],
        },
        HOOK_GUARD_KEY: {
            "enabled": True,
            "PreToolUse": [
                {
                    "matcher": "run_command|read_file|view_file|edit_file|replace_file_content|multi_replace_file_content|write_file|write_to_file",
                    "hooks": [
                        {
                            "type": "command",
                            "command": guard_cmd,
                            "timeout": 5,
                        }
                    ],
                }
            ],
        },
    }


def _backup_if_exists(path: Path) -> None:
    if path.is_file():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_suffix(f"{path.suffix}.{stamp}.bak")
        shutil.copy2(path, backup)


def _read_json_or_empty(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def install_antigravity(
    config_dir: Path | None = None,
    persona: str = "standard",
    use_uv: bool = False,
    enable_hooks: bool = True,
    dry_run: bool = False,
) -> int:
    """Safely merge Xenonite MCP, hooks, rules, and plugin into `~/.gemini/config`."""
    target_dir = (config_dir or get_gemini_config_dir()).resolve()
    repo_root = get_repo_root()
    templates_dir = repo_root / "templates"

    mcp_path = target_dir / "mcp_config.json"
    hooks_path = target_dir / "hooks.json"
    rules_dir = target_dir / "rules"
    plugin_dir = target_dir / "plugins" / "xenonite-core"

    rule_src = (
        templates_dir / "rules" / "mr-robot-persona.md"
        if persona == "mr-robot"
        else templates_dir / "rules" / "xenonite-4layer.md"
    )
    rule_dst = rules_dir / rule_src.name

    mcp_data = _read_json_or_empty(mcp_path)
    mcp_servers = dict(mcp_data.get("mcpServers") or {})
    mcp_servers[MCP_SERVER_KEY] = build_mcp_server_entry(use_uv=use_uv)
    mcp_data["mcpServers"] = mcp_servers

    hooks_data = _read_json_or_empty(hooks_path)
    if enable_hooks:
        hooks_data.update(build_hooks_entries())

    if dry_run:
        print(f"[DRY-RUN] Target directory: {target_dir}")
        print(f"[DRY-RUN] Would update: {mcp_path}")
        print(json.dumps(mcp_data, indent=2))
        if enable_hooks:
            print(f"[DRY-RUN] Would update: {hooks_path}")
            print(json.dumps(hooks_data, indent=2))
        print(f"[DRY-RUN] Would install rule: {rule_dst}")
        print(f"[DRY-RUN] Would install plugin skills to: {plugin_dir}")
        return 0

    target_dir.mkdir(parents=True, exist_ok=True)
    _backup_if_exists(mcp_path)
    _write_json(mcp_path, mcp_data)

    if enable_hooks:
        _backup_if_exists(hooks_path)
        _write_json(hooks_path, hooks_data)

    # Install canonical rule (single source of truth)
    rules_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rule_src, rule_dst)

    # Install lightweight portable plugin skills without duplicating MCP/rules
    plugin_skills_dst = plugin_dir / "skills"
    plugin_skills_src = templates_dir / "skills"
    if plugin_skills_src.is_dir():
        shutil.copytree(plugin_skills_src, plugin_skills_dst, dirs_exist_ok=True)

    _write_json(
        plugin_dir / "plugin.json",
        {
            "name": "xenonite-core",
            "description": "Xenonite 4-Layer Portable Skills (Memory & Sovereign Web Intel)",
        },
    )
    _write_json(plugin_dir / "mcp_config.json", {"mcpServers": {}})
    (plugin_dir / "rules").mkdir(parents=True, exist_ok=True)
    (plugin_dir / "rules" / rule_src.name).write_text(
        f"<!-- Canonical global rule lives at {rule_dst}. Deduplicated to prevent double prompt overhead. -->\n",
        encoding="utf-8",
    )

    print(f"[OK] Installed Xenonite MCP server (`{MCP_SERVER_KEY}`) -> {mcp_path}")
    if enable_hooks:
        print(f"[OK] Installed Anti-Churn Hooks -> {hooks_path}")
    print(f"[OK] Installed 4-Layer Rule ({persona}) -> {rule_dst}")
    print(f"[OK] Installed Portable Skills -> {plugin_skills_dst}")
    print("\nNext step: run `xenonite verify` to validate your setup, then restart your AI IDE.")
    return 0


def uninstall_antigravity(config_dir: Path | None = None) -> int:
    """Cleanly remove Xenonite entries from `~/.gemini/config` without touching other tools."""
    target_dir = (config_dir or get_gemini_config_dir()).resolve()
    mcp_path = target_dir / "mcp_config.json"
    hooks_path = target_dir / "hooks.json"

    if mcp_path.is_file():
        mcp_data = _read_json_or_empty(mcp_path)
        servers = mcp_data.get("mcpServers") or {}
        if MCP_SERVER_KEY in servers:
            _backup_if_exists(mcp_path)
            del servers[MCP_SERVER_KEY]
            mcp_data["mcpServers"] = servers
            _write_json(mcp_path, mcp_data)
            print(f"[OK] Removed `{MCP_SERVER_KEY}` from {mcp_path}")

    if hooks_path.is_file():
        hooks_data = _read_json_or_empty(hooks_path)
        changed = False
        for key in (HOOK_SESSION_KEY, HOOK_GUARD_KEY):
            if key in hooks_data:
                del hooks_data[key]
                changed = True
        if changed:
            _backup_if_exists(hooks_path)
            _write_json(hooks_path, hooks_data)
            print(f"[OK] Removed Xenonite hooks from {hooks_path}")

    for rule_name in ("xenonite-4layer.md", "mr-robot-persona.md"):
        rule_file = target_dir / "rules" / rule_name
        if rule_file.is_file():
            rule_file.unlink()
            print(f"[OK] Removed rule {rule_file}")

    plugin_dir = target_dir / "plugins" / "xenonite-core"
    if plugin_dir.is_dir():
        shutil.rmtree(plugin_dir)
        print(f"[OK] Removed plugin directory {plugin_dir}")

    return 0


def print_mcp_snippet(client: str = "generic", use_uv: bool = False) -> int:
    """Print ready-to-paste MCP JSON snippet for Antigravity, Claude Desktop, Cursor, or Windsurf."""
    snippet = {"mcpServers": {MCP_SERVER_KEY: build_mcp_server_entry(use_uv=use_uv)}}
    if client == "vscode":
        snippet = {"servers": {MCP_SERVER_KEY: build_mcp_server_entry(use_uv=use_uv)}}
    print(json.dumps(snippet, indent=2, ensure_ascii=False))
    return 0
