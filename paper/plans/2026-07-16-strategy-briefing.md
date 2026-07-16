# Strategy Briefing — 2026-07-16 (new Manager onboarding: manager-p3)

> Author: Manager (orchestrator-only, researcher-mandate). Audience: owner (@EloiseJulia).
> Purpose: VERIFIED ground truth (re-derived from git, not narrative) + scientific assessment +
> critical path + recommended pivots, BEFORE any registered run or scaling. Ends at an owner
> decision gate. I will NOT launch registered runs or scale without your sign-off.
> Companion living document: paper/decisions/DECISION-LOG.md (no new row filed — this briefing makes
> no design change; it only proposes decisions O1–O5 for your ruling).

---

## 1. VERIFIED GROUND TRUTH (re-derived from `git log` / `gh pr list` / file inspection 2026-07-16)

- **Authoritative HEAD:** local `main` == `origin/main` == **`eae639c`** (the 2026-07-16 handoff doc
  commit). Working tree **clean**. `gh pr list` now works (the transient GraphQL error in the handoff
  has cleared).
- **Full test suite GREEN:** `python -m pytest -q` → **312 passed in ~172s** (verified this session).

### Merged to main (verified against `gh pr list --state all`)
| Phase | What | PR | State |
|-------|------|----|-------|
| 0 | scaffold: `common/` (schema.py FROZEN), config.yaml, llm.py, tests, CI | #1 | ✅ merged |
| 1 (orig) | benchmark core + code_spec / data_analysis / policy_qa (target=default) | #3/#4/#5 | ✅ merged |
| 2 | metrics (convergent_delusion PRIMARY + golden) · flakiness fix · run configs · label (structured contract) · answer-format prompt · integration test · R1 null + MVP pilot | #6–#12 | ✅ merged |
| 3-INFRA | online LLM path (GitHub Models, Option-B routing) · temperature + o-series handling | #13/#14 | ✅ merged |
| Amdt 02 | `Task.regime` schema field | #15 | ✅ merged |
| **1-R** | **code_spec RECONSTRUCTION (target reversal + combinatorial 2^k' sets + regime tags + `__combdef`)** | **#16 (`f6e11c1`)** | ✅ merged |

### Pre-registration status 🔒
- **FROZEN `c0a0393`** (owner-signed 2026-07-15): H1/H2, regime criterion §2, PRIMARY =
  `convergent_delusion`, secondaries, co-primary nulls R1 (population-level label-shuffle) + R2
  (cross-family construction), silent-failure signature, detector false-surfacing headline, decision
  rules, sample sizes. **Metric definitions immutable.**
- **Amendments (all owner-signed, metric-frozen):** 01 target/default reversal (`a4fee0f`);
  02 `Task.regime` field (`a093783`); 03 combinatorial 2^k' interpretation sets + metric-integrity
  guardrail (`e91c63c`).

### What is DONE vs what REMAINS (the frontier)
**DONE:** all infra for real runs; code_spec reconstructed under the reversal AND empirically validated
on live models (mistral-small AND llama-3.3-70b converge on the SAME wrong interpretation, CD=1.0, at
k=1/2/3 — the phenomenon is real on ≥1 domain).

**REMAINS (dependency-ordered critical path):**
1. **[FIRST, parallel] Reconstruct `data_analysis` + `policy_qa` under the reversal.** VERIFIED this
   session by file inspection: only `bench/code_spec/__init__.py` sets `regime=` (9 sites, all
   `H1_external`); `data_analysis` and `policy_qa` have **NO** `regime=` assignments and still contain
   the OLD **target=default** construction (they inherited only the shared `__combdef` checker helper).
   **Running experiments on them now would reproduce the CD≈0 artifact we just fixed.** This is the #1
   task. Must include the H2 `median-under-visible-skew` demonstrator in data_analysis (Example C) — the
   only clean H2 regime we have.
2. **[dep:1] Empirical per-regime default-check** on all reconstructed tasks (live models, temp>0):
   H1 → homogeneous agents (incl. reasoners) converge on a wrong combination; H2 → reasoners RESOLVE,
   weaker default wrong. Empirical behavior is the FINAL arbiter of each regime tag (owner ruling);
   reclassify/exclude mismatches.
3. **[dep:2] Reversed spot-check gate → OWNER SIGN-OFF.** Manager does not self-approve scaling.
4. **[dep:3] Resumable, cache-backed, RPM-throttled runner.** NOT built yet (`scripts/mini_pilot.py`
   is a double-guarded smoke, not the runner). Required because gpt-4o-mini (the ρ-baseline) is
   per-DAY-capped → full-scale cannot finish in one session; must checkpoint + resume across days and
   lean on the disk cache. Token-independent to build + offline-test.
5. **[dep:4] Registered mini-pilot** (prereg §11) on a small real batch after the gpt-4o-mini daily
   cap resets: confirm `convergent_delusion` > 0 on real vs ≈CD₀ under R1 shuffle; integration +
   golden tests pass. Diagnostic, not confirmatory.
6. **[dep:5] Full-scale registered runs → Phase 6 stats/figures.** Phase 3 detector interface can
   start in parallel once labels are stable; Phase 4 rep-analysis (GPU) deferred to v2; Phase 5
   sim-users sit in the 0→2→5→6 chain.

---

## 2. SCIENTIFIC ASSESSMENT

### 2a. Single strongest FALSIFIABLE claim we can currently defend
> **H1 (primary).** In underspecified tasks whose resolution requires knowledge **external** to the
> prompt/artifacts (`regime = H1_external`; executable-gold domains code_spec + data_analysis),
> redundant aggregation (self-consistency k∈{5,10} / homogeneous-MAD / heterogeneous-MAD / verifier)
> does **not** reduce — and may **increase** — **convergent delusion**: the fraction of agents
> concentrating on the **same wrong interpretation**, over the FULL 2^k' combinatorial interpretation
> set. Confidence/consensus stay high while accuracy drops (a *silent* failure).

**Why it is defensible (the moat, already in code — not just prose):** executable gold (never
LLM-judge) → labels are deterministic and not judge-confounded; deletion-based ambiguity as the IV;
cross-family construction (R2) → rules out shared-prior-with-constructor; population-level label-shuffle
(R1) → rules out marginal-frequency artifacts; categorical *same-wrong* metric (not binary ρ) → measures
convergence, not task difficulty. **Live evidence exists on code_spec** (two families, CD=1.0 across k).

**Publishable contribution shape:** the **two-regime demarcation (H1 persists incl. reasoners ∧ H2
attenuates for reasoners)**, NOT a universal ρ* threshold (non-identifiable per Kaniovski). This
converts the biggest reviewer threat ("reasoning models dissolve the effect") into a *result*.

### 2b. Top 3 risks to novelty/validity for a top venue
1. **`I_perp` contaminates the primary metric (deepest, and it is LIVE).** The frozen
   `false_consensus_rate` counts the modal wrong label INCLUDING the degenerate `I_perp` bucket. In the
   code_spec default-check, llama converged on `I_perp` at k=2/k=3 — but multiple agents landing on
   `I_perp` for *different* off-axis reasons is **not** the "consensus on the SAME I_k" the report
   claims. A reviewer will say the effect is partly a parsing/degeneracy artifact. **This is the single
   most important open scientific-validity item** (decision O1 below). It does not require changing the
   frozen metric — only a Phase-6 reporting rule (CD with vs without I_perp).
2. **Effect-size / "another MAD-is-useless paper" risk.** If the effect is large only on weak models,
   or CD saturates at 1.0 so H1b's *rise with k* is invisible (already observed on code_spec — decision
   O2), novelty collapses. Hedge: lead with the H1/H2 **regime contrast** as the headline (a phenomenon
   no prior work manipulates), keep k-monotonicity as secondary, and bring the heterogeneous + reasoning
   pool + more graded tasks to try to recover the gradient.
3. **Construct-validity of the "reversed trap" + simulated-user/venue overreach.** (a) A reviewer may
   argue our non-default targets are contrived gotchas; the fairness bar (a human reading the full spec
   agrees the user wanted the non-default; the deleted clause is exactly what reveals it) must hold on
   EVERY reconstructed task and be defensible in the paper. (b) Every human-facing statement must say
   "simulated decision-maker" with the Lost-in-Simulation caveat; the detector stays **Hypothesis
   Surfacing** (system-level), never no-GT right/wrong judgment. Over-reach to human psychology is a
   desk-reject vector.

---

## 3. CRITICAL PATH TO A SUBMITTABLE RESULT (shortest defensible route)

1. **Reconstruct data_analysis + policy_qa** (2 parallel implement sub-agents, same template as #16;
   implementer = Claude family, each cross-family audited by a NON-Claude auditor to preserve
   provenance). data_analysis carries the H2 median-under-skew demonstrator + the H1 org-KPI item;
   policy_qa is SECONDARY breadth (structured-answer contract). → PRs → law-4 gate → merge.
2. **Empirical per-regime default-check** (one research/run sub-agent, live models) → reclassify/exclude
   per behavior.
3. **Reversed spot-check gate package → OWNER SIGN-OFF** (I present; you approve before any scale).
4. **Build the resumable runner** (one implement sub-agent, offline-testable) in parallel with 1–3.
5. **Registered mini-pilot** after the gpt-4o-mini cap resets → confirm machinery.
6. **Full-scale registered run → Phase 6 stats/figures** (mixed-effects; ρ–ambiguity phase diagram;
   H1/H2 interaction; silent-failure triad; CD reported with AND without I_perp).

**Deferred for a first submission (recommend CUT):** Phase 4 representation analysis (GPU, single
open-weight model) → v2/camera-ready; HCI dashboard / human study → future work (keep simulated-user
only); policy_qa stays SECONDARY (not a primary effect-size domain).

---

## 4. RECOMMENDED DESIGN DECISIONS / PIVOTS (for your ruling — nothing changed yet)

These are the open scientific-judgment calls I am escalating. **I will not act on any until you rule.**

- **O1 — `I_perp` in the primary metric (touches interpretation of a frozen metric; highest priority).**
  Recommend: KEEP `false_consensus_rate` frozen as-is, and in Phase-6 analysis report convergent delusion
  **BOTH with and without the `I_perp` bucket** (a reporting/robustness rule, not a metric redefinition).
  This pre-empts the "degeneracy artifact" attack while honoring the freeze. → *If you approve, I file a
  reporting-rule note (not an amendment, since the metric is unchanged) and log it.*
- **O2 — H1b (CD-rises-with-k) headline vs regime-contrast headline.** CD saturates at 1.0 on small
  models across k in code_spec → the k-gradient may be invisible. Recommend: LEAD with the **H1/H2 regime
  contrast** as the headline; keep H1b monotonicity as a secondary prediction tested on the graded
  heterogeneous+reasoning pool. No pre-registration change (both are already registered); this is a
  framing/emphasis decision. → *your call on headline framing.*
- **O3 — data_analysis regime balance.** Recommend building data_analysis with BOTH an H1_external item
  (org-KPI, Example D) AND the H2_derivable demonstrator (median-under-skew, Example C), so the two-regime
  contrast has ≥1 clean item per regime in an executable-gold domain. → *confirm this composition.*
- **O4 — policy_qa scope.** Recommend keeping policy_qa SECONDARY (cross-domain consistency check, exact-
  cent, never accuracy) and reconstructing it under the reversal for breadth only. → *confirm secondary.*
- **O5 — Reconstruction sequencing.** Recommend spawning data_analysis and policy_qa reconstruction as
  **parallel** independent slices now (they are independent per-domain files), each cross-family audited.
  → *approve me to spawn these two implement sub-agents on your go.*

No pivot proposed on the PRIMARY metric: `convergent_delusion` stays primary; binary `marginal_rho`
stays a secondary bridge. The combinatorial full-set measurement (Amdt 03 guardrail) is NOT narrowed.

---

## 5. OWNER DECISION GATE (I am STOPPING here per your instruction)

I will not scale, launch any registered/full-scale run, or spawn the reconstruction sub-agents until you
sign off. Please rule on:
- **(A)** Approve the critical path in §3 and the CUT list (Phase 4 rep-analysis + HCI → v2; policy_qa
  secondary)?
- **(B)** Ruling on **O1** (I_perp dual-reporting) — the top validity item.
- **(C)** Ruling on **O2** (headline: regime-contrast lead vs k-monotonicity).
- **(D)** Confirm **O3/O4/O5** (data_analysis dual-regime composition; policy_qa secondary; spawn the
  two reconstruction sub-agents in parallel now).

On your go, my first orchestration action is spawning the two reconstruction implement sub-agents
(implementer = Claude family) with a NON-Claude cross-family auditor each — preserving Hard Law 6
provenance — and, in parallel, an implement sub-agent for the resumable runner. Every adjustment I make
or approve from here will be appended to paper/decisions/DECISION-LOG.md, with a formal Amendment filed
if it ever touches the pre-registration.
