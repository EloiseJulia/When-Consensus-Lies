# Human-validation study — *When Consensus Lies* (Phase 8)

**Do people over-rely on unanimous multi-model AI "consensus," and does disclosing evidential
dependence reduce it?**

This folder contains the complete design of a pre-registered online experiment that accompanies the
system paper *When Consensus Lies: Fake Redundancy in Multi-Model AI Systems*. It is the authoritative
entry point; each component has its own file (see the [directory map](#directory-map)).

> **Status:** design complete and internally validated (power simulation, cross-family stimulus audit,
> bot-tested survey app, frozen analysis validated end-to-end). **Not yet frozen or run.** Data
> collection must not begin until the pre-registration is frozen on OSF/AsPredicted and IRB
> determination is obtained.

---

## 1. Why this study

The paper establishes, as **properties of the system** (no humans required):

- **A — fake redundancy.** Five same-prompt agents supply ≈ one independent judgment
  (n_eff = 1.10, ICC = 0.89; the within-item k=0-vs-k≥1 control gives ΔCD = 0.82).
- **B — interfaces mask it.** Current product UIs render this as independent corroboration ("N/N agree").

Two further claims the paper currently **borrows from the literature** rather than measures:

- **C — over-reliance.** People read unanimity as reliability and under-account for source
  non-independence (*correlation / system neglect*: Budescu & Yu 2007; Enke & Zimmermann 2019;
  Levy et al. 2022).
- **D — the fix.** Surfacing *evidential dependence* would reduce that over-reliance (the demoted §9
  design implications, and the abstract's normative "should").

**This study measures C and D directly.** It is **not logically required** — the paper's argument
closes on the system properties A/B and the borrowed C. Its purpose is to (i) convert *borrowed → measured*,
and (ii) put a human in the loop so the work sits comfortably at CSCW. Success lets the paper **re-earn**
the demoted design implications (§9) and the normative abstract line with first-party evidence. The design
is deliberately narrow: it tests **only** C and D and adds no other defensive arms.

## 2. Hypotheses (pre-registered, directional)

Conditions: **single** (one-model answer) · **fake** ("5 of 5 models agree") · **dep** (same consensus,
with a disclosure that the models are *not independent*, without revealing the correct value).

| ID | Claim | Prediction |
|----|-------|------------|
| **H-U1a** | C | P(accept-as-is \| fake) > P(accept-as-is \| single) |
| **H-U1b** | C | confidence(fake) > confidence(single) |
| **H-U2a** | D | P(accept-as-is \| dep) < P(accept-as-is \| fake) |
| **H-U2b** | D | confidence(dep) < confidence(fake) |

Exploratory: dep vs single; objective gap-identification by condition; moderation by AI-literacy.

## 3. Design

- **Online, within-subjects**, single ~10-minute session (Prolific, general population).
- **3 display conditions × 12 items**, balanced **Latin square**: `condition(group g, item i) =
  CONDITIONS[(i + g) mod 3]`, with `g` assigned round-robin on arrival. Each participant sees each item
  **once** (4 items per condition); across the three groups each item appears in all three conditions
  equally. Trial order and the 4 clarifying-option positions are randomized per participant/trial.
- Participants do **not** hold the missing convention (matches the paper's lost-handoff narrative, §8.4):
  the decisive disambiguator is outside the shown prompt (H1_external family).

## 4. The three display conditions

The **scenario, task, and answer text are identical** across conditions; only the evidence framing
differs. `fake` carries a **length-matched neutral banner** so the key **dep vs fake** contrast isolates
the *dependence content*, not the mere presence of a banner. Worked example (Item 01):

- **single** — `🤖 AI assistant answered: "Q1 revenue (January–March) was $2.4M."`
- **fake** — `✅ 5 of 5 AI models agree: [Model A–E ✓] "…$2.4M." ℹ Five separate AI models were each
  queried and all five returned this answer.`
- **dep** — same consensus block + `⚠ These five answers are not independent: all five made the same
  single unstated assumption, so together they count as about one independent check, not five.`

Model badges are generic (Model A–E) to avoid brand effects. `single` is intentionally lighter (the
consensus display itself is part of the H-U1 manipulation); the *matched* comparison is dep vs fake.

## 5. Stimuli

**12 lay-readable items**, each a workplace-handoff scenario whose answer silently commits to one value
of a single unstated convention. Convention types (one per item): fiscal-year start · rounding/remainder
· inclusive/exclusive date range · dedup · top-N tie · timezone · unit/scale · percentage base ·
mean-vs-median · business-vs-calendar days · sort tie-break · null/blank handling.

Each item has 4 clarifying-question options: exactly **one GOLD** (names the decisive gap) and three
**cosmetic/non-decisive** distractors, giving clean objective gap-identification scoring.

**Provenance (Law 6).** Items were authored by an Anthropic-family model (Opus) and independently
audited for construct validity by a **different family** (GPT-5.6), which caught a broken item (07, no
divergent answer) and a math-trap item (08), both replaced, and tightened all distractors. See
`STIMULI-v2.md` (final) and `STIMULI-draft.md` (v1 + audit trail). **Still needs owner sign-off.**

## 6. Measures

- **Primary — behavioral:** `accept` (1 = use answer as-is; 0 = flag missing info). Flagging is the
  appropriate response on every item.
- **Primary — subjective:** `confidence` 0–100.
- **Objective gold (no LLM judge):** `gap_correct` — when a participant flags, whether they pick the
  clarifying question that names the true missing convention (deterministic against the item key).
- Secondary/exploratory: clarifying-question distribution, response time, AI-literacy moderation.

## 7. Procedure (~10 min)

Consent → instructions + worked example → comprehension check (≤2 attempts) → **12 trials** → one
instructed-response attention-check screen (round 7) → brief demographics + one AI-literacy item →
**debrief** (discloses the curated "consensus" displays and the intentional underspecification).

**Pre-specified exclusions:** failed comprehension (2×); failed attention check; total time < 120 s
(‹CONFIRM›); zero-variance confidence (straightlining); duplicate ID. Excluded participants are
replaced up to the recruitment cap.

## 8. Sample & power

Simulation-based (GEE logistic with participant + item random intercepts). Assumptions:
p(accept\|single)=.55, fake=.72, dep=.56; SD_participant=.6, SD_item=.5 (logit); one-sided α=.025/family.

| items | N | H-U1 (fake>single) | H-U2 (dep<fake) | **both** |
|-------|---|--------------------|-----------------|----------|
| 9  | 50 | .80 | .76 | .66 |
| **12** | **50** | **.93** | **.90** | **.85** |
| 12 | 60 | .94 | .93 | .90 |
| 12 | 50 (conservative) | .71 | .53 | .43 |

**Decision:** **12 items; recruit ≈ 65 → ≈ 55 analyzable.** H-U2 (D) is the power-limiting arm, so the
dependence disclosure is made maximally salient. Pre-registered smallest effects of interest:
fake−single ≥ 10 pp on accept; dep−fake ≥ 8 pp (‹CONFIRM›). The reproduction script is in the analysis
folder.

## 9. Analysis (frozen with the pre-registration — Law 7)

- **accept** (behavioral): **GEE logistic**, exchangeable, participant-clustered, item fixed effects —
  the confirmatory engine (matches the power simulation). Crossed-random-intercept GLMM as sensitivity.
- **confidence** (subjective): **linear mixed model** with crossed participant + item random intercepts.
- Directional one-sided tests; **Holm** correction across the 4 primary contrasts at family-wise α = .05.
- The script (`analysis/preregistered_analysis.py`) is written and validated on *simulated* data
  **before** data collection: it rejects all 4 hypotheses under the pre-registered effect and ~none under
  the null. Only the input data file changes at run time.

## 10. Ethics

Minimal-risk, with **authorized (mild) deception + full debrief** (the "5/5 agree" displays are curated
illustrations, not live model outputs; tasks are intentionally underspecified). Anonymous platform IDs
only; fair pay (~$2 / 10 min ≈ $12/hr). Consent states some details are withheld until the end; the
debrief discloses everything and offers data withdrawal. Files in `ethics/`. **IRB/exempt determination
at Chang'an University required before launch.**

## 11. Implementation

Runnable **oTree 6** app in `otree/` implementing the design above. Validated headlessly with bots
(`otree test reliance 6`) across the full flow, and its `custom_export` produces one row per trial in the
**exact schema** the analysis script consumes — verified end-to-end
(`oTree export → preregistered_analysis.py`). See `otree/README.md` to run/deploy.

## 12. How the results feed back into the paper

- **If C and D hold:** re-promote the §9 design implications from "falsifiable conjectures" back to
  evidence-backed implications; restore the abstract's normative "should"; foreground the
  human-in-the-loop framing for CSCW.
- **If only C holds (not D):** keep the descriptive framing; report D as null/underpowered and discuss.
- **If neither holds:** the system contribution stands on A/B; report the human null honestly as a bound
  on the reliance mechanism. (Metrics/hypotheses are frozen, so any outcome is reportable without
  p-hacking.)

## 13. Directory map

```
README.md                     ← this overview
PREREGISTRATION.md            hypotheses, design, DVs, exclusions, analysis, power, ethics, deviations log
STIMULI-v2.md                 final 12 items (audited)
STIMULI-draft.md              v1 items + the cross-family audit trail
SURVEY-implementation.md      platform choice, Latin square, randomization, attention checks, UI copy
analysis/
  preregistered_analysis.py   FROZEN confirmatory analysis (GEE + MixedLM + Holm); self-tests on sim data
  README.md                   how to run + data schema
ethics/
  PROTOCOL-IRB-summary.md      protocol for the IRB/ethics form
  consent.md                  participant consent (authorized-deception clause)
  debrief.md                  end-of-study debrief (deception disclosure + withdrawal)
otree/
  settings.py, requirements.txt, _static/
  reliance/                   __init__.py (logic), stimuli.py (12 items), tests.py (bot), *.html (pages)
  README.md, .gitignore
```

## 14. Remaining steps (execution)

1. Owner sign-off on `STIMULI-v2.md` (esp. items 07/08) and resolve the `‹CONFIRM›` items across files
   (platform, budget, min-time, IRB route, slider-no-default, smallest effects of interest).
2. Freeze the pre-registration + analysis script + oTree code on OSF/AsPredicted.
3. IRB/exempt determination (Chang'an University).
4. Pilot (n ≈ 5) → confirm ~10-min timing and comprehension pass-rate.
5. Launch on Prolific (recruit ≈ 65) → run the frozen analysis → report.
6. Fold measured C/D back into the paper (§12).

## 15. Laws honored

Law 6 (provenance): stimuli authored and audited by different model families. Law 7 (pre-registration +
executable gold): hypotheses, metric definitions, exclusions, and the analysis script are frozen before
any run; the primary gap-identification measure is deterministic (no LLM judge). Independent adversarial
audit > self-review (cross-family stimulus audit).
