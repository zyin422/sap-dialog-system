# Research Groundings & Dataset Curation Specification
## Unshared Prompts Benchmark (Speech Accessibility Project)

**Authors:** Xiuwen Zheng, Haolong Zheng, Zixuan Yin, Kush Bhardwaj  
**Faculty Advisor:** Professor Mark Hasegawa-Johnson (UIUC)  
**Date:** November 2026  
**Scope:** Filtering, Stratification, and Benchmark Task Realization on Zero-Shot Unshared Prompts (`dev_unshared_prompts.csv`, `test1_out_of_prompts.csv`, `test2_out_of_prompts.csv`)

---

## 1. Foundational Research Groundings

### 1.1 Dialogue Management & Active Clarification Policies
The tripartite decision policy (`EXECUTE` vs. `CLARIFY` vs. `REJECT`) implemented for spoken error handling is grounded in peer-reviewed dialogue systems literature:

* **Bohus & Rudnicky (SIGdial 2005, CSL 2007)** — *"A probabilistic approach to constructing confidence-based clarification dialogue policies"*:
  * Formulated the canonical confidence-band decision framework for Spoken Dialogue Systems (SDS) operating under acoustic uncertainty:
    $$\text{Confidence}(u) \ge \theta_{\text{high}} \implies \text{Execute (Implicit / Silent Confirmation)}$$
    $$\theta_{\text{low}} \le \text{Confidence}(u) < \theta_{\text{high}} \implies \text{Clarify (Targeted / Reprise Clarification)}$$
    $$\text{Confidence}(u) < \theta_{\text{low}} \implies \text{Reject / Reprompt (Acoustic Failure)}$$
* **Purver (PhD Thesis 2004, CSL)** — *"The Theory and Use of Clarification Requests in Dialogue"*:
  * Established the formal linguistic categorization of Clarification Requests (CRs):
    1. **Reprise Clarification (Confirmation):** Echoes a suspected acoustic constituent to confirm understanding under phonological ambiguity (*"Did you say CBS or CVS?"*).
    2. **Gap-Filling Clarification (Elicitation):** Identifies an underspecified required slot and queries for missing information (*"For how long would you like to set the timer?"*).
* **Rieser & Lemon (2008, 2011)** — *"Reinforcement Learning in Spoken Dialogue Systems"*:
  * Proved that in acoustic environments characterized by speech degradation, dialogue policies must mathematically balance the conversational turn cost of clarification against the severe utility penalty of executing false actions.
* **Safety Asymmetry in Assistive Voice Agents (Kuhn et al. 2024; Interspeech 2025)**:
  * For individuals with severe neuromotor or physical disabilities, correcting an erroneous, irreversible machine action (e.g. heating an oven to an extreme temperature, sending an incorrect email, or deleting records) requires substantial physical exertion. Premature execution carries catastrophic cost relative to a low-overhead spoken confirmation turn.

### 1.2 Disordered Speech Curation & Benchmark Standards
* **Zwilling et al. (Interspeech 2025)** — *"The Speech Accessibility Project: Best Practices for Collection and Curation of Disordered Speech"*:
  * Documented the multi-stage curation, verbatim transcription protocols, and annotation standards for the Speech Accessibility Project (SAP).
  * Formalized guidelines for handling disfluencies (false starts, syllable repetitions, prolongations) and defined baseline exclusion criteria: empty audio files, interlopers (caregiver-only speech), and corrupted recordings.
* **TORGO (Rudzicz et al. 2012) & UA-Speech (Kim et al. 2008)**:
  * Established clinical severity stratification (Mild, Moderate, Severe, Very Severe) based on speech-language pathologist (SLP) perceptual ratings and clinical assessments.
  * Standardized the handling of non-speech vocalizations (coughs, throat clearing) and unprompted vocalizations.

---

## 2. ASR Error Profile: WER vs. Sentence Error Rate (SER)

On zero-shot unshared prompts (`dev_unshared_prompts.csv`), Fine-Tuned Parakeet achieves a substantial reduction in Word Error Rate over Base Parakeet, even while exact sentence match failure (SER) remains elevated due to minor phonetic slips:

| Metric | Base Parakeet ASR | Fine-Tuned Parakeet ASR | Absolute $\Delta$ | Relative Reduction |
| :--- | :---: | :---: | :---: | :---: |
| **Sentence Error Rate (SER)** | 69.82% | 66.67% | $-3.15\%$ | 4.5% |
| **Word Error Rate (WER)** | **42.25%** | **26.69%** | **$-15.56\%$** | **36.8%** |

### Per-Etiology Word Error Rate (WER)
* **Cerebral Palsy (CP):** 52.56% $\to$ **24.36%** ($-28.20\%$ abs)
* **Amyotrophic Lateral Sclerosis (ALS):** 41.70% $\to$ **22.88%** ($-18.82\%$ abs)
* **Down Syndrome (DS):** 51.50% $\to$ **33.48%** ($-18.02\%$ abs)
* **Stroke:** 56.16% $\to$ **42.12%** ($-14.04\%$ abs)
* **Parkinson's Disease (PD):** 18.96% $\to$ **14.29%** ($-4.67\%$ abs)

---

## 3. Dataset Preprocessing & Invariant Rules

### 3.1 Long Duration Preservation via Silence Trimming
* **Finding:** In dysarthric speech, total audio duration frequently ranges from $15\text{s}$ to $35\text{s}$. This extended duration is driven by:
  1. Motor initiation latency (time required to start vocal tract articulation).
  2. Trailing tap-latency (physical difficulty reaching and pressing the "stop" button on the UI).
* **Rule:** Long duration instances ($>20\text{s}$) are **retained**, not excluded. Leading and trailing acoustic silence is trimmed using standard energy-based Voice Activity Detection (VAD) / boundary-shrinking algorithms ($20\text{dB}\text{--}30\text{dB}$ threshold) without truncating user speech.

---

## 4. Tier 0 (Hard Exclusions) vs. Severe Dysarthric Speech

To prevent benchmark contamination without discarding genuine severe speech, we establish objective discrimination criteria:

```
                          Candidate Recording
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
   [Severe Dysarthric Speech]                  [Invalid Recording (Tier 0)]
   • Slow articulation rate                    • App instruction reading
   • Phonetic approximations                   • Total prompt abandonment
   • Intact core intent/entities               • Pure non-speech (cough only)
   • Prolonged duration ($>3\text{s}$)         • Out-of-scope schema tool
          │                                               │
          ▼                                               ▼
   RETAIN IN BENCHMARK                         HARD EXCLUSION (DISCARD)
```

### 4.1 Tier 0 (Hard Exclusion) Criteria
An instance is discarded from both the SLU and Turn-Taking benchmarks **if and only if** it satisfies one of the following four conditions:

1. **Rule 0.1: Out-of-Scope Tool Intent:**
   * Utterance maps to an action unsupported by the frozen 29-tool schema.
   * *Empirical count in unshared dev:* 107 instances (`"Open Duolingo."` — 3rd party app launcher).
2. **Rule 0.2: Pure Non-Speech / Acoustic Corruption:**
   * Transcript contains zero intelligible or phonetic tokens (pure cough `(kof-)`, throat clearing, microphone scratch, or digital clipping).
   * *Empirical count in unshared dev:* 0 instances.
3. **Rule 0.3: Complete Prompt Abandonment / Meta-Speech:**
   * Participant did not attempt the prompt and uttered only meta-commentary (e.g. `"(ss: Dang I cannot.)"`, `"But no."`).
   * *Empirical count in unshared dev:* 2 instances.
4. **Rule 0.4: Interface Instruction Reading:**
   * Participant read the recording prompt UI instructions instead of the stimulus (e.g. `"Press the record button, read the text, and press (uh) record."`).
   * *Empirical count in unshared dev:* 1 instance.

### 4.2 Severe Dysarthric Speech Preservation Rules (Retained)
The following phenomena are explicitly protected from exclusion:
* **Imprecise Articulation & Word Slur:** Utterances where transcribers recorded phonetic approximations (e.g. `(screet-) The oven`, `(renbul- and) farm`, `Movies (mu w-) with Tom Cruise`).
* **Telegraphic Phrasing:** Utterances where the speaker dropped auxiliary verbs or articles (e.g. `"Distance to Minnesota?"` instead of `"What's the distance to Minnesota?"`).
* **Incomplete Prompts (Routed to Task 2A):** If the speaker omitted a required entity (e.g. `"Make me a reservation."`), the instance is not discarded; it is assigned to **Task 2A (Missing Slot Elicitation)** as a real-world test of proactive clarification.

---

## 5. Master Benchmark Stratification Matrix

| Tier / Slice | Definition | Volume in Unshared Dev | Role in SLU Benchmark | Role in Turn-Taking Benchmark |
| :--- | :--- | :---: | :--- | :--- |
| **Tier 0** | Out-of-scope (`Duolingo`), instruction reading, pure abandonment | 110 | Excluded | Excluded |
| **Tier 1** | Clean operational commands, standard entity verbalizations | ~5,152 | Task 1 & 2 Core Evaluation | Clean Turn Completion / EoT Latency |
| **Tier 2** | Hesitations, filled pauses `(uh)`, word fragments `(s-)` | 493 | Robustness Evaluation | **False Cutoff Rate (FCR)** |
| **Tier 3** | Side-speech annotations `(ss: ...)` | 38 | Distractor Filtering | **Barge-In / Caregiver Invariance** |
| **Tier 4** | Lexical repetitions, restarts `(word) word` | 108 | Self-Repair Extraction | **Restart Floor-Holding** |
