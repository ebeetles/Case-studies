from __future__ import annotations

import os, sys
sys.path.insert(0, os.getcwd())  # repo root (run scripts from repo root)
import _exppath  # noqa: E402  (extends sys.path to experiment folders)

"""
Re-run degradation localization (section 3b) only, using the revised NOVELTY
rubric definition (validation_judge.rubric_score_novelty).

Reuses the existing hypothesis set (hypotheses_raw.json / id_to_text.json /
lookup_HIDDEN.json) from the prior run — does NOT regenerate degraded variants.
Only re-scores novelty (new prompt) for the 15 hypotheses relevant to
localization (5 Tier-1 originals + their 10 degraded variants); specificity
scores are reused unchanged from the prior run since that prompt didn't change.

Tier recovery (3a) is intentionally NOT rerun for novelty: the "reached trial"
ground truth is invalid for novelty specifically (trial stage confounds with
"became well-known over time"), per this run's request. Specificity tier
recovery is unaffected and can be found in results/archive/summary.md.

Output: results/archive/summary_v2_localization_only.md
"""

import json
from pathlib import Path

from main import _load_dotenv, _sanitize_env

_load_dotenv()
_sanitize_env()

from validation_judge import rubric_score_novelty
from judge import get_judge_model

OUT_DIR = Path("results/archive")
N_REPEATS = 2


def log(msg: str) -> None:
    print(f"[localize-v2] {msg}", flush=True)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _range_and_var(xs: list[float]) -> tuple[float, float]:
    r = max(xs) - min(xs)
    m = _mean(xs)
    v = _mean([(x - m) ** 2 for x in xs])
    return r, v


def main() -> None:
    lookup = json.loads((OUT_DIR / "lookup_HIDDEN.json").read_text())
    id_to_text = json.loads((OUT_DIR / "id_to_text.json").read_text())
    old_rubric = json.loads((OUT_DIR / "rubric_scores.json").read_text())

    # 15 hypotheses relevant to localization: the 5 Tier-1 originals whose
    # source_id appears as an origin_source_id, plus their 10 degraded variants.
    degraded_ids = [i for i, rec in lookup.items() if rec["degradation_type"] is not None]
    origin_source_ids = {lookup[i]["origin_source_id"] for i in degraded_ids}
    origin_ids = [
        i for i, rec in lookup.items()
        if rec["tier"] == 1 and rec["source_id"] in origin_source_ids
    ]
    relevant_ids = origin_ids + degraded_ids
    assert len(origin_ids) == 5 and len(degraded_ids) == 10, (
        f"Expected 5 originals + 10 degraded, got {len(origin_ids)} + {len(degraded_ids)}"
    )
    log(f"Re-scoring novelty (new prompt) for {len(relevant_ids)} hypotheses "
        f"({get_judge_model()}), {N_REPEATS} repeats each...")

    new_novelty: dict[str, list[dict]] = {}
    for anon_id in relevant_ids:
        text = id_to_text[anon_id]
        new_novelty[anon_id] = []
        for _ in range(N_REPEATS):
            score, just = rubric_score_novelty(text)
            new_novelty[anon_id].append({"score": score, "justification": just})
        log(f"  {anon_id} ({lookup[anon_id]['compound']}): "
            f"{[s['score'] for s in new_novelty[anon_id]]}")

    (OUT_DIR / "rubric_novelty_v2.json").write_text(json.dumps(new_novelty, indent=2))

    # Specificity scores reused unchanged from the prior run.
    specificity_mean = {
        i: _mean([s["score"] for s in old_rubric[i]["specificity"]])
        for i in relevant_ids
    }
    novelty_mean = {
        i: _mean([s["score"] for s in new_novelty[i]])
        for i in relevant_ids
    }

    # ── 3b. Dimension localization (revised novelty) ─────────────────────────
    localization: dict[str, dict] = {}
    for degradation_type in ("specificity", "novelty"):
        deltas_novelty = []
        deltas_specificity = []
        for anon_id in degraded_ids:
            rec = lookup[anon_id]
            if rec["degradation_type"] != degradation_type:
                continue
            origin_id = next(
                oid for oid in origin_ids
                if lookup[oid]["source_id"] == rec["origin_source_id"]
            )
            deltas_novelty.append(novelty_mean[origin_id] - novelty_mean[anon_id])
            deltas_specificity.append(
                specificity_mean[origin_id] - specificity_mean[anon_id]
            )
        localization[degradation_type] = {
            "novelty_delta": _mean(deltas_novelty),
            "specificity_delta": _mean(deltas_specificity),
            "n": len(deltas_novelty),
        }

    # ── 3c. Stability for novelty specifically (the 15 relevant hyps) ────────
    ranges, variances = [], []
    for anon_id in relevant_ids:
        r, v = _range_and_var([s["score"] for s in new_novelty[anon_id]])
        ranges.append(r)
        variances.append(v)
    stability_novelty = {
        "mean_range": _mean(ranges),
        "mean_variance": _mean(variances),
        "n_hyps_with_disagreement": sum(1 for r in ranges if r > 0),
        "n_hypotheses": len(relevant_ids),
        "n_repeats": N_REPEATS,
    }

    _write_summary(lookup, localization, stability_novelty, novelty_mean, specificity_mean,
                    origin_ids, degraded_ids)
    log("Done.")


def _write_summary(lookup, localization, stability_novelty, novelty_mean, specificity_mean,
                    origin_ids, degraded_ids) -> None:
    lines: list[str] = []
    lines.append("# Rubric Validation — v2 Localization Only (revised NOVELTY prompt)\n")
    lines.append(f"Judge model: `{get_judge_model()}` (OpenAI). "
                  "Novelty rubric prompt revised to score novelty of the AD "
                  "*application*, not novelty/rarity of the underlying mechanism. "
                  "Specificity prompt and scores are unchanged from the prior run.\n")
    lines.append("Tier recovery (3a) is not rerun here for novelty — trial-stage "
                  "ground truth is confounded with a hypothesis becoming well-known "
                  "over time, so it's not a valid novelty check. Specificity tier "
                  "recovery is unaffected; see results/archive/summary.md.\n")
    lines.append("No p-values / confidence intervals — n too small to be meaningful.\n")

    lines.append("## 3b. Dimension localization (degraded variants, revised novelty)\n")
    lines.append("Score delta = original rubric score minus degraded variant's rubric "
                  "score, mean over the 5 Tier-1 compounds.\n")
    lines.append("| Degradation type | n | Δ novelty | Δ specificity |")
    lines.append("|---|---|---|---|")
    for dt in ("specificity", "novelty"):
        d = localization[dt]
        lines.append(f"| {dt}-degraded | {d['n']} | {d['novelty_delta']:.2f} | "
                      f"{d['specificity_delta']:.2f} |")
    lines.append("")

    lines.append("## 3c. Stability — novelty (revised prompt) only\n")
    lines.append(f"{stability_novelty['n_hypotheses']} hypotheses (5 Tier-1 originals + "
                  f"10 degraded variants), {stability_novelty['n_repeats']} repeats each.\n")
    lines.append("| Mean range (max-min) | Mean variance | Hyps w/ any disagreement |")
    lines.append("|---|---|---|")
    lines.append(f"| {stability_novelty['mean_range']:.2f} | "
                  f"{stability_novelty['mean_variance']:.2f} | "
                  f"{stability_novelty['n_hyps_with_disagreement']}/"
                  f"{stability_novelty['n_hypotheses']} |")
    lines.append("")

    lines.append("## Raw scores (revised novelty prompt)\n")
    lines.append("| ID | True tier / degradation | Compound | Novelty v2 (mean) | "
                  "Specificity (mean, reused) |")
    lines.append("|---|---|---|---|---|")
    for anon_id in origin_ids + degraded_ids:
        rec = lookup[anon_id]
        truth = f"Tier {rec['tier']}" if rec["tier"] else f"{rec['degradation_type']}-degraded of {rec['origin_source_id']}"
        lines.append(f"| {anon_id} | {truth} | {rec['compound']} | "
                      f"{novelty_mean[anon_id]:.1f} | {specificity_mean[anon_id]:.1f} |")
    lines.append("")

    (OUT_DIR / "summary_v2_localization_only.md").write_text("\n".join(lines))
    log(f"Wrote {OUT_DIR / 'summary_v2_localization_only.md'}")


if __name__ == "__main__":
    main()
