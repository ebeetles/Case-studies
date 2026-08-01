# Novelty Decay — Time-Split Retrospective Validation

Adapted from HindSight (Jiang 2026, arXiv:2603.15164): tests the rubric NOVELTY dimension against each compound's OWN literature history (pre- vs. post-first-proposal), avoiding the cross-compound confound in the prior tier-recovery runs (trial status correlates with 'became well-known over time').

**Corpus**: hand-curated (Semantic Scholar API scraping stalled on persistent rate-limiting — see build_corpus.py / novelty_decay_curated_corpus.md). 3 pre-cutoff + 3 post-cutoff papers per compound, sourced via targeted web search. Two HIGH CONFIDENCE compounds only (metformin, sildenafil); losartan/pioglitazone/liraglutide deferred as lower-confidence estimates pending a decision to extend.

Embedding model: `text-embedding-3-small` (OpenAI). Judge model: `gpt-5.4-mini` (OpenAI, current rubric novelty prompt, unmodified — only a literature-context block and a 'score using only this context' instruction are added).

No correlation coefficients or p-values — n=2 compounds here. Raw per-compound numbers and directional agreement only.

## Results table

| Compound | Pre-cutoff max sim | Post-cutoff max sim | Embedding Δ (post-pre) | Judge pre-cutoff novelty | Judge post-cutoff novelty | Judge Δ (post-pre) |
|---|---|---|---|---|---|---|
| metformin | 0.746 | 0.783 | +0.037 | 3 | 3 | +0 |
| sildenafil | 0.625 | 0.752 | +0.127 | 3 | 3 | +0 |

## Directional agreement

Expected 'decay signature': embedding similarity should be higher post-cutoff (idea becomes more embedded in the literature over time → embedding Δ > 0), and — if the novelty judge is tracking real novelty decay rather than something else — its score should be LOWER post-cutoff (judge Δ < 0). Agreement = judge Δ and embedding Δ point in the expected opposite directions (embedding Δ > 0 AND judge Δ < 0).

- **metformin**: embedding Δ + (+0.037), judge Δ +/0 (+0) → does NOT match
- **sildenafil**: embedding Δ + (+0.127), judge Δ +/0 (+0) → does NOT match

**Agreement rate: 0/2 compounds.**

## Per-compound judge justifications

### metformin (cutoff: 2012-01-01, confidence: high)

- Hypothesis: Metformin may activate AMPK and modulate the mTOR pathway to reduce neuroinflammation and tau pathology relevant to Alzheimer's disease.
- Pre-cutoff score 3: This is a plausible but fairly expected repurposing link: metformin’s known AMPK activation is straightforwardly extended to AD-relevant processes like neuroinflammation and tau pathology, but the hypothesis does not articulate a particularly novel or non-obvious AD-specific mechanism beyond that general pathway.
- Post-cutoff score 3: This is a plausible and fairly expected AD repurposing rationale: the provided literature already links metformin to AMPK/mTOR/S6K/BACE1 effects, amyloid-beta reduction, and broader anti-dementia associations, so the added tau/neuroinflammation angle is coherent but not highly non-obvious.

### sildenafil (cutoff: 2021-12-06, confidence: high)

- Hypothesis: Sildenafil may inhibit phosphodiesterase-5 to increase cGMP signaling and reduce tau phosphorylation and amyloid accumulation relevant to Alzheimer's disease.
- Pre-cutoff score 3: This is a plausible but fairly expected repurposing idea: it extends a known PDE5/cGMP signaling mechanism into AD-relevant endpoints like tau phosphorylation and amyloid burden, but the provided literature does not show a prior AD-specific rationale or a particularly non-obvious mechanistic bridge.
- Post-cutoff score 3: The proposal is a plausible and fairly expected AD repurposing rationale because it links a known PDE5/cGMP mechanism to canonical AD pathologies (tau phosphorylation and amyloid burden), but it is not merely a generic restatement since the cited network-medicine and early validation literature gives it a more specific AD-targeted framing.
