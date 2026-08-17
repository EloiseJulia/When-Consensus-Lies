# Narrative reframe proposal (framing-only) — 2026-08-17

Owner-approved (2026-08-17). Writing-partner scope: language / framing / presentation only.
No scientific claim, number, hypothesis, metric definition, or provenance is changed.
§4 operational definitions stay verbatim precise. Frozen hypothesis names
(`H1_external`, `H2_derivable`, `H1a`, `H1b`, `R1a`, `R1b`, `R2`) are NOT renamed or redefined;
only surrounding motivational prose changes, plus plain-language glosses.

## Motivating concerns (owner)
1. **"4/4 models agree" attribution.** Most same-prompt UIs (ChatHub, Poe, Google AI Studio) show
   answers side-by-side; they do NOT emit an explicit "4/4 agree" verdict. Only a subset
   (PromptQuorum, MultipleChat) compute a vote/consensus. Attributing the agreement claim to every
   platform over-claims, and invites the "how can you tell the answers are identical?" question
   (model text always differs). Fix: attribute the reassurance to the *user's inference*, keep the
   quoted hook.
2. **inside/outside reads as tautological.** "We moved the disambiguating clause outside the prompt"
   sounds like "we injected ambiguity → of course it's ambiguous." The real finding is *silent
   convergence on the SAME WRONG reading*, not the existence of ambiguity. Reframe:
   - silently absent  ≈ the everyday case where a non-expert user under-specifies a boundary
     condition WITHOUT realizing a decision hinges on it (vibe-coding / prompting-by-intent).
   - present         ≈ the prompt a task-aware user would write (maps cleanly to the k=0 within-item
     control, R1a — the cleanest evidence).

## Guardrails (red lines)
- Motivational only: constructed + default-checked items *instantiate* the unaware-underspecification
  condition; NOT a sample of real user prompts, NOT a prevalence claim.
- Keep `H2_derivable` (info in-prompt but must be derived) distinct from k=0 (same task, properly
  specified). Do not collapse.
- §4 construct/estimand text unchanged.

## Landing points
- **L1 Abstract opening** — fix attribution verb (hook 1A retained).
- **L2 Abstract "single factor" sentence** — pivot from "ambiguity" to "same wrong convergence";
  "present … or silently absent".
- **L3 Intro opening** — "Nothing on the screen says so outright, but …" (user's inference).
- **L4 Intro new scenario** — unaware under-specification; foreground R1a (well-specified control).
- **L5 §3 RQ1 lead-in** — replace "location of the disambiguator" with "present … or silently absent"
  (hypothesis names preserved).

## Ripple checks
- Reconcile any remaining "outside/inside the retained prompt" / "location of the disambiguator" in
  §4, figures, discussion so the two vocabularies do not clash; §4 defs stay precise.
- No sentence rewritten into a real-user / prevalence register.
- Compile: 29 pages, 0 undefined.
