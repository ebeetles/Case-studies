from __future__ import annotations

"""
Main entry point for the Retrieval-Guided Beam Search case study.

Runs experimental conditions and saves results to results/run_log.json.
Final condition comparison uses pairwise judging (A vs C, B vs C).
"""

import json
import os
from pathlib import Path

from pipeline import run_pipeline, print_c_verification
from graphs   import generate_all_graphs
from judge    import print_condition_comparison
from seed_papers import SEED_PAPERS

RESULTS_DIR = "results"


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


def _sanitize_env() -> None:
    for var in ("OPENAI_API_KEY", "GROQ_API_KEY", "JUDGE_MODEL", "GENERATOR_MODEL"):
        if var in os.environ:
            os.environ[var] = os.environ[var].strip()


def save_logs(logs: list[list[dict]], condition_comparisons: list[dict]):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    combined: list[dict] = []
    for log in logs:
        combined.extend(log)
    combined.extend(condition_comparisons)
    path = os.path.join(RESULTS_DIR, "run_log.json")
    with open(path, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"Run log saved to {path} ({len(combined)} entries)")


if __name__ == "__main__":
    _load_dotenv()
    _sanitize_env()

    print("=" * 60)
    print("Retrieval-Guided Beam Search: Alzheimer's Drug Repurposing")
    print("=" * 60)

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set.\n"
            "  export OPENAI_API_KEY='sk-...'\n"
            "  Or put it in a .env file in the project root."
        )
    if not os.environ.get("GROQ_API_KEY"):
        raise SystemExit(
            "GROQ_API_KEY is not set.\n"
            "  export GROQ_API_KEY='gsk_...'\n"
            "  Or put it in a .env file in the project root."
        )

    from judge import JUDGE_MODEL, check_judge_ready
    from retrieval import check_retrieval_ready
    from generator import GENERATOR_MODEL, check_generator_ready

    print("\nPreflight checks...")
    check_judge_ready()
    print(f"  Judge:     {JUDGE_MODEL} (OpenAI)")
    check_retrieval_ready()
    print("  Retrieval: PubMed")
    check_generator_ready()
    print(f"  Generator: {GENERATOR_MODEL} (Groq)")

    print("\n>>> Running Condition A: Baseline")
    result_a, log_a = run_pipeline(condition="A")

    print("\n>>> Running Condition B: Generic RAG")
    result_b, log_b = run_pipeline(condition="B")

    print("\n>>> Running Condition C: Full Pipeline (targeted gap-filling)")
    result_c, log_c = run_pipeline(condition="C")

    print("\n" + "=" * 60)
    print("FINAL CONDITION COMPARISON (pairwise)")
    print("=" * 60)

    comparison_logs: list[dict] = []

    print("\n--- Condition B vs Condition C ---")
    b_vs_c = print_condition_comparison(
        result_b, result_c, SEED_PAPERS, "B", "C",
    )
    comparison_logs.append({
        "type": "condition_comparison",
        "comparison": b_vs_c["comparison"],
        "winners": b_vs_c["winners"],
        "justifications": b_vs_c["justifications"],
    })

    print("\n--- Condition A vs Condition C ---")
    a_vs_c = print_condition_comparison(
        result_a, result_c, SEED_PAPERS, "A", "C",
    )
    comparison_logs.append({
        "type": "condition_comparison",
        "comparison": a_vs_c["comparison"],
        "winners": a_vs_c["winners"],
        "justifications": a_vs_c["justifications"],
    })

    save_logs([log_a, log_b, log_c], comparison_logs)

    print("\n" + "=" * 60)
    print("FINAL IDEAS")
    print("=" * 60)

    print("\nCondition A (Baseline):")
    print(f"  Problem:      {result_a['problem']}")
    print(f"  Method:       {result_a['method']}")
    print(f"  Contribution: {result_a['contribution']}")

    print("\nCondition B (Generic RAG):")
    print(f"  Problem:      {result_b['problem']}")
    print(f"  Method:       {result_b['method']}")
    print(f"  Contribution: {result_b['contribution']}")

    print("\nCondition C (Full Pipeline):")
    print(f"  Problem:      {result_c['problem']}")
    print(f"  Method:       {result_c['method']}")
    print(f"  Contribution: {result_c['contribution']}")

    generate_all_graphs(log_a, log_b, log_c)

    print_c_verification(log_c)

    print("\nDone. Graphs saved to results/")
