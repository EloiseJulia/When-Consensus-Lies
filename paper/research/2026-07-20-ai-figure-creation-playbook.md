# Playbook: AI-Assisted Production of a Top-Venue Figure 1 (Scientifically Faithful, Reviewer-Effective, Reproducible, Editable)

> A reusable methodology (for AI agents or humans) to produce a **Figure 1 "overview / teaser"** for an
> academic paper that is (a) **scientifically accurate and non-overclaiming**, (b) **readable in ten seconds
> at the real paper size**, (c) **reproducible** from a frozen source, and (d) **editable** — decomposable in
> PowerPoint, with a native-PPTX fallback when true editable text is required, plus a publication PDF for
> LaTeX. Distilled from producing the "When Consensus Lies" overview figure and hardened against a detailed
> peer critique. **Model-agnostic:** model names are examples of *roles*, not requirements.
>
> **Framing:** the highest-level goal is *scientific communication and claim fidelity*. Editability and PPT
> compatibility are important engineering constraints, **not** the top of the hierarchy.

---

## 0. TL;DR (the pipeline)

1. **Define the scientific contract first.** Freeze the figure *type*, a one-sentence takeaway, a
   claim→evidence mapping, the source data, and what a reader should understand within ten seconds. If you
   cannot fill the one-sentence takeaway, it is too early to draw.
2. **Separate semantic design from mechanical rendering.** First a **storyboard**, then a **low-fidelity
   wireframe**; only after the composition is approved do you freeze coordinates, labels, palette, and
   typography. The two roles may be handled by the **same model in separate passes** or by **different
   models** — cross-model is optional and is mainly useful for *independent critique*, not a prerequisite.
3. **Render a semantic source SVG.** Stable element IDs, real `<text>`, explicit `viewBox`, restricted
   palette, redundant encoding (color + shape + word), and **only** the claims/values in the approved brief.
4. **Generate purpose-specific artifacts.** Keep a maintainable *semantic* SVG as the single source of truth.
   Deterministically derive a *PowerPoint-compatibility* SVG and a *publication* PDF (or PDF+LaTeX). Provide a
   native PPTX when editable text boxes are a hard requirement.
5. **Validate structure, rendering, semantics, and final-size readability.** XML validity, forbidden
   constructs, IDs, frozen labels/values, PDF rendering, font embedding, clipping, grayscale, contrast, and
   legibility at the *actual* printed size.
6. **Review the figure as a reviewer would.** Test whether an independent reader can identify the problem,
   contribution, comparison variable, method flow, and central conclusion **without reading the paper**.
7. **Iterate by diagnosis, not by redrawing.** Link every requested change to specific element IDs, preserve
   the scientific contract, run visual regression, and re-run all gates.

---

## 1. Scientific figure contract (freeze BEFORE any visual design)

This is the part most "AI draws a pretty figure" workflows skip, and it matters more for a top venue than
whether the SVG has any `<g>` elements.

### 1.1 Figure type
Name the primary function; do not blend types without deciding a **primary**:
- **Teaser** — the core phenomenon, counter-intuitive result, or single strongest takeaway.
- **Method overview** — inputs, modules, outputs, train/inference relations.
- **Problem setup** — task definition, notation, the compared variable.
- **System architecture** — components and data flow.
- **Study design** — conditions, sample flow, measurements.

A figure may serve two functions, but you must designate the primary one.

### 1.2 One-sentence claim
Require the author to complete:
> *After viewing Figure 1 for ten seconds, the reader should understand that ______.*

If this sentence cannot be written, stop — the figure is not ready to draw.

### 1.3 Claim → evidence mapping
Only **verified** claims may enter the final figure. Maintain a table:

| Claim ID | Visual claim | Evidence source | Figure element | Status |
|---|---|---|---|---|
| C1 | Method preserves X | Table 2 / Exp A | right outcome panel | verified |
| C2 | Baseline fails under Y | Fig. 4 / Exp B | red branch | verified |
| C3 | Module Z drives gain | Ablation Table 3 | center badge | pending → excluded |

This prevents the AI from drawing a visual narrative *stronger than the actual experiments*.

### 1.4 No visual overclaiming (hard rules)
- Arrows depict only flows/causal relations that truly exist in the paper.
- Area, length, and count must not imply unverified proportions.
- Do not exaggerate performance gaps for aesthetics.
- An illustrative example must not masquerade as an aggregate statistical result; mark schematics as
  *schematic / illustrative* if they could be misread.
- Every number comes from a single named data source; the renderer may **not** invent or complete values.
- Never draw correlation as causation.

---

## 2. Design in three fidelities (semantic first, geometric last)

Do **not** demand exact coordinates before the concept is stable — that traps the model in pixel-nudging
while the narrative is still wrong. Escalate fidelity in three passes:

- **Pass A — Semantic storyboard.** What question does Figure 1 answer? Inputs? Key intermediate mechanism?
  Compared variable? Output / core finding? Reader's intended reading order?
- **Pass B — Low-fidelity wireframe.** Number of columns/panels, each panel's job, the main visual focus,
  the information hierarchy, relative positions and rough proportions. E.g. `Left 24%: setup · Center 48%:
  mechanism · Right 28%: outcome + takeaway`.
- **Pass C — Render specification (freeze here).** `viewBox`, zone coordinates, element positions, exact
  labels, palette hex, font sizes, arrow routes.

> The brief should be **semantically prescriptive first and geometrically prescriptive only after the
> wireframe is approved.**

**Roles vs models.** *Role separation (design vs render) is required; model separation is optional.* Using a
second model family can add independent critique, but it also risks brief-misreading, coordinate/naming
drift, missing shared context, and style drift. Prefer cross-model for **critique**, not necessarily render.

**The brief is the reusable asset.** Save it (`fig_*_design_brief.md`); it documents intent, survives
re-renders, and lets any model/human redo the figure.

### 2.1 Render-spec (Pass C) template
1. **Concept & metaphor** — one composition, justified vs alternatives, tied to the paper's single causal
   claim (e.g. a fork = the independent variable).
2. **Layout & canvas** — aspect ratio + exact `viewBox` (e.g. `0 0 1200 560` for a 2-column `figure*`);
   named coordinate zones and a station grid shared across panels for like-for-like comparison.
3. **Concrete elements** — every box/arrow/icon/badge with what it depicts and a **stable semantic ID**.
4. **Visual language** — colorblind-safe palette with exact hex (Okabe–Ito base); typography with explicit
   sizes; line weights; flat iconography; how abstract ideas are encoded (e.g. "silent" = greyed crossed-out
   "?"; "fake redundancy" = 5→1 collapse).
5. **Verbatim labels & frozen values** — the exact short strings and every numeric label, sourced from a
   results JSON so figure ↔ paper stay consistent.
6. **Annotated element list** — a table `id → position → style → label`, one row per element.

**Design principles to enforce:** readable in ~10 s; one "aha"; redundant encoding (never color alone — pair
with shape + word so it survives grayscale and CVD); no real brand logos; align shared sub-stations on
identical x-centers so only the intended variable differs.

---

## 3. SVG rendering constraints (Pass C output)

- `viewBox` set; `xmlns` present.
- Implement **every** brief element at its coordinates, each with its **stable semantic ID**
  (`<rect id="method_encoder_box" .../>`, `<text id="method_encoder_label" ...>Encoder</text>`).
- **Labels as real `<text>`** (not outlined paths) with a system-safe sans stack; verbatim strings/sizes.
- **Exact hex palette**; flat — no gradients/filters/drop-shadows (they also break converters).
- Colorblind-safe (color + shape + word).
- **Glyphs & math (avoid decorative Unicode).** A symbol available as a simple vector primitive should be
  *drawn*, not typed as a character: state icons (✓, ✗, ★) as small SVG shapes, not font glyphs. Render
  **mathematical notation via LaTeX** (ρ, subscripts, ≈, ≠) rather than raw Unicode. Any glyph you do keep as
  text must be verified in the target font (`pdffonts` after PDF export). Rationale: font fallback,
  baseline jumps, glyph-width shifts, and missing glyphs in PDF/PowerPoint are common and machine-dependent.

---

## 4. PowerPoint compatibility and native-editability strategy

**Goal:** maximize the probability that, in PowerPoint, *Insert SVG → Convert to Shape → Ungroup* yields
individually selectable, editable pieces.

**Compatibility profile (not a guarantee).** Flattening groups, transforms, reusable definitions, CSS,
clipping, markers, and filters *substantially reduces* conversion ambiguity and *improves the probability* of
clean decomposition. It does **not** guarantee identical behavior across all PowerPoint versions/platforms,
and an SVG `<text>` element is **not** guaranteed to become a re-typable PowerPoint text box.

Flatten rules for the *compatibility* SVG:
- **No `<g>` groups** (at most one outer `<g>` with no transform); every element is a top-level child.
- **No `transform=` anywhere** — bake positions into absolute coordinates.
- **Every text label its own `<text>`** with absolute x/y; one `<text>` per line.
- **Inline presentation attributes only** — no `<style>`/CSS/`class`, no `<defs>`/`<use>`/`<symbol>`/
  `<marker>`/`clip-path`/filters.
- **Decompose compound paths** into primitives; arrowheads = separate `<polygon>`; icons = separate shapes.

**Edit-granularity, not object count.** Do **not** target "100–250 objects" — that misleads the model into
thinking more fragments are better and wrecks the PowerPoint Selection Pane. Instead:
> Decompose objects only to the granularity at which a human is likely to edit them. Avoid both monolithic
> paths and unnecessary micro-fragmentation.
A rounded-rect background = 1 object; an arrow = line + head = 2; a 15-segment icon nobody edits piece-wise
need not become 15; decorative dots that always move together need not be atomized.

**Stable IDs over comments.** Give every element a stable semantic `id`; IDs (not XML comments) are the
primary identity mechanism for linting, diffing, locating, data-binding, and screenshot feedback. XML
comments are optional navigation aids.

**Acceptance test (empirical, not XML-inferred).** For the target desktop PowerPoint:
1. Insert the SVG. 2. Run *Convert to Shape*. 3. Check every required component is separately selectable.
4. Verify whether labels stay editable **text** or become vector shapes. 5. Save, close, reopen the PPTX to
confirm persistence.

**Native-PPTX fallback.** If the hard requirement is "double-click any label and retype in PowerPoint," the
most robust delivery is **not** a single SVG but: `figure.source.svg` (structure decomposable) +
`figure_native.pptx` (labels as native PowerPoint text boxes) + `figure.pdf` (submission). Converge the
promise to: *PowerPoint-**decomposable** SVG, with a native-PPTX fallback when editable text is required.*

---

## 5. Toolchain: convert, embed, validate

**Converter hierarchy (publication master ≠ Python fallback):**
1. **Inkscape CLI — publication master.**
   `inkscape fig.svg --export-type=pdf --export-filename=fig.pdf --export-area-page`
   (supports export area, PDF version, text-to-path, and PDF+LaTeX export).
2. **LaTeX `svg` package / PDF+LaTeX — when strict font consistency is required.**
   `\usepackage{svg}` then `\includesvg[width=\textwidth]{fig_overview}` splits graphics from text so LaTeX
   typesets the text (fonts and math match the body). Requires Inkscape on the build host.
3. **CairoSVG / `rsvg-convert` — CI fallback.**
4. **svglib (`pip install svglib reportlab`) — pure-Python fallback** (Windows-friendly, no native cairo):
   `renderPDF.drawToFile(svg2rlg('fig.svg'),'fig.pdf')`. *This is what the "When Consensus Lies" figure
   actually used* because Inkscape was unavailable on the box — acceptable as a fallback, but not the
   recommended master for a submission, since it is weaker on Unicode, text baselines, and font fallback.

**Embed** as a spanning teaser in ACM `acmart`:
`\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{fig_overview.pdf}\caption{...}\label{fig:overview}\end{figure*}`,
placed right after `\maketitle`; reference it early in the Introduction.

**Four-layer validation gates (see §6).**

---

## 6. Validation: four gates (file-not-broken **and** figure-not-wrong)

### Gate A — Structural validity
- Well-formed XML (`xml.dom.minidom.parse`).
- `viewBox` present; `xmlns` present.
- Forbidden-construct counts: `transform=` → 0; `<g` → 0 (or 1 outer, no transform); no
  `<defs>/<use>/<symbol>/<marker>/clip-path`/filters/`<style>`.
- **Duplicate `id` count = 0**; all referenced IDs resolve.
- **No `NaN`/`inf`/`null` coordinates**; **no elements outside the `viewBox`** unless explicitly allowed.
- Referenced fonts are in an allowlist.

### Gate B — Rendering validity (use ≥ 2 renderers, e.g. Chromium + Inkscape)
- PNG preview non-empty; bounding box sane; no unexpected clipping.
- PDF has exactly one page; page size matches the intended width.
- Font status explicit: run `pdfinfo fig.pdf` and `pdffonts fig.pdf` to catch **un-embedded or substituted
  fonts**.

### Gate C — Visual regression
- Render a fixed-size `fig_overview.preview.png` each round; pixel/perceptual-diff against the previous
  version; report **changed-area %**, the bounding box of changed pixels, and a before/after montage. Catches
  the AI silently moving layout when asked to "just recolor the arrow."

### Gate D — Semantic validity (the most valuable, least common layer)
- Align brief element IDs with SVG IDs: `brief − SVG = missing elements`; `SVG − brief = undocumented`.
- Every **frozen label** and **frozen number** appears verbatim; the renderer added **no** new numbers.
- Every claim ID has a verified source; panel order matches the storyboard.

### Final-size readability gate (do not judge on the 1200×560 canvas)
AI figures look fine on a big canvas and collapse at two-column size. Every QA round, view at **three
scales**: native SVG, actual size inside the paper PDF, and the paper page at 100% zoom. Check: smallest text
legible; arrow directions obvious; adjacent lines not merging; icons still recognizable; panel-title vs label
hierarchy; core takeaway visible at first glance.

Specify sizes in the brief in **printed** units (tune per venue template, not as cross-venue absolutes):
`Intended printed width: 6.8 in · Min effective text size: 7.5 pt · Body labels: 8–9 pt · Panel titles:
9–11 pt`. Check effective size **at generation time** with:
```
effective_pt = svg_font_size_px × target_width_in × 72 / viewBox_width
```

---

## 7. Reviewer simulation (a sharper self-critique for Figure 1)

Give an independent model **only the raster preview** (not the paper) and ask:
1. What problem does the paper seem to solve? 2. Method inputs and outputs? 3. Which part is the new
contribution? 4. Which variable changes across the left/right comparison? 5. The single core conclusion?
6. Which arrows are data flow vs causal/contrast? 7. Any number, causal relation, or performance advantage
lacking a source? 8. The three hardest-to-read labels? 9. If deleting 30% of elements, what goes first?
10. Is this more a method overview, teaser, or results summary?

Compare to the intended answers. **If a reader cannot answer 1–5 without the text, Figure 1 is not yet
self-explanatory.** Crucially:
> The critique model must **not** immediately redesign the figure. It must first produce a **diagnosis linked
> to specific element IDs.** Iterate by diagnosis, not by full redraw.

---

## 8. Deliverables: four artifacts + manifest (decouple *editing* from *publication*)

| Artifact | Role |
|---|---|
| `fig_overview.source.svg` | **Source of truth** — semantic groups, stable IDs, *modest* transforms allowed, human-maintained. |
| `fig_overview.ppt.svg` | Deterministically **flattened** from source for *Convert to Shape*; never hand-maintained. |
| `fig_overview.pdf` (or `.pdf_tex`) | **Submission** — fonts embedded or typeset by LaTeX; PPT-editability not required. |
| `fig_overview.preview.png` | Fixed-size raster for visual QA / regression / reviewer simulation. |

Optional: `fig_overview.pptx` (native text boxes), `fig_overview.alt.txt`, `fig_overview_manifest.json`.

`fig_overview_manifest.json` records reproducibility metadata:
```json
{
  "figure_id": "fig:overview",
  "viewBox": "0 0 1200 560",
  "intended_width_in": 6.8,
  "minimum_effective_font_pt": 7.5,
  "palette": {},
  "labels": {},
  "claims": {},
  "alt_text": "...",
  "takeaway": "...",
  "source_data_hash": "...",
  "renderer": "Inkscape",
  "renderer_version": "...",
  "powerpoint_tested_on": "..."
}
```
Keeping the flatten step deterministic prevents "flatten for PPT" from polluting the long-term maintained
source.

---

## 9. Accessibility (beyond `<title>`/`<desc>`)

`<title>`/`<desc>` are good **source-level** metadata but may not survive SVG→PDF→LaTeX→production into the
paper's accessibility structure. Maintain a **separate manuscript-level alt-text / figure-description** field
(e.g. in `figures_data.json` / the manifest), distinct from the caption and *not* a repeat of it. Do not
encode meaning by color alone. Contrast targets: **body text 4.5:1**, **large text 3:1**, **meaningful
non-text graphics 3:1** (very thin lines may render too faint even if they nominally pass).

---

## 10. Iteration loop

1. Get concrete feedback ("PPT can't split it"; "colors too loud"; "label overflows").
2. Diagnose with counts/grep + Gate D ID-diff — pinpoint *why* and *which element IDs*.
3. Send a **targeted** refactor (same render model, context retained): state the one constraint changed;
   keep design/coords/palette/labels fixed.
4. Re-run all gates + visual regression; keep the scientific contract and brief as invariants.

---

## 11. Checklist (copy/paste)
- [ ] **Contract:** figure type + primary function; one-sentence 10-second takeaway; claim→evidence table
      (only *verified* claims); no-overclaim rules acknowledged.
- [ ] **Design:** storyboard → wireframe approved → render-spec frozen (viewBox, zones, elements+IDs, hex
      palette, typography, verbatim labels, frozen numbers from results JSON). Brief saved.
- [ ] **Render:** real `<text>`, stable IDs, exact palette, color+shape+word, math via LaTeX, icons as vector
      primitives, flat (no gradient/filter/shadow).
- [ ] **PPT-compat SVG:** 0 `<g>`, 0 `transform=`, absolute coords, inline styles, no defs/use/marker/clip;
      edit-granularity decomposition; **empirical Convert-to-Shape acceptance test** passed.
- [ ] **Gates:** A structural (dup-id 0, no NaN, in-viewBox, font allowlist); B rendering (≥2 renderers,
      `pdffonts` embedded, 1-page PDF); C visual regression diff; D semantic (brief↔SVG ID diff, frozen
      labels/numbers verbatim, no invented numbers).
- [ ] **Final-size:** legible at actual paper width; `effective_pt` ≥ venue minimum.
- [ ] **Reviewer sim:** independent reader answers Q1–Q5 from the raster alone.
- [ ] **Deliver:** `source.svg` + `ppt.svg` + `pdf` + `preview.png` (+ optional `pptx`/`alt.txt`/`manifest.json`).

---

### Provenance & scope note
Originating figure: the "When Consensus Lies" overview (Claude-opus design brief → GPT-5.6 SVG render →
deterministic flatten → svglib→PDF). This revision folds in a peer critique that (1) demoted cross-model from
a requirement to an optional critique aid, (2) added the **scientific figure contract**, (3) made
PPT-editability a probabilistic profile with a native-PPTX fallback, (4) moved math to LaTeX and icons to
vector primitives, (5) made **Inkscape** the publication master (svglib = fallback), (6) added the four-gate
validation, final-size gate, reviewer simulation, and the four-artifact + manifest delivery. The top-level
goal is **scientific claim fidelity and reviewer legibility**, with editability/PPT as supporting
constraints.
