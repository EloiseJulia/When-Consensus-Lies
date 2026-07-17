# Phase 6 — analysis pipeline v1 (offline scaffolding) — per-slice plan

> Manager plan. Implementer = Claude, worktree `.worktrees/phase6-analysis` (branch `slice/phase6-analysis`).
> Auditor = NON-Claude (GPT). OFFLINE, deps already present (numpy/scipy/statsmodels/pandas; NO matplotlib —
> produce figure-DATA, defer rendering). Implements signed **Amendment 04** (I_perp treatment) + FROZEN
> prereg §8 (analysis) + §9 (decision rules) + the row-35 cross-model / fake-redundancy framing. Build
> against SYNTHETIC data now; real data arrives from the registered run. **Do NOT modify harness/metrics.py,
> common/schema.py, or paper/preregistration/ (frozen).** The A04 PRIMARY CD is an ANALYSIS-LAYER function,
> NOT a change to the frozen `false_consensus_rate`.

## Deliverable 1 — `analysis/cd.py` — Amendment-04 CD computations (golden-tested, the crux)
Given a list of per-item agent interpretation labels + the target label:
- `cd_primary(labels, target)` — modal-wrong over ENUMERATED wrong labels ONLY; `I_perp` stays in the
  denominator N=len(labels) but is INELIGIBLE to be the convergent (modal-wrong) label. (A04 PRIMARY.)
- `cd_sensitivity_frozen(labels, target)` — MUST call `harness.metrics.false_consensus_rate` (I_perp
  eligible). (A04 SENSITIVITY A; pins to the frozen metric — import, do not reimplement.)
- `cd_sensitivity_drop_iperp(labels, target)` — drop `I_perp` agents from N, then modal-wrong share among
  the remaining. (A04 SENSITIVITY B.)
- `iperp_rate(labels)` — fraction of agents = `I_perp`. (A04 DIAGNOSTIC.)
- GOLDEN test (mirror the diagnostic's crafted case): `["I1","I1","I_perp","I_perp","I_perp"]`, target
  `"I0"` → frozen 0.60, primary 0.40, drop_iperp = 1.0 (I1 2/2 among 2 parseable), iperp_rate 0.60. Add
  more crafted cases (all-correct→0; all-I_perp→primary 0 & frozen 1.0 & fires nothing; partial-default
  combos count as enumerated per Amdt 03).

## Deliverable 2 — `analysis/contrasts.py` — the pre-registered comparisons
Operating on a tidy per-(item×config×model_class×seed) table of labels/correctness/CD:
- `aggregation_vs_single(...)` — CD difference: each aggregation method (SC k5/k10, homogeneous-MAD,
  heterogeneous-MAD, verifier) vs single (H1a input), on `H1_external` items, pooled over executable-gold
  domains. Return per-method deltas.
- `cross_model_vs_homogeneous(...)` — ⭐ row-35 framing: CD in the HETEROGENEOUS (cross-family) condition
  vs the HOMOGENEOUS/SC condition. (Homogeneous ≈ ρ→1 fake-redundancy; cross-model = genuine convergent
  delusion.) Report both; this is the headline contrast.
- `cd_by_regime(...)` — H1_external vs H2_derivable CD, by model_class (for the H2 `regime × model_class`
  interaction).
- `cd_vs_k(...)` — CD as a function of ambiguity level k (H1b), per model_class/method.
- Each computed with all THREE A04 CD variants (primary + both sensitivities) + the I_perp rate, so every
  contrast is reported per A04.

## Deliverable 3 — `analysis/stats.py` — implement the two stubs (§8)
- `fit_mixed_effects_model(data, formula)` — statsmodels mixed-effects logistic
  (`correct ~ regime * ambiguity_k * method * model_class` with random intercepts by task and by model);
  also support the item-level `cd`-outcome model. Return coefficients, CIs, p-values in a dict. Handle
  small/degenerate data gracefully (return a clear status, don't crash).
- `bootstrap_confidence_intervals(metric_fn, data, n_bootstrap=1000, cluster=...)` — item- AND
  model-clustered bootstrap (resample clusters, recompute metric); return (point, lo, hi) at 95%.

## Deliverable 4 — `analysis/decision_rules.py` — §9 support/refute helpers
Given the fitted contrasts + bootstrap CIs, evaluate the FROZEN §9 rules and return SUPPORTED / REFUTED /
INCONCLUSIVE per hypothesis: H1a (aggregation-vs-single CI not < 0), H1b (k coefficient > 0, CI excludes
0), H2 (`regime × model_class` interaction CI excludes 0 AND reasoner H2 CD not > single baseline), R1
(CD_real − CD_shuffled CI > 0 — wire to `harness/nulls.py`), R2 (cross-family effect CI excludes 0). Do
NOT hard-code outcomes; compute from inputs. Evaluate on the A04 PRIMARY treatment; also report under
SENSITIVITY A/B (row-26/A04: if PRIMARY and sensitivities agree in sign → robust; else report divergence).

## Deliverable 5 — `analysis/figure_data.py` — figure DATA (no matplotlib)
Produce the structured tables/arrays behind the frozen figure intents (§8): the ρ–ambiguity phase-diagram
table (CD by method × k × regime), the method×ambiguity silent-failure heatmap table, per-regime CD, and
CD-vs-k. Emit as pandas DataFrames / JSON. (Rendering with matplotlib is a LATER slice — matplotlib is not
installed; do NOT add it now.)

## Tests — `tests/test_analysis_cd.py`, `tests/test_analysis_stats.py`, `tests/test_analysis_contrasts.py`
- GOLDEN A04 CD values (Deliverable 1) — exact.
- Mixed-effects fit on SYNTHETIC data with a KNOWN injected effect (e.g. CD rises with k) → coefficient
  sign/CI recovered.
- Bootstrap CI covers a known metric on synthetic data; clustering respected.
- Contrasts on synthetic tables return the expected deltas; decision_rules returns SUPPORTED/REFUTED on
  crafted inputs where the answer is known.
- ALL OFFLINE (no network/token). `python -m pytest -q` fully green.

## Constraints / process
- No frozen-file changes; `cd_sensitivity_frozen` must import + call `harness.metrics.false_consensus_rate`
  (proves the frozen metric is the sensitivity anchor). Deterministic tests > review for the CD math
  (Hard Law 7). Record model family (Claude) in headers. Commit in the worktree (co-author trailer), push
  `slice/phase6-analysis`. Manager opens PR + spawns a NON-Claude GPT audit (verify A04 CD math against the
  golden cases; §8/§9 correctness; no frozen-file change; tests non-tautological), merges after Law-4 gate.
- Do NOT add matplotlib or any new dependency. Do NOT run live models. This is offline scaffolding against
  synthetic data — real data comes from the registered run (owner-gated).
