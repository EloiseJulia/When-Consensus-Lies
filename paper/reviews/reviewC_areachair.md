# Review C — Associate (Area) Chair Meta-Review & Decision

**Paper:** *When Consensus Lies: Fake Redundancy in Multi-Model AI Systems*
**Venue (as submitted):** PACM HCI (CSCW), acmsmall, ~28 pp., double-blind, pre-registered, zero human subjects.
**Inputs:** Reviewer A (Opus senior adversarial, internally simulating three reviewer voices; weak reject 2.0/5); Reviewer B (GPT hostile skeptic; strong reject 1/5); plus my own reading of the source.

---

## DECISION

**Weak Reject** (on the brief's five-point scale).

Because this is realistically a **PACM HCI (CSCW)** submission, and PACM HCI has a **Revise & Resubmit** track, my operational recommendation is **Major Revision (R&R)**, *not* outright reject. On a venue **without** R&R (CHI), the same assessment maps to **Reject**. See the venue contrast at the end.

I am **not** endorsing B's strong reject (1/5): several of B's "critical" points are either factually softened by text B did not credit, or are fixable by reanalysis rather than being disqualifying. I am also **not** endorsing an accept: the paper as submitted advances an *interaction-paradigm* and a *design* contribution with **zero** human or interface evidence, and its two most-quoted numbers are a screening-conditioned rate and an oracle upper bound. Weak Reject / R&R is the honest midpoint that neither over-rewards rigor-as-performance nor punishes a genuinely sound and useful core.

**Confidence:** 4/5. I read the full LaTeX source, the tables, the construct-validity and estimand specifications, Study 2's non-circularity argument, the design section, and the amendment ledger references.

---

## 1. FATAL vs FIXABLE TRIAGE

### Truly fatal *for a top-tier HCI venue as submitted* (cannot be repaired in a rebuttal)

- **(FATAL-1) No human, no interface, no deployment — for a paper that lists an "interaction-paradigm" and a "Design" contribution.** Verified: the Contributions list (§1) claims a *conceptual/interaction-paradigm* contribution and a *Design* contribution, yet §10 (Design Implications) opens "we ran no UI or human-subjects study, so each remains to be evaluated," and §11 concedes "Claims about human trust, teams, and high-stakes domains are *implications*, not tested deployments." Both A (W1) and B (M7) are correct and this is the single dominant issue. It is *not* rebuttal-fixable; it needs new studies. This is what caps the paper below the CHI bar and pushes it below the CSCW acceptance line as submitted.

### Serious but FIXABLE (reanalysis of existing data, relabeling, or disclosure — R&R-addressable)

- **(FIX-1) The "no attenuation from screening" rebuttal uses an unmatched comparison — B's C6 is right, and the paper's own numbers indict it.** Verified: §4.2 compares *unfiltered k=1* (CD=0.685) against the *pooled screened H1 rate 0.53* — but 0.53 is diluted by the structural-zero k=0 controls, whereas screened **k≥1** is **0.82** (R1a, §5.1). So the correct matched contrast (unfiltered k=1 = 0.685 vs screened k≥1 = 0.82) actually suggests *some* screening inflation, not "no attenuation." The paper's stated conclusion ("we find no evidence that screening inflated the effect") is over-claimed. Fixable by reporting the matched k=1-vs-k=1 contrast from data they already have.
- **(FIX-2) Chance-agreement floor unquantified; R1b inconclusive.** Verified (§5.7): "An interpretation-uniform null (R1b) is inconclusive on the primary metric (binary items give a high random baseline)." How much of pairwise agreement 0.98 / ICC 0.89 / n_eff=1.10 survives a cardinality-matched permutation null is not shown. Both A (T3) and B (C5) are right. Fixable by a cardinality-matched null over existing labels.
- **(FIX-3) n_eff/ICC conflate item difficulty with correlated interpretation.** The paper itself concedes this in the dependence-estimator spec: "a legitimate alternative account… is shared item *difficulty* rather than shared *interpretation*; we do not fully separate these." Honestly disclosed; fixable with family-blocked ICC / a family-random-effects model.
- **(FIX-4) Pseudoreplication — 54 variants collapse toward ~21 base families; bootstrap is by `task_id` (variant), not base family.** B's C7 is a legitimate statistical point; leave-one-family-out and base-family clustering would widen CIs. Reanalysis-fixable.
- **(FIX-5) "Independent" vs "debate" naming inconsistency.** §5.2 lists "homogeneous majority/debate" and "heterogeneous cross-family debate" among *primary* conditions, while §5.1 states "agents are queried independently (no inter-agent messages in the primary conditions)." This is a real clarity defect (see overreach note below), fixable by relabeling and by reporting the headline on one-shot non-communicating cells explicitly.
- **(FIX-6) Study 2's deployment-relevant FP is 0.402, reported apart from the 0.095 item-level FP.** B's M4 is right that `flag(mean(score))` (Table 6, k=0 FP 0.095) and `mean(flag(score))` (Table 7, over-clarification 0.402) are different estimands. The paper *does* report both and is candid about 0.402 (abstract and §8.4), but they should be reconciled into one deployment story.
- **(FIX-7) Study 2 marginal value is thin (+0.085 over requirements-probing; CI [0.01,0.19]); semantic entropy is a soft foil.** Both reviewers right; the paper concedes it "does not dominate every baseline." The nearest method (ICE) is discussed but not run (B's M3). Fixable by implementing ICE / a direct ambiguity baseline at equal budget.
- **(FIX-8) Gold-ambiguity label may include disambiguated H2 items as AMB+.** B's C3: AMB+ = "at least two enumerated interpretations produce different executable results," which is *counterfactual sensitivity*, not textual ambiguity; some H2 items retain the deciding fact yet could be AMB+. This is a construct concern distinct from the leakage argument the paper actually rebuts in §7.3. Fixable by excluding disambiguated H2 from AMB+ and validating on independent/natural annotations.
- **(FIX-9) Reproducibility/credibility.** Unverifiable model slugs (`gpt-5.4`, `gpt-5.6-sol`, `claude-opus-4.8`, `gemini-3.1-pro-preview`), constructor slug deferred to camera-ready, artifact promised not provided. Disclosure-fixable now.
- **(FIX-10) Missing the closest CSCW precedent — hidden-profile / shared-information bias (Stasser & Titus; Gigone & Hastie).** B's M16 is an excellent point I fully endorse: this literature maps almost 1:1 onto "shared prompt = shared information, decisive unshared evidence never pooled, confident consensus." Engaging it *both* sharpens venue fit *and* honestly bounds the novelty claim. Writing-fixable.

---

## 2. ARE THE REVIEWERS OVERESTIMATING THE WEAKNESSES?

**Yes, in several consequential places — mostly B, occasionally A. I checked each against the text.**

- **B overreaches on C1 ("wrong consensus is not an epistemically valid error").** This attacks a strawman of the paper's own framing. The paper never claims model irrationality — §1 explicitly calls the default "a locally reasonable inference… not model irrationality," and §9.2 titles the mechanism "Shared-input failure, not groupthink." The contribution is precisely that a *locally reasonable but silently correlated* default is what makes a "4/4 agree" display misleading **to the user**. That is an evidential/interface claim, not a claim that the model is deluded. B's "not a real error" objection does not touch the actual thesis. (The loaded term "delusion" is a fair *minor* point — B's m1 — but not a construct-invalidating one.)

- **B overreaches on C4 ("independent premise contradicted by debate — a direct methods contradiction, 90%").** The text states the primary conditions carry **no inter-agent messages**, and the headline analogue is *cross-vendor comparison/aggregation* (Fig. 4 caption), i.e., aggregation, not debate. B asserts the headline CD/ICC/n_eff "pool final debate outputs," but the source does not support that; the interpretation-diverse and synthesis/role-diversified conditions are explicitly secondary/exploratory and excluded from primary claims. There *is* a genuine naming inconsistency the authors must fix (FIX-5), but it is a clarity defect, not a fatal contradiction.

- **B overreaches on C2 ("location effect not identified… almost definitional, 95%").** R1a is a *within-item* k=0-vs-k≥1 control (same base task, pipeline, labeler, metric; Δ=0.82, CI [0.73,0.90]). That is a legitimate internal-validity identification that item family/difficulty is *not* the driver. Calling it "almost definitional" understates its value: showing CD≈0 when the same task is fully specified is exactly what rules out the generic-difficulty artifact. The confounded contrast is only the *between-family* H1-vs-H2 regime comparison, which the paper openly flags as "different item families, not paired minimal variants." B conflates the two.

- **A slightly overreaches on the oracle "buried caveat."** A (claim #8) says the 0.626→0.010 caveat sits "downstream of the headline." In fact the upper-bound caveat is in the **same abstract sentence** ("…an upper bound, since the detector localizes the missing premise only weakly (0.36) and cannot supply the fix itself"). The paper is unusually candid here; both reviewers' "tautological, oversold" framing is harsher than the text warrants (though de-headlining it is still good advice).

**Where the reviewers are right and I weight them heavily:** the no-humans/no-interface gap (A-W1, B-M7); the unmatched screening rebuttal (B-C6, FIX-1); chance-agreement (both); Study 2's modest increment and un-run ICE (both); the 0.402 deployment FP (B-M4); the hidden-profile omission (B-M16); pseudoreplication (B-C7). These are real and, together, they are why this is a weak reject and not an accept.

**Net:** B's "strong reject, confidence 5/5, requires new data not a rebuttal" is an *over*-estimate of fatality. Roughly three of B's seven "critical" items (C1, C2, C4) are either strawman or fixable-clarity, and two more (C5, C6, C7) are fixable reanalyses, not disqualifiers. A's "weak reject, strong potential after revision" is the more calibrated read.

---

## 3. IS THE CONTRIBUTION SUFFICIENTLY IMPACTFUL?

**Topic: yes. Delivered contribution: borderline-insufficient as submitted, strong after revision.**

The core message — *a consensus display can convert one shared blind spot into apparent multi-model corroboration; model diversity is not evidence diversity* — is timely, important, and directly relevant to how CSCW systems aggregate AI judgments. The **methodological** core (executable, LLM-free gold; correlated-error metric CD (Eq. 1); n_eff (Eq. 2); the within-item k=0 control; pre-registration with a signed amendment ledger and constructor/tested/auditor provenance separation) is the paper's strongest and genuinely transferable asset.

But the *delivered* contribution is an **AI-evaluation/benchmark result wearing HCI clothing**: the human-trust and interface claims are hypothetical; the flagship intervention is an oracle upper bound; the detector's novel step over an assumption-surfacing baseline is +0.085; and the headline 0.53 is a *conditioned* rate the authors themselves say "claims no generality beyond the tested items." That is enough to matter, not yet enough to clear a top HCI bar.

---

## 4. REALISTIC META-REVIEW (for the authors)

This is a rigorous, unusually transparent, and well-written study of a real and timely risk in multi-model interfaces: when several models are given one shared, underspecified prompt, they can silently commit to the *same wrong* reading, so a "4/4 agree" display presents one blind spot as independent corroboration. All three reviewer voices credit the pre-registration discipline, the executable/LLM-free gold, the reported nulls, and the elegance of the within-item k=0 control (R1a, Δ=0.82). I share that assessment, and I want to be explicit that the paper's honesty about its own limits is exemplary and should be preserved, not penalized.

The reason I cannot recommend acceptance as submitted is a mismatch between the paper's *claims* and its *evidence base*, concentrated in three areas.

First and dominant: the paper advances an *interaction-paradigm* and a *design* contribution, but contains no users, no interface, and no deployment (§10 concedes every design move "remains to be evaluated"; §11 concedes the trust/team/high-stakes claims are "implications, not tested deployments"). For CHI/CSCW, the human-centered layer is the contribution reviewers most expect to see evaluated, and here it is entirely hypothetical.

Second: the headline magnitude is conditioned by construction. Items are *reversed* so the natural default is a foil, and inclusion is *screened* on models producing that foil (§4.1–4.2). The paper's rebuttal — an unfiltered 24-item k=1 sample (CD=0.685) that "does not attenuate" relative to 0.53 — compares against a *pooled* rate diluted by k=0 controls; the matched comparison is unfiltered k=1 (0.685) vs screened k≥1 (0.82), which does not support the "no inflation" conclusion. The phenomenon is clearly real (79% of unfiltered items still show CD), but the specific "no attenuation" claim is over-stated and should be softened and re-run on matched strata.

Third: the dependence estimates rest on assumptions the paper concedes are imperfect. The uniform-interpretation null (R1b) is "inconclusive… (binary items give a high random baseline)," and the ICC "cannot fully separate shared difficulty from shared interpretation." The claim that n_eff=1.10 means "roughly one independent judgment" therefore needs a cardinality-matched chance-agreement null and a family-blocked dependence analysis before it can carry the weight the abstract places on it. Relatedly, the primary-condition list labels two conditions "…/debate" while the independence protocol asserts no inter-agent messages in primary conditions; please reconcile this and report the headline on one-shot, non-communicating cells explicitly.

Study 2 is a solid engineering result but is oversold relative to its increment. Against the assumption-surfacing baseline (requirements-probing, AUROC 0.810), counterfactual pinning adds only +0.085 (CI [0.01,0.19]); semantic entropy (0.581) is not the strongest available comparison, and the nearest method (ICE) is discussed but not implemented. The gold-ambiguity label measures counterfactual output-sensitivity, which is not identical to prompt ambiguity and may admit disambiguated H2 items as AMB+. The deployment-relevant false-positive behavior (over-clarification 0.402 pooled) should be presented as the primary operating cost rather than alongside the cosmetically lower 0.095 item-level FP. The 0.626→0.010 intervention is — as the abstract itself states — an oracle upper bound; please keep that caveat, but move the number out of the headline position.

None of the above erases the contribution. The methodological protocol and the diagnosis are valuable, and the framing ("evidential dependence, not agent count") is a good one. But to meet the venue's bar the paper needs (a) at least one human/interface signal, (b) de-conditioning of the core magnitude, and (c) a chance-agreement / family-blocked hardening of the dependence claims. I would also strongly encourage engaging the hidden-profile / shared-information-bias tradition (Stasser & Titus; Gigone & Hastie), which is the closest CSCW precedent and would both sharpen the framing and honestly position the novelty.

**Must-fix before acceptance:** (1) add a human-centered contribution (even a small pre-registered reliance pilot on "4/4 agree" vs a dependence-aware display) or drop the interaction-paradigm/design claims; (2) report the matched k=1-vs-k=1 screening contrast and soften the "no attenuation" language; (3) add a cardinality-matched chance null and family-blocked ICC; (4) demote the oracle result and the conditioned 0.53 from headline positions; (5) provide verifiable model identifiers, the constructor identity, and the artifact at review. Recommended: implement ICE as a Study-2 baseline; reconcile the 0.095/0.402 FP story; engage the hidden-profile literature; consider a neutral term for "convergent delusion."

---

## 5. VENUE CONTRAST — CHI vs CSCW/PACM HCI

The submission is formatted and framed for **PACM HCI (CSCW)**, and that changes both the decision mechanics and the reasoning.

**At CHI (single-shot accept/reject, no R&R; committee weights human-centered empirical/design evaluation heavily):**
- Decision: **Reject** (~10–15% acceptance odds). CHI committees will not accept "design implications" as a *design contribution*, and with zero users the trust/reliance thesis is untested. There is no R&R lever to reward the strong methods core, so the human-evidence gap is effectively decisive in one round. The paper would be told to either add human evaluation or re-target an ML/NLP evaluation venue.

**At CSCW / PACM HCI (has a Major-Revision / R&R track; more receptive to conceptual, methodological, and socio-technical contributions; the monoculture/grounding/hidden-profile framing fits the community):**
- Decision: **Weak Reject → Major Revision (R&R)** (~15–22% as-is; ~40–55% after the revision above). PACM HCI can hold the paper for a revision cycle, which is the right instrument here because the most damaging objections (FIX-1…FIX-10) are reanalysis/relabeling/disclosure, and the one structural gap (human/interface evidence) can be met by a *modest* pre-registered study rather than a full deployment. CSCW reviewers are also the audience most able to appreciate the executable-gold protocol and the "interpretive monoculture ≠ groupthink" distinction — and most likely to *require* engagement with hidden-profile/shared-information bias, which currently is a novelty-and-fit liability.

**Bottom line on venue:** the same paper is a **Reject at CHI** and a **Weak-Reject/R&R at CSCW**. My recommendation is the CSCW-appropriate one: hold for **Major Revision** rather than reject, because the core is sound and the fixes are tractable — but do not accept until at least one human/interface signal exists and the core magnitude is de-conditioned.

---

## 6. WHAT A REBUTTAL COULD SAY THAT WOULD CHANGE MY DECISION

**Would move me from Weak Reject toward Accept / R&R-accept (high leverage):**
1. **A matched screening contrast from existing data:** unfiltered **k=1** vs screened **k=1** (not vs pooled 0.53), showing the effect does not materially attenuate. This directly neutralizes the selection-on-DV objection (FIX-1, B-C6) — the single most damaging *fixable* strike.
2. **A cardinality-matched permutation / chance-agreement null** demonstrating that same-foil concentration (and hence n_eff→1) exceeds what binary/low-cardinality answer spaces produce by chance. This rescues the inconclusive R1b and legitimizes the "one effective judgment" claim (FIX-2/3, both reviewers).
3. **Evidence the headline is computed on one-shot, non-communicating agents only** (with family-blocked ICC), settling the debate-vs-independent naming issue (FIX-5, B-C4). Cheap and decisive because it is a reporting/relabeling fix.
4. **Any human signal** — even a small (N≈20–40) pre-registered within-subjects reliance pilot on "4/4 agree" vs a dependence-aware display. This is the one thing that converts the design/interaction-paradigm contribution from aspiration to evidence and flips venue fit. It is the highest-leverage single addition.
5. **Reframing package (writing-only, high credibility payoff):** state 0.53 as an explicitly conditioned rate; move the oracle 0.626→0.010 out of the abstract headline; adopt a neutral term for "convergent delusion"; and position the work against the hidden-profile / shared-information-bias literature (B-M16).
6. **Base-family clustered reanalysis** (leave-one-family-out; cluster bootstrap by base family) showing the effect and CIs are stable (FIX-4, B-C7).

**Would NOT change my decision (already credited, or non-responsive):**
- Re-asserting rigor, pre-registration, provenance separation, or the execution count (16,461 runs) — already fully credited; call-count is compute, not evidential breadth.
- Defending the terms "lies"/"delusion" on rhetorical grounds.
- Leaning harder on the oracle intervention as a *result* — it is, by the authors' own abstract, an upper bound.
- Arguing that requirements-probing's strength (0.810) *validates* the axis — it also caps the novelty of pinning (+0.085); this cuts both ways.

**Threshold statement:** items **1–3** (all reanalyses of existing data) plus item **5** (writing) would move me to a confident **R&R with a clear path to accept** at CSCW. Adding item **4** (a human pilot) would move me toward **Weak Accept** at CSCW and would be the minimum needed to make the paper viable at CHI. Absent any human/interface signal, my ceiling for this paper at a top HCI venue remains **Weak Reject / Major Revision**, because an interaction-paradigm-and-design contribution with no human or interface evaluation cannot clear the bar no matter how clean the benchmark.
