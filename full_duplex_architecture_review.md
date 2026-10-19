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

## 5. Deep-Dive: Hybrid LLM-FSM (Neural FSM) vs. Modular Orchestration (X-Talk)

### 5.1 The Hybrid LLM-FSM & The "Neural FSM" (NeurIPS 2024)

Standard voice assistants delegate turn-taking to an external deterministic script (e.g., if acoustic volume $> \text{threshold}$, stop TTS). However, an external script is linguistically blind: it cannot tell the difference between a real user interruption (*"Wait, stop!"*), a cough, or an agreeable backchannel (*"uh-huh"*).

The **NeurIPS 2024 framework** (*Wang et al.*) solves this by embedding a **2-state physical Finite State Machine (FSM)** directly governed by an aligned LLM:

```
                  ┌──────────────────────────────────────────────┐
                  │           Large Language Model (LLM)         │
                  │  (Autoregressive Next-Token Prediction)      │
                  └───────────────┬──────────────┬───────────────┘
                     Text Tokens  │              │ Control Tokens
                                  ▼              ▼
                       ┌────────────────┐  ┌─────────────┐
                       │  Motor Module  │  │  Neural     │
                       │ (Streaming TTS)│  │  FSM        │
                       └────────────────┘  └──────┬──────┘
                                                  │ Controls Physical
                                                  ▼ Actuation
                       ┌─────────────────────────────────────────┐
                       │ State: { LISTEN, SPEAK }                │
                       └─────────────────────────────────────────┘
                                                  ▲
                                                  │ Audio Chunk Events
                                           ┌──────┴──────┐
                                           │ Perception  │
                                           │ (Stream ASR)│
                                           └─────────────┘
```

#### Core Components & Mechanics:
1. **Perception Module:** Audio stream is partitioned into fixed 640ms chunks and transcribed by streaming ASR into incremental token packets.
2. **Motor Module:** Streaming TTS converting LLM-generated response tokens into audible waveforms.
3. **The 2 Physical States:**
   * **`LISTEN`:** Motor module is idle; system is ingesting user speech chunks.
   * **`SPEAK`:** Motor module is actively synthesizing; system continues listening in the background.
4. **Why is it called a "Neural" FSM?**
   The FSM transitions are **not hardcoded by heuristic rules**. Instead, the LLM emits special **discrete control tokens** interleaved directly in its autoregressive token stream:
   * **$\text{LISTEN} \to \text{LISTEN}$ (`WAIT`):** The user paused mid-sentence. The LLM reads the partial transcript, detects syntactic or semantic incompleteness, and emits a wait control token, holding the floor open without triggering TTS.
   * **$\text{LISTEN} \to \text{SPEAK}$ (`RESPOND` / `INTERRUPT`):** The LLM recognizes that the user completed their request (or timed out), emits a start-speech token, and begins streaming textual response tokens to the Motor module.
   * **$\text{SPEAK} \to \text{SPEAK}$ (`CONTINUE`):** The LLM continues delivering its planned response while ignoring benign acoustic noise.
   * **$\text{SPEAK} \to \text{LISTEN}$ (`YIELD` / `BARGE-IN`):** While the system is speaking, the Perception module passes new user tokens. The LLM immediately detects that the user is intentionally taking the floor, emits a yield token, instantly halts the Motor module (canceling remaining audio buffers), and shifts back to `LISTEN`.
5. **Serialized Dialogue Representation:**
   The entire conversation is represented as a single, time-serialized chronological sequence where user perception chunks and system motor tokens are interleaved in real-time. Next-token prediction on this unified sequence naturally optimizes both *what to say* and *when to yield*.

---

### 5.2 Deep-Dive into X-Talk (arXiv:2512.18706)

**X-Talk** (SJTU, Dec 2025) directly challenges the trend toward monolithic "omni-models" (like Moshi and GPT-4o voice), demonstrating that a **systematically optimized modular cascade** can achieve sub-second latency while preserving the full reasoning, tool-calling, and fine-tuning benefits of decoupled systems.

```
┌────────────────────────────────────────────────────────────────────────┐
│  1. CLIENT-SIDE FRONTEND LAYER                                         │
│     FastEnhancer (Neural Denoise) ──► Silero VAD (Speech Detection)    │
│     *Instant Local Playback Mute on Speech Detection*                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ WebSocket Typed Events
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  2. EVENT CENTER (Asynchronous Event Bus with Priority Routing)        │
├───────────────────────────────────┬────────────────────────────────────┤
│  3. SPEECH UNDERSTANDING          │  4. LLM CONVERSATIONAL AGENT       │
│     * Zipformer/SenseVoice ASR    │     * LangChain Toolset            │
│     * Sliding-Window Cache        │     * Web Search (Tiered Serper)   │
│     * Omni-Captioner (Env Audio)  │     * Local RAG (Chroma + Qwen3)   │
│     * Pyannote ResNet34 Voiceprint│     * Timbre & Emotion Switching   │
├───────────────────────────────────┴────────────────────────────────────┤
│  5. SPEECH GENERATION (TTS Chorus: CosyVoice, ChatTTS, IndexTTS)       │
└────────────────────────────────────────────────────────────────────────┘
```

#### Key Architectural Innovations in X-Talk:

1. **Client-Side Edge Interruption (Zero-Round-Trip Barge-In):**
   * Rather than sending audio to the server and waiting for a server VAD $\to$ network packet $\to$ client mute cycle (which adds 150–350ms of perceived lag), X-Talk runs **FastEnhancer** (neural denoiser) and **Silero VAD** directly on the client (browser / edge device).
   * The millisecond speech energy is detected, the client **instantly halts local audio playback**, creating an immediate, responsive barge-in experience.

2. **Sliding-Window Cache for ASR:**
   * To bridge offline and streaming ASR, X-Talk maintains a cumulative buffer and an incremental buffer.
   * A sliding-window cache tracks prefix stability: once the text prefix remains stable across $W$ consecutive windows, it is finalized and committed to the LLM context, flushing the processed audio buffer.

3. **Buffered Statement Mechanism (Acoustic Latency Masking):**
   * External tool calls (database queries, web searches, calendar lookups) introduce unavoidable 500–1500ms network delays that break spoken conversational rhythm.
   * X-Talk introduces **buffered filler statements**: the moment an agent triggers a tool call, it speculatively synthesizes and speaks a natural acoustic placeholder (*"Let me pull up your schedule..."* or *"Checking that now..."*), completely masking the execution latency of the backend API.

4. **Multi-Rule False Interruption Tolerance:**
   To prevent background noise or benign user habits from erroneously killing the system's speech, X-Talk implements three validation filters before confirming a barge-in:
   * **Rule 1 (Audio Duration Gate):** Any user sound $< 0.5\text{s}$ is classified as transient noise.
   * **Rule 2 (Lexical Density Gate):** If the streaming ASR returns an empty string or a single isolated digit/letter, it is discarded.
   * **Rule 3 (Filler / Backchannel Whitelist):** Maintains a dictionary of conversational backchannels (*"uh-huh"*, *"yeah"*, *"mm"*). If the user's speech consists solely of backchannels while the system is speaking, X-Talk treats it as active listening, keeps the TTS playing, and commands the client to **resume audio playback**.

---

### 5.3 Comparative Matrix: Neural FSM vs. X-Talk for Dysarthric Speech

| System Property | Neural FSM (*NeurIPS 2024*) | X-Talk (*arXiv:2512.18706*) | Direct Implication for SAP Project |
| :--- | :--- | :--- | :--- |
| **Turn-Taking Arbiter** | Internal LLM control tokens (`WAIT`, `YIELD`, `RESPOND`). | Client-side VAD + Server-side heuristic validation rules. | **Neural FSM is smarter for dysarthria:** Acoustic VAD cutoffs fail on dysarthric pauses; an LLM evaluating semantic completeness understands that *"Set timer for..."* is incomplete even after 1.5s of silence. |
| **Tool Calling / RAG** | Text-based prompt generation. | Native LangChain integration + Buffered statement latency masking. | **X-Talk is better engineered for tools:** Our 28-tool schema requires strict JSON validation and buffered fillers while querying calendars/alarms. |
| **Interruption Precision** | High semantic precision (understands intent to interrupt vs. cough). | Rule-based (0.5s duration threshold + backchannel whitelist). | X-Talk's 0.5s rule risks cutting off dysarthric speakers who produce short, low-intensity phonemes. |
| **Engineering Complexity** | Requires instruction fine-tuning / aligning an LLM to emit control tokens. | Plug-and-play modular framework (uses off-the-shelf models and event bus). | X-Talk can be deployed immediately with existing checkpoints; Neural FSM requires fine-tuning an LLM on serialized dialog tokens. |

---

## 6. Deep Internal Mechanics & Curated Learning Roadmap: Moving Beyond the Black Box

To transition from treating ASR and full-duplex systems as black-box APIs to engineering their internal mechanisms, you must master the mathematical foundations, decoding algorithms, and low-level streaming pipelines.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE SPOKEN DIALOG SYSTEMS LEARNING ROADMAP                      │
├────────────────────────────────────────────┬───────────────────────────────────────────┤
│  TRACK 1: STREAMING ASR INTERNALS          │  TRACK 2: FULL-DUPLEX & TURN-TAKING       │
│  * Acoustic Feature Extraction (Log-Mel)   │  * Audio Pipeline Plumbing (PCM/WebRTC)   │
│  * Causal Masking & Chunked Attention      │  * Acoustic Echo Cancellation (AEC)       │
│  * CTC Loss & Neural Transducers (RNN-T)   │  * Predictive Turn-Taking (VAP / TurnGPT) │
│  * Delayed-Streams Autoregression (DSM)    │  * Multi-Stream Codec Modeling (Moshi)    │
└────────────────────────────────────────────┴───────────────────────────────────────────┘
```

---

### Track 1: Streaming Automatic Speech Recognition (ASR) Internals

#### 1. What Happens Under the Hood:
1. **Front-End Acoustic Representations:**
   * Raw audio waveforms (16 kHz, 16-bit PCM) are converted via Short-Time Fourier Transform (STFT) using a 25ms Hamming window with a 10ms hop size.
   * Converted into an **80-dimensional Log-Mel Spectrogram**, which models human auditory frequency sensitivity (Mel scale).
2. **Streaming Acoustic Encoders:**
   * **The Lookahead Constraint:** Offline models (like standard Whisper) use bidirectional, non-causal self-attention, looking into the entire future audio. Streaming encoders enforce **causal masking** or **chunked attention** (e.g., processing 160ms chunks with a fixed 80ms lookahead), capping algorithmic latency at the cost of slight acoustic ambiguity.
   * **Conformer & Zipformer:** Modern encoders interleave Depthwise Separable Convolutions (capturing local phonetic details) with Multi-Head Self-Attention (capturing global syntactic dependencies).
3. **The Three Core Decoding Paradigms:**
   * **CTC (Connectionist Temporal Classification):** Introduces a blank token $\epsilon$ to align variable-length audio frames to shorter text token sequences without intermediate alignments. *Limitation:* Assumes conditional independence between output tokens given the acoustic input, preventing strong language modeling.
   * **Neural Transducers (RNN-T / Conformer-Transducer):** Eliminates CTC's independence flaw by coupling an **Acoustic Transcription Network** $h_t^{\text{enc}}$ with an autoregressive **Prediction Network** $p_u^{\text{pred}}$ via a **Joint Network**:
     $$z_{t,u} = \text{Joint}(h_t^{\text{enc}}, p_u^{\text{pred}}) \implies P(y_{t,u} \mid x_{1:t}, y_{1:u-1})$$
     This allows frame-synchronous streaming decoding where multiple tokens can be emitted for a single audio frame (or none, via blank $\varnothing$). This is the industrial foundation of low-latency assistants (Google Assistant, Apple Siri, Icefall).
   * **Delayed-Streams Autoregressive Models (Voxtral DSM):** Uses stream-synchronous next-token prediction with dynamic delay $\tau \in [80, 2400]\text{ms}$, interleaving acoustic padding $[P]$ tokens and word-boundary $[W]$ tokens to synchronize the decoder with live audio.

#### 2. Essential Curated Resources for Streaming ASR:
* **The Foundational Textbook:**
  * **Jurafsky & Martin, *Speech and Language Processing* (3rd ed. draft):** Read *Chapter 16: Automatic Speech Recognition* and *Chapter 17: Speech Recognition: Advanced Topics*. Covers STFT, Mel filterbanks, CTC forward-backward alignment, and WFST decoding.
* **The Canonical Lecture Course:**
  * **CMU 11-751 / Shinji Watanabe (Creator of ESPnet):** *Speech Recognition and Understanding*. Publicly available lecture slides and videos cover the mathematical derivation of CTC loss, Transducers (RNN-T), and Conformer self-attention.
* **The Hands-On Repositories (Read the Source Code):**
  * **[k2-fsa / icefall & sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx):** Developed by Daniel Povey (creator of Kaldi). This is the gold standard for high-performance streaming ASR in C++ and Python. Study `pruned_transducer_stateless` in Icefall to understand how streaming memory cache tensors are passed between audio chunks.
  * **[Hugging Face Audio Course (Chapter 5: Speech Recognition)](https://huggingface.co/learn/audio-course/chapter5/introduction):** Practical walkthrough of feature extractors, CTC fine-tuning, and audio data collation.

---

### Track 2: Full-Duplex Systems & Turn-Taking Internals

#### 1. What Happens Under the Hood:
1. **The Low-Level Audio & Networking Plumbing:**
   * **Audio Transport:** Real-time audio streams cannot use HTTP request/response. They use **WebSockets** or **WebRTC DataChannels** transmitting raw 16kHz PCM chunks or compressed Opus frames every 20ms.
   * **Acoustic Echo Cancellation (AEC):** In full-duplex, the speaker and microphone are active simultaneously. Without AEC (e.g., WebRTC APM module), the system’s microphone captures its own TTS voice, causing an infinite acoustic feedback loop.
   * **Asynchronous Task Cancellation:** When a user barge-in event occurs, the server must execute a non-blocking cancellation (e.g., `asyncio.Task.cancel()`), instantly flushing downstream TTS synthesis buffers and emptying OS audio device queues.
2. **Predictive Turn-Taking vs. Energy VAD:**
   * Traditional VAD only detects *past* energy (is there silence right now?).
   * Full-duplex systems use **continuous turn-completion forecasting**:
     * **Voice Activity Projection (VAP):** Rather than thresholding energy, a neural model continuously outputs the probability distribution of who will speak in the upcoming 2-second window (divided into discrete bins: $[0, 200\text{ms}], [200, 600\text{ms}], \dots$). It detects intonation drop (pitch fall) and syntactic completion *before* silence occurs.
3. **Multi-Stream Audio Modeling:**
   * Models like **Moshi** (Kyutai) compress audio into discrete tokens at 12.5 Hz using the **Mimi neural audio codec**.
   * The LLM models multiple parallel streams simultaneously: User Audio Tokens, User Text Tokens, Agent Text Tokens, Agent Audio Tokens. Turn-taking is completely internalized: the model emits audio silence tokens when listening and voice tokens when speaking.

#### 2. Essential Curated Resources for Full-Duplex:
* **The Breakthrough Full-Duplex Model:**
  * **Moshi: a speech-text foundation model for real-time dialogue** ([arXiv:2410.00037](https://arxiv.org/abs/2410.00037) / [GitHub: kyutai-labs/moshi](https://github.com/kyutai-labs/moshi)). Dissect the architecture: 80ms latency Mimi neural codec, Helium LLM, and multi-stream token interleaving.
* **The Predictive Turn-Taking Foundation:**
  * **Voice Activity Projection (VAP)** (*Ekstedt & Skantze*, Interspeech 2022 / IEEE TASLP 2024; [GitHub: ErikEkstedt/VoiceActivityProjection](https://github.com/ErikEkstedt/VoiceActivityProjection)). The definitive framework for learning continuous turn-taking from prosody and acoustics.
  * **TurnGPT** (*Findings of EMNLP 2020*): How language models predict turn-completion from incremental transcripts.
* **Open-Source Modular Frameworks (Engineering Blueprint):**
  * **[X-Talk Source Code](https://github.com/xcc-zach/xtalk):** Dissect `event_bus.py`, `service_manager.py`, and `frontend/vad.py` to see how event routing, client-side VAD, and buffered filler masking are implemented in Python.
  * **[Pipecat AI](https://github.com/pipecat-ai/pipecat):** The leading open-source framework for voice-to-voice agents. Study its pipeline design (`Transport -> VAD -> STT -> LLM -> TTS -> Transport`).

---

### Recommended 2-Week Learning Plan

| Phase | Focus Area | Concrete Hands-On Milestone |
| :--- | :--- | :--- |
| **Days 1–4** | **ASR Acoustic Pipeline & Streaming Transducers** | 1. Read Jurafsky & Martin (Ch. 16: ASR & CTC).<br>2. Run a minimal streaming Zipformer/Conformer inference loop in `sherpa-onnx` on a local WAV file, inspecting chunk cache updates. |
| **Days 5–8** | **Streaming Latency & Dysarthric Fine-Tuning** | 1. Read Voxtral DSM (arXiv:2602.11298, Sec. 3).<br>2. Understand why CTC and Transducer blank tokens collapse repetitive dysarthric speech differently. |
| **Days 9–11** | **Turn-Taking, VAP, & State Machines** | 1. Read the DuplexLM Survey (arXiv:2606.19453) and VAP paper.<br>2. Trace the 5-state transitions (`IDLE`, `LISTEN`, `WAIT`, `SPEAK`, `DUAL`) on an annotated dysarthric utterance with long pauses. |
| **Days 12–14** | **Modular Orchestration & Event Plumbing** | 1. Clone and trace `X-Talk` (`event_bus.py`) and `Pipecat`.<br>2. Implement a mock async Python loop where a synthetic user interrupt event immediately cancels an active streaming generator. |

---

## 7. Active Discussion & Evolution Log

* **2026-10-18 (Session 1):** Initial synthesis established. Key alignment around modular design (*X-Talk*), Neural State Machine (*NeurIPS 2024* / *DuplexLM*), and speculative execution (*Stream RAG*) for dysarthric spoken dialogue.
* **2026-10-18 (Session 2):** In-depth technical breakdown added for **Neural FSM** (two-state physical actuator controlled by LLM next-token control emissions) and **X-Talk** (client-side edge VAD, sliding-window ASR caching, buffered statement latency masking, and 3-rule false interruption tolerance). Compared both paradigms against dysarthric speech requirements.
* **2026-10-18 (Session 3):** Added **Section 6: Deep Internal Mechanics & Curated Learning Roadmap**, detailing acoustic feature extraction, CTC vs. Transducers (RNN-T), delayed streams, WebRTC/AEC plumbing, Voice Activity Projection (VAP), Moshi multi-stream modeling, and a structured 2-week learning plan with authoritative references (Jurafsky & Martin, CMU 11-751, sherpa-onnx, Moshi, X-Talk, Pipecat).
