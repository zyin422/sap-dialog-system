# Beyond WER: Quantifying ASR Error Propagation in Spoken Language Understanding for Dysarthric Speech

**Research Poster Blueprint & Presentation Content**  
**Event:** *Trick or Research 2026*  
**Host:** Siebel School of Computing and Data Science, University of Illinois Urbana-Champaign (UIUC)  
**Partner Organization:** CS STARS (Strengthening Underrepresented Students in Computing Research)  
**Venue:** Thomas M. Siebel Center for Computer Science Atrium  
**Poster Dimensions:** 48.0" wide × 36.0" high (Landscape, 4:3 Aspect Ratio, 3-Column Layout)

---

## Poster Header & Institutional Metadata

* **Title:** Beyond WER: Quantifying ASR Error Propagation in Spoken Language Understanding for Dysarthric Speech
* **Authors:** Zixuan Yin (Presenter)¹, Xiuwen Zheng¹, Haolong Zheng¹, Kush Bhardwaj¹, Mark Hasegawa-Johnson¹
* **Affiliations:**  
  ¹Department of Electrical & Computer Engineering and Siebel School of Computing & Data Science, University of Illinois Urbana-Champaign  
  Speech Accessibility Project (SAP), Beckman Institute for Advanced Science and Technology
* **Compute Allocation:** Supported by ACCESS Allocation `CIS250149` on the NCSA Delta GPU Cluster (`bjas-delta-gpu` / `bedl-delta-gpu`)

---

## 3-Column Visual Layout Outline

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          POSTER HEADER                                           │
│       Title, Authors, Affiliations, Beckman Institute & Siebel School Logos, ACCESS Grant       │
├──────────────────────────────┬───────────────────────────────────┬───────────────────────────────┤
│           COLUMN 1           │             COLUMN 2              │           COLUMN 3            │
│  1. Motivation: Why WER      │ 4. Decoupled Pipeline Architecture│ 7. Domain Breakdown (10 Domains)│
│     Fails Assistive Voice AI │ 5. Three Experimental Conditions  │ 8. Clinical Etiology Breakdown  │
│  2. Speech Accessibility     │ 6. Full Dev Results (N = 1,108)   │ 9. Qualitative Case Studies     │
│     Project (SAP) Corpus     │    • Tool Selection (TS)          │ 10. Next Steps: Conversational  │
│  3. Assistive SLU Catalog    │    • Parameter Filling (PF)       │     Grounding & Affirmations    │
│     (10 Domains, 29 Tools)   │    • Command Frame Accuracy & ARR │ Acknowledgments & Codebase      │
└──────────────────────────────┴───────────────────────────────────┴───────────────────────────────┘
```

---

# COLUMN 1: Motivation, Corpus, and Schema Formalization

### 1. Motivation: Why Word Error Rate (WER) Fails Assistive Voice AI
* **The Accessibility Gap:** Commercial voice assistants (Google Assistant, Siri, Alexa) assume standard speech acoustics. For individuals with dysarthria—a motor speech impairment resulting from Amyotrophic Lateral Sclerosis (ALS), Cerebral Palsy (CP), Parkinson’s Disease (PD), Stroke, or Down Syndrome—commercial ASR Word Error Rate (WER) jumps from ~5% to **30%–50%+**, rendering voice assistants virtually unusable.
* **Why Transcript WER is Misleading for Downstream Tasks:**
  * **Benign Disfluencies:** Dropped function words (*"the"*, *"a"*), vocal hesitations (*"um"*), and acoustic pauses are absorbed by modern Large Language Model (LLM) contextual reasoning, resulting in **0% task failure**.
  * **Catastrophic Slot Corruption:** Single-phoneme acoustic confusions in names, medications, or operational commands (*"call Kathy"* $\to$ *"call Cassie"*; *"turn on"* $\to$ *"turn off"*; *"take 5mg"* $\to$ *"take 50mg"*) lead to wrong phone calls, incorrect device states, or dangerous real-world errors.
* **Core Research Question:**  
  *What does fine-tuning a streaming ASR on dysarthric speech actually buy in a functional, downstream spoken assistant—not just in Word Error Rate, but in real-world task completion?*

---

### 2. Speech Accessibility Project (SAP) Evaluation Corpus
Audio recordings are drawn from the **Speech Accessibility Project (SAP)** at the UIUC Beckman Institute, supported by UIUC, Google, Apple, Microsoft, Amazon, and the Davis Phinney Foundation.

* **Global Dataset Scale:** **34,577 decoded audio recordings** across **124 dysarthric speakers**, containing **31,606 recordings** directly matching canonical voice assistant commands.
* **Evaluated Benchmark Cohort ($N = 1,108$ Audio Recordings):** A stratified, speaker-disjoint benchmark covering **372 unique commands** recorded by **16 dysarthric speakers** across **all 5 clinical etiologies**:
  1. **Amyotrophic Lateral Sclerosis (ALS):** 480 recordings (bulbar hypernasality, slow strained phonation, breathlessness).
  2. **Stroke (Dysarthria / Apraxia):** 247 recordings (inconsistent phoneme substitutions, prosodic decay, articulatory groping).
  3. **Parkinson's Disease (PD):** 231 recordings (hypophonia / reduced loudness, vocal tremor, rapid rushes).
  4. **Cerebral Palsy (CP):** 107 recordings (articulatory spasticity, irregular pitch bursts, prolonged distorted vowels).
  5. **Down Syndrome:** 43 recordings (articulatory imprecision, anatomical differences, phrasing hesitations).
* **Experimental Controls:**
  * *Speaker-Disjoint:* Zero speaker overlap between acoustic model training and evaluation sets.
  * *Push-to-Talk:* Eliminates standard energy-based Voice Activity Detection (VAD) cutoffs caused by involuntary mid-sentence pauses.

---

### 3. Assistive SLU Catalog (10 Domains, 29 Tools)
A formalized 29-tool catalog conforming strictly to OpenAPI 3.0 standards, covering the core everyday tasks of assistive living:

* **Accessibility:** `accessibility_dictation_toggle`, `accessibility_ui_scale`
* **Calendar & Alarm:** `alarm_manage`, `schedule_manage`
* **Communication:** `call_make`, `call_manage`, `messages_manage`, `email_manage`
* **General QA:** `qa_search`, `weather_query`, `device_find`, `order_manage`
* **Health:** `health_medication_reminder`, `health_refill_query`, `health_info_query`
* **Maps & Places:** `maps_route`, `places_search`, `reservations_manage`
* **Media:** `media_play`, `media_search`, `media_control`, `media_volume`
* **Notes & Memory:** `lists_manage`, `memory_note_manage`
* **Smart Home:** `iot_device_power`, `iot_device_adjust`, `iot_sensor_query`
* **Transport:** `rideshare_book`, `transit_lookup`

---

# COLUMN 2: Decoupled Architecture, Conditions, and Main Results

### 4. Decoupled Cascaded Evaluation Pipeline

```
User Audio (16 kHz Dysarthric Speech)
                 │
                 ▼
Push-to-Talk Turn Control (Eliminates VAD pause cutoffs)
                 │
                 ▼
Streaming Fast-Conformer ASR (NVIDIA Parakeet-TDT 0.6B @ 12.5 Hz / 80ms frames)
                 │
                 ├── Condition 2: Base Checkpoint (Zero-Shot, 28.15% Acoustic WER)
                 └── Condition 3: Fine-Tuned Checkpoint (SAP-Adapted, 10.70% Acoustic WER)
                 │
                 ▼
Downstream Task Agent: Frozen Qwen3-8B (Zero-Shot Greedy Decoding T=0.0, max_len=8192)
                 │
                 ▼
Validated JSON Output Schema: {"domain": "...", "intent": "...", "slots": {...}}
                 │
                 ▼
Strict Automated SLU Evaluation Suite
```

* **Streaming ASR:** NVIDIA Parakeet-TDT 0.6B running at 12.5 Hz (80ms frames) for responsive real-time inference.
* **Frozen Downstream LLM:** `Qwen/Qwen3-8B` operating under our certified unhacked prompt, held strictly at greedy decoding ($T=0.0$).

---

### 5. Controlled Experimental Conditions & Approved Metrics

To isolate acoustic error propagation, downstream LLM prompts, schemas, and model weights are held **100% frozen** across all conditions:

1. **Condition 1: Oracle (Clean Text):** Ground-truth reference transcript (WER: 0.00%). Establishes the agent's semantic reasoning upper bound.
2. **Condition 2: Base ASR Baseline:** Off-the-shelf, unadapted Parakeet-TDT 0.6B (Acoustic WER: **28.15%**).
3. **Condition 3: Fine-Tuned ASR:** Parakeet-TDT 0.6B fine-tuned on speaker-disjoint SAP dysarthric speech (Acoustic WER: **10.70%**).

#### Approved Evaluation Metrics
* **Acoustic WER (%):** Standard transcription Word Error Rate.
* **Tool Selection Accuracy (TS %):** Exact match of the invoked API tool ($\mathbb{I}[\hat{t} = t^*]$).
* **Tool Call Structure Validity (TCS %):** Proportion of outputs producing valid JSON compliant with schema keys and enums.
* **Parameter Filling Accuracy (PF %):** Proportion of required gold slot values correctly extracted (exact string match or normalized character-F1 $\ge 0.85$).
* **Command Frame Accuracy (%):** Strict end-to-end task completion ($\text{TS} = 1 \land \text{TCS} = 1 \land \text{All Gold Slots Matched}$).
* **Adaptation Recovery Rate (ARR %):** Proportion of the downstream degradation gap recovered by acoustic fine-tuning:
  $$\text{ARR} = \frac{\text{Frame}_{\text{FT}} - \text{Frame}_{\text{Base}}}{\text{Frame}_{\text{Oracle}} - \text{Frame}_{\text{Base}}} \times 100\%$$

---

### 6. Main Benchmark Results ($N = 1,108$ Audio Instances)

*Evaluated on NCSA Delta GPU (Job ID `23464832`, NVIDIA A100-SXM4-80GB, 3,324 total model inferences).*

| Evaluation Condition | Acoustic WER (%) | Tool Selection TS (%) | Struct Validity TCS (%) | Parameter Filling PF (%) | Command Frame Accuracy (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Condition 1: Oracle Ceiling** | 0.00% | **95.67%** (1060/1108) | **100.0%** (1108/1108) | **88.41%** (1434/1622) | **84.03%** (931/1108) |
| **Condition 2: Base Parakeet ASR** | 28.15% | 74.55% (826/1108) | 99.28% (1100/1108) | 46.22% (750/1622) | **38.09%** (422/1108) |
| **Condition 3: Fine-Tuned ASR** | **10.70%** | **92.96%** (1030/1108) | **99.82%** (1106/1108) | **75.73%** (1228/1622) | **66.88%** (741/1108) |
| **Acoustic Adaptation Gain ($\Delta$)** | **-17.45%** | **+18.41%** | **+0.54%** | **+29.51%** | **+28.79%** |

$$\mathbf{\text{Adaptation Recovery Rate (ARR)}} = \frac{66.88\% - 38.09\%}{84.03\% - 38.09\%} = \frac{28.79\%}{45.94\%} = \mathbf{62.67\%}$$

#### Key Research Insights:
1. **The Downstream Gap is in the Parameters:** Off-the-shelf ASR degrades Command Frame Accuracy by **45.94%**. While intent selection remains partially usable ($74.55\%$), Parameter Filling collapses from **88.41% down to 46.22%**.
2. **Fine-Tuning Recovers Over Six-Tenths of Task Success:** Dysarthria acoustic adaptation recovers **+28.79% absolute Command Frame Accuracy** (**38.09% $\to$ 66.88%**), achieving an **ARR of 62.67%**.

---

# COLUMN 3: Clinical Disparities, Error Regimes, and Future Work

### 7. Domain Disparities: Safety-Critical Domains Suffer Most

| Assistive Domain | Instance Count ($N$) | Condition 1 (Oracle) | Condition 2 (Base ASR) | Condition 3 (FT ASR) | Net Gain ($\Delta_{\text{FT} - \text{Base}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Health & Medication** | 180 | 95.0% | **8.3%** | **70.6%** | **+62.2%** |
| **Calendar & Alarms** | 104 | 76.9% | 39.4% | **72.1%** | **+32.7%** |
| **Communication** | 111 | 91.9% | 42.3% | **71.2%** | **+28.8%** |
| **Smart Home** | 99 | 75.8% | 46.5% | **72.7%** | **+26.3%** |
| **Transport** | 21 | 100.0% | 57.1% | **81.0%** | **+23.8%** |
| **Notes & Memory** | 48 | 81.2% | 43.8% | **66.7%** | **+22.9%** |
| **Accessibility** | 18 | 100.0% | 77.8% | **100.0%** | **+22.2%** |
| **Maps & Places** | 108 | 83.0% | 29.6% | **50.0%** | **+20.4%** |
| **General QA** | 300 | 75.7% | 43.0% | **62.0%** | **+19.0%** |
| **Media & Entertainment** | 119 | 92.4% | 52.5% | **66.1%** | **+13.6%** |

* **The Health Crisis in Base ASR:** In Health commands, Base ASR achieves only **8.3% Frame Accuracy**. Phonetic corruptions of pharmaceutical names (*"enalapril"*, *"pantoprazole"*) and dosages destroy parameter filling. Acoustic fine-tuning delivers an extraordinary **+62.2% net recovery** (**70.6% Frame Accuracy**).

---

### 8. Clinical Etiology Breakdown: Severe Articulatory Vulnerability

| Clinical Etiology Group | Instances ($N$) | Condition 1 (Oracle) | Condition 2 (Base ASR) | Condition 3 (FT ASR) | Net Recovery Gain ($\Delta$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Cerebral Palsy (CP)** | 107 | 86.9% | **2.8%** | **55.1%** | **+52.3%** |
| **Amyotrophic Lateral Sclerosis (ALS)** | 480 | 82.0% | 33.1% | **62.9%** | **+29.8%** |
| **Down Syndrome** | 43 | 83.2% | 51.2% | **76.7%** | **+25.4%** |
| **Stroke (Dysarthria / Apraxia)** | 247 | 84.1% | 44.9% | **66.5%** | **+21.6%** |
| **Parkinson's Disease (PD)** | 231 | 85.7% | 53.6% | **70.5%** | **+17.0%** |

* **Near-Zero Usability for Cerebral Palsy:** Off-the-shelf ASR fails on **97.2% of Cerebral Palsy commands** (only 2.8% completion). Acoustic fine-tuning restores task completion to **55.1%** (+52.3% absolute gain), proving that specialized acoustic models are mandatory for severe dysarthria.

---

### 9. Qualitative Case Studies: Three Downstream Error Regimes

```
Case 1: Content-Word Slot Substitution (Proper Name Telephony — SAP-CMD-0304)
  Audio Ground Truth:   "Please call Kathy Bianco."
  Base ASR Transcript:  "Please call Cassie Bianco."        -> TS: PASS | PF: FAIL (Dials wrong person)
  FT ASR Transcript:    "please call kathy bianco"          -> TS: PASS | PF: PASS (Complete Recovery)

Case 2: Catastrophic Acoustic Collapse (Climate Control — SAP-CMD-0318)
  Audio Ground Truth:   "Raise the temperature."
  Base ASR Transcript:  "Wait, change this to me."          -> TS: FAIL (Derailed to notes_memory)
  FT ASR Transcript:    "raise the temperature"             -> TS: PASS | PF: PASS (Complete Recovery)

Case 3: LLM Semantic Error Resilience (Media Volume — SAP-CMD-0197)
  Audio Ground Truth:   "Increase the volume."
  Base ASR Transcript:  "And volume."                       -> TS: PASS | PF: PASS (LLM absorbs omission)
  FT ASR Transcript:    "increase the volume"               -> TS: PASS | PF: PASS (Clean Parse)
```

---

### 10. Next Immediate Horizon: Conversational Grounding & Voice Affirmations

Voice assistants must go beyond silent JSON generation:
1. **Auditory Grounding for Dysarthric Users:** Because dysarthric speakers experience frequent ASR errors, the assistant must speak an immediate, concise affirmation echoing the extracted parameters (*"Got it, turning off the closet light."*), enabling immediate verbal verification.
2. **Eliminating Dead Air:** Generating a spoken affirmation concurrently with API execution masks pipeline latency ($>1.5\text{s}$) for a responsive conversational flow.
3. **Multi-Turn Extension:** When mandatory parameters are missing (*"Set a reminder"* without time), the system will produce an explicit clarification question rather than a premature execution.

---

### Acknowledgments & Research Context

* **Institutional Support:** Speech Accessibility Project (SAP) at the Beckman Institute for Advanced Science and Technology, UIUC, in partnership with Google, Apple, Microsoft, Amazon, and the Davis Phinney Foundation.
* **Supercomputing:** NCSA Delta GPU cluster under ACCESS Project Allocation `CIS250149`.
* **Undergraduate Engagement:** Presented at *Trick or Research 2026*, Siebel School of Computing and Data Science & CS STARS.
