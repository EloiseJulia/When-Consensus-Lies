"""Generate two top-venue conceptual figures for *When Consensus Lies*.
Flat-vector style (scientific-figure-generator skill spec). English labels.
Outputs PDF (for the paper) + PNG (for preview). Originals are NOT touched.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Polygon
import numpy as np

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
})

# ---- palette (skill spec: cool gray / light blue base; one accent) ----
INK      = "#2D3748"   # dark text
GRAY_ED  = "#8894A5"   # neutral edge
BLUEF    = "#E7EEF7"   # model chip fill
BLUEE    = "#3B6EA5"   # model chip edge
CARDF    = "#F1F3F6"   # neutral card fill
DANGER   = "#D9534F"   # accent (danger)
DANGERB  = "#FBEDEB"   # danger band
SAFE     = "#2E9E7B"   # safe accent
SAFEB    = "#E9F5F0"   # safe band
DEEP     = "#2B5EA8"   # deep blue accent (fig2 key step)

def rbox(ax, x, y, w, h, fc, ec, lw=1.3, rad=0.06, z=2):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rad}",
                       linewidth=lw, edgecolor=ec, facecolor=fc, zorder=z)
    ax.add_patch(p)
    return p

def txt(ax, x, y, s, size=10.5, color=INK, weight="normal", ha="center", va="center", z=5):
    ax.text(x, y, s, fontsize=size, color=color, weight=weight, ha=ha, va=va, zorder=z)

def arrow(ax, p0, p1, color=GRAY_ED, lw=1.6, ls="-", rad=0.0, z=3, mut=12):
    a = FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=mut, lw=lw,
                        color=color, linestyle=ls, zorder=z,
                        connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(a)

# =====================================================================
# FIGURE 1 — Graphical abstract: Fake redundancy (two-row contrast)
# =====================================================================
def fig_fake_redundancy(path):
    fig, ax = plt.subplots(figsize=(12.4, 6.6))
    ax.set_xlim(0, 12.4); ax.set_ylim(0, 6.6); ax.axis("off")

    models = ["GPT", "Claude", "Gemini", "reasoning", "small"]

    def regime(y0, band_fc, accent, band_title, complete):
        # background band
        rbox(ax, 0.25, y0, 11.9, 2.75, band_fc, "none", rad=0.12, z=1)
        yc = y0 + 1.375
        # 1) prompt card
        rbox(ax, 0.55, yc-0.7, 1.85, 1.4, "#FFFFFF", INK, lw=1.4, rad=0.05)
        txt(ax, 1.475, yc+0.42, "Prompt", 10.5, INK, "bold")
        # lines representing the prompt; one greyed/cut if incomplete
        for i, ly in enumerate([yc+0.05, yc-0.18, yc-0.41]):
            if (not complete) and i == 1:
                ax.plot([0.8, 1.75], [ly, ly], color=DANGER, lw=2.2, ls=(0,(2,1.4)), zorder=4)
                txt(ax, 2.02, ly, "\u2717", 11, DANGER, "bold")
            else:
                ax.plot([0.8, 2.15], [ly, ly], color="#B9C2CE", lw=2.2, zorder=4)
        cap = "missing decisive clause" if not complete else "clause retained"
        txt(ax, 1.475, yc-0.92, cap, 8.6, (DANGER if not complete else SAFE), "bold")

        # 2) model chips (fan-out)
        mx = 4.05
        ys = np.linspace(yc+1.02, yc-1.02, len(models))
        for m, my in zip(models, ys):
            rbox(ax, mx, my-0.2, 1.5, 0.4, BLUEF, BLUEE, lw=1.2, rad=0.08)
            txt(ax, mx+0.75, my, m, 9.2, INK)
            arrow(ax, (2.45, yc), (mx-0.03, my), color="#AEB8C4", lw=1.2, mut=9)

        # 3) aggregation region -> outcome
        if not complete:
            # converge: all arrows merge to one node
            node = (8.15, yc)
            for my in ys:
                arrow(ax, (mx+1.53, my), (node[0]-0.02, node[1]), color=accent, lw=1.5,
                      rad=(my-yc)*0.12, mut=10)
            # wrong-answer card
            rbox(ax, 8.2, yc-0.5, 1.7, 1.0, "#FFFFFF", accent, lw=1.8, rad=0.06)
            txt(ax, 9.05, yc+0.16, "same", 10, accent, "bold")
            txt(ax, 9.05, yc-0.16, "WRONG answer", 9.2, accent, "bold")
            # consensus badge
            rbox(ax, 10.15, yc-0.34, 1.9, 0.68, "#FFFFFF", accent, lw=1.5, rad=0.1)
            txt(ax, 10.72, yc, "5/5 agree", 10, INK, "bold")
            c = Circle((11.72, yc), 0.16, facecolor=accent, edgecolor="none", zorder=6)
            ax.add_patch(c); txt(ax, 11.72, yc, "\u2717", 10, "white", "bold", z=7)
            arrow(ax, (9.92, yc), (10.13, yc), color=accent, lw=1.6, mut=10)
        else:
            # stay independent: separate varied outputs, no merge
            ox = 8.2
            for k, my in enumerate(ys):
                rbox(ax, ox, my-0.16, 1.25, 0.32, "#FFFFFF", GRAY_ED, lw=1.1, rad=0.08)
                arrow(ax, (mx+1.53, my), (ox-0.02, my), color="#AEB8C4", lw=1.1, mut=8)
            # badge: no shared wrong
            rbox(ax, 9.75, yc-0.42, 2.3, 0.84, "#FFFFFF", accent, lw=1.5, rad=0.1)
            txt(ax, 10.9, yc+0.14, "no shared", 9.6, INK, "bold")
            txt(ax, 10.9, yc-0.16, "wrong answer", 9.6, INK, "bold")
            c = Circle((9.95, yc+0.0), 0.0, facecolor="none")  # placeholder
            cc = Circle((11.72, yc), 0.16, facecolor=accent, edgecolor="none", zorder=6)
            ax.add_patch(cc); txt(ax, 11.72, yc, "\u2713", 10, "white", "bold", z=7)

        # regime label (left, vertical strip)
        txt(ax, 0.42, yc, band_title, 9.4, accent, "bold")

    # TOP = danger (H1, clause outside) ; BOTTOM = safe (H2, clause inside)
    regime(3.45, DANGERB, DANGER, "", complete=False)
    regime(0.35, SAFEB,  SAFE,  "", complete=True)

    # regime headers
    txt(ax, 6.3, 6.42, "Decisive clause OUTSIDE the prompt  (H1$_{external}$)", 11.5, DANGER, "bold")
    txt(ax, 6.3, 3.30, "Decisive clause INSIDE the prompt  (H2$_{derivable}$)", 11.5, SAFE, "bold")

    # danger metric strip
    txt(ax, 6.3, 3.62,
        "fake redundancy:  convergent delusion $\\approx$0.53   \u00b7   "
        "$k$ agents $\\to$ $\\approx$1 effective voice ($n_{eff}$=1.10)   \u00b7   "
        "models ask $\\approx$0.03% of the time",
        9.0, INK, "normal")
    txt(ax, 6.3, 0.18, "diverse models stay independent  \u00b7  no silent shared error ($\\approx$0.00)",
        9.0, INK, "normal")

    fig.savefig(path + ".pdf", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(path + ".png", dpi=200, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)

# =====================================================================
# FIGURE 2 — LPP detector mechanism + danger quadrant
# =====================================================================
def fig_lpp(path):
    fig, ax = plt.subplots(figsize=(12.4, 5.4))
    ax.set_xlim(0, 12.4); ax.set_ylim(0, 5.4); ax.axis("off")

    # ---- LEFT: 3-step pipeline ----
    txt(ax, 3.55, 5.15, "Latent-Premise Pinning (LPP): black-box, inference-only", 11.5, INK, "bold")

    # Stage 1: self-surface
    rbox(ax, 0.35, 2.55, 2.05, 1.5, CARDF, GRAY_ED, rad=0.06)
    txt(ax, 1.375, 3.80, "1 \u00b7 Self-surface", 10.2, INK, "bold")
    rbox(ax, 0.55, 3.30, 1.65, 0.34, "#FFFFFF", BLUEE, lw=1.1, rad=0.08)
    txt(ax, 1.375, 3.47, "any LLM (black-box)", 8.0, INK)
    txt(ax, 1.375, 2.98, '"which unstated,\ndecision-relevant\npremises must be fixed?"', 7.4, "#55607A")

    # premises out
    prem = ["quarter convention?", "rounding?", "date range?"]
    for i, p in enumerate(prem):
        yy = 2.15 - i*0.42
        rbox(ax, 0.55, yy-0.16, 2.0, 0.32, "#FFFFFF", GRAY_ED, lw=1.0, rad=0.08)
        txt(ax, 1.55, yy, p, 7.8, INK)
    txt(ax, 1.55, 0.62, "self-surfaced premises\n(no gold leakage)", 7.6, "#55607A")

    # Stage 2: pin
    rbox(ax, 2.95, 2.55, 2.35, 1.5, CARDF, GRAY_ED, rad=0.06)
    txt(ax, 4.125, 3.80, "2 \u00b7 Counterfactually pin", 9.5, INK, "bold")
    txt(ax, 4.125, 3.42, "pin one premise to its\nown candidate values", 8.0, "#55607A")
    # value chips + candidate answers
    for i, (v, yy) in enumerate(zip(["v\u2081","v\u2082","v\u2083"], [2.98,2.66,2.34])):
        rbox(ax, 3.15, yy-0.13, 0.5, 0.26, BLUEF, BLUEE, lw=1.0, rad=0.1)
        txt(ax, 3.4, yy, v, 8.2, INK)
        rbox(ax, 4.05, yy-0.13, 1.05, 0.26, "#FFFFFF", GRAY_ED, lw=1.0, rad=0.1)
        txt(ax, 4.575, yy, "answer", 7.6, INK)
        arrow(ax, (3.67, yy), (4.03, yy), color=DEEP, lw=1.2, mut=8)

    # Stage 3: cluster
    rbox(ax, 5.85, 2.55, 2.35, 1.5, CARDF, GRAY_ED, rad=0.06)
    txt(ax, 7.025, 3.80, "3 \u00b7 Cluster (executable)", 10.2, INK, "bold")
    txt(ax, 7.025, 3.42, "group answers by\nrunning the code \u2699", 8.0, "#55607A")
    # two clusters
    rbox(ax, 6.05, 2.72, 0.95, 0.5, "#EDE7F5", "#7A5EA8", lw=1.2, rad=0.1)
    rbox(ax, 7.15, 2.72, 0.95, 0.5, "#E7EEF7", BLUEE, lw=1.2, rad=0.1)
    txt(ax, 6.525, 2.97, "cluster A", 7.8, INK); txt(ax, 7.625, 2.97, "cluster B", 7.8, INK)
    rbox(ax, 6.35, 2.02, 1.35, 0.4, "#FFFFFF", DEEP, lw=1.5, rad=0.1)
    txt(ax, 7.025, 2.22, "$H_{ctx}$ = entropy", 8.6, DEEP, "bold")

    # pipeline connectors
    arrow(ax, (2.42, 3.3), (2.93, 3.3), color=GRAY_ED, lw=1.5)
    arrow(ax, (5.32, 3.3), (5.83, 3.3), color=GRAY_ED, lw=1.5)

    # ---- RIGHT: danger quadrant ----
    qx, qy, qs = 9.05, 1.15, 3.05   # origin + size of quadrant axes
    # quadrant background: highlight low-Hseed x high-Hctx (top-left)
    rbox(ax, qx, qy+qs/2, qs/2, qs/2, DANGERB, "none", rad=0.02, z=1)
    # axes
    ax.plot([qx, qx+qs], [qy, qy], color=INK, lw=1.4, zorder=4)
    ax.plot([qx, qx], [qy, qy+qs], color=INK, lw=1.4, zorder=4)
    ax.plot([qx, qx+qs], [qy+qs/2, qy+qs/2], color="#C4CBD6", lw=0.9, ls=(0,(3,2)), zorder=3)
    ax.plot([qx+qs/2, qx+qs/2], [qy, qy+qs], color="#C4CBD6", lw=0.9, ls=(0,(3,2)), zorder=3)
    txt(ax, qx+qs/2, qy-0.30, "$H_{seed}$: semantic entropy (resampling) \u2192", 8.8, INK)
    ax.text(qx-0.32, qy+qs/2, "$H_{ctx}$: premise pinning \u2192", fontsize=8.8, color=INK,
            ha="center", va="center", rotation=90, zorder=5)
    # danger label (top-left, above the points)
    txt(ax, qx+qs*0.26, qy+qs*0.93, "DANGER quadrant", 9.4, DANGER, "bold")

    rng = np.random.default_rng(7)
    # AMB+ : low Hseed, high Hctx (top-left)
    ax_ = rng.normal(0.15, 0.055, 22).clip(0.02, 0.40)
    ay_ = rng.normal(0.70, 0.09, 22).clip(0.52, 0.85)
    ax.scatter(qx+ax_*qs, qy+ay_*qs, s=26, color=DANGER, edgecolor="white", lw=0.5, zorder=6, label="AMB+ (ambiguous)")
    # AMB- : near origin
    bx_ = rng.normal(0.12, 0.06, 16).clip(0.02, 0.35)
    by_ = rng.normal(0.12, 0.06, 16).clip(0.02, 0.35)
    ax.scatter(qx+bx_*qs, qy+by_*qs, s=22, color="#9AA6B4", edgecolor="white", lw=0.5, zorder=6, label="AMB\u2212 (unambiguous)")

    # callout (bottom-right, empty quadrant)
    rbox(ax, qx+qs*0.46, qy+qs*0.10, qs*0.52, 0.46, "#FFFFFF", DEEP, lw=1.3, rad=0.12, z=7)
    ax.text(qx+qs*0.72, qy+qs*0.10+0.23, "AUROC 0.895\nvs 0.581 (sem. entropy)",
            fontsize=7.8, color=DEEP, ha="center", va="center", zorder=8, weight="bold")

    # legend
    ax.legend(loc="lower left", bbox_to_anchor=(0.70, 0.02), fontsize=7.6, frameon=False)

    # connector from H_ctx to quadrant y-axis
    arrow(ax, (7.72, 2.22), (qx-0.02, qy+qs*0.72), color=DEEP, lw=1.3, rad=-0.15, mut=10)

    fig.savefig(path + ".pdf", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(path + ".png", dpi=200, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    fig_fake_redundancy(os.path.join(here, "fig_ga_fake_redundancy"))
    fig_lpp(os.path.join(here, "fig_lpp_mechanism"))
    print("done: fig_ga_fake_redundancy.{pdf,png}, fig_lpp_mechanism.{pdf,png}")
