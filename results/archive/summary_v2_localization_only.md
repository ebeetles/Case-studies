# Rubric Validation — v2 Localization Only (revised NOVELTY prompt)

Judge model: `gpt-5.4-mini` (OpenAI). Novelty rubric prompt revised to score novelty of the AD *application*, not novelty/rarity of the underlying mechanism. Specificity prompt and scores are unchanged from the prior run.

Tier recovery (3a) is not rerun here for novelty — trial-stage ground truth is confounded with a hypothesis becoming well-known over time, so it's not a valid novelty check. Specificity tier recovery is unaffected; see results/validation/summary.md.

No p-values / confidence intervals — n too small to be meaningful.

## 3b. Dimension localization (degraded variants, revised novelty)

Score delta = original rubric score minus degraded variant's rubric score, mean over the 5 Tier-1 compounds.

| Degradation type | n | Δ novelty | Δ specificity |
|---|---|---|---|
| specificity-degraded | 5 | -0.30 | 2.40 |
| novelty-degraded | 5 | 0.10 | 0.60 |

## 3c. Stability — novelty (revised prompt) only

15 hypotheses (5 Tier-1 originals + 10 degraded variants), 2 repeats each.

| Mean range (max-min) | Mean variance | Hyps w/ any disagreement |
|---|---|---|
| 0.47 | 0.12 | 7/15 |

## Raw scores (revised novelty prompt)

| ID | True tier / degradation | Compound | Novelty v2 (mean) | Specificity (mean, reused) |
|---|---|---|---|---|
| H013 | Tier 1 | Liraglutide | 2.5 | 5.0 |
| H017 | Tier 1 | Pioglitazone | 3.0 | 5.0 |
| H019 | Tier 1 | Sildenafil | 2.0 | 5.0 |
| H023 | Tier 1 | Metformin | 2.5 | 4.5 |
| H024 | Tier 1 | Losartan | 2.5 | 5.0 |
| H001 | novelty-degraded of T1-A | Metformin | 2.5 | 4.0 |
| H004 | specificity-degraded of T1-C | Pioglitazone | 2.5 | 2.0 |
| H005 | novelty-degraded of T1-B | Liraglutide | 2.0 | 4.0 |
| H009 | specificity-degraded of T1-A | Metformin | 2.5 | 2.5 |
| H010 | specificity-degraded of T1-D | Losartan | 3.0 | 2.5 |
| H012 | specificity-degraded of T1-B | Liraglutide | 3.0 | 2.0 |
| H015 | novelty-degraded of T1-D | Losartan | 2.5 | 4.0 |
| H018 | specificity-degraded of T1-E | Sildenafil | 3.0 | 3.5 |
| H020 | novelty-degraded of T1-E | Sildenafil | 3.0 | 4.5 |
| H025 | novelty-degraded of T1-C | Pioglitazone | 2.0 | 5.0 |
