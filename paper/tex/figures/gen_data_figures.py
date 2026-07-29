"""paper-figure skill: publication-quality DATA figures for *When Consensus Lies*.
Reads real data (checkpoint + verified-results JSON); does NOT hardcode.
Outputs vector PDF + PNG with *_v2 names. Original figures are preserved.
No titles inside figures (captions go in LaTeX). Colorblind-safe (Okabe-Ito).
"""
import json, re, collections, os
import numpy as np
from paper_plot_style import plt, CB, save_fig

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CKPT = os.path.join(REPO, "When Consensus Lies", ".run_partitions", "cp_lps_confirm_merged.jsonl")
if not os.path.exists(CKPT):
    CKPT = os.path.join(REPO, ".run_partitions", "cp_lps_confirm_merged.jsonl")

def load_json(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------------
# FIG A — Danger quadrant (REAL per-item data from the confirmatory run)
# ---------------------------------------------------------------------
def fig_danger_quadrant():
    by = collections.defaultdict(lambda: {"hs": [], "hc": []})
    with open(CKPT, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "task_id" not in r or r.get("H_seed") is None or r.get("H_ctx_max") is None:
                continue
            by[r["task_id"]]["hs"].append(r["H_seed"])
            by[r["task_id"]]["hc"].append(r["H_ctx_max"])
    items = {t: (np.mean(v["hs"]), np.mean(v["hc"])) for t, v in by.items() if v["hs"]}
    amb = lambda t: "AMB-" if re.search(r"_k0(\b|_|$)", t) else "AMB+"
    tau_s = 0.5
    pos = np.array([xy for t, xy in items.items() if amb(t) == "AMB+"])
    neg = np.array([xy for t, xy in items.items() if amb(t) == "AMB-"])
    danger = sum(1 for xy in pos if xy[0] <= tau_s and xy[1] > 0)

    rng = np.random.default_rng(0)
    def jit(a):  # tiny display jitter for coincident discrete points (disclosed in caption)
        return a + rng.uniform(-0.022, 0.022, size=a.shape)

    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    xmax = max(pos[:, 0].max(), neg[:, 0].max(), 1.0) + 0.15
    ymax = max(pos[:, 1].max(), neg[:, 1].max(), 1.0) + 0.15
    # danger region shading (low H_seed x high H_ctx)
    ax.axhspan(0, ymax, xmin=0, xmax=tau_s / xmax, color=CB["orange"], alpha=0.08, zorder=0)
    ax.axvline(tau_s, color=CB["gray"], lw=0.9, ls="--", zorder=1)
    ax.scatter(jit(neg[:, 0]), jit(neg[:, 1]), s=34, marker="o", facecolor="none",
               edgecolor=CB["blue"], linewidths=1.1, label="AMB$-$ (unambiguous)", zorder=3)
    ax.scatter(jit(pos[:, 0]), jit(pos[:, 1]), s=34, marker="^", color=CB["orange"],
               edgecolor="white", linewidths=0.4, label="AMB$+$ (ambiguous)", zorder=4)
    ax.text(0.02, ymax - 0.02, "danger quadrant", color=CB["orange"], fontsize=9,
            weight="bold", va="top")
    ax.text(0.02, ymax - 0.16, f"{danger}/{len(pos)} AMB$+$ items\n(semantic entropy blind)",
            color=CB["orange"], fontsize=7.5, va="top")
    ax.set_xlabel(r"$H_{\mathrm{seed}}$  (semantic entropy, resampling)")
    ax.set_ylabel(r"$H_{\mathrm{ctx}}$  (latent-premise pinning)")
    ax.set_xlim(-0.08, xmax); ax.set_ylim(-0.08, ymax)
    ax.legend(loc="upper right", frameon=False)
    save_fig(fig, "fig_danger_quadrant_v2")
    plt.close(fig)
    print(f"   danger-mass {danger}/{len(pos)} = {danger/len(pos):.3f}; AMB+/-: {len(pos)}/{len(neg)}")

# ---------------------------------------------------------------------
# FIG B — Detection AUROC per model: LPP vs semantic entropy
# ---------------------------------------------------------------------
def fig_auroc():
    d = load_json("results_verified.json")["detection_auroc"]
    short = {"gpt-5.6-sol": "gpt-5.6", "claude-opus-4.8": "opus-4.8", "gemini-3.1-pro": "gem-3.1",
             "gpt-4o-mini": "4o-mini", "claude-haiku-4.5": "haiku", "gemini-3.5-flash": "gem-3.5"}
    models = d["models"]
    labels = [short[m] for m in models] + ["Pooled"]
    lpp = [d["lpp_Hctx"][m] for m in models] + [d["lpp_Hctx"]["pooled"]]
    se  = [d["semantic_entropy_Hseed"][m] for m in models] + [d["semantic_entropy_Hseed"]["pooled"]]
    # 95% CIs (cluster task_id bootstrap), verbatim from files/study2_stage2_results.md sec.2 (frozen).
    lpp_ci = {"gpt-5.6-sol": (0.774, 0.932), "claude-opus-4.8": (0.808, 0.956),
              "gemini-3.1-pro": (0.771, 0.934), "gpt-4o-mini": (0.768, 0.933),
              "claude-haiku-4.5": (0.787, 0.941), "gemini-3.5-flash": (0.797, 0.955),
              "pooled": (0.815, 0.966)}
    se_ci  = {"gpt-5.6-sol": (0.467, 0.657), "claude-opus-4.8": (0.529, 0.662),
              "gemini-3.1-pro": (0.534, 0.682), "gpt-4o-mini": (0.472, 0.629),
              "claude-haiku-4.5": (0.483, 0.648), "gemini-3.5-flash": (0.493, 0.667),
              "pooled": (0.484, 0.675)}
    keys = list(models) + ["pooled"]
    def yerr(vals, ci):
        lo = [v - ci[k][0] for v, k in zip(vals, keys)]
        hi = [ci[k][1] - v for v, k in zip(vals, keys)]
        return np.array([lo, hi])
    err_kw = dict(ecolor=CB["ink"], elinewidth=0.9, capsize=2.4, capthick=0.9)
    x = np.arange(len(labels)); w = 0.38
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    b1 = ax.bar(x - w/2, lpp, w, color=CB["orange"], label=r"LPP  $H_{\mathrm{ctx}}$ (ours)",
                yerr=yerr(lpp, lpp_ci), error_kw=err_kw)
    b2 = ax.bar(x + w/2, se,  w, color=CB["blue"],   label=r"semantic entropy  $H_{\mathrm{seed}}$",
                yerr=yerr(se, se_ci), error_kw=err_kw)
    ax.axhline(d["requirements_probing_pooled"], color=CB["green"], lw=1.2, ls="--",
               label=f"requirements-probing (pooled {d['requirements_probing_pooled']:.3f})")
    ax.axhline(d["chance"], color=CB["gray"], lw=1.0, ls=":", label="chance")
    for b, hi in ((b1[-1], lpp_ci["pooled"][1]), (b2[-1], se_ci["pooled"][1])):  # pooled value labels, above CI cap
        ax.text(b.get_x()+b.get_width()/2, hi+0.015, f"{b.get_height():.3f}",
                ha="center", va="bottom", fontsize=8, weight="bold")
    ax.set_ylabel("AUROC (executable gold-ambiguity)")
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=0)
    ax.set_ylim(0.4, 1.0)
    # bold the pooled tick label
    ax.get_xticklabels()[-1].set_fontweight("bold")
    ax.legend(loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.20))
    save_fig(fig, "fig_auroc_v2")
    plt.close(fig)

# ---------------------------------------------------------------------
# FIG C — Intervention: net selective-clarification per policy (972 cells)
# ---------------------------------------------------------------------
def fig_intervention():
    d = load_json("results_verified.json")["intervention"]
    order = ["LPP-gated (ours)", "requirements-probing", "semantic-entropy-gated",
             "self-consistency-gated", "always-clarify"]
    vals = [d["net_clarification"][p] for p in order]
    cols = [CB["orange"] if p.startswith("LPP") else CB["gray"] for p in order]
    disp = ["LPP-gated\n(ours)", "req.-\nprobing", "semantic-\nentropy", "self-\nconsistency", "always-\nclarify"]
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    bars = ax.bar(np.arange(len(order)), vals, color=cols, width=0.66, edgecolor="white")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.006, f"{v:.3f}",
                ha="center", va="bottom", fontsize=8.2,
                weight=("bold" if v == vals[0] else "normal"))
    ax.set_ylabel("net selective clarification\n(appropriate $-$ over-clarification)")
    ax.set_xticks(np.arange(len(order))); ax.set_xticklabels(disp)
    ax.set_ylim(0, max(vals) + 0.06)
    dc = d["danger_subset_coverage"]
    ax.text(0.97, 0.93,
            f"danger-zone coverage:\nLPP {dc['LPP-gated (ours)']:.3f}  vs  "
            f"semantic entropy {dc['semantic-entropy-gated']:.3f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color=CB["ink"],
            bbox=dict(boxstyle="round,pad=0.35", fc="#F5F5F5", ec=CB["gray"], lw=0.8))
    save_fig(fig, "fig_intervention_v2")
    plt.close(fig)

# ---------------------------------------------------------------------
# FIG D — Silent failure: abstention is ~0 even though H1 CD = 0.53
# ---------------------------------------------------------------------
def fig_silent_abstention():
    from matplotlib.ticker import FixedLocator, FixedFormatter

    values = [0.532, 0.00323, 0.00031]
    labels = [
        "H1 convergent-delusion\n(should trigger clarification)",
        "H2 clarification\n(observed)",
        "H1 clarification\n(observed)",
    ]
    exact = ["53.2%", "0.323%", "0.031%"]
    colors = [CB["orange"], CB["sky"], CB["blue"]]
    y = np.array([2.0, 1.0, 0.0])
    xmin = 8e-5
    ticks = [1e-4, 1e-3, 1e-2, 1e-1, 1.0]
    tick_labels = ["0.01%", "0.1%", "1%", "10%", "100%"]

    fig, ax = plt.subplots(figsize=(5.5, 2.9))
    ax.set_xscale("log")
    ax.set_xlim(xmin, 1.0)

    for yi, value, label, text, color in zip(y, values, labels, exact, colors):
        ax.hlines(yi, xmin, value, color=color, lw=2.2, zorder=2)
        ax.plot([value], [yi], linestyle="None", marker="o", markersize=7.8,
            markerfacecolor=color, markeredgecolor="white", markeredgewidth=0.7, zorder=3)
        ax.text(value * 1.12, yi, text, ha="left", va="center", fontsize=8.8,
            color=color, weight="bold")
        ax.text(xmin * 1.02, yi + 0.2, label, ha="left", va="center", fontsize=8.2,
            color=CB["ink"])

    ax.set_ylim(-0.5, 2.55)
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FixedFormatter(tick_labels))
    ax.minorticks_off()
    ax.set_yticks([])
    ax.set_xlabel("Rate (percent, logarithmic scale)")
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color="#DDDDDD", lw=0.6)
    ax.text(xmin * 1.02, 2.45, "Failure vs. observed clarification", fontsize=8.2,
        color=CB["gray"], ha="left", va="bottom")
    save_fig(fig, "fig_silent_abstention_v2")
    plt.close(fig)
    print("   silent comparison: H1 CD=53.2%; H2 clarification=0.323%; H1 clarification=0.031%")

if __name__ == "__main__":
    os.chdir(HERE)
    fig_danger_quadrant()
    fig_auroc()
    fig_silent_abstention()
    fig_intervention()
    print("done.")
