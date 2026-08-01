from __future__ import annotations

"""
Step 2 of the novelty-decay experiment: build a dated corpus of AD
drug-repurposing literature via the Semantic Scholar public API.

Broad + per-compound queries (per-compound queries ensure both pre- and
post-cutoff windows actually contain compound-relevant papers, which is
needed for a meaningful embedding-similarity signal — see novelty_decay.py).

Falls back to a note in the output if S2 rate-limits persistently, per the
task's explicit instruction not to silently fail.
"""

import json
from pathlib import Path

from semantic_scholar import search_papers, SemanticScholarError

OUT_PATH = Path("results/validation/corpus.json")

QUERIES = [
    "Alzheimer's disease drug repurposing",
    "Alzheimer's disease drug repositioning",
    "Alzheimer's disease network pharmacology treatment",
    "Alzheimer's disease FDA approved drug neuroprotection",
    "Alzheimer's disease therapeutic target mechanism",
    "metformin Alzheimer's disease",
    "AMPK mTOR Alzheimer's disease",
    "liraglutide Alzheimer's disease",
    "GLP-1 receptor agonist Alzheimer's disease",
    "pioglitazone Alzheimer's disease",
    "PPAR gamma Alzheimer's disease",
    "losartan Alzheimer's disease",
    "angiotensin receptor blocker Alzheimer's disease",
    "sildenafil Alzheimer's disease",
    "phosphodiesterase 5 inhibitor Alzheimer's disease",
]


def main() -> None:
    papers_by_id: dict[str, dict] = {}
    failed_queries: list[str] = []

    for i, q in enumerate(QUERIES, 1):
        print(f"[corpus] ({i}/{len(QUERIES)}) querying: '{q}'...", flush=True)
        try:
            results = search_papers(q, limit=100)
        except SemanticScholarError as e:
            print(f"[corpus]   FAILED: {e}", flush=True)
            failed_queries.append(q)
            continue

        added = 0
        for p in results:
            pid = p.get("paperId")
            if not pid or not p.get("abstract") or not p.get("title"):
                continue
            year = p.get("year")
            if not year or year < 2000:
                continue
            if pid not in papers_by_id:
                papers_by_id[pid] = {
                    "paperId": pid,
                    "title": p["title"],
                    "abstract": p["abstract"],
                    "year": year,
                    "publicationDate": p.get("publicationDate"),
                    "source_queries": [q],
                }
                added += 1
            else:
                papers_by_id[pid]["source_queries"].append(q)
        print(f"[corpus]   {len(results)} results, {added} new unique papers "
              f"(total so far: {len(papers_by_id)})", flush=True)

    corpus = list(papers_by_id.values())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "papers": corpus,
        "n_papers": len(corpus),
        "queries_run": QUERIES,
        "queries_failed": failed_queries,
    }, indent=2))

    print(f"\n[corpus] Done. {len(corpus)} unique papers with abstracts, "
          f"{len(failed_queries)}/{len(QUERIES)} queries failed.")
    if failed_queries:
        print(f"[corpus] FAILED queries (S2 rate-limited): {failed_queries}")


if __name__ == "__main__":
    main()
