# Curated Dated Corpus — Novelty Decay Experiment

Replaces the Semantic Scholar scraping approach, which stalled on rate limits for 2 hours. 
This is hand-sourced, sufficient for the pre/post embedding + judge comparison — doesn't 
need to be exhaustive, just clearly dated on either side of each compound's cutoff.

Confidence is marked per compound. Two (metformin, sildenafil) are solid — verified 
first-proposal sourcing. The other three are reasonable estimates based on available 
review-article citations; flag this to your mentor as an approximation, not treat 
as exact.

---

## Metformin — CONFIDENCE: HIGH
**Cutoff (T): ~2011-2012** — earliest mechanistic AMPK-AD proposals (Gupta, Bisht & Dey 2011; 
Li et al. 2012 on AMPK/mTOR/S6K/BACE1 pathway).

**Pre-cutoff (before 2011) — should NOT mention metformin-AD-AMPK link:**
- General AMPK/mitochondrial biology papers, or general metformin/T2D papers pre-2011 
  (search: "AMPK diabetes metformin mechanism" restricted pre-2011)
- General AD amyloid/tau pathology reviews pre-2011 with no metformin mention

**Post-cutoff (2012+) — should show established link:**
- Li et al. 2012 (AMPK/mTOR/S6K/BACE1 pathway)
- Frontiers 2021 "Deciphering the Roles of Metformin in Alzheimer's Disease: A Snapshot" 
  (fphar.2021.728315) — full mechanistic review citing decade of work
- Charpignon et al., Nat Commun 2022 (causal inference + EHR)
- NCT04098666 MAP trial protocol (2024)

## Sildenafil — CONFIDENCE: HIGH
**Cutoff (T): ~Nov/Dec 2021** — original computational identification: Fang et al., 
*Nature Aging* 2021;1(12):1175-1188 (Cheng lab, endophenotype-based network medicine screen).

**Pre-cutoff (before Nov 2021) — should NOT mention sildenafil-AD-PDE5 link:**
- General PDE5/cGMP signaling papers pre-2021 unrelated to AD
- General AD network-medicine/endophenotype methodology papers pre-2021 that don't 
  name sildenafil specifically

**Post-cutoff (2022+) — should show established link:**
- Li et al., *Alzheimers Dement* 2025 (iPSC/5xFAD validation) — DOI:10.1002/alz.089662
- Hainsworth et al. 2023, PDE5 inhibitor drugs for dementia review (cites Fang et al. 
  as "recent study")
- Cleveland Clinic real-world data follow-ups (2024-2025)

## Losartan — CONFIDENCE: MODERATE (estimate)
**Cutoff (T): ~2015-2017** — AT4 receptor / angiotensin-AD mechanistic rationale predates 
the RADAR trial (2021) by several years; losartan was already one of the "comparator 
drugs...in an active AD clinical trial" per the sildenafil paper's 2012-2017 claims data, 
implying trial planning was underway well before 2021. Recommend confirming exact first 
mechanistic paper if you want to tighten this.

**Pre-cutoff:** general AT1R/AT4R renin-angiotensin system papers pre-2015 not AD-specific
**Post-cutoff:** Kehoe et al., RADAR trial, *Lancet Neurol* 2021; PMC8528717

## Pioglitazone — CONFIDENCE: MODERATE (estimate)
**Cutoff (T): ~2005-2008** — PPAR-γ/AD rationale predates TOMMORROW trial design (~2013) 
by many years; PPAR-γ agonists were being studied for AD neuroinflammation in the mid-2000s.

**Pre-cutoff:** general PPAR-γ/glucose metabolism papers pre-2005 not AD-specific
**Post-cutoff:** Burns et al., TOMMORROW trial, *Lancet Neurol* 2021 (full mechanistic 
context, cerebral glucose/lipid metabolism, microglial Aβ phagocytosis)

## Liraglutide — CONFIDENCE: MODERATE (estimate)
**Cutoff (T): ~2010-2012** — GLP-1R neuroprotection rationale in AD predates ELAD trial 
(2015-2019 recruitment) by several years; early GLP-1 agonist neuroprotection papers 
(exenatide, liraglutide) in rodent AD models appeared around this period.

**Pre-cutoff:** general GLP-1R/incretin biology papers pre-2010 not AD-specific
**Post-cutoff:** Edison et al., ELAD trial, *Nat Med* 2025; PMC6448216 (protocol)

---

## What to do with this

For each compound, you have a rough pre/post split even without a large scraped corpus — 
2-4 representative papers on each side is enough for the embedding similarity comparison, 
and the mechanistic review articles (Frontiers, Hainsworth et al.) conveniently summarize 
years of "post" literature in one document if you want fewer, denser data points rather 
than many thin ones.

**Recommendation:** proceed with metformin and sildenafil first (high confidence, clean 
cutoffs) as your primary 2-compound test. If the decay signature shows up clearly there, 
you have your answer without needing to firm up the other three dates. Treat losartan/
pioglitazone/liraglutide as a secondary, lower-confidence extension.
