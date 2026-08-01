# Rubric Validation — Results

Judge model: `gpt-5.4-mini` (OpenAI). Degradation-generator model: `llama-3.3-70b-versatile` (Groq).

No p-values / confidence intervals reported — n is too small (15-25 hypotheses) for that to be meaningful. Raw rates and deltas only.

## 3a. Tier recovery rate

Fraction of cross-tier hypothesis pairs (T1 vs T2, T1 vs T3, T2 vs T3; 25 pairs each = 75 total) correctly ordered higher-tier > lower-tier.

| Condition | Dimension | Correct / Total | Rate |
|---|---|---|---|
| Rubric | novelty | 26/75 | 0.35 |
| Rubric | specificity | 65/75 | 0.87 |
| Holistic | (single score) | 54/75 | 0.72 |
| Pairwise | novelty | 64/150 | 0.43 |
| Pairwise | specificity | 133/150 | 0.89 |

Pairwise instability (winner flipped when A/B order was swapped):

| Dimension | Unstable pairs / Total pairs |
|---|---|
| novelty | 10/75 |
| specificity | 5/75 |

## 3b. Dimension localization (degraded variants)

Score delta = original rubric score minus degraded variant's rubric score, mean over the 5 Tier-1 compounds. A correctly-behaving rubric shows a large drop on the TARGETED dimension and a small drop on the other.

| Degradation type | n | Δ novelty | Δ specificity |
|---|---|---|---|
| specificity-degraded | 5 | 0.10 | 2.40 |
| novelty-degraded | 5 | 0.60 | 0.60 |

## 3c. Stability across repeated runs

Each hypothesis scored 2 times independently (same prompt, same model, no context of prior runs) for rubric and holistic conditions.

| Condition | Mean range (max-min) | Mean variance | Hyps w/ any disagreement |
|---|---|---|---|
| Rubric — novelty | 0.40 | 0.10 | 10/25 |
| Rubric — specificity | 0.20 | 0.05 | 5/25 |
| Holistic | 0.20 | 0.05 | 5/25 |

## Raw per-hypothesis scores (anonymized IDs)

| ID | True tier / degradation | Compound | Rubric novelty (mean) | Rubric specificity (mean) | Holistic (mean) | Text |
|---|---|---|---|---|---|---|
| H001 | novelty-degraded of T1-A | Metformin | 2.0 | 4.0 | 4.0 | Metformin may reduce amyloid-beta accumulation and plaque formation relevant to Alzheimer's disease. |
| H002 | Tier 3 | Tamoxifen | 2.5 | 4.0 | 3.0 | Tamoxifen, a selective estrogen receptor modulator, may have a repurposing role in Alzheimer's disease. |
| H003 | Tier 2 | Acamprosate | 3.5 | 4.0 | 3.0 | Acamprosate may modulate glutamatergic signaling to produce non-redundant impact on Alzheimer's disease network pathophysiology. |
| H004 | specificity-degraded of T1-C | Pioglitazone | 2.0 | 2.0 | 2.5 | Pioglitazone may affect brain processes relevant to Alzheimer's disease. |
| H005 | novelty-degraded of T1-B | Liraglutide | 2.0 | 4.0 | 3.5 | Liraglutide may reduce amyloid-beta accumulation and plaque formation relevant to Alzheimer's disease. |
| H006 | Tier 2 | Ibudilast | 2.5 | 4.0 | 3.5 | Ibudilast may inhibit phosphodiesterase and neuroinflammatory glial activation to reduce amyloid and tau pathology relevant to Alzheimer's disease. |
| H007 | Tier 2 | Baclofen | 3.5 | 4.0 | 2.5 | Baclofen may act on GABA-B receptor signaling to produce non-redundant modulation of Alzheimer's disease network pathophysiology. |
| H008 | Tier 3 | Clozapine | 2.5 | 2.0 | 2.0 | Clozapine may have effects relevant to Alzheimer's disease. |
| H009 | specificity-degraded of T1-A | Metformin | 2.0 | 2.5 | 3.0 | Metformin may affect brain processes relevant to Alzheimer's disease. |
| H010 | specificity-degraded of T1-D | Losartan | 3.0 | 2.5 | 2.0 | Losartan may affect processes relevant to Alzheimer's disease. |
| H011 | Tier 3 | Verapamil | 2.5 | 2.0 | 3.0 | Verapamil, a calcium channel blocker, may be beneficial in Alzheimer's disease. |
| H012 | specificity-degraded of T1-B | Liraglutide | 2.0 | 2.0 | 3.5 | Liraglutide may affect brain processes relevant to Alzheimer's disease. |
| H013 | Tier 1 | Liraglutide | 3.0 | 5.0 | 4.0 | Liraglutide may activate the GLP-1 receptor to reduce neuroinflammation, improve neuronal insulin signaling, and slow cortical atrophy relevant to Alzheimer's disease. |
| H014 | Tier 3 | Vandetanib | 2.5 | 4.0 | 2.0 | Vandetanib, a tyrosine kinase inhibitor, may be repurposable for Alzheimer's disease. |
| H015 | novelty-degraded of T1-D | Losartan | 2.0 | 4.0 | 3.0 | Losartan may reduce amyloid-beta accumulation and plaque formation, relevant to slowing Alzheimer's disease progression. |
| H016 | Tier 3 | Adenosine | 3.5 | 2.0 | 2.0 | Adenosine may have relevance to Alzheimer's disease treatment. |
| H017 | Tier 1 | Pioglitazone | 2.5 | 5.0 | 3.0 | Pioglitazone may activate PPAR-γ to stabilize cerebral glucose and lipid metabolism and reduce neuroinflammation relevant to delaying Alzheimer's disease onset. |
| H018 | specificity-degraded of T1-E | Sildenafil | 3.0 | 3.5 | 3.0 | Sildenafil may affect brain processes relevant to Alzheimer's disease. |
| H019 | Tier 1 | Sildenafil | 2.0 | 5.0 | 3.0 | Sildenafil may inhibit phosphodiesterase-5 to increase cGMP signaling and reduce tau phosphorylation and amyloid accumulation relevant to Alzheimer's disease. |
| H020 | novelty-degraded of T1-E | Sildenafil | 2.0 | 4.5 | 3.0 | Sildenafil may reduce amyloid-beta accumulation and plaque formation, relevant to Alzheimer's disease. |
| H021 | Tier 2 | Chenodiol | 4.0 | 4.0 | 3.0 | Chenodiol may act as a primary bile acid modulating an AD-related endophenotype network to produce disease-relevant molecular effects in Alzheimer's disease. |
| H022 | Tier 2 | Arundine | 2.0 | 3.0 | 2.0 | Arundine may modulate AD-associated endophenotype pathways to produce protective molecular effects relevant to Alzheimer's disease. |
| H023 | Tier 1 | Metformin | 2.0 | 4.5 | 4.0 | Metformin may activate AMPK and modulate the mTOR pathway to reduce neuroinflammation and tau pathology relevant to Alzheimer's disease. |
| H024 | Tier 1 | Losartan | 3.0 | 5.0 | 4.0 | Losartan may antagonize the angiotensin II type 1 receptor to reduce oxidative stress and cerebrovascular dysfunction relevant to slowing Alzheimer's disease progression. |
| H025 | novelty-degraded of T1-C | Pioglitazone | 1.5 | 5.0 | 3.0 | Pioglitazone may reduce amyloid-beta accumulation and plaque formation, relevant to delaying Alzheimer's disease onset. |
