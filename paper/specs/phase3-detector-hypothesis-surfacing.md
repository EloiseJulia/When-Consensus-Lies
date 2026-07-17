# Phase 3 — Detector spec: Hypothesis Surfacing (v1 design, offline)

> Manager-authored spec (orchestrator). Owner-approved to start spec/interface design in parallel
> (2026-07-17): SPEC/INTERFACE ONLY — no live runs. Headline metric = false-surfacing rate on unambiguous
> (k=0) controls. Design against the RECONSTRUCTED benchmark (reversed target + regime tags). NO
> frozen-schema (`common/schema.py`) changes without an amendment. Implementation later via a spawned
> sub-agent (spec→plan→execute, cross-family audited). Governs prereg §6.

## 1. Framing (what the detector IS and IS NOT)
- **IS: Hypothesis Surfacing** — detect that a consensus/answer DEPENDS ON an unstated assumption `I_k`
  (an unresolved interpretation axis), so a downstream decision-maker can be warned "this result assumes
  X; confirm X." It surfaces the presence of an aleatoric interpretation fork.
- **IS NOT: no-ground-truth right/wrong judgment.** Consensus STRENGTH cannot separate TRUE consensus from
  FALSE (convergent-delusion) consensus (report round-3 point 3; a wrong shared prior looks identical to a
  right one from agreement alone). The detector must NEVER claim an answer is correct/incorrect.
- Therefore the discriminating signal is **interpretation-branch divergence / aleatoric uncertainty**
  (Hou et al. style), NOT agreement/confidence magnitude.

## 2. Headline + secondary metrics (prereg §6, FROZEN)
- **HEADLINE — false-surfacing rate on k=0 controls.** On genuinely unambiguous items (the k=0 control
  set: prompt == latent_spec, single interpretation, empty key_questions), the detector must NOT fire.
  **Pre-registered target: false-surfacing rate < 10%** on k=0 controls.
- **Paired — surfacing recall / discrimination on k≥1 items** (report AUROC / F1): on known-underspecified
  items (k≥1, which have real interpretation forks), the detector SHOULD fire. Report the ROC over a
  detection score, and the operating point that meets the <10% k=0 false-surfacing constraint.
- Do NOT promote any consensus-strength statistic to a headline detector signal.

## 3. Inputs / outputs (interface — works with the FROZEN schema, no changes)
Detector consumes what the run+label pipeline already produces — do NOT add frozen-schema fields:
- **Input:** a `Task` (from bench, carrying `interpretations`, `regime`, `ambiguity_level`,
  `key_questions`) + the set of `AgentRun`s for that task under a config (their raw outputs and/or their
  executable-gold interpretation labels from `harness/label.py`). Multiple agents/samples per task.
- **Output (proposed dataclass in the detector module, NOT in common/schema):**
  `SurfacingResult(task_id: str, fired: bool, score: float, diverging_axes: list[str],
  evidence: dict)` — `score` ∈ [0,1] (detection score for ROC), `fired` = score ≥ threshold,
  `diverging_axes` = the key_questions/interpretation axes the agents appear to split on (for the
  human-facing "this assumes X" message), `evidence` = per-interpretation label counts etc.
- If a genuinely new persisted field is ever needed on Task/AgentRun, STOP and request an amendment — do
  NOT edit the frozen schema.

## 4. Candidate detection signals (v1 — evaluate; pick by the k=0 false-surfacing constraint)
All operate on the interpretation-LABEL distribution across agents/samples (executable-gold labels), NOT
on consensus strength alone:
1. **Interpretation-branch divergence:** entropy / number of DISTINCT executable-gold interpretation
   labels among the agents (excluding I_perp handling per Amendment 04 — a scratch of `I_perp` is
   degeneracy, not a genuine fork; count distinct ENUMERATED interpretations). High distinct-branch
   spread ⇒ surface. On a true k=0 control there is one gold interpretation, so agents that solve it land
   on one label ⇒ low divergence ⇒ no fire (this is what keeps false-surfacing low).
2. **Sampling-induced label instability:** re-sampling the SAME model at temperature>0 and observing the
   label FLIP across samples (aleatoric fork) vs staying put. A control item is stable; an underspecified
   item is unstable.
3. **Cross-model label disagreement:** different model families landing on DIFFERENT enumerated
   interpretations (the cross-model signal — connects to the fake-redundancy framing: homogeneous
   agreement is uninformative; cross-model divergence reveals the fork).
4. (Optional, later) prompt-perturbation / self-probe: ask a model to enumerate assumptions; check if a
   deletable axis is named. Deferred — v1 leads with the label-distribution signals (1–3), which are
   executable-gold-grounded and cheap.

## 5. Evaluation harness (offline against the reconstructed benchmark)
- Build the evaluation set from the RECONSTRUCTED benchmark: k=0 controls (false-surfacing denominator)
  + k≥1 items across regimes (recall). The detector is scored on the LABEL distributions produced by the
  run+label pipeline — can be exercised OFFLINE on cached/mock AgentRun labels (no live runs for the spec;
  live evaluation waits for the registered run + owner go).
- Report: false-surfacing rate on k=0 (< 10% target), surfacing AUROC/F1 on k≥1, and a breakdown by
  regime (H1_external vs H2_derivable) and ambiguity level k.
- Guard: the detector must be blind to the gold TARGET (it never sees which interpretation is correct — it
  only sees the agent label DISTRIBUTION); surfacing is about DIVERGENCE, not correctness.

## 6. Module / test layout (proposed — for the implement sub-agent)
- `detector/surfacing.py` — the `SurfacingDetector` (signals 1–3, a `score()` + `fire()` API, threshold
  calibrated to the k=0 <10% constraint) + `SurfacingResult`.
- `detector/evaluate.py` — the offline evaluation harness (false-surfacing rate, AUROC/F1, per-regime).
- `tests/test_surfacing.py` — offline: k=0 controls do NOT fire (< 10% on a crafted control set); k≥1
  multi-interpretation label distributions DO fire; I_perp-heavy degeneracy does NOT falsely fire
  (Amendment-04 consistent); no dependence on the gold target.
- NO changes to common/schema.py, harness/metrics.py, or paper/preregistration/. Reuse harness/label.py
  outputs.

## 7. Out of scope for v1 (deferred / owner-gated)
- Any LIVE detector run (waits for the registered run + owner go).
- Representation-level signals (Phase 4 rep-analysis, GPU) — deferred to v2.
- Any HCI/dashboard surface — future work; keep the detector system-level, simulated-decision-maker only.

## 8. Build sequencing
Spec (this doc) → per-slice plan → implement sub-agent (Claude) → cross-family (GPT) audit → merge. First
implementation is OFFLINE (signals + evaluation harness on cached/mock labels); live evaluation is a later
owner-gated step after the registered run produces real label distributions.
