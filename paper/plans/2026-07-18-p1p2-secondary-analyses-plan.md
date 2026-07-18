# Plan — P1 dependence estimators + P2 abstention detection (Amendment 09 secondaries)

> Manager spec for an IMPLEMENT sub-agent (Claude family). Pre-registered by SIGNED Amendment 09
> (`paper/preregistration/2026-07-18-amendment-09-secondary-analyses-SIGNED.md`) — read it; it is the
> authoritative definition. These are ADDITIVE, POST-HOC SECONDARY analyses; they must change NOTHING
> frozen. Built in parallel with the live confirmatory run (no LLM calls, no budget). Auditor = GPT family.

## 0. Constraints (inviolable)
- Do NOT edit frozen metric MATH: `analysis/cd.py`, `analysis/contrasts.py`, `analysis/decision_rules.py`,
  `analysis/stats.py`, `analysis/nulls.py` (definitions), `harness/metrics.py`, `harness/nulls.py`,
  `common/schema.py`, `bench/*`, `paper/preregistration/*`. Do NOT change the frozen
  `decision_rules._item_level_cells` pooling or the cell key.
- ADD new modules only: `analysis/dependence.py` (P1) and `analysis/abstention.py` (P2), plus tests.
  You MAY read `analysis/io.py` and reuse its tidy loader; if P2 needs the raw `output` column and the
  loader doesn't already expose it, extend the loader ADDITIVELY (new optional column, existing behavior
  and columns byte-identical) — call this out prominently for the auditor.
- Deterministic > LLM-judge (Law 7). NO LLM is invoked anywhere in P1 or P2 (P2 is rule-based).

## 1. P1 — `analysis/dependence.py` (deterministic label statistics)
Operate on the tidy table from `analysis/io.py` (columns incl. task_id, config, model_class, model_id,
seed, label, regime). Respect the FROZEN cell grouping (item × method × model_class × seed) — reuse the
same cell semantics as `decision_rules._item_level_cells`; do NOT invent a new cell key. For each cell's
agent-label multiset compute (all pure functions, unit-tested against golden hand cases):
- `pairwise_wrong_agreement(labels, target)` — among UNORDERED agent pairs that are BOTH wrong
  (label ≠ target and ≠ I_perp), the fraction choosing the SAME wrong enumerated label. Define 0/0 = NaN
  (documented) and handle n<2.
- `cohen_kappa` / `fleiss_kappa(labels_over_agents, interpretation_set)` — chance-corrected agreement
  over the item's interpretation set. Use Fleiss for >2 agents; document the estimand.
- `icc_wrong_indicator(...)` — intraclass correlation of the wrong-interpretation indicator across agents
  within a cell (one-way random effects; document the formula).
- `effective_ensemble_size(n, rho_bar)` = n / (1 + (n−1)·rho_bar), with `rho_bar` the estimated mean
  pairwise correlation of the wrong-indicator. This operationalizes report §2.4 (ρ→1 ⇒ n_eff→1).
- `independence_counterfactual(...)` — resample each agent independently from ITS OWN marginal accuracy
  (per model_id marginal over the run), recompute CD (reuse `analysis.cd.cd_primary` — do NOT reimplement
  it), and return observed − independent with a bootstrap 95% CI (reuse existing bootstrap util in
  `analysis/stats.py` or `analysis/nulls.py` if one exists; otherwise add a small local bootstrap and note
  it). This is DISTINCT from R1b (uniform-over-interpretations): P1 preserves marginal accuracy.
Provide a top-level `compute_dependence_table(tidy, ...)` returning a per-cell (and regime-aggregated)
summary. These SUPPORT `cd_primary`; they do NOT replace it.

## 2. P2 — `analysis/abstention.py` (rule-based, cross-family-ready; NO same-family LLM-judge)
For each AgentRun `output` string, classify ABSTAINED / CLARIFICATION-REQUESTED / flagged-missing-info vs
CONFIDENT-COMMIT, purely by a RULE-BASED detector (regex/keyword grammar over uncertainty and
clarification phrasings — e.g. "cannot determine", "need more information", "which … did you mean",
"ambiguous", "assuming", explicit refusal/abstention, a trailing clarifying question, etc.). Requirements:
- Pure function `detect_abstention(output: str) -> {"abstained": bool, "signal": <category>, "evidence":
  <matched span/rule>}`. Deterministic, transparent, inspectable. NO LLM call. The rule list must be a
  documented, editable constant.
- `abstention_table(tidy_with_output, ...)` → abstention rate by regime (H1_external vs H2_derivable) ×
  model_class. (The silent-failure prediction: LOW abstention on H1_external despite HIGH cd_primary.)
- Provide a hook/interface for a FUTURE cross-family LLM classifier and a HUMAN-validation sample export
  (a function that emits a random sample of (output, rule_verdict) rows to CSV/JSONL for human spot-check),
  but do NOT wire any LLM. Document in the module docstring the A09 guardrail: the classifier MUST be
  rule-based and/or CROSS-FAMILY + human-validated, NEVER a same-family LLM-judge.

## 3. Tests (`tests/test_dependence.py`, `tests/test_abstention.py`)
- P1: golden hand cases for each statistic (e.g. all-agree-wrong → pairwise_wrong_agreement=1.0,
  n_eff→1; all-independent-correct → CD=0; κ chance-correction sanity; independence_counterfactual sign +
  CI on a constructed case). Verify P1 reuses `analysis.cd.cd_primary` (no reimplementation) and the
  frozen cell semantics.
- P2: positive/negative fixtures for each rule category; a confident-wrong output → abstained=False; an
  explicit "I can't determine which X you mean" → abstained=True with the right signal + evidence span;
  determinism (same input → same output).
- Do NOT modify existing tests; if you extend `analysis/io.py` additively, add a test proving existing
  columns/behavior are unchanged.

## 4. Self-check gate (before ready)
- `python -m pip install -e .` then `python -m pytest -q` → FULL suite green (report count).
- Confirm `git diff --stat main...HEAD` touches ONLY: `analysis/dependence.py`, `analysis/abstention.py`,
  the two new test files, and (if unavoidable) an ADDITIVE change to `analysis/io.py`. NO other file.
- Record implementer family = Claude in the PR body (Law 6). Remove any stray root scratch files.
- Commit on the branch with the standard trailer; do NOT push or open a PR (the Manager does).

## 5. Out of scope
No live run, no LLM calls, no human validation (Manager schedules that on real run data), no changes to
primary/frozen definitions, no new primary endpoints, no secondaries beyond P1/P2 (A09 discipline).
