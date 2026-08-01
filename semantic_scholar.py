from __future__ import annotations

"""
Semantic Scholar corpus fetcher for the novelty-decay experiment.

Follows the same conventions as retrieval.py's PubMed client: a plain
`requests` call, a delay between calls to respect rate limits, retry with
backoff on 429, and a local JSON cache so repeated runs don't re-hit the API.

No API key required for light use of the public Graph API.
"""

import json
import time
from pathlib import Path

import requests

S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
CACHE_PATH = Path("results/validation/s2_cache.json")
S2_DELAY = 10.0  # unauthenticated public API is aggressively rate-limited
HEADERS = {"User-Agent": "CaseStudy/1.0 (Alzheimer research; academic use)"}
FIELDS = "title,abstract,year,publicationDate,paperId"

_last_call = 0.0


class SemanticScholarError(RuntimeError):
    pass


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def search_papers(query: str, limit: int = 100, max_retries: int = 6) -> list[dict]:
    """Query Semantic Scholar for papers matching `query`. Cached by query+limit."""
    global _last_call
    cache = _load_cache()
    cache_key = f"{query}|{limit}"
    if cache_key in cache:
        return cache[cache_key]

    wait = max(0.0, S2_DELAY - (time.time() - _last_call))
    if wait > 0:
        time.sleep(wait)

    params = {"query": query, "limit": limit, "fields": FIELDS}
    backoff = 15.0
    for attempt in range(1, max_retries + 1):
        _last_call = time.time()
        try:
            r = requests.get(S2_SEARCH_URL, params=params, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            if attempt == max_retries:
                raise SemanticScholarError(f"S2 request failed for '{query}': {e}") from e
            time.sleep(backoff)
            backoff *= 2
            continue

        if r.status_code == 429:
            print(f"  [s2] 429 rate-limited on '{query}', backing off {backoff:.0f}s "
                  f"(attempt {attempt}/{max_retries})...")
            time.sleep(backoff)
            backoff *= 2
            continue
        if not r.ok:
            if attempt == max_retries:
                raise SemanticScholarError(
                    f"S2 request failed for '{query}': {r.status_code} {r.text[:200]}"
                )
            time.sleep(backoff)
            backoff *= 2
            continue

        data = r.json()
        papers = data.get("data", [])
        cache[cache_key] = papers
        _save_cache(cache)
        return papers

    raise SemanticScholarError(f"S2 request exhausted retries for '{query}'")
