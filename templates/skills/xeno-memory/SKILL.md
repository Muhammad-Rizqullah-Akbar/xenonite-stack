---
name: xeno-memory
description: Universal long-term working memory via self-hosted Qdrant + TEI (`BAAI/bge-m3`) with automatic SQLite FTS5 fallback. Use whenever starting work on a codebase, recalling architecture decisions, or recording completed milestones.
---

# Xeno-Memory: Layer 1 Persistent Context Engine

## Purpose
Prevent context amnesia across sessions and devices by storing architectural contracts, design decisions, and sprint milestones in persistent memory via the `xenonite-tools` MCP server.

## Backends (Automatic)
- **Full Mode**: Self-hosted Qdrant (`XENONITE_QDRANT_URL`, default `:6333`) + HuggingFace TEI (`XENONITE_TEI_URL`, default `:8080/embed`).
- **Lite Fallback**: Local SQLite FTS5 (`~/.xenonite/memory.db`) when Docker/Qdrant is offline.

## Standard Workflow
1. **Before Exploring a Project**: Call `search_memory` once with `{"query": "<task topic>", "project": "<project-slug>"}`.
2. **After Architecture Decisions**: Call `remember_context` to store schemas, invariants, or contracts.
3. **After Completing a Feature**: Call `update_project_progress` with status `ready`, `in_progress`, `planned`, or `blocked`.
4. **Discover Indexed Workspaces**: Call `list_indexed_projects`.
