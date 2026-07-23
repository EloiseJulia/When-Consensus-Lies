# constructed by: Claude (Anthropic) family
"""Study 2 LPS CONFIRMATORY detection driver (Phase 2a) — multi-model × multi-seed.

# Implementer model family: Claude / Anthropic
# Auditor model family: MUST be non-Anthropic (Law 6 — cross-family requirement)

Runs the black-box Latent-Premise-Probing detector (``lps_method.lpp_detect`` —
H_seed + assumption-surfacing + H_ctx-self) PLUS the pre-registered baseline panel
(``lps_baselines``) over ALL 54 frozen benchmark items × the confirmatory model
roster × ≥3 seeds, exactly as frozen in
``paper/preregistration/2026-07-23-study2-prereg-FROZEN.md`` (§2–§3): AUROC
primary; item-flag operating point τ = 0.0, τ_s = 0.5 bits; k = 5.

  * Confirmatory roster (§3): reasoning tier {openai gpt-5.6-sol, anthropic
    claude-opus-4.8, google gemini-3.1-pro} + weak tier {gpt-4o-mini,
    claude-haiku-4.5, gemini-3.5-flash}. Per-model + pooled detection.
  * Seeds: ≥3 collision-free (spaced far wider than any within-detect seed
    offset so no two (item,model,seed) cells ever share a proxy seed).

ISOLATED, RESUMABLE, GUARDED (mirrors ``lps_pilot`` / ``phaseB_diversified``):
  * OWN checkpoint ``.run_partitions/cp_lps_confirm.jsonl`` + cache
    ``.llm_cache_lps_confirm`` — path-guarded so it can NEVER clobber another
    pass's artifact.
  * FULL run-fingerprint (method version + k + tau/tau_s + the MODEL LIST + the
    SEED LIST) stamped on every record; a resume refuses to reuse any record whose
    fingerprint differs (a changed roster/seed/method ⇒ incompatible numbers).
  * ``main()`` requires ``RUNNER_LIVE=1`` AND a reachable copilot_proxy, else it
    prints "skipped" and exits 0 (offline/CI safe). ``--dry-run`` enumerates the
    job count (54 × 6 × ≥3) with NO network.

BASELINES captured per record (``lps_baselines``): the token-confidence baseline
replays H_seed's exact generic calls (cache HIT after ``lpp_detect`` — $0), while
self-consistency and requirements-probing are derived offline from the record's
own ``seed_labels`` / ``surfaced_dims``.

ANTI-CIRCULARITY / ANTI-LEAKAGE: gold-ambiguity (``lps_gold``) is computed for
EVALUATION ONLY (never in a prompt); every detector/baseline prompt is generic.

This driver BUILDS + DRY-RUNS the apparatus; the full live grid is a SEPARATE
gated step. Usage:
    python scripts/lps_confirm.py --dry-run                 # enumerate 972 jobs
    RUNNER_LIVE=1 python scripts/lps_confirm.py --max-items 2 \\
        --models gpt-4o-mini --seeds 20260713               # tiny smoke ($0)
    RUNNER_LIVE=1 python scripts/lps_confirm.py             # FULL grid (gated)

PARALLEL (one runner per model — owner's confirmatory workflow): launch 6
concurrent processes, each with ``--shard-by-model`` and a single ``--models``
slug; each writes an INDEPENDENT, independently-resumable shard
(``cp_lps_confirm__<slug>.jsonl`` + ``.llm_cache_lps_confirm__<slug>``), so a
crash/hang in one model's runner cannot affect the others:
    RUNNER_LIVE=1 python scripts/lps_confirm.py --shard-by-model --models gpt-5.6-sol
    ...                                        --shard-by-model --models gemini-3.1-pro
    # then merge + report across shards:
    python scripts/lps_confirm_merge.py
    python scripts/lps_confirm_report.py --shards '.run_partitions/cp_lps_confirm__*.jsonl' \\
        --out files/study2_confirm_results.md
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import re

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
for _p in (str(_REPO_ROOT), str(_SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lps_method as lps  # noqa: E402
import lps_baselines as baselines  # noqa: E402
import lps_pilot as pilot1  # noqa: E402  (reuse live/proxy guards read-only)


# ── Isolated artifacts (NEVER a pilot/confirmatory-other/other-pass path) ─────
CHECKPOINT = ".run_partitions/cp_lps_confirm.jsonl"
CACHE_DIR = ".llm_cache_lps_confirm"

#: Confirmatory roster (FROZEN prereg §3): reasoning tier + weak tier, 3 families.
CONFIRM_MODELS = [
    "gpt-5.6-sol",       # openai   — reasoning
    "claude-opus-4.8",   # anthropic — reasoning
    "gemini-3.1-pro",    # google   — reasoning
    "gpt-4o-mini",       # openai   — weak
    "claude-haiku-4.5",  # anthropic — weak
    "gemini-3.5-flash",  # google   — weak
]

#: ≥3 collision-free seed bases. Spaced 10_000 apart — far wider than any seed
#: offset lpp_detect uses internally (H_seed: base+j for j<k≈10; H_ctx pinning:
#: base + dim*100 + val, ≤ ~500) so no two (item,model,seed) cells collide.
CONFIRM_SEED_BASES = [20260713, 20270713, 20280713]

RPM = 30

#: Base names for per-model shards (PARALLEL runners). Concurrent runners — one per
#: model — write DISTINCT namespaced files so they never touch the same checkpoint or
#: cache: ``.run_partitions/cp_lps_confirm__<slug>.jsonl`` +
#: ``.llm_cache_lps_confirm__<slug>``. A crash/hang in one shard cannot corrupt another.
CHECKPOINT_BASE = ".run_partitions/cp_lps_confirm"
CACHE_BASE = ".llm_cache_lps_confirm"
#: Glob for the merge tool to discover every per-model shard checkpoint.
SHARD_CHECKPOINT_GLOB = ".run_partitions/cp_lps_confirm__*.jsonl"

#: FROZEN operating point (prereg §2). Item flag = (H_ctx-self > τ) ∧ (H_seed ≤ τ_s).
TAU = 0.0
TAU_S = 0.5

#: Forbidden output names — refuse to write over ANY other pass's artifact.
_FORBIDDEN_CHECKPOINT_NAMES = frozenset({
    "registered_run_checkpoint.jsonl",
    "pilot_gate_checkpoint.jsonl",
    "cp_sck10.jsonl",
    "cp_phaseB.jsonl",
    "cp_lps_pilot.jsonl",
    "cp_lps_pilot2.jsonl",
})
_FORBIDDEN_CACHE_NAMES = frozenset({
    ".llm_cache_registered_run",
    ".llm_cache_pilot_gate",
    ".llm_cache_sck10",
    ".llm_cache_phaseB",
    ".llm_cache_default_check_h2add",
    ".llm_cache_lps_pilot",
    ".llm_cache_lps_pilot2",
})


def _validate_output_paths(checkpoint_path: str, cache_dir: str) -> None:
    """Reject paths that could clobber a pilot/other-pass artifact."""
    cp = Path(checkpoint_path).resolve()
    if cp.name in _FORBIDDEN_CHECKPOINT_NAMES:
        raise ValueError(
            f"Refusing checkpoint {checkpoint_path!r}: collides with another run's "
            "artifact. Confirm must write its OWN checkpoint (cp_lps_confirm.jsonl)."
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
            "Confirm must use its OWN cache (.llm_cache_lps_confirm)."
        )


# ── Per-model sharding (PARALLEL-safe namespaced paths) ──────────────────────

def sanitize_slug(model: str) -> str:
    """Filesystem-safe token for a model slug (any non ``[A-Za-z0-9_-]`` → ``_``).

    e.g. ``"gpt-5.6-sol"`` → ``"gpt-5_6-sol"``; ``"anthropic/claude-opus-4.8"`` →
    ``"anthropic_claude-opus-4_8"``. Distinct slugs map to distinct tokens so two
    concurrent model-runners never collide on a checkpoint or cache path.
    """
    return re.sub(r"[^A-Za-z0-9_-]", "_", model.strip())


def shard_checkpoint(model: str) -> str:
    """Per-model checkpoint path: ``.run_partitions/cp_lps_confirm__<slug>.jsonl``."""
    return f"{CHECKPOINT_BASE}__{sanitize_slug(model)}.jsonl"


def shard_cache(model: str) -> str:
    """Per-model cache dir: ``.llm_cache_lps_confirm__<slug>``."""
    return f"{CACHE_BASE}__{sanitize_slug(model)}"



# ── Job enumeration ──────────────────────────────────────────────────────────

def enumerate_jobs(
    tasks: List[Any], models: List[str], seed_bases: List[int]
) -> List[Dict[str, Any]]:
    """Every (item × model × seed) cell (no network). Order: item→model→seed."""
    jobs: List[Dict[str, Any]] = []
    for task in tasks:
        for model in models:
            for seed_base in seed_bases:
                jobs.append({
                    "task_id": task.id,
                    "model": model,
                    "seed_base": int(seed_base),
                    "regime": task.regime,
                    "ambiguity_level": task.ambiguity_level,
                })
    return jobs


def run_fingerprint(
    *,
    models: List[str],
    seed_bases: List[int],
    k: int,
    tau: float,
    tau_s: float,
) -> Dict[str, Any]:
    """Canonical run fingerprint (Issue-3 resume guard) incl. models + seeds.

    Captures every knob whose change makes previously-recorded H_seed/H_ctx numbers
    incompatible: method version, k, tau, tau_s, the full MODEL list AND the full
    SEED list. On resume, records whose fingerprint differs are refused.
    """
    return {
        "method_version": lps.METHOD_VERSION,
        "k": int(k),
        "tau": float(tau),
        "tau_s": float(tau_s),
        "models": sorted(models),
        "seed_bases": sorted(int(s) for s in seed_bases),
    }


# ── Core run ─────────────────────────────────────────────────────────────────

def run(
    tasks: List[Any],
    cfg: Dict[str, Any],
    *,
    models: Optional[List[str]] = None,
    seed_bases: Optional[List[int]] = None,
    checkpoint_path: str = CHECKPOINT,
    cache_dir: str = CACHE_DIR,
    rpm: int = RPM,
    k: int = lps.DEFAULT_K,
    tau: float = TAU,
    tau_s: float = TAU_S,
    dry_run: bool = False,
    offline: bool = False,
    budget_usd: Optional[float] = None,
    _client_override: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run (or dry-run) the confirmatory detection grid. Offline-test-friendly.

    On dry_run: returns ``{status, total, jobs}`` with no network.
    On live/offline run: computes, per (item, model, seed), the detector result +
    the baseline panel, appends each as a JSON line to ``checkpoint_path``
    (resumable, fingerprint-guarded), and returns the collected records.
    """
    if models is None:
        models = list(CONFIRM_MODELS)
    if seed_bases is None:
        seed_bases = list(CONFIRM_SEED_BASES)

    jobs = enumerate_jobs(tasks, models, seed_bases)

    if dry_run:
        return {"status": "dry_run", "total": len(jobs), "jobs": jobs}

    _validate_output_paths(checkpoint_path, cache_dir)

    cp = Path(checkpoint_path)
    cp.parent.mkdir(parents=True, exist_ok=True)

    fingerprint = run_fingerprint(
        models=models, seed_bases=seed_bases, k=k, tau=tau, tau_s=tau_s
    )

    # Resume: reuse only records whose stored fingerprint matches this run.
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
                    continue
                rec_fp = rec.get("_fingerprint")
                if rec_fp != fingerprint:
                    raise RuntimeError(
                        "LPS-confirm checkpoint fingerprint mismatch — refusing to "
                        "reuse incompatible results.\n"
                        f"  checkpoint: {checkpoint_path}\n"
                        f"  record (task={rec.get('task_id')}, model={rec.get('model')}, "
                        f"seed={rec.get('seed_base')}) fingerprint: {rec_fp}\n"
                        f"  current run fingerprint: {fingerprint}\n"
                        "Delete/namespace the checkpoint before re-running with a "
                        "different roster/seeds/k/tau/tau_s/method-version."
                    )
                done.add((rec.get("task_id"), rec.get("model"), rec.get("seed_base")))
                results.append(rec)
    else:
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

    task_by_id = {t.id: t for t in tasks}
    completed = 0
    skipped = 0
    for job in jobs:
        key = (job["task_id"], job["model"], job["seed_base"])
        if key in done:
            skipped += 1
            continue
        task = task_by_id[job["task_id"]]
        model = job["model"]
        seed_base = job["seed_base"]

        res = lps.lpp_detect(
            task, client, model, tau=tau, tau_s=tau_s, k=k, base_seed=seed_base
        )

        # ── Baseline panel ────────────────────────────────────────────────────
        # token-confidence replays H_seed's exact generic calls (cache HIT → $0).
        tok = baselines.token_confidence(
            task, client, model,
            k=k, temperature=lps.DEFAULT_TEMPERATURE, base_seed=seed_base,
        )
        labels = res.get("seed_labels") or []
        surfaced = res.get("surfaced_dims") or []
        res["baselines"] = {
            "token_available": tok["available"],
            "token_mean_confidence": tok["mean_confidence"],
            "token_uncertainty": tok["uncertainty"],
            "self_consistency_agreement": baselines.self_consistency_agreement(labels),
            "self_consistency_disagreement":
                baselines.self_consistency_disagreement(labels),
            "requirements_probing_count":
                baselines.requirements_probing_count(surfaced),
            "requirements_probing_flag":
                baselines.requirements_probing_flag(surfaced),
        }

        # Localization sanity (gold axis — REPORTING ONLY).
        res["seed_base"] = seed_base
        res["deleted_axis"] = list(task.key_questions)
        res["axis_match"] = lps.axis_match(
            res["flagged_dimension"] or "", task.key_questions
        )
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


# ── CLI ──────────────────────────────────────────────────────────────────────

def _select_items(tasks: List[Any], item_ids: Optional[List[str]],
                  max_items: Optional[int]) -> List[Any]:
    """Optionally restrict the item set (smoke runs). Fail loud on unknown IDs."""
    if item_ids:
        by_id = {t.id: t for t in tasks}
        missing = [i for i in item_ids if i not in by_id]
        if missing:
            raise ValueError(f"Unknown --items IDs: {missing}")
        return [by_id[i] for i in item_ids]
    if max_items is not None:
        return list(tasks)[:max_items]
    return list(tasks)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Study 2 LPS CONFIRMATORY detection grid (multi-model × seed)."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Enumerate the job count with NO network.")
    parser.add_argument("--checkpoint", default=CHECKPOINT)
    parser.add_argument("--cache-dir", default=CACHE_DIR)
    parser.add_argument("--rpm", type=int, default=RPM)
    parser.add_argument("--models", nargs="+", default=None,
                        help=f"Override model slugs (default: {CONFIRM_MODELS}). "
                             "Pass ONE slug per runner for model-parallel execution.")
    parser.add_argument("--seeds", "--seed-bases", dest="seed_bases", nargs="+",
                        type=int, default=None,
                        help=f"Override seed bases (default: {CONFIRM_SEED_BASES}).")
    parser.add_argument("--shard-by-model", action="store_true",
                        help="Write PER-MODEL namespaced checkpoint+cache "
                             "(cp_lps_confirm__<slug>.jsonl / "
                             ".llm_cache_lps_confirm__<slug>) so concurrent runners — "
                             "one per model — never touch the same file. Ignores "
                             "--checkpoint/--cache-dir.")
    parser.add_argument("--items", nargs="+", default=None,
                        help="Restrict to specific item IDs (smoke).")
    parser.add_argument("--max-items", type=int, default=None,
                        help="Restrict to the first N items (smoke).")
    parser.add_argument("--k", type=int, default=lps.DEFAULT_K)
    parser.add_argument("--budget-usd", type=float, default=None)
    args = parser.parse_args(argv)

    import registered_run as _rr
    from common.config import load_config

    tasks_all = _rr.load_tasks()
    tasks = _select_items(tasks_all, args.items, args.max_items)
    models = args.models or list(CONFIRM_MODELS)
    seed_bases = args.seed_bases or list(CONFIRM_SEED_BASES)

    n_jobs = len(tasks) * len(models) * len(seed_bases)
    print("=" * 76)
    print("STUDY 2 — LPS CONFIRMATORY detection grid (Phase 2a)")
    print(f"  items={len(tasks)} (of {len(tasks_all)})  models={len(models)}  "
          f"seeds={len(seed_bases)}  k={args.k}")
    print(f"  models: {models}")
    print(f"  seed_bases: {seed_bases}")
    print(f"  operating point (FROZEN): tau={TAU}  tau_s={TAU_S}")
    print(f"  jobs = {len(tasks)} × {len(models)} × {len(seed_bases)} = {n_jobs}")
    if args.shard_by_model:
        print("  shard-by-model: ON — per-model namespaced checkpoint+cache "
              "(PARALLEL-safe)")
        for m in models:
            print(f"    {m:<20} → {shard_checkpoint(m)}  |  {shard_cache(m)}")
    else:
        print(f"  checkpoint={args.checkpoint}  cache={args.cache_dir}")
    print("=" * 76)

    if args.dry_run:
        res = run(tasks, load_config(), models=models, seed_bases=seed_bases,
                  k=args.k, dry_run=True)
        print(f"\n[Confirm] Dry-run: {res['total']} jobs "
              f"({len(tasks)} items × {len(models)} models × {len(seed_bases)} seeds).")
        if args.shard_by_model:
            per_shard = len(tasks) * len(seed_bases)
            print(f"[Confirm] Per-model shard: {per_shard} jobs each "
                  f"({len(models)} concurrent runners).")
        return

    if not pilot1._live_ok():
        print("lps_confirm: skipped (RUNNER_LIVE != 1). Set RUNNER_LIVE=1 to run "
              "live (copilot_proxy, no token required).")
        sys.exit(0)
    if not pilot1._proxy_reachable():
        print("lps_confirm: skipped (copilot_proxy not reachable at "
              "http://127.0.0.1:8313). Start the proxy before running live.")
        sys.exit(0)

    cfg = load_config()

    # ── Per-model shards: each model → its OWN checkpoint+cache (parallel-safe). ─
    # A single process can drive several shards sequentially; the intended parallel
    # workflow launches ONE process per model (each with --models <slug>), so each
    # writes an INDEPENDENT, independently-resumable shard.
    if args.shard_by_model:
        totals = {"completed": 0, "skipped": 0, "total": 0}
        for m in models:
            cp = shard_checkpoint(m)
            cache = shard_cache(m)
            r = run(
                tasks, cfg,
                models=[m], seed_bases=seed_bases,
                checkpoint_path=cp, cache_dir=cache,
                rpm=args.rpm, k=args.k, budget_usd=args.budget_usd,
            )
            print(f"[Confirm] shard {m}: completed={r['completed']} "
                  f"skipped={r['skipped']} → {r['checkpoint']}")
            for key in totals:
                totals[key] += r[key]
        print(f"\n[Confirm] All shards: completed={totals['completed']} "
              f"skipped={totals['skipped']} total={totals['total']}")
        print("[Confirm] Merge + analyse with: python scripts/lps_confirm_merge.py "
              "&& python scripts/lps_confirm_report.py "
              "--shards '.run_partitions/cp_lps_confirm__*.jsonl' "
              "--out files/study2_confirm_results.md")
        return

    result = run(
        tasks, cfg,
        models=models, seed_bases=seed_bases,
        checkpoint_path=args.checkpoint, cache_dir=args.cache_dir,
        rpm=args.rpm, k=args.k, budget_usd=args.budget_usd,
    )
    print(f"\n[Confirm] Result: completed={result['completed']} "
          f"skipped={result['skipped']} total={result['total']}")
    print(f"[Confirm] Checkpoint: {result['checkpoint']}")
    print("[Confirm] Analyse with: python scripts/lps_confirm_report.py "
          f"--checkpoint {args.checkpoint} --out files/study2_confirm_results.md")


if __name__ == "__main__":
    main()
