# Spoken Dialog System Evaluation Framework: Cascaded & Full-Duplex Architectures for Dysarthric Speech

**Authors:** Speech Accessibility Project (SAP) Dialog Research Team  
**Working Repository:** `sap-dialog-system`  
**Target Submission / Standard:** ACL / EMNLP / Interspeech  
**Document Version:** 1.0 (Phase 0 Evaluation Freeze)

---

## Executive Summary & Research Questions

This document specifies the end-to-end evaluation methodology for our cascaded spoken dialogue system (`Speech` $\to$ `Streaming ASR` $\to$ `LLM Dialog Manager` $\to$ `TTS Response`) and outlines the forward path toward full-duplex conversational interaction on dysarthric speech.

* **Primary Question (RQ1 - Semantic Utility Beyond WER):** What does an SAP fine-tuned streaming ASR buy at the level of a working spoken assistant, not just lexical Word Error Rate (WER)?
* **Downstream Error Propagation (RQ2 - Error Cascades vs. Absorption):** How do ASR errors on dysarthric speech propagate through LLM tool selection and parameter filling? When does an LLM successfully absorb/correct phonetic errors versus blindly propagating corrupted tokens or hallucinating?
* **Dialogue Interaction (RQ3 - Task Success & Turn-Taking):** How do acoustic disfluencies, prolonged vowels, and atypical pauses affect task completion, clarification calibration, and conversational latency?

---

## 1. Literature Grounding: The 7 Core Benchmarks

The evaluation framework synthesizes seven foundational benchmarks and papers surveyed in our project notes:

| # | Benchmark / Paper | Venue / Year | Target Architecture | Primary Evaluation Metrics Extracted |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **VoiceAgentBench** | arXiv 2025/2026 | Cascaded (`Whisperv3 + LLM`) vs. SpeechLMs | • **Tool Selection (`TS`)**<br>• **Tool Call Structure (`TCS`)**<br>• **Parameter Filling (`PF`)** via LLM Judge<br>• **ASR Degradation Gap & Recovery Rate** |
| **2** | **Audio2Tool** | Rivian / VW 2025/2026 | Spoken Tool Calling (152 tools) | • **Schema Parameter Validity**<br>• **Single vs. Chained Execution Accuracy**<br>• **Tool Hallucination Rate** |
| **3** | **SpokenWOZ** | NeurIPS 2023 | Spoken Multi-Turn TOD (8 domains, 36 slots) | • **Joint Goal Accuracy (`JGA`)**<br>• **Mentioned Slot Accuracy (`MAMS`)**<br>• **Task `INFORM` & `SUCCESS` Rates**<br>• **4-Way Slot Error Taxonomy** |
| **4** | **DSTC11 Track 3**<br>*(Spoken MultiWOZ)* | DSTC 2023 | Dialogue State Tracking under ASR Noise | • **Turn-Level Slot Error Propagation**<br>• **Acoustic Noise Recovery Rate**<br>• **Cumulative State Drift** |
| **5** | **UniverSLU** | ICASSP 2024 | Universal Multi-Task SLU (17 datasets) | • **Cross-Domain Slot F1**<br>• **Intent Classification Accuracy**<br>• **Phonetic vs. Semantic Alignment** |
| **6** | **Meta STOP / TOPv2** | Interspeech 2022 | Spoken Semantic Parsing (8 domains) | • **Exact Match Accuracy (`EMA`)**<br>• **Tree/Flat Semantic Parsing Accuracy**<br>• **Acoustic Variation Degradation** |
| **7** | **Amazon MASSIVE** | ACL 2022 | Modular SLU (18 domains, 60 intents, 55 slots) | • **Intent Accuracy**<br>• **Slot `F1`**<br>• **Exact Match Accuracy (`EMA`)** |

*Complementary Baseline References:*
* **SLURP** (EMNLP 2020): Origin of `Entity-WER`, `Word-F1`, `Char-F1`, and joint `SLU-F1`.
* **FireRedChat** (2025): Full-duplex interaction metrics—Semantic End-of-Turn (`EoT`) accuracy, Turn-Taking Latency ($P_{50}, P_{95}$), and False Barge-In Rate.

---

## 2. Multi-Stage Evaluation Framework

The system is evaluated across three decoupled, diagnostic stages:

```
[Raw Dysarthric Audio]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 1: ASR Semantic Metrics                         │
│ (Lexical vs. Semantic Error Concentration)             │
└────────────────────────────────────────────────────────┘
          │
          ▼ Incremental / Final Transcripts
┌────────────────────────────────────────────────────────┐
│ STAGE 2: LLM Functional Tool Calling & Error Impact   │
│ (Tool Selection, Parameter Filling & Recovery Rate)    │
└────────────────────────────────────────────────────────┘
          │
          ▼ Tool Call / Spoken Response
┌────────────────────────────────────────────────────────┐
│ STAGE 3: Conversational Dialogue & Interaction         │
│ (Task Success, Clarification Prudence & Latency)       │
└────────────────────────────────────────────────────────┘
```

---

### STAGE 1: Evaluating ASR Semantic Metrics (Base vs. Fine-Tuned)

Standard Word Error Rate (WER) is an unweighted average of insertions, deletions, and substitutions. In dysarthric speech, WER is dominated by repeated stutter syllables, dropped function words, and filler vocalizations. Stage 1 isolates semantic content errors from acoustic artifacts.

#### 1.1 Slot-WER (Entity-WER)
* **Definition:** Levenshtein word error rate computed strictly over the ground-truth parameter spans (e.g. `medication`, `destination`, `title`, `time`), masking out carrier phrases.
$$\text{Entity-WER} = \frac{S_{\text{slot}} + D_{\text{slot}} + I_{\text{slot}}}{N_{\text{slot}}}$$
* **Clinical Significance:** Directly tests whether fine-tuning recovers critical actionable words (e.g., drug names like *"baclofen"* or street names) rather than superficial filler words.
* **Supporting Literature:** **SLURP** (Fig. 2, pp. 2–3) demonstrated that while 40% of utterances had ASR errors ($\text{WER} > 0$), ~73% had $\text{Entity-WER} = 0$.

#### 1.2 Content-Word vs. Function-Word Error Ratio
* **Definition:** Separate WER computation for lexical content words (nouns, main verbs, numbers, proper entities) versus closed-class function words (determiners, prepositions, conjunctions).
* **Clinical Significance:** Proves that an SAP fine-tuned streaming ASR specifically repairs high-entropy lexical tokens.
* **Supporting Literature:** **SpokenWOZ** (Section 6.2) & **UniverSLU**.

#### 1.3 Acoustic-Phonetic Drift (Char-F1 / Phoneme Levenshtein)
* **Definition:** Character-level Levenshtein distance on extracted slot substrings.
* **Clinical Significance:** Distinguishes benign phonetic spelling variations that modern LLMs easily absorb (e.g., `"cliantro"` vs. `"cilantro"`, `"8am"` vs. `"8:00 AM"`) from catastrophic lexical substitutions (e.g., `"lisinopril"` $\to$ `"hospital"`).
* **Supporting Literature:** **SLURP** (Section 4: `Word-F1` vs. `Char-F1`).

---

### STAGE 2: Evaluating LLM Output, Error Recovery & Error Propagation

Stage 2 measures how ASR errors impact downstream agent execution, comparing three transcript conditions:
1. **Condition 1 (Oracle):** Ground-Truth Human Transcripts ($y^*$)
2. **Condition 2 (Base ASR):** Regular Pretrained Streaming ASR (e.g., Voxtral / Whisper)
3. **Condition 3 (Adapted ASR):** SAP Fine-Tuned Streaming ASR

#### 2.1 The 3-Stage Functional Calling Metrics (from VoiceAgentBench)
1. **Tool Selection Accuracy (`TS`):**
   $$\text{TS} = \frac{\mathbb{I}(\hat{t} = t^*)}{N_{\text{total}}}$$
   Measures whether the LLM selected the correct canonical intent (e.g., `schedule_manage` vs. `alarm_manage`).
2. **Tool Call Structure (`TCS`):**
   Percentage of tool calls that pass automated Pydantic / JSON schema validation (verifies all required arguments are present, correct data types, and no hallucinated extraneous keys).
3. **Parameter Filling Accuracy (`PF`):**
   $$\text{PF} = \frac{\sum_{i=1}^{K} \text{Sim}(\hat{v}_i, v_i^*)}{K_{\text{required slots}}}$$
   Semantic argument accuracy evaluated via normalized exact match for Enums, and semantic similarity (LLM-as-a-judge via GPT-4o-mini rubric) for open-vocabulary BaseNP spans.

#### 2.2 ASR-to-LLM Error Propagation Matrix
* **Downstream Degradation Gap ($\Delta_{\text{ASR}}$):**
  $$\Delta_{\text{ASR}} = \text{PF}_{\text{Oracle}} - \text{PF}_{\text{Base ASR}}$$
  Quantifies the exact downstream utility loss caused by dysarthric speech recognition errors.
* **Domain Adaptation Recovery Rate:**
  $$\text{Recovery Rate} = \frac{\text{PF}_{\text{Fine-Tuned}} - \text{PF}_{\text{Base ASR}}}{\text{PF}_{\text{Oracle}} - \text{PF}_{\text{Base ASR}}} \times 100\%$$
  *(In VoiceAgentBench Table 6, domain adaptation recovered 40–55% of this performance deficit).*

#### 2.3 Diagnostic Error Classification (Categorizing LLM Behaviors)
Every error turn is classified into one of three distinct failure modes:
* **Error Correction (Success):** ASR transcript is phonetically corrupted, but LLM utilizes conversational context to output the correct slot.
* **Verbatim Propagation (Failure):** ASR substitutes a phonetic token in a proper noun, and the LLM blindly injects the corrupted token into the tool call.
* **Hallucinatory Distortion (Failure):** Severe acoustic noise causes the LLM to hallucinate unuttered slots or trigger an unrelated tool.

*Supporting Literature:* **VoiceAgentBench** (Section 3.2 & Appendix J), **Audio2Tool**, **Meta STOP**, **Amazon MASSIVE**.

---

### STAGE 3: Evaluating Conversational Dialogue & Turn-Taking

Stage 3 evaluates multi-turn conversational robustness, user burden, and turn-taking latency.

#### 3.1 Task Completion & Dialogue Policy (from SpokenWOZ & DSTC11)
* **`INFORM` Rate:** Percentage of dialogues where the system successfully answered the user's specific query.
* **`SUCCESS` Rate:** Percentage of dialogues where the system satisfied all user constraints and executed the final action (booking, reservation, calendar update).
* **Joint Goal Accuracy (`JGA`):** Percentage of dialogue turns where all accumulated slot-value pairs match the ground-truth state.

#### 3.2 Clarification Calibration (Prudence vs. Friction)
* **Appropriate Clarification Rate:** Asking for confirmation when ASR confidence is low or slot entropy is high (e.g., *"Did you mean 7 AM or 7 PM?"*).
* **Redundant Clarification Friction:** Unnecessary confirmations on unambiguous, clean commands. For motor-impaired speakers, redundant spoken turns impose severe physical fatigue.

#### 3.3 Full-Duplex & Turn-Taking Dynamics (ACL Novelty Dimension)
* **Semantic End-of-Turn (`EoT`) Detection:** Binary classification accuracy determining whether an acoustic pause is an atypical dysarthric mid-sentence pause (800–1800 ms) versus actual message completion.
* **False Barge-In Rate (%):** System interruptions triggered erroneously by respiratory sounds, speech repairs, or stutters during assistant speech.
* **Turn-Taking Latency ($P_{50}, P_{95}$):** Time from user semantic turn completion to first audible assistant response.

*Supporting Literature:* **SpokenWOZ** (NeurIPS 2023), **DSTC11 Track 3**, **FireRedChat** (Xiaohongshu 2025).

---

## 3. Implementation Blueprint & Tool Mapping

| Stage | Input Data | Evaluated Component | Output Metric | Primary Supporting Paper |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1: ASR Semantics** | Audio $\to$ Text | Base vs. Fine-Tuned Streaming ASR | `Entity-WER`, Content/Function Error Ratio, `Char-F1` | **SLURP** (EMNLP 2020)<br>**UniverSLU** (ICASSP 2024) |
| **Stage 2: LLM Tool Calling** | Transcripts $\to$ JSON | Frozen Prompted LLM (`Qwen2.5-7B` / `Llama-3.3-70B`) | `TS`, `TCS`, `PF`, Recovery Rate (%) | **VoiceAgentBench** (2025)<br>**Audio2Tool** (2025) |
| **Stage 3: Conversational TOD** | Interactive / Replay Audio | Full Dialog Cascade | `INFORM`, `SUCCESS`, Clarification Precision, `EoT` Accuracy | **SpokenWOZ** (NeurIPS 2023)<br>**FireRedChat** (2025) |

---

## 4. Conclusion & Next Steps for the Research Team

1. **Information Sufficiency:** The 7 surveyed papers provide complete, rigorous coverage across all three architectural layers. No further exploratory survey is needed; the existing paradigms are directly applicable.
2. **Immediate Action:** Present this 3-stage plan to faculty advisors (Prof. Mark Hasegawa-Johnson and mentors) to finalize the automated evaluation script in [`conversation_llm_eval.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/conversation_llm_eval.py).
3. **Execution Sequence:** Complete Step 3 pilot annotation $\to$ compute Stage 1 and Stage 2 metrics on the 50 pilot items $\to$ scale to the full offline evaluation harness.
