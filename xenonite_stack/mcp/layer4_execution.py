# -*- coding: utf-8 -*-
"""Layer 4: Atomic Multi-Patch Execution & Big-O Algorithm Atlas."""

from __future__ import annotations

import os
import tempfile
from typing import Dict, List


BIG_O_ATLAS: Dict[str, str] = {
    "permissions": (
        "Recommendation: Bitwise Bitmask Flags | Time: O(1) | Space: O(1) (4-byte int). "
        "Replace repeated role/permission string array scans."
    ),
    "fsm_routing": (
        "Recommendation: Deterministic Transition Table (Record<State, Record<Event, State>>) | "
        "Time: O(1) | Space: O(K) states. Eliminates nested if-else staircases."
    ),
    "id_lookup": (
        "Recommendation: Hash Map / Set (Map<K, V> or Set<K>) | Time: O(1) avg | Space: O(N). "
        "Never call .find() or .includes() inside loops (avoids O(N^2))."
    ),
    "prefix_search": (
        "Recommendation: Radix Tree / Compact Trie | Time: O(L) [L = query length] | Space: O(N*L). "
        "Ideal for route matching, autocomplete, and taxonomy codes."
    ),
    "range_query": (
        "Recommendation: Segment Tree / Interval Tree / Binary Search on Sorted Intervals | "
        "Time: O(log N + K) | Space: O(N). Ideal for scheduling and time-window queries."
    ),
    "timeseries_stream": (
        "Recommendation: Two Pointers / Sliding Window + Contiguous Buffers | "
        "Time: O(N) single pass | Space: O(1) auxiliary buffer."
    ),
    "db_batching": (
        "Recommendation: Set-based Bulk Operations (createMany / $transaction / SQL CTE / COPY) | "
        "Time: O(1) round-trip | Eliminates N+1 database queries."
    ),
}


def apply_multi_patch(patches: List[Dict[str, str]]) -> str:
    """[LAYER 4] Apply multiple exact patches atomically across one or many files.

    Validates all targets in memory first (supporting multiple chained edits to
    the same file) and writes via temp-file replace with full rollback on error.
    """
    if not patches:
        return "No patches supplied."

    staged_contents: Dict[str, str] = {}
    originals: Dict[str, str] = {}
    patch_counts: Dict[str, int] = {}

    # Phase 1: Pre-flight validation & in-memory staging
    for idx, patch in enumerate(patches, start=1):
        path = patch.get("path", "")
        target = patch.get("target")
        replacement = patch.get("replacement")

        if not path or not os.path.isfile(path):
            return f"Failed [Rollback]: File not found: '{path}' (Patch #{idx})"
        if target is None or replacement is None:
            return f"Failed [Rollback]: Missing 'target' or 'replacement' (Patch #{idx})"

        abs_path = os.path.abspath(path)
        if abs_path not in staged_contents:
            try:
                with open(abs_path, "r", encoding="utf-8") as fp:
                    raw = fp.read()
            except OSError as exc:
                return f"Failed [Rollback]: Unable to read '{path}': {exc}"
            originals[abs_path] = raw
            staged_contents[abs_path] = raw
            patch_counts[abs_path] = 0

        if target not in staged_contents[abs_path]:
            return f"Failed [Rollback]: Exact target text not found in '{path}' (Patch #{idx})"

        staged_contents[abs_path] = staged_contents[abs_path].replace(target, replacement, 1)
        patch_counts[abs_path] += 1

    # Phase 2: Atomic disk commit with rollback safety
    committed: list[str] = []
    try:
        for abs_path, new_text in staged_contents.items():
            parent_dir = os.path.dirname(abs_path) or "."
            fd, tmp_path = tempfile.mkstemp(prefix=".xeno_patch_", dir=parent_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as tmp_fp:
                    tmp_fp.write(new_text)
                os.replace(tmp_path, abs_path)
                committed.append(abs_path)
            except Exception:
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                raise
    except Exception as exc:
        # Roll back already-committed files
        for rollback_path in committed:
            try:
                with open(rollback_path, "w", encoding="utf-8", newline="") as fp:
                    fp.write(originals[rollback_path])
            except OSError:
                pass
        return f"Failed [Rolled back {len(committed)} files]: Write error: {exc}"

    lines = [
        f"=== ATOMIC MULTI-PATCH SUCCESS ({len(patches)} patches across {len(committed)} files) ==="
    ]
    for abs_path in committed:
        lines.append(f"[OK] {abs_path} ({patch_counts[abs_path]} patch(es))")
    return "\n".join(lines)


def get_big_o_recommendation(domain_pattern: str) -> str:
    """[LAYER 4] Lookup optimal Big-O algorithm and data structure recommendation."""
    key = domain_pattern.strip().lower()
    if key in BIG_O_ATLAS:
        return BIG_O_ATLAS[key]
    available = ", ".join(sorted(BIG_O_ATLAS.keys()))
    return f"Pattern '{domain_pattern}' not found. Available patterns: {available}"
