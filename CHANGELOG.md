# Changelog

All notable changes to **Xenonite Stack** will be documented in this file.

## [1.0.0] - 2026-11-23

### Added
- **Modular 4-Layer Native MCP Server (`xenonite-tools`)**: 16 tools cleanly separated into `layer1_memory`, `layer2_intel`, `layer3_code_intel`, and `layer4_execution`.
- **Dual-Backend Layer 1 Memory**: Self-hosted Qdrant + HuggingFace TEI (`BAAI/bge-m3`) with automatic collection bootstrap and zero-Docker SQLite FTS5 fallback (`XENONITE_MEMORY_BACKEND=auto`).
- **Layer 2 Sovereign Web Intelligence**: Self-hosted SearXNG meta-search and Crawl4AI clean Markdown extraction with optional Bearer token authentication.
- **Layer 3 Local Code Intelligence**: Pure-Python project structure, code outline, blast radius, and batched `read_targeted_snippets`, plus auto-discovered `rg`, `sg`, and `madge` with graceful Python fallbacks.
- **Layer 4 Atomic Multi-Patch & Big-O Atlas**: In-memory pre-flight validation, chained multi-hunk edits per file, atomic temp-file replacement with full rollback on I/O error, and Big-O pattern recommendations.
- **Cross-Platform Anti-Churn Guardrails**: Fail-open `SessionStart`, `PreInvocation`, and stateful `PreToolUse` hooks.
- **Unified CLI (`xenonite`)**: `check`, `install` (non-destructive JSON merge + backup), `uninstall`, `print-mcp`, `serve`, `verify`, `docker`, and `memory`.
- **Self-Hosted Docker Compose Stack**: Modular `memory` and `intel` profiles with CPU default and NVIDIA CUDA GPU override (`docker/docker-compose.gpu.yml`).
- **1-Click Bootstrap Scripts**: `bootstrap.bat` (Windows) and `bootstrap.sh` (Linux/macOS).
- **Automated Verification & Unit Tests**: Full `unittest` coverage and silent-filtered `xenonite verify` gate.
