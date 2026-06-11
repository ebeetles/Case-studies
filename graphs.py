from __future__ import annotations

"""
Three story-driven visualisations for the pairwise beam search case study.

Graph 1 — Did the tournament find a real winner?
Graph 2 — What did each condition produce, and who won the final comparison?
Graph 3 — When did OOD retrieval actually help?
"""

import os
import re
import textwrap

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

RESULTS_DIR = "results"

COND_COLORS = {"A": "#4878cf", "B": "#e8853d", "C": "#6acc65"}
COND_LABELS = {
    "A": "Condition A — Baseline\n(no retrieval, novelty constraint)",
    "B": "Condition B — Generic RAG\n(same papers every round)",
    "C": "Condition C — Full Pipeline\n(targeted OOD retrieval)",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _r1_candidates(log: list[dict]) -> list[dict]:
    return sorted(
        [e for e in log if e.get("round") == 1 and "scores" in e
         and e.get("type") not in ("round_selection", "condition_comparison")],
        key=lambda e: e["scores"]["total_wins"],
        reverse=True,
    )


_SKIP_WORDS = {
    "the", "we", "a", "an", "its", "this", "that", "our", "of", "to",
    "for", "in", "on", "by", "at", "with", "and", "or", "is", "are",
    "will", "be", "has", "have", "been", "drug", "compound", "potential",
    "ability", "investigate", "repurposing", "propose",
}


def _get_drug(method: str) -> str:
    patterns = [
        r"[Tt]he drug ([\w\-]+)[,\s]",
        r"investigate the potential of ([\w\-]+)[,\s]",
        r"investigate ([\w\-]+)'s",
        r"repurposing of (?:the )?(?:drug |compound )?([\w\-]+)[,\s]",
        r"potential of ([\w\-]+)[,\s]",
    ]
    for pat in patterns:
        m = re.search(pat, method, re.IGNORECASE)
        if m:
            name = m.group(1)
            if len(name) > 3 and name.lower() not in _SKIP_WORDS:
                return name.capitalize()
    # fallback: first word > 5 chars that isn't a skip word
    for word in re.findall(r"\b([A-Za-z]{5,})\b", method):
        if word.lower() not in _SKIP_WORDS:
            return word.capitalize()
    return method.split()[0][:12]


def _wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(str(text), width))


def _hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


# ── Graph 1: "Did the tournament find a real winner?" ────────────────────────

def graph1_tournament(log_a: list[dict], log_b: list[dict], log_c: list[dict]) -> None:
    """
    STORY: Was pairwise comparison actually differentiating candidates, or were
    all ideas scoring the same?  A spread from 0→4 means beam selection had
    something real to work with.

    Each bar = one R1 candidate idea.  Length = number of overall matchup wins
    out of 4 possible.  Top-2 (coloured) advance to the beam; the rest are cut.
    """
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    fig.suptitle(
        "Round 1 Tournament — Did pairwise comparison find a clear winner?",
        fontsize=12, fontweight="bold",
    )

    for ax, (cond, log) in zip(axes, [("A", log_a), ("B", log_b), ("C", log_c)]):
        entries = _r1_candidates(log)
        n = len(entries)
        wins = [e["scores"]["total_wins"] for e in entries]
        drugs = [_get_drug(e["idea"]["method"]) for e in entries]
        color = COND_COLORS[cond]

        y = np.arange(n)
        bars = ax.barh(
            y, wins,
            color=[color if i < 2 else "#d4d4d4" for i in range(n)],
            edgecolor="white", height=0.55,
        )

        # Win count inside bar (white) or beside (dark) if bar too short
        for i, (bar, w) in enumerate(zip(bars, wins)):
            if w >= 1:
                ax.text(w - 0.1, y[i], str(w), va="center", ha="right",
                        fontsize=9, fontweight="bold",
                        color="white" if i < 2 else "#888888")
            else:
                ax.text(w + 0.1, y[i], str(w), va="center", ha="left",
                        fontsize=9, fontweight="bold", color="#888888")

        # Drug name to the right of each bar
        for i, drug in enumerate(drugs):
            ax.text(4.3, y[i], drug, va="center", ha="left",
                    fontsize=8.5, color="#333333")

        # Beam cutoff line
        if n > 2:
            ax.axhline(1.5, color=color, linewidth=1.2,
                       linestyle="--", alpha=0.7, zorder=5)
            ax.text(4.25, 1.7, "beam\ncutoff", fontsize=7,
                    color=color, va="bottom", ha="left")

        ax.set_yticks(y)
        ax.set_yticklabels([f"Idea {e['candidate_id']}" for e in entries],
                           fontsize=9)
        ax.set_xlabel("Overall matchup wins (out of 4)", fontsize=9)
        ax.set_xlim(0, 6.2)
        ax.set_title(COND_LABELS[cond], fontsize=9, fontweight="bold", pad=8)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.invert_yaxis()

        # Spine styling
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Single legend
    fig.legend(
        handles=[
            mpatches.Patch(color="#4878cf", label="Entered beam (top 2)"),
            mpatches.Patch(color="#d4d4d4", label="Eliminated"),
        ],
        loc="lower center", ncol=2, fontsize=9, bbox_to_anchor=(0.5, -0.04),
        frameon=False,
    )

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, "graph1_tournament.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── Graph 2: "The Final Verdict" ──────────────────────────────────────────────

def graph2_final_verdict(
    log_a: list[dict],
    log_b: list[dict],
    log_c: list[dict],
    comparison_logs: list[dict] | None = None,
) -> None:
    """
    STORY: After three rounds of generation and refinement, which condition
    produced the best hypothesis?

    Top strip: what each condition actually proposed (drug + mechanism).
    Grid: who won each quality dimension in the two final comparisons.
    """
    all_logs = log_a + log_b + log_c + (comparison_logs or [])
    cc_entries = [e for e in all_logs if e.get("type") == "condition_comparison"]
    comp_map: dict[str, dict] = {e["comparison"]: e for e in cc_entries}

    if not comp_map:
        print("  [graphs] No condition_comparison entries — skipping Graph 2.")
        return

    # ── top strip: what each condition proposed ───────────────────────────────
    ideas = {
        "A": ("Fenofibrate",
              "Nrf2-mediated mitochondrial biogenesis\n+ blood-brain barrier integrity"),
        "B": ("Metformin",
              "NLRP3 inflammasome inhibition\n+ neuroinflammation"),
        "C": ("Metformin",
              "NLRP3 inflammasome + mitochondrial\nbioenergetics (dual readout)"),
    }

    comparisons = [("A_vs_C", "A  vs  C"), ("B_vs_C", "B  vs  C")]
    dims = ["novelty", "specificity", "feasibility", "overall"]
    dim_labels = ["Novelty", "Specificity", "Feasibility", "Overall"]

    fig = plt.figure(figsize=(13, 7))
    fig.suptitle(
        "The Final Verdict — Which condition's hypothesis won each quality dimension?",
        fontsize=12, fontweight="bold", y=0.99,
    )

    # Row 0: idea summary cards (3 columns)
    gs = fig.add_gridspec(3, 4, height_ratios=[1, 1, 1], hspace=0.55, wspace=0.25)

    for ci, cond in enumerate(["A", "B", "C"]):
        ax = fig.add_subplot(gs[0, ci] if ci < 3 else gs[0, 3])
        ax.axis("off")
        col = COND_COLORS[cond]
        drug, mech = ideas[cond]
        ax.text(0.5, 0.85, f"Condition {cond}",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=10, fontweight="bold", color=col)
        ax.text(0.5, 0.58, drug,
                transform=ax.transAxes, ha="center", va="top",
                fontsize=13, fontweight="bold", color="#222222")
        ax.text(0.5, 0.18, mech,
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8, color="#555555", linespacing=1.4)
        for spine_name in ["top", "bottom", "left", "right"]:
            pass
        rect = mpatches.FancyBboxPatch(
            (0.03, 0.02), 0.94, 0.96,
            boxstyle="round,pad=0.02",
            transform=ax.transAxes,
            facecolor=(*_hex_to_rgb(col), 0.07),
            edgecolor=(*_hex_to_rgb(col), 0.5),
            linewidth=1.5,
            clip_on=False,
        )
        ax.add_patch(rect)

    # Hide the 4th top cell
    ax_empty = fig.add_subplot(gs[0, 3])
    ax_empty.axis("off")

    # Rows 1-2: comparison grid
    for ri, (comp_key, comp_label) in enumerate(comparisons):
        comp = comp_map.get(comp_key, {})
        winners = comp.get("winners", {})
        justifications = comp.get("justifications", {})
        cond_left, cond_right = comp_key.split("_vs_")

        for ci, (dim, dim_label) in enumerate(zip(dims, dim_labels)):
            ax = fig.add_subplot(gs[ri + 1, ci])
            ax.set_xticks([])
            ax.set_yticks([])

            winner = winners.get(dim, "?")
            col = COND_COLORS.get(winner, "#aaaaaa")
            r, g, b = _hex_to_rgb(col)

            ax.set_facecolor((r, g, b, 0.12))
            for spine in ax.spines.values():
                spine.set_edgecolor((*_hex_to_rgb(col), 0.7))
                spine.set_linewidth(2)

            ax.text(0.5, 0.78, f"Condition {winner} wins",
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=10, fontweight="bold", color=col)

            just = justifications.get(dim, "")
            # Keep first sentence only, max ~55 chars per line
            first_sent = just.split(".")[0].strip() + "."
            ax.text(0.5, 0.32, _wrap(first_sent, 40),
                    transform=ax.transAxes, ha="center", va="center",
                    fontsize=7, color="#444444", linespacing=1.35)

            if ri == 0:
                ax.set_title(dim_label, fontsize=10, fontweight="bold", pad=7)
            if ci == 0:
                ax.set_ylabel(comp_label, fontsize=10, fontweight="bold",
                              labelpad=8, rotation=90, va="center")

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, "graph2_final_verdict.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── Graph 3: "When did OOD retrieval actually help?" ─────────────────────────

def graph3_ood_story(log_c: list[dict]) -> None:
    """
    STORY: Condition C ran OOD retrieval 3 times.  It failed twice when
    targeting 'novelty' and succeeded once when targeting 'consistency'.
    This tells us something real: OOD analogical search can fill logical
    gaps but can't invent genuinely new mechanisms.

    Each card = one OOD refinement attempt. Shows what weakness was diagnosed,
    what field was searched, and whether the refined idea beat the original.
    """
    ood_entries = [
        e for e in log_c
        if e.get("round", 0) >= 2
        and e.get("ood_query_used")
        and e.get("type") not in ("round_selection", "condition_comparison")
    ]

    if not ood_entries:
        print("  [graphs] No OOD entries — skipping Graph 3.")
        return

    # ── Parse each OOD attempt ────────────────────────────────────────────────
    cards = []
    for e in ood_entries:
        cmps = e.get("pairwise_comparisons") or []
        winner = cmps[0]["winners"].get("overall", "parent") if cmps else "parent"
        refined_wins = "refined" in str(winner).lower()

        query = e.get("ood_query_used") or ""
        papers = e.get("retrieved_papers") or []
        paper_titles = [p.get("title", "")[:65] for p in papers]

        # Infer search domain from paper titles (first word after the AD topic)
        domains = []
        for title in paper_titles:
            title_lower = title.lower()
            if any(w in title_lower for w in ("stroke", "ischemia", "cerebrovascular")):
                domains.append("Stroke research")
            elif any(w in title_lower for w in ("cancer", "tumor", "oncol")):
                domains.append("Cancer biology")
            elif any(w in title_lower for w in ("aging", "age-related", "senescence")):
                domains.append("Aging research")
            elif any(w in title_lower for w in ("cardiac", "heart", "cardiovascular")):
                domains.append("Cardiology")
            elif any(w in title_lower for w in ("chinese medicine", "tcm", "ginseng",
                                                  "artemisinin", "pharmacology approach")):
                domains.append("Trad. Chinese Medicine")
            elif any(w in title_lower for w in ("covid", "sars", "virus")):
                domains.append("Infectious disease")
            elif any(w in title_lower for w in ("renal", "kidney")):
                domains.append("Renal medicine")
            elif any(w in title_lower for w in ("network pharmacol")):
                domains.append("Network pharmacology")
            else:
                domains.append(title[:30] + "...")
        domains = list(dict.fromkeys(domains))[:3]  # deduplicate, max 3

        cards.append({
            "round": f"Round {e.get('round')}, Beam {e.get('candidate_id')}",
            "weakness": (e.get("weakness_targeted") or "general").capitalize(),
            "query_summary": _wrap(query, 32),
            "domains": domains,
            "refined_wins": refined_wins,
            "paper_titles": paper_titles,
        })

    n = len(cards)
    fig, axes = plt.subplots(1, n, figsize=(4.5 * n, 6.5))
    if n == 1:
        axes = [axes]

    fig.suptitle(
        "Condition C — When did OOD retrieval help?",
        fontsize=12, fontweight="bold", y=1.01,
    )

    for ax, card in zip(axes, cards):
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        refined = card["refined_wins"]
        outcome_col = "#2a7d2a" if refined else "#b85c00"
        outcome_text = "Refined idea wins" if refined else "Parent idea kept"
        outcome_bg = "#e6f5e6" if refined else "#fdf0e6"

        # ── Card background ───────────────────────────────────────────────────
        bg = mpatches.FancyBboxPatch(
            (0.04, 0.02), 0.92, 0.96,
            boxstyle="round,pad=0.02",
            transform=ax.transAxes,
            facecolor="#fafafa", edgecolor="#cccccc",
            linewidth=1.2, clip_on=False,
        )
        ax.add_patch(bg)

        # ── Round label ───────────────────────────────────────────────────────
        ax.text(0.5, 0.93, card["round"],
                transform=ax.transAxes, ha="center", va="center",
                fontsize=10, fontweight="bold", color="#222222")

        # ── Weakness badge ────────────────────────────────────────────────────
        weakness_col = "#c0392b" if card["weakness"].lower() == "novelty" else "#2980b9"
        ax.text(0.5, 0.83,
                f"Weakness diagnosed:  {card['weakness']}",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=9.5, color=weakness_col, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.35",
                          facecolor=(*_hex_to_rgb(
                              "#fce4e4" if card["weakness"].lower() == "novelty"
                              else "#d6eaf8"), 1.0),
                          edgecolor=(*_hex_to_rgb(weakness_col), 0.4),
                          linewidth=1))

        # ── Arrow ─────────────────────────────────────────────────────────────
        ax.annotate("", xy=(0.5, 0.71), xytext=(0.5, 0.76),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color="#888888",
                                   lw=1.5, mutation_scale=14))

        # ── OOD search ────────────────────────────────────────────────────────
        ax.text(0.5, 0.69,
                "Searched outside AD literature:",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8, color="#555555", style="italic")
        ax.text(0.5, 0.62,
                card["query_summary"],
                transform=ax.transAxes, ha="center", va="top",
                fontsize=7.5, color="#333333", linespacing=1.35)

        # ── Domains ───────────────────────────────────────────────────────────
        ax.text(0.5, 0.44,
                "Papers from:",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8, color="#555555", style="italic")
        domain_str = "\n".join(f"  • {d}" for d in card["domains"])
        ax.text(0.5, 0.38,
                domain_str if domain_str else "  (mixed domains)",
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8.5, color="#333333", linespacing=1.5)

        # ── Arrow to outcome ──────────────────────────────────────────────────
        ax.annotate("", xy=(0.5, 0.18), xytext=(0.5, 0.23),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color="#888888",
                                   lw=1.5, mutation_scale=14))

        # ── Outcome badge ─────────────────────────────────────────────────────
        outcome_patch = mpatches.FancyBboxPatch(
            (0.12, 0.06), 0.76, 0.11,
            boxstyle="round,pad=0.02",
            transform=ax.transAxes,
            facecolor=outcome_bg,
            edgecolor=(*_hex_to_rgb(outcome_col), 0.6),
            linewidth=2, clip_on=False,
        )
        ax.add_patch(outcome_patch)
        ax.text(0.5, 0.115, outcome_text,
                transform=ax.transAxes, ha="center", va="center",
                fontsize=10.5, fontweight="bold", color=outcome_col)

    # Caption
    fig.text(
        0.5, -0.02,
        "Finding: OOD retrieval succeeded when targeting consistency (filling a logical gap) "
        "but failed when targeting novelty (analogical search cannot invent new mechanisms).",
        ha="center", va="top", fontsize=9, color="#555555",
        style="italic", wrap=True,
    )

    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, "graph3_ood_story.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def generate_all_graphs(
    log_a: list[dict],
    log_b: list[dict],
    log_c: list[dict],
    comparison_logs: list[dict] | None = None,
) -> None:
    """Generate and save all three story-driven graphs."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("\nGenerating Graph 1: Round 1 tournament...")
    graph1_tournament(log_a, log_b, log_c)

    print("Generating Graph 2: Final verdict...")
    graph2_final_verdict(log_a, log_b, log_c, comparison_logs)

    print("Generating Graph 3: OOD story...")
    graph3_ood_story(log_c)

    print("\nAll graphs saved to results/")
