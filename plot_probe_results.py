"""
Plot the exploration/exploitation probe results (results/probe_results.json)
produced by probe_exploration_tradeoff.py.

Bar chart: within-condition pairwise cosine similarity per config, with the
temp=0/rounds=3 baseline highlighted.
"""

import json
import os

import matplotlib.pyplot as plt

RESULTS_DIR = "results"
PROBE_RESULTS_PATH = os.path.join(RESULTS_DIR, "probe_results.json")


def main():
    with open(PROBE_RESULTS_PATH) as f:
        results = json.load(f)

    labels = list(results.keys())
    sims = [results[l]["within_pairwise_cosine_sim"] for l in labels]
    dists = [results[l]["mean_centroid_distance"] for l in labels]

    colors = ["#c0392b" if "baseline" in l else "#2980b9" for l in labels]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].bar(range(len(labels)), sims, color=colors)
    axes[0].set_xticks(range(len(labels)))
    axes[0].set_xticklabels(labels, rotation=30, ha="right")
    axes[0].set_ylabel("Mean within-pair cosine similarity")
    axes[0].set_title("Concentration (higher = less diverse)")
    axes[0].set_ylim(0, 1)
    for i, v in enumerate(sims):
        axes[0].text(i, v + 0.02, f"{v:.3f}", ha="center", fontsize=9)

    axes[1].bar(range(len(labels)), dists, color=colors)
    axes[1].set_xticks(range(len(labels)))
    axes[1].set_xticklabels(labels, rotation=30, ha="right")
    axes[1].set_ylabel("Mean centroid distance")
    axes[1].set_title("Spread (higher = more diverse)")
    for i, v in enumerate(dists):
        axes[1].text(i, v + 0.003, f"{v:.3f}", ha="center", fontsize=9)

    fig.suptitle("Condition C: exploration/exploitation probe", fontsize=13)
    fig.tight_layout()

    out_path = os.path.join(RESULTS_DIR, "probe_diversity.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
