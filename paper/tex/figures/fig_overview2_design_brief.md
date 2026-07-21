# FIGURE 1 v2 — SCIENTIFIC CONTRACT + RENDER SPEC ("When Consensus Lies" teaser)

> Produced with the upgraded playbook (paper/research/2026-07-20-ai-figure-creation-playbook.md).
> Design/contract author: Manager (Claude family). SVG render author: GPT family (different family →
> provenance separation on the artifact). Independent reviewer-simulation: Gemini family (raster only).
> **Render target `viewBox="0 0 1000 640"`.** This is the frozen Pass-C render specification.

---

## 1. SCIENTIFIC FIGURE CONTRACT (frozen before any drawing)

**Figure type.** PRIMARY = *teaser* (the single counter-intuitive finding). SECONDARY = *method overview*
(one glance at the pipeline). Do not let the method detail crowd out the teaser.

**One-sentence 10-second claim.** *After 10 seconds, the reader understands: the SAME agents on the SAME
prompt reach confident 5/5 consensus that is WRONG when the disambiguating clause lives OUTSIDE the prompt
(H1), yet CORRECT when it lives INSIDE (H2) — so the failure axis is the clause's LOCATION, not model
capability, and the consensus is fake redundancy (n_eff≈1).*

**Claim → evidence map (ONLY `verified` claims may appear; no others).**

| ID | Visual claim in the figure | Evidence source (confirmatory run) | Figure element | Status |
|----|----------------------------|------------------------------------|----------------|--------|
| C1 | H1 (external): agents converge on the WRONG foil | cd_primary=0.53 (H1) | `h1_outcome`, `h1_cd_chip` | verified |
| C2 | H2 (derivable): agents resolve CORRECTLY, every tier incl. weak | cd_primary=0.00 (H2, all classes) | `h2_outcome`, `h2_cd_chip` | verified |
| C3 | The k-agent ensemble collapses to ONE effective voice | n_eff=1.10, ICC=0.89 (H1) | `h1_collapse_arrow`, `h1_neff_chip` | verified |
| C4 | H2 stays genuinely independent/parallel | H2 CD=0 across classes | `h2_parallel_arrows` | verified |
| C5 | Failure is silent — agents are confidently wrong, not uncertain | abstention_H1≈0.03% | `silence_cue` | verified |
| C6 | Verdict is by executable gold, not an LLM judge | executable-gold harness | `h1_gold_check`, `h2_gold_check` | verified |
| — | (EXCLUDED) capability/reasoning-tier ordering; SC amplification | H1a inconclusive, row-35 not confirmed | — | excluded (not drawn) |

**No-overclaim rules (hard).** Arrows show only real pipeline flow. The 5→1 collapse depicts n_eff≈1 (a
measured dependence), not a literal routing. No area/length encodes an unverified magnitude. Every number is
verbatim from `figures_data.json`; the renderer invents NO numbers. Mark nothing as a statistic that is only
illustrative. The agent tiles are a schematic of the roster, not per-run identities.

**Frozen numbers (verbatim; source `figures_data.json`).** CD_H1 = **0.53**; CD_H2 = **0**; n_eff =
**1.10** → shown as "**1 of 5**"; ICC = 0.89; pairwise wrong-agreement = 0.98; abstention_H1 ≈ **0.03%**.
Only the **bold** ones appear IN the figure; ICC/pairwise go in the LaTeX caption (keeps the teaser legible).

---

## 2. STORYBOARD (Pass A) & WIREFRAME (Pass B)

**Storyboard (reading order).** (1) One underspecified prompt with a clause struck out. (2) One shared column
of k independent agents. (3) A FORK asking *where does the missing clause live?* (4) TOP path H1 → agents
collapse into one fat arrow → 5/5 badge → gold-check says "chose foil" → ✗ WRONG. (5) BOTTOM path H2 → agents
stay 5 parallel arrows → 5/5 badge → gold-check says "chose target" → ✓ CORRECT. (6) Right-edge takeaway:
LOCATION, not capability.

**Wireframe (zones, `viewBox 1000×640`).**
```
 y0   ┌───────────────────────── TITLE strip (y 0–52) ─────────────────────────┐
      │ INPUT (x30–255)   AGENTS (x275–440)   FORK   ── TOP LANE H1 (x505–905) ─┤ callout
      │ prompt+knob        shared 5-tile stack  ◇     collapse→badge→gold→✗     │ (x915
      │ y110–330                                      band y66–336              │  –985)
      │                                        ── BOTTOM LANE H2 (x505–905) ────┤
      │                                               parallel→badge→gold→✓     │
      │                                               band y360–620             │
 y640 └────────────────────────── CAPTION strip (y 618–638) ────────────────────┘
```
Both lanes share IDENTICAL station x-centers so only the vertical (color + verdict) differs:
`S1 collapse/parallel ≈ x545`, `S2 consensus badge ≈ x650`, `S3 gold-check ≈ x760`, `S4 outcome ≈ x865`.

---

## 3. TYPOGRAPHY — sized for the FINAL PRINTED WIDTH (the key v1→v2 fix)

Target printed width **T = 5.478 in** (ACM `acmsmall` `\textwidth`). Scale factor = T·72/W =
5.478·72/1000 = **0.3944 pt per user-unit**. `effective_pt = font_px × 0.3944`. **Minimum body text = 20px
(→ 7.9 pt ≥ 7.5 pt floor).** v1 used 11–13px (→ 4.3–5.1 pt) — illegible at column width; that is why v2
cuts text and enlarges it.

| Role | font-size (px) | effective pt | Use |
|------|----------------|--------------|-----|
| Title | 34 | 13.4 | one line |
| Lane title | 27 | 10.6 | H1/H2 headers |
| Outcome word | 26 | 10.3 | WRONG / CORRECT |
| Key label / chip | 22 | 8.7 | badges, CD/n_eff chips, callout |
| Body label | 20 | 7.9 | everything else (floor) |

Use `font-weight` (600/700) and color for hierarchy, NOT smaller sizes. If a label would need < 20px, cut
or shorten it instead. Font stack: `font-family="Inter, 'Helvetica Neue', Arial, sans-serif"`. Mathematical
subscripts (I₀, I₁, ρ, n_eff) are acceptable as plain text here (short, in the safe stack); do NOT introduce
decorative Unicode beyond what is listed in §5.

---

## 4. PALETTE (Okabe–Ito, colorblind-safe; exact hex)
- Wrong / H1 accent `#D55E00`; soft lane fill `#FBEAE1`; lane border `#D55E00` @ 40%.
- Correct / H2 accent `#0072B2`; soft lane fill `#E2EEF6`; lane border `#0072B2` @ 40%.
- Executable-gold glyph only `#E6A700`. Text `#1A1A1A` (primary) / `#555555` (secondary). Neutral border
  `#C9CCD1`. Panels white `#FFFFFF`. Family stripes (agent tiles) neutral greys `#8A8F98`/`#B4B9C1`
  (NO brand colors/logos).
- **Redundant encoding (survives grayscale):** every verdict pairs COLOR + SHAPE + WORD — H1 = red + ✗ +
  "WRONG"; H2 = blue + ✓ + "CORRECT".

---

## 5. VERBATIM LABELS (use EXACTLY; terse for legibility)
- `title`: **Consensus ≠ correctness: same agents, one deleted clause, two fates**
- `prompt_header`: **Underspecified prompt**
- `prompt_deleted`: **use the fiscal calendar** (rendered struck-through) + tag **✂ clause deleted**
- `knob_label`: **Where is the missing clause?**  ·  `knob_out`: **outside → H1**  ·  `knob_in`: **inside → H2**
- `agents_bracket`: **k independent agents · 3 families × tiers**
- `silence_cue`: **No one asks (abstention ≈ 0.03%)**
- `fork_label`: **Same prompt · same agents**
- `h1_lane_title`: **H1 — clause OUTSIDE the prompt**
- `h2_lane_title`: **H2 — clause INSIDE the prompt**
- `h1_badge`: **5 / 5 agree**  ·  `h1_badge_sub`: **looks like consensus**
- `h2_badge`: **5 / 5 agree**  ·  `h2_badge_sub`: **genuine agreement**
- `h1_gold`: **Executable gold: chose I₁ (foil) ≠ I₀**
- `h2_gold`: **Executable gold: chose I₀ = target**
- `gold_note`: **(no LLM judge)**
- `h1_outcome`: **✗ WRONG** · `h1_outcome_sub`: **silent convergent delusion**
- `h2_outcome`: **✓ CORRECT** · `h2_outcome_sub`: **every tier, incl. weak**
- `h1_cd_chip`: **CD ≈ 0.53** · `h1_neff_chip`: **n_eff = 1 of 5 (ρ→1)**
- `h2_cd_chip`: **CD = 0**
- `callout`: **Failure axis = clause LOCATION, not model capability**
- `caption_strip`: **A shared information boundary makes consensus fake: measure independence, not agreement**

---

## 6. ELEMENT LIST — id → zone → style → label (each a stable-id element)
Every drawn element gets a STABLE SEMANTIC `id` (used for the semantic gate & PPT Selection Pane). Decompose
to edit-granularity: a box = 1 rect; an arrow = shaft + head (2 shapes); an icon = a few primitives (do NOT
over-fragment). Order the elements top-to-bottom by zone.

1. `title` — title strip y8–44, centered, 34px 700 `#1A1A1A`.
2. `prompt_box` — [30,110]–[255,250], white rect r10, 1.5px `#C9CCD1`; `prompt_header` chip top-left.
3. `prompt_deleted` — inside prompt ~y200, 20px `#555555` with `#D55E00` strikethrough line + `✂` tag.
4. `knob` — [30,268]–[255,330] dashed `#C9CCD1` r8; `knob_label` 20px; red dot + `knob_out`, teal dot + `knob_in`.
5. `agents_stack` — [275,150]–[440,450]: 5 rounded-square tiles (r8) in a column, each with 3 thin family
   stripes + a neutral agent glyph; `agents_bracket` as a left vertical bracket label (rotate allowed ONLY
   in source; in the flat deliverable place it as horizontal text above/below if rotation is dropped).
6. `silence_cue` — ~[275,110]–[440,145]: greyed crossed-out "?" bubble + `silence_cue` text 20px `#555555`.
7. `fork_node` — diamond centered (470,300), white, 1.5px `#8A8F98`; `fork_label` 20px below.
8. `h1_lane_bg` — [505,66]–[905,336] fill `#FBEAE1` r12, 1px `#D55E00`@40%; `h1_lane_title` 27px 700 `#D55E00`.
9. `h2_lane_bg` — [505,360]–[905,620] fill `#E2EEF6` r12, 1px `#0072B2`@40%; `h2_lane_title` 27px 700 `#0072B2`.
10. `h1_collapse_arrow` — 5 tapering inputs from x505 merge into ONE fat shaft → S1 (x545,y150); shaft 12px
    `#D55E00`, arrowhead separate polygon; small `ρ→1` tag 20px.
11. `h2_parallel_arrows` — 5 DISTINCT 3px `#0072B2` arrows x505→x585 at y≈430, kept clearly separate.
12. `h1_badge` — rosette/star @ (650,150) `#D55E00` w/ white ✗-free star; `h1_badge`+`h1_badge_sub` 22/20px.
13. `h2_badge` — rosette/star @ (650,430) `#0072B2` white star; `h2_badge`+`h2_badge_sub` 22/20px.
14. `h1_gold_check` — beaker/gear @ (760,150) `#E6A700`; `h1_gold` 20px + `gold_note`.
15. `h2_gold_check` — beaker/gear @ (760,430) `#E6A700`; `h2_gold` 20px + `gold_note`.
16. `h1_outcome` — circle @ (865,150) `#D55E00`, white `✗` 34px; `h1_outcome`(26px 700)+`h1_outcome_sub`(20px).
17. `h1_neff_motif` — @ ~(820,250)–(900,285): 5 dots, 4 faded (15% alpha) + 1 solid `#D55E00`; adjacent `h1_neff_chip` 22px pill.
18. `h1_cd_chip` — pill @ ~(520,300) `#FBEAE1`/`#D55E00` text 22px.
19. `h2_outcome` — circle @ (865,430) `#0072B2`, white `✓` 34px; `h2_outcome`(26px 700)+`h2_outcome_sub`(20px).
20. `h2_cd_chip` — pill @ ~(520,585) `#E2EEF6`/`#0072B2` text 22px.
21. `callout` — right edge x915–985: a `[` brace + `callout` text 22px 700 `#1A1A1A` (wrap to 3 lines).
22. `caption_strip` — full width y620–636, 20px `#333333` centered.

---

## 7. HARD RENDER CONSTRAINTS (flat, PPT-decomposable, stable-id)
- `viewBox="0 0 1000 640"`, `xmlns` set. Add ONE `<desc id="figdesc">` with a 1–2 sentence alt-text
  (see §8) — source-level metadata only.
- **Every label is real `<text>`** with absolute x/y and a stable `id`; verbatim §5 strings; sizes per §3
  (nothing below 20px). One `<text>` per line.
- **Flat / PPT-decomposable:** NO `<g>` (or a single outer `<g>` w/ no transform), **NO `transform=`**
  anywhere (bake absolute coords), inline presentation attributes only — no `<style>`/CSS/class, no
  `<defs>/<use>/<symbol>/<marker>/clip-path`, no gradients/filters/shadows. Arrowheads = separate
  `<polygon>`. Decompose compound icons into a few primitives (edit-granularity, not micro-fragments).
- **Stable semantic `id` on every element** (`id="h1_outcome_circle"`, `id="h1_outcome_label"`, …).
- Colorblind-safe: color + shape + word on every verdict. No brand logos.
- Only these non-ASCII glyphs allowed (verify in the font): `≠ ✂ ✗ ✓ ★ ρ → I₀ I₁`. Nothing else decorative.

## 8. DELIVERABLES the render agent must output
1. `fig_overview2.svg` — the flat, stable-id SVG above (this is BOTH the maintained source and the
   PPT-decomposable artifact for this deliverable).
2. `fig_overview2_alt.txt` — a 2–4 sentence manuscript-level alt-text (distinct from the caption; describes
   the pipeline, the H1-wrong/H2-correct fork, and the takeaway).
3. `fig_overview2_manifest.json` — `{figure_id, viewBox, intended_width_in:5.478,
   minimum_effective_font_pt:7.5, palette{}, frozen_numbers{}, claims[C1..C6], alt_text, source_data:
   "figures_data.json"}`.
Report the element count and confirm 0 `<g>`/0 `transform=`/all-text≥20px.
