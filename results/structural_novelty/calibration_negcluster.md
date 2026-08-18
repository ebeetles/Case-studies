# Step 2 — Negative-control CLUSTER test (expanded set)

Option 1: expand to **20 negative controls** and test pos-vs-neg separation at the CLUSTER level, sidestepping the per-drug small-count resolution limit (a single near-zero-AD-count drug can't be resolved alone, but the groups can be compared).

**Pre-registered pass condition (set before results):** (a) one-sided Mann-Whitney U (H1: Tier-1 percentiles > negative percentiles) **p < 0.05**, AND (b) bootstrap 95% CI of the AUC effect size (P a random positive outranks a random negative) has **lower bound > 0.5**.

## Result

- Mann-Whitney U = 100, **one-sided p = 0.00042** (H1: positives rank above negatives).
- Effect size **AUC = 0.99** (95% CI 0.95–1.00), i.e. a random Tier-1 drug outranks a random negative ~99% of the time.
- Tier-1 percentiles: median 95th (range 85–98); negatives: median 54th (range 0–85).

## VERDICT (computed)

- (a) MWU one-sided p = 0.00042 < 0.05 → **PASS**.
- (b) AUC 95% CI lower 0.95 > 0.50 → **PASS**.

**Cluster verdict (a AND b): PASS.** Tier-1 drugs rank significantly and reliably above the negative controls; the top tier is real signal, not a low bar.

## Full ranking (all drugs by calibrated percentile)

| Drug | Group | AD obs | Raw AD ratio (95% CI) | Calibrated percentile (95% CI) |
|---|---|---|---|---|
| Pioglitazone | pos | 90 | 3.41 (2.74–4.2) | **98th** (92–100) |
| Liraglutide | pos | 78 | 3.82 (3.02–4.8) | **97th** (93–100) |
| Metformin | pos | 178 | 1.35 (1.15–1.6) | **95th** (89–99) |
| Sildenafil | pos | 38 | 1.23 (0.87–1.7) | **91th** (83–97) |
| Losartan | pos | 21 | 0.52 (0.32–0.8) | **85th** (74–95) |
| Tamsulosin | neg | 4 | 0.45 (0.12–1.1) | **85th** (78–95) |
| Loperamide | neg | 5 | 0.50 (0.16–1.2) | **80th** (73–91) |
| Sumatriptan | neg | 1 | 0.08 (0.00–0.45) | **78th** (0–90) |
| Loratadine | neg | 2 | 0.29 (0.03–1) | **75th** (0–89) |
| Finasteride | neg | 2 | 0.14 (0.02–0.5) | **74th** (0–86) |
| Clotrimazole | neg | 1 | 0.08 (0.00–0.44) | **70th** (0–83) |
| Albuterol | neg | 5 | 0.09 (0.03–0.22) | **61th** (54–77) |
| Nitrofurantoin | neg | 1 | 0.05 (0.00–0.26) | **57th** (0–75) |
| Omeprazole | neg | 10 | 0.20 (0.10–0.37) | **55th** (45–74) |
| Hydrochlorothiazide | neg | 1 | 0.03 (0.00–0.16) | **54th** (0–72) |
| Ranitidine | neg | 3 | 0.11 (0.02–0.33) | **54th** (0–75) |
| Azithromycin | neg | 4 | 0.07 (0.02–0.19) | **43th** (36–60) |
| Fluconazole | neg | 3 | 0.05 (0.01–0.13) | **41th** (0–59) |
| Amoxicillin | neg | 3 | 0.03 (0.01–0.088) | **31th** (0–48) |
| Metronidazole | neg | 3 | 0.03 (0.01–0.1) | **25th** (0–44) |
| Ciprofloxacin | neg | 2 | 0.01 (0.00–0.051) | **21th** (0–39) |
| Fexofenadine | neg | 0 | 0.00 (0.00–0.85) | **0th** (0–0) |
| Cetirizine | neg | 0 | 0.00 (0.00–0.45) | **0th** (0–0) |
| Terbinafine | neg | 0 | 0.00 (0.00–0.26) | **0th** (0–0) |
| Oseltamivir | neg | 0 | 0.00 (0.00–0.18) | **0th** (0–0) |
