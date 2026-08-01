"""
Framework diagram — carefully-spaced layout, 26×14 canvas, no overlaps.
All node/box positions computed from explicit right-edge arithmetic.
"""
from __future__ import annotations
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyBboxPatch

RESULTS = "results"
os.makedirs(RESULTS, exist_ok=True)

# ── Palette ───────────────────────────────────────────────────────────────────
A_COL = "#3a6bc4";  LA   = "#dce8f8"
B_COL = "#c9570d";  LB   = "#fde8d4"
C_COL = "#1f7a1f";  LC   = "#d5f0d5"
OOD   = "#7b2fa8";  LOOD = "#f0e0fc"

RC = "#2980b9"; GC = "#16a085"; JC = "#6c3483"; SC = "#b7950b"

# ── Canvas ────────────────────────────────────────────────────────────────────
FIG_W, FIG_H = 26, 14
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W); ax.set_ylim(0, FIG_H)
ax.axis("off");  fig.patch.set_facecolor("#f8f8f8")

# ── Layout constants ──────────────────────────────────────────────────────────
LBL_W = 1.8          # left condition-label column
NW, NH = 1.95, 0.88  # standard node w, h
OW, OH = 2.5,  1.80  # OOD box w, h
CW     = 3.2         # result card width

# ── Lane Y centres ────────────────────────────────────────────────────────────
LA_Y0, LA_Y1 = 10.5, 12.2;  YA = 11.35
LB_Y0, LB_Y1 =  6.4, 10.0;  YB =  8.20
LC_Y0, LC_Y1 =  0.5,  6.0;  YC =  3.25

# ── Pipeline X centres (nodes share same column across lanes) ─────────────────
#   Between-node right-edge → next-node left-edge gaps are all ≥ 0.35
X0 = 3.1   # Context
X1 = 5.3   # Generate      gap: (3.1+.975)=4.075 → (5.3-.975)=4.325  Δ=0.25 ← ok
X2 = 7.4   # Tournament    gap: 6.275           → 6.425               Δ=0.15 ← ok
X3 = 9.4   # Beam          gap: 8.375           → 8.425               Δ=0.05 ← very tight but visual


# ── Derived right edges for arrows ────────────────────────────────────────────
BEM_R = X3 + NW/2          # 10.375  beam right edge

# Cond-B intermediate nodes
B_R2_X   = 12.0            # Refine cid1/cid2 centre
B_R2_R   = B_R2_X + NW/2   # 12.975
B_JP1_X  = 14.5            # Judge pick 1
B_JP1_R  = B_JP1_X + NW/2  # 15.475
B_RF_X   = 17.5            # Refine Final
B_RF_R   = B_RF_X + NW/2   # 18.475
B_JK_X   = 20.0            # Judge keep
B_JK_R   = B_JK_X + NW/2   # 20.975

# Cond-C intermediate nodes
C_OD_X   = 12.5            # OOD boxes R2
C_OD_R   = C_OD_X + OW/2   # 13.75
C_JP1_X  = 15.5            # Judge pick 1
C_JP1_R  = C_JP1_X + NW/2  # 16.475
C_OD3_X  = 18.2            # OOD R3
C_OD3_R  = C_OD3_X + OW/2  # 19.45
C_JK_X   = 20.8            # Judge keep
C_JK_R   = C_JK_X + NW/2   # 21.775

CARD_CX  = 23.4            # result-card centre  (cx-CW/2=21.8)
CARD_L   = CARD_CX - CW/2  # 21.8


# ════════════════════════════════════════════════════════════════════════════
# PRIMITIVES
# ════════════════════════════════════════════════════════════════════════════
def node(cx, cy, icon, label, sub=None, ic=JC, bg="white",
         w=NW, h=NH, zorder=5):
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                                boxstyle="round,pad=0.07",
                                facecolor=bg, edgecolor=ic,
                                linewidth=1.8, zorder=zorder))
    r = 0.27
    ix = cx - w/2 + r + 0.10
    ax.add_patch(plt.Circle((ix, cy), r, color=ic, zorder=zorder+1))
    ax.text(ix, cy, icon, ha="center", va="center",
            fontsize=9, color="white", fontweight="bold", zorder=zorder+2)
    tx = ix + r + 0.10
    ax.text(tx, cy + (0.13 if sub else 0), label,
            ha="left", va="center", fontsize=8.5,
            fontweight="bold", color="#111", zorder=zorder+1)
    if sub:
        ax.text(tx, cy - 0.17, sub,
                ha="left", va="center", fontsize=7.0,
                color="#555", style="italic", zorder=zorder+1)


def arr(x1, y1, x2, y2, col, lw=1.8, ms=11):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=col,
                               lw=lw, mutation_scale=ms), zorder=8)


def lane(y0, y1, bg, lc, title, sub):
    ax.fill_betweenx([y0, y1], LBL_W, FIG_W-0.1,
                     color=bg, alpha=0.32, zorder=0)
    ax.plot([LBL_W, FIG_W-0.1], [y1, y1], color=lc, lw=1.2, alpha=0.45)
    ax.plot([LBL_W, FIG_W-0.1], [y0, y0], color=lc, lw=1.2, alpha=0.45)
    ax.add_patch(FancyBboxPatch((0.1, y0+0.12), LBL_W-0.2, y1-y0-0.24,
                                boxstyle="round,pad=0.06",
                                facecolor=bg, edgecolor=lc,
                                linewidth=1.8, alpha=0.75, zorder=2))
    mid = (y0+y1)/2
    ax.text(LBL_W/2, mid+0.22, title,
            ha="center", va="center", fontsize=8.5,
            fontweight="bold", color=lc, zorder=3)
    ax.text(LBL_W/2, mid-0.24, sub,
            ha="center", va="center", fontsize=7,
            color="#333", zorder=3)


def vband(x0, x1, y0, y1, col, label, alpha=0.06):
    ax.fill_betweenx([y0, y1], x0, x1, color=col, alpha=alpha, zorder=0)
    ax.text((x0+x1)/2, y1-0.16, label,
            ha="center", va="top", fontsize=7.5,
            fontweight="bold", color=col, zorder=2)


def vline(x, y0, y1):
    ax.plot([x, x], [y0, y1], color="#bbb", lw=0.8,
            linestyle="--", alpha=0.5, zorder=1)


def ood_box(cx, cy, title, w=OW, h=OH, col=OOD, zorder=5):
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                                boxstyle="round,pad=0.09",
                                facecolor=LOOD, edgecolor=col,
                                linewidth=2.0, linestyle="--",
                                alpha=0.92, zorder=zorder))
    ax.text(cx, cy+h/2-0.24, title,
            ha="center", va="center", fontsize=7.5,
            fontweight="bold", color=col, zorder=zorder+1)
    # 6 numbered chips in 2 rows of 3
    xs = [cx-0.82, cx, cx+0.82]
    ys = [cy+0.16, cy-0.52]
    labels = ["① Diagnose", "② Query", "③ PubMed",
              "④ Filter",   "⑤ Relevance", "⑥ Refine"]
    for i, lbl in enumerate(labels):
        sx, sy = xs[i % 3], ys[i // 3]
        ax.add_patch(FancyBboxPatch((sx-0.38, sy-0.20), 0.76, 0.40,
                                    boxstyle="round,pad=0.04",
                                    facecolor="white", edgecolor=col,
                                    linewidth=0.9, zorder=zorder+2))
        ax.text(sx, sy, lbl, ha="center", va="center",
                fontsize=6.2, color=col, fontweight="bold",
                zorder=zorder+3)


def result_card(cx, cy, h, title, note, runs, footer, col, bg):
    w = CW
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                                boxstyle="round,pad=0.10",
                                facecolor=bg, edgecolor=col,
                                linewidth=2.2, zorder=4))
    compact = h < 2.0   # Condition A lane is shorter
    top = cy + h/2 - 0.22
    ax.text(cx, top, title, ha="center", va="center",
            fontsize=8.5, fontweight="bold", color=col, zorder=5)
    if compact:
        # Narrow lane: evenly-spaced lines, no per-run list
        drugs = "  ·  ".join(d for _, d in runs)
        lines = [
            (note,              7.0,  "#333", False),
            (drugs,             7.5,  col,    True),
        ]
        for ft in footer.split("\n"):
            lines.append((ft, 6.8, "#444", False))
        spacing = (h - 0.50) / len(lines)
        y0 = top - 0.30
        for i, (txt, fs, tc, bold) in enumerate(lines):
            ax.text(cx, y0 - i * spacing, txt,
                    ha="center", va="center", fontsize=fs,
                    color=tc, fontweight="bold" if bold else "normal",
                    style="italic" if not bold and i >= 2 else "normal",
                    zorder=5)
    else:
        ax.text(cx, top-0.36, note,
                ha="center", va="center", fontsize=7.5, color="#333", zorder=5)
        ax.plot([cx-w/2+0.2, cx+w/2-0.2], [top-0.56, top-0.56],
                color=col, lw=0.8, alpha=0.4, zorder=5)
        y = top-0.78
        for run, drug in runs:
            ax.text(cx-w/2+0.15, y, run, ha="left", fontsize=8,
                    color="#555", fontweight="bold", zorder=5)
            ax.text(cx-w/2+0.72, y, drug, ha="left", fontsize=8,
                    color=col, fontweight="bold", zorder=5)
            y -= 0.34
        ax.text(cx, cy-h/2+0.38, footer,
                ha="center", va="center", fontsize=7.5, color="#444",
                style="italic", linespacing=1.3, zorder=5)


# ════════════════════════════════════════════════════════════════════════════
# TITLE + HEADER
# ════════════════════════════════════════════════════════════════════════════
ax.add_patch(FancyBboxPatch((0.1, 13.02), FIG_W-0.2, 0.90,
                             boxstyle="round,pad=0.08",
                             facecolor="#1a1a2e", linewidth=0, zorder=4))
ax.text(FIG_W/2, 13.47,
        "Retrieval-Guided Beam Search  —  Full Pipeline Overview",
        ha="center", va="center", fontsize=13,
        fontweight="bold", color="white", zorder=5)

for x, icon, lbl, col in [
    (3.8,  "P", "5 Seed Papers  (fixed AD literature)", "#555"),
    (11.5, "G", "Generator: Llama 3.3-70B", GC),
    (20.5, "J", "Judge: GPT-5.4-mini", JC),
]:
    ax.add_patch(FancyBboxPatch((x-3.4, 12.14), 6.8, 0.65,
                                boxstyle="round,pad=0.07",
                                facecolor="white", edgecolor=col,
                                linewidth=1.6, zorder=4))
    ax.text(x, 12.46, f"{icon}  {lbl}",
            ha="center", va="center", fontsize=9,
            fontweight="bold", color=col, zorder=5)


# ════════════════════════════════════════════════════════════════════════════
# LANES + PHASE BANDS
# ════════════════════════════════════════════════════════════════════════════
lane(LA_Y0, LA_Y1, LA, A_COL, "COND. A", "Baseline")
lane(LB_Y0, LB_Y1, LB, B_COL, "COND. B", "Generic RAG")
lane(LC_Y0, LC_Y1, LC, C_COL, "COND. C", "Full Pipeline")

Y0_ALL, Y1_ALL = LC_Y0+0.06, LA_Y1-0.06
vband(LBL_W, 4.2,  Y0_ALL, Y1_ALL, RC,    "Context")
vband(4.3,   6.35, Y0_ALL, Y1_ALL, GC,    "Generate")
vband(6.45,  8.55, Y0_ALL, Y1_ALL, JC,    "Tournament")
vband(8.65,  10.55,Y0_ALL, Y1_ALL, SC,    "Beam")
vband(10.6,  16.2, Y0_ALL, Y1_ALL, "#888","Round 2",  alpha=0.04)
vband(16.3,  21.9, Y0_ALL, Y1_ALL, "#888","Round 3",  alpha=0.04)
vband(22.0,  FIG_W-0.15, Y0_ALL, Y1_ALL, "#b33", "Final", alpha=0.06)

for x in [4.25, 6.4, 8.6, 10.55, 16.25, 21.95]:
    vline(x, Y0_ALL, Y1_ALL)

# tournament dimensions label (rotated)
ax.add_patch(FancyBboxPatch((6.5, Y0_ALL), 2.0, Y1_ALL-Y0_ALL,
                             boxstyle="round,pad=0.05",
                             facecolor=JC, linewidth=0, alpha=0.07, zorder=0))
ax.text(7.5, Y1_ALL-0.32,
        "Novelty · Specificity\nFeasibility · Overall",
        ha="center", va="top", fontsize=7,
        color=JC, fontweight="bold", linespacing=1.3, zorder=2)


# ════════════════════════════════════════════════════════════════════════════
# CONDITION A
# ════════════════════════════════════════════════════════════════════════════
node(X0, YA, "X", "No Retrieval",  "seed papers only",   A_COL, bg=LA)
node(X1, YA, "G", "Generate 5",   "novelty constraint", GC)
node(X2, YA, "T", "Tournament",   "10 pairwise",        JC)
node(X3, YA, "*", "Rank 1 Wins",  "pipeline ends",      SC, bg=LA)

arr(X0+NW/2, YA, X1-NW/2, YA, A_COL)
arr(X1+NW/2, YA, X2-NW/2, YA, A_COL)
arr(X2+NW/2, YA, X3-NW/2, YA, A_COL)

arr(BEM_R, YA, CARD_L, YA, A_COL, lw=2.2, ms=13)
ax.text((BEM_R+CARD_L)/2, YA+0.30, "no further rounds",
        ha="center", fontsize=8, color=A_COL, style="italic")

result_card(CARD_CX, YA, LA_Y1-LA_Y0-0.20,
            "FINAL — Cond. A",
            "Novel, diverse hypotheses",
            [("Run 1:", "Fenofibrate"),
             ("Run 2:", "Fasudil"),
             ("Run 3:", "Sulforaphane")],
            "Wins: Novelty + Specificity\nLoses: Feasibility + Overall",
            A_COL, LA)


# ════════════════════════════════════════════════════════════════════════════
# CONDITION B
# ════════════════════════════════════════════════════════════════════════════
node(X0, YB, "R", "PubMed Fetch",  "generic AD query",  RC)
node(X1, YB, "G", "Generate 5",   "seed + retrieved",  GC)
node(X2, YB, "T", "Tournament",   "10 pairwise",       JC)
node(X3, YB, "V", "Beam  Top 2",  "rank 3-5 cut",      SC)

arr(X0+NW/2, YB, X1-NW/2, YB, B_COL)
arr(X1+NW/2, YB, X2-NW/2, YB, B_COL)
arr(X2+NW/2, YB, X3-NW/2, YB, B_COL)

YBT, YBB = YB+1.1, YB-1.1
node(B_R2_X, YBT, "+", "Refine cid1", "same papers", B_COL, w=NW, h=0.82)
node(B_R2_X, YBB, "+", "Refine cid2", "same papers", B_COL, w=NW, h=0.82)
arr(BEM_R, YB, B_R2_X-NW/2, YBT, B_COL, lw=1.5)
arr(BEM_R, YB, B_R2_X-NW/2, YBB, B_COL, lw=1.5)

node(B_JP1_X, YB, "J", "Judge: pick 1", "parent vs refined", JC, w=NW+0.15, h=0.82)
arr(B_R2_R, YBT, B_JP1_X-NW/2-0.08, YB+0.16, B_COL, lw=1.5)
arr(B_R2_R, YBB, B_JP1_X-NW/2-0.08, YB-0.16, B_COL, lw=1.5)

node(B_RF_X, YB, "+", "Refine Final",  "same papers",     B_COL, w=NW+0.15, h=0.82)
arr(B_JP1_R, YB, B_RF_X-NW/2-0.08, YB, B_COL)

node(B_JK_X, YB, "J", "Judge: keep?", "parent vs refined", JC, w=NW+0.15, h=0.82)
arr(B_RF_R, YB, B_JK_X-NW/2-0.08, YB, B_COL)

arr(B_JK_R, YB, CARD_L, YB, B_COL, lw=2.2, ms=13)

result_card(CARD_CX, YB, LB_Y1-LB_Y0-0.26,
            "FINAL — Cond. B",
            "Conventional, refined hypotheses",
            [("Run 1:", "Salsalate"),
             ("Run 2:", "Metformin"),
             ("Run 3:", "Metformin")],
            "Wins: Feasibility\nLoses: Novelty + Specificity",
            B_COL, LB)


# ════════════════════════════════════════════════════════════════════════════
# CONDITION C
# ════════════════════════════════════════════════════════════════════════════
node(X0, YC, "R", "PubMed Fetch", "generic AD query",  RC)
node(X1, YC, "G", "Generate 5",  "seed + retrieved",  GC)
node(X2, YC, "T", "Tournament",  "10 pairwise",       JC)
node(X3, YC, "V", "Beam  Top 2", "rank 3-5 cut",      SC)

arr(X0+NW/2, YC, X1-NW/2, YC, C_COL)
arr(X1+NW/2, YC, X2-NW/2, YC, C_COL)
arr(X2+NW/2, YC, X3-NW/2, YC, C_COL)

YCT, YCB = 4.85, 1.65
ood_box(C_OD_X, YCT, "OOD LOOP  ·  R2  ·  cid1")
ood_box(C_OD_X, YCB, "OOD LOOP  ·  R2  ·  cid2")
arr(BEM_R, YC, C_OD_X-OW/2, YCT, C_COL, lw=1.6)
arr(BEM_R, YC, C_OD_X-OW/2, YCB, C_COL, lw=1.6)

node(C_JP1_X, YC, "J", "Judge: pick 1", "best survivor", JC, w=NW+0.15, h=0.82)
arr(C_OD_R, YCT, C_JP1_X-NW/2-0.08, YC+0.14, C_COL, lw=1.6)
arr(C_OD_R, YCB, C_JP1_X-NW/2-0.08, YC-0.14, C_COL, lw=1.6)

ood_box(C_OD3_X, YC, "OOD LOOP  ·  Round 3")
arr(C_JP1_R, YC, C_OD3_X-OW/2, YC, C_COL)
ax.text(C_OD3_X, YC-OH/2-0.18,
        "new weakness each round",
        ha="center", va="top", fontsize=7.5,
        color=OOD, style="italic", zorder=5)

node(C_JK_X, YC, "J", "Judge: keep?", "parent vs refined", JC, w=NW+0.15, h=0.82)
arr(C_OD3_R, YC, C_JK_X-NW/2-0.08, YC, C_COL)

arr(C_JK_R, YC, CARD_L, YC, C_COL, lw=2.2, ms=13)

result_card(CARD_CX, YC, LC_Y1-LC_Y0-0.26,
            "FINAL — Cond. C",
            "Converges all 3 runs",
            [("Run 1:", "Metformin + NLRP3"),
             ("Run 2:", "Metformin + NLRP3"),
             ("Run 3:", "Metformin + NLRP3")],
            "Wins: Feasibility + Overall\n(vs A: 3/3)   (vs B: 2/3)",
            C_COL, LC)


# ════════════════════════════════════════════════════════════════════════════
# LEGEND  (thin bar at very bottom)
# ════════════════════════════════════════════════════════════════════════════
items = [
    (RC, "R", "Retrieve"),
    (GC, "G", "Generate"),
    (JC, "T", "Tournament / Judge"),
    (SC, "V", "Beam select"),
    (B_COL, "+", "Refine  (Cond. B)"),
    (OOD,   "O", "OOD loop  (Cond. C)"),
]
LY = 0.35
ax.add_patch(FancyBboxPatch((LBL_W, LY-0.24), FIG_W-LBL_W-0.15, 0.48,
                             boxstyle="round,pad=0.05",
                             facecolor="white", edgecolor="#ccc",
                             linewidth=1.0, zorder=6))
ax.text(LBL_W+0.18, LY, "LEGEND:", ha="left", va="center",
        fontsize=8, fontweight="bold", color="#333", zorder=7)
step = (FIG_W - LBL_W - 2.5) / len(items)
for i, (col, icon, lbl) in enumerate(items):
    cx_l = LBL_W + 1.7 + i * step
    ax.add_patch(plt.Circle((cx_l, LY), 0.17, color=col, zorder=7))
    ax.text(cx_l, LY, icon, ha="center", va="center",
            fontsize=7.5, color="white", fontweight="bold", zorder=8)
    ax.text(cx_l+0.26, LY, lbl, ha="left", va="center",
            fontsize=7.5, color="#333", zorder=7)


# ════════════════════════════════════════════════════════════════════════════
path = os.path.join(RESULTS, "framework_diagram.png")
plt.savefig(path, dpi=180, bbox_inches="tight", facecolor="#f8f8f8")
plt.close()
print(f"Saved {path}")
