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


def _call_generator(prompt: str, temperature: float = 0) -> str:
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
                temperature=temperature,
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
    temperature: float = 0,
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
            text = _call_generator(prompt, temperature=temperature)
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
    temperature: float = 0,
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

    text = _call_generator(prompt, temperature=temperature)
    return _parse_single_idea(text)


# ── Condition D: Structured Abstraction Before Retrieval ─────────────────────
#
# Domain-general analogical reasoning. Four steps per candidate:
#   1. Abstract the problem structure into domain-neutral language
#   2. Search for cross-domain solutions to that abstract structure
#   3. Map cross-domain solutions back to the target domain
#   4. Enforce diversity at the abstraction level (handled by the caller via
#      abstraction_history)
#
# None of the functions below are used by Conditions A, B, or C.

ABSTRACTION_PROMPT = """You are a domain-agnostic scientific reasoning assistant.

Read these research papers carefully:
{seed_papers}

Your task is to describe the core scientific challenge
in completely domain-neutral language.

Rules:
- Do NOT mention Alzheimer's disease, neurodegeneration,
  or any specific disease name
- Do NOT mention specific proteins, genes, or biological
  terms unless they describe a general class of mechanism
- Express the problem using this template:
  "A [type of process] causes [harmful outcome] through
   [specific mechanism]. The mechanism involves
   [key molecular/physical steps]. The goal is to
   [intervention objective] without [key constraint
   that makes this hard]."
- Be specific about the mechanism, not the domain
- The description should be recognisable as the same
  problem if encountered in a completely different field

Output ONLY the abstract problem description.
Nothing else."""


DIVERSITY_ABSTRACTION_PROMPT = """You are a domain-agnostic scientific reasoning assistant.

Read these research papers:
{seed_papers}

Previous abstract problem framings already explored:
{abstraction_history}

Your task is to describe the SAME underlying research
challenge from a structurally different angle.

Do not simply rephrase the previous framings with
different words. Identify a genuinely different
aspect of the problem structure — a different
mechanism, a different intervention point, or a
different way the problem manifests.

Apply the same rules as before:
- No disease-specific terminology
- Use the template: "A [process] causes [outcome]
  through [mechanism]. The goal is to [objective]
  without [constraint]."
- Be specific about mechanism, not domain

Output ONLY the new abstract problem description."""


# Weakness-targeted abstraction (Rounds 2 and 3). The focus instruction is
# injected based on the diagnosed weakness dimension.
_WEAKNESS_ABSTRACTION_FOCUS = {
    "novelty": (
        "Abstract the MECHANISM more specifically — drill into the precise "
        "molecular/physical steps so an analogous, less obvious solution from "
        "another field becomes findable."
    ),
    "consistency": (
        "Abstract the CAUSAL CHAIN more specifically — make each link from "
        "root process to harmful outcome explicit so the intervention point is "
        "unambiguous."
    ),
    "feasibility": (
        "Abstract the INTERVENTION CONSTRAINTS more specifically — make the "
        "practical limits (selectivity, delivery, reversibility) that make this "
        "hard explicit."
    ),
}

WEAKNESS_ABSTRACTION_PROMPT = """You are a domain-agnostic scientific reasoning assistant.

Read these research papers:
{seed_papers}

A current candidate intervention (for context only — do not copy it):
Problem: {problem}
Method: {method}
Contribution: {contribution}

This candidate is weak on the {weakness} dimension.
{focus}

Re-describe the underlying scientific challenge in completely
domain-neutral language, sharpening the aspect noted above.

Rules:
- Do NOT mention Alzheimer's disease, neurodegeneration, or any disease name
- Do NOT name specific drugs, proteins, or genes
- Use the template: "A [process] causes [outcome] through [mechanism].
  The mechanism involves [key steps]. The goal is to [objective]
  without [constraint]."
- Be specific about mechanism, not domain

Output ONLY the new abstract problem description. Nothing else."""


CROSS_DOMAIN_QUERY_PROMPT = """Given this abstract scientific problem:
"{abstraction}"

Generate a PubMed search query (5-8 words) that would
find papers from a completely different field that solved
an analogous problem.

Rules:
- Do NOT include: Alzheimer, neurodegeneration, dementia,
  brain, neuron, microglia, or any neuroscience term
- DO search in one of these domains only:
  oncology, cardiology, rheumatology, immunology,
  metabolic disease, pulmonology, or infectious disease
- The query should target the MECHANISM described in
  the abstract problem, not the disease context
- Focus on the intervention type, not the disease

Examples of good queries for different abstractions:
- "kinase cascade overactivation immune cells inhibitor"
- "aldosterone receptor inflammation organ fibrosis"
- "incretin receptor metabolic neuronal protection"
- "autophagy lysosomal pathway restoration aging"

Output ONLY the search query. Nothing else."""


MAPPING_PROMPT = """You are a scientific reasoning assistant specialising
in cross-domain analogical transfer.

The original research problem (in abstract terms):
{abstraction}

The original research context (seed papers):
{seed_papers_summary}

Papers from an adjacent field that solved an
analogous problem:
{retrieved_papers}

Your task: For each retrieved paper, identify the
core intervention principle it describes. Then ask:
what would that SAME PRINCIPLE look like if applied
to the original research context?

Do not copy the specific drug, compound, or technique
from the adjacent field directly. Instead, identify
WHAT PROPERTY makes it work, and find the equivalent
in the target domain (Alzheimer's disease drug repurposing).

First, in 2-4 sentences, explain the analogical transfer:
which adjacent-field principle you are borrowing and how it
maps onto the Alzheimer's context. Begin that block with
"Reasoning:".

Then generate ONE research hypothesis using this format:
Problem: [one sentence — the specific gap in the
          original research context]
Method: [one sentence — a specific intervention
         that applies the analogical principle,
         naming a specific drug, target, and model]
Contribution: [one sentence — what success looks like]

The method sentence MUST name:
- One specific FDA-approved drug or compound
- One specific molecular target or pathway
- One specific experimental model"""


MAPPING_PROMPT_NO_PAPERS = """You are a scientific reasoning assistant specialising
in cross-domain analogical transfer.

The original research problem (in abstract terms):
{abstraction}

The original research context (seed papers):
{seed_papers_summary}

No adjacent-field papers were retrieved for this abstraction.
Reason directly from the abstract problem structure: recall how
an analogous problem is solved in a different field (oncology,
cardiology, rheumatology, immunology, metabolic disease, or
pulmonology), then map that principle onto the Alzheimer's context.

First, in 2-4 sentences beginning with "Reasoning:", explain the
analogical principle you are borrowing and how it maps over.

Then generate ONE research hypothesis using this format:
Problem: [one sentence]
Method: [one sentence — naming a specific drug, target, and model]
Contribution: [one sentence]

The method sentence MUST name:
- One specific FDA-approved drug or compound
- One specific molecular target or pathway
- One specific experimental model"""


_CROSS_DOMAIN_BANNED = (
    "alzheimer", "alzheimers", "neurodegeneration", "neurodegenerative",
    "dementia", "brain", "neuron", "neuronal", "neurons", "microglia",
    "microglial", "neuroinflammation", "amyloid", "neuroscience",
)

_REASONING_RE = re.compile(
    r"reasoning\s*:?\s*(.+?)(?=\n\s*(?:\*{0,2})(?:problem)\s*:)",
    re.IGNORECASE | re.DOTALL,
)


def _format_abstraction_history(history: list[str]) -> str:
    if not history:
        return "(none yet)"
    return "\n".join(f"{i+1}. {a}" for i, a in enumerate(history))


def abstract_problem(
    seed_papers: list[dict],
    abstraction_history: list[str] | None = None,
    weakness_dimension: str | None = None,
    current_idea: dict | None = None,
) -> str:
    """
    Step 1 / Step 4 / Round 2-3: produce a domain-neutral abstraction of the
    seed-paper problem.

    - First candidate (no history, no weakness): ABSTRACTION_PROMPT
    - Candidates 2-5 (history given): DIVERSITY_ABSTRACTION_PROMPT
    - Refinement rounds (weakness_dimension given): WEAKNESS_ABSTRACTION_PROMPT
    """
    seed_block = _format_papers(seed_papers, SEED_TRUNCATE)

    if weakness_dimension and current_idea is not None:
        focus = _WEAKNESS_ABSTRACTION_FOCUS.get(
            weakness_dimension,
            _WEAKNESS_ABSTRACTION_FOCUS["novelty"],
        )
        prompt = WEAKNESS_ABSTRACTION_PROMPT.format(
            seed_papers=seed_block,
            problem=current_idea.get("problem", ""),
            method=current_idea.get("method", ""),
            contribution=current_idea.get("contribution", ""),
            weakness=weakness_dimension,
            focus=focus,
        )
    elif abstraction_history:
        prompt = DIVERSITY_ABSTRACTION_PROMPT.format(
            seed_papers=seed_block,
            abstraction_history=_format_abstraction_history(abstraction_history),
        )
    else:
        prompt = ABSTRACTION_PROMPT.format(seed_papers=seed_block)

    text = _call_generator(prompt)
    return re.sub(r"\s+", " ", text.replace("*", "")).strip()


def cross_domain_query(abstraction: str) -> str:
    """Step 2: derive a cross-domain PubMed query from an abstraction."""
    prompt = CROSS_DOMAIN_QUERY_PROMPT.format(abstraction=abstraction)
    text = _call_generator(prompt)
    query = re.sub(r"\s+", " ", text.replace("*", "")).strip()
    query = query.strip('"\'').rstrip(".")
    # Hard-strip any neuroscience terms that slipped through.
    kept = [
        w for w in query.split()
        if w.lower().strip(",.;:") not in _CROSS_DOMAIN_BANNED
    ]
    cleaned = " ".join(kept).strip()
    if len(cleaned.split()) < 3:
        cleaned = "mechanism pathway inhibition inflammation intervention"
    return cleaned


def map_cross_domain(
    abstraction: str,
    seed_papers: list[dict],
    retrieved_papers: list[dict],
) -> tuple[dict, str]:
    """
    Step 3: map adjacent-field solutions back to the Alzheimer's context.

    Returns (idea, analogy_mapping_reasoning). When no cross-domain papers were
    retrieved, reasons directly from the abstraction.
    """
    seed_summary = _format_papers(seed_papers, SEED_TRUNCATE)

    if retrieved_papers:
        paper_block = "\n".join(
            f"{i+1}. {p['title']}: {p.get('abstract', '')}"[:PAPER_TRUNCATE]
            for i, p in enumerate(retrieved_papers)
        )
        prompt = MAPPING_PROMPT.format(
            abstraction=abstraction,
            seed_papers_summary=seed_summary,
            retrieved_papers=paper_block,
        )
    else:
        prompt = MAPPING_PROMPT_NO_PAPERS.format(
            abstraction=abstraction,
            seed_papers_summary=seed_summary,
        )

    text = _call_generator(prompt)
    idea = _parse_single_idea(text)
    m = _REASONING_RE.search(text)
    reasoning = (
        re.sub(r"\s+", " ", m.group(1).replace("*", "")).strip()
        if m else ""
    )
    return idea, reasoning
