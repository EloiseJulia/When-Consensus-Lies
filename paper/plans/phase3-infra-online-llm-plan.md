# Phase 3-INFRA — Online LLM path (GitHub Models) + provenance re-routing — slice plan

> Owner-approved (2026-07-15): GitHub Models token verified (User-scope env `GH_MODELS_TOKEN`, 93 chars).
> Orchestrator-only: spawned sub-agent in a worktree; implementer family ≠ auditor family. This is the
> gating infrastructure for ALL real-model runs. NO full-scale run in this slice — ends at a cheap
> MINI-PILOT smoke, results reported before scale-up (Hard Law 1 + owner instruction).

## Verified capability (probe results, 2026-07-15)
- Endpoint: `https://models.github.ai/inference` (OpenAI-compatible; `POST /chat/completions`,
  `Authorization: Bearer <token>`). Catalog: `https://models.github.ai/catalog/models` (37 models).
- Reachable families/slugs (confirmed real completions on ★):
  - **OpenAI** (17): `openai/gpt-4o-mini`★, `openai/gpt-4.1-mini`, `openai/gpt-4.1`, `openai/gpt-4o`,
    `openai/gpt-5`, `openai/gpt-4.1-nano`, …
  - **Meta/Llama** (7): `meta/llama-3.3-70b-instruct`★, `meta/llama-4-scout-17b-16e-instruct`,
    `meta/meta-llama-3.1-405b-instruct`, …
  - **DeepSeek** (3): `deepseek/deepseek-r1`, `deepseek/deepseek-r1-0528`, `deepseek/deepseek-v3-0324`.
  - **Mistral AI** (4): `mistral-ai/mistral-small-2503`, `mistral-ai/mistral-medium-2505`,
    `mistral-ai/ministral-3b`★, `mistral-ai/codestral-2501`.
  - **Microsoft/Phi** (5): `microsoft/phi-4`, `microsoft/phi-4-reasoning`, `microsoft/phi-4-mini-*`.
  - **Cohere** (1): `cohere/cohere-command-a`.
- **logprobs:** supported on **OpenAI** models (`logprobs:true` → token logprobs returned). NOT exposed
  on Llama/Mistral/etc. → `logit_conf` is available-only-on-OpenAI; all other families use verbalized
  confidence (owner step 3). Anthropic + Google are NOT on GitHub Models → dropped.

## Deliverable 1 — `common/llm.py` online mode (OpenAI-compatible, provider-pluggable)
- Implement `_generate` online branch (replace the `NotImplementedError`). Use the OpenAI-compatible
  `POST {base}/chat/completions` with the token from env. Base URL + token env name configurable
  (default base `https://models.github.ai/inference`; token env: read `GITHUB_MODELS_TOKEN` OR
  `GH_MODELS_TOKEN` — the persistent one is `GH_MODELS_TOKEN`). NEVER log/print the token.
- **Model routing:** map role→(family, model slug) via config; send the slug as the `model` field.
- **logit_conf:** if the model is an OpenAI slug, request `logprobs:true` and populate a confidence
  signal; otherwise leave `logit_conf=None` and rely on verbalized confidence. Document this per-family
  capability. Keep `AgentRun`/`Completion` schema untouched (schema.py FROZEN) — only populate existing
  fields.
- **Caching:** REUSE the existing provenance-aware disk cache (`_cache_key` already includes
  mode|identity|role|prompt|seed). Confirm online responses are cached and re-served deterministically;
  a cache hit must NOT re-call the API. This is the primary cost control.
- **Budget + rate caps (hard):** a configurable max-USD (or max-call) budget and a max-requests/min cap;
  on exceeding budget → raise a clear `BudgetExceeded` and STOP (never silently continue). On HTTP 429
  → exponential backoff with jitter + retry (bounded); on other 5xx → bounded retry; on 4xx (non-429) →
  fail loud (no infinite retry). Log per-call cost/tokens to the existing cost log.
- **Offline default preserved:** `offline=True` remains the default; all existing offline tests must
  still pass unchanged. Online mode is opt-in.

## Deliverable 2 — `common/config.yaml` provenance re-routing (Hard Law 6: constructor≠tested≠judge≠code_reviewer)
Drop `anthropic`/`google`/`qwen` (not on GitHub Models). **FINAL family table (owner-approved 2026-07-15,
Option B — all roles mutually distinct):**

| Role | Family | Slug | Notes |
|------|--------|------|-------|
| constructor | `cohere` | `cohere/cohere-command-a` | outside tested set → keeps R2 cross-family-construction control clean |
| tested_agents.homogeneous | `openai` | `openai/gpt-4o-mini` | shared-prior baseline / ρ-baseline (owner-ruled: strongest deployed shared prior + only family exposing logprobs for the silent-failure signature) |
| tested_agents.heterogeneous | `openai`,`meta`,`mistral-ai`,`deepseek` | `openai/gpt-4o-mini`, `meta/llama-3.3-70b-instruct`, `mistral-ai/mistral-small-2503`, `deepseek/deepseek-v3-0324` | 4-family diverse mix |
| tested_agents.reasoning | `deepseek`,`openai` | `deepseek/deepseek-r1`, `openai/<FRONTIER — verify slug when token live>` | H2 tested on FRONTIER reasoners (deepseek-r1 + an OpenAI o-series/gpt-5). Gives a within-provider H1→H2 gradient (gpt-4o-mini shows convergent-delusion; same-provider frontier reasoner resolves it). **Fallback if no OpenAI frontier reasoner is reachable: `deepseek-r1` alone, documented as a limitation.** |
| judge | `microsoft` | `microsoft/phi-4` | NOT in any tested pool now (Phi freed by moving reasoning off phi-4-reasoning) → fully clean. Used only if executable gold unavailable (rare; all domains use executable gold). |
| code_reviewer | (override per slice) | placeholder | CODE-audit routing only; the Manager overrides per slice so auditor family ≠ implementer family. Orthogonal to the experiment (current code audits: Claude-impl / GPT-audit via task tool). Not part of the experiment family-distinctness requirement. |

Mutual distinctness check: constructor(cohere) ∉ tested{openai,meta,mistral-ai,deepseek} ; judge(microsoft) ∉
tested ∪ {constructor}. ✅ All experiment roles mutually distinct.

**Token-live verification (owner: not a blocker for the table, required before mini-pilot):** once the
rotated token is reachable, confirm (a) the exact OpenAI frontier reasoning slug is on this catalog and
(b) whether it exposes logprobs and (c) its rate limits. If unavailable → fall back to `deepseek-r1`
alone for the reasoning pool and document the limitation. Keep `seeds.global`. Update the header comment
to reflect the GitHub-Models families.

**Token source:** read from env `GITHUB_MODELS_TOKEN` OR `GH_MODELS_TOKEN` (the persistent User-scope var
is currently `GH_MODELS_TOKEN`; the rotated token should be persisted to User scope by the owner). NEVER
log/print the token. Endpoint `https://models.github.ai/inference` (OpenAI-compatible).

## Deliverable 3 — cheap MINI-PILOT (smoke, NOT full-scale)
- A small runnable script (e.g. `scripts/mini_pilot.py`, NOT a pytest that hits the network by default)
  that: loads a HANDFUL (≤3) real bench tasks from ONE primary domain, runs `single` + `sc(k=3)` with
  online mode on 2–3 families, labels via real `label_run`, computes `convergent_delusion`, and prints
  the per-config labels + metric + total token cost. Hard budget cap set very low (e.g. ≤ $0.50). Must
  be idempotent via cache. Guard so it does nothing unless an env flag + token are present (never runs
  in CI/offline).
- Report the numbers to the Manager; do NOT scale up.

## Tests (offline-safe)
- Online path unit tests must NOT hit the network: mock the HTTP call (e.g. monkeypatch urlopen) to
  assert request shape (model slug, auth header present but not logged, logprobs only for openai),
  budget/429 backoff logic, and cache hit-skips-call. All existing offline tests stay green.

## Verification / merge gate (Law 4)
`pip install -e .` + full `pytest -q` green (2x). Cross-family audit 0 BLOCKER/MAJOR (auditor family ≠
implementer; auditor must verify: token never logged, budget cap actually stops, 429 backoff bounded,
cache prevents re-calls, offline default intact, schema.py untouched). `common/schema.py` and
`harness/metrics.py` UNTOUCHED. `config.yaml` change (provenance routing) called out PROMINENTLY in the
PR body (shared-infra + Hard-Law-6 relevant). The MINI-PILOT numbers reported before any full-scale run.

## Provenance
Implementer: Claude/Anthropic. Auditor: GPT family (cross-family). NOTE: `anthropic` is dropped from the
EXPERIMENT routing, but code build/audit provenance (Claude-impl / GPT-audit) is unchanged and orthogonal.
