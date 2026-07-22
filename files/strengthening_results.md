# Strengthening analyses — post-hoc secondary (blind-review response)

> **SECONDARY / post-hoc. Offline reuse of frozen metrics; does NOT change any confirmatory number, metric, or pre-registered hypothesis.**
>
> Implementer model family: Claude (Anthropic). Bootstrap seed: 42. Data dir: `C:\Users\v-elzhang\Desktop\MyFolder\When Consensus Lies`.

## Pre-stated equivalence margins (Analysis 2, declared before computing)
- **Primary ΔCD = 0.15** (Amendment 08 §3 pre-registered minimum detectable effect / power target).
- **Secondary (stricter) ΔCD = 0.1** (transparency; a stronger claim).

## Analysis 1 — per-item cross-MODEL label concentration (blind-review #6)

R2 Anthropic-constructed subset (`cp_r2_xf.jsonl`), single-agent labels from tested models with family ≠ Anthropic, across distinct models/seeds. Per-item **concentration** = frozen A04 `cd_primary` (modal-wrong ENUMERATED-foil share; `I_perp` ineligible as modal but kept in the denominator).

**Cross-family (non-Anthropic)** — models: gemini-3.1-pro-preview, gemini-3.5-flash, gpt-4o-mini, gpt-5.4, gpt-5.6-sol; families: google, openai.

- Items: **12**; agents/item (max): see item table.
- Mean per-item concentration: **0.3556** (median 0.0000, range [0.0000, 1.0000]).
- Item-level bootstrap 95% CI of the mean: **[0.1167, 0.6222]**.
- Mean # distinct models on the modal wrong foil: **1.833**; mean # distinct families: **0.750**.
- Items with any wrong-foil convergence: 5/12.
- **Fraction of items where ≥2 DISTINCT non-Anthropic families concentrate on the SAME wrong foil: 0.3333** (4/12).
- Fraction of items where ≥2 distinct models concentrate on the same wrong foil: 0.4167 (5/12).

**Same-family (Anthropic) reference** (NOT part of the cross-family estimate) — models: claude-haiku-4.5, claude-opus-4.8: mean concentration 0.2639, ≥2-families fraction 0.0000.

Interpretation: multiple INDEPENDENT non-Anthropic models/families landing on the SAME specific wrong foil per item is genuine cross-MODEL convergence — not a within-cell N=1 error-rate tautology.

| task | concentration | modal_wrong_foil | n_agents | n_models_on_foil | n_families_on_foil |
|---|---|---|---|---|---|
| r2xf_code_intdiv_001_k0 | 0.0000 | — | 15 | 0 | 0 |
| r2xf_code_intdiv_001_k1_integer_division | 1.0000 | I1 | 15 | 5 | 2 |
| r2xf_code_weekday_001_k0 | 0.0000 | — | 15 | 0 | 0 |
| r2xf_code_weekday_001_k1_weekday_numbering | 0.8667 | I1 | 15 | 5 | 2 |
| r2xf_data_argmax_001_k0 | 0.0000 | — | 15 | 0 | 0 |
| r2xf_data_argmax_001_k1_position_base | 1.0000 | I1 | 15 | 5 | 2 |
| r2xf_data_sortids_001_k0 | 0.0000 | — | 15 | 0 | 0 |
| r2xf_data_sortids_001_k1_id_sort_order | 0.0000 | — | 15 | 0 | 0 |
| r2xf_policy_days_001_k0 | 0.0000 | — | 15 | 0 | 0 |
| r2xf_policy_days_001_k1_day_count | 0.4000 | I1 | 15 | 2 | 1 |
| r2xf_policy_weeks_001_k0 | 0.0000 | — | 15 | 0 | 0 |
| r2xf_policy_weeks_001_k1_week_definition | 1.0000 | I1 | 15 | 5 | 2 |

## Analysis 2 — TOST equivalence tests (blind-review #8)

Test statistic: paired-difference t-based TOST (df = n_items - 1). Item-level paired differences (per-task mean `cd_primary`). Equivalence at margin δ ⇔ the 90% CI of the paired mean difference lies fully within (−δ, +δ) ⇔ TOST p < 0.05.

Tier mean cd_primary (H1_external): reasoning=0.5043, weak=0.4874, heterogeneous=0.5437.

### (a) heterogeneous-MAD vs homogeneous-MAD
#### heterogeneous-MAD vs homogeneous-MAD (row-35)
- n items (paired): 40; observed Δ = **-0.0196**; 95% CI [-0.0666, 0.0274].
- Pooled row-35 reference (frozen contrast): Δ = -0.0033 (hetero 0.5437 − homo 0.5470).
  - TOST ±0.15: 90% CI [-0.0587, 0.0196], p_TOST = 0.0000 → **✅ EQUIVALENT**.
  - TOST ±0.1: 90% CI [-0.0587, 0.0196], p_TOST = 0.0007 → **✅ EQUIVALENT**.

### (b) capability-tier CD invariance
#### reasoning vs weak (capability-tier CD)
- n items (paired): 40; observed Δ = **0.0169**; 95% CI [-0.0465, 0.0803].
- Mean CD: 0.5043 vs 0.4874.
  - TOST ±0.15: 90% CI [-0.0359, 0.0697], p_TOST = 0.0001 → **✅ EQUIVALENT**.
  - TOST ±0.1: 90% CI [-0.0359, 0.0697], p_TOST = 0.0058 → **✅ EQUIVALENT**.

#### reasoning vs heterogeneous (capability-tier CD)
- n items (paired): 40; observed Δ = **-0.0394**; 95% CI [-0.0855, 0.0067].
- ⚠️ heterogeneous tier carries only the heterogeneous-MAD method; this comparison is not method-matched
- Mean CD: 0.5043 vs 0.5437.
  - TOST ±0.15: 90% CI [-0.0778, -0.0010], p_TOST = 0.0000 → **✅ EQUIVALENT**.
  - TOST ±0.1: 90% CI [-0.0778, -0.0010], p_TOST = 0.0057 → **✅ EQUIVALENT**.

#### weak vs heterogeneous (capability-tier CD)
- n items (paired): 40; observed Δ = **-0.0563**; 95% CI [-0.1387, 0.0261].
- ⚠️ heterogeneous tier carries only the heterogeneous-MAD method; this comparison is not method-matched
- Mean CD: 0.4874 vs 0.5437.
  - TOST ±0.15: 90% CI [-0.1250, 0.0123], p_TOST = 0.0135 → **✅ EQUIVALENT**.
  - TOST ±0.1: 90% CI [-0.1250, 0.0123], p_TOST = 0.1452 → **❌ NOT established**.

