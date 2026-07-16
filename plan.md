# Slice plan — default-check diagnostic (EXPLORATORY)

Implementer family: **Claude (Anthropic)**. Auditor MUST be non-Claude (GPT).
The **Manager** runs the LIVE API calls after a clean cross-family audit. This slice
ships OFFLINE-verifiable code only; no live calls are made here.

Spec followed: `paper/plans/2026-07-16-default-check-diagnostic-plan.md`.
Frozen / do-not-touch: `harness/metrics.py`, `common/schema.py`,
`paper/preregistration/`, and the registered `bench/data/*.jsonl` (diagnostic traps
live in a SEPARATE module `bench/diagnostic/`, never written to the registered jsonl).

## Deliverable 1 — SUBTLER-trap diagnostic fixture (`bench/diagnostic/`)

4 deliberately SUBTLER reversed traps (≥1 per executable-gold domain), each a k=1
FullSpec assembled with the existing `bench.build` engine, executable gold via the
existing `CodeChecker`/`DataChecker` subprocess runners, 100% distinguishable,
regime-tagged, FAIR (a human reading the full latent_spec agrees the non-default I0
is genuinely intended). All keep the REVERSED property: I0 = non-default true intent;
the `[combined-default]` foil = the model's natural default (wrong).

"SUBTLER" = the deleted convention's population-default is LESS universally the
model's first choice than in the corresponding strong trap, so a discriminating
`convergent_delusion` should land strictly between 0 and 1 (the O2 saturation
instrument), instead of saturating at 1.0.

| id (base)          | domain        | I0 (target, non-default)                | default foil (wrong)                | regime      | weaker-default rationale vs the strong trap |
|--------------------|---------------|-----------------------------------------|-------------------------------------|-------------|---------------------------------------------|
| diag_weekday_001   | code_spec     | US business calendar: Sunday=1..Sat=7   | ISO-8601 Monday=1..Sun=7            | H1_external | Strong trap `code_quarter` (calendar quarters) is a near-universal single default; here BOTH weekday conventions are pervasive — Python `isoweekday()` is Monday-first, but Excel `WEEKDAY` default & US calendars are Sunday-first — so a meaningful minority independently picks each → split, CD<1. |
| diag_casesort_001  | code_spec     | case-INSENSITIVE alphabetical order     | Python `sorted()` case-sensitive ASCII (upper before lower) | H1_external | Naive code reaches for `sorted()` (case-sensitive), but "alphabetical" colloquially means case-insensitive → genuine ~50/50 split, neither dominant. Inputs mix cases so ASCII order and case-insensitive order DIFFER on every case (no aliasing; `list(set())`/codepoint order cannot masquerade as either reading). |
| diag_quartile_001  | data_analysis | exclusive-method Q1 (Excel PERCENTILE.EXC / stdlib `quantiles` default) | inclusive linear-interp Q1 (numpy.percentile default / R-7) | H1_external | Q1 has several widely-used definitions giving DIFFERENT numbers on the same data — numpy users get linear/inclusive, Excel-EXC/textbook/stdlib users get exclusive. Genuine methodological ~50/50 split, far weaker than an arbitrary external KPI threshold. |
| diag_stddev_001    | data_analysis | sample std (Bessel, ÷ n-1)              | population std (÷ n)                | H1_external | Classic genuine split: numpy defaults population (ddof=0), pandas/`statistics.stdev` sample (n-1). Models genuinely disagree → weak default. Much weaker pull than an external policy threshold. |

Distinguishability: every reference implementation passes ONLY its own checker across
≥2 test cases that differ on every case; validated in the offline test (100%).

Labeling: diagnostic tasks keep the REAL `domain` ("code_spec"/"data_analysis") so
`answer_format_instruction` in `harness/run.py` still asks for a single python block,
but their ids are prefixed `diag_`. A thin custom `label_run_fn` (in the driver) routes
`diag_` tasks to `bench.diagnostic` checkers and defers everything else to the frozen
`harness.label.label_run`. `harness/label.py` is NOT modified.

## Deliverable 2 — driver `scripts/default_check.py` (offline-guarded)

Double-guard (mirrors `scripts/mini_pilot.py`): CLI `main()` does nothing unless BOTH
`RUN_DEFAULT_CHECK=1` AND a token (`GITHUB_MODELS_TOKEN`/`GH_MODELS_TOKEN`) are present;
otherwise prints "skipped" and exits 0. Live execution USES `harness/runner.py`
(resumable/throttled/cache-backed). Token is NEVER logged.

### Task set (SMALL, 11 tasks)
Strong H1 traps: `code_quarter_001_k1_fiscal_year_start`,
`policy_overtime_001_k1_overtime_threshold`, `data_activeusers_001_k1_active_user_threshold`.
k-gradient (saturation-vs-k): `code_invoice_001_k1_fiscal_year_start`,
`code_invoice_001_k2_fiscal_date`, `code_invoice_001_k3_all`.
H2 resolution: `data_typical_001_k1_central_tendency`.
Subtler traps (Deliverable 1): the 4 above.

### Pool (owner ruling — reasoner-vs-weaker weighted; gpt-4o-mini EXCLUDED)
- Homogeneous within-ensemble convergence via config `sc` (k=5, temperature 0.7),
  REASONER-WEIGHTED (both reasoners + one weak):
  - `deepseek/deepseek-r1` (reasoner), `openai/o4-mini` (reasoner),
    `mistral-ai/mistral-small-2503` (weak).
- Heterogeneous diverse pool via config `single` (temperature 0.0, one independent
  sample per family): `deepseek/deepseek-r1`, `openai/o4-mini`,
  `mistral-ai/mistral-small-2503`, `meta/llama-3.3-70b-instruct` (4-family pool).
- Single reasoner resolution pass (H2) = the `single` runs of the two reasoners on the
  H2 task.
- **`openai/gpt-4o-mini` is EXCLUDED** — protects its daily cap for the registered mini-pilot.

Two Runner invocations share ONE checkpoint + cache (resumable/idempotent):
- Pass A: `configs=["sc"]`, models = 3 homogeneous (2 reasoner + 1 weak) → 11×3×5 = 165 calls.
- Pass B: `configs=["single"]`, models = 4 pool → 11×4×1 = 44 calls.
Estimated live budget per model (≈209 calls): deepseek-r1 66, o4-mini 66,
mistral-small 66, llama-70b 11 → **reasoner total 132 ≥ weak total 77** (reasoner-weighted).
Nominal cost ≈ $0.30, hard cap $0.50 (Runner stops
cleanly + resumes). RPM throttled conservatively (default 10). GitHub Models is
free/rate-limited, so calls (not dollars) are the binding constraint.

### Reporting (per task, regime, model_class)
`convergent_delusion` computed BOTH ways:
- (i) **enumerated-foils-only**: modal wrong over ENUMERATED foils (I_perp NOT eligible
  as the modal-wrong, but I_perp agents STAY in the denominator) — a thin helper in the
  script, NOT a change to `harness/metrics.py`.
- (ii) **frozen** `false_consensus_rate` with I_perp eligible (Amendment-04 pair).
Plus: the **I_perp RATE**, **resolve-to-I0 rate** (H2: do reasoners RESOLVE to I0 vs
default-wrong H1), and the **CD-vs-k curve** for the `code_invoice` family (k1/k2/k3).
Emits a machine-readable JSONL summary AND a human-readable table; prints total calls,
per-model counts, total cost.

## Offline test (`tests/test_default_check.py`)
1. End-to-end offline: run the driver's `run_diagnostic` against an OFFLINE mock
   `LLMClient` (no network/token) → verifies select→run→label→CD/I_perp report works
   and produces well-formed rows (all I_perp under the mock).
2. CD math: on a CRAFTED label set, assert enumerated-only vs with-I_perp CD differ
   correctly (e.g. `["I1","I1","I_perp","I_perp","I_perp"]`, target I0 → frozen 0.60,
   enumerated 0.40) and resolve-rate/I_perp-rate are exact.
3. Distinguishability: every diagnostic task validates 100% (reference candidate passes
   ONLY its own checker; foils match ≤1 checker).
`python -m pytest -q` fully green.

## Provenance
Header `# constructed by: Claude (Anthropic) family` on new source. Commit trailer
`Co-authored-by: copilot <copilot@users.noreply.github.com>`. Push
`slice/diagnostic-default-check`. No PR (Manager audits then runs live).
