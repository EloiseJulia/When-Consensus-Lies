"""Mini-pilot smoke script: online LLM path on a handful of real bench tasks.

OFFLINE / CI SAFE: this script does NOTHING unless BOTH guards pass:
  1. RUN_MINI_PILOT=1 environment variable is set
  2. GITHUB_MODELS_TOKEN or GH_MODELS_TOKEN environment variable is present

Without both flags it prints "skipped" and exits 0 — no network, no cost.

Purpose (when enabled):
  Load ≤3 tasks from the code_spec domain, run `single` + `sc(k=3)` with
  ONLINE mode on 2–3 families, label via real label_run (executable gold),
  compute convergent_delusion, print per-config labels + metric + total cost.

Hard guards:
  - Budget cap: $0.50 (hard stop via BudgetExceeded)
  - Idempotent: results cached on disk; re-running is free
  - NEVER run at full scale from this script; smoke only

Usage (after token is verified by the Manager):
  RUN_MINI_PILOT=1 python scripts/mini_pilot.py

NOTE: The Manager is responsible for running this script and reporting results.
This script was written as OFFLINE-ONLY verifiable; live execution is deferred
to the Manager who has the token (Hard Law 1 caveat acknowledged in the plan).
"""

from __future__ import annotations

import os
import sys


# ── Guard: must have both RUN_MINI_PILOT=1 AND a present token ────────────────

def _token() -> str:
    return (
        os.environ.get("GITHUB_MODELS_TOKEN")
        or os.environ.get("GH_MODELS_TOKEN")
        or ""
    )


def _should_run() -> bool:
    return os.environ.get("RUN_MINI_PILOT", "0") == "1" and bool(_token())


if not _should_run():
    print(
        "mini_pilot: skipped (RUN_MINI_PILOT != 1 or no token in "
        "GITHUB_MODELS_TOKEN / GH_MODELS_TOKEN). Set both to run."
    )
    sys.exit(0)


# ── Imports (only reached when both guards pass) ───────────────────────────────

from typing import Dict, List

from bench.code_spec import generate_tasks
from common.config import load_config
from common.llm import BudgetExceeded, LLMClient
from harness.label import label_run
from harness.metrics import convergent_delusion
from harness.run import run_self_consistency, run_single


# ── Configuration ──────────────────────────────────────────────────────────────

MAX_TASKS = 3           # Use at most this many tasks from the domain
SC_K = 3                # Self-consistency samples
BUDGET_USD = 0.50       # Hard stop — never exceed $0.50 in this smoke run
CACHE_DIR = ".llm_cache_mini_pilot"

# Families to test in this smoke.  Intentionally small to keep cost low.
# Manager can extend once the baseline run cost is known.
PILOT_FAMILIES = [
    ("openai", "openai/gpt-4o-mini"),
    ("meta",   "meta/llama-3.3-70b-instruct"),
    ("deepseek", "deepseek/deepseek-r1"),
]


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("MINI-PILOT: online LLM smoke (code_spec domain)")
    print(f"  Budget cap: ${BUDGET_USD:.2f} USD")
    print(f"  Tasks: ≤{MAX_TASKS} | SC k={SC_K} | Families: {len(PILOT_FAMILIES)}")
    print("=" * 70)

    cfg = load_config()
    # Load real benchmark tasks (deterministic, same as full-scale run)
    all_tasks = generate_tasks()
    tasks = all_tasks[:MAX_TASKS]
    print(f"\nLoaded {len(tasks)} task(s) from code_spec domain.\n")

    # Shared online client with hard budget cap
    client = LLMClient(
        cfg,
        cache_dir=CACHE_DIR,
        offline=False,
        max_budget_usd=BUDGET_USD,
        max_requests_per_min=30,  # Stay well below GitHub Models rate limit
    )

    total_cost_usd = 0.0
    results: List[Dict] = []

    for task in tasks:
        target_label = next(i.id for i in task.interpretations if i.is_target)

        for fam, slug in PILOT_FAMILIES:
            for config_name, runs_fn in [
                ("single", lambda t, c, f, s: [run_single(t, c)]),
                ("sc_k3",  lambda t, c, f, s: run_self_consistency(t, c, k=SC_K)),
            ]:
                # Each config uses the explicit family/model to override role routing
                # so different families produce genuinely different outputs.
                # We set these on each call via family/model kwargs in a patched client.
                # The cleanest way: pass family+model explicitly through run_* helpers.
                # Since run_single/run_sc route through role="tested_agents", we need
                # to temporarily override the client's config for this family.
                # Approach: create a per-family wrapper around complete().

                class _FamilyClient(LLMClient):
                    """Thin wrapper: forwards complete() with explicit family/model."""
                    _family: str = fam
                    _slug: str = slug

                    def complete(self, role, prompt, seed=None, max_retries=3,
                                 family=None, model=None):
                        # Use explicit family/model override for experiment correctness
                        return super().complete(
                            role=role,
                            prompt=prompt,
                            seed=seed,
                            max_retries=max_retries,
                            family=self._family,
                            model=self._slug,
                        )

                family_client = _FamilyClient(
                    cfg,
                    cache_dir=CACHE_DIR,
                    offline=False,
                    max_budget_usd=BUDGET_USD,
                    max_requests_per_min=30,
                )
                # Share cost state with the main client
                family_client._total_cost_usd = client._total_cost_usd
                family_client._request_times = client._request_times

                try:
                    if config_name == "single":
                        runs = [run_single(task, family_client)]
                    else:
                        runs = run_self_consistency(task, family_client, k=SC_K)
                except BudgetExceeded:
                    print(f"\n[BUDGET EXCEEDED] Stopping at ${BUDGET_USD:.2f} cap.")
                    _print_summary(results, total_cost_usd)
                    return

                # Sync cost back
                client._total_cost_usd = family_client._total_cost_usd
                # Label via executable gold
                labeled_runs = []
                for run in runs:
                    run.label = label_run(run, task)
                    labeled_runs.append(run)

                labels = [r.label for r in labeled_runs]
                cd = convergent_delusion(labels, target=target_label)
                cost_this = sum(r2.logit_conf or 0 for r2 in labeled_runs)  # just for print

                row = {
                    "task_id": task.id,
                    "family": fam,
                    "slug": slug,
                    "config": config_name,
                    "labels": labels,
                    "target": target_label,
                    "convergent_delusion": cd,
                    "cost_usd_accumulated": client._total_cost_usd,
                }
                results.append(row)

                print(
                    f"  task={task.id[:20]:<20} family={fam:<10} "
                    f"config={config_name:<8} "
                    f"labels={labels} "
                    f"conv_delusion={cd:.3f}"
                )

    total_cost_usd = client._total_cost_usd
    _print_summary(results, total_cost_usd)


def _print_summary(results: List[Dict], total_cost_usd: float) -> None:
    print("\n" + "=" * 70)
    print(f"MINI-PILOT COMPLETE — total cost: ${total_cost_usd:.4f} USD")
    print(f"  {len(results)} config×task combinations evaluated")
    if results:
        avg_cd = sum(r["convergent_delusion"] for r in results) / len(results)
        print(f"  Mean convergent_delusion across all configs: {avg_cd:.4f}")
    print(
        "\nNOTE: This is a SMOKE only. Report these numbers to the Manager "
        "before full-scale runs (Hard Law 1)."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
