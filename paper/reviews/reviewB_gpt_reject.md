# Reviewer B — Strongest Rejection Case

## Recommendation

**Strong reject (1/5). Confidence: 5/5.**

The paper has an intuitively appealing warning—agreement cannot recover information absent from every model—but the current evidence does not establish the stronger claims of fake redundancy, independent-error collapse, or a deployable ambiguity detector. The decisive problems are construct validity and estimand validity, not presentation. Study 1 largely engineers a hidden answer that cannot be inferred from the prompt and then calls the natural default “delusion.” Its main causal contrast is not matched, its “independence” analysis pools debate conditions, and its dependence estimators cannot distinguish shared item difficulty from correlated judgment. Study 2’s executable “ambiguity” label does not actually test whether a prompt is ambiguous; it tests whether counterfactual interpretations yield different outputs, including on H2 prompts whose deciding fact is explicitly present. The human-facing CSCW contribution remains unevaluated.

---

## Critical rejection arguments

### C1. The benchmark makes the designated answer unknowable, so “wrong consensus” is not an epistemically valid model error

**Paper location and exact wording.** In **“Executable-Gold Benchmark — Construct and design,”** a task is underspecified when “**multiple interpretations remain consistent with the retained input**.” The paper then says: “**Items are reversed so the natural default an unaware solver would produce is a foil**,” and Table 2 defines H1 so “**the target \((I_0)\) requires external knowledge**.” The Introduction concedes that “**an agent’s default is often a locally reasonable inference from the underspecified prompt, not model irrationality**.”

**Logic.** If multiple readings are consistent and the fact selecting \(I_0\) is deliberately unavailable, the output is not wrong relative to the evidence supplied; it is wrong only relative to a private latent specification. Executable code can verify compatibility with that hidden specification, but cannot make the hidden specification inferable. The demonstrated fact is therefore the elementary one that several systems given the same insufficient evidence may choose the same salient default. The normative failure would have to be *failure to qualify or seek clarification*, yet that construct is measured only by an unvalidated abstention rule (M6). “Convergent delusion,” “lies,” and “evidence of roughly one independent judgment” inflate a hidden-spec compliance test into epistemic failure.

**Persuasiveness:** **Very high (95%)**; this attacks the primary outcome’s meaning.

**Possible author rebuttal.** Reframe the outcome as *latent-spec mismatch*, not delusion; establish a task norm that requires clarification; compare models with humans or domain experts; and evaluate whether answers explicitly disclose assumptions rather than merely whether they match \(I_0\).

### C2. The claimed causal “location of the disambiguator” effect is not identified

**Paper location and exact wording.** The benchmark section explicitly admits: “**the 40 H1_external and 14 H2_derivable items are different item families, not paired minimal variants of identical tasks, so the H1-versus-H2 contrast is a broad regime comparison**,” and “**Constructing fully matched paired H1/H2 variants … is future work**.” It substitutes R1a, saying the “**sharpest causal evidence**” is within-item \(k=0\) versus \(k\ge1\). The primary H2 interaction is “**not estimable**” on 14 items. The later regime-by-domain check has only “**\(n=4\) items per cell per domain**.”

**Logic.** H1 versus H2 changes item family, domain mix, task semantics, and whether the answer is actually recoverable. R1a does not isolate *external versus internal location*; it compares a fully specified prompt with a prompt from which decisive information was deleted. A large difference is almost definitional. It cannot show that “location” rather than item family, solvability, foil construction, or prompt cues is the mechanism. The small secondary crossing cannot repair the absent primary matched manipulation.

**Persuasiveness:** **Very high (95%)**.

**Possible author rebuttal.** Create matched triplets for each base task: the same convention stated in-prompt, supplied through an external context channel, or absent; randomize which convention is target; use the same domains and item families; and analyze the paired contrast.

### C3. Study 2’s “executable gold-ambiguity” label is not a gold label for prompt ambiguity

**Paper location and exact wording.** H2 is defined in Table 2 as a regime where “**the deciding fact is in the prompt, so a competent solver can derive \(I_0\)**,” and F1 says H2 contains the disambiguator. Yet **“Study 2 — Executable gold-ambiguity and non-circularity”** labels an item AMB+ “**iff at least two of its own enumerated interpretations produce different executable results on its test inputs**.” It reports **33 AMB+ and 21 AMB−**.

**Logic.** Different hypothetical conventions producing different outputs establishes *counterfactual sensitivity*, not textual ambiguity. An H2 item can have two executable counterfactuals even though the prompt explicitly determines which one applies; such an item is not ambiguous under the paper’s own Study 1 definition. The reported 33 positives correspond to the \(k\ge1\) variants, including seven H2-derivable variants whose decisive facts are retained. LPP then generates alternative premise values and asks whether outputs change—the same property used by the gold. Separate pin sets avoid literal leakage but not criterion circularity. AUROC 0.895 therefore does not validate detection of a “missing latent premise.”

**Persuasiveness:** **Very high (95%)**; it invalidates Study 2’s target construct.

**Possible author rebuttal.** Obtain independent human judgments of whether multiple interpretations remain reasonable *given the actual prompt*, exclude disambiguated H2 cases from AMB+, and validate on naturally occurring ambiguous and unambiguous prompts.

### C4. The paper’s “independently queried” premise contradicts its primary debate conditions

**Paper location and exact wording.** Under **“Models, tiers, and families,”** the paper states: “**agents are queried independently (no inter-agent messages in the primary conditions) so that any error correlation reflects shared priors and shared inputs, not conversational influence**.” But **“Conditions and estimands”** lists “**homogeneous majority/debate**” and “**heterogeneous cross-family debate**” as primary conditions. The artifact prompt in `harness/run.py` explicitly supplies “**Previous round answers from all agents**” before requesting an updated answer.

**Logic.** Debate creates exactly the conformity and social-influence dependence that the paper claims to exclude and itself cites in related work. If the headline CD, ICC, kappa, pairwise agreement, and \(n_{\mathrm{eff}}\) pool final debate outputs, they cannot identify a shared-input mechanism. Even if only some rows are interactive, pooling them with non-interactive sampling contaminates the estimand. The paper cannot simultaneously call these agents independent and expose them to peers’ answers.

**Persuasiveness:** **Very high (90%)** because this is a direct methods contradiction.

**Possible author rebuttal.** Report all primary claims using only one-shot, non-communicating cross-vendor agents; separate debate as an intervention; state exactly which round is scored; and show the result survives without any answer exchange.

### C5. \(n_{\mathrm{eff}}=1.10\) does not estimate the number of independent judgments

**Paper location and exact wording.** Under **“Dependence-estimator specification,”** ICC is a one-way random-effects model on the binary wrong indicator, with “**item-cell … as the random grouping factor**”; the paper concedes that “**a legitimate alternative account of the observed excess is shared item difficulty rather than shared interpretation; we do not fully separate these**.” Table 4 reports pairwise wrong-answer agreement 0.98, ICC 0.89, and \(n_{\mathrm{eff}}=1.10\). R1b’s interpretation-uniform null is “**inconclusive on the primary metric (binary items give a high random baseline)**.”

**Logic.** This ICC is high whenever some item-cells are easy and others hard, even if agents are conditionally independent given an item’s difficulty. It is not a residual cross-agent correlation estimate. Pairwise agreement is conditioned on both agents being wrong and is nearly forced when a binary item has only one enumerated wrong foil. Applying the exchangeable survey-sampling formula to heterogeneous models, task-varying Bernoulli errors, debate outputs, and a pooled ICC has no demonstrated justification. The paper’s own caveat admits the key alternative explanation, yet the abstract turns the estimate into “close to one effective independent judgment.”

**Persuasiveness:** **Very high (90%)**.

**Possible author rebuttal.** Estimate dependence conditional on item with repeated independent runs, use hierarchical multivariate models with model-family effects, report label-distribution agreement against item-specific independent marginals, and validate the \(n_{\mathrm{eff}}\) estimator by simulation under known dependence.

### C6. The “unfiltered replication” compares different estimands and cannot rebut selection-on-the-outcome

**Paper location and exact wording.** The construct-validity section admits that inclusion was “**partly conditioned on the default behavior we then measure**.” It claims an unfiltered replication resolves this: “**across 24 unfiltered \(k=1\) items, pooled unconditioned convergent delusion is CD=0.685 … The point-estimate delta relative to the screened confirmatory rate is +0.155**,” where the comparison rate is 0.53. F1 shows that the confirmatory H1 aggregate includes \(k=0\), where CD is 0, and \(k\ge1\), where CD is 0.82; Figure 2 further shows strong variation across \(k\).

**Logic.** A \(k=1\)-only unfiltered sample is compared with a pooled screened H1 rate that includes structural-zero \(k=0\) controls and \(k=2,3\) variants where CD declines. The two rates have different \(k\) compositions and weights. The fact that 0.53 lies inside the unfiltered CI says nothing about attenuation from screening. The required comparison is unfiltered \(k=1\) versus screened \(k=1\) under the same models, conditions, domains, and item weighting. This leaves Reviewer A’s selection-on-the-dependent-variable objection intact despite the paper’s claimed rebuttal.

**Persuasiveness:** **Very high (90%)**.

**Possible author rebuttal.** Report a matched \(k=1\)-to-\(k=1\) contrast, predefine a population sampling frame, include every generated item before observing model behavior, and provide selection-flow counts and excluded-item outcomes.

### C7. The effective sample is about 21 base families, not 54 independent tasks or thousands of jobs

**Paper location and exact wording.** The benchmark calls its corpus “**54 task variants**” and repeatedly describes matched variants of the “**same base task**.” Study 2 bootstraps by `task_id`; the paper emphasizes **5,832 aggregation jobs (16,461 agent executions)**. Inspection of the provided JSONL files shows that the 54 variants reduce to **21 base families** (14 H1 and 7 H2), with some bases contributing 4 or 8 variants; the IDs encode these families.

**Logic.** Variants from one base share prompt text, semantics, checker code, target/default axis, and construction history. Treating each variant ID as a bootstrap cluster understates uncertainty and gives prolific bases disproportionate weight. The H2 primary sample is only seven paired base families. Thousands of model calls are repeated measurements, not independent task evidence. The headline 0.53 is also a design-weighted average over unequal numbers of \(k\), condition, and variant cells; changing the number of structural-zero controls or combinatorial variants changes it without changing any underlying phenomenon.

**Persuasiveness:** **High (85%)**, especially to statistically attentive reviewers.

**Possible author rebuttal.** Cluster and weight by base family, report family-level estimates and leave-one-family-out sensitivity, expand to many independently sourced bases, and define the target population that makes the 0.53 weighting meaningful.

---

## Major rejection arguments

### M1. Study 2 has no independent development/test split or external validation

**Paper location and exact wording.** Study 2 is evaluated on “**the 54 pre-registered items**” from Study 1. The method, thresholds \(\tau=0,\tau_s=0.5\), pilot, and validation were all developed around this benchmark, and the paper states that the “**method and the validation pilot were audited**” before the confirmatory run.

**Logic.** Preregistration prevents some outcome switching but does not establish out-of-sample validity after method and threshold development on the same constructed task ecology. Cross-vendor replication repeats models, not prompt distributions. LPP may recognize deletion-template artifacts or the existence of benchmark-authored axes. No natural prompts, external ambiguity dataset, new constructor, temporal holdout, or untouched domain tests generalization.

**Persuasiveness:** **High (85%)**.

**Possible author rebuttal.** Freeze LPP, then evaluate once on a separately collected corpus with independent ambiguity annotations, unseen domains, natural conversation history, and no benchmark-template overlap.

### M2. The detector is not evaluated against the actual failure it claims to detect

**Paper location and exact wording.** Study 2 asks whether the system can “**detect … that a prompt harbors a decision-relevant latent premise**” and calls this “**the latent-premise ambiguity behind the failure**.” Its gold is AMB+/AMB−, not whether a multi-model ensemble actually exhibits high CD, harmful wrong consensus, or low effective redundancy.

**Logic.** Ambiguity is neither necessary nor sufficient for fake redundancy. Some ambiguous prompts produce diverse answers; some fully specified prompts produce correlated mistakes. A generic ambiguity detector therefore does not establish a detector of misleading consensus. The paper provides no precision/recall for actual wrong consensus, no calibration conditional on observed model agreement, and no incremental prediction beyond prompt difficulty or requirements count.

**Persuasiveness:** **High (85%)**.

**Possible author rebuttal.** Make the target an independently held-out event such as high same-wrong-foil concentration conditional on consensus, evaluate prospective prediction before ensemble answers are seen, and compare against agreement-strength and task-difficulty baselines.

### M3. “SOTA-blind” is a straw comparison; the nearest relevant method is not implemented

**Paper location and exact wording.** The paper calls semantic entropy the “**state-of-the-art hallucination signal**” and headlines a \(+0.314\) AUROC gap. Yet it admits that requirements probing reaches **0.810**, that LPP’s pinning increment is only “**modest (+0.085; 95% CI [0.01,0.19])**,” and that the closest method is ICE. It explicitly says LPP “**does not dominate every baseline**.”

**Logic.** Semantic entropy was designed for uncertainty/hallucination, not for detecting deliberately deleted requirements. Defining a low-semantic-entropy “danger quadrant” and then celebrating semantic entropy’s failure there is close to choosing the baseline’s blind spot by construction. The relevant comparison is against ambiguity/clarification methods such as ICE, direct ambiguity classification, assumption elicitation, and calibrated clarification policies. ICE is discussed but not run. The actual algorithmic novelty over “ask for assumptions” is small and uncertain.

**Persuasiveness:** **High (85%)**.

**Possible author rebuttal.** Implement ICE and strong direct ambiguity baselines under equal query budgets, compare calibrated operating points and cost, and center the claim on the incremental value of pinning rather than the semantic-entropy gap.

### M4. Study 2 reports incompatible false-positive behavior for the “same” frozen detector

**Paper location and exact wording.** Table 7 reports, at \(\tau=0,\tau_s=0.5\), pooled **precision 0.926, recall 0.758, \(k=0\) FP rate 0.095**. Table 8, also at the “**frozen operating point**” on the same 33 AMB+/21 AMB− items, reports LPP **appropriate 0.741 and over-clarification 0.402**.

**Logic.** The actionable detector appears four times worse on negatives than the headline confusion table suggests. The artifact indicates different aggregation orders—thresholding an across-model mean versus averaging per-cell threshold decisions—so `flag(mean(score))` and `mean(flag(score))` produce different estimands. The paper does not explain this consequential nonlinearity while presenting both as pooled performance at the same threshold. A deployer cares about 40.2% unnecessary clarifications, not the cosmetically cleaner 9.5% item-level FP.

**Persuasiveness:** **High (80%)**.

**Possible author rebuttal.** Define one deployment unit and aggregation order, use it consistently in both tables, reconcile every discrepancy, and report per-model calibrated precision, recall, and cost.

### M5. The oracle intervention is tautological and does not validate the detector-to-fix loop

**Paper location and exact wording.** H-B2′ uses “**a controlled oracle that supplies the deleted axis’s gold convention**,” reducing CD from **0.626 to 0.010**. The paper concedes that “**LPP’s own premise localization is weak**” at **0.36**, “**the detector does not autonomously supply the fix**,” and real users are untested.

**Logic.** Giving the model the exact withheld answer condition should resolve a task whose construction consists of deleting that condition; R1a already showed this. Because the oracle receives the gold axis independently of LPP’s weak localization, the dramatic reduction is not evidence that the proposed detector can produce an effective clarification. It is a manipulation check marketed as a constructive intervention.

**Persuasiveness:** **High (85%)**.

**Possible author rebuttal.** Generate clarification questions from LPP without gold access, have real or independently simulated users answer only those questions, and score end-to-end utility including wrong localization, unanswered questions, and clarification cost.

### M6. “Silent” and “confident” are not validly operationalized, and the prompts discourage abstention

**Paper location and exact wording.** F4 reports an abstention/clarification rate of **approximately 0.03%** using a “**rule-based (non-LLM) detector**,” and says “**we use ‘confident’ descriptively for this commit-without-flagging behavior**”; the detector “**awaits human validation**.” In the provided artifact, the prompts command “Please provide your answer” and require a final code block or exact numeric answer. The blinded coding instructions classify “Assuming X, here is the answer” as a non-abstention.

**Logic.** An explicit assumption plus answer is a user-visible warning, but the metric calls it silent because the model did not refuse. Exact-answer prompting also suppresses clarification by design. Thus 0.03% measures complete answer withholding under answer-forcing instructions, not whether models surface missing context, hedge, offer alternatives, or signal uncertainty. The central “nothing in the display distinguishes it” claim is unsupported.

**Persuasiveness:** **High (85%)**.

**Possible author rebuttal.** Human-code assumption disclosure, hedging, alternatives, clarification, and refusal separately; use neutral prompts that permit clarification; validate inter-rater reliability; and test what users notice.

### M7. The paper’s HCI/CSCW claims have no human or interface evidence

**Paper location and exact wording.** The Introduction asserts “**It is hard not to read that unanimity as reassurance**” and that consensus cues can increase reliance. But **“Design Implications”** states: “**we ran no UI or human-subjects study**,” and Limitations/Ethics confirms “**no human subjects**” and that the interface remains “**to be built and evaluated**.”

**Logic.** The paper does not show that users infer independence, that a “4/4” display changes trust, that users fail to notice shared inputs, that context loss occurs in collaborative workflows, or that the proposed warning improves reliance. Primary agents mostly perform benchmark tasks, not cooperative work. At CSCW/PACM HCI, the social, organizational, and interaction claims are motivational extrapolations from an ML evaluation.

**Persuasiveness:** **High (85%)** for CSCW reviewers.

**Possible author rebuttal.** Add a preregistered user study with actual multi-model interfaces, behavioral reliance outcomes, qualitative analysis of interpretation, and ecologically grounded collaborative handoffs.

### M8. Capability and family invariance are overclaimed from confounded and post-hoc null tests

**Paper location and exact wording.** F2 says “**frontier reasoners are trapped about as reliably as weaker, non-frontier models**,” based on “**post-hoc secondary**” TOSTs. One contrast fails the stricter \(\pm0.10\) margin (\(p=0.145\)); the H2 capability interaction is “**not estimable**”; and the paper notes some comparisons are not method-matched.

**Logic.** Model tier, family, aggregation method, and ensemble composition are not cleanly crossed. Equivalence margins of 0.10–0.15 CD are large relative to many practical improvements and were applied post hoc. Failure to estimate H2 interactions cannot support capability-insensitivity. Three vendor labels—some proxy-renamed—do not establish invariance across architectures or training lineages.

**Persuasiveness:** **High (80%)**.

**Possible author rebuttal.** Use a fully crossed model-by-method design, preregister equivalence tests and substantively justified margins, analyze model-level random effects, and replicate on transparent open models.

### M9. The constructor control does not rule out construction artifacts

**Paper location and exact wording.** Table 3 withholds the primary constructor as “**slug in camera-ready**.” R2 has only six ambiguous items; its preregistered aggregation metric is “**statistically inconclusive**,” so F5 relies on a “**post-hoc secondary**” concentration analysis in which only **4/6** items show two non-constructor families on the same foil.

**Logic.** A second model constructor choosing conventional defaults does not establish constructor independence: model families share web data, benchmark tropes, and common conventions. Six ambiguous items and a failed preregistered test cannot support “not an artifact.” There is no human-authored or naturally sourced benchmark control and no analysis of rejected constructor outputs.

**Persuasiveness:** **High (80%)**.

**Possible author rebuttal.** Reveal the constructor for review, use multiple human and model constructors, preregister a much larger held-out construction sample, and report all generated items before screening.

### M10. The preregistration provides weak protection against analytic flexibility

**Paper location and exact wording.** Appendix A lists **A01–A14**, including reversing defaults, expanding foil sets, changing \(I_\perp\) treatment, replacing the shuffle null, pilot-calibrating the sample, and adding robustness analyses. After the confirmatory run, two interventions were “**post-hoc exploratory**” but also “**pre-registered as a secondary amendment**.” A preregistered AU-Probe was “**not run**.” Several preregistered primary tests are inconclusive or not estimable, while post-hoc analyses sustain the narrative.

**Logic.** A git timestamp before a selected “confirmatory run” does not eliminate adaptation to pilots, default checks, construction iterations, or prior runs. Calling an after-data amendment preregistration is misleading. The unavailable ledger prevents reviewers from checking the chronology. The pattern—failed planned tests followed by favorable direct or TOST analyses—creates substantial researcher degrees of freedom.

**Persuasiveness:** **High (80%)**.

**Possible author rebuttal.** Supply a public anonymized timestamped registration and complete amendment diff, identify all data observed before each change, distinguish confirmatory from exploratory claims in the abstract, and replicate once with no amendments.

### M11. Reproducibility is inadequate for review

**Paper location and exact wording.** Table 3 uses unstable or unverifiable slugs, says a proxy renamed Gemini, and withholds the constructor. **“Data and code availability”** says an artifact “**will**” be released and a permanent link comes “**on acceptance**.”

**Logic.** Model identity, version, prompts, generation settings, raw outputs, preregistration chronology, and checkers are necessary to assess a model-behavior paper during review, not after acceptance. Institution-hosted proxy aliases impede independent replication and model drift makes later reproduction unlikely. The paper’s unusually strong provenance claims are not externally auditable.

**Persuasiveness:** **High (85%)**.

**Possible author rebuttal.** Provide an anonymous artifact now with immutable hashes, full raw data and prompts, exact provider/version metadata, executable scripts, and the complete registration ledger.

### M12. Executability validates internal consistency, not semantic validity or realism

**Paper location and exact wording.** The benchmark says code checks are “**finite behavioral checks, not proofs**”; policy QA “**verifies only the final numeric amount rather than the reasoning path**.” It reports two items with “**incomplete foil sets**.” No human annotation was required, and the main semantics were machine-constructed.

**Logic.** The checkers show that authored candidates are distinguishable, not that \(I_0\) is the uniquely appropriate real-world interpretation, that prompts are naturally occurring, or that model outputs are correctly mapped outside the finite tests. Numeric equality can conceal invalid policy reasoning. The already discovered incomplete foil sets show enumeration is fallible. “Executable gold” is valuable engineering, but the paper treats it as broader construct validation than it provides.

**Persuasiveness:** **Moderately high (75%)**.

**Possible author rebuttal.** Add expert semantic review, adversarial test generation independent of the constructor, all-input property checks where possible, natural-task validation, and error analysis of \(I_\perp\) and ambiguous labels.

### M13. External validity is too narrow to support the system-level conclusions

**Paper location and exact wording.** Limitations admits “**single-episode and non-interactive**” tasks, no prevalence estimate, and future generalization beyond three domains. The conclusion nevertheless says “**The fix is not more agents but a different question**” and recommends system-wide dependence-aware design.

**Logic.** The 21 base families are synthetic code/data/policy exercises with known deleted axes. Real systems include retrieval, conversation, multimodal evidence, tool use, expertise specialization, dynamic context, and users who can inspect reasoning. The prevalence of decisive omitted conventions and the cost of wrong defaults are unknown. Two post-hoc same-input interventions with CIs crossing zero cannot show that more agents or other coordination methods do not help.

**Persuasiveness:** **High (80%)**.

**Possible author rebuttal.** Narrow the conclusion to an existence proof on constructed tasks and replicate in natural collaborative workflows with diverse evidence paths and consequential decisions.

### M14. The novelty and five-contribution framing are inflated

**Paper location and exact wording.** The paper claims five contributions: conceptual, empirical, methodological, design, and detector. Related work already covers correlated cross-provider errors, debate convergence, underspecification, monoculture, semantic entropy, and ICE. The design contribution is explicitly “**a proposed concept; its evaluation is future work**,” and pinning adds only \(+0.085\) over requirements probing.

**Logic.** Study 1 combines known ingredients around an almost definitional manipulation: agents cannot recover a uniformly withheld convention. “Fake redundancy,” “interpretive monoculture,” and “convergent delusion” mostly rename correlated errors under shared information. Study 2 is assumption elicitation plus counterfactual clarification. The landscape table and unevaluated UI do not constitute separate empirical contributions. At most, the paper offers one useful benchmark protocol and one incremental detector.

**Persuasiveness:** **Moderately high (75%)**.

**Possible author rebuttal.** Collapse the contribution list, precisely isolate algorithmic novelty against ICE and requirements probing, and present the benchmark as the principal contribution without claiming a validated interaction paradigm.

### M15. The platform “landscape audit” is not rigorous enough to support a field-level gap

**Paper location and exact wording.** **“Same-prompt multi-model comparison interfaces”** says candidates came from public web search; no accounts or telemetry were used; six of nine platforms are tabulated; hosted products are not version-pinned. It then claims “**none warned**” about missing information or shared-input dependence.

**Logic.** There is no reproducible search query set, screening flow, coder count, codebook reliability, UI inspection, usage weighting, or archived evidence. Absence from marketing/docs is not absence from the actual interface. The table’s binary “input-adequacy signal” also embeds the authors’ preferred concept. This is a convenience sample, not a landscape audit capable of establishing a systematic design gap.

**Persuasiveness:** **Moderate (70%)**.

**Possible author rebuttal.** Archive all evidence, report a systematic sampling/coding protocol and reliability, inspect product behavior, and call the result an illustrative survey rather than an audit.

### M16. The related-work framing omits the closest CSCW/group-decision tradition

**Paper location and exact wording.** The related-work section is organized around aggregation, grounding, reliance, monoculture, and LLM ensembles, and claims a distinct CSCW contribution concerning aggregated judgment.

**Logic.** The most direct conceptual precedent is the **hidden-profile/shared-information-bias/common-knowledge-effect** literature (e.g., Stasser & Titus; Gigone & Hastie): groups overweight commonly held information and fail when decisive unshared information is not pooled. That tradition maps almost exactly onto shared prompts, missing unique evidence, confident consensus, and information pooling. The paper also under-engages CSCW work on awareness/provenance, social translucence, conversational repair, and collaborative sensemaking. Omitting these literatures makes “fake redundancy” look newer than it is and weakens the venue fit.

**Persuasiveness:** **Moderately high (75%)** among CSCW reviewers.

**Possible author rebuttal.** Position the work explicitly as a computational instantiation of shared-information bias, explain what model ensembles add beyond hidden profiles, and engage CSCW provenance/repair scholarship in the design implications.

---

## Minor rejection arguments

### m1. The terminology is sensational and anthropomorphic

**Paper location and exact wording.** The title says **“When Consensus Lies”** and the core metric is **“convergent delusion,”** although the Introduction admits defaults are locally reasonable and says the term is not psychological.

**Logic.** A system selecting a plausible default under genuine underdetermination is neither lying nor deluded. The labels rhetorically pre-judge the construct and encourage readers to treat hidden-spec mismatch as irrationality.

**Persuasiveness:** **Moderate (60%)**.

**Possible author rebuttal.** Use neutral terms such as *shared-default mismatch* or *latent-spec consensus error*.

### m2. Null and inconclusive findings are repeatedly converted into mechanistic evidence

**Paper location and exact wording.** Table 5 says capability/family nulls “**make the failure a property of the information boundary**.” Phase B calls a null “**informative**” and suggests same-input remedies may be insufficient, although both intervention CIs include zero and only two workflows were tested.

**Logic.** Failure to detect alternatives does not establish the proposed mechanism. The paper often includes a caveat and then restates the stronger causal interpretation in captions or conclusions.

**Persuasiveness:** **Moderate (65%)**.

**Possible author rebuttal.** Reserve mechanistic language for identified contrasts and label all null-based interpretations as hypotheses.

### m3. The large execution count is rhetorically misleading

**Paper location and exact wording.** Results and Ethics foreground **5,832 jobs and 16,461 executions**, while the benchmark contains 54 variants and only 21 base families in the provided data.

**Logic.** API-call count measures compute, not evidential breadth. Repetition across methods, models, rounds, and seeds cannot substitute for independent tasks.

**Persuasiveness:** **Moderate (60%)**.

**Possible author rebuttal.** Lead with independent base-family counts and treat call totals only as reproducibility/resource information.

---

## Ranked danger summary

### Critical
1. **C1 — The hidden target is unknowable; “wrong consensus” is not an epistemically valid error.**
2. **C3 — Study 2’s gold label measures counterfactual sensitivity, not prompt ambiguity.**
3. **C2 — The disambiguator-location causal effect is not identified.**
4. **C4 — “Independent” primary agents are contradicted by primary debate conditions.**
5. **C5 — ICC/\(n_{\mathrm{eff}}\) do not identify independent-judgment collapse.**
6. **C6 — The unfiltered replication is an unmatched \(k=1\) versus pooled-\(k\) comparison.**
7. **C7 — Pseudoreplication and arbitrary cell weighting reduce 54 variants to about 21 base families.**

### Major
1. **M1 — No independent detector test set or external validation.**
2. **M2 — The detector is not evaluated against actual fake redundancy/wrong consensus.**
3. **M3 — Semantic entropy is a straw baseline; ICE is not implemented; pinning adds only +0.085.**
4. **M4 — The same operating point yields 9.5% FP in detection but 40.2% over-clarification in action.**
5. **M5 — The gold-convention oracle is tautological and bypasses weak localization.**
6. **M6 — “Silent/confident” is answer-withholding under answer-forcing prompts, not validated warning absence.**
7. **M7 — No humans or evaluated interface support the CSCW reliance/design claims.**
8. **M8 — Capability/family invariance rests on confounded, post-hoc equivalence tests and an unestimable interaction.**
9. **M9 — Six-item, partly post-hoc R2 evidence cannot eliminate constructor artifacts.**
10. **M10 — Fourteen amendments and favorable post-hoc substitutions weaken preregistration protection.**
11. **M11 — Artifacts, constructor identity, and stable model/version metadata are unavailable for review.**
12. **M12 — Executable checks validate internal behavior, not semantic gold or realism.**
13. **M13 — Synthetic, non-interactive tasks do not support broad system-level prescriptions.**
14. **M14 — Five contributions largely repackage known results and an unevaluated design concept.**
15. **M15 — The six-platform public-document audit cannot establish a systematic interface gap.**
16. **M16 — Missing hidden-profile/shared-information and CSCW provenance/repair literature weakens novelty.**

### Minor
1. **m1 — “Lies” and “delusion” are sensational labels for plausible defaulting under underdetermination.**
2. **m2 — Null and inconclusive findings are overinterpreted as mechanism.**
3. **m3 — Execution count inflates perceived evidence relative to independent task breadth.**

## Bottom line

The strongest defensible contribution is a carefully engineered executable benchmark illustrating that models often share conventional defaults when decisive context is deleted. That is substantially narrower than the paper’s claims. The current studies do not establish a causal information-boundary mechanism, a valid effective-ensemble-size estimate, a detector of misleading consensus, or an HCI intervention. Fixing these issues requires new matched benchmark data, redefined ambiguity gold, non-interacting analyses, independent external validation, and human/interface evaluation—not a rebuttal-only revision.
