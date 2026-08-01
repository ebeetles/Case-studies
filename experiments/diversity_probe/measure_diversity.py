from __future__ import annotations

"""
Embedding-based diversity measurement for Alzheimer's drug-repurposing hypotheses.

Follows Tang & Yang (2026), "AI Research Agents Narrow Scientific Exploration"
(arXiv:2605.27905): computes within-condition pairwise cosine similarity and
centroid distance per condition.

Data source: results/all_runs_log.json
Embedding model: OpenAI text-embedding-3-small (swap via EMBEDDING_MODEL env var)

Hypothesis extraction logic:
  - Condition A (zero-shot): round=1, highest total_wins per run
  - Conditions B & C (RAG / OOD beam search): final round, candidate_id=1 (survivor)

Embedding text = method + " " + contribution
  (method = core mechanism claim; contribution = rationale/expected impact)
  Problem field is excluded — it is generic framing shared across conditions.
"""

import json
import os
from collections import defaultdict
from itertools import combinations

import numpy as np
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_PATH = os.path.join("results", "all_runs_log.json")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

# ---------------------------------------------------------------------------
# Step 1: Extract final hypotheses
# ---------------------------------------------------------------------------

def extract_final_hypotheses(data: list[dict]) -> dict[str, list[dict]]:
    """Return {condition: [idea_dict, ...]} for the winner of each run."""
    idea_records = [r for r in data if "idea" in r]

    by_cond_run: dict[tuple, list] = defaultdict(list)
    for r in idea_records:
        by_cond_run[(r["condition"], r["run_id"])].append(r)

    hypotheses: dict[str, list] = defaultdict(list)
    for (cond, run_id), recs in sorted(by_cond_run.items()):
        max_round = max(r["round"] for r in recs)
        final_recs = [r for r in recs if r["round"] == max_round]

        if cond == "A":
            # Zero-shot: only one round; winner = most overall wins
            winner = max(final_recs, key=lambda x: x["ranking"]["total_wins"])
            idea = winner["idea"]
        else:
            # B / C: iterative refinement; candidate_id=1 is the surviving hypothesis
            winner = next(r for r in final_recs if r["candidate_id"] == 1)
            idea = winner.get("idea_after_refinement") or winner["idea"]

        hypotheses[cond].append(
            {
                "run_id": run_id,
                "condition": cond,
                "problem": idea["problem"],
                "method": idea["method"],
                "contribution": idea["contribution"],
            }
        )

    return dict(hypotheses)


# ---------------------------------------------------------------------------
# Step 2: Build embedding input text
# ---------------------------------------------------------------------------

def build_embedding_text(hyp: dict) -> str:
    """Concatenate method and contribution; exclude problem (generic framing)."""
    return hyp["method"].strip() + " " + hyp["contribution"].strip()


# ---------------------------------------------------------------------------
# Step 3: Embed
# ---------------------------------------------------------------------------

def embed_texts(texts: list[str], model: str, client: OpenAI) -> np.ndarray:
    response = client.embeddings.create(input=texts, model=model)
    vectors = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
    return np.array(vectors, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


# ---------------------------------------------------------------------------
# Step 4: Diversity metrics
# ---------------------------------------------------------------------------

def within_condition_pairwise_similarity(embeddings: np.ndarray) -> float | None:
    """Mean cosine similarity over all unique pairs. None if fewer than 2 hypotheses."""
    n = len(embeddings)
    if n < 2:
        return None
    sims = [
        cosine_similarity(embeddings[i], embeddings[j])
        for i, j in combinations(range(n), 2)
    ]
    return float(np.mean(sims))


def centroid_distance(embeddings: np.ndarray) -> float | None:
    """
    Mean cosine distance (1 - cosine_similarity) from each hypothesis to the
    condition centroid (mean embedding). Higher = more spread / diverse.
    Returns None if fewer than 2 hypotheses.
    """
    if len(embeddings) < 2:
        return None
    centroid = embeddings.mean(axis=0)
    dists = [1.0 - cosine_similarity(e, centroid) for e in embeddings]
    return float(np.mean(dists))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    client = OpenAI()  # reads OPENAI_API_KEY from environment

    print(f"Embedding model: {EMBEDDING_MODEL}\n")

    # Load data
    with open(DATA_PATH) as f:
        data = json.load(f)

    hypotheses = extract_final_hypotheses(data)

    # Print what we found
    print("=== Extracted hypotheses ===")
    for cond in sorted(hypotheses):
        print(f"\nCondition {cond} ({len(hypotheses[cond])} hypotheses):")
        for h in hypotheses[cond]:
            drug_hint = h["method"][:80].replace("\n", " ")
            print(f"  Run {h['run_id']}: {drug_hint}...")

    # Build ordered list for a single batch API call
    ordered: list[tuple[str, int, dict]] = []
    for cond in sorted(hypotheses):
        for i, h in enumerate(hypotheses[cond]):
            ordered.append((cond, i, h))

    texts = [build_embedding_text(h) for _, _, h in ordered]

    print(f"\nEmbedding {len(texts)} hypotheses...")
    all_embeddings = embed_texts(texts, EMBEDDING_MODEL, client)
    print("Done.\n")

    # Split embeddings back by condition
    cond_embeddings: dict[str, np.ndarray] = defaultdict(list)
    for (cond, _, _), vec in zip(ordered, all_embeddings):
        cond_embeddings[cond].append(vec)
    cond_embeddings = {c: np.array(vs) for c, vs in cond_embeddings.items()}

    # Compute metrics
    results = {}
    for cond in sorted(cond_embeddings):
        emb = cond_embeddings[cond]
        results[cond] = {
            "n": len(emb),
            "within_pairwise_cosine_sim": within_condition_pairwise_similarity(emb),
            "mean_centroid_distance": centroid_distance(emb),
        }

    # Report
    print("=== Diversity Metrics ===")
    print(
        f"{'Condition':<12} {'N':<5} {'Within-pair sim (mean)':<26} {'Centroid dist (mean)'}"
    )
    print("-" * 68)
    cond_labels = {"A": "A (zero-shot)", "B": "B (generic RAG)", "C": "C (OOD beam)"}
    for cond in sorted(results):
        r = results[cond]
        sim = f"{r['within_pairwise_cosine_sim']:.4f}" if r["within_pairwise_cosine_sim"] is not None else "N/A"
        dist = f"{r['mean_centroid_distance']:.4f}" if r["mean_centroid_distance"] is not None else "N/A"
        print(f"{cond_labels.get(cond, cond):<22} {r['n']:<5} {sim:<26} {dist}")

    print()
    print("Interpretation (Tang & Yang methodology):")
    print("  Within-pair sim: higher = more concentrated (less diverse)")
    print("  Centroid dist:   higher = more spread (more diverse)")

    # Save results
    out_path = os.path.join("results", "diversity_probe", "diversity_metrics.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    payload = {
        "embedding_model": EMBEDDING_MODEL,
        "conditions": {
            cond: {
                **results[cond],
                "hypotheses": [
                    {
                        "run_id": h["run_id"],
                        "embedding_text": build_embedding_text(h),
                    }
                    for h in hypotheses[cond]
                ],
            }
            for cond in sorted(results)
        },
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
