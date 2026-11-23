# -*- coding: utf-8 -*-
"""Xenonite 4-Layer Native MCP Server (`xenonite-tools`).

Registers all 16 modular tools across Layer 1-4 on a single FastMCP server.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from xenonite_stack.mcp import (
    layer1_memory,
    layer2_intel,
    layer3_code_intel,
    layer4_execution,
)

mcp = FastMCP("xenonite-tools")


# =============================================================================
# LAYER 1: PERSISTENT MEMORY (QDRANT+TEI / SQLITE-FTS5)
# =============================================================================

@mcp.tool()
def search_memory(
    query: str,
    project: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 4,
) -> str:
    """[LAYER 1] Semantic memory search across Qdrant+TEI (or local SQLite FTS5 fallback)."""
    return layer1_memory.search_memory(query=query, project=project, domain=domain, limit=limit)


@mcp.tool()
def remember_context(
    project: str,
    title: str,
    content: str,
    domain: str = "architecture",
    module: Optional[str] = None,
    tags: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    status: str = "active",
) -> str:
    """[LAYER 1] Persist architectural knowledge, decisions, API contracts, or rules."""
    return layer1_memory.remember_context(
        project=project,
        title=title,
        content=content,
        domain=domain,
        module=module,
        tags=tags,
        files=files,
        status=status,
    )


@mcp.tool()
def update_project_progress(
    project: str,
    feature: str,
    status: str,
    note: str,
    files: Optional[List[str]] = None,
) -> str:
    """[LAYER 1] Record real-time milestone or feature progress ('ready'|'in_progress'|'planned'|'blocked')."""
    return layer1_memory.update_project_progress(
        project=project,
        feature=feature,
        status=status,
        note=note,
        files=files,
    )


@mcp.tool()
def list_indexed_projects() -> str:
    """[LAYER 1] List all projects currently indexed in persistent memory."""
    return layer1_memory.list_indexed_projects()


# =============================================================================
# LAYER 2: SOVEREIGN WEB INTELLIGENCE (SEARXNG + CRAWL4AI)
# =============================================================================

@mcp.tool()
def searxng_search(
    query: str,
    max_results: int = 5,
    category: Optional[str] = None,
) -> str:
    """[LAYER 2] Multi-engine web search via self-hosted SearXNG without SEO filter bubbles."""
    return layer2_intel.searxng_search(query=query, max_results=max_results, category=category)


@mcp.tool()
def crawl_web_markdown(
    url: str,
    mode: str = "fit",
    query: Optional[str] = None,
) -> str:
    """[LAYER 2] Extract clean, noise-free technical Markdown from a URL via Crawl4AI."""
    return layer2_intel.crawl_web_markdown(url=url, mode=mode, query=query)


# =============================================================================
# LAYER 3: CODE INTELLIGENCE, BLAST RADIUS & SURGICAL READING
# =============================================================================

@mcp.tool()
def get_project_structure(root_dir: str = ".", max_depth: int = 3) -> str:
    """[LAYER 3] Compact project directory tree filtering build/cache directories."""
    return layer3_code_intel.get_project_structure(root_dir=root_dir, max_depth=max_depth)


@mcp.tool()
def get_code_outline(file_path: str) -> str:
    """[LAYER 3] Extract symbol declarations (classes, functions, structs, methods) with line numbers."""
    return layer3_code_intel.get_code_outline(file_path=file_path)


@mcp.tool()
def analyze_blast_radius(target_file: str, search_dir: str) -> str:
    """[LAYER 3] Calculate impact blast radius by finding all files importing `target_file`."""
    return layer3_code_intel.analyze_blast_radius(target_file=target_file, search_dir=search_dir)


@mcp.tool()
def analyze_function_callers(
    function_name: str,
    search_dir: str = ".",
    max_results: int = 15,
) -> str:
    """[LAYER 3] Trace active call sites (call graph) for `function_name` across a directory."""
    return layer3_code_intel.analyze_function_callers(
        function_name=function_name,
        search_dir=search_dir,
        max_results=max_results,
    )


@mcp.tool()
def analyze_module_dependencies(target_path: str, circular_only: bool = False) -> str:
    """[LAYER 3] Map JS/TS module dependencies and detect circular imports via Madge."""
    return layer3_code_intel.analyze_module_dependencies(
        target_path=target_path,
        circular_only=circular_only,
    )


@mcp.tool()
def ripgrep_search(
    pattern: str,
    search_path: str = ".",
    file_type: Optional[str] = None,
    max_results: int = 25,
) -> str:
    """[LAYER 3] Fast regex/string code search via local ripgrep (`rg`), with Python fallback."""
    return layer3_code_intel.ripgrep_search(
        pattern=pattern,
        search_path=search_path,
        file_type=file_type,
        max_results=max_results,
    )


@mcp.tool()
def ast_grep_search(
    pattern: str,
    search_path: str = ".",
    language: Optional[str] = None,
    max_results: int = 15,
) -> str:
    """[LAYER 3] Syntax-aware AST pattern search via ast-grep (`sg`)."""
    return layer3_code_intel.ast_grep_search(
        pattern=pattern,
        search_path=search_path,
        language=language,
        max_results=max_results,
    )


@mcp.tool()
def read_targeted_snippets(snippets: List[Dict[str, Any]]) -> str:
    """[LAYER 3] Batch-read exact line slices across one or many files in a single tool call."""
    return layer3_code_intel.read_targeted_snippets(snippets=snippets)


# =============================================================================
# LAYER 4: ATOMIC MULTI-PATCH & BIG-O ATLAS
# =============================================================================

@mcp.tool()
def apply_multi_patch(patches: List[Dict[str, str]]) -> str:
    """[LAYER 4] Apply multiple exact text patches atomically across files with rollback."""
    return layer4_execution.apply_multi_patch(patches=patches)


@mcp.tool()
def get_big_o_recommendation(domain_pattern: str) -> str:
    """[LAYER 4] Lookup optimal Big-O algorithm and data structure patterns."""
    return layer4_execution.get_big_o_recommendation(domain_pattern=domain_pattern)


def main() -> None:
    """Run the `xenonite-tools` stdio MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
