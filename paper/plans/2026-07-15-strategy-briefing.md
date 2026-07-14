# Strategy Briefing — 2026-07-15 (new Manager onboarding)

> Author: Manager (orchestrator-only). Audience: owner (@EloiseJulia).
> Purpose: verified ground truth + scientific assessment + critical path + design pivots,
> BEFORE any Phase 3 / full-scale run. Ends with an owner decision gate (do NOT scale until sign-off).

---

## 1. VERIFIED GROUND TRUTH (re-derived from git, not narrative)

Local `main` == `origin/main` == **`fba11bd`** (handoff doc commit); the "local main is 4 behind"
warning in the handoff is now **resolved** (checkout is current).

### Merged to main (real, verified)
| Phase | Slice | PR | Commit | State |
|-------|-------|----|--------|-------|
| 0 | scaffold (`common/` schema FROZEN, llm offline mock, config, tests, CI) | #1 | `e58c994` | ✅ merged |
| 1 | code_spec (+core) — 21/21 distinguishable | #3 | `88f3ae7` | ✅ merged |
| 1 | data_analysis — 10/10 distinguishable | #4 | `358ee22` | ✅ merged |
| 1 | policy_qa — 20/20 distinguishable (refund reworked to natural default) | #5 | `199933c` | ✅ merged |
| 2 | metrics: `convergent_delusion` PRIMARY + slope + golden tests | #6 | `385fbdb` | ✅ merged |
| 2 | data_analysis harness flakiness fix (infra-error retry/cache discipline) | #7 | `9bc4341` | ✅ merged |
| 2 | run: 6 configs (single/SC/MAD-homo/MAD-hetero/verifier/interp-diverse) | #8 | `97058a3` | ✅ merged |

### NOT merged / in-flight (verified)
- **Phase 2 label slice** — branch `slice/phase2-S2b-label` (worktree `.worktrees/phase2-label`).
  The structured-answer-contract rework is **functionally COMPLETE but UNCOMMITTED**: working tree
  has modified `harness/label.py` + `tests/test_label.py` + untracked `verify_structured_canonical.py`.
  **I ran `tests/test_label.py` in the worktree: 21 passed.** Branch has diverged (6 ahead / 1 behind
  main). This is the single biggest "almost-done, not landed" asset. **No PR yet.**
- **Phase 2 integration test (S2d)** — NOT started (real run→label→metrics end-to-end over a few
  offline-mock tasks/domain, asserting a real convergent-delusion number, not the mock hash path).
- **Policy prompt structured-answer instruction** (`p2-answerfmt-prompt`) — NOT started. The labeler
  now REQUIRES a `FINAL ANSWER: $<amount>` / JSON `{"amount": N}` contract; `run.py`/the policy prompt
  must be made to INSTRUCT agents to emit it, or policy_qa labels degrade to `I_perp` en masse.
- **PRE-REGISTRATION (H1/H2 + frozen metric defs + phase-diagram prediction)** — **NOT done.** No
  committed artifact exists. This is the hard gate before ANY full-scale run (Law 7).
- **Phase 3+ (detector, rep-analysis, sim-users, stats, figures, writing)** — NOT started.

### Housekeeping
- Leftover merged branches/worktrees (`phase1-*`, `phase2-dataflaky`, `phase2-run`, `phase2-metrics`,
  `slice/phase1-S0-core`, `topic/phase1-benchmark`) are prunable. `phase2-label` must be kept until landed.

**Bottom line:** Phases 0–1 done; Phase 2 is ~80% done (metrics+run merged, label green-but-unlanded);
the science-critical Phase-2 tail (label land → answer-format prompt → integration → **pre-registration**)
is the current frontier. Nothing has been run at scale, so nothing is p-hackable yet — good.

---

## 2. SCIENTIFIC ASSESSMENT

### 2a. Where the idea stands
The engineering (benchmark + metrics + run harness) faithfully implements the *strongest* version of
the synthesis report: executable gold, deletion-based ambiguity, provenance separation, and
convergent-delusion (categorical same-wrong) as PRIMARY — all four of the report's round-2/round-3
reviewer defenses are baked into the code, not just the prose. This is the moat. **But no scientific
claim is EARNED yet** — we have infrastructure, zero measurements.

### 2b. Current single strongest FALSIFIABLE claim
> **H1 (primary, publishable target):** In underspecified tasks whose resolution requires *external*
> business knowledge absent from context (code_spec + data_analysis, executable gold), redundant
> aggregation (SC / MAD / verifier) does **not** reduce and may **increase** *convergent delusion* —
> the fraction of agents converging on the **same wrong interpretation I_k** — relative to a single
> agent, and this convergent-delusion rate **rises monotonically with ambiguity level (k=1→2→3)**.

This is falsifiable three ways: convergent delusion could stay flat vs. a single agent (redundancy
neutral), could *fall* (redundancy helps — thesis dead), or could rise on binary-ρ but NOT on the
categorical same-wrong metric (meaning we're measuring task difficulty, not collusion — the report's
own §2.2 self-critique). The categorical metric is what makes the claim defensible.

> **H2 (boundary condition, also publishable):** In *derivable* ambiguity (resolvable from context by
> reasoning), stronger reasoning models shrink the effect → a clean two-regime demarcation.

Delivering H1∧H2 as a **two-regime phase result** (not a universal ρ* law) is the maximally novel,
minimally over-claimed contribution. It converts the biggest threat (reasoning models dissolve the
effect, §8.2) into a *result*.

### 2c. Top 3 risks to novelty/validity for a top venue
1. **The metric-is-an-artifact risk (deepest).** If convergent delusion is driven by our *foil design*
   (the prior-trap interpretations we authored are just the "obvious" default), a reviewer says ρ is a
   constructor artifact. Mitigation already partly in place (executable gold + deletion-based ambiguity
   + cross-family provenance), but we must **empirically show** convergent delusion survives cross-family
   construction and is not reproducible by shuffling labels. This must be a pre-registered robustness cell.
2. **Effect-size / "yet another MAD-is-useless paper" risk.** If the effect is small or only appears on
   weak models, novelty collapses to a known result. Hedge: pre-register H1/H2 two-regime; make reasoning
   models a first-class condition; lead with the *underspecification-as-IV* + *no-GT convergent-delusion
   metric*, which no prior work manipulates jointly.
3. **Simulated-user / venue-scope risk.** The detector (Phase 3) and any "observability" claim must stay
   system-level; every human-facing statement must say "simulated decision-maker" with the Lost-in-Simulation
   caveat. Over-reaching to human psychology is an instant ACL/CHI desk-reject vector.

---

## 3. CRITICAL PATH TO A SUBMITTABLE RESULT

### PRE-REGISTER NOW (before scale) — owner-gated
A committed `paper/preregistration/2026-07-15-prereg.md` freezing:
- **H1 / H2** exactly as §2b (external-knowledge regime persists/intensifies; derivable regime shrinks).
- **Primary metric:** `convergent_delusion` (= modal-wrong share) — locked to `harness/metrics.py`.
- **Secondary:** `marginal_rho` (bridge only), `a_maj`, `ece`, `confidence_accuracy_slope`.
- **Predicted phase diagram:** convergent delusion rises with ambiguity k; SC/MAD ≥ single in the
  external-knowledge regime; effect attenuates for reasoning models on derivable ambiguity.
- **Domain roles:** code_spec + data_analysis = PRIMARY (executable gold); policy_qa = secondary
  (structured-answer contract, exact-cent match).
- **Analysis:** mixed-effects logistic (correctness ~ ρ + ambiguity + method + model + interactions),
  bootstrap CIs; **metric defs never change afterward.**
- **Robustness pre-commitments:** cross-family construction cell; label-shuffle null; false-surfacing
  control (unambiguous k=0 tasks must NOT fire).

**Metrics are already frozen in code (golden tests) — pre-registration is mostly a WRITE + owner-sign,
not new engineering. This is the cheapest highest-leverage gate. Do it before Phase 3.**

### Experiments that matter most (in order)
1. Land the label slice (green, cross-family re-audit non-Claude) → PR → merge. **[blocks everything]**
2. Answer-format prompt change in run.py/policy prompt → re-run run↔label integration.
3. Phase-2 integration test (real convergent-delusion number on offline mock).
4. **Pre-registration commit + owner sign-off.** ← STOP GATE before scale.
5. Full-scale run (Phase 5 sim-users feed configs) → metrics → Phase 6 stats/figures (phase diagram).
6. Phase 3 detector (Hypothesis Surfacing framing, false-surfacing rate on controls) — can start
   interface design in parallel once labels are stable.

### What can be CUT / deferred for a first submission
- **Phase 4 representation analysis (logit-lens/activation patching, GPU)** — defer to v2/camera-ready.
  It's the ACL "internal mechanism" upgrade but not required for the first defensible claim; it's also
  the most resource-heavy and scope-restricted (single open-weight model only).
- **HCI dashboard / human study (Direction C)** — future work; keep simulated-user only, non-core.
- **policy_qa as a primary domain** — keep as secondary/robustness; the executable-gold domains carry H1.

---

## 4. RECOMMENDED DESIGN PIVOTS (with rationale)

1. **Lead with the two-regime (H1/H2) framing, not a single universal effect.** Rationale: the report's
   own strongest reviewer threat (§8.2, reasoning models) is neutralized only by pre-registering both
   regimes. This is a *reframe*, not new code — but it must be locked in the pre-registration.
2. **Elevate the label-shuffle null + cross-family construction cell to pre-registered primary robustness.**
   Rationale: risk #1 (metric-is-artifact) is the deepest ACL hit; showing convergent delusion is
   destroyed by label-shuffling and survives cross-family construction is the single most persuasive
   defense. Cheap to add now, devastating to add post-hoc (looks like p-hacking).
3. **Keep the detector as "Hypothesis Surfacing," never "no-GT right/wrong judgment."** Rationale: report
   §6/round-3 point 3 — consensus strength cannot separate true/false consensus; the defensible claim is
   "this consensus depends on unstated assumption I_k," measured against a false-surfacing rate on
   unambiguous controls. This shapes Phase 3 spec (not yet written).
4. **No pivot on the metric.** convergent_delusion stays PRIMARY; binary ρ stays secondary bridge only.
   The code already enforces this; do not let any downstream agent "simplify" to ρ.

---

## 5. OWNER DECISION GATE (I am STOPPING here per instruction)

I will NOT launch Phase 3 or any full-scale run until you sign off. I need your rulings on:
- **(A)** Approve the Phase-2 tail sequence (land label → answer-format prompt → integration → prereg)?
- **(B)** Approve H1/H2 exactly as stated in §2b, or amend, before I draft the pre-registration doc?
- **(C)** Confirm the CUT list (defer Phase 4 rep-analysis + HCI to v2; policy_qa secondary)?
- **(D)** Any scientific-judgment items you want to weigh in on now: target-is-natural-default rulings
  are already settled per handoff; venue lead (ACL/EMNLP vs NeurIPS D&B) can wait until we see effect sizes.

On your go, my first orchestration action is spawning a **non-Claude** cross-family audit of the
uncommitted label rework, then a fix/commit sub-agent to land it — keeping implementer(Claude) ≠
auditor(non-Claude) provenance intact.
