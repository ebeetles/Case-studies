# Hypothesis Sources for Rubric Validation (Part 1)

Sourced candidates for validating the **novelty** and **specificity** dimensions of the hypothesis quality rubric. Organized for two sub-experiments:

- **Sub-experiment A (controlled degradation):** start from high-quality hypotheses, degrade one dimension at a time, check the rubric detects the specific drop.
- **Sub-experiment B (tiered literature):** externally-grounded quality tiers based on how far each hypothesis advanced in the real world. Check the rubric recovers the ordering.

Every entry below is drawn from a real, citable source. Nothing is invented. Tier assignment is based on external evidence (clinical trial stage, validation history, number of supporting studies) — established *before* any rubric is applied.

---

## The tiering logic (external ground truth)

| Tier | Definition | External signal | What it tests |
|------|-----------|-----------------|---------------|
| **Tier 1** | Reached a dedicated AD clinical trial (Phase 2+) with a documented mechanism | ClinicalTrials.gov + peer-reviewed trial publication | High-quality, specific, community-validated |
| **Tier 2** | Computationally/preclinically proposed with a specific mechanism, no dedicated AD trial | Peer-reviewed computational/preclinical paper | Mechanistically specific but unvalidated clinically |
| **Tier 3** | Nominated as a candidate with little/no mechanistic hypothesis | Appears in review long-tail, often single-study, frequency-based | Weak specificity, weak grounding |

**Important framing note:** Tier 1 means "the community judged this hypothesis good enough to run a real trial," NOT "the drug worked." Several Tier 1 entries below *failed* their trials (pioglitazone, losartan). That's correct and intentional — you're validating hypothesis *quality*, not therapeutic success. A well-formed, specific, grounded hypothesis can still fail in the clinic. Keep this distinction explicit in the writeup or a reviewer will pounce.

---

## TIER 1 — Reached dedicated AD clinical trials (high quality)

### T1-A. Metformin
- **Hypothesis (your format):** Metformin may activate AMPK and modulate the mTOR pathway to reduce neuroinflammation and tau pathology relevant to Alzheimer's disease.
- **Mechanism specificity:** AMPK activation, mTOR modulation; also documented suppression of APOE and SPP1 in human neural cells.
- **Trial status:** Phase 3, NCT04098666 (disease-modifying). Also multiple EHR target-trial emulations (Charpignon et al., Nat Commun 2022).
- **Sources:** Nat Commun 2022 (DOI: 10.1038/s41467-022-35157-w); trial NCT04098666.
- **Note:** This is your pipeline's own recurrent hypothesis (metformin/NLRP3/5xFAD). Including it lets you directly connect the validation set back to your convergence finding.

### T1-B. Liraglutide
- **Hypothesis:** Liraglutide may activate the GLP-1 receptor to reduce neuroinflammation, improve neuronal insulin signaling, and slow cortical atrophy relevant to Alzheimer's disease.
- **Mechanism specificity:** GLP-1R agonism → reduced amyloid oligomers, normalized synaptic plasticity, improved cerebral glucose uptake, PKA and PI3K/Akt signaling restoration.
- **Trial status:** Phase 2b ELAD trial, 204 patients, published Nature Medicine 2025. Primary endpoint (cerebral glucose metabolism) missed, but significant secondary endpoints (≈50% less brain atrophy, 18% slower cognitive decline).
- **Sources:** Edison et al., Nat Med 2025 (DOI: 10.1038/s41591-025-04106-7); ELAD protocol PMC6448216.

### T1-C. Pioglitazone
- **Hypothesis:** Pioglitazone may activate PPAR-γ to stabilize cerebral glucose and lipid metabolism and reduce neuroinflammation relevant to delaying Alzheimer's disease onset.
- **Mechanism specificity:** PPAR-γ agonism → improved cerebral glucose/lipid metabolism, microglial Aβ phagocytosis via PPARγ/RXRα/CD36.
- **Trial status:** Phase 3 TOMMORROW trial (Burns et al., Lancet Neurol 2021). Terminated for futility — good "high-quality hypothesis, failed drug" case.
- **Sources:** Lancet Neurol 2021;20:537-547.

### T1-D. Losartan
- **Hypothesis:** Losartan may antagonize the angiotensin II type 1 receptor to reduce oxidative stress and cerebrovascular dysfunction relevant to slowing Alzheimer's disease progression.
- **Mechanism specificity:** AT1R blockade → mitigated AT1-initiated oxidative stress, normalized AT4 receptors, improved neurovascular coupling.
- **Trial status:** Phase 2 RADAR trial (Kehoe et al., Lancet Neurol 2021). Null on brain atrophy — again, quality hypothesis, negative result.
- **Sources:** Lancet Neurol 2021, PMC8528717.

### T1-E. Sildenafil  *(borderline T1/T2 — see note)*
- **Hypothesis:** Sildenafil may inhibit phosphodiesterase-5 to increase cGMP signaling and reduce tau phosphorylation and amyloid accumulation relevant to Alzheimer's disease.
- **Mechanism specificity:** PDE5 inhibition → increased cGMP, reduced pTau181, decreased Aβ; validated in patient iPSC-derived neurons and 5xFAD mice.
- **Trial status:** Identified via network medicine + real-world data (Cheng lab), mechanistically validated in iPSC/5xFAD, meta-analysis supports Phase 3 — but **no completed dedicated AD RCT yet**.
- **Sources:** Li et al., Alzheimers Dement 2025 (DOI: 10.1002/alz.089662); npj Dementia meta-analysis 2025.
- **Note:** Excellent *boundary* case. Use it to test whether the rubric gives an intermediate score to a hypothesis with strong mechanism + strong preclinical validation but no completed trial. Could be scored as high T2 or low T1.

---

## TIER 2 — Computationally/preclinically proposed, specific mechanism, no dedicated AD trial

### T2-A. Baclofen
- **Hypothesis:** Baclofen may act on GABA-B receptor signaling to produce non-redundant modulation of Alzheimer's disease network pathophysiology.
- **Mechanism specificity:** Predicted via network proximity to have non-redundant impact on AD networks (Fang et al.).
- **Status:** Computational prediction, no dedicated AD trial. Mechanism is target-level but AD-specific pathway less spelled out than Tier 1.
- **Source:** Fang et al., cited in Cummings et al., Nat Commun 2025 (DOI: 10.1038/s41467-025-56690-4).

### T2-B. Ibudilast
- **Hypothesis:** Ibudilast may inhibit phosphodiesterase and neuroinflammatory glial activation to reduce amyloid and tau pathology relevant to Alzheimer's disease.
- **Mechanism specificity:** PDE inhibitor / glial attenuator; multiscale computational prediction, back-translated to transgenic rat model with reduced spatial memory deficits, amyloid plaque, tau filament changes.
- **Status:** Computational + preclinical animal validation, no dedicated AD RCT.
- **Source:** Oliveros et al., cited in Cummings et al., Nat Commun 2025.

### T2-C. Chenodiol (chenodeoxycholic acid)
- **Hypothesis:** Chenodiol may act as a primary bile acid modulating an AD-related endophenotype network to produce disease-relevant molecular effects in Alzheimer's disease.
- **Mechanism specificity:** Network-pharmacology-predicted proximity to AD modules; experimentally followed up in phenotypic assays.
- **Status:** Network screen + cell-based phenotypic assay, no clinical AD trial.
- **Source:** Network pharmacology screen, PMC13061003.

### T2-D. Arundine (3,3'-diindolylmethane)
- **Hypothesis:** Arundine may modulate AD-associated endophenotype pathways to produce protective molecular effects relevant to Alzheimer's disease.
- **Mechanism specificity:** Identified by interactome-proximity screen; less-characterized mechanism, validated in phenotypic assays.
- **Status:** Computational + in vitro, no clinical trial.
- **Source:** PMC13061003.

### T2-E. Acamprosate
- **Hypothesis:** Acamprosate may modulate glutamatergic signaling to produce non-redundant impact on Alzheimer's disease network pathophysiology.
- **Mechanism specificity:** Glutamate-modulating; network-proximity predicted non-redundant AD impact.
- **Status:** Computational prediction, no dedicated AD trial.
- **Source:** Fang et al., cited in Cummings et al., Nat Commun 2025.

*(Backups if you want alternates: trofinetide→IGF1, plerixafor→CXCR4, cysteamine — all from systems-pharmacology screens, PMC12563243 / PMC13061003.)*

---

## TIER 3 — Nominated candidates, little/no mechanistic hypothesis (weak)

Source: Grabowska et al., Front Pharmacol 2023 (10-year review). 573 candidates; 65% (370) suggested by only a single study. Top-frequency drugs were nominated largely by repetition/association, frequently **without an AD-specific mechanistic hypothesis** — exactly the "vague" profile you want for Tier 3. Reformat each into your template *without adding mechanism that isn't in the source* (adding mechanism would artificially inflate the tier).

### T3-A. Clozapine
- **Hypothesis (deliberately mechanism-light, as sourced):** Clozapine may have effects relevant to Alzheimer's disease.
- **Why T3:** Most-suggested candidate (6 studies) but as an antipsychotic nominated largely by association/repurposing signals; no crisp AD-specific mechanism given.
- **Source:** Grabowska et al. 2023, Table 1.

### T3-B. Verapamil
- **Hypothesis:** Verapamil, a calcium channel blocker, may be beneficial in Alzheimer's disease.
- **Why T3:** 5 supporting studies; calcium-channel rationale is generic, not an AD-specific mechanistic pathway.
- **Source:** Grabowska et al. 2023.

### T3-C. Tamoxifen
- **Hypothesis:** Tamoxifen, a selective estrogen receptor modulator, may have a repurposing role in Alzheimer's disease.
- **Why T3:** 5 studies; SERM rationale generic, no specific AD mechanism advanced.
- **Source:** Grabowska et al. 2023.

### T3-D. Adenosine
- **Hypothesis:** Adenosine may have relevance to Alzheimer's disease treatment.
- **Why T3:** 5 studies; nominated without a specific, testable AD mechanism.
- **Source:** Grabowska et al. 2023.

### T3-E. Vandetanib (or sunitinib / vorinostat as alternates)
- **Hypothesis:** Vandetanib, a tyrosine kinase inhibitor, may be repurposable for Alzheimer's disease.
- **Why T3:** 5 studies; kinase-inhibitor nomination without AD-specific mechanistic hypothesis.
- **Source:** Grabowska et al. 2023.

---

## How to use this for Sub-experiment A (degradation)

Use the **Tier 1** hypotheses as your high-quality starting points (they have crisp mechanisms). For each, generate degraded variants:

- **Specificity-degraded:** strip the molecular mechanism, keep compound + disease. e.g. liraglutide GLP-1R version → "Liraglutide may affect brain processes to help Alzheimer's disease."
- **Novelty-degraded:** swap the specific mechanism for the single most over-represented high-prior AD mechanism (generic amyloid-cascade language), collapsing what made it distinct.

Because you author the degradation, the ordering (original > degraded on the targeted dimension) is known by construction. The rubric should show a **targeted** drop on the degraded dimension, not a diffuse drop across all dimensions.

## How to use this for Sub-experiment B (tiered)

Reformat all 15 (5×3) into the identical template so surface form can't leak tier. Then run rubric / holistic / pairwise judges blind and measure tier-recovery rate. Key discipline: **do not add mechanism to Tier 3** during reformatting, and **do not strip mechanism from Tier 1**. The whole validity of B rests on preserving the specificity that actually exists in each source.

## Reformatting template

> "[Compound] may [modulate/inhibit/activate] [specific target/pathway, or left generic for T3] to produce [specific measurable effect, or generic effect for T3] relevant to Alzheimer's disease."

## Confound to watch

Famous drugs (metformin, tamoxifen) may be recognized by the judge and scored on reputation, not hypothesis content. Two mitigations: (1) the degradation experiment controls for this since the compound is held constant while only the mechanism changes; (2) consider a robustness pass where compound names are masked to a placeholder ("Compound X") and only the mechanism statement is scored.

---

## Full citation list

- Charpignon et al. Causal inference + systems pharmacology for metformin in dementia. *Nat Commun* 2022. DOI:10.1038/s41467-022-35157-w
- Edison et al. Liraglutide in mild-to-moderate AD: phase 2b (ELAD). *Nat Med* 2025. DOI:10.1038/s41591-025-04106-7
- Burns et al. Pioglitazone (TOMMORROW): phase 3. *Lancet Neurol* 2021;20:537-547
- Kehoe et al. Losartan (RADAR): phase 2. *Lancet Neurol* 2021. PMC8528717
- Li et al. Sildenafil candidate for AD (iPSC + 5xFAD). *Alzheimers Dement* 2025. DOI:10.1002/alz.089662
- Cummings et al. Drug repurposing for AD and other neurodegenerative disorders. *Nat Commun* 2025. DOI:10.1038/s41467-025-56690-4
- Network pharmacology experimental validation screen (chenodiol, arundine, cysteamine). PMC13061003
- Systems pharmacology / network medicine (trofinetide, plerixafor; IGF1/SNCA/SOX9). PMC12563243
- Rodriguez et al. DRIAD: ML identifies AD repurposing candidates. *Nat Commun* 2021;12:1033
- Grabowska et al. Drug repurposing for AD 2012–2022: 10-year review. *Front Pharmacol* 2023. DOI:10.3389/fphar.2023.1257700
