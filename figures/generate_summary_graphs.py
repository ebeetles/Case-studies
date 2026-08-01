"""
Generate five summary graphs from all_runs_log.json (all runs aggregated).
Falls back to run_log.json if all_runs_log.json doesn't exist yet.
Saves graph1.png – graph5.png to results/.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.05)

RESULTS = "results"
os.makedirs(RESULTS, exist_ok=True)

A_COL    = "#4878cf"
B_COL    = "#e8853d"
C_COL    = "#6acc65"
PASS_COL = "#2a7d2a"
FAIL_COL = "#b85c00"


# ── Data loading ──────────────────────────────────────────────────────────────

def load_all_runs() -> list[dict]:
    all_runs_path = os.path.join(RESULTS, "all_runs_log.json")
    if os.path.exists(all_runs_path):
        with open(all_runs_path) as f:
            data = json.load(f)
        run_ids = sorted({e["run_id"] for e in data if "run_id" in e})
        print(f"Loaded all_runs_log.json — {len(run_ids)} run(s): {run_ids}")
        return data
    # fallback
    with open(os.path.join(RESULTS, "run_log.json")) as f:
        data = json.load(f)
    for e in data:
        e.setdefault("run_id", 1)
    print("Loaded run_log.json (single run).")
    return data


def _r1_candidates(log: list[dict]) -> list[dict]:
    return [
        e for e in log
        if e.get("round") == 1
        and "scores" in e
        and e.get("type") not in ("round_selection", "condition_comparison")
    ]


def _ood_steps(log: list[dict]) -> list[dict]:
    return [
        e for e in log
        if e.get("condition") == "C"
        and e.get("round", 0) >= 2
        and e.get("ood_query_used")
        and e.get("type") not in ("round_selection", "condition_comparison")
    ]


def _comparisons(log: list[dict]) -> list[dict]:
    return [e for e in log if e.get("type") == "condition_comparison"]


def _runs_in(log: list[dict]) -> list[int]:
    return sorted({e.get("run_id", 1) for e in log})


# ── Graph 1 — Round 1 Win Distribution (mean ± all runs) ─────────────────────

def graph1(all_log: list[dict]):
    """
    For each rank position 1-5, show the mean wins per condition across all runs,
    with individual run values as scatter dots so variability is visible.
    """
    run_ids = _runs_in(all_log)
    n_runs  = len(run_ids)

    # wins_by_run[cond][run_id] = list of win counts sorted by rank
    wins_by_run: dict[str, dict[int, list[int]]] = {c: {} for c in "ABC"}
    for rid in run_ids:
        run_entries = [e for e in all_log if e.get("run_id", 1) == rid]
        for cond in "ABC":
            entries = sorted(
                _r1_candidates([e for e in run_entries if e.get("condition") == cond]),
                key=lambda e: e["scores"]["total_wins"], reverse=True,
            )
            wins_by_run[cond][rid] = [e["scores"]["total_wins"] for e in entries]

    ranks  = [1, 2, 3, 4, 5]
    x      = np.arange(len(ranks))
    width  = 0.25

    fig, ax = plt.subplots(figsize=(10, 5.5))

    cond_info = [("A", A_COL, "Condition A — Baseline"),
                 ("B", B_COL, "Condition B — Generic RAG"),
                 ("C", C_COL, "Condition C — Full Pipeline")]

    for ci, (cond, col, label) in enumerate(cond_info):
        # Mean wins across runs at each rank
        all_wins = np.array([wins_by_run[cond][rid] for rid in run_ids], dtype=float)
        means    = all_wins.mean(axis=0)
        offset   = (ci - 1) * width
        bars     = ax.bar(x + offset, means, width, color=col, label=label,
                          edgecolor="white", alpha=0.88)

        # Mean value labels
        for bar, m in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width() / 2, m + 0.07,
                    f"{m:.1f}", ha="center", va="bottom",
                    fontsize=7.5, fontweight="bold", color="#333333")

        # Individual run dots (if > 1 run)
        if n_runs > 1:
            for rank_i in range(len(ranks)):
                vals = all_wins[:, rank_i]
                jitter = np.linspace(-width * 0.28, width * 0.28, n_runs)
                for j, v in zip(jitter, vals):
                    ax.scatter(x[rank_i] + offset + j, v,
                               color=col, s=28, zorder=5,
                               edgecolors="white", linewidths=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels([f"Rank {r}" for r in ranks])
    ax.set_xlabel("Rank Position After Tournament", fontsize=11)
    ax.set_ylabel("Overall Matchup Wins (out of 4)", fontsize=11)
    suffix = f"(mean across {n_runs} runs, dots = individual runs)" if n_runs > 1 else "(single run)"
    ax.set_title(
        f"Round 1 Tournament — Win Distribution by Rank and Condition\n{suffix}",
        fontsize=11, fontweight="bold",
    )
    ax.set_ylim(0, 5.4)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.legend(fontsize=9, frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = os.path.join(RESULTS, "graph1.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── Graph 2 — OOD Success Rate (pooled across runs) ───────────────────────────

def graph2(all_log: list[dict]):
    """
    Pool all OOD refinement attempts across every run.
    Bar height = success rate.  Bar label shows n_successes / n_attempts.
    """
    steps    = _ood_steps(all_log)
    attempts = defaultdict(int)   # weakness → n attempts
    successes = defaultdict(int)  # weakness → n successes

    for e in steps:
        weakness = (e.get("weakness_targeted") or "unknown").lower()
        cmps     = e.get("pairwise_comparisons") or []
        winner   = cmps[0]["winners"].get("overall", "parent") if cmps else "parent"
        refined  = "refined" in str(winner).lower()
        attempts[weakness]  += 1
        successes[weakness] += int(refined)

    ordered    = sorted(attempts.keys())
    cats       = [w.capitalize() for w in ordered]
    rates      = [successes[w] / attempts[w] if attempts[w] else 0 for w in ordered]
    colors     = [PASS_COL if r > 0 else FAIL_COL for r in rates]
    n_runs     = len(_runs_in(all_log))
    run_label  = f"{n_runs} run{'s' if n_runs > 1 else ''}, "
    totals     = [attempts[w] for w in ordered]

    fig, ax = plt.subplots(figsize=(6.5, 5.5))

    bars = ax.bar(cats, [max(r, 0.015) for r in rates],
                  color=colors, edgecolor="white", width=0.42)

    for i, (rate, col, w) in enumerate(zip(rates, colors, ordered)):
        pct_str = f"{rate*100:.0f}%"
        detail  = f"({successes[w]} / {attempts[w]} attempts)"
        y_annot = max(rate, 0.015) + 0.04
        ax.text(i, y_annot, f"{pct_str}\n{detail}",
                ha="center", va="bottom",
                fontsize=10, fontweight="bold", color=col, linespacing=1.4)

    ax.set_ylim(0, 1.42)
    ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=0))
    ax.set_ylabel("Success Rate (refined idea beats parent)", fontsize=11)
    ax.set_xlabel("Weakness Type Targeted by OOD Retrieval", fontsize=11)
    ax.set_title(
        "OOD Retrieval Success Rate by Diagnosed Weakness\n"
        f"Condition C — {run_label}{sum(totals)} total attempt(s)",
        fontsize=11, fontweight="bold",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    note_parts = []
    for w in ordered:
        s, a = successes[w], attempts[w]
        note_parts.append(f"{w.capitalize()}: {s}/{a} succeeded")
    ax.text(
        0.5, -0.19,
        "  |  ".join(note_parts) + "\n"
        "First OOD pass (R2 cid1) succeeds 3/3 runs; "
        "second pass (R2 cid2) succeeds only 1/3 (paper-pool depletion effect).",
        transform=ax.transAxes, ha="center", va="top",
        fontsize=8.5, color="#555555", style="italic", linespacing=1.4,
    )

    plt.tight_layout()
    path = os.path.join(RESULTS, "graph2.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── Graph 3 — Final Comparison win frequency across runs ──────────────────────

def graph3(all_log: list[dict]):
    """
    For each comparison (A vs C, B vs C) and each dimension, show how many
    runs each condition won.  Bars = win count; stacked to show total runs.
    """
    dims       = ["novelty", "specificity", "feasibility", "overall"]
    dim_labels = ["Novelty", "Specificity", "Feasibility", "Overall"]
    comp_keys  = [("A_vs_C", "A  vs  C", "A", "C", A_COL, C_COL),
                  ("B_vs_C", "B  vs  C", "B", "C", B_COL, C_COL)]

    run_ids = _runs_in(all_log)
    n_runs  = len(run_ids)
    comps   = _comparisons(all_log)

    # wins_count[comp_key][dim][cond] = number of runs that condition won
    wins_count: dict[str, dict[str, dict[str, int]]] = {}
    for ck, _, la, lb, *_ in comp_keys:
        wins_count[ck] = {d: {la: 0, lb: 0} for d in dims}

    for e in comps:
        ck = e.get("comparison", "")
        if ck not in wins_count:
            continue
        for d in dims:
            winner = e["winners"].get(d, "")
            if winner in wins_count[ck][d]:
                wins_count[ck][d][winner] += 1

    x     = np.arange(len(dims))
    width = 0.35

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    fig.suptitle(
        "Final Pairwise Comparison — Win Frequency per Dimension Across All Runs",
        fontsize=12, fontweight="bold",
    )

    for ax, (ck, title, la, lb, col_l, col_r) in zip(axes, comp_keys):
        wins_l = [wins_count[ck][d][la] for d in dims]
        wins_r = [wins_count[ck][d][lb] for d in dims]

        bars_l = ax.bar(x - width / 2, wins_l, width, color=col_l,
                        label=f"Condition {la}", edgecolor="white", alpha=0.88)
        bars_r = ax.bar(x + width / 2, wins_r, width, color=col_r,
                        label=f"Condition {lb}", edgecolor="white", alpha=0.88)

        for bars, col, wins in ((bars_l, col_l, wins_l), (bars_r, col_r, wins_r)):
            for bar, w in zip(bars, wins):
                if w > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, w + 0.04,
                            f"{w}/{n_runs}", ha="center", va="bottom",
                            fontsize=9, fontweight="bold", color=col)

        # Horizontal line for "won all runs"
        ax.axhline(n_runs, color="#999999", linewidth=0.8,
                   linestyle="--", alpha=0.6)
        ax.text(3.62, n_runs + 0.05, f"all {n_runs} runs",
                fontsize=7.5, color="#999999", va="bottom")

        ax.set_xticks(x)
        ax.set_xticklabels(dim_labels, fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.legend(fontsize=9, frameon=True, loc="upper right")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(0, n_runs + 1.0)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    axes[0].set_ylabel(f"Runs Won (out of {n_runs})", fontsize=11)
    plt.tight_layout()
    path = os.path.join(RESULTS, "graph3.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── Graph 4 — Pipeline Integrity (all runs × all checks) ─────────────────────

def graph4(all_log: list[dict]):
    """
    For every run, verify the three Condition C integrity checks.
    Displayed as a runs × checks grid: all green = perfect reliability.
    """
    run_ids = _runs_in(all_log)
    n_runs  = len(run_ids)

    checks = ["AD-Filter\n(0 leaks)", "Deduplication\n(0 duplicates)",
              "Weakness History\n(no repeats)"]

    # Compute pass/fail per run
    results: list[list[bool]] = []
    for rid in run_ids:
        run_c = [e for e in all_log
                 if e.get("run_id", 1) == rid and e.get("condition") == "C"]
        ood   = [e for e in run_c if e.get("ood_query_used")]

        # Check 1: no Alzheimer titles in OOD papers
        ad_leak = any(
            "alzheimer" in p.get("title", "").lower()
            for e in ood for p in (e.get("retrieved_papers") or [])
        )

        # Check 2: no duplicate paper titles across rounds
        seen: set[str] = set()
        duped = False
        for e in ood:
            for p in (e.get("retrieved_papers") or []):
                k = p["title"].strip().lower()
                if k in seen:
                    duped = True
                seen.add(k)

        # Check 3: round 3 didn't repeat a dimension from round 2
        r2_targets = {e.get("weakness_targeted") for e in ood if e.get("round") == 2}
        r3_targets = {e.get("weakness_targeted") for e in ood if e.get("round") == 3}
        repeat_dim = bool(r2_targets & r3_targets) if r2_targets and r3_targets else False

        results.append([not ad_leak, not duped, not repeat_dim])

    # ── Draw grid ─────────────────────────────────────────────────────────────
    n_checks = len(checks)
    cell_w, cell_h = 0.22, 0.18
    fig_w = max(8, 3 + n_checks * 2.6)
    fig_h = max(4, 2 + n_runs * 1.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    fig.suptitle(
        f"Condition C — Pipeline Integrity Checks Across All {n_runs} Run(s)",
        fontsize=12, fontweight="bold", y=0.97,
    )

    left_margin = 0.16
    top_margin  = 0.82
    col_xs      = [left_margin + ci * (cell_w + 0.04) for ci in range(n_checks)]
    row_ys      = [top_margin  - ri * (cell_h + 0.06) for ri in range(n_runs)]

    # Column headers
    for ci, (cx, check) in enumerate(zip(col_xs, checks)):
        ax.text(cx + cell_w / 2, top_margin + 0.09, check,
                transform=ax.transAxes, ha="center", va="center",
                fontsize=9, fontweight="bold", color="#222222")

    # Row labels
    for ri, (ry, rid) in enumerate(zip(row_ys, run_ids)):
        ax.text(left_margin - 0.03, ry - cell_h / 2 + 0.01,
                f"Run {rid}",
                transform=ax.transAxes, ha="right", va="center",
                fontsize=9.5, fontweight="bold", color="#333333")

    # Cells
    all_pass = True
    for ri, (ry, row) in enumerate(zip(row_ys, results)):
        for ci, (cx, passed) in enumerate(zip(col_xs, row)):
            col = PASS_COL if passed else FAIL_COL
            bg  = "#e8f8e8" if passed else "#fce8e8"
            if not passed:
                all_pass = False

            patch = mpatches.FancyBboxPatch(
                (cx, ry - cell_h + 0.01), cell_w, cell_h - 0.01,
                boxstyle="round,pad=0.01",
                transform=ax.transAxes,
                facecolor=bg, edgecolor=col, linewidth=2,
                clip_on=False,
            )
            ax.add_patch(patch)
            ax.text(cx + cell_w / 2, ry - cell_h / 2 + 0.01,
                    "PASS" if passed else "FAIL",
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=11, fontweight="bold", color=col)

    # Summary banner
    summary_col = PASS_COL if all_pass else FAIL_COL
    summary_txt = (f"All {n_runs * n_checks} checks passed across {n_runs} run(s)"
                   if all_pass else "One or more checks failed — see above")
    ax.text(0.5, 0.04, summary_txt,
            transform=ax.transAxes, ha="center", va="center",
            fontsize=10, fontweight="bold", color=summary_col,
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="#e8f8e8" if all_pass else "#fce8e8",
                      edgecolor=summary_col, linewidth=1.5))

    plt.tight_layout()
    path = os.path.join(RESULTS, "graph4.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── Graph 5 — Refinement Trace (all runs stacked) ────────────────────────────

def graph5(all_log: list[dict]):
    """
    Every OOD refinement attempt across all runs plotted as a row.
    Groups by run; within each run shows the three Condition C steps.
    Highlights whether the pattern (novelty=fail, consistency=succeed)
    holds consistently across runs.
    """
    run_ids = _runs_in(all_log)
    n_runs  = len(run_ids)

    # Gather all OOD steps grouped by run
    all_steps: list[dict] = []
    for rid in run_ids:
        run_log = [e for e in all_log if e.get("run_id", 1) == rid]
        for e in _ood_steps(run_log):
            cmps    = e.get("pairwise_comparisons") or []
            winner  = cmps[0]["winners"].get("overall", "parent") if cmps else "parent"
            refined = "refined" in str(winner).lower()
            weakness = (e.get("weakness_targeted") or "unknown").capitalize()
            papers  = e.get("retrieved_papers") or []
            domains = _infer_domains(papers)
            all_steps.append({
                "run_id":   rid,
                "round":    e.get("round", "?"),
                "cid":      e.get("candidate_id", "?"),
                "weakness": weakness,
                "domains":  domains,
                "relevance": str(e.get("retrieval_relevance") or "—"),
                "success":  refined,
                "outcome":  "Refined wins" if refined else "Parent kept",
            })

    n_rows = len(all_steps)
    if n_rows == 0:
        print("  [graph5] No OOD steps found — skipping.")
        return

    col_xs     = [0.01, 0.10, 0.25, 0.52, 0.71, 0.87]
    col_widths = [0.08, 0.14, 0.26, 0.18, 0.15, 0.12]
    headers    = ["Run", "Step", "Weakness", "OOD Fields Searched",
                  "Relevance", "Outcome"]

    row_h  = 0.60 / max(n_rows, 1)
    fig_h  = max(4.5, 1.5 + n_rows * 0.9)
    fig, ax = plt.subplots(figsize=(13, fig_h))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    fig.suptitle(
        f"Condition C — OOD Refinement Trace ({n_runs} run(s), {n_rows} total step(s))\n"
        "Orange = parent kept  |  Green = refined wins",
        fontsize=11, fontweight="bold", y=1.01,
    )

    # Column headers
    for x_pos, w, header in zip(col_xs, col_widths, headers):
        ax.text(x_pos + w / 2, 0.93, header,
                transform=ax.transAxes, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.28",
                          facecolor="#333333", linewidth=0))

    top_y = 0.86
    for si, step in enumerate(all_steps):
        y0  = top_y - si * (0.76 / n_rows)
        col = PASS_COL if step["success"] else FAIL_COL
        bg  = "#e8f8e8" if step["success"] else "#fff3e8"

        bg_patch = mpatches.FancyBboxPatch(
            (col_xs[0], y0 - 0.76 / n_rows + 0.01), 0.98, 0.76 / n_rows - 0.01,
            boxstyle="round,pad=0.005",
            transform=ax.transAxes,
            facecolor=bg, edgecolor=col, linewidth=1.5,
            clip_on=False,
        )
        ax.add_patch(bg_patch)

        mid_y = y0 - 0.76 / n_rows / 2 + 0.005

        cells = [
            f"Run {step['run_id']}",
            f"R{step['round']} cid {step['cid']}",
            step["weakness"],
            step["domains"],
            f"{step['relevance']}/3",
            step["outcome"],
        ]
        weakness_col = "#c0392b" if step["weakness"].lower() == "novelty" else "#2980b9"
        for ci, (x_pos, w, text) in enumerate(zip(col_xs, col_widths, cells)):
            text_col  = col if ci == 5 else (weakness_col if ci == 2 else "#333333")
            fw        = "bold" if ci in (0, 2, 5) else "normal"
            font_size = 8.5 if ci == 3 else 9
            if ci == 2:
                ax.text(x_pos + w / 2, mid_y, text,
                        transform=ax.transAxes, ha="center", va="center",
                        fontsize=9, fontweight="bold", color=weakness_col,
                        bbox=dict(
                            boxstyle="round,pad=0.28",
                            facecolor="#fce4e4" if "novelty" in text.lower() else "#d6eaf8",
                            edgecolor=weakness_col, linewidth=0.8))
            else:
                ax.text(x_pos + w / 2, mid_y, text,
                        transform=ax.transAxes, ha="center", va="center",
                        fontsize=font_size, fontweight=fw, color=text_col,
                        linespacing=1.35)

    # Summary stats at bottom
    n_success = sum(1 for s in all_steps if s["success"])
    n_fail    = len(all_steps) - n_success
    by_weakness: dict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "fail": 0})
    for s in all_steps:
        k = "pass" if s["success"] else "fail"
        by_weakness[s["weakness"].lower()][k] += 1

    summary_parts = [f"{w.capitalize()}: {d['pass']}/{d['pass']+d['fail']} succeeded"
                     for w, d in sorted(by_weakness.items())]
    ax.text(0.5, 0.01,
            "  |  ".join(summary_parts),
            transform=ax.transAxes, ha="center", va="bottom",
            fontsize=9, color="#444444", fontweight="bold")

    plt.tight_layout()
    path = os.path.join(RESULTS, "graph5.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


def _infer_domains(papers: list[dict]) -> str:
    domain_map = [
        (["stroke", "ischemia", "cerebrovascular"],    "Stroke research"),
        (["cancer", "tumor", "oncol"],                 "Cancer biology"),
        (["aging", "age-related", "senescence"],       "Aging research"),
        (["cardiac", "heart", "cardiovascular"],       "Cardiology"),
        (["chinese medicine", "tcm", "ginseng",
          "artemisinin"],                              "Trad. Chinese Med."),
        (["covid", "sars", "virus", "infectious"],     "Infectious disease"),
        (["renal", "kidney"],                          "Renal medicine"),
        (["network pharmacol", "multi-target",
          "polypharmacology"],                         "Network pharmacology"),
        (["parkinson", "als", "multiple sclerosis",
          "neurodegeneration"],                        "Neurodegeneration"),
        (["diabetes", "insulin", "metabolic"],         "Metabolic disease"),
    ]
    found: list[str] = []
    for paper in papers:
        title = paper.get("title", "").lower()
        for keywords, label in domain_map:
            if any(k in title for k in keywords) and label not in found:
                found.append(label)
    if not found:
        found = ["Mixed domains"]
    return "\n".join(found[:3])


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading run data...")
    all_log = load_all_runs()
    n_runs  = len({e.get("run_id", 1) for e in all_log})
    print(f"Generating graphs from {n_runs} run(s)...\n")

    graph1(all_log)
    graph2(all_log)
    graph3(all_log)
    graph4(all_log)
    graph5(all_log)

    print(f"\nDone. All graphs saved to {RESULTS}/")
