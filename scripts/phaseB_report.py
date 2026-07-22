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
  items, loaded from the FULL confirmatory dataset. The complete confirmatory
  grid (all 54 items, incl. heterogeneous-MAD on every item) lives in the three
  domain partitions (``.run_partitions/cp_{code_spec,data_analysis,policy_qa}
  .jsonl``); ``registered_run_checkpoint.jsonl`` is a strict SUBSET (only 3
  heterogeneous-MAD task_ids), so using it alone left the baseline nearly empty
  (n_delta_items=3). We therefore concatenate the partitions (+ the checkpoint
  if present) at the RAW-RECORD level with order-preserving DEDUP, then run the
  SAME frozen ``load_runs_tidy`` → ``compute_cell_cd`` → ``_per_item_cd`` pipeline
  (no frozen file edited; the concat/dedup lives here only).
- P-B1 = cd_primary(cross-vendor-synthesis) − cd_primary(heterogeneous-MAD).
- P-B2 = cd_primary(role-diversified)      − cd_primary(heterogeneous-MAD).
Per-item deltas → ``_bootstrap_ci`` 95% CI.  Abstention/clarification rate is
reported per config.  Nothing here weakens the pre-committed predictions; it
only computes them.

OFFLINE / CI SAFE: pure pandas, no network.  ``compute_report()`` is callable by
offline tests with two small checkpoints.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

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

#: Default confirmatory checkpoint (LEGACY single-file source — kept for
#: backward compatibility). NOTE: this file is a strict SUBSET of the domain
#: partitions (heterogeneous-MAD on only 3 task_ids), so it must NOT be used as
#: the sole baseline — use DEFAULT_CONFIRMATORY_SOURCES instead.
DEFAULT_CONFIRMATORY_CHECKPOINT = "registered_run_checkpoint.jsonl"
#: Default FULL confirmatory baseline sources — the three domain partitions hold
#: the complete grid (all 54 items, heterogeneous-MAD on every item); the legacy
#: checkpoint is appended (and deduped) only if present. This is the default the
#: CLI uses so a plain ``python scripts/phaseB_report.py`` gets the full baseline.
DEFAULT_CONFIRMATORY_SOURCES: List[str] = [
    ".run_partitions/cp_code_spec.jsonl",
    ".run_partitions/cp_data_analysis.jsonl",
    ".run_partitions/cp_policy_qa.jsonl",
    DEFAULT_CONFIRMATORY_CHECKPOINT,
]
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


def _resolve_data_path(path: Union[str, Path]) -> str:
    """Resolve a (possibly relative) data path against cwd/ancestors.

    A git worktree does not carry the gitignored checkpoint data, so the real
    files often live in the main checkout — an ancestor of the worktree cwd. If
    ``path`` exists as given (absolute or relative to cwd) it is returned
    unchanged; otherwise the same relative path is searched under the cwd's
    ancestors and the repo-root's ancestors, returning the first hit. If nothing
    is found the original string is returned (the frozen loader then yields an
    empty tidy frame). Pure lookup — never writes.
    """
    p = Path(path)
    if p.exists():
        return str(p)
    if p.is_absolute():
        return str(p)
    bases = [Path.cwd()] + list(Path.cwd().resolve().parents) \
        + [_REPO_ROOT] + list(_REPO_ROOT.parents)
    seen: set = set()
    for b in bases:
        if b in seen:
            continue
        seen.add(b)
        cand = b / path
        if cand.exists():
            return str(cand)
    return str(path)


def _load_confirmatory_tidy(
    sources: Union[str, Path, Sequence[Union[str, Path]]],
    tasks: List[Any],
) -> pd.DataFrame:
    """Load the FULL confirmatory baseline from one or more checkpoint sources.

    The three domain partitions hold the complete confirmatory grid (all 54
    items, heterogeneous-MAD on every item); ``registered_run_checkpoint.jsonl``
    is a strict SUBSET. To assemble the complete baseline WITHOUT double-counting
    the overlapping subset (which would corrupt CD), the raw JSONL lines from all
    existing sources are unioned with ORDER-PRESERVING DEDUP (identical lines
    collapse; genuinely distinct agents — which differ in model_id/output/label —
    are kept). The deduped union is materialised to a transient temp file inside
    the worktree and handed to the FROZEN ``analysis.io.load_runs_tidy`` unchanged
    (so the multi-endpoint guard and every derivation apply exactly as normal),
    then the temp file is removed. A single existing source reduces to the
    original single-file load (dedup is a no-op on a duplicate-free file), so this
    is backward-compatible with callers that pass one path.

    Args:
        sources: One path, or a sequence of paths, to confirmatory checkpoints.
        tasks: Frozen task list (regime/target/ambiguity metadata).

    Returns:
        Tidy agent-level DataFrame (``include_output=True``), or an empty tidy
        frame (correct columns) if no source exists.
    """
    if isinstance(sources, (str, Path)):
        sources = [sources]
    resolved = [_resolve_data_path(s) for s in sources]
    existing = [s for s in resolved if Path(s).exists()]
    if not existing:
        # No data present → return an empty tidy frame with the correct columns.
        return load_runs_tidy(resolved[0] if resolved else "not_a_file",
                              tasks, include_output=True)

    seen_lines: set = set()
    merged: List[str] = []
    for path in existing:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if not s or s in seen_lines:
                    continue
                seen_lines.add(s)
                merged.append(s)

    fd, tmp = tempfile.mkstemp(suffix=".jsonl", prefix="_phaseb_confbase_",
                               dir=str(_REPO_ROOT))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            if merged:
                fh.write("\n".join(merged) + "\n")
        return load_runs_tidy(tmp, tasks, include_output=True)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def compute_report(
    phaseb_checkpoint: str,
    confirmatory_checkpoint: Union[str, Path, Sequence[Union[str, Path]]],
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
        confirmatory_checkpoint: One path OR a sequence of paths to confirmatory
            checkpoints used as the baseline heterogeneous-MAD source. When a
            sequence, the raw records are unioned + deduped (see
            :func:`_load_confirmatory_tidy`). May be missing → empty baseline.
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
    tidy_pb = load_runs_tidy(_resolve_data_path(phaseb_checkpoint), tasks,
                             include_output=True)
    cells_pb = compute_cell_cd(tidy_pb)

    tidy_base = _load_confirmatory_tidy(confirmatory_checkpoint, tasks)
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
    parser.add_argument(
        "--confirmatory-checkpoint", nargs="+",
        default=list(DEFAULT_CONFIRMATORY_SOURCES),
        help="One or more confirmatory checkpoint sources (baseline "
             "heterogeneous-MAD). Default: the three domain partitions + the "
             "legacy checkpoint (raw records unioned + deduped).",
    )
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
