from __future__ import annotations

import logging
from typing import Iterable

import requests

from .models import SearchResult

logger = logging.getLogger(__name__)


def serper_search(query: str, api_key: str, max_results: int = 6) -> list[SearchResult]:
    """Search Google through Serper and return organic results."""
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "num": max_results,
    }

    response = requests.post(
        "https://google.serper.dev/search",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    results: list[SearchResult] = []
    for item in data.get("organic", [])[:max_results]:
        url = item.get("link") or ""
        title = item.get("title") or ""
        snippet = item.get("snippet") or ""
        if not url or not title:
            continue
        results.append(
            SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                source_query=query,
            )
        )

    return results


def search_all(
    queries: Iterable[str],
    provider: str,
    serper_api_key: str,
    max_results_per_query: int,
) -> list[SearchResult]:
    all_results: list[SearchResult] = []

    for query in queries:
        logger.info("Searching query: %s", query)
        if provider == "serper":
            try:
                all_results.extend(
                    serpapi_search(
                        query=query,
                        api_key=serper_api_key,
                        max_results=max_results_per_query,
                    )
                )
            except Exception as exc:
                logger.exception("Search failed for query %r: %s", query, exc)
        else:
            raise ValueError(f"Unsupported SEARCH_PROVIDER: {provider}")

    return dedupe_results(all_results)


def dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
    seen: set[str] = set()
    deduped: list[SearchResult] = []

    for result in results:
        normalized = result.url.strip().rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(result)

    return deduped
