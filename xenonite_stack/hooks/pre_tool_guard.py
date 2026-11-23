# -*- coding: utf-8 -*-
"""Xenonite Global PreToolUse Mechanical Guardrail Hook.

Deterministically enforces Layer 3 & Layer 4 Anti-Churn discipline across
Windows, macOS, and Linux:
1. Blocks blind recursive filesystem scans via `run_command` and redirects to
   MCP `xenonite-tools` (`get_project_structure` / `ripgrep_search`).
2. Blocks repetitive single-file `read_file` / `view_file` churn within the
   configured step/time window and redirects to `read_targeted_snippets`.
3. Blocks repetitive single-file `edit_file` / overwrite churn within the
   configured step/time window and redirects to atomic `apply_multi_patch`.

Fail-open: always returns `{"decision": "allow"}` on unexpected input or error.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time


MEDIA_BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".ico",
    ".pdf", ".mp3", ".mp4", ".wav", ".ogg", ".webm", ".avi", ".mov",
}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


CHURN_STEP_WINDOW = _env_int("XENONITE_CHURN_STEP_WINDOW", 4)
CHURN_TIME_WINDOW_SEC = _env_float("XENONITE_CHURN_TIME_WINDOW_SEC", 20.0)

BLIND_SCAN_PATTERNS = [
    re.compile(r"(?i)\b(?:Get-ChildItem|gci|ls)\b[^\n|;]*\s-Recurse\b"),
    re.compile(r"(?i)\bdir\s+/s\b"),
    re.compile(r"(?i)\bfindstr\s+/s\b"),
    re.compile(r"(?i)\bgrep\s+-[a-zA-Z]*r[a-zA-Z]*\b"),
    re.compile(r"(?i)\bfind\s+\S+\s+-name\b"),
    re.compile(r"\.rglob\s*\("),
    re.compile(r"\bos\.walk\s*\("),
]


def _norm_path(path: str) -> str:
    return path.replace("\\", "/").lower()


def _is_brain_artifact(path: str) -> bool:
    return "/.gemini/antigravity/brain/" in _norm_path(path)


def _is_mcp_schema(path: str) -> bool:
    norm = _norm_path(path)
    return "/.gemini/antigravity/mcp/" in norm and norm.endswith(".json")


def _state_path(conv_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", conv_id or "default")[:64]
    return os.path.join(tempfile.gettempdir(), f"xenonite_antichurn_{safe}.json")


def _load_state(conv_id: str) -> dict:
    try:
        with open(_state_path(conv_id), "r", encoding="utf-8") as fp:
            data = json.load(fp)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(conv_id: str, state: dict) -> None:
    try:
        with open(_state_path(conv_id), "w", encoding="utf-8") as fp:
            json.dump(state, fp)
    except Exception:
        pass


def _is_repetitive(state: dict, key: str, step_idx, now: float) -> bool:
    last_step = state.get(f"{key}_step")
    last_ts = state.get(f"{key}_ts")
    if step_idx is not None and last_step is not None:
        try:
            diff = int(step_idx) - int(last_step)
            return 0 <= diff <= CHURN_STEP_WINDOW
        except (TypeError, ValueError):
            pass
    if last_ts is not None:
        try:
            return (now - float(last_ts)) <= CHURN_TIME_WINDOW_SEC
        except (TypeError, ValueError):
            pass
    return False


def _record(conv_id: str, state: dict, key: str, step_idx, now: float) -> None:
    if step_idx is not None:
        state[f"{key}_step"] = step_idx
    state[f"{key}_ts"] = now
    _save_state(conv_id, state)


def _allow() -> dict:
    return {"decision": "allow"}


def _deny(reason: str) -> dict:
    return {"decision": "deny", "reason": reason}


def _check_run_command(args: dict) -> dict:
    cmd = str(args.get("CommandLine") or args.get("command") or "")
    if not cmd:
        return _allow()

    for pat in BLIND_SCAN_PATTERNS:
        if pat.search(cmd):
            return _deny(
                "XENONITE LAYER 3 GUARDRAIL: Blind recursive scan via run_command is blocked. "
                "Use call_mcp_tool(ServerName='xenonite-tools', ToolName='get_project_structure' "
                "or 'ripgrep_search') for token-efficient workspace mapping and search."
            )
    return _allow()


def _check_read_file(args: dict, conv_id: str, step_idx) -> dict:
    path = str(args.get("Path") or args.get("AbsolutePath") or args.get("path") or "")
    if not path:
        return _allow()

    base = os.path.basename(path)
    _, ext = os.path.splitext(path.lower())
    if ext in MEDIA_BINARY_EXTENSIONS or base == "SKILL.md" or _is_mcp_schema(path):
        return _allow()

    now = time.time()
    state = _load_state(conv_id)
    if _is_repetitive(state, "read", step_idx, now):
        return _deny(
            "XENONITE ANTI-CHURN GUARDRAIL: Repetitive single-file read_file calls detected. "
            "Batch all target line slices into 1 call via call_mcp_tool(ServerName='xenonite-tools', "
            "ToolName='read_targeted_snippets') after locating targets with 'ripgrep_search' / 'get_code_outline'."
        )

    _record(conv_id, state, "read", step_idx, now)
    return _allow()


def _check_edit_or_overwrite(args: dict, conv_id: str, step_idx, is_write: bool) -> dict:
    path = str(args.get("Path") or args.get("TargetFile") or args.get("path") or "")
    if path and _is_brain_artifact(path):
        return _allow()
    if is_write and (not path or not os.path.isfile(path)):
        return _allow()

    now = time.time()
    state = _load_state(conv_id)
    if _is_repetitive(state, "edit", step_idx, now):
        return _deny(
            "XENONITE ANTI-CHURN GUARDRAIL: Repetitive single-file edits detected. "
            "Combine all file modifications into 1 atomic call via "
            "call_mcp_tool(ServerName='xenonite-tools', ToolName='apply_multi_patch')."
        )

    _record(conv_id, state, "edit", step_idx, now)
    return _allow()


def evaluate_tool_call(data: dict) -> dict:
    """Evaluate a PreToolUse hook payload and return allow/deny decision."""
    conv_id = str(data.get("conversationId") or "default")
    step_idx = data.get("stepIdx")
    tool_call = data.get("toolCall") or {}
    name = str(tool_call.get("name") or "").lower()
    args = tool_call.get("args") or {}

    if name == "run_command":
        return _check_run_command(args)
    if name in ("read_file", "view_file"):
        return _check_read_file(args, conv_id, step_idx)
    if name in ("edit_file", "replace_file_content", "multi_replace_file_content"):
        return _check_edit_or_overwrite(args, conv_id, step_idx, is_write=False)
    if name in ("write_file", "write_to_file"):
        return _check_edit_or_overwrite(args, conv_id, step_idx, is_write=True)
    return _allow()


def main() -> None:
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.stdout.write(json.dumps(_allow()))
            return
        data = json.loads(raw)
        decision = evaluate_tool_call(data if isinstance(data, dict) else {})
        sys.stdout.write(json.dumps(decision, ensure_ascii=False))
    except Exception:
        sys.stdout.write(json.dumps(_allow()))


if __name__ == "__main__":
    main()
