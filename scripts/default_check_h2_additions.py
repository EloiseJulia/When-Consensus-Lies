# constructed by: Claude (Anthropic) family
"""default_check_h2_additions.py — Targeted default-check for the 4 NEW H2_derivable families.

Scientific purpose (see paper/plans/2026-07-18-h2-additions-default-check-plan.md):
  The H2 top-up (PR #32) added 4 new `data_analysis` families tagged H2_derivable:
  data_geomean, data_harmonic, data_cumulative, data_tierank (each k0 + k1).
  Before they count toward the confirmatory run we must CONFIRM that tag EMPIRICALLY
  on the frontier proxy roster. A family whose k1 does NOT resolve to I0 for capable
  models is mis-tagged → the Manager reclassifies or excludes it.

OFFLINE / CI SAFE: ``main()`` does NOTHING unless ``RUN_H2ADD_CHECK=1`` AND (unless
bypassed) the proxy is reachable. Offline → prints "skipped" and exits 0 (no network).

LIVE execution is the MANAGER's job (after a clean cross-family audit). The offline
unit test drives ``run_h2_additions`` against the deterministic mock client with
provider="copilot_proxy" and NO network — same discipline as default_check_frontier.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Import the shared pipeline (scripts/ is not a package) ────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load(mod_name: str, filename: str):
    # Return the cached module if already in sys.modules so all callers share one
    # identity — this is essential for monkeypatching in tests.
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    path = _THIS_DIR / filename
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod  # register BEFORE exec to handle re-entrant imports
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


default_check = _load("default_check", "default_check.py")
frontier = _load("default_check_frontier", "default_check_frontier.py")


# ── H2-additions constants (SEPARATE from the frontier/GitHub-Models runs) ────
H2ADD_TASK_IDS: List[str] = [
    "data_geomean_001_k0",
    "data_geomean_001_k1_growth_averaging",
    "data_harmonic_001_k0",
    "data_harmonic_001_k1_speed_averaging",
    "data_cumulative_001_k0",
    "data_cumulative_001_k1_cumulative_interpretation",
    "data_tierank_001_k0",
    "data_tierank_001_k1_tie_ranking",
]

# k1 ids, used for per-family verdict output.
H2ADD_K1_IDS: List[str] = [
    "data_geomean_001_k1_growth_averaging",
    "data_harmonic_001_k1_speed_averaging",
    "data_cumulative_001_k1_cumulative_interpretation",
    "data_tierank_001_k1_tie_ranking",
]

H2ADD_CHECKPOINT = "default_check_h2add_checkpoint.jsonl"
H2ADD_CACHE_DIR = ".llm_cache_default_check_h2add"
H2ADD_SUMMARY_JSONL = "default_check_h2add_summary.jsonl"
H2ADD_TABLE_TXT = "default_check_h2add_table.txt"


# ── Guard helpers (reuse frontier's proxy_reachable / resolve_probe_url) ──────

def _flag_set(env: Optional[Dict[str, str]] = None) -> bool:
    env = os.environ if env is None else env
    return env.get("RUN_H2ADD_CHECK", "0") == "1"


def _should_run(
    env: Optional[Dict[str, str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    """Double-guard (same discipline as the frontier driver).

    Guard 1: RUN_H2ADD_CHECK=1
    Guard 2: proxy reachable (skippable via FRONTIER_SKIP_PROXY_PROBE=1).
    """
    env = os.environ if env is None else env
    if not _flag_set(env):
        return False, "RUN_H2ADD_CHECK != 1"
    if env.get("FRONTIER_SKIP_PROXY_PROBE", "0") == "1":
        return True, "flag set; proxy probe skipped"
    base_url = frontier.resolve_probe_url(env, config)
    if not frontier.proxy_reachable(base_url):
        return False, f"proxy not reachable at {base_url}"
    return True, f"flag set; proxy reachable at {base_url}"


# ── Task selection (the ONLY thing that differs from the frontier driver) ──────

def select_h2add_tasks() -> Tuple[List[Any], Dict[str, str]]:
    """Select exactly the 8 H2_derivable tasks; raise KeyError on any missing id."""
    from bench.data_analysis import generate_tasks as gen_data

    by_id = {t.id: t for t in gen_data()}
    tasks: List[Any] = []
    task_role: Dict[str, str] = {}
    for tid in H2ADD_TASK_IDS:
        if tid not in by_id:
            raise KeyError(
                f"default_check_h2_additions: expected task '{tid}' not found in "
                "bench.data_analysis.generate_tasks(). Possible rename? Check H2ADD_TASK_IDS."
            )
        tasks.append(by_id[tid])
        task_role[tid] = "h2"
    return tasks, task_role


# ── Per-family verdict (documented diagnostic screen, NOT a frozen metric) ────

def _family_name(task_id: str) -> str:
    """Extract the base family name from a k1 task id (e.g. 'data_geomean_001')."""
    return task_id.split("_k")[0] if "_k" in task_id else task_id


def print_family_verdicts(report: Dict[str, Any]) -> None:
    """Print one verdict line per k1 family.

    RESOLVES iff (reasoner-class k1 rows only) resolve_rate_to_I0 >= 0.5 AND
    cd_enumerated <= 0.5.  rho_baseline, weak, and heterogeneous rows are EXCLUDED
    from this screen — including them could falsely lift a failing family to RESOLVES.
    This is a DIAGNOSTIC SCREEN only (exploratory, not pre-registered).
    """
    # Collect ONLY model_class == "reasoner" rows for k1 task ids.
    # rho_baseline / weak / heterogeneous / other are intentionally excluded.
    reasoner_k1: Dict[str, List[Dict[str, Any]]] = {}
    for row in report.get("rows", []):
        tid = row.get("task_id", "")
        if tid not in H2ADD_K1_IDS:
            continue
        if row.get("model_class") != "reasoner":
            continue
        reasoner_k1.setdefault(tid, []).append(row)

    print("")
    print("H2ADD FAMILY VERDICTS (reasoner-class rows only, diagnostic screen only):")
    print("  Threshold: RESOLVES iff resolve_rate_to_I0 >= 0.5 AND cd_enumerated <= 0.5")
    for k1_id in H2ADD_K1_IDS:
        family = _family_name(k1_id)
        rows = reasoner_k1.get(k1_id, [])
        if not rows:
            # No reasoner k1 rows — do NOT fall back to weak/rho_baseline/heterogeneous.
            print(f"FAMILY {family} k1: -> INSUFFICIENT-DATA (no reasoner k1 rows)")
            continue
        # Average over all matching reasoner-class rows.
        rr = sum(r["resolve_rate_to_I0"] for r in rows) / len(rows)
        cd = sum(r["cd_enumerated"] for r in rows) / len(rows)
        ip = sum(r["i_perp_rate"] for r in rows) / len(rows)
        verdict = "RESOLVES" if rr >= 0.5 and cd <= 0.5 else "MIS-TAGGED"
        print(
            f"FAMILY {family} k1: resolve_rate_to_I0={rr:.3f} "
            f"cd_enumerated={cd:.3f} i_perp={ip:.3f} -> {verdict}"
        )
    print("")


# ── Core run function (offline-testable, no network) ──────────────────────────

def run_h2_additions(
    client,
    *,
    checkpoint_path: str = H2ADD_CHECKPOINT,
    sc_k: int = frontier.SC_K,
    budget_usd: Optional[float] = frontier.FRONTIER_BUDGET_USD,
    rpm: int = frontier.FRONTIER_RPM,
) -> Dict[str, Any]:
    """Run the H2-additions default-check against *client* and return the report.

    ``client`` fully controls online/offline — the offline unit test passes a mock
    client with provider="copilot_proxy" and offline=True; the Manager's live run
    passes a real client. Same pipeline as the frontier driver, different task plane.
    """
    tasks, task_role = select_h2add_tasks()
    report = default_check.run_diagnostic(
        client, tasks, task_role,
        checkpoint_path=checkpoint_path,
        sc_k=sc_k,
        budget_usd=budget_usd,
        rpm=rpm,
        roster=frontier.FRONTIER_ROSTER,
    )
    report["roster_name"] = frontier.FRONTIER_ROSTER.name + "_h2add"
    return report


def write_h2add_report(report: Dict[str, Any], out_dir: str = ".") -> Tuple[str, str]:
    """Write H2-additions-named JSONL + human table (separate from frontier files)."""
    out = Path(out_dir)
    jsonl_path = out / H2ADD_SUMMARY_JSONL
    table_path = out / H2ADD_TABLE_TXT
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for row in report["rows"]:
            fh.write(json.dumps({"type": "row", **row}) + "\n")
        summary = {k: v for k, v in report.items() if k != "rows"}
        fh.write(json.dumps({"type": "summary", **summary}) + "\n")
    with open(table_path, "w", encoding="utf-8") as fh:
        fh.write(default_check.render_table(report) + "\n")
    return str(jsonl_path), str(table_path)


# ── CLI entry point (double-guarded) ──────────────────────────────────────────

def main() -> None:
    from common.config import load_config

    # Fast path: no explicit opt-in → skip before loading anything.
    if not _flag_set():
        print(
            "default_check_h2_additions: skipped (RUN_H2ADD_CHECK != 1). "
            "Set RUN_H2ADD_CHECK=1 (and ensure the Copilot proxy is reachable, or set "
            "FRONTIER_SKIP_PROXY_PROBE=1) to run live."
        )
        sys.exit(0)

    cfg = load_config()
    ok, reason = _should_run(config=cfg)
    if not ok:
        print(
            f"default_check_h2_additions: skipped ({reason}). "
            "Ensure the Copilot proxy is reachable, or set FRONTIER_SKIP_PROXY_PROBE=1."
        )
        sys.exit(0)

    base_url = frontier.resolve_base_url(config=cfg)

    print("=" * 74)
    print("DEFAULT-CHECK H2-ADDITIONS — LIVE (EXPLORATORY, pre-launch checklist #1)")
    print(f"  provider={frontier.PROVIDER}  base_url={base_url or '(config/provider default)'}")
    print(f"  sc_k={frontier.SC_K}  budget=${frontier.FRONTIER_BUDGET_USD:.2f}  rpm={frontier.FRONTIER_RPM}")
    print(f"  checkpoint={H2ADD_CHECKPOINT}  cache={H2ADD_CACHE_DIR}")
    print(f"  tasks={H2ADD_TASK_IDS}")
    print(f"  roster={frontier.FRONTIER_ROSTER.name}")
    print("=" * 74)

    client = frontier.build_client(
        cfg,
        offline=False,
        base_url=base_url,
        cache_dir=H2ADD_CACHE_DIR,
    )
    report = run_h2_additions(client)
    jsonl_path, table_path = write_h2add_report(report)

    print(default_check.render_table(report))
    print_family_verdicts(report)
    print(f"Wrote machine summary -> {jsonl_path}")
    print(f"Wrote human table     -> {table_path}")
    print("\nNOTE: EXPLORATORY diagnostic — report to the Manager before the confirmatory run.")


if __name__ == "__main__":
    main()
