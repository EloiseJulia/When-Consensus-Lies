# constructed by: Claude (Anthropic) family
"""Phase B EXPLORATORY reporter — cd_primary contrast + abstention (Amendment 12).

# Implementer model family: Claude / Anthropic
# Auditor model family: GPT (Law 6 — cross-family requirement)

Additive, OFFLINE, network-free analysis of the Phase B checkpoint
(``.run_partitions/cp_phaseB.jsonl``).  It changes NO frozen definition — it
IMPORTS and calls the FROZEN machinery unchanged:

- ``analysis.io.load_runs_tidy``   → tidy agent table (reads the frozen labeler's
  labels already persisted in the checkpoint by the driver).
- ``analysis.contrasts.compute_cell_cd`` + ``analysis.cd.cd_primary`` (via the
  frozen ``CD_VARIANTS``) → per-(item×method×seed) A04 CD.  Each Phase B config
  produces ONE final answer per (item, seed), so — exactly like the confirmatory
  ``single`` config — each (item, seed) is a singleton cell and the per-item CD
  is the mean over the 3 seeds.
- ``analysis.abstention.detect_abstention`` → the frozen rule-based
  clarification/abstention detector (no LLM).
- ``registered_run._bootstrap_ci`` → the SAME item-level bootstrap CI helper
  used for R1a/R1b (paired per-item deltas).

Contrast (design §3):
- Baseline = the confirmatory ``heterogeneous-MAD`` CD on the SAME H1_external
  items (loaded from the confirmatory checkpoint).
- P-B1 = cd_primary(cross-vendor-synthesis) − cd_primary(heterogeneous-MAD).
- P-B2 = cd_primary(role-diversified)      − cd_primary(heterogeneous-MAD).
Per-item deltas → ``_bootstrap_ci`` 95% CI.  Abstention/clarification rate is
reported per config.  Nothing here weakens the pre-committed predictions; it
only computes them.

OFFLINE / CI SAFE: pure pandas, no network.  ``compute_report()`` is callable by
offline tests with two small checkpoints.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# ── Repo root + scripts dir on sys.path ──────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from analysis.io import load_runs_tidy  # noqa: E402
from analysis.contrasts import COLS, compute_cell_cd  # noqa: E402
from analysis.abstention import detect_abstention  # noqa: E402

from harness.diversified import (  # noqa: E402
    CONFIG_CROSS_VENDOR_SYNTHESIS,
    CONFIG_ROLE_DIVERSIFIED,
)

#: Default confirmatory checkpoint (baseline source) — read-only here.
DEFAULT_CONFIRMATORY_CHECKPOINT = "registered_run_checkpoint.jsonl"
#: Default Phase B checkpoint (this pass).
DEFAULT_PHASEB_CHECKPOINT = ".run_partitions/cp_phaseB.jsonl"

#: The confirmatory baseline method for the P-B1/P-B2 contrast (design §3).
BASELINE_METHOD = "heterogeneous-MAD"

#: config → pre-committed directional prediction tag (design §3).
_PREDICTION_TAG = {
    CONFIG_CROSS_VENDOR_SYNTHESIS: "P-B1",
    CONFIG_ROLE_DIVERSIFIED: "P-B2",
}

_ITEM = COLS["item"]
_METHOD = COLS["method"]
_SEED = COLS["seed"]
_REGIME = COLS["regime"]


def _per_item_cd(
    cells: pd.DataFrame,
    method: str,
    regime: str,
    cd_col: str = "cd_primary",
) -> Dict[str, float]:
    """Per-item CD for *method* within *regime*: mean of the cell CD over seeds."""
    if cells.empty:
        return {}
    sub = cells[(cells[_METHOD] == method) & (cells[_REGIME] == regime)]
    if sub.empty:
        return {}
    grouped = sub.groupby(_ITEM)[cd_col].mean()
    return {str(k): float(v) for k, v in grouped.items()}


def compute_report(
    phaseb_checkpoint: str,
    confirmatory_checkpoint: str,
    tasks: List[Any],
    *,
    configs: Optional[List[str]] = None,
    baseline_method: str = BASELINE_METHOD,
    regimes: Tuple[str, ...] = ("H1_external", "H2_derivable"),
    cd_col: str = "cd_primary",
    n_boot: int = 2000,
    boot_seed: int = 42,
) -> Dict[str, pd.DataFrame]:
    """Compute the Phase B exploratory CD contrast + abstention tables.

    Args:
        phaseb_checkpoint: Path to cp_phaseB.jsonl (labeled by the driver).
        confirmatory_checkpoint: Path to the confirmatory checkpoint (baseline
            heterogeneous-MAD source). May be missing → empty baseline.
        tasks: Frozen task list (for regime/target/ambiguity metadata).
        configs: Phase B configs to report. Default: both exploratory conditions.
        baseline_method: Confirmatory method used as the contrast baseline.
        regimes: Regimes to report (H1_external primary bed + H2 control).
        cd_col: Which A04 CD variant to contrast (default frozen ``cd_primary``).
        n_boot / boot_seed: Bootstrap params (mirror R1a/R1b: 2000, seed 42).

    Returns:
        Dict with two DataFrames:
          ``"contrasts"`` columns: config, prediction, regime, n_items,
            mean_cd, baseline_method, baseline_mean_cd, mean_delta,
            delta_ci_lo, delta_ci_hi, n_delta_items.
          ``"abstention"`` columns: config, regime, n_agents, n_abstained,
            abstention_rate.
    """
    if configs is None:
        configs = [CONFIG_CROSS_VENDOR_SYNTHESIS, CONFIG_ROLE_DIVERSIFIED]

    from registered_run import _bootstrap_ci  # frozen item-level bootstrap helper

    # ── Load & cell-collapse both checkpoints with the FROZEN machinery ───────
    tidy_pb = load_runs_tidy(phaseb_checkpoint, tasks, include_output=True)
    cells_pb = compute_cell_cd(tidy_pb)

    tidy_base = load_runs_tidy(confirmatory_checkpoint, tasks, include_output=True)
    cells_base = compute_cell_cd(tidy_base)

    # ── Contrast rows ─────────────────────────────────────────────────────────
    contrast_rows: List[Dict[str, Any]] = []
    for config in configs:
        for regime in regimes:
            pb_items = _per_item_cd(cells_pb, config, regime, cd_col)
            base_items = _per_item_cd(cells_base, baseline_method, regime, cd_col)

            mean_cd = (
                sum(pb_items.values()) / len(pb_items) if pb_items else float("nan")
            )
            baseline_mean = (
                sum(base_items.values()) / len(base_items)
                if base_items else float("nan")
            )

            # Paired per-item deltas over items present in BOTH (design §3).
            common = sorted(set(pb_items) & set(base_items))
            deltas = [pb_items[i] - base_items[i] for i in common]
            if deltas:
                mean_delta = sum(deltas) / len(deltas)
                ci_lo, ci_hi = _bootstrap_ci(deltas, n_boot=n_boot, seed=boot_seed)
            else:
                mean_delta = float("nan")
                ci_lo, ci_hi = float("nan"), float("nan")

            contrast_rows.append({
                "config": config,
                "prediction": _PREDICTION_TAG.get(config, ""),
                "regime": regime,
                "n_items": len(pb_items),
                "mean_cd": mean_cd,
                "baseline_method": baseline_method,
                "baseline_mean_cd": baseline_mean,
                "mean_delta": mean_delta,
                "delta_ci_lo": ci_lo,
                "delta_ci_hi": ci_hi,
                "n_delta_items": len(deltas),
            })

    contrasts = pd.DataFrame(contrast_rows)

    # ── Abstention / clarification rate per config × regime ───────────────────
    abst_rows: List[Dict[str, Any]] = []
    if not tidy_pb.empty and "output" in tidy_pb.columns:
        for config in configs:
            for regime in regimes:
                sub = tidy_pb[
                    (tidy_pb[_METHOD] == config) & (tidy_pb[_REGIME] == regime)
                ]
                n = len(sub)
                n_abs = int(
                    sum(bool(detect_abstention(str(o))["abstained"]) for o in sub["output"])
                )
                abst_rows.append({
                    "config": config,
                    "regime": regime,
                    "n_agents": n,
                    "n_abstained": n_abs,
                    "abstention_rate": (n_abs / n) if n > 0 else float("nan"),
                })
    abstention = pd.DataFrame(abst_rows)

    return {"contrasts": contrasts, "abstention": abstention}


def main(argv: Optional[List[str]] = None) -> None:
    """CLI: print the Phase B exploratory contrast + abstention tables (offline)."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Phase B EXPLORATORY reporter — cd_primary(C5/C7) vs heterogeneous-MAD "
            "baseline (P-B1/P-B2) + abstention. Offline, frozen-machinery-only."
        )
    )
    parser.add_argument("--phaseb-checkpoint", default=DEFAULT_PHASEB_CHECKPOINT)
    parser.add_argument("--confirmatory-checkpoint", default=DEFAULT_CONFIRMATORY_CHECKPOINT)
    parser.add_argument("--domains", nargs="+", default=None)
    parser.add_argument("--cd-col", default="cd_primary")
    args = parser.parse_args(argv)

    import registered_run as _rr

    tasks = _rr.load_tasks(args.domains)
    report = compute_report(
        args.phaseb_checkpoint,
        args.confirmatory_checkpoint,
        tasks,
        cd_col=args.cd_col,
    )

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 40)
    print("=" * 72)
    print("PHASE B — EXPLORATORY cd_primary contrast (P-B1 / P-B2)")
    print("=" * 72)
    print(report["contrasts"].to_string(index=False))
    print("\n" + "=" * 72)
    print("PHASE B — abstention / clarification rate per config")
    print("=" * 72)
    print(report["abstention"].to_string(index=False))


if __name__ == "__main__":
    main()
