# Plan — Targeted default-check on the 4 NEW H2_derivable families (pre-launch checklist #1)

> Manager spec for an IMPLEMENT sub-agent (Claude family). Orchestrator-only Manager wrote this;
> the sub-agent writes ALL code in its worktree. Auditor will be a DIFFERENT family (GPT).

## 0. Why (scientific purpose)
The H2 top-up (PR #32, decision-log row 61) added 4 new `data_analysis` families tagged
`H2_derivable`: **data_geomean, data_harmonic, data_cumulative, data_tierank** (each k0 + k1).
The `H2_derivable` tag is a SCIENTIFIC claim: on the ambiguous (k1) variant, a CAPABLE model
RESOLVES the ambiguity to **I0** (the natural default that is *derivable from the retained
prompt/data*), rather than converging on an enumerated foil. Before this counts toward the
confirmatory run we must CONFIRM that tag EMPIRICALLY on the frontier proxy roster. Any family
whose k1 does NOT resolve to I0 for capable models is mis-tagged → the Manager reclassifies or
excludes it and logs the mismatch (this is exploratory; it does NOT count toward H1/H2).

## 1. Scope (what to build)
A NEW standalone script: `scripts/default_check_h2_additions.py`.

It MUST reuse — with ZERO edits to any existing file — the shared pipeline:
- `scripts/default_check.py` (`run_diagnostic`, `summarize_labels`/per-item CD+resolve math,
  `render_table`, `make_label_run_fn`, the `Roster`),
- `scripts/default_check_frontier.py` (`FRONTIER_ROSTER`, `build_client`, `PROVIDER`,
  `resolve_base_url`, `write_report`-style output helpers, guard helpers).

Do NOT edit `default_check.py` or `default_check_frontier.py` (both merged/reviewed). Do NOT
edit any `bench/*`, `harness/*`, `analysis/*`, `common/schema.py`, or `paper/preregistration/*`
(all FROZEN). Import the frontier module the SAME way it imports default_check (importlib by
path, since `scripts/` is not a package).

### 1.1 Task plane (the ONLY thing that differs from the frontier driver)
Select EXACTLY these 8 tasks from `bench.data_analysis.generate_tasks()` by `.id`:
- `data_geomean_001_k0`,   `data_geomean_001_k1_growth_averaging`
- `data_harmonic_001_k0`,  `data_harmonic_001_k1_speed_averaging`
- `data_cumulative_001_k0`,`data_cumulative_001_k1_cumulative_interpretation`
- `data_tierank_001_k0`,   `data_tierank_001_k1_tie_ranking`

Assign every one `task_role = "h2"`. Raise `KeyError` if any id is missing (guards against a
future rename). The k0 controls are the sanity anchor (no ambiguity → everyone → I0); the k1
variants are the actual H2 test.

### 1.2 Model plane
Use the imported `FRONTIER_ROSTER` unchanged (reasoners gpt-5.6-sol/claude-opus-4.8/
gemini-3.1-pro-preview; weak gpt-4o-mini/gemini-3.5-flash/claude-haiku-4.5/gpt-3.5-turbo;
ρ-baseline gpt-5.4; heterogeneous pool gpt-5.4/claude-sonnet-4.6/gemini-3.1-pro-preview).
`reasoner_sc_excluded_ids` = K_GRADIENT_IDS does not intersect our data_* ids, so all 8 tasks
run in both passes.

### 1.3 Call default_check.run_diagnostic directly
```
tasks, task_role = <the 8 selected tasks, all role "h2">
report = default_check.run_diagnostic(
    client, tasks, task_role,
    checkpoint_path="default_check_h2add_checkpoint.jsonl",
    sc_k=default_check_frontier.SC_K,          # 5
    budget_usd=default_check_frontier.FRONTIER_BUDGET_USD,
    rpm=default_check_frontier.FRONTIER_RPM,
    roster=frontier.FRONTIER_ROSTER,
)
report["roster_name"] = frontier.FRONTIER_ROSTER.name + "_h2add"
```
Use a SEPARATE checkpoint + cache dir (`.llm_cache_default_check_h2add`) so it never collides
with the pilot / frontier / confirmatory checkpoints.

### 1.4 Output
Write, next to the other diagnostic outputs (cwd):
- `default_check_h2add_summary.jsonl` (one row per item + a summary line),
- `default_check_h2add_table.txt` (human-readable, via `default_check.render_table`).
Print the table to stdout. Print a one-line PER-FAMILY verdict for each k1 item:
`FAMILY <family> k1: resolve_rate_to_I0=<x> cd_enumerated=<y> i_perp=<z> -> <RESOLVES|MIS-TAGGED>`
using a documented threshold (see §2).

### 1.5 Guards (offline/CI-safe, identical discipline to the frontier driver)
- `main()` runs LIVE only when `RUN_H2ADD_CHECK=1` AND the proxy is reachable (reuse
  `default_check_frontier.proxy_reachable` / `resolve_probe_url`; honor
  `FRONTIER_SKIP_PROXY_PROBE=1`). Offline → print "skipped", `sys.exit(0)`, NO network.
- Expose a pure `run_h2_additions(client, ...) -> report` so the offline unit test drives it
  against the deterministic mock client (`provider="copilot_proxy"`, `offline=True`) with NO
  network — mirror `default_check_frontier`'s `run_frontier` testability.

## 2. Interpretation threshold (documented, NOT a new frozen metric — diagnostic only)
Per the two-regime finding (rows 51-52), H2_derivable is "resolved by everyone". A family's k1
is CONFIRMED H2 iff, POOLED across the frontier roster (or at minimum across the reasoners),
`resolve_rate_to_I0` is HIGH and `cd_enumerated` (convergent delusion on a foil) is LOW. Use a
transparent, reported cutoff: **RESOLVES if reasoner-class resolve_rate_to_I0 >= 0.5 and
cd_enumerated <= 0.5; else flag MIS-TAGGED for Manager review.** This is a diagnostic screen,
not a pre-registered metric; the Manager makes the final reclassify/exclude ruling and logs it.

## 3. Tests (add to tests/, do NOT modify existing tests)
Add `tests/test_default_check_h2_additions.py`:
- offline: the 8 expected ids are selected, all role "h2", KeyError on a bogus id.
- offline: `run_h2_additions` against the mock client returns a report with 8 item rows and a
  summary; NO network (assert offline path).
- guard: `main()` with `RUN_H2ADD_CHECK` unset prints skip + exits 0.
Reuse existing offline-mock patterns from `tests/test_default_check_frontier.py` (read it first).

## 4. Self-check gate (before marking ready)
- `python -m pip install -e .` then `python -m pytest -q` → full suite green.
- `RUN_H2ADD_CHECK` unset: `python scripts/default_check_h2_additions.py` → prints skip, exit 0.
- Record the sub-agent MODEL FAMILY (Claude) in the PR body for provenance (Law 6).
- Remove any stray root `plan.md`/scratch files before ready.

## 5. Out of scope
- Do NOT run the live check (the Manager runs it after a clean cross-family audit + merge).
- Do NOT change any metric, hypothesis, roster, or frozen file. Do NOT alter H2_TASK_IDS in
  default_check.py (leave the merged driver untouched).
