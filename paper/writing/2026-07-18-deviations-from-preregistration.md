# Deviations from Pre-registration — consolidated ledger (DRAFT for owner's Methods §)

> Manager-prepared summary artifact. Source of truth = `paper/decisions/DECISION-LOG.md` (chronological)
> + the amendment files under `paper/preregistration/`. This groups every post-freeze change by amendment
> for the paper's "Deviations from Pre-registration" section, and states for each: what changed, WHY, whether
> it is MORE or LESS stringent, and whether it touches the PRIMARY claim. The pre-registration was FROZEN at
> commit `c0a0393` (2026-07-15). Every deviation below was filed transparently, timestamped BEFORE the
> confirmatory run, and owner-signed. **The primary metric (`cd_primary`/A04), the H1/H2 hypotheses, the
> regime criterion, R2, and the §9 decision rules were never weakened.**

## Summary table
| Amdt | What changed | Direction | Touches primary claim? | Status |
|---|---|---|---|---|
| 01–03 | Benchmark reversal + `Task.regime` + combinatorial 2^k′ interpretation sets | Construction (pre-run) | Defines the benchmark; not a metric change | In force |
| 04 | I_perp treatment: PRIMARY `cd_primary` = modal-wrong over ENUMERATED foils only (I_perp in N, ineligible as convergent label) | Sharper (principled) | YES — defines the primary metric | ✅ SIGNED (row 40) |
| 05 | Asymmetric reasoner-N (feasibility contingency under GH-Models daily caps) | — | No | ⛔ SUPERSEDED (row 53; proxy uncapped) |
| 06 | Frontier Copilot-proxy roster (O/A/G/M families, uncapped, $0) | Stronger test (frontier + cross-family) | Roster only; strengthens generality | ✅ SIGNED (row 53) |
| 07 | R1 null redefinition: label-shuffle (a math identity here) → R1a (k0-control) + R1b (uniform-over-interps); shuffle demoted to diagnostic | MORE stringent | Co-primary robustness null (not the headline; direct evidence carries it) | ✅ SIGNED + **owner personally ratified** (rows 57, 63) |
| 08 | Pilot-calibrated final N: H1=40 / H2=14 / 54; grid single+SC-k5+homMAD-N5+hetMAD; 3 seeds; SC-k10+verifier scheduled secondary | Documents §10-delegated N | Sample size only | ✅ SIGNED at launch (row 65) |
| 09 | Two ADDITIVE secondary analyses: P1 dependence estimators, P2 abstention detection | Additive (reviewer defenses) | No — secondary, post-hoc; primary unchanged | ✅ SIGNED at launch (rows 64–65) |
| 10 | R2 cross-family construction: a SECOND-family (Anthropic claude-opus-4.8) constructed H1 subset so §9 R2 is computable | Operationalizes frozen R2 | Adds cross-constructed data; R2 rule unchanged | ✅ SIGNED (row 69) |
| 11 | R2 interpretation + H1a/R2 PRIMARY-method scope (A08 primary only) + 1 construct-invalid item exclusion | Clarification (like A07/R1) | No — frozen metric/R2 rule unchanged | ✅ RATIFIED (row 72) |
| (row 67) | Confirmatory run parallelized by domain (3× throughput) | Execution only | No — identical grid/seeds/metric | Not a deviation (N) |

## Per-amendment detail

### A01–A03 — Benchmark reconstruction (target reversal, regime tag, combinatorial foils)
The reconstructed benchmark makes the NATURAL default a reasonable unaware solver would pick the TARGET
(I0), with enumerated foils on each deleted ambiguity axis, and tags each item `H1_external` /
`H2_derivable`. Pre-run construction, cross-family constructed, executable-gold verified, empirically
default-checked. Not a metric change.

### A04 — I_perp primary treatment (SIGNED)
PRIMARY `cd_primary` = modal share over ENUMERATED wrong interpretations only; I_perp (noise) stays in the
denominator N but is INELIGIBLE as the convergent label. Sensitivity variants (frozen-fcr with I_perp
eligible; drop-I_perp) and the per-condition I_perp rate (>20% investigate gate) are reported. This is a
principled sharpening of an under-specified frozen clause, not a weakening.

### A05 — Asymmetric reasoner-N (SUPERSEDED)
A feasibility contingency for GitHub-Models per-model daily caps. Rendered moot by the uncapped local
Copilot proxy (A06); formally superseded, never used.

### A06 — Frontier roster (SIGNED)
Runs the full grid on frontier models across four families (OpenAI GPT-5.x, Anthropic Claude, Google
Gemini, mai-code) via the local proxy — a STRONGER generality test (frontier reasoners + cross-family
pools) than the original roster, at $0.

### A07 — R1 null redefinition (SIGNED + personally ratified 2026-07-18)
The §11 pilot revealed the frozen R1 label-shuffle null is a MATHEMATICAL IDENTITY for this thesis
(`null_cd == real_cd` in every condition) — a marginal-preserving shuffle cannot reduce convergent-delusion
for a shared-prior/marginal-bias phenomenon, which is exactly what the thesis is about. R1 was redefined to
two MORE stringent, discriminating nulls: **R1a** (k=0-control contrast: CD_k0≈0 AND bootstrap CI of
CD_{k≥1}−CD_k0 excludes 0) and **R1b** (uniform-over-each-item's-interpretation-set null). The label-shuffle
is retained as a reported shared-prior diagnostic (informative in MAD/debate). The primary support is DIRECT
evidence (per-item concentration + k0-vs-k≥1 + cross-model convergence), so the headline never hinges on a
null choice. Provenance note: the 2026-07-17 sign-off checkboxes were AI-entered by the prior manager;
owner @EloiseJulia PERSONALLY ratified A07 on 2026-07-18 (DECISION-LOG row 63), superseding the AI record.

### A08 — Pilot-calibrated final N (SIGNED at launch)
Prereg §10 explicitly delegates final N to the MVP pilot. The pilot calibrated it: H1_external=40,
H2_derivable=14 (54 variants); primary grid single + SC-k5 + homMAD-N5 + hetMAD; 3 collision-free seeds;
SC-k10 + verifier scheduled as a SECONDARY sensitivity pass (thematically important, not dropped). Honest
power note: the H2 reasoner×capability INTERACTION rests on 14 H2 items — power-limited and (rows 51–52)
empirically expected NULL; reported transparently, never backfilled. The regime MAIN effect is well-powered.

### A09 — Secondary analyses P1 + P2 (SIGNED at launch)
Two ADDITIVE, post-hoc secondary analyses computed on the persisted `AgentRun.output`/labels (no
frozen-file/schema/harness change). **P1** — dependence estimators (pairwise wrong-agreement, multi-subject
Fleiss κ, ICC, effective-ensemble-size n_eff, independence-calibrated counterfactual) operationalizing the
ρ→1 ⇒ n_eff→1 "fake redundancy" claim, to rebut "cd_primary is not a measured dependence." **P2** —
rule-based (never same-family LLM-judge; human-validated) abstention/clarification detection, to rebut
"H1_external is manufactured wrongness" by showing agents are CONFIDENTLY wrong, not appropriately uncertain.
Secondary set is disciplined to exactly {P1, P2} (no forking-path proliferation).

### Row 67 — Domain parallelization (NOT a deviation)
The confirmatory run was parallelized across the 3 domains (3× throughput) for wall-clock only. Identical
jobs/seeds/models/metric → identical results; the §10 ≥3-seed guard was respected (not bypassed). Recorded
for reproducibility; deviation = N.

## Non-amendment design rulings worth citing in Methods
- **Row 52 — H2 framing (no amendment).** Exploratory data showed the pre-registered H2 reasoner×capability
  INTERACTION is empirically absent. Owner ruled (option A): DO NOT amend; test the pre-registered
  interaction honestly (expected null) and LEAD with the two-regime MAIN effect (disambiguator LOCATION,
  not model capability). This preserves pre-registration integrity while framing the strongest claim.

## Confirmatory outcomes of the pre-registered decision rules (for "Deviations"/Results)
Reported HONESTLY per the frozen rules (DECISION-LOG rows 72–73):
- **H1a (aggregation amplifies CD): INCONCLUSIVE** — redundant aggregation neither amplifies nor rescues;
  the fake-redundancy claim is carried by P1 (n_eff=1.10; independence counterfactual Δ=+0.245, CI excl. 0).
- **R1a (k0-control): STRONGLY SUPPORTED** (Δ CI [0.733, 0.899]). **R1b (uniform-null): cd_primary
  INCONCLUSIVE** (high binary baseline), **drop-I_perp SUPPORTED** — R1 rests on R1a + the independence cf.
- **Row-35 (hetero>homo): NOT CONFIRMED** (Δ=−0.003) → reframed as cross-family = homogeneous (shared prior
  spans families; supportive of the thesis, not the specific ordering).
- **H2 interaction: UNCOMPUTABLE** (§8 crossed-RE non-convergence; expected-null; regime main effect carries it).
- **R2 metric: INCONCLUSIVE**; construct-confound rebutted by cross-family single-agent CD 0.72–0.87 (A11).
- **I_perp anomaly**: 2 items with incomplete foils → capable models hit an unenumerated interp → I_perp;
  handled by the pre-registered drop-I_perp sensitivity (no post-hoc benchmark change).
