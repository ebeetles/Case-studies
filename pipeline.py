from __future__ import annotations

"""
Pipeline module: implements the three experimental conditions.

  Condition A — Baseline (no retrieval, no iteration)
  Condition B — Generic RAG (retrieval, but same papers every round, unchanged)
  Condition C — Full pipeline with targeted gap-filling fixes

Beam selection uses pairwise comparison (novelty, specificity, feasibility, overall)
instead of absolute scoring. Legacy score_idea() is not called.
"""

from generator  import generate_candidates, refine_candidate
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


def _refinement_context_b(
    generic_papers: list[dict],
) -> tuple[str | None, str | None, list[dict], str]:
    return (
        None,
        None,
        generic_papers[:3],
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

def run_pipeline(condition: str) -> tuple[dict, list[dict]]:
    assert condition in ("A", "B", "C"), f"Unknown condition: {condition}"
    log: list[dict] = []

    print(f"\n[{condition}] Round 1: generating candidates...")

    if condition == "A":
        generic_papers: list[dict] = []
    else:
        print(f"[{condition}] Retrieving generic papers...")
        generic_papers = retrieve_papers(GENERIC_QUERY, n=5)
        print(f"[{condition}] Retrieved {len(generic_papers)} generic papers.")

    ideas = generate_candidates(SEED_PAPERS, generic_papers, n=N_CANDIDATES)
    print(f"[{condition}] Generated {len(ideas)} candidates. Pairwise ranking...")

    r1_ranked, r1_comparisons = rank_candidates_pairwise(ideas, SEED_PAPERS)
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
            weakness_feedback = diagnose_weakness(idea, weakness_type, SEED_PAPERS)
            ood_query = generate_ood_query(idea, weakness_type, weakness_feedback)
            gap_papers, filtered_titles = tracker.retrieve_deduplicated(ood_query, n=3)
            relevance = check_retrieval_relevance(
                idea, weakness_feedback, gap_papers, is_ood=True,
            )

            print(f"[{condition}]   Refining candidate {cid}...")
            refined = refine_candidate(
                idea, weakness_type, weakness_feedback, gap_papers, is_ood=True,
            )

            print(f"[{condition}]   Pairwise: parent vs refined candidate {cid}...")
            kept_idea, kept_ranking, refine_cmp = pairwise_pick_winner(
                idea, refined, SEED_PAPERS, "parent", "refined",
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
                _refinement_context_b(generic_papers)
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
                idea, refined, SEED_PAPERS, "parent", "refined",
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
        [c[0] for c in r2_candidates], SEED_PAPERS,
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

    print(f"\n[{condition}] Round 3: final refinement...")

    best_idea, best_ranking = top1_r2

    if condition == "C":
        history_before_r3 = list(round3_history)

        weakness_type = identify_weakness_from_ranking(best_ranking, round3_history)
        weakness_feedback = diagnose_weakness(best_idea, weakness_type, SEED_PAPERS)
        ood_query = generate_ood_query(best_idea, weakness_type, weakness_feedback)
        gap_papers, filtered_titles = tracker.retrieve_deduplicated(ood_query, n=3)
        final_relevance = check_retrieval_relevance(
            best_idea, weakness_feedback, gap_papers, is_ood=True,
        )

        print(f"[{condition}]   Refining final candidate...")
        refined_final = refine_candidate(
            best_idea, weakness_type, weakness_feedback, gap_papers, is_ood=True,
        )

        print(f"[{condition}]   Pairwise: parent vs final refined...")
        final_idea, final_ranking, final_cmp = pairwise_pick_winner(
            best_idea, refined_final, SEED_PAPERS, "parent", "refined",
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
            _refinement_context_b(generic_papers)
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
            best_idea, refined_final, SEED_PAPERS, "parent", "refined",
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
