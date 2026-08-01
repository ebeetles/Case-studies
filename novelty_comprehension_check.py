from __future__ import annotations

"""
Follow-up diagnostic to novelty_decay.py: is the novelty judge's flat 3/5-both-
conditions result because it (a) reads the literature but doesn't weight it in
the novelty score, or (b) doesn't meaningfully process the literature content
at all?

For each compound-condition pair (metformin/sildenafil x pre-cutoff/post-cutoff,
4 total), runs a direct comprehension question about the SAME literature block
used in novelty_decay.py, immediately followed by the same rubric novelty call.

Reuses curated_corpus_data.py's pre/post contexts unchanged — no corpus rebuild.

n=4 — no statistics, raw pattern only.
"""

import json
from pathlib import Path

from main import _load_dotenv, _sanitize_env

_load_dotenv()
_sanitize_env()

from curated_corpus_data import CUTOFFS, CURATED_PAPERS, HYPOTHESIS_TEXT
from validation_judge import check_literature_comprehension, rubric_score_novelty
from judge import get_judge_model

OUT_DIR = Path("results/validation")
COMPOUNDS = ["metformin", "sildenafil"]

# Specific mechanism phrase probed in the comprehension question, matching
# each compound's hypothesis text.
MECHANISM_LABEL = {
    "metformin": "AMPK/mTOR pathway modulation reducing tau pathology or neuroinflammation",
    "sildenafil": "PDE5 inhibition / cGMP signaling reducing tau phosphorylation or amyloid accumulation",
}

EXPECTED_ANSWER = {"pre": False, "post": True}  # pre should say NO, post should say YES


def log(msg: str) -> None:
    print(f"[comprehension] {msg}", flush=True)


def main() -> None:
    log(f"Judge model: {get_judge_model()}")
    rows: list[dict] = []

    for compound in COMPOUNDS:
        hyp_text = HYPOTHESIS_TEXT[compound]
        mechanism = MECHANISM_LABEL[compound]
        compound_scores: dict[str, int] = {}

        for condition in ("pre", "post"):
            papers = CURATED_PAPERS[compound][condition]
            log(f"--- {compound} / {condition}-cutoff ---")

            answer_is_yes, raw_comprehension = check_literature_comprehension(
                compound, mechanism, papers, context_label=f"{condition}-cutoff"
            )
            expected = EXPECTED_ANSWER[condition]
            correct = answer_is_yes == expected
            log(f"  comprehension: {'YES' if answer_is_yes else 'NO'} "
                f"(expected {'YES' if expected else 'NO'}) -> "
                f"{'CORRECT' if correct else 'INCORRECT'}")

            score, justification = rubric_score_novelty(
                hyp_text, context_papers=papers, context_label=f"{condition}-cutoff"
            )
            log(f"  novelty score: {score} — {justification}")
            compound_scores[condition] = score

            rows.append({
                "compound": compound,
                "condition": condition,
                "cutoff": CUTOFFS[compound]["date"],
                "comprehension_answer": "YES" if answer_is_yes else "NO",
                "expected_answer": "YES" if expected else "NO",
                "comprehension_correct": correct,
                "comprehension_raw": raw_comprehension,
                "novelty_score": score,
                "novelty_justification": justification,
            })

        judge_delta = compound_scores["post"] - compound_scores["pre"]
        matches_decay = judge_delta < 0
        for row in rows:
            if row["compound"] == compound:
                row["judge_delta_post_minus_pre"] = judge_delta
                row["matches_expected_decay_direction"] = matches_decay

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "novelty_comprehension_raw.json").write_text(json.dumps(rows, indent=2))

    write_summary(rows)
    log("Done.")


def write_summary(rows: list[dict]) -> None:
    lines: list[str] = []
    lines.append("# Novelty Comprehension Check\n")
    lines.append(
        "Diagnostic follow-up to results/validation/novelty_decay.md, which found "
        "the novelty judge scored 3/5 in BOTH pre-cutoff and post-cutoff literature "
        "conditions for both compounds — a flat, non-responsive result despite the "
        "embedding-similarity sanity check confirming the corpora were correctly "
        "differentiated. This checks whether the judge (a) reads the literature "
        "correctly but doesn't weight it in its novelty score, or (b) doesn't "
        "meaningfully process the literature content at all.\n"
    )
    lines.append(
        "Method: before each novelty scoring call, a direct comprehension question "
        "is asked about the SAME literature block — 'does this literature already "
        "describe [compound] + [mechanism] in an AD context?' Pre-cutoff context "
        "should answer NO (the connection hadn't been proposed yet); post-cutoff "
        "should answer YES.\n"
    )
    lines.append(
        "n=4 cases (2 compounds x 2 conditions). No statistics — raw pattern only.\n"
    )

    lines.append("## Results table\n")
    lines.append(
        "| Compound | Condition | Comprehension answer | Expected | Correct? | "
        "Novelty score | Compound judge Δ (post-pre) | Matches expected decay direction? |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['compound']} | {r['condition']}-cutoff | {r['comprehension_answer']} | "
            f"{r['expected_answer']} | {'✓' if r['comprehension_correct'] else '✗'} | "
            f"{r['novelty_score']} | {r['judge_delta_post_minus_pre']:+d} | "
            f"{'✓' if r['matches_expected_decay_direction'] else '✗'} |"
        )
    lines.append("")

    lines.append("## Per-case pattern\n")
    for compound in dict.fromkeys(r["compound"] for r in rows):
        c_rows = [r for r in rows if r["compound"] == compound]
        pre, post = c_rows[0], c_rows[1]
        lines.append(f"**{compound}**:")
        if pre["comprehension_correct"] and post["comprehension_correct"]:
            if pre["novelty_score"] != post["novelty_score"]:
                verdict = ("Comprehension correct in both conditions AND novelty "
                           "score responded — the flat result in the original decay "
                           "experiment looks prompt/instance-specific rather than a "
                           "fundamental comprehension failure.")
            else:
                verdict = ("Comprehension correct in both conditions but novelty "
                           "score did NOT move — the judge understands what the "
                           "literature shows but its novelty score is decoupled "
                           "from that understanding ('scoring on autopilot').")
        elif not pre["comprehension_correct"] and not post["comprehension_correct"]:
            verdict = ("Comprehension INCORRECT in both conditions — the judge is "
                       "not reliably extracting the relevant connection from the "
                       "provided context at all, a more basic failure than score "
                       "weighting.")
        else:
            wrong_cond = pre["condition"] if not pre["comprehension_correct"] else post["condition"]
            verdict = (f"MIXED — comprehension correct on one condition, incorrect "
                       f"on the other ({wrong_cond}-cutoff failed). Report as-is, "
                       f"do not average away.")
        lines.append(f"- {verdict}\n")

    lines.append("## Raw comprehension-check responses (verbatim)\n")
    for r in rows:
        lines.append(f"### {r['compound']} / {r['condition']}-cutoff\n")
        lines.append(f"Expected: {r['expected_answer']}, got: {r['comprehension_answer']} "
                      f"({'correct' if r['comprehension_correct'] else 'INCORRECT'})\n")
        lines.append("```")
        lines.append(r["comprehension_raw"])
        lines.append("```")
        lines.append(f"\nNovelty score immediately after: {r['novelty_score']} — "
                      f"{r['novelty_justification']}\n")

    (OUT_DIR / "novelty_comprehension_check.md").write_text("\n".join(lines))
    log(f"Wrote {OUT_DIR / 'novelty_comprehension_check.md'}")


if __name__ == "__main__":
    main()
