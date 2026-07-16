# Default-check diagnostic — PRELIMINARY findings (2026-07-16, EXPLORATORY)

> EXPLORATORY / diagnostic ONLY — does NOT count toward H1/H2 (pre-registration §11). Purpose: validate
> regime tags, trap behavior, I_perp rate, and the O2 CD-saturation question BEFORE the reversed
> spot-check gate. **This run is PARTIAL** — both reasoners day-capped mid-run (see §0). Numbers are
> directional; the reasoner arm must be completed (resume after cap reset) before any conclusion is
> trusted. Raw artifacts: session files/ (default_check_summary.jsonl, default_check_table.txt,
> default_check_live.log). Total: 122 live calls, $0.176 (cap $0.50), gpt-4o-mini EXCLUDED.

## 0. ⭐ PIVOTAL: both reasoners hit the daily cap mid-run
`deepseek/deepseek-r1` (only 20 calls done) AND `openai/o4-mini` (25 calls) both hit
`x-ratelimit-type=UserByModelByDay` — the SAME per-day cap class as gpt-4o-mini. The resumable runner
stopped them cleanly (resumable checkpoint) — infra worked exactly as designed. BUT:
- The **H2 reasoner-resolution single-pass has ZERO data** ("no reasoner single-pass runs present").
- The core two-regime contrast (H1 persists for reasoners ∧ H2 resolved by reasoners) is UNDERPOWERED.
- **Consequence:** the reasoner arm MUST be completed (resume after ~24h cap reset via the resumable
  runner, continuing from `default_check_checkpoint.jsonl`) before the regime/saturation conclusions hold.

## 1. Strong H1 traps — clean saturation (incl. the reasoner runs that completed)
Homogeneous sc (k=5, temp 0.7), CDenum = CDfrozen = 1.0, I_perp = 0.0:
- `code_quarter_001_k1` (fiscal): reasoner 1.0, weak 1.0.
- `policy_overtime_001_k1` (35h contract): reasoner 1.0, weak 1.0.
- `data_activeusers_001_k1` (org-KPI ≥3): reasoner 1.0, weak 1.0.
→ Strong H1 traps saturate CD=1.0 for BOTH weak AND the reasoner runs that completed — consistent with the
H1 tag (external knowledge unrecoverable, even reasoners default to the wrong foil). Encouraging but the
reasoner n is small (cap).

## 2. ⭐ O2 SATURATION — the discrimination is in the CROSS-MODEL (heterogeneous) condition, not homogeneous
| condition | STRONG traps (quarter/overtime/activeusers) | SUBTLER traps (weekday/casesort/geomean/stddev) |
|---|---|---|
| **homogeneous** (single model, sc) | CD **1.0** | weekday 1.0, casesort 1.0, stddev 1.0, **geomean 0.0** (→I0=1.0) |
| **heterogeneous** (2 diff models, temp 0) | CD **1.0** (both models → SAME foil) | weekday **0.5**, stddev **0.5**, geomean **0.5** (split), casesort 1.0 |

**Interpretation (preliminary):** On a HOMOGENEOUS single-model ensemble, even *subtler* traps mostly
saturate (0 or 1) — a single model at temp 0.7 deterministically commits to ONE reading; there is little
intermediate structure. The CD measure's DISCRIMINATION appears in the CROSS-MODEL (heterogeneous)
condition: strong traps make DIFFERENT models converge on the SAME wrong foil (CD=1.0 = genuine
convergent delusion), while subtler traps make them SPLIT (CD≈0.5). This is exactly the report's thesis
(convergence on the *same* wrong interpretation *across agents*).
→ **Provisional O2 answer (owner-endorsed direction, 2026-07-16; headline NOT locked until reasoner arm):**
CD=1.0 on strong traps is a MIX of (a) genuine cross-agent same-wrong convergence AND (b) a homogeneous
single-model determinism effect. The CLEAN convergent-delusion signal is the HETEROGENEOUS / cross-model
condition. **Lead with cross-model convergent delusion** (independent model families landing on the SAME
wrong foil under a strong shared prior: CD=1.0 strong, ~0.5 subtle) — this preempts the "just single-model
determinism" attack.
→ **⭐ FAKE-REDUNDANCY reframe (owner, connects to report §2.4):** do NOT treat homogeneous saturation as a
confound to hide — reframe it as the **ρ→1 fake-redundancy demonstration**: same-model sampling (SC /
homogeneous-MAD) has near-perfect error correlation → effective sample size ≈ 1 → aggregation cannot
help. Homogeneous CD≈1.0 IS that phenomenon; heterogeneous cross-family convergence is the genuine
convergent delusion. Both are pre-registered (prereg §1 H1a lists SC, homogeneous-MAD, heterogeneous-MAD,
verifier; §8 has `method` as a factor), so leading with cross-model is a FRAMING refinement within the
registered design — **no amendment needed, LOGGED** (decision-log row 35). **Confirm after the reasoner arm.**
- Caveat: `diag_casesort_001` saturated even heterogeneously (both models default to Python `sorted()`
  case-sensitive) → it is less "subtle" than intended (a semi-strong trap); note/maybe reclassify.
- `diag_geomean_001`: the weak model RESOLVED to the target (→I0=1.0) — its default-pull toward arithmetic
  mean is weak enough that the model got the intended geometric mean; behaves as a genuine subtle trap.

## 3. H2 median-under-skew — partial, reasoner data missing
`data_typical_001_k1` (H2_derivable): homogeneous WEAK model CD=0.60, →I0=0.40 (40% of the weak ensemble
already resolve to the median because the outlier is VISIBLE); heterogeneous →I0=0.50. Consistent with the
H2 tag (derivable), BUT the KEY prediction — reasoners resolve MORE than weak models — has NO reasoner
data (cap). **Cannot validate the H2 regime empirically until the reasoner arm completes.** No
reclassification yet.

## 4. ⭐ I_perp / answer-format issue (guardrail B triggered on some cells) — FIX before scaling
Overall I_perp = 0.172 (< 0.20 threshold), but per-condition:
- `single | llama-3.3-70b` = 0.273, `single | mistral-small` = 0.273 (> 0.20).
- `sc | deepseek-r1` = 0.20 (reasoning models wrap answers in reasoning text the labeler can't parse).
- `code_invoice_001_k1` WEAK homogeneous: **all 5 = I_perp** (CDenum 0.0 vs CDfrozen 1.0) — the 3-part
  `format_invoice_line` output does not match the exact-format gold → parse failure, NOT real convergence.
  (This is exactly why the Amendment-04 enumerated-vs-frozen split matters: enumerated correctly reports
  0.0 real convergence where frozen would report 1.0 spurious I_perp "convergence".)
→ **The answer-format contract / labeler needs hardening for (a) complex multi-part outputs (code_invoice)
and (b) reasoning-model wrapping (deepseek-r1) BEFORE the registered run.** Elevated I_perp currently
contaminates CD on those cells.

## 5. CD-vs-k (H1b, homogeneous, I_perp-contaminated — directional only)
`code_invoice` family: mistral k1=0.00, k2=0.20, k3=0.80 (rises with k); o4-mini k1=0.80, k2=0.80. The
k1=0.00/all-I_perp on mistral is a format artifact (see §4), so this curve is not yet trustworthy. H1b
(demoted to secondary per O2/row 27) needs the format fix + more graded tasks.

## 6. Regime-tag status (empirical = final arbiter; NO reclassification yet)
- H1 strong traps (quarter, overtime, activeusers): behave as H1 (saturate incl. limited reasoner data). ✅ provisional.
- H2 median-skew: weak partially resolves (40%) — consistent, but reasoner-resolves-more UNCONFIRMED (cap). ⏳
- Subtler traps: geomean behaves subtle (resolves/splits); casesort behaves semi-strong (saturates cross-model). Note for the saturation instrument.
- **No tag reclassified** — insufficient reasoner data. Revisit after the reasoner arm completes.

## 7. Recommendations (→ owner)
1. **RESUME the reasoner arm** after the ~24h cap reset (resumable runner continues from checkpoint) to
   complete H1-reasoner + the H2 reasoner-resolution — the core two-regime evidence.
2. **Fix the answer-format contract / labeler** for complex multi-part outputs + reasoning-model wrapping
   (spawn a fix sub-agent) — closes the guardrail-B I_perp inflation before the registered run.
3. **O2 framing (provisional):** lead with cross-model (heterogeneous) convergent delusion; homogeneous
   saturation is determinism-confounded. Confirm after the reasoner arm.
4. Do NOT proceed to the reversed spot-check gate / scaling until 1–2 are done and the reasoner arm confirms
   the H1/H2 contrast.
