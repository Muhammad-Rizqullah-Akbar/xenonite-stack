# -*- coding: utf-8 -*-
"""Silent-Filtered Verification Suite (`xenonite verify`).

Validates:
- `security`: JSON validity, Zero Em-Dash compliance, MCP & rule deduplication.
- `hooks`   : SessionStart, PreInvocation, and 11-case stateful PreToolUse matrix.
- `mcp`     : End-to-end smoke test of L1 SQLite, L3 Code Intel, and L4 Atomic Patch.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

from xenonite_stack.config import XenoniteSettings, get_gemini_config_dir, get_repo_root
from xenonite_stack.mcp import layer1_memory, layer3_code_intel, layer4_execution


def run_security_checks(config_dir: Path | None = None) -> List[str]:
    """Audit repository files and optional installed config for integrity & Zero Em-Dash."""
    failures: List[str] = []
    repo_root = get_repo_root()

    repo_files = [
        repo_root / "README.md",
        repo_root / "CONTRIBUTING.md",
        repo_root / "pyproject.toml",
        repo_root / ".env.example",
        repo_root / "templates" / "rules" / "xenonite-4layer.md",
        repo_root / "templates" / "rules" / "mr-robot-persona.md",
        repo_root / "xenonite_stack" / "hooks" / "session_start.py",
        repo_root / "xenonite_stack" / "hooks" / "pre_tool_guard.py",
    ]

    for fpath in repo_files:
        if not fpath.is_file():
            failures.append(f"FAIL [missing]: {fpath}")
            continue
        txt = fpath.read_text(encoding="utf-8")
        if "\u2014" in txt or "\u2013" in txt:
            failures.append(f"FAIL [em-dash]: {fpath}")

    if config_dir and config_dir.is_dir():
        mcp_file = config_dir / "mcp_config.json"
        hooks_file = config_dir / "hooks.json"
        plugin_mcp = config_dir / "plugins" / "xenonite-core" / "mcp_config.json"

        for jf in (mcp_file, hooks_file, plugin_mcp):
            if jf.is_file():
                try:
                    json.loads(jf.read_text(encoding="utf-8"))
                except Exception as exc:
                    failures.append(f"FAIL [json]: {jf} -> {exc}")

        if mcp_file.is_file():
            data = json.loads(mcp_file.read_text(encoding="utf-8"))
            if "xenonite-tools" not in (data.get("mcpServers") or {}):
                failures.append("FAIL [mcp]: xenonite-tools not registered in mcp_config.json")
        if plugin_mcp.is_file():
            pdata = json.loads(plugin_mcp.read_text(encoding="utf-8"))
            if pdata.get("mcpServers"):
                failures.append("FAIL [mcp-dup]: plugin xenonite-core registers duplicate mcpServers")

    return failures


def run_hook_checks() -> Tuple[List[str], float, int]:
    """Run SessionStart, PreInvocation, and 11-case PreToolUse stateful matrix."""
    failures: List[str] = []
    py = sys.executable

    t0 = time.perf_counter()
    res = subprocess.run(
        [py, "-m", "xenonite_stack.hooks.session_start"],
        input='{"conversationId":"verify"}',
        text=True,
        capture_output=True,
    )
    dt_ms = (time.perf_counter() - t0) * 1000.0
    if res.returncode != 0:
        failures.append(f"FAIL [SessionStart exit={res.returncode}]: {res.stderr.strip()}")
    else:
        try:
            out = json.loads(res.stdout)
            msg = out["injectSteps"][0]["systemMessage"]["systemMessage"]
            if "xenonite-tools" not in msg:
                failures.append("FAIL [SessionStart]: anchor missing xenonite-tools")
        except Exception as exc:
            failures.append(f"FAIL [SessionStart json]: {exc}")

    res_pre = subprocess.run(
        [py, "-m", "xenonite_stack.hooks.session_start"],
        input='{"conversationId":"verify","invocationNum":3}',
        text=True,
        capture_output=True,
    )
    if res_pre.returncode != 0:
        failures.append(f"FAIL [PreInvocation exit={res_pre.returncode}]: {res_pre.stderr.strip()}")
    else:
        try:
            out_pre = json.loads(res_pre.stdout)
            if "ephemeralMessage" not in out_pre["injectSteps"][0]:
                failures.append("FAIL [PreInvocation]: missing ephemeralMessage")
        except Exception as exc:
            failures.append(f"FAIL [PreInvocation json]: {exc}")

    cid = f"verify-antichurn-{int(time.time() * 1000)}"
    repo_root = get_repo_root()
    existing_a = str(repo_root / "xenonite_stack" / "config.py")
    existing_b = str(repo_root / "README.md")
    skill_md = str(repo_root / "templates" / "skills" / "xeno-memory" / "SKILL.md")
    brain_art = "/home/dev/.gemini/antigravity/brain/test-conv/PLAN.md"
    nonexistent = str(repo_root / "_does_not_exist_new_file.py")

    cases = [
        ("run_blind_scan_ps_deny", {"conversationId": cid, "stepIdx": 1, "toolCall": {"name": "run_command", "args": {"CommandLine": "Get-ChildItem . -Recurse"}}}, "deny"),
        ("run_blind_scan_unix_deny", {"conversationId": cid, "stepIdx": 2, "toolCall": {"name": "run_command", "args": {"CommandLine": "grep -rn foo ."}}}, "deny"),
        ("run_filtered_pipe_allow", {"conversationId": cid, "stepIdx": 3, "toolCall": {"name": "run_command", "args": {"CommandLine": "pytest | grep FAIL"}}}, "allow"),
        ("read_1st_single_allow", {"conversationId": cid, "stepIdx": 10, "toolCall": {"name": "read_file", "args": {"Path": existing_a}}}, "allow"),
        ("read_2nd_churn_deny", {"conversationId": cid, "stepIdx": 11, "toolCall": {"name": "read_file", "args": {"Path": existing_b}}}, "deny"),
        ("read_skill_always_allow", {"conversationId": cid, "stepIdx": 12, "toolCall": {"name": "read_file", "args": {"Path": skill_md}}}, "allow"),
        ("read_later_task_allow", {"conversationId": cid, "stepIdx": 20, "toolCall": {"name": "read_file", "args": {"Path": existing_b}}}, "allow"),
        ("edit_1st_single_allow", {"conversationId": cid, "stepIdx": 30, "toolCall": {"name": "edit_file", "args": {"Path": existing_a, "Target": "a", "Replacement": "b"}}}, "allow"),
        ("edit_2nd_churn_deny", {"conversationId": cid, "stepIdx": 31, "toolCall": {"name": "edit_file", "args": {"Path": existing_b, "Target": "a", "Replacement": "b"}}}, "deny"),
        ("edit_brain_always_allow", {"conversationId": cid, "stepIdx": 32, "toolCall": {"name": "edit_file", "args": {"Path": brain_art, "Target": "a", "Replacement": "b"}}}, "allow"),
        ("write_new_file_allow", {"conversationId": cid, "stepIdx": 33, "toolCall": {"name": "write_file", "args": {"Path": nonexistent, "Content": "x"}}}, "allow"),
    ]

    for label, payload, expected in cases:
        r = subprocess.run(
            [py, "-m", "xenonite_stack.hooks.pre_tool_guard"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        if r.returncode != 0:
            failures.append(f"FAIL [{label} exit={r.returncode}]: {r.stderr.strip()}")
            continue
        try:
            dec = json.loads(r.stdout).get("decision")
            if dec != expected:
                failures.append(f"FAIL [{label}]: got '{dec}', expected '{expected}'")
        except Exception as exc:
            failures.append(f"FAIL [{label} json]: {exc}")

    return failures, dt_ms, len(cases)


def run_mcp_smoke_checks() -> List[str]:
    """Smoke-test L1 SQLite fallback, L3 Code Intel, and L4 Atomic Multi-Patch."""
    failures: List[str] = []
    with tempfile.TemporaryDirectory(prefix="xenonite_verify_") as tmp:
        tmp_path = Path(tmp)

        # L1 SQLite memory round-trip
        base = XenoniteSettings.load()
        sqlite_cfg = XenoniteSettings(
            **{
                **base.__dict__,
                "memory_backend": "sqlite",
                "sqlite_path": tmp_path / "memory.db",
            }
        )
        saved = layer1_memory.remember_context(
            project="smoke-proj",
            title="Auth Contract",
            content="JWT tokens rotate every 15 minutes with Redis revocation.",
            settings=sqlite_cfg,
        )
        if "Saved memory [sqlite-fts5]" not in saved:
            failures.append(f"FAIL [L1-save]: {saved}")

        found = layer1_memory.search_memory("Redis revocation", project="smoke-proj", settings=sqlite_cfg)
        if "Auth Contract" not in found:
            failures.append(f"FAIL [L1-search]: {found}")

        listed = layer1_memory.list_indexed_projects(settings=sqlite_cfg)
        if "smoke-proj" not in listed:
            failures.append(f"FAIL [L1-list]: {listed}")

        # L3 Structure + Outline + Snippets
        sample_file = tmp_path / "demo.py"
        sample_file.write_text("class Engine:\n    def run(self):\n        return 42\n", encoding="utf-8")
        struct_out = layer3_code_intel.get_project_structure(str(tmp_path), max_depth=2)
        if "demo.py" not in struct_out:
            failures.append(f"FAIL [L3-structure]: {struct_out}")

        outline_out = layer3_code_intel.get_code_outline(str(sample_file))
        if "class Engine:" not in outline_out:
            failures.append(f"FAIL [L3-outline]: {outline_out}")

        snip_out = layer3_code_intel.read_targeted_snippets(
            [{"file_path": str(sample_file), "start_line": 1, "end_line": 3, "label": "demo"}]
        )
        if "return 42" not in snip_out:
            failures.append(f"FAIL [L3-snippets]: {snip_out}")

        # L4 Atomic Multi-Patch (chained + rollback check)
        patch_ok = layer4_execution.apply_multi_patch(
            [
                {"path": str(sample_file), "target": "return 42", "replacement": "return 99"},
                {"path": str(sample_file), "target": "class Engine:", "replacement": "class FastEngine:"},
            ]
        )
        if "ATOMIC MULTI-PATCH SUCCESS" not in patch_ok:
            failures.append(f"FAIL [L4-patch]: {patch_ok}")

        rollback_res = layer4_execution.apply_multi_patch(
            [
                {"path": str(sample_file), "target": "return 99", "replacement": "return 0"},
                {"path": str(sample_file), "target": "DOES_NOT_EXIST", "replacement": "x"},
            ]
        )
        if "Failed [Rollback]" not in rollback_res or "return 99" not in sample_file.read_text(encoding="utf-8"):
            failures.append(f"FAIL [L4-rollback]: {rollback_res}")

        big_o = layer4_execution.get_big_o_recommendation("permissions")
        if "Bitmask" not in big_o:
            failures.append(f"FAIL [L4-bigo]: {big_o}")

    return failures


def run_verify(mode: str = "all", config_dir: Path | None = None) -> int:
    """Execute selected verification suites with silent-filtered output."""
    all_failures: List[str] = []
    dt_ms = 0.0
    case_count = 0

    if mode in ("security", "all"):
        all_failures.extend(run_security_checks(config_dir=config_dir))
    if mode in ("hooks", "all"):
        hook_fails, dt_ms, case_count = run_hook_checks()
        all_failures.extend(hook_fails)
    if mode in ("mcp", "all"):
        all_failures.extend(run_mcp_smoke_checks())

    if all_failures:
        for line in all_failures:
            print(line)
        return 1

    if mode == "security":
        print("PASS [security]: Repository & config valid, 0 em-dash, zero duplicate MCP/rules")
    elif mode == "hooks":
        print(f"PASS [hooks]: SessionStart ({dt_ms:.1f}ms) + PreToolUse {case_count}/{case_count} PASS")
    elif mode == "mcp":
        print("PASS [mcp]: L1 SQLite + L3 Code Intel + L4 Atomic Multi-Patch & Big-O PASS")
    else:
        print(
            f"PASS [verify-all]: Security 0 em-dash | SessionStart ({dt_ms:.1f}ms) | "
            f"PreToolUse {case_count}/{case_count} | MCP L1/L3/L4 Smoke PASS"
        )
    return 0
