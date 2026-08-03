# Survey implementation spec (DRAFT) — human-reliance study (Phase 8)

Serves `PREREGISTRATION.md` + `STIMULI-v2.md`. Output data must match the schema in
`analysis/preregistered_analysis.py`. **Needs owner sign-off before build/freeze.**

---

## 1. Platform

**Recommended: oTree** (Python, open-source). Why: the design (within-subjects Latin square,
per-trial option randomization, condition assignment balanced across participants, objective
gap-ID scoring) is a few lines of Python; it exports one-row-per-trial CSV that maps **directly** to
the analysis schema; it is reproducible (code frozen with the pre-reg); integrates with Prolific via
completion URL. Hosting: Heroku/other, or a lab server.

**No-code fallback: Qualtrics.** Feasible via loop-&-merge + embedded data + a randomizer, and IRBs
know it. Limitations to accept: the balanced item×condition Latin square is awkward (approximate with
a 3-arm randomizer + evenly-distributed quotas); per-trial option-order randomization needs
question-level randomization; export is wide and needs reshaping to the trial-level schema.

**Recruitment:** Prolific (screeners: fluent English, ≥95% approval, desktop). One session, ~10 min.

> Decision needed (‹CONFIRM›): oTree (recommended, reproducible) vs Qualtrics (no-code).

## 2. Assignment & randomization (frozen scheme)

- **Condition assignment (balanced Latin square).** Items indexed `i = 0..11`. Each participant is
  assigned a rotation group `g ∈ {0,1,2}` by **round-robin on arrival** (1st→0, 2nd→1, 3rd→2, 4th→0…).
  Condition for (participant, item) is:
  ```
  condition(g, i) = CONDITIONS[(i + g) mod 3]     # CONDITIONS = [single, fake, dep]
  ```
  → each participant sees each of the 12 items **once**, with **4 items per condition**; across the
  three groups each item appears in all three conditions equally (balanced). Record `g` per participant.
- **Trial order:** the 12 trials are presented in a **random order per participant** (record `order_index`).
- **Option order:** the 4 clarifying options are shuffled **per trial** (so the GOLD position varies);
  record which position was GOLD and which the participant chose.
- **Seeds:** store the RNG seed / assignment per participant for reproducibility.

## 3. Flow (~10 min) and quality gates

1. **Consent** (see IRB doc). No stimulus before consent.
2. **Instructions** + a worked non-scored example.
3. **Comprehension check** (must pass, ≤2 attempts, else screen out): e.g. "In each task your job is to
   decide whether the AI answer can be used as-is, or whether key information is missing." (single correct
   option among plausible foils).
4. **12 trials** (§4). One **instructed-response attention check** is inserted as its **own screen**
   between two trials (NOT inside a clarifying-option list, to avoid corrupting gap-ID scoring), e.g.:
   "To show you are reading, select 'Disagree' below." → [Agree / Disagree / Neutral].
5. **Short demographics** + one AI-literacy item (exploratory moderator).
6. **Debrief** (see IRB doc): the multi-model "agreement" displays were curated illustrations and the
   answers were deliberately underspecified; explains the study aim.

**Exclusions (logged, applied in analysis):** failed comprehension (2×); failed attention check;
total time < ‹CONFIRM 120s›; zero-variance confidence across all 12 trials (straightlining);
duplicate Prolific/IP id. Replace excluded up to the recruitment cap.

## 4. Per-trial screen

Layout (identical skeleton across conditions; only the **evidence block** changes):

```
[ Scenario ]   «scenario text»
[ Task ]       «task text»
[ Evidence ]   «CONDITION-SPECIFIC block — see §5»
---------------------------------------------------------------
Q1 (primary, behavioral):  What would you do?
     ( ) Use this answer as-is
     ( ) Flag that key information is missing / ask a clarifying question first
IF "Flag" →  Q1b (objective gap-ID): Which clarifying question is most important?
     [ 4 options, order randomized; exactly one is the GOLD ]
Q2 (primary, subjective):  How confident are you this answer is correct as given?
     0 ──────────────●────────────── 100   (slider; no default; must move to proceed)
```
Record per trial: `condition, accept(=1 if "use as-is"), gap_correct(1/0 if flagged else blank),
confidence, rt_sec, order_index, gold_position, chosen_option`.

## 5. The three display conditions — concrete UI copy

The **scenario, task, and answer text are byte-identical** across conditions. Only the evidence framing
differs. To keep the **dep vs fake** contrast clean, `fake` carries a **length-matched neutral banner**
so the H-U2 effect isolates the *dependence content*, not the mere presence of a banner.

Using Item 01 as a worked example (answer = "Q1 revenue (January–March) was **$2.4M**."):

**Condition `single`** (one model — baseline):
```
🤖 AI assistant answered:
   “Q1 revenue (January–March) was $2.4M.”
```

**Condition `fake`** (unanimous consensus + neutral matched banner):
```
✅ 5 of 5 AI models agree:
   [Model A ✓] [Model B ✓] [Model C ✓] [Model D ✓] [Model E ✓]
   “Q1 revenue (January–March) was $2.4M.”
   ℹ Five separate AI models were each queried and all five returned this answer.
```

**Condition `dep`** (same consensus + dependence disclosure, matched length; does NOT reveal the correct value):
```
✅ 5 of 5 AI models agree:
   [Model A ✓] [Model B ✓] [Model C ✓] [Model D ✓] [Model E ✓]
   “Q1 revenue (January–March) was $2.4M.”
   ⚠ These five answers are not independent: all five made the same single unstated
     assumption, so together they count as about one independent check, not five.
```

Notes:
- `fake`'s neutral banner ("five separate … all five returned") reinforces the *apparent* independence
  the interface implies (the fake-redundancy framing the paper critiques); `dep`'s banner corrects it
  **without** naming which convention/value is right. Banners are matched in length and visual weight.
- Model badges are generic labels (Model A–E), not real vendor names, to avoid brand effects.
- `single` is intentionally lighter (one model): the consensus display itself is part of the H-U1
  manipulation. The **matched** comparison is `dep` vs `fake` (H-U2), where both carry the 5-model block
  + a banner.
- Apply the identical three templates to all 12 items (answer/scenario swapped in).

## 6. Timing budget
Consent+instructions+comprehension ≈ 2 min; 12 trials × ~35 s ≈ 7 min; demographics+debrief ≈ 1 min →
≈ 10 min total. Pilot (n≈5) to confirm median time and comprehension pass-rate before launch.

## 7. Open items (‹CONFIRM›)
- Platform (oTree vs Qualtrics); hosting.
- Min-time threshold; attention-check exact wording.
- Whether model badges show "Model A–E" (recommended) or realistic vendor names.
- Demographics fields + the single AI-literacy item wording.
