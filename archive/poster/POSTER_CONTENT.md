# Academic Poster Blueprint: "Beyond WER"
## Trick or Research 2026 — Siebel School of Computing and Data Science, UIUC

**Title:** Beyond WER: Quantifying ASR Error Propagation in Spoken Language Understanding for Dysarthric Speech  
**Authors:** Zixuan Yin$^1$, Xiuwen Zheng$^1$, Haolong Zheng$^1$, Kush Bhardwaj$^1$, Mark Hasegawa-Johnson$^1$  
**Affiliation:** $^1$Department of Electrical & Computer Engineering and Siebel School of Computing & Data Science, University of Illinois Urbana-Champaign  
**Consortium:** Speech Accessibility Project (SAP), Beckman Institute for Advanced Science and Technology  
**Compute:** ACCESS Allocation `CIS250149` on NCSA Delta GPU cluster  

---

## Section 1: Introduction & Clinical Motivation
* Over 100 million individuals globally live with motor speech disorders (dysarthria) resulting from Cerebral Palsy (CP), ALS, Parkinson’s disease (PD), and stroke.
* Hands-free voice interfaces provide essential independence for individuals with severe physical motor impairments.
* **Acoustic Degradation:** Dysarthric speech patterns exhibit hypernasality, prolonged phonemes, atypical pitch contours, and variable speech rate. Standard commercial speech models (trained predominantly on normative speech) degrade severely, yielding Word Error Rates (WER) of 30% to 50%+.
* **Turn-Taking Truncation:** Involuntary mid-sentence pauses trigger standard Voice Activity Detection (VAD) energy thresholds, cutting off commands before completion.

---

## Section 2: The "Beyond WER" Problem
* Conventional speech benchmarks evaluate models solely by minimizing transcript Word Error Rate ($\text{WER}$).
* Downstream task completion exhibits non-linear sensitivity to acoustic errors:
  * **Benign Disfluencies:** Dropped function words (*"the"*, *"a"*), repetitions, and conversational hesitation tokens (*"uh"*, *"um"*) are absorbed by downstream Large Language Model (LLM) contextual priors.
  * **Catastrophic Slot Corruptions:** Phonetic mutations in **named entities, numerical arguments, and operational slots** (e.g., *"call mom"* $\to$ *"call tom"*, *"take 5mg"* $\to$ *"take 50mg"*) trigger unrecoverable downstream failures or hazardous actions.
* **Core Research Question (RQ):** *What quantitative gains does dysarthria-specific acoustic fine-tuning yield at the level of downstream spoken language understanding (SLU) and tool invocation, beyond transcript WER?*

---

## Section 3: Speech Accessibility Project & SLU Benchmark (Schema v1.3)
* Audio is sourced from the **Speech Accessibility Project (SAP)** at UIUC Beckman Institute, encompassing diverse dysarthric etiologies.
* To quantify downstream task execution, we formulated an audited SLU benchmark grounded in OpenAPI 3.0 tool schemas:
  * **1,274 Canonical Gold Commands:** Multi-model consensus (Claude 3.5 Sonnet & GPT-4o) with human adjudication. 100% compliant with strict typing, explicit enum constraints, and slot validation rules.
  * **35 Out-of-Domain (OOD) Items:** Standalone wake phrases, OS system utility invocations, and dictation fragments partitioned out to prevent metric distortion.
  * **10 Real-World Domains (29 Tools):** Health (`health_log`), Communication (`messages_send`, `calls_dial`), Calendar/Alarm (`alarm_create`), Smart Home, Media, Places, QA, Notes, Accessibility, and Transport.
  * **Speaker-Disjoint Protocol:** Evaluation audio is strictly disjoint from acoustic training splits to measure true generalized adaptation.

---

## Section 4: Decoupled System Architecture
We reject end-to-end black-box architectures in favor of a **strictly decoupled cascaded pipeline**, allowing exact failure attribution:
1. **Turn Segmentation:** Push-to-talk capture to eliminate VAD pause-cutoff confounds.
2. **Streaming ASR:** NVIDIA Parakeet-TDT 0.6B (12.5 Hz frame rate, 80ms chunks). Condition 2 (Base) vs. Condition 3 (SAP Fine-Tuned).
3. **Downstream LLM Agent:** Qwen 2.5 72B-Instruct held frozen at greedy decoding ($T=0.0$) with rigid OpenAPI function-calling definitions.
4. **Evaluation Engine:** Automated parser verifying Tool Selection (TS), Tool Call Structural Validity (TCS), Parameter Filling (PF), and Command Frame Accuracy.

---

## Section 5: Controlled Evaluation Protocol & Metrics
* **Condition 1 (Oracle Ceiling):** Pristine human ground-truth transcripts provided to the agent. Quantifies the LLM's intrinsic semantic reasoning ceiling.
* **Condition 2 (Base ASR Baseline):** Unadapted zero-shot NVIDIA Parakeet-TDT 0.6B (Acoustic WER: 28.15%).
* **Condition 3 (Fine-Tuned ASR):** Parakeet-TDT fine-tuned on speaker-disjoint SAP dysarthric audio (Acoustic WER: 10.70%).
* **Evaluation Metrics:**
  * **Tool Selection Accuracy (TS):** Exact match of the target API function.
  * **Parameter Filling Accuracy (PF):** Strict exact match of all ground-truth slot keys and argument values.
  * **Command Frame Accuracy:** Strict end-to-end task completion ($\text{TS} = 1 \land \text{PF} = 1$).
  * **Adaptation Recovery Rate (ARR):**
    $$\text{ARR} = \frac{\text{Acc}_{\text{FT}} - \text{Acc}_{\text{Base}}}{\text{Acc}_{\text{Oracle}} - \text{Acc}_{\text{Base}}} \times 100\%$$

---

## Section 6: Empirical Results (Pilot Dev Set, N=291)

| Condition | Acoustic WER (%) | Tool Selection (TS %) | Parameter Filling (PF %) | Command Frame Acc (%) |
| :--- | :---: | :---: | :---: | :---: |
| **1. Oracle Ceiling** | 0.00 | 88.32 | 66.67 | **59.45** |
| **2. Base Parakeet** | 28.15 | 74.23 | 40.34 | **28.18** |
| **3. Fine-Tuned ASR** | **10.70** | **86.60** | **58.70** | **50.52** |
| **Net Gain / Recovery** | **-17.45** | **+12.37** | **+18.36** | **+22.34 (ARR: 71.4%)** |

* Acoustic adaptation closes **71.44%** of the entire downstream task degradation gap caused by dysarthria.
* **Domain Sensitivity Breakdown:**
  * **Health & Medication (N=42):** Base 14.3% $\to$ Fine-Tuned **81.0%** (**+66.7% gain**). Preserves critical dosages and symptom entities.
  * **Communication (N=33):** Base 24.2% $\to$ Fine-Tuned **72.7%** (**+48.5% gain**). Recovers distorted recipient contact names.
  * **General QA (N=90):** Base 35.6% $\to$ Fine-Tuned **48.9%** (**+13.3% gain**). Search engines tolerate noisy query terms through fuzzy indexing.

---

## Section 7: Qualitative Error Propagation & SECR
* **Slot Value Mutation:**
  * Spoken command: *"Set alarm for 7:30 am"*
  * Base ASR: *"set alarm for several thirty"* $\to$ Tool: `alarm_create(time="several:30")` $\to$ **Type Error / Execution Crash**.
  * Fine-Tuned ASR: *"set alarm for 7:30 a.m."* $\to$ Tool: `alarm_create(time="07:30")` $\to$ **Task Success**.
* **Semantic Error Correction Rate (SECR):** In **35.07%** of eligible corrupted slots, the LLM successfully inferred ground-truth arguments using phonetic and sentence context (e.g., *"call doctor house agar"* $\to$ *"Dr. Hasegawa"*).

---

## Section 8: Future Research Roadmap
1. **Corpus Scaling:** Expand inference across all 1,274 audited gold utterances on NCSA Delta GPUs.
2. **Phonetic Tolerance:** Incorporate Double Metaphone / Soundex distance metrics into parameter grading to avoid penalizing near-miss phonetic spellings.
3. **Towards Full-Duplex Turn-Taking:** Develop pause-tolerant atypical VAD models to replace push-to-talk, preventing cutoff during prolonged phonations.
4. **Edge Assistant:** Quantize fine-tuned streaming ASR for on-device deployment in accessible hardware.

---

## Acknowledgments & Computing Support
* Supported by the **Speech Accessibility Project (SAP)**, Beckman Institute for Advanced Science and Technology, UIUC.
* Computing allocation `CIS250149` provided by **ACCESS on NCSA Delta GPU cluster**.
* Repository: `github.com/zyin422/sap-dialog-system`
