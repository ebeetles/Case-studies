from __future__ import annotations

"""
Retrieval module: live PubMed search driven by the gap/query text.

Each retrieval call searches PubMed by relevance to the query.
Condition C uses judge-authored PubMed queries from the weakest scoring
dimension. Condition B uses a fixed generic query.

Uses the NCBI E-utilities API (no API key required).
Raises on failure — no fallback corpus.
"""

import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CACHE_PATH = Path("results/pubmed_cache.json")
PUBMED_DELAY = 0.4  # NCBI allows 3 req/s without an API key
HEADERS = {"User-Agent": "CaseStudy/1.0 (Alzheimer research; academic use)"}

_PUBMED_QUERY_RE = re.compile(
    r"^\s*PubMed query:\s*(.+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_query_cache: dict[str, list[dict]] = {}
_last_pubmed_call = 0.0


class RetrievalError(RuntimeError):
    pass


def extract_pubmed_query(judge_text: str) -> str:
    """Parse the 'PubMed query:' line from a judge response."""
    m = _PUBMED_QUERY_RE.search(judge_text)
    if not m:
        raise RuntimeError(
            "Judge response missing 'PubMed query:' line:\n"
            f"{judge_text[:500]}"
        )
    query = m.group(1).strip().rstrip(".")
    if query.startswith('"') and query.endswith('"'):
        query = query[1:-1].strip()
    if query.startswith("'") and query.endswith("'"):
        query = query[1:-1].strip()
    if not query:
        raise RuntimeError("Judge returned an empty PubMed query.")
    return query


def _clean_query(query: str) -> str:
    """Strip markdown and noise so PubMed gets a usable search string."""
    q = re.sub(r"\*+", "", query)
    q = re.sub(r'["\'\u2018\u2019\u201c\u201d]', "", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q[:200]


def _throttle() -> None:
    global _last_pubmed_call
    elapsed = time.time() - _last_pubmed_call
    if elapsed < PUBMED_DELAY:
        time.sleep(PUBMED_DELAY - elapsed)
    _last_pubmed_call = time.time()


def _esearch_ids(term: str, n: int) -> list[str]:
    _throttle()
    esearch = requests.get(
        PUBMED_ESEARCH,
        params={
            "db": "pubmed",
            "term": term,
            "retmax": n,
            "retmode": "json",
            "datetype": "pdat",
            "mindate": "1900",
            "maxdate": "2023/12/31",
        },
        headers=HEADERS,
        timeout=30,
    )
    esearch.raise_for_status()
    return esearch.json().get("esearchresult", {}).get("idlist", [])


def _pubmed_query_variants(query: str, append_alzheimer: bool = True) -> list[str]:
    """Progressively narrower queries when PubMed ANDs too many terms."""
    clean = _clean_query(query)
    if not clean:
        return []
    if append_alzheimer and "alzheimer" not in clean.lower():
        clean = f"{clean} Alzheimer disease"

    lower = clean.lower()
    alz_idx = lower.find("alzheimer")
    if alz_idx >= 0:
        prefix = clean[:alz_idx].strip()
        suffix = clean[alz_idx:].strip()
        keywords = prefix.split()
        if not keywords:
            return [suffix]
        return [
            f"{' '.join(keywords[:k])} {suffix}".strip()
            for k in range(len(keywords), 0, -1)
        ]
    else:
        # OOD mode: no Alzheimer term, produce progressively shorter variants
        words = clean.split()
        if not words:
            return []
        return [" ".join(words[:k]) for k in range(len(words), 0, -1)]


def _pubmed_search(query: str, n: int, append_alzheimer: bool = True) -> list[dict]:
    """Search PubMed and fetch titles + abstracts. Raises RetrievalError on failure."""
    variants = _pubmed_query_variants(query, append_alzheimer=append_alzheimer)
    if not variants:
        raise RetrievalError("Empty retrieval query.")

    idlist: list[str] = []
    used_term = ""
    for term in variants:
        print(f"  [retrieval] PubMed search: '{term[:70]}'")
        try:
            idlist = _esearch_ids(term, n)
        except requests.RequestException as e:
            raise RetrievalError(f"PubMed esearch failed: {e}") from e
        if idlist:
            used_term = term
            break

    if not idlist:
        raise RetrievalError(
            f"PubMed returned 0 papers for all query variants of: '{query}'"
        )

    _throttle()
    try:
        efetch = requests.get(
            PUBMED_EFETCH,
            params={"db": "pubmed", "id": ",".join(idlist), "retmode": "xml"},
            headers=HEADERS,
            timeout=30,
        )
        efetch.raise_for_status()
    except requests.RequestException as e:
        raise RetrievalError(f"PubMed efetch failed: {e}") from e

    root = ET.fromstring(efetch.content)
    papers = []
    for art in root.findall(".//PubmedArticle"):
        title = (art.findtext(".//ArticleTitle") or "").strip()
        abstract = " ".join(
            (a.text or "") for a in art.findall(".//AbstractText")
        ).strip()
        if title:
            papers.append({"title": title, "abstract": abstract[:400]})

    if not papers:
        raise RetrievalError(
            f"PubMed returned IDs but no parseable abstracts for: '{used_term}'"
        )

    print(f"  [retrieval]   PubMed returned {len(papers)} papers.")
    print(f"  [retrieval]   Top: {papers[0]['title'][:65]}")
    return papers


def check_retrieval_ready() -> None:
    """Verify PubMed is reachable. Raises RetrievalError on failure."""
    papers = _pubmed_search("Alzheimer disease drug repurposing", n=2)
    if len(papers) < 1:
        raise RetrievalError("PubMed connectivity check returned no papers.")


def _load_disk_cache() -> None:
    global _query_cache
    if CACHE_PATH.exists():
        with open(CACHE_PATH) as f:
            _query_cache = json.load(f)


def _save_disk_cache() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(_query_cache, f)


def retrieve_papers(query: str, n: int = 5, append_alzheimer: bool = True) -> list[dict]:
    """
    Retrieve papers relevant to the query via live PubMed search.

    Results are cached per query to avoid duplicate API calls within a run.
    Set append_alzheimer=False for OOD queries that must stay outside AD literature.
    Raises RetrievalError if PubMed fails or returns nothing.
    """
    if not _query_cache:
        _load_disk_cache()

    cache_key = f"{_clean_query(query)}|{n}|alz={append_alzheimer}"
    if cache_key in _query_cache:
        cached = _query_cache[cache_key]
        print(f"  [retrieval] Cache hit ({len(cached)} papers) for: '{query[:50]}...'")
        return cached

    papers = _pubmed_search(query, n, append_alzheimer=append_alzheimer)
    _query_cache[cache_key] = papers
    _save_disk_cache()
    return papers


class RetrievalTracker:
    """
    Tracks seen paper titles across all retrieval calls within a single pipeline run.
    Used for Condition C only to prevent the same paper appearing in multiple rounds.
    """

    def __init__(self) -> None:
        self.seen_titles: set[str] = set()

    def retrieve_deduplicated(
        self, query: str, n: int = 3
    ) -> tuple[list[dict], list[str]]:
        """
        Retrieve n papers not yet seen in this run, with two filters applied:
          1. Deduplication: skip titles already returned in a previous round.
          2. AD filter: skip any paper whose title contains 'Alzheimer'
             (OOD queries must stay outside the AD literature).

        Fetches n*3 to account for filtering. Falls back to
        query + 'novel mechanisms' if not enough fresh papers found.

        Returns (fresh_papers, filtered_titles).
        """
        raw = retrieve_papers(query, n=n * 3, append_alzheimer=False)

        fresh: list[dict] = []
        filtered: list[str] = []
        for paper in raw:
            key = paper["title"].strip().lower()
            if "alzheimer" in key:
                filtered.append(f"[AD-filtered] {paper['title']}")
                continue
            if key not in self.seen_titles:
                self.seen_titles.add(key)
                fresh.append(paper)
            else:
                filtered.append(paper["title"])
            if len(fresh) == n:
                break

        # First broadening pass
        if len(fresh) < n:
            fallback_query = query + " novel mechanisms"
            print(f"  [retrieval] Dedup fallback query: '{fallback_query[:60]}'")
            try:
                fallback = retrieve_papers(fallback_query, n=n * 2, append_alzheimer=False)
            except RetrievalError:
                fallback = []
            for paper in fallback:
                key = paper["title"].strip().lower()
                if "alzheimer" in key:
                    filtered.append(f"[AD-filtered] {paper['title']}")
                    continue
                if key not in self.seen_titles:
                    self.seen_titles.add(key)
                    fresh.append(paper)
                if len(fresh) == n:
                    break

        # Second broadening pass: truncate to first two keywords
        if len(fresh) < n:
            words = _clean_query(query).split()
            short_query = " ".join(words[:2]) if len(words) >= 2 else _clean_query(query)
            if short_query and short_query != query:
                print(f"  [retrieval] Broad fallback query: '{short_query}'")
                try:
                    broad = retrieve_papers(short_query, n=n * 3, append_alzheimer=False)
                except RetrievalError:
                    broad = []
                for paper in broad:
                    key = paper["title"].strip().lower()
                    if "alzheimer" in key:
                        filtered.append(f"[AD-filtered] {paper['title']}")
                        continue
                    if key not in self.seen_titles:
                        self.seen_titles.add(key)
                        fresh.append(paper)
                    if len(fresh) == n:
                        break

        if filtered:
            print(f"  [retrieval] Filtered {len(filtered)} paper(s) (dedup/AD).")
        if not fresh:
            print(f"  [retrieval] WARNING: zero OOD papers found after all fallback attempts.")

        return fresh, filtered
