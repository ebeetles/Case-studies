# Novelty Comprehension Check

Diagnostic follow-up to results/validation/novelty_decay.md, which found the novelty judge scored 3/5 in BOTH pre-cutoff and post-cutoff literature conditions for both compounds — a flat, non-responsive result despite the embedding-similarity sanity check confirming the corpora were correctly differentiated. This checks whether the judge (a) reads the literature correctly but doesn't weight it in its novelty score, or (b) doesn't meaningfully process the literature content at all.

Method: before each novelty scoring call, a direct comprehension question is asked about the SAME literature block — 'does this literature already describe [compound] + [mechanism] in an AD context?' Pre-cutoff context should answer NO (the connection hadn't been proposed yet); post-cutoff should answer YES.

n=4 cases (2 compounds x 2 conditions). No statistics — raw pattern only.

## Results table

| Compound | Condition | Comprehension answer | Expected | Correct? | Novelty score | Compound judge Δ (post-pre) | Matches expected decay direction? |
|---|---|---|---|---|---|---|---|
| metformin | pre-cutoff | NO | NO | ✓ | 3 | +0 | ✗ |
| metformin | post-cutoff | NO | YES | ✗ | 3 | +0 | ✗ |
| sildenafil | pre-cutoff | NO | NO | ✓ | 3 | -1 | ✓ |
| sildenafil | post-cutoff | YES | YES | ✓ | 2 | -1 | ✓ |

## Per-case pattern

**metformin**:
- MIXED — comprehension correct on one condition, incorrect on the other (post-cutoff failed). Report as-is, do not average away.

**sildenafil**:
- Comprehension correct in both conditions AND novelty score responded — the flat result in the original decay experiment looks prompt/instance-specific rather than a fundamental comprehension failure.

## Raw comprehension-check responses (verbatim)

### metformin / pre-cutoff

Expected: NO, got: NO (correct)

```
NO

The provided literature does **not** describe a connection between **metformin** and **AMPK/mTOR pathway modulation reducing tau pathology or neuroinflammation in Alzheimer’s disease**.

What it does contain instead:
- **Metformin/AMPK papers**: These describe metformin activating **AMP-activated protein kinase (AMPK)** and affecting **hepatic glucose production**, **insulin sensitivity**, and **lipogenic/glucose metabolism**. For example, one entry says metformin “**lowers hepatic glucose production and increases insulin sensitivity via AMPK activation**,” and another says metformin “**activates AMP-activated protein kinase (AMPK) in intact cells**.”
- **Alzheimer’s review**: The Alzheimer’s paper reviews the **amyloid hypothesis**, including “**amyloid-beta production, aggregation, and downstream tau pathology**,” but it explicitly does **not** mention metformin, AMPK, mTOR, or diabetes-drug repurposing.

So, based only on the provided literature, there is **no stated link** between metformin-driven AMPK/mTOR modulation and reduced tau pathology or neuroinflammation in Alzheimer’s disease.
```

Novelty score immediately after: 3 — This is a plausible and fairly expected repurposing rationale: metformin’s known AMPK activation is being linked to AD-relevant processes like neuroinflammation and tau pathology, but the provided literature does not show a prior AD-specific mechanistic connection, making it neither fully established nor highly non-obvious.

### metformin / post-cutoff

Expected: YES, got: NO (INCORRECT)

```
NO

The provided literature does describe metformin as modulating the **AMPK/mTOR/S6K1 axis** in Alzheimer’s disease, but only in the context of **reducing BACE1-mediated amyloid precursor protein processing and lowering amyloid-beta production/toxicity**:

- “Metformin activates AMPK in brain tissue, which modulates the mTOR/S6K1 signaling axis and reduces BACE1-mediated processing of amyloid precursor protein, decreasing amyloid-beta production and toxicity…”

The other entries describe broader associations with **lower AD risk, better cognitive performance**, and possible mechanisms such as **suppression of APOE and SPP1 expression**, but they do **not** explicitly connect metformin’s AMPK/mTOR modulation to **tau pathology** or **neuroinflammation** in the text provided.
```

Novelty score immediately after: 3 — This is a plausible and fairly expected AD repurposing rationale: the provided literature already links metformin to AMPK/mTOR/S6K/BACE1 effects, reduced amyloid-beta, and broader AD-relevant associations, so the added neuroinflammation/tau angle is extension rather than a highly novel mechanistic leap.

### sildenafil / pre-cutoff

Expected: NO, got: NO (correct)

```
NO

The provided literature does **not** describe a connection between sildenafil and PDE5 inhibition/cGMP signaling reducing tau phosphorylation or amyloid accumulation in Alzheimer’s disease.

What it does contain instead:
- **Cardiac phosphodiesterase 5 (2001):** discusses PDE5 in **cardiac tissue**, its role in **cGMP-mediated beta-adrenergic signaling**, and its **down-regulation in heart failure**.
- **Network medicine (2011):** presents a **general disease-network and drug-repurposing framework**, with no mention of sildenafil, PDE5, or Alzheimer’s disease.
- **Oral Sildenafil in the Treatment of Erectile Dysfunction (1998):** shows sildenafil as an **oral PDE5 inhibitor for erectile dysfunction**, with no cognitive, neurodegenerative, tau, amyloid, or Alzheimer’s endpoints.

So, based only on the provided literature, there is **no** stated Alzheimer’s-related mechanism involving sildenafil, PDE5 inhibition, cGMP signaling, tau phosphorylation, or amyloid accumulation.
```

Novelty score immediately after: 3 — This is a plausible repurposing hypothesis with a clear mechanistic bridge (PDE5 inhibition → increased cGMP signaling → potential effects on tau/amyloid), but the provided literature snapshot does not show a specific AD-focused, non-obvious connection beyond a reasonable extrapolation from known signaling biology.

### sildenafil / post-cutoff

Expected: YES, got: YES (correct)

```
YES

The provided literature does describe that connection. Specifically, the 2025 summary says: **“PDE5 inhibition increases cGMP signaling, reduces phospho-tau181, and decreases amyloid-beta, supporting the network-medicine candidate identification with direct experimental evidence.”**

This directly links sildenafil/PDE5 inhibition and cGMP signaling to reduced tau phosphorylation and reduced amyloid accumulation in the context of Alzheimer’s disease.
```

Novelty score immediately after: 2 — This is a fairly expected AD repurposing idea because it leverages a standard PDE5→cGMP→neuroprotection rationale that is directly supported by the provided network and retrospective human-data literature, rather than introducing a distinctly novel AD-specific mechanistic angle.
