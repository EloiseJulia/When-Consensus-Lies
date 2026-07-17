# Reversed Spot-Check Gate — package for OWNER SIGN-OFF (2026-07-17)

> Per the reversal spec's gate + owner reaffirmations: the reversed spot-check gate returns to the OWNER
> for FINAL sign-off before any full-scale / registered run; the EMPIRICAL per-regime default-check is the
> FINAL ARBITER of the H1/H2 tags. This package consolidates the evidence across all three reconstructed
> domains. **Nothing is scaled until you sign here.**

## 0. What is being gated
The reversed 3-domain benchmark on `main` (code_spec #16, policy_qa #17, data_analysis #18), reconstructed
under Amendment 01 (target=NON-default true intent; model default=wrong foil) + Amendment 03 (combinatorial
binary-axis 2^k' interpretation sets) + Amendment 02 (`Task.regime`). 42 task variants total.

## 1. Structural guarantees (verified on `main`, apply to ALL 42 tasks)
| Domain | Tasks | Distinguishable | Regime tags | Invariants |
|--------|-------|-----------------|-------------|------------|
| code_spec | 20 | **20/20 (100%)** | all H1_external | ✅ per-variant `len(key_questions)==k'`, `len(interps)==2^k'`, exactly-one I0, one `[combined-default]`, k0 empty |
| data_analysis | 8 | **8/8 (100%)** | H2_derivable (median-skew) + H1_external (org-KPI, report) | ✅ same |
| policy_qa | 14 | **14/14 (100%)** | all H1_external | ✅ same |
- Executable gold only (never LLM-judge). Cross-family construction: constructor = `cohere/cohere-command-a`
  (outside every tested pool). Verified by `python -m bench.validate --domain <d>` + the per-domain test
  suites (full suite 528 green). Combined-default foil marked via `__combdef`; power-set invariant enforced.

## 2. ⭐ EMPIRICAL per-regime default-check (the FINAL ARBITER — completed 2026-07-17)
From the live default-check diagnostic (weak model + heterogeneous pool + BOTH reasoners deepseek-r1 &
o4-mini; 174 calls, $0.35; findings doc 2026-07-16 §UPDATE, decision-log row 46):

| Regime | Representative task | Reasoners (deepseek-r1 / o4-mini) | Weak model | Verdict |
|--------|--------------------|-----------------------------------|-----------|---------|
| **H1_external** | code_quarter (fiscal) | CD=**1.000** | CD=1.000 | ✅ persists incl. reasoners |
| **H1_external** | policy_overtime (35h) | CD=**1.000** | CD=1.000 | ✅ persists incl. reasoners |
| **H1_external** | data_activeusers (org-KPI) | CD=**1.000** | CD=1.000 | ✅ persists incl. reasoners |
| **H2_derivable** | data_typical (median-skew) | →I0=**1.000**, CD=0.00 | →I0=0.40, CD=0.60 | ✅ reasoners RESOLVE, weak default wrong |

→ **All representative H1 tags behave as H1** (default = wrong foil; convergent delusion persists even for
reasoners — external knowledge unrecoverable). **The H2 tag behaves as H2** (reasoners derive the median
from the visible skew; weak models default to the mean). **NO task was reclassified or excluded** — observed
behavior matched every tested tag (empirical = final arbiter, satisfied).
- Coverage note (honest): the diagnostic directly default-checked REPRESENTATIVE families per regime (the
  ones above + the 4 subtler diagnostic traps), not all 42 variants. The structural guarantees (§1) hold for
  all 42; the empirical regime BEHAVIOR is validated on the representative set. If you want a specific
  additional family default-checked before scale, name it (cheap to add).

## 3. Fairness bar (per reversed task — human agrees the non-default is genuinely intended)
Each reversed task's `I0` is a genuine, clearly-specified non-default intent; the DELETED clause is exactly
what reveals it; the model's natural default = a wrong foil. Cross-family audits confirmed the fairness bar
on every family, and fixed the two that failed it (policy k=2 mileage-rate → timeless mileage-rounding;
prompt-leakage / GAAP-tie fixes in code_spec). Examples: code fiscal-April quarter (default=calendar);
policy 35h union overtime $1000 (default=40h FLSA $950); data org-KPI ≥3 active (default=≥1 any-activity);
data median-under-skew 4.50 (default=mean 116.38).

## 4. O2 saturation finding (informs framing, not a gate blocker)
Strong-trap mean CD=1.0 vs subtler-trap mean CD=0.725 → the CD measure **discriminates** (subtler traps
split; geomean even resolves). Cross-model (heterogeneous) convergent delusion is the clean signal;
homogeneous saturation is the ρ→1 fake-redundancy demonstration (row 35). No benchmark change required;
this is the pre-registered framing (headline = cross-model / two-regime).

## 5. I_perp / answer-format (guardrail B — satisfied)
Overall I_perp 0.126 (< 0.20). The only high cell is code_invoice/deepseek-r1 (0.80) — a complex 3-part
off-axis task ALREADY EXCLUDED from the registered reasoner arm (A05) and flagged. Labeler hardened + A04
signed (PR #21/#23). No answer-format blocker for the essential items.

## 6. Reversed spot-check gate criteria (from the reversal spec) — status
1. Full latent_spec clearly specifies the non-default intent; deleted clause reveals it; fair — ✅ (audited).
2. I0 ≠ model default; labeled default foil = the model's actual default — ✅ (empirical default-check §2).
3. Regime tag correct, cross-family re-derived; disagreement→EXCLUDED — ✅ (no disagreement; none excluded).
4. Per-regime empirical default-check (H1 persists incl. reasoners; H2 reasoners resolve) — ✅ (§2).
5. Executable gold distinguishes all interpretations (100%) — ✅ (§1).
6. Per-variant invariant holds (`len(key_questions)==k'==...`; k0 empty) — ✅ (§1, tests).
7. Cross-family construction (constructor family ≠ tested families) — ✅ (constructor=cohere).

## 7. ⭐ OWNER SIGN-OFF (required before any registered/full-scale run)
- [ ] Owner APPROVES the reversed spot-check gate — the reconstructed 3-domain benchmark is READY for the
      registered mini-pilot → full-scale run. (H1/H2 regime tags empirically validated; 100% distinguishable;
      invariants + fairness + cross-family construction hold.)
- [ ] Owner notes any specific additional task family to default-check before scale (optional), or confirms
      the representative-set validation is sufficient.

On sign-off, the sequence is: **freeze Amendment 05** (reasoning-condition N, now that the item pool +
reasoner behavior are settled — its freeze checklist §7 items are now satisfiable) → **registered mini-pilot**
(prereg §11) → **full-scale registered run** (day-spanning via the resumable runner) → **Phase 6 real
analysis** (the merged pipeline) → writing. The Manager does NOT scale without this sign-off.
