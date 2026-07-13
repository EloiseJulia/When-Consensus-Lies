**Silent Failure of Multi-Agent Redundancy under Underspecified Prompts**

**From Correlated Errors to False High-Confidence Consensus — A Critical Synthesis of Three AI Research Reports**

*Meta-review / cross-verification and best-of integrated report (targeting CHI · IUI · CSCW · ACL · NeurIPS)*

Hard constraint: every step is realizable purely in software/code — no human-subject psychology lab study, no hardware; LLM-simulated users may replace human participants.

Table of Contents

1\. Executive Summary (TL;DR)

**One-line core judgment:** When the prompt is underspecified, the business intent is not fully stated, and no unique ground truth exists in reality, the “wisdom-of-the-crowd” paradigm of “spin up many sessions / many agents + a review agent + majority voting” does not merely fail — it amplifies the **correlated errors** driven by shared priors + sycophancy into a **high-confidence yet wrong consensus**, with neither human nor AI receiving any error signal — a silent failure.

**The hypothesis holds, but must be narrowed to a falsifiable version.** This synthesis, after independent web verification, confirms: mathematically, redundant aggregation only suppresses variance-type error, not bias-type error; when shared pretraining priors and sycophancy push the inter-agent error correlation ρ significantly positive, adding agents yields negative returns on collective accuracy. However — **adopting the more rigorous stance of reports B and C:** the “phase transition” is not a universal theorem but an empirical crossover depending on n, single-agent accuracy p, and the joint distribution; it should be delivered as a measurable, pre-registered contribution rather than a claimed universal threshold.

Three causal links already supported by evidence (all verified)

- **Underspecification → filling gaps with priors:** Yang et al., “What Prompts Don’t Say” (ACL Findings 2026) shows LLMs infer unspecified requirements by default 41.1% of the time, but this is fragile — roughly 2× the regression rate of specified requirements across model/prompt changes, with individual drops exceeding 20 points.

- **Shared priors + sycophancy → correlated errors:** “Ask don’t tell” (arXiv:2602.23971, UK AISI) shows non-question form, epistemic certainty, and first-person framing monotonically amplify sycophancy; SYCON Bench (EMNLP 2025) finds across 17 LLMs that alignment tuning amplifies conforming behavior.

- **Voting/debate → consensus-forming rather than error-correction:** M3MAD-Bench (arXiv:2601.02854) finds 65% of MAD failures are Collective Delusion (agents mutually reinforcing a wrong assumption); Byerly & Khashabi (TACL 2026) directly show self-consistency “amplifies rather than cancels” correlated errors.

> **\[Synthesizer’s judgment\]** The evidence for each link exists independently, but to date **no single work** manipulates “degree of prompt underspecification” as an independent variable while simultaneously measuring “rising inter-agent ρ,” “the inversion of consensus confidence vs. correctness,” and “whether a human / simulated user can perceive the silent failure.” This is the irreplaceable moat of the project.

**Proposed title (main line, system-level claim):** When Consensus Lies: Ground-Truth-Free Detection of Silent Consensus Failures under Underspecified Prompts.

> **\[Claim–method alignment · review-round-2 correction\]** The original proposed title contained “Human–Multi-Agent Collaboration,” which conflicts with the pure-software hard constraint — simulated users cannot substitute for human-psychology conclusions (see the empirical counter-evidence in “Lost in Simulation,” arXiv:2601.17087). The main line is therefore narrowed to a system/detection-level claim; “human observability / appropriate reliance” is always stated as an effect on a “simulated decision-maker,” never as a psychological claim about real humans. The Human-framed strong version is reserved for the CHI packaging with explicit simulated-user caveats (see 8.4, 8.5).

2\. Problem Definition & Formalization

2.1 Underspecification and Ambiguity

**Underspecification** is defined as “omitting essential requirements such that multiple valid but inconsistent behaviors are all admissible” (Yang et al., 2026); ambiguity leans more toward “competing interpretations.” Both force the model to complete user intent with a prior, thereby triggering the **same correlated interpretation default** across agents. CLAMBER (ACL 2024) further shows LLMs have limited ability to recognize ambiguity, and CoT / few-shot may even worsen overconfidence.

2.2 Symbolic notation: ρ, accuracy, and confidence

- **n**: number of concurrent agents / spun-up sessions.

- **p**: the accuracy of a single agent in decoding the user’s true-but-unstated intent.

- **Interpretation-label set (primary construct):** I = {I₀, I₁, …, I_m, I⊥} — I₀ = the user’s true hidden intent, I₁…I_m = prior-biased interpretations, I⊥ = degenerate/noise errors. Each agent is assigned a label L_i ∈ I (clustering handle = executable signals: unit-test error type / traceback / deterministic numeric result, not an LLM judge).

- **Convergent-delusion (the project’s primary metric):** false-consensus rate = the fraction of items where a majority of agents land on the same I_k (k≠0); or the categorical association (Cramér’s V) of labels within the subset of wrong agents. Only “colluding on the same wrong interpretation” counts.

- **Binary marginal correlation (secondary, theory-bridging only):** E_i = 1\[ŷ_i ≠ y\*\], ρ_ij = corr(E_i, E_j) (phi). Used only to connect to the CJT / Tumer–Ghosh theorems; explicitly labeled “marginal error correlation.”

- **Consensus accuracy A_maj = P( majority(ŷ₁,…,ŷ_n) = y\* )**. Under the classical independent, p\>0.5 assumption, A_maj\>p and → 1 as n→∞; once errors are positively correlated, this property fails.

> **\[Why the distinction is mandatory · review-round-3 point 2 (the deepest hit)\]** Binary “both wrong” miscounts “each wrong differently” as positive correlation, so what it measures is task difficulty, not consensus bias. Example: Agent A errs on natural-calendar Q1 (type X), Agent B crashes on a syntax parse (type Y); binary records ρ↑, yet the two did not converge on the same wrong assumption and do not constitute Collective Delusion. Hence the primary construct uses an interpretation-label categorical variable to separate “independently wrong” from “convergently wrong” mathematically.

2.3 Theoretical foundation (I): Condorcet Jury Theorem with correlation

The classical CJT requires independent votes and p\>0.5. Ladha (1992) notes the independence assumption is unrealistic — common information, communication, and opinion leaders all produce correlated votes. Kaniovski (and Kaniovski & Zaigraev) prove that in a homogeneous jury **negative correlation raises, and positive correlation lowers, collective accuracy**, and under positive correlation enlarging the jury can be harmful within a certain range.

> **\[Conflict adjudication · does a universal threshold ρ\* exist?\]** Report A states ρ\* almost as a derived “negative-return phase-transition law”; reports B and C point out this is not rigorous. This synthesis **sides with B/C (confidence 90):** Kaniovski shows that individual accuracies plus pairwise correlations do not uniquely determine the joint distribution, so no closed-form universal ρ\* exists. The correct framing treats ρ\* as an **empirical crossover depending on n, p, and the joint distribution**, delivered as a “pre-registered hypothesis + measured phase diagram,” not a claimed universal constant.

2.4 Theoretical foundation (II): the bias–variance decomposition of ensembles

Following Tumer & Ghosh (1996) on correlated error, the ensemble added error is approximately E_ens ≈ E_single · \[ (1 + ρ(n−1)) / n \].

- **When ρ = 0:** E_ens → E_single / n — redundancy fully reduces variance (ideal case).

- **When ρ → 1:** the bracket → 1, E_ens → E_single — the **effective sample size degenerates to 1**, so extra sampling yields nothing. This is the mathematical statement of “redundancy suppresses variance, not bias.”

Mechanistic implication: underspecification produces systematic understanding bias. When shared pretraining and RLHF alignment push ρ high, aggregation not only fails to correct but pathologically inflates the internal confidence of a biased conclusion by eliminating minority variance.

2.5 Three-layer confidence and the formalization of “silent failure”

This synthesis adopts report B’s three-layer confidence decomposition (fusing metrics from A and C):

- **(a) verbalized confidence**: the model’s self-stated certainty; **(b) vote margin / consensus strength**: agreement level; **(c) calibration confidence**: confidence–correctness alignment (ECE, confidence–accuracy slope).

- **Optional internal signal:** for open-weight models, use TSLD (Target Set Logit Difference, from “Wired for Overconfidence,” arXiv:2604.01457, verified as a real metric) to quantify internal false high-confidence; C’s ADVICE / AFCE offer answer-grounded calibration refinements.

**Silent Failure** = an operating regime satisfying all three conditions simultaneously: (1) **objective failure** (output fundamentally departs from the user’s true intent); (2) **high-confidence consensus** (agreement and all three confidence layers are high); (3) **normal trajectory** (no loops, no tool crashes, no semantic drift — even the verifier approves). Neither human nor AI receives a correction signal, forming an “unknown-unknowns” trap.

3\. Literature Review (merged comparison table)

The table below is the union of the literature clusters from all three reports (de-duplicated, grouped by evidence cluster), each annotated with method/setting, whether it explicitly treats error correlation ρ, core conclusion, and limitation. Credibility grades are in Section 9.

| **Method / paper** | **Setting** | **Treats ρ?** | **Core conclusion** | **Limitation** |
|:---|:---|:---|:---|:---|
| Self-Consistency (Wang et al., ICLR 2023) | short-chain reasoning | No (implicitly assumes path independence) | sample multiple paths, take most consistent; GSM8K +17.9% | assumes a unique answer; no multi-interpretation / underspecification |
| SC Falls Short (Byerly & Khashabi, TACL 2026) | long-context QA | Yes (position bias induces correlated error) | in long context SC “amplifies” rather than cancels correlated error, degrading accuracy — the most direct mechanistic precedent | targets position bias, not prompt underspecification; ρ not quantified |
| Multi-Agent Debate (Du et al., ICML 2024) | math / factual reasoning | Indirect (depends on diversity) | cross-model debate improves factuality, reduces hallucination | efficacy premised on low correlation / high diversity; requires GT |
| M3MAD-Bench (Ao Li et al., 2026, 2601.02854) | 9 models · 5 domains · multimodal | Yes (Collective Delusion 65%) | adversarial Div-MAD −12.8%; 65% of errors are collective delusion, 17% selection failure | does not manipulate ambiguity strength; ρ unmeasured; tasks have GT |
| ICLR 2025 Blogpost | 5 MAD frameworks · 9 benchmarks | Indirect | SC (MMLU 82.13%) often beats MAD variants (67.9–80.4%); more rounds/agents not reliably better | does not consider underspecification |
| iMAD (Fan et al., AAAI 2026 Oral, 2511.11306) | 6 (V)QA | Indirect (hesitation cues) | MAD truly corrects only 5–19%; selective triggering saves 92% tokens, +13.5% | solves “when to trigger,” not “is the consensus false” |
| Huang et al. (ICLR 2024) | self-correction | Indirect (generator–verifier shared blind spot) | without external feedback self-correction is hard, even degrades | does not study multi-agent settings |
| Self-Preference Bias (2410.21819) | LLM-as-judge | Indirect (shared low-perplexity preference) | the judge prefers low-perplexity / same-family style outputs | weakens verifier independence; ρ unmeasured |
| SYCON Bench (Hong et al., EMNLP 2025, 2505.23840) | multi-turn sycophancy · 17 LLMs | Yes (conformity = correlation trigger) | alignment amplifies conformity; third-person cuts −63.8% in debate | single agent, not multi-agent aggregation |
| Ask don’t tell (Dubois et al., 2026, 2602.23971) | sycophancy trigger / mitigation | No (provides the trigger) | non-question / high certainty / first-person amplify sycophancy; rewriting as a question reduces it | single agent; not connected to consensus failure |
| Wired for Overconfidence (2604.01457) | calibration / interpretability | No | LLMs are “confidently wrong”; TSLD quantifies false high-confidence and enables inference-time recalibration | single-model level; no multi-agent amplification |
| Yang, “What Prompts Don’t Say” (ACL Findings 2026, 2505.13360) | prompt underspecification | No (no multi-agent study) | 41.1% default inference but fragile; ~2× regression rate, some \>20% drops | single-agent analysis |
| Detecting Silent Failures (Pathak et al., IBM, 2511.04032) | multi-agent trajectory anomaly | No (structural anomaly, not semantic consensus) | defines drift/cycles/missing; XGBoost 98%, SVDD 96% | does not detect “consensus looks normal but interpretation is wrong” |
| Schoeffer et al. (CHI 2024) / TRAP (CHI’25 Wksp) | human over-reliance | No (human-side dependence) | explanations don’t help distinguish right/wrong AI advice; shift to complementarity | must fold “consensus = confidence” into HCI design |
| CJT with correlated votes & ensemble error (Ladha’92; Kaniovski; Tumer&Ghosh’96) | probability / ensemble theory | Yes (core variable) | positive correlation lowers collective accuracy; ensemble gain depends on reducing correlation | pure theory; needs porting to generative agents empirically |

4\. Mechanism: Underspecification → Correlated Errors → False High-Confidence Consensus

The evidence for each of the five links below is independently verified; each link clearly separates “sourced fact” from “synthesizer inference.”

> **\[Claim boundary · pragmatics clarification · review-round-3 point 4\]** The project does NOT claim that “using a prior to complete an underspecified context” is itself a bug — under Gricean / Bayesian pragmatics that is rational, near-optimal behavior (“Q1 = calendar quarter” is a learned statistical consensus). The failure is not in “choosing a prior,” but in two things: (a) silently committing on consequential ambiguity (interpretations with materially different outcomes) without flagging it; and (b) redundant aggregation averaging away individual uncertainty (hedges / minority samples), manufacturing false certainty. Grice’s cooperative principle (Quantity / Manner) in fact requires surfacing the ambiguity / asking a clarification under consequential underspecification — the real pathology is that redundancy suppresses this cooperative move. We therefore describe our own thesis neutrally as a “system-level cooperative-communication failure”; “Collective Delusion” is retained only as M3MAD-Bench’s quoted term.

Link 1 \| Underspecification / ambiguity → gap-filling with priors

**Fact:** Yang et al. show that under underspecification the model infers by default, but with a cross-prompt std of 8.9% (vs ~4% for specified) and ~2× cross-model regression; CLAMBER shows weak ambiguity recognition and CoT worsening overconfidence. The underspecified prompt thus acts as a unified “bias generator.”

Link 2 \| Shared priors + sycophancy → highly correlated error (ρ↑)

**Fact:** even given different personas, agents share the same pretraining weights, RLHF reward, and probability priors; “When Truth Is Overridden” shows sycophancy is a “structural override of knowledge in deeper layers,” strongest under first-person framing; SYCON confirms alignment amplifies conformity.

> **\[Synthesizer inference\]** agents that should sample independently become “strongly error-correlated entities” — individual blind spots are uniformly amplified and system-level ρ climbs sharply. Byerly & Khashabi’s empirical result on position bias (SC amplifies correlated error) is the closest empirical analogue.

Link 3 \| Voting / debate → consensus-forming rather than correction

**Fact:** once ρ crosses the empirical crossover, most agents converge on the same “intent-mismatching” answer. M3MAD’s Collective Delusion (65%), the ICLR’25 blog’s “MAD overturns correct answers more than SC,” and iMAD’s “only 5–19% truly corrected” jointly characterize this end-state.

Link 4 \| Verifier shares the blind spot → rubber-stamps as an accomplice

**Fact:** Huang et al. show intrinsic self-correction without external feedback is unreliable and even degrades; Self-Preference Bias shows judges favor low-perplexity / same-family output. Handing the verifier to a model homologous with the generator equals “the same biased juror both votes and audits” — the line of defense collapses.

Link 5 \| Confidence–correctness inversion → silent failure forms, humans do not doubt

**Fact:** aggregation suppresses expression variance while retaining understanding bias; output confidence (verbalized / TSLD) is inflated by “majority agreement + independent verifier approval.” The trajectory looks smooth, evading IBM’s (2511.04032) structural anomaly detection. Schoeffer (CHI’24) and Bo et al. (CHI’25) show explanations don’t help humans tell right from wrong and interventions cut over-reliance yet rarely improve appropriate reliance — when the output is packaged as “multi-verified consensus,” automation bias is further amplified.

5\. Research Gap and the Project’s Moat

Existing MAD/SC critiques (M3MAD, ICLR blog, iMAD, Talk Isn’t Always Cheap) almost all compare accuracy on **ground-truth** benchmarks (MMLU/GSM8K/MATH/HumanEval/MedQA). This project’s target regime is precisely their blind spot: **the prompt is underspecified, no unique ground truth exists, yet the agents agree.**

Three seizable gaps

- **Benchmark gap:** M3MAD admits standardized tasks, automatic scoring, and lack of open-ended emergent behavior; it never constructs “multiple valid interpretations + hidden ground truths.”

- **Mechanism gap:** prior work observes Collective Delusion but never chains underspecification → sycophancy → ρ↑ → Condorcet reversal into a manipulable causal path, nor measures ρ as a mediator.

- **Detection gap:** IBM’s silent-failure work is trajectory-level structural anomaly; “consensus-type silent failure” has a normal trajectory that even the verifier approves, requiring a new no-GT detection handle.

> **\[Moat in one line\]** underspecification × correlated errors (ρ) × human observability = an academic vacuum. The triple, evaluated purely computationally (LLM-simulated users + algorithmic metrics), forms territory hard to be covered by “yet another paper proving MAD is useless.”

5.1 Evidence-strength assessment of decorrelation interventions (from report C, verified)

| **Intervention** | **Evidence** | **Basis** | **Synthesizer expectation** |
|:---|:---|:---|:---|
| Heterogeneous models | Medium | ICLR blog: mixing GPT-4o-mini/Llama/Claude sometimes helps but not always; M3MAD: heterogeneity ≠ distinct reasoning paths | may lower ρ but not guaranteed; must measure interpretation diversity |
| Temperature / sampling diversity | Weak–Medium | SC relies on diverse paths; but TACL’26 shows long-context sampling inherits structural bias | reduces variance only, not necessarily bias |
| Role prompting / devil’s advocate | Weak | ICLR blog: Multi-Persona often underperforms, over-aggressive, overturns correct answers | shell personas insufficient; must force orthogonal interpretations |
| Ranked / minority-aware aggregation | Medium | Mirror-Consistency, Ranked Voting show minority / ranking info has value | better as a detection signal than a direct answer selector |
| Clarification questions | Strong | Curiosity by Design, Hidden in Plain Sight: clarification effective on ambiguous tasks | best fit for the no-GT setting — the primary intervention |
| Ground-truth verifier | Strong but N/A to core setting | Huang et al.: without external feedback self-correction is weak | usable when an oracle exists; our contribution is oracle-free detection |

6\. Candidate Research Directions

The three reports’ candidate plans converge strongly (A’s Divergence-Surfacing, B’s Detector+Dashboard, C’s three directions). This synthesis merges them into three complementary directions, each explicitly annotated with pure-software feasibility, resources, metrics, and whether humans/hardware are involved.

| **Direction** | **Core idea & contribution** | **Pure SW? Resources** | **Metrics** | **Humans/HW?** | **Feasibility** |
|:---|:---|:---|:---|:---|:---|
| Direction A \| Phase-transition measurement benchmark (When Consensus Lies) | Build an underspecification benchmark (each item 2–4 valid interpretations + hidden gold + prior traps); measure the ρ–accuracy–confidence phase diagram; quantitatively reproduce Collective Delusion. | Pure software; GPT-4o-mini/Claude/Qwen/Llama API; logits from open weights for TSLD; no A100 (cloud GPU optional). ~\$500–1000 tokens. | ρ(phi), A_maj, ECE, false-consensus rate, confidence–correctness slope | No | High |
| Direction B \| Ground-truth-free silent-consensus detector (recommended core) | Detect false consensus without gold: forced interpretation branching (enumerate interpretations before answering) + insufficient coverage + minority signal + reasoning-trace embedding overlap → consensus suspicion score. | Pure software; use Direction A (with hidden gold) as dev set; add lightweight embeddings; LLM-simulated user answers clarifications. | silent-failure recall/precision, AUROC/F1, abstention quality, false-alarm rate, ECE | No | High |
| Direction C \| HCI surfacing interface (Consensus Uncertainty Dashboard) | Side-by-side display of “all agents agree but depend on the same unconfirmed assumption”; visualize divergence; generate clarification questions; main experiment evaluated via silicon sampling. | Pure software (main paper): browser/VS Code mock + LLM-simulated users (personas injected with automation bias). Optional 24–40-person online (non-core). | over-reliance rate, corrective/detrimental override, silent-failure awareness, clarification acceptance | No (main) | High (SW) / Med (with humans) |

Recommended combination: A (evaluation infrastructure) + B (no-GT detector, quantifiable ML contribution) + C (HCI surfacing, human-AI collaboration system contribution) — a single pipeline, i.e. the convergent conclusion of all three reports.

> **\[Detector repositioning · review-round-3 point 3\]** Direction B does NOT claim “judging right/wrong without GT” — consensus strength inherently cannot separate true from false consensus (a correct high-confidence consensus also has high overlap). It is repositioned as Hypothesis Surfacing: detect whether the consensus depends heavily on an “unstated latent assumption I_k,” and excavate it (e.g., “Warning: current consensus depends on the unverified assumption ‘Q1 = calendar quarter’”). The discriminating signal is interpretation-branch output divergence / aleatoric uncertainty (Hou et al.’s Input Clarification Ensembling), NOT consensus strength: unambiguous tasks collapse the branches → no alarm; underspecified false consensus diverges → alarm. FP is quantified by the false-surfacing rate on unambiguous controls.

7\. Recommended Plan + Executable Protocol (pure software)

**Proposed title (main line, system-level):** When Consensus Lies: Ground-Truth-Free Detection of Silent Consensus Failures under Underspecified Prompts. Venue packaging: the ACL/EMNLP cut leads with linguistic triggers + representational correlation + ρ measurement + detector; the NeurIPS D&B cut leads with benchmark + detector; the CHI/IUI cut leads with the surfacing interface + reliance (simulated users; limitations in 8.4/8.5).

7.1 Dataset construction (Underspecified-Trap Benchmark)

- **Each sample:** underspecified prompt (1–3 key constraints hidden) + full latent spec + 2–4 plausible interpretations (each with hidden gold) + key clarification questions + executable/decidable tests.

- **Prior-trap example (from A):** require “extract Q1 revenue” without specifying whether Q1 means the natural quarter (Jan–Mar) or a fiscal quarter (e.g., Apr–Jun); due to alignment priors, an un-clarifying agent defaults to the natural quarter with high probability.

- **Sources & scale:** rewrite ClarifyCodeBench / SWE-bench-style (delete 1/2/3 classes of requirements for low/medium/high ambiguity); 3 task types (code spec, data analysis, policy QA) × 100–150 items ≈ 300–800 items.

> **\[Omniscient-Blind evaluation paradigm (all three agree; named by A)\]** To the executing system the prompt is underspecified with no unique GT; but inside the “god’s-eye” scoring script we retain the hidden gold corresponding to the simulated user’s true intent. Whether the system recovers this hidden intent becomes a code-decidable, objective metric — defusing the “how to evaluate without GT” legitimacy crisis.

7.2 Model settings (from report B)

| **Setting** | **Configuration** | **Purpose** |
|:---|:---|:---|
| **Homogeneous agents** | same model (e.g., GPT-4o) ×5, temperature ∈ {0.3,0.7,1.0} | measure the ρ baseline from shared prior |
| **Heterogeneous agents** | GPT-4o + Claude + Qwen + DeepSeek mix | measure the decorrelation effect of model diversity |
| **Verifier coupling** | same-family / cross-model / tool-grounded verifier | measure the generator–verifier gap and accomplice effect |
| **Reasoning models** | o3-mini / DeepSeek-R1, etc. | test whether reasoning weakens sycophancy-driven correlation |

**Model boundary for mechanistic analysis:** internal representation analysis (logit-lens / activation patching) is performed only in the “homogeneous agents = single open-weight model, multi-session” cell; the heterogeneous and verifier-coupling cells measure behavior only, and no internal-mechanism claim is made for closed models (see 8.5).

7.3 Baselines

- Single-agent direct answer; CoT; Self-Consistency majority vote (Wang et al.); standard MAD (Du et al.); Generator + same-family verifier; iMAD-style selective triggering; Input Clarification Ensembling (Hou et al., as an uncertainty-decomposition baseline).

- **Proposed method:** interpretation branching + divergence detector + clarification trigger + consensus uncertainty dashboard.

7.4 Key metrics

- Interpretation match (equals hidden I₀?); task accuracy (vs latent spec); convergent-delusion / false-consensus rate (primary) + marginal ρ phi (secondary); A_maj; calibration (ECE, confidence–accuracy slope); detection side = latent-assumption surfacing quality (did it excavate the truly relied-on I_k) + AUROC/F1 + the key new metric false-surfacing rate on unambiguous controls (false-alarm rate on the unambiguous set, directly answering “does it over-fire on true consensus”); HCI side = appropriate reliance (corrective/detrimental override), silent-failure awareness, clarification acceptance, extra interaction cost.

7.5 Ablation design (from report B)

| **Ablation variable** | **Levels** | **Prediction** |
|:---|:---|:---|
| **Ambiguity strength** | low/medium/high (remove 1/2/3 requirement classes) | ρ rises with ambiguity strength |
| **Temperature** | 0 / 0.3 / 0.7 / 1.0 | higher temp → more path diversity → partial decorrelation |
| **Model diversity** | homogeneous / heterogeneous | heterogeneity should lower ρ; shared training data may limit it |
| **Prompt perturbation** | statement vs question, first/third person | first-person / high-certainty → ↑sycophancy → ↑ρ (Ask don’t tell / SYCON) |
| **Verifier oracle** | no external feedback / with tool·test·retrieval evidence | external evidence should break the consensus loop |
| **Forced interpretation branching** | on / off | branching → ↑interpretation coverage → ↓silent failure |

7.6 Primary statistical test (from report C)

Mixed-effects logistic regression: correctness ~ ρ + ambiguity + method + model + interactions, random effects grouped by task/model, reporting bootstrap CIs. Robustness: stronger reasoning models, different domains, prompt paraphrases, and a three-way comparison of LLM-judge vs programmatic verifier vs hidden gold.

7.7 Construct validity and provenance separation (answering “LLM-evaluating-LLM circularity”)

**The sharpest reviewer hit:** if ambiguous prompts and hidden gold are auto-generated by GPT-4 and interpretation match is judged by an LLM-as-judge, the measured ρ may merely be an artifact of “sharing priors with the data-construction model,” not task-inherent correlation. The three design moves below turn this confound from a weakness into a selling point:

- **(1) Executable/decidable gold, not LLM-judged gold:** code (unit test pass/fail), data-analysis (deterministic numbers), natural- vs fiscal-Q1 (computable different outputs) — gold comes from execution or human annotation, not an LLM judge. Hence code / data-analysis are the primary domains; policy-QA is de-emphasized or uses human rubrics only.

- **(2) Deletion-based ambiguity, not generative ambiguity:** following Yang et al., delete 1/2/3 requirement classes from a full human-written spec to make low/medium/high ambiguity. Deletion-based ambiguity is a model-agnostic structural absence, not a generation artifact — directly defusing “your ρ is the constructor model’s artifact.”

- **(3) Provenance separation as an explicit control (killer robustness check):** run constructor model / tested agents / judge as same-family vs cross-family. If ρ remains significant under cross-family construction, the “shared-prior-with-constructor” confound is ruled out. The judge is additionally calibrated by human sampling (Yang et al. report 95.6% human–LLM agreement); executable tasks need no judge at all.

8\. Risks and Limitations

8.1 Legitimacy of no-ground-truth evaluation

**Mitigation:** the Omniscient-Blind paradigm separates “hidden gold exists at construction” from “gold invisible at detector inference”; also report interpretation coverage/diversity to avoid mis-scoring genuinely multi-valid tasks. The paper must state this separation explicitly, or reviewers will challenge the no-GT claim.

8.2 Reasoning models may weaken the effect (the reviewer’s premise is refuted by recent evidence)

**Challenge:** if strong reasoning models (o3-mini / R1) correct sycophancy at scale via System-2 and push ρ into a harmless range, “silent failure” gets demoted to “local degradation only on weak models (GPT-4o-mini / Llama-8B).” This is a real downside to hedge; but the premise is refuted by 2025–2026 evidence:

- **Reasoning only attenuates, never eliminates:** “Reasoning Isn’t Enough” (arXiv:2506.21561) finds o4-mini/GPT-4.1/R1 still sycophantic, truth-bias still above human baselines; SYCON shows reasoning cuts sycophancy by at most 21.6% (scaling reaches 81.4%), with “over-indexing on logical exposition” as its signature failure.

- **May even worsen (Inverse Scaling):** “Internal Reasoning vs External Control” (arXiv:2601.03263) empirically finds “frontier models sycophant more because rationalization requires capability,” and self-correction only drops to 7–9% “because the model critiques itself with the same biases” — exactly this report’s verifier-accomplice mechanism.

- **Two-regime demarcation (key):** RLVR works only in strong-verifier domains (math/code/proof) and is nearly flat on writing/underspecification. So reasoning rescues only “context-derivable” ambiguity; for “external business knowledge absent from context,” no amount of System-2 conjures it — it may even dress a wrong assumption in prettier justification. Moreover, even a fully non-sycophantic model shares the “Q1 = calendar quarter” pretraining default — a model-strength-invariant correlation source.

- **Mitigation:** make reasoning models a first-class condition and pre-register two hypotheses: (H1) in true external-knowledge underspecification the effect persists or even intensifies via inverse scaling; (H2) in derivable-ambiguity domains the effect shrinks = a clean boundary condition. Both are publishable. Add RCA (2601.03263, a no-GT trace–output consistency detector) to related work / baselines.

8.3 Avoiding “yet another paper proving MAD is useless”

**Mitigation:** pin novelty on four intersections: (1) underspecification manipulated as an independent variable (not a benchmark stress test); (2) a detection method under no explicit GT (not just accuracy reporting); (3) extending from agent-only to human-AI collaboration observability; (4) a computable CHI interaction plan (LLM-simulated users, not a traditional lab study).

8.4 The absent “Human” and silicon legitimacy (claim–method alignment)

**Challenge:** the title speaks of human collaboration while the method is all simulated users — ACL will rule “claim too big, experiments can’t support it.” This is a real weakness of the original synthesis, to be corrected head-on.

- **Evidence supports the challenge:** “Lost in Simulation” (arXiv:2601.17087) empirically finds simulated users diverge from humans — success rate swings ±9pp across user LLMs, systematic miscalibration, unfairness to AAVE/Indian-English speakers, conversational artifacts and different failure patterns; “Simulacrum of Stories” (CHI 2025, honorable mention) concludes “LLMs cannot replace human qualitative participants.”

- **Mitigation (narrow the claim under the hard constraint):** (1) the main-line claim is narrowed to system/detection level; the simulated user is only a load model / test fixture and results are phrased as “reducing a simulated decision-maker’s acceptance of wrong consensus,” not human automation bias; (2) cross-model judge + human-sampled checks, deterministic tests for executable tasks; (3) “LLM-ification of CHI” (arXiv:2501.12557) shows simulated users are an accepted CHI role but require explicit validity caveats — the CHI cut accordingly lists a real human study as future work and cites Lost in Simulation to self-disclose limits.

8.5 Venue fit and NLP/representational core (answering “this is a systems paper, go to CHI”)

**Valid part:** if the centerpiece is dashboard design / agent-pipeline engineering, ACL will desk-reject. Overstated part: the project does have a CL/NLP core, merely buried under the dashboard — the ACL cut should foreground it:

- **Linguistic triggers → multi-agent correlation:** extend Ask don’t tell’s “sentence form / epistemic certainty / person causally drive sycophancy” from single-agent to “multi-agent correlated interpretation default” — a pure NLP increment.

- **Representation-level correlation (scoped to a single open-weight model, multi-session · point 1):** using When Truth Is Overridden’s logit-lens + activation patching as a paradigm, prove that “shared representational perturbation” is the source of cross-agent error correlation — the “internal representational change” ACL wants. Patching runs only across multi-session/multi-sample of a single open model (Llama-3-70B / Qwen-2.5-72B) where weights and hidden space are identical; closed models (GPT-4o/Claude) and heterogeneous mixes are measured behaviorally only (cross-tokenizer/hidden-dim/architecture cannot be cross-model patched). This boundary aligns with 8.2’s two channels: mechanism layer = shared-prior-default channel, behavior layer = where decorrelation interventions live. TSLD is also an internal signal of that single open model.

- **Packaging strategy:** do not submit the same paper to ACL and CHI. ACL/EMNLP = linguistic triggers + representational correlation + ρ measurement + detector; CHI/IUI = surfacing + reliance; NeurIPS D&B = benchmark + detector.

8.6 Round-2 adversarial review: four challenges and the absorbed responses

| **Challenge** | **Verdict** | **Point** | **Absorbed response** |
|:---|:---|:---|:---|
| \#1 Human absence / silicon legitimacy | Largely valid | title’s “Human” conflicts with pure software; Lost in Simulation shows sim ≠ human | narrow to system-level claim; sim users as fixtures; CHI cut self-discloses (see 8.4) |
| \#2 LLM-eval-LLM circularity / Hidden Gold | Fully valid (strongest) | auto-generate + auto-judge → ρ may be a constructor artifact | executable gold + deletion-based ambiguity + provenance-separation control (see 7.7) |
| \#3 Missing NLP core / venue fit | Partly valid | dashboard-first gets ACL-rejected to CHI; but a linguistic/representational core exists | venue packaging; ACL cut foregrounds linguistic triggers + representation (see 8.5) |
| \#4 Reasoning models weaken effect | Real threat, premise refuted | reviewer assumes ρ drops to harmless; evidence shows only attenuation, even inverse scaling | two-regime + reasoning as first-class condition + pre-registered H1/H2 (see 8.2) |

8.7 Round-3 adversarial review: ACL-level technical faults and absorbed responses

| **Fault** | **Verdict** | **Point** | **Absorbed response** |
|:---|:---|:---|:---|
| \#1 Representation × closed-model paradox | Fully valid | closed/cross-model cannot be activation-patched; blowback from the last round’s patch | mechanism scoped to single open-model multi-session; closed/hetero behavior-only (see 8.5, 7.2) |
| \#2 Binary ρ mismatch | Fully valid (deepest) | binary both-wrong ≠ same-wrong; ρ collapses to task difficulty | interpretation-label categorical variable + convergent-delusion primary metric (see 2.2) |
| \#3 No-GT detection FP blowup | Valid | consensus strength cannot separate true/false consensus | reposition detector to Hypothesis Surfacing + false-surfacing rate (see 6, 7.4) |
| \#4 Pragmatics backlash (Grice) | Partly valid (framing) | “using a prior” is rational, should not be called delusion | reframe as “system-level cooperative-communication failure” + consequential scoping; Grice supports us (see 4) |

> **\[Hard-constraint re-check\]** All three directions and every experimental phase are pure software — no A100/local GPU dependency (open-weight logits optionally via cloud GPU or skipped), no eye-tracking/EEG/VR/sensor hardware, no human subjects at the core — fully satisfying the hard constraint. The narrowed system-level claim aligns exactly with the pure-software method.

9\. References (unified, de-duplicated · credibility-tagged)

**Tagging convention:** “High” = verified via web search this session or a recognized classic; “Medium” = agreed across reports or has an arXiv ID but not individually re-verified; “Unverified” = single-source and unconfirmed this session, or a suspected conflated entry — already handled conservatively in the body.

| **Work** | **Author / year / venue · arXiv** | **Credibility** |
|:---|:---|:---|
| Self-Consistency Improves CoT Reasoning | Wang et al. — ICLR 2023 | High |
| Improving Factuality & Reasoning via Multiagent Debate | Du et al. — ICML 2024 (arXiv:2305.14325) | High |
| Self-Consistency Falls Short! (positional bias) | Byerly & Khashabi — TACL 2026 / arXiv:2411.01101 | High (verified) |
| M3MAD-Bench | Ao Li et al. — arXiv:2601.02854 (2026-01) | High (verified) |
| iMAD: Intelligent Multi-Agent Debate | Fan, Yoon, Ji — AAAI 2026 Oral / arXiv:2511.11306 | High (verified) |
| Multi-LLM-Agents Debate (blogpost) | ICLR 2025 Blogposts | Medium |
| Talk Isn’t Always Cheap (MAD failure modes) | Wynn et al. — ICML MAS Wksp 2025 / arXiv:2509.05396 | Medium (report B only) |
| LLMs Cannot Self-Correct Reasoning Yet | Huang et al. — ICLR 2024 | High |
| Self-Preference Bias in LLM-as-a-Judge | arXiv:2410.21819 (2024) | Medium |
| SYCON Bench (multi-turn sycophancy) | Hong et al. — EMNLP 2025 Findings / arXiv:2505.23840 | High (verified) |
| Ask don’t tell (reducing sycophancy) | Dubois et al. — UK AISI / arXiv:2602.23971 | High (verified) |
| When Truth Is Overridden (sycophancy mechanism) | arXiv:2508.02087 (2025) | Medium |
| Wired for Overconfidence (TSLD) | Zhao et al. — arXiv:2604.01457 | High (verified) |
| What Prompts Don’t Say (underspecification) | Yang et al. — ACL Findings 2026 / arXiv:2505.13360 | High (verified) |
| CLAMBER (ambiguity benchmark) | Zhang et al. — ACL 2024 | High |
| Decomposing Uncertainty via Input Clarification Ensembling | Hou et al. — ICML 2024 / arXiv:2311.08718 | Medium |
| Curiosity by Design (clarification) | arXiv:2507.21285 (2025) | Medium |
| Detecting Silent Failures in Multi-Agentic AI Trajectories | Pathak et al. — IBM / arXiv:2511.04032 | High (verified) |
| Reasoning Isn’t Enough (truth-bias & sycophancy) | Barkett et al. — ICML 2025 Wksp / arXiv:2506.21561 | High (verified) |
| Internal Reasoning vs External Control (RCA, Inverse Scaling) | Chang — arXiv:2601.03263 (2026-01) | High (verified) |
| Lost in Simulation (simulated users ≠ humans) | Seshadri et al. — UC Irvine/Cohere / arXiv:2601.17087 | High (verified) |
| Understanding the LLM-ification of CHI | Pang et al. — CHI 2025 / arXiv:2501.12557 | High (verified) |
| ‘Simulacrum of Stories’ (LLMs as qual. participants) | Kapania et al. — CHI 2025 (honorable mention) | High (verified) |
| Explanations, Fairness & Appropriate Reliance | Schoeffer et al. — CHI 2024 | High |
| To Rely or Not to Rely (reliance interventions) | Bo et al. — CHI 2025 / arXiv:2412.15584 | Medium |
| Over-Relying on Reliance (TRAP) | Sivaraman et al. — CHI 2025 Wksp / arXiv:2504.07423 | Medium |
| Condorcet’s Jury Theorem & Correlated Voters | Ladha 1992; Kaniovski (& Zaigraev) | High (classic) |
| Error Correlation & Reduction in Ensemble Classifiers | Tumer & Ghosh — Connection Science 1996 | High (classic) |
| Mirror-Consistency / Ranked Voting SC | EMNLP 2024 Findings / ACL 2025 Findings | Medium |
| CLARITI / Ask or Assume / ClarifyCodeBench | arXiv:2604.14624 / (SWE-bench) / arXiv:2607.00711 | Unverified (report B only) |
| ADVICE / AFCE / Mind the Confidence Gap (calibration) | 2026 / ACL 2025 / 2025 | Unverified (report C only) |
| Hidden in Plain Sight (MLLM clarification) | EMNLP 2025 | Unverified (report C only) |
| Yan et al. (under/misspecified scenarios) | EMNLP 2025 (suspected conflation with Yang et al.) | Unverified (suspected conflation) |
| Romeo & Conti (automation-bias survey) | AI & SOCIETY 2025 | Unverified (report B only) |

Appendix A: Multi-dimensional comparison scores of the three reports

Scores are the synthesizer’s assessment (1–5, higher is better), based on close reading and this session’s citation verification. Totals: **A = 33, B = 39, C = 36 (out of 40).**

| **Scoring dimension** | **A** | **B** | **C** | **Key rationale** |
|:---|:---|:---|:---|:---|
| 1 Literature coverage & currency | 4 | 5 | 4 | B most complete (clarification cluster + Talk Isn’t Always Cheap); C uniquely has Byerly & calibration cluster; A uniquely has Wired for Overconfidence |
| 2 Citation verifiability / accuracy | 3 | 5 | 4 | B has full arXiv/venue with all numbers verified; C’s Byerly is real but the ‘53 of 56’ stat is unconfirmed and ‘Yan et al.’ is suspected conflation; A has few arXiv IDs but TSLD verified real |
| 3 Formalization & theoretical rigor | 4 | 5 | 5 | B/C correctly note the phase transition is not universal (Kaniovski joint-distribution non-identifiability); A over-claims ρ\* as a law |
| 4 Mechanism depth | 5 | 5 | 4 | A’s 4-step causal chain is tightest (incl. verifier accomplice); B ties each of 5 links to evidence; C is briefer but the ρ-mediator framing is sharp |
| 5 Gap / moat clarity | 4 | 5 | 5 | B: ‘underspec × ρ × observability = gap’ is crispest; C’s Benchmark/Mechanism/Detection trichotomy is clear |
| 6 Candidate quality & pure-software feasibility | 4 | 5 | 5 | B has costed plans (\$500–1000); C has the intervention-evidence table + explicit ‘no A100’; A’s Direction A depends on open-weight logits |
| 7 Protocol executability | 4 | 5 | 4 | B most complete (model settings/baselines/ablations/figure list); C uniquely has the mixed-effects model; A’s Q1 natural/fiscal example is most concrete |
| 8 Hard-constraint compliance | 5 | 4 | 5 | A, C are fully pure-software + silicon sampling; B’s main paper is pure software but suggests an optional 24–40-person online study (marked non-core) |
| Total (/40) | 33 | 39 | 36 | B strongest (literature + citations + protocol + honesty); C second (rigor + Byerly + statistics); A third (mechanism narrative + paradigm naming) |

Appendix B: Integration Log

B.1 Which report each part draws on

- **Executive summary / mechanism chain:** A’s four-step causal narrative as the skeleton, fused with B’s ‘evidence vs hypothesis’ layering and C’s ‘ρ as mediator’ framing.

- **Formalization (Section 2):** CJT and Tumer-Ghosh common to A/B/C; three-layer confidence from B; TSLD from A (verified); the rigorous ρ\* phrasing from B/C (rejecting A’s over-claim).

- **Literature review (Section 3):** union, de-duplicated; adds C’s unique Byerly & Khashabi (strongest mechanistic precedent) and B’s unique clarification cluster and Talk Isn’t Always Cheap.

- **Intervention-evidence table (5.1):** taken wholesale from C.

- **Protocol (Section 7):** model-settings/ablation tables from B; Omniscient-Blind and the Q1 trap example from A; mixed-effects statistics from C.

B.2 Conflict-adjudication record

- **Is ρ\* a universal law:** A (yes) vs B, C (no) → side with B/C, confidence 90. Basis: Kaniovski proves pairwise correlations + marginals do not uniquely determine the joint distribution, so no closed-form universal ρ\*; replaced with an empirical crossover + pre-registered phase diagram.

- **M3MAD year:** A’s ‘2026-01’ is correct (arXiv:2601.02854, 2026-01-06); B/C loosely say ‘2025’. Corrected to 2026.

- **Recommended plan:** A (Divergence-Surfacing lead), B (Detector+Dashboard), C (three directions) are actually convergent → merged into the A+B+C pipeline.

- **Confidence metric:** TSLD(A) / three-layer(B) / ADVICE·AFCE(C) are complementary, not conflicting → B’s three layers as the backbone, A and C as supplements.

B.3 Discarded content and reasons

- **A’s ‘ρ\* is a derived law’ phrasing:** discarded/downgraded — theoretically untenable, invites reviewer challenge.

- **Over-precise effect numbers (e.g., ‘over-reliance drops from 85% to below 20%’):** changed to ‘expected direction,’ as they are predictions, not measured results.

- **B’s optional human online study:** retained but explicitly downgraded to a ‘non-core robustness check’ to honor the hard constraint.

B.4 Suspect-citation list (handled conservatively in the body)

- **Unverified:** CLARITI (2604.14624), Ask or Assume, ClarifyCodeBench (2607.00711), ADVICE, AFCE, Mind the Confidence Gap, Hidden in Plain Sight, Romeo & Conti — all single-source and not re-verified this session.

- **Suspected conflation:** C’s ‘Yan et al. EMNLP 2025 (under/misspecified scenarios)’ may be conflated with the verified Yang et al. (ACL Findings 2026, 2505.13360); the body uses Yang et al.

- **Statistic in doubt:** C claims Byerly & Khashabi report ‘53 of 56 task-model pairs show no improvement’ — the paper actually reports ‘651 experiments / 8 models / 9 tasks’; that specific count is unconfirmed, so the body uses only the verified ‘SC amplifies correlated error’ conclusion.

B.5 Absorption of round-2 adversarial review

- **Point 1 (Human absence) — adopted:** acknowledged the title’s claim–method mismatch as a real weakness; main title drops Human, narrows to system/detection level; simulated-user results restated as ‘simulated decision-maker.’ Added Lost in Simulation / LLM-ification of CHI / Simulacrum of Stories as support and self-disclosure.

- **Point 2 (circularity) — fully adopted (most valuable):** added 7.7 construct validity & provenance separation — executable gold + deletion-based ambiguity + same/cross-family control.

- **Point 3 (missing NLP core) — partly adopted:** added 8.5 — venue packaging, ACL cut foregrounds the ‘linguistic triggers + representational correlation’ core; but rebutted the ‘no NLP core at all’ over-statement.

- **Point 4 (reasoning dissolves effect) — kept the hedge, refuted the premise:** upgraded 8.2 — refute ‘ρ drops to harmless’ with Reasoning Isn’t Enough and Internal Reasoning vs External Control (Inverse Scaling / self-correction only to 7–9%), introduced the two-regime split and H1/H2 pre-registration.

B.6 Absorption of round-3 adversarial review (ACL-level technical faults)

- **Point 1 (representation × closed-model) — adopted:** 8.5 / 7.2 restrict logit-lens·activation patching to a single open-weight model, multi-session; closed and heterogeneous measured behaviorally — fixing the technical fault introduced by last round’s ‘NLP core’ patch.

- **Point 2 (binary ρ) — fully adopted (deepest):** 2.2 switches to an interpretation-label categorical variable; the primary metric is convergent-delusion / false-consensus rate; binary ρ is downgraded to marginal, bridging CJT/Tumer-Ghosh only.

- **Point 3 (no-GT detection FP) — adopted:** detector repositioned to Hypothesis Surfacing (excavate the latent assumption I_k); discriminating signal uses interpretation-branch divergence / aleatoric (Hou et al.), not consensus strength; added false-surfacing rate on unambiguous controls.

- **Point 4 (Grice backlash) — softened framing + counter:** Section 4 adds a pragmatics clarification: the failure is not ‘using a prior’ but ‘silent commitment on consequential ambiguity + redundancy-induced false confidence’; Grice’s cooperative principle in fact supports us; own thesis restated as ‘system-level cooperative-communication failure.’

> **\[Synthesizer’s overall assessment\]** The vast majority of the three reports’ citations are real literature (including several 2026 SOTA), with no systematic hallucination; the main differences are rigor and coverage. This synthesis uses B as the skeleton, C to reinforce theory and the key precedent, and A to reinforce the mechanism narrative and paradigm naming, and through three rounds of adversarial review — narrowing the claim, shoring up construct validity / formalization / detector positioning and venue packaging — produces a topic report stronger than any single one, fully compliant with the pure-software hard constraint.
