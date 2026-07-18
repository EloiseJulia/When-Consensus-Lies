# Manager Handoff — 2026-07-18 (session retiring: context saturated)

> Successor Manager: READ THIS FIRST, then re-derive ground truth from git (`git log --oneline -30 main`,
> `gh pr list --state all`) and read `paper/decisions/DECISION-LOG.md` (rows 1–61) + the prereg +
> amendments. Trust the log + git over any prose. You are ORCHESTRATOR-ONLY + a top-venue researcher.

## 0. ONE-LINE STATE
The reconstructed benchmark is done, the resumable runner + Phase-6 analysis + the §11 pilot-gate driver
are built and merged, the **§11 MVP pilot PASSED cleanly**, and the **H2 top-up (→14 H2 items) is merged**.
The project is at the **pre-registration FREEZE moment**, one short checklist away from launching the
CONFIRMATORY run. Do NOT launch until the checklist below is green and the owner presses go.

## 1. THE SCIENCE (what we're proving + current strongest claim)
Thesis: under UNDERSPECIFIED prompts, redundant aggregation does not reduce (and can amplify) **convergent
delusion** — independent agents converging on the SAME wrong interpretation because they share a prior
(ρ→1 fake redundancy). Primary metric = `cd_primary` (A04: modal-wrong over ENUMERATED foils; I_perp
ineligible). See `Silent-Consensus-Failure-Report-EN.md` for the full framing.

⭐ **Strongest falsifiable claim (empirically supported at pilot scale):** a **two-regime MAIN EFFECT** —
- **H1_external** (disambiguator needs OUTSIDE knowledge): silently traps **everyone**, incl. frontier
  reasoners (GPT-5.6 / Claude-Opus-4.8 / Gemini-3.1-Pro) AND cross-family pools → CD≈1.0.
- **H2_derivable** (disambiguator is IN the retained prompt/data): **resolved by everyone**, incl.
  legacy-weak gpt-3.5-turbo → I0.
- **The failure axis is the disambiguator's LOCATION, not model capability.** The pre-registered H2
  reasoner-vs-weak INTERACTION is empirically ABSENT (rows 51-52); we TEST + REPORT it honestly (expected
  null) and LEAD with the regime main-effect (owner ruling row 52, option A — no amendment).

Pilot evidence (row 60, $0, 460 runs): Gate A cd_primary=0.766 on H1 k≥1; R1a k0-control CI [0.531,1.000];
R1b uniform-null CI [0.030,0.499]; I_perp 0.076. The corrected A07 nulls DISCRIMINATE (see §3).

Top risks to novelty/validity (keep pre-empting): (a) construct validity of the reversed benchmark —
mitigated by cross-family construction + the empirical default-check + the reversed spot-check gate;
(b) "single-model determinism" attack on homogeneous CD — mitigated by LEADING with cross-model
convergent delusion + framing homogeneous saturation as the ρ→1 fake-redundancy demo; (c) H2 interaction
underpowered — pre-registered as secondary, reported honestly, never backfilled; (d) row 56: "single"
method for MULTI-model classes is a cross-model pool, not N=1 → at analysis, restrict the H1a
single-baseline contrast to the homogeneous (single-model) class or document the pooled semantics.

## 2. VERIFIED GROUND TRUTH (merged to main; all cross-family GPT-audited, 0 BLOCKER/MAJOR at merge)
- Reconstructed reversed benchmark (Amdt 01 target-reversal, 02 Task.regime, 03 combinatorial 2^k'):
  code_spec #16, policy_qa #17, data_analysis #18, harder-H2 #29, **H2 top-up #32**.
  **Item set NOW: H1_external=40 (code_spec 20 + policy_qa 14 + data_analysis 6), H2_derivable=14
  (data_analysis: typical, avgprice, rate, geomean, harmonic, cumulative, tierank × {k0,k1}). 54 total.**
- Infra: resumable runner #19 (+ token-budget fix #28, replicate-seed + config_kwargs + gate hardening
  #30); labeler hardening #21/#23; diagnostic driver #20; cache-test fix #25; Phase-6 analysis pipeline
  #26 (`analysis/` — cd.py, contrasts.py, decision_rules.py, stats.py, figure_data.py); copilot_proxy
  provider #27; frontier default-check #28; registered-run wiring + §11 pilot gate #30; **A07 R1a/R1b null
  redefinition #31**; **H2 top-up #32**. Main is green (~698 passed).
- Detector (Phase 3) offline v1 #24 (Hypothesis-Surfacing; live eval deferred, owner-gated).

## 3. PRE-REGISTRATION PACKAGE (status — successor MUST verify before launch)
Frozen prereg `paper/preregistration/2026-07-15-prereg.md` (freeze `c0a0393`). Amendments:
- **A01/02/03** — reversal/regime/combinatorial — in force (benchmark built on them).
- **A04** (I_perp treatment) — ✅ SIGNED (row 40). PRIMARY cd_primary = modal-wrong over ENUMERATED foils.
- **A05** (asymmetric reasoner-N) — ⛔ SUPERSEDED (row 53; proxy uncapped). Contingency only.
- **A06** (frontier proxy roster, option-a) — ✅ SIGNED (row 53).
- **A07** (R1 null redefinition) — ✅ SIGNED (row 57). ⭐ The frozen R1 label-shuffle null is a MATHEMATICAL
  IDENTITY for this thesis (null_cd==real_cd: a marginal-preserving shuffle can't reduce cd for a
  shared-prior/marginal-bias phenomenon). REPLACED by **R1a** (k=0-control contrast, bootstrap 95% CI of
  CD_{k≥1}−CD_k0 excl. 0, AND CD_k0≈0) + **R1b** (uniform-over-each-item's-interpretation-set null, bootstrap
  CI of obs−uniform excl. 0). Label-shuffle DEMOTED to a reported shared-prior diagnostic (kept for
  MAD/debate). The pilot caught this before scaling.
- **A08** (pilot-calibrated final N) — 📝 DRAFT (`...amendment-08-final-n-DRAFT.md`), counts now filled
  (H1=40, H2=14, 54 total; grid single+SC k5+homMAD N5+hetMAD; 3 seeds; verifier+SC-k10 SCHEDULED as a
  secondary sensitivity pass, NOT dropped). **Owner signs A08 at LAUNCH.**

## 4. ⭐ IMMEDIATE NEXT STEPS (the remaining pre-launch checklist, owner 2026-07-17)
1. **Empirical default-check on the 4 NEW H2 families** (data_geomean/harmonic/cumulative/tierank) on the
   frontier proxy — confirm the H2 tag EMPIRICALLY (capable models RESOLVE → I0, not the foil).
   Reclassify/exclude any mismatch + log it. This is checklist item #2's "re-run the spot-check gate on
   the additions." Driver: `scripts/default_check_frontier.py` (or a targeted variant). Quick, $0.
2. **Finalize + get owner sign-off on Amendment 08** (final N). Rename DRAFT→SIGNED on sign.
3. **Report to owner: the final H2 item count + the signed amendment list**, then get the explicit GO
   (owner: "Report back the H2 item count + the signed amendment list before pressing go"). This LOCKS the
   pre-registration — results reported honestly whatever they are, NO further design changes.
4. **LAUNCH the confirmatory run**: `scripts/registered_run.py` (NON-pilot; ≥3 seeds enforced) on
   `--provider copilot_proxy`, resumable/day-spanning ($0; gpt-4o-mini's intermittent UserByModelByDay cap
   is handled by resume). Endpoint-namespaced checkpoint. This is CONFIRMATORY — results count toward H1/H2.
5. **Phase-6 real analysis** on the AgentRun JSONL (merged `analysis/` pipeline: A04 CD variants + A07
   R1a/R1b + §8 crossed-RE mixed model + §9 decision rules + row-35 cross-model contrast + figure_data).
   Settle the row-56 H1a-single-baseline interpretation here.
6. **Verifier + SC-k10 sensitivity pass** (A08 §2 — scheduled, do NOT drop; verifier-accomplice result is
   thematically important).
7. **Writing** (Phase 7): Methods + "Deviations from Pre-registration" straight from the DECISION-LOG.

## 5. KEY TECHNICAL FACTS
- **Proxy:** local `ghc-api` Copilot proxy, `http://127.0.0.1:8313/v1` (also :8787), OpenAI-compatible, NO
  token, effectively UNLIMITED. Frontier families O/A/G/M. Requests: `max_completion_tokens` (not max_tokens);
  logprobs only from OpenAI (→ homogeneous ρ-baseline = gpt-5.4); temperature omitted for gpt-5.6/mai-code.
  gpt-4o-mini has an intermittent daily cap even via the proxy → day-spanning resume.
- **Roster (A06):** tested homogeneous=gpt-5.4; heterogeneous=gpt-5.4/claude-sonnet-4.6/gemini-3.1-pro;
  reasoning=gpt-5.6-sol/claude-opus-4.8/gemini-3.1-pro; weak=gpt-4o-mini/gemini-3.5-flash/claude-haiku-4.5;
  constructor+judge=mai-code-1-flash-picker (judge vestigial under executable gold); code_reviewer=gpt-5.6-sol.
- **Runner:** live guard `RUNNER_LIVE=1` (proxy needs no token). Grid = task×config×model×seed. Genuine
  collision-free replicate seeds (stride≥ensemble); AgentRun dedup includes replicate_seed. Checkpoint
  namespaced by provider|base_url (no cross-endpoint pooling). `config_kwargs` sets SC k=5, homMAD N=5.
- **Analysis cell (frozen):** `decision_rules._item_level_cells` POOLS multi-model classes into ONE cell
  with a `pool:<sorted>` id for the (1|model) RE — this is INTENTIONAL (was audit-flagged, ruled a false
  positive). Do NOT add `model` to the cell key.
- **Build/test:** `python -m pip install -e . && python -m pytest -q`. Validate a domain:
  `python -m bench.validate --domain <d>`. Pilot: `RUNNER_LIVE=1 python scripts/registered_run.py --pilot`.
- **FROZEN — never edit:** `harness/metrics.py`, `common/schema.py`, `harness/nulls.py` DEFINITIONS,
  `paper/preregistration/*` (except authoring new amendments), `bench/*` existing items, and the metric
  MATH in `analysis/cd.py|contrasts.py|decision_rules.py|stats.py`.

## 6. INVIOLABLE WORKFLOW (Hard Laws)
Orchestrator-only: Manager writes ONLY specs/plans/reports/decision-log/amendments under paper/*; spawns a
sub-agent (worktree) for EVERY code/audit/fix, incl. one-liners. Provenance separation (Law 6):
implementer = **Claude** family (claude-sonnet-4.6 / opus), auditor = **GPT** family (gpt-5.6-sol), fresh &
hostile, report-only; different family than the implementer. Merge only after full build+run + suite green
+ a cross-family audit returns 0 BLOCKER/MAJOR (Law 4; call out config.yaml/schema/shared-infra in the PR
body). Executable gold > LLM-judge (Law 7). Primary metric = convergent delusion (frozen). One clean audit
→ merge, don't re-audit endlessly (Law 5). ESCALATE every SCIENTIFIC judgment call to the owner
(target/default rulings, H1/H2 tagging, claim/venue framing, design pivots, amendments, the moment before
scaling). Sub-agents drop stray root `plan.md`/`plan.md` — remove before merge (harmless; the Manager plan
files live under paper/plans). NEVER edit the main checkout directly.

## 7. DECISION-LOG DISCIPLINE (critical for the paper)
`paper/decisions/DECISION-LOG.md` is LIVING (rows 1–61). Append a row for EVERY adjustment: [date | what |
before→after | WHY | hypothesis/metric affected | commit/amendment SHA | prereg deviation? Y/N]. The owner
writes Methods + "Deviations from Pre-registration" straight from it. Never make a silent design change.

## 8. SESSION ARTIFACTS (this session's files/, not committed)
`~/.copilot/session-state/<id>/files/`: pilot_gate_CLEAN_PASS.log (the passing §11 verdict),
pilot_gate2_verdict.log, default_check_frontier_*.{log,jsonl,txt}, default_check_*.{log,jsonl,txt}.
The pilot checkpoints (pilot_gate2_checkpoint.jsonl) are there too. These are diagnostic; the CONFIRMATORY
run writes a fresh checkpoint.
