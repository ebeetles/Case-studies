from __future__ import annotations

"""
Sourced hypothesis data for rubric validation (see hypothesis_validation_sources.md).

Hypotheses are copied verbatim from the sources doc's "Hypothesis (your format)"
fields — already reformatted into the fixed template there. Tier assignment is
external ground truth (clinical trial stage / validation history), established
before any rubric is applied.
"""

TIERED_HYPOTHESES: list[dict] = [
    # ── Tier 1 — reached dedicated AD clinical trials ──────────────────────
    {
        "source_id": "T1-A",
        "tier": 1,
        "compound": "Metformin",
        "text": (
            "Metformin may activate AMPK and modulate the mTOR pathway to reduce "
            "neuroinflammation and tau pathology relevant to Alzheimer's disease."
        ),
    },
    {
        "source_id": "T1-B",
        "tier": 1,
        "compound": "Liraglutide",
        "text": (
            "Liraglutide may activate the GLP-1 receptor to reduce neuroinflammation, "
            "improve neuronal insulin signaling, and slow cortical atrophy relevant to "
            "Alzheimer's disease."
        ),
    },
    {
        "source_id": "T1-C",
        "tier": 1,
        "compound": "Pioglitazone",
        "text": (
            "Pioglitazone may activate PPAR-γ to stabilize cerebral glucose and "
            "lipid metabolism and reduce neuroinflammation relevant to delaying "
            "Alzheimer's disease onset."
        ),
    },
    {
        "source_id": "T1-D",
        "tier": 1,
        "compound": "Losartan",
        "text": (
            "Losartan may antagonize the angiotensin II type 1 receptor to reduce "
            "oxidative stress and cerebrovascular dysfunction relevant to slowing "
            "Alzheimer's disease progression."
        ),
    },
    {
        "source_id": "T1-E",
        "tier": 1,
        "compound": "Sildenafil",
        "text": (
            "Sildenafil may inhibit phosphodiesterase-5 to increase cGMP signaling "
            "and reduce tau phosphorylation and amyloid accumulation relevant to "
            "Alzheimer's disease."
        ),
    },
    # ── Tier 2 — computational/preclinical, specific mechanism, no AD trial ─
    {
        "source_id": "T2-A",
        "tier": 2,
        "compound": "Baclofen",
        "text": (
            "Baclofen may act on GABA-B receptor signaling to produce non-redundant "
            "modulation of Alzheimer's disease network pathophysiology."
        ),
    },
    {
        "source_id": "T2-B",
        "tier": 2,
        "compound": "Ibudilast",
        "text": (
            "Ibudilast may inhibit phosphodiesterase and neuroinflammatory glial "
            "activation to reduce amyloid and tau pathology relevant to Alzheimer's "
            "disease."
        ),
    },
    {
        "source_id": "T2-C",
        "tier": 2,
        "compound": "Chenodiol",
        "text": (
            "Chenodiol may act as a primary bile acid modulating an AD-related "
            "endophenotype network to produce disease-relevant molecular effects in "
            "Alzheimer's disease."
        ),
    },
    {
        "source_id": "T2-D",
        "tier": 2,
        "compound": "Arundine",
        "text": (
            "Arundine may modulate AD-associated endophenotype pathways to produce "
            "protective molecular effects relevant to Alzheimer's disease."
        ),
    },
    {
        "source_id": "T2-E",
        "tier": 2,
        "compound": "Acamprosate",
        "text": (
            "Acamprosate may modulate glutamatergic signaling to produce "
            "non-redundant impact on Alzheimer's disease network pathophysiology."
        ),
    },
    # ── Tier 3 — nominated candidates, little/no mechanistic hypothesis ─────
    {
        "source_id": "T3-A",
        "tier": 3,
        "compound": "Clozapine",
        "text": "Clozapine may have effects relevant to Alzheimer's disease.",
    },
    {
        "source_id": "T3-B",
        "tier": 3,
        "compound": "Verapamil",
        "text": (
            "Verapamil, a calcium channel blocker, may be beneficial in Alzheimer's "
            "disease."
        ),
    },
    {
        "source_id": "T3-C",
        "tier": 3,
        "compound": "Tamoxifen",
        "text": (
            "Tamoxifen, a selective estrogen receptor modulator, may have a "
            "repurposing role in Alzheimer's disease."
        ),
    },
    {
        "source_id": "T3-D",
        "tier": 3,
        "compound": "Adenosine",
        "text": "Adenosine may have relevance to Alzheimer's disease treatment.",
    },
    {
        "source_id": "T3-E",
        "tier": 3,
        "compound": "Vandetanib",
        "text": (
            "Vandetanib, a tyrosine kinase inhibitor, may be repurposable for "
            "Alzheimer's disease."
        ),
    },
]

TIER1_SOURCE_IDS = [h["source_id"] for h in TIERED_HYPOTHESES if h["tier"] == 1]
