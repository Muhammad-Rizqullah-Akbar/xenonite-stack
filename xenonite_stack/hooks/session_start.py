# -*- coding: utf-8 -*-
"""Xenonite Global SessionStart & PreInvocation Lifecycle Hook.

Injects a compact 4-Layer Native MCP operational anchor on every new session
and invocation across all models and tabs. Fail-open: never blocks a session.
"""

from __future__ import annotations

import json
import sys


SESSION_ANCHOR = (
    "[XENONITE 4-LAYER ANTI-CHURN ACTIVE] "
    "Global MCP server 'xenonite-tools' is active (16 tools, inline signatures in rules). "
    "Minimum Turn, Maximum Result discipline: "
    "(1) ON-DEMAND: do not force tool calls for pure conceptual Q&A; "
    "(2) L1: call search_memory once before exploring a project and sync major changes with remember_context/update_project_progress; "
    "(3) L3: map with get_project_structure / get_code_outline / ripgrep_search, then batch all reads in 1 read_targeted_snippets call (avoid repetitive single-file read_file); "
    "(4) L4: batch multi-file or multi-hunk edits in 1 atomic apply_multi_patch call (avoid repetitive edit_file), and filter test output; "
    "(5) Maintain clean typography and Zero Em-Dash compliance."
)

EPHEMERAL_ANCHOR = (
    "[XENONITE 4-LAYER DEFAULT - MINIMUM TURN, MAXIMUM RESULT] "
    "Prefer ServerName='xenonite-tools' (ON-DEMAND only). "
    "L1: search_memory/remember_context/update_project_progress/list_indexed_projects | "
    "L2: searxng_search/crawl_web_markdown | "
    "L3: get_project_structure/get_code_outline/analyze_blast_radius/analyze_function_callers/"
    "analyze_module_dependencies/ripgrep_search/ast_grep_search/read_targeted_snippets | "
    "L4: apply_multi_patch/get_big_o_recommendation. "
    "Single actions remain flexible; PreToolUse blocks blind recursive scans and repetitive single-file read/edit churn."
)


def evaluate_hook(payload: dict) -> dict:
    """Return the hook injection payload for SessionStart or PreInvocation."""
    if "invocationNum" in payload:
        return {"injectSteps": [{"ephemeralMessage": EPHEMERAL_ANCHOR}]}
    return {"injectSteps": [{"systemMessage": {"systemMessage": SESSION_ANCHOR}}]}


def main() -> None:
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
        result = evaluate_hook(data if isinstance(data, dict) else {})
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
    except Exception:
        sys.stdout.write("{}")


if __name__ == "__main__":
    main()
