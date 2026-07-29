# Review A — Adversarial Senior Review (CHI/CSCW, <25% acceptance)

**Paper:** *When Consensus Lies: Fake Redundancy in Multi-Model AI Systems*
**Venue framing:** PACM HCI (CSCW), venue-neutral ACM template, ~28 pp., double-blind
**Reviewer stance:** Senior HCI/CSCW reviewer; expertise in Human–AI Interaction, CSCW, HCI methodology, LLM systems, user studies, mixed methods. Mandate: find every weakness and reason to reject. This review does not attempt to help the authors.

---

## TASK 1 — High-Level Assessment

**1. One-sentence summary.**
Using a hand-constructed 54-item "executable-gold" benchmark of deliberately underspecified tasks, the paper claims that independently queried LLMs from three vendors silently converge on the *same wrong* interpretation when a disambiguating clause is deleted from the shared prompt ("fake redundancy," convergent-delusion ≈0.53, effective ensemble size *n*_eff=1.10), and proposes a black-box detector (LPP, pooled AUROC 0.895) plus unevaluated interface design implications.

**2. Claimed contributions** (verbatim from the "Contributions" paragraph, §1):
- (C1) *Conceptual/interaction-paradigm*: names "fake redundancy" + a landscape audit (Table 1) of same-prompt multi-model interfaces.
- (C2) *Empirical*: pre-registered evidence that agents across tiers and three families silently converge on the same wrong reading when the disambiguator is omitted, and this vanishes when present; "capability-insensitive and cross-family."
- (C3) *Methodological*: an "executable-gold" protocol measuring correlated error (not accuracy), with dependence estimators (pairwise agreement, ICC, *n*_eff).
- (C4) *Design*: a "dependence-aware multi-model interface" concept + six design implications (explicitly unevaluated).
- (C5) *Systems/detector (Study 2)*: black-box cross-vendor LPP detector (AUROC 0.895) + detector-gated oracle clarification that "nearly eliminates" convergent delusion (0.626→0.010).

**3. Actual contributions (my assessment).**
- A *clean, controlled demonstration* — on a small constructed benchmark — that deleting a disambiguating clause switches on shared-default convergence, and that this is not eliminated by mixing vendors or capability tiers. This is the paper's real, defensible core (F1/F2, R1a).
- A *reframing* of correlated-error / monoculture / underspecification results (already established separately by Kim et al., Estornell & Liu, Yang et al., Kleinberg et al.) into an interface-centered vocabulary and a single manipulation (disambiguator location).
- A *detector engineering result* (Study 2) whose marginal value over an existing-style baseline is small (+0.085 AUROC over requirements-probing).
- Everything human-, interface-, and deployment-facing is **aspiration, not contribution**: no UI, no users, no deployment. C4 is self-described as unvalidated; the headline intervention number is an **oracle upper bound**.

**4. Main strengths.**
- Genuinely rigorous open-science posture: pre-registration frozen at a commit, a signed amendment ledger (Appendix A, Table 8), reported nulls, executable/LLM-free gold labels, and provenance separation between constructor/tested/auditor families.
- The disambiguator-location manipulation with the within-item *k*=0 control (R1a; Δ=0.82, CI [0.73,0.90]) is a clean internal-validity move that rules out generic item difficulty.
- The metric *convergent delusion* (Eq. 1) sensibly separates *correlated* error from mere inaccuracy, and the *n*_eff framing (Eq. 2) is a crisp way to say "5 agents = ~1 judgment."
- Honest self-critique throughout (screening caveat, exchangeability caveat, oracle caveat, weak localization).

**5. Main weaknesses (headline).**
- **(W1) Zero human subjects in a paper whose thesis, title, and design section are entirely about *human* trust, reliance, and interface design.** Every user-facing claim is an "implication." For a top-tier HCI venue this is the dominant rejection risk.
- **(W2) The central number is manufactured by construction.** Items are *reversed* so the natural default is a foil, and inclusion is *conditioned on* models producing that foil (default screen). The 0.53 rate is therefore not a measurement of a phenomenon's magnitude — the paper concedes it "claims no generality beyond the tested items."
- **(W3) Near-tautology risk.** Delete the only clause that determines the answer → the model outputs the default → the default is defined as wrong. The surprising part ("they converge on the *same* wrong reading") is undercut by small answer spaces: R1b (uniform null) is **inconclusive** because "binary items give a high random baseline." Much of the "convergence" may be chance agreement.
- **(W4) Tiny, synthetic, non-interactive benchmark.** 54 items (40 H1 / **14** H2), single-episode, no retrieval, no real interface, no iteration; H2 interaction "not estimable." External validity to CSCW collaborative pipelines is asserted, not shown.
- **(W5) Study 2's practical value is thin.** Pinning adds only +0.085 AUROC over requirements-probing (CI [0.01,0.19], barely excludes 0); pooled over-clarification is **0.402** (flags 40% of unambiguous prompts); localization is **0.36**; the "0.626→0.010" fix is an **oracle** that hands the model the gold convention.
- **(W6) Reproducibility/credibility flags.** Model roster uses slugs that do not correspond to publicly known models at submission (e.g., `gpt-5.4`, `gpt-5.6-sol`, `claude-opus-4.8`, `claude-sonnet-4.6`, `gemini-3.1-pro-preview`); the primary constructor's slug is deferred to camera-ready ("slug in camera-ready," Table 3). Artifact is promised but not available at review.

---

## TASK 2 — Novelty Assessment

**Is the problem truly new?** *Partially.* The *interface framing* ("a 4/4-agree display can mislead because models share one input") is a fresh, HCI-relevant packaging. But the underlying *phenomena* are established: LLM errors correlate across providers (Kim et al. 2025, cited); debate converges on shared misconceptions (Estornell & Liu 2024, cited); underspecification degrades LLM performance (Yang et al. 2025, cited); algorithmic monoculture produces correlated outcomes (Kleinberg et al. 2021, cited); alignment/instruction tuning narrows output diversity (Murthy 2025; Padmakumar 2024, cited). The paper's own §2.6 concedes these "establish related pieces *separately*."

**Is the contribution incremental?** The empirical core is a *controlled recombination*: it isolates "disambiguator location" as an on/off switch and measures correlated error rather than accuracy. That is a real methodological refinement, but it is **incremental over a dense prior literature** the authors themselves cite.

**Which prior work makes this vulnerable?**
- **Kim et al. 2025 (correlated errors across providers)** — a skeptic will say the headline "cross-family convergence" is a re-demonstration on constructed items. The authors' disclaimer ("our aim is not to rediscover that frontier-model errors are correlated," §1) is a tell that the reviewer's first instinct is exactly this.
- **Hou et al. 2024 (ICE)** — the Study 2 detector is a close cousin (self-surface + counterfactual pin vs. clarify + ensemble). The differentiation is in *target/mechanism/setting*, not performance; and requirements-probing (an assumption-surfacing baseline) already hits 0.810, so the novel "pinning" step adds only +0.085.
- **Farquhar et al. 2024 (semantic entropy)** — used as the foil; the "SOTA-blind" claim is real but narrow (semantic entropy was never designed to catch stable, confident latent-premise commitment).

**What would a skeptical reviewer say?** "This is a nicely engineered confirmation that if you delete the deciding clause, models give the common-convention answer and agree with each other — which is close to definitional — dressed in an HCI vocabulary. The genuinely new artifacts (interface, human study) aren't here."

**Novelty gaps / positioning weaknesses / contribution inflation.**
- **Inflation:** five contributions, but C4 is explicitly unevaluated ("its evaluation is future work"), and C5's flagship intervention is an oracle. Counting a *concept* and an *oracle upper bound* as contributions is overreach.
- The abstract foregrounds "cuts convergent delusion from CD 0.626 to 0.010" and only parenthetically flags it as an upper bound with weak (0.36) localization.

**Verdict: C. Mostly incremental.** The framing and controlled manipulation are moderately novel; the empirical phenomenon is largely a recombination of cited results, and the strongest *new* artifacts are unevaluated or oracle-bounded.

---

## TASK 3 — Methodology Audit

### Study 1 (benchmark diagnosis)

**Design.** 2-regime (H1_external vs H2_derivable) × model-class × ambiguity-level *k*∈{0,1,2,3}, 54 items, 3 seeds, primary aggregation conditions; 5,832 aggregation jobs / 16,461 executions. Outcome = convergent delusion (Eq. 1).

**Recruitment / participants / diversity / sample size.** No human participants. "Sample" = 54 constructed items (40 H1 / 14 H2) and a 12-model roster. **The item sample is small and unbalanced**; H2 has only 14 items across four *k* levels, so per-cell *n* is tiny (the robustness crossing uses *n*=4 items/cell/domain, §Results F/robustness). This directly causes the "H2 interaction not estimable" failure (Table 5, §5.7).

**Threats to validity.**

| # | Threat | Type | Severity | Likely reviewer criticism | Suggested fix |
|---|--------|------|----------|---------------------------|---------------|
| T1 | Items *reversed* + *screened* on the very default behavior later measured (§Construct validity) | Construct / selection-on-DV | **Critical** | "0.53 is engineered; you selected items where models produce the foil, then report how often they produce the foil." | Report unconditioned prevalence on a representative task sample; the 24-item unfiltered check (CD=0.685, CI [0.521,0.839]) is a start but is itself tiny and still constructed. |
| T2 | H1 vs H2 are *different item families*, not paired minimal variants (§4.1 explicit) | Internal | High | "Your headline regime contrast confounds regime with item family/domain/difficulty." | Ship truly paired items (same base task in both regimes); authors defer this to future work. |
| T3 | Small answer spaces → chance agreement; R1b uniform null **inconclusive** (Table 5) | Statistical/construct | High | "How much of *n*_eff=1.10 is chance agreement on binary/low-cardinality outputs?" | Report answer-space cardinality per item; use a cardinality-matched permutation null; condition CD on ≥3 enumerated foils. |
| T4 | *n*_eff / ICC assume within-cell exchangeability, admitted violated for heterogeneous families (§Dependence-estimator spec) | Statistical | Medium-High | "*n*_eff=1.10 for a cross-family pool rests on an exchangeability idealization you say is false." | Report family-blocked dependence, or a mixed model with family random effects; avoid a single pooled ICC. |
| T5 | "Wrong" is defined against a *hidden external convention* (fiscal year, C truncation) the model cannot infer; authors call the default "locally reasonable" (§1) yet label it "delusion" | Construct / framing | Medium-High | "This isn't a model error; it's unavoidable underspecification. 'Convergent delusion' is loaded." | Reframe as 'shared-default commitment'; separate *silence* (the real harm) from *wrongness*. |
| T6 | Abstention/silence measured by an unvalidated **rule-based** detector (§F4), which underpins the "silent" claim (0.03%) | Construct | Medium-High | "If your regex misses hedges/soft clarifications, the silence rate is wrong." | Human-validate abstention coding on a sample; report inter-rater/agreement vs. the rule. |
| T7 | Multiple comparisons, post-hoc TOST, seed=3, temp=0.0 makes per-item CD coarse (§Study 2 intervention notes) | Statistical | Medium | "Family-wise error uncontrolled; equivalence tests are post-hoc secondary." | Pre-register equivalence margins; correct for multiplicity; more seeds. |
| T8 | Ecological validity: single-episode, non-interactive, synthetic, no retrieval, no UI | External | **Critical for CSCW** | "No collaborative pipeline, no handoff, no human — the CSCW framing is untested." | Add an interactive/handoff simulation and, ideally, humans. |
| T9 | Model slugs not publicly identifiable at submission; constructor slug withheld | Reproducibility | Medium-High | "Can these runs be reproduced? Which models are these?" | Provide verifiable model identifiers/version records now (anonymized), not "in camera-ready." |

### Study 2 (LPP detector + intervention)

- **Construct validity of gold-ambiguity label** is reasonable (executable, detector-independent; 33 AMB+/21 AMB−). The non-circularity argument (§7.3) is sound.
- **Internal validity:** the flagged operating point (τ=0, τ_s=0.5) is frozen — good. But **over-clarification 0.402 pooled** (Table 7) means the gate fires on ~40% of *unambiguous* prompts; the *k*=0 FP of 0.095 (Table 6) and the AMB− over-rate 0.402 are reported in different places and read inconsistently to a fast reviewer (needs a single, reconciled FP story).
- **Incremental value:** pinning adds **+0.085** over requirements-probing (CI [0.01,0.19]); the CI's lower bound (0.01) means the "real but modest" increment is *barely* distinguishable from zero. The paper is commendably candid, but a skeptic reads this as "the novel step is near-noise."
- **Intervention is oracle-bounded:** H-B2′ supplies the *gold convention* on clarification (a "simulated-user oracle"). 0.626→0.010 shows only that *if you tell the model the answer, it answers correctly*. Since localization is 0.36, the detector cannot itself produce the clarification content, so the end-to-end system is not demonstrated. **External validity ≈ 0** without a human clarifier.
- **Statistical power:** 6 models × 54 items × 3 seeds, temp 0.0; per-item CD "coarse," CIs carried by task_id bootstrap — acceptable but thin.

---

## TASK 4 — Evidence vs Claims

| # | Claim (location) | Supporting evidence | Adequate? | Reviewer concern |
|---|------------------|---------------------|-----------|------------------|
| 1 | "convergent-delusion rate ≈0.53" as the magnitude of fake redundancy (Abstract; Table 2) | 40 screened H1 items | **No (as prevalence)** | Selection-on-DV (T1); explicitly "no generality beyond tested items." A rate, not a discovery of magnitude. |
| 2 | "model diversity is not evidence diversity"; cross-family ≈ homogeneous (Δ=−0.003; §5.2) | Table 2, TOST (post-hoc) | Partly | Equivalence rests on post-hoc secondary TOST; weak-vs-heterogeneous *not* equivalent at ±0.10 (p=0.145) — quietly contradicts the clean "capability-insensitive" story. |
| 3 | "*n*_eff=1.10 … adding agents cannot restore independence" (§5.3; Table 4) | ICC 0.89, pairwise 0.98 | Partly | Exchangeability admitted false for heterogeneous pool (T4); chance-agreement floor unquantified (T3). |
| 4 | "The failure is silent" (abstention ≈0.03%; F4, Fig. 5) | Rule-based detector | Partly | Detector unvalidated by humans (T6); "confident" used descriptively but rhetorically loaded. |
| 5 | "vanishes when disambiguator is present" (CD H2=0.00; Table 2) | 14 H2 items | Partly | Different item families (T2); H2 *ι*_⊥ rate up to 15.2% means "resolved" overstates; *n*=14 underpowered. |
| 6 | "not an artifact of the constructor" (R2; §5.5) | Anthropic-built subset, 6 items *k*≥1 | Weak | R2 aggregation metric **inconclusive**; concentration 0.711 with CI [0.400,0.978] on 6 items — extremely wide; rebuttal rests on a handful of items. |
| 7 | Detector "separates ambiguous from unambiguous at AUROC 0.895" (Abstract; Table 5-2) | Table 5-2 | Yes (narrow) | True vs semantic entropy; but requirements-probing 0.810 makes the *novel* margin +0.085. |
| 8 | "cuts convergent delusion from 0.626 to 0.010" (Abstract; §8.5) | Oracle intervention | **No (misleading as stated)** | Oracle supplies gold; localization 0.36 means the detector can't do it alone. Upper-bound caveat is downstream of the headline. |
| 9 | Landscape "systematic asymmetry … none warned … none asked" (§2.1, Table 1) | 6–9 platforms, marketing copy, 1 snapshot | Weak | Coding from public copy only; no usage/behavioral verification; *n*≤9; "no claims about popularity/harm" concedes limited weight. |
| 10 | Design implications will help users (§9, six moves) | None (no study) | **No** | Zero evaluation; the authors label them implications — but they are framed as a contribution. |

**Places where claims exceed evidence:** the abstract's 0.53 (as phenomenon magnitude), the 0.626→0.010 intervention (oracle), the "capability-insensitive/cross-family" universality (screened items, post-hoc TOST with one failing margin), and the design contribution (unevaluated).

---

## TASK 5 — CHI/CSCW Contribution Test

| Category | Present? | Strength |
|----------|----------|----------|
| **Empirical** | Yes | Moderate — clean manipulation, but small/synthetic/screened; external validity weak. |
| **Methodological** | Yes | **Strongest** — executable-gold, correlated-error metric, *n*_eff, pre-registration discipline. This is the paper's best claim to a CSCW contribution. |
| **Theoretical** | Partial | "Shared-input monoculture ≠ groupthink" (§Discussion) is a nice conceptual distinction but lightly developed. |
| **Design** | Weak | Concept + six implications, **all unevaluated**. |
| **Systems** | Partial | LPP detector runs cross-vendor, but marginal value (+0.085) and over-clarification (0.402) limit it; no system deployed. |

**Strongest category:** methodological (executable-gold + correlated-error + pre-registration).

**Is it strong enough for CHI/CSCW?** *Borderline-to-insufficient as submitted.* CHI/CSCW reward **human-centered** empirical or design contributions with demonstrated relevance to people/collaboration. Here the human-centered layer is entirely hypothetical. A methodological/AI-evaluation contribution of this kind is a better fit for an ML/NLP evaluation venue (or CSCW *only* if paired with a human or interface study). The "collaborative work" framing (grounding, handoffs, CSCW) is invoked verbally but never instantiated in an actual collaborative setting.

---

## TASK 6 — Simulated Reviewers

### Reviewer A — Constructive but critical (leaning weak reject / borderline)
- **Strengths:** Timely, well-written, unusually rigorous pre-registration and honest null reporting; the disambiguator-location manipulation + *k*=0 control is elegant; *n*_eff framing is memorable and useful for practitioners.
- **Weaknesses:** No humans, no interface — for CHI/CSCW the design and trust claims are untested; benchmark is small/synthetic/screened; Study 2's practical increment is small and the flagship fix is an oracle.
- **Questions:** (1) Can you produce a *paired* H1/H2 item set to remove the family confound? (2) What is the unconditioned prevalence on a representative (unscreened, non-reversed) task distribution? (3) How much of *n*_eff=1.10 survives a cardinality-matched chance-agreement null?

### Reviewer B — Methodology-focused skeptic (reject)
- **Strengths:** Executable/LLM-free gold; frozen operating points; reported nulls; provenance separation.
- **Weaknesses:** **Selection-on-the-dependent-variable** (screen for items where models produce the foil, then measure foil production). R1b uniform null **inconclusive** — chance agreement not ruled out. *n*_eff rests on an exchangeability assumption the authors admit is false for the cross-family pool. TOST is post-hoc secondary; one margin (weak vs heterogeneous, ±0.10) fails. H2 interaction not estimable (*n*=14). Multiplicity uncontrolled. Model slugs unverifiable; constructor withheld.
- **Questions:** (1) Provide the cardinality-matched permutation baseline for CD and *n*_eff. (2) Report family-blocked ICC. (3) Give verifiable model identifiers and the constructor now. (4) Human-validate the abstention rule.

### Reviewer C — Novelty-focused skeptic (reject)
- **Strengths:** Nice interface vocabulary ("fake redundancy," "danger quadrant"); good synthesis of the literature.
- **Weaknesses:** Core phenomenon = recombination of Kim et al. (correlated errors), Estornell & Liu (debate converges on misconceptions), Yang et al. (underspecification), Kleinberg (monoculture); detector ≈ ICE variant with a +0.085 marginal step. The paper's own disclaimers ("not to rediscover…," "differs in target, not in being better") signal thin novelty. The genuinely new artifacts (interface, human study) are absent.
- **Questions:** (1) What can a practitioner do *differently* today that Kim et al. + ICE didn't already imply? (2) Beyond naming, what is the *mechanistic* advance over "shared priors cause correlated errors"? (3) Is "convergent delusion" more than "the default answer to an underspecified question"?

---

## TASK 7 — Meta-Review (Associate Chair)

**Summary of discussion.** All three reviewers credit the paper's rigor, clarity, and pre-registration discipline, and agree the disambiguator-location manipulation with the within-item *k*=0 control is a clean result. The disagreement is about sufficiency for a top HCI venue. R-A is borderline; R-B rejects on selection-on-DV, chance-agreement, and exchangeability; R-C rejects on incremental novelty. The unifying concern across all three is that **a paper whose title, thesis, and design section are about human trust and interface design contains no humans, no interface, and no deployment** — the CSCW payload is entirely hypothetical, and the most striking numbers (0.53 rate; 0.626→0.010 fix) are respectively a screening-conditioned rate and an oracle upper bound.

**Likely outcome.** **Reject** at CHI/CSCW as submitted, with encouragement to resubmit either (a) with a human-subjects study and an implemented dependence-aware interface for a CSCW resubmission, or (b) reframed as an LLM-evaluation/benchmark paper for an ML/NLP venue. In an R&R-capable track this would be a **major revision** at best.

**Major concerns (must-fix).**
1. Add a human-centered contribution (user study and/or working interface) — or drop the trust/design framing.
2. Break the selection-on-DV confound: report unconditioned prevalence and paired H1/H2 items.
3. Rule out chance agreement (cardinality-matched null); reconcile with the inconclusive R1b.
4. De-oracle Study 2 or clearly demote the 0.626→0.010 result out of the abstract's headline position.
5. Fix reproducibility: verifiable model identities, constructor disclosure, available artifact at review.

**What must be fixed before acceptance.** At minimum #1–#3 for CSCW; #4–#5 are necessary for credibility regardless of venue.

---

## TASK 8 — Final Scores (1–5; 5 = best)

| Dimension | Score | Justification |
|-----------|-------|---------------|
| **Originality** | **2.5** | Fresh interface framing + controlled manipulation, but core phenomenon recombines heavily-cited prior work; detector is an ICE-adjacent variant (+0.085 novel step). |
| **Significance** | **2.5** | Important *topic* (consensus displays mislead), but significance is capped by screened/synthetic items, no humans, and an oracle-bounded fix. |
| **Methodological Rigor** | **3.5** | Strong pre-registration, executable gold, reported nulls, provenance separation — but selection-on-DV, chance-agreement gap, exchangeability, post-hoc TOST, *n*=14 H2. |
| **Technical Quality** | **3.5** | Careful, internally consistent, well-instrumented; the honesty about limitations is exemplary. |
| **Clarity** | **4.0** | Very well written and organized; occasionally over-dense and rhetorically loaded ("delusion"). |
| **Reproducibility** | **3.0** | Excellent intent (frozen commits, promised artifact) undercut by unverifiable model slugs, withheld constructor, artifact not available at review. |
| **Overall Recommendation** | **2.0 (weak reject)** | Rigorous and clear, but not yet a top-tier *HCI* contribution: no human-centered evidence, and headline claims exceed evidence. |

**Reviewer confidence:** **4/5** (high). I read the full source, tables, figures, appendix, and confirmed the supporting artifacts exist; my main residual uncertainty is whether the promised artifact would resolve the reproducibility flags.

---

## TASK 9 — Acceptance Probability

- **CHI:** **~10–15%.** CHI strongly weights human-centered empirical/design contributions and interaction evaluation. With zero users, no interface, and design implications as the "design contribution," most CHI committees would reject; the methodological rigor and topical relevance keep it from near-zero.
- **CSCW (PACM HCI):** **~15–22%.** CSCW is somewhat more receptive to conceptual/socio-technical framing and to systems/methods contributions, and the pre-registration + monoculture-in-collaboration framing fits the community. But the same "no humans / no collaborative pipeline / oracle fix" gap, plus the selection-on-DV concern, will likely push it below the acceptance line in a competitive cycle. A revision adding a human study or a built interface could move it to ~40–50%.

**Why:** the work is rigorous but sits in an awkward venue gap — too human-framed to be judged purely as an ML benchmark paper, too human-empty to satisfy HCI's core evaluation expectations.

---

## TASK 10 — Revision Roadmap (2 weeks; top 10, ranked by impact)

1. **Reposition the headline away from the oracle and the screened rate.** Rewrite the abstract so 0.53 is stated as a *conditioned* rate and 0.626→0.010 is stated up-front as an oracle upper bound (not a system result). *Highest impact, ~1 day, pure writing — removes the two biggest "overclaim" rejection triggers.*
2. **Run a cardinality-matched chance-agreement null for CD and *n*_eff.** Show the observed convergence exceeds chance on the actual answer-space sizes; this directly answers R-B's strongest objection and rescues the inconclusive R1b. *~2–3 days, reuses existing labels.*
3. **Report unconditioned prevalence on a modest unscreened, non-reversed task sample.** Extend the 24-item unfiltered probe to a larger, non-reversed set to blunt selection-on-DV. *~3–4 days of runs.*
4. **Add a minimal human-subjects pilot (even N≈20–30).** A short within-subjects reliance study on "4/4 agree" vs a dependence-aware display — even a pilot converts C4 from aspiration to evidence and addresses the universal reviewer concern. *~1 week if IRB/expedited is feasible; the single largest lever for HCI acceptance.* (If IRB is impossible in 2 weeks, prototype the interface and run a small heuristic-eval instead.)
5. **Build and demo the dependence-aware interface** (functional prototype + walkthrough), so the "design contribution" is an artifact, not a list. *~3–4 days.*
6. **De-emphasize/relabel "convergent delusion."** Adopt a neutral term (e.g., "shared-default convergence") and cleanly separate *wrongness* (unavoidable under underspecification) from *silence* (the actionable harm). *~1 day, defuses R-B/R-C framing objections.*
7. **Human-validate the abstention/silence detector** on a labeled sample and report agreement with the rule. *~2 days; shores up the "silent" claim (F4).*
8. **Report family-blocked dependence estimators** (ICC/*n*_eff within family + a family-random-effects model) to honor the exchangeability caveat instead of only footnoting it. *~1–2 days.*
9. **Fix reproducibility:** give verifiable (anonymized) model identifiers and versions, disclose the constructor family/slug now, and attach the artifact for review. *~1 day.*
10. **Add one paired H1/H2 item mini-set** (same base task shipped in both regimes) even if only 6–10 items, to remove the item-family confound behind the headline regime contrast. *~3–4 days of construction + runs.*

*Ranking rationale:* #1, #2, #6, #9 are cheap and remove the most damaging "overclaim/confound/credibility" objections; #4 and #5 are the only moves that create the missing *human/design* contribution and thus most change the venue-fit verdict; #3, #7, #8, #10 harden the empirical core against the methodology skeptic.

---

### Bottom line
A rigorously executed, clearly written, and admirably transparent study of a real risk in multi-model interfaces — but as submitted it is an *AI-evaluation* paper wearing *HCI* clothing: the human trust and interface claims are untested, the headline effect is conditioned by construction, the flagship fix is an oracle, and the novelty is largely a controlled recombination of cited results. **Recommendation: Reject (weak) for CHI/CSCW as submitted; strong potential after a revision that adds a human/interface evaluation and de-conditions the core estimate.**
