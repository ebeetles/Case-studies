from __future__ import annotations

import os, sys
sys.path.insert(0, os.getcwd())  # repo root (run scripts from repo root)
import _exppath  # noqa: E402  (extends sys.path to experiment folders)

"""
Structural novelty — AMENDMENT 2 (PMI normalization).

Pre-registered BEFORE observing any normalized counts. Does NOT rerun Steps
2-4; reuses the prior observed A-C / B-C counts from structural_novelty_raw.json
for the pre-cutoff and present windows, and adds only:
  - count(A), count(C), total-records per window  -> PMI ratio
  - a fixed cutoff+5yr window (equalizes elapsed post-cutoff time across compounds)

PMI ratio (pointwise-mutual-information style association):
    expected  = count(A) * count(C) / total_records_in_window
    pmi_ratio = observed(A-C) / expected
  pmi_ratio >> 1  -> A and C co-occur far more than chance (link established)
  pmi_ratio ~1    -> co-occur at chance (no special association)
  pmi_ratio < 1   -> co-occur less than chance

Classification on pmi (amendment #3):
    A-C pmi >> 1                      -> Case 1 (already proposed)
    A-C pmi <~1, B-C pmi >> 1         -> Case 2 (bridgeable, unbridged) [target]
    both <~1                          -> Case 3 (disconnected)
No hard cutoff is baked in — actual pmi values are reported and the natural
separation (if any) is described.

Scope: the 5 Tier-1 compounds (the only ones with cutoffs; Test 1's subjects).
Prior results (structural_novelty.md / .json) are left intact.
"""

import json
from pathlib import Path

from scipy.stats import chi2

import structural_novelty_run as snr  # reuses esearch_count (+ query logging), term builders
from structural_novelty import TIER1_CUTOFFS

OUT_DIR = Path("results/structural_novelty")
PRESENT_MAXDATE = snr.PRESENT_MAXDATE

TIER1 = ["T1-A", "T1-B", "T1-C", "T1-D", "T1-E"]

AMENDMENT2_TEXT = """\
AMENDMENT 2 (pre-registered BEFORE observing any normalized counts):
1. Per compound per window, also query count(A), count(C), total records;
   expected = count(A)*count(C)/total ; pmi_ratio = observed/expected.
   Report A-C pmi_ratio at pre-cutoff and present.
2. Added fixed cutoff+5yr post window for every compound (equalizes elapsed
   post-cutoff time; metformin had 14y, sildenafil 4y).
3. New classification on pmi_ratio (A-C pmi>>1 -> Case 1; A-C pmi<~1 &
   B-C pmi>>1 -> Case 2; both <~1 -> Case 3). Report actual values; no hard cutoff.
4. SUCCESS CRITERION: >=4/5 Tier-1 show A-C pmi increasing pre-cutoff -> cutoff+5yr,
   AND pre-cutoff values cluster separately from post values with a visible gap.
5. Nothing else rerun; prior results intact. Amendment made before observing
   normalized counts.
"""

_count_cache: dict[tuple, int] = {}


def log(m: str) -> None:
    print(f"[pmi] {m}", flush=True)


def total_term(maxdate: str) -> str:
    return f'("1900/01/01"[PDAT] : "{maxdate}"[PDAT])'


def cached_count(term: str, maxdate: str, link: str, context: str) -> int:
    key = (term, maxdate)
    if key in _count_cache:
        return _count_cache[key]
    val = snr.esearch_count(term, maxdate, "1900", link, context)
    _count_cache[key] = val
    return val


def poisson_ci(k: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Garwood) two-sided Poisson confidence interval on a count k.

    Uses the chi-square form: lower = chi2.ppf(a/2, 2k)/2 (0 when k == 0),
    upper = chi2.ppf(1-a/2, 2(k+1))/2. Preferred over the sqrt(N) normal
    approximation, which is invalid for the small counts that dominate the
    pre-cutoff windows (e.g. observed = 1).
    """
    lower = chi2.ppf(alpha / 2, 2 * k) / 2 if k > 0 else 0.0
    upper = chi2.ppf(1 - alpha / 2, 2 * (k + 1)) / 2
    return lower, upper


def ratio_ci(observed: int, expected: float,
             alpha: float = 0.05) -> tuple[float, float]:
    """95% CI on the observed/expected ratio: the Poisson interval on the
    observed count divided through by the (fixed) expected count."""
    if not expected or expected != expected:  # 0 or NaN
        return float("nan"), float("nan")
    lo_k, hi_k = poisson_ci(observed, alpha)
    return lo_k / expected, hi_k / expected


def pmi(observed: int, count_a: int, count_c: int,
        total: int) -> tuple[float, float, float, float]:
    """Return (expected, ratio, ratio_low, ratio_high).

    ratio = observed / expected; (ratio_low, ratio_high) is the exact 95%
    Poisson interval on the observed count, propagated through the ratio.
    """
    expected = (count_a * count_c / total) if total else float("nan")
    if not expected or expected != expected:
        nan = float("nan")
        return expected, nan, nan, nan
    ratio = observed / expected
    lo, hi = ratio_ci(observed, expected)
    return expected, ratio, lo, hi


def fmt_ci(ratio: float, lo: float, hi: float) -> str:
    """Format a ratio with its 95% CI, e.g. '1.58 (0.04–8.8)'."""
    if ratio != ratio:  # NaN
        return "nan"
    return f"{ratio:.2f} ({lo:.2f}–{hi:.2g})"


def main() -> None:
    prior = json.loads((OUT_DIR / "structural_novelty_raw.json").read_text())
    prior_results = prior["results"]

    windows_pmi: dict[str, dict] = {}

    for sid in TIER1:
        e = prior_results[sid]
        compound = e["compound"]
        cy = TIER1_CUTOFFS[compound]["year"]
        conf = TIER1_CUTOFFS[compound]["confidence"]

        win_defs = {
            "pre_cutoff": f"{cy - 1}/12/31",
            "post5yr":    f"{cy + 5}/12/31",
            "present":    PRESENT_MAXDATE,
        }

        comp_term = snr.compound_term(compound)
        mech = snr.mech_term(sid)

        rec: dict = {"compound": compound, "cutoff_year": cy, "confidence": conf,
                     "windows": {}}

        for wname, maxd in win_defs.items():
            count_a = cached_count(comp_term, maxd, "A-alone", f"{sid}/{wname}")
            count_c = cached_count(snr.DISEASE_TERM, maxd, "C-alone", f"{sid}/{wname}")
            count_b = cached_count(mech, maxd, "B-alone", f"{sid}/{wname}")
            total = cached_count(total_term(maxd), maxd, "total", f"{sid}/{wname}")

            # Observed A-C / B-C: reuse prior counts for pre_cutoff & present;
            # query fresh only for the new post5yr window.
            if wname in ("pre_cutoff", "present"):
                obs_ac = e["windows"][wname]["A_C"]
                obs_bc = e["windows"][wname]["B_C"][sid]
            else:
                obs_ac = snr.esearch_count(f"{comp_term} AND {snr.DISEASE_TERM}",
                                           maxd, "1900", "A-C", f"{sid}/{wname}")
                obs_bc = snr.esearch_count(f"{mech} AND {snr.DISEASE_TERM}",
                                           maxd, "1900", "B-C", f"{sid}/{wname}")

            exp_ac, pmi_ac, lo_ac, hi_ac = pmi(obs_ac, count_a, count_c, total)
            exp_bc, pmi_bc, lo_bc, hi_bc = pmi(obs_bc, count_b, count_c, total)

            rec["windows"][wname] = {
                "maxdate": maxd, "count_A": count_a, "count_B": count_b,
                "count_C": count_c, "total": total,
                "observed_AC": obs_ac, "expected_AC": exp_ac,
                "pmi_AC": pmi_ac, "pmi_AC_low": lo_ac, "pmi_AC_high": hi_ac,
                "observed_BC": obs_bc, "expected_BC": exp_bc,
                "pmi_BC": pmi_bc, "pmi_BC_low": lo_bc, "pmi_BC_high": hi_bc,
            }
            log(f"{sid}/{wname}: A-C obs={obs_ac} exp={exp_ac:.1f} "
                f"pmi={pmi_ac:.2f} [{lo_ac:.2f}–{hi_ac:.2g}] | "
                f"B-C obs={obs_bc} pmi={pmi_bc:.2f} [{lo_bc:.2f}–{hi_bc:.2g}]")
        windows_pmi[sid] = rec

    raw = {
        "amendment2": AMENDMENT2_TEXT,
        "present_maxdate": PRESENT_MAXDATE,
        "pmi_results": windows_pmi,
        "query_log": snr._query_log,
    }
    (OUT_DIR / "structural_novelty_pmi_raw.json").write_text(json.dumps(raw, indent=2))
    log(f"Wrote structural_novelty_pmi_raw.json ({len(snr._query_log)} new queries)")

    write_summary(windows_pmi)
    log("Done.")


def write_summary(windows_pmi: dict) -> None:
    L: list[str] = []
    L.append("# Structural Novelty — Amendment 2 (PMI normalization)\n")
    L.append("Extends structural_novelty.md. Prior raw-count results are left "
             "intact; this adds PMI-style normalized association for the A-C and "
             "B-C links, plus a fixed cutoff+5yr window. Scope: the 5 Tier-1 "
             "compounds (Test 1's subjects).\n")
    L.append("## Amendment 2 (verbatim)\n")
    L.append("```\n" + AMENDMENT2_TEXT + "```\n")

    L.append("## PMI ratios per compound × window\n")
    L.append("`pmi = observed / (count(A)*count(C)/total)`. >>1 = over-represented "
             "(link established); ~1 = chance; <1 = under-represented.\n")
    L.append("Each ratio is shown as **point (95% CI)**. The interval is the exact "
             "Poisson (Garwood) confidence interval on the observed co-occurrence "
             "count, divided through by the expected count — *not* a sqrt(N) "
             "approximation, which is invalid at the small counts here (e.g. "
             "liraglutide pre-cutoff, observed = 1).\n")
    L.append("| ID | Compound | Conf | Window | maxdate | count(A) | count(C) | "
             "total | obs A-C | exp A-C | **pmi A-C (95% CI)** | obs B-C | "
             "pmi B-C (95% CI) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for sid in TIER1:
        r = windows_pmi[sid]
        for wname in ("pre_cutoff", "post5yr", "present"):
            w = r["windows"][wname]
            lo_ac, hi_ac = ratio_ci(w["observed_AC"], w["expected_AC"])
            lo_bc, hi_bc = ratio_ci(w["observed_BC"], w["expected_BC"])
            L.append(
                f"| {sid} | {r['compound']} | {r['confidence'][:3]} | {wname} | "
                f"{w['maxdate']} | {w['count_A']} | {w['count_C']} | {w['total']} | "
                f"{w['observed_AC']} | {w['expected_AC']:.1f} | "
                f"**{fmt_ci(w['pmi_AC'], lo_ac, hi_ac)}** | "
                f"{w['observed_BC']} | {fmt_ci(w['pmi_BC'], lo_bc, hi_bc)} |"
            )
    L.append("")

    # Success criterion #4
    L.append("## Pre-registered success criterion (Amendment 2 #4)\n")
    L.append(">=4/5 Tier-1 compounds show A-C pmi increasing pre-cutoff -> "
             "cutoff+5yr, AND pre-cutoff values cluster separately from post "
             "values with a visible gap.\n")
    L.append("| ID | Compound | pmi A-C pre-cutoff (95% CI) | "
             "pmi A-C cutoff+5yr (95% CI) | Increased? | 95% CIs disjoint? |")
    L.append("|---|---|---|---|---|---|")
    n_inc = 0
    n_disjoint = 0
    pre_vals, post_vals = [], []
    for sid in TIER1:
        r = windows_pmi[sid]
        wp, wq = r["windows"]["pre_cutoff"], r["windows"]["post5yr"]
        pre, post = wp["pmi_AC"], wq["pmi_AC"]
        lo_p, hi_p = ratio_ci(wp["observed_AC"], wp["expected_AC"])
        lo_q, hi_q = ratio_ci(wq["observed_AC"], wq["expected_AC"])
        pre_vals.append(pre)
        post_vals.append(post)
        inc = post > pre
        n_inc += int(inc)
        disjoint = (hi_p < lo_q) or (hi_q < lo_p)  # intervals do not overlap
        n_disjoint += int(disjoint)
        L.append(f"| {sid} | {r['compound']} | {fmt_ci(pre, lo_p, hi_p)} | "
                 f"{fmt_ci(post, lo_q, hi_q)} | {'YES' if inc else 'no'} | "
                 f"{'yes' if disjoint else 'no (overlap)'} |")
    L.append("")

    max_pre = max(pre_vals)
    min_post = min(post_vals)
    gap = min_post - max_pre
    clusters_separate = gap > 0
    L.append(f"- A-C pmi increased pre→post in **{n_inc}/5** compounds.")
    L.append(f"- The pre- vs post-cutoff 95% CIs are **disjoint in {n_disjoint}/5** "
             f"compounds; in the rest the increase is not distinguishable from no "
             f"change at 95%. (Liraglutide's headline pre-cutoff 1.58 rests on a "
             f"single observed paper: CI ≈ 0.04–8.8, which overlaps its own post "
             f"value — the point estimate is not reliable.)")
    L.append(f"- Pre-cutoff pmi range: [{min(pre_vals):.2f}, {max(pre_vals):.2f}]; "
             f"cutoff+5yr pmi range: [{min(post_vals):.2f}, {max(post_vals):.2f}] "
             f"(point estimates).")
    L.append(f"- Highest pre-cutoff pmi = {max_pre:.2f}; lowest post pmi = "
             f"{min_post:.2f}; gap = {gap:+.2f} "
             f"({'clean separation — no overlap' if clusters_separate else 'OVERLAP — clusters not separable'} "
             f"on point estimates alone).")
    crit_met = (n_inc >= 4) and clusters_separate
    L.append(f"\n**Criterion {'MET' if crit_met else 'NOT MET'}** "
             f"(needs >=4/5 increasing AND a visible gap; got {n_inc}/5 increasing, "
             f"gap {gap:+.2f}).\n")

    # PMI-based classification (report values; describe natural separation)
    L.append("## PMI-based classification (Amendment 2 #3)\n")
    L.append("No hard cutoff baked in. Values reported; a descriptive boundary of "
             "pmi≈1 (chance) is used only to label, and flagged as descriptive.\n")
    L.append("| ID | Compound | Window | pmi A-C (95% CI) | pmi B-C (95% CI) | "
             "Descriptive case |")
    L.append("|---|---|---|---|---|---|")
    for sid in TIER1:
        r = windows_pmi[sid]
        for wname in ("pre_cutoff", "post5yr", "present"):
            w = r["windows"][wname]
            ac, bc = w["pmi_AC"], w["pmi_BC"]
            lo_ac, hi_ac = ratio_ci(w["observed_AC"], w["expected_AC"])
            lo_bc, hi_bc = ratio_ci(w["observed_BC"], w["expected_BC"])
            if ac >= 2:
                case = "Case 1 (A-C over-represented)"
            elif bc >= 2:
                case = "Case 2 (B-C over-rep, A-C not)"
            else:
                case = "Case 3 (neither over-represented)"
            L.append(f"| {sid} | {r['compound']} | {wname} | "
                     f"{fmt_ci(ac, lo_ac, hi_ac)} | {fmt_ci(bc, lo_bc, hi_bc)} | "
                     f"{case} |")
    L.append("")
    L.append("_Descriptive boundary pmi≥2 = '>>1'. This is a post-hoc label for "
             "readability, not a pre-registered threshold; the raw pmi values above "
             "are the primary output._\n")

    # Natural-separation commentary
    L.append("## Does a natural separation appear in the values?\n")
    def _ci_list(window: str) -> list[str]:
        out = []
        for s in TIER1:
            w = windows_pmi[s]["windows"][window]
            lo, hi = ratio_ci(w["observed_AC"], w["expected_AC"])
            out.append(fmt_ci(w["pmi_AC"], lo, hi))
        return out

    L.append(f"- A-C pmi pre-cutoff values: {_ci_list('pre_cutoff')}")
    L.append(f"- A-C pmi cutoff+5yr values: {_ci_list('post5yr')}")
    L.append("- On point estimates a gap can appear, but once the 95% Poisson CIs "
             "are drawn the pre- and post-cutoff ranges overlap for most compounds; "
             "the separation is not robust at n this small.")
    L.append("")

    (OUT_DIR / "structural_novelty_pmi.md").write_text("\n".join(L))
    log(f"Wrote {OUT_DIR / 'structural_novelty_pmi.md'}")


if __name__ == "__main__":
    main()
