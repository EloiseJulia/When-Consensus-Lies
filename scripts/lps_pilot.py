# constructed by: Claude (Anthropic) family
"""Study 2 LPS PILOT — small $0 feasibility run (NOT confirmatory).

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6)

Verifies that the DANGER-quadrant signal exists on a SMALL, pre-specified item
set before the (separately pre-registered) confirmatory run. Per
``paper/plans/2026-07-23-study2-latent-premise-sensitivity-design.md`` §6, this
pilot is EXPLORATORY: it calibrates the intuition (H1 lands high-H_ctx/low-H_seed;
H2 & k0 stay low-H_ctx) and is reported to the owner WITH the prereg for personal
ratification. It changes NO metric definition.

Scope (pre-specified, 9 items):
  * 4 H1_external k>=1 items (answer depends on an EXTERNAL unstated axis)
  * 3 H2_derivable k>=1 items (disambiguator derivable in-prompt)
  * 2 H1_external k0 controls (no deleted axis)
  × reasoning-tier models for 1-2 families (default: openai gpt-5.6-sol +
    anthropic claude-opus-4.8) × 1 seed.

For each (item, model) it computes H_seed, H_ctx (over model-surfaced dims), the
danger-quadrant flag, and — for reporting ONLY — whether the surfaced argmax
dimension matches the true deleted axis (``key_questions``).

OFFLINE / CI SAFE:
    ``main()`` requires RUNNER_LIVE=1 AND a reachable copilot_proxy; otherwise it
    prints "skipped" and exits 0 (no network, no cost). ``--dry-run`` enumerates
    the (item, model) jobs with NO network. Separate checkpoint
    ``.run_partitions/cp_lps_pilot.jsonl`` + cache ``.llm_cache_lps_pilot`` — it
    NEVER writes a confirmatory/other-pass artifact.

Usage:
    python scripts/lps_pilot.py --dry-run
    RUNNER_LIVE=1 python scripts/lps_pilot.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Repo root + scripts dir on sys.path ──────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import lps_method as lps  # noqa: E402


# ── Isolated artifacts (NEVER a confirmatory/other-pass path) ────────────────
CHECKPOINT = ".run_partitions/cp_lps_pilot.jsonl"
CACHE_DIR = ".llm_cache_lps_pilot"
RPM = 30

#: Pre-specified pilot item IDs (frozen for reproducibility). See task listing.
PILOT_H1_K1 = [
    "code_quarter_001_k1_fiscal_year_start",
    "code_getitems_001_k1_indexing_convention",
    "data_activeusers_001_k1_active_user_threshold",
    "policy_overtime_001_k1_overtime_threshold",
]
PILOT_H2 = [
    "data_typical_001_k1_central_tendency",
    "data_avgprice_001_k1_price_weighting",
    "data_rate_001_k1_rate_interval",
]
PILOT_H1_K0 = [
    "code_quarter_001_k0",
    "policy_overtime_001_k0",
]
PILOT_ITEM_IDS = PILOT_H1_K1 + PILOT_H2 + PILOT_H1_K0

#: Reasoning-tier models across 2 families (openai + anthropic).
PILOT_MODELS = ["gpt-5.6-sol", "claude-opus-4.8"]

#: Single seed (pilot).
PILOT_BASE_SEED = 20260713

#: Guards mirroring scripts/phaseB_diversified.py.
_FORBIDDEN_CHECKPOINT_NAMES = frozenset({
    "registered_run_checkpoint.jsonl",
    "pilot_gate_checkpoint.jsonl",
    "cp_sck10.jsonl",
    "cp_phaseB.jsonl",
})
_FORBIDDEN_CACHE_NAMES = frozenset({
    ".llm_cache_registered_run",
    ".llm_cache_pilot_gate",
    ".llm_cache_sck10",
    ".llm_cache_phaseB",
    ".llm_cache_default_check_h2add",
})


def _validate_output_paths(checkpoint_path: str, cache_dir: str) -> None:
    """Reject paths that could clobber a confirmatory/other-pass artifact."""
    import tempfile

    cp = Path(checkpoint_path).resolve()
    if cp.name in _FORBIDDEN_CHECKPOINT_NAMES:
        raise ValueError(
            f"Refusing checkpoint {checkpoint_path!r}: collides with another run's "
            "artifact. Pilot must write its OWN checkpoint (cp_lps_pilot.jsonl)."
        )
    tmp_root = Path(tempfile.gettempdir()).resolve()
    under_runparts = ".run_partitions" in cp.parts
    try:
        under_tmp = cp.is_relative_to(tmp_root)
    except AttributeError:
        under_tmp = str(cp).startswith(str(tmp_root))
    if not (under_runparts or under_tmp):
        raise ValueError(
            f"Refusing checkpoint {checkpoint_path!r}: not under '.run_partitions' "
            "(or a temp dir for tests)."
        )
    cache = Path(cache_dir).resolve()
    if cache.name in _FORBIDDEN_CACHE_NAMES:
        raise ValueError(
            f"Refusing cache dir {cache_dir!r}: collides with another run's cache. "
            "Pilot must use its OWN cache (.llm_cache_lps_pilot)."
        )


# ── Guards ───────────────────────────────────────────────────────────────────

def _live_ok() -> bool:
    return os.environ.get("RUNNER_LIVE", "0") == "1"


def _proxy_reachable() -> bool:
    import socket
    import urllib.error
    import urllib.request
    try:
        from common.llm import COPILOT_PROXY_BASE_URL
        url = COPILOT_PROXY_BASE_URL.rstrip("/") + "/models"
    except (ImportError, AttributeError):
        url = "http://127.0.0.1:8313/v1/models"
    try:
        urllib.request.urlopen(url, timeout=2)  # noqa: S310
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError, socket.timeout):
        return False


# ── Job enumeration ──────────────────────────────────────────────────────────

def _select_pilot_tasks(tasks: List[Any]) -> List[Any]:
    """Return the pre-specified pilot tasks, preserving PILOT_ITEM_IDS order.

    Raises if any pre-specified ID is missing (fail loud — no silent subset).
    """
    by_id = {t.id: t for t in tasks}
    missing = [tid for tid in PILOT_ITEM_IDS if tid not in by_id]
    if missing:
        raise ValueError(f"Pilot item IDs not found in benchmark: {missing}")
    return [by_id[tid] for tid in PILOT_ITEM_IDS]


def enumerate_jobs(tasks: List[Any], models: List[str]) -> List[Dict[str, Any]]:
    """Enumerate every (item x model) job (no network)."""
    jobs: List[Dict[str, Any]] = []
    for task in tasks:
        for model in models:
            jobs.append({"task_id": task.id, "model": model, "regime": task.regime,
                         "ambiguity_level": task.ambiguity_level})
    return jobs


# ── Core run ─────────────────────────────────────────────────────────────────

def run_fingerprint(
    *,
    models: List[str],
    k: int,
    base_seed: int,
    tau: float,
    tau_s: float,
) -> Dict[str, Any]:
    """Canonical run fingerprint stored in the checkpoint (Issue 3 guard).

    Captures every knob whose change makes previously-recorded H_seed/H_ctx numbers
    incompatible: the method version, k, base seed, tau, tau_s and the model set.
    On resume, records whose fingerprint differs are refused (not silently reused).
    """
    return {
        "method_version": lps.METHOD_VERSION,
        "k": int(k),
        "base_seed": int(base_seed),
        "tau": float(tau),
        "tau_s": float(tau_s),
        "models": sorted(models),
    }


def run(
    tasks: List[Any],
    cfg: Dict[str, Any],
    *,
    models: Optional[List[str]] = None,
    checkpoint_path: str = CHECKPOINT,
    cache_dir: str = CACHE_DIR,
    rpm: int = RPM,
    base_seed: int = PILOT_BASE_SEED,
    k: int = lps.DEFAULT_K,
    tau: float = 0.0,
    tau_s: float = lps.DEFAULT_TAU_S,
    dry_run: bool = False,
    offline: bool = False,
    budget_usd: Optional[float] = None,
    select_pilot: bool = True,
    _client_override: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run (or dry-run) the LPS pilot. Pure/offline-test-friendly.

    On dry_run: returns ``{status, total, jobs}`` with no network.
    On live/offline run: computes LPP results per (item, model), appends each as a
    JSON line to ``checkpoint_path`` (resumable), and returns the collected results.

    ``select_pilot``: if True (default) restrict to the pre-specified 9-item set;
    if False, run every task in ``tasks`` verbatim (used by the expanded
    full-set validation pilot, ``lps_pilot2``).
    """
    if models is None:
        models = list(PILOT_MODELS)

    pilot_tasks = _select_pilot_tasks(tasks) if select_pilot else list(tasks)
    jobs = enumerate_jobs(pilot_tasks, models)

    if dry_run:
        return {"status": "dry_run", "total": len(jobs), "jobs": jobs}

    _validate_output_paths(checkpoint_path, cache_dir)

    cp = Path(checkpoint_path)
    cp.parent.mkdir(parents=True, exist_ok=True)

    # Run FINGERPRINT: any change to these makes prior records incompatible.
    fingerprint = run_fingerprint(
        models=models, k=k, base_seed=base_seed, tau=tau, tau_s=tau_s
    )

    # Resume: skip (task_id, model) cells already recorded — but ONLY reuse records
    # whose stored fingerprint matches this run. A mismatch (different k/seed/tau/
    # tau_s/method-version/models) means the cached number was computed under an
    # incompatible method; refuse to silently reuse it and fail loudly instead.
    done: set = set()
    results: List[Dict[str, Any]] = []
    if cp.exists():
        with cp.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("_header"):
                    continue  # header line; fingerprint validated per-record below
                rec_fp = rec.get("_fingerprint")
                if rec_fp != fingerprint:
                    raise RuntimeError(
                        "LPS checkpoint fingerprint mismatch — refusing to reuse "
                        "incompatible results.\n"
                        f"  checkpoint: {checkpoint_path}\n"
                        f"  record (task={rec.get('task_id')}, model={rec.get('model')}) "
                        f"fingerprint: {rec_fp}\n"
                        f"  current run fingerprint: {fingerprint}\n"
                        "Delete/namespace the checkpoint before re-running with "
                        "different k/seed/tau/tau_s/method-version/models."
                    )
                done.add((rec.get("task_id"), rec.get("model")))
                results.append(rec)
    else:
        # Fresh checkpoint: write a header line recording the run fingerprint.
        with cp.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"_header": True, "_fingerprint": fingerprint}) + "\n")

    if _client_override is not None:
        client = _client_override
    else:
        import copy
        import registered_run as _rr
        client = _rr.build_client(
            copy.deepcopy(cfg),
            offline=offline,
            cache_dir=cache_dir,
            budget_usd=budget_usd,
            rpm=rpm,
        )

    task_by_id = {t.id: t for t in pilot_tasks}
    completed = 0
    skipped = 0
    for job in jobs:
        key = (job["task_id"], job["model"])
        if key in done:
            skipped += 1
            continue
        task = task_by_id[job["task_id"]]
        model = job["model"]
        res = lps.lpp_detect(
            task, client, model, tau=tau, tau_s=tau_s, k=k, base_seed=base_seed
        )
        # Localization sanity check (gold axis — REPORTING ONLY).
        res["deleted_axis"] = list(task.key_questions)
        res["axis_match"] = lps.axis_match(res["flagged_dimension"] or "", task.key_questions)
        res["category"] = _category(task)
        res["_fingerprint"] = fingerprint
        with cp.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(res) + "\n")
        results.append(res)
        done.add(key)
        completed += 1

    return {
        "status": "ok",
        "total": len(jobs),
        "completed": completed,
        "skipped": skipped,
        "checkpoint": str(cp),
        "results": results,
    }


def _category(task: Any) -> str:
    """Reporting bucket: H1_k1 | H2 | H1_k0."""
    if task.regime == "H2_derivable":
        return "H2"
    if task.regime == "H1_external":
        return "H1_k1" if task.ambiguity_level >= 1 else "H1_k0"
    return "other"


# ── Reporting ────────────────────────────────────────────────────────────────

def _mean(xs: List[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate the danger-quadrant key check + localization hit-rate.

    Refinements (2026-07-23):
      * H_ctx here is the DROP-I_perp entropy (valid interpretations only). The
        old all-label H_ctx is also aggregated as ``mean_H_ctx_all`` for contrast.
      * Localization argmax uses the drop-I_perp H_ctx (via each result's
        ``flagged_dimension``).
      * The danger-quadrant target population is the genuinely CONVERGENT H1_k1
        subset: H_seed <= the H2 median H_seed (low-H_seed). Separation is judged
        on THAT subset vs H2 and k0.
    """
    by_cat: Dict[str, Dict[str, List[float]]] = {}
    for r in results:
        cat = r.get("category", "other")
        b = by_cat.setdefault(cat, {"H_seed": [], "H_ctx": [], "H_ctx_all": [],
                                    "match": [], "flag": [], "parse": [], "pins": []})
        b["H_seed"].append(r["H_seed"])
        b["H_ctx"].append(r["H_ctx_max"])
        b["H_ctx_all"].append(r.get("H_ctx_max_all", r["H_ctx_max"]))
        b["flag"].append(1.0 if r.get("is_flagged") else 0.0)
        b["parse"].append(r.get("n_parseable_total", 0))
        b["pins"].append(r.get("n_pins_total", 0))
        if cat == "H1_k1":
            b["match"].append(1.0 if r.get("axis_match") else 0.0)

    summary: Dict[str, Any] = {"by_category": {}}
    for cat, b in by_cat.items():
        n_pins = sum(b["pins"])
        summary["by_category"][cat] = {
            "n": len(b["H_seed"]),
            "n_flagged": int(sum(b["flag"])),
            "flag_rate": _mean(b["flag"]),
            "mean_H_seed": _mean(b["H_seed"]),
            "mean_H_ctx_dropIperp": _mean(b["H_ctx"]),
            "mean_H_ctx_all": _mean(b["H_ctx_all"]),
            "pins_parseable": int(sum(b["parse"])),
            "pins_total": int(n_pins),
            "coverage": (sum(b["parse"]) / n_pins) if n_pins else None,
        }

    summary["localization_hit_rate_H1_k1"] = _mean(
        by_cat.get("H1_k1", {}).get("match", [])
    )

    # ── Genuinely-convergent H1_k1 subset (danger-quadrant target population) ──
    h2_hseed = by_cat.get("H2", {}).get("H_seed", [])
    h2_median = _median(h2_hseed)
    conv = [r for r in results
            if r.get("category") == "H1_k1"
            and h2_median is not None and r["H_seed"] <= h2_median]
    summary["h2_median_H_seed"] = h2_median
    summary["H1_k1_convergent_subset"] = {
        "n": len(conv),
        "task_models": [f"{r['task_id']}|{r['model']}" for r in conv],
        "mean_H_ctx_dropIperp": _mean([r["H_ctx_max"] for r in conv]),
        "localization_hit_rate": _mean(
            [1.0 if r.get("axis_match") else 0.0 for r in conv]
        ),
    }

    h1_conv = summary["H1_k1_convergent_subset"]["mean_H_ctx_dropIperp"]
    h2 = summary["by_category"].get("H2", {}).get("mean_H_ctx_dropIperp")
    k0 = summary["by_category"].get("H1_k0", {}).get("mean_H_ctx_dropIperp")

    def _gt(a, b):
        return a is not None and b is not None and a > b

    # Clean separation = convergent-H1 H_ctx strictly exceeds BOTH H2 and k0.
    summary["danger_quadrant_separates"] = bool(_gt(h1_conv, h2) and _gt(h1_conv, k0))
    # Specificity: how many H2 / k0 items are STILL flagged under the new rule.
    summary["false_flags_H2"] = sum(
        1 for r in results if r.get("category") == "H2" and r.get("is_flagged")
    )
    summary["false_flags_H1_k0"] = sum(
        1 for r in results if r.get("category") == "H1_k0" and r.get("is_flagged")
    )
    return summary


def _median(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _print_table(results: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 120)
    print(f"{'item':<42}{'cat':<7}{'model':<16}{'H_seed':>8}"
          f"{'H_ctx':>8}{'flag':>6}{'match':>7}{'cover':>8}{'filt':>6}")
    print("-" * 120)
    for r in sorted(results, key=lambda x: (x.get("category", ""), x["task_id"], x["model"])):
        cov = f"{r.get('n_parseable_total', 0)}/{r.get('n_pins_total', 0)}"
        print(
            f"{r['task_id'][:41]:<42}{r.get('category',''):<7}{r['model'][:15]:<16}"
            f"{r['H_seed']:>8.3f}{r['H_ctx_max']:>8.3f}"
            f"{('Y' if r['is_flagged'] else '.'): >6}"
            f"{('Y' if r.get('axis_match') else '.'): >7}"
            f"{cov:>8}"
            f"{len(r.get('filtered_dims', [])): >6}"
        )
    print("=" * 120)
    print("  H_ctx = mutual-equivalence entropy (bits); flag = item-level danger flag "
          "(H_ctx>0 AND H_seed low).")
    print("  cover = pinned answers parseable/runnable out of total pins (coverage "
          "fix); match = argmax dim == true deleted axis.")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Study 2 LPS PILOT — small $0 danger-quadrant feasibility run."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Enumerate (item x model) jobs without executing any.")
    parser.add_argument("--checkpoint", default=CHECKPOINT)
    parser.add_argument("--cache-dir", default=CACHE_DIR)
    parser.add_argument("--rpm", type=int, default=RPM)
    parser.add_argument("--models", nargs="+", default=None,
                        help=f"Override model slugs (default: {PILOT_MODELS}).")
    parser.add_argument("--k", type=int, default=lps.DEFAULT_K,
                        help="Seed-resamples for H_seed (default: %(default)s).")
    parser.add_argument("--budget-usd", type=float, default=None)
    args = parser.parse_args(argv)

    from common.config import load_config
    import registered_run as _rr

    cfg = load_config()
    tasks = _rr.load_tasks()  # all 3 domains → select the pilot subset

    if not args.dry_run:
        if not _live_ok():
            print("lps_pilot: skipped (RUNNER_LIVE != 1). Set RUNNER_LIVE=1 to run "
                  "live (copilot_proxy, no token required).")
            sys.exit(0)
        if not _proxy_reachable():
            print("lps_pilot: skipped (copilot_proxy not reachable at "
                  "http://127.0.0.1:8313). Start the proxy before running live.")
            sys.exit(0)

    models = args.models or list(PILOT_MODELS)

    print("=" * 72)
    print("STUDY 2 — LPS PILOT (EXPLORATORY, not confirmatory)")
    print(f"  items={len(PILOT_ITEM_IDS)}  models={models}  k={args.k}")
    print(f"  checkpoint={args.checkpoint}  cache={args.cache_dir}")
    print("=" * 72)

    result = run(
        tasks, cfg,
        models=models,
        checkpoint_path=args.checkpoint,
        cache_dir=args.cache_dir,
        rpm=args.rpm,
        k=args.k,
        dry_run=args.dry_run,
        budget_usd=args.budget_usd,
    )

    if args.dry_run:
        print(f"\n[Pilot] Dry-run: {result['total']} jobs "
              f"({len(PILOT_ITEM_IDS)} items x {len(models)} models).")
        for j in result["jobs"]:
            print(f"    {j['task_id']:<42} {j['model']:<16} regime={j['regime']}")
        return

    results = result["results"]
    _print_table(results)
    summary = summarize(results)
    print("\n[Pilot] Summary:")
    print(json.dumps(summary, indent=2))

    # ── PRIMARY: item-level flag by ground-truth bucket + coverage ────────────
    print("\n[Pilot] PRIMARY item-level flag (H_ctx>0 AND H_seed low) by bucket:")
    for cat in ("H1_k1", "H2", "H1_k0"):
        c = summary["by_category"].get(cat)
        if not c:
            continue
        should = {"H1_k1": "SHOULD flag", "H2": "should NOT (disambiguator in-prompt)",
                  "H1_k0": "should NOT (no deleted axis)"}[cat]
        cov = c["coverage"]
        print(f"    {cat:<6} flagged {c['n_flagged']}/{c['n']}  "
              f"(rate {c['flag_rate']:.2f})  coverage {c['pins_parseable']}/{c['pins_total']}"
              f"{f' ({cov:.0%})' if cov is not None else ''}  — {should}")

    sep = summary["danger_quadrant_separates"]
    print(f"\n[Pilot] KEY CHECK — mutual-equivalence H_ctx separates the CONVERGENT "
          f"(low-H_seed) H1_k1 subset from H2 and k0? {'YES' if sep else 'NO'}")
    print(f"[Pilot] False flags still present: H2={summary['false_flags_H2']} "
          f"H1_k0={summary['false_flags_H1_k0']}")
    print(f"[Pilot] Localization hit-rate (argmax==true axis) on H1_k1: "
          f"{summary['localization_hit_rate_H1_k1']}  | convergent subset: "
          f"{summary['H1_k1_convergent_subset']['localization_hit_rate']}")
    print(f"[Pilot] Result: completed={result['completed']} skipped={result['skipped']} "
          f"checkpoint={result['checkpoint']}")


if __name__ == "__main__":
    main()
