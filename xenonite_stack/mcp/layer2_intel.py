# -*- coding: utf-8 -*-
"""Layer 2: Sovereign Web Intelligence (SearXNG Meta-Search + Crawl4AI Extraction)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional

from xenonite_stack.config import XenoniteSettings


def searxng_search(
    query: str,
    max_results: int = 5,
    category: Optional[str] = None,
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 2] Multi-engine meta-search via self-hosted SearXNG JSON API."""
    cfg = settings or XenoniteSettings.load()
    try:
        params: dict[str, object] = {"q": query, "format": "json"}
        if category:
            params[f"category_{category}"] = 1

        url = f"{cfg.searxng_url}/search?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Xenonite-Stack/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        raw_results = data.get("results", [])[:max_results]
        if not raw_results:
            return f"No SearXNG results found for query: '{query}'"

        output = [f"=== SEARXNG SEARCH RESULTS (Total: {len(raw_results)}) ==="]
        for idx, item in enumerate(raw_results):
            output.append(f"[{idx + 1}] {item.get('title')}")
            output.append(f"    URL: {item.get('url')}")
            output.append(f"    Snippet: {item.get('content')}")
            output.append(f"    Engines: {item.get('engines')}")
            output.append("-" * 40)
        return "\n".join(output)
    except Exception as exc:
        return (
            f"SearXNG search error ({cfg.searxng_url}): {exc}\n"
            "Hint: Start the self-hosted intel stack with `xenonite docker up intel` "
            "or point XENONITE_SEARXNG_URL in .env to a running instance."
        )


def crawl_web_markdown(
    url: str,
    mode: str = "fit",
    query: Optional[str] = None,
    settings: Optional[XenoniteSettings] = None,
) -> str:
    """[LAYER 2] Extract clean, noise-free Markdown from any webpage via Crawl4AI."""
    cfg = settings or XenoniteSettings.load()
    try:
        payload: dict[str, object] = {"url": url, "f": mode}
        if query:
            payload["q"] = query

        headers = {"Content-Type": "application/json"}
        if cfg.crawl4ai_token:
            headers["Authorization"] = f"Bearer {cfg.crawl4ai_token}"

        req = urllib.request.Request(
            f"{cfg.crawl4ai_url}/crawl",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        status = data.get("status", False)
        if not status and not data.get("success", False):
            return f"Crawl4AI extraction failed for {url}: {data.get('error', 'Unknown error')}"

        raw_md = data.get("markdown", "")
        if isinstance(raw_md, dict):
            raw_md = raw_md.get("fit_markdown") or raw_md.get("raw_markdown") or ""

        full_len = len(raw_md)
        markdown = raw_md
        if full_len > cfg.crawl4ai_max_chars:
            markdown = (
                raw_md[: cfg.crawl4ai_max_chars]
                + "\n\n... [CONTENT TRUNCATED FOR CONTEXT WINDOW EFFICIENCY] ..."
            )

        return (
            f"=== CRAWL4AI MARKDOWN EXTRACTION: {url} ===\n"
            f"Mode: {mode}\n"
            f"Total Chars: {full_len}\n"
            f"Clean Markdown:\n\n{markdown}"
        )
    except Exception as exc:
        return (
            f"Crawl4AI extraction error ({cfg.crawl4ai_url}): {exc}\n"
            "Hint: Start the self-hosted intel stack with `xenonite docker up intel` "
            "or point XENONITE_CRAWL4AI_URL in .env to a running instance."
        )
