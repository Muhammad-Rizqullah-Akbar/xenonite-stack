---
name: xeno-intel
description: Sovereign multi-engine search via self-hosted SearXNG (`:8888`) and clean headless Markdown extraction via Crawl4AI (`:11235`). Use for technical documentation lookup and web research without HTML/DOM token bloat.
---

# Xeno-Intel: Layer 2 Sovereign Web Intelligence

## Purpose
Execute clean, privacy-preserving technical research and extract documentation directly into compact Markdown via the `xenonite-tools` MCP server.

## Endpoints (Configured via `.env`)
- **SearXNG**: `XENONITE_SEARXNG_URL` (default `http://127.0.0.1:8888`)
- **Crawl4AI**: `XENONITE_CRAWL4AI_URL` (default `http://127.0.0.1:11235`)

## Standard Workflow
1. Call `searxng_search` with `{"query": "<technical query>", "max_results": 5, "category": "it"}`.
2. Pick the highest-signal URL and call `crawl_web_markdown` with `{"url": "<target-url>", "mode": "fit", "query": "<optional filter>"}`.
3. If services are offline, start them with `xenonite docker up intel`.
