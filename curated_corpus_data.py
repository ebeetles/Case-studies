from __future__ import annotations

"""
Hand-curated dated corpus for the novelty-decay experiment (HindSight-style
time-split validation, adapted from Jiang 2026 arXiv:2603.15164).

Replaces the Semantic Scholar scraper, which stalled on persistent 429s from
the unauthenticated public API (see build_corpus.py / novelty_decay_curated_corpus.md).
Sourced from novelty_decay_curated_corpus.md plus abstracts/summaries pulled
via targeted web searches (2-3 per compound). Where a full abstract wasn't
retrievable, the review-article summary text is used instead, noted inline.

Only the two HIGH CONFIDENCE compounds per the curated doc: metformin and
sildenafil. Losartan/pioglitazone/liraglutide are lower-confidence estimates,
deferred pending a decision to extend.
"""

CUTOFFS = {
    "metformin": {
        "date": "2012-01-01",
        "note": (
            "First mechanistic AMPK/mTOR-BACE1-AD proposals (Gupta, Bisht & Dey "
            "2011; Li et al. 2012). Cutoff set to the Li et al. 2012 publication "
            "boundary per novelty_decay_curated_corpus.md."
        ),
        "confidence": "high",
    },
    "sildenafil": {
        "date": "2021-12-06",
        "note": (
            "Fang et al., Nature Aging, published online 2021-12-06 — original "
            "computational (network-medicine) identification of sildenafil as an "
            "AD candidate. NOTE: this differs from the general PDE5/AD mechanistic "
            "biology literature (e.g. Puzzo et al. 2009), which predates this by "
            "over a decade — this cutoff specifically tests the computational-"
            "repurposing-identification framing, per novelty_decay_curated_corpus.md."
        ),
        "confidence": "high",
    },
}

CURATED_PAPERS: dict[str, dict[str, list[dict]]] = {
    "metformin": {
        "pre": [
            {
                "title": (
                    "The Antidiabetic Drug Metformin Activates the AMP-Activated "
                    "Protein Kinase Cascade via an Adenine Nucleotide-Independent "
                    "Mechanism"
                ),
                "abstract": (
                    "Metformin activates AMP-activated protein kinase (AMPK) in "
                    "intact cells, stimulating phosphorylation of the key regulatory "
                    "site (Thr-172) on the catalytic alpha subunit. This occurs via "
                    "an adenine-nucleotide-independent mechanism distinct from "
                    "classical AMPK activators, and underlies metformin's effects "
                    "on hepatic glucose production and lipid metabolism. No mention "
                    "of Alzheimer's disease or neurodegeneration."
                ),
                "year": 2002,
                "source": "Hawley et al., Diabetes 2002;51(8):2420-2425",
            },
            {
                "title": (
                    "Role of AMP-activated protein kinase in mechanism of metformin "
                    "action"
                ),
                "abstract": (
                    "Metformin lowers hepatic glucose production and increases "
                    "insulin sensitivity via AMPK activation, with downstream "
                    "effects on gene expression of lipogenic enzymes and glucose "
                    "uptake in skeletal muscle. Focused entirely on diabetes and "
                    "hepatic/muscle metabolism; no discussion of neurodegenerative "
                    "disease or brain mechanisms."
                ),
                "year": 2001,
                "source": "Zhou et al., J Clin Invest 2001",
            },
            {
                "title": (
                    "The Amyloid Hypothesis of Alzheimer's Disease: Progress and "
                    "Problems on the Road to Therapeutics"
                ),
                "abstract": (
                    "Reviews the amyloid cascade hypothesis of Alzheimer's disease, "
                    "covering amyloid-beta production, aggregation, and downstream "
                    "tau pathology, and surveys candidate therapeutic strategies "
                    "targeting amyloid processing. No mention of metformin, AMPK, or "
                    "any diabetes-drug repurposing angle."
                ),
                "year": 2002,
                "source": "Hardy & Selkoe, Science 2002",
            },
        ],
        "post": [
            {
                "title": (
                    "AMPK/mTOR/S6K/BACE1 signaling pathway regulation by metformin "
                    "reduces amyloid-beta production (summarized mechanism)"
                ),
                "abstract": (
                    "Metformin activates AMPK in brain tissue, which modulates the "
                    "mTOR/S6K1 signaling axis and reduces BACE1-mediated processing "
                    "of amyloid precursor protein, decreasing amyloid-beta "
                    "production and toxicity in cell and rodent AD models. Full "
                    "abstract not directly retrievable; text is the mechanism "
                    "summary as cited in later reviews (e.g. Liao et al. 2022)."
                ),
                "year": 2012,
                "source": "Li et al. 2012 (cited via Liao et al. 2022 review) — abstract text approximated, see note",
            },
            {
                "title": (
                    "Deciphering the Roles of Metformin in Alzheimer's Disease: "
                    "A Snapshot"
                ),
                "abstract": (
                    "Metformin, a first-line Type 2 Diabetes medication, exerts "
                    "multiple beneficial effects on neurodegenerative disorders "
                    "including Alzheimer's disease. Clinical studies show metformin "
                    "use is associated with lower AD risk and better cognitive "
                    "performance, modified by diabetic status and APOE-e4 status. "
                    "Mechanistic studies have unveiled effects on amyloid-beta "
                    "deposition, tau phosphorylation, chronic neuroinflammation, "
                    "insulin resistance, glucose metabolism and mitochondrial "
                    "dysfunction, though findings remain limited and controversial."
                ),
                "year": 2022,
                "source": "Liao et al., Front Pharmacol 2022;12:728315",
            },
            {
                "title": (
                    "Causal inference and systems pharmacology for the identification "
                    "of metformin as an Alzheimer's-relevant drug (summarized)"
                ),
                "abstract": (
                    "Target-trial emulation using electronic health record data "
                    "combined with systems pharmacology analysis provides causal "
                    "evidence for metformin's association with reduced dementia "
                    "incidence, and identifies suppression of APOE and SPP1 "
                    "expression in human neural cells as a candidate mechanism."
                ),
                "year": 2022,
                "source": "Charpignon et al., Nat Commun 2022 — abstract text approximated, see note",
            },
        ],
    },
    "sildenafil": {
        "pre": [
            {
                "title": (
                    "Cardiac phosphodiesterase 5 (cGMP-specific) modulates "
                    "beta-adrenergic signaling in vivo and is down-regulated in "
                    "heart failure"
                ),
                "abstract": (
                    "Characterizes PDE5 expression and function in cardiac tissue, "
                    "its role in modulating cGMP-mediated beta-adrenergic signaling, "
                    "and its downregulation in heart failure. Purely cardiovascular; "
                    "no mention of Alzheimer's disease, neurodegeneration, or drug "
                    "repurposing."
                ),
                "year": 2001,
                "source": "PubMed 11481219",
            },
            {
                "title": "Network medicine: a network-based approach to human disease",
                "abstract": (
                    "Introduces the network-medicine framework: mapping the "
                    "interactome and disease-gene associations to understand "
                    "molecular relationships between distinct disease phenotypes, "
                    "with implications for drug discovery and repurposing. General "
                    "methodological review; does not mention sildenafil, PDE5, or "
                    "Alzheimer's disease specifically."
                ),
                "year": 2011,
                "source": "Barabasi, Gulbahce & Loscalzo, Nat Rev Genet 2011",
            },
            {
                "title": "Oral Sildenafil in the Treatment of Erectile Dysfunction",
                "abstract": (
                    "Randomized controlled trial establishing sildenafil's efficacy "
                    "and safety as an oral PDE5-inhibitor treatment for erectile "
                    "dysfunction. Purely a urology/sexual-medicine indication study; "
                    "no mention of cognitive, neurological, or Alzheimer's-relevant "
                    "endpoints."
                ),
                "year": 1998,
                "source": "Goldstein et al., N Engl J Med 1998",
            },
        ],
        "post": [
            {
                "title": (
                    "Endophenotype-based in silico network medicine discovery "
                    "combined with insurance record data mining identifies "
                    "sildenafil as a candidate drug for Alzheimer's disease"
                ),
                "abstract": (
                    "Develops an endophenotype disease-module methodology for AD "
                    "drug repurposing, constructing networks of AD-associated genes "
                    "and drug-target interactions across 1,600+ FDA-approved drugs "
                    "to identify sildenafil as a candidate disease-risk modifier. "
                    "Retrospective case-control analysis of insurance claims for "
                    "7.23 million individuals found sildenafil use associated with "
                    "a 69% reduced risk of AD; sildenafil also increased neurite "
                    "growth and decreased phospho-tau in iPSC-derived AD neuron "
                    "models."
                ),
                "year": 2021,
                "source": "Fang et al., Nature Aging 2021;1(12):1175-1188",
            },
            {
                "title": "PDE5 inhibitor drugs for use in dementia",
                "abstract": (
                    "Reviews the rationale for repurposing licensed PDE5 inhibitors "
                    "(sildenafil, vardenafil, tadalafil) for dementia. PDE5 is "
                    "widely expressed in vascular myocytes, neurons, and glia; "
                    "animal data indicate cognitive benefits, and real-world human "
                    "data suggest sildenafil and vardenafil are associated with "
                    "reduced dementia risk. Concludes prospective clinical trials "
                    "are warranted."
                ),
                "year": 2023,
                "source": "Hainsworth et al., Alzheimers Dement Transl Res Clin Interv 2023;9:e12412",
            },
            {
                "title": (
                    "Sildenafil candidate validation in iPSC-derived neurons and "
                    "5xFAD mice for Alzheimer's disease (summarized)"
                ),
                "abstract": (
                    "Validates sildenafil's mechanistic effects in patient-derived "
                    "iPSC neurons and 5xFAD transgenic mice: PDE5 inhibition "
                    "increases cGMP signaling, reduces phospho-tau181, and "
                    "decreases amyloid-beta, supporting the network-medicine "
                    "candidate identification with direct experimental evidence."
                ),
                "year": 2025,
                "source": "Li et al., Alzheimers Dement 2025 — abstract text approximated, see note",
            },
        ],
    },
}

HYPOTHESIS_TEXT = {
    "metformin": (
        "Metformin may activate AMPK and modulate the mTOR pathway to reduce "
        "neuroinflammation and tau pathology relevant to Alzheimer's disease."
    ),
    "sildenafil": (
        "Sildenafil may inhibit phosphodiesterase-5 to increase cGMP signaling "
        "and reduce tau phosphorylation and amyloid accumulation relevant to "
        "Alzheimer's disease."
    ),
}
