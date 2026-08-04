# oTree app — human-reliance study

Runnable **oTree 6** experiment implementing the current within-subjects study: 3 display conditions
(`single` / `fake` / `dep`) × **14 items** (9 underspecified + 5 complete controls). It is bilingual
(English / 简体中文), selected on the first in-app page, and exports one row per trial for
`../analysis/preregistered_analysis.py`.

## Layout

```text
settings.py            session config and stable `reliance` room
requirements.txt       oTree and deployment dependencies
runtime.txt Procfile render.yaml   free-tier deployment configuration
reliance/
  __init__.py          assignment, pages, validation, export
  content.py           bilingual UI strings and displayed model names
  stimuli.py           U1–U9 and C1–C5 bilingual stimulus/scoring data
  tests.py             headless PlayerBot flow test
  *.html               page templates
```

## Run

```bash
pip install -r requirements.txt
otree test reliance 6 --export=_botdata
# _botdata/reliance_custom.csv

# Development preview
otree devserver 8001
```

For a production-like preview, set `OTREE_PRODUCTION=1`, run `otree resetdb --noinput`, then
`otree prodserver 8001`. Create a session or share the `reliance` room participant URL. See
`DEPLOY.md` for Render/Fly.io deployment.

## Implementation notes

- **Language:** one participant link serves both languages. `Language` stores `en` or `zh` in
  `participant.vars`; later templates use its bilingual UI dictionary.
- **Latin square:** `condition(g, i) = CONDITIONS[(i + g) % 3]`, where
  `g = (id_in_subsession - 1) % 3`. Each participant sees all 14 items once; trial order and the
  four clarification options are randomized.
- **Completeness:** U1–U9 set `complete=False`: their answer silently assumes an omitted convention,
  so FLAG is appropriate and one randomized option is scored as GOLD. C1–C5 set `complete=True`:
  the convention is stated, so ACCEPT is appropriate; they show generic options and no gap score.
- **Display cards:** all use the same card style and real-name chips (`ChatGPT`, `Gemini`, `Claude`,
  `Copilot`, `DeepSeek`). `single` shows one chip; `fake` and `dep` show five agreeing chips.
  `dep` adds a neutral shared-prompt mechanism disclosure—not a correctness verdict.
- **Measures:** `accept` (use as-is / flag), conditional `gap_choice`, deterministic `gap_correct`,
  required **1–5-star** `confidence`, and `rt_ms` (exported as `rt_sec`).
- **Quality fields:** comprehension is recorded but its correct option is pre-selected and it is not
  an exclusion. Attention appears after round 8. Analysis excludes failed attention, task time
  below 120 seconds, and duplicate IDs; confidence straightlining is a robustness split.
- **Demographics:** age bracket including “Under 18” and AI-use frequency.

## Export

`custom_export` emits:

```text
participant_id,label,item_id,condition,complete,accept,confidence,gap_correct,rt_sec,
order_index,group_g,lang,passed_comprehension,passed_attention,total_time_sec,
straightline_confidence,duplicate_id,age_group,ai_use
```

Run the frozen analysis against an export:

```bash
python ../analysis/preregistered_analysis.py --data _botdata/reliance_custom.csv
```
