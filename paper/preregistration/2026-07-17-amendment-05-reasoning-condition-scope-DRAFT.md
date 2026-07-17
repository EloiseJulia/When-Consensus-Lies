# Pre-Registration Amendment 05 — Asymmetric reasoning-condition sample size (DRAFT, NOT yet frozen)

> Amends FROZEN pre-registration `2026-07-15-prereg.md` (freeze `c0a0393`) §10 (sample sizes) ONLY — for
> the reasoning `model_class`. **Metric definitions, hypotheses, regime criterion, and decision rules are
> UNCHANGED and remain frozen.** §10 already anticipates the MVP pilot calibrating final N; this records a
> principled, rate-constrained, PRE-REGISTERED calibration of the reasoning-class N specifically.
> **STATUS: DRAFT — do NOT freeze until the reasoner arm completes + the reversed spot-check gate settles
> the item pool + a variance/power estimate (owner ruling Q4, 2026-07-17). Exact N is a placeholder range
> here.** Owner sign-off required to freeze.

## 0. Motivation (empirical, external constraint — not effect-seeking)
The reasoning models are per-DAY capped on GitHub Models (deepseek-r1 ~20/day, o4-mini ~25/day; observed
2026-07-16 and re-confirmed 2026-07-17). At the frozen §10 scale (~60 items × ≥3 seeds × the full config
grid) the reasoning condition would need ~1080–4000 calls/model = ~45–180 days/model — INFEASIBLE. We
therefore scope the reasoning `model_class` N; this is an EXTERNAL rate constraint, pre-registered
transparently, not a design choice to fit a result.

## 1. ⭐ What stays PRIMARY vs SECONDARY (owner ruling Q1)
- **PRIMARY (full N, NOT scoped):** the H1a/H1b convergent-delusion result on the NON-reasoning model
  classes — the full-§10 cross-model / heterogeneous convergent delusion (independent families → same
  wrong foil) and the ρ→1 fake-redundancy demonstration (homogeneous/SC). The paper's headline rests here.
- **SECONDARY, power-limited (scoped):** the reasoning `model_class` arm — the `regime × model_class`
  interaction (H2 attenuates for reasoners). **If H2 is underpowered, the paper still stands on the H1
  cross-model result** (owner Q1). We never let the scoped H2 arm gate the primary claim.

## 2. Scope of the reasoning-class arm (BALLPARK — frozen later, Q4)
Keep FULL §10 N for all non-reasoning classes (single, SC k5/k10, homogeneous-MAD, heterogeneous-MAD
non-reasoner members, verifier). Scope ONLY the reasoning class (`deepseek-r1` + `o4-mini`):
- **Items:** a BALANCED subset, ~½ `H1_external` + ½ `H2_derivable`, drawn from the executable-gold
  domains (code_spec + data_analysis), centered on the clean H2 demonstrators (median-under-visible-skew,
  etc.). **Prefer MORE ITEMS over more seeds** (owner Q2: item count buys more power for a
  regime×model_class contrast than seed replication — items are the replication unit of the `regime`
  factor). Ballpark **~20–24 items (10–12 per regime)**.
- **Configs (reasoners only):** `single(1)` + `SC-k5(5)` = 6 calls/item/seed (single-vs-SC is enough for
  the "aggregation doesn't help reasoners" contrast; drop SC-k10 / MAD / verifier for the reasoning class).
- **Seeds (reasoners only):** **1–2** (lean to 1 if trading for more items).
- **Both reasoner models** (per-model caps are parallel → 2 models don't slow wall-clock).
- **Call budget (ballpark):** ~20–24 items × 1–2 seeds × 6 ≈ **120–288 calls/reasoner model** →
  ~6–13 days/model at ~22/day; feasible over ~1.5–2 weeks with the resumable runner + cache.

## 3. ⭐ Rough power note (owner Q2 — refine with the gate's variance estimate)
The scoped arm tests the `regime × model_class` INTERACTION for reasoners (a difference-in-differences on
CD between H1 and H2). With ~10–12 items/regime × 1–2 seeds (item-clustered), only a LARGE interaction is
detectable at ~80% power: roughly **ΔΔCD ≳ 0.4–0.5** — i.e. the difference between H1 CD saturating near
1.0 for reasoners and H2 CD dropping to ~0.4–0.5 when reasoners resolve the visible-skew ambiguity. This
is exactly the EXPECTED large attenuation (the diagnostic already shows even a weak model partially
resolves H2 at ~0.4→I0), so the design can detect the predicted effect but NOT subtle attenuations. A
precise power figure will be computed from the item-level CD variance measured at the reversed spot-check
gate + the completed reasoner-arm diagnostic (this is why N freezes AFTER the gate, Q4). If the observed
interaction CI is too wide to conclude, we report H2 as **UNDERPOWERED** — honestly, per §9.

## 4. gpt-4o-mini (homogeneous ρ-baseline) — FULL N, cross-day (owner Q3)
Do NOT shrink gpt-4o-mini. It anchors both the ρ→1 fake-redundancy demonstration and the cross-model pool.
Its daily cap is looser than the reasoners'; the resumable runner runs it at full §10 N across days.

## 5. Integrity commitments (owner Q4)
- Pre-register the asymmetric N (this amendment) BEFORE the registered run.
- If the reasoning/H2 arm is underpowered, **REPORT it as underpowered — do NOT backfill reasoner data
  later to chase significance** and do NOT re-scope post-hoc.
- Metric definitions, hypotheses, regime criterion, decision rules: UNCHANGED/frozen. This touches only
  per-model_class sample size (§10 calibration).

## 6. Rate-tier contingency (owner de-risk note)
If a higher GitHub Models reasoner allocation (plan tier / purchased AI credits) becomes available, the
reasoning-class shrink may be UNNECESSARY — revisit and, if so, run the reasoning class at (closer to)
full §10 N and note the reversion. This does not block drafting; it may relax §2 before freeze.

## 7. Freeze checklist (before the registered run)
- [ ] Reasoner-arm diagnostic completed (H1-persist + H2-resolution behavior confirmed).
- [ ] Reversed spot-check gate settles the confirmatory item pool (incl. the balanced reasoning subset).
- [ ] Item-level CD variance → precise power figure computed; final reasoning-class N (items/seeds) fixed.
- [ ] Owner signs off → freeze; record Amendment 05 SHA.

Amendment status: **DRAFT — awaiting item pool + variance estimate + owner sign-off.** Metric frozen.
