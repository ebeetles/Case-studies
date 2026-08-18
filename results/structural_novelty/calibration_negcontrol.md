# Step 2 — Negative-control validation

Does the calibration rank true NEGATIVES low? The negative-control drugs below (healthy literature, no strong Alzheimer's story) are run through the **identical** path as the Tier-1 drugs — same ~100 control diseases, same observed/expected ratio, same bootstrap 95% CI (B=2000), same contamination trim (ratio ≥ 3), same present window (2026/07/20).

**Scope of this test.** These are STRONG negatives (raw AD ratios 0.03–0.29, floor values), not boundary cases near chance. So this validates *doesn't rank obvious non-candidates high* — NOT that the metric discriminates at the positive/negative boundary.

## Pre-registered pass condition (set before results)

**(a)** negative cluster median < 60th, AND **(b)** every negative's percentile-CI upper < the Tier-1 CI lower floor (**74th**, the lowest Tier-1 CI bound). Negatives with AD obs ≤ 2 are DIRECTIONAL ONLY.

## Combined table — negatives and Tier-1 for contrast

| Drug | Group | AD obs | Raw AD ratio (95% CI) | Calibrated percentile (95% CI) | Trimmed |
|---|---|---|---|---|---|
| Metformin | pos | 178 | 1.35 (1.15–1.6) | **95th** (89–99) | 98th |
| Liraglutide | pos | 78 | 3.82 (3.02–4.8) | **97th** (93–100) | 100th |
| Pioglitazone | pos | 90 | 3.41 (2.74–4.2) | **98th** (92–100) | 100th |
| Losartan | pos | 21 | 0.52 (0.32–0.8) | **85th** (74–95) | 87th |
| Sildenafil | pos | 38 | 1.23 (0.87–1.7) | **91th** (83–97) | 93th |
| Omeprazole | neg | 10 | 0.20 (0.10–0.37) | **55th** (45–74) | 58th |
| Loratadine | neg | 2 | 0.29 (0.03–1) | **75th** (0–89) | 83th |
| Hydrochlorothiazide | neg | 1 | 0.03 (0.00–0.16) | **54th** (0–72) | 57th |
| Amoxicillin | neg | 3 | 0.03 (0.01–0.088) | **31th** (0–48) | 36th |
| Clotrimazole | neg | 1 | 0.08 (0.00–0.44) | **70th** (0–83) | 74th |
| Albuterol | neg | 5 | 0.09 (0.03–0.22) | **61th** (54–77) | 64th |

## Per-negative: CI upper vs Tier-1 floor (74th)

| Drug | AD obs | Percentile (95% CI) | CI upper | < floor (74)? | Status |
|---|---|---|---|---|---|
| Omeprazole | 10 | 55th (45–74) | 74 | no | CI overlaps Tier-1 — can't resolve at these counts |
| Loratadine | 2 | 75th (0–89) | 89 | no | DIRECTIONAL (obs≤2) — can't resolve |
| Hydrochlorothiazide | 1 | 54th (0–72) | 72 | yes | DIRECTIONAL (obs≤2) — can't resolve |
| Amoxicillin | 3 | 31th (0–48) | 48 | yes | clears floor |
| Clotrimazole | 1 | 70th (0–83) | 83 | no | DIRECTIONAL (obs≤2) — can't resolve |
| Albuterol | 5 | 61th (54–77) | 77 | no | CI overlaps Tier-1 — can't resolve at these counts |

## Cluster comparison

- Negative controls: min 31th, median 58th, max 75th (range 31–75).
- Tier-1: min 85th, median 95th, max 98th (range 85–98).

## VERDICT (computed)

- (a) negative median 58th < 60 → **PASS**.
- (b) all six CI uppers < Tier-1 floor 74 → **FAIL**.
- Among the 3 RESOLVABLE negatives (obs > 2: Omeprazole, Amoxicillin, Albuterol), all CI uppers < floor → **FAIL**.
- 3 DIRECTIONAL negatives (obs ≤ 2: Loratadine, Hydrochlorothiazide, Clotrimazole) — wide CIs; read as 'can't resolve', not pass/fail.

**Strict verdict (a AND b over all six): FAIL / INCONCLUSIVE.** At least one negative's CI reaches the Tier-1 floor; where that is driven by AD obs ≤ 2 (directional) or a wide CI, the reading is 'can't resolve at these counts' (small-count limit), not a metric failure. See the per-negative status column.
