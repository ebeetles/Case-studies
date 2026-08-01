"""
Exploratory probe: can the exploration/exploitation tradeoff in Condition C
(OOD retrieval-guided beam search) be steered by simple pipeline knobs?

Varies one knob at a time, 3 runs per setting:
  - temperature: 0 (baseline, reused from results/all_runs_log.json), 0.7, 1.0
  - max_rounds:  1, 2, 3 (baseline, reused) — i.e. less exploitation/refinement

Novelty-as-a-ranking-criterion is NOT varied here — removing it would require
changing rank_candidates_pairwise's win tally, a bigger and riskier change to
the core beam-selection logic. Out of scope for this quick probe.

For each configuration, computes the same two diversity metrics as
measure_diversity.py (within-condition pairwise cosine similarity, mean
centroid distance) over the 3 resulting Condition C hypotheses.

This script calls the Groq (generation) and PubMed (retrieval) APIs directly —
each configuration is a full 1-3 round Condition C pipeline run, done 3x.
Uses OpenAI text-embedding-3-small for the diversity metrics (same as
measure_diversity.py).
"""

import json
import os
from itertools import combinations

import numpy as np
from openai import OpenAI

from pipeline import run_pipeline
from measure_diversity import (
    build_embedding_text,
    embed_texts,
    within_condition_pairwise_similarity,
    centroid_distance,
    EMBEDDING_MODEL,
)

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results", "probe_results.json")
BASELINE_LOG_PATH = os.path.join(os.path.dirname(__file__), "results", "all_runs_log.json")

CONFIGS = [
    # (label, temperature, max_rounds)
    ("temp=0.0, rounds=3 (baseline)", 0.0, 3),  # reused from existing logs
    ("temp=0.7, rounds=3", 0.7, 3),
    ("temp=1.0, rounds=3", 1.0, 3),
    ("temp=0.0, rounds=1", 0.0, 1),
    ("temp=0.0, rounds=2", 0.0, 2),
]
N_RUNS_PER_CONFIG = 3


def load_baseline_hypotheses() -> list[dict]:
    """Reuse the 3 existing Condition C runs (temp=0, rounds=3) instead of re-running."""
    with open(BASELINE_LOG_PATH) as f:
        data = json.load(f)
    idea_records = [r for r in data if "idea" in r and r["condition"] == "C"]
    by_run: dict[int, list] = {}
    for r in idea_records:
        by_run.setdefault(r["run_id"], []).append(r)

    hyps = []
    for run_id, recs in sorted(by_run.items()):
        max_round = max(r["round"] for r in recs)
        final_recs = [r for r in recs if r["round"] == max_round]
        winner = next(r for r in final_recs if r["candidate_id"] == 1)
        idea = winner.get("idea_after_refinement") or winner["idea"]
        hyps.append(idea)
    return hyps[:N_RUNS_PER_CONFIG]


def run_config(temperature: float, max_rounds: int) -> list[dict]:
    hyps = []
    for i in range(N_RUNS_PER_CONFIG):
        print(f"  Run {i + 1}/{N_RUNS_PER_CONFIG} (temperature={temperature}, max_rounds={max_rounds})...")
        idea, _log = run_pipeline(condition="C", temperature=temperature, max_rounds=max_rounds)
        hyps.append(idea)
    return hyps


def compute_metrics(hyps: list[dict], client: OpenAI) -> dict:
    texts = [build_embedding_text(h) for h in hyps]
    embeddings = embed_texts(texts, EMBEDDING_MODEL, client)
    return {
        "n": len(hyps),
        "within_pairwise_cosine_sim": within_condition_pairwise_similarity(embeddings),
        "mean_centroid_distance": centroid_distance(embeddings),
        "drugs_mentioned": [h["method"][:60] for h in hyps],
    }


def main():
    client = OpenAI()

    results = {}

    for label, temperature, max_rounds in CONFIGS:
        print(f"\n=== Config: {label} ===")
        if temperature == 0.0 and max_rounds == 3:
            hyps = load_baseline_hypotheses()
            print(f"  Reusing {len(hyps)} existing runs from all_runs_log.json")
        else:
            hyps = run_config(temperature, max_rounds)

        metrics = compute_metrics(hyps, client)
        results[label] = metrics
        print(f"  within_pairwise_sim={metrics['within_pairwise_cosine_sim']:.4f}  "
              f"centroid_dist={metrics['mean_centroid_distance']:.4f}")

    print("\n" + "=" * 78)
    print("EXPLORATION/EXPLOITATION PROBE — Condition C")
    print("=" * 78)
    print(f"{'Config':<30} {'N':<4} {'Within-pair sim':<18} {'Centroid dist'}")
    print("-" * 78)
    for label, m in results.items():
        print(f"{label:<30} {m['n']:<4} {m['within_pairwise_cosine_sim']:<18.4f} {m['mean_centroid_distance']:.4f}")

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
