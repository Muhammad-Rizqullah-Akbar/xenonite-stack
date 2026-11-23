# -*- coding: utf-8 -*-
"""Main CLI router for `xenonite`."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from xenonite_stack import __version__
from xenonite_stack.cli.diagnostics import run_diagnostics
from xenonite_stack.cli.installer import (
    install_antigravity,
    print_mcp_snippet,
    uninstall_antigravity,
)
from xenonite_stack.cli.verifier import run_verify
from xenonite_stack.config import XenoniteSettings, get_repo_root
from xenonite_stack.mcp import layer1_memory
from xenonite_stack.mcp.server import main as run_mcp_server


def _run_docker_command(action: str, profile: str, gpu: bool) -> int:
    docker_bin = shutil.which("docker")
    if not docker_bin:
        print("[ERROR] Docker CLI not found in PATH. Install Docker Desktop or Docker Engine first.")
        return 1

    repo_root = get_repo_root()
    compose_base = repo_root / "docker" / "docker-compose.yml"
    compose_gpu = repo_root / "docker" / "docker-compose.gpu.yml"

    cmd = [docker_bin, "compose", "-f", str(compose_base)]
    if gpu and compose_gpu.is_file():
        cmd.extend(["-f", str(compose_gpu)])

    if profile == "memory":
        cmd.extend(["--profile", "memory"])
    elif profile == "intel":
        cmd.extend(["--profile", "intel"])
    else:
        cmd.extend(["--profile", "memory", "--profile", "intel"])

    if action == "up":
        cmd.extend(["up", "-d"])
    elif action == "down":
        cmd.append("down")
    elif action == "status":
        cmd.append("ps")
    elif action == "logs":
        cmd.extend(["logs", "--tail", "80"])
    else:
        print(f"[ERROR] Unknown docker action: {action}")
        return 1

    print(f"[*] Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(repo_root))
    return res.returncode


def _run_memory_command(action: str) -> int:
    cfg = XenoniteSettings.load()
    if action == "init-qdrant":
        try:
            layer1_memory.ensure_qdrant_collection(cfg)
            print(
                f"[OK] Qdrant collection '{cfg.qdrant_collection}' "
                f"(size={cfg.qdrant_vector_size}, Cosine) is ready at {cfg.qdrant_url}"
            )
            return 0
        except Exception as exc:
            print(f"[ERROR] Failed to initialize Qdrant collection: {exc}")
            return 1
    if action == "status":
        print(layer1_memory.list_indexed_projects(settings=cfg))
        return 0
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xenonite",
        description="Xenonite 4-Layer Self-Hosted Autonomous Engineering MCP Stack",
    )
    parser.add_argument("--version", action="version", version=f"xenonite-stack {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = sub.add_parser("check", help="Run Pre-Flight System Audit across all 4 layers")
    p_check.add_argument("--config-dir", type=Path, default=None, help="Custom Gemini/Antigravity config dir")

    # install
    p_install = sub.add_parser("install", help="Install MCP, Anti-Churn hooks, rules, and skills into Antigravity")
    p_install.add_argument("--persona", choices=["standard", "mr-robot"], default="standard", help="Rule style")
    p_install.add_argument("--config-dir", type=Path, default=None, help="Custom Gemini/Antigravity config dir")
    p_install.add_argument("--use-uv", action="store_true", help="Run MCP via `uv run` instead of current Python")
    p_install.add_argument("--no-hooks", action="store_true", help="Skip installing PreToolUse/SessionStart hooks")
    p_install.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")

    # uninstall
    p_un = sub.add_parser("uninstall", help="Cleanly remove Xenonite entries from Antigravity config")
    p_un.add_argument("--config-dir", type=Path, default=None, help="Custom Gemini/Antigravity config dir")

    # print-mcp
    p_print = sub.add_parser("print-mcp", help="Print MCP JSON snippet for Claude Desktop, Cursor, Windsurf, or VS Code")
    p_print.add_argument("--client", choices=["generic", "vscode"], default="generic")
    p_print.add_argument("--use-uv", action="store_true")

    # serve
    sub.add_parser("serve", help="Start the `xenonite-tools` stdio MCP server")

    # verify
    p_verify = sub.add_parser("verify", help="Run silent-filtered security, hooks, and MCP verification suite")
    p_verify.add_argument("--mode", choices=["security", "hooks", "mcp", "all"], default="all")
    p_verify.add_argument("--config-dir", type=Path, default=None, help="Optional installed config dir to audit")

    # docker
    p_docker = sub.add_parser("docker", help="Manage self-hosted L1/L2 Docker services (Qdrant, TEI, SearXNG, Crawl4AI)")
    p_docker.add_argument("action", choices=["up", "down", "status", "logs"])
    p_docker.add_argument("profile", nargs="?", choices=["full", "memory", "intel"], default="full")
    p_docker.add_argument("--gpu", action="store_true", help="Enable NVIDIA CUDA GPU acceleration for TEI")

    # memory
    p_mem = sub.add_parser("memory", help="Inspect or initialize Layer 1 persistent memory")
    p_mem.add_argument("action", choices=["status", "init-qdrant"])

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return run_diagnostics(config_dir=args.config_dir)
    if args.command == "install":
        return install_antigravity(
            config_dir=args.config_dir,
            persona=args.persona,
            use_uv=args.use_uv,
            enable_hooks=not args.no_hooks,
            dry_run=args.dry_run,
        )
    if args.command == "uninstall":
        return uninstall_antigravity(config_dir=args.config_dir)
    if args.command == "print-mcp":
        return print_mcp_snippet(client=args.client, use_uv=args.use_uv)
    if args.command == "serve":
        run_mcp_server()
        return 0
    if args.command == "verify":
        return run_verify(mode=args.mode, config_dir=args.config_dir)
    if args.command == "docker":
        return _run_docker_command(action=args.action, profile=args.profile, gpu=args.gpu)
    if args.command == "memory":
        return _run_memory_command(action=args.action)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
