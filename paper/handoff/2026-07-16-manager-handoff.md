# Manager Handoff — 2026-07-16

> For a BRAND-NEW manager session with zero access to the retiring manager's context.
> Re-derive everything from git yourself (Hard Law 1); this doc is a map, not gospel.
> You are ORCHESTRATOR-ONLY: write only under paper/, delegate every code change to a spawned
> sub-agent in a worktree, keep implementer-family ≠ auditor-family.
> Companion: paper/decisions/DECISION-LOG.md (every design adjustment + owner ruling, for the paper).

## 0. TL;DR
- Phases 0, 1 (original), 2 (harness+metrics+labeling+integration+nulls): **DONE, merged.**
- Infra for real runs: online LLM path (GitHub Models) + temperature/o-series handling: **DONE, merged.**
- Pre-registration: **FROZEN c0a0393**; **Amendments 01/02/03** all owner-signed & merged (metric frozen throughout).
- **PIVOT (this session):** the original benchmark had **target = the model's natural default** ⇒ competent
  models are CORRECT ⇒ convergent-delusion ≈ 0 ⇒ the pre-registered phenomenon could NOT appear. Owner
  approved a **TARGET/DEFAULT REVERSAL** (target = a NON-default intent; the model's default = a wrong foil)
  with a **combinatorial** interpretation structure for multi-axis tasks and an **H1_external vs H2_derivable**
  regime split.
- **code_spec reconstruction (reversal) = DONE, MERGED (#16 / f6e11c1).** Empirically validated on live
  models (both mistral-small AND llama-3.3-70b converge on the SAME wrong interpretation, CD=1.0, at k=1/2/3).
- **data_analysis + policy_qa reconstruction under the reversal = NOT DONE.** This is the #1 next task.
- **Current authoritative HEAD: origin/main `f6e11c1`.** Local main == origin/main, working tree clean.

## 1. Git ground truth (verified 2026-07-16)
- **origin/main HEAD = `f6e11c1`** (Phase 1-R code_spec reconstruction, #16). Local main is in sync; clean.
- `gh pr list` FAILED this session with a transient "Could not resolve to a Repository" GraphQL error
  (auth/API hiccup, NOT a repo problem — `git remote -v` = https://github.com/EloiseJulia/When-Consensus-Lies.git,
  fetch/push work). Derive PRs from merge-commit messages in `git log` until `gh` recovers.

### PRs (from merge commits; #1–#8 per the 2026-07-15 handoff)
| PR | Title | State | Commit |
|----|-------|-------|--------|
| #1 | Phase 0 scaffold | MERGED | e58c994 |
| #2 | Phase 1-S0 core | CLOSED (subsumed by #3) | — |
| #3 | Phase 1-S1 code_spec (+core) | MERGED | 88f3ae7 |
| #4 | Phase 1-S2 data_analysis | MERGED | 358ee22 |
| #5 | Phase 1-S3 policy_qa | MERGED | 199933c |
| #6 | Phase 2-S2a metrics | MERGED | 385fbdb |
| #7 | data_analysis harness flakiness fix | MERGED | 9bc4341 |
| #8 | Phase 2-S2c run configs | MERGED | 97058a3 |
| #9 | Phase 2-S2b label (structured-answer contract) | MERGED | fc38e9b |
| #10 | Phase 2-S2e answer-format prompt | MERGED | fbe60be |
| #11 | Phase 2-S2d integration test | MERGED | 90f3b2a |
| #12 | Phase 2-S2f R1 label-shuffle null + MVP pilot | MERGED | d5f3453 |
| #13 | Phase 3-INFRA online LLM path (GitHub Models) + Option-B routing | MERGED | 3afe30f |
| #14 | Phase 3-INFRA-2 temperature + o-series handling | MERGED | 76ea1f1 |
| #15 | Schema Amendment 02 (Task.regime) | MERGED | a093783 |
| #16 | **Phase 1-R code_spec reconstruction (target reversal + combinatorial)** | MERGED | f6e11c1 |

### Doc-only commits on main (no PR): prereg freeze c0a0393; Amendment 01 a4fee0f; Amendment 03 e91c63c;
directional findings 43d93b3; design-fork aab2f3d; various spec/plan commits.

### Branches / worktrees — ALL leftover & prunable (everything merged; NO in-flight code, NO uncommitted work)
- Local leftover branches: fix/data_analysis-harness-flaky, slice/phase1-S0-core, slice/phase1-S1-code_spec,
  slice/phase1-S2-data_analysis, slice/phase1-S3-policy_qa, slice/phase2-S2a-metrics, slice/phase2-S2c-run,
  topic/phase1-benchmark. Plus stale worktrees under .worktrees/ (phase1-*, phase2-*). **All safe to prune**
  (`git worktree prune`; delete merged branches). The reconstruction worktrees (phase1r-code_spec, phase3-*,
  schema-regime, phase2-*) were already removed after merge.
- **No uncommitted work anywhere.** Working tree clean. (One transient incident: a stray copy of the #16
  reconstruction appeared in the MAIN checkout's working tree during merge; it was `git checkout --`
  discarded — the content is safely in #16. Lesson: after `gh pr merge`, `git pull --ff-only` can fail if the
  worktree has leftover edits; verify `git status` clean first.)

## a. STATE by phase
- **Phase 0 (scaffold)** — DONE. common/ (schema.py FROZEN — now +Task.regime via Amdt 02), config.yaml,
  llm.py, tests, CI. #1.
- **Phase 1 (ORIGINAL benchmark, 3 domains)** — DONE & merged (#3/#4/#5). BUT superseded in design: see Phase 1-R.
- **Phase 1-R (RECONSTRUCTION under target reversal)** — **code_spec DONE, MERGED #16.**
  data_analysis + policy_qa **NOT started** (they still contain the OLD target=default construction on main).
- **Phase 2 (harness+metrics+label+run+integration+nulls)** — DONE & merged (#6–#12). Metrics: primary =
  `convergent_delusion` (false_consensus_rate); secondaries marginal_rho/a_maj/ece/confidence_accuracy_slope;
  golden tests. Label: executable-gold + policy_qa structured FINAL-ANSWER contract. Run: 6 configs +
  per-domain answer-format instruction + temperature. R1 label-shuffle null (harness/nulls.py) + MVP pilot.
- **Phase 3-INFRA (online LLM path)** — DONE & merged (#13/#14). Real GitHub Models calls verified.
- **Phase 3 (detector), Phase 4 (rep-analysis), Phase 5 (sim-users), Phase 6 (stats/figures), Phase 7
  (writing)** — NOT started.
- **Current HEAD: origin/main f6e11c1.**

## b. PROVENANCE CONFIG (common/config.yaml — Option-B, owner-approved 2026-07-15)
EXPERIMENT routing (for the paper runs; Hard Law 6 — all experiment roles mutually distinct):
- **constructor:** cohere / cohere-command-a  (outside every tested pool → clean R2 cross-family construction)
- **tested_agents.homogeneous (ρ-baseline):** openai / gpt-4o-mini  (strongest deployed shared prior; ONLY
  GitHub-Models family exposing logprobs → logit_conf for the silent-failure signature)
- **tested_agents.heterogeneous:** openai/gpt-4o-mini, meta/llama-3.3-70b-instruct,
  mistral-ai/mistral-small-2503, deepseek/deepseek-v3-0324  (4-family diverse mix)
- **tested_agents.reasoning (H2 condition):** deepseek/deepseek-r1, openai/o4-mini  (both live-verified;
  o4-mini 160 req/60s; logprobs NOT supported on reasoning models → verbalized confidence only)
- **judge:** microsoft / phi-4  (outside all tested pools; used ONLY if executable gold unavailable — rare)
- **code_reviewer:** placeholder mistral-ai/mistral-medium-2505 — Manager OVERRIDES per slice so auditor
  family ≠ implementer family. This is CODE-audit routing, orthogonal to the experiment.
- seeds.global = 20260713.

CODE-CONSTRUCTION provenance held on EVERY audited slice this session: implementer = **Claude/Anthropic**,
auditor = **GPT (gpt-5.6-sol)**. Cross-family invariant HELD on: label (#9, 4 rounds), answer-format (#10),
integration (#11), R1-null/pilot (#12), online-llm (#13, 4 rounds), infra2 (#14), schema-regime (#15),
code_spec reconstruction (#16, 3 rounds). NOTE the two provenance planes: config.yaml routing is for the
EXPERIMENT; the CODE was Claude-built / GPT-audited. Keep the next auditor a NON-Claude family.

## c. PRE-REGISTRATION STATUS  🔒 FROZEN + 3 AMENDMENTS (all metric-frozen)
- **FROZEN: paper/preregistration/2026-07-15-prereg.md @ c0a0393** (owner-signed). Locks: H1/H2 hypotheses,
  the construction-time H1/H2 regime criterion (§2), PRIMARY metric = convergent_delusion, secondaries,
  co-primary robustness nulls (R1 label-shuffle POPULATION-LEVEL/cross-item; R2 cross-family construction),
  silent-failure signature, detector false-surfacing headline, decision rules, sample sizes. Pre-freeze
  integrity fix: R1 corrected from within-item (a no-op for convergent_delusion) to cross-item reshuffle.
- **Amendment 01 (a4fee0f):** target/default REVERSAL — target = NON-default intent; model default = wrong
  foil. Rationale: target=default ⇒ CD≈0 ⇒ H1 untestable (construct-validity fix, NOT effect-maximizing).
- **Amendment 02 (a093783, PR #15):** add `Task.regime: Optional[str]` ∈ {H1_external, H2_derivable, None};
  validated + backward-compatible; stores the pre-registered per-task regime tag.
- **Amendment 03 (e91c63c):** COMBINATORIAL interpretation sets for reversed multi-axis tasks. Per variant
  deleting subset S (|S|=k'): interpretations = full 2^k' cross-product (each stacked axis ∈ {target,default}),
  I0 = all-target, combined-all-default foil MARKED (via a `__combdef` gold_check-name convention, since the
  frozen Interpretation dataclass has no description field), partial-default combos ALSO labeled. Invariant:
  len(key_questions)==k' AND len(interpretations)==2^k' AND exactly one combined-default marker AND 100%
  distinguishable. **Metric-integrity guardrail (owner):** convergent_delusion measures the modal wrong over
  the FULL combinatorial set — convergence on a PARTIAL-default combo still counts; do NOT narrow to the
  combined-default foil only. Report BOTH (any-shared-wrong AND combined-default) in analysis.
- **LOCKED:** metric definitions (unchanged since freeze), R1/R2 nulls, decision rules, regime criterion.
  Metric NOT silently narrowed — verified: harness/metrics.py.false_consensus_rate operates over all labels.
- **OPEN (still to pre-register/verify before scale):** the reversed spot-check GATE sign-off on the fully
  reconstructed 3-domain benchmark; the empirical per-regime default-check confirming each task's tag
  (owner ruled the EMPIRICAL check is the FINAL arbiter, not the a-priori heuristic).

## d. OPEN THREADS / next steps (dependency order)
1. **[FIRST] Reconstruct data_analysis + policy_qa under the reversal** (parallel; same template as code_spec
   #16). Use paper/specs/phase1-benchmark-reversal-spec.md (Examples: A code_spec fiscal-quarter=H1,
   B policy_qa 35h-overtime=H1, C data_analysis median-under-skew=H2, D data_analysis org-KPI=H1). Each:
   single-axis convention units + stacking + full 2^k combinatorial interp sets + __combdef marker + regime
   tags + executable gold 100% distinguishable + per-variant invariant. data_analysis MUST include the H2
   median-under-visible-skew demonstrator (the only clean H2 so far; code H2 was dropped because weak models
   resolve it). Cross-family (GPT) audit each; keep implementer=Claude.
2. **[dep:1] Empirical per-regime default-check** on all reconstructed tasks (live GitHub Models, temp>0):
   H1 → homogeneous agents (incl. reasoning) converge on a wrong combination; H2 → reasoners RESOLVE, weaker
   default wrong. Reclassify/EXCLUDE any task whose behavior ≠ its tag (owner: empirical = final arbiter).
3. **[dep:2] Reversed spot-check gate → OWNER SIGN-OFF.** Manager does NOT self-approve scaling.
4. **[dep:3] Resumable, cache-backed, RPM-throttled runner** (checkpointed; resumes across rate-limit stalls
   / days). Token-independent to build+offline-test. (todo: resumable-runner, pending.)
5. **[dep:4] Registered mini-pilot** (prereg §11) on a small real batch AFTER gpt-4o-mini daily cap resets;
   confirm convergent_delusion>0 real vs ≈CD0 under shuffle, integration+golden tests included.
6. **[dep:5] Full-scale runs** → **Phase 6 stats/figures** (mixed-effects; ρ–ambiguity phase diagram; H1b
   monotonicity; report CD with/without I_perp — see limitations). **Phase 3 detector** can start interface
   design in parallel once labels stable. **Phase 4 rep-analysis (GPU)** deferred to v2. **Phase 5 sim-users**
   in the 0→2→5→6 chain.
7. Housekeeping: prune merged branches/worktrees (all safe now).

## e. TOKEN / RATE-LIMIT notes (GitHub Models)
- Endpoint https://models.github.ai/inference (OpenAI-compatible). Token in **User-scope env
  `GITHUB_MODELS_TOKEN`** (93 chars; rotated 2026-07-15 — owner will DELETE the User var after the project).
  A DIFFERENT process cannot see a token set only in the owner's interactive terminal; read from User scope:
  `[Environment]::GetEnvironmentVariable('GITHUB_MODELS_TOKEN','User')`. **NEVER print/log the token.** The
  OLD var `GH_MODELS_TOKEN` (also 93 chars) is the EXPOSED/rotated-out token — do NOT use it (the client
  falls back to it only if GITHUB_MODELS_TOKEN is unset; prefer the new one).
- **RATE LIMITS are the real constraint (cost is trivial, ~$0.0001/call):** per-model, MIXED. o-series
  (o4-mini) ~160 req/60s; cohere/phi-4/mistral healthy. **gpt-4o-mini (the homogeneous ρ-baseline) has a
  per-DAY cap** (hit 2026-07-15, ~12h reset; header x-ratelimit-type=UserByModelByDay). ⇒ full-scale CANNOT
  finish in one session; needs the resumable runner + aggressive disk cache (client cache already keys on
  mode|identity|role|prompt|seed|temperature and a cache hit makes ZERO HTTP calls).
- Client safety (all cross-family audited): token never logged (scrubbed; raised outside except → no
  __context__ leak); hard budget PRE-AUTHORIZATION (utf-8 byte input upper bound + max_tokens sent → true
  upper bound); bounded 429/5xx backoff (≤6) + finite timeout; per-attempt RPM recording; BudgetExceeded is
  permanent (not retried). Reasoning models: max_completion_tokens, no logprobs/temperature.
- **Resumable runner: NOT built yet** (todo pending). scripts/mini_pilot.py exists (double-guarded:
  RUN_MINI_PILOT=1 AND token present, else no-network exit 0) but is a smoke, not the full runner.

## f. KNOWN LIMITATIONS / documented boundaries
1. **I_perp inflation of convergent_delusion (OPEN — needs owner ruling, touches frozen metric):** the frozen
   false_consensus_rate counts the modal WRONG label INCLUDING the degenerate `I_perp` bucket. In the
   code_spec default-check, llama converged on `I_perp` at k=2/k=3 (off-axis conventions not in our 2-values
   set). Multiple agents at I_perp for DIFFERENT reasons is NOT true convergent delusion (report §2.2 wants
   consensus on the SAME I_k). Recommended: keep the frozen metric as-is, but in Phase-6 analysis report CD
   BOTH with and without I_perp (a robustness/reporting choice, not a metric change). RAISE with owner before
   full-scale. (This is the single most important open scientific-validity item.)
2. **CD saturates at 1.0** on small models at all k in code_spec ⇒ the H1b *rising-with-k* gradient is not
   visible with mistral/llama alone. Need the heterogeneous/reasoning pool + more/graded tasks to see
   monotonicity; or accept "CD high across k" and test the H1/H2 REGIME contrast as the headline.
2b. **data_analysis + policy_qa on main are still the OLD target=default construction** — do NOT run
   experiments on them until reconstructed (they will give CD≈0, the very artifact we fixed).
3. **Harness is not a security sandbox** (cooperative-candidate threat model; OS sandbox = future work).
4. **Simulated users ≠ humans:** every human-facing claim must say "simulated decision-maker" with the
   Lost-in-Simulation caveat. Phase-5 sim-users are load fixtures, not psychology.
5. **Reasoning-model H2 in code is weak:** weak models already resolve code sortnum-style H2 (dropped from
   code_spec). H2 demonstrators live in data_analysis (median-under-visible-skew).
6. **Detector = Hypothesis Surfacing**, never no-GT right/wrong judgment (false-surfacing rate on k=0 controls
   is the headline; consensus strength cannot separate true/false consensus).

## g. LESSONS / COST for the successor
- **Trust git + independent live checks, not agent self-reports.** Multiple "all green" reports were correct
  on tests but hid deeper design flaws only a LIVE model run exposed (the target=default artifact; the
  prompt-leakage of a deleted axis). ALWAYS run a small real-model default-check on reconstructed tasks — it
  is the fastest way to catch a benchmark that can't exhibit the phenomenon.
- **The benchmark, not the harness, is the science.** The biggest win this session was catching (via a
  directional real batch) that target=default made the whole thing measure "models do the obvious thing." A
  clean reversed trap is inherently SINGLE-AXIS; multi-axis needs the combinatorial structure (Amdt 03).
- **Cross-family audit is worth it on shared infra.** The online-LLM path took 4 audit rounds to close real
  money/security bugs (token leak via __context__, budget not a true upper bound, RPM bypass, no timeout).
  Mocked tests passed throughout; only the hostile GPT auditor's scratch tests found them.
- **Delegate every code edit; keep manager context lean.** Read to triage (Manager may READ), give the fix
  agent an EXACT narrow diagnosis, and prefer write_agent follow-ups over churning fresh sessions. Don't edit
  the main checkout — if a stray edit appears, `git checkout --` it (content is in the merged PR).
- **Rate limits, not cost, gate scale.** Plan for a resumable, cache-backed, day-spanning runner from the start.
- **Owner owns every scientific judgment.** Escalate: target-is-natural-default rulings, metric-touching
  choices (I_perp), design pivots, and the pre-registration/spot-check gates. The empirical default-check is
  the FINAL arbiter of H1/H2 tags (owner ruling).

## h. Source-of-truth pointers
- Laws/method: AGENTS.md; AI-Native-Workflow-可复用模板.md; AI-Execution-Plan.md.
- Frozen interface: common/schema.py (Task now has regime via Amdt 02). Routing: common/config.yaml.
- Metric + golden: harness/metrics.py, tests/test_metrics_golden.py, tests/test_marginal_rho.py.
- Null: harness/nulls.py (R1). Labeling: harness/label.py. Run: harness/run.py (+answer_format_instruction,
  temperature, is_reasoning_model). Online client: common/llm.py.
- Benchmark: bench/build.py (FullSpec.regime, power-set invariant, __combdef), bench/code_spec (RECONSTRUCTED),
  bench/data_analysis + bench/policy_qa (OLD — to reconstruct), bench/data/*.jsonl.
- Pre-registration: paper/preregistration/2026-07-15-prereg.md (+ amendments 01/02/03).
- Specs/plans: paper/specs/phase1-benchmark-reversal-spec.md (Examples A–D + reversed gate + staged plan);
  paper/plans/phase3-infra*-plan.md; paper/research/2026-07-15-directional-findings.md +
  2026-07-15-reconstruction-design-fork.md.
- **Decision log (for the paper): paper/decisions/DECISION-LOG.md.**
- This handoff: paper/handoff/2026-07-16-manager-handoff.md. Prior: 2026-07-15-manager-handoff.md.
