# Full-Duplex Spoken Dialogue Systems: Architecture, Turn-Taking, & Dataset Realization

**Project:** Speech Accessibility Project (SAP) — Spoken Dialog System  
**Context:** Synthesis & Architectural Analysis of Curated Literature for Full-Duplex System Design  
**Collaborators:** Haolong Zheng, Zixuan Yin, Xiuwen Zheng, Kush Bhardwaj  
**Version:** 1.0 (Initial Synthesis & Literature Mapping)  

---

## 1. Master Literature Taxonomy

The curated reading list spans three functional layers: foundational surveys, systems/architectures, and conversational datasets.

| Category | Paper Title & Citation | Key Mechanism / Architecture | Relevance to SAP Dysarthric Dialog |
| :--- | :--- | :--- | :--- |
| **Survey** | **WavChat** ([arXiv:2411.13577](https://arxiv.org/abs/2411.13577)) | Comprehensive taxonomy of cascaded vs. end-to-end spoken dialogue models. | Establishes baselines for streaming latency, duplex interaction, and audio tokenization. |
| **Survey** | **Landscape of Spoken Language Models** ([arXiv:2504.08528](https://arxiv.org/abs/2504.08528)) | Survey of discrete speech tokens, speech encoders, and multimodal LLMs. | Background on audio representation representations and tokenizer choices. |
| **Survey** | **Turn-Taking Modeling in SDS** ([IWSDS 2025](https://aclanthology.org/2025.iwsds-1.27/)) | Acoustic, prosodic, and linguistic turn-completion forecasting. | Explains why acoustic-only silence thresholds fail on atypical speech. |
| **Survey** | **Full-Duplex SDS Survey** ([arXiv:2606.19453](https://arxiv.org/abs/2606.19453)) | L0–L3 architectural hierarchy, $T \times I \times R$ interaction ontology, and 5-state Decision State Machine (`IDLE`, `LISTEN`, `SPEAK`, `WAIT`, `DUAL`). | **Core architectural blueprint.** Documents the "realization gap" between model capability and training/evaluation data. |
| **System** | **X-Talk** ([arXiv:2512.18706](https://arxiv.org/abs/2512.18706)) | Decoupled modular cascade (VAD + ASR + LLM + TTS) achieving sub-second latency. | **Primary candidate architecture.** Retains tool use, RAG, and swappable domain-fine-tuned ASR. |
| **System** | **Stream RAG** ([arXiv:2510.02044](https://arxiv.org/abs/2510.02044)) | Streaming tool invocation predicted *in parallel* with ongoing user speech. | Hides tool latency by extracting arguments while dysarthric speakers are mid-command. |
| **System** | **E2E S2S with RAG** ([EMNLP 2025 Findings](https://aclanthology.org/anthology-files/anthology-files/pdf/findings/2025.findings-emnlp.241.pdf)) | Fusing audio queries with external knowledge in speech-to-speech models. | Grounds speech responses in factual knowledge bases. |
| **System** | **SCoT (Streaming CoT)** ([arXiv:2510.02066](https://arxiv.org/abs/2510.02066)) | Blockwise streaming generation alternating audio frames and reasoning tokens; predicts silence tokens to avoid VAD. | Demonstrates how to maintain semantic reasoning in continuous full-duplex streams. |
| **System** | **LLM Full-Duplex Scheme** ([NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/180d4373aca26bd86bf45fc50d1a709f-Abstract-Conference.html)) | 8B LLM emitting control tokens to a Neural Finite State Machine (perception + motor modules). | Achieves sub-500ms latency and high interruption precision via discrete state control. |
| **Dataset** | **UltraVoice** ([arXiv:2510.22588](https://arxiv.org/abs/2510.22588)) | 830-hour speech dialogue dataset with fine-grained style control (emotion, speed, volume). | Reference for expressive speech synthesis and multi-turn audio conversation structures. |

---

## 2. Architectural Comparison: Modular vs. End-to-End vs. Hybrid FSM

```
PARADIGM A: Decoupled Modular (X-Talk)
[Streaming Audio] ──► [Streaming ASR (Voxtral)] ──► [LLM Agent + Tools] ──► [Streaming TTS]
                             ▲                               │
                             └──────── State Machine ────────┘

PARADIGM B: Pure End-to-End Omni (Moshi, SCoT)
[Streaming Audio In] ──────► [Single Multimodal Speech LLM] ──────► [Streaming Audio Out]
                             (Internalized Turn-Taking & Tokens)

PARADIGM C: Hybrid LLM-FSM (NeurIPS 2024)
[Perception Module] ──────► [Streaming LLM] ──────► [Motor Module (TTS)]
                             │ (Emits Control Tokens: SPEAK / WAIT / INTERRUPT)
                             ▼
                    [Neural Finite State Machine]
```

### Critical Trade-Offs for Dysarthric Spoken Dialog

1. **Acoustic Robustness & Fine-Tuning Feasibility:**
   * **Modular (*X-Talk*):** Superior for our project. We can independently fine-tune the streaming ASR (e.g., Voxtral or Conformer-Transducer) on SAP speech without touching the LLM or TTS.
   * **End-to-End (Omni):** Extremely fragile on atypical speech. Fine-tuning a 7B omni-model on SAP's limited hours risks catastrophic forgetting of language reasoning and tool calling.
2. **Deterministic Tool Execution & Schema Adherence:**
   * Full-duplex interaction in an assistant setting requires rigid API calls (`schedule_manage`, `alarm_manage`, `iot_device_power`).
   * Modular systems enforce Pydantic/JSON Schema validation natively. E2E models struggle with exact slot extraction while simultaneously generating audio tokens.
3. **Latency Mitigation:**
   * *X-Talk* demonstrates that optimized streaming buffers, chunked LLM decoding, and sentence-level TTS synthesis achieve sub-second perceived latency, neutralizing the main historical advantage of E2E models.

---

## 3. Turn-Taking Modeling & The Decision State Machine

Standard half-duplex voice assistants use **energy/silence-based VAD**:
$$\text{Silence Duration} > \tau_{\text{cutoff}} \quad (\text{typically } 700\text{ms}) \implies \text{Turn Over} \to \text{Trigger Pipeline}$$

### The Failure Mode for Dysarthric Speech
Dysarthric speakers frequently exhibit:
* Prolonged intra-utterance pauses ($>1.2\text{s}$) during lexical access or motor planning.
* Prolonged consonants, vowel elongations, and repetitions.
* Breath breaks mid-clause.
Standard VAD cuts the user off mid-sentence, causing catastrophic truncation and downstream task failure.

### The Full-Duplex Solution (DuplexLM Survey & NeurIPS 2024)
Full-duplex replaces static silence thresholds with a **5-State Decision State Machine**:
* **`IDLE`:** System standby; listening for wake events.
* **`LISTEN`:** User speaking; system buffering and streaming interim transcripts.
* **`WAIT`:** User paused mid-utterance (prosody/syntax indicates incomplete clause); system holds floor open.
* **`SPEAK`:** System synthesizing response while continuing to listen.
* **`DUAL`:** Simultaneous user speech and system speech (user barge-in or system backchannel); system decides whether to yield floor or continue.

```
       ┌───────────────────────────────┐
       │             IDLE              │
       └───────────────┬───────────────┘
                       │ User Speech Detected
                       ▼
       ┌───────────────────────────────┐
       │            LISTEN             │◄──────────────┐
       └───────┬───────────────▲───────┘               │
               │               │ User Resumes          │ User Resumes
  Intra-Clause │               │ Speech                │ Speech
  Pause        ▼               │                       │
       ┌───────────────┐       │                       │
       │     WAIT      │───────┘                       │
       └───────┬───────┘                               │
               │ Turn Complete                         │
               ▼                                       │
       ┌───────────────┐        User Barge-In          │
       │     SPEAK     │──────────────────────┐        │
       └───────▲───────┘                      │        │
               │                              ▼        │
               │ Backchannel /        ┌───────────────┐│
               │ System Yields Floor  │     DUAL      │┘
               └──────────────────────┤ (Barge-in/BC) │
                                      └───────────────┘
```

---

## 4. The Realization Gap: Bridging the Single-Turn SAP Dataset to Full-Duplex

### The Fundamental Problem
The survey by DuplexLM ([arXiv:2606.19453](https://arxiv.org/abs/2606.19453)) identifies the **realization gap**: architectures support duplex states, but evaluation benchmarks remain strictly turn-by-turn.

Furthermore, the **SAP dataset consists of isolated, single-turn read prompts** (*"Add laundry detergent to shopping list"*, *"Set timer for 10 minutes"*). It lacks:
1. Spontaneous multi-turn back-and-forth.
2. Natural user barge-in / interruptions.
3. Conversational repairs (*"No, I meant tomorrow at two"*).
4. System clarifying turns.

### How to Build a Full-Duplex Benchmark from SAP Read Speech

To build a scientifically valid full-duplex benchmark using the existing dataset, we can employ three structured simulation paradigms:

#### Paradigm 1: Pause Tolerance & Premature Cutoff Benchmark (Acoustic Evaluation)
* **Goal:** Quantify how well the full-duplex state machine prevents premature turn termination during dysarthric speech pauses.
* **Method:** Replay SAP recordings through:
  * Baseline A: Standard Silence VAD ($\tau = 700\text{ms}$).
  * Baseline B: Extended Silence VAD ($\tau = 1500\text{ms}$).
  * Full-Duplex State Machine: Linguistic + acoustic completeness prediction (`LISTEN` vs. `WAIT`).
* **Metrics:**
  * **Premature Cutoff Rate (%):** Utterances terminated before the syntactic sentence end.
  * **Turn-End Latency (ms):** Delay between actual speech termination and system response onset.

#### Paradigm 2: Speculative Streaming Tool Prediction (*Stream RAG* Style)
* **Goal:** Exploit dysarthric speech duration to eliminate tool execution latency.
* **Method:**
  * As streaming ASR frames arrive, the LLM agent speculatively predicts intent and extracts slots mid-utterance.
  * If confidence passes threshold $\theta$, pre-fetch or validate parameters before the user finishes speaking.
* **Metrics:**
  * **Speculative Precision:** Accuracy of tool calls initiated prior to speech end.
  * **Latency Savings (ms):** Reduction in time-to-first-token compared to waiting for audio completion.

#### Paradigm 3: Scripted Multi-Turn Dialog Replay with Forced Interruptions
* **Goal:** Evaluate the system's ability to handle barge-in and conversational repair.
* **Method:**
  * Construct 6 multi-turn goal trees (e.g., *Reschedule an Appointment*, *Order a Meal*).
  * Synthesize system clarifying prompts (*"Did you want morning or afternoon?"*).
  * Programmatically trigger user response audio at controlled timestamps (e.g., overlapping system speech by 500ms to test barge-in handling in the `DUAL` state).
* **Metrics:**
  * **Barge-In Detection Latency (ms):** Time taken to halt TTS output once user audio starts.
  * **Slot Repair Accuracy:** Did the LLM update the existing state with the new correction?

---

## 5. Active Discussion & Evolution Log

*(This section will track questions, critiques, and design refinements as our discussion progresses).*

* **2026-10-18:** Initial synthesis established. Key alignment around modular design (*X-Talk*), Neural State Machine (*NeurIPS 2024* / *DuplexLM*), and speculative execution (*Stream RAG*) for dysarthric spoken dialogue.
