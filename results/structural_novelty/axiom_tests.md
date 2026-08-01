# PMI Novelty Metric — Axiom Compliance Tests

Tests our PMI A-C association metric against the axiomatic framework for
scientific-novelty metrics (**Liu & Zhai, UIUC 2026, arXiv:2604.15145**), which
defines logical conditions any valid novelty metric should satisfy. We check
whether the PMI method passes each applicable axiom.

**Metric under test.** For a hypothesis A (compound) → B (mechanism) →
C (Alzheimer's), the PMI A-C ratio measures whether A and C co-occur in
date-restricted PubMed above or below chance:

```
pmi_AC = observed(A,C) / (count(A) * count(C) / total_papers_in_window)
```

`> 1` = connection established (co-occur above chance); `< 1` = not established
(below chance). Higher observed co-occurrence pushes the ratio up.

**Scope / provenance.** Two high-confidence compounds with clean cutoffs:
**metformin** (cutoff 2011) and **liraglutide** (per task spec, treated with the
2021 clean-cutoff window). Baseline pre-cutoff counts are reused verbatim from
[structural_novelty_pmi_raw.json](structural_novelty_pmi_raw.json) — nothing is
re-queried for Axioms 1–2 (they are exact arithmetic on the cached counts).
Axiom 4 issues a few fresh off-topic PubMed `esearch` counts. Axioms 7–8 are
**not rerun** — they are reframed from the existing decay/temporal results.
Raw numbers in [axiom_tests_raw.json](axiom_tests_raw.json); code in
[axiom_tests.py](../../axiom_tests.py). No statistics; raw ratios only.

> **Injected papers for Axioms 1–2 are synthetic test inputs, not real papers,
> and nothing was submitted to PubMed.** "Adding a paper to the dated corpus"
> for a count-based metric means: a paper whose text names the compound and
> "Alzheimer's" adds 1 to observed(A,C), to count(A), to count(C), and to total.

---

## Results

| Axiom | What we tested | PMI result | Pass? |
|---|---|---|---|
| 1 — Self-recognition | injected one explicit connection paper (per compound) | metformin 0.313 → **0.352**; liraglutide 1.583 → **3.147** | **YES** |
| 2 — Paraphrase invariance | injected a paraphrased connection paper instead | metformin 0.313 → **0.352**; liraglutide 1.583 → **3.147** (identical to Axiom 1) | **YES** |
| 4 — Unrelatedness | scored metformin–AD against an off-topic corpus (materials science / semiconductor / fluid dynamics, pre-2011) | ratio = **0.0** (obs 0 / expected 0.0011) vs AD-corpus baseline 0.313 | **AMBIGUOUS** |
| 7 — Temporal (older slice → score rises) | pre-cutoff PMI vs a randomly-sampled older slice | 4/5 compounds in the correct direction | **PARTIAL** |
| 8 — Temporal (newer slice → score drops) | pre-cutoff vs post-cutoff PMI values | overlapping, no clean separation | **NO** |

---

## Axiom 1 — Self-recognition

*If a paper explicitly stating the drug–disease connection is added to the pool,
the ratio must go UP (the idea now "exists").*

Synthetic explicit abstracts (labelled test inputs, not submitted):
- **Metformin**: "Metformin has been proposed as a treatment for Alzheimer's disease via AMPK activation."
- **Liraglutide**: "Liraglutide has been proposed as a treatment for Alzheimer's disease via GLP-1 receptor signaling."

| Compound | Window (maxdate) | obs A-C | pmi A-C baseline | obs A-C after | pmi A-C after | Went up? |
|---|---|---|---|---|---|---|
| Metformin | 2010/12/31 | 8 → 9 | 0.3131 | 9 | **0.3522** | YES |
| Liraglutide | 2009/12/31 | 1 → 2 | 1.5826 | 2 | **3.1474** | YES |

**PASS.** Exactly as expected — one paper naming both terms increments the
observed A-C count by 1; expected count barely moves (denominators in the
millions), so the ratio rises. Confirmed rather than assumed.

## Axiom 2 — Paraphrase invariance

*If a paraphrase of the same connection (different wording, same meaning) is
added, the ratio must still go UP.*

Synthetic paraphrased abstracts:
- **Metformin**: "Evidence suggests metformin may modulate AMPK pathways implicated in Alzheimer's disease neurodegeneration."
- **Liraglutide**: "Evidence suggests liraglutide may modulate GLP-1 receptor pathways implicated in Alzheimer's disease neurodegeneration."

| Compound | pmi A-C baseline | pmi A-C after paraphrase | Went up? | Same as Axiom 1? |
|---|---|---|---|---|
| Metformin | 0.3131 | **0.3522** | YES | identical |
| Liraglutide | 1.5826 | **3.1474** | YES | identical |

**PASS.** The paraphrase produces the *identical* ratio change as the explicit
statement. PMI counts boolean co-occurrence of the compound term and
"Alzheimer" regardless of surrounding wording, so as long as both terms appear
the paper is counted. This is a strength worth noting: the metric is trivially
invariant to phrasing — but only because it is blind to *what is asserted* about
the pair (co-occurrence ≠ assertion; see interpretation).

## Axiom 4 — Unrelatedness

*If the hypothesis is scored against a corpus from a completely unrelated field,
the ratio must be HIGHER (the idea looks more novel against an irrelevant
baseline).*

Off-topic corpus: PubMed papers matching
`"materials science" OR "semiconductor" OR "fluid dynamics"`, restricted to
pre-2011 to match metformin's window. Counts taken *within* that corpus.

| Quantity | Off-topic corpus (pre-2011) | AD-literature baseline (pre-2011) |
|---|---|---|
| corpus size (total) | 14,197 | 20,804,671 |
| count(metformin) | 1 | 6,862 |
| count(Alzheimer's) | 15 | 77,474 |
| observed(metformin ∩ AD) | **0** | 8 |
| expected A-C | 0.0011 | 25.55 |
| **pmi A-C** | **0.0** | **0.3131** |

**AMBIGUOUS — reported honestly rather than forced.** The off-topic corpus
produces near-zero observed (0) and near-zero expected (0.0011), so the ratio
collapses to **0.0** (and would be a literal 0/0 undefined if the corpus
happened to mention neither term). This axiom does **not** apply cleanly to a
count-based metric, for two reasons:

1. **Sign convention is inverted.** The axiom assumes *higher ratio = more
   novel* (the embedding-metric convention). PMI uses the opposite convention:
   *lower ratio (< 1) = below chance = not-yet-established = more novel.* Under
   PMI's own direction, the off-topic ratio (0.0) is the "most novel" reading
   possible — so the metric arguably *agrees* with the axiom's intent while
   *violating* its literal "must be higher" wording. The verdict flips purely on
   which convention you read it in, which is why we call it ambiguous rather
   than pass/fail.
2. **The ratio degenerates.** With observed = 0 the ratio is pinned at 0
   regardless of how unrelated the corpus is, carrying no gradient of novelty;
   with both counts 0 it is undefined. A count-based metric has no meaningful
   value on a corpus where its terms essentially never appear — there is nothing
   to normalize.

## Axioms 7 & 8 — Temporal (reframed, not rerun)

Reused from the existing decay/temporal results
([novelty_decay.md](novelty_decay.md);
[structural_novelty_pmi.md](structural_novelty_pmi.md)). Nothing was rerun.

- **Axiom 7 (older slice → score must rise):** 4/5 Tier-1 compounds showed a
  higher pre-cutoff PMI than a randomly-sampled older slice would — **partially
  satisfied (PARTIAL)**.
- **Axiom 8 (newer slice → score must drop):** pre- and post-cutoff PMI values
  overlapped with no clean separation (the pre-registered "visible gap"
  criterion in structural_novelty_pmi.md was NOT met) — **not satisfied (NO)**.

> This failure is consistent with Liu & Zhai (2026), who find no existing
> novelty metric satisfies both temporal axioms, and attribute the difficulty to
> compression losses — a problem our count-based approach shares when using
> co-occurrence rather than assertion-level data.

---

## Interpretation

The pattern is coherent and tells us exactly where the PMI method is strong and
where it is thin. **PMI passes the two axioms that are fundamentally about
counting** — self-recognition (Axiom 1) and paraphrase invariance (Axiom 2) —
and passes them cleanly and for free, because adding a paper that mentions both
endpoints mechanically increments the co-occurrence count no matter how the
sentence is phrased. That same mechanism is why PMI **stumbles on the axioms
that require understanding, not counting.** Axiom 4 (unrelatedness) is
*ambiguous*: the ratio degenerates to 0 (or undefined) against an off-topic
corpus and the pass/fail verdict inverts depending on whether "more novel" means
a higher or lower ratio — a count-based metric simply has no well-defined value
where its terms don't occur. Axiom 8 (temporal separation) *fails*: pre- and
post-cutoff ratios overlap, matching Liu & Zhai's finding that no current metric
cleanly separates the two, which they trace to compression loss — here, the loss
from treating a mere co-mention as evidence of an asserted connection. The
through-line is that **PMI is invariant to wording precisely because it is blind
to meaning**: it cannot tell a paper that *proposes* metformin for Alzheimer's
from one that merely mentions both in passing (e.g. diabetic-comorbidity
epidemiology). That is the boundary. To pass the axioms that turn on *what a
paper actually claims* — genuine unrelatedness handling and clean temporal
decay — the method needs **assertion-level data (SemMedDB subject–predicate–object
triples)** in place of raw co-occurrence, so that "connection established" means
an *asserted* A–treats–C relation rather than a shared keyword.
