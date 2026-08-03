# oTree app — human-reliance study (Phase 8)

Runnable oTree 6 experiment implementing `../SURVEY-implementation.md`. Within-subjects, 3 display
conditions (single / fake / dep) × 12 items, balanced Latin square, per-participant trial- and
option-order randomization. Exports one row per trial matching `../analysis/preregistered_analysis.py`.

## Layout
```
settings.py            session config (SESSION_CONFIGS: 'reliance', 6 demo participants)
requirements.txt       otree>=5.10 (validated on 6.0.15)
_static/               required by oTree (kept empty)
reliance/
  __init__.py          Constants, models, Latin-square assignment, pages, custom_export
  stimuli.py           the 12 audited items (STIMULI-v2)
  tests.py             PlayerBot (headless full-flow test)
  *.html               page templates (Consent, Instructions, Comprehension, Trial,
                       AttentionCheck, Demographics, Debrief)
```

## Run
```bash
pip install -r requirements.txt

# validate the whole flow headlessly (6 bots through all pages) + export the trial-level CSV
otree test reliance 6 --export=_botdata
#   -> _botdata/reliance_custom.csv  (schema matches the analysis script)

# interactive preview
otree devserver          # then open the printed URL; create a 'reliance' session

# production (Prolific): set OTREE_SECRET_KEY, OTREE_ADMIN_PASSWORD, deploy (Heroku/otree hub),
# use the session-wide completion link as the Prolific completion URL.
```

## Design implementation notes
- **Latin square:** `condition(group g, item i) = CONDITIONS[(i + g) % 3]`; `g = (id_in_subsession-1) % 3`
  (round-robin). Each participant sees each item once, 4 per condition; balanced across the 3 groups.
- **Randomization:** trial order and the 4-option order are shuffled per participant/trial in
  `creating_session`; the GOLD option's position is stored for objective scoring.
- **DVs:** `accept` (radio), `gap_choice` (shown only if flagged; JS-toggled), `confidence` (0–100 slider),
  `rt_ms` (JS timer). `gap_correct` computed in `before_next_page`.
- **Quality gates:** comprehension check (≤2 attempts, flags `passed_comprehension`), one attention-check
  screen at round 7 (`passed_attention`); straightlining computed in `custom_export`.
- **Export → analysis:** `custom_export` emits the exact columns
  `participant_id,item_id,condition,accept,confidence,gap_correct,rt_sec,order_index,group_g,
  passed_comprehension,passed_attention,total_time_sec,straightline_confidence,duplicate_id`.
  Validated end-to-end: `python ../analysis/preregistered_analysis.py --data _botdata/reliance_custom.csv`.

## Before launch (‹CONFIRM›)
- Fill `total_time_sec` per participant (from oTree page timings) if the min-time exclusion is used.
- Confidence slider currently defaults to 50; add "must-move" enforcement if a no-default slider is required.
- Confirm payment/participation_fee, attention-check wording, and Prolific integration.
- Freeze code together with the pre-registration.
