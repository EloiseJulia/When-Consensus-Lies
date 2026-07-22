# Pre-Registration Amendment 12 — Exploratory diversified-evidence conditions (RATIFIED)

> **STATUS: RATIFIED by owner @EloiseJulia (2026-07-22).** The owner personally approved the two exploratory
> conditions (C5, C7), their pre-committed prompts/roles/predictions, the anti-leakage guarantee, and their
> EXPLORATORY (never-confirmatory) reporting. Design implementation + cross-family audit proceed; a SEPARATE
> owner GO is required immediately before the live run (per the owner's instruction to "confirm once more
> before launch"). The AI Manager did NOT self-sign owner.

## 0. Purpose & scope
Registers two NEW, **post-hoc EXPLORATORY** computational conditions added AFTER the confirmatory run, to
test the paper's constructive design principle ("diversify evidence and interpretations, not merely model
providers"). Owner chose Option B (2026-07-22). Full mechanics: `paper/plans/2026-07-22-phaseB-diversified-
conditions-design.md`. This amendment exists so the "Deviations from Pre-registration" section can state
transparently that these conditions are exploratory, pre-committed, and additive.

**This amendment changes NO frozen definition.** Same `cd_primary`/A04 metric, same abstention detector,
same H1_external/H2_derivable item sets, same seeds, same decision-rule machinery. It does not touch the
confirmatory hypotheses, results, or numbers.

## 1. The two exploratory conditions (pre-committed BEFORE running)
- **C5 `cross-vendor-synthesis`** — cross-family pool answers the same prompt independently; a synthesizer
  (`microsoft/mai-code-1-flash-picker`, outside the tested pool) merges into one final answer. Generic
  synthesis prompt, no gold/target/foil reference.
- **C7 `role-diversified`** — five cross-family agents with DISTINCT GENERIC epistemic roles
  (solve / find-missing-info / propose-alternatives / check-defaults / integrate-without-treating-
  agreement-as-correctness). Role prompts are generic epistemic scaffolding ONLY.

Exact prompts, model/family/role/seed assignments, and the labeler binding are frozen in the design spec §2.

## 2. Anti-leakage guarantee (construct validity)
No C5/C7 prompt may reference the target interpretation, the deleted convention/axis, the enumerated foils,
`interp.id`, `gold_check`, or `is_target` — mirroring why the confirmatory `interpretation-diverse` method
was restricted out of the PRIMARY set (A11). All agents share the SAME underspecified prompt boundary as the
confirmatory `single`/`heterogeneous` conditions; only ROLES (not inputs) are diversified.

## 3. Pre-committed directional predictions (registered before the run)
- **P-B1 (synthesis does not help):** `cd_primary(cross-vendor-synthesis)` is NOT meaningfully below
  `cd_primary(heterogeneous-MAD)` on the frozen H1_external items (Δ CI overlaps 0 or positive); abstention
  ≈ 0. → synthesis interfaces may manufacture confident shared error.
- **P-B2 (role diversification helps):** `cd_primary(role-diversified)` is BELOW
  `cd_primary(heterogeneous-MAD)` on H1_external, and/or clarification/abstention is substantially higher —
  achieved with GENERIC scaffolding only.
- Item-level bootstrap CIs (R1a/R1b machinery). **Any outcome, including nulls, is reported honestly and
  never relabeled confirmatory.** A P-B2 null strengthens the "information-boundary dominates aggregation-
  recipe" thesis.

## 4. Comparison & analysis
Baseline = the confirmatory `heterogeneous-MAD` ("cross-vendor comparison") on the SAME 40 H1_external items
(already collected). H2_derivable (14 items) is a control (interventions must not break the resolved regime).
Metric = frozen `cd_primary`/A04 (I_perp-eligible + drop-I_perp sensitivities) + frozen abstention detector.
3 frozen collision-free seeds. Reported in a clearly labeled EXPLORATORY subsection, separate from the
confirmatory Results.

## 5. What stays FROZEN
`cd_primary` + A04 CD variants, H1/H2 hypotheses, the regime criterion, R1 (A07) + R2 (A11) nulls, the §9
decision rules, and the confirmatory item set / config grid / results. This amendment adds exploratory
conditions and pre-commits their design; it fixes nothing about the confirmatory study and chases no
significance. Implementation is ADDITIVE (new driver + module, separate checkpoint/cache); no frozen file is
edited.

## 6. Ratification (owner-personal — REQUIRED before any run)
- [x] Owner @EloiseJulia personally ratifies the two exploratory conditions (C5, C7), their pre-committed
      prompts/roles/predictions (design spec §2–§3), the anti-leakage guarantee (§2 here), and that they are
      reported as EXPLORATORY, never confirmatory. — DATE: 2026-07-22 (owner selection: "批准 Amendment 12")
- [x] Owner acknowledges the run is $0 (local proxy) and additive (no frozen file / no confirmatory
      checkpoint touched). — DATE: 2026-07-22
- [x] SEPARATE owner GO immediately before the LIVE run (owner asked to confirm once more after the driver
      is implemented + cross-family audited). — DATE: 2026-07-22 (owner selection: "GO：现在开跑 C5+C7 live run")

Amendment status: **RATIFIED (owner @EloiseJulia, 2026-07-22).** Implementation + cross-family audit proceed;
the live run awaits the separate pre-launch owner GO above.
