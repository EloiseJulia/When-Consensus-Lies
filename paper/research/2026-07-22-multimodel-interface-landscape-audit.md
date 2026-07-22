---
title: "Landscape Analysis of Same-Prompt Multi-Model AI Comparison Interfaces"
paper: "When Consensus Lies"
venue-target: CHI
document-type: landscape-audit
audit-date: 2026-07-22
author: research-subagent (on behalf of main agent)
status: draft-for-paper
---

# Landscape Analysis of Same-Prompt Multi-Model AI Comparison Interfaces

*Prepared for: "When Consensus Lies" — CHI submission*
*Audit snapshot date: 2026-07-22*

---

## 1. Purpose and Scope

This document establishes, through a survey of publicly accessible product materials, that a growing class of multi-model interfaces exists in which users submit a single prompt to multiple language models simultaneously and observe or aggregate the resulting responses. The purpose is to:

1. Verify that each surveyed platform genuinely supports same-prompt multi-model querying;
2. Characterize, through a coded audit table, the interaction affordances these interfaces offer around comparison, consensus, synthesis, and (critically) the absence of input-quality or context-completeness signals;
3. Synthesize what the landscape collectively suggests about how plurality of models is framed for end users.

This analysis draws exclusively on publicly accessible product homepages, official documentation, official blog posts, and open-source repository README files. It is a design-artifact audit, not a user study, usability evaluation, or market-share analysis.

---

## 2. Platform Selection and Verification

### 2.1 Verified Platforms (Final Audit Set)

Nine platforms were verified as operationally supporting same-prompt multi-model comparison as of the audit date.

| # | Platform | Official URL | Type |
|---|----------|--------------|------|
| 1 | **ChatHub** | https://chathub.gg | Web app + browser extension |
| 2 | **Open WebUI** | https://openwebui.com | Self-hosted open-source web UI |
| 3 | **PromptQuorum** | https://www.promptquorum.com | Web app (public beta: Aug 2026) |
| 4 | **MultipleChat** | https://multiple.chat | Web platform |
| 5 | **Poe** (by Quora) | https://poe.com | Consumer web + mobile app |
| 6 | **LMArena / Chatbot Arena** | https://arena.ai (formerly lmarena.ai) | Research-oriented evaluation platform |
| 7 | **TypingMind** | https://typingmind.com | Web app (BYO API-key) |
| 8 | **LibreChat** | https://librechat.ai | Self-hosted open-source web UI |
| 9 | **Google AI Studio Compare Mode** | https://aistudio.google.com | Developer-facing web tool |

### 2.2 Seed Platforms Dropped or Reclassified

| Seed Platform | Disposition | Reason |
|---------------|-------------|--------|
| **Consensus** (consensus.app) | **Excluded** | Consensus.app is an AI-powered academic literature search engine that surfaces scientific consensus *from peer-reviewed papers*, not a platform for querying multiple language models with the same prompt. Its "consensus meter" reflects agreement across the scholarly literature, not across LLM outputs. The name overlap could be confusing in the paper; a clarifying footnote is recommended. Verified via: https://consensus.app (accessed 2026-07-22) and https://openai.com/index/consensus/ |
| **AskManyAI** (askmany.ai) | **Excluded** | The official site at https://askmany.ai returns "Site will be available soon. Thank you for your patience!" as of 2026-07-22. The platform cannot be independently verified as currently operational. |

---

## 3. Audit Coding Table

**Coding key:**
- ✓ = Feature clearly present; direct evidence in public materials
- ✗ = Feature absent; no evidence in public materials
- ~ = Partial or implicit; inferrable but not explicitly described

**Dimensions:**
- **(a)** Broadcasts one prompt to multiple models
- **(b)** Shows model/vendor names
- **(c)** Parallel side-by-side answers displayed
- **(d)** Computes agreement / consensus score
- **(e)** Automatic majority vote or verdict
- **(f)** Synthesized / merged single answer
- **(g)** Highlights disagreement between models
- **(h)** Shows sources / citations
- **(i)** Signals that all models share the same input (explicit prompt parity framing)
- **(j)** Warns that the prompt may be missing information / context
- **(k)** Asks models to disclose task interpretation before answering
- **(l)** Product materials frame multi-model use as improving trust, confidence, accuracy, or verification

---

### ChatHub — https://chathub.gg

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | "Get insights from ChatGPT, Claude, Gemini, and more – all at once!" — chathub.gg homepage (2026-07-22) |
| (b) | ✓ | Named panels for GPT-5, Claude 4.5, Gemini 3, DeepSeek, Grok, Llama — chathub.gg (2026-07-22) |
| (c) | ✓ | "Side-by-side response comparison: Instantly see how models differ in handling the same prompt." — chathub.gg (2026-07-22) |
| (d) | ✗ | No consensus scoring described in public materials |
| (e) | ✗ | No automatic vote |
| (f) | ✗ | No merge/synthesis feature described |
| (g) | ~ | Visual comparison is available; no automated disagreement highlighting |
| (h) | ✗ | No citation/source display in public materials |
| (i) | ~ | Same prompt box dispatches to all; not foregrounded in framing language |
| (j) | ✗ | No missing-context warning |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ✓ | **"Any single AI can hallucinate. Get multiple perspectives to gain confidence."** — chathub.gg feature section, "One question, multiple AI responses" (2026-07-22) |

---

### Open WebUI — https://openwebui.com / https://docs.openwebui.com

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | "your prompt is sent to two or more selected models at the same time" — docs.openwebui.com/features/chat-conversations/chat-features/multi-model-chats/ (2026-07-22) |
| (b) | ✓ | Model selector shows named models (GPT-5.1, Gemini 3, Claude Sonnet 4.5, etc.) — docs.openwebui.com (2026-07-22) |
| (c) | ✓ | "Their responses are displayed in parallel columns (or stacked, depending on screen size)" — docs.openwebui.com/features/.../multi-model-chats/ (2026-07-22) |
| (d) | ✗ | No automated consensus scoring |
| (e) | ✗ | No automatic vote |
| (f) | ✓ | "Mixture of Agents (MOA)" Merge button: "takes the outputs from all your active models and sends them...to a 'Synthesizer Model'" — docs.openwebui.com (2026-07-22) |
| (g) | ~ | "If two models say X and one says Y, you can investigate further" — docs.openwebui.com, Fact Validation use-case (2026-07-22); described as user-initiated, not automated |
| (h) | ✗ | No built-in citation panel in multi-model mode |
| (i) | ~ | Implicit; same input dispatched simultaneously but not foregrounded as parity signal |
| (j) | ✗ | No missing-context warning |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ✓ | "Reduced Hallucinations: The synthesizer model can filter out inconsistencies found in individual responses." — docs.openwebui.com, Advantages of Merging (2026-07-22); also: "Research suggests that aggregating outputs from multiple models often outperforms any single model acting alone." — ibid. |

---

### PromptQuorum — https://www.promptquorum.com

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | "PromptQuorum lets you send a single prompt to 25+ leading AI models simultaneously" — promptquorum.com (2026-07-22); GitHub README: github.com/PromptQuorum/promptquorum (2026-07-22) |
| (b) | ✓ | GPT-4o, Claude 4.6 Sonnet, Gemini 2.5 Pro, Mistral Large, DeepSeek named — promptquorum.com (2026-07-22) |
| (c) | ✓ | "Side-by-side Comparison — See every model's response in a clean, scannable layout" — GitHub README (2026-07-22) |
| (d) | ✓ | "Consensus Verdict — PromptQuorum aggregates and compares outputs to surface the most agreed-upon answer" — GitHub README (2026-07-22) |
| (e) | ✓ | **"Stop guessing which AI gives the best answer. Let them vote."** — GitHub README (2026-07-22) |
| (f) | ✗ | Consensus verdict is a score/aggregate, not a synthesized prose answer |
| (g) | ✓ | "scores the results for consensus and **hallucination risk**" — promptquorum.com (2026-07-22); blog: "Claim-level extraction surfaces disagreements that a quick read would miss" — promptquorum.com/blog/what-is-ai-consensus-scoring (2026-07-22) |
| (h) | ✗ | No cited sources feature described |
| (i) | ✓ | Tagline: "One Prompt. 25+ AI Responses." — promptquorum.com (2026-07-22) |
| (j) | ✗ | No missing-context warning |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ✓ | "consensus scoring produces a structured, auditable signal you can reference and share" — promptquorum.com/blog/what-is-ai-consensus-scoring (2026-07-22) |

---

### MultipleChat — https://multiple.chat

*Note: multiple.chat returns HTTP 403 for automated requests; all evidence is from search-indexed public materials, including multiple.chat sub-pages indexed by search engines and the platform's own marketing articles.*

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | "You can send a single prompt to several leading large language models (LLMs) such as ChatGPT, Claude, Gemini, and Grok at once." — multiple.chat/ai-model-comparison-tool (indexed 2026-07-22) |
| (b) | ✓ | ChatGPT, Claude, Gemini, Grok explicitly named — multiple.chat (2026-07-22) |
| (c) | ✓ | "Answers are shown side-by-side" — multiple.chat/compare-ai-models (indexed 2026-07-22) |
| (d) | ✓ | Consensus / team mode: "assign models to work together as a 'team'" with "Smart Chain, Debate, Ensemble, Simulation, Expert" modes — multiple.chat/collaborative-ai (indexed 2026-07-22) |
| (e) | ~ | Ensemble/team mode aggregates; not described as strict majority vote |
| (f) | ✓ | Ensemble mode described as synthesizing one stronger answer — multiple.chat/collaborative-ai (indexed 2026-07-22) |
| (g) | ✓ | "Disagreements are surfaced and become signals for deeper reasoning." — multiple.chat/collaborative-ai (indexed 2026-07-22) |
| (h) | ~ | "web-aided" mode adds web sources — multiple.chat/features (indexed 2026-07-22) |
| (i) | ✓ | Comparison tool explicitly frames same-prompt dispatch — multiple.chat/ai-model-comparison-tool (indexed 2026-07-22) |
| (j) | ✗ | No missing-context warning in public materials |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ✓ | "auto-verification to reduce hallucination risk" — multiple.chat/features (indexed 2026-07-22); dedicated page: multiple.chat/reduce-ai-hallucinations (indexed 2026-07-22) |

---

### Poe (by Quora) — https://poe.com

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | "@-mention each bot you want to query, add your message, and watch as all the selected models respond" — poe.com/pages/demos/send-multiple-messages-at-the-same-time (2026-07-22) |
| (b) | ✓ | Model identities shown via @-mention names (e.g., @Claude-3, @GPT-4) — poe.com/blog/multi-bot-chat-on-poe (2026-07-22) |
| (c) | ~ | Responses appear in the same thread; strictly serial in thread display rather than columnar side-by-side |
| (d) | ✗ | No automated consensus computation |
| (e) | ✗ | No automatic vote |
| (f) | ✗ | No merge feature in multi-bot chat |
| (g) | ~ | Users can visually compare in thread; no automated highlighting |
| (h) | ~ | Web Search bot can be summoned to add sources, but is separate from multi-model comparison |
| (i) | ~ | Implicit in the @-mention multi-send; not foregrounded as parity framing |
| (j) | ✗ | No missing-context warning |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ~ | "easily compare results from various bots and discover optimal combinations of models to use the best tool for each step in a workflow" — poe.com/blog/multi-bot-chat-on-poe (2026-07-22); trust/confidence framing is present but softer than other platforms |

---

### LMArena / Chatbot Arena — https://arena.ai (formerly lmarena.ai)

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | User submits one prompt; system sends it to two anonymous models — arena.ai / lmarena.ai (2026-07-22); original LMSYS blog post: "Chatbot Arena: Benchmarking LLMs in the Wild with Elo Ratings", lmsys.org/blog/2023-05-03-arena/ |
| (b) | ✗ | **Model identities are deliberately hidden until after the user votes** — blind evaluation design |
| (c) | ✓ | Side-by-side blind comparison is the core interaction — arena.ai (2026-07-22) |
| (d) | ✗ | No automated consensus; user votes determine preference |
| (e) | ✗ | Human vote is user-initiated, not automatic |
| (f) | ✗ | No synthesis feature |
| (g) | ~ | Side-by-side layout allows users to detect differences; not automated |
| (h) | ✗ | No citation/source display |
| (i) | ✓ | Same prompt explicitly submitted to both models; parity is structurally enforced |
| (j) | ✗ | No missing-context warning |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ~ | Framed primarily as a research/benchmarking tool (Elo leaderboard); trust/confidence claims are indirect (leaderboard reflects human preference) |

---

### TypingMind — https://typingmind.com

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | "Multi-model response enables you to run the **same prompt across several AI models simultaneously**." — docs.typingmind.com/manage-and-connect-ai-models/activate-multi-model-responses (2026-07-22) |
| (b) | ✓ | GPT-4.1, Claude Sonnet 4, Gemini 2.5 Pro named in documentation — docs.typingmind.com (2026-07-22) |
| (c) | ✓ | "view how different models—such as GPT-4.1, Claude Sonnet 4, Gemini 2.5 Pro—respond to the same input in TypingMind interface" — docs.typingmind.com (2026-07-22) |
| (d) | ✗ | No consensus scoring |
| (e) | ✗ | No automatic vote |
| (f) | ✓ | **"Finalize Mode...allows you to merge responses from multiple AI models into one final answer"** — docs.typingmind.com (2026-07-22) |
| (g) | ✗ | No automated disagreement highlighting |
| (h) | ✗ | No source/citation display |
| (i) | ✓ | "TypingMind sends your prompt to multiple selected AI models at once. Each model generates its own independent response" — docs.typingmind.com (2026-07-22) |
| (j) | ✗ | No missing-context warning |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ~ | "especially useful for comparing outputs, evaluating model performance, or gathering diverse perspectives on a prompt" — docs.typingmind.com (2026-07-22); confidence framing is implicit |

---

### LibreChat — https://librechat.ai

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | Sends same prompt to multiple configured providers — librechat.ai/docs (2026-07-22); confirmed by: "side-by-side model comparison" — docs.openwebui.com/alternatives/librechat/ (2026-07-22) |
| (b) | ✓ | Provider/model names shown (OpenAI, Anthropic, Google, Azure, Ollama) — librechat.ai (2026-07-22) |
| (c) | ✓ | "Model comparison with side-by-side responses from different models in a single conversation" — docs.openwebui.com/alternatives/librechat/ (2026-07-22) |
| (d) | ✗ | No automated consensus |
| (e) | ✗ | No automatic vote |
| (f) | ✗ | No merge/synthesis feature described in current public materials |
| (g) | ~ | Side-by-side display enables manual comparison; no automated highlighting |
| (h) | ✗ | No citation/source display for multi-model mode |
| (i) | ~ | Implicit; same input dispatched across providers |
| (j) | ✗ | No missing-context warning |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ~ | Framed as enabling "clean, focused multi-provider chat interface with strong model comparison features" for research and evaluation — docs.openwebui.com/alternatives/librechat/ (2026-07-22); explicit trust claims absent |

---

### Google AI Studio Compare Mode — https://aistudio.google.com

| Dim | Code | Evidence quote + source |
|-----|------|------------------------|
| (a) | ✓ | "Provide a prompt, and optional system instructions, and Compare Mode will display the outputs from various models" — developers.googleblog.com/compare-mode-in-google-ai-studio/ (2026-07-22) |
| (b) | ✓ | Gemini/Gemma model variants named and selectable — aistudio.google.com (2026-07-22) |
| (c) | ✓ | Side-by-side display explicitly described — developers.googleblog.com/compare-mode-in-google-ai-studio/ (2026-07-22) |
| (d) | ✗ | No consensus scoring; focuses on quality/latency/cost metrics |
| (e) | ✗ | No automatic vote |
| (f) | ✗ | No merge/synthesis |
| (g) | ~ | Differences in response quality, latency, and cost are surfaced; textual disagreement not highlighted |
| (h) | ✗ | No citation display |
| (i) | ✓ | "Provide a prompt...Compare Mode will display the outputs from various models" — prompt parity is structurally enforced — developers.googleblog.com (2026-07-22) |
| (j) | ✗ | No missing-context warning |
| (k) | ✗ | No interpretation-disclosure step |
| (l) | ✓ | "Compare Mode helps you **confidently** select the best model for your use case." — developers.googleblog.com/compare-mode-in-google-ai-studio/ (2026-07-22) |

---

## 4. Consolidated Feature Summary Table

| Platform | (a) Broadcast | (b) Names | (c) Side-by-side | (d) Consensus score | (e) Auto vote | (f) Synthesis | (g) Disagree highlight | (h) Sources | (i) Prompt parity framing | (j) Missing-context warn | (k) Interpret disclose | (l) Trust/conf claim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ChatHub | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ~ | ✗ | ~ | **✗** | **✗** | ✓ |
| Open WebUI | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ~ | ✗ | ~ | **✗** | **✗** | ✓ |
| PromptQuorum | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ | **✗** | **✗** | ✓ |
| MultipleChat | ✓ | ✓ | ✓ | ✓ | ~ | ✓ | ✓ | ~ | ✓ | **✗** | **✗** | ✓ |
| Poe | ✓ | ✓ | ~ | ✗ | ✗ | ✗ | ~ | ~ | ~ | **✗** | **✗** | ~ |
| LMArena | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ~ | ✗ | ✓ | **✗** | **✗** | ~ |
| TypingMind | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | **✗** | **✗** | ~ |
| LibreChat | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ~ | ✗ | ~ | **✗** | **✗** | ~ |
| Google AI Studio | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ~ | ✗ | ✓ | **✗** | **✗** | ✓ |
| **Column total (✓)** | 9/9 | 8/9 | 8/9 | 2/9 | 1/9 | 3/9 | 0 firm | 0 firm | 5/9 | **0/9** | **0/9** | 6/9 |

*Bold ✗ columns (j, k) show zero presence across all nine platforms.*

---

## 5. Synthesis: What the Landscape Offers and What It Withholds

### 5.1 What Is Commonly Offered: Plurality, Comparison, and Corroboration Framing

A growing class of multi-model interfaces allows users to query multiple AI language models with a single prompt and observe their responses in parallel. All nine platforms surveyed here support simultaneous or rapid-sequential dispatch of one prompt to at least two models (dimension a), and eight of nine display model names transparently (dimension b). Eight of nine offer some form of side-by-side visual comparison (dimension c). Across these platforms, the single-prompt broadcast mechanism is treated not as a convenience feature but as an epistemic one: querying multiple models with the same text is presented as a means of achieving greater confidence, reducing hallucination risk, or obtaining a more reliable answer.

This corroboration framing is explicit in six of the nine platforms surveyed (dimension l). ChatHub states directly: *"Any single AI can hallucinate. Get multiple perspectives to gain confidence"* (chathub.gg, 2026-07-22). Open WebUI's documentation promises that its Mixture-of-Agents merge reduces hallucinations because *"the synthesizer model can filter out inconsistencies found in individual responses"* (docs.openwebui.com, 2026-07-22). PromptQuorum's tagline reads *"Stop guessing which AI gives the best answer. Let them vote"* and frames its consensus verdict as *"a structured, auditable signal you can reference and share"* (promptquorum.com/blog, 2026-07-22). Google AI Studio's developer blog invites users to *"confidently select the best model for your use case"* after running Compare Mode (developers.googleblog.com, 2026-07-22). MultipleChat promotes *"auto-verification to reduce hallucination risk"* as a built-in feature (multiple.chat/features, 2026-07-22). In each case, the implicit argument is that model plurality functions as evidence plurality — that agreement across independently responding models signals factual reliability.

### 5.2 What Is Less Common: Automation of Agreement

More advanced corroboration features — computed consensus scores (dimension d) and automatic majority-vote verdicts (dimension e) — are currently available in only a minority of platforms. PromptQuorum is the most explicit, computing a numerical consensus verdict across 25+ models. MultipleChat offers an "Ensemble" team mode that synthesizes a joint output. Only three of nine platforms offer response synthesis/merging (dimension f: Open WebUI, MultipleChat, TypingMind), which takes the plurality of outputs and collapses them into a single answer. Disagreement highlighting (dimension g) is present in some form in most platforms, but it is almost universally user-initiated or visually implicit — no platform in this survey automatically surfaces or labels structural disagreements with accompanying interpretation. Source/citation display (dimension h) is essentially absent from multi-model comparison views, with only MultipleChat offering a partial implementation via its "web-aided" collaboration mode.

### 5.3 What Is Absent: Input-Quality Signals

The most consistent gap across all nine platforms is the complete absence of three input-side affordances. No platform audited here (dimension j) warns users that a submitted prompt may be missing information, context, or background necessary for the models to answer accurately. No platform (dimension k) instructs models to disclose their interpretation of an ambiguous task before responding. No platform (dimension i in a strong sense) foregrounds prompt parity as a limitation rather than as a strength — that is, none signals that if the prompt is under-specified, multiple models receiving the same under-specified prompt will not produce independent evidence. This absence is structurally consistent across interaction styles ranging from consumer (Poe, ChatHub) to developer (Google AI Studio, LibreChat) to research (LMArena) to enterprise (MultipleChat, TypingMind) contexts.

### 5.4 The Asymmetry as a Design Pattern

The landscape thus reveals a systematic asymmetry in interface design: output-side diversity is richly supported and actively marketed, while input-side adequacy is unexamined by the interface. Users receive affordances for comparing, synthesizing, voting on, and merging multiple model outputs; they receive no affordances for assessing whether those outputs rest on a shared, under-specified, or systematically incomplete input. Insofar as these platforms invoke plurality as a basis for confidence — as most do — the design implicitly treats the shared prompt as a neutral conduit rather than as a potential locus of epistemic failure.

This asymmetry motivates the theoretical contribution of the present paper: when multiple models receive the same ambiguous or context-deficient prompt, what appears to be independent corroboration is structurally dependent, not independent, evidence. The interface landscape surveyed here does not disclose this dependence, and in several cases actively markets the inverse claim.

---

## 6. Limitations of This Audit

1. **Public-materials only.** All codings are based on publicly accessible product homepages, official documentation, blog posts, and open-source repository README files retrieved on 2026-07-22. Internal features, beta-only features, enterprise-tier features, or features not described in public marketing materials are not captured.

2. **Snapshot date.** Software products update frequently. Feature availability, marketing copy, and interface design may have changed between the audit date (2026-07-22) and the date of this paper's review. No version pinning is possible for hosted web applications.

3. **No hands-on interaction.** This audit does not include live interaction with the platforms. Feature presence is coded from descriptive materials, not from direct interaction testing. Some coded features (particularly dimension g, "highlights disagreement") are difficult to assess precisely from documentation alone and are therefore conservatively marked as partial (∼).

4. **Platform scope.** Nine platforms were selected from a much larger possible set. The selection is representative of major categories (browser extension, self-hosted open-source, consumer web app, developer tool, research platform) but is not exhaustive. Rapidly emerging platforms and region-specific tools are not captured.

5. **Not a usability or user-study.** This audit characterizes design affordances as described in product materials. It does not measure user behavior, user beliefs, or the actual epistemic effects of using these platforms.

6. **MultipleChat direct verification.** The multiple.chat domain returned HTTP 403 for all automated fetch attempts; all evidence for this platform was sourced from search-indexed public materials including the platform's own sub-pages (multiple.chat/ai-model-comparison-tool, multiple.chat/collaborative-ai, multiple.chat/features). The platform's existence and described features are confirmed through multiple independent indexed sources.

7. **PromptQuorum beta status.** PromptQuorum is publicly described as launching in public beta in August 2026 (github.com/PromptQuorum/promptquorum). The platform's homepage and GitHub README are fully accessible and describe the intended feature set clearly; some features may not yet be fully deployed.

---

## 7. Bibliography (Ready-to-Cite)

All URLs accessed 2026-07-22 unless otherwise noted.

### ChatHub
```
@misc{chathub2026,
  title        = {{ChatHub} — {GPT-5}, {Claude 4.5}, {Gemini 3} side by side},
  howpublished = {\url{https://chathub.gg}},
  note         = {Accessed: 2026-07-22},
  year         = {2026}
}
```

### Open WebUI — Multi-Model Chats Documentation
```
@misc{openwebui2026multimodel,
  title        = {Multi-Model Chats — {Open WebUI} Documentation},
  howpublished = {\url{https://docs.openwebui.com/features/chat-conversations/chat-features/multi-model-chats/}},
  note         = {Accessed: 2026-07-22},
  year         = {2026}
}
```

### Open WebUI — LibreChat Comparison Page
```
@misc{openwebui2026librechat,
  title        = {{Open WebUI} vs {LibreChat}},
  howpublished = {\url{https://docs.openwebui.com/alternatives/librechat/}},
  note         = {Accessed: 2026-07-22},
  year         = {2026}
}
```

### PromptQuorum — Homepage
```
@misc{promptquorum2026home,
  title        = {{PromptQuorum} — {AI} Prompt Optimization Across 25+ Models},
  howpublished = {\url{https://www.promptquorum.com}},
  note         = {Accessed: 2026-07-22},
  year         = {2026}
}
```

### PromptQuorum — GitHub README
```
@misc{promptquorum2026github,
  title        = {{PromptQuorum/promptquorum}: Multi-model {AI} prompt tool},
  howpublished = {\url{https://github.com/PromptQuorum/promptquorum}},
  note         = {Accessed: 2026-07-22},
  year         = {2026}
}
```

### PromptQuorum — Consensus Scoring Blog
```
@misc{promptquorum2026blog,
  title        = {What Is {AI} Consensus Scoring? Multi-Model Agreement (2026)},
  howpublished = {\url{https://www.promptquorum.com/blog/what-is-ai-consensus-scoring}},
  note         = {Accessed: 2026-07-22},
  year         = {2026}
}
```

### MultipleChat — Homepage / Features
```
@misc{multiplechat2026,
  title        = {{MultipleChat} — Access to {ChatGPT}, {Claude}, {Gemini} and {Grok}},
  howpublished = {\url{https://multiple.chat}},
  note         = {Accessed: 2026-07-22 (via search-indexed materials)},
  year         = {2026}
}
```

### MultipleChat — Collaborative AI
```
@misc{multiplechat2026collab,
  title        = {{AI} Collaboration — Multi-Model Reasoning System — {MultipleChat}},
  howpublished = {\url{https://multiple.chat/collaborative-ai}},
  note         = {Accessed: 2026-07-22 (via search-indexed materials)},
  year         = {2026}
}
```

### Poe — Multi-bot Chat Announcement
```
@misc{poe2024multibot,
  title        = {Multi-bot chat on {Poe}},
  author       = {{Quora, Inc.}},
  howpublished = {\url{https://poe.com/blog/multi-bot-chat-on-poe}},
  note         = {Published: April 15, 2024; Accessed: 2026-07-22},
  year         = {2024}
}
```

### Poe — Send Multiple Messages Demo
```
@misc{poe2025multisend,
  title        = {Send multiple messages at the same time — {Poe}},
  author       = {{Quora, Inc.}},
  howpublished = {\url{https://poe.com/pages/demos/send-multiple-messages-at-the-same-time}},
  note         = {Published: February 16, 2025; Accessed: 2026-07-22},
  year         = {2025}
}
```

### LMArena / Chatbot Arena
```
@misc{lmarena2026,
  title        = {{LMArena} — {AI} Ranking \& {LLM} Leaderboard},
  howpublished = {\url{https://arena.ai}},
  note         = {Formerly lmarena.ai; Accessed: 2026-07-22},
  year         = {2026}
}
```

### Chatbot Arena Original Paper
```
@inproceedings{zheng2023chatbot,
  title        = {Judging {LLM}-as-a-{Judge} with {MT}-{Bench} and {Chatbot} Arena},
  author       = {Zheng, Lianmin and Chiang, Wei-Lin and Sheng, Ying and others},
  booktitle    = {Advances in Neural Information Processing Systems},
  year         = {2023},
  url          = {https://www.lmsys.org/blog/2023-05-03-arena/}
}
```

### TypingMind — Multi-Model Responses Documentation
```
@misc{typingmind2026,
  title        = {Multi-model Responses — {TypingMind} Docs},
  howpublished = {\url{https://docs.typingmind.com/manage-and-connect-ai-models/activate-multi-model-responses}},
  note         = {Accessed: 2026-07-22},
  year         = {2026}
}
```

### LibreChat — Official Documentation
```
@misc{librechat2026,
  title        = {{LibreChat} Documentation},
  howpublished = {\url{https://www.librechat.ai/docs}},
  note         = {Accessed: 2026-07-22},
  year         = {2026}
}
```

### Google AI Studio Compare Mode — Developer Blog
```
@misc{googleaistudio2024compare,
  title        = {Compare Mode in {Google AI Studio}: Your Companion for Choosing the Right {Gemini} Model},
  author       = {{Google}},
  howpublished = {\url{https://developers.googleblog.com/compare-mode-in-google-ai-studio/}},
  note         = {Accessed: 2026-07-22},
  year         = {2024}
}
```

### Consensus.app (Excluded — for paper footnote)
```
@misc{consensusapp2026,
  title        = {{Consensus} — {AI} Search Engine for Research},
  howpublished = {\url{https://consensus.app}},
  note         = {Accessed: 2026-07-22. Note: Consensus.app is an academic literature
                  synthesis tool, not a same-prompt multi-model comparison interface.
                  Excluded from the audit on this basis.},
  year         = {2026}
}
```

---

*End of landscape audit. Document version: 1.0 (2026-07-22).*
