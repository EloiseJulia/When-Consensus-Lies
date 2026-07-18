# Plan — R2 cross-family construction subset (Amendment 10, SIGNED)

> Manager spec for a CONSTRUCTION sub-agent running ON claude-opus-4.8 (so the items are literally
> Anthropic-family-constructed = `constructor_family="anthropic/claude-opus-4.8"`). Implements SIGNED
> Amendment 10. Audit = GPT (cross-family, Law 6). Runs in a worktree; the Manager runs the R2 partition
> after merge. This is ADDITIVE (new bench module + additive plumbing); nothing frozen changes.

## Deliverables
1. NEW `bench/r2_xf/__init__.py` — `generate_tasks()` returns ~9–12 **H1_external** items across the 3
   domain flavors (code/policy/data), each with a deterministic executable-gold `check()`, unique-I0
   fairness, `regime="H1_external"`, k∈{0,1} (k0 control + k1 trap), task_id prefixed `r2xf_`. Mirror an
   existing domain module (bench/code_spec, bench/policy_qa, bench/data_analysis) for structure/gold/foils.
2. Register the domain: add `"r2_xf"` to `_DOMAIN_LOADERS` in `scripts/registered_run.py` (do NOT add it to
   `_ALL_DOMAIN_NAMES` — it is run explicitly via `--domains r2_xf`, never in the default confirmatory grid).
   Wire it into `bench.validate` domain discovery the same way the 3 domains are.
3. `constructor_family` plumbing (additive, NO schema.py edit): in `analysis/io.py`, derive a
   `constructor_family` tidy column from task_id — prefix `r2xf_` → `"anthropic/claude-opus-4.8"`, everything
   else → `"mai-code"` — so `decision_rules.CONSTRUCTOR_COL` is populated for R2. Keep existing columns/
   behavior byte-identical (gate behind the same additive path; default callers unaffected).
4. Tests `tests/test_r2_xf.py` + a constructor_family plumbing test.

## H1_external item design constraints (CRITICAL — build valid items)
- **H1_external** = the disambiguating fact requires OUTSIDE knowledge NOT in the retained prompt. The
  NATURAL DEFAULT interpretation I0 is what a reasonable UNAWARE solver picks, and it MUST SURVIVE deletion
  of the disambiguating clause (deleting it leaves I0 as the default).
- Use **"which-convention" axes with a natural default** (e.g. language/format/domain-standard default).
  AVOID fee/cap/restriction/threshold axes (they have NO default when the clause is deleted).
- I0 (target) = the natural default; each foil deviates on EXACTLY ONE axis. `key_questions` = EXACTLY the
  deleted axes; k0 → `key_questions` empty; invariant `len(key_questions)==ambiguity_level==len(interpretations)-1`.
- Deterministic executable-gold `check()`; I0 uniquely identifiable; enumerated foils; cross-family-fair
  (not tuned to any one tested family).
- These are H1 (external disambiguator) — UNLIKE H2 they must NOT be resolvable from the retained prompt.

## Constraints
- Constructor = claude-opus-4.8 (this agent designs the item semantics). Do NOT edit frozen files:
  `common/schema.py`, `harness/metrics.py`, `harness/nulls.py` defs, existing `bench/*` items, and the
  metric math in `analysis/cd.py|contrasts.py|decision_rules.py|stats.py|nulls.py`. `analysis/io.py` and
  `scripts/registered_run.py` changes must be ADDITIVE.
- Self-check: `python -m pip install -e . && python -m pytest -q` green; `python -m bench.validate --domain
  r2_xf` → 100% distinguishable; a dry-run `python scripts/registered_run.py --dry-run --domains r2_xf
  --seeds 0 1000 2000` enumerates the R2 grid.

## After merge (Manager)
Run the R2 partition live (`RUNNER_LIVE=1 ... --domains r2_xf --seeds 0 1000 2000`, $0), then Phase-6
`decision_rules.evaluate_r2` on the cross-family (non-Anthropic tested) cells.
