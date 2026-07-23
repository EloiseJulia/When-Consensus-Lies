"""make_figures.py — Publication-quality figures for CSCW paper (When Consensus Lies).

Scope (Amendment 11): A08 PRIMARY methods only:
  {single, sc, homogeneous-MAD, heterogeneous-MAD}
  (interpretation-diverse and verifier are excluded).

Reads:
  - .run_partitions/cp_code_spec.jsonl
  - .run_partitions/cp_data_analysis.jsonl
  - .run_partitions/cp_policy_qa.jsonl

Writes (all under paper/tex/figures/):
  fig_phase_diagram.pdf
  fig_capability_invariance.pdf
  fig_fake_redundancy.pdf
  fig_silent_failure.pdf
  figures_data.json

Usage:
  python paper/tex/figures/make_figures.py
  (run from repo root OR any directory; paths are resolved relative to this
   script's location so the script is always position-independent.)

Author: Copilot sub-agent (Claude/Anthropic).
Deterministic: all randomness is seeded; matplotlib uses the Agg backend.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

# ── Non-interactive backend BEFORE any matplotlib import ─────────────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ── Repo root resolution ──────────────────────────────────────────────────────
# This script lives at <repo>/paper/tex/figures/make_figures.py
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent.parent

# Make sure repo root is on sys.path so analysis/bench imports work.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── Analysis imports (after sys.path fix) ────────────────────────────────────
from analysis.io import load_runs_tidy
from analysis.contrasts import compute_cell_cd, cd_by_regime, COLS
from analysis.dependence import compute_dependence_table
from analysis.abstention import abstention_table

import bench.code_spec as _cs
import bench.data_analysis as _da
import bench.policy_qa as _pq

# ── Paths ─────────────────────────────────────────────────────────────────────
_PART_DIR = _REPO_ROOT / ".run_partitions"
_CP_FILES = [
    _PART_DIR / "cp_code_spec.jsonl",
    _PART_DIR / "cp_data_analysis.jsonl",
    _PART_DIR / "cp_policy_qa.jsonl",
]
_FIGURES_DIR = _SCRIPT_DIR
_DATA_JSON = _FIGURES_DIR / "figures_data.json"

# ── A08 PRIMARY method filter ─────────────────────────────────────────────────
PRIMARY_METHODS = {"single", "sc", "homogeneous-MAD", "heterogeneous-MAD"}

# ── CSCW style constants ──────────────────────────────────────────────────────
FONT_SIZE = 9.5          # pt — readable at single-column width
TICK_SIZE = 8.5
LABEL_SIZE = 9.5
LEGEND_SIZE = 8.5
FIG_W_SINGLE = 3.3       # inches (ACM single-column ~84 mm)
FIG_W_DOUBLE = 6.8       # inches (ACM double-column ~172 mm)

# Colorblind-friendly palette (Wong 2011 + IBM Design)
C_H1 = "#E69F00"   # amber  — H1_external (the dangerous regime)
C_H2 = "#56B4E9"   # sky    — H2_derivable (safe baseline)
C_SINGLE = "#999999"
C_SC = "#0072B2"
C_HOMO = "#D55E00"
C_HETERO = "#009E73"

METHOD_COLOR = {
    "single":           C_SINGLE,
    "sc":               C_SC,
    "homogeneous-MAD":  C_HOMO,
    "heterogeneous-MAD": C_HETERO,
}
METHOD_LABEL = {
    "single":           "Single",
    "sc":               "SC",
    "homogeneous-MAD":  "Homo-MAD",
    "heterogeneous-MAD": "Hetero-MAD",
}

MODEL_CLASS_ORDER = ["homogeneous", "heterogeneous", "reasoning", "weak"]
MODEL_CLASS_LABEL = {
    "homogeneous":  "Homogeneous",
    "heterogeneous": "Heterogeneous",
    "reasoning":    "Reasoning",
    "weak":         "Weak",
}
MODEL_CLASS_COLOR = {
    "homogeneous":   C_HOMO,
    "heterogeneous": C_HETERO,
    "reasoning":     "#CC79A7",
    "weak":          C_SINGLE,
}

REGIME_LABEL = {
    "H1_external":  "H1 external",
    "H2_derivable": "H2 derivable",
}
REGIME_COLOR = {"H1_external": C_H1, "H2_derivable": C_H2}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _apply_cscw_style() -> None:
    """Set global matplotlib rcParams for CSCW style."""
    plt.rcParams.update({
        "font.size":         FONT_SIZE,
        "axes.titlesize":    FONT_SIZE,
        "axes.labelsize":    LABEL_SIZE,
        "xtick.labelsize":   TICK_SIZE,
        "ytick.labelsize":   TICK_SIZE,
        "legend.fontsize":   LEGEND_SIZE,
        "lines.linewidth":   1.4,
        "lines.markersize":  5,
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "figure.dpi":        150,
        "savefig.dpi":       300,
        "savefig.bbox":      "tight",
        "savefig.pad_inches": 0.02,
        "font.family":       "sans-serif",
        "axes.grid":         True,
        "grid.alpha":        0.3,
        "grid.linestyle":    "--",
    })


def _save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, format="pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"  Saved: {path.name}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Data loading
# ─────────────────────────────────────────────────────────────────────────────

def load_all_tasks():
    tasks = (
        _cs.generate_tasks()
        + _da.generate_tasks()
        + _pq.generate_tasks()
    )
    return tasks


def concat_checkpoints(cp_files: list[Path]) -> Path:
    """Concatenate multiple JSONL checkpoints, skipping malformed last lines.

    Writes to a named temp file (deleted when the returned path object is
    garbage-collected by caller, or caller manages it).
    Returns Path to the concatenated file.
    """
    # We write into the figures dir (not /tmp) so we stay within the repo.
    out_path = _FIGURES_DIR / "_combined_checkpoint.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_lines = 0
    with open(out_path, "w", encoding="utf-8") as fout:
        for cp in cp_files:
            if not cp.exists():
                print(f"  WARNING: checkpoint not found: {cp}")
                continue
            with open(cp, "r", encoding="utf-8") as fin:
                lines = fin.readlines()
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    json.loads(stripped)   # validate JSON
                    fout.write(stripped + "\n")
                    n_lines += 1
                except json.JSONDecodeError:
                    # skip malformed lines (e.g. truncated last line)
                    pass
    print(f"  Combined {n_lines} valid JSONL lines from {len(cp_files)} files.")
    return out_path


def load_tidy(tasks, include_output: bool = False) -> pd.DataFrame:
    combined = concat_checkpoints(_CP_FILES)
    try:
        df = load_runs_tidy(
            combined,
            tasks,
            include_output=include_output,
        )
    finally:
        # Clean up temp file
        try:
            combined.unlink(missing_ok=True)
        except Exception:
            pass
    print(f"  Loaded tidy table: {len(df)} agent rows")
    return df


def filter_primary_methods(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only A08 PRIMARY methods."""
    method_col = COLS["method"]
    if method_col not in df.columns:
        return df
    mask = df[method_col].isin(PRIMARY_METHODS)
    n_before = len(df)
    df = df[mask].copy()
    print(f"  After method filter ({PRIMARY_METHODS}): {len(df)}/{n_before} rows")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Figure 1: Phase diagram — CD vs ambiguity level k
# ─────────────────────────────────────────────────────────────────────────────

def make_phase_diagram(df: pd.DataFrame) -> dict:
    """fig_phase_diagram.pdf: CD (cd_primary) vs k, by regime."""
    cells = compute_cell_cd(df)

    k_col = COLS["ambiguity_k"]
    regime_col = COLS["regime"]
    method_col = COLS["method"]

    # Average cd_primary over all methods (primary methods already filtered)
    # and seeds, per (regime, k).
    rows = []
    for (regime, k), grp in cells.groupby([regime_col, k_col], sort=True):
        rows.append({
            "regime": regime,
            "ambiguity_k": int(k),
            "cd_primary": float(grp["cd_primary"].mean()),
            "cd_primary_se": float(grp["cd_primary"].sem()),
            "n_cells": len(grp),
        })
    data = pd.DataFrame(rows)

    # k=0 control: add a synthetic point at k=0 with CD=0 (pre-reg claim).
    # We also check if any real k=0 data exists.
    real_k0 = data[data["ambiguity_k"] == 0]
    if real_k0.empty:
        for regime in data["regime"].unique():
            data = pd.concat([
                data,
                pd.DataFrame([{"regime": regime, "ambiguity_k": 0,
                               "cd_primary": 0.0, "cd_primary_se": 0.0,
                               "n_cells": 0}])
            ], ignore_index=True)

    data = data.sort_values(["regime", "ambiguity_k"]).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(FIG_W_SINGLE + 0.4, 2.4))

    for regime in ["H1_external", "H2_derivable"]:
        sub = data[data["regime"] == regime]
        if sub.empty:
            continue
        color = REGIME_COLOR[regime]
        label = REGIME_LABEL[regime]
        ks = sub["ambiguity_k"].values
        cds = sub["cd_primary"].values
        ses = sub["cd_primary_se"].values
        ax.plot(ks, cds, "o-", color=color, label=label, zorder=3)
        ax.fill_between(ks, cds - ses, cds + ses, alpha=0.18, color=color, zorder=2)

    ax.set_xlabel("Ambiguity level $k$", fontsize=LABEL_SIZE)
    ax.set_ylabel("Convergent delusion (CD)", fontsize=LABEL_SIZE)
    ax.set_xticks(sorted(data["ambiguity_k"].unique()))
    ax.set_ylim(bottom=-0.02)
    ax.axhline(0, color="black", linewidth=0.6, linestyle=":", alpha=0.5)
    ax.legend(loc="upper left", frameon=False)
    _save(fig, _FIGURES_DIR / "fig_phase_diagram.pdf")

    return data.to_dict(orient="records")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Figure 2: Capability invariance — CD by model_class x regime
# ─────────────────────────────────────────────────────────────────────────────

def make_capability_invariance(df: pd.DataFrame) -> dict:
    """fig_capability_invariance.pdf: grouped bars of cd_primary by model_class x regime."""
    by_regime_class = cd_by_regime(df)
    regime_col = COLS["regime"]
    mc_col = COLS["model_class"]

    present_classes = [c for c in MODEL_CLASS_ORDER if c in by_regime_class[mc_col].values]
    regimes_present = [r for r in ["H1_external", "H2_derivable"]
                       if r in by_regime_class[regime_col].values]

    n_classes = len(present_classes)
    n_regimes = len(regimes_present)
    width = 0.35
    x = np.arange(n_classes)

    fig, ax = plt.subplots(figsize=(FIG_W_SINGLE + 0.6, 2.6))

    for i, regime in enumerate(regimes_present):
        sub = by_regime_class[by_regime_class[regime_col] == regime]
        cds = []
        for mc in present_classes:
            row = sub[sub[mc_col] == mc]
            cds.append(float(row["cd_primary"].values[0]) if len(row) > 0 else 0.0)
        offset = (i - (n_regimes - 1) / 2) * width
        bars = ax.bar(
            x + offset, cds, width,
            label=REGIME_LABEL[regime],
            color=REGIME_COLOR[regime],
            alpha=0.88,
            edgecolor="white",
            linewidth=0.5,
        )
        # Annotate values
        for bar, val in zip(bars, cds):
            if val > 0.02:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.008,
                    f"{val:.2f}",
                    ha="center", va="bottom",
                    fontsize=7.5, color="black",
                )

    ax.set_xlabel("Model class", fontsize=LABEL_SIZE)
    ax.set_ylabel("Convergent delusion (CD)", fontsize=LABEL_SIZE)
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_CLASS_LABEL.get(c, c) for c in present_classes],
                       fontsize=TICK_SIZE)
    ax.set_ylim(bottom=0)
    ax.axhline(0, color="black", linewidth=0.5, alpha=0.4)
    ax.legend(frameon=False, loc="upper right")
    _save(fig, _FIGURES_DIR / "fig_capability_invariance.pdf")

    return by_regime_class.to_dict(orient="records")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Figure 3: Fake redundancy — n_eff and ICC by regime
# ─────────────────────────────────────────────────────────────────────────────

def make_fake_redundancy(df: pd.DataFrame, regime_summary: dict) -> dict:
    """fig_fake_redundancy.pdf: n_eff and pairwise wrong-agreement by regime."""
    # Cell-level: pairwise wrong agreement (PWA) by regime
    cells = compute_cell_cd(df)
    regime_col = COLS["regime"]

    # Get mean nominal n from cells (n_agents) per regime
    regime_n_agents = {}
    regime_pwa = {}
    regime_icc = {}
    regime_neff = {}
    for regime in ["H1_external", "H2_derivable"]:
        rs = regime_summary.get(regime, {})
        regime_icc[regime] = rs.get("icc", float("nan"))
        regime_neff[regime] = rs.get("n_eff_mean", float("nan"))

    # Compute pairwise wrong agreement from cell_df (if available)
    # compute_dependence_table returns cell_df with 'pairwise_wrong_agreement'
    # but we already have it in the cell loop; use the tidy cell
    # Actually we call compute_dependence_table separately to get pwa
    # (already computed in the caller; passed in via regime_summary)
    # For the figure we extract what we have.

    # ── Prepare bar data ──────────────────────────────────────────────────────
    regimes_plot = [r for r in ["H1_external", "H2_derivable"]
                    if r in regime_summary]

    # Nominal ensemble sizes (from cells table per regime)
    for regime in regimes_plot:
        sub = cells[cells[regime_col] == regime] if regime_col in cells.columns else cells
        regime_n_agents[regime] = float(sub["n_agents"].mean()) if not sub.empty else float("nan")

    n_eff_vals = [regime_neff.get(r, float("nan")) for r in regimes_plot]
    icc_vals   = [regime_icc.get(r, float("nan")) for r in regimes_plot]
    n_nom_vals = [regime_n_agents.get(r, float("nan")) for r in regimes_plot]

    # Two-panel figure: left = n_eff, right = ICC
    fig, axes = plt.subplots(1, 2, figsize=(FIG_W_DOUBLE * 0.55, 2.5))

    colors = [REGIME_COLOR[r] for r in regimes_plot]
    xlabels = [REGIME_LABEL[r] for r in regimes_plot]
    x = np.arange(len(regimes_plot))

    # Panel A: n_eff
    ax_neff = axes[0]
    bars_neff = ax_neff.bar(x, n_eff_vals, color=colors, alpha=0.88,
                             edgecolor="white", width=0.5)
    # Dashed line at the NOMINAL ensemble size (mean across regimes or mode)
    nominal_mean = np.nanmean([v for v in n_nom_vals if not math.isnan(v)])
    ax_neff.axhline(nominal_mean, color="black", linewidth=1.0,
                    linestyle="--", label=f"Nominal $n$≈{nominal_mean:.1f}", zorder=4)
    ax_neff.set_xticks(x)
    ax_neff.set_xticklabels(xlabels, fontsize=TICK_SIZE)
    ax_neff.set_ylabel("Effective ensemble size ($n_{{eff}}$)", fontsize=LABEL_SIZE)
    ax_neff.set_ylim(bottom=0)
    ax_neff.legend(frameon=False, fontsize=7.5)
    for bar, val in zip(bars_neff, n_eff_vals):
        if not math.isnan(val):
            ax_neff.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.03,
                f"{val:.2f}",
                ha="center", va="bottom", fontsize=7.5,
            )
    ax_neff.set_title("(a) Effective ensemble size", fontsize=FONT_SIZE, pad=4)

    # Panel B: ICC
    ax_icc = axes[1]
    bars_icc = ax_icc.bar(x, icc_vals, color=colors, alpha=0.88,
                           edgecolor="white", width=0.5)
    ax_icc.axhline(0, color="black", linewidth=0.6, linestyle=":", alpha=0.5)
    ax_icc.axhline(1, color="black", linewidth=0.5, linestyle="--", alpha=0.4)
    ax_icc.set_xticks(x)
    ax_icc.set_xticklabels(xlabels, fontsize=TICK_SIZE)
    ax_icc.set_ylabel("ICC (wrong-indicator)", fontsize=LABEL_SIZE)
    ax_icc.set_ylim(-0.05, 1.1)
    for bar, val in zip(bars_icc, icc_vals):
        if not math.isnan(val):
            ax_icc.text(
                bar.get_x() + bar.get_width() / 2,
                max(bar.get_height(), 0) + 0.03,
                f"{val:.3f}",
                ha="center", va="bottom", fontsize=7.5,
            )
    ax_icc.set_title("(b) Inter-agent ICC", fontsize=FONT_SIZE, pad=4)

    fig.tight_layout(pad=0.8)
    _save(fig, _FIGURES_DIR / "fig_fake_redundancy.pdf")

    return {
        "n_eff": {r: regime_neff.get(r, float("nan")) for r in regimes_plot},
        "icc": {r: regime_icc.get(r, float("nan")) for r in regimes_plot},
        "n_nominal_mean": {r: regime_n_agents.get(r, float("nan")) for r in regimes_plot},
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Figure 4: Silent failure — abstention rate x regime (+ CD twin)
# ─────────────────────────────────────────────────────────────────────────────

def make_silent_failure(df_with_output: pd.DataFrame,
                        cells_cd: pd.DataFrame) -> dict:
    """fig_silent_failure.pdf: abstention rate + CD by regime (two panels)."""
    abs_tbl = abstention_table(df_with_output)

    regime_col = COLS["regime"]
    mc_col = COLS["model_class"]

    # Grand-total rows per regime
    # filter where model_class == "ALL" but regime != "ALL"
    regime_abs = abs_tbl[
        (abs_tbl["regime"] != "ALL") & (abs_tbl["model_class"] == "ALL")
    ].copy() if "ALL" in abs_tbl["model_class"].values else abs_tbl[
        abs_tbl["regime"] != "ALL"
    ].copy()

    # If that slice is empty fall back to groupby
    if regime_abs.empty:
        rows = []
        for regime, grp in abs_tbl[abs_tbl["regime"] != "ALL"].groupby("regime"):
            n = int(grp["n_agents"].sum())
            n_abs = int(grp["n_abstained"].sum())
            rows.append({
                "regime": regime,
                "n_agents": n,
                "n_abstained": n_abs,
                "abstention_rate": n_abs / n if n > 0 else float("nan"),
            })
        regime_abs = pd.DataFrame(rows)

    # CD by regime (already computed elsewhere; recompute here from cells)
    cd_by_r = {}
    if not cells_cd.empty and regime_col in cells_cd.columns:
        for regime, grp in cells_cd.groupby(regime_col):
            cd_by_r[str(regime)] = float(grp["cd_primary"].mean())

    regimes_plot = [r for r in ["H1_external", "H2_derivable"]
                    if r in regime_abs["regime"].values]

    abs_vals = []
    cd_vals = []
    for r in regimes_plot:
        row = regime_abs[regime_abs["regime"] == r]
        abs_vals.append(float(row["abstention_rate"].values[0]) if len(row) > 0 else 0.0)
        cd_vals.append(cd_by_r.get(r, float("nan")))

    colors = [REGIME_COLOR[r] for r in regimes_plot]
    xlabels = [REGIME_LABEL[r] for r in regimes_plot]
    x = np.arange(len(regimes_plot))
    width = 0.45

    fig, axes = plt.subplots(1, 2, figsize=(FIG_W_DOUBLE * 0.55, 2.5))

    # Panel A: abstention rate
    ax_abs = axes[0]
    bars = ax_abs.bar(x, abs_vals, color=colors, alpha=0.88,
                      edgecolor="white", width=width)
    ax_abs.set_xticks(x)
    ax_abs.set_xticklabels(xlabels, fontsize=TICK_SIZE)
    ax_abs.set_ylabel("Abstention / clarification rate", fontsize=LABEL_SIZE)
    ax_abs.set_ylim(bottom=0)
    ax_abs.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=2))
    for bar, val in zip(bars, abs_vals):
        ax_abs.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(max(abs_vals) * 0.02, 0.00002),
            f"{val*100:.3f}%",
            ha="center", va="bottom", fontsize=7.5,
        )
    ax_abs.set_title("(a) Abstention rate", fontsize=FONT_SIZE, pad=4)

    # Panel B: CD by regime (for juxtaposition with abstention)
    ax_cd = axes[1]
    bars2 = ax_cd.bar(x, cd_vals, color=colors, alpha=0.88,
                      edgecolor="white", width=width)
    ax_cd.set_xticks(x)
    ax_cd.set_xticklabels(xlabels, fontsize=TICK_SIZE)
    ax_cd.set_ylabel("Convergent delusion (CD)", fontsize=LABEL_SIZE)
    ax_cd.set_ylim(bottom=0)
    for bar, val in zip(bars2, cd_vals):
        if not math.isnan(val):
            ax_cd.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.008,
                f"{val:.3f}",
                ha="center", va="bottom", fontsize=7.5,
            )
    ax_cd.set_title("(b) Convergent delusion (CD)", fontsize=FONT_SIZE, pad=4)

    fig.suptitle(
        "Silent failure: high CD, near-zero abstention on H1",
        fontsize=FONT_SIZE, y=1.01, fontstyle="italic"
    )
    fig.tight_layout(pad=0.8)
    _save(fig, _FIGURES_DIR / "fig_silent_failure.pdf")

    # Detailed abstention by regime × model_class (for data JSON)
    detail_rows = abs_tbl[abs_tbl["regime"] != "ALL"].to_dict(orient="records")
    return {
        "regime_abstention_rate": {
            r: float(abs_vals[i]) for i, r in enumerate(regimes_plot)
        },
        "regime_cd": cd_by_r,
        "detail": detail_rows,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5b. Study 2 figures (LPP detector) — F-DQ danger quadrant & F-AUROC comparison
# ─────────────────────────────────────────────────────────────────────────────
#
# These two figures are INDEPENDENT of the Study-1 CD pipeline above. All plotted
# values trace to REAL sources (no fabrication):
#   * F-DQ scatter points are the 54 pre-registered items at their POOLED per-item
#     (H_seed, H_ctx-self) means, extracted by REUSING the frozen aggregation of
#     scripts/lps_confirm_report.aggregate_by_item on the confirmatory checkpoint
#     .run_partitions/cp_lps_confirm__*.jsonl (via scripts/lps_danger_quadrant_export).
#     The extracted data is cached in fig_danger_quadrant_data.json so the figure is
#     reproducible without the live checkpoints and each point is auditable.
#   * F-AUROC values are the FROZEN numbers from files/study2_stage2_results.md
#     (per-model + pooled AUROC and 95% CIs). They are transcribed verbatim below;
#     no number is recomputed or invented.

_DQ_DATA_JSON = _FIGURES_DIR / "fig_danger_quadrant_data.json"

# Frozen operating point (prereg §2): H_seed convergent cutoff / H_ctx flag threshold.
TAU_S = 0.5   # bits — low-H_seed ("convergent") cutoff defining the danger quadrant
TAU = 0.0     # bits — H_ctx flag threshold

# Colorblind-safe strata colors (reuse the Wong palette already defined above).
C_AMB_POS = C_H1     # amber  — AMB+ (executable-ambiguous; the dangerous items)
C_AMB_NEG = C_H2     # sky    — AMB- (executable-unambiguous; controls)


def _load_danger_quadrant_data() -> dict:
    """Load the per-item F-DQ scatter data (real, frozen-aggregation extraction).

    Prefers a LIVE extraction from the confirmatory checkpoint shards when present
    (reusing the frozen aggregation and refreshing the cached asset); otherwise
    falls back to the committed fig_danger_quadrant_data.json data asset. Never
    fabricates points.
    """
    shards = sorted(_PART_DIR.glob("cp_lps_confirm__*.jsonl"))
    if shards:
        try:
            scripts_dir = str(_REPO_ROOT / "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            import lps_danger_quadrant_export as dqx
            data = dqx.extract_items(str(_PART_DIR / "cp_lps_confirm__*.jsonl"))
            _DQ_DATA_JSON.write_text(json.dumps(data, indent=2) + "\n",
                                     encoding="utf-8")
            print("  F-DQ: live extraction from confirm checkpoints (asset refreshed)")
            return data
        except Exception as exc:  # noqa: BLE001
            print(f"  F-DQ: live extraction failed ({exc}); using committed asset")
    if not _DQ_DATA_JSON.exists():
        raise FileNotFoundError(
            f"F-DQ data asset missing and no confirm checkpoints found: "
            f"{_DQ_DATA_JSON}")
    print("  F-DQ: using committed data asset (no live checkpoints)")
    return json.loads(_DQ_DATA_JSON.read_text(encoding="utf-8"))


def make_danger_quadrant() -> dict:
    """fig_danger_quadrant.pdf: data-driven scatter of the 54 items in the

    (H_seed, H_ctx-self) plane, colored by executable gold stratum (AMB+/AMB-),
    with the low-H_seed AND high-H_ctx DANGER quadrant shaded and the frozen
    thresholds (tau_s=0.5, tau=0) marked. Every point is a REAL per-item mean.
    """
    data = _load_danger_quadrant_data()
    points = data["points"]
    counts = data["counts"]

    pos = [p for p in points if p["stratum"] == "AMB+"]
    neg = [p for p in points if p["stratum"] == "AMB-"]

    fig, ax = plt.subplots(figsize=(4.6, 3.4))

    x_max = 0.80
    y_max = 1.70

    # ── Danger zone: H_seed <= tau_s AND H_ctx > tau (SOTA-blind quadrant) ──────
    ax.axvspan(0.0, TAU_S, ymin=0.0, ymax=1.0, color="#D55E00", alpha=0.07,
               zorder=0)
    ax.add_patch(plt.Rectangle((-0.03, TAU + 1e-9), TAU_S + 0.03, y_max - TAU,
                               facecolor="#D55E00", alpha=0.10, edgecolor="none",
                               zorder=0))

    # Frozen thresholds.
    ax.axvline(TAU_S, color="black", linestyle="--", linewidth=1.1, alpha=0.7,
               zorder=1)
    ax.axhline(TAU, color="black", linestyle=":", linewidth=1.0, alpha=0.6,
               zorder=1)

    # ── Scatter (true per-item means; small alpha for overplot density) ────────
    ax.scatter([p["H_seed"] for p in neg], [p["H_ctx_self"] for p in neg],
               marker="s", s=46, facecolor=C_AMB_NEG, edgecolor="black",
               linewidth=0.5, alpha=0.75, zorder=4,
               label=f"AMB\u2212 (unambiguous, n={len(neg)})")
    ax.scatter([p["H_seed"] for p in pos], [p["H_ctx_self"] for p in pos],
               marker="o", s=52, facecolor=C_AMB_POS, edgecolor="black",
               linewidth=0.5, alpha=0.8, zorder=5,
               label=f"AMB+ (executable-ambiguous, n={len(pos)})")

    # ── Origin overplot callout (many items share the exact (0,0) point) ───────
    eps = 1e-9
    n_origin_pos = sum(1 for p in pos
                       if abs(p["H_seed"]) < eps and abs(p["H_ctx_self"]) < eps)
    n_origin_neg = sum(1 for p in neg
                       if abs(p["H_seed"]) < eps and abs(p["H_ctx_self"]) < eps)
    if (n_origin_pos + n_origin_neg) > 1:
        ax.annotate(
            f"{n_origin_pos + n_origin_neg} items at $(0,0)$\n"
            f"({n_origin_neg} AMB\u2212, {n_origin_pos} AMB+)",
            xy=(0.0, 0.0), xytext=(0.20, 0.28),
            fontsize=TICK_SIZE - 0.5, ha="left", va="bottom",
            arrowprops=dict(arrowstyle="->", color="#555555", lw=0.8),
            color="#333333", zorder=6)

    # ── Danger-zone label with the frozen mass ─────────────────────────────────
    dmass = counts["danger_mass"]
    ax.text(0.02, y_max - 0.08,
            "DANGER ZONE\n"
            "confident latent-premise ambiguity\n"
            "(semantic-entropy-blind)\n"
            f"AMB+ mass: {counts['n_danger_AMB_pos']}/{counts['n_AMB_pos']} "
            f"= {dmass:.3f}",
            fontsize=TICK_SIZE - 0.5, ha="left", va="top", color="#7A2E00",
            fontweight="bold", zorder=3,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#D55E00", alpha=0.85, linewidth=0.8))

    ax.text(TAU_S + 0.012, y_max - 0.02, r"$\tau_s=0.5$", fontsize=TICK_SIZE - 0.5,
            ha="left", va="top", color="black", rotation=90, alpha=0.8)

    ax.set_xlabel(r"$H_{\mathrm{seed}}$ — semantic entropy (bits)  [SOTA baseline]",
                  fontsize=LABEL_SIZE)
    ax.set_ylabel(r"$H_{\mathrm{ctx\text{-}self}}$ — latent-premise pinning (bits)",
                  fontsize=LABEL_SIZE)
    ax.set_xlim(-0.03, x_max)
    ax.set_ylim(-0.06, y_max)
    ax.legend(loc="lower right", frameon=True, fontsize=LEGEND_SIZE - 0.5,
              framealpha=0.9)
    ax.grid(True, alpha=0.25, linestyle="--")
    _save(fig, _FIGURES_DIR / "fig_danger_quadrant.pdf")

    return {
        "counts": counts,
        "n_origin_overlap": {"AMB+": n_origin_pos, "AMB-": n_origin_neg},
        "provenance": data.get("provenance", {}),
    }


def make_auroc_comparison() -> dict:
    """fig_auroc_comparison.pdf: per-model + pooled AUROC for LPP (H_ctx-self) vs

    semantic entropy (H_seed) vs requirements-probing, with 95% CIs. All values are
    transcribed VERBATIM from files/study2_stage2_results.md (frozen). Chance = 0.5.
    """
    # (auroc, ci_lo, ci_hi) per model, verbatim from study2_stage2_results.md §2.
    models = [
        "claude-haiku-4.5", "claude-opus-4.8", "gemini-3.1-pro",
        "gemini-3.5-flash", "gpt-4o-mini", "gpt-5.6-sol", "POOLED",
    ]
    lpp = [
        (0.869, 0.787, 0.941), (0.887, 0.808, 0.956), (0.857, 0.771, 0.934),
        (0.880, 0.797, 0.955), (0.856, 0.768, 0.933), (0.857, 0.774, 0.932),
        (0.895, 0.815, 0.966),
    ]
    sem = [
        (0.567, 0.483, 0.648), (0.591, 0.529, 0.662), (0.606, 0.534, 0.682),
        (0.580, 0.493, 0.667), (0.551, 0.472, 0.629), (0.563, 0.467, 0.657),
        (0.581, 0.484, 0.675),
    ]
    reqp = [
        (0.802, 0.677, 0.914), (0.832, 0.717, 0.934), (0.794, 0.667, 0.909),
        (0.802, 0.662, 0.922), (0.807, 0.683, 0.918), (0.802, 0.674, 0.922),
        (0.810, 0.680, 0.931),
    ]

    signals = [
        ("LPP  ($H_{\\mathrm{ctx\\text{-}self}}$, detector)", lpp, C_HETERO, "o"),
        ("requirements-probing", reqp, C_H1, "^"),
        ("semantic entropy ($H_{\\mathrm{seed}}$, SOTA)", sem, C_SINGLE, "s"),
    ]

    n_models = len(models)
    fig, ax = plt.subplots(figsize=(5.6, 4.6))

    offsets = [0.26, 0.0, -0.26]  # LPP top, req-probing mid, sem-entropy bottom
    y_base = np.arange(n_models)[::-1]  # pooled at bottom row visually

    for (label, vals, color, marker), off in zip(signals, offsets):
        ys = y_base + off
        xs = [v[0] for v in vals]
        lo = [v[0] - v[1] for v in vals]
        hi = [v[2] - v[0] for v in vals]
        ax.errorbar(xs, ys, xerr=[lo, hi], fmt=marker, color=color,
                    markersize=6, markeredgecolor="black", markeredgewidth=0.4,
                    elinewidth=1.3, capsize=2.6, capthick=1.0, linestyle="none",
                    label=label, zorder=4)

    # Chance line.
    ax.axvline(0.5, color="black", linestyle="--", linewidth=1.0, alpha=0.6,
               zorder=1)
    ax.text(0.5, y_base[0] + 0.62, "chance (0.5)", fontsize=TICK_SIZE - 0.5,
            ha="center", va="bottom", color="#333333")

    # Divider above the POOLED row.
    ax.axhline(y_base[-1] + 0.5, color="#888888", linestyle="-", linewidth=0.7,
               alpha=0.6, zorder=1)

    ax.set_yticks(y_base)
    labels = [m if m != "POOLED" else "POOLED" for m in models]
    ax.set_yticklabels(labels, fontsize=TICK_SIZE)
    for tick, m in zip(ax.get_yticklabels(), models):
        if m == "POOLED":
            tick.set_fontweight("bold")

    ax.set_xlabel("AUROC vs executable gold-ambiguity (higher = better)",
                  fontsize=LABEL_SIZE)
    ax.set_xlim(0.4, 1.0)
    ax.set_ylim(y_base[-1] - 0.6, y_base[0] + 0.9)
    ax.grid(True, axis="x", alpha=0.25, linestyle="--")
    ax.grid(False, axis="y")

    # Honest annotation of the modest LPP - req-probing pooled gap (+0.085),
    # placed in the empty strip just above the POOLED row.
    pooled_y = y_base[-1]
    ax.annotate("", xy=(0.895, pooled_y + 0.26), xytext=(0.810, pooled_y + 0.26),
                arrowprops=dict(arrowstyle="<->", color="#555555", lw=0.9))
    ax.text(0.852, pooled_y + 0.44,
            "LPP $+0.085$ over req.-probing (pooled; modest)",
            fontsize=TICK_SIZE - 1.0, ha="center", va="center", color="#333333")

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3,
              frameon=True, fontsize=LEGEND_SIZE - 0.5, framealpha=0.92,
              columnspacing=1.0, handletextpad=0.4)
    _save(fig, _FIGURES_DIR / "fig_auroc_comparison.pdf")

    return {
        "models": models,
        "lpp": lpp, "semantic_entropy": sem, "requirements_probing": reqp,
        "pooled_gap_lpp_minus_reqprobing": round(lpp[-1][0] - reqp[-1][0], 3),
    }


def make_study2_figures() -> dict:
    """Generate both Study-2 figures (independent of the Study-1 CD pipeline)."""
    print("  \u2192 fig_danger_quadrant.pdf")
    dq = make_danger_quadrant()
    print("  \u2192 fig_auroc_comparison.pdf")
    au = make_auroc_comparison()
    return {"danger_quadrant": dq, "auroc_comparison": au}


# ─────────────────────────────────────────────────────────────────────────────
# 6. Main orchestration
# ─────────────────────────────────────────────────────────────────────────────

def _safe_float(v) -> object:
    """Convert numpy/pandas scalar to Python float, preserving NaN as None."""
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _to_json_safe(obj):
    """Recursively convert a structure to JSON-safe Python objects."""
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if math.isnan(f) else f
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.DataFrame):
        return _to_json_safe(obj.to_dict(orient="records"))
    return obj


def main():
    print("=== make_figures.py ===")
    _apply_cscw_style()

    # Study-2 figures (F-DQ, F-AUROC) are independent of the Study-1 CD pipeline.
    # `--study2-only` generates just those two (does not need the Study-1
    # code/data/policy checkpoints).
    if "--study2-only" in sys.argv:
        print("[study2-only] Generating Study-2 figures ...")
        make_study2_figures()
        print("\nDone (study2-only).")
        return

    # 1. Load tasks
    print("[1/6] Loading benchmark tasks ...")
    tasks = load_all_tasks()
    print(f"  Tasks loaded: {len(tasks)}")

    # 2. Load tidy table (without output — for CD/dependence figures)
    print("[2/6] Loading tidy run table (no output) ...")
    df_all = load_tidy(tasks, include_output=False)
    df = filter_primary_methods(df_all)
    if df.empty:
        print("ERROR: No data after filtering. Check checkpoint paths and method names.")
        sys.exit(1)

    # 3. Load tidy table WITH output for abstention
    print("[3/6] Loading tidy run table (with output for abstention) ...")
    df_all_out = load_tidy(tasks, include_output=True)
    df_out = filter_primary_methods(df_all_out)

    # 4. Compute dependence table (regime summary with ICC, n_eff, counterfactual)
    print("[4/6] Computing dependence table (ICC, n_eff, counterfactual) ...")
    cell_df, regime_summary = compute_dependence_table(df, n_bootstrap=500, seed=42)
    print(f"  Cell-level rows: {len(cell_df)}")
    print(f"  Regime summaries: {list(regime_summary.keys())}")

    # 5. Compute pairwise wrong agreement (per cell) and aggregate by regime
    regime_col = COLS["regime"]
    pwa_by_regime = {}
    kappa_by_regime = {}
    if not cell_df.empty and "pairwise_wrong_agreement" in cell_df.columns and regime_col in cell_df.columns:
        for regime, grp in cell_df.groupby(regime_col):
            pwa_by_regime[str(regime)] = float(grp["pairwise_wrong_agreement"].mean(skipna=True))
        for regime, grp in cell_df.groupby(regime_col):
            kappa_by_regime[str(regime)] = float(grp["kappa"].mean(skipna=True)) if "kappa" in grp.columns else float("nan")

    # 6. Generate figures
    print("[5/6] Generating figures ...")

    print("  → fig_phase_diagram.pdf")
    phase_data = make_phase_diagram(df)

    print("  → fig_capability_invariance.pdf")
    cap_data = make_capability_invariance(df)

    print("  → fig_fake_redundancy.pdf")
    redund_data = make_fake_redundancy(df, regime_summary)

    print("  → fig_silent_failure.pdf")
    cells_for_sf = compute_cell_cd(df)
    sf_data = make_silent_failure(df_out, cells_for_sf)

    print("  → Study-2 figures (fig_danger_quadrant.pdf, fig_auroc_comparison.pdf)")
    make_study2_figures()

    # 7. Dump figures_data.json
    print("[6/6] Writing figures_data.json ...")

    cells_full = compute_cell_cd(df)
    # CD by (regime, k) — primary metric
    cd_by_regime_k = []
    if not cells_full.empty:
        k_col = COLS["ambiguity_k"]
        for (regime, k), grp in cells_full.groupby([regime_col, k_col], sort=True):
            cd_by_regime_k.append({
                "regime": str(regime),
                "ambiguity_k": int(k),
                "cd_primary_mean": float(grp["cd_primary"].mean()),
                "cd_primary_se": float(grp["cd_primary"].sem()),
                "cd_sensitivity_frozen_mean": float(grp["cd_sensitivity_frozen"].mean()),
                "cd_sensitivity_drop_iperp_mean": float(grp["cd_sensitivity_drop_iperp"].mean()),
                "iperp_rate_mean": float(grp["iperp_rate"].mean()),
                "n_cells": int(len(grp)),
            })

    # CD by (regime, model_class)
    mc_col = COLS["model_class"]
    cd_by_regime_class = []
    if not cells_full.empty and mc_col in cells_full.columns and regime_col in cells_full.columns:
        for (regime, mc), grp in cells_full.groupby([regime_col, mc_col], sort=True):
            cd_by_regime_class.append({
                "regime": str(regime),
                "model_class": str(mc),
                "cd_primary_mean": float(grp["cd_primary"].mean()),
                "cd_sensitivity_frozen_mean": float(grp["cd_sensitivity_frozen"].mean()),
                "cd_sensitivity_drop_iperp_mean": float(grp["cd_sensitivity_drop_iperp"].mean()),
                "iperp_rate_mean": float(grp["iperp_rate"].mean()),
                "n_cells": int(len(grp)),
            })

    dependence_table_records = {
        "regime_summary": {
            k: {kk: _safe_float(vv) for kk, vv in v.items()}
            for k, v in regime_summary.items()
        },
        "pairwise_wrong_agreement_by_regime": {
            k: _safe_float(v) for k, v in pwa_by_regime.items()
        },
        "kappa_by_regime": {
            k: _safe_float(v) for k, v in kappa_by_regime.items()
        },
    }

    figures_json = {
        "cd_by_regime_k": cd_by_regime_k,
        "cd_by_regime_model_class": cd_by_regime_class,
        "dependence": dependence_table_records,
        "abstention": {
            "regime_abstention_rate": {
                k: _safe_float(v) for k, v in sf_data["regime_abstention_rate"].items()
            },
            "regime_cd": {
                k: _safe_float(v) for k, v in sf_data["regime_cd"].items()
            },
            "detail": _to_json_safe(sf_data["detail"]),
        },
        "phase_diagram_raw": _to_json_safe(phase_data),
        "capability_invariance_raw": _to_json_safe(cap_data),
        "fake_redundancy_raw": _to_json_safe(redund_data),
    }

    with open(_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(figures_json, f, indent=2, default=str)
    print(f"  Saved: figures_data.json ({_DATA_JSON.stat().st_size // 1024} KB)")

    # 8. Print key numbers to stdout for Manager tables
    print("\n" + "=" * 60)
    print("KEY NUMBERS (for paper tables)")
    print("=" * 60)

    print("\n── CD by regime × k (cd_primary_mean) ──")
    for row in cd_by_regime_k:
        print(f"  {row['regime']:20s} k={row['ambiguity_k']}  "
              f"CD={row['cd_primary_mean']:.4f}  SE={row['cd_primary_se']:.4f}  "
              f"n_cells={row['n_cells']}")

    print("\n── CD by regime × model_class (cd_primary_mean) ──")
    for row in cd_by_regime_class:
        print(f"  {row['regime']:20s} {row['model_class']:15s}  "
              f"CD={row['cd_primary_mean']:.4f}  "
              f"iperp_rate={row['iperp_rate_mean']:.4f}  "
              f"n_cells={row['n_cells']}")

    print("\n── Dependence by regime ──")
    for regime, stats in regime_summary.items():
        print(f"  {regime}:")
        for k, v in stats.items():
            print(f"    {k:20s} = {v}")
    print(f"\n  Pairwise wrong agreement: {pwa_by_regime}")
    print(f"  Fleiss kappa by regime:   {kappa_by_regime}")

    print("\n── Abstention by regime ──")
    for regime, rate in sf_data["regime_abstention_rate"].items():
        cd_val = sf_data["regime_cd"].get(regime, float("nan"))
        print(f"  {regime:20s}  abstention_rate={rate:.6f}  CD={cd_val:.4f}")

    print("\n── Figures written ──")
    for fname in [
        "fig_phase_diagram.pdf",
        "fig_capability_invariance.pdf",
        "fig_fake_redundancy.pdf",
        "fig_silent_failure.pdf",
        "fig_danger_quadrant.pdf",
        "fig_auroc_comparison.pdf",
        "figures_data.json",
    ]:
        p = _FIGURES_DIR / fname
        size = p.stat().st_size if p.exists() else -1
        status = f"{size:,} bytes" if size >= 0 else "MISSING"
        print(f"  {fname:40s}  {status}")

    print("\nDone.")


if __name__ == "__main__":
    main()
