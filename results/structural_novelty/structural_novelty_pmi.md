# Structural Novelty — Amendment 2 (PMI normalization)

Extends structural_novelty.md. Prior raw-count results are left intact; this adds PMI-style normalized association for the A-C and B-C links, plus a fixed cutoff+5yr window. Scope: the 5 Tier-1 compounds (Test 1's subjects).

## Amendment 2 (verbatim)

```
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
```

## PMI ratios per compound × window

`pmi = observed / (count(A)*count(C)/total)`. >>1 = over-represented (link established); ~1 = chance; <1 = under-represented.

Each ratio is shown as **point (95% CI)**. The interval is the exact Poisson (Garwood) confidence interval on the observed co-occurrence count, divided through by the expected count — *not* a sqrt(N) approximation, which is invalid at the small counts here (e.g. liraglutide pre-cutoff, observed = 1).

| ID | Compound | Conf | Window | maxdate | count(A) | count(C) | total | obs A-C | exp A-C | **pmi A-C (95% CI)** | obs B-C | pmi B-C (95% CI) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1-A | Metformin | hig | pre_cutoff | 2010/12/31 | 6862 | 77474 | 20804671 | 8 | 25.6 | **0.31 (0.14–0.62)** | 19 | 1.44 (0.87–2.3) |
| T1-A | Metformin | hig | post5yr | 2016/12/31 | 15287 | 124193 | 26928345 | 57 | 70.5 | **0.81 (0.61–1)** | 131 | 2.55 (2.13–3) |
| T1-A | Metformin | hig | present | 2026/07/20 | 37573 | 253317 | 40725178 | 425 | 233.7 | **1.82 (1.65–2)** | 755 | 3.42 (3.18–3.7) |
| T1-B | Liraglutide | mod | pre_cutoff | 2009/12/31 | 177 | 71234 | 19954080 | 1 | 0.6 | **1.58 (0.04–8.8)** | 10 | 4.17 (2.00–7.7) |
| T1-B | Liraglutide | mod | post5yr | 2015/12/31 | 1245 | 115498 | 25811826 | 39 | 5.6 | **7.00 (4.98–9.6)** | 62 | 5.43 (4.17–7) |
| T1-B | Liraglutide | mod | present | 2026/07/20 | 5785 | 253317 | 40725178 | 154 | 36.0 | **4.28 (3.63–5)** | 348 | 3.22 (2.89–3.6) |
| T1-C | Pioglitazone | mod | pre_cutoff | 2004/12/31 | 881 | 46668 | 16282757 | 8 | 2.5 | **3.17 (1.37–6.2)** | 31 | 4.46 (3.03–6.3) |
| T1-C | Pioglitazone | mod | post5yr | 2010/12/31 | 2763 | 77474 | 20804671 | 29 | 10.3 | **2.82 (1.89–4)** | 114 | 4.07 (3.36–4.9) |
| T1-C | Pioglitazone | mod | present | 2026/07/20 | 7494 | 253317 | 40725178 | 175 | 46.6 | **3.75 (3.22–4.4)** | 554 | 3.25 (2.98–3.5) |
| T1-D | Losartan | mod | pre_cutoff | 2014/12/31 | 8253 | 107070 | 24715382 | 14 | 35.8 | **0.39 (0.21–0.66)** | 26 | 0.75 (0.49–1.1) |
| T1-D | Losartan | mod | post5yr | 2020/12/31 | 9977 | 166378 | 31937290 | 30 | 52.0 | **0.58 (0.39–0.82)** | 63 | 1.21 (0.93–1.5) |
| T1-D | Losartan | mod | present | 2026/07/20 | 11383 | 253317 | 40725178 | 46 | 70.8 | **0.65 (0.48–0.87)** | 88 | 1.22 (0.98–1.5) |
| T1-E | Sildenafil | hig | pre_cutoff | 2020/12/31 | 7258 | 166378 | 31937290 | 38 | 37.8 | **1.01 (0.71–1.4)** | 73 | 2.84 (2.23–3.6) |
| T1-E | Sildenafil | hig | post5yr | 2026/12/31 | 8787 | 253332 | 40727664 | 70 | 54.7 | **1.28 (1.00–1.6)** | 131 | 3.32 (2.77–3.9) |
| T1-E | Sildenafil | hig | present | 2026/07/20 | 8787 | 253317 | 40725178 | 70 | 54.7 | **1.28 (1.00–1.6)** | 131 | 3.32 (2.77–3.9) |

## Pre-registered success criterion (Amendment 2 #4)

>=4/5 Tier-1 compounds show A-C pmi increasing pre-cutoff -> cutoff+5yr, AND pre-cutoff values cluster separately from post values with a visible gap.

| ID | Compound | pmi A-C pre-cutoff (95% CI) | pmi A-C cutoff+5yr (95% CI) | Increased? | 95% CIs disjoint? |
|---|---|---|---|---|---|
| T1-A | Metformin | 0.31 (0.14–0.62) | 0.81 (0.61–1) | YES | no (overlap) |
| T1-B | Liraglutide | 1.58 (0.04–8.8) | 7.00 (4.98–9.6) | YES | no (overlap) |
| T1-C | Pioglitazone | 3.17 (1.37–6.2) | 2.82 (1.89–4) | no | no (overlap) |
| T1-D | Losartan | 0.39 (0.21–0.66) | 0.58 (0.39–0.82) | YES | no (overlap) |
| T1-E | Sildenafil | 1.01 (0.71–1.4) | 1.28 (1.00–1.6) | YES | no (overlap) |

- A-C pmi increased pre→post in **4/5** compounds.
- The pre- vs post-cutoff 95% CIs are **disjoint in 0/5** compounds; in the rest the increase is not distinguishable from no change at 95%. (Liraglutide's headline pre-cutoff 1.58 rests on a single observed paper: CI ≈ 0.04–8.8, which overlaps its own post value — the point estimate is not reliable.)
- Pre-cutoff pmi range: [0.31, 3.17]; cutoff+5yr pmi range: [0.58, 7.00] (point estimates).
- Highest pre-cutoff pmi = 3.17; lowest post pmi = 0.58; gap = -2.59 (OVERLAP — clusters not separable on point estimates alone).

**Criterion NOT MET** (needs >=4/5 increasing AND a visible gap; got 4/5 increasing, gap -2.59).

## PMI-based classification (Amendment 2 #3)

No hard cutoff baked in. Values reported; a descriptive boundary of pmi≈1 (chance) is used only to label, and flagged as descriptive.

| ID | Compound | Window | pmi A-C (95% CI) | pmi B-C (95% CI) | Descriptive case |
|---|---|---|---|---|---|
| T1-A | Metformin | pre_cutoff | 0.31 (0.14–0.62) | 1.44 (0.87–2.3) | Case 3 (neither over-represented) |
| T1-A | Metformin | post5yr | 0.81 (0.61–1) | 2.55 (2.13–3) | Case 2 (B-C over-rep, A-C not) |
| T1-A | Metformin | present | 1.82 (1.65–2) | 3.42 (3.18–3.7) | Case 2 (B-C over-rep, A-C not) |
| T1-B | Liraglutide | pre_cutoff | 1.58 (0.04–8.8) | 4.17 (2.00–7.7) | Case 2 (B-C over-rep, A-C not) |
| T1-B | Liraglutide | post5yr | 7.00 (4.98–9.6) | 5.43 (4.17–7) | Case 1 (A-C over-represented) |
| T1-B | Liraglutide | present | 4.28 (3.63–5) | 3.22 (2.89–3.6) | Case 1 (A-C over-represented) |
| T1-C | Pioglitazone | pre_cutoff | 3.17 (1.37–6.2) | 4.46 (3.03–6.3) | Case 1 (A-C over-represented) |
| T1-C | Pioglitazone | post5yr | 2.82 (1.89–4) | 4.07 (3.36–4.9) | Case 1 (A-C over-represented) |
| T1-C | Pioglitazone | present | 3.75 (3.22–4.4) | 3.25 (2.98–3.5) | Case 1 (A-C over-represented) |
| T1-D | Losartan | pre_cutoff | 0.39 (0.21–0.66) | 0.75 (0.49–1.1) | Case 3 (neither over-represented) |
| T1-D | Losartan | post5yr | 0.58 (0.39–0.82) | 1.21 (0.93–1.5) | Case 3 (neither over-represented) |
| T1-D | Losartan | present | 0.65 (0.48–0.87) | 1.22 (0.98–1.5) | Case 3 (neither over-represented) |
| T1-E | Sildenafil | pre_cutoff | 1.01 (0.71–1.4) | 2.84 (2.23–3.6) | Case 2 (B-C over-rep, A-C not) |
| T1-E | Sildenafil | post5yr | 1.28 (1.00–1.6) | 3.32 (2.77–3.9) | Case 2 (B-C over-rep, A-C not) |
| T1-E | Sildenafil | present | 1.28 (1.00–1.6) | 3.32 (2.77–3.9) | Case 2 (B-C over-rep, A-C not) |

_Descriptive boundary pmi≥2 = '>>1'. This is a post-hoc label for readability, not a pre-registered threshold; the raw pmi values above are the primary output._

## Does a natural separation appear in the values?

- A-C pmi pre-cutoff values: ['0.31 (0.14–0.62)', '1.58 (0.04–8.8)', '3.17 (1.37–6.2)', '0.39 (0.21–0.66)', '1.01 (0.71–1.4)']
- A-C pmi cutoff+5yr values: ['0.81 (0.61–1)', '7.00 (4.98–9.6)', '2.82 (1.89–4)', '0.58 (0.39–0.82)', '1.28 (1.00–1.6)']
- On point estimates a gap can appear, but once the 95% Poisson CIs are drawn the pre- and post-cutoff ranges overlap for most compounds; the separation is not robust at n this small.
