from __future__ import annotations

"""
Generation module: produces candidate research hypotheses via the Groq API.

Default model: llama-3.3-70b-versatile.
Override with GENERATOR_MODEL env var.

Set GROQ_API_KEY in your environment before running.

Two functions:
  - generate_candidates: given seed papers + optional retrieved papers, produce n ideas
  - refine_candidate:    improve a single idea based on diagnosed weakness + gap papers

Raises GenerationError on any API or parse failure.
"""

import os
import re
import time

from groq import Groq

_DEFAULT_GENERATOR = "llama-3.3-70b-versatile"
_stale_model_warned = False


def get_generator_model() -> str:
    """Resolve the active Groq model, ignoring stale Gemini env overrides."""
    global _stale_model_warned
    model = os.environ.get("GENERATOR_MODEL", _DEFAULT_GENERATOR).strip()
    if model and model.startswith("gemini"):
        if not _stale_model_warned:
            print(
                f"  [generator] Ignoring stale GENERATOR_MODEL '{model}' "
                f"→ {_DEFAULT_GENERATOR}"
            )
            _stale_model_warned = True
        return _DEFAULT_GENERATOR
    return model or _DEFAULT_GENERATOR


GENERATOR_MODEL = _DEFAULT_GENERATOR

SEED_TRUNCATE     = 300
PAPER_TRUNCATE    = 300
FEEDBACK_TRUNCATE = 400

_client: Groq | None = None

METHOD_SPECIFICITY_CONSTRAINT = """Your Method sentence MUST name:
- One specific drug or compound by name
- One specific biological target or pathway
- One specific experimental model or validation approach"""

CONDITION_A_NOVELTY_CONSTRAINT = """Do not propose any drug or intervention that has already been investigated for Alzheimer's disease in clinical trials or published research. Only propose connections that combine mechanisms in ways not yet tested."""


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


def _rate_limit_wait_seconds(err: Exception) -> float | None:
    """Parse a suggested wait time from a 429 / rate-limit error message."""
    msg = str(err)
    m = re.search(r"try again in (\d+)m([\d.]+)s", msg, re.IGNORECASE)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    m = re.search(r"try again in ([\d.]+)s", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"retry.{0,30}after.{0,10}(\d+)", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _is_rate_limit(err: Exception) -> bool:
    msg = str(err).lower()
    return "rate_limit" in msg or "error code: 429" in msg or "429" in msg


def _call_generator(prompt: str) -> str:
    """Call Groq. Retries on rate-limit with wait; raises GenerationError on failure."""
    client = _get_client()
    last_err: Exception | None = None
    non_rate_attempts = 0
    max_attempts = 8
    model = get_generator_model()

    for attempt in range(1, max_attempts + 1):
        try:
            r = client.chat.completions.create(
                model=model,
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
            wait = _rate_limit_wait_seconds(e)
            if _is_rate_limit(e) and attempt < max_attempts:
                wait_secs = min((wait or 60) + 2, 900)
                mins, secs = divmod(int(wait_secs), 60)
                print(
                    f"  [generator] Rate limit on {model} — "
                    f"waiting {mins}m{secs}s before retry ({attempt}/{max_attempts})..."
                )
                time.sleep(wait_secs)
                continue
            non_rate_attempts += 1
            print(f"  [generator] Groq error (attempt {attempt}): {e}")
            if non_rate_attempts >= 3:
                break

    if last_err and _is_rate_limit(last_err):
        raise GenerationError(
            f"Groq token quota exhausted for {model}. "
            "Wait for the daily limit to reset, upgrade your Groq tier, or "
            f"set GENERATOR_MODEL to a smaller model. Last error: {last_err}"
        ) from last_err
    raise GenerationError(f"Generator failed after retries: {last_err}") from last_err


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


def _generation_prompt(
    literature: str,
    existing: list[dict],
    condition: str | None = None,
) -> str:
    diversity = ""
    if existing:
        diversity = f"""
These hypotheses were already generated — yours must be clearly different
(different drug/target, mechanism, or approach):
{_format_existing_ideas(existing)}
"""
    condition_a_rule = ""
    if condition == "A":
        condition_a_rule = f"\n{CONDITION_A_NOVELTY_CONSTRAINT}\n"
    return f"""You are a biomedical research assistant helping generate novel drug repurposing hypotheses for Alzheimer's disease.

Here is relevant literature:
{literature}
{diversity}
Generate ONE distinct research hypothesis for drug repurposing in Alzheimer's disease that goes BEYOND what is already described in these papers.
{condition_a_rule}
{METHOD_SPECIFICITY_CONSTRAINT}

Use EXACTLY this plain-text format (no markdown, no bold, no bullets):

Problem: [one sentence]
Method: [one sentence — must include the drug, target/pathway, and experimental model named above]
Contribution: [one sentence]"""


def check_generator_ready() -> None:
    """Verify Groq is reachable. Raises GenerationError on failure."""
    _call_generator("Reply with exactly: OK")


def generate_candidates(
    seed_papers: list[dict],
    retrieved_papers: list[dict],
    n: int = 5,
    condition: str | None = None,
) -> list[dict]:
    """Generate exactly n candidate research ideas. Raises on any failure."""
    literature = _build_literature_block(seed_papers, retrieved_papers)
    ideas: list[dict] = []
    seen: set[tuple] = set()

    max_dup_retries = 3
    for i in range(1, n + 1):
        idea: dict | None = None
        for attempt in range(max_dup_retries):
            prompt = _generation_prompt(literature, ideas, condition=condition)
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
- {METHOD_SPECIFICITY_CONSTRAINT}

Use exactly this format:
Problem: [revised or unchanged]
Method: [revised — must be shorter or equal length and include the drug, target/pathway, and experimental model named above]
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
{METHOD_SPECIFICITY_CONSTRAINT}
Use EXACTLY this plain-text format (no markdown, no bold, no bullets):

Problem: [revised or same]
Method: [revised to address weakness — must include the drug, target/pathway, and experimental model named above]
Contribution: [revised or same]"""

    text = _call_generator(prompt)
    return _parse_single_idea(text)
