# Step 2 — Alzheimer's PMI ratio as a per-drug percentile

For each drug, its Alzheimer's ratio is placed within the distribution of ratios that drug produces against ~100 **unrelated** MeSH diseases (its own null). Percentiles are cross-drug-comparable; raw ratios are not. The disease dimension is MeSH-only for the controls and for Alzheimer's alike.

Window: present (2026/07/20). Bootstrap 95% CI on the percentile (B=2000) resamples the control diseases with replacement and redraws every count from its Poisson. Controls with ratio ≥ 3 are flagged as likely real indications and a trimmed percentile is reported as a sensitivity check.

## Headline — raw ratio vs. calibrated percentile

| Drug | Raw AD ratio (95% CI) | AD percentile (95% CI) | Trimmed | n | Reading |
|---|---|---|---|---|---|
| Metformin | 1.35 (1.15–1.6) | **95th** (89–99) | 98th | 102 | raw above chance; AD in the top 5% of Metformin's own diseases |
| Liraglutide | 3.82 (3.02–4.8) | **97th** (93–100) | 100th | 102 | raw above chance; AD in the top 3% of Liraglutide's own diseases |
| Pioglitazone | 3.41 (2.74–4.2) | **98th** (92–100) | 100th | 102 | raw above chance; AD in the top 2% of Pioglitazone's own diseases |
| Losartan | 0.52 (0.32–0.8) | **85th** (74–95) | 87th | 102 | raw below chance; AD in the top 15% of Losartan's own diseases |
| Sildenafil | 1.23 (0.87–1.7) | **91th** (83–97) | 93th | 102 | raw above chance; AD in the top 9% of Sildenafil's own diseases |

## Metformin  (count_A=37629, total=40762085)

- Alzheimer's: observed=178, expected=132.32, ratio=1.35 (1.15–1.6)
- **AD percentile within Metformin's own null: 95th (95% CI 89–99)**, trimmed 98th, of 102 diseases.
- Null distribution: min 0.00, median 0.13, max 74.97.
- Flagged (ratio ≥ 3, likely real indications, excluded from trimmed): Acne Vulgaris, Hidradenitis Suppurativa, Ovarian Cysts.

Top of Metformin's own distribution (most over-represented diseases), with Alzheimer's placed in context:

| Rank | Disease | observed | expected | ratio |
|---|---|---|---|---|
| 1 | Ovarian Cysts | 1994 | 26.60 | 74.97 |
| 2 | Hidradenitis Suppurativa | 33 | 3.77 | 8.75 |
| 3 | Acne Vulgaris | 45 | 13.66 | 3.29 |
| 4 | Acromegaly | 20 | 9.00 | 2.22 |
| 5 | Gout | 23 | 14.29 | 1.61 |
| 6 | Osteoporosis | 78 | 64.89 | 1.20 |
| 7 | Pancreatitis | 61 | 55.95 | 1.09 |
| 8 | Rosacea | 4 | 3.70 | 1.08 |
| — | **ALZHEIMER'S** | 178 | 132.32 | **1.35** |

## Liraglutide  (count_A=5807, total=40762085)

- Alzheimer's: observed=78, expected=20.42, ratio=3.82 (3.02–4.8)
- **AD percentile within Liraglutide's own null: 97th (95% CI 93–100)**, trimmed 100th, of 102 diseases.
- Null distribution: min 0.00, median 0.00, max 15.59.
- Flagged (ratio ≥ 3, likely real indications, excluded from trimmed): Hidradenitis Suppurativa, Pancreatitis, Ovarian Cysts.

Top of Liraglutide's own distribution (most over-represented diseases), with Alzheimer's placed in context:

| Rank | Disease | observed | expected | ratio |
|---|---|---|---|---|
| 1 | Ovarian Cysts | 64 | 4.10 | 15.59 |
| 2 | Hidradenitis Suppurativa | 5 | 0.58 | 8.59 |
| 3 | Pancreatitis | 58 | 8.63 | 6.72 |
| 4 | Psoriasis | 22 | 7.73 | 2.85 |
| 5 | Hemochromatosis | 2 | 1.20 | 1.67 |
| 6 | Gastroesophageal Reflux | 5 | 4.49 | 1.11 |
| 7 | Cholelithiasis | 6 | 5.55 | 1.08 |
| 8 | Schizophrenia | 18 | 17.54 | 1.03 |
| — | **ALZHEIMER'S** | 78 | 20.42 | **3.82** |

## Pioglitazone  (count_A=7501, total=40762085)

- Alzheimer's: observed=90, expected=26.38, ratio=3.41 (2.74–4.2)
- **AD percentile within Pioglitazone's own null: 98th (95% CI 92–100)**, trimmed 100th, of 102 diseases.
- Null distribution: min 0.00, median 0.00, max 26.03.
- Flagged (ratio ≥ 3, likely real indications, excluded from trimmed): Lichen Planus, Ovarian Cysts.

Top of Pioglitazone's own distribution (most over-represented diseases), with Alzheimer's placed in context:

| Rank | Disease | observed | expected | ratio |
|---|---|---|---|---|
| 1 | Ovarian Cysts | 138 | 5.30 | 26.03 |
| 2 | Lichen Planus | 11 | 1.73 | 6.36 |
| 3 | Gout | 8 | 2.85 | 2.81 |
| 4 | Acromegaly | 5 | 1.79 | 2.79 |
| 5 | Psoriasis | 27 | 9.99 | 2.70 |
| 6 | Klinefelter Syndrome | 2 | 0.78 | 2.56 |
| 7 | Graves Disease | 8 | 3.74 | 2.14 |
| 8 | Osteoporosis | 22 | 12.94 | 1.70 |
| — | **ALZHEIMER'S** | 90 | 26.38 | **3.41** |

## Losartan  (count_A=11386, total=40762085)

- Alzheimer's: observed=21, expected=40.04, ratio=0.52 (0.32–0.8)
- **AD percentile within Losartan's own null: 85th (95% CI 74–95)**, trimmed 87th, of 102 diseases.
- Null distribution: min 0.00, median 0.00, max 9.49.
- Flagged (ratio ≥ 3, likely real indications, excluded from trimmed): Urticaria, Gout.

Top of Losartan's own distribution (most over-represented diseases), with Alzheimer's placed in context:

| Rank | Disease | observed | expected | ratio |
|---|---|---|---|---|
| 1 | Gout | 41 | 4.32 | 9.49 |
| 2 | Urticaria | 38 | 5.68 | 6.69 |
| 3 | Polycythemia Vera | 4 | 1.93 | 2.07 |
| 4 | Hemochromatosis | 3 | 2.34 | 1.28 |
| 5 | Pancreatitis | 17 | 16.93 | 1.00 |
| 6 | Hyperthyroidism | 13 | 13.49 | 0.96 |
| 7 | Cryptorchidism | 2 | 2.49 | 0.80 |
| 8 | Varicocele | 1 | 1.42 | 0.70 |
| — | **ALZHEIMER'S** | 21 | 40.04 | **0.52** |

## Sildenafil  (count_A=8792, total=40762085)

- Alzheimer's: observed=38, expected=30.92, ratio=1.23 (0.87–1.7)
- **AD percentile within Sildenafil's own null: 91th (95% CI 83–97)**, trimmed 93th, of 102 diseases.
- Null distribution: min 0.00, median 0.00, max 6.25.
- Flagged (ratio ≥ 3, likely real indications, excluded from trimmed): Prostatitis, Anemia, Sickle Cell.

Top of Sildenafil's own distribution (most over-represented diseases), with Alzheimer's placed in context:

| Rank | Disease | observed | expected | ratio |
|---|---|---|---|---|
| 1 | Anemia, Sickle Cell | 38 | 6.08 | 6.25 |
| 2 | Prostatitis | 6 | 1.37 | 4.39 |
| 3 | Cystic Fibrosis | 18 | 9.30 | 1.93 |
| 4 | Alopecia Areata | 2 | 1.04 | 1.93 |
| 5 | beta-Thalassemia | 4 | 2.36 | 1.70 |
| 6 | Retinitis Pigmentosa | 4 | 2.52 | 1.59 |
| 7 | Urinary Incontinence | 12 | 8.38 | 1.43 |
| 8 | Tinnitus | 3 | 2.27 | 1.32 |
| — | **ALZHEIMER'S** | 38 | 30.92 | **1.23** |
