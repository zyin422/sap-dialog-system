# Spoken Dialog System Evaluation Framework: ASR Semantics & LLM Tool Calling

**Project:** Speech Accessibility Project (SAP) — Spoken Dialog System  
**Pipeline:** $\text{Dysarthric Audio} \xrightarrow{\quad\text{Streaming ASR}\quad} \text{Transcript} \xrightarrow{\quad\text{LLM Agent}\quad} \text{Canonical Tool Call } \{\text{domain}, \text{intent}, \text{slots}\}$  
**Target Standard:** ACL / EMNLP / Interspeech  
**Version:** 1.3 (Hybrid Evaluation: Lexical, Embedding, & LLM-as-a-Judge)

---

## 1. Master Metric Summary Table

| Pipeline Layer | Evaluation Metric | Primary Paper / Origin | Target Evaluated & Core Definition |
| :--- | :--- | :--- | :--- |
| **ASR Semantic** | **SemScore** | SAPC Interspeech / *Towards Robust Dysarthric Speech Recognition* (2026) | Meaning preservation via composite metric: $\text{BERTScore}_{\text{F1}}$ + NLI entailment (MENLI) + phonetic similarity (Soundex). |
| **ASR Semantic** | **Word-F1** | SLURP (EMNLP 2020) | Token-level precision and recall computed strictly over ground-truth parameter spans, masking carrier phrases. |
| **ASR Semantic** | **Char-F1** | SLURP (EMNLP 2020) | Character Levenshtein edit distance on entity spans, isolating minor phonetic/spelling drift from parsing failure. |
| **ASR Semantic** | **LLM-as-a-Judge** | VoiceAgentBench / Interspeech (2025/2026) | Semantic equivalence (1–5 scale) & error severity taxonomy: isolates *Harmless* acoustic drift (stutters, phonetic spelling) from *Critical* slot corruption. |
| **LLM Tool Calling** | **Tool Selection (`TS`)** | VoiceAgentBench / Audio2Tool (2025/2026) | Canonical tool / intent classification accuracy: $\frac{1}{N}\sum \mathbb{I}(\hat{t} = t^*)$ across the 28-tool catalog. |
| **LLM Tool Calling** | **Tool Call Structure (`TCS`)** | VoiceAgentBench / Audio2Tool (2025/2026) | Syntactic schema validity via Pydantic: required slots present, correct data types, zero hallucinated keys. |
| **LLM Tool Calling** | **Parameter Filling (`PF`)** | VoiceAgentBench / Audio2Tool (2025/2026) | Semantic argument accuracy: exact match for Enums; BaseNP string match + LLM judge for open-vocabulary spans. |
| **Ablation Matrix** | **Recovery Rate (%)** | VoiceAgentBench (2025/2026) | Percentage of Oracle parameter accuracy recovered by SAP fine-tuning: $\frac{\text{PF}_{\text{Fine-Tuned}} - \text{PF}_{\text{Base}}}{\text{PF}_{\text{Oracle}} - \text{PF}_{\text{Base}}} \times 100\%$. |

---

## 2. Stage 1: ASR Semantic Evaluation Metrics

Standard Word Error Rate (WER) penalizes every insertion, deletion, and substitution equally, making it a misleading metric for dysarthric speech where disfluencies, repetitions, and dropped function words inflate WER without destroying actionable intent. SOTA speech literature (Interspeech, ACL, EMNLP) avoids relying solely on either WER or LLM-as-a-Judge; instead, it uses a **triangulated hybrid framework** combining:
1. **Deterministic Lexical Metrics** (`Word-F1`, `Char-F1`) for objective, token/character-level ground truth fidelity.
2. **Deterministic Embedding Metrics** (`SemScore`) for reproducible semantic vector distance without inference variance.
3. **Cognitive LLM Evaluation** (`LLM-as-a-Judge`) for pragmatic equivalence and error severity classification.

### 2.1 SemScore (Semantic Fidelity & Intent Preservation)
* **Origin:** *Towards Robust Dysarthric Speech Recognition: LLM-Agent Post-ASR Correction Beyond WER* (arXiv:2602.04652 / SAPC Challenge, Interspeech).
* **Formula:**
  $$\text{SemScore} = w_1 \cdot \text{BERTScore}_{\text{F1}} + w_2 \cdot \text{NLI}_{\text{entailment}} + w_3 \cdot \text{Sim}_{\text{phonetic}}$$
  * **$\text{BERTScore}_{\text{F1}}$:** Contextual embedding cosine similarity (RoBERTa/DeBERTa) between reference and hypothesis tokens.
  * **$\text{NLI}_{\text{entailment}}$ (e.g. MENLI):** Measures whether the hypothesis logically entails the reference, rewarding valid paraphrases.
  * **$\text{Sim}_{\text{phonetic}}$ (Soundex / Jaro-Winkler):** Accounts for pronunciation variation and minor dysarthric phonetic drift.
* **Why It Matters:** Dysarthric speakers often produce phonetically imprecise but semantically complete utterances. SemScore captures whether the core intent survived, proving that fine-tuning or post-ASR correction restores actionable meaning even when exact verbatim wording fluctuates.

### 2.2 Word-F1 (Entity / Slot Level)
* **Origin:** *SLURP: A Spoken Language Understanding Resource Package* (EMNLP 2020).
* **Formula:**
  $$\text{Precision}_{\text{word}} = \frac{|T_{\text{hyp}} \cap T_{\text{ref}}|}{|T_{\text{hyp}}|}, \quad \text{Recall}_{\text{word}} = \frac{|T_{\text{hyp}} \cap T_{\text{ref}}|}{|T_{\text{ref}}|}, \quad \text{Word-F1} = \frac{2 \cdot P_{\text{word}} \cdot R_{\text{word}}}{P_{\text{word}} + R_{\text{word}}}$$
* **Why It Matters:** Evaluates token overlap strictly inside parameter spans (e.g., medication names, dates, times, destinations). Isolates critical content words from generic carrier phrases (*"can you please..."*, *"remind me to..."*).

### 2.3 Char-F1 (Acoustic-Phonetic Tolerance)
* **Origin:** *SLURP* (Section 4, pp. 4–6).
* **Formula:** Harmonic mean based on minimum character-level Levenshtein edit distance between reference and hypothesis entity strings.
* **Why It Matters:** Crucially separates **ASR phonetic drift** (e.g., `"cliantro"` vs. `"cilantro"`, `"8am"` vs. `"8:00 AM"`) from **semantic parsing failure**. LLMs easily parse minor phonetic drifts into the correct tool action, so penalizing them as complete lexical errors misrepresents downstream system viability.

### 2.4 LLM-as-a-Judge (Semantic Equivalence & Pragmatic Error Severity)
* **Origin & Methodology:** VoiceAgentBench (2025/2026), HATS-en (2025), MT-Bench.
* **Why Use in Conjunction (Not Solely):**
  * **Zero Sole-Reliance Standard:** Top-tier papers almost never use LLM-as-a-Judge in isolation. LLM judges suffer from model version drift, non-determinism, temperature noise, and *over-forgiveness bias* (where a capable LLM "hallucinates" understanding from badly mangled acoustic input, falsely masking severe speech recognition failure).
  * **Triangulation:** Pairing the LLM judge with deterministic metrics (`Word-F1`, `SemScore`) ensures that high ratings reflect genuine semantic retention rather than LLM inference guesswork.
* **Evaluation Protocol (1–5 Likert Scale):**
  * **Score 5 (Identical Intent):** Core intent and all entity arguments are fully preserved. Differences are limited to stutters, repetitions, or benign phonetic spellings (`"ah set timer 5 mins"` vs. `"set a timer for five minutes"`).
  * **Score 4 (Harmless Variation):** Minor phrasing drift or dropped filler words; downstream tool call is deterministically recoverable with zero argument loss.
  * **Score 3 (Borderline / Ambiguous):** Intent recognizable, but one optional parameter is partially ambiguous or requires conversational clarification.
  * **Score 2 (Critical Parameter Corruption):** Intent recognizable, but a critical argument (medication dosage, date/time, contact name) is corrupted or negated.
  * **Score 1 (Intent Collapse / Hallucination):** Spoken command completely misparsed into an unrelated domain or nonsensical tool call.
* **Pragmatic Error Severity Taxonomy:**
  * $\text{Score} \ge 4 \implies \textbf{Harmless Drift}$ (zero downstream tool-calling impact).
  * $\text{Score} \le 3 \implies \textbf{Critical Failure}$ (leads directly to tool execution failure or unintended real-world action).

---

## 3. Stage 2: LLM Tool-Calling Evaluation Metrics

Downstream LLM execution is evaluated using the 3-tier scoring pipeline established in **VoiceAgentBench** (2025/2026) and validated by **Audio2Tool** (2025/2026):

```
[ASR Transcript] ──► [LLM Agent] ──► Predicted Tool Call
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      ▼                                      ▼                                      ▼
1. Tool Selection (TS)             2. Tool Call Structure (TCS)           3. Parameter Filling (PF)
   Exact Match on Intent Name         Schema & Pydantic Validation           Semantic Argument Accuracy
```

### 3.1 Tool Selection (`TS` / Intent Accuracy)
* **Formula:** $\text{TS} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(\hat{\text{tool}}_i = \text{tool}_i^*)$
* **Why It Matters:** Measures high-level intent classification accuracy across boundary clusters (e.g., `schedule_manage` vs. `alarm_manage`, `media_play` vs. `media_control`, `iot_device_power` vs. `iot_device_adjust`).

### 3.2 Tool Call Structure (`TCS` / Schema Validity)
* **Formula:** $\text{TCS} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(\text{SchemaValid}(\hat{C}_i) = \text{True})$
* **Validation Criteria (Pydantic / JSON Schema):**
  1. *Required Slot Completeness:* All mandatory arguments are present.
  2. *Type Conformance:* Enums, integers, and strings conform strictly to declared types.
  3. *Zero Hallucinated Keys:* No undeclared or invented parameters.
* **Why It Matters:** Noisy dysarthric transcripts often cause un-calibrated LLMs to hallucinate arguments or output malformed JSON. TCS ensures the tool call will not crash downstream execution environments.

### 3.3 Parameter Filling (`PF` / Slot Semantic Accuracy)
* **Formula:** $\text{PF} = \frac{1}{\sum_{i=1}^N K_i} \sum_{i=1}^{N} \sum_{j=1}^{K_i} \text{Sim}(\hat{v}_{i,j}, v_{i,j}^*)$
  * **Categorical Enums:** Strict exact match against the closed literal set (`action: "add"`, `state: "on"`).
  * **Extractive Spans:** BaseNP string match + LLM-as-a-judge rubric (GPT-4o-mini, $\kappa = 0.80$) for benign phrasing variations.
* **Why It Matters:** VoiceAgentBench proved that while TS remains high (>91%), ASR noise drops PF by **24–38 percentage points**. PF identifies the exact locus of downstream degradation caused by ASR phonetic substitution errors.

---

## 4. Ablation Matrix: ASR Error Propagation & Recovery Rate

To isolate what an SAP fine-tuned streaming ASR buys at the assistant level, the identical frozen LLM is evaluated across three conditions:
$$\text{Condition 1: Oracle Transcripts } (y^*) \quad \longrightarrow \quad \text{Condition 2: Base Streaming ASR} \quad \longrightarrow \quad \text{Condition 3: Fine-Tuned SAP ASR}$$

### Key Derived Metrics:
1. **Downstream ASR Degradation Gap ($\Delta_{\text{ASR}}$):**
   $$\Delta_{\text{ASR}} = \text{PF}_{\text{Oracle}} - \text{PF}_{\text{Base ASR}}$$
   *(Measures the total downstream task penalty imposed by baseline speech recognition errors).*
2. **Domain Adaptation Recovery Rate (%):**
   $$\text{Recovery Rate} = \frac{\text{PF}_{\text{Fine-Tuned}} - \text{PF}_{\text{Base ASR}}}{\text{PF}_{\text{Oracle}} - \text{PF}_{\text{Base ASR}}} \times 100\%$$
   *(Quantifies the exact percentage of Oracle task performance recovered by the SAP fine-tuned ASR).*
3. **LLM Error Behavior Taxonomy:**
   * **Error Correction (Success):** Noisy ASR input $\to$ LLM infers correct slot.
   * **Verbatim Copying (Failure):** ASR phonetic substitution $\to$ LLM copies corrupted token into tool call.
   * **Hallucinatory Distortion (Failure):** Severe ASR noise $\to$ LLM hallucinates unmentioned arguments or wrong tools.
