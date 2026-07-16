# Default-check diagnostic (EXPLORATORY) — plan (2026-07-16)

> Owner-approved live diagnostic (bounds: SMALL, exploratory/NON-confirmatory, reasoner-weighted,
> minimize gpt-4o-mini to protect the registered mini-pilot's daily-capped baseline). Implementer =
> Claude family (worktree). Auditor = NON-Claude (GPT). The MANAGER runs the live calls (holds token).
> Purpose: validate regime tags + trap behavior + I_perp rate + the O2 CD-saturation question BEFORE the
> reversed spot-check gate. Results are EXPLORATORY (do NOT count toward H1/H2 support). Metric FROZEN.

## What we must learn
1. **Regime tags (final arbiter = empirical).** H1_external items → homogeneous agents INCLUDING reasoners
   converge on the wrong default combination (external knowledge unrecoverable). H2_derivable item
   (data_analysis median-under-visible-skew) → REASONERS RESOLVE to the target while WEAK models default
   to the mean. Reclassify/exclude any task whose behavior ≠ its tag (Manager logs it).
2. **Trap behavior.** The model's default is actually the labeled wrong foil (target ≠ real default).
3. **Per-condition I_perp RATE** (owner guardrail B) — a first-class diagnostic; a high rate (>20%) flags
   answer-format-contract non-compliance to fix before scaling.
4. **⭐ O2 CD-saturation disambiguation.** Current strong traps hit CD=1.0 at k=1. To tell "failure is
   IMMEDIATE (real)" from "traps too STRONG (artifact)", include DELIBERATELY SUBTLER traps: if even
   subtle traps hit CD=1.0 → saturation is robust/real (report the stronger "immediate failure" claim);
   if subtle traps show CD<1.0 → the measure DISCRIMINATES and saturation is just strong-trap (then add
   subtler traps and/or a finer measure to the registered benchmark). DECIDE before freezing the
   registered run.

## Deliverable 1 — SUBTLER-trap diagnostic fixture (SEPARATE from the main benchmark)
Build a SMALL set (~3–4) of deliberately SUBTLER reversed traps in a **separate diagnostic fixture**
(e.g. `bench/diagnostic/` or a `scripts/` fixture — NOT added to bench/data/*.jsonl for the registered
benchmark yet; keep provenance clean and reversible). Each keeps executable gold + fairness + the reversed
property, but with a WEAKER default-pull so a discriminating CD would land strictly between 0 and 1:
- "Subtler" = the deleted convention's population-default is LESS universally the model's first choice
  (the default answer is more contestable), so agents plausibly SPLIT between target and default →
  expected CD < 1.0 if the measure discriminates. Examples of the axis of subtlety (implementer designs
  the concrete tasks, ≥1 per executable-gold domain): a convention where BOTH readings are common in the
  wild (so no single dominant default); a smaller/less-obvious numeric deviation; a target that a
  meaningful minority of models would independently pick. Do NOT make them unfair (a human reading the
  full spec must still agree the non-default is genuinely intended).
- Tag each with `regime` and keep 100% executable-gold distinguishability. Mark clearly as DIAGNOSTIC.

## Deliverable 2 — diagnostic driver `scripts/default_check.py`
Offline-guarded (like `scripts/mini_pilot.py`: does nothing unless an explicit env flag AND a token are
present; offline prints "skipped" exit 0). Uses `harness/runner.py` (resumable/throttled/cache-backed).
- **Task set (SMALL):** a few STRONG H1 traps (existing benchmark: e.g. code fiscal_quarter k1, policy
  overtime k1, data org-KPI k1) + the k-gradient variants (a k1/k2/k3 family, e.g. code_invoice) to probe
  saturation across k + the SUBTLER traps (Deliverable 1) + the H2 median-skew item.
- **Pool (owner ruling):** weight toward the REASONER-vs-WEAKER contrast (this validates H1/H2). Use the
  Option-B config as-is but: reasoners (deepseek-r1, o4-mini) + one WEAK model (mistral-small or
  llama-3.3-70b) as the homogeneous ensemble + the heterogeneous diverse pool. **MINIMIZE gpt-4o-mini**
  (exclude it here, or ≤ a token handful) — protect its daily cap for the registered mini-pilot baseline.
- **Ensemble:** small homogeneous k (e.g. 5) at temperature>0 to observe within-ensemble convergence, per
  model class; a single reasoner pass for the H2 resolution check.
- **Labeling:** executable gold (`harness/label.py`), never LLM-judge.
- **Report per (task, regime, model_class):** convergent_delusion computed BOTH ways (enumerated-foils-only
  AND with-I_perp-eligible — the Amendment-04 sensitivity pair), the I_perp RATE, whether reasoners
  RESOLVE to I0 (H2 check) vs default wrong (H1 check), and the CD-vs-k curve for the k-gradient family.
  Emit a compact machine-readable summary (JSONL/CSV) the Manager can paste into the report.
- **Cost/rate discipline:** throttle hard (conservative RPM), rely on the disk cache, hard budget cap;
  print total calls + per-model counts + total cost. Token never logged.
- **Offline test:** a unit test that runs the driver against the OFFLINE mock end-to-end (no network) so
  the pipeline (select→run→label→CD/I_perp report) is verified before the live run.

## Provenance / process
- Implementer records model FAMILY (Claude). Commit in the worktree; push the branch. The Manager spawns a
  NON-Claude (GPT) audit of (a) subtler-trap FAIRNESS + reversed direction, (b) driver correctness
  (minimizes gpt-4o-mini, correct CD/I_perp math, reasoner-weighted, offline-guarded). After 0
  BLOCKER/MAJOR, the **Manager runs the driver LIVE** (small, throttled) and interprets results.
- Do NOT touch harness/metrics.py, common/schema.py, or paper/preregistration/ (frozen). Do NOT add the
  subtler traps to the registered benchmark jsonl — keep them a diagnostic fixture pending the saturation
  finding + a later full audit if promoted.

Commit trailer: `Co-authored-by: copilot <copilot@users.noreply.github.com>`.
