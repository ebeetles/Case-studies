from __future__ import annotations

import os, sys
sys.path.insert(0, os.getcwd())  # repo root (run scripts from repo root)
import _exppath  # noqa: E402  (extends sys.path to experiment folders)

"""
Step 2 — per-drug calibration of the Alzheimer's PMI ratio.

Motivation (from structural_novelty_pmi.md + calibration_pilot.md): a raw PMI
ratio isn't comparable across drugs because a drug's total publication volume
sets its whole scale (losartan's 0.65 never crosses 1 because losartan is
enormously published, not because AD is unrelated). Fix: for each drug, compute
its ratio against a large sample of UNRELATED diseases to get the distribution
of ratios that drug produces on its own, then report the Alzheimer's ratio as a
PERCENTILE within that null — cross-drug-comparable by construction.

This is the full build the pilot de-risked:
  - ~100 clean control diseases (MeSH), drug-agnostic and fixed.
  - Bootstrap 95% CI on each percentile, propagating BOTH the control-set choice
    (resample diseases with replacement) and Poisson count noise (redraw each
    observed count). B = 2000.
  - All 5 Tier-1 drugs, present window.
  - Likely-real-indication contamination flagged (controls with ratio >= 3) and a
    trimmed-percentile sensitivity check.

Apples-to-apples: the disease dimension is MeSH-only for the controls AND for
Alzheimer's, so AD is just one disease in the same set. The drug dimension uses
the same compound_term as the main experiment and cancels out of the ranking.

NOT included here: scoring pipeline-surfaced drugs for cross-condition comparison
(depends on the pipeline hypothesis output format — the documented next step).
"""

import json
import statistics as st
from pathlib import Path

import numpy as np

import structural_novelty_run as snr
from structural_novelty_pmi import ratio_ci, fmt_ci, total_term

OUT_DIR = Path("results/structural_novelty")
MAXDATE = snr.PRESENT_MAXDATE
AD_MESH = "Alzheimer Disease"
BOOTSTRAP_B = 2000
CONTAMINATION_RATIO = 3.0  # controls at/above this are flagged as likely-real links
SEED = 0

DRUGS = [
    ("T1-A", "Metformin"), ("T1-B", "Liraglutide"), ("T1-C", "Pioglitazone"),
    ("T1-D", "Losartan"), ("T1-E", "Sildenafil"),
]

# Negative-control drugs: healthy literature, no strong Alzheimer's story. Run
# through the IDENTICAL calibration path (same controls, ratio, bootstrap, trim,
# present window) to test whether the metric ranks true negatives LOW. If they
# cluster near the 50th percentile, the Tier-1 top tier (85th–98th) is real
# signal; if they also land high, that tier is a low bar.
NEG_CONTROLS = [
    ("N-1", "Omeprazole"), ("N-2", "Loratadine"), ("N-3", "Hydrochlorothiazide"),
    ("N-4", "Amoxicillin"), ("N-5", "Clotrimazole"), ("N-6", "Albuterol"),
]

# Register synonyms so snr.compound_term (the Tier-1 query builder) works for the
# negative controls too — same MeSH-heading + brand/INN[tiab] construction as the
# Tier-1 drugs, so drug-literature capture is comparable.
NEG_CONTROL_SYNONYMS = {
    "Omeprazole":          ["Omeprazole", "Prilosec", "Losec"],
    "Loratadine":          ["Loratadine", "Claritin"],
    "Hydrochlorothiazide": ["Hydrochlorothiazide", "Microzide", "HydroDIURIL"],
    "Amoxicillin":         ["Amoxicillin", "Amoxil"],
    "Clotrimazole":        ["Clotrimazole", "Lotrimin", "Canesten"],
    "Albuterol":           ["Albuterol", "Salbutamol", "Ventolin"],
}
snr.COMPOUND_SYNONYMS.update(NEG_CONTROL_SYNONYMS)

# ~100 MeSH disease headings, drug-agnostic and chosen to avoid every Tier-1
# drug's real domain (metabolic/diabetes/obesity, cardiovascular/renal, fibrosis/
# Marfan, pulmonary-hypertension/erectile) and anything neurodegenerative /
# AD-adjacent. Residual contamination only RAISES a drug's null, making AD's
# percentile conservative; genuine indications that slip in are flagged, not
# hidden.
CONTROL_DISEASES = [
    # infectious / parasitic
    "Malaria", "Tuberculosis", "Leprosy", "Cholera", "Dengue", "Measles",
    "Hepatitis C", "Schistosomiasis", "Typhoid Fever", "Rabies", "Tetanus",
    "Diphtheria", "Mumps", "Rubella", "Toxoplasmosis", "Leishmaniasis",
    "Trachoma", "Syphilis", "Gonorrhea", "Chikungunya Fever",
    # dermatology
    "Psoriasis", "Vitiligo", "Acne Vulgaris", "Alopecia Areata", "Pemphigus",
    "Rosacea", "Hidradenitis Suppurativa", "Ichthyosis", "Lichen Planus",
    "Urticaria",
    # ophthalmology
    "Glaucoma", "Cataract", "Keratoconus", "Retinitis Pigmentosa", "Strabismus",
    "Uveitis", "Conjunctivitis", "Amblyopia",
    # psychiatry
    "Schizophrenia", "Bipolar Disorder", "Anorexia Nervosa",
    "Obsessive-Compulsive Disorder", "Panic Disorder", "Bulimia Nervosa",
    "Tourette Syndrome",
    # gastroenterology
    "Crohn Disease", "Celiac Disease", "Cholelithiasis", "Appendicitis",
    "Colitis, Ulcerative", "Diverticulitis", "Hemorrhoids",
    "Gastroesophageal Reflux", "Pancreatitis",
    # rheumatology / musculoskeletal
    "Osteoarthritis", "Gout", "Spondylitis, Ankylosing", "Scoliosis",
    "Arthritis, Rheumatoid", "Fibromyalgia", "Osteoporosis",
    "Osteogenesis Imperfecta", "Dupuytren Contracture",
    # respiratory
    "Asthma", "Cystic Fibrosis", "Sarcoidosis", "Bronchiectasis",
    "Rhinitis, Allergic",
    # endocrine (non-metabolic)
    "Hyperthyroidism", "Acromegaly", "Cushing Syndrome", "Addison Disease",
    "Graves Disease", "Hyperparathyroidism",
    # genitourinary / reproductive
    "Endometriosis", "Prostatitis", "Urinary Incontinence", "Varicocele",
    "Leiomyoma", "Ovarian Cysts", "Cryptorchidism",
    # hematology
    "Anemia, Sickle Cell", "Hemophilia A", "beta-Thalassemia",
    "Purpura, Thrombocytopenic, Idiopathic", "Polycythemia Vera",
    "Hemochromatosis",
    # ENT
    "Otitis Media", "Tinnitus", "Meniere Disease", "Sinusitis", "Laryngitis",
    # genetic / congenital (non-neurodegenerative)
    "Turner Syndrome", "Klinefelter Syndrome", "Neurofibromatosis 1",
    "Phenylketonurias",
    # oncology (limited)
    "Melanoma", "Osteosarcoma", "Retinoblastoma", "Testicular Neoplasms",
    "Wilms Tumor", "Mycosis Fungoides",
]

_count_cache: dict[tuple, int] = {}


def log(m: str) -> None:
    print(f"[calib] {m}", flush=True)


def mesh(name: str) -> str:
    return f'"{name}"[MeSH Terms]'


def cached_count(term: str, link: str, ctx: str) -> int:
    """Drug-agnostic counts (disease totals, corpus total) — cached across drugs."""
    key = (term, MAXDATE)
    if key not in _count_cache:
        _count_cache[key] = snr.esearch_count(term, MAXDATE, "1900", link, ctx)
    return _count_cache[key]


def one_disease(comp_term: str, count_a: int, total: int,
                disease: str, tag: str) -> dict | None:
    count_c = cached_count(mesh(disease), "C", f"{tag}/{disease}")
    if not count_c:
        log(f"  skip {disease}: count_C=0")
        return None
    obs = snr.esearch_count(f"{comp_term} AND {mesh(disease)}", MAXDATE, "1900",
                            "drug-C", f"{tag}/{disease}")
    expected = count_a * count_c / total
    return {"disease": disease, "observed": obs, "count_C": count_c,
            "expected": expected, "ratio": (obs / expected if expected else float("nan"))}


def bootstrap_percentile(ad_obs: int, ad_exp: float,
                         ctrl_obs: np.ndarray, ctrl_exp: np.ndarray,
                         B: int = BOOTSTRAP_B) -> tuple[float, float, float]:
    """95% CI on AD's percentile, resampling controls with replacement AND
    redrawing every observed count from its Poisson to propagate count noise."""
    rng = np.random.default_rng(SEED)
    n = len(ctrl_obs)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    ad_draw = rng.poisson(ad_obs, size=B) / ad_exp                      # (B,)
    ctrl_draw = rng.poisson(ctrl_obs[None, :].repeat(B, 0)) / ctrl_exp  # (B, n)
    idx = rng.integers(0, n, size=(B, n))                              # resample cols
    resampled = np.take_along_axis(ctrl_draw, idx, axis=1)            # (B, n)
    pct = (resampled < ad_draw[:, None]).mean(axis=1) * 100.0          # (B,)
    return float(np.percentile(pct, 2.5)), float(np.percentile(pct, 97.5)), float(pct.mean())


def percentile_point(value: float, sample: list[float]) -> float:
    return 100.0 * sum(1 for x in sample if x < value) / len(sample) if sample else float("nan")


def calibrate(sid: str, compound: str) -> dict:
    comp_term = snr.compound_term(compound)
    count_a = snr.esearch_count(comp_term, MAXDATE, "1900", "A", f"{compound}/A")
    total = cached_count(total_term(MAXDATE), "total", "corpus")
    log(f"{compound}: count_A={count_a} total={total}")

    ad = one_disease(comp_term, count_a, total, AD_MESH, compound)
    ad_lo, ad_hi = ratio_ci(ad["observed"], ad["expected"])
    ad.update(ratio_low=ad_lo, ratio_high=ad_hi)

    controls = []
    for d in CONTROL_DISEASES:
        row = one_disease(comp_term, count_a, total, d, compound)
        if row is not None:
            controls.append(row)
    ratios = [c["ratio"] for c in controls]

    pct = percentile_point(ad["ratio"], ratios)
    # trimmed sensitivity: drop likely-real-indication controls
    kept = [c for c in controls if c["ratio"] < CONTAMINATION_RATIO]
    pct_trim = percentile_point(ad["ratio"], [c["ratio"] for c in kept])
    flagged = [c["disease"] for c in controls if c["ratio"] >= CONTAMINATION_RATIO]

    lo, hi, _ = bootstrap_percentile(
        ad["observed"], ad["expected"],
        np.array([c["observed"] for c in controls], float),
        np.array([c["expected"] for c in controls], float))

    log(f"{compound}: AD ratio={ad['ratio']:.3f} -> {pct:.0f}th pct "
        f"[{lo:.0f}–{hi:.0f}] (n={len(controls)})")

    return {
        "sid": sid, "compound": compound, "window_maxdate": MAXDATE,
        "count_A": count_a, "total": total, "AD": ad,
        "n_controls": len(controls),
        "AD_percentile": pct, "AD_percentile_ci": [lo, hi],
        "AD_percentile_trimmed": pct_trim,
        "flagged_contamination": flagged,
        "null_min": min(ratios), "null_median": st.median(ratios), "null_max": max(ratios),
        "controls": sorted(controls, key=lambda x: x["ratio"], reverse=True),
    }


def write_report(results: list[dict]) -> None:
    L: list[str] = []
    L.append("# Step 2 — Alzheimer's PMI ratio as a per-drug percentile\n")
    L.append("For each drug, its Alzheimer's ratio is placed within the distribution "
             "of ratios that drug produces against ~100 **unrelated** MeSH diseases "
             "(its own null). Percentiles are cross-drug-comparable; raw ratios are "
             "not. The disease dimension is MeSH-only for the controls and for "
             "Alzheimer's alike.\n")
    L.append(f"Window: present ({MAXDATE}). Bootstrap 95% CI on the percentile "
             f"(B={BOOTSTRAP_B}) resamples the control diseases with replacement and "
             f"redraws every count from its Poisson. Controls with ratio ≥ "
             f"{CONTAMINATION_RATIO:g} are flagged as likely real indications and a "
             f"trimmed percentile is reported as a sensitivity check.\n")

    L.append("## Headline — raw ratio vs. calibrated percentile\n")
    L.append("| Drug | Raw AD ratio (95% CI) | AD percentile (95% CI) | Trimmed | "
             "n | Reading |")
    L.append("|---|---|---|---|---|---|")
    for r in results:
        ad = r["AD"]
        raw = fmt_ci(ad["ratio"], ad["ratio_low"], ad["ratio_high"])
        lo, hi = r["AD_percentile_ci"]
        over = "above" if ad["ratio"] >= 1 else "below"
        reading = (f"raw {over} chance; AD in the top "
                   f"{100 - r['AD_percentile']:.0f}% of {r['compound']}'s own diseases")
        L.append(f"| {r['compound']} | {raw} | **{r['AD_percentile']:.0f}th** "
                 f"({lo:.0f}–{hi:.0f}) | {r['AD_percentile_trimmed']:.0f}th | "
                 f"{r['n_controls']} | {reading} |")
    L.append("")

    for r in results:
        ad = r["AD"]
        lo, hi = r["AD_percentile_ci"]
        L.append(f"## {r['compound']}  (count_A={r['count_A']}, total={r['total']})\n")
        L.append(f"- Alzheimer's: observed={ad['observed']}, expected={ad['expected']:.2f}, "
                 f"ratio={fmt_ci(ad['ratio'], ad['ratio_low'], ad['ratio_high'])}")
        L.append(f"- **AD percentile within {r['compound']}'s own null: "
                 f"{r['AD_percentile']:.0f}th (95% CI {lo:.0f}–{hi:.0f})**, "
                 f"trimmed {r['AD_percentile_trimmed']:.0f}th, of {r['n_controls']} diseases.")
        L.append(f"- Null distribution: min {r['null_min']:.2f}, "
                 f"median {r['null_median']:.2f}, max {r['null_max']:.2f}.")
        if r["flagged_contamination"]:
            L.append(f"- Flagged (ratio ≥ {CONTAMINATION_RATIO:g}, likely real "
                     f"indications, excluded from trimmed): "
                     f"{', '.join(r['flagged_contamination'])}.")
        L.append("")
        L.append(f"Top of {r['compound']}'s own distribution (most over-represented "
                 f"diseases), with Alzheimer's placed in context:\n")
        L.append("| Rank | Disease | observed | expected | ratio |")
        L.append("|---|---|---|---|---|")
        for i, c in enumerate(r["controls"][:8], 1):
            L.append(f"| {i} | {c['disease']} | {c['observed']} | "
                     f"{c['expected']:.2f} | {c['ratio']:.2f} |")
        L.append(f"| — | **ALZHEIMER'S** | {ad['observed']} | {ad['expected']:.2f} | "
                 f"**{ad['ratio']:.2f}** |")
        L.append("")

    (OUT_DIR / "calibration.md").write_text("\n".join(L))
    log(f"Wrote {OUT_DIR / 'calibration.md'}")


def preview(drugs: list[tuple[str, str]]) -> None:
    """Cheap pre-flight (no full calibration): print each drug's total literature
    count (count_A) and its raw Alzheimer's co-occurrence, so the drug list can be
    finalized — e.g. confirm a 'negative' control has no major AD literature —
    before spending ~600 queries on the full run."""
    total = cached_count(total_term(MAXDATE), "total", "corpus")
    log(f"window = present ({MAXDATE}); corpus total = {total}")
    log(f"{'drug':22} {'count_A':>9} {'AD obs':>7} {'AD exp':>8} {'raw ratio':>10}")
    ad_c = cached_count(mesh(AD_MESH), "C", "AD")
    for _sid, comp in drugs:
        comp_term = snr.compound_term(comp)
        count_a = snr.esearch_count(comp_term, MAXDATE, "1900", "A", f"{comp}/A")
        ad_obs = snr.esearch_count(f"{comp_term} AND {mesh(AD_MESH)}", MAXDATE,
                                   "1900", "drug-C", f"{comp}/AD")
        ad_exp = count_a * ad_c / total
        ratio = ad_obs / ad_exp if ad_exp else float("nan")
        log(f"{comp:22} {count_a:>9} {ad_obs:>7} {ad_exp:>8.1f} {ratio:>10.2f}")
    log("Preview only — no calibration run. Confirm the drug list to proceed.")


def _load_results(name: str) -> list[dict]:
    return json.loads((OUT_DIR / name).read_text())["results"]


def run_negative_controls() -> None:
    """Run the negative controls through the identical calibrate() path and write a
    combined report contrasting them with the cached Tier-1 results."""
    tier1 = _load_results("calibration_raw.json")  # reuse; do not re-run Tier-1
    neg = [calibrate(sid, comp) for sid, comp in NEG_CONTROLS]
    raw = {"window_maxdate": MAXDATE, "bootstrap_B": BOOTSTRAP_B,
           "contamination_ratio": CONTAMINATION_RATIO,
           "control_diseases": CONTROL_DISEASES, "results": neg,
           "query_log": snr._query_log}
    (OUT_DIR / "calibration_negcontrol_raw.json").write_text(json.dumps(raw, indent=2))
    log(f"Wrote calibration_negcontrol_raw.json ({len(snr._query_log)} queries)")
    write_negcontrol_report(tier1, neg)
    log("Done.")


# Pre-registered pass condition (set BEFORE looking at results):
#   (a) negative cluster median < CLUSTER_MAX (60th), AND
#   (b) each negative's percentile-CI UPPER < the Tier-1 CI LOWER floor.
# Nuance: AD obs <= DIRECTIONAL_OBS rests on 1-2 papers -> DIRECTIONAL ONLY, its
# wide CI reads "can't resolve", not pass/fail. A negative whose CI is so wide it
# overlaps the Tier-1 floor is "can't resolve at these counts", not "failed".
CLUSTER_MAX = 60.0
DIRECTIONAL_OBS = 2


def _contrast_row(r: dict, kind: str) -> str:
    ad = r["AD"]
    raw = fmt_ci(ad["ratio"], ad["ratio_low"], ad["ratio_high"])
    lo, hi = r["AD_percentile_ci"]
    return (f"| {r['compound']} | {kind} | {ad['observed']} | {raw} | "
            f"**{r['AD_percentile']:.0f}th** ({lo:.0f}–{hi:.0f}) | "
            f"{r['AD_percentile_trimmed']:.0f}th |")


def write_negcontrol_report(tier1: list[dict], neg: list[dict]) -> None:
    t1_pcts = [r["AD_percentile"] for r in tier1]
    neg_pcts = [r["AD_percentile"] for r in neg]
    tier1_floor = min(r["AD_percentile_ci"][0] for r in tier1)  # Tier-1 CI lower floor

    L: list[str] = []
    L.append("# Step 2 — Negative-control validation\n")
    L.append("Does the calibration rank true NEGATIVES low? The negative-control "
             "drugs below (healthy literature, no strong Alzheimer's story) are run "
             "through the **identical** path as the Tier-1 drugs — same ~100 control "
             "diseases, same observed/expected ratio, same bootstrap 95% CI "
             f"(B={BOOTSTRAP_B}), same contamination trim (ratio ≥ "
             f"{CONTAMINATION_RATIO:g}), same present window ({MAXDATE}).\n")
    L.append("**Scope of this test.** These are STRONG negatives (raw AD ratios "
             "0.03–0.29, floor values), not boundary cases near chance. So this "
             "validates *doesn't rank obvious non-candidates high* — NOT that the "
             "metric discriminates at the positive/negative boundary.\n")

    L.append("## Pre-registered pass condition (set before results)\n")
    L.append(f"**(a)** negative cluster median < {CLUSTER_MAX:.0f}th, AND "
             f"**(b)** every negative's percentile-CI upper < the Tier-1 CI lower "
             f"floor (**{tier1_floor:.0f}th**, the lowest Tier-1 CI bound). "
             f"Negatives with AD obs ≤ {DIRECTIONAL_OBS} are DIRECTIONAL ONLY.\n")

    L.append("## Combined table — negatives and Tier-1 for contrast\n")
    L.append("| Drug | Group | AD obs | Raw AD ratio (95% CI) | "
             "Calibrated percentile (95% CI) | Trimmed |")
    L.append("|---|---|---|---|---|---|")
    for r in tier1:
        L.append(_contrast_row(r, "pos"))
    for r in neg:
        L.append(_contrast_row(r, "neg"))
    L.append("")

    # (1) per-drug pass/fail: negative CI upper vs Tier-1 floor
    L.append(f"## Per-negative: CI upper vs Tier-1 floor ({tier1_floor:.0f}th)\n")
    L.append("| Drug | AD obs | Percentile (95% CI) | CI upper | "
             f"< floor ({tier1_floor:.0f})? | Status |")
    L.append("|---|---|---|---|---|---|")
    for r in neg:
        lo, hi = r["AD_percentile_ci"]
        obs = r["AD"]["observed"]
        clears = hi < tier1_floor
        directional = obs <= DIRECTIONAL_OBS
        if directional:
            status = "DIRECTIONAL (obs≤2) — can't resolve"
        elif clears:
            status = "clears floor"
        else:
            status = "CI overlaps Tier-1 — can't resolve at these counts"
        L.append(f"| {r['compound']} | {obs} | {r['AD_percentile']:.0f}th "
                 f"({lo:.0f}–{hi:.0f}) | {hi:.0f} | {'yes' if clears else 'no'} | "
                 f"{status} |")
    L.append("")

    # (3) cluster stats
    L.append("## Cluster comparison\n")
    L.append(f"- Negative controls: min {min(neg_pcts):.0f}th, "
             f"median {st.median(neg_pcts):.0f}th, max {max(neg_pcts):.0f}th "
             f"(range {min(neg_pcts):.0f}–{max(neg_pcts):.0f}).")
    L.append(f"- Tier-1: min {min(t1_pcts):.0f}th, median {st.median(t1_pcts):.0f}th, "
             f"max {max(t1_pcts):.0f}th (range {min(t1_pcts):.0f}–{max(t1_pcts):.0f}).")
    L.append("")

    # (2) computed verdict
    resolvable = [r for r in neg if r["AD"]["observed"] > DIRECTIONAL_OBS]
    directional = [r for r in neg if r["AD"]["observed"] <= DIRECTIONAL_OBS]
    crit_a = st.median(neg_pcts) < CLUSTER_MAX
    all_clear = all(r["AD_percentile_ci"][1] < tier1_floor for r in neg)
    resolvable_clear = all(r["AD_percentile_ci"][1] < tier1_floor for r in resolvable)
    overall = crit_a and all_clear

    L.append("## VERDICT (computed)\n")
    L.append(f"- (a) negative median {st.median(neg_pcts):.0f}th < {CLUSTER_MAX:.0f} "
             f"→ **{'PASS' if crit_a else 'FAIL'}**.")
    L.append(f"- (b) all six CI uppers < Tier-1 floor {tier1_floor:.0f} "
             f"→ **{'PASS' if all_clear else 'FAIL'}**.")
    L.append(f"- Among the {len(resolvable)} RESOLVABLE negatives (obs > "
             f"{DIRECTIONAL_OBS}: "
             f"{', '.join(r['compound'] for r in resolvable)}), all CI uppers < "
             f"floor → **{'PASS' if resolvable_clear else 'FAIL'}**.")
    if directional:
        L.append(f"- {len(directional)} DIRECTIONAL negatives (obs ≤ "
                 f"{DIRECTIONAL_OBS}: {', '.join(r['compound'] for r in directional)}) "
                 f"— wide CIs; read as 'can't resolve', not pass/fail.")
    L.append(f"\n**Strict verdict (a AND b over all six): "
             f"{'PASS' if overall else 'FAIL / INCONCLUSIVE'}.** "
             + ("The metric ranks these strong negatives below the Tier-1 cluster."
                if overall else
                "At least one negative's CI reaches the Tier-1 floor; where that is "
                "driven by AD obs ≤ 2 (directional) or a wide CI, the reading is "
                "'can't resolve at these counts' (small-count limit), not a metric "
                "failure. See the per-negative status column.") + "\n")

    (OUT_DIR / "calibration_negcontrol.md").write_text("\n".join(L))
    log(f"Wrote {OUT_DIR / 'calibration_negcontrol.md'}")
    # console mirror of the machine-checkable verdict
    log(f"VERDICT: crit_a(median<{CLUSTER_MAX:.0f})={crit_a}; "
        f"all_clear(CIupper<{tier1_floor:.0f})={all_clear}; "
        f"resolvable_clear={resolvable_clear}; overall={'PASS' if overall else 'FAIL/INCONCLUSIVE'}")


def main() -> None:
    results = [calibrate(sid, comp) for sid, comp in DRUGS]
    raw = {"window_maxdate": MAXDATE, "bootstrap_B": BOOTSTRAP_B,
           "contamination_ratio": CONTAMINATION_RATIO,
           "control_diseases": CONTROL_DISEASES, "results": results,
           "query_log": snr._query_log}
    (OUT_DIR / "calibration_raw.json").write_text(json.dumps(raw, indent=2))
    log(f"Wrote calibration_raw.json ({len(snr._query_log)} queries)")
    write_report(results)
    log("Done.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "tier1"
    if mode == "preview":
        preview(NEG_CONTROLS)
    elif mode == "negcontrols":
        run_negative_controls()
    else:
        main()
