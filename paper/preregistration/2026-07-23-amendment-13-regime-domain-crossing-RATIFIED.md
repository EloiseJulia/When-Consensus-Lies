# Amendment 13 (RATIFIED by owner @EloiseJulia 2026-07-23) — regime × domain crossing

> STATUS: **RATIFIED (owner personal sign-off 2026-07-23).** Owner input (verbatim): "按推荐默认批准（每域
> 4 个 H2 base task、single+heterogeneous-MAD×3 seed、mai-code 构造、pilot 完后再跑）（Recommended）". The
> recommended §6 scope + §8 defaults are hereby FROZEN. Construction+run per §6; **the RUN starts only AFTER
> the Phase 2b pilot finishes** (owner-directed, to avoid proxy contention). Additive sidecar ONLY — the
> frozen 54 confirmatory items / schema / metrics / results are NOT touched. The Manager did NOT self-sign;
> this records the owner's personal ratification.
> Motivation: owner asked (2026-07-23) why H1(40)/H2(14) are unbalanced and unpaired. Answer established:
> H1/H2 is an INTRINSIC semantic property (derivable-in-prompt vs needs-external-convention), so it is
> necessarily BETWEEN-item; the strict WITHIN-item disambiguator control already exists as k0-vs-k1. BUT the
> H1-vs-H2 secondary boundary contrast is CONFOUNDED WITH DOMAIN — all 14 H2 items live in data_analysis;
> code_spec and policy_qa have H2=0. Owner chose to add H2 items to code_spec + policy_qa so regime CROSSES
> domain, rebutting "H1/H2 differences might be domain differences."

## 1. What this amendment ADDS (and what it must NOT touch)
- ADDS a **pre-registered SECONDARY ROBUSTNESS analysis** on a NEW, ADDITIVE **sidecar item set** of
  `H2_derivable` items in `code_spec` and `policy_qa` (domains that currently have none), plus matched
  `H1_external` anchors in the same domains (some already exist).
- **INVIOLABLE:** does NOT modify the frozen `bench/data/{code_spec,policy_qa,data_analysis}.jsonl`, the frozen
  54 confirmatory items, the frozen `schema.py`, any frozen metric, or any confirmatory result. New items go
  in SEPARATE sidecar files (e.g. `bench/data/amd13_code_spec.jsonl`, `bench/data/amd13_policy_qa.jsonl`).
  Reported as pre-registered SECONDARY/robustness (like A12 Phase B), never as a change to the confirmatory
  finding. The frozen Study-1 headline does NOT depend on this.

## 2. Pre-registered hypothesis (FROZEN on ratification)
- **H-A13 (regime main effect is not domain-confounded):** within EACH of code_spec and policy_qa, matched
  `H1_external` items show HIGH convergent delusion while `H2_derivable` items show LOW (attenuated ≈ 0)
  convergent delusion — i.e. the H1→high / H2→low pattern holds WITHIN domain, not only across domains.
  Pre-committed direction: per-domain `cd_primary(H1) − cd_primary(H2) > 0` with item-level bootstrap CI
  excluding 0; and a `regime × domain` analysis showing the regime effect is significant with NO significant
  regime×domain interaction that would explain it away as domain.
- Metric = the FROZEN `cd_primary` (target I0); NO metric redefinition. Same anti-leakage discipline.

## 3. Item construction rule (must genuinely satisfy the frozen H2 operational definition)
An item is `H2_derivable` iff I0 is UNIQUELY recoverable from information LITERALLY PRESENT in the retained
prompt + artifacts. Concrete construction per domain:
- **code_spec H2:** the ambiguous behavior is pinned by an IN-PROMPT artifact a careful solver must use —
  a provided doctest/example I/O, an explicit type signature, or an internal invariant (e.g. a rounding fn
  whose provided example output disambiguates half-even vs half-up; an indexing fn whose provided example
  pins 0- vs 1-based). Deleting NOTHING external is needed — the resolution is in the artifact.
- **policy_qa H2:** a numeric policy item whose disambiguating convention is STATED within the provided
  policy text / derivable by internal consistency (e.g. the threshold is defined earlier in the SAME provided
  paragraph and must be read+applied), NOT an external org KPI.
- Each item ships k0 (fully specified) + k1 (the derivable-ambiguous variant), enumerated interpretations
  {I0,I1,...}, and EXECUTABLE deterministic gold checkers (Law 7 — no LLM judge).

## 4. Mandatory manipulation check (gates the whole analysis)
Run the FROZEN oracle-hint recovery probe (prereg §) on the new items: recovery-rate must be HIGH on the new
H2 items (confirming genuine in-prompt derivability) and LOW on the matched H1 items. **If the constructed
"H2" items do NOT separate on this probe, we report the construction failure honestly and do NOT claim the
crossing** — no tuning to force separation. This is the pre-committed validity gate.

## 5. Provenance (construct validity — Law 6)
- EXECUTABLE deterministic gold makes `cd_primary` independent of who wrote the item.
- Constructor family DOCUMENTED and HELD OUT of the primary regime-contrast: compute the per-domain contrast
  on cells where tested-family ≠ constructor-family (mirroring Amendment 10's R2 design), so the result is not
  a constructor artifact. RECOMMENDED constructor = the original primary constructor (Microsoft mai-code,
  outside the tested pool) via the proxy; fallback = Claude-constructed with the held-out-cell contrast.
- Anti-leakage: no gold/target/foil/key_questions text in any tested-agent prompt (same as the frozen study).

## 6. RECOMMENDED run scope (caution-first — owner to confirm §8)
- **Items:** ~4 H2 base tasks per domain × (k0 + k1) ≈ 8 items/domain, + reuse/add matched H1 anchors →
  ~16–24 new sidecar items total. Start SMALL; expand only if the pilot separates.
- **Conditions:** the HEADLINE conditions that show the effect — `single` + `heterogeneous-MAD` (cross-family)
  — ≥ 3 seeds, on the frozen roster; $0 via the proxy. (NOT the full SC/verifier grid unless the small pass
  warrants it.)
- **Pipeline:** additive driver/sidecar (worktree) → GPT cross-family audit (executable-gold correctness +
  anti-leakage + H2-derivability via manipulation check) → merge → run → analyze regime×domain → report as
  pre-registered SECONDARY robustness.

## 7. What stays fixed / honesty
No frozen file touched. Reported as pre-registered secondary robustness (Amendment 13), not a confirmatory
change. All nulls/limitations reported honestly (incl. if the manipulation check fails). DECISION-LOG row on
ratification + this Amendment SIGNED only by the owner personally.

## 8. Owner ratification points (please confirm/adjust BEFORE any construction)
1. **Item count/scope:** OK with ~4 H2 base tasks/domain in code_spec+policy_qa (k0+k1), small-first? (adjust N)
2. **Run conditions:** OK with `single` + `heterogeneous-MAD`, ≥3 seeds, $0? (or add SC/verifier?)
3. **Constructor provenance:** prefer mai-code (original constructor, out-of-pool) or Claude-with-held-out-cell
   contrast?
4. **Timing:** run AFTER the Phase 2b pilot finishes (avoid proxy contention), or in parallel?
