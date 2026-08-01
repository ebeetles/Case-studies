from __future__ import annotations

import os, sys
sys.path.insert(0, os.getcwd())  # repo root (run scripts from repo root)
import _exppath  # noqa: E402  (extends sys.path to experiment folders)

"""
Novelty-decay experiment (Steps 3-5): time-split retrospective validation of
the rubric NOVELTY dimension, adapted from HindSight (Jiang 2026,
arXiv:2603.15164) — testing each compound against itself at two points in
time rather than comparing across compounds (which the prior tier-recovery
runs showed is confounded: trial status correlates with "became well-known").

Uses the hand-curated corpus (curated_corpus_data.py) in place of the
Semantic Scholar scrape, which stalled on rate limits. Two HIGH CONFIDENCE
compounds only: metformin, sildenafil.

Step 3: embed the fixed-template hypothesis text + curated pre/post papers
         (OpenAI text-embedding-3-small, reusing measure_diversity.py's
         embed_texts/cosine_similarity — same client/model as the existing
         diversity experiment).
Step 4: rubric novelty judge, run twice per compound — once restricted to
         pre-cutoff literature context, once to post-cutoff — using
         validation_judge.rubric_score_novelty's context_papers parameter
         (current rubric prompt, unmodified; only the literature block and
         a "score using only this context" instruction are added).
Step 5: table + directional agreement between judge delta and embedding delta.
         No correlation coefficients / p-values (n=2, later n=5) — raw
         numbers and per-compound direction only.
"""

import json
from pathlib import Path

from main import _load_dotenv, _sanitize_env

_load_dotenv()
_sanitize_env()

from openai import OpenAI

from curated_corpus_data import CUTOFFS, CURATED_PAPERS, HYPOTHESIS_TEXT
from measure_diversity import embed_texts, cosine_similarity, EMBEDDING_MODEL
from validation_judge import rubric_score_novelty
from judge import get_judge_model

OUT_DIR = Path("results/archive")
COMPOUNDS = ["metformin", "sildenafil"]  # high-confidence only; see prompt


def log(msg: str) -> None:
    print(f"[decay] {msg}", flush=True)


def _paper_embed_text(p: dict) -> str:
    return f"{p['title']}: {p['abstract']}"


def main() -> None:
    client = OpenAI()
    log(f"Embedding model: {EMBEDDING_MODEL}, judge model: {get_judge_model()}")

    results: dict[str, dict] = {}

    for compound in COMPOUNDS:
        log(f"--- {compound} (cutoff {CUTOFFS[compound]['date']}) ---")
        hyp_text = HYPOTHESIS_TEXT[compound]
        pre_papers = CURATED_PAPERS[compound]["pre"]
        post_papers = CURATED_PAPERS[compound]["post"]

        # ── Step 3: embedding similarity ────────────────────────────────────
        texts = [hyp_text] + [_paper_embed_text(p) for p in pre_papers + post_papers]
        embeddings = embed_texts(texts, EMBEDDING_MODEL, client)
        hyp_emb = embeddings[0]
        pre_embs = embeddings[1:1 + len(pre_papers)]
        post_embs = embeddings[1 + len(pre_papers):]

        pre_sims = [cosine_similarity(hyp_emb, e) for e in pre_embs]
        post_sims = [cosine_similarity(hyp_emb, e) for e in post_embs]
        max_pre_sim = max(pre_sims)
        max_post_sim = max(post_sims)
        log(f"  embedding: max pre-sim={max_pre_sim:.3f}, max post-sim={max_post_sim:.3f}")

        # ── Step 4: context-restricted rubric novelty judge ─────────────────
        pre_score, pre_just = rubric_score_novelty(
            hyp_text, context_papers=pre_papers, context_label="pre-cutoff"
        )
        log(f"  judge (pre-cutoff context): {pre_score} — {pre_just}")
        post_score, post_just = rubric_score_novelty(
            hyp_text, context_papers=post_papers, context_label="post-cutoff"
        )
        log(f"  judge (post-cutoff context): {post_score} — {post_just}")

        results[compound] = {
            "cutoff": CUTOFFS[compound],
            "hypothesis_text": hyp_text,
            "pre_sims": pre_sims,
            "post_sims": post_sims,
            "max_pre_sim": max_pre_sim,
            "max_post_sim": max_post_sim,
            "embedding_delta_post_minus_pre": max_post_sim - max_pre_sim,
            "judge_pre_score": pre_score,
            "judge_pre_justification": pre_just,
            "judge_post_score": post_score,
            "judge_post_justification": post_just,
            "judge_delta_post_minus_pre": post_score - pre_score,
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "novelty_decay_raw.json").write_text(json.dumps(results, indent=2))
    (OUT_DIR / "corpus_curated.json").write_text(json.dumps(
        {c: CURATED_PAPERS[c] for c in COMPOUNDS}, indent=2
    ))

    write_summary(results)
    log("Done.")


def write_summary(results: dict) -> None:
    lines: list[str] = []
    lines.append("# Novelty Decay — Time-Split Retrospective Validation\n")
    lines.append(
        "Adapted from HindSight (Jiang 2026, arXiv:2603.15164): tests the "
        "rubric NOVELTY dimension against each compound's OWN literature "
        "history (pre- vs. post-first-proposal), avoiding the cross-compound "
        "confound in the prior tier-recovery runs (trial status correlates "
        "with 'became well-known over time').\n"
    )
    lines.append(
        "**Corpus**: hand-curated (Semantic Scholar API scraping stalled on "
        "persistent rate-limiting — see build_corpus.py / "
        "novelty_decay_curated_corpus.md). 3 pre-cutoff + 3 post-cutoff papers "
        "per compound, sourced via targeted web search. Two HIGH CONFIDENCE "
        "compounds only (metformin, sildenafil); losartan/pioglitazone/"
        "liraglutide deferred as lower-confidence estimates pending a decision "
        "to extend.\n"
    )
    lines.append(
        f"Embedding model: `{EMBEDDING_MODEL}` (OpenAI). Judge model: "
        f"`{get_judge_model()}` (OpenAI, current rubric novelty prompt, "
        "unmodified — only a literature-context block and a "
        "'score using only this context' instruction are added).\n"
    )
    lines.append(
        "No correlation coefficients or p-values — n=2 compounds here. "
        "Raw per-compound numbers and directional agreement only.\n"
    )

    lines.append("## Results table\n")
    lines.append(
        "| Compound | Pre-cutoff max sim | Post-cutoff max sim | Embedding Δ "
        "(post-pre) | Judge pre-cutoff novelty | Judge post-cutoff novelty | "
        "Judge Δ (post-pre) |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for compound, r in results.items():
        lines.append(
            f"| {compound} | {r['max_pre_sim']:.3f} | {r['max_post_sim']:.3f} | "
            f"{r['embedding_delta_post_minus_pre']:+.3f} | {r['judge_pre_score']} | "
            f"{r['judge_post_score']} | {r['judge_delta_post_minus_pre']:+d} |"
        )
    lines.append("")

    lines.append("## Directional agreement\n")
    lines.append(
        "Expected 'decay signature': embedding similarity should be higher "
        "post-cutoff (idea becomes more embedded in the literature over time "
        "→ embedding Δ > 0), and — if the novelty judge is tracking real "
        "novelty decay rather than something else — its score should be LOWER "
        "post-cutoff (judge Δ < 0). Agreement = judge Δ and embedding Δ point "
        "in the expected opposite directions (embedding Δ > 0 AND judge Δ < 0).\n"
    )
    agree = 0
    for compound, r in results.items():
        emb_up = r["embedding_delta_post_minus_pre"] > 0
        judge_down = r["judge_delta_post_minus_pre"] < 0
        matched = emb_up and judge_down
        agree += int(matched)
        lines.append(
            f"- **{compound}**: embedding Δ {'+' if emb_up else '-'} "
            f"({r['embedding_delta_post_minus_pre']:+.3f}), judge Δ "
            f"{'-' if judge_down else '+/0'} "
            f"({r['judge_delta_post_minus_pre']:+d}) → "
            f"{'MATCHES expected decay signature' if matched else 'does NOT match'}"
        )
    lines.append(f"\n**Agreement rate: {agree}/{len(results)} compounds.**\n")

    lines.append("## Per-compound judge justifications\n")
    for compound, r in results.items():
        lines.append(f"### {compound} (cutoff: {r['cutoff']['date']}, "
                      f"confidence: {r['cutoff']['confidence']})\n")
        lines.append(f"- Hypothesis: {r['hypothesis_text']}")
        lines.append(f"- Pre-cutoff score {r['judge_pre_score']}: {r['judge_pre_justification']}")
        lines.append(f"- Post-cutoff score {r['judge_post_score']}: {r['judge_post_justification']}")
        lines.append("")

    (OUT_DIR / "novelty_decay.md").write_text("\n".join(lines))
    log(f"Wrote {OUT_DIR / 'novelty_decay.md'}")


if __name__ == "__main__":
    main()
