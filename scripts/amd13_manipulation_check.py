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
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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

# The verdict artifact the A13 report READS to enforce the validity gate (MAJOR 4).
# Non-protected filename; lives in files/ next to the reports.
MANIP_VERDICT_PATH = str(_REPO_ROOT / "files" / "amd13_manipulation_verdict.json")

# ── The FROZEN oracle-hint recovery probe (Amendment 13 §4 / construction §2) ─
# For each retained k1 item we SUPPLY the deleted-axis ORACLE HINT — the item's
# ``key_questions`` (which name the implicit axis + its candidate resolutions, but
# NEVER which one is the target I0) — as a controlled clarification, and instruct
# the solver to RESOLVE it using ONLY the retained in-prompt information/artifacts
# (no external default). Recovery = fraction of answers the EXECUTABLE labeler puts
# at I0. This is the ONLY permitted gold-bearing input (a controlled recovery
# probe); the target/foil/gold_check/latent_spec are NEVER revealed. Pre-committed:
# recovery HIGH on genuinely in-prompt-derivable H2 items, LOW on H1 anchors whose
# disambiguator is external and was deleted.
_RECOVERY_HINT_TEMPLATE = (
    "\n\n---\n"
    "Clarification (recovery probe). One aspect of the required behaviour was left "
    "implicit above. To answer correctly you MUST resolve the following question "
    "using ONLY the information, worked examples, type signatures, and artifacts "
    "already present in the prompt above — do NOT fall back on any external or "
    "conventional default, and do NOT guess:\n"
    "{questions}\n"
    "Resolve it strictly from the retained information, then give your final answer."
)


def build_probe_task(task: Any) -> Any:
    """Return a copy of *task* whose prompt appends the oracle-hint recovery block.

    The copy keeps the SAME ``id`` and ``interpretations`` (so executable-gold
    labeling and the tidy join are unchanged); only the tested PROMPT is augmented
    with the deleted-axis question (the oracle hint). Items with no
    ``key_questions`` (k0 controls) are returned unchanged and are not probed.
    """
    if not getattr(task, "key_questions", None):
        return task
    questions = "\n".join(f"- {q}" for q in task.key_questions)
    hint = _RECOVERY_HINT_TEMPLATE.format(questions=questions)
    return replace(task, prompt=task.prompt + hint)


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
    completeness: Optional[Dict[str, Any]] = None,
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
    mean_h2 = _mean(list(h2_recoveries.values())) if h2_recoveries else float("nan")
    mean_h1 = _mean(list(h1_recoveries.values())) if h1_recoveries else float("nan")
    separation = mean_h2 - mean_h1

    cond_high = bool(h2_recoveries and mean_h2 >= high_thr)
    cond_low = bool(h1_recoveries and mean_h1 <= low_thr)
    cond_sep = bool(h2_recoveries and h1_recoveries and separation >= margin)
    grid_complete = bool((completeness or {}).get("complete", False))
    gate_pass = bool(grid_complete and cond_high and cond_low and cond_sep)
    status = "PASS" if gate_pass else ("FAIL" if grid_complete else "INCOMPLETE")

    return {
        "gate_pass": gate_pass,
        "verdict_status": status,
        "grid_complete": grid_complete,
        "completeness": completeness or {"complete": False, "reason": "no completeness validation supplied"},
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
    if not report.get("grid_complete", True):
        comp = report.get("completeness") or {}
        lines.append(
            "GRID STATUS: INCOMPLETE "
            f"({comp.get('n_missing_observations', 'unknown')} missing observations)"
        )
    lines.append(f"GATE VERDICT: {report.get('verdict_status', 'PASS' if report['gate_pass'] else 'FAIL')}")
    if not report["gate_pass"]:
        lines.append("HONEST NOTE: the construction did NOT separate as pre-committed. "
                     "Per Amendment 13 §4 we report this honestly and do NOT claim the "
                     "regime×domain crossing; items are NOT tuned to rescue separation. "
                     "Incomplete grids are INVALID and never count as a passing gate.")
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
    # FROZEN oracle-hint recovery probe: run the AUGMENTED probe prompts (retained
    # prompt + surfaced deleted-axis question), NOT the ordinary task prompt.
    probe_h2 = [build_probe_task(t) for t in h2_tasks]
    probe_h1 = [build_probe_task(t) for t in h1_tasks]
    tasks = probe_h2 + probe_h1

    if seeds is None:
        stride = getattr(rr, "_SEED_STRIDE", 1000)
        base = cfg.get("seeds", {}).get("global", 20260713)
        seeds = [base + i * stride for i in range(DEFAULT_N_SEEDS)]

    reasoner_models = [("tested_agents", slug) for slug in REASONER_SLUGS]

    if not dry_run:
        amd_run.write_run_manifest(
            checkpoint_path,
            which="amd13",
            seeds=seeds,
            configs=["single"],
            tasks=tasks,
            include_h1_anchors=True,
        )

    if _runner_override is not None:
        runner, client = _runner_override
    else:
        runner, client = rr.build_runner(
            cfg, tasks,
            checkpoint_path=checkpoint_path,
            models=reasoner_models,
            configs=["single"],   # recovery probe is single-agent (capability test)
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
    from harness.runner import endpoint_identity

    ep = endpoint_identity(client.provider, client.base_url)
    tidy = load_runs_tidy(
        checkpoint_path, tasks,
        model_class_map=FRONTIER_MODEL_CLASS_MAP, expected_endpoint=ep,
    )
    done_complete = _checkpoint_done_completeness(
        checkpoint_path, h2_tasks, h1_tasks, expected_seeds=seeds,
    )
    verdict = build_verdict_from_tidy(
        tidy, h2_tasks, h1_tasks,
        expected_seeds=seeds,
        extra_completeness=done_complete,
    )
    write_verdict(verdict)
    return verdict


def write_verdict(verdict: Dict[str, Any], path: str = MANIP_VERDICT_PATH) -> str:
    """Persist the manipulation verdict as JSON (read by the A13 report gate)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(verdict, indent=2, sort_keys=True), encoding="utf-8")
    return str(p)


def _observed_labels_by_item(
    tidy,
    *,
    expected_items: Optional[Set[str]] = None,
    expected_reasoners: Tuple[str, ...] = REASONER_SLUGS,
    expected_seeds: Optional[List[int]] = None,
) -> Dict[str, List[str]]:
    from analysis.contrasts import COLS
    item_col = COLS["item"]
    label_col = COLS["label"]
    labels_by_item: Dict[str, List[str]] = {}
    if expected_items is None or expected_seeds is None:
        return labels_by_item
    allowed_reasoners = set(expected_reasoners)
    allowed_seeds = {int(s) for s in expected_seeds}
    seen: Set[Tuple[str, str, int]] = set()
    if len(tidy) > 0:
        for _, row in tidy.iterrows():
            iid = row.get(item_col)
            model = row.get("model")
            seed = int(row.get(COLS["seed"]))
            key = (iid, model, seed)
            if key in seen:
                continue
            if iid in expected_items and model in allowed_reasoners and seed in allowed_seeds:
                seen.add(key)
                labels_by_item.setdefault(iid, []).append(row.get(label_col))
    return labels_by_item


def _manip_completeness(
    tidy,
    h2_tasks: List[Any],
    h1_tasks: List[Any],
    *,
    expected_reasoners: Tuple[str, ...] = REASONER_SLUGS,
    expected_seeds: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Validate the preregistered manipulation-check grid before any PASS.

    Expected grid = every H2 k1 item + every matched H1 k1 anchor, crossed with
    the required reasoner roster and ≥3 distinct manifest-requested seeds. Missing,
    unexpected, or duplicate observations are INCOMPLETE; expected seeds are never
    inferred from observed rows.
    """
    from analysis.contrasts import COLS

    h2_ids = {t.id for t in h2_tasks}
    h1_ids = {t.id for t in h1_tasks}
    expected_items = h2_ids | h1_ids

    if expected_seeds is None:
        return {
            "complete": False,
            "reason": "authoritative requested seeds missing; refusing to infer seeds from observed rows",
            "seed_count_ok": False,
            "expected_n_seeds": DEFAULT_N_SEEDS,
            "observed_or_requested_seeds": [],
            "expected_reasoners": list(expected_reasoners),
            "expected_h2_items": sorted(h2_ids),
            "expected_h1_items": sorted(h1_ids),
            "n_expected_observations": 0,
            "n_observed_observations": 0,
            "n_missing_observations": 0,
            "n_unexpected_observations": 0,
            "n_duplicate_observations": 0,
            "missing_observations": [],
            "unexpected_observations": [],
            "duplicate_observations": [],
        }
    expected_seed_set: Set[int] = {int(s) for s in expected_seeds}
    seed_ok = len(expected_seed_set) >= DEFAULT_N_SEEDS

    observed_counts: Dict[Tuple[str, str, int], int] = {}
    unexpected_counts: Dict[Tuple[str, str, int], int] = {}
    expected = {
        (iid, model, seed)
        for iid in expected_items
        for model in expected_reasoners
        for seed in expected_seed_set
    }
    if len(tidy) > 0:
        for _, row in tidy.iterrows():
            iid = row.get(COLS["item"])
            model = row.get("model")
            seed = int(row.get(COLS["seed"]))
            key = (iid, model, seed)
            if key in expected:
                observed_counts[key] = observed_counts.get(key, 0) + 1
            else:
                unexpected_counts[key] = unexpected_counts.get(key, 0) + 1

    observed = {k for k, n in observed_counts.items() if n == 1}
    duplicates = {k: n for k, n in observed_counts.items() if n > 1}

    missing = [
        {"item": iid, "model": model, "seed": seed}
        for iid in sorted(expected_items)
        for model in expected_reasoners
        for seed in sorted(expected_seed_set)
        if (iid, model, seed) not in observed_counts
    ]
    return {
        "complete": bool(seed_ok and not missing and not unexpected_counts and not duplicates),
        "seed_count_ok": seed_ok,
        "expected_n_seeds": DEFAULT_N_SEEDS,
        "observed_or_requested_seeds": sorted(expected_seed_set),
        "expected_reasoners": list(expected_reasoners),
        "expected_h2_items": sorted(h2_ids),
        "expected_h1_items": sorted(h1_ids),
        "n_expected_observations": len(expected_items) * len(expected_reasoners) * len(expected_seed_set),
        "n_observed_observations": len(observed),
        "n_missing_observations": len(missing),
        "n_unexpected_observations": len(unexpected_counts),
        "n_duplicate_observations": len(duplicates),
        "missing_observations": missing[:50],
        "unexpected_observations": [
            {"item": iid, "model": model, "seed": seed, "rows": n}
            for (iid, model, seed), n in list(sorted(unexpected_counts.items()))[:50]
        ],
        "duplicate_observations": [
            {"item": iid, "model": model, "seed": seed, "rows": n}
            for (iid, model, seed), n in list(sorted(duplicates.items()))[:50]
        ],
    }


def _checkpoint_done_completeness(
    checkpoint_path: str,
    h2_tasks: List[Any],
    h1_tasks: List[Any],
    *,
    expected_reasoners: Tuple[str, ...] = REASONER_SLUGS,
    expected_seeds: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Validate job_done completion markers for the manipulation-check grid."""
    if expected_seeds is None:
        expected_seeds = []
    expected_items = {t.id for t in h2_tasks} | {t.id for t in h1_tasks}
    expected = {
        (iid, "single", "tested_agents", model, int(seed))
        for iid in expected_items
        for model in expected_reasoners
        for seed in expected_seeds
    }
    done: Set[Tuple[str, str, str, str, int]] = set()
    p = Path(checkpoint_path)
    if p.exists():
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") == "job_done":
                    done.add((
                        rec.get("task_id", ""),
                        rec.get("config", ""),
                        rec.get("model_role", ""),
                        rec.get("model_id", ""),
                        int(rec.get("seed", 0)),
                    ))
    missing = [
        {"item": iid, "config": cfg, "role": role, "model": model, "seed": seed}
        for iid, cfg, role, model, seed in sorted(expected - done)
    ]
    return {
        "complete": len(missing) == 0 and len(set(expected_seeds)) >= DEFAULT_N_SEEDS,
        "n_expected_done_jobs": len(expected),
        "n_done_jobs": len(expected & done),
        "n_missing_done_jobs": len(missing),
        "missing_done_jobs": missing[:50],
    }


def _combine_completeness(*parts: Dict[str, Any]) -> Dict[str, Any]:
    return {"complete": all(p.get("complete") for p in parts), "checks": list(parts)}


def build_verdict_from_tidy(
    tidy,
    h2_tasks: List[Any],
    h1_tasks: List[Any],
    *,
    expected_seeds: Optional[List[int]] = None,
    expected_reasoners: Tuple[str, ...] = REASONER_SLUGS,
    extra_completeness: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Aggregate a tidy run table into the per-item recovery verdict."""
    h2_ids = {t.id for t in h2_tasks}
    h1_ids = {t.id for t in h1_tasks}

    tidy_completeness = _manip_completeness(
        tidy, h2_tasks, h1_tasks,
        expected_reasoners=expected_reasoners,
        expected_seeds=expected_seeds,
    )
    completeness = (
        _combine_completeness(tidy_completeness, extra_completeness)
        if extra_completeness is not None else tidy_completeness
    )
    labels_by_item = _observed_labels_by_item(
        tidy,
        expected_items=h2_ids | h1_ids,
        expected_reasoners=expected_reasoners,
        expected_seeds=expected_seeds,
    )

    h2_rec = per_item_recovery({i: labels_by_item[i] for i in h2_ids if i in labels_by_item})
    h1_rec = per_item_recovery({i: labels_by_item[i] for i in h1_ids if i in labels_by_item})
    verdict = manipulation_verdict(h2_rec, h1_rec, completeness=completeness)
    verdict["_authoritative_recomputed"] = True
    return verdict


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
