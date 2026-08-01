from __future__ import annotations

"""
Structural novelty via literature-based discovery (Swanson's ABC model, 1986;
time-sliced as in SKiM, bioRxiv 2020, and Zhang et al., J Biomed Inform 2021).

Replaces the LLM-judged novelty dimension (shown non-functional across four
prior experiments — see novelty_validation_full_summary.md) with a paper-
counting decomposition that asks no LLM for a novelty opinion.

Each hypothesis = [Compound A] modulates [Mechanism B] relevant to [Disease C].
Three links, counted in PubMed within a date window:
    A-B  compound + mechanism    is the drug known to affect this mechanism?
    B-C  mechanism + disease     is this mechanism known to matter in AD?
    A-C  compound + disease      has anyone already connected the drug to AD?

Classification (thresholds applied post hoc, not baked in — see Step 4):
    Case 1  A-C high                      -> Already proposed (not novel)
    Case 2  A-B high, B-C high, A-C ~0     -> Bridgeable but unbridged (novel) [target]
    Case 3  A-B low, B-C low, A-C ~0       -> Disconnected (not grounded)
    Case 0  mechanism == null             -> Undecomposable (fails specificity gate)

LLM is used ONLY to parse hypotheses into (compound, mechanism, disease) —
never to score. PubMed counts are the signal.

USAGE
    python structural_novelty.py            # Step 1 only: decompose + print, STOP
    python structural_novelty.py --run      # Steps 2-4: queries + classification

Step 1 stops for manual review by design (a bad parse invalidates everything
downstream). Re-run with --run only after the decomposition table is verified.
"""

import json
import re
import sys
from pathlib import Path

from main import _load_dotenv, _sanitize_env

_load_dotenv()
_sanitize_env()

from validation_data import TIERED_HYPOTHESES
from judge import _call_judge, get_judge_model

OUT_DIR = Path("results/validation")

# Per-compound cutoffs for Test 1 (from novelty_decay_curated_corpus.md).
# HIGH confidence: metformin, sildenafil. MODERATE (estimates): the rest.
TIER1_CUTOFFS = {
    "Metformin":    {"year": 2011, "confidence": "high"},
    "Sildenafil":   {"year": 2021, "confidence": "high"},
    "Losartan":     {"year": 2015, "confidence": "moderate"},
    "Pioglitazone": {"year": 2005, "confidence": "moderate"},
    "Liraglutide":  {"year": 2010, "confidence": "moderate"},
}


def log(msg: str) -> None:
    print(f"[structural] {msg}", flush=True)


# ── Step 1: decompose (LLM for PARSING ONLY) ─────────────────────────────────

def _parse_json_block(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise RuntimeError(f"No JSON object in parser response:\n{text[:400]}")
    return json.loads(m.group(0))


def decompose_hypothesis(hyp_text: str) -> dict:
    """
    Extract (compound, mechanism, disease) from one hypothesis. Mechanism must
    be a specific molecular target/pathway EXPLICITLY named in the text; if none
    is named, mechanism must be null (do not invent or substitute a general one).
    """
    prompt = f"""You are a text parser. Extract structured fields from a drug-repurposing
hypothesis. Do NOT judge quality. Do NOT add information not present in the text.

Hypothesis: {hyp_text}

Extract exactly these fields as JSON:
- "compound": the drug/compound name (string).
- "mechanism": the SPECIFIC molecular target or pathway explicitly named in the
  text that the compound acts on — e.g. "AMPK", "PDE5", "PPAR-gamma",
  "GLP-1 receptor", "angiotensin II type 1 receptor", "GABA-B receptor".
  CRITICAL RULES:
  * Only extract a mechanism that is EXPLICITLY stated in the hypothesis text.
  * If the text names no specific molecular target/pathway (e.g. it only says
    "may have effects", "may be beneficial", "may modulate AD network
    pathophysiology" with no named target), set "mechanism": null.
  * A bare drug-class descriptor with no named molecular target (e.g. "a calcium
    channel blocker", "a tyrosine kinase inhibitor", "a selective estrogen
    receptor modulator") — extract it VERBATIM as the mechanism string, since it
    does name a target class, but do NOT expand it into a specific molecule.
  * Do NOT invent, generalize, or substitute a mechanism. When in doubt, null.
- "disease": the disease (string) — will be "Alzheimer's disease".

Reply with ONLY the JSON object."""

    text = _call_judge(prompt)
    obj = _parse_json_block(text)
    mech = obj.get("mechanism")
    if isinstance(mech, str) and mech.strip().lower() in ("", "null", "none"):
        mech = None
    return {
        "compound": (obj.get("compound") or "").strip(),
        "mechanism": mech.strip() if isinstance(mech, str) else None,
        "disease": (obj.get("disease") or "").strip(),
    }


def run_decomposition() -> list[dict]:
    log(f"Decomposing {len(TIERED_HYPOTHESES)} hypotheses (parser: "
        f"{get_judge_model()}, parsing only — no scoring)...")
    rows: list[dict] = []
    for h in TIERED_HYPOTHESES:
        parsed = decompose_hypothesis(h["text"])
        case0 = parsed["mechanism"] is None
        rows.append({
            "source_id": h["source_id"],
            "tier": h["tier"],
            "compound": parsed["compound"],
            "mechanism": parsed["mechanism"],
            "disease": parsed["disease"],
            "case0_undecomposable": case0,
            "text": h["text"],
        })
        log(f"  {h['source_id']} (T{h['tier']}): compound={parsed['compound']!r}, "
            f"mechanism={parsed['mechanism']!r}"
            f"{'  <- CASE 0' if case0 else ''}")
    return rows


def print_decomposition_table(rows: list[dict]) -> None:
    print("\n" + "=" * 100)
    print("STEP 1 — DECOMPOSITION TABLE (verify by hand before proceeding)")
    print("=" * 100)
    header = f"{'ID':<6} {'Tier':<5} {'Compound':<14} {'Mechanism (B)':<40} {'Case 0?':<8}"
    print(header)
    print("-" * 100)
    for r in rows:
        mech = r["mechanism"] if r["mechanism"] is not None else "— (null)"
        print(f"{r['source_id']:<6} {r['tier']:<5} {r['compound']:<14} "
              f"{mech[:40]:<40} {'YES' if r['case0_undecomposable'] else '':<8}")
    print("-" * 100)
    n_case0 = sum(1 for r in rows if r["case0_undecomposable"])
    print(f"{len(rows)} hypotheses; {n_case0} flagged Case 0 (undecomposable / no "
          f"specific mechanism).")
    print("=" * 100)


def main() -> None:
    do_run = "--run" in sys.argv

    rows = run_decomposition()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "structural_decomposition.json").write_text(json.dumps(rows, indent=2))
    print_decomposition_table(rows)

    if not do_run:
        print("\n[STOP] Step 1 complete. Decomposition written to "
              "results/validation/structural_decomposition.json")
        print("Review the table above. If the parse is correct, re-run with --run "
              "to execute Steps 2-4 (PubMed queries + classification).")
        return

    # Steps 2-4 are implemented in a later turn, after manual review of Step 1.
    raise SystemExit("--run path not yet enabled; awaiting decomposition review.")


if __name__ == "__main__":
    main()
