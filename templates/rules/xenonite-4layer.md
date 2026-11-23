# ==============================================================================
# XENONITE 4-LAYER AUTONOMOUS ENGINEERING ENGINE (GLOBAL ALWAYS-ON RULES)
# ==============================================================================

## 1. CORE OPERATING PRINCIPLES
- **Minimum Turn, Maximum Result**: Eliminate repetitive micro-tool churn across all models and sessions. Batch reads and batch edits atomically.
- **On-Demand Discipline**: Never force tool calls for pure conceptual Q&A or casual discussion. Invoke tools only when inspecting files, memory, web docs, or editing code.
- **Hard Brake Enforcement**: If the user explicitly asks to pause or take over testing, stop all tool execution immediately and respond concisely.
- **Escalating Approval**: Always request explicit confirmation before destructive actions (permanent deletion, destructive git commands, mass database writes, or secret rotation).
- **Clean Typography**: Zero Em-Dash compliant (avoid U+2014 and U+2013; use standard `-` or `:`).

---

## 2. THE 4-LAYER NATIVE MCP ENGINE

### LAYER 1: PERSISTENT MEMORY & LIVING SYNC (Qdrant+TEI / SQLite FTS5)
- **No Blind Recursive Scans**: Never run recursive shell scans (`Get-ChildItem -Recurse`, `dir /s`, `grep -r`, `find . -name`, `os.walk`) to explore a codebase.
- **1-Call Scoping**: Call `search_memory` once at the start of project work to retrieve architectural contracts, ADRs, and constraints.
- **Living Sync**: After finishing a feature or changing an architectural contract, persist the summary using `update_project_progress` or `remember_context`.

### LAYER 2: SOVEREIGN WEB INTELLIGENCE (SearXNG + Crawl4AI)
- Use `searxng_search` for clean multi-engine technical research without SEO noise.
- Use `crawl_web_markdown` to extract clean, token-efficient Markdown from documentation pages.

### LAYER 3: BLAST RADIUS, AST & SURGICAL CODE INTELLIGENCE
- **Structure & Outline First**: Map directories with `get_project_structure` and inspect large files via `get_code_outline` before reading implementation bodies.
- **Impact Graph**: Check `analyze_blast_radius`, `analyze_function_callers`, and `analyze_module_dependencies` before modifying shared modules.
- **Surgical Batch Reading**: Locate exact lines with `ripgrep_search` or `ast_grep_search`, then fetch all target slices across multiple files in **1 single call** via `read_targeted_snippets`.

### LAYER 4: ATOMIC MULTI-PATCH, BIG-O DISCIPLINE & FILTERED TESTING
- **1-Turn Atomic Patching**: Combine multi-hunk and multi-file edits into **1 atomic call** using `apply_multi_patch` (built-in pre-flight validation + rollback).
- **Big-O Engineering**: Consult `get_big_o_recommendation` and prefer O(1) Hash Map/Set lookups (avoid `.find()` inside loops), bitmask flags for permissions, guard clauses, and set-based bulk DB queries (zero N+1).
- **Flexible Anti-Churn**: Single simple actions remain allowed, while `PreToolUse` automatically blocks blind recursive scans and repetitive single-file `read_file`/`edit_file` loops.
- **Filtered Verification**: Run targeted project test commands and filter output to surface errors cleanly.

---

## 3. INLINE NATIVE MCP CONTRACT (`ServerName="xenonite-tools"`)
All 16 tools run on the single global server **`xenonite-tools`**. Call them directly via `call_mcp_tool(ServerName="xenonite-tools", ToolName="<name>", Arguments={...})` without wasting turns reading JSON schema files:

| Layer | `ToolName` | `Arguments` (Exact Signature) |
| :--- | :--- | :--- |
| **L1** | `search_memory` | `{"query": str, "project": str?, "domain": str?, "limit": int?}` |
| **L1** | `remember_context` | `{"project": str, "title": str, "content": str, "domain": str?, "module": str?, "tags": [str]?, "files": [str]?, "status": str?}` |
| **L1** | `update_project_progress` | `{"project": str, "feature": str, "status": "ready"|"in_progress"|"planned"|"blocked", "note": str, "files": [str]?}` |
| **L1** | `list_indexed_projects` | `{}` |
| **L2** | `searxng_search` | `{"query": str, "max_results": int?, "category": str?}` |
| **L2** | `crawl_web_markdown` | `{"url": str, "mode": "fit"|"raw"?, "query": str?}` |
| **L3** | `get_project_structure` | `{"root_dir": str, "max_depth": int?}` |
| **L3** | `get_code_outline` | `{"file_path": str}` |
| **L3** | `analyze_blast_radius` | `{"target_file": str, "search_dir": str}` |
| **L3** | `analyze_function_callers` | `{"function_name": str, "search_dir": str, "max_results": int?}` |
| **L3** | `analyze_module_dependencies` | `{"target_path": str, "circular_only": bool?}` |
| **L3** | `ripgrep_search` | `{"pattern": str, "search_path": str, "file_type": str?, "max_results": int?}` |
| **L3** | `ast_grep_search` | `{"pattern": str, "search_path": str, "language": str?, "max_results": int?}` |
| **L3** | `read_targeted_snippets` | `{"snippets": [{"file_path": str, "start_line": int, "end_line": int, "label": str?}]}` |
| **L4** | `apply_multi_patch` | `{"patches": [{"path": str, "target": str, "replacement": str}]}` |
| **L4** | `get_big_o_recommendation` | `{"domain_pattern": str}` |
