# Pre-Registration Amendment 06 — Frontier model roster via the Copilot proxy (DRAFT, owner sign-off required)

> Amends the model ROSTER / provenance routing (config.yaml + prereg §10 / Option-B family table) — NOT
> the frozen metric, hypotheses, regime criterion, or decision rules. Motivated by a new capability: a
> local GitHub Copilot API proxy (`ghc-api`, OpenAI-compatible http://127.0.0.1:8313/v1, no token,
> effectively UNLIMITED quota) exposing FRONTIER models across three genuine families. Owner selected
> "adopt for the registered run" (2026-07-17). **STATUS: DRAFT — owner sign-off required before the
> registered run; re-validation on the new roster (below) must complete first.**

## 0. Why (owner-approved direction)
The GitHub-Models roster had per-model DAILY caps (reasoners ~20-25/day) = the binding constraint on the
registered reasoning condition (drove Amendment 05's reasoning-N shrink). The proxy removes that cap AND
upgrades to frontier families. Preliminary signal: gpt-5.6-sol on the fiscal-quarter H1 trap returned
calendar quarters (the wrong default) — i.e. H1 convergent delusion appears to SURVIVE on frontier models
(a STRONGER result). This is a roster/infra change; the measurement contract stays frozen.

## 1. What changes vs what stays frozen
- CHANGES: the model roster + role routing (config.yaml), the online provider (base_url → local proxy),
  and — pending re-validation — the empirical default-check + reversed spot-check gate get RE-RUN on the
  new models.
- FROZEN / UNCHANGED: convergent_delusion + all metric defs (A04), H1/H2 hypotheses, the regime criterion,
  R1/R2 nulls + directions, decision rules (§9), executable gold, the reversed/combinatorial benchmark
  construction (Amdt 01/03), Task.regime (Amdt 02). This amendment does NOT touch any of those.

## 2. ⭐ Provenance-separated roster (Hard Law 6) — OWNER CHOSE OPTION (a) 2026-07-17
Available families on the proxy: OpenAI (O), Anthropic/Claude (A), Google/Gemini (G), Microsoft/mai-code (M).
| Role | Model(s) | Family |
|------|-------------------|--------|
| tested_agents.heterogeneous (⭐ cross-family MAD — the row-35 headline) | gpt-5.4, claude-sonnet-4.6, gemini-3.1-pro-preview | O, A, G |
| tested_agents.homogeneous (ρ→1 fake-redundancy baseline; ⭐ needs logprobs → OpenAI) | **gpt-5.4** (logprobs+temperature capable; sampled repeatedly) | O |
| tested_agents.reasoning (H2 strong-reasoner condition) | gpt-5.6-sol, claude-opus-4.8, gemini-3.1-pro-preview | O, A, G |
| tested_agents.weak (H2 weak-model contrast — reasoner-vs-weak) | gpt-4o-mini (logprobs-capable) / gemini-3.5-flash / claude-haiku-4.5 | O / G / A |
| constructor (R2 cross-family construction control) | mai-code-1-flash-picker | M |
| judge (fallback ONLY — executable gold ⇒ ~never invoked; VESTIGIAL) | mai-code-1-flash-picker | M |
| code_reviewer (CODE-audit plane, orthogonal; implementer=Claude) | gpt-5.6-sol | O |

## 2b. ⭐ logprobs availability (from live proxy probing 2026-07-17) — affects the silent-failure signal
Only **OpenAI** families return logprobs on the proxy: gpt-4o-mini ✓, gpt-5.4 ✓; but gpt-5.6-sol ✗,
claude-* ✗, gemini-* ✗, mai-code ✗. The prereg §5 silent-failure **logit-confidence (`logit_conf`)**
signature is therefore only directly measurable on the OpenAI logprobs-capable models; Claude/Gemini/
reasoners degrade to **verbalized confidence** (the client already does this for reasoning models). ⇒ the
homogeneous ρ-baseline is set to **gpt-5.4** (OpenAI, logprobs+temperature) so the logit-conf silent-failure
signature has a clean home; the cross-family + reasoning conditions use verbalized confidence. Request
shapes handled by the merged provider (proxy always uses max_completion_tokens, requests logprobs
harmlessly, omits temperature for gpt-5.6 / mai-code). This is a REPORTING/coverage note, not a metric change.

## 3. Family-count tension — RESOLVED: owner selected option (a) (2026-07-17)
Tested pool = all 3 frontier families O/A/G (strongest cross-family headline); constructor = mai-code (M);
judge = mai-code (M) but explicitly VESTIGIAL (executable gold is always available ⇒ judge never invoked,
so the constructor/judge family overlap is moot in practice); code_reviewer = OpenAI (O) treated as a
SEPARATE code-audit plane (orthogonal to the experiment, per the handoff). Documented; provenance separation
holds on the experiment plane (constructor M ≠ tested O/A/G ≠ judge-when-used).

## 4. Reasoning vs weak in the frontier roster (H2 operationalization)
On the proxy, all frontier models "reason"; the H2 contrast is REASONER (frontier top: gpt-5.6-sol /
claude-opus-4.8 / gemini-3.1-pro) vs WEAKER (gpt-4o-mini / gemini-3.5-flash / claude-haiku-4.5). The
EMPIRICAL default-check (re-run, §6) is the FINAL arbiter of which models resolve H2 vs default wrong.

## 5. Amendment 05 status under this change
If the proxy is truly unlimited, the reasoner daily-cap that motivated A05's reasoning-N shrink is GONE →
**A05 likely becomes UNNECESSARY** (run the reasoning condition at full §10 N). Recommendation: SUPERSEDE
A05 (keep it as a documented contingency if the proxy proves rate-limited/unstable at scale).

## 6. Required re-validation BEFORE the registered run (cheap now — unlimited)
- RE-RUN the empirical per-regime default-check on the new roster (H1 persists incl. frontier reasoners;
  H2 reasoners resolve, weak default wrong) → RE-ISSUE the reversed spot-check gate on the frontier roster
  for owner sign-off. (The current gate was validated on the old GitHub-Models roster.)
- Confirm the proxy handles the harness request shape (reasoning models: max_completion_tokens; logprobs
  availability for the silent-failure logit_conf signal — verify per family).

## 7. Reproducibility / documentation (reviewer pre-empt)
Document: the endpoint is a local GitHub Copilot API proxy; pin the exact model version strings from
/v1/models; note determinism/seed limits; state the provenance families. Address that a Copilot-proxied
frontier roster is the run substrate (cite versions; note any ToS/reproducibility caveats).

## 8. Sign-off
- [ ] Owner approves adopting the proxy roster for the registered run + the §3 family-count option (a/b/c).
- [ ] Owner confirms the roster in §2 (or adjusts).
- [ ] Re-validation (§6) completed + reversed spot-check gate re-issued on the new roster and signed.
- [ ] A05 superseded (or retained as contingency).

Amendment status: **DRAFT — awaiting owner sign-off + re-validation.** Metric/hypotheses/rules frozen.
