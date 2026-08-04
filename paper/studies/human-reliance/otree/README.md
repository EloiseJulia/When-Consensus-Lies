# oTree app — human-reliance study (Phase 8)

Runnable **oTree 6** experiment implementing `../SURVEY-implementation.md`. **Bilingual** (English /
简体中文, chosen by the participant on the first page). Within-subjects, 3 display conditions
(single / fake / dep) × 12 items, balanced Latin square, per-participant trial- and option-order
randomization. Exports one row per trial matching `../analysis/preregistered_analysis.py`.

## Layout
```
settings.py            one session config 'reliance' + a ROOM 'reliance' (stable participant link)
requirements.txt       otree>=5.10 (validated on 6.0.15) + psycopg2-binary (deploy DB)
runtime.txt Procfile render.yaml   free-tier deploy (see DEPLOY.md)
_static/               required by oTree (kept empty)
reliance/
  __init__.py          Constants, models, Latin-square assignment, pages, custom_export
  content.py           ALL bilingual UI strings (UI['en'|'zh']) + MODELS (shown model names)
  stimuli.py           the 12 audited items, bilingual (STIMULI-v2)
  tests.py             PlayerBot (headless full-flow test; picks a random language)
  Language.html Consent Instructions WorkedExample Comprehension Trial AttentionCheck
  Demographics Debrief  page templates (each wrapped in lang=zh-Hans + CJK font for zh)
```

## Run
```bash
pip install -r requirements.txt

# validate the whole flow headlessly (6 bots through all pages) + export the trial-level CSV
otree test reliance 6 --export=_botdata
#   -> _botdata/reliance_custom.csv  (schema matches the analysis script)

# interactive preview WITH debug info (dev):        otree devserver 8001
# clean preview WITHOUT debug info (like production): 
#   set OTREE_PRODUCTION=1 ; otree resetdb --noinput ; otree prodserver 8001
# then create a session (admin -> Sessions, config 'reliance') and open its participant link,
# or share the Room 'reliance' participant URL. Deploy for real via DEPLOY.md.
```

## Design implementation notes
- **One link, in-app language:** the first page (`Language`) lets the participant pick English or
  简体中文; the choice is stored in `participant.vars['lang']` and drives every later page. Chinese
  pages are wrapped in `<div lang="zh-Hans" style="…CJK font…">` so browsers render Simplified glyphs.
- **Latin square:** `condition(group g, item i) = CONDITIONS[(i + g) % 3]`; `g = (id_in_subsession-1) % 3`
  (round-robin). Each participant sees each item once, 4 per condition; balanced across the 3 groups.
- **Randomization:** trial order and the 4-option order are shuffled per participant/trial in
  `creating_session`; the GOLD option's position is stored for objective scoring.
- **Display cards (consistent 1-vs-5):** the same card style shows model chips with **real names**
  (`MODELS = ChatGPT, Gemini, Claude, Copilot, DeepSeek`) — **single** = 1 chip, **fake/dep** = 5 chips
  all agreeing. `dep` adds a dependence-disclosure banner (matched-length; does not reveal the correct
  value). Instructions pre-announce that some tasks show 1 AI and some show 5.
- **DVs:** `accept` (radio: use-as-is / flag-missing-info), `gap_choice` (shown only if flagged;
  JS-toggled), `confidence` (**1–5 star** rating), `rt_ms` (JS timer). `gap_correct` computed in
  `before_next_page`.
- **Quality gates:** comprehension check (correct option pre-selected; ≤2 attempts; flags
  `passed_comprehension`), one attention-check screen at round 7 (`passed_attention`); straightlining
  computed in `custom_export`.
- **Demographics:** age **bracket** (incl. "Under 18") + AI-use frequency (exploratory).
- **Export → analysis:** `custom_export` emits
  `participant_id,item_id,condition,accept,confidence,gap_correct,rt_sec,order_index,group_g,lang,
  passed_comprehension,passed_attention,total_time_sec,straightline_confidence,duplicate_id,
  age_group,ai_use`. Validated end-to-end:
  `python ../analysis/preregistered_analysis.py --data _botdata/reliance_custom.csv`.

## Before launch (‹CONFIRM›)
- Fill `total_time_sec` per participant (from oTree page timings) if the min-time exclusion is used.
- Payment / participation_fee; recruitment channel (team-run: Prolific or local pool).
- **All ages are allowed** (no 18+ gate) — per IRB, **minors typically need guardian consent**; confirm.
- Update the pre-registration to match (confidence = 5-star; real model names; age brackets), then
  freeze the code together with it.
