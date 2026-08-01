from __future__ import annotations

"""
Rubric-quality validation experiment (hypothesis_validation_sources.md).

Part 1: build 15 tiered + 10 degraded (5 Tier-1 x 2) = 25 anonymized hypotheses.
Part 2: run rubric / holistic / pairwise judges blind (text only, no labels).
Part 3: analyze tier recovery, dimension localization, stability. No p-values
         / confidence intervals (n too small) — raw rates and deltas only.

Output: results/validation/*.json (raw), results/validation/summary.md (tables).
"""

import json
import os
import random
import sys
import time
from itertools import combinations
from pathlib import Path

from main import _load_dotenv, _sanitize_env

_load_dotenv()
_sanitize_env()

from validation_data import TIERED_HYPOTHESES, TIER1_SOURCE_IDS
from validation_degrade import specificity_degrade, novelty_degrade
from validation_judge import (
    rubric_score_novelty,
    rubric_score_specificity,
    holistic_score,
    pairwise_compare,
)
from judge import get_judge_model
from generator import get_generator_model

OUT_DIR = Path("results/validation")
SEED = 42
N_REPEATS = 2


def log(msg: str) -> None:
    print(f"[validate] {msg}", flush=True)


def _save(name: str, data) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / name, "w") as f:
        json.dump(data, f, indent=2)


# ── Part 1: build the hypothesis set ─────────────────────────────────────────

def build_hypothesis_set() -> list[dict]:
    records: list[dict] = []
    for h in TIERED_HYPOTHESES:
        records.append({
            "source_id": h["source_id"],
            "compound": h["compound"],
            "tier": h["tier"],
            "degradation_type": None,
            "origin_source_id": None,
            "text": h["text"],
        })

    log(f"Generating degraded variants for {len(TIER1_SOURCE_IDS)} Tier-1 hypotheses "
        f"via Groq ({get_generator_model()})...")
    tier1_by_id = {h["source_id"]: h for h in TIERED_HYPOTHESES if h["tier"] == 1}
    for source_id in TIER1_SOURCE_IDS:
        h = tier1_by_id[source_id]
        log(f"  {source_id} ({h['compound']}): specificity-degrading...")
        spec_text = specificity_degrade(h["text"])
        log(f"    -> {spec_text}")
        records.append({
            "source_id": f"{source_id}-degrad-specificity",
            "compound": h["compound"],
            "tier": None,
            "degradation_type": "specificity",
            "origin_source_id": source_id,
            "text": spec_text,
        })

        log(f"  {source_id} ({h['compound']}): novelty-degrading...")
        nov_text = novelty_degrade(h["text"])
        log(f"    -> {nov_text}")
        records.append({
            "source_id": f"{source_id}-degrad-novelty",
            "compound": h["compound"],
            "tier": None,
            "degradation_type": "novelty",
            "origin_source_id": source_id,
            "text": nov_text,
        })

    assert len(records) == 25, f"Expected 25 hypotheses, got {len(records)}"
    return records


def assign_anonymous_ids(records: list[dict]) -> tuple[dict, dict]:
    """
    Returns (id_to_text, lookup). id_to_text is the ONLY thing passed to judges.
    lookup carries tier/degradation truth and is used for analysis only.
    """
    rng = random.Random(SEED)
    shuffled = records[:]
    rng.shuffle(shuffled)

    id_to_text: dict[str, str] = {}
    lookup: dict[str, dict] = {}
    for i, rec in enumerate(shuffled, 1):
        anon_id = f"H{i:03d}"
        id_to_text[anon_id] = rec["text"]
        lookup[anon_id] = rec
    return id_to_text, lookup


# ── Part 2: run judges ────────────────────────────────────────────────────────

def run_rubric_judge(id_to_text: dict[str, str]) -> dict:
    log(f"Rubric judge ({get_judge_model()}): {len(id_to_text)} hyps x 2 dims x "
        f"{N_REPEATS} repeats...")
    results: dict[str, dict] = {}
    total = len(id_to_text) * 2 * N_REPEATS
    done = 0
    for anon_id, text in id_to_text.items():
        results[anon_id] = {"novelty": [], "specificity": []}
        for _ in range(N_REPEATS):
            score, just = rubric_score_novelty(text)
            results[anon_id]["novelty"].append({"score": score, "justification": just})
            done += 1
        for _ in range(N_REPEATS):
            score, just = rubric_score_specificity(text)
            results[anon_id]["specificity"].append({"score": score, "justification": just})
            done += 1
        log(f"  {anon_id} done ({done}/{total})")
        _save("rubric_scores.json", results)
    return results


def run_holistic_judge(id_to_text: dict[str, str]) -> dict:
    log(f"Holistic judge ({get_judge_model()}): {len(id_to_text)} hyps x "
        f"{N_REPEATS} repeats...")
    results: dict[str, list] = {}
    for anon_id, text in id_to_text.items():
        results[anon_id] = []
        for _ in range(N_REPEATS):
            score, just = holistic_score(text)
            results[anon_id].append({"score": score, "justification": just})
        log(f"  {anon_id} done")
        _save("holistic_scores.json", results)
    return results


def run_pairwise_judge(id_to_text: dict[str, str], lookup: dict[str, dict]) -> list[dict]:
    tiered_ids = [i for i in id_to_text if lookup[i]["tier"] is not None]
    by_tier = {1: [], 2: [], 3: []}
    for i in tiered_ids:
        by_tier[lookup[i]["tier"]].append(i)

    pairs: list[tuple[str, str]] = []
    for t_hi, t_lo in ((1, 2), (1, 3), (2, 3)):
        for a in by_tier[t_hi]:
            for b in by_tier[t_lo]:
                pairs.append((a, b))  # a is the true-higher-tier hypothesis

    log(f"Pairwise judge ({get_judge_model()}): {len(pairs)} cross-tier pairs x 2 orders...")
    results: list[dict] = []
    for idx, (hi_id, lo_id) in enumerate(pairs, 1):
        # Order 1: higher-tier hypothesis presented as A
        r1 = pairwise_compare(id_to_text[hi_id], id_to_text[lo_id], "A", "B")
        # Order 2: swapped, higher-tier hypothesis presented as B
        r2 = pairwise_compare(id_to_text[lo_id], id_to_text[hi_id], "A", "B")

        results.append({
            "higher_tier_id": hi_id,
            "lower_tier_id": lo_id,
            "higher_tier": lookup[hi_id]["tier"],
            "lower_tier": lookup[lo_id]["tier"],
            "order1_winners": r1["winners"],       # A=higher, B=lower
            "order2_winners": r2["winners"],        # A=lower, B=higher
        })
        if idx % 10 == 0 or idx == len(pairs):
            log(f"  {idx}/{len(pairs)} pairs done")
            _save("pairwise_results.json", results)
    return results


# ── Part 3: analysis ──────────────────────────────────────────────────────────

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def analyze(
    lookup: dict[str, dict],
    rubric: dict,
    holistic: dict,
    pairwise: list[dict],
) -> dict:
    tiered_ids = [i for i in lookup if lookup[i]["tier"] is not None]
    by_tier = {1: [], 2: [], 3: []}
    for i in tiered_ids:
        by_tier[lookup[i]["tier"]].append(i)

    rubric_mean = {
        i: {
            "novelty": _mean([r["score"] for r in rubric[i]["novelty"]]),
            "specificity": _mean([r["score"] for r in rubric[i]["specificity"]]),
        }
        for i in rubric
    }
    holistic_mean = {i: _mean([r["score"] for r in holistic[i]]) for i in holistic}

    # ── 3a. Tier recovery rate ──────────────────────────────────────────────
    tier_recovery = {"rubric": {}, "holistic": None, "pairwise": {}}

    for dim in ("novelty", "specificity"):
        correct = 0
        total = 0
        for t_hi, t_lo in ((1, 2), (1, 3), (2, 3)):
            for a in by_tier[t_hi]:
                for b in by_tier[t_lo]:
                    total += 1
                    if rubric_mean[a][dim] > rubric_mean[b][dim]:
                        correct += 1
        tier_recovery["rubric"][dim] = {"correct": correct, "total": total,
                                         "rate": correct / total if total else None}

    correct = 0
    total = 0
    for t_hi, t_lo in ((1, 2), (1, 3), (2, 3)):
        for a in by_tier[t_hi]:
            for b in by_tier[t_lo]:
                total += 1
                if holistic_mean[a] > holistic_mean[b]:
                    correct += 1
    tier_recovery["holistic"] = {"correct": correct, "total": total,
                                  "rate": correct / total if total else None}

    for dim in ("novelty", "specificity"):
        correct = 0
        total = 0
        flips = 0
        for p in pairwise:
            w1 = p["order1_winners"][dim]   # 'A' or 'B'; A=higher-tier
            w2 = p["order2_winners"][dim]   # A=lower-tier, B=higher-tier
            hi_won_1 = (w1 == "A")
            hi_won_2 = (w2 == "B")
            total += 2
            correct += int(hi_won_1) + int(hi_won_2)
            if hi_won_1 != hi_won_2:
                flips += 1
        tier_recovery["pairwise"][dim] = {
            "correct": correct, "total": total,
            "rate": correct / total if total else None,
            "unstable_pairs": flips, "total_pairs": len(pairwise),
        }

    # ── 3b. Dimension localization (degraded variants) ──────────────────────
    localization: dict[str, dict[str, float]] = {"specificity": {}, "novelty": {}}
    for degradation_type in ("specificity", "novelty"):
        deltas_novelty = []
        deltas_specificity = []
        for anon_id, rec in lookup.items():
            if rec["degradation_type"] != degradation_type:
                continue
            origin_id = next(
                oid for oid, orec in lookup.items()
                if orec["source_id"] == rec["origin_source_id"]
            )
            deltas_novelty.append(
                rubric_mean[origin_id]["novelty"] - rubric_mean[anon_id]["novelty"]
            )
            deltas_specificity.append(
                rubric_mean[origin_id]["specificity"] - rubric_mean[anon_id]["specificity"]
            )
        localization[degradation_type] = {
            "novelty_delta": _mean(deltas_novelty),
            "specificity_delta": _mean(deltas_specificity),
            "n": len(deltas_novelty),
        }

    # ── 3c. Stability (variance across repeats) ──────────────────────────────
    def _range_and_var(xs: list[float]) -> tuple[float, float]:
        r = max(xs) - min(xs)
        m = _mean(xs)
        v = _mean([(x - m) ** 2 for x in xs])
        return r, v

    rubric_novelty_ranges = []
    rubric_novelty_vars = []
    rubric_specificity_ranges = []
    rubric_specificity_vars = []
    for i in rubric:
        r, v = _range_and_var([s["score"] for s in rubric[i]["novelty"]])
        rubric_novelty_ranges.append(r)
        rubric_novelty_vars.append(v)
        r, v = _range_and_var([s["score"] for s in rubric[i]["specificity"]])
        rubric_specificity_ranges.append(r)
        rubric_specificity_vars.append(v)

    holistic_ranges = []
    holistic_vars = []
    for i in holistic:
        r, v = _range_and_var([s["score"] for s in holistic[i]])
        holistic_ranges.append(r)
        holistic_vars.append(v)

    stability = {
        "rubric_novelty": {
            "mean_range": _mean(rubric_novelty_ranges),
            "mean_variance": _mean(rubric_novelty_vars),
            "n_hyps_with_disagreement": sum(1 for r in rubric_novelty_ranges if r > 0),
        },
        "rubric_specificity": {
            "mean_range": _mean(rubric_specificity_ranges),
            "mean_variance": _mean(rubric_specificity_vars),
            "n_hyps_with_disagreement": sum(1 for r in rubric_specificity_ranges if r > 0),
        },
        "holistic": {
            "mean_range": _mean(holistic_ranges),
            "mean_variance": _mean(holistic_vars),
            "n_hyps_with_disagreement": sum(1 for r in holistic_ranges if r > 0),
        },
        "n_hypotheses": len(rubric),
        "n_repeats": N_REPEATS,
    }

    return {
        "rubric_mean": rubric_mean,
        "holistic_mean": holistic_mean,
        "tier_recovery": tier_recovery,
        "localization": localization,
        "stability": stability,
    }


# ── Output ────────────────────────────────────────────────────────────────────

def write_summary_md(lookup: dict[str, dict], analysis: dict) -> None:
    tr = analysis["tier_recovery"]
    loc = analysis["localization"]
    stab = analysis["stability"]
    rubric_mean = analysis["rubric_mean"]
    holistic_mean = analysis["holistic_mean"]

    lines: list[str] = []
    lines.append("# Rubric Validation — Results\n")
    lines.append(f"Judge model: `{get_judge_model()}` (OpenAI). "
                  f"Degradation-generator model: `{get_generator_model()}` (Groq).\n")
    lines.append("No p-values / confidence intervals reported — n is too small "
                  "(15-25 hypotheses) for that to be meaningful. Raw rates and "
                  "deltas only.\n")

    lines.append("## 3a. Tier recovery rate\n")
    lines.append("Fraction of cross-tier hypothesis pairs (T1 vs T2, T1 vs T3, "
                  "T2 vs T3; 25 pairs each = 75 total) correctly ordered "
                  "higher-tier > lower-tier.\n")
    lines.append("| Condition | Dimension | Correct / Total | Rate |")
    lines.append("|---|---|---|---|")
    for dim in ("novelty", "specificity"):
        d = tr["rubric"][dim]
        lines.append(f"| Rubric | {dim} | {d['correct']}/{d['total']} | {d['rate']:.2f} |")
    h = tr["holistic"]
    lines.append(f"| Holistic | (single score) | {h['correct']}/{h['total']} | {h['rate']:.2f} |")
    for dim in ("novelty", "specificity"):
        d = tr["pairwise"][dim]
        lines.append(f"| Pairwise | {dim} | {d['correct']}/{d['total']} | {d['rate']:.2f} |")
    lines.append("")
    lines.append("Pairwise instability (winner flipped when A/B order was swapped):\n")
    lines.append("| Dimension | Unstable pairs / Total pairs |")
    lines.append("|---|---|")
    for dim in ("novelty", "specificity"):
        d = tr["pairwise"][dim]
        lines.append(f"| {dim} | {d['unstable_pairs']}/{d['total_pairs']} |")
    lines.append("")

    lines.append("## 3b. Dimension localization (degraded variants)\n")
    lines.append("Score delta = original rubric score minus degraded variant's rubric "
                  "score, mean over the 5 Tier-1 compounds. A correctly-behaving rubric "
                  "shows a large drop on the TARGETED dimension and a small drop on the "
                  "other.\n")
    lines.append("| Degradation type | n | Δ novelty | Δ specificity |")
    lines.append("|---|---|---|---|")
    for dt in ("specificity", "novelty"):
        d = loc[dt]
        lines.append(f"| {dt}-degraded | {d['n']} | {d['novelty_delta']:.2f} | {d['specificity_delta']:.2f} |")
    lines.append("")

    lines.append("## 3c. Stability across repeated runs\n")
    lines.append(f"Each hypothesis scored {stab['n_repeats']} times independently "
                  f"(same prompt, same model, no context of prior runs) for rubric "
                  f"and holistic conditions.\n")
    lines.append("| Condition | Mean range (max-min) | Mean variance | Hyps w/ any disagreement |")
    lines.append("|---|---|---|---|")
    for key, label in (("rubric_novelty", "Rubric — novelty"),
                        ("rubric_specificity", "Rubric — specificity"),
                        ("holistic", "Holistic")):
        d = stab[key]
        lines.append(f"| {label} | {d['mean_range']:.2f} | {d['mean_variance']:.2f} | "
                      f"{d['n_hyps_with_disagreement']}/{stab['n_hypotheses']} |")
    lines.append("")

    lines.append("## Raw per-hypothesis scores (anonymized IDs)\n")
    lines.append("| ID | True tier / degradation | Compound | Rubric novelty (mean) | "
                  "Rubric specificity (mean) | Holistic (mean) | Text |")
    lines.append("|---|---|---|---|---|---|---|")
    for anon_id in sorted(lookup, key=lambda x: int(x[1:])):
        rec = lookup[anon_id]
        truth = f"Tier {rec['tier']}" if rec["tier"] else f"{rec['degradation_type']}-degraded of {rec['origin_source_id']}"
        text = rec["text"].replace("|", "/")
        lines.append(
            f"| {anon_id} | {truth} | {rec['compound']} | "
            f"{rubric_mean[anon_id]['novelty']:.1f} | {rubric_mean[anon_id]['specificity']:.1f} | "
            f"{holistic_mean[anon_id]:.1f} | {text} |"
        )
    lines.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "summary.md", "w") as f:
        f.write("\n".join(lines))
    log(f"Wrote {OUT_DIR / 'summary.md'}")


def write_raw_csv(lookup: dict[str, dict], rubric: dict, holistic: dict) -> None:
    import csv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "raw_scores.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "anon_id", "true_tier", "degradation_type", "origin_source_id", "compound",
            "text", "rubric_novelty_r1", "rubric_novelty_r2",
            "rubric_specificity_r1", "rubric_specificity_r2",
            "holistic_r1", "holistic_r2",
        ])
        for anon_id in sorted(lookup, key=lambda x: int(x[1:])):
            rec = lookup[anon_id]
            rn = [s["score"] for s in rubric[anon_id]["novelty"]]
            rs = [s["score"] for s in rubric[anon_id]["specificity"]]
            hs = [s["score"] for s in holistic[anon_id]]
            w.writerow([
                anon_id, rec["tier"], rec["degradation_type"], rec["origin_source_id"],
                rec["compound"], rec["text"],
                rn[0], rn[1], rs[0], rs[1], hs[0], hs[1],
            ])
    log(f"Wrote {OUT_DIR / 'raw_scores.csv'}")


def main() -> None:
    t0 = time.time()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set.")
    if not os.environ.get("GROQ_API_KEY"):
        sys.exit("GROQ_API_KEY is not set.")

    log("Building hypothesis set (15 tiered + 10 degraded)...")
    records = build_hypothesis_set()
    _save("hypotheses_raw.json", records)

    id_to_text, lookup = assign_anonymous_ids(records)
    _save("lookup_HIDDEN.json", lookup)   # analysis-only, never passed to judges
    _save("id_to_text.json", id_to_text)
    log(f"Assigned {len(id_to_text)} anonymized IDs (H001-H{len(id_to_text):03d}).")

    rubric = run_rubric_judge(id_to_text)
    holistic = run_holistic_judge(id_to_text)
    pairwise = run_pairwise_judge(id_to_text, lookup)

    log("Running analysis...")
    analysis = analyze(lookup, rubric, holistic, pairwise)
    _save("analysis.json", analysis)

    write_summary_md(lookup, analysis)
    write_raw_csv(lookup, rubric, holistic)

    log(f"Done in {time.time() - t0:.0f}s.")


if __name__ == "__main__":
    main()
