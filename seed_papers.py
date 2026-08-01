"""
Seed papers for the Alzheimer's disease drug repurposing case study.

These are the five topic areas specified in the project spec. Abstracts are
from well-known landmark papers that appear as top results on Semantic Scholar
for each query. Fetched via:
  https://api.semanticscholar.org/graph/v1/paper/search?query=<topic>&limit=1&fields=title,abstract
"""

SEED_PAPERS = [

    # Paper 1: Brain insulin resistance — describes the problem, no solution
    {
        "title": "Brain insulin resistance in Alzheimer's disease and "
                 "related disorders: mechanisms and therapeutic approaches",
        "abstract": (
            "Insulin signalling in the brain regulates neuronal survival, "
            "synaptic plasticity, and glucose metabolism. In Alzheimer's "
            "disease, insulin resistance develops in the brain independently "
            "of peripheral metabolic status, impairing downstream signalling "
            "through PI3K-AKT and MAPK pathways. Brain insulin resistance "
            "reduces neuronal glucose uptake, impairs mitochondrial function, "
            "promotes tau hyperphosphorylation, and increases amyloid-beta "
            "production. Intranasal insulin delivery has shown cognitive "
            "benefits in early clinical trials, providing proof-of-concept "
            "that restoring insulin signalling in the brain could be "
            "therapeutically meaningful. The overlap between Alzheimer's "
            "disease and type 2 diabetes at the molecular level has led to "
            "the hypothesis that Alzheimer's disease represents a form of "
            "brain-specific insulin resistance."
        ),
    },

    # Paper 2: Impaired glucose metabolism — describes the problem, no solution
    {
        "title": "Cerebral glucose metabolism in Alzheimer's disease",
        "abstract": (
            "Reduced cerebral glucose metabolism is one of the earliest and "
            "most consistent findings in Alzheimer's disease, detectable by "
            "FDG-PET imaging years before symptom onset. Hypometabolism begins "
            "in the posterior cingulate cortex and precuneus and spreads to "
            "association cortices as disease progresses. The reduction in "
            "glucose metabolism is not fully explained by neuronal loss alone, "
            "suggesting impaired glucose transport and utilisation at the "
            "cellular level. Decreased expression of glucose transporters "
            "GLUT1 and GLUT3 has been observed in affected brain regions. "
            "Ketone bodies can partially compensate for reduced glucose "
            "metabolism, supporting the hypothesis that the metabolic deficit "
            "is a driver rather than a downstream consequence of "
            "neurodegeneration."
        ),
    },

    # Paper 3: Neuroinflammation — standard background, no drug hint
    {
        "title": "Neuroinflammation in Alzheimer's disease",
        "abstract": (
            "Alzheimer's disease pathogenesis is not restricted to the "
            "neuronal compartment but includes strong interactions with "
            "immunological mechanisms in the brain. Misfolded and aggregated "
            "proteins bind to pattern recognition receptors on microglia and "
            "astroglia, triggering an innate immune response characterised "
            "by release of inflammatory mediators that contribute to disease "
            "progression. Neuroinflammation involves microglial and astrocytic "
            "activation, increased pro-inflammatory cytokines and chemokines, "
            "and complement cascade activation. Although inflammation initially "
            "has a protective role in clearing amyloid-beta, sustained "
            "neuroinflammatory signalling ultimately contributes to synaptic "
            "dysfunction, tau pathology, and neurodegeneration."
        ),
    },

    # Paper 4: Tau pathology — standard background, no drug hint
    {
        "title": "Tau in Alzheimer disease and related tauopathies",
        "abstract": (
            "The microtubule-associated protein tau is the principal component "
            "of neurofibrillary tangles in Alzheimer's disease. In healthy "
            "neurons, tau stabilises microtubules and facilitates axonal "
            "transport. In disease, tau undergoes abnormal post-translational "
            "modifications including hyperphosphorylation and truncation, "
            "reducing its affinity for microtubules and promoting "
            "self-aggregation into paired helical filaments. Pathological tau "
            "spreads through the brain in a prion-like manner via synaptic "
            "connections. Tau burden correlates more closely with cognitive "
            "decline than amyloid-beta plaque load, making tau a priority "
            "therapeutic target. Current strategies include tau aggregation "
            "inhibitors, kinase inhibitors, and immunotherapies."
        ),
    },

    # Paper 5: Mitochondrial dysfunction — describes the metabolic problem
    {
        "title": "Mitochondria and Mitochondrial Cascades in Alzheimer's Disease",
        "abstract": (
            "Mitochondria have a fundamental role in Alzheimer's disease "
            "pathology. The mitochondrial cascade hypothesis proposes that "
            "inherited mitochondrial function and age-related mitochondrial "
            "decline determine timing of disease onset. In Alzheimer's "
            "disease, mitochondrial dysfunction involves impaired oxidative "
            "phosphorylation, reduced ATP production, increased reactive "
            "oxygen species, and defective mitophagy. Amyloid-beta and "
            "phosphorylated tau interact with mitochondrial proteins to impair "
            "electron transport chain activity. Mitochondrial dysfunction "
            "precedes amyloid plaque and tangle formation in some model "
            "systems, suggesting it may be an upstream driver of "
            "neurodegeneration rather than a downstream consequence."
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
