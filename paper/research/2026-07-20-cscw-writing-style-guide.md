> Doc-only CSCW writing/positioning guide (research sub-agent, GPT family, 2026-07-20). Manager-persisted to RESEARCH_DIR.
> NOTE: CSCW 2026 requires marking LLM-generated text, verifying every citation, and author-written prose.

# CSCW Writing and Positioning Guide: “When Consensus Lies”

## Executive recommendation

Frame the paper as a **sociotechnical study of false collective confidence**, not as a benchmark comparing LLM accuracy. The central CSCW claim should be:

> **Consensus is epistemically valuable only when judgments retain sufficiently independent evidence and interpretations. When multiple AI agents inherit the same underspecified information boundary, agreement can amplify—not diagnose—a shared error.**

The unit of concern is the **AI-mediated organizational decision pipeline**: teams and institutions increasingly treat agreement among multiple models as corroboration. Your study demonstrates when that apparent redundancy is structurally fake.

This distinction is essential because the current CSCW scope explicitly warns that purely algorithmic work, and work benefiting only one user collaborating with AI agents, may be desk rejected. Technical AI work must explain its relevance to cooperative, collaborative, or social systems and engage CSCW concepts directly ([CSCW 2026 CFP, “Paper Guidelines Regarding Scope”](https://cscw.acm.org/2026/papers.html)).

---

## 1. CSCW contribution norms

### What strong CSCW contributions look like

CSCW recognizes multiple research paradigms: technical/systems, empirical-qualitative, empirical-quantitative, mixed methods, design, and theoretical work. The venue explicitly welcomes empirical investigations, methodologies, systems, collective intelligence, social computing, and analysis of algorithms shaping collaborative practices ([CSCW 2026 CFP](https://cscw.acm.org/2026/papers.html)).

For this paper, claim four bounded contributions:

1. **Empirical contribution:** Pre-registered evidence that independently queried agents across model families and capability tiers can silently converge on the same incorrect interpretation when decisive context is omitted from the retained prompt.
2. **Methodological contribution:** An executable-gold protocol that manipulates whether a disambiguator crosses the prompt boundary and measures correlated error, not merely individual accuracy.
3. **Conceptual contribution:** “Fake redundancy” as a failure mode of AI aggregation: nominally \(k\) agents but approximately one effective independent judgment when error correlation approaches one.
4. **Artifact contribution:** Benchmark instances, executable evaluators, preregistration, prompts, analysis code, and model/version records—only claim this if they will actually be released.

Do not claim a new general theory of collaboration unless the paper develops and tests one. A safer claim is that the results **identify a boundary condition for applying collective-intelligence assumptions to AI ensembles**.

### Translate ML framing into CSCW framing

| Pure-ML framing | CSCW framing |
|---|---|
| Ensemble accuracy | Reliability of aggregated advice in collaborative decision infrastructures |
| Correlated model errors | Loss of epistemic independence and fake redundancy |
| Prompt ablation | Information-boundary manipulation / contextual grounding failure |
| Cross-model benchmark | Test of whether supplier and capability diversity create meaningful viewpoint independence |
| Majority vote failure | Consensus becoming an invalid warrant for organizational decisions |
| Better prompt | Preservation of provenance, context, and interpretive alternatives across handoffs |
| Model robustness | Sociotechnical resilience of AI-assisted group judgment |

The paper should repeatedly answer: **Why does this matter to groups, organizations, communities, and collaborative decision-making?**

Use examples such as incident response, policy analysis, medical case conferences, moderation teams, intelligence analysis, and collaborative software work—but label them as implications, not tested deployments.

### What reviewers reward

- A consequential cooperative or social problem, stated before technical details.
- A clear conceptual bridge to CSCW theory.
- Methods appropriate to the claim, with transparent operationalization.
- Evidence that distinguishes competing explanations.
- Honest boundary conditions and null results.
- Actionable implications for collaborative-system design.
- Reproducibility, preregistration, and careful reporting.
- Contribution commensurate with paper length.

The awards process separately recognizes Best Papers, methodological strength, and practical impact. Best Papers represent approximately 1% of submissions and honorable mentions another 3% ([CSCW 2023 awards](https://cscw.acm.org/2023/index.php/awards/); [CSCW 2024 awards](https://cscw.acm.org/2024/index.php/awards/)).

### Common rejection risks

1. **Out of scope:** “We benchmarked several agents” without showing how the result changes understanding or design of collaborative systems.
2. **Agents treated as humans:** Anthropomorphizing model agreement as genuine social consensus.
3. **Benchmark-first introduction:** Opening with model families, datasets, or accuracy tables rather than the failure of corroboration.
4. **Weak construct validity:** Treating any ambiguous item as evidence of consensus failure without proving that the external disambiguator establishes a unique gold interpretation.
5. **Overgeneralization:** Moving directly from synthetic agents to claims about human trust or real teams.
6. **Theory as decoration:** Mentioning groupthink or common ground without explaining what the study extends, contradicts, or bounds.
7. **Artifact-only novelty:** A benchmark with no CSCW knowledge contribution.
8. **Hidden researcher degrees of freedom:** Unclear exclusions, model selection, prompt variants, or post-preregistration deviations.

---

## 2. Structure and rhetoric of strong CSCW papers

### Typical full-paper structure

1. Introduction  
2. Conceptual Background / Related Work  
3. Research Questions or Hypotheses  
4. Benchmark and Study Design  
5. Results / Findings  
6. Discussion  
7. Design Implications or Implications for CSCW  
8. Limitations  
9. Ethics and Open Science  
10. Conclusion  

CSCW papers often end the Introduction with an explicit numbered contribution paragraph. Bullets are useful but not mandatory; specificity matters more than format.

### Introduction rhetoric

Use a five-step funnel:

1. Establish a collaborative practice: groups seek corroboration by consulting multiple sources.
2. State the accepted premise: aggregation helps when errors are diverse and sufficiently independent.
3. Expose the gap: model-family or agent-count diversity may not produce interpretive independence when all agents receive the same lossy representation.
4. State the study and headline finding.
5. Enumerate contributions and implications.

Avoid spending the first page defining LLM agents. Make the problem legible without ML expertise.

### Related Work

Organize by arguments, not technologies:

- Conditions for wisdom of crowds.
- Consensus pathologies and correlated judgment.
- Grounding and information boundaries in cooperative work.
- Human reliance on aggregated AI advice.
- LLM ensembles and multi-agent evaluation.

End each subsection with the unresolved premise your study tests. For example:

> Prior ensemble research varies models or samples but rarely verifies whether nominally independent agents form independent task interpretations when all inherit the same underspecified representation.

### Findings rhetoric

Use answer-first headings:

- **F1: Omitted context produced accurate-looking but systematically wrong consensus.**
- **F2: Capability and model-family diversity did not restore interpretive independence.**
- **F3: Increasing agent count added little effective redundancy.**
- **F4: Retaining the disambiguator eliminated the failure.**

Within each finding:

1. State the result.
2. Present effect size and uncertainty.
3. Show representative cases.
4. Report preregistered tests.
5. Report robustness checks and nulls.
6. Reserve broader interpretation for Discussion.

### Discussion and design implications

Discussion should not merely repeat results. It should explain:

- Which assumption of collective intelligence failed.
- Why model diversity did not equal evidence diversity.
- Why the failure occurred at an information boundary.
- When consensus remains useful.
- What collaborative-system designers should change.

A dedicated **“Implications for CSCW and Collaborative AI Systems”** section is advisable. Separate empirical findings from recommendations and label each recommendation by evidential strength.

---

## 3. Lessons from award-winning papers

### Cura: Curation at Social Media Scale

*Cura* was a CSCW 2023 Best Paper ([official award listing](https://cscw.acm.org/2023/index.php/awards/)). Its rhetorical strength is that it does not present scaling as merely an algorithmic problem. It first defines **curation as a community-level practice**, distinguishes it from personalization and deletion-oriented moderation, and positions automation inside a collaborative human-curator workflow ([paper](https://arxiv.org/abs/2308.13841)).

**Lesson:** Define “consensus” as a sociotechnical practice and institutional signal before introducing metrics.

### Measuring User-Moderator Alignment on r/ChangeMyView

Also a CSCW 2023 Best Paper ([official listing](https://cscw.acm.org/2023/index.php/awards/); DOI [10.1145/3610077](https://doi.org/10.1145/3610077)). Its significance comes from making a fuzzy governance concept—alignment—measurable while retaining its policy and community meaning.

**Lesson:** Operationalize “silent consensus failure” with multiple observable components: correctness, unanimity, confidence/silence, pairwise correlation, and effective ensemble size. Do not collapse the construct into accuracy alone.

### SUMMIT

*SUMMIT: Scaffolding Open Source Software Issue Discussion through Summarization* was both a CSCW 2023 Best Paper and Methods Recognition recipient ([official listing](https://cscw.acm.org/2023/index.php/awards/)). Its Introduction progresses through existing collaborative practice, observed breakdown, sequential RQs, content analysis, formative design, implementation, and evaluation. Its contribution paragraph cleanly separates empirical evidence, guidelines, artifact, and broader opportunity ([paper](https://arxiv.org/abs/2308.02780); DOI [10.1145/3610088](https://doi.org/10.1145/3610088)).

**Lesson:** Let each study stage answer a distinct question. Present the executable-gold benchmark, preregistered test, and robustness analyses as a cumulative methodological argument.

### Embedding Democratic Values into Social Media AIs

This CSCW 2024 Best Paper opens with a societal question—whether social media can support democracy—not with model performance. It translates established social-science constructs into algorithmic objectives, validates the manual operationalization before automation, and uses three studies to connect technical behavior to a social outcome ([paper](https://arxiv.org/abs/2307.13912); [official award listing](https://cscw.acm.org/2024/index.php/awards/)).

**Lesson:** Begin with the social consequence of treating AI consensus as corroboration. Establish the validity of the gold interpretation before presenting cross-model scaling.

---

## 4. Recommended theoretical positioning

### 1. Wisdom of crowds and Condorcet

The Condorcet Jury Theorem’s optimistic result depends on assumptions including competence and sufficiently independent judgments. Social influence can reduce diversity without improving accuracy, creating confident convergence around error (Lorenz et al., 2011, DOI [10.1073/pnas.1008636108](https://doi.org/10.1073/pnas.1008636108)).

Your extension is precise: **independently executed agents can still have statistically dependent errors because they share the same information representation and interpretive priors.**

If appropriate for the estimator, explain:

\[
n_{\mathrm{eff}} \approx \frac{k}{1+(k-1)\rho}
\]

State its assumptions and provide uncertainty intervals.

### 2. Groupthink and social influence

Use Janis’s *Victims of Groupthink* cautiously. Classic groupthink concerns cohesion, conformity pressure, and suppressed dissent. Your agents apparently do not influence one another.

Therefore write:

> This resembles groupthink in outcome—unanimous error—but not in mechanism. The convergence arises without interpersonal conformity, suggesting a distinct pathway: shared-input or representational monoculture.

That distinction is more valuable than loosely labeling the phenomenon “AI groupthink.”

### 3. Common ground and grounding

Clark and Brennan define grounding as the process through which collaborators establish mutual understanding sufficient for present purposes (1991, DOI [10.1037/10096-006](https://doi.org/10.1037/10096-006)).

The disambiguator manipulation can be framed as a **grounding-resource boundary**:

- In-prompt context becomes available to the interpretive process.
- Out-of-prompt context is lost at the handoff.
- Agreement downstream cannot repair an upstream grounding failure.

Do not claim that non-interacting agents themselves establish common ground. Instead, describe the retained prompt as their common information environment.

### 4. Automation bias and appropriate reliance

Automation misuse and overreliance are established concerns (Parasuraman and Riley, 1997, DOI [10.1518/001872097778543886](https://doi.org/10.1518/001872097778543886); Skitka et al., 1999, DOI [10.1006/ijhc.1999.0252](https://doi.org/10.1006/ijhc.1999.0252)).

Connect your work to the CSCW 2023 honorable-mention paper showing that explanations reduce overreliance when they lower verification cost ([Vasconcelos et al.](https://arxiv.org/abs/2212.06823); DOI [10.1145/3579605](https://doi.org/10.1145/3579605)).

Your implication: displaying “5/5 agents agree” may create stronger reliance while adding almost no independent evidence. Interfaces should expose provenance, interpretation, and dependence—not agent count alone.

### 5. Algorithmic monoculture

Kleinberg and Raghavan show that widespread reliance on the same algorithm can reduce system-level welfare despite strong individual accuracy (2021, DOI [10.1073/pnas.2018340118](https://doi.org/10.1073/pnas.2018340118)).

Your paper identifies a related within-ensemble phenomenon: even nominally heterogeneous models can form an **interpretive monoculture** when the decisive context is uniformly absent.

---

## 5. Recommended outline for this paper

### Title options

1. **When Consensus Lies: Correlated Interpretive Failure in Multi-Agent LLM Ensembles**
2. **Consensus Without Independence: Fake Redundancy in AI-Assisted Collective Judgment**
3. **Five Agents, One Mistake: Silent Consensus Failure Under Underspecified Prompts**
4. **The Illusion of Corroboration: When Diverse LLM Agents Converge on the Same Wrong Interpretation**
5. **Lost Context, False Consensus: Information Boundaries in Multi-Agent AI Systems**

Option 2 is strongest for CSCW; Option 1 best preserves the project identity.

### Abstract shape

1. Collaborative systems increasingly aggregate multiple AI judgments as though agreement supplied corroboration.
2. Crowd wisdom requires sufficiently independent errors, but shared information boundaries may violate this assumption.
3. Describe the executable-gold benchmark, preregistration, model families/tiers, and disambiguator manipulation.
4. Report the main numerical result, including wrong-consensus rate, \(\rho\), and effective ensemble size.
5. State the in-prompt boundary condition.
6. Conclude with implications: preserve context/provenance, elicit interpretations before voting, and measure dependence rather than counting agents.

### Introduction contribution paragraph

> This paper makes four contributions. First, we provide preregistered empirical evidence of silent consensus failure across independently queried LLM agents spanning capability tiers and model families. Second, we introduce an executable-gold method for isolating whether task-disambiguating context crosses the retained prompt boundary. Third, we quantify fake redundancy through correlated error and effective ensemble size, showing when nominally \(k\)-agent systems supply approximately one independent judgment. Fourth, we derive implications for AI-mediated collaborative decision systems: consensus displays should expose interpretive and evidential dependence, preserve contextual provenance, and solicit competing task interpretations before aggregating answers.

### Section plan

1. **Introduction**
2. **Consensus, Grounding, and AI-Mediated Collective Judgment**
   - Wisdom-of-crowds assumptions
   - Grounding and information boundaries
   - Automation reliance and algorithmic monoculture
   - LLM ensembles and multi-agent systems
3. **Research Questions and Hypotheses**
4. **Executable-Gold Benchmark**
   - Construct definition
   - Item generation and validation
   - Disambiguator manipulation
5. **Preregistered Study**
   - Models, tiers, families, independence protocol
   - Outcomes and estimands
   - Statistical analysis
6. **Results**
   - Manipulation check
   - Wrong consensus
   - Cross-tier/family results
   - Error dependence and effective ensemble size
   - In-prompt resolution
   - Robustness and nulls
7. **Discussion**
   - Consensus without epistemic independence
   - Shared-input failure versus groupthink
   - Information loss as a sociotechnical failure
8. **Implications for CSCW and Collaborative AI**
9. **Limitations, Ethics, and Open Science**
10. **Conclusion**

---

## 6. Acceptance checklist

### Emphasize

- [ ] Consensus is a social/institutional signal, not just majority vote.
- [ ] The benchmark tests a specific cooperative-system assumption.
- [ ] “Independent calls” are distinguished from independent evidence and interpretations.
- [ ] The executable gold establishes correctness independently of model agreement.
- [ ] External disambiguators are realistic omitted context, not adversarial trivia.
- [ ] Preregistered outcomes are clearly separated from exploratory analyses.
- [ ] Deviations and exclusions are disclosed.
- [ ] Confidence intervals accompany \(\rho\), wrong-consensus rates, and effective size.
- [ ] Family/tier nulls are treated as theoretically informative.
- [ ] The in-prompt success condition is foregrounded as a constructive boundary condition.
- [ ] Claims about humans, organizations, and high-stakes domains are labeled implications unless directly studied.
- [ ] Design implications are traceable to findings.

### Recommended design implications

1. Preserve the provenance and scope of context across agent handoffs.
2. Ask agents to state task interpretations before solving.
3. Aggregate interpretations and evidence before aggregating answers.
4. Diversify information sources, retrieval paths, and representations—not merely model vendors.
5. Estimate error dependence during validation.
6. Replace “5/5 agents agree” with dependence-aware uncertainty displays.
7. Trigger human review when consensus is high but contextual completeness is uncertain.
8. Maintain dissent channels rather than forcing early convergence.

---

## 7. PACM HCI / CSCW format facts

- CSCW papers are published in *Proceedings of the ACM on Human-Computer Interaction*.
- The current CSCW 2026 guidance requires the ACM journal template with the `acmsmall` call—not the traditional `sigchi` proceedings format.
- Papers below 5,000 words or above 12,000 words receive additional scrutiny; contribution must be commensurate with length.
- Appendices may be submitted, but reviewers are not required to consider them.
- Review submissions are anonymous.
- The current CFP encourages preregistration, FAIR materials, and reproducibility statements.
- CCS Concepts and author keywords are generated through the standard `acmart` workflow.
- Verify exact class options against the target cycle’s official template; future-cycle requirements may change ([CSCW 2026 formatting guidance](https://cscw.acm.org/2026/papers.html)).

**Ethics statement:** An explicit paper-track ethics-section mandate was not confirmed on the cited CFP—**UNVERIFIED**. Nevertheless, include a short ethics section covering benchmark construction, API/data handling, environmental/resource costs, model-provider terms, release risks, and whether human-subjects review was applicable.

**Important LLM-writing policy:** CSCW 2026 states that LLM-generated text used beyond editing authors’ own text must be marked and warns against using AI to generate manuscript ideas or fake references. Independently verify every citation, rewrite all prose, and follow the target cycle’s disclosure policy; do not paste this guide directly into a submission ([CSCW 2026, “Policy on Use of Large Language Models in Writing Papers”](https://cscw.acm.org/2026/papers.html)).
