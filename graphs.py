from __future__ import annotations

"""
Graphs module: generates all four output artefacts for the case study.

Graph 1 — Final Idea Quality Across Conditions  (grouped bar chart)
Graph 2 — Score Improvement Across Rounds, Condition C  (line chart)
Graph 3 — Decomposed Novelty by Condition  (stacked bar chart)
Graph 4 — Gap-Filling Retrieval Trace, Condition C  (plain text file)

All visual graphs use seaborn styling and are saved to results/.
"""

import os
import re

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

RESULTS_DIR = "results"
sns.set_theme(style="whitegrid")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _final_entry(log: list[dict], condition: str) -> dict:
    """Return the final logged entry for a condition (round 1 for A, round 3 for B/C)."""
    if not log:
        raise RuntimeError(f"No log entries for condition {condition}.")
    candidates = [
        e for e in log
        if e.get("type") != "round_selection"
        and e.get("type") != "condition_comparison"
        and "scores" in e
    ]
    if condition == "A":
        return max(candidates, key=lambda e: e["scores"]["composite"])
    r3 = [e for e in candidates if e["round"] == 3]
    if not r3:
        raise RuntimeError(f"Condition {condition} missing round 3 entry.")
    return r3[-1]


def _entries_for_condition(log: list[dict], round_num: int) -> list[dict]:
    """All log entries for a given round number."""
    return [
        e for e in log
        if e["round"] == round_num
        and e.get("type") != "round_selection"
        and "scores" in e
    ]


def _parse_novelty_components(novelty_text: str) -> dict:
    """
    Extract per-component YES/NO from the novelty judge response.

    The judge answers three numbered questions; we look for YES or NO at the
    start of each numbered answer line.
    Returns {"problem": bool, "method": bool, "contribution": bool}.
    """
    components = {"problem": False, "method": False, "contribution": False}
    keys = list(components.keys())

    lines = novelty_text.splitlines()
    for line in lines:
        m = re.match(r"^\s*(\d)\.", line)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(keys):
                components[keys[idx]] = bool(re.search(r"\byes\b", line, re.IGNORECASE))
    return components


def _best_entry_round(log: list[dict], round_num: int) -> dict:
    """Return the highest-composite entry in a given round."""
    entries = _entries_for_condition(log, round_num)
    if not entries:
        raise RuntimeError(f"No entries for round {round_num}.")
    return max(entries, key=lambda e: e["scores"]["composite"])


# ── Graph 1: Final idea quality across conditions ─────────────────────────────

def graph1_condition_comparison(log_a, log_b, log_c):
    """
    Grouped bar chart comparing final idea quality across conditions.

    All bars are oriented so higher = better:
      Novelty:      raw score (0-3), normalised /3
      Consistency:  (max_gaps - gaps) / max_gaps  — fewer gaps is better
      Feasibility:  (4 - feasibility) / 3         — lower severity is better
    """
    final_a = _final_entry(log_a, "A")
    final_b = _final_entry(log_b, "B")
    final_c = _final_entry(log_c, "C")

    all_gaps = []
    for log in (log_a, log_b, log_c):
        for e in log:
            if "scores" in e and "gaps" in e["scores"]:
                all_gaps.append(e["scores"]["gaps"])
    max_gaps = max(all_gaps) if all_gaps else 1

    def extract(entry):
        s = entry["scores"]
        if "specificity" in s:
            max_wins = max(
                e["scores"].get("overall_wins", 0)
                for log in (log_a, log_b, log_c)
                for e in log if "scores" in e
            ) or 1
            return [
                s.get("novelty", 0) / max_wins,
                s.get("specificity", 0) / max_wins,
                s.get("feasibility", 0) / max_wins,
            ]
        novelty_norm      = s["novelty"] / 3
        consistency_norm  = (max_gaps - s["gaps"]) / max_gaps if max_gaps > 0 else 0
        feasibility_norm  = (4 - s["feasibility"]) / 3
        return [novelty_norm, consistency_norm, feasibility_norm]

    vals_a = extract(final_a)
    vals_b = extract(final_b)
    vals_c = extract(final_c)

    use_pairwise = "specificity" in final_a["scores"]
    dims  = (
        ["Novelty wins", "Specificity wins", "Feasibility wins"]
        if use_pairwise
        else ["Novelty", "Consistency\n(inverted)", "Feasibility\n(inverted)"]
    )
    x     = np.arange(len(dims))
    width = 0.25

    fig, ax = plt.subplots(figsize=(9, 6))
    bars_a = ax.bar(x - width,     vals_a, width, label="A: Baseline",     color="#4878cf")
    bars_b = ax.bar(x,             vals_b, width, label="B: Generic RAG",  color="#e8853d")
    bars_c = ax.bar(x + width,     vals_c, width, label="C: Full Pipeline",color="#6acc65")

    ax.set_ylabel("Normalised Score (higher = better)")
    ax.set_title("Final Idea Quality Across Conditions")
    ax.set_xticks(x)
    ax.set_xticklabels(dims)
    ax.set_ylim(0, 1.2)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
    ax.legend()

    for bars in (bars_a, bars_b, bars_c):
        ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=8)

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, "graph1_condition_comparison.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved {path}")


# ── Graph 2: Score improvement across rounds (Condition C) ────────────────────

def graph2_round_improvement(log_c):
    """
    Line chart showing how scores evolve over rounds 1→2→3 in Condition C.

    Three lines (all normalised to 0-1):
      Novelty:      score / 3
      Consistency:  (3 - gaps) / 3   (clamped to [0,1])
      Feasibility:  (4 - feasibility) / 3
    """
    rounds = [1, 2, 3]
    novelty_by_round      = []
    consistency_by_round  = []
    feasibility_by_round  = []

    for r in rounds:
        entry = _best_entry_round(log_c, r)
        s = entry["scores"]
        if "specificity" in s:
            max_w = max(
                e["scores"].get("overall_wins", 0)
                for e in log_c if "scores" in e
            ) or 1
            novelty_by_round.append(s.get("novelty", 0) / max_w)
            consistency_by_round.append(s.get("specificity", 0) / max_w)
            feasibility_by_round.append(s.get("feasibility", 0) / max_w)
        else:
            novelty_by_round.append(s["novelty"] / 3)
            consistency_by_round.append(max(0, (3 - s["gaps"]) / 3))
            feasibility_by_round.append((4 - s["feasibility"]) / 3)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(rounds, novelty_by_round,     marker="o", label="Novelty (score/3)",          color="#4878cf")
    cons_label = "Specificity wins" if "specificity" in _best_entry_round(log_c, 1)["scores"] else "Consistency ((3-gaps)/3)"
    ax.plot(rounds, consistency_by_round, marker="s", label=cons_label, color="#6acc65")
    ax.plot(rounds, feasibility_by_round, marker="^", label="Feasibility ((4-feas)/3)",    color="#e8853d")

    ax.set_xlabel("Round")
    ax.set_ylabel("Normalised Score (0-1, higher = better)")
    ax.set_title("Score Improvement Across Rounds (Full Pipeline — Condition C)")
    ax.set_xticks(rounds)
    ax.set_ylim(0, 1.15)
    ax.legend()

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, "graph2_round_improvement.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved {path}")


# ── Graph 3: Decomposed novelty breakdown ─────────────────────────────────────

def graph3_novelty_breakdown(log_a, log_b, log_c):
    """
    Stacked bar chart breaking down novelty into its three components
    (Problem novel, Method novel, Contribution novel) for each condition's
    final idea.
    """
    def get_components(log, condition):
        entry = _final_entry(log, condition)
        s = entry["scores"]
        if "novelty_text" not in s:
            wins = entry.get("ranking", {}).get("dimension_wins", s)
            return {
                "problem": wins.get("novelty", 0) > 0,
                "method": wins.get("specificity", 0) > 0,
                "contribution": wins.get("feasibility", 0) > 0,
            }
        return _parse_novelty_components(s["novelty_text"])

    comps_a = get_components(log_a, "A")
    comps_b = get_components(log_b, "B")
    comps_c = get_components(log_c, "C")

    conditions = ["A: Baseline", "B: Generic RAG", "C: Full Pipeline"]
    problem_vals      = [int(comps_a["problem"]),      int(comps_b["problem"]),      int(comps_c["problem"])]
    method_vals       = [int(comps_a["method"]),       int(comps_b["method"]),       int(comps_c["method"])]
    contribution_vals = [int(comps_a["contribution"]), int(comps_b["contribution"]), int(comps_c["contribution"])]

    x = np.arange(len(conditions))
    width = 0.5

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x, problem_vals,      width,                                         label="Problem novel",      color="#4878cf")
    bars2 = ax.bar(x, method_vals,       width, bottom=problem_vals,                   label="Method novel",       color="#6acc65")
    bars3 = ax.bar(x, contribution_vals, width, bottom=[p + m for p, m in zip(problem_vals, method_vals)],
                   label="Contribution novel", color="#e8853d")

    ax.set_ylabel("YES count (0 or 1 per component)")
    ax.set_title("Decomposed Novelty by Condition")
    ax.set_xticks(x)
    ax.set_xticklabels(conditions)
    ax.set_ylim(0, 3.5)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.legend()

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, "graph3_novelty_breakdown.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved {path}")


# ── Graph 4: Gap-filling retrieval trace (Condition C, plain text) ────────────

def graph4_retrieval_trace(log_c):
    """
    Write a plain-text summary of every targeted retrieval in Condition C.
    Shows what weakness was diagnosed, what query was used, which papers
    were retrieved, and whether scores improved.
    """
    path = os.path.join(RESULTS_DIR, "graph4_retrieval_trace.txt")

    def _candidate_entries(log: list[dict], round_num: int) -> list[dict]:
        return [
            e for e in log
            if e.get("round") == round_num
            and e.get("type") not in ("round_selection", "condition_comparison")
            and "scores" in e
        ]

    r2_entries = [
        e for e in _candidate_entries(log_c, 2) if e.get("weakness_targeted")
    ]
    r3_entries = [
        e for e in _candidate_entries(log_c, 3) if e.get("weakness_targeted")
    ]
    r1_entries = {e["candidate_id"]: e for e in _candidate_entries(log_c, 1)}

    def fmt_scores(s: dict) -> str:
        if not s:
            return "(none)"
        if "novelty_wins" in s:
            return (
                f"novelty_wins={s.get('novelty_wins', 0)}, "
                f"specificity_wins={s.get('specificity_wins', 0)}, "
                f"feasibility_wins={s.get('feasibility_wins', 0)}"
            )
        if "specificity" in s:
            return (
                f"novelty_wins={s.get('novelty', 0)}, "
                f"specificity_wins={s.get('specificity', 0)}, "
                f"feasibility_wins={s.get('feasibility', 0)}"
            )
        return f"novelty={s['novelty']}, gaps={s['gaps']}, feasibility={s['feasibility']}"

    def _metric(s: dict) -> float:
        return s.get(
            "total_wins",
            s.get("overall_wins", s.get("composite", 0)),
        )

    def improvement(before: dict, after: dict) -> str:
        b, a = _metric(before), _metric(after)
        if a > b:
            return "improved"
        if a == b:
            return "same"
        return "worse"

    lines = []

    for e in r2_entries:
        cid    = e["candidate_id"]
        before = e.get("ranking_before") or r1_entries.get(cid, {}).get("scores", {})
        after  = e.get("ranking_after") or e["scores"]
        papers = e.get("retrieved_papers") or []

        lines.append(f"ROUND 2, CANDIDATE {cid}:")
        lines.append(f"  Weakness diagnosed: {e['weakness_targeted']}")
        lines.append(f"  Query used: \"{e.get('targeted_query', '')}\"")
        rel = e.get("retrieval_relevance")
        if rel is not None:
            lines.append(f"  Retrieval relevance: {rel}/3")
        lines.append(  "  Papers retrieved:")
        for j, p in enumerate(papers, 1):
            lines.append(f"    {j}. {p.get('title', '(no title)')}")
        lines.append(f"  Score before: {fmt_scores(before)}")
        lines.append(f"  Score after:  {fmt_scores(after)}")
        lines.append(f"  Change: {improvement(before, after)}")
        lines.append("")

    for e in r3_entries:
        r2_best = max(
            _candidate_entries(log_c, 2),
            key=lambda x: _metric(x["scores"]),
            default=None,
        )
        before = e.get("ranking_before") or (r2_best["scores"] if r2_best else {})
        after  = e.get("ranking_after") or e["scores"]
        papers = e.get("retrieved_papers") or []

        lines.append("ROUND 3, FINAL CANDIDATE:")
        lines.append(f"  Weakness diagnosed: {e['weakness_targeted']}")
        lines.append(f"  Query used: \"{e.get('targeted_query', '')}\"")
        rel = e.get("retrieval_relevance")
        if rel is not None:
            lines.append(f"  Retrieval relevance: {rel}/3")
        lines.append(  "  Papers retrieved:")
        for j, p in enumerate(papers, 1):
            lines.append(f"    {j}. {p.get('title', '(no title)')}")
        lines.append(f"  Score before: {fmt_scores(before)}")
        lines.append(f"  Score after:  {fmt_scores(after)}")
        lines.append(f"  Change: {improvement(before, after)}")
        lines.append("")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"Saved {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def generate_all_graphs(log_a: list[dict], log_b: list[dict], log_c: list[dict]):
    """Generate and save all four output artefacts."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("\nGenerating Graph 1: condition comparison...")
    graph1_condition_comparison(log_a, log_b, log_c)

    print("Generating Graph 2: round improvement (Condition C)...")
    graph2_round_improvement(log_c)

    print("Generating Graph 3: novelty breakdown...")
    graph3_novelty_breakdown(log_a, log_b, log_c)

    print("Generating Graph 4: retrieval trace (Condition C)...")
    graph4_retrieval_trace(log_c)

    print("\nAll graphs saved to results/")
