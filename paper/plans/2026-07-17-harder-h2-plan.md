# Harder H2 demonstrators (frontier-calibrated) + genuinely-weak tier — per-slice plan (2026-07-17)

> Owner ruling (2026-07-17): the median-skew H2 demonstrator is resolved by ALL frontier models (reasoner +
> weak), collapsing the reasoner-vs-weak H2 interaction. Do BOTH: (1) add a genuinely-weak model
> (gpt-3.5-turbo, on the proxy) to the frontier weak class; (2) design 1-2 HARDER H2_derivable demonstrators
> that split frontier REASONERS (resolve) from frontier-WEAK (default wrong). Implementer = Claude (worktree
> slice/harder-h2). Auditor = NON-Claude (GPT). Metric/schema/prereg FROZEN. This preserves the
> pre-registered H2 `regime × model_class` interaction; empirical default-check is the final arbiter.

## H2 design property (what makes a HARDER derivable trap)
An H2_derivable item: the disambiguator is PRESENT in the prompt/data (a strong reasoner CAN recover I0),
but the derivation is SUBTLE enough that weaker models default to a naive foil. I0 = the derivable-correct
interpretation; the default foil = the naive answer a weak model produces. regime = H2_derivable. Reversed +
executable-gold + 100% distinguishable + fair (a human reading the full spec / data agrees I0 is intended
and derivable). The median-skew was too OBVIOUS (visible outlier → median); the new ones must require a
genuine reasoning step that frontier-weak models skip.

## Required: 2 candidate harder-H2 demonstrators (data_analysis, executable gold, regime=H2_derivable)
Build in `bench/data_analysis` (the executable-gold H2 domain) as reversed H2 families. Concrete candidates
(build BOTH; the live default-check will confirm which actually split):
1. **Quantity-weighted average** (strong candidate): a table of (item, quantity, unit_price). Prompt asks
   for "the average price". I0 (derivable-correct, target) = the QUANTITY-WEIGHTED average (weights are the
   quantities, PRESENT in the data → derivable); default foil = the naive simple mean of the unit_price
   column. A reasoner recognizes it should weight by quantity; a weak model averages the price column.
   Executable gold: exact weighted avg vs simple mean (distinct values). k=1 single axis (target=weighted,
   default=simple).
2. **Unequal-interval rate of change** (or a second subtle derivable task you justify): time points with
   UNEQUAL gaps + a value series. Prompt: "the average rate of change per unit time". I0 (derivable) =
   total change / total elapsed time (accounts for the unequal intervals present in the data); default foil
   = the naive mean of per-step deltas (ignores unequal spacing). Reasoner accounts for spacing; weak
   averages the steps. Executable gold: exact. (Or propose an equally-good subtle-derivable alternative —
   e.g. a base-rate/percentage-base task where the base is derivable from context — and justify why it is
   H2-derivable, not H1-external.)

For EACH: reversed (I0=derivable-correct non-default; default=naive foil), regime="H2_derivable",
executable-gold 100% distinguishable, fair, per-variant invariants (Amdt 03 binary-axis), combined-default
marker. Document WHY the disambiguator is PRESENT/derivable (so it is H2, not H1) and WHY a weak model
would default to the foil (the split hypothesis). Add golden tests pinning I0/default values.

## Also: add the genuinely-weak tier to the frontier driver
In `scripts/default_check_frontier.py`: add **gpt-3.5-turbo** to the FRONTIER weak class (weak =
[claude-haiku-4.5, gemini-3.5-flash, gpt-4o-mini, gpt-3.5-turbo]). Keep everything else (roster, provider,
checkpoint, code_invoice exclusion, offline guard). Update the offline test for the new weak slug. Make
sure the new harder-H2 tasks are INCLUDED in the frontier default-check task set (both the sc homogeneous
pass and the heterogeneous pass) so the reasoner-vs-weak split is measurable.

## Verify + process
- `python -m bench.validate --domain data_analysis` → 100% distinguishable (incl. the new H2 families).
- `python -m pytest -q` → whole suite green (golden tests for the new H2 values; frontier-driver test updated).
- Cross-family (GPT) audit: H2 fairness + regime=H2_derivable correctness (disambiguator genuinely PRESENT/
  derivable, NOT external) + distinguishability + the split hypothesis is plausible; driver weak-tier change.
- Do NOT run live (the Manager re-runs the frontier default-check to EMPIRICALLY confirm the split:
  reasoners resolve I0, weak incl. gpt-3.5-turbo default to the foil). If a new H2 task does NOT split
  empirically, we iterate (design is hypothesis; empirical default-check is the arbiter).
- Do NOT touch harness/metrics.py, common/schema.py, paper/preregistration/.

## Provenance
Implementer records Claude family. Commit in the worktree (co-author trailer); push slice/harder-h2. Manager
opens PR + spawns the NON-Claude audit + merges after the Law-4 gate, then RE-RUNS the frontier default-check
to confirm the H2 split.
