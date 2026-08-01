from __future__ import annotations

"""
MOOSE-Chem-style rediscovery evaluation.

Runs one holdout paper at a time with paper-specific seed literature,
research questions, and contamination checks.

Usage:
  python evaluate_rediscovery.py
"""

import importlib.util
import json
import os
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from openai import OpenAI

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "PyYAML is required. Install with: pip install pyyaml"
    ) from exc

import generator as gen_module
import judge as judge_module
import pipeline as pipeline_module
import retrieval as retrieval_module
from judge import print_condition_comparison
from pipeline import run_pipeline

BENCHMARK_PATH = Path("holdout_benchmark.yaml")
RESULTS_DIR = Path("results")
PUBMED_CACHE_PATH = RESULTS_DIR / "pubmed_cache.json"
EMBEDDING_MODEL = "text-embedding-3-small"
SIM_THRESHOLD = 0.65
PARTIAL_THRESHOLD = 0.45

GENERIC_DRUG_PHRASES = (
    r"\bexisting\s+(?:FDA[- ]approved\s+)?(?:approved\s+)?drugs?\b",
    r"\bFDA[- ]approved\s+drugs?\b",
    r"\bapproved\s+(?:therapeutic\s+)?(?:agents?|compounds?|drugs?)\b",
    r"\brepurposed\s+(?:therapeutic\s+)?(?:agents?|compounds?|drugs?)\b",
    r"\bexisting\s+(?:therapeutic\s+)?(?:agents?|compounds?|medications?)\b",
)

SPECIFIC_DRUG_PATTERNS = (
    r"\b[a-zA-Z][\w-]*(?:glutide|tinib|mab|fenone|formin|statin|sartan|prazole|"
    r"zole|pam|done|mil|nib|ide|ate|one|ol|il)\b",
    r"\b(?:valproic|folic|salicylic|mevalonic)\s+acid\b",
    r"\b(?:drug|compound|agent|inhibitor|antagonist|agonist)\s+[A-Z][\w-]+\b",
    r"\b[A-Z][a-z]{3,}(?:in|ib|ide|ate|one|ol)\b",
)

_original_generation_prompt = gen_module._generation_prompt
_original_retrieve_papers = retrieval_module.retrieve_papers
_original_check_retrieval_relevance = judge_module.check_retrieval_relevance

_active_research_question: str = ""
_active_contamination_terms: tuple[str, ...] = ()


def _load_dotenv() -> None:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val


def clear_pubmed_cache() -> None:
    """Fix 6: delete cached post-2023 PubMed results before each test run."""
    if PUBMED_CACHE_PATH.exists():
        PUBMED_CACHE_PATH.unlink()
        print(f"Cleared {PUBMED_CACHE_PATH}")


def load_benchmark() -> list[dict]:
    with open(BENCHMARK_PATH) as f:
        data = yaml.safe_load(f)
    return data["holdout_papers"]


def load_seed_papers(seed_paper_file: str) -> list[dict]:
    path = Path(seed_paper_file)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load seed papers from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    papers = getattr(module, "SEED_PAPERS", None)
    if not papers:
        raise RuntimeError(f"{path} does not define SEED_PAPERS")
    return papers


def _contains_terms(text: str, terms: list[str]) -> list[str]:
    hits: list[str] = []
    lower = text.lower()
    for term in terms:
        if term.lower() in lower:
            hits.append(term)
    return hits


def verify_no_contamination(
    seed_papers: list[dict],
    research_question: str,
    contamination_terms: list[str],
    label: str,
) -> None:
    """Ensure holdout terms never appear in static generator inputs."""
    static_strings: list[tuple[str, str]] = [
        (f"{label}/research_question", research_question),
    ]
    for i, paper in enumerate(seed_papers):
        static_strings.append((f"{label}/seed_{i+1}_title", paper["title"]))
        static_strings.append(
            (f"{label}/seed_{i+1}_abstract", paper.get("abstract", ""))
        )

    for name, text in static_strings:
        hits = _contains_terms(text, contamination_terms)
        if hits:
            raise RuntimeError(
                f"Contamination in {name}: term(s) {hits}"
            )


def _patched_generation_prompt(
    literature: str,
    existing: list[dict],
    condition: str | None = None,
) -> str:
    base = _original_generation_prompt(literature, existing, condition=condition)
    return base.replace(
        "Here is relevant literature:",
        f"Research question:\n{_active_research_question}\n\n"
        "Here is relevant literature:",
    )


def _paper_text(paper: dict) -> str:
    return f"{paper.get('title', '')} {paper.get('abstract', '')}"


def _filter_contaminated_papers(papers: list[dict]) -> list[dict]:
    return [
        p for p in papers
        if not _contains_terms(_paper_text(p), list(_active_contamination_terms))
    ]


def _patched_retrieve_papers(
    query: str,
    n: int = 5,
    append_alzheimer: bool = True,
) -> list[dict]:
    batch = max(n * 5, 15)
    fetched = _original_retrieve_papers(
        query, n=batch, append_alzheimer=append_alzheimer,
    )
    filtered = _filter_contaminated_papers(fetched)
    dropped = len(fetched) - len(filtered)
    if dropped:
        print(
            f"  [eval] Filtered {dropped} retrieved paper(s) "
            f"containing holdout contamination terms."
        )
    return filtered[:n]


def _patched_check_retrieval_relevance(
    idea: dict,
    weakness_feedback: str,
    retrieved_papers: list[dict],
    is_ood: bool = False,
) -> int:
    try:
        return _original_check_retrieval_relevance(
            idea, weakness_feedback, retrieved_papers, is_ood=is_ood,
        )
    except RuntimeError as exc:
        if "not relevant to the diagnosed weakness" in str(exc):
            print(f"    [eval] Warning: {exc} — continuing evaluation run.")
            return 1
        raise


def install_eval_patches(
    research_question: str,
    contamination_terms: list[str],
) -> None:
    global _active_research_question, _active_contamination_terms
    _active_research_question = research_question.strip()
    _active_contamination_terms = tuple(contamination_terms)
    gen_module._generation_prompt = _patched_generation_prompt
    retrieval_module.retrieve_papers = _patched_retrieve_papers
    pipeline_module.retrieve_papers = _patched_retrieve_papers
    judge_module.check_retrieval_relevance = _patched_check_retrieval_relevance
    pipeline_module.check_retrieval_relevance = _patched_check_retrieval_relevance


def hypothesis_text(hypothesis: dict) -> str:
    return " ".join(
        hypothesis.get(k, "").strip()
        for k in ("problem", "method", "contribution")
    )


def detect_contamination(
    hypothesis: dict,
    contamination_terms: list[str],
) -> list[str]:
    return _contains_terms(hypothesis_text(hypothesis), contamination_terms)


def _has_specific_drug_name(method: str) -> bool:
    for pattern in SPECIFIC_DRUG_PATTERNS:
        if re.search(pattern, method):
            return True
    return False


def check_drug_named(hypothesis: dict) -> float:
    method = hypothesis.get("method", "")
    if _has_specific_drug_name(method):
        return 1.0
    for pattern in GENERIC_DRUG_PHRASES:
        if re.search(pattern, method, re.IGNORECASE):
            return 0.0
    return 0.0


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


class EmbeddingScorer:
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise SystemExit(
                "OPENAI_API_KEY is not set (required for embedding similarity)."
            )
        self._client = OpenAI(api_key=api_key)

    @lru_cache(maxsize=256)
    def embed(self, text: str) -> tuple[float, ...]:
        text = text.strip()
        if not text:
            return tuple()
        response = self._client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )
        return tuple(response.data[0].embedding)

    def similarity(self, text_a: str, text_b: str) -> float:
        ea = self.embed(text_a)
        eb = self.embed(text_b)
        if not ea or not eb:
            return 0.0
        return cosine_similarity(list(ea), list(eb))


def check_drug_class(
    hypothesis: dict,
    ground_truth: dict,
    scorer: EmbeddingScorer,
) -> float:
    text = hypothesis_text(hypothesis)
    drug = ground_truth["drug"]
    drug_class = ground_truth["drug_class"]
    mechanism = ground_truth["mechanism"]

    if drug.lower() in text.lower():
        return 1.0

    class_sim = scorer.similarity(text, drug_class)
    if class_sim >= SIM_THRESHOLD:
        return 1.0

    mech_sim = scorer.similarity(text, mechanism)
    if mech_sim >= SIM_THRESHOLD:
        return 0.5

    return 0.0


def check_mechanism(
    hypothesis: dict,
    mechanism: str,
    scorer: EmbeddingScorer,
) -> float:
    text = (
        f"{hypothesis.get('method', '')} "
        f"{hypothesis.get('contribution', '')}"
    ).strip()
    sim = scorer.similarity(text, mechanism)
    if sim >= SIM_THRESHOLD:
        return 1.0
    if sim >= PARTIAL_THRESHOLD:
        return 0.5
    return 0.0


def score_rediscovery(
    hypothesis: dict,
    ground_truth: dict,
    scorer: EmbeddingScorer,
    contamination_hit: bool,
) -> dict:
    scores = {
        "named_specific_drug": check_drug_named(hypothesis),
        "drug_class_match": check_drug_class(hypothesis, ground_truth, scorer),
        "mechanism_match": check_mechanism(
            hypothesis, ground_truth["mechanism"], scorer
        ),
    }
    scores["total"] = sum(scores.values()) / 3
    scores["overall_similarity"] = scorer.similarity(
        hypothesis_text(hypothesis),
        ground_truth["key_claim"],
    )
    scores["genuine_rediscovery"] = not contamination_hit
    return scores


def _short_paper_id(paper_id: str) -> str:
    if paper_id.startswith("liraglutide"):
        return "liraglutide_2025"
    if paper_id.startswith("finerenone"):
        return "finerenone_2026"
    if paper_id.startswith("baricitinib"):
        return "baricitinib_2024"
    return paper_id


def print_results_table(rows: list[dict]) -> None:
    header = (
        f"{'Paper':<20}| {'Condition':<9}| {'Drug Named':<10}| "
        f"{'Drug Class':<10}| {'Mechanism':<9}| {'Overall Sim':<11}| "
        f"{'Contam.'}"
    )
    print("\n" + header)
    print("-" * len(header))
    for row in rows:
        scores = row["scores"]
        contam = "YES" if row.get("contamination_hit") else "no"
        print(
            f"{row['paper_short']:<20}| {row['condition']:<9}| "
            f"{scores['named_specific_drug']:<10.0f}| "
            f"{scores['drug_class_match']:<10.1f}| "
            f"{scores['mechanism_match']:<9.1f}| "
            f"{scores['overall_similarity']:.2f}       | {contam}"
        )


def run_paper_test(paper: dict, scorer: EmbeddingScorer) -> list[dict]:
    clear_pubmed_cache()
    paper_id = paper["paper_id"]
    research_question = paper["research_question"].strip()
    contamination_terms = list(paper["contamination_terms"])
    seed_papers = load_seed_papers(paper["seed_paper_file"])

    print(f"\n{'=' * 60}")
    print(f"Holdout: {paper_id}")
    print(f"Seed file: {paper['seed_paper_file']}")
    print(f"Ground-truth drug: {paper['ground_truth']['drug']}")
    print("=" * 60)

    verify_no_contamination(
        seed_papers, research_question, contamination_terms, paper_id,
    )
    install_eval_patches(research_question, contamination_terms)

    paper_results: list[dict] = []
    final_ideas: dict[str, dict] = {}
    for condition in ("A", "B", "C", "D"):
        print(f"\n>>> Running Condition {condition} for {paper_id}...")
        final_idea, log = run_pipeline(
            condition=condition,
            seed_papers=seed_papers,
            research_question=research_question,
            background_topics=paper.get("background_topics"),
        )

        contamination_terms_triggered = detect_contamination(
            final_idea, contamination_terms,
        )
        contamination_hit = bool(contamination_terms_triggered)
        if contamination_hit:
            print(
                f"  CONTAMINATION HIT: {contamination_terms_triggered} "
                f"— not counted as genuine rediscovery."
            )

        scores = score_rediscovery(
            final_idea,
            paper["ground_truth"],
            scorer,
            contamination_hit=contamination_hit,
        )

        entry = {
            "paper_id": paper_id,
            "paper_short": _short_paper_id(paper_id),
            "condition": condition,
            "research_question": research_question,
            "seed_paper_file": paper["seed_paper_file"],
            "ground_truth_drug": paper["ground_truth"]["drug"],
            "final_hypothesis": final_idea,
            "contamination_hit": contamination_hit,
            "contamination_terms_triggered": contamination_terms_triggered,
            "scores": scores,
            "pipeline_log": log,
        }
        paper_results.append(entry)
        final_ideas[condition] = final_idea

        print(
            f"  Scores: drug_named={scores['named_specific_drug']:.0f}, "
            f"class={scores['drug_class_match']:.1f}, "
            f"mechanism={scores['mechanism_match']:.1f}, "
            f"overall_sim={scores['overall_similarity']:.2f}, "
            f"genuine={scores['genuine_rediscovery']}"
        )

    # Pairwise condition comparison: A vs D, B vs D, C vs D (same judge).
    if "D" in final_ideas:
        print(f"\n>>> Condition comparison for {paper_id} (vs Condition D)...")
        comparisons: list[dict] = []
        for baseline in ("A", "B", "C"):
            if baseline not in final_ideas:
                continue
            cmp = print_condition_comparison(
                final_ideas[baseline], final_ideas["D"],
                seed_papers, baseline, "D",
            )
            comparisons.append(cmp)
        for entry in paper_results:
            entry["condition_comparisons_vs_D"] = comparisons

    out_path = RESULTS_DIR / f"rediscovery_{paper_id}.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(paper_results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    return paper_results


def main() -> None:
    _load_dotenv()

    if not os.environ.get("GROQ_API_KEY"):
        raise SystemExit("GROQ_API_KEY is not set.")

    holdout_papers = load_benchmark()
    scorer = EmbeddingScorer()
    all_results: list[dict] = []

    print("=" * 60)
    print("Rediscovery evaluation (MOOSE-Chem-style holdout benchmark)")
    print("=" * 60)
    print(f"Holdout papers: {len(holdout_papers)}")
    print("PubMed retrieval capped at 2023/12/31")
    print(f"Embedding model: {EMBEDDING_MODEL}")

    for paper in holdout_papers:
        paper_results = run_paper_test(paper, scorer)
        all_results.extend(paper_results)

    run_log_path = RESULTS_DIR / "run_log.json"
    pubmed_queries = [
        entry
        for row in all_results
        for entry in row["pipeline_log"]
        if entry.get("type") == "pubmed_query"
    ]
    with open(run_log_path, "w") as f:
        json.dump(
            {"pubmed_queries": pubmed_queries, "results": all_results},
            f,
            indent=2,
        )
    print(f"\nPubMed query log saved to {run_log_path}")

    print_results_table(all_results)


if __name__ == "__main__":
    main()
