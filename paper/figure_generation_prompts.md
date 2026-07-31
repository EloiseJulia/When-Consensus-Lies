# Figure-generation prompts — *When Consensus Lies* (CSCW / PACM HCI)

Hand each block to a figure-drawing AI to reproduce/compare. Data values are the
**frozen confirmatory numbers** (from `figures_data.json` / `results_verified.json`);
do not alter any number. Figs 1 and 6 are **schematics** (concept diagrams), not data
charts — described qualitatively.

---

## GLOBAL STYLE (applies to every figure)

- **Venue / size:** ACM PACM HCI (CSCW), `acmsmall` single column. Export **vector PDF**
  (+ PNG preview). Draw at final print size (~3.3–5.5 in wide); do **not** rescale afterward.
- **Fonts:** serif (Times New Roman) to match ACM body; tick/label ≥ 6 pt at final size.
- **No title inside the figure** (the caption lives in LaTeX).
- **Colorblind-safe** with redundant encoding (line style / marker shape, not color alone).
- **Semantic color convention (keep consistent across all figures):**
  - **Red** `#D9534F` = H1_external / danger regime / convergent-delusion (the *bad* thing)
  - **Blue** `#3B6EA5` = LPP (our detector, `H_ctx`) / H2_derivable / safe regime
  - **Gray** `#7F7F7F` = semantic-entropy baseline (`H_seed`)
  - **Green dashed** `#2E9E7B` = requirements-probing baseline
  - **Dotted gray** = chance
  - Ink text `#2D3748`
- **Error bars:** bootstrap **95% CI**, clustered on `task_id`; always state N + CI type.
- No top/right spines; light horizontal gridlines only where they aid reading.

---

## Figure 2 — Convergent-delusion phase diagram  *(line + CI band)*

**Message:** The failure is a property of the *information boundary*, not task difficulty.
On H1_external, convergent delusion (CD) is zero at the fully specified `k=0` control and
jumps once a disambiguating clause is deleted; on H2_derivable it stays ~0 at every k.

**Chart:** line plot, two series, shaded ±SE band, markers at each point.

**Data (x = ambiguity level k; y = CD, 0–~0.9):**

| series | k=0 | k=1 | k=2 | k=3 |
|---|---|---|---|---|
| **H1_external** (red, circle) | 0.000 (SE 0.000, n=420) | 0.890 (SE 0.010, n=570) | 0.676 (SE 0.028, n=180) | 0.316 (SE 0.059, n=30) |
| **H2_derivable** (blue, diamond) | 0.000 (SE 0.000, n=210) | 0.000 (SE 0.000, n=210) | — | — |

- x-axis: "Ambiguity level *k*" (integer 0–3). y-axis: "Convergent delusion (CD)".
- H2_derivable only measured at k=0,1 (flat line at 0). Shade ±SE.

---

## Figure 3 — Fake redundancy  *(two-panel bar)*

**Message:** High inter-agent error dependence collapses the effective ensemble size to ≈1 —
nominally many agents supply the evidence of roughly one. Adding agents adds no independent evidence.

**Chart:** 1×2 bar panels, H1_external vs H2_derivable, danger-red bars for H1.

**Panel (a) — Effective ensemble size (n_eff):**
- H1_external = **1.10** ; H2_derivable = not defined (CD=0, omit/blank bar)
- Dashed reference line at **nominal n ≈ 8.1** ("Nominal n≈8.1")
- y-axis: "Effective ensemble size (n_eff)", range 0–8.

**Panel (b) — Inter-agent ICC (wrong-indicator):**
- H1_external = **0.894** ; H2_derivable ≈ 0 (omit/blank)
- Dotted reference lines at 0 and 1. y-axis: "ICC (wrong-indicator)", range 0–1.

**Context for caption (not plotted):** pairwise wrong-answer agreement = 0.982; κ = 0.971.
Panel labels "(a)"/"(b)" placed cleanly (do not overlap legend).

---

## Figure 4 — The failure is silent  *(log-scale bar)*

**Message:** Agents almost never flag missing information — the abstention rate is ~3 orders of
magnitude below the convergent-delusion rate. Consensus offers no internal warning.

**Chart:** 3 bars, **log-scale y**.

| bar | value | color |
|---|---|---|
| H1 abstention | 0.031% (0.00031) | blue |
| H2 abstention | 0.323% (0.00323) | blue |
| **H1 convergent delusion** | **53.2% (0.532)** | red |

- y-axis: "rate (log scale)", range ~1e-4 to 1e0.
- Annotate the ≈10³× gap between H1 abstention and H1 convergent-delusion (label "≈10³× gap (silent)").
- Abstention/clarification measured by the **rule-based (non-LLM)** signal detector.

---

## Figure 5 — The danger quadrant  *(scatter, per-item)*

**Message:** Ambiguous items are confidently self-consistent under resampling (low semantic
entropy) yet flip once a latent premise is pinned (high LPP entropy) — exactly the quadrant
semantic entropy is blind to.

**Chart:** scatter, 54 pre-registered items, one point each (pooled per-item mean).
- x-axis: `H_seed` — semantic entropy (SOTA baseline), bits.
- y-axis: `H_ctx` — latent-premise pinning (LPP), bits.
- Color by **executable gold-ambiguity**: AMB+ (ambiguous) vs AMB− (unambiguous, control).
- **Shaded danger quadrant:** `H_seed ≤ τ_s=0.5`  ∧  `H_ctx > τ=0`.
- Key stat to reproduce: **25 of 33 (0.758) AMB+ items** fall inside the quadrant;
  AMB− controls cluster near the origin; many low-signal items coincide at (0,0) — annotate the pile-up.

> ⚠️ **Per-point coordinates are NOT in `figures_data.json`** — they live in the raw checkpoint
> `.run_partitions/cp_lps_confirm_merged.jsonl` (fields `H_seed`, `H_ctx_max`, `task_id`; AMB±
> from a `_k0` task-id marker). Give the drawing AI that file, or the coordinates exported from
> the current `fig_danger_quadrant_v2.pdf`, so it plots the real 54 points.

---

## Figure 7 — Detection AUROC  *(grouped bar + reference lines + 95% CI)*

**Message:** LPP (`H_ctx`) separates ambiguous from unambiguous prompts (pooled 0.895) while
same-prompt semantic entropy (`H_seed`) sits near chance (0.581). Requirements-probing alone is
already strong (0.810); counterfactual pinning adds a real but modest **+0.085**.

**Chart:** grouped bars (LPP = blue, semantic entropy = gray), one group per model + a bold
"Pooled" group; green dashed line = requirements-probing 0.810; dotted line = chance 0.5.
y-axis: "AUROC (executable gold-ambiguity)", range **0.4–1.0**. Error bars = 95% CI.

| model | LPP `H_ctx` (95% CI) | semantic entropy `H_seed` (95% CI) |
|---|---|---|
| gpt-5.6 | 0.857 (0.774–0.932) | 0.563 (0.467–0.657) |
| opus-4.8 | 0.887 (0.808–0.956) | 0.591 (0.529–0.662) |
| gem-3.1 | 0.857 (0.771–0.934) | 0.606 (0.534–0.682) |
| 4o-mini | 0.856 (0.768–0.933) | 0.551 (0.472–0.629) |
| haiku | 0.869 (0.787–0.941) | 0.567 (0.483–0.648) |
| gem-3.5 | 0.880 (0.797–0.955) | 0.580 (0.493–0.667) |
| **Pooled** | **0.895 (0.815–0.966)** | **0.581 (0.484–0.675)** |

- Print the pooled value labels (0.895, 0.581) above their CI caps. Bold the "Pooled" x-tick.
- Reference lines: requirements-probing **0.810** (green dashed), chance **0.5** (dotted).

---

## Figure 1 — Overview  *(concept diagram / schematic — NOT a data chart)*

**Purpose (30-second read):** show that the *same* multi-model setup forks into two regimes,
that consensus can be fake, and that a black-box detector recovers the hidden ambiguity.

**Content to depict:**
- **Top:** the same underspecified task → *k* independent agents (three model families × capability tiers).
  The matched causal control is **within-item**: same base task, `k=0` (clause retained) vs `k≥1` (clause deleted).
- **Left fork — H1_external** (deciding clause *outside* the retained prompt): agents *silently*
  converge on the **same wrong** interpretation. Consensus looks strong ("5/5 agree") but is wrong;
  the k-agent ensemble collapses to ≈1 effective independent judgment → **fake redundancy**
  (ρ→1, n_eff = 1.10; CD ≈ 0.53).
- **Right fork — H2_derivable** (clause *inside* the prompt): no tier converges on a shared wrong
  interpretation (CD = 0; residual off-axis `I⊥` remains).
- **Correctness** is set by an **executable-gold** check, not an LLM judge.
- **H3 / Detector:** on the same 54 tasks, pinning a self-surfaced latent premise and testing whether
  the answer flips detects ambiguous items at **AUROC = 0.895**.
- **Takeaway label:** the failure tracks the clause's *location*, not model capability.
- Footnote values: ICC = 0.89, mean pairwise wrong-answer agreement = 0.98, abstention ≈ 0.03%.
- **Honesty note for the illustrator:** H1 and H2 are *different constructed task families* (a broad
  regime comparison), **not** a single prompt with a clause moved — do **not** draw it as a minimal pair.
  For H2's box prefer wording like "5 agents, correctly resolved" over "5 independent readings"
  (CD=0 shows no shared wrong reading, not statistical independence).

---

## Figure 6 — LPP detector mechanism  *(three-step flowchart + scatter inset — schematic)*

**Purpose:** show the detector is black-box, inference-only, three steps, and why it catches what
semantic entropy misses.

**Content to depict (left → right flow):**
1. **Self-surface** — a *generic* prompt asks the model to name decision-relevant **unstated premises**
   (e.g., quarter convention, rounding, date range); it never mentions the gold key (anti-leakage).
2. **Counterfactually pin** — each self-surfaced premise is pinned to the model's **own** candidate
   values v₁…vₘ, producing **one answer per pin**.
3. **Cluster (executable)** — pinned answers are grouped by **mutual executable equivalence**;
   `H_ctx` = entropy over the resulting answer clusters.
- **Right inset scatter:** ambiguous items concentrate in the **high-`H_ctx`, low-`H_seed` danger
  quadrant** that same-prompt semantic entropy misses; detector reaches **AUROC 0.895 vs 0.581**.
- Black-box / inference-only badge: needs only sampled completions — no logits, gradients, or
  vendor-specific access (runs identically across OpenAI / Anthropic / Google).
