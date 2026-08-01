from __future__ import annotations

"""
Pipeline module: implements the three experimental conditions.

  Condition A — Baseline (no retrieval, no iteration)
  Condition B — Generic RAG (fresh PubMed query each retrieval call)
  Condition C — Full pipeline with targeted gap-filling fixes
  Condition D — Structured Abstraction Before Retrieval (cross-domain analogy)

Beam selection uses pairwise comparison (novelty, specificity, feasibility, overall)
instead of absolute scoring. Legacy score_idea() is not called.
"""

import re

from generator  import (
    generate_candidates,
    refine_candidate,
    abstract_problem,
    cross_domain_query,
    map_cross_domain,
)
from judge      import (
    rank_candidates_pairwise,
    pairwise_pick_winner,
    identify_weakness_from_ranking,
    diagnose_weakness,
    check_retrieval_relevance,
    generate_ood_query,
    _ranking_to_scores,
)
from retrieval  import retrieve_papers, RetrievalTracker
from seed_papers import SEED_PAPERS

BEAM_WIDTH   = 2
N_CANDIDATES = 5

GENERIC_QUERY = "Alzheimer disease therapeutic target drug repurposing"

_DEFAULT_B_RESEARCH_QUESTION = (
    "What existing FDA-approved drug, originally developed "
    "for a non-Alzheimer's indication, could address the "
    "metabolic and inflammatory dysfunction described in "
    "these papers, and through what specific mechanism?"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ranking_summary(ranking: dict) -> dict:
    wins = ranking["dimension_wins"]
    return {
        "novelty_wins":     wins.get("novelty", 0),
        "specificity_wins": wins.get("specificity", 0),
        "feasibility_wins": wins.get("feasibility", 0),
        "overall_wins":     wins.get("overall", 0),
        "total_wins":       ranking["total_wins"],
    }


def _make_entry(
    condition: str,
    round_num: int,
    candidate_id: int,
    idea: dict,
    ranking: dict,
    pairwise_comparisons: list[dict] | None = None,
    weakness_targeted: str | None = None,
    targeted_query: str | None = None,
    retrieved_papers: list[dict] | None = None,
    retrieval_relevance: int | None = None,
    weakness_history: list[str] | None = None,
    weakness_targeted_this_round: str | None = None,
    ood_query_used: str | None = None,
    duplicate_papers_filtered: list[str] | None = None,
    idea_before_refinement: dict | None = None,
    idea_after_refinement: dict | None = None,
    ranking_before: dict | None = None,
    ranking_after: dict | None = None,
) -> dict:
    return {
        "condition":                    condition,
        "round":                        round_num,
        "candidate_id":                 candidate_id,
        "idea":                         idea,
        "ranking":                      ranking,
        "scores":                       _ranking_to_scores(ranking),
        "pairwise_comparisons":         pairwise_comparisons or [],
        "weakness_targeted":            weakness_targeted,
        "targeted_query":               targeted_query,
        "retrieved_papers":             retrieved_papers,
        "retrieval_relevance":          retrieval_relevance,
        "weakness_history":             weakness_history,
        "weakness_targeted_this_round": weakness_targeted_this_round,
        "ood_query_used":               ood_query_used,
        "duplicate_papers_filtered":    duplicate_papers_filtered,
        "idea_before_refinement":       idea_before_refinement,
        "idea_after_refinement":        idea_after_refinement,
        "ranking_before":               ranking_before,
        "ranking_after":                ranking_after,
    }


def _top_n(
    candidates: list[tuple[dict, dict]], n: int,
) -> list[tuple[dict, dict]]:
    return sorted(
        candidates,
        key=lambda x: (x[1]["total_wins"], x[1]["total_dimension_wins"]),
        reverse=True,
    )[:n]


_QUERY_STOPWORDS = frozenset({
    "about", "address", "after", "also", "and", "are", "been", "being",
    "between", "brain", "combination", "complex", "contribution", "could",
    "described", "development", "disease", "drug", "drugs", "effective",
    "efficacy", "existing", "for", "from", "have", "hindered", "hypothesis",
    "identification", "improve", "indication", "inhibitor", "into",
    "interplay", "investigate", "investigated", "limited", "mechanism",
    "method", "modulate", "more", "must", "named", "necessitates",
    "neurodegeneration", "non", "not", "novel", "originally", "other",
    "pathogenesis", "pathology", "pathway", "potential", "problem",
    "propose", "proposed", "repurposing", "research", "specific", "strategies",
    "such", "target", "targeted", "test", "testing", "than", "that",
    "therapeutic", "the", "their", "these", "this", "through", "using",
    "validate", "validated", "validation", "what", "which", "will", "with",
    "would", "alzheimer",
})


def _clean_query_text(text: str, max_len: int = 120) -> str:
    q = re.sub(r"\s+", " ", text).strip()
    return q[:max_len]


def _strip_alzheimer_phrases(text: str) -> str:
    text = re.sub(r"\bAlzheimer(?:'s)?\s+disease\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brelated\s+disorders\b", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _keywords_from_text(text: str, max_words: int = 10) -> str:
    words = re.findall(r"[A-Za-z][\w-]*", text)
    kept: list[str] = []
    seen: set[str] = set()
    for word in words:
        key = word.lower()
        if key in _QUERY_STOPWORDS or key in seen or len(key) <= 2:
            continue
        seen.add(key)
        kept.append(word)
        if len(kept) == max_words:
            break
    return " ".join(kept)


def _derive_condition_b_r1_query(
    seed_papers: list[dict],
    research_question: str,
    background_topics: list[str] | None = None,
) -> str:
    """Round 1 Condition B query from seed topics and the research question."""
    if background_topics:
        topic_text = " ".join(background_topics)
    else:
        title_bits: list[str] = []
        for paper in seed_papers[:3]:
            title_bits.append(
                _strip_alzheimer_phrases(paper["title"].split(":")[0].strip())
            )
        topic_text = _keywords_from_text(" ".join(title_bits), max_words=8)

    rq_hint = _keywords_from_text(research_question, max_words=5)
    if not rq_hint:
        rq_hint = "FDA-approved drug repurposing mechanism"
    return _clean_query_text(f"{topic_text} {rq_hint} drug repurposing")


def _derive_condition_b_refine_query(idea: dict) -> str:
    """Refinement-round Condition B query from the candidate Problem and Method."""
    method = _strip_alzheimer_phrases(idea.get("method", ""))
    problem = _strip_alzheimer_phrases(idea.get("problem", ""))

    # Method carries the drug, target, and model — weight it heavily.
    method_kw = _keywords_from_text(method, max_words=8).split()
    problem_kw = _keywords_from_text(problem, max_words=4).split()
    seen = {w.lower() for w in method_kw}
    extra = [w for w in problem_kw if w.lower() not in seen][:2]
    keywords = " ".join(method_kw + extra)

    if not keywords:
        keywords = "repurposing mechanism preclinical"
    return _clean_query_text(f"{keywords} repurposing")


def _make_unique_query(base: str, used_queries: set[str]) -> str:
    """Return a query string not yet used in this run."""
    query = _clean_query_text(base)
    if not query:
        query = "drug repurposing neuroinflammation metabolic"
    if query not in used_queries:
        used_queries.add(query)
        return query
    suffix = 2
    while True:
        candidate = _clean_query_text(f"{query} mechanism {suffix}")
        if candidate not in used_queries:
            used_queries.add(candidate)
            return candidate
        suffix += 1


def _log_pubmed_query(
    log: list[dict],
    condition: str,
    round_num: int,
    candidate_id: int,
    query: str,
) -> None:
    log.append({
        "condition": condition,
        "round": round_num,
        "candidate_id": candidate_id,
        "type": "pubmed_query",
        "pubmed_query": query,
    })


def _refinement_context_b(
    idea: dict,
    used_queries: set[str],
    log: list[dict],
    condition: str,
    round_num: int,
    candidate_id: int,
) -> tuple[str | None, str, list[dict], str]:
    """Fresh Condition B retrieval for one refinement step."""
    base_query = _derive_condition_b_refine_query(idea)
    query = _make_unique_query(base_query, used_queries)
    _log_pubmed_query(log, condition, round_num, candidate_id, query)
    print(f"  [{condition}] PubMed query: '{query[:70]}'")
    gap_papers = retrieve_papers(query, n=3)
    return (
        None,
        query,
        gap_papers,
        "No targeted weakness identified (generic RAG).",
    )


# ── Post-run verification (Condition C) ──────────────────────────────────────

def print_c_verification(log_c: list[dict]) -> None:
    """Print verification trace for the three Condition C fixes."""
    print("\n" + "=" * 60)
    print("CONDITION C VERIFICATION")
    print("=" * 60)

    refinement_entries = [e for e in log_c if e.get("ood_query_used")]

    r3_entries = [e for e in refinement_entries if e["round"] == 3]
    fix1_pass = True
    fix1_notes: list[str] = []

    for r3 in r3_entries:
        history = r3.get("weakness_history") or []
        targeted = r3.get("weakness_targeted")
        note = f"R3 targeted '{targeted}', R2 history was {history}"
        fix1_notes.append(note)
        if targeted in history:
            fix1_pass = False

    all_targeted = [e.get("weakness_targeted") for e in refinement_entries]
    print(f"\n[Fix 1] Weakness dimensions targeted each round: {all_targeted}")
    for note in fix1_notes:
        print(f"  {note}")
    if fix1_pass:
        print("  PASS — Round 3 targeted a different dimension than Round 2 for same candidate")
    else:
        print("  FAIL — Round 3 repeated a dimension already in candidate's history!")

    seen_titles: set[str] = set()
    duplicates: list[str] = []
    for e in refinement_entries:
        for paper in (e.get("retrieved_papers") or []):
            key = paper["title"].strip().lower()
            if key in seen_titles:
                duplicates.append(paper["title"])
            else:
                seen_titles.add(key)

    print(f"\n[Fix 2] Duplicate paper titles across rounds: {duplicates or 'none'}")
    if not duplicates:
        print("  PASS — no duplicate papers across rounds")
    else:
        print(f"  FAIL — {len(duplicates)} duplicate(s) detected!")

    alz_titles: list[str] = []
    for e in refinement_entries:
        for paper in (e.get("retrieved_papers") or []):
            if "alzheimer" in paper["title"].lower():
                alz_titles.append(paper["title"])

    print(f"\n[Fix 3] Papers with 'Alzheimer' in title from OOD queries: {len(alz_titles)}")
    if not alz_titles:
        print("  PASS — no retrieved papers contain 'Alzheimer' in title")
    else:
        print("  FAIL — OOD retrieval returned Alzheimer papers:")
        for t in alz_titles:
            print(f"    - {t}")

    print("\n--- Full Retrieval Trace ---")
    for e in refinement_entries:
        print(f"\nRound {e['round']}, Candidate {e['candidate_id']}:")
        print(f"  History before this round : {e.get('weakness_history', [])}")
        print(f"  Weakness targeted         : {e.get('weakness_targeted')}")
        print(f"  OOD query                 : {e.get('ood_query_used')}")
        filtered = e.get("duplicate_papers_filtered") or []
        if filtered:
            print(f"  Filtered (dedup)          : {filtered}")
        print("  Papers retrieved:")
        for p in (e.get("retrieved_papers") or []):
            print(f"    - {p['title']}")
        print(f"  Ranking before: {e.get('ranking_before')}")
        print(f"  Ranking after : {e.get('ranking_after')}")

    print("\n" + "=" * 60)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(
    condition: str,
    seed_papers: list[dict] | None = None,
    research_question: str | None = None,
    background_topics: list[str] | None = None,
    temperature: float = 0,
    max_rounds: int | None = None,
) -> tuple[dict, list[dict]]:
    """
    max_rounds (condition C only): stop after round 1 or round 2 instead of the
    full 3-round refinement. None (default) runs all 3 rounds, preserving
    existing behavior. Used for probing the exploration/exploitation tradeoff.
    """
    assert condition in ("A", "B", "C", "D"), f"Unknown condition: {condition}"
    papers = seed_papers if seed_papers is not None else SEED_PAPERS
    rq = (research_question or _DEFAULT_B_RESEARCH_QUESTION).strip()

    if condition == "D":
        return run_condition_d(papers)

    log: list[dict] = []
    used_b_queries: set[str] = set()

    print(f"\n[{condition}] Round 1: generating candidates...")

    if condition == "A":
        generic_papers: list[dict] = []
    elif condition == "B":
        r1_query = _make_unique_query(
            _derive_condition_b_r1_query(papers, rq, background_topics),
            used_b_queries,
        )
        _log_pubmed_query(log, condition, 1, 0, r1_query)
        print(f"[{condition}] R1 PubMed query: '{r1_query[:70]}'")
        print(f"[{condition}] Retrieving papers for Round 1...")
        generic_papers = retrieve_papers(r1_query, n=5)
        print(f"[{condition}] Retrieved {len(generic_papers)} papers.")
    else:
        print(f"[{condition}] Retrieving generic papers...")
        generic_papers = retrieve_papers(GENERIC_QUERY, n=5)
        _log_pubmed_query(log, condition, 1, 0, GENERIC_QUERY)
        print(f"[{condition}] Retrieved {len(generic_papers)} generic papers.")

    ideas = generate_candidates(
        papers, generic_papers, n=N_CANDIDATES, condition=condition,
        temperature=temperature,
    )
    print(f"[{condition}] Generated {len(ideas)} candidates. Pairwise ranking...")

    r1_ranked, r1_comparisons = rank_candidates_pairwise(ideas, papers)
    log.append({
        "condition": condition,
        "round": 1,
        "candidate_id": 0,
        "type": "round_selection",
        "pairwise_comparisons": r1_comparisons,
    })
    r1_candidates: list[tuple[dict, dict]] = []
    for rank, (idea, ranking) in enumerate(r1_ranked):
        cid = rank + 1
        print(
            f"[{condition}]   Candidate {cid}: overall_wins={ranking['total_wins']}, "
            f"dims={_ranking_summary(ranking)}"
        )
        log.append(_make_entry(condition, 1, cid, idea, ranking))
        r1_candidates.append((idea, ranking))

    if condition == "A":
        best_idea, best_ranking = r1_candidates[0]
        print(
            f"[{condition}] Baseline done. Best overall wins: "
            f"{best_ranking['total_wins']}"
        )
        return best_idea, log

    if condition == "C" and max_rounds == 1:
        best_idea, best_ranking = r1_candidates[0]
        print(f"[{condition}] Stopped after round 1 (max_rounds=1). Best overall wins: {best_ranking['total_wins']}")
        return best_idea, log

    top2 = _top_n(r1_candidates, BEAM_WIDTH)

    print(f"\n[{condition}] Round 2: refining top {len(top2)} candidates...")

    r2_candidates: list[tuple[dict, dict]] = []

    if condition == "C":
        tracker = RetrievalTracker()
        weakness_histories: dict[int, list[str]] = {}
        r2_cand_cids: list[int] = []

    for rank, (idea, ranking) in enumerate(top2):
        cid = rank + 1

        if condition == "C":
            weakness_histories[cid] = []
            history_before = list(weakness_histories[cid])

            weakness_type = identify_weakness_from_ranking(
                ranking, weakness_histories[cid],
            )
            weakness_feedback = diagnose_weakness(idea, weakness_type, papers)
            ood_query = generate_ood_query(idea, weakness_type, weakness_feedback)
            gap_papers, filtered_titles = tracker.retrieve_deduplicated(ood_query, n=3)

            if not gap_papers:
                print(f"[{condition}]   No OOD papers available — keeping parent for cid {cid}.")
                kept_idea, kept_ranking = idea, ranking
                refine_cmp = {
                    "idea_a_label": "parent", "idea_b_label": "refined",
                    "winners": {d: "parent" for d in ("novelty", "specificity", "feasibility", "overall")},
                    "justifications": {d: "No OOD papers retrieved; parent kept unchanged." for d in ("novelty", "specificity", "feasibility", "overall")},
                }
                relevance = None
                weakness_histories[cid].append(weakness_type)
            else:
                relevance = check_retrieval_relevance(
                    idea, weakness_feedback, gap_papers, is_ood=True,
                )

                print(f"[{condition}]   Refining candidate {cid}...")
                refined = refine_candidate(
                    idea, weakness_type, weakness_feedback, gap_papers, is_ood=True,
                    temperature=temperature,
                )

                print(f"[{condition}]   Pairwise: parent vs refined candidate {cid}...")
                kept_idea, kept_ranking, refine_cmp = pairwise_pick_winner(
                    idea, refined, papers, "parent", "refined",
                )
                weakness_histories[cid].append(weakness_type)

            log.append(_make_entry(
                condition, 2, cid, kept_idea, kept_ranking,
                pairwise_comparisons=[refine_cmp],
                weakness_targeted=weakness_type,
                targeted_query=ood_query,
                retrieved_papers=gap_papers,
                retrieval_relevance=relevance,
                weakness_history=history_before,
                weakness_targeted_this_round=weakness_type,
                ood_query_used=ood_query,
                duplicate_papers_filtered=filtered_titles,
                idea_before_refinement=idea,
                idea_after_refinement=kept_idea,
                ranking_before=_ranking_summary(ranking),
                ranking_after=_ranking_summary(kept_ranking),
            ))
            r2_cand_cids.append(cid)

        else:
            weakness_type_b, weakness_query_b, gap_papers_b, weakness_feedback_b = (
                _refinement_context_b(
                    idea, used_b_queries, log, condition, 2, cid,
                )
            )
            relevance_b = check_retrieval_relevance(
                idea, weakness_feedback_b, gap_papers_b,
            )
            print(f"[{condition}]   Refining candidate {cid}...")
            refined = refine_candidate(
                idea, weakness_type_b or "general", weakness_feedback_b, gap_papers_b,
            )
            print(f"[{condition}]   Pairwise: parent vs refined candidate {cid}...")
            kept_idea, kept_ranking, refine_cmp = pairwise_pick_winner(
                idea, refined, papers, "parent", "refined",
            )
            log.append(_make_entry(
                condition, 2, cid, kept_idea, kept_ranking,
                pairwise_comparisons=[refine_cmp],
                weakness_targeted=weakness_type_b,
                targeted_query=weakness_query_b,
                retrieved_papers=gap_papers_b,
                retrieval_relevance=relevance_b,
                idea_before_refinement=idea,
                idea_after_refinement=kept_idea,
                ranking_before=_ranking_summary(ranking),
                ranking_after=_ranking_summary(kept_ranking),
            ))

        r2_candidates.append((kept_idea, kept_ranking))

    print(f"[{condition}] Round 2 selection: pairwise ranking refined candidates...")
    r2_ranked, r2_selection_cmp = rank_candidates_pairwise(
        [c[0] for c in r2_candidates], papers,
    )
    top1_r2 = r2_ranked[0]
    log.append({
        "condition": condition,
        "round": 2,
        "candidate_id": 0,
        "type": "round_selection",
        "pairwise_comparisons": r2_selection_cmp,
        "ranking": top1_r2[1],
    })

    if condition == "C":
        top1_idx = next(
            i for i, (idea, _) in enumerate(r2_candidates) if idea is top1_r2[0]
        )
        round3_history = list(weakness_histories[r2_cand_cids[top1_idx]])

        if max_rounds == 2:
            print(f"[{condition}] Stopped after round 2 (max_rounds=2). Best overall wins: {top1_r2[1]['total_wins']}")
            return top1_r2[0], log

    print(f"\n[{condition}] Round 3: final refinement...")

    best_idea, best_ranking = top1_r2

    if condition == "C":
        history_before_r3 = list(round3_history)

        weakness_type = identify_weakness_from_ranking(best_ranking, round3_history)
        weakness_feedback = diagnose_weakness(best_idea, weakness_type, papers)
        ood_query = generate_ood_query(best_idea, weakness_type, weakness_feedback)
        gap_papers, filtered_titles = tracker.retrieve_deduplicated(ood_query, n=3)

        if not gap_papers:
            print(f"[{condition}]   No OOD papers available — keeping parent for Round 3.")
            final_idea, final_ranking = best_idea, best_ranking
            final_cmp = {
                "idea_a_label": "parent", "idea_b_label": "refined",
                "winners": {d: "parent" for d in ("novelty", "specificity", "feasibility", "overall")},
                "justifications": {d: "No OOD papers retrieved; parent kept unchanged." for d in ("novelty", "specificity", "feasibility", "overall")},
            }
            final_relevance = None
        else:
            final_relevance = check_retrieval_relevance(
                best_idea, weakness_feedback, gap_papers, is_ood=True,
            )

            print(f"[{condition}]   Refining final candidate...")
            refined_final = refine_candidate(
                best_idea, weakness_type, weakness_feedback, gap_papers, is_ood=True,
                temperature=temperature,
            )

            print(f"[{condition}]   Pairwise: parent vs final refined...")
            final_idea, final_ranking, final_cmp = pairwise_pick_winner(
                best_idea, refined_final, papers, "parent", "refined",
            )
        round3_history.append(weakness_type)

        log.append(_make_entry(
            condition, 3, 1, final_idea, final_ranking,
            pairwise_comparisons=[final_cmp],
            weakness_targeted=weakness_type,
            targeted_query=ood_query,
            retrieved_papers=gap_papers,
            retrieval_relevance=final_relevance,
            weakness_history=history_before_r3,
            weakness_targeted_this_round=weakness_type,
            ood_query_used=ood_query,
            duplicate_papers_filtered=filtered_titles,
            idea_before_refinement=best_idea,
            idea_after_refinement=final_idea,
            ranking_before=_ranking_summary(best_ranking),
            ranking_after=_ranking_summary(final_ranking),
        ))

    else:
        weakness_type_b, weakness_query_b, gap_papers_b, weakness_feedback_b = (
            _refinement_context_b(
                best_idea, used_b_queries, log, condition, 3, 1,
            )
        )
        final_relevance = check_retrieval_relevance(
            best_idea, weakness_feedback_b, gap_papers_b,
        )
        print(f"[{condition}]   Refining final candidate...")
        refined_final = refine_candidate(
            best_idea, weakness_type_b or "general", weakness_feedback_b, gap_papers_b,
        )
        print(f"[{condition}]   Pairwise: parent vs final refined...")
        final_idea, final_ranking, final_cmp = pairwise_pick_winner(
            best_idea, refined_final, papers, "parent", "refined",
        )
        log.append(_make_entry(
            condition, 3, 1, final_idea, final_ranking,
            pairwise_comparisons=[final_cmp],
            weakness_targeted=weakness_type_b,
            targeted_query=weakness_query_b,
            retrieved_papers=gap_papers_b,
            retrieval_relevance=final_relevance,
            idea_before_refinement=best_idea,
            idea_after_refinement=final_idea,
            ranking_before=_ranking_summary(best_ranking),
            ranking_after=_ranking_summary(final_ranking),
        ))

    print(
        f"[{condition}] Done. Final overall wins: {final_ranking['total_wins']}"
    )
    return final_idea, log


# ── Condition D: Structured Abstraction Before Retrieval ─────────────────────

def _make_d_entry(
    round_num: int,
    candidate_id: int,
    idea: dict,
    ranking: dict | None,
    abstract_problem_text: str,
    cross_domain_query_text: str,
    retrieved_papers: list[dict],
    retrieval_relevance: int | None,
    ad_papers_filtered: list[str],
    abstraction_history_at_this_step: list[str],
    analogy_mapping_reasoning: str,
    weakness_targeted: str | None = None,
    pairwise_comparisons: list[dict] | None = None,
    idea_before_mapping: dict | None = None,
) -> dict:
    """Build a Condition D log entry with the full abstraction trace."""
    entry = {
        "condition":                        "D",
        "round":                            round_num,
        "candidate_id":                     candidate_id,
        "idea":                             idea,
        "ranking":                          ranking,
        "scores":                           _ranking_to_scores(ranking) if ranking else None,
        "abstract_problem":                 abstract_problem_text,
        "cross_domain_query":               cross_domain_query_text,
        "retrieved_papers":                 retrieved_papers,
        "retrieval_relevance":              retrieval_relevance,
        "ad_papers_filtered":               ad_papers_filtered,
        "abstraction_history_at_this_step": list(abstraction_history_at_this_step),
        "analogy_mapping_reasoning":        analogy_mapping_reasoning,
        "weakness_targeted":                weakness_targeted,
        "idea_before_mapping":              idea_before_mapping,
        "final_idea":                       idea,
        "pairwise_comparisons":             pairwise_comparisons or [],
    }
    return entry


def _d_generate_candidate(
    papers: list[dict],
    tracker: RetrievalTracker,
    abstraction_history: list[str],
    log: list[dict],
    round_num: int,
    candidate_id: int,
    n_papers: int,
    weakness_dimension: str | None = None,
    current_idea: dict | None = None,
) -> tuple[dict, str, dict]:
    """
    Run the four-step abstraction→retrieval→mapping cycle for one candidate.

    Returns (idea, abstraction, d_log_entry). The entry is also appended to log,
    along with a pubmed_query entry for the cross-domain query.
    """
    # Step 1 — abstract the problem structure
    abstraction = abstract_problem(
        papers,
        abstraction_history=abstraction_history if abstraction_history else None,
        weakness_dimension=weakness_dimension,
        current_idea=current_idea,
    )
    print(f"\n[D] R{round_num} candidate {candidate_id} — abstract problem:")
    print(f"    {abstraction}")

    history_snapshot = list(abstraction_history) + [abstraction]

    # Step 2 — cross-domain query
    query = cross_domain_query(abstraction)
    print(f"[D]   cross-domain query: '{query}'")
    _log_pubmed_query(log, "D", round_num, candidate_id, query)

    # Cross-domain retrieval: deduplicated, AD-filtered, contamination-filtered
    # (via the eval-patched retrieve_papers), date-capped at 2023/12/31.
    gap_papers, filtered_titles = tracker.retrieve_deduplicated(query, n=n_papers)
    if gap_papers:
        print(f"[D]   retrieved {len(gap_papers)} cross-domain paper(s):")
        for p in gap_papers:
            print(f"      - {p['title'][:70]}")
    else:
        print("[D]   no cross-domain papers retrieved — mapping from abstraction only.")

    # Step 3 — map adjacent-field solutions back to the target domain
    idea, reasoning = map_cross_domain(abstraction, papers, gap_papers)
    print(f"[D]   mapped hypothesis: {idea['method'][:90]}")

    relevance: int | None = None
    if gap_papers:
        relevance = check_retrieval_relevance(
            idea, abstraction, gap_papers, is_ood=True,
        )

    entry = _make_d_entry(
        round_num=round_num,
        candidate_id=candidate_id,
        idea=idea,
        ranking=None,
        abstract_problem_text=abstraction,
        cross_domain_query_text=query,
        retrieved_papers=gap_papers,
        retrieval_relevance=relevance,
        ad_papers_filtered=filtered_titles,
        abstraction_history_at_this_step=history_snapshot,
        analogy_mapping_reasoning=reasoning,
        weakness_targeted=weakness_dimension,
    )
    log.append(entry)
    return idea, abstraction, entry


def run_condition_d(
    papers: list[dict],
) -> tuple[dict, list[dict]]:
    """
    Condition D — Structured Abstraction Before Retrieval.

    Round 1: 5 candidates, each via abstraction→cross-domain retrieval→mapping.
             Diversity is enforced at the abstraction level (history-aware).
    Round 2: refine top 2 with weakness-targeted abstractions.
    Round 3: refine the single survivor the same way.
    """
    log: list[dict] = []
    abstraction_history: list[str] = []
    tracker = RetrievalTracker()

    print("\n[D] Round 1: structured abstraction before retrieval...")

    r1_ideas: list[dict] = []
    for cid in range(1, N_CANDIDATES + 1):
        idea, abstraction, _ = _d_generate_candidate(
            papers, tracker, abstraction_history, log,
            round_num=1, candidate_id=cid, n_papers=5,
        )
        r1_ideas.append(idea)
        abstraction_history.append(abstraction)

    print("\n[D] Round 1: pairwise ranking of 5 candidates...")
    r1_ranked, r1_comparisons = rank_candidates_pairwise(r1_ideas, papers)
    log.append({
        "condition": "D",
        "round": 1,
        "candidate_id": 0,
        "type": "round_selection",
        "pairwise_comparisons": r1_comparisons,
    })
    r1_candidates: list[tuple[dict, dict]] = []
    for rank, (idea, ranking) in enumerate(r1_ranked):
        cid = rank + 1
        print(
            f"[D]   Candidate {cid}: overall_wins={ranking['total_wins']}, "
            f"dims={_ranking_summary(ranking)}"
        )
        log.append(_make_entry("D", 1, cid, idea, ranking))
        r1_candidates.append((idea, ranking))

    top2 = _top_n(r1_candidates, BEAM_WIDTH)

    # ── Round 2: weakness-targeted abstraction refinement of top 2 ──────────
    print(f"\n[D] Round 2: refining top {len(top2)} candidates...")
    r2_candidates: list[tuple[dict, dict]] = []
    weakness_histories: dict[int, list[str]] = {}

    for rank, (idea, ranking) in enumerate(top2):
        cid = rank + 1
        weakness_histories[cid] = []
        weakness_type = identify_weakness_from_ranking(ranking, weakness_histories[cid])

        refined, abstraction, d_entry = _d_generate_candidate(
            papers, tracker, abstraction_history, log,
            round_num=2, candidate_id=cid, n_papers=3,
            weakness_dimension=weakness_type, current_idea=idea,
        )
        abstraction_history.append(abstraction)
        weakness_histories[cid].append(weakness_type)

        print(f"[D]   Pairwise: parent vs refined candidate {cid}...")
        kept_idea, kept_ranking, refine_cmp = pairwise_pick_winner(
            idea, refined, papers, "parent", "refined",
        )
        d_entry["pairwise_comparisons"] = [refine_cmp]
        d_entry["idea_before_mapping"] = idea
        d_entry["ranking"] = kept_ranking
        d_entry["scores"] = _ranking_to_scores(kept_ranking)
        d_entry["idea"] = kept_idea
        d_entry["final_idea"] = kept_idea
        r2_candidates.append((kept_idea, kept_ranking))

    print("[D] Round 2 selection: pairwise ranking refined candidates...")
    r2_ranked, r2_selection_cmp = rank_candidates_pairwise(
        [c[0] for c in r2_candidates], papers,
    )
    top1_r2 = r2_ranked[0]
    log.append({
        "condition": "D",
        "round": 2,
        "candidate_id": 0,
        "type": "round_selection",
        "pairwise_comparisons": r2_selection_cmp,
        "ranking": top1_r2[1],
    })

    top1_idx = next(
        i for i, (idea, _) in enumerate(r2_candidates) if idea is top1_r2[0]
    )
    round3_history = list(weakness_histories[top1_idx + 1])

    # ── Round 3: final weakness-targeted refinement of the survivor ─────────
    print("\n[D] Round 3: final refinement...")
    best_idea, best_ranking = top1_r2
    weakness_type = identify_weakness_from_ranking(best_ranking, round3_history)

    refined_final, abstraction, d_entry = _d_generate_candidate(
        papers, tracker, abstraction_history, log,
        round_num=3, candidate_id=1, n_papers=3,
        weakness_dimension=weakness_type, current_idea=best_idea,
    )
    abstraction_history.append(abstraction)

    print("[D]   Pairwise: parent vs final refined...")
    final_idea, final_ranking, final_cmp = pairwise_pick_winner(
        best_idea, refined_final, papers, "parent", "refined",
    )
    d_entry["pairwise_comparisons"] = [final_cmp]
    d_entry["idea_before_mapping"] = best_idea
    d_entry["ranking"] = final_ranking
    d_entry["scores"] = _ranking_to_scores(final_ranking)
    d_entry["idea"] = final_idea
    d_entry["final_idea"] = final_idea

    print(f"[D] Done. Final overall wins: {final_ranking['total_wins']}")
    return final_idea, log
