# Step-2 calibration PILOT — Alzheimer's ratio as a per-drug percentile

De-risking probe (not the full Step 2). For each drug we compute its PMI ratio against ~40 **unrelated** MeSH diseases to get the drug's own null distribution of ratios, then locate the **Alzheimer's** ratio as a percentile within it. Question: does AD rank high in the drug's own distribution even when the *raw* ratio is unimpressive (≤1)?

Window: present (2026/07/20). Disease dimension is MeSH-only for both the controls and Alzheimer's (AD is just one disease in the set). 95% CI on the AD ratio is the exact Poisson interval.

## Headline

| Drug | Raw AD ratio (95% CI) | AD percentile within drug's own null | Reading |
|---|---|---|---|
| Losartan | 0.52 (0.32–0.8) | **85th** (n=40) | raw ratio **below chance**, but AD sits at the 85th percentile of Losartan's own disease distribution |
| Sildenafil | 1.23 (0.87–1.7) | **92th** (n=40) | raw ratio above chance, but AD sits at the 92th percentile of Sildenafil's own disease distribution |

## Losartan  (count_A=11386, total=40762085)

- Alzheimer's: observed=21, expected=40.04, ratio=0.52 (0.32–0.8)
- **AD percentile within Losartan's own null: 85th** (of 40 unrelated diseases)
- Null distribution of Losartan disease ratios: min 0.00, median 0.11, max 9.49

Top of Losartan's own distribution (highest ratios = most over-represented diseases for this drug):

| Rank | Disease | observed | expected | ratio |
|---|---|---|---|---|
| 1 | Gout | 41 | 4.32 | 9.49 |
| 2 | Hyperthyroidism | 13 | 13.49 | 0.96 |
| 3 | Pancreatic Neoplasms | 27 | 29.06 | 0.93 |
| 4 | Celiac Disease | 4 | 6.51 | 0.61 |
| 5 | Schistosomiasis | 4 | 7.32 | 0.55 |
| 6 | Psoriasis | 8 | 15.16 | 0.53 |
| 7 | Cystic Fibrosis | 6 | 12.05 | 0.50 |
| 8 | Osteoarthritis | 12 | 25.28 | 0.47 |
| — | **ALZHEIMER'S** | 21 | 40.04 | **0.52** |

## Sildenafil  (count_A=8792, total=40762085)

- Alzheimer's: observed=38, expected=30.92, ratio=1.23 (0.87–1.7)
- **AD percentile within Sildenafil's own null: 92th** (of 40 unrelated diseases)
- Null distribution of Sildenafil disease ratios: min 0.00, median 0.07, max 1.93

Top of Sildenafil's own distribution (highest ratios = most over-represented diseases for this drug):

| Rank | Disease | observed | expected | ratio |
|---|---|---|---|---|
| 1 | Cystic Fibrosis | 18 | 9.30 | 1.93 |
| 2 | Alopecia Areata | 2 | 1.04 | 1.93 |
| 3 | Retinitis Pigmentosa | 4 | 2.52 | 1.59 |
| 4 | Melanoma | 21 | 25.75 | 0.82 |
| 5 | Glaucoma | 9 | 14.11 | 0.64 |
| 6 | Gout | 2 | 3.34 | 0.60 |
| 7 | Schizophrenia | 10 | 26.56 | 0.38 |
| 8 | Hepatitis C | 5 | 15.98 | 0.31 |
| — | **ALZHEIMER'S** | 38 | 30.92 | **1.23** |
