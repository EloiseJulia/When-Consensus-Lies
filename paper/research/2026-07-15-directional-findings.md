# Directional Real-Batch Findings — 2026-07-15 (pre-scale checkpoint)

> Manager research finding from the owner-approved directional real-model batch (GitHub Models,
> working models mistral-small + llama-3.3-70b, homogeneous k=5 ensembles over code_spec + policy_qa
> k≥2 tasks). Purpose: sanity-check that convergent delusion (CD>0) is observable before scaling.
> **Reliability caveat:** the long batch hit transient rate-limit noise (some cells mislabeled I_perp
> that were clean I0 on careful re-check). Treat cell-level numbers as directional, not final. The
> STRUCTURAL findings below were confirmed by clean per-seed re-checks.

## What we saw (directional)
Across 16 (task×model) cells: ~9 CORRECT-CONSENSUS (models agree on the TARGET I0 → CD≈0) and ~7
CONVERGENT-DELUSION (models agree on the SAME WRONG interpretation → CD≈1). Clean re-checks confirmed
e.g. overtime = all-I0 (correct), and code_csv-k2 / code_count-k2 = both models on a non-target.

## Finding 1 (PIVOTAL — benchmark design): target = the model's natural default on many tasks
Inspecting the benchmark: **the target I0 is constructed to be "the natural default a reasonable
unaware solver would pick."** Examples:
- code_spec sort: I0 = ascending+stable (Python's default). Models default → I0 → **correct**.
- policy_qa overtime (45h @ $20): I0 = $950 (standard 40h/1.5x). Models compute → $950 → **correct**.
Consequence: a competent model does the natural default = the target = **correct**, so **CD≈0**
(correct-consensus) on those tasks. **This is backwards for the thesis.** Convergent/silent consensus
failure requires the model's prior DEFAULT to be a WRONG interpretation while the user's true hidden
intent (target) is the NON-default (cf. the report's canonical trap: model defaults to *calendar* Q1
while the user's true intent is *fiscal* Q1 → default ≠ target → silent failure). Our construction set
target = default, which largely PREVENTS the phenomenon.

The convergent-delusion cells we DID observe (code_csv-k2, code_count-k2, tip) are exactly the tasks
where the model's ACTUAL default diverged from the constructor's labeled "natural default" — i.e.,
accidental prior-traps. This confirms: **the phenomenon appears iff target ≠ the model's real default.**

## Finding 2 (INFRA): no temperature control → degenerate ensembles
The online client sends NO `temperature` (API default). Observed: mistral produced near-identical
outputs across all 5 seeds (same length, same answer). So homogeneous/SC "ensembles" collapse to
~identical samples → the within-ensemble convergent-delusion measurement is degenerate. The
pre-registered ablation needs temperature ∈ {0, 0.3, 0.7, 1.0} (report §7.5). `run.py`/`llm.py` must
set per-config temperature.

## Finding 3 (INFRA): o-series / reasoning models are incompatible with the current request
The client sends `logprobs:true` for ALL openai slugs and `max_tokens` for all models. o-series/gpt-5
(our H2 reasoning pool, e.g. openai/o4-mini) REJECT `logprobs` (400 "unsupported_parameter") and expect
`max_completion_tokens` (not `max_tokens`) with no temperature/logprobs. The client will 400 on the
reasoning condition. Needs per-family request handling (reasoning models: no logprobs, no temperature,
max_completion_tokens; verbalized confidence only).

## Finding 4 (INFRA): rate-limit noise on long runs
gpt-4o-mini is daily-capped; long unthrottled batches produced transient bad/empty outputs (spurious
I_perp). Confirms the need for the resumable, cache-backed, RPM-throttled runner + repeated-run
verification before trusting any numbers.

## Recommendation (pre-scale, ordered)
1. **[owner decision — pivotal] Benchmark target/default policy.** Reconstruct tasks so the TARGET is a
   deliberately NON-default hidden intent (genuine prior-trap: default = a non-target foil), so a
   defaulting model fails — the only way convergent/silent consensus failure can appear. This REVERSES
   the earlier "target = natural default" construction ruling. It does NOT change the frozen metric
   (convergent_delusion) — it makes the benchmark actually capable of exhibiting it (a validity fix,
   permitted under prereg "engineering/prompts may be refined"). Alternative (weaker): keep construction
   but FILTER/label tasks by whether they are genuine traps, and report only trap tasks — but this is
   post-hoc and reviewer-vulnerable; deliberate construction is stronger.
2. **[infra] Add temperature control** (per-config temp; ablation levels) to run.py/llm.py.
3. **[infra] Fix o-series/reasoning request handling** (no logprobs, max_completion_tokens, verbalized
   confidence) so the H2 reasoning condition works.
4. **[infra] Build the resumable, cache-backed, RPM-throttled runner** (checkpointed, resumes across
   rate-limit stalls / days).
5. **[verify] Re-run a clean directional pilot** on genuine-trap tasks with temperature diversity, then
   proceed to the registered mini-pilot + full-scale.

## Bottom line
The machinery (online path, executable-gold labeling on real outputs) WORKS. But the directional batch
surfaced a pivotal design issue — the benchmark's target=default construction largely prevents the very
phenomenon we pre-registered to measure — plus two real infra gaps (temperature, o-series). These must
be resolved BEFORE scaling; otherwise a full run would mostly measure "models do the obvious thing"
(CD≈0) rather than silent consensus failure.
