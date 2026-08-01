from __future__ import annotations

"""
Degradation module: generates specificity- and novelty-degraded variants of
Tier 1 hypotheses for the rubric-localization sub-experiment.

Uses the Groq generator (llama-3.3-70b-versatile by default), NOT the OpenAI
judge model, so the model that authors the degraded text is never the same
model that later scores it blind.
"""

import re

from generator import _call_generator, GenerationError


def _clean_hypothesis_text(text: str) -> str:
    text = text.strip().strip('"').strip()
    text = re.sub(r"\s+", " ", text)
    # Strip a leading "Rewritten hypothesis:" style label if the model adds one.
    text = re.sub(r"^(rewritten hypothesis|hypothesis)\s*:\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def specificity_degrade(original_text: str) -> str:
    """Strip molecular mechanism, keep compound + disease, make it vague."""
    prompt = f"""Rewrite the following Alzheimer's disease drug-repurposing hypothesis to
REMOVE all molecular mechanism detail (no named receptors, pathways, or
molecular targets), while keeping the same compound name and the same disease
link. Make it vague and generic, in the style of: "Liraglutide may affect brain
processes relevant to Alzheimer's disease." Do not add any new detail — only
strip detail out. Keep the compound name exactly as given.

Original hypothesis: {original_text}

Reply with ONLY the rewritten hypothesis sentence, nothing else."""

    text = _call_generator(prompt, temperature=0.3)
    result = _clean_hypothesis_text(text)
    if not result:
        raise GenerationError(f"Empty specificity-degraded output for: {original_text}")
    return result


def novelty_degrade(original_text: str) -> str:
    """Replace the specific mechanism with generic amyloid-cascade language, same compound."""
    prompt = f"""Rewrite the following Alzheimer's disease drug-repurposing hypothesis to
REPLACE its specific mechanism with the single most over-represented, generic
amyloid-cascade mechanism in the AD literature (e.g. "reduce amyloid-beta
accumulation and plaque formation"). Keep the EXACT SAME compound name — only
the mechanism/pathway language should change to this generic, over-used framing.

Original hypothesis: {original_text}

Reply with ONLY the rewritten hypothesis sentence, nothing else."""

    text = _call_generator(prompt, temperature=0.3)
    result = _clean_hypothesis_text(text)
    if not result:
        raise GenerationError(f"Empty novelty-degraded output for: {original_text}")
    return result
