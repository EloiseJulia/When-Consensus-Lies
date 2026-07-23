# Manager Handoff — "When Consensus Lies" (2026-07-23)

> Authoritative current-state handoff from the retiring Manager+Lead-Researcher session (context saturated)
> to a fresh session. READ THIS FIRST, then re-derive ground truth from git (`git --no-pager log --oneline
> -30 main`; `git branch -a`) — trust the log over any narrative. Supersedes the 2026-07-22 handoff for
> current state; earlier handoffs remain valid for history.

---

## 0. One-paragraph status
The paper has TWO studies. **Study 1 (original)** = the pre-registered confirmatory finding that under a
shared, underspecified prompt, independent models CONFIDENTLY and SILENTLY converge on the same wrong
interpretation ("fake redundancy"); it is COMPLETE, written up as a **20-page CHI draft** (compiles clean),
repositioned around **same-prompt multi-model interfaces**, with a landscape audit, verified references,
Phase B honest-null intervention results, TOST/cross-model strengthening analyses, and an R2 two-constructor
fix. **Study 2 (new, owner-approved 2026-07-23)** = a black-box, inference-only **Latent-Premise Probing
(LPP)** detector + the **seed/context uncertainty decomposition** that exposes a SOTA blind spot. Study-2
**DETECTION is CONFIRMED** (6 models × 3 seeds, $0): H_ctx-self AUROC **0.895** vs semantic-entropy **0.58**.
**Study-2 Phase 2b (intervention) and 2c (AU-Probe white-box contrast) are NOT yet started** — that is the
immediate next work. An abstention human-validation KIT is built and waiting for the owner to code ~316 rows.

---

## 1. The science — two studies, one story
**Study 1 (frozen confirmatory; DONE):** two-regime MAIN effect keyed on the disambiguator's LOCATION.
- H1_external: silent convergent delusion, `cd_primary≈0.53`, abstention≈0.03%, `n_eff=1.10`, ICC=0.89.
- H2_derivable: resolved by all tiers, `cd=0`. Cross-family ≈ homogeneous (TOST-equivalent at ±0.15/±0.10).
- R2 constructor confound rebutted (Microsoft mai-code primary constructor + Anthropic claude-opus held-out
  R2 constructor; cross-model concentration 0.71 on k1 items). Phase B: neither cross-vendor synthesis
  (P-B1 Δ=+0.023) nor generic role-diversification (P-B2 Δ=+0.031) reduces CD — an honest null that
  strengthens "the information boundary dominates the aggregation recipe."

**Study 2 (new; detection CONFIRMED, intervention pending):** the constructive answer to "so what do we do?"
- **Concept:** decompose uncertainty into `H_seed` (semantic entropy over resamples of the SAME prompt — the
  SOTA signal) and `H_ctx` (answer dispersion under COUNTERFACTUAL PINNING of a self-surfaced unstated
  dimension). The DANGER QUADRANT = low `H_seed` ∧ high `H_ctx` = "confident latent-premise ambiguity" =
  the zone semantic entropy is BLIND to.
- **Detector (LPP), black-box, inference-only, no GPU:** (1) model self-surfaces decision-relevant unstated
  assumptions (generic prompt, NO gold); (2) counterfactual-pin each with the model's OWN values, cluster
  the pinned answers by MUTUAL executable equivalence (frozen-harness `_compare`, union-find), `H_ctx-self`
  = entropy over clusters; (3) flag if `H_ctx-self > τ ∧ H_seed ≤ τ_s`.
- **Gold-ambiguity (executable, detector-independent → NON-CIRCULAR):** an item is AMB+ iff its OWN
  enumerated interpretations produce DIFFERENT executable results on its inputs. 33 AMB+ / 21 AMB− / 0
  NON-DISC of 54.
- **CONFIRMED result (6 models × 3 seeds, `files/study2_stage2_results.md`):** pooled AUROC(H_ctx-self)=
  **0.895** [0.815,0.966] vs AUROC(H_seed)=**0.581** (≈chance); ΔAUROC=**0.314**; danger-quadrant=**0.758**
  (25/33); precision 0.93, recall 0.76, k0-FP low. **All 6 frontier models individually** 0.86–0.89 vs
  0.55–0.61. Pre-registered H-A1′ MET.
- **HONEST caveats (must keep):** the requirements-probing baseline (assumption-surfacing WITHOUT pinning)
  is strong (pooled **0.81**) — so the counterfactual-pinning increment is real but MODEST (+0.085). Frame
  the contribution as "**explicitly surfacing latent premises** exposes the SOTA blind spot"; pinning is a
  refinement, not the whole story. Localization (which axis) is WEAK (0.36, secondary). token-logprob
  baseline is N/A on non-OpenAI slugs.

---

## 2. Pre-registration & governance (INVIOLABLE)
- **Study 1** prereg FROZEN at `c0a0393`; amendments A04/A06/A07(owner-ratified)/A08–A12 SIGNED, A05
  superseded. **Study 2** prereg FROZEN at `paper/preregistration/2026-07-23-study2-prereg-FROZEN.md`
  (H-A1′/A1b/A2′/B1′/B2′; `H_seed`/`H_ctx-self`/gold-ambiguity defs; AUROC primary + item-flag op point
  τ=0/τ_s=0.5; 54 items; ≥3 seeds; baseline set; AU-Probe contrast).
- **Amendment 12** (Phase B exploratory) RATIFIED by owner. **Study-2 launch** ran under a documented owner
  CONDITIONAL PRE-AUTHORIZATION (2026-07-23: "if signal strong, launch full run, I authorize you… if weak,
  report and wait"), delegating go/no-go to the Manager against a pre-committed rule; the pilot met the bar.
  This is recorded honestly in DECISION-LOG row 87 and the frozen prereg — NOT self-signed as "owner."
- **Frozen-contract changes still require owner @EloiseJulia PERSONAL ratification.** Never AI-self-sign.
  Every design change → DECISION-LOG row (now at **row 88**) + (if it touches a prereg) a formal Amendment.

---

## 3. Immediate next steps (in priority order)
1. **Study-2 Phase 2b — intervention闭环 (owner said: do 2b then 2c).** Additive; frozen prereg H-B1′/H-B2′.
   - H-B1′ selective clarification: LPP triggers a clarification on AMB+ (needed), NOT on AMB−/k0; compare vs
     always-clarify and semantic-entropy-gated baselines (semantic entropy under-fires in the danger zone).
   - H-B2′ resolution: supply the deleted axis's gold convention as a CONTROLLED ORACLE (simulated user) →
     answer moves to I0 (cd_primary→0), executable gold. Real-user study = future work (avoid simulated-user
     overreach — frame as controlled oracle). Claude impl in a worktree → GPT cross-family audit → merge.
2. **Study-2 Phase 2c — AU-Probe white-box contrast (SECONDARY, compute-caveated).** Reproduce an activation
   probe on a small open CPU model (e.g. Qwen2.5-1.5B/Llama-3.2-1B); contrast with black-box LPP on the same
   items; position LPP as the black-box, cross-vendor-deployable method. Descope to a subset if CPU too slow.
3. **Write Study 2 into the paper** — a new section, honest framing per §1 caveats. Then re-assess venue
   length (owner said篇幅 later).
4. **Owner-only gates (blocking for submission):** (a) code the abstention human-validation KIT
   (`files/abstention_coding_sheet.csv`, ~316 rows, ~1.5–2h) → run `scripts/abstention_score.py` → finalize
   the abstention `\todo`; (b) verify every `references.bib` cite; (c) rewrite AI-assisted prose in own voice
   per CHI LLM-authorship policy (the draft is a marked SCAFFOLD); (d) decide CHI `sigconf` template switch
   (currently acmsmall/PACMHCI).

---

## 4. Tech facts the next Manager needs (verified)
- **All runs are $0** via the local **ghc-api Copilot proxy** `http://127.0.0.1:8313/v1` (no token, 40
  frontier models). MUST be running for live work; verify with Invoke-RestMethod to `/v1/models`.
- **Parallelize Study-2 by MODEL:** `python scripts/lps_confirm.py --shard-by-model --models <slug> --seeds
  <s...>` → per-model checkpoint `.run_partitions/cp_lps_confirm__<sanitized>.jsonl` + cache. RUNNER_LIVE=1
  guard; `--dry-run` enumerates; resumable per shard; then `scripts/lps_confirm_merge.py` (fail-loud
  fingerprint/conflict) + `scripts/lps_confirm_report.py --shards '...__*.jsonl'`. Launch 6 detached runners,
  set a ~20-min monitor schedule to relaunch stalled shards (proxy 504 hangs recur — kill+resume, resumable).
- **Study-2 code (all on main, additive):** `scripts/lps_method.py` (H_seed, surfacing, H_ctx-self via
  frozen-harness pairwise tolerance clustering + union-find, lpp_detect, METHOD_VERSION run-fingerprint),
  `scripts/lps_gold.py` (executable gold-ambiguity), `scripts/lps_confirm.py` / `lps_baselines.py` /
  `lps_confirm_merge.py` / `lps_confirm_report.py`, tests under `tests/test_lps_*`. 1014+ tests green.
- **LaTeX:** MiKTeX at `C:\Users\v-elzhang\AppData\Local\Programs\MiKTeX\miktex\bin\x64` (NOT on PATH);
  pdflatex ×1 → bibtex → pdflatex ×2; `pdflatex` may exit 1 on the update nag — verify via log "Output
  written on … (N pages)". Paper is 20 pp.
- **Shell quirks:** fresh process each call; `&&` only chains native cmds — use `;` before PowerShell
  keywords; no heredoc (pipe a single-quoted here-string to `python -`); kill with `Stop-Process -Id <PID>`
  only. `git add -A` can hang ingesting the untracked `.llm_cache_*/` dirs — add explicit paths only.

---

## 5. Where things live
- Paper: `paper/tex/consensus-lies.tex` (20 pp, CHI reframe, acmsmall/PACMHCI) + `references.bib` (verified,
  owner to re-check) + `figures/`. Compiled PDF + Stage-1/2 reports in the session `files/` folder.
- Living record: `paper/decisions/DECISION-LOG.md` (**row 88**). Prereg/amendments: `paper/preregistration/`.
- Study-2 design/prereg: `paper/plans/2026-07-23-study2-latent-premise-sensitivity-design.md`,
  `…study2-eval-redesign.md`, `paper/preregistration/2026-07-23-study2-prereg-FROZEN.md`.
- Plans/aids: `paper/plans/` (CHI reframe spec, Phase B design, finalize-writeup spec), `paper/research/`
  (landscape audit, references verification, figure playbook, R5 novelty), `paper/writing/` (deviations).
- Abstention KIT: `scripts/abstention_sample.py` / `abstention_score.py`, `files/abstention_coding_sheet.csv`
  (owner codes) + hidden `abstention_key.csv` + `abstention_coding_instructions.md`.

---

## 6. Laws (unchanged, inviolable)
Orchestrator-only (Manager writes ONLY specs/plans/reports/decision-log/amendments under `paper/*`, owns
git/gh, spawns a sub-agent in a worktree for EVERY code/audit/fix). Provenance separation (Law 6):
implementer=Claude family, hostile auditor=different family (GPT gpt-5.6-sol), report-only. Merge only after
build+run + suite green + cross-family audit 0 BLOCKER/MAJOR (Law 4). Executable gold > LLM-judge (Law 7);
pre-register before scaling; anti-leakage (self-generated prompts contain NO gold/target/foil/key_questions).
One clean audit → merge; don't re-audit endlessly (Law 5). NEVER edit frozen files or the main checkout
directly. NEVER fabricate data (the Manager REFUSED to simulate the abstention human labels — hold that line).
Owner prefers Chinese (中文) responses; caution-first on scaling; escalate every SCIENTIFIC judgment call.
