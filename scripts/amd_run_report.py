# constructed by: Claude (Anthropic) family
"""Amendment 13 / 14 sidecar analysis + report.

# Implementer model family: Claude/Anthropic

Reads an ``amd_run`` sidecar checkpoint (written by ``scripts/amd_run.py``) and
produces the pre-registered SECONDARY-robustness analysis:

  * **Amendment 13 (regime×domain crossing, H-A13):** per-domain
    ``cd_primary(H1) − cd_primary(H2)`` on the k1 (underspecified) items, with an
    item-level bootstrap CI, plus a ``regime × domain`` read — the regime effect
    (H1→high / H2→low convergent delusion) must hold WITHIN code_spec AND
    policy_qa, i.e. it is not a domain artifact. Provenance: the contrast is
    computed on tested-family ≠ constructor-family cells (mai-code is out-of-pool,
    so all tested cells qualify — documented).

  * **Amendment 14 (unfiltered replication, H-A14):** the UNCONDITIONED pooled
    ``cd_primary`` on the unfiltered k1 items + the DELTA vs the screened
    confirmatory rate (≈0.53), item-level bootstrap CI, reported HONESTLY
    regardless of outcome (integrity clause §0).

Executable gold ONLY — the frozen ``cd_primary`` (target I0) via the frozen
labeler; NO LLM judge. Writes ``files/amd13_results.md`` / ``files/amd14_results.md``.

Usage::

    python scripts/amd_run_report.py --which amd13
    python scripts/amd_run_report.py --which amd14 --checkpoint .run_partitions/cp_amd_run__amd14.jsonl
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# The screened confirmatory pooled cd_primary rate (Amendment 14 §2 / §3 baseline).
SCREENED_CONFIRMATORY_RATE = 0.53
# Constructor family (out-of-pool). Provenance holdout drops any tested cell whose
# model family equals this (none exist, since mai-code is not in the tested roster).
CONSTRUCTOR_FAMILY = "mai-code"

# The A13 validity gate reads this verdict artifact (written by
# scripts/amd13_manipulation_check.py). The regime×domain crossing is claimed ONLY
# when this file exists AND records gate_pass == True (MAJOR 4). Non-protected name.
MANIP_VERDICT_PATH = str(_REPO_ROOT / "files" / "amd13_manipulation_verdict.json")

# The two named domains Amendment 13 REQUIRES (both must be sufficiently powered;
# a missing/underpowered domain must NOT pass as "holds" — MAJOR 5).
A13_REQUIRED_DOMAINS: Tuple[str, ...] = ("code_spec", "policy_qa")
# Backward-compatible display only. Scientific sufficiency is the exact
# preregistered task × condition × model/pool × seed grid validated below.
A13_MIN_ITEMS_PER_CELL = 2


def _load(mod_name: str, filename: str):
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    sys.modules[mod_name] = mod
    return mod


# ── Path guard (BLOCKER 2): every report INPUT + OUTPUT is isolated ───────────

def validate_report_input(checkpoint_path: str) -> None:
    """Reject any report INPUT checkpoint outside the amd_run namespace.

    Mirrors amd_run.validate_output_paths for the read side: the checkpoint must be
    an amd_run partition (``cp_amd_run__*.jsonl``) with NO protected token anywhere
    in its resolved path — so the report can never read a confirmatory / intervention
    / pilot / registered_run artifact.
    """
    amd_run = _load("amd_run", "amd_run.py")
    cp = Path(checkpoint_path)
    if not cp.name.startswith("cp_amd_run__"):
        raise ValueError(
            f"Refusing report input {checkpoint_path!r}: must be an amd_run "
            "checkpoint (cp_amd_run__<which>*.jsonl), never a confirmatory/other-pass file."
        )
    amd_run.scan_protected_path(cp, "report checkpoint")


def validate_report_output(report_path: str) -> None:
    """Reject any report OUTPUT path that could clobber another pass's artifact.

    The output basename must be ``amd13_results.md`` / ``amd14_results.md`` and its
    resolved path must contain NO protected token (confirmatory/intervention/pilot/…).
    """
    amd_run = _load("amd_run", "amd_run.py")
    p = Path(report_path)
    if p.name not in ("amd13_results.md", "amd14_results.md"):
        raise ValueError(
            f"Refusing report output {report_path!r}: amd_run_report writes ONLY "
            "amd13_results.md / amd14_results.md."
        )
    amd_run.scan_protected_path(p, "report output")


# ── A13 validity gate: read the pre-registered manipulation verdict (MAJOR 4) ─

def load_manip_verdict(path: str = MANIP_VERDICT_PATH) -> Optional[Dict[str, Any]]:
    """Return the manipulation-check verdict dict, or None if absent/unreadable.

    The A13 crossing claim is gated on this returning a dict with
    ``gate_pass == True``. An absent verdict (probe never run) is treated as NOT
    passing — the report renders only the validity-failure outcome.
    """
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _gate_passed(verdict: Optional[Dict[str, Any]]) -> bool:
    return bool(
        verdict
        and verdict.get("gate_pass") is True
        and verdict.get("grid_complete") is True
        and verdict.get("verdict_status") == "PASS"
    )


# ── Exact preregistered grid completeness (MAJOR scientific-integrity fix) ───

def _expected_tasks(which: str) -> List[Any]:
    amd_run = _load("amd_run", "amd_run.py")
    return amd_run.load_amd_tasks(which, include_h1_anchors=(which == "amd13"))


def _expected_seeds() -> List[int]:
    amd_run = _load("amd_run", "amd_run.py")
    from common.config import load_config
    return amd_run._default_seeds(load_config())


def load_run_manifest(checkpoint_path: str) -> Optional[Dict[str, Any]]:
    """Load the amd_run sidecar manifest that records requested seeds."""
    amd_run = _load("amd_run", "amd_run.py")
    return amd_run.load_run_manifest(checkpoint_path)


def requested_seeds_from_manifest(checkpoint_path: str, which: str) -> Tuple[Optional[List[int]], Dict[str, Any]]:
    """Return the run-authoritative requested seeds, or fail-closed metadata."""
    manifest = load_run_manifest(checkpoint_path)
    if not manifest:
        return None, {
            "complete": False,
            "which": which,
            "reason": "run manifest missing or unreadable; requested seeds are unknown",
            "manifest_path": _load("amd_run", "amd_run.py").run_manifest_path(checkpoint_path),
        }
    if manifest.get("which") != which:
        return None, {
            "complete": False,
            "which": which,
            "reason": f"run manifest is for {manifest.get('which')!r}, not {which!r}",
        }
    raw = manifest.get("requested_seeds")
    if not isinstance(raw, list):
        return None, {"complete": False, "which": which, "reason": "run manifest lacks requested_seeds"}
    try:
        seeds = list(dict.fromkeys(int(s) for s in raw))
    except (TypeError, ValueError):
        return None, {"complete": False, "which": which, "reason": "run manifest has non-integer requested_seeds"}
    return seeds, {"complete": True, "which": which, "requested_seeds": seeds, "manifest": manifest}


def expected_run_jobs(
    which: str,
    *,
    tasks: Optional[List[Any]] = None,
    seeds: Optional[List[int]] = None,
) -> Set[Tuple[str, str, str, int]]:
    """Return exact expected analysis grid as (task, config, model_id, seed)."""
    amd_run = _load("amd_run", "amd_run.py")
    rr = _load("registered_run", "registered_run.py")
    if tasks is None:
        tasks = _expected_tasks(which)
    if seeds is None:
        seeds = _expected_seeds()
    from common.config import load_config

    cp = str(_REPO_ROOT / ".run_partitions" / f"cp_amd_run__{which}__gridcheck.jsonl")
    cache = str(_REPO_ROOT / f".llm_cache_amd_run_{which}_gridcheck")
    runner, _ = amd_run.build_amd_runner(
        load_config(), tasks, which=which, checkpoint_path=cp, cache_dir=cache,
        seeds=seeds, configs=amd_run.AMD_CONFIGS, offline=True,
    )
    return {(t, cfg, model, int(seed)) for t, cfg, _role, model, seed in runner.enumerate_grid()}


def _min_agents_for_config(config: str) -> int:
    if config == "heterogeneous-MAD":
        amd_run = _load("amd_run", "amd_run.py")
        return int(amd_run.AMD_CONFIG_KWARGS["heterogeneous-MAD"].get("n_agents", 4))
    return 1


def tidy_grid_completeness(
    tidy,
    which: str,
    *,
    tasks: Optional[List[Any]] = None,
    seeds: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Validate tidy rows against the exact preregistered run grid.

    This prevents partial checkpoints from being treated as powered A13 evidence
    or as an A14 unconditioned result. The expected grid is driven by the sidecar
    item files + matched A13 anchors, pre-registered configs, roster/pool, and
    ≥3 default seeds.
    """
    from analysis.contrasts import COLS

    if tasks is None:
        tasks = _expected_tasks(which)
    if seeds is None:
        seeds = _expected_seeds()
    expected = expected_run_jobs(which, tasks=tasks, seeds=seeds)
    expected_seed_set = {int(s) for s in seeds}
    seed_ok = len(expected_seed_set) >= 3

    counts: Dict[Tuple[str, str, str, int], int] = {}
    unexpected: Dict[Tuple[str, str, str, int], int] = {}
    if len(tidy) > 0:
        for _, row in tidy.iterrows():
            key = (
                row.get(COLS["item"]),
                row.get(COLS["method"]),
                row.get("model"),
                int(row.get(COLS["seed"])),
            )
            if key in expected:
                counts[key] = counts.get(key, 0) + 1
            else:
                unexpected[key] = unexpected.get(key, 0) + 1

    missing = []
    underfilled = []
    for task_id, config, model_id, seed in sorted(expected):
        n = counts.get((task_id, config, model_id, seed), 0)
        need = _min_agents_for_config(config)
        if n == 0:
            missing.append({"task": task_id, "config": config, "model": model_id, "seed": seed})
        elif n < need:
            underfilled.append({
                "task": task_id, "config": config, "model": model_id,
                "seed": seed, "observed_agents": n, "required_agents": need,
            })

    return {
        "complete": bool(seed_ok and not missing and not underfilled and not unexpected),
        "which": which,
        "seed_count_ok": seed_ok,
        "expected_seeds": sorted(expected_seed_set),
        "n_expected_jobs": len(expected),
        "n_observed_jobs": sum(1 for k in expected if counts.get(k, 0) >= _min_agents_for_config(k[1])),
        "n_missing_jobs": len(missing),
        "n_underfilled_jobs": len(underfilled),
        "n_unexpected_jobs": len(unexpected),
        "missing_jobs": missing[:50],
        "underfilled_jobs": underfilled[:50],
        "unexpected_jobs": [
            {"task": t, "config": c, "model": m, "seed": s, "rows": n}
            for (t, c, m, s), n in list(sorted(unexpected.items()))[:50]
        ],
    }


def checkpoint_done_completeness(
    checkpoint_path: str,
    which: str,
    *,
    tasks: Optional[List[Any]] = None,
    seeds: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Validate checkpoint job_done markers against the expected grid before load."""
    if tasks is None:
        tasks = _expected_tasks(which)
    if seeds is None:
        seeds = _expected_seeds()
    expected = expected_run_jobs(which, tasks=tasks, seeds=seeds)
    done: Set[Tuple[str, str, str, int]] = set()
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
                        rec.get("model_id", ""),
                        int(rec.get("seed", 0)),
                    ))
    missing = [
        {"task": t, "config": c, "model": m, "seed": s}
        for t, c, m, s in sorted(expected - done)
    ]
    unexpected = [
        {"task": t, "config": c, "model": m, "seed": s}
        for t, c, m, s in sorted(done - expected)
    ]
    return {
        "complete": len(missing) == 0 and len(unexpected) == 0 and len(set(seeds)) >= 3,
        "which": which,
        "expected_seeds": sorted({int(s) for s in seeds}),
        "n_expected_jobs": len(expected),
        "n_done_jobs": len(expected & done),
        "n_missing_done_jobs": len(missing),
        "n_unexpected_done_jobs": len(unexpected),
        "missing_done_jobs": missing[:50],
        "unexpected_done_jobs": unexpected[:50],
    }


def _merge_completeness(*parts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    present = [p for p in parts if p is not None]
    if not present:
        return {"complete": False, "reason": "no completeness validation supplied"}
    merged: Dict[str, Any] = {"complete": all(p.get("complete") for p in present), "checks": present}
    return merged


def filter_tidy_to_seeds(tidy, seeds: Optional[List[int]]):
    """Restrict tidy rows to the authoritative requested seed set."""
    if seeds is None or len(tidy) == 0:
        return tidy
    from analysis.contrasts import COLS
    allowed = {int(s) for s in seeds}
    return tidy[tidy[COLS["seed"]].map(lambda s: int(s) in allowed)].copy()


# ── Provenance holdout (tested-family ≠ constructor-family) ──────────────────

def _model_family(model_id: str) -> str:
    """Extract a coarse model family from a slug / pool identity."""
    if not isinstance(model_id, str):
        return ""
    low = model_id.lower()
    if "mai-code" in low or "mai_code" in low:
        return "mai-code"
    if "/" in model_id:
        return model_id.split("/", 1)[0]
    return model_id.split("-", 1)[0]


def apply_provenance_holdout(tidy):
    """Drop tested cells whose model family == the constructor family (mai-code).

    Returns (filtered_df, n_dropped). With mai-code out-of-pool this drops 0 rows
    — the holdout is documented and enforced defensively.
    """
    if len(tidy) == 0 or "model" not in tidy.columns:
        return tidy, 0
    fam = tidy["model"].map(_model_family)
    mask = fam != CONSTRUCTOR_FAMILY
    n_dropped = int((~mask).sum())
    return tidy[mask], n_dropped


# ── Per-item cd_primary means (restricted to k1 items of a regime/domain) ────

def _per_item_cd(tidy, *, regime: Optional[str] = None, domain: Optional[str] = None,
                 k_min: int = 1):
    """Return {item_id: mean cd_primary over its cells} for the filtered subset.

    Filters to ambiguity_k >= ``k_min`` (default 1 = underspecified) and, when
    given, the requested ``regime`` and ``domain``. cd_primary is computed per
    (item, method, model_class, seed) cell via the frozen ``compute_cell_cd`` then
    averaged per item.
    """
    from analysis.contrasts import compute_cell_cd, COLS

    if len(tidy) == 0:
        return {}
    df = tidy
    df = df[df[COLS["ambiguity_k"]] >= k_min]
    if regime is not None:
        df = df[df[COLS["regime"]] == regime]
    if domain is not None and "domain" in df.columns:
        df = df[df["domain"] == domain]
    elif domain is not None:
        # tidy has no explicit domain column → derive from task id prefix mapping
        df = df[df[COLS["item"]].map(_domain_of_item) == domain]
    if len(df) == 0:
        return {}
    cells = compute_cell_cd(df)
    if len(cells) == 0:
        return {}
    item_col = COLS["item"]
    return cells.groupby(item_col)["cd_primary"].mean().to_dict()


def _domain_of_item(item_id: str) -> str:
    """Best-effort domain from a task-id prefix (code_*, policy_*, data_*)."""
    if not isinstance(item_id, str):
        return ""
    if item_id.startswith("code_"):
        return "code_spec"
    if item_id.startswith("policy_"):
        return "policy_qa"
    if item_id.startswith("data_"):
        return "data_analysis"
    return ""


# ── Amendment 13: per-domain contrast + regime×domain interaction read ───────

def _bootstrap_ci_interaction(
    h1_a: List[float], h2_a: List[float], h1_b: List[float], h2_b: List[float],
    *, n_boot: int = 2000, seed: int = 42,
):
    """Bootstrap 95% CI for the interaction [(H1_a−H2_a) − (H1_b−H2_b)].

    Resamples each of the four item-value lists independently. Returns
    (lo, hi); (-inf, +inf) if any list is empty.
    """
    import random
    if not (h1_a and h2_a and h1_b and h2_b):
        return (float("-inf"), float("inf"))
    rng = random.Random(seed)

    def _m(xs):
        return sum(xs) / len(xs)

    stats = sorted(
        (_m(rng.choices(h1_a, k=len(h1_a))) - _m(rng.choices(h2_a, k=len(h2_a))))
        - (_m(rng.choices(h1_b, k=len(h1_b))) - _m(rng.choices(h2_b, k=len(h2_b))))
        for _ in range(n_boot)
    )
    lo = stats[max(0, int(n_boot * 0.025) - 1)]
    hi = stats[min(n_boot - 1, int(n_boot * 0.975))]
    return (lo, hi)


def a13_analysis(tidy, *, domains: List[str] = None,
                 manip_verdict: Any = "__load__",
                 grid_completeness: Optional[Dict[str, Any]] = None,
                 expected_tasks: Optional[List[Any]] = None,
                 expected_seeds: Optional[List[int]] = None) -> Dict[str, Any]:
    """Per-domain cd_primary(H1) − cd_primary(H2) + regime×domain INTERACTION read.

    Implements the pre-registered Amendment 13 H-A13 analysis (MAJOR 5) AND the
    executable validity gate (MAJOR 4):

      * per-domain contrast (H1−H2) with item-level bootstrap CI;
      * a pooled regime MAIN EFFECT (both domains) with bootstrap CI;
      * a regime×domain INTERACTION estimate (difference of the two required-domain
        contrasts) with bootstrap CI — H-A13 requires a significant regime main
        effect that is NOT explained away by a significant interaction;
      * BOTH named domains (code_spec AND policy_qa) MUST be sufficiently powered;
        a missing/underpowered domain does NOT pass as "holds";
      * the crossing claim is GATED on a PASS manipulation verdict — if the verdict
        is absent or not PASS, ``gate_pass`` is False and no crossing is claimed.

    ``manip_verdict``: pass a dict to inject a verdict (tests), ``None`` to force
    "absent", or leave the sentinel to load from ``MANIP_VERDICT_PATH``.
    """
    rr = _load("registered_run", "registered_run.py")
    if domains is None:
        domains = list(A13_REQUIRED_DOMAINS)

    if manip_verdict == "__load__":
        manip_verdict = load_manip_verdict()
    gate_pass = _gate_passed(manip_verdict)
    if grid_completeness is None:
        grid_completeness = tidy_grid_completeness(
            tidy, "amd13", tasks=expected_tasks, seeds=expected_seeds,
        )
    grid_complete = bool(grid_completeness.get("complete"))
    if expected_seeds is None:
        expected_seeds = tidy.attrs.get("expected_seeds")
    tidy_for_analysis = filter_tidy_to_seeds(tidy, expected_seeds)

    held, n_dropped = apply_provenance_holdout(tidy_for_analysis)

    per_domain: Dict[str, Any] = {}
    # keep raw item-value lists for the pooled / interaction bootstraps
    dom_vals: Dict[str, Dict[str, List[float]]] = {}
    for dom in domains:
        h1 = _per_item_cd(held, regime="H1_external", domain=dom, k_min=1)
        h2 = _per_item_cd(held, regime="H2_derivable", domain=dom, k_min=1)
        h1_vals = list(h1.values())
        h2_vals = list(h2.values())
        dom_vals[dom] = {"h1": h1_vals, "h2": h2_vals}
        mean_h1 = sum(h1_vals) / len(h1_vals) if h1_vals else float("nan")
        mean_h2 = sum(h2_vals) / len(h2_vals) if h2_vals else float("nan")
        contrast = (mean_h1 - mean_h2) if (h1_vals and h2_vals) else float("nan")
        ci_lo, ci_hi = rr._bootstrap_ci_diff(h1_vals, h2_vals) if (
            len(h1_vals) >= A13_MIN_ITEMS_PER_CELL and len(h2_vals) >= A13_MIN_ITEMS_PER_CELL
        ) else (float("-inf"), float("inf"))
        sufficient = bool(
            grid_complete and
            len(h1_vals) >= A13_MIN_ITEMS_PER_CELL and len(h2_vals) >= A13_MIN_ITEMS_PER_CELL
        )
        holds = bool(sufficient and contrast > 0 and ci_lo > 0)
        per_domain[dom] = {
            "n_h1_items": len(h1_vals),
            "n_h2_items": len(h2_vals),
            "sufficient": sufficient,
            "cd_h1": mean_h1,
            "cd_h2": mean_h2,
            "contrast": contrast,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "direction_holds": holds,
            "h1_items": h1,
            "h2_items": h2,
        }

    # ── pooled regime MAIN EFFECT across the required domains ────────────────
    pooled_h1 = [v for d in A13_REQUIRED_DOMAINS for v in dom_vals.get(d, {}).get("h1", [])]
    pooled_h2 = [v for d in A13_REQUIRED_DOMAINS for v in dom_vals.get(d, {}).get("h2", [])]
    main_mean_h1 = sum(pooled_h1) / len(pooled_h1) if pooled_h1 else float("nan")
    main_mean_h2 = sum(pooled_h2) / len(pooled_h2) if pooled_h2 else float("nan")
    main_contrast = (main_mean_h1 - main_mean_h2) if (pooled_h1 and pooled_h2) else float("nan")
    main_ci_lo, main_ci_hi = rr._bootstrap_ci_diff(pooled_h1, pooled_h2) if (
        len(pooled_h1) >= A13_MIN_ITEMS_PER_CELL and len(pooled_h2) >= A13_MIN_ITEMS_PER_CELL
    ) else (float("-inf"), float("inf"))
    main_effect_significant = bool(
        grid_complete and pooled_h1 and pooled_h2 and main_contrast > 0 and main_ci_lo > 0
    )

    # ── require BOTH named domains sufficiently powered (MAJOR 5) ────────────
    both_domains_sufficient = all(
        per_domain.get(d, {}).get("sufficient", False) for d in A13_REQUIRED_DOMAINS
    )
    missing_domains = [
        d for d in A13_REQUIRED_DOMAINS if not per_domain.get(d, {}).get("sufficient", False)
    ]

    # ── regime×domain INTERACTION estimate + CI (only when both powered) ─────
    interaction = float("nan")
    inter_ci_lo, inter_ci_hi = float("-inf"), float("inf")
    interaction_significant = None
    if both_domains_sufficient:
        d0, d1 = A13_REQUIRED_DOMAINS
        c0 = per_domain[d0]["contrast"]
        c1 = per_domain[d1]["contrast"]
        interaction = c0 - c1
        inter_ci_lo, inter_ci_hi = _bootstrap_ci_interaction(
            dom_vals[d0]["h1"], dom_vals[d0]["h2"],
            dom_vals[d1]["h1"], dom_vals[d1]["h2"],
        )
        # "significant interaction" = CI excludes 0 (would explain the effect away)
        interaction_significant = bool(inter_ci_lo > 0 or inter_ci_hi < 0)

    # regime effect holds WITHIN domain, not domain-confounded: BOTH required
    # domains must be sufficient AND show the positive contrast (CI>0).
    holds_within_both = both_domains_sufficient and all(
        per_domain[d]["direction_holds"] for d in A13_REQUIRED_DOMAINS
    )
    # H-A13 crossing supported iff: gate PASSED, both domains powered, a positive
    # pooled main effect, it holds in BOTH domains, and no interaction that would
    # explain it away.
    no_explanatory_interaction = both_domains_sufficient and interaction_significant is False
    crossing_supported = bool(
        gate_pass
        and grid_complete
        and both_domains_sufficient
        and main_effect_significant
        and holds_within_both
        and no_explanatory_interaction
    )

    return {
        "gate_pass": gate_pass,
        "grid_complete": grid_complete,
        "grid_completeness": grid_completeness,
        "manip_verdict_present": manip_verdict is not None,
        "manip_verdict": manip_verdict,
        "per_domain": per_domain,
        "required_domains": list(A13_REQUIRED_DOMAINS),
        "both_domains_sufficient": both_domains_sufficient,
        "missing_or_underpowered_domains": missing_domains,
        "main_effect": {
            "n_h1_items": len(pooled_h1),
            "n_h2_items": len(pooled_h2),
            "cd_h1": main_mean_h1,
            "cd_h2": main_mean_h2,
            "contrast": main_contrast,
            "ci_lo": main_ci_lo,
            "ci_hi": main_ci_hi,
            "significant": main_effect_significant,
        },
        "interaction": {
            "estimate": interaction,
            "ci_lo": inter_ci_lo,
            "ci_hi": inter_ci_hi,
            "significant": interaction_significant,
        },
        "regime_effect_holds_within_domain": holds_within_both,
        "no_explanatory_interaction": no_explanatory_interaction,
        "crossing_supported": crossing_supported,
        "provenance_dropped_cells": n_dropped,
        "constructor_family": CONSTRUCTOR_FAMILY,
    }


# ── Amendment 14: unconditioned pooled rate + delta vs screened ──────────────

def a14_analysis(tidy, *,
                 grid_completeness: Optional[Dict[str, Any]] = None,
                 expected_tasks: Optional[List[Any]] = None,
                 expected_seeds: Optional[List[int]] = None) -> Dict[str, Any]:
    """Pooled UNCONDITIONED cd_primary on the unfiltered k1 items + delta vs 0.53."""
    rr = _load("registered_run", "registered_run.py")
    if grid_completeness is None:
        grid_completeness = tidy_grid_completeness(
            tidy, "amd14", tasks=expected_tasks, seeds=expected_seeds,
        )
    grid_complete = bool(grid_completeness.get("complete"))
    if expected_seeds is None:
        expected_seeds = tidy.attrs.get("expected_seeds")
    tidy_for_analysis = filter_tidy_to_seeds(tidy, expected_seeds)
    held, n_dropped = apply_provenance_holdout(tidy_for_analysis)

    per_item = _per_item_cd(held, regime="H1_external", k_min=1)
    vals = list(per_item.values())
    if grid_complete and vals:
        pooled = sum(vals) / len(vals)
        ci_lo, ci_hi = rr._bootstrap_ci(vals) if len(vals) >= 2 else (float("-inf"), float("inf"))
        delta = pooled - SCREENED_CONFIRMATORY_RATE
        frac_convergent = sum(1 for v in vals if v > 0) / len(vals)
        status = "COMPLETE"
    else:
        pooled = float("nan")
        ci_lo, ci_hi = float("-inf"), float("inf")
        delta = float("nan")
        frac_convergent = float("nan")
        status = "INCOMPLETE"
    return {
        "status": status,
        "grid_complete": grid_complete,
        "grid_completeness": grid_completeness,
        "n_items": len(vals),
        "pooled_cd_primary": pooled,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "screened_rate": SCREENED_CONFIRMATORY_RATE,
        "delta_vs_screened": delta,
        "fraction_convergent": frac_convergent,
        "per_item": per_item,
        "provenance_dropped_cells": n_dropped,
    }


# ── Markdown rendering ────────────────────────────────────────────────────────

def render_amd13(result: Dict[str, Any]) -> str:
    L: List[str] = []
    L.append("# Amendment 13 — regime × domain crossing (pre-registered SECONDARY robustness)")
    L.append("")
    L.append("Metric: FROZEN `cd_primary` (target I0), executable gold only (Law 7). "
             "Reported as pre-registered secondary robustness — the frozen confirmatory "
             "finding is NOT changed.")
    L.append("")
    L.append("Hypothesis **H-A13**: within EACH of code_spec and policy_qa, matched "
             "`H1_external` items show HIGH convergent delusion while `H2_derivable` "
             "items show LOW (attenuated) — i.e. the regime effect is NOT domain-confounded. "
             "Pre-committed: a significant positive pooled regime main effect "
             "(`cd_primary(H1) − cd_primary(H2)`) AND the effect holding within BOTH named "
             "domains AND NO significant regime×domain interaction that would explain it "
             "away as a domain artifact.")
    L.append("")

    if not result.get("grid_complete", False):
        comp = result.get("grid_completeness") or {}
        L.append("## Outcome: INCOMPLETE / VALIDITY NOT MET — no inferential crossing claim")
        L.append("")
        L.append("The sidecar checkpoint does NOT cover the exact pre-registered "
                 "task × condition × model/pool × seed grid. Missing data are "
                 "not treated as powered evidence, so no per-domain sufficiency, "
                 "main-effect, interaction, or crossing claim is rendered.")
        L.append("")
        L.append(f"- expected jobs: {comp.get('n_expected_jobs', 'unknown')}")
        L.append(f"- observed complete jobs: {comp.get('n_observed_jobs', comp.get('n_done_jobs', 'unknown'))}")
        L.append(f"- missing jobs: {comp.get('n_missing_jobs', comp.get('n_missing_done_jobs', 'unknown'))}")
        L.append(f"- underfilled jobs: {comp.get('n_underfilled_jobs', 0)}")
        L.append("")
        return "\n".join(L)

    # ── VALIDITY GATE (MAJOR 4): no crossing claim unless the manipulation ──
    #    check PASSED. Render ONLY the validity outcome otherwise.
    gate_pass = result.get("gate_pass", False)
    L.append("## Validity gate (manipulation check)")
    if not result.get("manip_verdict_present", False):
        L.append("- **Verdict artifact ABSENT** — the oracle-hint recovery probe "
                 "(`scripts/amd13_manipulation_check.py`) has not produced a verdict.")
    else:
        mv = result.get("manip_verdict") or {}
        L.append(f"- manipulation verdict `gate_pass` = **{mv.get('gate_pass')}** "
                 f"(mean H2 recovery={_f(mv.get('mean_h2_recovery'))}, "
                 f"mean H1 recovery={_f(mv.get('mean_h1_recovery'))}, "
                 f"separation={_f(mv.get('separation'))}).")
    L.append(f"- **GATE PASSED: {gate_pass}**")
    L.append("")

    if not gate_pass:
        L.append("## Outcome: CONSTRUCTION / VALIDITY FAILURE — no crossing claim rendered")
        L.append("")
        L.append("Per Amendment 13 §4 the regime×domain crossing is claimed ONLY when the "
                 "pre-registered oracle-hint manipulation check PASSES (recovery HIGH on "
                 "`H2_derivable`, LOW on matched `H1_external` anchors, separation ≥ margin). "
                 "The gate did NOT pass (or was never run), so the H2_derivable construction "
                 "is NOT validated and **no regime×domain crossing is asserted**. This is an "
                 "HONEST validity outcome; items are NOT tuned to rescue the gate.")
        L.append("")
        L.append(f"Provenance holdout: tested-family ≠ constructor-family "
                 f"(`{result['constructor_family']}`, out-of-pool) — "
                 f"{result['provenance_dropped_cells']} cell(s) dropped (0 expected).")
        L.append("")
        return "\n".join(L)

    # ── Gate PASSED → render the full regime×domain analysis ────────────────
    L.append(f"Provenance holdout: contrast computed on tested-family ≠ constructor-family "
             f"(`{result['constructor_family']}`, out-of-pool) cells — "
             f"{result['provenance_dropped_cells']} cell(s) dropped (0 expected, mai-code not in the tested roster).")
    L.append("")
    L.append("## Per-domain contrast")
    L.append("| domain | n(H1) | n(H2) | sufficient | cd_primary(H1) | cd_primary(H2) | contrast (H1−H2) | 95% CI | direction holds |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for dom, r in result["per_domain"].items():
        L.append(
            f"| {dom} | {r['n_h1_items']} | {r['n_h2_items']} | {r['sufficient']} | "
            f"{_f(r['cd_h1'])} | {_f(r['cd_h2'])} | {_f(r['contrast'])} | "
            f"[{_f(r['ci_lo'])}, {_f(r['ci_hi'])}] | {r['direction_holds']} |"
        )
    L.append("")
    me = result["main_effect"]
    L.append("## regime × domain read (pre-registered interaction analysis)")
    L.append(f"- Required domains: {result['required_domains']}; "
             f"BOTH sufficiently powered (≥{A13_MIN_ITEMS_PER_CELL}/cell): "
             f"**{result['both_domains_sufficient']}** "
             f"(missing/underpowered: {result['missing_or_underpowered_domains'] or 'none'}).")
    L.append(f"- **Regime MAIN effect** (pooled H1−H2) = {_f(me['contrast'])} "
             f"(95% CI [{_f(me['ci_lo'])}, {_f(me['ci_hi'])}]) → significant: "
             f"**{me['significant']}**.")
    it = result["interaction"]
    L.append(f"- **regime×domain INTERACTION** = {_f(it['estimate'])} "
             f"(95% CI [{_f(it['ci_lo'])}, {_f(it['ci_hi'])}]) → significant: "
             f"**{it['significant']}** (a significant interaction would explain the effect "
             f"away as domain).")
    L.append(f"- Effect holds WITHIN BOTH named domains: "
             f"**{result['regime_effect_holds_within_domain']}**; "
             f"no explanatory interaction: **{result['no_explanatory_interaction']}**.")
    L.append("")
    L.append(f"## **H-A13 crossing supported: {result['crossing_supported']}**")
    L.append("")
    L.append("Honesty: this crossing is claimed ONLY when the manipulation check PASSED, "
             "BOTH named domains are sufficiently powered, the pooled regime main effect is "
             "significant, it holds within BOTH domains, and there is no significant "
             "regime×domain interaction. Any null / underpowered domain / interaction is "
             "reported as-is; items are never tuned.")
    L.append("")
    return "\n".join(L)


def render_amd14(result: Dict[str, Any]) -> str:
    L: List[str] = []
    L.append("# Amendment 14 — unfiltered-sample replication (pre-registered SECONDARY robustness)")
    L.append("")
    L.append("Metric: FROZEN `cd_primary` (target I0), executable gold only (Law 7).")
    L.append("")
    L.append("Hypothesis **H-A14**: on the UNFILTERED sample (NO default-screen inclusion "
             "filter), report the cross-family convergent-delusion rate UNCONDITIONALLY. "
             "Integrity clause (§0): reported HONESTLY regardless of outcome (high, "
             "attenuated, or null) — prominence, not suppression.")
    L.append("")
    if not result.get("grid_complete", False):
        comp = result.get("grid_completeness") or {}
        L.append("## Outcome: INCOMPLETE / VALIDITY NOT MET")
        L.append("")
        L.append("The checkpoint does NOT cover the exact pre-registered "
                 "24 unfiltered items × condition × model/pool × seed grid. "
                 "Therefore this is NOT rendered as the unfiltered-sample result, "
                 "and no pooled unconditioned `cd_primary` claim is reported.")
        L.append("")
        L.append(f"- expected jobs: {comp.get('n_expected_jobs', 'unknown')}")
        L.append(f"- observed complete jobs: {comp.get('n_observed_jobs', comp.get('n_done_jobs', 'unknown'))}")
        L.append(f"- missing jobs: {comp.get('n_missing_jobs', comp.get('n_missing_done_jobs', 'unknown'))}")
        L.append(f"- underfilled jobs: {comp.get('n_underfilled_jobs', 0)}")
        L.append(f"- observed k1 items with any labels: {result.get('n_items')}")
        L.append("")
        return "\n".join(L)

    L.append(f"- Unfiltered items (k1): **{result['n_items']}**")
    L.append(f"- **Pooled UNCONDITIONED cd_primary = {_f(result['pooled_cd_primary'])}** "
             f"(95% CI [{_f(result['ci_lo'])}, {_f(result['ci_hi'])}])")
    L.append(f"- Screened confirmatory rate (baseline) = {result['screened_rate']:.2f}")
    L.append(f"- **Delta vs screened = {_f(result['delta_vs_screened'])}**")
    L.append(f"- Fraction of unfiltered items still exhibiting convergent delusion "
             f"(cd_primary > 0) = {_f(result['fraction_convergent'])}")
    L.append("")
    L.append("Reading (pre-committed, NOT a pass/fail gate): if the unfiltered rate stays "
             "HIGH → prominent rebuttal to the selection-bias attack; if it ATTENUATES → an "
             "honest bound (effect partly enrichment-driven) and the claim is sharpened to "
             "its conditional form. NO tuning; the result stands as-is.")
    L.append("")
    return "\n".join(L)


def _f(x: Any) -> str:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return str(x)
    if xf != xf:  # NaN
        return "n/a"
    if xf in (float("inf"), float("-inf")):
        return "±inf" if xf > 0 else "-inf"
    return f"{xf:.4f}"


# ── Checkpoint → tidy → report ───────────────────────────────────────────────

def load_tidy_for(which: str, checkpoint_path: str):
    """Load the amd_run checkpoint into a tidy table (with a domain column)."""
    amd_run = _load("amd_run", "amd_run.py")
    from analysis.io import load_runs_tidy, FRONTIER_MODEL_CLASS_MAP

    include_anchors = which == "amd13"
    tasks = amd_run.load_amd_tasks(which, include_h1_anchors=include_anchors)
    requested_seeds, manifest_complete = requested_seeds_from_manifest(checkpoint_path, which)
    if requested_seeds is None:
        requested_seeds = []
    done_complete = checkpoint_done_completeness(
        checkpoint_path, which, tasks=tasks, seeds=requested_seeds,
    )
    # endpoint None is fine when the checkpoint has a single namespace; if it has
    # several, load_runs_tidy raises and the caller must pass expected_endpoint.
    tidy = load_runs_tidy(
        checkpoint_path, tasks, model_class_map=FRONTIER_MODEL_CLASS_MAP,
    )
    tidy = attach_domain_column(tidy, tasks)
    tidy_complete = tidy_grid_completeness(tidy, which, tasks=tasks, seeds=requested_seeds)
    tidy = filter_tidy_to_seeds(tidy, requested_seeds)
    tidy.attrs["expected_seeds"] = requested_seeds
    tidy.attrs["grid_completeness"] = _merge_completeness(
        manifest_complete, done_complete, tidy_complete,
    )
    return tidy


def attach_domain_column(tidy, tasks: List[Any]):
    """Add a ``domain`` column derived from each task's domain (fallback: id prefix)."""
    if len(tidy) == 0:
        return tidy
    from analysis.contrasts import COLS
    dom_by_id = {t.id: t.domain for t in tasks}
    tidy = tidy.copy()
    tidy["domain"] = tidy[COLS["item"]].map(
        lambda i: dom_by_id.get(i) or _domain_of_item(i)
    )
    return tidy


def write_report(which: str, markdown: str, out_dir: str = None) -> str:
    out = Path(out_dir) if out_dir else (_REPO_ROOT / "files")
    path = out / f"{which}_results.md"
    validate_report_output(str(path))  # BLOCKER 2: guard OUTPUT before any write
    out.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return str(path)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Amendment 13/14 sidecar analysis + report")
    parser.add_argument("--which", choices=("amd13", "amd14"), required=True)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    amd_run = _load("amd_run", "amd_run.py")
    def_cp, _, _ = amd_run._which_defaults(args.which)
    checkpoint = args.checkpoint or def_cp

    # BLOCKER 2: guard INPUT + OUTPUT paths BEFORE any read/write.
    validate_report_input(checkpoint)
    out_path = (Path(args.out_dir) if args.out_dir else (_REPO_ROOT / "files")) / f"{args.which}_results.md"
    validate_report_output(str(out_path))

    tidy = load_tidy_for(args.which, checkpoint)
    if len(tidy) == 0:
        print(f"amd_run_report: checkpoint {checkpoint} has no labeled runs yet — "
              "writing a placeholder report (run the driver live first).", file=sys.stderr)

    if args.which == "amd13":
        result = a13_analysis(tidy, grid_completeness=tidy.attrs.get("grid_completeness"))
        md = render_amd13(result)
    else:
        result = a14_analysis(tidy, grid_completeness=tidy.attrs.get("grid_completeness"))
        md = render_amd14(result)

    path = write_report(args.which, md, out_dir=args.out_dir)
    print(md)
    print(f"\n[amd_run_report] wrote {path}")


if __name__ == "__main__":
    main()
