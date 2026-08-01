# Structural Novelty — Literature-Based Discovery (Swanson ABC)

Replaces the LLM-judged novelty dimension (non-functional across four prior experiments — see novelty_validation_full_summary.md) with a PubMed paper-counting decomposition. Method: Swanson's ABC model of literature-based discovery (1986), time-sliced as in SKiM (bioRxiv 2020) and Zhang et al. (J Biomed Inform 2021). An LLM was used only to parse hypotheses (Step 1); all novelty signal here is paper counts.

## Amendment (verbatim)

```
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
```

## Decomposition (with mechanism_specificity)

| ID | Tier | Compound | Mechanism (B) | Specificity | Gate case |
|---|---|---|---|---|---|
| T1-A | 1 | Metformin | AMPK | molecular_target | (scored) |
| T1-B | 1 | Liraglutide | GLP-1 receptor | molecular_target | (scored) |
| T1-C | 1 | Pioglitazone | PPAR-γ | molecular_target | (scored) |
| T1-D | 1 | Losartan | angiotensin II type 1 receptor | molecular_target | (scored) |
| T1-E | 1 | Sildenafil | phosphodiesterase-5 | molecular_target | (scored) |
| T2-A | 2 | Baclofen | GABA-B receptor signaling | molecular_target | (scored) |
| T2-B | 2 | Ibudilast | phosphodiesterase *(borderline)* | molecular_target | (scored) |
| T2-C | 2 | Chenodiol | primary bile acid modulating an AD-related endophenotype network | drug_class | Case 0-class |
| T2-D | 2 | Arundine | — (null) | null | Case 0 |
| T2-E | 2 | Acamprosate | glutamatergic signaling *(borderline)* | molecular_target | (scored) |
| T3-A | 3 | Clozapine | — (null) | null | Case 0 |
| T3-B | 3 | Verapamil | a calcium channel blocker | drug_class | Case 0-class |
| T3-C | 3 | Tamoxifen | a selective estrogen receptor modulator | drug_class | Case 0-class |
| T3-D | 3 | Adenosine | — (null) | null | Case 0 |
| T3-E | 3 | Vandetanib | tyrosine kinase inhibitor | drug_class | Case 0-class |

## Raw counts: hypothesis × link × date window

A-B = compound+mechanism (sanity check). B-C = mechanism+AD. A-C = compound+AD. Present maxdate = 2026/07/20. Tier-1 pre-cutoff maxdate = (cutoff year − 1)/12/31.

| ID | Compound | Mechanism | Window | maxdate | A-B | B-C | A-C |
|---|---|---|---|---|---|---|---|
| T1-A | Metformin | AMPK | present | 2026/07/20 | 3492 | 755 | 425 |
| T1-A | Metformin | mTOR (secondary) | present | 2026/07/20 | 1339 | 1271 | 425 |
| T1-A | Metformin | AMPK | pre_cutoff | 2010/12/31 | 310 | 19 | 8 |
| T1-A | Metformin | mTOR (secondary) | pre_cutoff | 2010/12/31 | 47 | 49 | 8 |
| T1-B | Liraglutide | GLP-1 receptor | present | 2026/07/20 | 2803 | 348 | 154 |
| T1-B | Liraglutide | GLP-1 receptor | pre_cutoff | 2009/12/31 | 48 | 10 | 1 |
| T1-C | Pioglitazone | PPAR-γ | present | 2026/07/20 | 1942 | 554 | 175 |
| T1-C | Pioglitazone | PPAR-γ | pre_cutoff | 2004/12/31 | 233 | 31 | 8 |
| T1-D | Losartan | angiotensin II type 1 receptor | present | 2026/07/20 | 3002 | 88 | 46 |
| T1-D | Losartan | angiotensin II type 1 receptor | pre_cutoff | 2014/12/31 | 2331 | 26 | 14 |
| T1-E | Sildenafil | phosphodiesterase-5 | present | 2026/07/20 | 2366 | 131 | 70 |
| T1-E | Sildenafil | phosphodiesterase-5 | pre_cutoff | 2020/12/31 | 1934 | 73 | 38 |
| T2-A | Baclofen | GABA-B receptor signaling | present | 2026/07/20 | 2251 | 37 | 34 |
| T2-B | Ibudilast | phosphodiesterase | present | 2026/07/20 | 89 | 454 | 10 |
| T2-C | Chenodiol | primary bile acid modulating an AD-related endophenotype network | present | 2026/07/20 | 2491 | 240 | 11 |
| T2-D | Arundine | — | present | 2026/07/20 | — | — | 4 |
| T2-E | Acamprosate | glutamatergic signaling | present | 2026/07/20 | 95 | 1988 | 9 |
| T3-A | Clozapine | — | present | 2026/07/20 | — | — | 118 |
| T3-B | Verapamil | a calcium channel blocker | present | 2026/07/20 | 3031 | 175 | 71 |
| T3-C | Tamoxifen | a selective estrogen receptor modulator | present | 2026/07/20 | 1168 | 27 | 122 |
| T3-D | Adenosine | — | present | 2026/07/20 | — | — | 1287 |
| T3-E | Vandetanib | tyrosine kinase inhibitor | present | 2026/07/20 | 440 | 103 | 1 |

## Classification under each threshold

Molecular-target rows classified on A-C / B-C. Gated rows (null → Case 0, drug_class → Case 0-class) shown as gated.

| ID | Compound | Window | ≥5 | ≥20 | ≥100 | Stable? |
|---|---|---|---|---|---|---|
| T1-A | Metformin | present | Case 1 | Case 1 | Case 1 | yes |
| T1-A | Metformin | pre_cutoff | Case 1 | Case 3 | Case 3 | no |
| T1-B | Liraglutide | present | Case 1 | Case 1 | Case 1 | yes |
| T1-B | Liraglutide | pre_cutoff | Case 2 | Case 3 | Case 3 | no |
| T1-C | Pioglitazone | present | Case 1 | Case 1 | Case 1 | yes |
| T1-C | Pioglitazone | pre_cutoff | Case 1 | Case 2 | Case 3 | no |
| T1-D | Losartan | present | Case 1 | Case 1 | Case 3 | no |
| T1-D | Losartan | pre_cutoff | Case 1 | Case 2 | Case 3 | no |
| T1-E | Sildenafil | present | Case 1 | Case 1 | Case 2 | no |
| T1-E | Sildenafil | pre_cutoff | Case 1 | Case 1 | Case 3 | no |
| T2-A | Baclofen | present | Case 1 | Case 1 | Case 3 | no |
| T2-B | Ibudilast | present | Case 1 | Case 2 | Case 2 | no |
| T2-C | Chenodiol | present | Case 0-class | Case 0-class | Case 0-class | yes |
| T2-D | Arundine | present | Case 0 | Case 0 | Case 0 | yes |
| T2-E | Acamprosate | present | Case 1 | Case 2 | Case 2 | no |
| T3-A | Clozapine | present | Case 0 | Case 0 | Case 0 | yes |
| T3-B | Verapamil | present | Case 0-class | Case 0-class | Case 0-class | yes |
| T3-C | Tamoxifen | present | Case 0-class | Case 0-class | Case 0-class | yes |
| T3-D | Adenosine | present | Case 0 | Case 0 | Case 0 | yes |
| T3-E | Vandetanib | present | Case 0-class | Case 0-class | Case 0-class | yes |

## Test 1 (PRIMARY) — Case 2 → Case 1 flip for Tier 1

Expected if the method works: **Case 2** (A-C low, B-C high) at the pre-cutoff date → **Case 1** (A-C high) at present. This is the flip the LLM judge failed to produce.

### HIGH confidence (metformin, sildenafil)

| ID | Compound | Cutoff | Pre-cutoff class (≥5/≥20/≥100) | Present class (≥5/≥20/≥100) | Flip on ≥2/3 thresholds? |
|---|---|---|---|---|---|
| T1-A | Metformin | 2011 | Case 1/Case 3/Case 3 | Case 1/Case 1/Case 1 | no (0/3) |
| T1-E | Sildenafil | 2021 | Case 1/Case 1/Case 3 | Case 1/Case 1/Case 2 | no (0/3) |

### MODERATE confidence — cutoffs are estimates (losartan, pioglitazone, liraglutide)

| ID | Compound | Cutoff | Pre-cutoff class (≥5/≥20/≥100) | Present class (≥5/≥20/≥100) | Flip on ≥2/3 thresholds? |
|---|---|---|---|---|---|
| T1-B | Liraglutide | 2010 | Case 2/Case 3/Case 3 | Case 1/Case 1/Case 1 | no (1/3) |
| T1-C | Pioglitazone | 2005 | Case 1/Case 2/Case 3 | Case 1/Case 1/Case 1 | no (1/3) |
| T1-D | Losartan | 2015 | Case 1/Case 2/Case 3 | Case 1/Case 1/Case 3 | no (1/3) |

Metformin secondary mechanism (mTOR) classification — pre-cutoff Case 1/Case 2/Case 3, present Case 1/Case 1/Case 1.

## Test 2 (discrimination) — Tier 3 at present

Expected: Case 0 / Case 0-class / Case 3 — NOT Case 2. These are the hypotheses the LLM judge wrongly scored as highly novel.

| ID | Compound | Specificity | Present class (≥5/≥20/≥100) |
|---|---|---|---|
| T3-A | Clozapine | null | Case 0/Case 0/Case 0 |
| T3-B | Verapamil | drug_class | Case 0-class/Case 0-class/Case 0-class |
| T3-C | Tamoxifen | drug_class | Case 0-class/Case 0-class/Case 0-class |
| T3-D | Adenosine | null | Case 0/Case 0/Case 0 |
| T3-E | Vandetanib | drug_class | Case 0-class/Case 0-class/Case 0-class |

## Test 3 (exploratory) — Tier 2 at present

No firm prediction; reported as-is.

| ID | Compound | Specificity | Present class (≥5/≥20/≥100) | Borderline? |
|---|---|---|---|---|
| T2-A | Baclofen | molecular_target | Case 1/Case 1/Case 3 |  |
| T2-B | Ibudilast | molecular_target | Case 1/Case 2/Case 2 | yes |
| T2-C | Chenodiol | drug_class | Case 0-class/Case 0-class/Case 0-class |  |
| T2-D | Arundine | null | Case 0/Case 0/Case 0 |  |
| T2-E | Acamprosate | molecular_target | Case 1/Case 2/Case 2 | yes |

## Pre-registered success criteria

**Primary** (≥4/5 Tier-1 show Case 2→Case 1 flip, stable across ≥2/3 thresholds): flips observed = 0/5 (high-confidence 0/2, moderate 0/3). **NOT MET.**

**Secondary** (≥4/5 Tier-3 classify as NOT Case 2): 5/5 are not Case 2. **MET.**

## Weakness check #1 — earliest A-C titles (co-occurrence ≠ assertion)

Do the earliest compound+AD papers actually propose the repurposing link, or are they e.g. diabetic-comorbidity epidemiology? Eyeball the 5 earliest for the 2 high-confidence compounds.

**Metformin** (5 earliest of A-C at present):
- 2005: Investigation of the pharmacokinetic and pharmacodynamic interactions between memantine and glyburide/metformin in healthy young subjects: a single-center, multiple-dose, open-label study.
- 2006: Inhibitors of the Maillard reaction and AGE breakers as therapeutics for multiple diseases.
- 2007: Methylglyoxal and advanced glycation endproducts: new therapeutic horizons?
- 2008: Memantine-induced myoclonus and delirium exacerbated by trimethoprim.
- 2009: Antidiabetic drug metformin (GlucophageR) increases biogenesis of Alzheimer's amyloid peptides via up-regulating BACE1 transcription.

**Sildenafil** (5 earliest of A-C at present):
- 2004: Phosphodiesterase inhibition by sildenafil citrate attenuates the learning impairment induced by blockade of cholinergic muscarinic receptors in rats.
- 2007: Versatile effects of sildenafil: recent pharmacological applications.
- 2008: Role of phosphodiesterase 5 in synaptic plasticity and memory.
- 2008: Prostacyclin among prostanoids.
- 2009: PDE5 inhibitors in non-urological conditions.

## Known weaknesses (reported, not hidden)

- **Co-occurrence ≠ assertion**: an A-C paper counts a co-mention, not necessarily a repurposing proposal (see earliest-title check above).
- **Synonym coverage**: undercount risk if a synonym is missing; every query URL is logged in structural_novelty_raw.json for auditing.
- **n=5 per tier**: raw numbers only; no p-values / correlations.
- **Moderate-confidence cutoffs** (losartan 2015, pioglitazone 2005, liraglutide 2010) are estimates — reported separately from the two high-confidence compounds above.
- **Drug-class A-B is high by construction** for gated Case 0-class rows (the class IS the drug's pharmacology); this is why they are gated out rather than scored.

## Full query log

60 queries. Full URLs in `results/validation/structural_novelty_raw.json` (`query_log`). Sample (first 8):

| Link | Context | maxdate | Count | Term |
|---|---|---|---|---|
| A-C | T1-A/present | 2026/07/20 | 425 | `("Metformin"[MeSH Terms] OR "Metformin"[Title/Abstract] OR "Glucophage…` |
| A-B[T1-A] | T1-A/present | 2026/07/20 | 3492 | `("Metformin"[MeSH Terms] OR "Metformin"[Title/Abstract] OR "Glucophage…` |
| B-C[T1-A] | T1-A/present | 2026/07/20 | 755 | `("AMPK"[Title/Abstract] OR "AMP-activated protein kinase"[Title/Abstra…` |
| A-B[T1-A-mtor] | T1-A/present | 2026/07/20 | 1339 | `("Metformin"[MeSH Terms] OR "Metformin"[Title/Abstract] OR "Glucophage…` |
| B-C[T1-A-mtor] | T1-A/present | 2026/07/20 | 1271 | `("mTOR"[Title/Abstract] OR "mechanistic target of rapamycin"[Title/Abs…` |
| A-C | T1-A/pre_cutoff | 2010/12/31 | 8 | `("Metformin"[MeSH Terms] OR "Metformin"[Title/Abstract] OR "Glucophage…` |
| A-B[T1-A] | T1-A/pre_cutoff | 2010/12/31 | 310 | `("Metformin"[MeSH Terms] OR "Metformin"[Title/Abstract] OR "Glucophage…` |
| B-C[T1-A] | T1-A/pre_cutoff | 2010/12/31 | 19 | `("AMPK"[Title/Abstract] OR "AMP-activated protein kinase"[Title/Abstra…` |
