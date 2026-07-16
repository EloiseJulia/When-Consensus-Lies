# Reasoner budget plan (2026-07-16) — reasoners are the SCARCE resource

> Owner ruling (2026-07-16): "per-model daily caps make reasoners the scarce resource; estimate the calls
> the H1-reasoner + H2-resolution evidence needs, schedule across days, and RESERVE reasoner budget for the
> registered run (don't burn it all on diagnostics)." This plan operationalizes that.

## Observed daily caps (empirical, 2026-07-16 — stored to memory)
- `deepseek/deepseek-r1`: day-capped at **~20 calls** (UserByModelByDay). `openai/o4-mini`: **~25 calls**.
- These are LOW. The reasoning (H2) condition is therefore the binding rate constraint for the WHOLE
  project — far tighter than gpt-4o-mini's daily cap. Plan around it.
- Mitigation: the resumable runner's disk cache makes a cache-hit ZERO calls, so re-runs / resumes are
  free; only NEW (identity) reasoner calls consume the daily cap.

## A. Completing the diagnostic reasoner arm — RE-SCOPED to ESSENTIAL cells only (conserve)
Do NOT re-run all 11 tasks × both reasoners × k=5 (that already partly ran + would waste ~2 days of cap).
Run ONLY the cells that carry reasoner-critical evidence not yet obtained:
- **E1 — H1 persists for reasoners (partly already seen):** confirm CD≈1.0 for a reasoner on the strong H1
  traps `code_quarter_k1`, `policy_overtime_k1`, `data_activeusers_k1` + one k-graded `code_invoice` — 1
  reasoner homogeneous sc (k=5). Some deepseek-r1 cells already completed (cache); only fill gaps.
  ≈ 3-4 tasks × 5 ≈ **15-20 new calls**.
- **E2 — ⭐ H2 reasoners RESOLVE (the key missing piece):** `data_typical_001_k1` median-skew, BOTH
  reasoners, single-pass + sc(k=5) → does the reasoner recover I0 (median) where the weak model defaulted
  to the mean? ≈ 2 reasoners × ~6 ≈ **12 calls**.
- **E3 — subtler-trap cross-model discrimination for reasoners:** weekday, geomean, stddev, casesort ×
  reasoner single-pass, to see the strong(1.0)-vs-subtle(split) contrast holds cross-family with reasoners.
  ≈ 4 tasks × 2 reasoners × 1 ≈ **8 calls**.
- **Total essential ≈ 35-40 new reasoner calls** → ~1-2 cap-days (≈20-25/model/day). Schedule: resume the
  runner (it skips completed cells) on the next 1-2 days after the cap resets; the checkpoint
  (`default_check_checkpoint.jsonl`) makes this idempotent.

## B. RESERVE policy for the registered run
- After the essential diagnostic reasoner arm (A) completes, run NO further diagnostic reasoner calls.
- **Registered-run reasoner estimate (must refine before scale):** the reasoning condition (prereg §1 H2,
  §10 heterogeneous-MAD across 4 families + reasoning-model condition, ~60 items × k-levels × ≥3 seeds)
  will need HUNDREDS of reasoner calls. At ~20-25/model/day this is WEEKS of wall-clock unless scoped.
- **Options to raise with owner before the registered run (do NOT decide unilaterally — scientific/scope):**
  (i) schedule the registered reasoning condition across many days via the resumable runner (cache-backed);
  (ii) pre-register a SMALLER reasoning-condition N (fewer items/seeds for the reasoning models only) with a
  transparent power note — the reasoner daily cap is an external constraint, and asymmetric N by model_class
  is defensible if pre-registered; (iii) seek higher-limit reasoner access. Any N-asymmetry for reasoners
  must be pre-registered (amendment) BEFORE the registered run — flag when we get there.
- **Do not** spend reasoner cap on exploratory re-runs once the essential diagnostic evidence is in.

## C. Sequencing (this holds until the reasoner arm completes AND the I_perp fix lands)
1. NOW (parallel, no reasoner cap needed): labeler/answer-format fix (offline) → re-run the AFFECTED
   non-reasoner items (weak models / cached) to confirm I_perp recovery. [in progress: slice/labeler-format-fix]
2. After cap reset (~24h): resume the runner for the ESSENTIAL reasoner cells (A) only.
3. Re-assess O2 saturation + H1/H2 regime tags WITH reasoner data → finalize the findings.
4. THEN: reversed spot-check gate → owner sign-off → registered mini-pilot → registered run (with the
   reasoner-budget schedule from B).
