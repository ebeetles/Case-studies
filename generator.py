from __future__ import annotations

"""
Generation module: produces candidate research hypotheses via the Groq API.

Default model: llama-3.3-70b-versatile (Groq's current 70B Llama; 3.1 70B was
deprecated). Override with GENERATOR_MODEL env var.

Set GROQ_API_KEY in your environment before running.

Two functions:
  - generate_candidates: given seed papers + optional retrieved papers, produce n ideas
  - refine_candidate:    improve a single idea based on diagnosed weakness + gap papers

Raises GenerationError on any API or parse failure.
"""

import os
import re

from groq import Groq

GENERATOR_MODEL = os.environ.get("GENERATOR_MODEL", "llama-3.3-70b-versatile")

SEED_TRUNCATE   = 300
PAPER_TRUNCATE  = 300
FEEDBACK_TRUNCATE = 400

_client: Groq | None = None


class GenerationError(RuntimeError):
    pass


def _get_api_key() -> str:
    raw = os.environ.get("GROQ_API_KEY", "")
    key = raw.strip()
    if not key:
        raise GenerationError(
            "GROQ_API_KEY is not set. Export your key before running:\n"
            "  export GROQ_API_KEY='gsk_...'"
        )
    if raw != key:
        os.environ["GROQ_API_KEY"] = key
    if any(c in key for c in "\n\r\t"):
        raise GenerationError(
            "GROQ_API_KEY contains whitespace inside the key. "
            "Re-export on one line with no trailing newline."
        )
    return key


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=_get_api_key(), timeout=60.0)
    return _client


def is_valid_idea(idea: dict | None) -> bool:
    """Return True if idea has non-empty problem, method, and contribution."""
    if not idea:
        return False
    return all(idea.get(k, "").strip() for k in ("problem", "method", "contribution"))


def _format_papers(papers: list[dict], truncate: int) -> str:
    lines = []
    for i, p in enumerate(papers, 1):
        snippet = f"{p['title']}: {p.get('abstract', '')}"[:truncate]
        lines.append(f"{i}. {snippet}")
    return "\n".join(lines)


def _call_generator(prompt: str) -> str:
    """Call the generator model via Groq. Raises GenerationError on failure."""
    client = _get_client()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=GENERATOR_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            text = r.choices[0].message.content
            if text and text.strip():
                return text.strip()
            raise GenerationError("Groq returned an empty message.")
        except GenerationError:
            raise
        except Exception as e:
            last_err = e
            print(f"  [generator] Groq error (attempt {attempt+1}/3): {e}")
    raise GenerationError(f"Generator failed after 3 attempts: {last_err}") from last_err


def _clean_field_value(text: str) -> str:
    """Normalize a parsed field value (strip markdown noise, collapse whitespace)."""
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_single_idea(block: str) -> dict:
    """Extract Problem, Method, Contribution. Raises GenerationError if incomplete."""
    text = block.strip()
    result: dict[str, str] = {}

    field_line = re.compile(
        r"^\s*(?:\*{1,2}|#{1,3}\s*)?(Problem|Method|Contribution)\s*:?\s*\*{0,2}\s*(.*)$",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        m = field_line.match(line)
        if m:
            result[m.group(1).lower()] = _clean_field_value(m.group(2))

    if not is_valid_idea(result):
        for field in ("problem", "method", "contribution"):
            if result.get(field):
                continue
            m = re.search(
                rf"(?:\*{{1,2}}|#{{1,3}}\s*)?{field}\s*:?\s*\*{{0,2}}\s*"
                rf"(.+?)(?=\n\s*(?:\*{{1,2}}|#{{1,3}}\s*)?(?:problem|method|contribution)\s*:|\Z)",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            if m:
                result[field] = _clean_field_value(m.group(1))

    if not is_valid_idea(result):
        raise GenerationError(
            f"Could not parse idea (missing fields). Model output:\n{text[:500]}"
        )
    for field, value in result.items():
        if re.search(r"\[(?:revised or same|one sentence)", value, re.IGNORECASE):
            raise GenerationError(
                f"Model echoed prompt placeholder in {field}: {value[:200]}"
            )
    return result


def _build_literature_block(seed_papers: list[dict], retrieved_papers: list[dict]) -> str:
    literature = _format_papers(seed_papers, SEED_TRUNCATE)
    if retrieved_papers:
        literature += "\n" + _format_papers(retrieved_papers, PAPER_TRUNCATE)
    return literature


def _format_existing_ideas(ideas: list[dict]) -> str:
    lines = []
    for i, idea in enumerate(ideas, 1):
        lines.append(
            f"{i}. Problem: {idea['problem']}\n"
            f"   Method: {idea['method']}\n"
            f"   Contribution: {idea['contribution']}"
        )
    return "\n".join(lines)


def _generation_prompt(literature: str, existing: list[dict]) -> str:
    diversity = ""
    if existing:
        diversity = f"""
These hypotheses were already generated — yours must be clearly different
(different drug/target, mechanism, or approach):
{_format_existing_ideas(existing)}
"""
    return f"""You are a biomedical research assistant helping generate novel drug repurposing hypotheses for Alzheimer's disease.

Here is relevant literature:
{literature}
{diversity}
Generate ONE distinct research hypothesis for drug repurposing in Alzheimer's disease that goes BEYOND what is already described in these papers.

Use EXACTLY this plain-text format (no markdown, no bold, no bullets):

Problem: [one sentence]
Method: [one sentence]
Contribution: [one sentence]"""


def check_generator_ready() -> None:
    """Verify Groq is reachable. Raises GenerationError on failure."""
    _call_generator("Reply with exactly: OK")


def generate_candidates(
    seed_papers: list[dict],
    retrieved_papers: list[dict],
    n: int = 5,
) -> list[dict]:
    """Generate exactly n candidate research ideas. Raises on any failure."""
    literature = _build_literature_block(seed_papers, retrieved_papers)
    ideas: list[dict] = []
    seen: set[tuple] = set()

    max_dup_retries = 3
    for i in range(1, n + 1):
        idea: dict | None = None
        for attempt in range(max_dup_retries):
            prompt = _generation_prompt(literature, ideas)
            if attempt > 0:
                prompt += (
                    f"\n\nYour previous answer duplicated an existing hypothesis. "
                    f"Attempt {attempt + 1}: pick a different drug class, molecular "
                    f"target, or biological pathway."
                )
            text = _call_generator(prompt)
            candidate = _parse_single_idea(text)
            key = tuple(candidate.items())
            if key not in seen:
                idea = candidate
                break
            print(
                f"  [generator]   Duplicate at {i}/{n} "
                f"(attempt {attempt+1}/{max_dup_retries}), retrying..."
            )
        if idea is None:
            raise GenerationError(
                f"Could not generate a unique idea at {i}/{n} "
                f"after {max_dup_retries} attempts."
            )
        ideas.append(idea)
        seen.add(tuple(idea.items()))
        print(f"  [generator]   Got idea {i}/{n}")

    return ideas


def refine_candidate(
    idea: dict,
    weakness_type: str,
    weakness_text: str,
    gap_papers: list[dict],
    is_ood: bool = False,
) -> dict:
    """
    Revise a single idea to address its diagnosed weakness.

    When is_ood=True (Condition C), papers are framed as inspiration from adjacent
    fields and the generator is instructed not to copy their mechanisms directly.
    When is_ood=False (Condition B), uses direct evidence framing.
    Raises on failure.
    """
    if not gap_papers:
        raise GenerationError("refine_candidate called with no gap papers.")

    feedback = weakness_text[:FEEDBACK_TRUNCATE]

    if is_ood:
        paper_block = "\n".join(
            f"Inspiration {i+1} (from adjacent field): "
            f"{p['title']}: {p.get('abstract', '')}"[:PAPER_TRUNCATE]
            for i, p in enumerate(gap_papers)
        )
        prompt = f"""You are a biomedical research assistant helping improve a research hypothesis.

Current hypothesis:
Problem: {idea['problem']}
Method: {idea['method']}
Contribution: {idea['contribution']}

Identified weakness: {feedback}

The following papers are from ADJACENT fields and solved analogous problems differently. Use them as INSPIRATION only — do not copy their specific targets, drugs, or mechanisms directly into the hypothesis. Instead, ask: what PRINCIPLE from these papers could be applied differently to the Alzheimer's context?

{paper_block}

Revise the hypothesis to address the weakness using inspiration from these adjacent approaches. Follow these rules strictly:
- Make the method MORE specific, not more comprehensive
- Do NOT add new diseases, targets, or mechanisms beyond what is necessary to fix the specific weakness
- The revised method sentence must be SHORTER than or equal to the current method sentence in word count
- Do not mention the adjacent field papers directly

Use exactly this format:
Problem: [revised or unchanged]
Method: [revised — must be shorter or equal length]
Contribution: [revised or unchanged]"""
    else:
        paper_block = _format_papers(gap_papers, PAPER_TRUNCATE)
        prompt = f"""You are a biomedical research assistant.

Here is a research hypothesis that needs improvement:
Problem: {idea['problem']}
Method: {idea['method']}
Contribution: {idea['contribution']}

The main weakness identified was: {weakness_type}
Specific feedback: {feedback}

Here are papers specifically relevant to addressing this weakness:
{paper_block}

Revise the hypothesis to address ONLY the identified weakness.
Do NOT add new concepts, mechanisms, or approaches.
Make it MORE specific, not more comprehensive.
Keep the revised idea to the same length or shorter than the original.
Use EXACTLY this plain-text format (no markdown, no bold, no bullets):

Problem: [revised or same]
Method: [revised to address weakness]
Contribution: [revised or same]"""

    text = _call_generator(prompt)
    return _parse_single_idea(text)
