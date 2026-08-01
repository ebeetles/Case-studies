# Case Studies — LLM drug-repurposing hypothesis generation for Alzheimer's

A pipeline that generates novel drug-repurposing hypotheses for Alzheimer's
disease, plus a series of validation experiments probing whether the generated
hypotheses (and the metrics that score them) actually hold up.

> **Run everything from the repo root** (paths like `results/...` are resolved
> relative to the working directory), using the project virtualenv:
> `.venv/bin/python experiments/<group>/<script>.py`.

---

## 👉 Most recent experiment

**Structural novelty via PMI paper-counting** — `experiments/structural_novelty/`
→ results in **`results/structural_novelty/`**.

The newest run is the **axiom-compliance test** of the PMI metric
([`axiom_tests.py`](experiments/structural_novelty/axiom_tests.py) →
[`results/structural_novelty/axiom_tests.md`](results/structural_novelty/axiom_tests.md)).
This line replaced the LLM-as-judge novelty metric (see the archive below) with a
PubMed co-occurrence / PMI measure, and is the current working approach.

| Script | What it does | Result |
|---|---|---|
| `structural_novelty.py` | Swanson ABC decomposition of each hypothesis (A→B→C) | `structural_novelty/structural_decomposition.json` |
| `structural_novelty_run.py` | Raw A-C / B-C PubMed co-occurrence counts per window | `structural_novelty/structural_novelty.md`, `_raw.json` |
| `structural_novelty_pmi.py` | PMI normalization of those counts (observed/expected ratios) | `structural_novelty/structural_novelty_pmi.md`, `_raw.json` |
| `axiom_tests.py` | Tests the PMI metric against the novelty-metric axioms | `structural_novelty/axiom_tests.md`, `_raw.json` |

---

## Repository layout

```
.                          core pipeline (the system under study)
├── main.py                pipeline entry point (Conditions A–D)
├── pipeline.py            generation + retrieval + judging loop
├── generator.py           hypothesis generation + all generation prompts
├── judge.py               pipeline judge (novelty / consistency / feasibility)
├── retrieval.py           PubMed retrieval + cache
├── seed_papers.py         seed literature
├── graphs.py              pipeline result figures
├── _exppath.py            import-path bootstrap for the experiment folders
│
├── experiments/           live / non-abandoned experiments
│   ├── structural_novelty/   ← CURRENT working line (see above)
│   ├── rediscovery/          retrospective rediscovery benchmark
│   └── diversity_probe/      exploration/exploitation diversity probe
│
├── archive/               ❌ superseded LLM-as-judge novelty line (see below)
├── figures/               standalone case-study figure generators
└── results/               all outputs, grouped to mirror the experiments
    ├── structural_novelty/   ← current results
    ├── rediscovery/
    ├── diversity_probe/
    ├── archive/              results from the abandoned line
    └── *.png, run_log.json, all_runs_log.json, pubmed_cache.json
                               shared pipeline outputs + headline figures
```

## Experiments

### Live — `experiments/`

| Group | Scripts | Outcome |
|---|---|---|
| **structural_novelty** | `structural_novelty*`, `axiom_tests` | ✅ current metric — PMI co-occurrence; passes the axiom checks |
| **rediscovery** | `evaluate_rediscovery`, `seed_papers_*` | retrospective benchmark: can the pipeline re-derive known repurposing findings (liraglutide, baricitinib, finerenone) |
| **diversity_probe** | `measure_diversity`, `probe_exploration_tradeoff`, `plot_probe_results` | exploration/exploitation + generation-diversity probe |

### ❌ Archived — `archive/` (the LLM-as-judge novelty line)

Four attempts to make an LLM score hypothesis *novelty* reliably. All failed the
same way — the judge's novelty score was flat / non-responsive to whether the
idea was actually novel — which is what motivated the pivot to the paper-counting
structural-novelty metric above.

| Attempt | Scripts | Result (`results/archive/`) |
|---|---|---|
| Rubric validation | `run_validation`, `validation_data`, `validation_degrade`, `validation_judge` | novelty tier-recovery 0.35 (failed); specificity 0.87 worked — `summary.md` |
| Localization v2 (revised novelty prompt) | `rerun_localization_v2` | revised prompt still didn't localize novelty — `summary_v2_localization_only.md` |
| Novelty decay (time-split) | `novelty_decay`, `build_corpus`, `curated_corpus_data`, `semantic_scholar` | judge flat at 3/5, 0/2 directional agreement — `novelty_decay.md` |
| Comprehension check | `novelty_comprehension_check` | diagnostic: judge reads the literature but doesn't weight it — `novelty_comprehension_check.md` |

## Prompts

Prompts are inline in the code (no separate prompt files):

- **Generation** — `generator.py` (`_generation_prompt`, `ABSTRACTION_PROMPT`,
  `DIVERSITY_ABSTRACTION_PROMPT`, `MAPPING_PROMPT`, …)
- **Pipeline judge** — `judge.py` (`score_novelty` / `score_consistency` /
  `score_feasibility` + pairwise comparison)
- **Validation judges / rubrics** — `archive/validation_judge.py`
  (`rubric_score_novelty`, `rubric_score_specificity`, `holistic_score`)
- **Hypothesis parsing** — `experiments/structural_novelty/structural_novelty.py`

## Notes on the layout

The experiment scripts use flat `import X` statements and cross-import each
other. Each entry script starts with a 3-line header that adds the repo root and
the experiment folders to `sys.path` (via `_exppath.py`), so imports resolve from
any folder — as long as scripts are run from the repo root.
