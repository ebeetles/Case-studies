from __future__ import annotations

import os, sys
sys.path.insert(0, os.getcwd())  # repo root (run scripts from repo root)
import _exppath  # noqa: E402  (extends sys.path to experiment folders)

"""
Step-2 calibration PILOT (de-risking, before building the full machinery).

Question: a drug's raw Alzheimer's PMI ratio isn't comparable across drugs
because the drug's total publication volume sets its whole scale (losartan's
0.65 never crosses 1 not because AD is unrelated but because losartan is
enormously published). Fix: for one drug, compute its ratio against a large
sample of UNRELATED diseases -> the distribution of ratios that drug produces
on its own -> report the Alzheimer's ratio as a PERCENTILE within that null,
not as a raw number.

If AD lands high in the drug's own distribution even when the raw ratio is <1,
calibration recovers signal the raw ratio hides, and the full Step 2 is worth
building. If AD is middling, calibration won't save it.

Apples-to-apples: the DISEASE dimension is MeSH-only for the controls AND for
Alzheimer's (so AD is just one disease in the same set). The drug dimension uses
the same compound_term as the main experiment and cancels out of the ranking.

Scope: pilot on the two most informative cases — losartan (raw ratio never
crosses chance) and sildenafil (~chance, but a genuine repurposing story).
Window: present (2026/07/20), the most-counts / most-stable window.
No new machinery is committed downstream; this only writes a pilot report.
"""

import json
from pathlib import Path

import structural_novelty_run as snr
from structural_novelty import TIER1_CUTOFFS
from structural_novelty_pmi import ratio_ci, fmt_ci, total_term

OUT_DIR = Path("results/structural_novelty")
MAXDATE = snr.PRESENT_MAXDATE

# Compounds to calibrate: (sid, compound). sid feeds the mech term if needed.
DRUGS = [("T1-D", "Losartan"), ("T1-E", "Sildenafil")]

AD_MESH = '"Alzheimer Disease"[MeSH Terms]'

# ~40 MeSH disease headings chosen to be UNRELATED to the drugs under test:
# nothing cardiovascular / renal / fibrotic / Marfan / diabetes (losartan's
# domains), nothing pulmonary-hypertension / erectile / Raynaud (sildenafil's),
# and nothing neurodegenerative (AD-adjacent). A little contamination only
# raises the null and makes AD's percentile CONSERVATIVE.
CONTROL_DISEASES = [
    "Malaria", "Tuberculosis", "Leprosy", "Cholera", "Dengue", "Measles",
    "Hepatitis C", "Schistosomiasis",
    "Melanoma", "Osteosarcoma", "Retinoblastoma", "Pancreatic Neoplasms",
    "Leukemia, Myeloid, Acute", "Uterine Cervical Neoplasms",
    "Psoriasis", "Vitiligo", "Acne Vulgaris", "Alopecia Areata", "Pemphigus",
    "Glaucoma", "Cataract", "Keratoconus", "Retinitis Pigmentosa",
    "Schizophrenia", "Bipolar Disorder", "Anorexia Nervosa",
    "Obsessive-Compulsive Disorder",
    "Crohn Disease", "Celiac Disease", "Cholelithiasis", "Appendicitis",
    "Osteoarthritis", "Gout", "Spondylitis, Ankylosing", "Scoliosis",
    "Asthma", "Cystic Fibrosis",
    "Hyperthyroidism", "Acromegaly", "Endometriosis",
]


def log(m: str) -> None:
    print(f"[calib] {m}", flush=True)


def ratio_for(comp_term: str, count_a: int, total: int,
              disease_mesh: str, tag: str) -> tuple[int, int, float, float]:
    """Return (observed, count_disease, expected, ratio) for drug × disease."""
    disease_term = f'"{disease_mesh}"[MeSH Terms]'
    count_c = snr.esearch_count(disease_term, MAXDATE, "1900", "C", tag)
    obs = snr.esearch_count(f"{comp_term} AND {disease_term}", MAXDATE, "1900",
                            "drug-C", tag)
    expected = (count_a * count_c / total) if total else float("nan")
    ratio = (obs / expected) if expected else float("nan")
    return obs, count_c, expected, ratio


def percentile_of(value: float, sample: list[float]) -> float:
    """Fraction of the sample strictly below `value` (0-100)."""
    if not sample:
        return float("nan")
    below = sum(1 for x in sample if x < value)
    return 100.0 * below / len(sample)


def calibrate(sid: str, compound: str) -> dict:
    comp_term = snr.compound_term(compound)
    count_a = snr.esearch_count(comp_term, MAXDATE, "1900", "A", f"{compound}/A")
    total = snr.esearch_count(total_term(MAXDATE), MAXDATE, "1900", "total",
                              f"{compound}/total")
    log(f"{compound}: count_A={count_a} total={total}")

    # Alzheimer's, computed MeSH-only so it sits in the same set as the controls.
    ad_c = snr.esearch_count(AD_MESH, MAXDATE, "1900", "C", f"{compound}/AD")
    ad_obs = snr.esearch_count(f"{comp_term} AND {AD_MESH}", MAXDATE, "1900",
                               "drug-C", f"{compound}/AD")
    ad_exp = count_a * ad_c / total
    ad_ratio = ad_obs / ad_exp if ad_exp else float("nan")
    ad_lo, ad_hi = ratio_ci(ad_obs, ad_exp)
    log(f"{compound}: AD obs={ad_obs} exp={ad_exp:.2f} ratio={ad_ratio:.3f}")

    controls = []
    for d in CONTROL_DISEASES:
        obs, c, exp, r = ratio_for(comp_term, count_a, total, d, f"{compound}/{d}")
        if not c:  # MeSH heading returned nothing — skip, not a valid control
            log(f"  skip {d}: count_C=0")
            continue
        controls.append({"disease": d, "observed": obs, "count_C": c,
                         "expected": exp, "ratio": r})
    ratios = [c["ratio"] for c in controls]
    pct = percentile_of(ad_ratio, ratios)
    controls_sorted = sorted(controls, key=lambda x: x["ratio"])

    return {
        "sid": sid, "compound": compound, "window_maxdate": MAXDATE,
        "count_A": count_a, "total": total,
        "AD": {"observed": ad_obs, "count_C": ad_c, "expected": ad_exp,
               "ratio": ad_ratio, "ratio_low": ad_lo, "ratio_high": ad_hi},
        "raw_ratio_meshOR_tiab_reference":
            TIER1_CUTOFFS.get(compound, {}),  # for provenance only
        "n_controls": len(controls),
        "AD_percentile": pct,
        "controls_sorted": controls_sorted,
    }


def write_report(results: list[dict]) -> None:
    L: list[str] = []
    L.append("# Step-2 calibration PILOT — Alzheimer's ratio as a per-drug percentile\n")
    L.append("De-risking probe (not the full Step 2). For each drug we compute its "
             "PMI ratio against ~40 **unrelated** MeSH diseases to get the drug's own "
             "null distribution of ratios, then locate the **Alzheimer's** ratio as a "
             "percentile within it. Question: does AD rank high in the drug's own "
             "distribution even when the *raw* ratio is unimpressive (≤1)?\n")
    L.append(f"Window: present ({MAXDATE}). Disease dimension is MeSH-only for both "
             "the controls and Alzheimer's (AD is just one disease in the set). "
             "95% CI on the AD ratio is the exact Poisson interval.\n")

    L.append("## Headline\n")
    L.append("| Drug | Raw AD ratio (95% CI) | AD percentile within drug's own null | "
             "Reading |")
    L.append("|---|---|---|---|")
    for r in results:
        ad = r["AD"]
        raw = fmt_ci(ad["ratio"], ad["ratio_low"], ad["ratio_high"])
        pct = r["AD_percentile"]
        over = "above chance" if ad["ratio"] >= 1 else "**below chance**"
        reading = (f"raw ratio {over}, but AD sits at the {pct:.0f}th percentile "
                   f"of {r['compound']}'s own disease distribution")
        L.append(f"| {r['compound']} | {raw} | **{pct:.0f}th** (n={r['n_controls']}) | "
                 f"{reading} |")
    L.append("")

    for r in results:
        ad = r["AD"]
        L.append(f"## {r['compound']}  (count_A={r['count_A']}, total={r['total']})\n")
        L.append(f"- Alzheimer's: observed={ad['observed']}, expected={ad['expected']:.2f}, "
                 f"ratio={fmt_ci(ad['ratio'], ad['ratio_low'], ad['ratio_high'])}")
        L.append(f"- **AD percentile within {r['compound']}'s own null: "
                 f"{r['AD_percentile']:.0f}th** (of {r['n_controls']} unrelated diseases)")
        ratios = sorted(c["ratio"] for c in r["controls_sorted"])
        import statistics as st
        L.append(f"- Null distribution of {r['compound']} disease ratios: "
                 f"min {min(ratios):.2f}, median {st.median(ratios):.2f}, "
                 f"max {max(ratios):.2f}")
        # show the top of the drug's distribution + where AD would slot
        L.append("")
        L.append(f"Top of {r['compound']}'s own distribution (highest ratios = most "
                 f"over-represented diseases for this drug):\n")
        L.append("| Rank | Disease | observed | expected | ratio |")
        L.append("|---|---|---|---|---|")
        top = sorted(r["controls_sorted"], key=lambda x: x["ratio"], reverse=True)[:8]
        for i, c in enumerate(top, 1):
            L.append(f"| {i} | {c['disease']} | {c['observed']} | "
                     f"{c['expected']:.2f} | {c['ratio']:.2f} |")
        L.append(f"| — | **ALZHEIMER'S** | {ad['observed']} | {ad['expected']:.2f} | "
                 f"**{ad['ratio']:.2f}** |")
        L.append("")

    (OUT_DIR / "calibration_pilot.md").write_text("\n".join(L))
    log(f"Wrote {OUT_DIR / 'calibration_pilot.md'}")


def main() -> None:
    results = [calibrate(sid, comp) for sid, comp in DRUGS]
    raw = {"window_maxdate": MAXDATE, "control_diseases": CONTROL_DISEASES,
           "results": results, "query_log": snr._query_log}
    (OUT_DIR / "calibration_pilot_raw.json").write_text(json.dumps(raw, indent=2))
    log(f"Wrote calibration_pilot_raw.json ({len(snr._query_log)} queries)")
    write_report(results)
    log("Done.")


if __name__ == "__main__":
    main()
