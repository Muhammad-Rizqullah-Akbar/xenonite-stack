# -*- coding: utf-8 -*-
"""Layer 3: Code Intelligence, Blast Radius, AST & Surgical Reading Tools.

All 8 tools operate locally with zero Docker requirement.
External CLI tools (`rg`, `sg`, `madge`) are auto-discovered from PATH, with
graceful pure-Python fallbacks for `ripgrep_search` and `analyze_function_callers`.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any, Dict, List, Optional

from xenonite_stack.config import XenoniteSettings, resolve_binary

IGNORED_DIRS = {
    "node_modules", ".git", "dist", ".turbo", "target", "build",
    ".next", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache",
}

CODE_EXTENSIONS = (
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".rs", ".go", ".java", ".kt", ".dart",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".yaml", ".yml",
)


def _python_regex_search(
    pattern: str,
    search_path: str,
    file_type: Optional[str],
    max_results: int,
) -> list[str]:
    """Pure-Python regex fallback when `rg` binary is not installed."""
    compiled = re.compile(pattern)
    ext_filter = f".{file_type.lstrip('.').lower()}" if file_type else None
    matches: list[str] = []

    if os.path.isfile(search_path):
        target_files = [search_path]
    else:
        target_files = []
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
            for fname in files:
                if ext_filter and not fname.lower().endswith(ext_filter):
                    continue
                target_files.append(os.path.join(root, fname))

    for fpath in target_files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, start=1):
                    if compiled.search(line):
                        matches.append(f"{fpath}:{line_no}:{line.rstrip()}")
                        if len(matches) >= max_results:
                            return matches
        except OSError:
            continue
    return matches


def analyze_blast_radius(target_file: str, search_dir: str) -> str:
    """[LAYER 3] Identify all files importing or referencing `target_file`."""
    try:
        base_name = os.path.splitext(os.path.basename(target_file))[0]
        esc = re.escape(base_name)
        import_pattern = re.compile(
            rf"""(?:import|from|require)\s*\(?['"][^'"]*{esc}['"]\)?"""
            rf"""|^\s*(?:from|import)\s+[\w.]*\b{esc}\b"""
            rf"""|^\s*(?:use|mod)\s+[\w:]*\b{esc}\b""",
            re.MULTILINE,
        )

        impacted_files: list[str] = []
        total_scanned = 0
        target_abs = os.path.abspath(target_file)

        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for fname in files:
                if not fname.endswith(CODE_EXTENSIONS):
                    continue
                total_scanned += 1
                full_path = os.path.join(root, fname)
                if os.path.abspath(full_path) == target_abs:
                    continue
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        if import_pattern.search(fp.read()):
                            impacted_files.append(os.path.relpath(full_path, search_dir))
                except OSError:
                    continue

        output = [
            "=== BLAST RADIUS IMPACT ANALYSIS ===",
            f"Target File: {target_file}",
            f"Files Scanned: {total_scanned}",
            f"Directly Impacted Files: {len(impacted_files)}\n",
        ]
        if impacted_files:
            output.append("Impacted files to verify/test:")
            for idx, item in enumerate(sorted(impacted_files), start=1):
                output.append(f"  [{idx}] {item}")
        else:
            output.append("No direct importers found (safe for isolated modification).")
        return "\n".join(output)
    except Exception as exc:
        return f"Blast radius analysis error: {exc}"


def ripgrep_search(
    pattern: str,
    search_path: str = ".",
    file_type: Optional[str] = None,
    max_results: int = 25,
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 3] High-speed code search via local ripgrep (`rg`), with Python fallback."""
    cfg = settings or XenoniteSettings.load()
    try:
        rg_bin = resolve_binary(cfg.rg_bin_override, "rg")
        if rg_bin:
            cmd = [rg_bin, "-n", "--no-heading", "--color=never", "-m", str(max_results)]
            if file_type:
                cmd.extend(["-t", file_type])
            cmd.extend([pattern, search_path])

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            lines = [line for line in res.stdout.splitlines() if line.strip()]
            if not lines:
                return f"No matches for '{pattern}' in {search_path}"
            return (
                f"=== RIPGREP SEARCH: '{pattern}' ({len(lines[:max_results])} matches) ===\n"
                + "\n".join(lines[:max_results])
            )

        lines = _python_regex_search(pattern, search_path, file_type, max_results)
        if not lines:
            return f"No matches for '{pattern}' in {search_path} [python-fallback]"
        return (
            f"=== REGEX SEARCH [python-fallback, install ripgrep for speed]: '{pattern}' ({len(lines)} matches) ===\n"
            + "\n".join(lines)
        )
    except Exception as exc:
        return f"Ripgrep search error: {exc}"


def ast_grep_search(
    pattern: str,
    search_path: str = ".",
    language: Optional[str] = None,
    max_results: int = 15,
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 3] Syntax-aware AST pattern search via ast-grep (`sg`)."""
    cfg = settings or XenoniteSettings.load()
    try:
        sg_bin = resolve_binary(cfg.sg_bin_override, "sg", "ast-grep")
        if not sg_bin:
            return (
                "ast-grep binary (`sg` / `ast-grep`) not found in PATH. "
                "Install via `npm i -g @ast-grep/cli`, `cargo install ast-grep`, or `brew install ast-grep`."
            )

        cmd = [sg_bin, "run", "--pattern", pattern]
        if language:
            cmd.extend(["--lang", language])
        cmd.append(search_path)

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        out = res.stdout.strip()
        if not out:
            return f"No AST matches for pattern '{pattern}' in {search_path}"

        lines = out.splitlines()
        truncated = "\n".join(lines[: max_results * 5])
        return f"=== AST-GREP RESULTS: '{pattern}' ===\n{truncated}"
    except Exception as exc:
        return f"ast-grep error: {exc}"


def get_project_structure(root_dir: str = ".", max_depth: int = 3) -> str:
    """[LAYER 3] Compact directory hierarchy tree excluding cache/build noise."""
    try:
        abs_root = os.path.abspath(root_dir)
        if not os.path.isdir(abs_root):
            return f"Directory not found: {root_dir}"

        lines = [f"=== PROJECT STRUCTURE: {os.path.basename(abs_root)} (Depth <= {max_depth}) ==="]
        base_depth = abs_root.rstrip(os.sep).count(os.sep)

        for root, dirs, files in os.walk(abs_root):
            cur_depth = root.rstrip(os.sep).count(os.sep) - base_depth
            if cur_depth >= max_depth:
                dirs.clear()
                continue

            dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not d.startswith("."))
            indent = "  " * cur_depth
            if cur_depth > 0:
                lines.append(f"{indent}[DIR] {os.path.basename(root)}/")

            file_indent = "  " * (cur_depth + 1)
            visible_files = sorted(f for f in files if not f.startswith("."))
            for fname in visible_files[:12]:
                lines.append(f"{file_indent}{fname}")
            if len(visible_files) > 12:
                lines.append(f"{file_indent}... (+{len(visible_files) - 12} more files)")

            if len(lines) > 160:
                lines.append("... [TREE TRUNCATED FOR TOKEN EFFICIENCY] ...")
                break

        return "\n".join(lines)
    except Exception as exc:
        return f"Project structure error: {exc}"


def get_code_outline(file_path: str) -> str:
    """[LAYER 3] Extract symbol declarations (classes, functions, structs, methods) with line numbers."""
    try:
        if not os.path.isfile(file_path):
            return f"File not found: {file_path}"

        with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
            file_lines = fp.readlines()

        decl_pattern = re.compile(
            r"^\s*(?:export\s+)?(?:default\s+)?(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?"
            r"(?:class|interface|type|enum|struct|trait|impl|fn|def|func|function|"
            r"public\s+function|private\s+function|protected\s+function)"
            r"\s+([A-Za-z0-9_$]+)"
        )
        method_pattern = re.compile(
            r"^\s*(?:(?:public|private|protected|static|async|override|readonly)\s+)+([A-Za-z0-9_$]+)\s*\("
        )

        outline_items: list[str] = []
        for idx, line in enumerate(file_lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "#", "/*", "*")):
                continue
            if decl_pattern.search(line):
                outline_items.append(f"Line {idx:4d}: {stripped[:90]}")
            elif method_pattern.search(line):
                outline_items.append(f"Line {idx:4d}:   -> {stripped[:85]}")

        if not outline_items:
            return f"No top-level symbols detected in {file_path} (Total lines: {len(file_lines)})"

        header = [
            f"=== CODE OUTLINE: {os.path.basename(file_path)} (Total: {len(file_lines)} lines) ===",
            f"Symbols found: {len(outline_items)}\n",
        ]
        return "\n".join(header + outline_items)
    except Exception as exc:
        return f"Code outline error: {exc}"


def analyze_function_callers(
    function_name: str,
    search_dir: str = ".",
    max_results: int = 15,
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 3] Trace active call sites of `function_name` across a workspace."""
    cfg = settings or XenoniteSettings.load()
    try:
        call_pattern = rf"\b{re.escape(function_name)}\s*\("
        rg_bin = resolve_binary(cfg.rg_bin_override, "rg")

        if rg_bin:
            cmd = [rg_bin, "-n", "--no-heading", "--color=never", "-m", str(max_results * 2), call_pattern, search_dir]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            raw_lines = [line for line in res.stdout.splitlines() if line.strip()]
        else:
            raw_lines = _python_regex_search(call_pattern, search_dir, None, max_results * 2)

        def_markers = (
            f"function {function_name}",
            f"def {function_name}",
            f"fn {function_name}",
            f"func {function_name}",
        )
        filtered = [line for line in raw_lines if not any(marker in line for marker in def_markers)]

        if not filtered:
            return f"No callers found for '{function_name}' in {search_dir}"

        selected = filtered[:max_results]
        header = [
            f"=== CALL GRAPH / CALLERS: '{function_name}' ===",
            f"Active call sites ({len(selected)}):\n",
        ]
        return "\n".join(header + selected)
    except Exception as exc:
        return f"Function callers error: {exc}"


def analyze_module_dependencies(
    target_path: str,
    circular_only: bool = False,
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 3] Map JS/TS module dependency graphs and detect circular dependencies via Madge."""
    cfg = settings or XenoniteSettings.load()
    try:
        madge_bin = resolve_binary(cfg.madge_bin_override, "madge")
        if not madge_bin:
            return (
                "Madge binary (`madge`) not found in PATH. "
                "Install via `npm i -g madge` to enable JS/TS module dependency graphs."
            )

        cmd = [madge_bin]
        if circular_only:
            cmd.append("--circular")
        cmd.extend(["--extensions", "ts,js,tsx,jsx", target_path])

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        out = res.stdout.strip() or res.stderr.strip()
        if not out:
            return f"Madge completed with empty output for {target_path} (no circular dependencies if circular_only=True)."
        return f"=== MADGE DEPENDENCY GRAPH: {target_path} ===\n{out}"
    except Exception as exc:
        return f"Madge dependency error: {exc}"


def read_targeted_snippets(snippets: List[Dict[str, Any]]) -> str:
    """[LAYER 3] Batch-read exact line ranges across one or multiple files in 1 call."""
    try:
        output_blocks = [f"=== CHERRY-PICKED CODE SLICES ({len(snippets)} targets) ==="]
        total_lines_read = 0

        for idx, item in enumerate(snippets, start=1):
            fpath = str(item.get("file_path", ""))
            sline = int(item.get("start_line", 1))
            eline = int(item.get("end_line", sline + 50))
            label = item.get("label") or os.path.basename(fpath)

            if not fpath or not os.path.isfile(fpath):
                output_blocks.append(f"\n[Snippet {idx}] ERROR: File not found: '{fpath}'")
                continue

            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                all_lines = fp.readlines()

            total_lines = len(all_lines)
            s_idx = max(0, sline - 1)
            e_idx = min(total_lines, eline)
            sliced = all_lines[s_idx:e_idx]
            total_lines_read += len(sliced)

            block = [
                f"\n--- [Target {idx}: {label}] ---",
                f"File: {fpath} (Lines {s_idx + 1}-{e_idx} of {total_lines})",
            ]
            for line_no, text in enumerate(sliced, start=s_idx + 1):
                block.append(f"{line_no:4d} | {text.rstrip()}")
            output_blocks.append("\n".join(block))

        output_blocks.append(
            f"\n[TOTAL SLICES: {len(snippets)} targets | Lines extracted: {total_lines_read}]"
        )
        return "\n".join(output_blocks)
    except Exception as exc:
        return f"Targeted snippets read error: {exc}"
