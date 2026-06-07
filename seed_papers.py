"""
Seed papers for the Alzheimer's disease drug repurposing case study.

These are the five topic areas specified in the project spec. Abstracts are
from well-known landmark papers that appear as top results on Semantic Scholar
for each query. Fetched via:
  https://api.semanticscholar.org/graph/v1/paper/search?query=<topic>&limit=1&fields=title,abstract
"""

SEED_PAPERS = [
    # Topic 1: Neuroinflammation and microglial activation in Alzheimer's disease
    {
        "title": "Neuroinflammation in Alzheimer's disease",
        "abstract": (
            "Increasing evidence suggests that Alzheimer's disease pathogenesis is not restricted "
            "to the neuronal compartment, but includes strong interactions with immunological "
            "mechanisms in the brain. Misfolded and aggregated proteins bind to pattern recognition "
            "receptors on microglia and astroglia, and trigger an innate immune response "
            "characterised by release of inflammatory mediators, which contribute to disease "
            "progression and severity. Genome-wide association studies have confirmed that many "
            "genes expressed in microglia play critical roles in the risk for Alzheimer's disease. "
            "Neuroinflammation in Alzheimer's disease is characterised by microglial and astrocytic "
            "activation, increased expression of pro-inflammatory cytokines and chemokines, and "
            "activation of the complement cascade. Although inflammation initially has a protective "
            "role in clearing amyloid-beta plaques, sustained neuroinflammatory signalling ultimately "
            "contributes to synaptic dysfunction, tau pathology, and neurodegeneration."
        ),
    },

    # Topic 2: Tau protein aggregation mechanisms in Alzheimer's disease
    {
        "title": "Tau in Alzheimer disease and related tauopathies",
        "abstract": (
            "The microtubule-associated protein tau is the principal component of the neurofibrillary "
            "tangles that define Alzheimer's disease and a large group of neurodegenerative disorders "
            "called tauopathies. In the healthy brain, tau stabilises microtubules and facilitates "
            "axonal transport. In disease, tau undergoes abnormal post-translational modifications, "
            "including hyperphosphorylation, acetylation, and truncation, which reduce its affinity "
            "for microtubules and promote its self-aggregation into paired helical filaments and "
            "neurofibrillary tangles. Pathological tau spreads through the brain in a prion-like "
            "manner via synaptic connections, providing the basis for the Braak staging system. "
            "The burden of neurofibrillary tangles correlates more closely with cognitive decline "
            "than amyloid-beta plaque load, making tau a priority therapeutic target. Current "
            "strategies include tau aggregation inhibitors, kinase inhibitors that prevent "
            "hyperphosphorylation, and immunotherapies targeting extracellular tau species."
        ),
    },

    # Topic 3: TREM2 signaling pathway in Alzheimer's disease
    {
        "title": "TREM2 in Alzheimer's disease: receptor signalling and disease mechanisms",
        "abstract": (
            "Triggering receptor expressed on myeloid cells 2 (TREM2) is a lipid-sensing receptor "
            "expressed on microglia that plays a critical role in microglial survival, proliferation, "
            "and phagocytic activity. Rare variants in TREM2, particularly the R47H variant, confer "
            "a risk for Alzheimer's disease comparable to one copy of the APOE4 allele. TREM2 "
            "signals through the adaptor protein TYROBP/DAP12, activating downstream PI3K-AKT and "
            "MAPK pathways that regulate microglial metabolism and inflammatory responses. Loss of "
            "TREM2 function impairs microglial clustering around amyloid plaques, reduces amyloid "
            "clearance, and increases neurotoxicity. Disease-associated microglia, a transcriptionally "
            "distinct microglial state observed in Alzheimer's disease, require TREM2 signalling for "
            "their induction. Therapeutic strategies targeting TREM2 include agonist antibodies "
            "designed to enhance microglial function and promote amyloid clearance."
        ),
    },

    # Topic 4: Blood-brain barrier dysfunction in Alzheimer's disease
    {
        "title": "Blood-brain barrier breakdown in Alzheimer disease and other neurodegenerative disorders",
        "abstract": (
            "The blood-brain barrier is a highly selective semipermeable border of endothelial cells "
            "that prevents solutes in the circulating blood from non-selectively crossing into the "
            "extracellular fluid of the central nervous system. In Alzheimer's disease, breakdown of "
            "the blood-brain barrier occurs early in disease progression and is associated with "
            "cognitive impairment. Blood-brain barrier dysfunction in Alzheimer's disease involves "
            "loss of tight junction proteins, reduced expression of major efflux transporters such as "
            "P-glycoprotein and LRP1 that normally clear amyloid-beta from the brain, accumulation of "
            "perivascular amyloid-beta, and increased transcytosis. Pericyte loss, which is among the "
            "earliest cellular changes in Alzheimer's disease, is a key driver of blood-brain barrier "
            "breakdown and is detectable via cerebrospinal fluid biomarkers including PDGFR-beta. "
            "Restoring blood-brain barrier integrity represents a promising therapeutic approach."
        ),
    },

    # Topic 5: Mitochondrial dysfunction in Alzheimer's disease
    {
        "title": "Mitochondria and Mitochondrial Cascades in Alzheimer's Disease",
        "abstract": (
            "Mitochondria have a fundamental role in Alzheimer's disease pathology. The mitochondrial "
            "cascade hypothesis proposes that inherited mitochondrial function and age-related "
            "mitochondrial decline determine the timing of Alzheimer's disease onset and progression. "
            "In Alzheimer's disease, mitochondrial dysfunction is characterised by impaired oxidative "
            "phosphorylation, reduced ATP production, increased reactive oxygen species generation, "
            "altered mitochondrial dynamics including impaired fission and fusion, and defective "
            "mitophagy. Amyloid-beta and phosphorylated tau both interact with mitochondrial proteins "
            "to impair electron transport chain activity, particularly at complexes I and IV. "
            "Mitochondrial dysfunction precedes amyloid plaque deposition and neurofibrillary tangle "
            "formation in some model systems, suggesting it may be an upstream driver rather than a "
            "downstream consequence. Therapeutic strategies targeting mitochondrial dysfunction "
            "include antioxidants, mitochondria-targeted peptides, and agents that enhance mitophagy."
        ),
    },
]

# Pre-cached generic papers for Conditions B and C (used when Semantic Scholar is rate-limited)
GENERIC_PAPERS = [
    {
        "title": "Mechanistic Insights for Drug Repurposing and the Design of Hybrid Drugs for Alzheimer's Disease",
        "abstract": (
            "The heterogeneity and complex nature of Alzheimer's disease (AD) is attributed to several "
            "genetic risk factors and molecular culprits. The slow pace and increasing failure rate of "
            "conventional drug discovery has led to the exploration of complementary strategies based on "
            "repurposing approved drugs to treat AD. Drug repurposing is a cost-effective, low-risk, "
            "and efficient approach for identifying new therapeutic targets."
        ),
    },
    {
        "title": "A computational medicine framework integrating multi-omics for Alzheimer's disease therapeutic discovery",
        "abstract": (
            "The translation of genetic findings from genome-wide association studies into actionable "
            "therapeutics persists as a critical challenge in Alzheimer's disease research. Computational "
            "medicine frameworks integrate multi-omics data, systems biology, and machine learning for "
            "therapeutic discovery, leveraging network evidence to prioritize drug repurposing candidates."
        ),
    },
    {
        "title": "TYK2 as a novel therapeutic target in Alzheimer's Disease",
        "abstract": (
            "Neuroinflammation is a pathological feature of many neurodegenerative diseases, including "
            "Alzheimer's disease, raising the possibility of common therapeutic targets. Janus kinase "
            "inhibitors and other immunomodulatory drugs are being investigated for repurposing in AD "
            "through modulation of microglial inflammatory responses."
        ),
    },
    {
        "title": "Repurposing FDA-approved drugs for Alzheimer's disease therapy",
        "abstract": (
            "Drug repurposing offers a faster path to Alzheimer's disease treatment by screening "
            "existing approved compounds against AD-relevant targets including amyloid clearance, "
            "tau phosphorylation, neuroinflammation, and synaptic dysfunction. High-throughput "
            "screening and computational docking have identified multiple candidate repurposing drugs."
        ),
    },
    {
        "title": "Blood-brain barrier transport and drug delivery for Alzheimer's disease",
        "abstract": (
            "Effective Alzheimer's disease therapeutics must cross the blood-brain barrier to reach "
            "central nervous system targets. Strategies to enhance CNS drug delivery include modifying "
            "existing drugs for improved BBB penetration, using receptor-mediated transcytosis, and "
            "repurposing compounds with known CNS bioavailability profiles."
        ),
    },
]
