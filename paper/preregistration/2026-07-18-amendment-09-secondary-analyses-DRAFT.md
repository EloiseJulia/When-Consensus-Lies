# Pre-Registration Amendment 09 — Secondary analyses: dependence estimators (P1) + abstention detection (P2)

> Adds TWO pre-registered SECONDARY analyses to the confirmatory run, motivated by the R5 novelty audit
> (`paper/research/2026-07-18-R5-novelty-positioning.md`, exposure risks #2 and #3). Both are ADDITIVE and
> computed POST-HOC on the persisted `AgentRun.output` + labels — they change NOTHING frozen: the PRIMARY
> metric (`cd_primary`/A04), the hypotheses, the regime criterion, R2, the §9 decision rules, and R1 (as
> personally-ratified Amendment 07) are all UNCHANGED. These are secondary/supporting analyses, NOT new
> primary endpoints. **STATUS: DRAFT — owner signs at LAUNCH (with A08).** Owner approved the content
> 2026-07-18; discipline: keep secondaries to EXACTLY these two (no forking-path proliferation).

## 0. Why (reviewer pre-empt)
The R5 related-work audit narrows our defensible novelty and flags two near-necessary methodological
defenses:
- **(risk #3, HIGH)** "`cd_primary` is a renamed wrong-answer agreement statistic; ρ→1 is never actually
  measured." Methods reviewers will demand a mapping onto classical dependence language.
- **(risk #2, VERY HIGH)** "`H1_external` items are epistemically impossible → the benchmark manufactures
  wrongness." The "SILENT" claim requires showing agents were CONFIDENTLY wrong (did not abstain / ask to
  clarify), not appropriately uncertain.

## 1. P1 — Direct dependence estimators (SECONDARY, deterministic)
Computed additively on the labels {L_i} per (item × config × model_class × seed) cell (the frozen
`decision_rules._item_level_cells` pooling is respected; no change to the cell key). All are deterministic
label statistics (no LLM in the loop):
- **Pairwise wrong-answer agreement:** among agent pairs that are BOTH wrong, the rate they chose the SAME
  wrong interpretation.
- **Chance-corrected agreement (Cohen's/Fleiss' κ)** over the interpretation set, to discount agreement
  expected from skewed marginals.
- **Intraclass correlation (ICC)** of the wrong-interpretation indicator across agents within a cell.
- **Effective ensemble size** n_eff = n / (1 + (n−1)ρ̄) using the estimated mean pairwise correlation ρ̄ —
  directly operationalizing the report §2.4 "ρ→1 ⇒ n_eff→1 fake redundancy" thesis.
- **Independence-calibrated counterfactual:** resample each agent independently from ITS OWN marginal
  accuracy distribution, recompute CD, and report observed−independent (bootstrap CI). Distinct from R1b
  (uniform-over-interpretations): P1 preserves each model's marginal accuracy.
These SUPPORT, and are reported alongside, the primary `cd_primary`; they do NOT replace it. `marginal_rho`
(already in the pipeline) is the partial bridge these extend.

## 2. P2 — Abstention / clarification-request detection (SECONDARY, post-hoc)
For each `AgentRun`, classify whether the agent ABSTAINED or REQUESTED CLARIFICATION / flagged missing
information (vs. confidently committing to an interpretation), extracted POST-HOC from the persisted
`AgentRun.output` (no run-time change, no schema edit).
- **⭐ Provenance guardrail (owner-required, inviolable):** the abstention/clarification classifier MUST
  NOT be a SAME-FAMILY LLM-judge (shared-blind-spot / provenance risk, Law 6). Use a RULE-BASED detector
  (regex/keyword grammar over clarification/uncertainty phrasings) and/or a CROSS-FAMILY classifier,
  VALIDATED against a HUMAN-spot-checked sample (report agreement / a small confusion matrix). Executable/
  deterministic > LLM-judge (Law 7).
- **Report:** abstention rate by regime (H1_external vs H2_derivable) × model_class. The silent-failure
  claim predicts LOW abstention on H1_external despite high CD (confidently wrong), and that P2 does not
  merely track CD.

## 3. What stays FROZEN / UNCHANGED
`cd_primary` + all A04 CD variants, H1/H2 hypotheses, the regime criterion, R2, the §9 decision rules,
R1 (A07 R1a+R1b), `harness/metrics.py`, `harness/nulls.py` definitions, `common/schema.py`, the benchmark.
P1/P2 add ONLY non-frozen, secondary, post-hoc computations. No primary endpoint is added or changed.

## 4. Discipline (no forking paths)
The confirmatory secondary-analysis set is EXACTLY {P1, P2} (plus the already-registered R1a/R1b, R2, and
the A04 sensitivity variants). No further post-hoc secondaries will be added to chase significance.

## 5. Sign-off (at LAUNCH, with A08)
- [ ] Owner confirms P1 (dependence estimators) + P2 (abstention detection, rule-based/cross-family +
      human-validated, NOT same-family LLM-judge) as pre-registered SECONDARY analyses.
- [ ] Owner acknowledges these are additive/post-hoc and change nothing frozen.

Amendment status: **DRAFT — owner signs at launch (with A08).** Content approved by owner 2026-07-18.
See DECISION-LOG.
