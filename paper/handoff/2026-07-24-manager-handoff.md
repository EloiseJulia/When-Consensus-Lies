# Manager Handoff — "When Consensus Lies" (2026-07-24, session 3 retiring)

> Authoritative current-state handoff from the retiring Manager+Lead-Researcher session (context saturated)
> to a fresh session. READ THIS FIRST, then re-derive ground truth from git (`git --no-pager log --oneline
> -40 main`; `git branch -a`; `git worktree list`) — trust the log over any narrative. Supersedes the
> 2026-07-23 handoff for current state; earlier handoffs remain valid for history. DECISION-LOG is at **row
> 105**.

## 0. One-paragraph status
The paper has TWO studies, both now with substantial results. **Study 1 (original, DONE):** the pre-registered
confirmatory silent-convergent-delusion finding (two-regime main effect keyed on disambiguator LOCATION;
`cd≈0.53`, `n_eff=1.10`); written up as a **24-page CHI draft** (compiles clean). **Study 2 (DONE for
detection + intervention):** the black-box **Latent-Premise Probing (LPP)** detector. **DETECTION CONFIRMED**
(row 88; 6 models, AUROC **0.895** vs semantic-entropy 0.58) and now **WRITTEN INTO THE PAPER** + integrity
**VERIFIED** (row 103). **INTERVENTION (Phase 2b) DONE:** single-model pilot (row 95) + multi-model result
(row 105) — **both H-B1′ and H-B2′ MET**, with an honest cross-model nuance (see §1). The paper also gained:
Study-2 detection section, danger-quadrant + AUROC figures, ICE/Kim novelty differentiation, and a
selection-bias framing-hardening pass. **Two experiments remain to run:** Amendment 13 (regime×domain
crossing) and Amendment 14 (unfiltered-sample replication) — their ITEMS are built+merged, and their RUN
APPARATUS is being fixed after an audit (see §3). Owner is caution-first, prefers Chinese, and wants a
top-venue research-partner who sharpens the science, not just an executor.

## 1. The science — current strongest claims
**Study 1 (frozen; DONE):** two-regime MAIN effect keyed on the disambiguator's LOCATION (not capability).
H1_external silent convergent delusion `cd≈0.53`, `n_eff=1.10`, ICC=0.89; H2_derivable `cd=0`. Cross-family ≈
homogeneous (TOST). Selection-bias caveat honestly disclosed + rebutted by within-item k0-vs-k1 controls
(§Construct validity; row 98). Detection-integrity of Study-2's per-model routing VERIFIED (row 103) — the
paper stands; NO reported result was ever invalidated.

**Study 2 detection (CONFIRMED, in paper):** pooled AUROC(H_ctx-self)=**0.895** [0.815,0.966] vs
semantic-entropy **0.581**; danger-quadrant 0.758 (25/33); all 6 frontier models 0.86–0.89. HONEST caveats
(kept): requirements-probing baseline strong (0.81 → pinning increment modest +0.085); localization weak
(0.36). Positioned vs ICE (Hou 2024) + Kim 2025 (row 92).

**Study 2 intervention (Phase 2b, DONE — rows 95, 105):** BOTH pre-registered directions MET.
- **H-B1′ (selective clarification):** LPP reaches the SOTA-blind danger zone — danger-subset AMB+ coverage
  **0.730 vs semantic-entropy 0.149**; pooled net **0.321** [0.188,0.448] > every baseline. **HONEST cross-
  model nuance (the key scientific subtlety):** SELECTIVITY is model-dependent — gpt-5.6-sol (reasoning) is
  clean (over-clarification 0.000, net 0.667 in the pilot); pooled across weaker models over-clarification
  rises (0.408), lowering pooled net. So LPP reliably COVERS the danger zone; its PRECISION varies by model.
- **H-B2′ (oracle resolution):** ROBUST across models — supplying the deleted axis's gold convention (a
  controlled simulated-user oracle) nearly eliminates the failure (cd **0.604→0.014**, I0-hit 0.931), by
  executable gold. Real-user study = future work.
- The multi-model run: 4 models complete; gemini-3.1-pro-preview partial (~73%); gemini-3.5-flash
  excluded/partial (a pathological proxy generation-hang, operational not scientific); 163 N/A cells EXCLUDED
  from all metrics (disclosed). Report: `files/study2_intervention_5model_results.md`.

## 2. Pre-registration & governance (INVIOLABLE)
- **Study 1** prereg FROZEN `c0a0393`; amendments A01–A12 signed. **Study 2** prereg FROZEN
  `paper/preregistration/2026-07-23-study2-prereg-FROZEN.md`. **Amendment 13** (regime×domain crossing) and
  **Amendment 14** (unfiltered-sample replication) are **owner-RATIFIED** (rows 94, 96;
  `...amendment-13-...-RATIFIED.md`, `...amendment-14-...-RATIFIED.md`). A14 carries an explicit
  scientific-integrity clause: **report honestly regardless of outcome; prominence not suppression; drop ONLY
  for methodological invalidity, never to hide a valid disconfirming result.**
- **Frozen-contract changes still require owner @EloiseJulia PERSONAL ratification. Never AI-self-sign.** Every
  design change → DECISION-LOG row + (if it touches a prereg) a formal Amendment.
- Owner granted **full autonomy for the current window** (row 97) within ratified designs + laws; HOLD only
  for a NEW frozen-contract change or a genuine scientific pivot.

## 3. Immediate next steps (in priority order)
1. **Finish the two sub-agents:**
   - `intv-writeup` — **DONE + COMMITTED** on branch `slice/study2-intervention-writeup` at **`8a5a210c`**
     (worktree `.worktrees/intv-writeup`, agent idle). Writes the Phase-2b intervention into the paper
     (replaces the `\todo{forthcoming}`), honest framing per §1; `paper/tex/consensus-lies.tex` only
     (+67/−9), self-check green (pdflatex×2 clean, **27 pages**, 0 undefined refs). **NOT merged — needs GPT
     (gpt-5.6-sol) cross-family number-fidelity + overclaim audit FIRST (Law 6), then merge.** Every inserted
     number is listed in the agent's delivery report (see git log / agent transcript) for the audit diff.
   - `amd-run-apparatus` (branch `slice/amd-run-apparatus`, worktree `.worktrees/amd-run`, agent idle):
     **FIXES DELIVERED at commit `07ab83f3`.** One GPT audit round already ran (found 2 BLOCKER + 3 MAJOR +
     1 MINOR — all legit integrity flaws) and the implementer fixed ALL of them: strict
     `ALLOWED_CONFIGS={single,heterogeneous-MAD}` (kills the `interpretation-diverse` gold-leakage path) +
     anti-leakage test on ACTUAL generated prompts; report path-isolation guard on every checkpoint read /
     report write; **the manipulation-check now actually supplies the oracle hint** (deleted-axis key_questions
     as controlled clarification, scored by executable I0 labeling); A13 crossing claim now REQUIRES a PASS
     manipulation verdict (executable gate); regime×domain interaction analysis added (both code_spec AND
     policy_qa must be powered); A14 honesty test parameterized over high/attenuated/null. Full suite **1162
     passed, 1 skipped**; dry-runs amd13=576, amd14=1152, manip=144; `--configs interpretation-diverse`→exit 2.
     **NEEDS a fresh GPT cross-family RE-AUDIT of `07ab83f3` (Law 5: one clean audit → merge). Do NOT run
     A13/A14 live until this is re-audited clean + merged.**
2. **Run Amendment 13 (regime×domain):** first the MANIPULATION-CHECK gate (`amd13_manipulation_check.py`:
   oracle-hint recovery — H2 high / H1 low; **if it FAILS, report honestly and HOLD — do NOT tune**). Only if
   it PASSES: run `amd_run.py --which amd13` (single + heterogeneous-MAD, ≥3 seeds) → `amd_run_report.py`
   (per-domain cd(H1)−cd(H2) + regime×domain interaction; H-A13 = regime effect not domain-confounded). Write
   into the paper as pre-registered secondary robustness.
3. **Run Amendment 14 (unfiltered replication):** `amd_run.py --which amd14` → unconditioned pooled cd vs the
   screened ~0.53. **Report HONESTLY regardless of outcome** (A14 §0 clause). Update the Construct-validity
   framing with the actual result (it currently says "forthcoming").
4. **Write Study 2 fully + AU-Probe (Phase 2c, SECONDARY, still not started):** small open CPU white-box
   probe contrast; descope-able. Then re-assess venue length (owner deferred).
5. **Owner-only submission gates (blocking, NOT Manager-doable):** (a) code the abstention human-validation
   KIT (`files/abstention_coding_sheet.csv`, ~316 rows) → `scripts/abstention_score.py`; (b) verify
   `references.bib`; (c) rewrite AI-assisted prose in own voice per CHI LLM-authorship policy; (d) decide CHI
   `sigconf` template.

## 4. Tech facts the next Manager needs (VERIFIED this session — read carefully)
- **All runs $0** via the local **ghc-api Copilot proxy** `http://127.0.0.1:8313/v1` (no token, ~40 models).
  MUST be running for live work. The proxy is SLOW for reasoning/gemini models (each call several seconds;
  each LPP cell ≈ 15 calls) — multi-model runs take HOURS. Proxy 504-hangs recur → runners die/stall.
- **⚠️ CACHE-KEY / MODEL-ROUTING GOTCHA (critical, now fixed but be careful):** `common/llm._cache_key` +
  generation historically fell back to the ROLE model when a caller passed `model` without `family` (the
  `lps_method._complete_text` path). FIXED (row 101, shared-infra, backward-compatible). BUT: **for multi-
  model LPS runs, ALWAYS use `--shard-by-model` (per-model cache dirs).** A non-sharded multi-model run
  sharing one cache collided (all models replayed the first model's cached data) — caught pre-paper by
  verifying raw per-model data (Law 1). Memory stored.
- **Concurrent per-model runners:** `lps_intervention.py --models <slug> --roster-models <all N> --shard-by-
  model` (row: the `--roster-models` flag lets 6 concurrent single-model runners each stamp the FULL roster so
  the strict merge accepts them; ~6× speedup, detection-proven). Launch each as a detached `Start-Process`;
  monitor via a ~20-min schedule; relaunch-DEAD-only (do NOT kill alive runners — a slow cell must not be
  interrupted); do NOT spawn duplicate runners for the same model (they deadlock on the shard).
- **⚠️ gemini-3.1-pro slug was RENAMED to `gemini-3.1-pro-preview`** by the proxy (row 103). Check
  `/v1/models` for current slugs before a run.
- **Per-cell fault tolerance (row 104):** `lps_intervention.py` records a hanging/erroring cell as an N/A cell
  (240s wall-clock guard, Windows-safe) so one bad cell can't block a shard; merge counts N/A as present;
  report EXCLUDES N/A from all metrics + discloses. gemini-3.5-flash hangs on `code_invoice` (complex 3-part
  output) — handled via N/A. To close out a run without the slow tail, you can N/A-fill missing cells (a
  script pattern is in the session history: build N/A records with the shard's `_fingerprint` + task fields).
- **Study-2 code (all on main, additive):** `scripts/lps_method.py`, `lps_gold.py`, `lps_confirm*.py`,
  `lps_intervention*.py` (driver+merge+report, fault-tolerant, `--roster-models`), `lps_baselines.py`. A13/A14
  run apparatus (`amd_run.py`, `amd13_manipulation_check.py`, `amd_run_report.py`) is on branch
  `slice/amd-run-apparatus` (fixing audit findings — NOT merged). Sidecar items+gold merged:
  `bench/amd13_sidecar.py` + `bench/data/amd13_*.jsonl`; `bench/amd14_sidecar.py` +
  `bench/data/amd14_unfiltered.jsonl`. ~1128+ tests green.
- **LaTeX:** MiKTeX `C:\Users\v-elzhang\AppData\Local\Programs\MiKTeX\miktex\bin\x64` (NOT on PATH); `pdflatex
  ×1 → bibtex → pdflatex ×2`; verify via log "Output written on … (N pages)". Paper is **24 pp**.
- **Shell quirks:** fresh process each call; `&&` only chains native cmds (use `;` before PowerShell keywords);
  no heredoc (pipe a single-quoted here-string to `python -`); kill procs with `Stop-Process -Id <PID>` only
  (name-based kills are blocked). `git add -A` hangs on untracked `.llm_cache_*/` — add explicit paths.
  `bare pytest -q` has a PRE-EXISTING `ModuleNotFoundError: analysis`; use `python -m pytest`.
  Get-CimInstance CommandLine matches can false-match your own inspection command's string.

## 5. Where things live
- Paper: `paper/tex/consensus-lies.tex` (24 pp) + `references.bib` + `figures/`. Reports in the session
  `files/` folder (`study2_intervention_5model_results.md`, `study2_intervention_report.md`,
  `study2_stage2_results.md`). Compiled PDFs in session `files/`.
- Living record: `paper/decisions/DECISION-LOG.md` (**row 105**). Prereg/amendments: `paper/preregistration/`
  (Study-2 FROZEN; A13/A14 RATIFIED). Specs/plans: `paper/plans/`. Research: `paper/research/`
  (incl. `2026-07-23-novelty-collision-review.md`).
- In-flight worktrees: `.worktrees/amd-run` (A13/A14 apparatus), `.worktrees/intv-writeup` (intervention
  writeup). Merged-branch worktrees are cleaned up after each merge.

## 6. Laws (unchanged, inviolable)
Orchestrator-only (Manager writes ONLY specs/plans/reports/decision-log/amendments under `paper/*`, owns
git/gh, spawns a sub-agent in a worktree for EVERY code/audit/fix — even one-liners). Provenance separation
(Law 6): implementer=Claude family, hostile auditor=different family (GPT gpt-5.6-sol), report-only. Merge only
after build+run + suite green + cross-family audit 0 BLOCKER/MAJOR (Law 4); shared-infra changes called out
prominently. Executable gold > LLM-judge (Law 7); pre-register before scaling; anti-leakage (self-generated
prompts contain NO gold/target/foil/key_questions). One clean audit → merge; don't re-audit endlessly (Law 5).
Verify the REAL artifact, not just green tests (Law 1) — this session caught TWO silent bugs (cache-collision,
gemini hang) by checking raw per-model data before writing to the paper. NEVER edit frozen files or the main
checkout directly. NEVER fabricate data. Owner prefers Chinese; caution-first on scaling; escalate every
SCIENTIFIC judgment; never AI-self-sign "owner".

## 7. Research-partner mandate (why the next session exists — not just an executor)
The owner explicitly wants a **top-venue (CHI/CSCW/IUI/ACL/NeurIPS) research partner**, not only an
orchestrator. Continuously judge: (a) is the design still a novel, falsifiable, defensible contribution;
(b) reframe with results (this session's honest H-B1′ model-dependent-selectivity nuance is a FEATURE, not a
failure — lead with H-B2′'s robust resolution + the SOTA-blind coverage, report the selectivity honestly);
(c) pre-empt every reviewer objection (construct validity, artifact, simulated-user overreach, provenance,
pre-registration completeness, statistical power, selection bias — the last two already hardened this session);
(d) always know the single strongest publishable claim and what evidence is still missing. Honest nulls are a
FEATURE. Bring sharper framing, related-work threats, and "which one analysis would make a skeptical reviewer
concede." **Single strongest claim right now:** *In a black-box, cross-vendor, inference-only setting, LPP
surfaces + counterfactually pins hidden premises to detect the "confident latent-premise ambiguity" that SOTA
semantic entropy is blind to (AUROC 0.895 vs 0.58, consistent across 6 frontier models), and the failure is
constructively RESOLVABLE by supplying the specific surfaced premise (cd 0.60→0.01) — a full detect-and-fix
loop for a failure mode the field currently cannot see.*
