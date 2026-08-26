# Ethics protocol summary — human-reliance study

Companion notes for the **HKUST(GZ) Human Research Ethics Protocol** (HAREC). Minimal-risk, with
**authorized (mild) deception + full debrief**. The detailed field-by-field filling guide lives outside
this repository; this file is the short internal summary.

- **Title:** Do people over-rely on unanimous multi-model AI "consensus," and does surfacing its
  mechanism reduce it?
- **PI / contact:** Weikai Yang, The Hong Kong University of Science and Technology (Guangzhou),
  weikaiyang@hkust-gz.edu.cn. **Do not begin confirmatory data collection before the HAREC determination
  is issued and the approved consent text is live in the application.**
- **Purpose:** Test whether a "5 of 5 AI models agree" display raises acceptance/confidence in an answer
  to an underspecified task vs a single-model answer (H-U1), and whether disclosing that the five models
  share the same prompt (so their agreement is not five independent checks) reduces it (H-U2). Companion
  to the system paper *When Consensus Lies*.
- **Design/procedures:** Online, ~11 min, single session, bilingual (English / 简体中文). Language choice
  → consent → instructions → a non-scored worked example → comprehension check → **14 short trials** (each:
  a workplace scenario + task + an AI answer shown as single-model / "5/5 agree" / dependence-mechanism
  disclosure; participant chooses use-as-is vs flag-missing-info, optionally picks a clarifying question,
  and gives a 1–5 star rating of confidence in the displayed AI answer itself) → 1 attention check →
  brief demographics → **debrief**. 9 items are
  underspecified (missing a convention) and 5 are well-specified.
- **Participants:** Recruit up to 200 seats to obtain roughly 65–90 analyzable participants.
  **Adults aged 18 or above only**; no guardian-consent procedure is used. The age restriction is
  implemented through the recruitment channel (the link circulates only within adult networks), the
  consent page asks participants to confirm they are 18 or above, and any response indicating an age
  below 18 is deleted without being analysed. Recruited via a team/local channel (university networks /
  WeChat); **not** Prolific.
- **Recruitment/compensation:** Team-recruited volunteers; no payment.
- **Risks:** Minimal — brief, non-sensitive workplace judgments; no distressing content. **Deception
  (mild):** the AI "answers" and the "5/5 agreement" are **curated illustrations**, not live model outputs;
  participants may assume they are real. **Justification:** the research question (response to *apparent*
  unanimous consensus) requires controlled consensus displays; risk is minimal and there is no reasonable
  non-deceptive alternative. **Mitigation:** the consent states some details are withheld until the end; a
  **full debrief** discloses the curation and purpose.
- **Benefits:** No direct benefit; advances understanding of trust in multi-model AI interfaces.
- **Privacy/data:** No direct identifiers; no IP address and no location are recorded. Only an
  automatically generated anonymous oTree participant code is stored, alongside task responses. Stored
  de-identified and retained per the approved protocol; aggregate/anonymized results may be shared
  publicly (e.g., OSF) with the paper. Because recruitment uses a single open anonymous link, repeat
  participation is neither restricted nor detectable.
- **Voluntariness:** Fully voluntary; withdraw anytime by closing the window.
- **Pre-registration:** Hypotheses, design, primary DVs, exclusions, and analysis frozen on OSF/AsPredicted
  before confirmatory data collection (`PREREGISTRATION.md`, `analysis/`). A pre-freeze design-validation
  pilot was run on an earlier version of the instrument and its data are excluded; the go/no-go function is
  carried out as an interim instrument check at the first 20 completers, which examines no condition
  contrast (`PREREGISTRATION.md` §11).
