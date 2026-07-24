# constructed by: Claude (Anthropic) family
"""Amendment 13 manipulation check — the pre-registered VALIDITY GATE.

# Implementer model family: Claude/Anthropic

Runs the FROZEN oracle-hint recovery probe (pre-registration 2026-07-15 §
"Pre-registered manipulation check"): a strong reasoning model is given ONLY the
retained ``k1`` prompt + in-prompt artifacts (NEVER the hidden ``latent_spec``)
and asked to recover the intended interpretation ``I0``. The recovery rate =
fraction of runs whose executable-gold label is ``I0``.

Pre-committed prediction (FROZEN — do NOT tune to force it):
  * recovery is **HIGH** on the NEW amd13 ``H2_derivable`` items (their I0 IS
    uniquely derivable from the retained in-prompt artifact), AND
  * recovery is **LOW** on the matched FROZEN ``H1_external`` anchors (their
    disambiguator is external and was deleted — the model defaults to the foil).

If the constructed "H2" items do NOT separate on this probe (recovery not high,
or not separated from H1), we REPORT the construction failure HONESTLY and DO NOT
claim the crossing (Amendment 13 §4). This gate decides whether H-A13 can be
tested at all. NO item tuning to rescue separation.

Executable gold ONLY (frozen ``harness.label.label_run``; Law 7). Anti-leakage:
the tested prompt is the retained ``k1`` prompt (no gold/target/foil/key_questions).

OFFLINE / CI SAFE: live execution requires ``RUNNER_LIVE=1``; otherwise (non
``--dry-run``) prints "skipped" and exits 0. ``--dry-run`` enumerates the grid.

Usage::

    python scripts/amd13_manipulation_check.py --dry-run
    RUNNER_LIVE=1 python scripts/amd13_manipulation_check.py
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load(mod_name: str, filename: str):
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    sys.modules[mod_name] = mod
    return mod


# ── Pre-committed validity-gate thresholds (FROZEN — do NOT tune) ─────────────
RECOVERY_HIGH_THR = 0.60   # H2 items must recover I0 at >= this rate
RECOVERY_LOW_THR = 0.40    # H1 anchors must recover I0 at <= this rate
SEPARATION_MARGIN = 0.20   # mean(H2 recovery) − mean(H1 recovery) must be >= this

TARGET_LABEL = "I0"

# Recovery probe roster: strong REASONING models only (class "reasoning" in the
# frozen FRONTIER_MODEL_CLASS_MAP). The probe is a capability test — a strong
# solver SHOULD recover a genuinely in-prompt-derivable I0.
REASONER_SLUGS = ("gpt-5.6-sol", "claude-opus-4.8", "gemini-3.1-pro-preview")

DEFAULT_N_SEEDS = 3
RPM_DEFAULT = 30

_CHECKPOINT = str(_REPO_ROOT / ".run_partitions" / "cp_amd_run__amd13_manip.jsonl")
_CACHE_DIR = str(_REPO_ROOT / ".llm_cache_amd_run_amd13_manip")


# ── Task selection: amd13 H2 k1 items + matched frozen H1 k1 anchors ─────────

def select_manip_tasks() -> Tuple[List[Any], List[Any]]:
    """Return (h2_tasks, h1_tasks): the k1 (underspecified) items for the probe.

    H2 = the NEW amd13 sidecar ``H2_derivable`` k1 items (gold registered on load).
    H1 = the matched FROZEN ``H1_external`` k1 anchors (read-only).
    """
    amd_run = _load("amd_run", "amd_run.py")
    all_tasks = amd_run.load_amd_tasks("amd13", include_h1_anchors=True)
    # Only the k1 (ambiguity_level >= 1) variants carry the deleted-disambiguator
    # condition the probe targets; k0 controls are fully specified (recovery trivially 1).
    h2 = [t for t in all_tasks if t.regime == "H2_derivable" and t.ambiguity_level >= 1]
    h1 = [t for t in all_tasks if t.regime == "H1_external" and t.ambiguity_level >= 1]
    return h2, h1


# ── Pure recovery / verdict logic (testable with synthetic labels) ───────────

def recovery_rate(labels: List[str], target: str = TARGET_LABEL) -> float:
    """Fraction of *labels* equal to *target* (the recovery-to-I0 rate)."""
    if not labels:
        return 0.0
    return sum(1 for lb in labels if lb == target) / len(labels)


def per_item_recovery(
    labels_by_item: Dict[str, List[str]], target: str = TARGET_LABEL
) -> Dict[str, float]:
    """Map each item id → its recovery-to-target rate."""
    return {iid: recovery_rate(lbs, target) for iid, lbs in labels_by_item.items()}


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def manipulation_verdict(
    h2_recoveries: Dict[str, float],
    h1_recoveries: Dict[str, float],
    *,
    high_thr: float = RECOVERY_HIGH_THR,
    low_thr: float = RECOVERY_LOW_THR,
    margin: float = SEPARATION_MARGIN,
) -> Dict[str, Any]:
    """Render the pre-committed PASS/FAIL verdict from per-item recovery rates.

    Per-item:
      * an H2 item PASSES iff its recovery >= ``high_thr`` (genuinely derivable);
      * an H1 anchor is a CONTROL — it "behaves" iff its recovery <= ``low_thr``.

    Overall GATE PASSES iff ALL hold:
      (1) mean H2 recovery >= ``high_thr``,
      (2) mean H1 recovery <= ``low_thr``,
      (3) mean(H2) − mean(H1) >= ``margin`` (genuine separation).

    Reported honestly regardless of outcome; the caller never tunes items.
    """
    h2_items = {
        iid: {"recovery": r, "pass": r >= high_thr}
        for iid, r in sorted(h2_recoveries.items())
    }
    h1_items = {
        iid: {"recovery": r, "behaves_as_control": r <= low_thr}
        for iid, r in sorted(h1_recoveries.items())
    }
    mean_h2 = _mean(list(h2_recoveries.values()))
    mean_h1 = _mean(list(h1_recoveries.values()))
    separation = mean_h2 - mean_h1

    cond_high = mean_h2 >= high_thr
    cond_low = mean_h1 <= low_thr
    cond_sep = separation >= margin
    gate_pass = bool(cond_high and cond_low and cond_sep)

    return {
        "gate_pass": gate_pass,
        "mean_h2_recovery": mean_h2,
        "mean_h1_recovery": mean_h1,
        "separation": separation,
        "cond_h2_high": cond_high,
        "cond_h1_low": cond_low,
        "cond_separation": cond_sep,
        "thresholds": {"high": high_thr, "low": low_thr, "margin": margin},
        "h2_items": h2_items,
        "h1_items": h1_items,
        "n_h2": len(h2_recoveries),
        "n_h1": len(h1_recoveries),
    }


def render_verdict(report: Dict[str, Any]) -> str:
    """Human-readable PASS/FAIL summary + per-item table."""
    lines: List[str] = []
    lines.append("=" * 72)
    lines.append("AMENDMENT 13 MANIPULATION CHECK (oracle-hint recovery probe)")
    lines.append("=" * 72)
    thr = report["thresholds"]
    lines.append(
        f"thresholds: H2 recovery >= {thr['high']:.2f}, "
        f"H1 recovery <= {thr['low']:.2f}, separation >= {thr['margin']:.2f}"
    )
    lines.append("")
    lines.append("H2_derivable items (recovery should be HIGH):")
    for iid, d in report["h2_items"].items():
        lines.append(f"  {'PASS' if d['pass'] else 'FAIL'}  {iid:<44} recovery={d['recovery']:.3f}")
    lines.append("")
    lines.append("H1_external anchors (recovery should be LOW — control):")
    for iid, d in report["h1_items"].items():
        ok = d["behaves_as_control"]
        lines.append(f"  {'ok  ' if ok else 'HIGH'}  {iid:<44} recovery={d['recovery']:.3f}")
    lines.append("")
    lines.append(f"mean H2 recovery = {report['mean_h2_recovery']:.3f}  "
                 f"(>= {thr['high']:.2f}? {report['cond_h2_high']})")
    lines.append(f"mean H1 recovery = {report['mean_h1_recovery']:.3f}  "
                 f"(<= {thr['low']:.2f}? {report['cond_h1_low']})")
    lines.append(f"separation       = {report['separation']:.3f}  "
                 f"(>= {thr['margin']:.2f}? {report['cond_separation']})")
    lines.append("")
    lines.append(f"GATE VERDICT: {'PASS' if report['gate_pass'] else 'FAIL'}")
    if not report["gate_pass"]:
        lines.append("HONEST NOTE: the construction did NOT separate as pre-committed. "
                     "Per Amendment 13 §4 we report this honestly and do NOT claim the "
                     "regime×domain crossing; items are NOT tuned to rescue separation.")
    lines.append("=" * 72)
    return "\n".join(lines)


# ── Live run (RUNNER_LIVE-guarded) ───────────────────────────────────────────

def run_recovery_probe(
    cfg: Dict[str, Any],
    *,
    checkpoint_path: str = _CHECKPOINT,
    cache_dir: str = _CACHE_DIR,
    seeds: Optional[List[int]] = None,
    rpm: int = RPM_DEFAULT,
    budget_usd: Optional[float] = None,
    dry_run: bool = False,
    _runner_override=None,
) -> Dict[str, Any]:
    """Execute the recovery probe (single config over reasoners) and build the verdict.

    ``dry_run`` enumerates the grid with NO network. Returns a dict with the
    ``dry_run_report`` (dry) or the full manipulation verdict (live).
    """
    amd_run = _load("amd_run", "amd_run.py")
    rr = _load("registered_run", "registered_run.py")
    amd_run.validate_output_paths(checkpoint_path, cache_dir)

    h2_tasks, h1_tasks = select_manip_tasks()
    tasks = h2_tasks + h1_tasks

    if seeds is None:
        stride = getattr(rr, "_SEED_STRIDE", 1000)
        base = cfg.get("seeds", {}).get("global", 20260713)
        seeds = [base + i * stride for i in range(DEFAULT_N_SEEDS)]

    reasoner_models = [("tested_agents", slug) for slug in REASONER_SLUGS]

    if _runner_override is not None:
        runner, client = _runner_override
    else:
        runner, client = rr.build_runner(
            cfg, tasks,
            checkpoint_path=checkpoint_path,
            models=reasoner_models,
            configs=["single"],
            seeds=seeds,
            budget_usd=budget_usd,
            rpm=rpm,
            offline=dry_run,
            cache_dir=cache_dir,
        )

    if dry_run:
        return {"dry_run": True, **runner.run(dry_run=True)}

    runner.run(dry_run=False)

    from analysis.io import load_runs_tidy, FRONTIER_MODEL_CLASS_MAP
    from analysis.contrasts import COLS
    from harness.runner import endpoint_identity

    ep = endpoint_identity(client.provider, client.base_url)
    tidy = load_runs_tidy(
        checkpoint_path, tasks,
        model_class_map=FRONTIER_MODEL_CLASS_MAP, expected_endpoint=ep,
    )
    return build_verdict_from_tidy(tidy, h2_tasks, h1_tasks)


def build_verdict_from_tidy(tidy, h2_tasks: List[Any], h1_tasks: List[Any]) -> Dict[str, Any]:
    """Aggregate a tidy run table into the per-item recovery verdict."""
    from analysis.contrasts import COLS
    item_col = COLS["item"]
    label_col = COLS["label"]

    h2_ids = {t.id for t in h2_tasks}
    h1_ids = {t.id for t in h1_tasks}

    labels_by_item: Dict[str, List[str]] = {}
    if len(tidy) > 0:
        for iid, grp in tidy.groupby(item_col):
            labels_by_item[iid] = list(grp[label_col])

    h2_rec = per_item_recovery({i: labels_by_item.get(i, []) for i in h2_ids})
    h1_rec = per_item_recovery({i: labels_by_item.get(i, []) for i in h1_ids})
    return manipulation_verdict(h2_rec, h1_rec)


def _live_ok() -> bool:
    return os.environ.get("RUNNER_LIVE", "0") == "1"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Amendment 13 manipulation check (oracle-hint recovery probe)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seeds", nargs="+", type=int, default=None)
    parser.add_argument("--checkpoint", default=_CHECKPOINT)
    parser.add_argument("--cache-dir", default=_CACHE_DIR)
    parser.add_argument("--rpm", type=int, default=RPM_DEFAULT)
    parser.add_argument("--budget-usd", type=float, default=None)
    args = parser.parse_args(argv)

    if not args.dry_run and not _live_ok():
        print(
            "amd13_manipulation_check: skipped (RUNNER_LIVE != 1). "
            "Set RUNNER_LIVE=1 to run the recovery probe live (copilot_proxy)."
        )
        sys.exit(0)

    from common.config import load_config
    cfg = load_config()

    if args.dry_run:
        h2, h1 = select_manip_tasks()
        n_tasks = len(h2) + len(h1)
        seeds = args.seeds or [cfg.get("seeds", {}).get("global", 20260713) + i for i in range(DEFAULT_N_SEEDS)]
        expected = n_tasks * len(REASONER_SLUGS) * len(set(seeds))
        print("=" * 72)
        print("AMD13 MANIPULATION CHECK — DRY RUN")
        print(f"  H2 k1 items: {len(h2)}   H1 k1 anchors: {len(h1)}")
        print(f"  reasoners: {list(REASONER_SLUGS)}  seeds: {seeds}")
        print(f"  EXPECTED JOB COUNT (single × reasoners × seeds): {expected}")
        report = run_recovery_probe(
            cfg, checkpoint_path=args.checkpoint, cache_dir=args.cache_dir,
            seeds=seeds, rpm=args.rpm, dry_run=True,
        )
        print(f"  [DRY-RUN] enumerated grid total={report.get('total')}")
        if report.get("total") != expected:
            print(f"  WARNING: grid total {report.get('total')} != expected {expected}",
                  file=sys.stderr)
        print("  [DRY-RUN] no live calls, no confirmatory writes.")
        print("=" * 72)
        return

    report = run_recovery_probe(
        cfg, checkpoint_path=args.checkpoint, cache_dir=args.cache_dir,
        seeds=args.seeds, rpm=args.rpm, budget_usd=args.budget_usd, dry_run=False,
    )
    print(render_verdict(report))
    if not report["gate_pass"]:
        # A FAILED gate is an HONEST scientific outcome, not an execution error;
        # exit 0 so the Manager records the honest verdict (no tuning).
        return


if __name__ == "__main__":
    main()
