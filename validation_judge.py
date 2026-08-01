from __future__ import annotations

"""
Judge conditions for the rubric-validation experiment (blind — text only, no
tier/degradation labels, no other hypotheses).

Reuses judge._call_judge / judge.get_judge_model (OpenAI, same model as the
main pipeline's judge) for all three conditions:

  - rubric_score_novelty / rubric_score_specificity: absolute 1-5 scores.
    Dimension definitions are carried over verbatim in substance from
    judge.compare_ideas()'s NOVELTY / SPECIFICITY definitions (the only
    existing definitions of these dimensions in this codebase), reformatted
    for single-item 1-5 scoring instead of pairwise A/B choice. There is no
    pre-existing absolute-scoring rubric for these two hypothesis-quality
    dimensions to reuse verbatim (the existing score_idea() rubric is
    problem/method/contribution-shaped and uses 0-3 / 1-3 scales for a
    different set of dimensions), so these prompts are new.
  - holistic_score: single unstructured 1-5 quality score, no rubric.
  - pairwise_compare: A/B choice on novelty and specificity, one call,
    following judge.compare_ideas()'s existing prompt/parsing structure.

Per judge.py's own stated convention ("Three separate LLM calls per idea,
never combined into one prompt"), rubric novelty and specificity are scored
in separate calls.
"""

import re

from judge import _call_judge


def _parse_1_to_5(text: str, label: str) -> tuple[int, str]:
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if not lines:
        raise RuntimeError(f"Empty response parsing {label}")
    first = lines[0].strip()
    m = re.search(r"[1-5]", first)
    if not m:
        m = re.search(r"[1-5]", text)
    if not m:
        raise RuntimeError(f"Could not parse {label} (expected 1-5):\n{text[:500]}")
    score = int(m.group())
    justification = " ".join(lines[1:]).strip() if len(lines) > 1 else ""
    return score, justification


# ── Rubric judge (absolute, 1-5, one dimension per call) ────────────────────

def rubric_score_novelty(
    hypothesis_text: str,
    context_papers: list[dict] | None = None,
    context_label: str = "",
) -> tuple[int, str]:
    """
    context_papers: if given, a literature-context block is injected and the
    judge is told to score using ONLY that context (for the time-split
    novelty-decay experiment). None (default) reproduces the exact prompt
    used in all prior validation runs, byte-for-byte.
    """
    context_block = ""
    if context_papers:
        lit_lines = "\n".join(
            f"- {p['title']} ({p.get('year', '?')}): {p.get('abstract', '')[:300]}"
            for p in context_papers
        )
        context_block = f"""
RELEVANT LITERATURE ({context_label}):
{lit_lines}

Score novelty based ONLY on the provided literature context above. Do not use
any other knowledge you may have about whether this idea became established,
validated, or well-known later — judge it as if this literature snapshot is
everything known about the field right now.
"""

    prompt = f"""You are a critical scientific reviewer evaluating a drug-repurposing
hypothesis for Alzheimer's disease (AD).

Hypothesis: {hypothesis_text}
{context_block}
NOVELTY (1-5)

Score how novel this hypothesis is AS AN APPLICATION TO ALZHEIMER'S DISEASE
specifically — not how novel or obscure the underlying biological mechanism is
in general.

Critical distinction: a hypothesis can use a well-known, textbook biological
pathway (e.g. a common signaling cascade) and still be highly novel, if applying
that pathway to Alzheimer's disease is a new or underexplored idea. Conversely,
a hypothesis can invoke an obscure or rarely-discussed pathway and still be
low-novelty, if it does so vaguely, without articulating why that pathway is
specifically relevant to AD pathology.

Do NOT penalize novelty just because the mechanism (e.g. a common receptor,
enzyme, or signaling pathway) is well-characterized in the broader biological
literature. Familiarity of the underlying biology is irrelevant to this score.

Do NOT reward novelty just because the compound or pathway is rarely discussed
in the AD literature. Rarity alone is not evidence of a genuine, non-obvious
insight — it may simply reflect that no one has proposed it, for good or bad
reasons that this score should not assume.

Score based on: does this hypothesis draw a specific, articulated, non-obvious
connection between this compound's mechanism and AD pathology, that goes beyond
restating an already-established repurposing rationale?

1 = Restates an already well-established AD repurposing rationale with no new angle
3 = Proposes a reasonable but fairly expected connection between mechanism and AD
5 = Draws a specific, non-obvious mechanistic connection to AD not commonly proposed

Example (should NOT score low just for familiar biology): "Metformin may activate
AMPK to reduce neuroinflammation and tau pathology" — AMPK is a well-known pathway,
but this represents a genuine, non-obvious repurposing rationale.

Example (should NOT score high just for being rare): "Adenosine may have effects
relevant to Alzheimer's disease" — rarely discussed, but this is vague and doesn't
articulate a specific mechanistic connection, so it should score LOW despite being
an unusual pairing.

Reply with ONLY the number (1-5) on the first line, then a one-sentence
justification on the second line."""

    text = _call_judge(prompt)
    return _parse_1_to_5(text, "rubric novelty")


def check_literature_comprehension(
    compound: str,
    mechanism_label: str,
    context_papers: list[dict],
    context_label: str = "",
) -> tuple[bool, str]:
    """
    Direct comprehension probe, separate from and prior to novelty scoring:
    does the judge correctly read whether the given literature block already
    describes compound+mechanism in an AD context? Returns (answer_is_yes, raw_text).
    """
    lit_lines = "\n".join(
        f"- {p['title']} ({p.get('year', '?')}): {p.get('abstract', '')[:300]}"
        for p in context_papers
    )
    prompt = f"""Here is a literature context ({context_label}):
{lit_lines}

Based ONLY on the literature provided above, does this literature already
describe a connection between {compound} and {mechanism_label} in the context
of Alzheimer's disease? Answer YES or NO, and quote or paraphrase the specific
part of the provided literature that supports your answer. If the provided
literature does not contain such a connection, say NO and explain what the
literature does contain instead.

Reply with YES or NO on the first line, then your explanation."""

    text = _call_judge(prompt)
    first_line = text.strip().splitlines()[0].strip().upper() if text.strip() else ""
    if "YES" in first_line:
        answer_is_yes = True
    elif "NO" in first_line:
        answer_is_yes = False
    else:
        raise RuntimeError(f"Could not parse YES/NO from comprehension check:\n{text[:500]}")
    return answer_is_yes, text.strip()


def rubric_score_specificity(hypothesis_text: str) -> tuple[int, str]:
    prompt = f"""You are a critical scientific reviewer evaluating a drug-repurposing
hypothesis for Alzheimer's disease (AD).

Hypothesis: {hypothesis_text}

Rate this hypothesis's SPECIFICITY: does it name concrete, actionable targets
(a specific drug, a specific molecular pathway or target, a specific
measurable effect) rather than vague general claims ("may have effects",
"may be beneficial") without naming what to test?

Score on a 1-5 scale:
1 = no concrete target or mechanism named, entirely vague
2 = names the compound and disease link only, no mechanism
3 = names a general pathway/class but not a specific molecular target or effect
4 = names compound and a specific molecular target/pathway
5 = names compound, specific molecular target/pathway, AND a specific
    measurable downstream effect

Reply with ONLY the number (1-5) on the first line, then a one-sentence
justification on the second line."""

    text = _call_judge(prompt)
    return _parse_1_to_5(text, "rubric specificity")


# ── Holistic judge (no rubric, single score) ─────────────────────────────────

def holistic_score(hypothesis_text: str) -> tuple[int, str]:
    prompt = f"""Rate this hypothesis's overall quality as an Alzheimer's disease
drug-repurposing proposal, 1-5, and briefly explain why.

Hypothesis: {hypothesis_text}

Reply with ONLY the number (1-5) on the first line, then a one-sentence
explanation on the second line."""

    text = _call_judge(prompt)
    return _parse_1_to_5(text, "holistic score")


# ── Pairwise judge (novelty + specificity, one call, A/B swap done by caller) ─

_PAIRWISE_DIMENSIONS = ("novelty", "specificity")


def pairwise_compare(
    text_a: str, text_b: str, label_a: str = "A", label_b: str = "B",
) -> dict:
    prompt = f"""You are a critical scientific reviewer comparing two Alzheimer's
disease drug-repurposing hypotheses.

Hypothesis {label_a}: {text_a}

Hypothesis {label_b}: {text_b}

Compare the two hypotheses on two dimensions. For each, pick the BETTER
hypothesis ({label_a} or {label_b}) and give exactly one sentence of
justification.

NOVELTY: Which hypothesis is more genuinely novel — proposing a distinct
mechanistic angle rather than a rephrasing of common, over-represented
mechanisms?
{label_a} or {label_b}
NOVELTY_JUSTIFICATION: one sentence

SPECIFICITY: Which hypothesis names more concrete, actionable targets (a
specific drug, pathway, mechanism, or measurable effect) rather than vague
general claims without naming what to test?
{label_a} or {label_b}
SPECIFICITY_JUSTIFICATION: one sentence

Reply in exactly this format (dimension labels uppercase, winner is
{label_a} or {label_b} only):
NOVELTY: <{label_a} or {label_b}>
NOVELTY_JUSTIFICATION: <one sentence>
SPECIFICITY: <{label_a} or {label_b}>
SPECIFICITY_JUSTIFICATION: <one sentence>"""

    text = _call_judge(prompt)
    winners: dict[str, str] = {}
    justifications: dict[str, str] = {}
    for dim in _PAIRWISE_DIMENSIONS:
        winner_re = re.compile(
            rf"^\s*{dim}\s*:\s*({re.escape(label_a)}|{re.escape(label_b)})\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        just_re = re.compile(
            rf"^\s*{dim}_justification\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE,
        )
        m = winner_re.search(text)
        if not m:
            raise RuntimeError(f"Pairwise response missing '{dim}:' line:\n{text[:500]}")
        winners[dim] = m.group(1).strip()
        jm = just_re.search(text)
        justifications[dim] = jm.group(1).strip() if jm else ""
    return {"winners": winners, "justifications": justifications, "raw": text}
