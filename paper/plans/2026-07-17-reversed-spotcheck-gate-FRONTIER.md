# Reversed Spot-Check Gate — FRONTIER roster (RE-ISSUE for OWNER SIGN-OFF, 2026-07-17)

> SUPERSEDES `2026-07-17-reversed-spotcheck-gate.md` (which validated the regime tags on the OLD
> GitHub-Models roster deepseek-r1/o4-mini). Amendment 06 adopts the frontier proxy roster; per A06 §6 the
> gate must be RE-ISSUED on the frontier models. This package consolidates the frontier evidence (rows
> 49-52 of the decision log). **Nothing is scaled until you sign §7.**

## 0. What is being gated
The reversed 3-domain benchmark on `main` (code_spec #16, policy_qa #17, data_analysis #18 + 2 harder H2
demonstrators #29), reconstructed under Amendment 01 (target = NON-default true intent; model default =
wrong foil) + Amendment 03 (combinatorial 2^k' interpretation sets) + Amendment 02 (`Task.regime`).
Evaluated on the **frontier proxy roster** (Amendment 06): OpenAI gpt-5.4/gpt-5.6-sol/gpt-4o-mini, Anthropic
claude-opus-4.8/sonnet-4.6/haiku-4.5, Google gemini-3.1-pro/3.5-flash, plus legacy-weak gpt-3.5-turbo.

## 1. Structural guarantees (verified on `main`, apply to ALL task variants — UNCHANGED by roster)
| Domain | Tasks | Distinguishable | Regime tags | Invariants |
|--------|-------|-----------------|-------------|------------|
| code_spec | 20 | **20/20 (100%)** | all H1_external | ✅ per-variant `len(key_questions)==k'`, `len(interps)==2^k'`, exactly-one I0, one `[combined-default]`, k0 empty |
| data_analysis | 8 (+2 harder H2: avgprice, rate) | **100%** | H2_derivable (typical/avgprice/rate) + H1_external (activeusers, report) | ✅ same |
| policy_qa | 14 | **14/14 (100%)** | all H1_external | ✅ same |
- Executable gold only (never LLM-judge). Cross-family construction: constructor = `cohere/cohere-command-a`
  (bench build) / `mai-code-1-flash-picker` (A06 role table) — outside every tested frontier family
  (O/A/G). Verified by `python -m bench.validate` + per-domain suites (full suite green on `main`).

## 2. ⭐ EMPIRICAL per-regime default-check on the FRONTIER roster (the FINAL ARBITER — 2026-07-17)
From the frontier default-check, 2 runs (rows 50-51; 313 + 439 calls; **$0.00, no cap**;
`default_check_frontier_summary.jsonl` / `_table.txt`):

| Regime | Representative task | Reasoner (gpt-5.6/opus-4.8/gemini-pro) | Weak (4o-mini/flash/haiku) | Legacy-weak gpt-3.5-turbo | Cross-family pool | Verdict |
|--------|--------------------|------------------|------------|------------|-------------------|---------|
| **H1_external** | code_quarter (fiscal) | CD=**1.000** | CD=1.000 | CD=1.000 | CD=**1.000** | ✅ persists ALL incl. frontier reasoners + cross-family |
| **H1_external** | policy_overtime (35h) | CD=**1.000** | CD=1.000 | CD=1.000 | CD=**1.000** | ✅ persists ALL |
| **H1_external** | data_activeusers (org-KPI) | CD=**1.000** | CD=1.000 | CD=1.000 | CD=**1.000** | ✅ persists ALL |
| **H2_derivable** | data_typical (median-skew) | →I0=**1.000** | →I0≈1.000 | →I0≈1.0 | →I0≈0.667 | ✅ resolved by ALL classes |
| **H2_derivable** | data_avgprice (weighted-avg, harder) | →I0=**1.000** | →I0=1.000 | →I0=1.0 | →I0=1.000 | ✅ resolved by ALL classes |
| **H2_derivable** | data_rate (unequal-interval, harder) | →I0=**1.000** | →I0≈0.9 | →I0≈0.8 | →I0≈0.667 | ✅ resolved by ALL classes |

→ **All H1 tags behave as H1** (default = wrong foil; convergent delusion persists even for FRONTIER
reasoners AND across three independent families — the strongest H1 result). **All H2 tags behave as H2**
(the derivable disambiguator is recovered from the visible data by EVERY class, incl. legacy-weak
gpt-3.5-turbo). **NO task reclassified or excluded** — observed behavior matched every tag.
- ⭐ **Key empirical conclusion (row 51-52):** the two-regime demarcation is a **REGIME MAIN EFFECT**
  (disambiguator LOCATION: external-knowledge vs derivable), **NOT a reasoner-vs-weak interaction** — even
  gpt-3.5-turbo resolves H2. Per owner ruling (row 52) the registered run STILL includes the model_class
  factor and formally tests+reports the pre-registered interaction (expected null, §9); the paper LEADS
  with the regime main-effect. This is a REPORTING framing; no frozen hypothesis/metric/rule changes.
- Coverage note (honest): the default-check covers REPRESENTATIVE families per regime + the subtler diagnostic
  traps, not all variants. Structural guarantees (§1) hold for all; empirical BEHAVIOR is validated on the
  representative set across all three frontier families. Name any additional family to check (cheap).

## 3. Fairness bar (per reversed task — human agrees the non-default is genuinely intended)
Unchanged by roster (fairness is a property of the task, not the model). Each reversed task's `I0` is a
genuine, clearly-specified non-default intent; the DELETED clause reveals it; the model's natural default =
a wrong foil. Cross-family audits confirmed the bar on every family and fixed the two that failed it
(policy mileage-rate → timeless mileage-rounding; code prompt-leakage/GAAP-tie). The harder H2 tasks
(avgprice, rate) passed an audit fairness fix (row 51; I0 uniquely derivable from the retained prompt).

## 4. O2 saturation finding on the frontier roster (informs framing, not a gate blocker)
Frontier strong-trap mean CD=1.0 vs subtler-trap mean CD**enum=0.62 / frozen=0.74** → the CD measure
**DISCRIMINATES** on frontier too (subtler traps split; some resolve). Cross-family convergent delusion is
the clean headline signal; homogeneous saturation is the ρ→1 fake-redundancy demonstration (logprobs
ρ-baseline = gpt-5.4). No benchmark change required.

## 5. I_perp / answer-format (guardrail B — SATISFIED on frontier)
Overall frontier I_perp **0.089** (< 0.20; improved from 0.126 on the old roster). The only elevated cells
are isolated answer-format slips (gpt-5.4 data_typical; a stray data_rate seed) — well under threshold.
Labeler hardened + A04 signed (PR #21/#23). No answer-format blocker.

## 6. Reversed spot-check gate criteria — status (frontier)
1. Full latent_spec specifies the non-default intent; deleted clause reveals it; fair — ✅ (audited).
2. I0 ≠ model default; labeled default foil = the model's ACTUAL frontier default — ✅ (§2, frontier check).
3. Regime tag correct, cross-family re-derived; disagreement → EXCLUDED — ✅ (none excluded).
4. Per-regime empirical default-check (H1 persists incl. frontier reasoners + cross-family; H2 resolved) — ✅ (§2).
5. Executable gold distinguishes all interpretations (100%) — ✅ (§1).
6. Per-variant invariant holds (`len(key_questions)==k'==...`; k0 empty) — ✅ (§1, tests).
7. Cross-family construction (constructor family ≠ tested frontier families O/A/G) — ✅ (constructor cohere/mai-code).

## 7. ⭐ OWNER SIGN-OFF (required before any registered/full-scale run)
- [x] Owner APPROVES the reversed spot-check gate ON THE FRONTIER ROSTER — the reconstructed benchmark is
      READY for the registered mini-pilot → full-scale run. (H1/H2 tags empirically validated on all three
      frontier families; 100% distinguishable; invariants + fairness + cross-family construction hold.)
- [x] Owner co-signs Amendment 06 (frontier roster) — its §6 re-validation is now complete.
- [x] Owner confirms the representative-set validation is sufficient (no additional family requested).

**SIGNED (owner, 2026-07-17).** See DECISION-LOG row 53.

On sign-off, the sequence is: **sign Amendment 06** (frontier roster) + **supersede Amendment 05**
(reasoner N shrink — moot, proxy uncapped) → **registered mini-pilot** (prereg §11) → **full-scale
registered run** (resumable runner) → **Phase 6 real analysis** (merged pipeline) → writing. The Manager
does NOT scale without this sign-off.
