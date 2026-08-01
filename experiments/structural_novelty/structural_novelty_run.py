from __future__ import annotations

import os, sys
sys.path.insert(0, os.getcwd())  # repo root (run scripts from repo root)
import _exppath  # noqa: E402  (extends sys.path to experiment folders)

"""
Structural novelty — Steps 2-4 (PubMed counting + classification).

Runs after structural_novelty.py Step 1 (decomposition, manually reviewed).
Implements the AMENDMENT recorded verbatim below (made after decomposition
review, before any PubMed counts were observed).

Swanson ABC literature-based discovery (1986); time-sliced per SKiM (bioRxiv
2020) and Zhang et al. (J Biomed Inform 2021). LLM was used only to parse
(Step 1); all novelty signal here is PubMed paper counts. No LLM scoring.

PubMed E-utilities esearch, reusing retrieval.py's endpoint/headers/throttle
conventions (3 req/sec cap -> 0.4s delay). Every query's exact URL is logged.
"""

import json
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import requests

from main import _load_dotenv, _sanitize_env

_load_dotenv()
_sanitize_env()

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
HEADERS = {"User-Agent": "CaseStudy/1.0 (Alzheimer research; academic use)"}
PUBMED_DELAY = 0.4
TOOL = "CaseStudyStructuralNovelty"

OUT_DIR = Path("results/structural_novelty")
PRESENT_MAXDATE = date(2026, 7, 20).strftime("%Y/%m/%d")  # currentDate
THRESHOLDS = [5, 20, 100]

AMENDMENT_TEXT = """\
AMENDMENT (made after decomposition review, BEFORE any PubMed counts observed):

1. Added field mechanism_specificity = molecular_target | drug_class | null.
   - null           -> Case 0 (undecomposable)
   - drug_class     -> Case 0-class (names the drug's own class; makes no claim
                       about how it acts on the disease -> fails specificity gate)
   - molecular_target -> proceed to scoring.

2. Revised classification. A-B is a sanity check, not a discriminator (in
   repurposing the drug's target is known by construction, so A-B is high for
   nearly all valid rows). Classify on B-C and A-C:
   - A-C high              -> Case 1 (already proposed)
   - A-C low, B-C high     -> Case 2 (bridgeable but unbridged)  [TARGET]
   - A-C low, B-C low      -> Case 3 (disconnected)
   Still report A-B; flag any row where A-B is unexpectedly low as a parse problem.

3. Applied: chenodiol -> Case 0-class. verapamil, tamoxifen, vandetanib ->
   Case 0-class. ibudilast ("phosphodiesterase", no isoform) and acamprosate
   ("glutamatergic signaling", pathway-level) are borderline molecular_target —
   flagged, results reported.

4. Metformin: mTOR run as a secondary mechanism alongside AMPK, both windows.

5. This amendment documented verbatim; no counts were observed before it was made.
"""

# ── Amendment overrides: mechanism_specificity per source_id ──────────────────
# molecular_target rows proceed to scoring; drug_class -> Case 0-class;
# null -> Case 0. (Derived from the reviewed Step-1 decomposition + amendment #3.)
SPECIFICITY = {
    "T1-A": "molecular_target",   # AMPK (+ mTOR secondary)
    "T1-B": "molecular_target",   # GLP-1 receptor
    "T1-C": "molecular_target",   # PPAR-gamma
    "T1-D": "molecular_target",   # angiotensin II type 1 receptor
    "T1-E": "molecular_target",   # PDE5
    "T2-A": "molecular_target",   # GABA-B receptor
    "T2-B": "molecular_target",   # phosphodiesterase (borderline)
    "T2-C": "drug_class",         # "primary bile acid ..." -> Case 0-class
    "T2-D": "null",               # Arundine -> Case 0
    "T2-E": "molecular_target",   # glutamatergic signaling (borderline)
    "T3-A": "null",               # Clozapine -> Case 0
    "T3-B": "drug_class",         # calcium channel blocker -> Case 0-class
    "T3-C": "drug_class",         # SERM -> Case 0-class
    "T3-D": "null",               # Adenosine -> Case 0
    "T3-E": "drug_class",         # tyrosine kinase inhibitor -> Case 0-class
}
BORDERLINE = {"T2-B", "T2-E"}

# ── Synonym maps (logged; auditable) ──────────────────────────────────────────
COMPOUND_SYNONYMS = {
    "Metformin":    ["Metformin", "Glucophage"],
    "Liraglutide":  ["Liraglutide", "Victoza", "Saxenda"],
    "Pioglitazone": ["Pioglitazone", "Actos"],
    "Losartan":     ["Losartan", "Cozaar"],
    "Sildenafil":   ["Sildenafil", "Viagra"],
    "Baclofen":     ["Baclofen"],
    "Ibudilast":    ["Ibudilast", "MN-166", "AV-411"],
    "Acamprosate":  ["Acamprosate", "Campral"],
    "Chenodiol":    ["Chenodiol", "Chenodeoxycholic acid"],
    "Verapamil":    ["Verapamil"],
    "Tamoxifen":    ["Tamoxifen"],
    "Vandetanib":   ["Vandetanib", "Caprelsa", "ZD6474"],
    "Clozapine":    ["Clozapine", "Clozaril"],
    "Adenosine":    ["Adenosine"],
    "Arundine":     ["Arundine", "3,3'-diindolylmethane", "diindolylmethane"],
}

# Mechanism (B) synonyms keyed by source_id. "T1-A-mtor" = metformin secondary.
MECH_SYNONYMS = {
    "T1-A":      ["AMPK", "AMP-activated protein kinase"],
    "T1-A-mtor": ["mTOR", "mechanistic target of rapamycin", "mammalian target of rapamycin"],
    "T1-B":      ["GLP-1 receptor", "GLP-1R", "glucagon-like peptide-1 receptor"],
    "T1-C":      ["PPAR gamma", "PPAR-gamma", "PPARG", "peroxisome proliferator-activated receptor gamma"],
    "T1-D":      ["angiotensin II type 1 receptor", "AT1 receptor", "AT1R"],
    "T1-E":      ["phosphodiesterase-5", "phosphodiesterase 5", "PDE5"],
    "T2-A":      ["GABA-B receptor", "GABAB receptor", "GABA(B) receptor"],
    "T2-B":      ["phosphodiesterase"],
    "T2-E":      ["glutamatergic", "glutamate signaling", "glutamate receptor"],
    # class rows — B-C reported though gated Case 0-class:
    "T2-C":      ["bile acid", "bile acids"],
    "T3-B":      ["calcium channel blocker", "calcium channel blockers"],
    "T3-C":      ["selective estrogen receptor modulator", "estrogen receptor modulator"],
    "T3-E":      ["tyrosine kinase inhibitor", "tyrosine kinase inhibitors"],
}

DISEASE_TERM = '("Alzheimer Disease"[MeSH Terms] OR Alzheimer*[Title/Abstract])'

_query_log: list[dict] = []
_last_call = 0.0


def log(msg: str) -> None:
    print(f"[structural] {msg}", flush=True)


def _throttle() -> None:
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < PUBMED_DELAY:
        time.sleep(PUBMED_DELAY - elapsed)
    _last_call = time.time()


def _or_block(terms: list[str], field: str = "Title/Abstract") -> str:
    return "(" + " OR ".join(f'"{t}"[{field}]' for t in terms) + ")"


def compound_term(compound: str) -> str:
    syns = COMPOUND_SYNONYMS[compound]
    parts = [f'"{compound}"[MeSH Terms]'] + [f'"{s}"[Title/Abstract]' for s in syns]
    return "(" + " OR ".join(parts) + ")"


def mech_term(mech_key: str) -> str:
    return _or_block(MECH_SYNONYMS[mech_key])


def esearch_count(term: str, maxdate: str, mindate: str = "1900",
                  link: str = "", context: str = "") -> int:
    _throttle()
    params = {
        "db": "pubmed", "term": term, "datetype": "pdat",
        "mindate": mindate, "maxdate": maxdate,
        "retmode": "json", "retmax": 0, "tool": TOOL,
    }
    last_err = None
    for attempt in range(4):
        try:
            r = requests.get(PUBMED_ESEARCH, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            count = int(r.json()["esearchresult"]["count"])
            _query_log.append({
                "link": link, "context": context, "term": term,
                "mindate": mindate, "maxdate": maxdate, "count": count, "url": r.url,
            })
            return count
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = 2.0 * (attempt + 1)
            log(f"  PubMed error ({link} {context}) attempt {attempt+1}/4: {e}; "
                f"retry in {wait:.0f}s")
            time.sleep(wait)
    raise RuntimeError(f"PubMed esearch failed after retries for '{term[:80]}': {last_err}")


def esearch_ids(term: str, maxdate: str, retstart: int, retmax: int) -> list[str]:
    _throttle()
    params = {
        "db": "pubmed", "term": term, "datetype": "pdat",
        "mindate": "1900", "maxdate": maxdate, "retmode": "json",
        "retstart": retstart, "retmax": retmax, "sort": "pub_date", "tool": TOOL,
    }
    r = requests.get(PUBMED_ESEARCH, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])


def efetch_titles(ids: list[str]) -> list[dict]:
    if not ids:
        return []
    _throttle()
    r = requests.get(
        PUBMED_EFETCH,
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "tool": TOOL},
        headers=HEADERS, timeout=30,
    )
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for art in root.findall(".//PubmedArticle"):
        title = (art.findtext(".//ArticleTitle") or "").strip()
        year = (art.findtext(".//PubDate/Year")
                or art.findtext(".//PubDate/MedlineDate") or "?")
        out.append({"year": year, "title": title})
    return out


def earliest_ac_titles(compound: str, n: int = 5) -> list[dict]:
    """5 earliest compound+AD (A-C) papers at present date, for weakness check #1."""
    term = f"{compound_term(compound)} AND {DISEASE_TERM}"
    count = esearch_count(term, PRESENT_MAXDATE, link="A-C-earliest",
                          context=f"{compound}-earliest-titles")
    retstart = max(0, count - n)
    ids = esearch_ids(term, PRESENT_MAXDATE, retstart=retstart, retmax=n)
    titles = efetch_titles(ids)
    titles.sort(key=lambda t: (t["year"] if t["year"].isdigit() else "9999"))
    return titles


def classify(a_c: int, b_c: int, threshold: int) -> str:
    if a_c >= threshold:
        return "Case 1"
    if b_c >= threshold:
        return "Case 2"
    return "Case 3"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    rows = json.loads((OUT_DIR / "structural_decomposition.json").read_text())
    by_id = {r["source_id"]: r for r in rows}
    for r in rows:
        r["mechanism_specificity"] = SPECIFICITY[r["source_id"]]
        r["borderline"] = r["source_id"] in BORDERLINE

    log(f"Present maxdate: {PRESENT_MAXDATE}; thresholds: {THRESHOLDS}")

    # Windows per source_id: Tier 1 gets (pre-cutoff, present); others present-only.
    from structural_novelty import TIER1_CUTOFFS

    def pre_maxdate(compound: str) -> str:
        cy = TIER1_CUTOFFS[compound]["year"]
        return f"{cy - 1}/12/31"  # strictly before the proposal year

    results: dict[str, dict] = {}

    for r in rows:
        sid = r["source_id"]
        compound = r["compound"]
        spec = r["mechanism_specificity"]
        entry: dict = {"source_id": sid, "tier": r["tier"], "compound": compound,
                       "mechanism": r["mechanism"], "mechanism_specificity": spec,
                       "borderline": r["borderline"], "windows": {}}

        # Determine which windows to run.
        windows = {"present": ("1900", PRESENT_MAXDATE)}
        if r["tier"] == 1:
            windows["pre_cutoff"] = ("1900", pre_maxdate(compound))
            entry["cutoff"] = TIER1_CUTOFFS[compound]

        # Which links are queryable: A-C always; A-B / B-C need a mechanism.
        has_mech = sid in MECH_SYNONYMS  # true for molecular_target + drug_class rows
        mech_keys = [sid]
        if sid == "T1-A":
            mech_keys.append("T1-A-mtor")

        for wname, (mind, maxd) in windows.items():
            w: dict = {"maxdate": maxd}
            ct_comp = compound_term(compound)
            # A-C
            ac_term = f"{ct_comp} AND {DISEASE_TERM}"
            w["A_C"] = esearch_count(ac_term, maxd, mind, "A-C", f"{sid}/{wname}")
            # A-B and B-C per mechanism key
            if has_mech:
                w["A_B"] = {}
                w["B_C"] = {}
                for mk in mech_keys:
                    mt = mech_term(mk)
                    w["A_B"][mk] = esearch_count(f"{ct_comp} AND {mt}", maxd, mind,
                                                 f"A-B[{mk}]", f"{sid}/{wname}")
                    w["B_C"][mk] = esearch_count(f"{mt} AND {DISEASE_TERM}", maxd, mind,
                                                 f"B-C[{mk}]", f"{sid}/{wname}")
            entry["windows"][wname] = w
            log(f"  {sid}/{wname}: A-C={w['A_C']}"
                + (f", A-B={w.get('A_B')}, B-C={w.get('B_C')}" if has_mech else ""))

        # Classification (only for molecular_target rows; gate the rest).
        entry["classification"] = {}
        for wname, w in entry["windows"].items():
            if spec == "null":
                entry["classification"][wname] = {t: "Case 0" for t in THRESHOLDS}
            elif spec == "drug_class":
                entry["classification"][wname] = {t: "Case 0-class" for t in THRESHOLDS}
            else:
                # molecular_target: primary mechanism = sid (AMPK for metformin)
                b_c = w["B_C"][sid]
                entry["classification"][wname] = {
                    t: classify(w["A_C"], b_c, t) for t in THRESHOLDS
                }
                if sid == "T1-A":
                    entry["classification_mtor"] = entry.get("classification_mtor", {})
                    entry["classification_mtor"][wname] = {
                        t: classify(w["A_C"], w["B_C"]["T1-A-mtor"], t) for t in THRESHOLDS
                    }
        results[sid] = entry

    # Weakness mitigation #1: earliest A-C titles for the 2 high-confidence compounds.
    earliest_titles = {}
    for compound in ("Metformin", "Sildenafil"):
        log(f"Fetching 5 earliest A-C titles for {compound}...")
        earliest_titles[compound] = earliest_ac_titles(compound)

    raw = {
        "amendment": AMENDMENT_TEXT,
        "present_maxdate": PRESENT_MAXDATE,
        "thresholds": THRESHOLDS,
        "results": results,
        "earliest_ac_titles": earliest_titles,
        "query_log": _query_log,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "structural_novelty_raw.json").write_text(json.dumps(raw, indent=2))
    log(f"Wrote structural_novelty_raw.json ({len(_query_log)} queries)")

    write_summary(rows, results, earliest_titles)
    log("Done.")


def write_summary(rows, results, earliest_titles) -> None:
    from structural_novelty import TIER1_CUTOFFS
    L: list[str] = []
    L.append("# Structural Novelty — Literature-Based Discovery (Swanson ABC)\n")
    L.append("Replaces the LLM-judged novelty dimension (non-functional across four "
             "prior experiments — see novelty_validation_full_summary.md) with a "
             "PubMed paper-counting decomposition. Method: Swanson's ABC model of "
             "literature-based discovery (1986), time-sliced as in SKiM (bioRxiv "
             "2020) and Zhang et al. (J Biomed Inform 2021). An LLM was used only "
             "to parse hypotheses (Step 1); all novelty signal here is paper counts.\n")

    L.append("## Amendment (verbatim)\n")
    L.append("```\n" + AMENDMENT_TEXT + "```\n")

    # Decomposition table
    L.append("## Decomposition (with mechanism_specificity)\n")
    L.append("| ID | Tier | Compound | Mechanism (B) | Specificity | Gate case |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        spec = SPECIFICITY[r["source_id"]]
        gate = {"null": "Case 0", "drug_class": "Case 0-class",
                "molecular_target": "(scored)"}[spec]
        bl = " *(borderline)*" if r["source_id"] in BORDERLINE else ""
        mech = r["mechanism"] if r["mechanism"] else "— (null)"
        L.append(f"| {r['source_id']} | {r['tier']} | {r['compound']} | {mech}{bl} | "
                 f"{spec} | {gate} |")
    L.append("")

    # Raw counts table
    L.append("## Raw counts: hypothesis × link × date window\n")
    L.append("A-B = compound+mechanism (sanity check). B-C = mechanism+AD. "
             "A-C = compound+AD. Present maxdate = "
             f"{PRESENT_MAXDATE}. Tier-1 pre-cutoff maxdate = (cutoff year − 1)/12/31.\n")
    L.append("| ID | Compound | Mechanism | Window | maxdate | A-B | B-C | A-C |")
    L.append("|---|---|---|---|---|---|---|---|")
    for sid, e in results.items():
        for wname, w in e["windows"].items():
            ab = w.get("A_B", {}).get(sid, "—")
            bc = w.get("B_C", {}).get(sid, "—")
            L.append(f"| {sid} | {e['compound']} | {e['mechanism'] or '—'} | {wname} | "
                     f"{w['maxdate']} | {ab} | {bc} | {w['A_C']} |")
            if sid == "T1-A" and "A_B" in w:  # metformin mTOR secondary
                L.append(f"| {sid} | {e['compound']} | mTOR (secondary) | {wname} | "
                         f"{w['maxdate']} | {w['A_B']['T1-A-mtor']} | "
                         f"{w['B_C']['T1-A-mtor']} | {w['A_C']} |")
    L.append("")

    # Classification under each threshold
    L.append("## Classification under each threshold\n")
    L.append("Molecular-target rows classified on A-C / B-C. Gated rows "
             "(null → Case 0, drug_class → Case 0-class) shown as gated.\n")
    L.append("| ID | Compound | Window | ≥5 | ≥20 | ≥100 | Stable? |")
    L.append("|---|---|---|---|---|---|---|")
    for sid, e in results.items():
        for wname in e["windows"]:
            cls = e["classification"][wname]
            vals = [cls[t] for t in THRESHOLDS]
            stable = "yes" if len(set(vals)) == 1 else "no"
            L.append(f"| {sid} | {e['compound']} | {wname} | {vals[0]} | {vals[1]} | "
                     f"{vals[2]} | {stable} |")
    L.append("")

    # Test 1
    L.append("## Test 1 (PRIMARY) — Case 2 → Case 1 flip for Tier 1\n")
    L.append("Expected if the method works: **Case 2** (A-C low, B-C high) at the "
             "pre-cutoff date → **Case 1** (A-C high) at present. This is the flip "
             "the LLM judge failed to produce.\n")

    def flip_block(compounds, label):
        L.append(f"### {label}\n")
        L.append("| ID | Compound | Cutoff | Pre-cutoff class (≥5/≥20/≥100) | "
                 "Present class (≥5/≥20/≥100) | Flip on ≥2/3 thresholds? |")
        L.append("|---|---|---|---|---|---|")
        n_flip = 0
        for sid in compounds:
            e = results[sid]
            pre = e["classification"]["pre_cutoff"]
            pres = e["classification"]["present"]
            flips = sum(1 for t in THRESHOLDS
                        if pre[t] == "Case 2" and pres[t] == "Case 1")
            flipped = flips >= 2
            n_flip += int(flipped)
            cy = TIER1_CUTOFFS[e["compound"]]["year"]
            L.append(f"| {sid} | {e['compound']} | {cy} | "
                     f"{'/'.join(pre[t] for t in THRESHOLDS)} | "
                     f"{'/'.join(pres[t] for t in THRESHOLDS)} | "
                     f"{'YES' if flipped else 'no'} ({flips}/3) |")
        L.append("")
        return n_flip

    high = [s for s in ("T1-A", "T1-B", "T1-C", "T1-D", "T1-E")
            if TIER1_CUTOFFS[results[s]["compound"]]["confidence"] == "high"]
    mod = [s for s in ("T1-A", "T1-B", "T1-C", "T1-D", "T1-E")
           if TIER1_CUTOFFS[results[s]["compound"]]["confidence"] == "moderate"]
    n_flip_high = flip_block(high, "HIGH confidence (metformin, sildenafil)")
    n_flip_mod = flip_block(mod, "MODERATE confidence — cutoffs are estimates "
                            "(losartan, pioglitazone, liraglutide)")
    n_flip_all = n_flip_high + n_flip_mod

    # metformin mTOR note
    mt = results["T1-A"].get("classification_mtor", {})
    if mt:
        L.append("Metformin secondary mechanism (mTOR) classification — pre-cutoff "
                 f"{'/'.join(mt['pre_cutoff'][t] for t in THRESHOLDS)}, present "
                 f"{'/'.join(mt['present'][t] for t in THRESHOLDS)}.\n")

    # Test 2
    L.append("## Test 2 (discrimination) — Tier 3 at present\n")
    L.append("Expected: Case 0 / Case 0-class / Case 3 — NOT Case 2. These are the "
             "hypotheses the LLM judge wrongly scored as highly novel.\n")
    L.append("| ID | Compound | Specificity | Present class (≥5/≥20/≥100) |")
    L.append("|---|---|---|---|")
    n_t3_ok = 0
    for sid in ("T3-A", "T3-B", "T3-C", "T3-D", "T3-E"):
        e = results[sid]
        pres = e["classification"]["present"]
        vals = [pres[t] for t in THRESHOLDS]
        not_case2 = all(v != "Case 2" for v in vals)
        n_t3_ok += int(not_case2)
        L.append(f"| {sid} | {e['compound']} | {e['mechanism_specificity']} | "
                 f"{'/'.join(vals)} |")
    L.append("")

    # Test 3
    L.append("## Test 3 (exploratory) — Tier 2 at present\n")
    L.append("No firm prediction; reported as-is.\n")
    L.append("| ID | Compound | Specificity | Present class (≥5/≥20/≥100) | Borderline? |")
    L.append("|---|---|---|---|---|")
    for sid in ("T2-A", "T2-B", "T2-C", "T2-D", "T2-E"):
        e = results[sid]
        pres = e["classification"]["present"]
        vals = [pres[t] for t in THRESHOLDS]
        L.append(f"| {sid} | {e['compound']} | {e['mechanism_specificity']} | "
                 f"{'/'.join(vals)} | {'yes' if e['borderline'] else ''} |")
    L.append("")

    # Success criteria
    L.append("## Pre-registered success criteria\n")
    prim_met = n_flip_high >= 0 and (n_flip_all >= 4)
    L.append(f"**Primary** (≥4/5 Tier-1 show Case 2→Case 1 flip, stable across ≥2/3 "
             f"thresholds): flips observed = {n_flip_all}/5 "
             f"(high-confidence {n_flip_high}/2, moderate {n_flip_mod}/3). "
             f"**{'MET' if n_flip_all >= 4 else 'NOT MET'}.**\n")
    L.append(f"**Secondary** (≥4/5 Tier-3 classify as NOT Case 2): "
             f"{n_t3_ok}/5 are not Case 2. **{'MET' if n_t3_ok >= 4 else 'NOT MET'}.**\n")

    # Weakness mitigation #1
    L.append("## Weakness check #1 — earliest A-C titles (co-occurrence ≠ assertion)\n")
    L.append("Do the earliest compound+AD papers actually propose the repurposing "
             "link, or are they e.g. diabetic-comorbidity epidemiology? Eyeball the "
             "5 earliest for the 2 high-confidence compounds.\n")
    for compound, titles in earliest_titles.items():
        L.append(f"**{compound}** (5 earliest of A-C at present):")
        for t in titles:
            L.append(f"- {t['year']}: {t['title']}")
        L.append("")

    # Known weaknesses
    L.append("## Known weaknesses (reported, not hidden)\n")
    L.append("- **Co-occurrence ≠ assertion**: an A-C paper counts a co-mention, not "
             "necessarily a repurposing proposal (see earliest-title check above).\n"
             "- **Synonym coverage**: undercount risk if a synonym is missing; every "
             "query URL is logged in structural_novelty_raw.json for auditing.\n"
             "- **n=5 per tier**: raw numbers only; no p-values / correlations.\n"
             "- **Moderate-confidence cutoffs** (losartan 2015, pioglitazone 2005, "
             "liraglutide 2010) are estimates — reported separately from the two "
             "high-confidence compounds above.\n"
             "- **Drug-class A-B is high by construction** for gated Case 0-class "
             "rows (the class IS the drug's pharmacology); this is why they are gated "
             "out rather than scored.\n")

    L.append("## Full query log\n")
    L.append(f"{len(_query_log)} queries. Full URLs in "
             "`results/structural_novelty/structural_novelty_raw.json` (`query_log`). "
             "Sample (first 8):\n")
    L.append("| Link | Context | maxdate | Count | Term |")
    L.append("|---|---|---|---|---|")
    for q in _query_log[:8]:
        term = q["term"].replace("|", "\\|")
        L.append(f"| {q['link']} | {q['context']} | {q['maxdate']} | {q['count']} | "
                 f"`{term[:70]}…` |")
    L.append("")

    (OUT_DIR / "structural_novelty.md").write_text("\n".join(L))
    log(f"Wrote {OUT_DIR / 'structural_novelty.md'}")


if __name__ == "__main__":
    main()
