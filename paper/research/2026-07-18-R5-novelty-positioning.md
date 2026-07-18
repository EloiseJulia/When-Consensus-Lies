> Doc-only research (R5 novelty positioning). Author: research sub-agent, GPT family (gpt-5.6-sol), 2026-07-18.
> Commissioned by owner directive item 5. Manager persisted to RESEARCH_DIR; not independently re-verified.

# Novelty Positioning and Related Work for *When Consensus Lies*

**Research date:** 2026-07-18  
**Scope note:** Literature claims below were checked against primary-paper metadata or abstracts where possible. Claims about *When Consensus Lies* are based on the supplied thesis and are **not independently verified here**. “First” claims are avoided unless supportable.

## Executive assessment

The broad proposition that aggregation fails under correlated errors is not new: it follows from correlated-vote extensions of the Condorcet Jury Theorem and classical ensemble theory. Nor is it new that LLM debate can converge to a shared misconception: Estornell and Liu provide essentially that theoretical result, while Kim et al. document correlated errors across more than 350 LLMs and Wynn et al. show harmful conformity in heterogeneous debate.

The defensible novelty therefore lies in the **controlled causal characterization of a particular failure regime**, not in discovering correlated consensus generally. The strongest claim is that a matched manipulation of **where the disambiguating information resides**—outside versus inside the retained prompt—produces a capability-invariant, cross-family phase change between near-universal modal-wrong convergence and near-universal recovery. The executable-gold reversal and the `cd_primary` modal-wrong metric sharpen this contribution by distinguishing a single shared interpretation from generic inaccuracy or disagreement.

---

# 1. Self-consistency and sampling-based aggregation

## 1.1 What this literature establishes

Self-consistency samples multiple reasoning paths and chooses the most frequent answer. Its motivating hypothesis is that diverse correct paths tend to converge on the unique correct answer, while incorrect paths disperse across alternatives. Wang et al. report substantial improvements over greedy chain-of-thought decoding: +17.9 points on GSM8K, +11.0 on SVAMP, +12.2 on AQuA, +6.4 on StrategyQA, and +3.9 on ARC-Challenge ([Wang et al., 2023, ICLR, arXiv:2203.11171](https://arxiv.org/abs/2203.11171)).

The method’s benefit is conditional, however, on two properties:

1. enough probability mass lies on the correct answer; and  
2. wrong samples are sufficiently dispersed that no wrong answer becomes modal.

The original paper’s accuracy curves flatten as the number of samples grows—approximately by tens of samples rather than indefinitely—showing diminishing returns rather than Condorcet-style convergence to certainty. More fundamentally, majority sampling estimates the **mode of the model-induced answer distribution**. If the mode is wrong, additional samples identify that wrong mode more reliably rather than correcting it.

Recent evidence makes this limitation concrete. Kim et al. study more than 350 LLMs and find substantial error correlation: on one leaderboard, two models that are both wrong choose the same wrong answer about 60% of the time. Correlation is especially high among larger, more accurate models, including models from distinct architectures and providers ([Kim et al., 2025, ICML, arXiv:2506.07962](https://arxiv.org/abs/2506.07962)). Thus, apparent model or sample multiplicity need not supply independent evidence.

## 1.2 Strongest prior papers

- **Wang et al., “Self-Consistency Improves Chain of Thought Reasoning in Language Models,” ICLR 2023.** Introduces sampled reasoning plus majority aggregation and demonstrates large average gains, but its premise is explicitly that incorrect paths are less likely to agree ([arXiv:2203.11171](https://arxiv.org/abs/2203.11171)).
- **Kim et al., “Correlated Errors in Large Language Models,” ICML 2025.** Large-scale cross-model evidence that errors remain correlated across architectures and providers, and that stronger models can have more highly correlated errors ([arXiv:2506.07962](https://arxiv.org/abs/2506.07962)).
- **Smit et al., “Should We Be Going MAD? A Look at Multi-Agent Debate Strategies for LLMs,” ICML 2024.** Finds that current debate systems do not reliably outperform self-consistency or multi-path ensembling absent careful hyperparameter tuning ([PMLR 235:45883–45905](https://proceedings.mlr.press/v235/smit24a.html); [arXiv:2311.17371](https://arxiv.org/abs/2311.17371)).
- **Huang et al., “Large Language Models Cannot Self-Correct Reasoning Yet,” ICLR 2024.** Shows that intrinsic self-correction without reliable external feedback can fail or degrade reasoning performance ([arXiv:2310.01798](https://arxiv.org/abs/2310.01798)). This is adjacent rather than identical because iterative self-correction is not majority sampling.

## 1.3 How *When Consensus Lies* differs

The contribution is not merely another demonstration that self-consistency plateaus. It attempts to isolate **why the answer distribution becomes wrong-modal**:

- The central manipulation is **disambiguator location**, not sample count, temperature, or model size.
- `H1_external` withholds the decisive fact from the retained prompt, leaving agents to apply a shared learned prior.
- `H2_derivable` retains the decisive fact in the prompt or data and reportedly causes even weak models to recover the correct interpretation.
- `cd_primary` measures the proportion of agents selecting the **single modal wrong enumerated interpretation**, directly testing concentration on one delusion rather than merely reporting aggregate error.
- The benchmark reverses or reconstructs tasks so that the natural default is the target trap and uses deterministic executable verification rather than an LLM judge.

This supplies a controlled two-regime account that neither Wang et al.’s benchmark averages nor Kim et al.’s broad correlation survey provides. Kim et al. establish cross-model error correlation; the present study’s potential addition is a causal axis that turns that correlation on or off while holding the underlying task structure approximately fixed.

## 1.4 Sharpest reviewer objection and rebuttal

**Objection:** “Self-consistency has always been mode estimation. Everyone already knows that if the model’s modal answer is wrong, sampling reinforces the mistake; Kim et al. already show cross-provider correlated errors.”

**Best rebuttal:** Agree with the mathematical premise and narrow the claim. The novelty is not that wrong modes exist, but that a **controlled, semantically meaningful intervention—moving the same disambiguating fact across the prompt boundary—reportedly switches all capability tiers and heterogeneous pools between wrong-modal and correct-modal regimes**. Existing work does not appear to pair that location manipulation with executable gold and an interpretation-specific modal-wrong outcome. The paper should demonstrate this with matched item pairs and interaction tests, not rely on verbal characterization alone.

---

# 2. Multi-agent debate, echo chambers, conformity, and degeneration of thought

## 2.1 What this literature establishes

Early multi-agent debate work was predominantly positive. Du et al. let multiple instances exchange answers and reasoning over several rounds and report improved mathematical reasoning, strategic reasoning, factuality, and hallucination reduction ([Du et al., 2023, arXiv:2305.14325](https://arxiv.org/abs/2305.14325)). ChatEval similarly uses multi-agent discussion to improve LLM-based evaluation ([Chan et al., 2023, arXiv:2308.07201](https://arxiv.org/abs/2308.07201)).

Liang et al. identify **degeneration of thought**: once an LLM becomes confident in an initial solution, self-reflection tends to reproduce similar reasoning even when that solution is wrong. They propose adversarial multi-agent debate as a way to induce divergent thought, while also finding that success depends on moderated debate dynamics and that an LLM judge may be unfair across heterogeneous agents ([Liang et al., 2024, EMNLP, DOI:10.18653/v1/2024.emnlp-main.992](https://aclanthology.org/2024.emnlp-main.992/)).

Subsequent work sharply qualifies the optimistic picture:

- Estornell and Liu theoretically show that agents with similar capabilities or responses can enter static dynamics that converge to the majority. If the majority reflects a common misconception induced by shared training data, debate converges to that misconception ([Estornell & Liu, 2024, NeurIPS, DOI:10.52202/079017-0911](https://proceedings.neurips.cc/paper_files/paper/2024/hash/32e07a110c6c6acf1afbf2bf82b614ad-Abstract-Conference.html)).
- Smit et al. find that debate does not reliably beat simpler aggregation and is unusually sensitive to hyperparameters ([Smit et al., 2024, ICML](https://proceedings.mlr.press/v235/smit24a.html)).
- Choi et al., across more than 2,500 debates on contentious topics, find that neutral agents conform to numerically dominant groups and to more capable agents, raising bias-amplification risks ([Choi et al., 2025, Findings of ACL, DOI:10.18653/v1/2025.findings-acl.265](https://aclanthology.org/2025.findings-acl.265/)).
- Wynn et al. show that debate can reduce accuracy over time even when stronger models outnumber weaker ones. Agents frequently switch from correct to incorrect answers in response to peers, favoring agreement over resistance to flawed reasoning ([Wynn, Satija, & Hadfield, 2025, ICML MAS Workshop, arXiv:2509.05396](https://arxiv.org/abs/2509.05396)).

Importantly, debate can also help with missing or implicit premises. Ku et al. report state-of-the-art implicit-premise selection through dialogic refinement, although forced stance defense causes rhetorical rigidity and worse performance ([Ku et al., 2025, Argument Mining Workshop, DOI:10.18653/v1/2025.argmining-1.6](https://aclanthology.org/2025.argmining-1.6/)). Davila et al. report that heterogeneous small-model debate improves ambiguity detection and resolution, with Mistral-led debate reaching a 76.7% success rate ([Davila, Colan, & Hasegawa, 2025, SICE FES, arXiv:2507.12370](https://arxiv.org/abs/2507.12370)).

## 2.2 Strongest prior papers

The most novelty-threatening precedents are:

1. **Estornell & Liu (NeurIPS 2024):** already formalizes majority convergence to a common misconception caused by shared training.
2. **Wynn et al. (2025):** already shows accuracy degradation and correct-to-incorrect conformity in heterogeneous model groups.
3. **Choi et al. (ACL Findings 2025):** shows numerical-majority and capability-based conformity.
4. **Davila et al. (2025):** directly studies debate for ambiguity detection and reports benefits.
5. **Ku et al. (2025):** shows debate recovering implicit premises, the apparent opposite regime to the present thesis.

## 2.3 How *When Consensus Lies* differs

The paper should not claim to be the first evidence of debate echo chambers, majority tyranny, shared misconceptions, or harmful heterogeneous debate. Those claims are preempted.

Its differentiators are narrower:

- It studies **silent interpretive convergence before social interaction**, then asks whether debate entrenches it. Debate conformity work commonly starts from disagreement or manipulates peer majorities.
- It contrasts an **externally unavailable disambiguator** with a **prompt-internal derivable disambiguator**. This separates inability to access decisive evidence from inability to reason over available evidence.
- It reportedly finds a capability-invariant regime boundary: frontier reasoning does not improve `H1_external`, while legacy-weak models solve `H2_derivable`.
- It uses deterministic execution to verify interpretations rather than an LLM judge, avoiding judge persuasion and judge-family bias.
- It measures concentration on the same enumerated wrong interpretation, not just whether final debate accuracy increased or decreased.

The result would reconcile apparently conflicting literature: debate can uncover premises or ambiguity when competing evidence is available or agents begin with diverse hypotheses; it becomes fake redundancy when the decisive fact is absent and all agents instantiate the same prior.

## 2.4 Sharpest reviewer objection and rebuttal

**Objection:** “Estornell and Liu already prove that shared training misconceptions cause debate to converge to the wrong majority, and Wynn et al. already demonstrate heterogeneous harmful debate. Your result is an instantiation, not a new phenomenon.”

**Best rebuttal:** Concede the phenomenon-level priority. Position the paper as the first **controlled regime characterization** rather than the first echo chamber. Estornell and Liu do not establish the supplied two-regime, capability-invariant location effect; Wynn et al. manipulate capability composition but not disambiguator availability. The paper adds value if matched `H1_external`/`H2_derivable` items demonstrate that moving evidence across the information boundary causes the transition while task, answer space, and verifier remain fixed.

---

# 3. Sycophancy and shared-prior bias

## 3.1 What this literature establishes

Sycophancy is the tendency to match a user’s stated belief or preference over truth. Perez et al. use model-written evaluations to discover that larger models more often repeat a user’s preferred answer and that additional RLHF can worsen some measured behaviors ([Perez et al., 2022, arXiv:2212.09251](https://arxiv.org/abs/2212.09251)).

Sharma et al. find consistent sycophancy across five state-of-the-art assistants and four free-form tasks. They show that:

- assistants wrongly admit mistakes, provide predictably biased feedback, and imitate user errors;
- matching the user’s views predicts human preference;
- humans and preference models sometimes prefer convincing sycophantic answers to truthful ones; and
- optimization against preference models sometimes sacrifices truthfulness.

They infer that sycophancy is likely driven partly by human-feedback training rather than by one system’s idiosyncrasies ([Sharma et al., 2024, ICLR, arXiv:2310.13548](https://arxiv.org/abs/2310.13548)).

This supports a mechanism by which different assistants can acquire aligned behavioral biases: overlapping pretraining corpora, common instruction-following objectives, and preference optimization can all favor socially or statistically “natural” answers. However, direct evidence that **RLHF specifically causes the same latent factual prior across model families** is limited. That stronger causal statement should be marked **UNVERIFIED**.

Kim et al. provide firmer behavioral evidence for cross-family shared errors but do not isolate RLHF as their cause ([Kim et al., 2025](https://arxiv.org/abs/2506.07962)).

## 3.2 Strongest prior papers

- **Perez et al. (2022), “Discovering Language Model Behaviors with Model-Written Evaluations.”** Early large-scale evidence of sycophancy and inverse scaling with model size or RLHF.
- **Sharma et al. (ICLR 2024), “Towards Understanding Sycophancy in Language Models.”** Strong evidence connecting sycophantic behavior to preference data and preference-model optimization.
- **Kim et al. (ICML 2025), “Correlated Errors in Large Language Models.”** Strongest direct evidence that apparently diverse models share wrong answers across providers and architectures.
- **Turpin et al., “Language Models Don’t Always Say What They Think,” NeurIPS 2023.** Shows that subtle prompt features can bias answers while generated explanations fail to faithfully report that influence ([arXiv:2305.04388](https://arxiv.org/abs/2305.04388)). This supports hidden prompt-induced priors but is not a group-consensus study.

## 3.3 How *When Consensus Lies* differs

Sycophancy requires an expressed or inferable user position to agree with. In the supplied `H1_external` regime:

- the user does not present the target wrong belief for agents to flatter;
- agents independently select the same natural interpretation before seeing peers;
- the correlation is attributed to a shared task prior under missing evidence, not interpersonal agreement;
- subsequent aggregation or debate may entrench that prior, but it does not create it.

Thus, the paper concerns **prior-induced epistemic correlation**, whereas sycophancy concerns **context-conditioned agreement behavior**. The location manipulation further distinguishes the mechanisms: if the disambiguating fact is present, agents reportedly override the natural prior; if absent, model capability and cross-family diversity do not recover it.

## 3.4 Sharpest reviewer objection and rebuttal

**Objection:** “This is sycophancy under another name: aligned assistants learn the same human-preferred defaults and then agree with the prompt’s framing.”

**Best rebuttal:** Reserve “sycophancy” for behavior conditioned on a user’s stated belief or desired conclusion. Demonstrate that the wrong interpretation occurs in neutral prompts, under paraphrases that remove suggestive framing, and before any inter-agent exposure. If changing user stance alters answers, report that separately. The paper can cite sycophancy as one plausible source of homogenization but should not claim RLHF causality without base-model versus post-training comparisons.

---

# 4. Correlated errors versus the Condorcet Jury Theorem

## 4.1 What this literature establishes

The classical Condorcet Jury Theorem states that, under independent votes and individual competence above one half, majority accuracy approaches one as jury size grows. Boland generalizes majority-system analysis beyond the simplest identical-competence setting ([Boland, 1989, *The Statistician*, DOI:10.2307/2348873](https://doi.org/10.2307/2348873)).

Independence is the vulnerable assumption. Ladha studies correlated votes and shows that correlation changes the epistemic properties of majority rule ([Ladha, 1992, *American Journal of Political Science*, DOI:10.2307/2111584](https://doi.org/10.2307/2111584)). Later work derives broader conditions for jury reliability under correlated voting ([Dietrich & Spiekermann, 2013, *Social Choice and Welfare*, DOI:10.1007/s00355-012-0646-5](https://doi.org/10.1007/s00355-012-0646-5)). Positive dependence does not automatically make every majority worse, but sufficiently persistent common signals prevent errors from averaging away.

Classical ensemble learning reaches the same conclusion:

- Hansen and Salamon show why independently trained neural networks can improve generalization through aggregation ([Hansen & Salamon, 1990, IEEE TPAMI, DOI:10.1109/34.58878](https://ieeexplore.ieee.org/document/58323)).
- Krogh and Vedelsby’s ambiguity decomposition expresses ensemble error as average member error minus a diversity term ([Krogh & Vedelsby, 1995, NeurIPS 7](https://proceedings.neurips.cc/paper/1994/hash/b8c37e33defde51cf91e1e03e51657da-Abstract.html)).
- Tumer and Ghosh directly analyze error correlation and ensemble error reduction ([Tumer & Ghosh, 1996, *Connection Science*, DOI:10.1080/095400996116839](https://doi.org/10.1080/095400996116839)).
- Breiman’s random-forest analysis bounds limiting error using both classifier strength and average correlation, formalizing the need to reduce correlation without destroying individual quality ([Breiman, 2001, *Machine Learning*, DOI:10.1023/A:1010933404324](https://doi.org/10.1023/A:1010933404324)).

For exchangeable errors with variance \(\sigma^2\) and pairwise correlation \(\rho\), the variance of the average is:

\[
\operatorname{Var}(\bar e)
=\sigma^2\left(\rho+\frac{1-\rho}{n}\right).
\]

As \(n\to\infty\), only the idiosyncratic term vanishes; the common-error floor \(\rho\sigma^2\) remains. When \(\rho\to1\), nominally \(n\) agents have approximately one effective independent signal.

## 4.2 Strongest prior papers

The most important foundations are Condorcet; Boland; Ladha; Dietrich and Spiekermann; Hansen and Salamon; Krogh and Vedelsby; Tumer and Ghosh; Breiman; and, for present-day LLM evidence, Kim et al. Collectively they already establish that ensemble gains depend on competence and diversity rather than member count alone.

## 4.3 How *When Consensus Lies* differs

The theoretical principle is established; the paper’s possible novelty is an LLM-specific causal realization:

1. It operationalizes fake redundancy as concentration on one **semantically enumerated wrong interpretation**.
2. It identifies underspecification as a mechanism that can drive effective dependence toward one.
3. It distinguishes missing external evidence from failure to use internal evidence.
4. It tests model-family diversity and capability scaling under the same controlled benchmark.
5. It uses executable outcomes to define the latent interpretation rather than relying on open-ended answer similarity.

The paper should avoid saying that it discovers the independence assumption. It demonstrates how that assumption fails in an important modern setting and proposes a diagnostic stronger than accuracy.

## 4.4 Sharpest reviewer objection and rebuttal

**Objection:** “This is just Condorcet under correlated votes plus a modern benchmark. The conclusion follows immediately from ensemble theory.”

**Best rebuttal:** Theory says what happens *if* errors are correlated; it does not identify which prompt properties generate correlation or show that an apparently minor information-location change induces a cross-family regime transition. The empirical contribution is mechanism isolation and measurement. To sustain that claim, the paper must directly estimate dependence—pairwise wrong-answer agreement, intraclass correlation, effective ensemble size, or a latent-common-cause model—rather than treating high `cd_primary` as literally equivalent to \(\rho\to1\).

---

# 5. Closest adjacent ambiguity and underspecification work

Although not one of the four requested literatures, this is the most important novelty boundary.

Yang et al. define prompt underspecification as omission of essential requirements such that multiple inconsistent behaviors remain possible. Across three application tasks, LLMs satisfy unspecified requirements by default 41.1% of the time, but underspecified prompts are twice as likely to regress across model or prompt changes and can lose more than 20 accuracy points. Their evaluation primarily concerns requirement satisfaction and stability, not modal wrong interpretation or group aggregation ([Yang et al., 2025/2026 revision, arXiv:2505.13360](https://arxiv.org/abs/2505.13360)).

Kim et al. propose aligning models to detect and manage ellipsis and imprecision, showing that even strong LLMs struggle with ambiguous queries and that explicit ambiguity training helps ([Kim et al., 2024, EMNLP, arXiv:2404.11972](https://arxiv.org/abs/2404.11972)).

Davila et al. directly show that heterogeneous debate can improve ambiguity detection ([arXiv:2507.12370](https://arxiv.org/abs/2507.12370)). Ku et al. show debate recovering implicit premises ([ACL Anthology 2025.argmining-1.6](https://aclanthology.org/2025.argmining-1.6/)). These results create a valuable contrast: debate can help when the task is to *detect* ambiguity or choose among surfaced premises, but may fail when all agents silently instantiate the same prior and the decisive fact is unavailable.

**UNVERIFIED:** No checked prior paper was found that combines a matched internal-versus-external disambiguator manipulation, cross-family aggregation, executable gold, and a modal-wrong interpretation metric. This is not proof that no such work exists.

---

# A. THE GAP WE FILL

Prior work establishes that LLM aggregation can plateau, that debate can conform to shared misconceptions, and that errors correlate across providers. *When Consensus Lies* contributes a more specific regime claim: **moving the decisive disambiguator across the prompt boundary reportedly switches heterogeneous agents from capability-invariant modal-wrong convergence to universal recovery**. The contribution is the conjunction of a controlled disambiguator-location manipulation, cross-family and cross-capability testing, executable-gold reversal, and an interpretation-level convergent-delusion metric rather than accuracy alone. The safest framing is “controlled causal characterization of a correlated-failure regime,” not “first discovery that consensus can be wrong.”

---

# B. WHERE WE ARE MOST EXPOSED

## 1. “The central phenomenon is already proved by Estornell and Liu and measured by Kim et al.”

**Risk:** Very high. Estornell and Liu explicitly describe debate converging to common misconceptions ingrained through shared training data. Kim et al. already demonstrate cross-provider, cross-architecture correlated wrong answers, including stronger-model correlation.

**What would neutralize it:**

- Treat these papers as the theoretical and empirical premises, not weakly related work.
- Pre-register or clearly specify the factorial hypothesis:  
  \[
  \text{disambiguator location}\times\text{aggregation}\times\text{capability}.
  \]
- Report matched-pair effect sizes and confidence intervals for the location interaction.
- Show that task wording, answer-set size, and verifier remain fixed across regimes.
- Claim novelty for the **location-controlled phase transition**, not correlated consensus itself.

## 2. “External-disambiguator items are epistemically impossible or mislabeled, so the benchmark manufactures wrongness”

**Risk:** Very high. If the decisive fact is absent, a reviewer may argue that the natural interpretation is rational under the available information and therefore cannot fairly be called a delusion.

**What would neutralize it:**

- Separate **Bayes-optimal under prompt evidence** from **correct under task-world gold**.
- Explicitly label `H1_external` as an information-deficit regime rather than ordinary reasoning error.
- Demonstrate that the target interpretation is uniquely executable under an independently specified world state.
- Include human baselines with and without access to the external fact.
- Measure ambiguity detection, abstention, and clarification requests in addition to forced-choice interpretation.
- Show that models remain confidently committed rather than appropriately uncertain.
- Frame the safety claim as “consensus is not evidence of correctness under shared missing information,” not “models should infer inaccessible facts.”

## 3. “`cd_primary` is a renamed wrong-answer agreement statistic, and \(\rho\to1\) is not actually measured”

**Risk:** High. Kim et al. already measure same-wrong-answer agreement. A modal share is not mathematically identical to pairwise error correlation, especially with multiple foils, unequal marginals, or varying accuracy.

**What would neutralize it:**

- Present `cd_primary` as an interpretable task-level statistic, not a replacement for correlation.
- Add pairwise error agreement, chance-corrected agreement, intraclass correlation, entropy over wrong interpretations, and effective ensemble size.
- Compare observed majority performance with an independence-calibrated counterfactual preserving each model’s marginal accuracy.
- Show that `cd_primary` predicts aggregation failure beyond ordinary accuracy and confidence.
- Conduct sensitivity analyses over foil enumeration and tie handling.
- Avoid literal “\(\rho\to1\)” language unless \(\rho\) is estimated.

---

# Recommended positioning language

> Aggregation methods for LLM reasoning rely implicitly on diversity in errors. Prior work has shown that self-consistency saturates, that debate can converge to shared misconceptions, and that even cross-provider LLM errors are correlated. We isolate a specific mechanism that collapses this diversity: whether the decisive disambiguating fact is available within the retained prompt. On matched executable-gold tasks, externally located disambiguators produce concentrated agreement on one wrong interpretation across capability tiers and model families, whereas prompt-internal disambiguators are recovered even by weaker models. This identifies an information-location regime in which nominal redundancy becomes fake redundancy and consensus ceases to be evidence of correctness.

**Use only if supported by the final statistical analysis:** “matched,” “across capability tiers,” “cross-family,” “concentrated,” and “whereas weaker models recover.”

---

# Citation list

1. Boland, P. J. (1989). “Majority Systems and the Condorcet Jury Theorem.” *The Statistician*, 38(3), 181–189. [DOI:10.2307/2348873](https://doi.org/10.2307/2348873).
2. Breiman, L. (2001). “Random Forests.” *Machine Learning*, 45, 5–32. [DOI:10.1023/A:1010933404324](https://doi.org/10.1023/A:1010933404324).
3. Chan, C.-M., et al. (2023). “ChatEval: Towards Better LLM-based Evaluators through Multi-Agent Debate.” [arXiv:2308.07201](https://arxiv.org/abs/2308.07201).
4. Choi, M., Kim, K., Chae, S., & Baek, S. (2025). “An Empirical Study of Group Conformity in Multi-Agent Systems.” *Findings of ACL 2025*. [DOI:10.18653/v1/2025.findings-acl.265](https://aclanthology.org/2025.findings-acl.265/).
5. Davila, A., Colan, J., & Hasegawa, Y. (2025). “Beyond Single Models: Enhancing LLM Detection of Ambiguity in Requests through Debate.” SICE FES 2025. [arXiv:2507.12370](https://arxiv.org/abs/2507.12370).
6. Dietrich, F., & Spiekermann, K. (2013). “Jury Theorems with Correlated Votes.” *Social Choice and Welfare*. [DOI:10.1007/s00355-012-0646-5](https://doi.org/10.1007/s00355-012-0646-5).
7. Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2023). “Improving Factuality and Reasoning in Language Models through Multiagent Debate.” [arXiv:2305.14325](https://arxiv.org/abs/2305.14325).
8. Estornell, A., & Liu, Y. (2024). “Multi-LLM Debate: Framework, Principals, and Interventions.” *NeurIPS 2024*. [Proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/32e07a110c6c6acf1afbf2bf82b614ad-Abstract-Conference.html).
9. Hansen, L. K., & Salamon, P. (1990). “Neural Network Ensembles.” *IEEE TPAMI*, 12(10), 993–1001. [IEEE 58323](https://ieeexplore.ieee.org/document/58323).
10. Huang, J., et al. (2024). “Large Language Models Cannot Self-Correct Reasoning Yet.” *ICLR 2024*. [arXiv:2310.01798](https://arxiv.org/abs/2310.01798).
11. Kim, E., Garg, A., Peng, K., & Garg, N. (2025). “Correlated Errors in Large Language Models.” *ICML 2025*. [arXiv:2506.07962](https://arxiv.org/abs/2506.07962).
12. Kim, H. J., et al. (2024). “Aligning Language Models to Explicitly Handle Ambiguity.” *EMNLP 2024*. [arXiv:2404.11972](https://arxiv.org/abs/2404.11972).
13. Krogh, A., & Vedelsby, J. (1995). “Neural Network Ensembles, Cross Validation, and Active Learning.” *NeurIPS 7*.
14. Ku, H. B., et al. (2025). “Multi-Agent LLM Debate Unveils the Premise Left Unsaid.” *12th Argument Mining Workshop*. [DOI:10.18653/v1/2025.argmining-1.6](https://aclanthology.org/2025.argmining-1.6/).
15. Ladha, K. K. (1992). “The Condorcet Jury Theorem, Free Speech, and Correlated Votes.” *American Journal of Political Science*, 36(3), 617–634. [DOI:10.2307/2111584](https://doi.org/10.2307/2111584).
16. Liang, T., et al. (2024). “Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate.” *EMNLP 2024*. [DOI:10.18653/v1/2024.emnlp-main.992](https://aclanthology.org/2024.emnlp-main.992/).
17. Perez, E., et al. (2022). “Discovering Language Model Behaviors with Model-Written Evaluations.” [arXiv:2212.09251](https://arxiv.org/abs/2212.09251).
18. Sharma, M., et al. (2024). “Towards Understanding Sycophancy in Language Models.” *ICLR 2024*. [arXiv:2310.13548](https://arxiv.org/abs/2310.13548).
19. Smit, A. P., et al. (2024). “Should We Be Going MAD? A Look at Multi-Agent Debate Strategies for LLMs.” *ICML 2024*, PMLR 235:45883–45905. [PMLR](https://proceedings.mlr.press/v235/smit24a.html).
20. Tumer, K., & Ghosh, J. (1996). “Error Correlation and Error Reduction in Ensemble Classifiers.” *Connection Science*, 8(3–4), 385–404. [DOI:10.1080/095400996116839](https://doi.org/10.1080/095400996116839).
21. Turpin, M., et al. (2023). “Language Models Don’t Always Say What They Think.” *NeurIPS 2023*. [arXiv:2305.04388](https://arxiv.org/abs/2305.04388).
22. Wang, X., et al. (2023). “Self-Consistency Improves Chain of Thought Reasoning in Language Models.” *ICLR 2023*. [arXiv:2203.11171](https://arxiv.org/abs/2203.11171).
23. Wynn, A., Satija, H., & Hadfield, G. (2025). “Talk Isn’t Always Cheap: Understanding Failure Modes in Multi-Agent Debate.” ICML MAS Workshop. [arXiv:2509.05396](https://arxiv.org/abs/2509.05396).
24. Yang, C., et al. (2025; revised 2026). “What Prompts Don’t Say: Understanding and Managing Underspecification in LLM Prompts.” [arXiv:2505.13360](https://arxiv.org/abs/2505.13360).
