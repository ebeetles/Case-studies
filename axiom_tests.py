from __future__ import annotations

"""
Axiom compliance tests for the PMI novelty metric.

Checks our PMI A-C association metric against the axiomatic framework for
scientific-novelty metrics (Liu & Zhai, UIUC 2026, arXiv:2604.15145), which
defines logical conditions any valid novelty metric should satisfy.

Scope: the two high-confidence Tier-1 compounds with clean cutoffs —
metformin (2011) and liraglutide (2021, per task spec) — reusing the baseline
pre-cutoff PMI counts already computed in structural_novelty_pmi_raw.json.
NOTHING is re-queried for Axioms 1-2 (they are arithmetic on the cached
counts). Axiom 4 issues a handful of fresh off-topic esearch counts. Axioms
7-8 are NOT rerun — they are reframed from results/validation/novelty_decay.md
and the pre-registered decay success criterion (structural_novelty_pmi.md).

PMI A-C ratio:  observed(A,C) / (count(A) * count(C) / total)
  > 1  = A and C co-occur above chance (connection established)
  < 1  = below chance (not established)

Injecting one paper that names the compound and "Alzheimer's" adds 1 to the
observed A-C co-occurrence, to count(A), to count(C), and to total — that is
what "adding a paper to the dated corpus" means for a count-based metric.
No paper is submitted anywhere; the injected abstracts are synthetic test
inputs, labelled as such in the output.
"""

import json
from pathlib import Path

import structural_novelty_run as snr

OUT_DIR = Path("results/validation")
RAW = OUT_DIR / "structural_novelty_pmi_raw.json"

# --- Synthetic test papers (NOT real; never submitted to PubMed) --------------
# Axiom 1: explicit statement of the drug->disease connection.
SYN_EXPLICIT = {
    "Metformin":   "Metformin has been proposed as a treatment for Alzheimer's "
                   "disease via AMPK activation.",
    "Liraglutide": "Liraglutide has been proposed as a treatment for Alzheimer's "
                   "disease via GLP-1 receptor signaling.",
}
# Axiom 2: paraphrase — same connection, different wording.
SYN_PARAPHRASE = {
    "Metformin":   "Evidence suggests metformin may modulate AMPK pathways "
                   "implicated in Alzheimer's disease neurodegeneration.",
    "Liraglutide": "Evidence suggests liraglutide may modulate GLP-1 receptor "
                   "pathways implicated in Alzheimer's disease neurodegeneration.",
}


def pmi_ratio(observed: int, count_a: int, count_c: int, total: int) -> float:
    expected = (count_a * count_c / total) if total else float("nan")
    return (observed / expected) if expected else float("nan")


def matches_ac(abstract: str, compound: str) -> bool:
    """Does the synthetic abstract match BOTH the compound term and the AD term
    used by the PMI queries? (Boolean term co-occurrence — the only thing PMI
    counts.) Compound synonyms + 'Alzheimer' stem, per snr's query builders."""
    text = abstract.lower()
    syns = [compound.lower()] + [s.lower() for s in snr.COMPOUND_SYNONYMS[compound]]
    hit_a = any(s in text for s in syns)
    hit_c = "alzheimer" in text
    return hit_a and hit_c


def inject_one(base: dict, abstract: str, compound: str) -> dict:
    """Return the A-C PMI after adding one paper. If the paper's text contains
    both the compound term and 'Alzheimer', it increments observed(A,C),
    count(A), count(C) and total by 1; otherwise only total (a corpus paper
    that doesn't mention the pair still enlarges the pool)."""
    hit = matches_ac(abstract, compound)
    d = 1 if hit else 0
    obs = base["observed_AC"] + d
    ca = base["count_A"] + d
    cc = base["count_C"] + d
    tot = base["total"] + 1
    return {
        "matched_AC": hit,
        "observed_AC": obs, "count_A": ca, "count_C": cc, "total": tot,
        "pmi_AC": pmi_ratio(obs, ca, cc, tot),
    }


# --- Axiom 4: off-topic corpus ------------------------------------------------
OFF_TOPIC = ('("materials science"[Title/Abstract] OR "semiconductor"'
             '[Title/Abstract] OR "fluid dynamics"[Title/Abstract])')


def axiom4_offtopic(compound: str, maxdate: str) -> dict:
    """Score compound-AD PMI against an off-topic corpus (materials science /
    semiconductor / fluid dynamics), same pre-cutoff window. The 'corpus' is
    the set of off-topic papers in the window; counts are taken *within* it."""
    comp = snr.compound_term(compound)
    dis = snr.DISEASE_TERM
    total = snr.esearch_count(OFF_TOPIC, maxdate, "1900", "offtopic-total",
                              f"axiom4/{compound}")
    ca = snr.esearch_count(f"{OFF_TOPIC} AND {comp}", maxdate, "1900",
                           "offtopic-A", f"axiom4/{compound}")
    cc = snr.esearch_count(f"{OFF_TOPIC} AND {dis}", maxdate, "1900",
                           "offtopic-C", f"axiom4/{compound}")
    obs = snr.esearch_count(f"{OFF_TOPIC} AND {comp} AND {dis}", maxdate, "1900",
                            "offtopic-A-C", f"axiom4/{compound}")
    return {
        "maxdate": maxdate, "corpus_size": total,
        "count_A": ca, "count_C": cc, "observed_AC": obs,
        "expected_AC": (ca * cc / total) if total else float("nan"),
        "pmi_AC": pmi_ratio(obs, ca, cc, total),
    }


def main() -> None:
    raw = json.loads(RAW.read_text())["pmi_results"]
    compounds = {"Metformin": "T1-A", "Liraglutide": "T1-B"}

    out: dict = {"axiom1": {}, "axiom2": {}, "axiom4": {}}

    for compound, sid in compounds.items():
        base = raw[sid]["windows"]["pre_cutoff"]  # observed/count/total/pmi
        base_slim = {k: base[k] for k in
                     ("observed_AC", "count_A", "count_C", "total")}
        base_slim["pmi_AC"] = base["pmi_AC"]

        a1 = inject_one(base, SYN_EXPLICIT[compound], compound)
        a2 = inject_one(base, SYN_PARAPHRASE[compound], compound)
        out["axiom1"][compound] = {"baseline": base_slim,
                                   "injected_abstract": SYN_EXPLICIT[compound],
                                   "after": a1}
        out["axiom2"][compound] = {"baseline": base_slim,
                                   "injected_abstract": SYN_PARAPHRASE[compound],
                                   "after": a2}
        print(f"[axiom1] {compound}: pmi {base['pmi_AC']:.4f} -> {a1['pmi_AC']:.4f} "
              f"({'UP' if a1['pmi_AC'] > base['pmi_AC'] else 'not up'})")
        print(f"[axiom2] {compound}: pmi {base['pmi_AC']:.4f} -> {a2['pmi_AC']:.4f} "
              f"({'UP' if a2['pmi_AC'] > base['pmi_AC'] else 'not up'})")

    # Axiom 4 — metformin only (task spec), pre-2011 window.
    met_pre = raw["T1-A"]["windows"]["pre_cutoff"]
    off = axiom4_offtopic("Metformin", "2010/12/31")
    out["axiom4"]["Metformin"] = {
        "offtopic": off,
        "baseline_ad_corpus_pmi": met_pre["pmi_AC"],
        "baseline_window": met_pre["maxdate"],
    }
    print(f"[axiom4] Metformin off-topic: corpus={off['corpus_size']} "
          f"A={off['count_A']} C={off['count_C']} obs={off['observed_AC']} "
          f"pmi={off['pmi_AC']} vs AD-corpus baseline {met_pre['pmi_AC']:.4f}")

    out["query_log_axiom4"] = snr._query_log
    (OUT_DIR / "axiom_tests_raw.json").write_text(json.dumps(out, indent=2))
    print(f"[axiom] wrote {OUT_DIR/'axiom_tests_raw.json'}")


if __name__ == "__main__":
    main()
