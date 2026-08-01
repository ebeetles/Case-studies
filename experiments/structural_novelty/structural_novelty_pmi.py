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


def pmi(observed: int, count_a: int, count_c: int, total: int) -> tuple[float, float]:
    expected = (count_a * count_c / total) if total else float("nan")
    ratio = (observed / expected) if expected else float("nan")
    return expected, ratio


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

            exp_ac, pmi_ac = pmi(obs_ac, count_a, count_c, total)
            exp_bc, pmi_bc = pmi(obs_bc, count_b, count_c, total)

            rec["windows"][wname] = {
                "maxdate": maxd, "count_A": count_a, "count_B": count_b,
                "count_C": count_c, "total": total,
                "observed_AC": obs_ac, "expected_AC": exp_ac, "pmi_AC": pmi_ac,
                "observed_BC": obs_bc, "expected_BC": exp_bc, "pmi_BC": pmi_bc,
            }
            log(f"{sid}/{wname}: A-C obs={obs_ac} exp={exp_ac:.1f} pmi={pmi_ac:.2f} | "
                f"B-C obs={obs_bc} exp={exp_bc:.1f} pmi={pmi_bc:.2f}")
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
    L.append("| ID | Compound | Conf | Window | maxdate | count(A) | count(C) | "
             "total | obs A-C | exp A-C | **pmi A-C** | obs B-C | pmi B-C |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for sid in TIER1:
        r = windows_pmi[sid]
        for wname in ("pre_cutoff", "post5yr", "present"):
            w = r["windows"][wname]
            L.append(
                f"| {sid} | {r['compound']} | {r['confidence'][:3]} | {wname} | "
                f"{w['maxdate']} | {w['count_A']} | {w['count_C']} | {w['total']} | "
                f"{w['observed_AC']} | {w['expected_AC']:.1f} | **{w['pmi_AC']:.2f}** | "
                f"{w['observed_BC']} | {w['pmi_BC']:.2f} |"
            )
    L.append("")

    # Success criterion #4
    L.append("## Pre-registered success criterion (Amendment 2 #4)\n")
    L.append(">=4/5 Tier-1 compounds show A-C pmi increasing pre-cutoff -> "
             "cutoff+5yr, AND pre-cutoff values cluster separately from post "
             "values with a visible gap.\n")
    L.append("| ID | Compound | pmi A-C pre-cutoff | pmi A-C cutoff+5yr | Increased? |")
    L.append("|---|---|---|---|---|")
    n_inc = 0
    pre_vals, post_vals = [], []
    for sid in TIER1:
        r = windows_pmi[sid]
        pre = r["windows"]["pre_cutoff"]["pmi_AC"]
        post = r["windows"]["post5yr"]["pmi_AC"]
        pre_vals.append(pre)
        post_vals.append(post)
        inc = post > pre
        n_inc += int(inc)
        L.append(f"| {sid} | {r['compound']} | {pre:.2f} | {post:.2f} | "
                 f"{'YES' if inc else 'no'} |")
    L.append("")

    max_pre = max(pre_vals)
    min_post = min(post_vals)
    gap = min_post - max_pre
    clusters_separate = gap > 0
    L.append(f"- A-C pmi increased pre→post in **{n_inc}/5** compounds.")
    L.append(f"- Pre-cutoff pmi range: [{min(pre_vals):.2f}, {max(pre_vals):.2f}]; "
             f"cutoff+5yr pmi range: [{min(post_vals):.2f}, {max(post_vals):.2f}].")
    L.append(f"- Highest pre-cutoff pmi = {max_pre:.2f}; lowest post pmi = "
             f"{min_post:.2f}; gap = {gap:+.2f} "
             f"({'clean separation — no overlap' if clusters_separate else 'OVERLAP — clusters not separable'}).")
    crit_met = (n_inc >= 4) and clusters_separate
    L.append(f"\n**Criterion {'MET' if crit_met else 'NOT MET'}** "
             f"(needs >=4/5 increasing AND a visible gap; got {n_inc}/5 increasing, "
             f"gap {gap:+.2f}).\n")

    # PMI-based classification (report values; describe natural separation)
    L.append("## PMI-based classification (Amendment 2 #3)\n")
    L.append("No hard cutoff baked in. Values reported; a descriptive boundary of "
             "pmi≈1 (chance) is used only to label, and flagged as descriptive.\n")
    L.append("| ID | Compound | Window | pmi A-C | pmi B-C | Descriptive case |")
    L.append("|---|---|---|---|---|---|")
    for sid in TIER1:
        r = windows_pmi[sid]
        for wname in ("pre_cutoff", "post5yr", "present"):
            w = r["windows"][wname]
            ac, bc = w["pmi_AC"], w["pmi_BC"]
            if ac >= 2:
                case = "Case 1 (A-C over-represented)"
            elif bc >= 2:
                case = "Case 2 (B-C over-rep, A-C not)"
            else:
                case = "Case 3 (neither over-represented)"
            L.append(f"| {sid} | {r['compound']} | {wname} | {ac:.2f} | {bc:.2f} | {case} |")
    L.append("")
    L.append("_Descriptive boundary pmi≥2 = '>>1'. This is a post-hoc label for "
             "readability, not a pre-registered threshold; the raw pmi values above "
             "are the primary output._\n")

    # Natural-separation commentary
    L.append("## Does a natural separation appear in the values?\n")
    ac_pre = [windows_pmi[s]["windows"]["pre_cutoff"]["pmi_AC"] for s in TIER1]
    ac_post = [windows_pmi[s]["windows"]["post5yr"]["pmi_AC"] for s in TIER1]
    L.append(f"- A-C pmi pre-cutoff values: {[f'{v:.2f}' for v in ac_pre]}")
    L.append(f"- A-C pmi cutoff+5yr values: {[f'{v:.2f}' for v in ac_post]}")
    L.append("")

    (OUT_DIR / "structural_novelty_pmi.md").write_text("\n".join(L))
    log(f"Wrote {OUT_DIR / 'structural_novelty_pmi.md'}")


if __name__ == "__main__":
    main()
