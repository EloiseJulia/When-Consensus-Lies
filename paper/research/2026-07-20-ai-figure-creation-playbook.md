# Playbook: Producing a Publication-Quality, PPT-Editable Overview/Teaser Figure (SVG) with AI

> A reusable methodology (for AI agents or humans) to generate a beautiful, self-explanatory **Figure 1
> "overview/teaser"** for an academic paper as a **fully PowerPoint-editable SVG**, plus a PDF for LaTeX.
> Distilled from producing the "When Consensus Lies" overview figure. Model-agnostic; the model names below
> are examples of the *roles*, not requirements.

---

## 0. TL;DR (the pipeline)
1. **Separate design from rendering, across model families.** One strong *reasoning* model writes a precise
   **design brief** (what/where/why); a different high-tier model **renders SVG** from that brief. Diversity
   of strengths + a written spec = better, more controllable output than one-shot "draw me a figure."
2. **Design brief first** — a prescriptive, coordinate-level spec (concept, layout, elements, palette,
   typography, verbatim labels, an annotated element list). No SVG in this step.
3. **Render SVG** to the brief with hard constraints (viewBox, real `<text>`, exact hex palette,
   colorblind-safe, abstract glyphs, flat style).
4. **Make it PPT-editable** — this is the step most people miss: **flatten** the SVG (no groups, no
   transforms, absolute coords, every shape/text a top-level element).
5. **Convert + embed + validate** — SVG→PDF (svglib), embed as `figure*`, compile, and gate on
   well-formedness / zero-transforms / renders-to-PDF / no missing-figure errors.
6. **Iterate on real feedback** — diagnose with `grep`/counts, send a targeted refactor, re-validate.

---

## 1. Why two models, two steps
- **Design ≠ execution.** A one-shot "make an SVG" conflates *deciding what to draw* with *writing 200 XML
  elements*. Splitting them gives a reviewable artifact (the brief) and a controllable render.
- **Cross-family.** Use a strong reasoning/design model (e.g. Claude-opus) for the brief and a strong
  precise-output model (e.g. GPT-5.6, high reasoning effort) for the SVG. Different families have different
  strengths; the brief is the contract between them.
- **The brief is the reusable asset.** Save it (`fig_*_design_brief.md`). It documents intent, survives
  re-renders, and lets a human or another model redo the figure.

---

## 2. The design-brief template (step 2 output)
Ask the design model for a **text-only** brief with these sections (be prescriptive, coordinate-level):
1. **Concept & visual metaphor** — pick ONE clearest composition and *justify vs alternatives*. Tie the
   composition to the paper's single causal claim (e.g. a fork = the independent variable).
2. **Layout & canvas** — aspect ratio + exact `viewBox` (e.g. `0 0 1200 560` for a 2-column `figure*`);
   partition the canvas into named coordinate zones (x/y ranges) and a station grid shared across panels so
   the reader compares like-for-like.
3. **Concrete elements** — every box, arrow, icon, badge, motif, with what it depicts.
4. **Visual language** — a **colorblind-safe palette with exact hex codes** (Okabe–Ito is a good base);
   typography (one humanist sans, explicit sizes); line weights; flat iconography; and *how to encode the
   abstract ideas* (e.g. "silent" = greyed crossed-out "?"; "fake redundancy" = 5→1 arrow collapse).
5. **Verbatim labels** — the exact short strings for every element (so numbers/wording are fixed and
   consistent with the results). Freeze data values here.
6. **Annotated element list** — a table: `id → position(box/point) → style → label`, one row per element,
   each to become a labeled layer. This is what the SVG author implements directly.

**Design principles worth enforcing in the brief:**
- Readable in ~10 seconds; one "aha" visual that carries the thesis.
- Redundancy of encoding: never rely on color alone — pair color with **shape** and a **word** (e.g. ✗/✓ +
  "WRONG"/"CORRECT") so it survives grayscale and color-vision deficiency.
- Never use real company/brand logos — use neutral abstract glyphs.
- Align shared sub-stations on identical x-centers across panels so only the intended variable differs.

---

## 3. SVG rendering constraints (step 3)
Give the render model hard requirements:
- `viewBox` set; `xmlns` present; `<title>`/`<desc>` for accessibility.
- Implement **every** brief element at the given coordinates.
- **All labels as real `<text>`** (not outlined paths) with a system-safe sans stack
  (`font-family="Inter, 'Helvetica Neue', Arial, sans-serif"`), using the verbatim strings/sizes.
- **Exact hex palette**; flat — **no gradients, no filters, no drop-shadows** (these also break converters).
- Colorblind-safe (color + shape + word); abstract glyphs only.
- Unicode symbols directly (✗ ✓ ★ ✂ ρ → ≠ ≈ ₀ ₁).

---

## 4. ⭐ The PPT-editability step (the key lesson)
**Goal:** in PowerPoint, *Insert SVG → right-click → "Convert to Shape" → Ungroup (once)* yields **every
shape and text label as an independent, hand-editable object**.

PowerPoint cannot reliably ungroup SVGs that use nested groups or transforms — it collapses them into one
un-splittable blob. So **flatten** the SVG:
- **No `<g>` groups** (or at most one outer `<g>` with no transform). Every element is a **top-level** child
  of `<svg>`.
- **No `transform=` anywhere.** Bake all positions into **absolute coordinates** (fold any group offset into
  each element's own x/y/points).
- **Every text label = its own `<text>`** with absolute x/y; prefer one `<text>` per line (each line moves
  independently) over stacked `<tspan>`.
- **Inline presentation attributes only** — no `<style>`/CSS/`class`, no `<defs>`/`<use>`/`<symbol>`/
  `<marker>`/`clip-path`.
- **Decompose compound paths** that draw multiple visual parts into separate primitives (`rect`/`line`/
  `circle`/`ellipse`/`polygon`/`polyline`). Arrowheads = separate `<polygon>`. Icons = separate shapes, not
  one merged path. Simple single shapes may stay one element.
- Add an **XML comment before each logical element** (`<!-- [8] lane-H1 background -->`) for navigation;
  comments do not affect ungrouping.

Result: a flat SVG of ~100–250 independent objects that PowerPoint fully decomposes.

**Note on the design↔flatten tension:** grouped/nested SVG is nicer for *code* readability; flat SVG is
required for *PPT* editability. If you also want a print-only grouped version, keep both, but ship the flat
one for editing.

---

## 5. Toolchain: convert, embed, validate
- **SVG → PDF for LaTeX** (Windows-friendly, no native cairo needed):
  `pip install svglib reportlab`, then
  `python -c "from svglib.svglib import svg2rlg; from reportlab.graphics import renderPDF; renderPDF.drawToFile(svg2rlg('fig.svg'),'fig.pdf')"`.
  svglib is picky about exotic constructs — the flat/no-filter rules above also make it convert cleanly.
  (Alternatives: Inkscape `--export-type=pdf`, `rsvg-convert`, `cairosvg` if native libs are available.)
- **Embed** as a spanning teaser in ACM `acmart`:
  `\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{fig_overview.pdf}\caption{...}\label{fig:overview}\end{figure*}`,
  placed right after `\maketitle`; reference it early in the Introduction.
- **Validation gates (run every time):**
  1. Well-formed XML: `python -c "import xml.dom.minidom as m; m.parse('fig.svg')"`.
  2. PPT-flat: `grep -c 'transform=' fig.svg` → **0**; `grep -c '<g' fig.svg` → 0 (or 1 outer, no transform).
  3. Converts to PDF (svglib, above).
  4. LaTeX build: 0 errors, 0 "undefined reference/citation", 0 "file not found" for the figure.

---

## 6. Iteration loop (how to fix "it's wrong / can't edit it")
1. **Get concrete feedback** ("PPT can't split it"; "colors too loud"; "label overflows").
2. **Diagnose with counts/grep**, e.g. `count(<g>), count(transform=), count(<defs>), count(<text>)` — this
   pinpoints *why* (nested groups + transforms → PPT blob).
3. **Send a targeted refactor** to the same render model (it retains context): state the exact constraint
   changed, keep design/coords/palette/labels fixed.
4. **Re-validate** with the gates. Keep the design brief as the invariant contract.

---

## 7. Optimizations / refinements (beyond the first pass)
- **Freeze data in the brief.** Put every numeric label (rates, CIs) in the brief and forbid the renderer
  from altering them; ideally source them from a results JSON (`figures_data.json`) so figure ↔ paper stay
  consistent.
- **Add a raster preview for visual QA.** Also export a PNG (e.g. via the PDF) so a human/model can eyeball
  overlap/overflow that XML checks miss; feed it back as "fix overlapping labels at (x,y)."
- **Self-critique pass.** Ask the design model to critique the rendered SVG against the brief (missing
  elements, misalignment, contrast) before the human sees it.
- **Grayscale check.** Render a desaturated copy to confirm the figure still parses without color.
- **Two artifacts by purpose:** a grouped/layered SVG for archival + the flat SVG for PPT editing; generate
  the flat one by a deterministic "flatten" transform if you want to avoid a second model call.
- **Accessibility:** keep `<title>`/`<desc>`, ensure ≥4.5:1 text contrast, and don't encode meaning by color
  alone.
- **Reuse:** this brief template + PPT-flatten rules generalize to system diagrams, pipeline figures, and
  study-design figures, not just teasers.

---

## 8. Checklist (copy/paste)
- [ ] Design brief written (concept+justification, viewBox, zones, elements, hex palette, typography,
      verbatim labels, annotated element table) and saved.
- [ ] SVG rendered to the brief: real `<text>`, exact palette, colorblind-safe (color+shape+word), abstract
      glyphs, flat (no gradient/filter/shadow).
- [ ] **PPT-flat:** 0 `<g>`, 0 `transform=`, absolute coords, inline styles, no defs/use/marker/clip,
      compound paths decomposed, per-element XML comments.
- [ ] Validated: well-formed XML; transforms=0; converts to PDF; LaTeX builds clean; grayscale legible.
- [ ] Delivered: editable `.svg` + embedded `.pdf`; design brief archived.
