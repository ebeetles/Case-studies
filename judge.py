from __future__ import annotations

"""
Judge module: scores research ideas using the OpenAI API.

Set OPENAI_API_KEY in your environment before running.
Override model with JUDGE_MODEL env var (default: gpt-5.4-mini).

Three separate LLM calls per idea (never combined into one prompt):
  1. Novelty score    (0-3)  + PubMed query for novelty literature
  2. Consistency score (gap count) + PubMed query targeting gap #1
  3. Feasibility score (1-3) + PubMed query targeting the main obstacle

Before refinement, check_retrieval_relevance() rates whether retrieved papers
address the diagnosed weakness (1-3). Score 1 raises — no silent continuation.

Composite score = novelty - (gaps * 0.5) - feasibility  [legacy — not used for beam selection]

Beam selection and condition comparison use compare_ideas() pairwise ranking
on novelty, specificity, feasibility, and overall.
"""

import os
import re

from openai import OpenAI

from retrieval import extract_pubmed_query

_DEFAULT_JUDGE = "gpt-5.4-mini"
_LEGACY_JUDGE_MODELS = frozenset({"gpt-4o-mini", "gpt-4o"})


def get_judge_model() -> str:
    """Resolve the active judge model, upgrading legacy gpt-4o defaults."""
    model = os.environ.get("JUDGE_MODEL", _DEFAULT_JUDGE).strip()
    if model in _LEGACY_JUDGE_MODELS:
        return _DEFAULT_JUDGE
    return model or _DEFAULT_JUDGE


JUDGE_MODEL = _DEFAULT_JUDGE
SEED_TRUNCATE = 200

_client: OpenAI | None = None

def _get_api_key() -> str:
    raw = os.environ.get("OPENAI_API_KEY", "")
    key = raw.strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Export your key before running:\n"
            "  export OPENAI_API_KEY='sk-...'"
        )
    if raw != key:
        os.environ["OPENAI_API_KEY"] = key
    if any(c in key for c in "\n\r\t"):
        raise RuntimeError(
            "OPENAI_API_KEY contains whitespace inside the key. "
            "Re-export on one line with no trailing newline."
        )
    return key


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=_get_api_key(), timeout=60.0)
    return _client


def _uses_gpt5_api(model: str) -> bool:
    return model.startswith("gpt-5") or model.startswith("o")


def _chat_completion(
    client: OpenAI,
    *,
    model: str,
    messages: list[dict],
    temperature: float = 0,
    max_output: int | None = None,
):
    """Call chat.completions with parameters compatible with the target model."""
    params: dict = {"model": model, "messages": messages}
    if not _uses_gpt5_api(model):
        params["temperature"] = temperature
    if max_output is not None:
        token_key = "max_completion_tokens" if _uses_gpt5_api(model) else "max_tokens"
        params[token_key] = max_output
    return client.chat.completions.create(**params)


def check_judge_ready() -> None:
    """Verify OpenAI is reachable. Raises on failure."""
    client = _get_client()
    r = _chat_completion(
        client,
        model=get_judge_model(),
        messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        max_output=5,
        temperature=0,
    )
    if not r.choices[0].message.content:
        raise RuntimeError("OpenAI returned an empty response during connectivity check.")


def _call_judge(prompt: str) -> str:
    """Call the judge model. Raises on failure."""
    client = _get_client()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            r = _chat_completion(
                client,
                model=get_judge_model(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            text = r.choices[0].message.content
            if text and text.strip():
                return text.strip()
            raise RuntimeError("OpenAI returned an empty message.")
        except Exception as e:
            last_err = e
            cause = getattr(e, "__cause__", None)
            detail = f"{type(e).__name__}: {e}"
            if cause:
                detail += f" (cause: {type(cause).__name__}: {cause})"
            print(f"  [judge] OpenAI error (attempt {attempt+1}/3): {detail}")
    raise RuntimeError(f"Judge failed after 3 attempts: {last_err}") from last_err


def _parse_rating_1_to_3(text: str, label: str) -> int:
    """Parse a 1-3 rating from the first line of a judge response."""
    first_char = text.strip()[0] if text.strip() else ""
    if first_char in ("1", "2", "3"):
        return int(first_char)
    match = re.search(r"[123]", text)
    if match:
        return int(match.group())
    raise RuntimeError(
        f"Could not parse {label} (expected 1, 2, or 3):\n{text[:500]}"
    )


def _count_yes_answers(text: str) -> int:
    """Count numbered YES answers (handles markdown like '1. **YES**')."""
    count = 0
    for line in text.splitlines():
        if re.match(r"^\s*\d+[.)]", line) and re.search(r"\byes\b", line, re.IGNORECASE):
            count += 1
    return min(count, 3)


# ── Scoring calls (one per dimension) ────────────────────────────────────────

def score_novelty(idea: dict, seed_papers: list[dict]) -> tuple[int, str]:
    seed_lines = "\n".join(
        f"- {p['title']}: {p.get('abstract','')[:SEED_TRUNCATE]}"
        for p in seed_papers
    )

    prompt = f"""You are a critical scientific reviewer.

Here are 5 existing research papers in Alzheimer's disease:
{seed_lines}

Here is a new research idea:
Problem: {idea['problem']}
Method: {idea['method']}
Contribution: {idea['contribution']}

Answer YES or NO for each question, then explain in one sentence:
1. Is the Problem genuinely different from the problems addressed in the existing papers?
2. Is the Method genuinely different from the methods used in the existing papers?
3. Is the Contribution genuinely different from what the existing papers claim to achieve?

On the last line, write exactly one PubMed search line to find papers on more novel
approaches related to this idea's method in Alzheimer disease:
PubMed query: <3-5 concrete biomedical terms, no full sentences>"""

    text = _call_judge(prompt)
    return _count_yes_answers(text), text


def score_consistency(idea: dict) -> tuple[int, str]:
    prompt = f"""You are a critical scientific reviewer.

Research idea:
Problem: {idea['problem']}
Method: {idea['method']}

List the top 3 most serious logical gaps — specific reasons why this Method might NOT actually solve this Problem. Number each gap 1, 2, 3.
Be specific. If there are genuinely no gaps, say "No gaps identified."

After the gaps, add exactly one line with PubMed search terms to find papers that
would help a researcher address gap #1 (not gaps 2 or 3):
PubMed query: <3-5 concrete biomedical terms targeting the scientific issue in gap #1, no full sentences>"""

    text = _call_judge(prompt)
    return _count_gaps(text), text


def _count_gaps(text: str) -> int:
    if "no gaps identified" in text.lower():
        return 0
    matches = re.findall(
        r"^\s*(?:\*{0,2})([1-3])(?:\*{0,2})[.)]\s",
        text,
        re.MULTILINE,
    )
    return len(matches)


def score_feasibility(idea: dict) -> tuple[int, str]:
    prompt = f"""You are a critical scientific reviewer.

Research idea:
Method: {idea['method']}
Contribution: {idea['contribution']}

What is the single biggest practical obstacle to executing this research in a real laboratory or clinical setting?

Rate the severity:
1 = minor obstacle, addressable with standard methods
2 = moderate obstacle, requires significant resources or time
3 = major obstacle, currently infeasible

Reply with ONLY the number (1, 2, or 3) on the first line, then explain in one sentence on the second line.

On the third line, add PubMed search terms to find papers that help overcome this obstacle:
PubMed query: <3-5 concrete biomedical terms, no full sentences>"""

    text = _call_judge(prompt)
    return _parse_rating_1_to_3(text, "feasibility score"), text


def composite_score(novelty: int, gaps: int, feasibility: int) -> float:
    return novelty - (gaps * 0.5) - feasibility


def score_idea(idea: dict, seed_papers: list[dict]) -> dict:
    """Legacy absolute scoring — retained for reference, not used in the pipeline."""
    print(f"    [judge] Scoring with {get_judge_model()}...")
    print("    [judge] Scoring novelty...")
    novelty,     novelty_text     = score_novelty(idea, seed_papers)
    print("    [judge] Scoring consistency...")
    gaps,        consistency_text = score_consistency(idea)
    print("    [judge] Scoring feasibility...")
    feasibility, feasibility_text = score_feasibility(idea)

    comp = composite_score(novelty, gaps, feasibility)

    return {
        "novelty":           novelty,
        "novelty_text":      novelty_text,
        "gaps":              gaps,
        "consistency_text":  consistency_text,
        "feasibility":       feasibility,
        "feasibility_text":  feasibility_text,
        "composite":         comp,
    }


PAIRWISE_DIMENSIONS = ("novelty", "specificity", "feasibility", "overall")


def _format_idea_block(label: str, idea: dict) -> str:
    return (
        f"Idea {label}:\n"
        f"Problem: {idea['problem']}\n"
        f"Method: {idea['method']}\n"
        f"Contribution: {idea['contribution']}"
    )


def _parse_pairwise_response(
    text: str, label_a: str, label_b: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """Parse dimension winners and justifications from a pairwise judge response."""
    winners: dict[str, str] = {}
    justifications: dict[str, str] = {}

    for dim in PAIRWISE_DIMENSIONS:
        winner_re = re.compile(
            rf"^\s*{dim}\s*:\s*({re.escape(label_a)}|{re.escape(label_b)})\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        just_re = re.compile(
            rf"^\s*{dim}_justification\s*:\s*(.+)$",
            re.IGNORECASE | re.MULTILINE,
        )
        m = winner_re.search(text)
        if not m:
            raise RuntimeError(
                f"Pairwise response missing '{dim}:' line:\n{text[:500]}"
            )
        winners[dim] = m.group(1).strip()
        jm = just_re.search(text)
        if not jm:
            raise RuntimeError(
                f"Pairwise response missing '{dim}_justification:' line:\n{text[:500]}"
            )
        justifications[dim] = jm.group(1).strip()

    return winners, justifications


def compare_ideas(
    idea_a: dict,
    idea_b: dict,
    seed_papers: list[dict],
    label_a: str = "A",
    label_b: str = "B",
) -> dict:
    """
    Pairwise comparison of two ideas on novelty, specificity, feasibility, overall.

    Returns dict with winners (per dimension, using label_a/label_b) and
    one-sentence justifications for each dimension.
    """
    seed_lines = "\n".join(
        f"- {p['title']}: {p.get('abstract', '')[:SEED_TRUNCATE]}"
        for p in seed_papers
    )
    prompt = f"""You are a critical scientific reviewer comparing two Alzheimer's disease drug repurposing hypotheses.

Existing seed literature:
{seed_lines}

{_format_idea_block(label_a, idea_a)}

{_format_idea_block(label_b, idea_b)}

Compare the two ideas on four dimensions. For each, pick the BETTER idea ({label_a} or {label_b}) and give exactly one sentence of justification.

NOVELTY: Which idea is more genuinely novel relative to the seed literature — not just a rephrasing of known approaches?
{label_a} or {label_b}
NOVELTY_JUSTIFICATION: one sentence

SPECIFICITY: Which idea names more concrete actionable targets (specific drugs, pathways, mechanisms) rather than vague general strategies like "multi-omics" or "systems biology" without naming what to test?
{label_a} or {label_b}
SPECIFICITY_JUSTIFICATION: one sentence

FEASIBILITY: Which idea is more feasible to execute in a real laboratory or clinical setting with existing tools and resources?
{label_a} or {label_b}
FEASIBILITY_JUSTIFICATION: one sentence

OVERALL: Which is the better drug repurposing hypothesis overall?
{label_a} or {label_b}
OVERALL_JUSTIFICATION: one sentence

Reply in exactly this format (dimension labels uppercase, winner is {label_a} or {label_b} only):
NOVELTY: <{label_a} or {label_b}>
NOVELTY_JUSTIFICATION: <one sentence>
SPECIFICITY: <{label_a} or {label_b}>
SPECIFICITY_JUSTIFICATION: <one sentence>
FEASIBILITY: <{label_a} or {label_b}>
FEASIBILITY_JUSTIFICATION: <one sentence>
OVERALL: <{label_a} or {label_b}>
OVERALL_JUSTIFICATION: <one sentence>"""

    print(f"    [judge] Pairwise: {label_a} vs {label_b}...")
    text = _call_judge(prompt)
    winners, justifications = _parse_pairwise_response(text, label_a, label_b)
    return {"winners": winners, "justifications": justifications, "raw": text}


def _ranking_from_wins(dimension_wins: dict[str, int]) -> dict:
    """Build a ranking summary dict used for beam selection and logging."""
    return {
        "dimension_wins": dimension_wins,
        "total_wins": dimension_wins.get("overall", 0),
        "total_dimension_wins": sum(
            dimension_wins.get(d, 0) for d in ("novelty", "specificity", "feasibility")
        ),
    }


def _ranking_to_scores(ranking: dict) -> dict:
    """Map pairwise ranking to a scores dict for logging / graph compatibility."""
    wins = ranking["dimension_wins"]
    return {
        "novelty":     wins.get("novelty", 0),
        "specificity": wins.get("specificity", 0),
        "feasibility": wins.get("feasibility", 0),
        "overall_wins": wins.get("overall", 0),
        "total_wins":  ranking["total_wins"],
        "composite":   ranking["total_wins"],
    }


def rank_candidates_pairwise(
    ideas: list[dict],
    seed_papers: list[dict],
) -> tuple[list[tuple[dict, dict]], list[dict]]:
    """
    Round-robin pairwise comparison of all candidates.

    Returns ranked list of (idea, ranking_dict) sorted by overall wins then
    total dimension wins, and a log of every pairwise comparison.
    """
    n = len(ideas)
    labels = [str(i + 1) for i in range(n)]
    dimension_wins = [
        {d: 0 for d in PAIRWISE_DIMENSIONS}
        for _ in range(n)
    ]
    comparisons: list[dict] = []

    for i in range(n):
        for j in range(i + 1, n):
            result = compare_ideas(
                ideas[i], ideas[j], seed_papers, labels[i], labels[j],
            )
            record = {
                "idea_a_id": i + 1,
                "idea_b_id": j + 1,
                "winners": result["winners"],
                "justifications": result["justifications"],
            }
            comparisons.append(record)

            for dim in PAIRWISE_DIMENSIONS:
                winner_label = result["winners"][dim]
                if winner_label.lower() == labels[i].lower():
                    dimension_wins[i][dim] += 1
                elif winner_label.lower() == labels[j].lower():
                    dimension_wins[j][dim] += 1
                else:
                    raise RuntimeError(
                        f"Unexpected winner label '{winner_label}' "
                        f"for {labels[i]} vs {labels[j]}"
                    )

    ranked: list[tuple[dict, dict]] = []
    for i, idea in enumerate(ideas):
        ranking = _ranking_from_wins(dimension_wins[i])
        ranked.append((idea, ranking))

    ranked.sort(
        key=lambda x: (x[1]["total_wins"], x[1]["total_dimension_wins"]),
        reverse=True,
    )
    return ranked, comparisons


def pairwise_pick_winner(
    idea_a: dict,
    idea_b: dict,
    seed_papers: list[dict],
    label_a: str = "parent",
    label_b: str = "refined",
) -> tuple[dict, dict, dict]:
    """
    Compare two ideas head-to-head; return (winning_idea, winning_ranking, comparison_log).
    """
    result = compare_ideas(idea_a, idea_b, seed_papers, label_a, label_b)
    comparison = {
        "idea_a_label": label_a,
        "idea_b_label": label_b,
        "winners": result["winners"],
        "justifications": result["justifications"],
    }
    def _is(label: str, winner: str) -> bool:
        return winner.lower() == label.lower()

    if _is(label_a, result["winners"]["overall"]):
        wins = {d: (1 if _is(label_a, result["winners"][d]) else 0) for d in PAIRWISE_DIMENSIONS}
        return idea_a, _ranking_from_wins(wins), comparison
    wins = {d: (1 if _is(label_b, result["winners"][d]) else 0) for d in PAIRWISE_DIMENSIONS}
    return idea_b, _ranking_from_wins(wins), comparison


def diagnose_weakness(
    idea: dict,
    weakness_type: str,
    seed_papers: list[dict],
) -> str:
    """Return a short description of the idea's weakness on the given dimension."""
    seed_lines = "\n".join(
        f"- {p['title']}: {p.get('abstract', '')[:SEED_TRUNCATE]}"
        for p in seed_papers
    )
    prompts = {
        "novelty": (
            "What is the main novelty weakness of this hypothesis relative to "
            "existing Alzheimer's disease literature? Be specific in 2-3 sentences."
        ),
        "consistency": (
            "What is the single most serious logical gap — a specific reason why "
            "the Method might NOT actually solve the Problem? Be specific in 2-3 sentences."
        ),
        "feasibility": (
            "What is the single biggest practical obstacle to executing this research "
            "in a real laboratory? Be specific in 2-3 sentences."
        ),
    }
    instruction = prompts.get(weakness_type)
    if not instruction:
        raise RuntimeError(f"Unknown weakness_type: {weakness_type}")

    prompt = f"""You are a critical scientific reviewer.

Seed literature:
{seed_lines}

Hypothesis:
Problem: {idea['problem']}
Method: {idea['method']}
Contribution: {idea['contribution']}

{instruction}"""

    return _call_judge(prompt)


def identify_weakness_from_ranking(
    ranking: dict,
    weakness_history: list[str] | None = None,
) -> str:
    """
    Pick weakest dimension from pairwise win counts, excluding already-targeted dims.

    Maps specificity → consistency for Condition C refinement targeting.
    """
    if weakness_history is None:
        weakness_history = []

    dim_wins = ranking["dimension_wins"]
    pairwise_to_weakness = (
        ("novelty", "novelty"),
        ("specificity", "consistency"),
        ("feasibility", "feasibility"),
    )
    candidates = [
        (weakness_dim, dim_wins.get(pairwise_dim, 0))
        for pairwise_dim, weakness_dim in pairwise_to_weakness
    ]

    untargeted = [(dim, wins) for dim, wins in candidates if dim not in weakness_history]
    if untargeted:
        untargeted.sort(key=lambda x: x[1])
        chosen = untargeted[0][0]
    else:
        candidates.sort(key=lambda x: x[1])
        chosen = candidates[0][0]

    print(f"    [judge] Weakness selected: '{chosen}' (history: {weakness_history})")
    return chosen


def print_condition_comparison(
    idea_a: dict,
    idea_b: dict,
    seed_papers: list[dict],
    label_a: str,
    label_b: str,
) -> dict:
    """Compare two final condition ideas and print results clearly."""
    result = compare_ideas(idea_a, idea_b, seed_papers, label_a, label_b)
    print(f"\n  {label_a} vs {label_b}:")
    for dim in PAIRWISE_DIMENSIONS:
        winner = result["winners"][dim]
        just = result["justifications"][dim]
        print(f"    {dim.capitalize():12s} → {winner}  ({just})")
    print(f"    {'Overall winner':12s} → {result['winners']['overall']}")
    return {
        "comparison": f"{label_a}_vs_{label_b}",
        "winners": result["winners"],
        "justifications": result["justifications"],
    }


def check_retrieval_relevance(
    idea: dict,
    weakness_feedback: str,
    retrieved_papers: list[dict],
    is_ood: bool = False,
) -> int:
    """
    Rate how well retrieved papers address the diagnosed weakness (1-3).

    When is_ood=False (Condition B): asks about direct relevance; raises on score 1.
    When is_ood=True  (Condition C): asks about analogical relevance (adjacent-field
      inspiration); never raises — OOD papers are expected to score low on direct
      relevance by design, and a score of 1 here is informational, not a failure.
    """
    if not retrieved_papers:
        raise RuntimeError("check_retrieval_relevance called with no papers.")

    papers_text = "\n".join(
        f"- {p['title']}: {p.get('abstract', '')[:150]}"
        for p in retrieved_papers
    )
    feedback = weakness_feedback[:400]

    if is_ood:
        prompt = f"""A research hypothesis has the following weakness:
"{feedback}"

These papers are from ADJACENT fields (not Alzheimer's disease) and were retrieved
as potential inspiration for addressing the weakness by analogy:
{papers_text}

On a scale of 1-3, how useful could these papers be as analogical inspiration
for fixing the weakness — even if they are from a completely different disease area?
1 = no analogical value (unrelated problem/solution structure)
2 = some analogical value (similar problem structure, different context)
3 = strong analogical value (directly applicable principle from adjacent field)

Reply with only the number."""
    else:
        prompt = f"""The following weakness was identified in a research hypothesis:
"{feedback}"

These papers were retrieved to address it:
{papers_text}

On a scale of 1-3, how relevant are these papers to addressing the weakness?
1 = not relevant at all
2 = somewhat relevant
3 = directly relevant

Reply with only the number."""

    label = "OOD analogical relevance" if is_ood else "retrieval relevance"
    print(f"    [judge] Checking {label}...")
    text = _call_judge(prompt)
    score = _parse_rating_1_to_3(text, label)
    print(f"    [judge] {label.capitalize()}: {score}/3")
    if not is_ood and score == 1:
        raise RuntimeError(
            "Retrieved papers are not relevant to the diagnosed weakness "
            f"(relevance {score}/3). Query or retrieval failed."
        )
    return score


def identify_weakness(scores: dict, weakness_history: list[str] | None = None) -> str:
    """
    Return the weakest dimension not yet in weakness_history.

    Priority order: novelty (if <2), consistency (if gaps>2), feasibility (if >1).
    Scores are negated so lower = worse rank, enabling a uniform sort.
    If all weak dimensions were already targeted, fall back to worst overall.
    If no dimension is weak, default to novelty to push it further.
    """
    if weakness_history is None:
        weakness_history = []

    candidates: list[tuple[str, float]] = []
    if scores["novelty"] < 2:
        candidates.append(("novelty", float(scores["novelty"])))
    if scores["gaps"] > 2:
        candidates.append(("consistency", -float(scores["gaps"])))
    if scores["feasibility"] > 1:
        candidates.append(("feasibility", -float(scores["feasibility"])))

    untargeted = [(dim, s) for dim, s in candidates if dim not in weakness_history]

    if untargeted:
        untargeted.sort(key=lambda x: x[1])
        chosen = untargeted[0][0]
    elif candidates:
        candidates.sort(key=lambda x: x[1])
        chosen = candidates[0][0]
    else:
        chosen = "novelty"

    print(f"    [judge] Weakness selected: '{chosen}' (history: {weakness_history})")
    return chosen


def generate_ood_query(
    idea: dict,
    weakness_type: str,
    weakness_feedback: str,
) -> str:
    """
    Generate a PubMed search query targeting analogous solutions from OUTSIDE
    the Alzheimer's disease literature.

    Raises if the returned query contains 'Alzheimer'.
    """
    feedback = weakness_feedback[:400]
    prompt = f"""A research hypothesis about Alzheimer's disease has a weakness in its {weakness_type} dimension.

The hypothesis:
Problem: {idea['problem']}
Method: {idea['method']}
Contribution: {idea['contribution']}

The specific weakness is:
"{feedback}"

Your task is to generate a PubMed search query that finds papers from OUTSIDE the Alzheimer's disease literature that have solved an analogous problem in a different disease or biological context.

You MUST search within exactly one of these adjacent domains:
cardiology, rheumatology, metabolic disease, oncology, pulmonology.

Rules:
- Do NOT include "Alzheimer's" or "Alzheimer" or any variant in the query
- Do NOT name specific drugs from the hypothesis
- Do NOT search for the specific mechanism already named in the hypothesis
- DO search for how analogous problems were solved in one of the five allowed domains
- The goal is unexpected inspiration, not confirmation of existing approaches

Good examples by domain:
- cardiology: "cardiac fibrosis aldosterone inflammation macrophage resolution"
- rheumatology: "rheumatoid arthritis synovial cytokine macrophage reprogramming"
- metabolic disease: "type 2 diabetes insulin resistance inflammatory cytokine signalling"
- oncology: "tumor associated macrophage cytokine microenvironment reprogramming"
- pulmonology: "pulmonary fibrosis oxidative stress macrophage activation"

Bad examples (never produce queries like these):
- any query containing Alzheimer / Alzheimer's / AD dementia
- "heart failure treatment guidelines review" (too generic, not analogous)
- "baricitinib rheumatoid arthritis clinical trial" (names a specific drug)
- "liraglutide semaglutide glycaemic control" (names holdout-class drugs)

Generate ONE search query of 5-8 words following these rules.
Reply with ONLY the query, nothing else."""

    print("    [judge] Generating OOD retrieval query...")
    text = _call_judge(prompt)
    query = text.strip().strip('"\'').rstrip(".")
    if "alzheimer" in query.lower():
        raise RuntimeError(
            f"OOD query contains 'Alzheimer' despite instructions: '{query}'"
        )
    print(f"    [judge] OOD query: '{query}'")
    return query
