# Phase 1-R — policy_qa reconstruction under target/default reversal (per-slice plan)

> Manager-authored plan (orchestrator-only). Implementer = Claude family, in worktree
> `.worktrees/phase1r-policy_qa` (branch `slice/phase1r-policy_qa`). Auditor = NON-Claude (Hard Law 6).
> Template of record: `bench/code_spec/__init__.py` (merged PR #16). Metric FROZEN.
> **Role: policy_qa is the SECONDARY breadth / cross-domain consistency domain** (structured-answer
> exact-cent match; reported as a consistency check, NEVER as accuracy — prereg §7). It is NOT a primary
> effect-size domain; the executable-gold domains (code_spec, data_analysis) carry H1/H2.

## Why this slice
`policy_qa` on main is still the OLD **target = model's natural default** construction (e.g. overtime I0 =
$950 standard 40h rule = what the model computes = CORRECT ⇒ CD≈0). Reconstruct under the REVERSED
property so the target is a NON-default contract term and the model's default is a WRONG foil.

## Governing decisions (frozen — read first)
- **Amendment 01**: I0 = NON-default true intent; model default = a WRONG foil.
- **Amendment 03**: each convention axis is **BINARY** `{target, default}`; a variant deleting S (|S|=k')
  has EXACTLY `2^k'` interpretations; I0 = all-target; combined-all-default foil marked
  `[combined-default]` in the branch description (build.py appends `__combdef` to the serialized
  gold_check automatically — do NOT hand-append).
- **⭐ Binary-axis ruling (Manager, 2026-07-16, logged):** follow code_spec #16's binary model. The older
  reversal-spec Example B shows a THIRD "flat/no-overtime $900" foil — that illustrative example PREDATES
  Amendment 03 and is SUPERSEDED. Keep every axis strictly `{target, default}` so the `2^k'` invariant
  holds. (Add a third value later only if the empirical default-check shows real convergence dumped to
  I_perp — documented.)
- **Structured-answer contract (prereg §7, frozen):** answers are `{"amount": <float>}` compared
  exact-cent. Keep the existing `StructuredAnswerChecker` (deterministic, NO LLM). The domain's prompts
  must keep instructing agents to emit `FINAL ANSWER: $<amount>` or JSON `{"amount": N}` (the answer-format
  contract from PR #10) — do not break it. Unparseable/ambiguous/conflicting → I_perp (labeler's job).
- Metric FROZEN — do not touch `harness/metrics.py`, `common/schema.py`, or the prereg.

## Required scientific content (I own the design; you implement it faithfully)
All policy_qa reversed traps are **H1_external** (contract/convention terms are external knowledge, not
derivable from the prompt) — set `regime="H1_external"` on every reconstructed FullSpec. Build reversed
families over the existing problem set (overtime, interest, tip, refund, discount), each a genuine
prior-trap where the full latent_spec clearly states the NON-default term and deleting that clause makes
an unaware model default to the standard/population rule (a wrong foil).

### Anchor single-axis (k=1, binary) — overtime contract threshold (REQUIRED)
- `regime="H1_external"`. prompt_core: "An employee worked 45 hours at $20.00/hr base. Compute gross pay,
  rounded to the nearest cent." latent_spec clause (deleted at k=1): "Under this employer's union contract,
  overtime (1.5×) begins after 35 hours per week."
- Axis `overtime_threshold`: **target = OT after 35h** → 35×20 + 10×30 = **$1000.00** (I0);
  **default = standard OT after 40h** → 40×20 + 5×30 = **$950.00** `[combined-default]`,
  `opened_by="overtime_threshold"`.
- key_questions(k1): ["After how many hours/week does overtime begin (the contract threshold)?"]

### Additional single-axis binary reversed families (build several for breadth)
Reconstruct the other problems as reversed binary-axis traps with a clearly-stated non-default term and a
standard-default wrong foil. For each, pick a natural non-default contract convention (e.g. interest:
target = 365-day exact-day simple interest per contract vs default 360-day banker's; tip: target = tip on
PRE-tax subtotal per house policy vs default on post-tax total; refund/discount: an explicitly stated
non-standard order-of-operations or basis). Each axis strictly `{target, default}`, exact-cent
distinguishable, fair (a human agrees the full spec genuinely specifies the non-default).

### At least one MULTI-AXIS H1_external family (k=2, 4 interps)
Stack two GENUINELY INDEPENDENT external policy conventions on one calculation (deleting one must not
change the other's amount — verify independence). Emit k0 (control), both k1 variants, and k2_all (4
interps incl. the marked combined-default). Example candidate: overtime-threshold axis (35h vs 40h)
stacked with a tip/rounding or pre-tax-basis axis on the same pay/bill calculation — only if the two are
truly independent. If no clean independent pair exists, flag it in plan.md rather than forcing interaction.

## Structural invariants (enforced by build.py + validate.py + tests)
- Per variant deleting S (|S|=k'): `len(key_questions)==k'`, `len(interpretations)==2^k'`, one
  `is_target=True` (I0), one `[combined-default]` marker, 100% distinguishable via exact-cent gold.
- k0 control: empty key_questions, single interp, prompt == latent_spec.
- Every non-target declares `opened_by`. Set `regime="H1_external"` on every FullSpec.

## Deliverables
1. Rewrite `bench/policy_qa/__init__.py` FullSpecs to the reversed binary-axis combinatorial model with
   `regime` tags; update gold expected-amounts + reference answers; keep `StructuredAnswerChecker` and the
   per-domain answer-format instruction intact.
2. Regenerate `bench/data/policy_qa.jsonl` via `python bench/policy_qa/__init__.py`.
3. Update `tests/test_policy_qa.py` to assert the reversed invariants (mirror `tests/test_code_spec.py`):
   per-variant `len(key_questions)==k'`, `len(interpretations)==2^k'`, one target, combined-default marker,
   regime set, 100% distinguishability; golden test pinning I0/default amounts (e.g. $1000 vs $950).
4. `python -m bench.validate --domain policy_qa` → 100% distinguishable.
5. `python -m pytest -q` → full suite green.

## Provenance / process
- Record model FAMILY in the PR body + keep the `# constructed by: Claude (Anthropic) family` header.
  Commit in the worktree; push `slice/phase1r-policy_qa`. Manager opens the PR, spawns a NON-Claude
  cross-family audit, routes fixes, merges after the Law-4 gate. Call out the benchmark (science) change
  in the PR body. Self-check gate before ready: full pytest green + validate 100% + invariants + fairness.
- Do NOT edit the main checkout, harness/metrics.py, common/schema.py, or the prereg.

Commit trailer: `Co-authored-by: copilot <copilot@users.noreply.github.com>`.
