# Spoken Dialog System Evaluation Framework: ASR Semantics & LLM Tool Calling for Dysarthric Speech

**Authors:** Speech Accessibility Project (SAP) Dialog Research Team  
**Working Repository:** `sap-dialog-system`  
**Target Submission:** ACL / EMNLP / Interspeech  
**Document Version:** 1.1 (Phase 0 Focused Metric Specification)

---

## Executive Summary & Core Research Questions

This document specifies the exact quantitative evaluation metrics for our cascaded spoken dialogue system:
$$\text{Dysarthric Audio} \xrightarrow{\quad\text{Streaming ASR}\quad} \text{Transcript} \xrightarrow{\quad\text{LLM Dialog Agent}\quad} \text{Canonical Tool Call } \{\text{domain}, \text{intent}, \text{slots}\}$$

* **RQ1 (ASR Semantic Preservation Beyond WER):** What does an SAP fine-tuned streaming ASR buy at the level of semantic intelligibility and entity preservation, rather than superficial lexical Word Error Rate (WER)?
* **RQ2 (Downstream Error Propagation & Recovery):** How do ASR errors propagate into LLM tool calling? When does an LLM absorb/correct phonetic errors versus propagating corrupted tokens into API arguments?

---

## 1. Stage 1: ASR Semantic Evaluation Metrics

Standard Word Error Rate (WER) penalizes every insertion, deletion, and substitution equally, making it a flawed proxy for dysarthric speech where disfluencies, repetitions, and dropped function words inflate WER without destroying the user's intent. We evaluate ASR hypotheses using three semantic and entity-focused metrics:

### 1.1 SemScore
* **Origin & Reference:** *Towards Robust Dysarthric Speech Recognition: LLM-Agent Post-ASR Correction Beyond WER* (arXiv:2602.04652 / SAPC Challenge, Interspeech).
* **Definition:** A composite metric measuring semantic fidelity and intent preservation by combining contextual embedding similarity, natural language inference, and phonetic string distance:
  $$\text{SemScore} = w_1 \cdot \text{BERTScore}_{\text{F1}} + w_2 \cdot \text{NLI}_{\text{entailment}} + w_3 \cdot \text{Sim}_{\text{phonetic}}$$
  * **BERTScore (Contextual Token Similarity):** Computes cosine similarity of contextual embeddings from RoBERTa/DeBERTa between reference and hypothesis tokens.
  * **NLI / Entailment (e.g. MENLI):** Measures whether the hypothesis logically entails the true intended meaning, rewarding valid paraphrases.
  * **Phonetic / String Distance (Soundex & Jaro-Winkler):** Accounts for pronunciation variation and minor dysarthric phonetic drift.
* **Why It Matters for Dysarthria:** Dysarthric speakers often produce phonetically imprecise but semantically complete utterances. SemScore captures whether the core message survived, proving that post-processing or fine-tuning restores actionable meaning even when exact word-for-word matching fluctuates.

---

### 1.2 Word-F1 (Entity / Slot Level)
* **Origin & Reference:** *SLURP: A Spoken Language Understanding Resource Package* (EMNLP 2020).
* **Definition:** Harmonic mean of precision and recall computed over lexical tokens within extracted parameter spans (e.g., medication names, dates, times, destinations):
  $$\text{Precision}_{\text{word}} = \frac{|T_{\text{hyp}} \cap T_{\text{ref}}|}{|T_{\text{hyp}}|}, \quad \text{Recall}_{\text{word}} = \frac{|T_{\text{hyp}} \cap T_{\text{ref}}|}{|T_{\text{ref}}|}, \quad \text{Word-F1} = \frac{2 \cdot P_{\text{word}} \cdot R_{\text{word}}}{P_{\text{word}} + R_{\text{word}}}$$
* **Why It Matters for Dysarthria:** Isolates critical content words from non-essential carrier phrases (e.g., *"remind me to..."*, *"can you please..."*). Proves whether the ASR preserves the actionable arguments required for tool execution.

---

### 1.3 Char-F1 (Acoustic-Phonetic Tolerance)
* **Origin & Reference:** *SLURP* (Section 4, pp. 4–6).
* **Definition:** Character-level harmonic mean based on minimum Levenshtein edit distance between the reference entity string and hypothesis entity string:
  $$\text{Char-F1} = \frac{2 \cdot P_{\text{char}} \cdot R_{\text{char}}}{P_{\text{char}} + R_{\text{char}}}$$
* **Why It Matters for Dysarthria:** Crucially separates **ASR acoustic/spelling drift** (e.g., `"cliantro"` vs. `"cilantro"`, `"8am"` vs. `"8:00 AM"`) from **semantic parsing failure**. An LLM can easily parse `"cliantro"` into the correct recipe search, so penalizing it as a 100% word error misrepresents downstream system viability.

---

## 2. Stage 2: LLM Tool-Calling Evaluation Metrics

Following **VoiceAgentBench** (2025/2026) and **Audio2Tool** (2025/2026), downstream LLM tool execution is evaluated via a 3-tier hierarchical scoring pipeline:

```
[ASR Transcript] ──► [LLM Agent] ──► Predicted Tool Call
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      ▼                                      ▼                                      ▼
1. Tool Selection (TS)             2. Tool Call Structure (TCS)           3. Parameter Filling (PF)
   Exact Match on Intent Name         Schema & Pydantic Validation           Semantic Argument Accuracy
```

---

### 2.1 Tool Selection (`TS` / Intent Accuracy)
* **Definition:** Percentage of turns where the agent selects the exact canonical tool / intent name from the 28-tool catalog:
  $$\text{TS} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(\hat{\text{tool}}_i = \text{tool}_i^*)$$
* **Why It Matters:** Tests high-level intent disambiguation across confusing boundaries (e.g. `schedule_manage` vs. `alarm_manage`, `media_play` vs. `media_control`, `iot_device_power` vs. `iot_device_adjust`).

---

### 2.2 Tool Call Structure (`TCS` / Schema Validity)
* **Definition:** Percentage of generated tool calls that pass automated JSON Schema / Pydantic validation:
  $$\text{TCS} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(\text{SchemaValid}(\hat{C}_i) = \text{True})$$
  * **Required Slot Completeness:** All non-optional arguments are present.
  * **Type Conformance:** Integers, enums, and string literals strictly conform to declared types.
  * **No Hallucinated Keys:** Zero undeclared or invented parameter keys.
* **Why It Matters:** Evaluates syntactic robustness. Noisy dysarthric transcripts often cause naive LLMs to hallucinate arguments or output malformed JSON.

---

### 2.3 Parameter Filling (`PF` / Slot Semantic Accuracy)
* **Definition:** Percentage of declared tool parameters whose extracted values semantically match ground truth:
  $$\text{PF} = \frac{1}{\sum_{i=1}^N K_i} \sum_{i=1}^{N} \sum_{j=1}^{K_i} \text{Sim}(\hat{v}_{i,j}, v_{i,j}^*)$$
  * **Categorical Enums:** Evaluated via strict exact match against the closed literal menu (e.g., `action: "add"`, `state: "on"`).
  * **Extractive Spans:** Evaluated via normalized BaseNP string match (stripping leading articles/prepositions) supplemented by an LLM-as-a-judge rubric (GPT-4o-mini, $\kappa = 0.80$) for benign phrasing variations.
* **Why It Matters:** This is where the brunt of ASR degradation occurs. VoiceAgentBench proved that while TS remains high (>91%), ASR noise drops PF by **24–38 percentage points**.

---

## 3. Downstream Error Propagation & Recovery Analysis

To quantify how ASR improvements translate into real-world assistant utility, the exact same LLM is evaluated across three conditions:
$$\text{Condition 1: Oracle Transcript } (y^*) \quad \longrightarrow \quad \text{Condition 2: Base Streaming ASR} \quad \longrightarrow \quad \text{Condition 3: Fine-Tuned SAP ASR}$$

### Core Comparative Metrics:
* **Downstream ASR Degradation Gap ($\Delta_{\text{ASR}}$):**
  $$\Delta_{\text{ASR}} = \text{PF}_{\text{Oracle}} - \text{PF}_{\text{Base ASR}}$$
* **Domain Adaptation Recovery Rate:**
  $$\text{Recovery Rate} = \frac{\text{PF}_{\text{Fine-Tuned}} - \text{PF}_{\text{Base ASR}}}{\text{PF}_{\text{Oracle}} - \text{PF}_{\text{Base ASR}}} \times 100\%$$
* **Error Behavior Taxonomy:**
  * **LLM Error Correction (Success):** Noisy ASR input $\to$ LLM infers correct slot.
  * **Verbatim Copying (Failure):** Phonetic substitution in ASR $\to$ LLM copies corrupted token into tool call.
  * **Hallucinatory Distortion (Failure):** High ASR noise $\to$ LLM hallucinates unuttered arguments or wrong tools.

---

## 4. Summary Table for Mentor Presentation

| Pipeline Layer | Evaluation Metric | Primary Paper / Origin | Target Evaluated |
| :--- | :--- | :--- | :--- |
| **ASR Semantic** | **SemScore** | SAPC Interspeech / *Towards Robust Dysarthric Speech Recognition* (2026) | Meaning preservation via BERTScore + NLI entailment + phonetic similarity |
| **ASR Semantic** | **Word-F1** | SLURP (EMNLP 2020) | Token-level precision & recall on critical parameter spans |
| **ASR Semantic** | **Char-F1** | SLURP (EMNLP 2020) | Character Levenshtein edit distance, isolating phonetic drift from slot error |
| **LLM Tool Calling** | **Tool Selection (`TS`)** | VoiceAgentBench (2025/2026) | Exact canonical intent classification accuracy |
| **LLM Tool Calling** | **Tool Call Structure (`TCS`)** | VoiceAgentBench / Audio2Tool (2025/2026) | Pydantic schema validity, required slot presence, zero hallucinated keys |
| **LLM Tool Calling** | **Parameter Filling (`PF`)** | VoiceAgentBench (2025/2026) | Semantic argument extraction accuracy (Enum match + Span rubric) |
| **Ablation Matrix** | **Recovery Rate (%)** | VoiceAgentBench (2025/2026) | Percentage of Oracle parameter accuracy recovered by SAP fine-tuning |
