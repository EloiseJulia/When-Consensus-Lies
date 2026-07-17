# Phase 3 — detector implementation (offline v1) — per-slice plan

> Manager plan. Implementer = Claude family, worktree `.worktrees/phase3-detector` (branch
> `slice/phase3-detector`). Auditor = NON-Claude (GPT). OFFLINE ONLY — no live runs (owner scope).
> Spec of record: `paper/specs/phase3-detector-hypothesis-surfacing.md` (READ IT FIRST — it is authoritative).
> Metric/schema FROZEN — no changes to common/schema.py, harness/metrics.py, paper/preregistration/.

## Deliverables (per the spec §3–§6)
1. **`detector/surfacing.py`** — `SurfacingDetector` + `SurfacingResult(task_id, fired, score, diverging_axes, evidence)`.
   - Consumes what the run+label pipeline produces: a `Task` (bench, carrying `interpretations`, `regime`,
     `ambiguity_level`, `key_questions`) + the set of executable-gold interpretation LABELS assigned to its
     agents/samples (from `harness/label.py`), and/or raw `AgentRun`s. Do NOT add frozen-schema fields.
   - **Signals (operate on the interpretation-LABEL distribution, NOT consensus strength):**
     (1) interpretation-branch divergence = entropy / count of DISTINCT ENUMERATED interpretation labels
     across agents (Amendment-04-consistent: `I_perp` is degeneracy, NOT a genuine fork — do not let an
     I_perp-heavy distribution FIRE; count distinct enumerated interps); (2) sampling-induced label
     instability (label flips across same-model temperature>0 samples); (3) cross-model label disagreement
     (different families → different enumerated interps). Combine into a `score()` ∈ [0,1]; `fire()` =
     score ≥ threshold. The threshold is a parameter CALIBRATED so the k=0 control false-surfacing rate
     < 10% (spec §2).
   - `diverging_axes` = the `key_questions` / interpretation axes agents split on (for the human-facing
     "this assumes X" message). Detector must be BLIND to the gold TARGET (never uses is_target/which
     label is correct — only the label DISTRIBUTION); surfacing = divergence, not correctness.
2. **`detector/evaluate.py`** — offline evaluation harness: given a set of (Task, agent-label-distribution)
   pairs, compute **false-surfacing rate on k=0 controls** (headline, target < 10%), **surfacing
   AUROC/F1 on k≥1** items over the `score`, and a breakdown by regime (H1_external vs H2_derivable) and
   ambiguity level k. Include a threshold-selection routine (pick the operating point meeting the k=0
   <10% constraint) — all offline.
3. **`tests/test_surfacing.py`** — OFFLINE (no network/token). Assert:
   - k=0 controls (all agents on the single gold interpretation) → do NOT fire; the control-set
     false-surfacing rate < 10%.
   - k≥1 items with a genuinely divergent enumerated-label distribution → DO fire (high score).
   - An `I_perp`-heavy / degenerate distribution → does NOT falsely fire (Amendment-04 consistent).
   - The detector's output is invariant to WHICH interpretation is the target (relabel target → same
     fired/score) — proves gold-target blindness.
   - `evaluate.py` computes the headline false-surfacing rate + AUROC correctly on a crafted set.

## Build against the RECONSTRUCTED benchmark
Use `bench.load_tasks` / the reconstructed domains (code_spec, data_analysis, policy_qa) for realistic
Task structures (regime tags, k-levels, combinatorial interpretations). For agent-label DISTRIBUTIONS in
the offline tests, CONSTRUCT them synthetically (no live models): e.g. k=0 → all agents = I0; k≥1 → a
divergent mix over the enumerated interps; degenerate → mostly I_perp. (Real label distributions arrive
later from the registered run; live detector evaluation is owner-gated and OUT OF SCOPE here.)

## Constraints
- OFFLINE ONLY; no live API calls; no `RUNNER_LIVE`/token dependence in code or tests.
- No frozen-schema (common/schema.py), harness/metrics.py, or paper/preregistration/ changes. Reuse
  harness/label.py outputs; if a genuinely new persisted field seems needed, STOP and flag for an
  amendment (do not edit the schema).
- Keep the framing strict: Hypothesis Surfacing (divergence), NEVER no-GT right/wrong; consensus strength
  is NOT a headline signal.
- `python -m pytest -q` fully green (whole suite).

## Process / provenance
Record model family (Claude) in a header comment. Commit in the worktree (trailer:
`Co-authored-by: copilot <copilot@users.noreply.github.com>`); push `slice/phase3-detector`. The Manager
opens the PR + spawns a NON-Claude (GPT) cross-family audit (verify: k=0 false-surfacing < 10% on a real
control set; no gold-target leakage; I_perp non-firing per A04; no frozen-file changes; tests
non-tautological), then merges after the Law-4 gate. Do NOT open a PR yourself; do NOT run live.
