# Phase 3-INFRA-2 — Temperature control + o-series/reasoning request handling (slice plan)

> Owner-approved prerequisite infra fixes (uncontroversial). Orchestrator-only: spawned sub-agent in a
> worktree; implementer family ≠ auditor family. Fixes two real gaps found in the directional batch
> (`paper/research/2026-07-15-directional-findings.md`). Do NOT touch `common/schema.py` or
> `harness/metrics.py` (frozen). This slice is offline-unit-testable (mock HTTP); a Manager live smoke
> confirms real behavior before merge (Hard Law 1).

## Fix 1 — Temperature control (enables non-degenerate ensembles + the pre-registered ablation)
Problem: `common/llm.py` online payload sends NO `temperature`; homogeneous/SC ensembles collapse to
near-identical samples. The pre-registered ablation needs temperature ∈ {0, 0.3, 0.7, 1.0} (report §7.5).
- Add a `temperature: Optional[float]` parameter to `LLMClient.complete(...)` and include it in the
  online payload WHEN provided (and when the model supports it — see Fix 2). Include `temperature` in the
  cache key so different temperatures cache separately (do not collide).
- Thread temperature through `harness/run.py`: each config passes a temperature. Sensible defaults:
  `single` → 0.0 (deterministic); `sc`/`homogeneous-MAD`/`heterogeneous-MAD`/`verifier`/`diverse` →
  a configurable sampling temperature (default 0.7) so ensembles are diverse. Expose an override so the
  ablation can sweep {0, 0.3, 0.7, 1.0}. Keep AgentRun identity unique per sample (seed already varies).
- Offline mock: incorporate temperature into the mock hash so offline behavior stays deterministic but
  temperature-aware (optional but preferred for test realism). Keep offline the default; all existing
  offline tests green.

## Fix 2 — o-series / reasoning-model request handling (unbreaks the H2 reasoning condition)
Problem: the client sends `logprobs:true` for ALL openai slugs and `max_tokens` for all models. o-series
/ gpt-5 (e.g. `openai/o4-mini`, our reasoning pool) REJECT `logprobs` (HTTP 400 "unsupported_parameter")
and require `max_completion_tokens` (not `max_tokens`), and do not accept a non-default `temperature`.
- Add a capability classifier for the model slug, e.g. `is_reasoning_model(slug)` matching
  `openai/o1*`, `openai/o3*`, `openai/o4*`, `openai/gpt-5*` (document the list; make it easily editable).
- For reasoning models: send `max_completion_tokens` (NOT `max_tokens`), do NOT send `logprobs`/
  `top_logprobs`, do NOT send `temperature` (omit → API default). `logit_conf = None` (verbalized
  confidence only). Budget pre-authorization still applies (use `max_completion_tokens` as the output
  bound).
- For non-reasoning OpenAI models: keep `logprobs` (→ `logit_conf`) and `max_tokens` + `temperature`.
- For non-OpenAI models (meta/mistral/deepseek/cohere/microsoft): `max_tokens` + `temperature`, no
  logprobs (already `logit_conf=None`).
- Preserve ALL prior safety guarantees (token never logged; budget pre-auth true upper bound; bounded
  429/5xx backoff; finite timeout; per-attempt RPM recording; cache hit = no HTTP).

## Tests (offline; MUST NOT hit the network)
- Mock HTTP: assert temperature is sent for non-reasoning models when provided and included in the cache
  key (different temps ⇒ different cache entries ⇒ separate calls); assert a reasoning slug (`openai/
  o4-mini`) payload uses `max_completion_tokens`, omits `logprobs` and `temperature`; assert a
  non-reasoning openai slug still sends `logprobs` + `max_tokens` + `temperature`.
- run.py: assert each config passes the expected temperature (single=0.0, sampling configs>0), and the
  ablation override changes it. Keep existing per-config shape/determinism tests green.
- All prior online-path safety tests remain green. No network.

## Verification / merge gate (Law 4)
`pip install -e .` + full `pytest -q` green (2x). Cross-family audit 0 BLOCKER/MAJOR. `schema.py` +
`metrics.py` untouched; `config.yaml` unchanged (routing already set). SHARED-INFRA (llm.py + run.py) —
call out in PR. **Hard Law 1 (Manager, before merge):** a real live smoke — (a) a non-reasoning model
call at temperature 0.7 succeeds; (b) `openai/o4-mini` (reasoning) call succeeds through the client
(previously 400'd). Manager runs this with the token; merge only after both succeed.

## Provenance
Implementer: Claude/Anthropic. Auditor: GPT family (cross-family).
