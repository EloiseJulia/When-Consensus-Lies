# FIGURE 1 — DESIGN BRIEF (for the SVG author)
### "When Consensus Lies" overview/teaser. Author: claude-opus-4.8 (design). Render at viewBox 0 0 1200 560.

## 1. Concept & metaphor
Single left-to-right pipeline with ONE fork into two stacked regime lanes.
`[Underspecified prompt]` → `[k independent agents, 3 families × tiers]` → FORK → two lanes sharing the
same agent column, differing only by WHERE the missing clause lives:
- TOP lane = H1_external (disambiguator deleted & unrecoverable) → silent convergence on the WRONG foil → red ✗.
- BOTTOM lane = H2_derivable (disambiguator retained) → correct resolution → green/teal ✓.
The fork IS the independent variable (clause LOCATION, not model capability). Keep ONE shared agent column.
The "aha": in H1 the five outputs collapse into ONE fat arrow "n_eff = 1 of 5" (fake redundancy); in H2 the
five stay as five parallel arrows.

## 2. Layout (viewBox 0 0 1200 560, wide 2-column `figure*`)
- INPUT column x[40,300], y≈210–350 (prompt box) + location knob below.
- AGENTS column x[320,540], y≈120–440 (5 tiles, 3 family bands), shared by both lanes.
- FORK node diamond at (560,280) "Same prompt · same agents".
- TOP LANE (H1) band y[40,270], x[580,1160], warm/red tint.
- BOTTOM LANE (H2) band y[290,520], x[580,1160], cool/teal tint.
- Title strip y[0,36]; bottom caption strip y[524,556].
- Each lane = 4 stations at IDENTICAL x-centers in both lanes: S1 aggregation ~660, S2 consensus badge ~800,
  S3 executable-gold check ~950, S4 outcome ~1090. Only the vertical (color+verdict) differs.

## 4. Palette (Okabe-Ito, colorblind-safe; exact hex)
- Wrong/H1: `#D55E00`; soft fill `#FBEAE1`. Correct/H2: `#0072B2`; soft fill `#E2EEF6`; secondary teal `#009E9E`.
- Executable-gold glyph only: gold `#E6A700`. Text `#1A1A1A`/`#555555`; borders `#C9CCD1`; white panels.
- Verdict must survive grayscale: pair color with ✗/✓ shape AND the words WRONG/CORRECT.
Typography: humanist sans (Inter/Helvetica/Source Sans). Title 20px semibold; lane titles 17px bold in accent;
labels/badges 13px; body/prompt 11px; stat chips 12px semibold pills. Connectors 2px; H1 fat collapse arrow
10–14px; H2 arrows 2px each; boxes 1.5px r8; chips r4. Flat, no gradients/shadows (≤4% panel elevation).

## 5. Labels (verbatim, short)
- Title: "Consensus ≠ correctness: the same agents, one deleted clause, two fates."
- Input header "Underspecified prompt"; struck clause "~~use the FISCAL calendar~~" + tag "✂ disambiguator deleted".
- Location knob "Where does the missing clause live?" dots "outside → H1" / "inside → H2".
- Agents bracket "k independent agents · 3 model families × capability tiers".
- Silence cue (greyed crossed-out "?"): "No clarification requested (abstention ≈ 0.03%)".
- Fork "Same prompt · same agents".
- H1 lane title "H1_external — disambiguator OUTSIDE the retained prompt".
- H2 lane title "H2_derivable — disambiguator INSIDE the retained prompt".
- Consensus badges "5 / 5 agree" (H1 sub "looks like strong consensus"; H2 sub "genuine agreement").
- Gold check "Executable-gold check (no LLM judge)"; H1 result "chose I₁ (foil) ≠ target I₀"; H2 "chose I₀ = target I₀".
- H1 outcome "✗ WRONG — silent convergent delusion"; chips "CD ≈ 0.53", "n_eff = 1 of 5", "ρ → 1 · fake redundancy".
- H2 outcome "✓ CORRECT"; chip "CD = 0 (every tier, incl. weak)".
- Right-edge callout "Failure axis = clause LOCATION, not model capability."
- Bottom caption "Under a shared information boundary, consensus is not evidence of correctness. Measure independence, not agreement."
Numbers are FIXED (confirmatory run): CD_H1≈0.53, CD_H2=0, n_eff=1.10→"1 of 5", ICC=0.89, pairwise=0.98, abstention_H1≈0.03%.

## 6. Annotated element list (id → box/pos → style → label). Group each as `<g id="...">`.
1 title: full width y6–30; 20px semibold #1A1A1A centered.
2 prompt-box: [40,210]-[300,350]; white, 1.5px #C9CCD1, r8; header chip "Underspecified prompt".
3 deleted-clause: inside prompt y≈300; 11px #555 with #D55E00 strikethrough + ✂ tag.
4 location-knob: [60,360]-[290,400]; dashed #C9CCD1 boundary; red dot outside, teal dot inside.
5 agents-stack: [330,130]-[530,430], 5 rounded-square tiles, 3 family stripes, robot glyph; left bracket label.
6 silence-cue: ~[340,90]-[520,120]; greyed crossed-out "?" bubble.
7 fork-node: diamond @ (560,280); white, 1.5px gray.
8 lane-H1-bg: [580,40]-[1160,270]; fill #FBEAE1 r10, 1px #D55E00@40%; lane title 17px bold #D55E00.
9 lane-H2-bg: [580,290]-[1160,520]; fill #E2EEF6 r10, 1px #0072B2@40%; lane title 17px bold #0072B2.
10 H1-collapse-arrow: 5 inputs @x580 taper→ fat shaft to (660,155); 12px #D55E00; tag "ρ→1".
11 H2-parallel-arrows: 5 separate 2px #0072B2 arrows @x580→660, kept distinct.
12 H1-consensus-badge: rosette @ (800,155); amber #D55E00, white ★; "5/5 agree — looks like strong consensus".
13 H2-consensus-badge: rosette @ (800,405); teal #0072B2, white ★; "5/5 agree — genuine agreement".
14 H1-gold-check: gear/beaker @ (950,155); gold #E6A700; "…→ chose I₁(foil) ≠ I₀".
15 H2-gold-check: gear/beaker @ (950,405); gold #E6A700; "…→ chose I₀ = I₀".
16 H1-outcome: circle @ (1090,140); red #D55E00 ✗ 40px; "✗ WRONG — silent convergent delusion".
17 n_eff-motif: @ (1060,205)-(1140,240); 5 dots, 4 faded 15% alpha, 1 solid #D55E00; "n_eff = 1 of 5 · fake redundancy".
18 H1-stat-chips: @ (1030,250) pills 12px; "CD ≈ 0.53" · "ρ→1".
19 H2-outcome: circle @ (1090,405); teal #0072B2 ✓ 40px; "✓ CORRECT".
20 H2-stat-chip: @ (1030,470) pill; "CD = 0 (every tier, incl. weak)".
21 right-callout: vertical brace @ x1170 y90–470; 1.5px #1A1A1A 13px; "Failure axis = clause LOCATION, not model capability."
22 bottom-caption: full width y528–552; 12px #333 centered.

## Implementation notes
Group each numbered item in its own `<g id>`; nest lane contents under g#lane-H1 / g#lane-H2. Keep S1–S4
x-centers identical across lanes. NO real company logos (abstract family glyphs). Verdict survives grayscale.
Fonts as `<text>` (not paths), system-safe sans stack. Flat, print-clean at 300 dpi.
