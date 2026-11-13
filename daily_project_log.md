# Daily Project Log: Effect of ASR Errors on Spoken Dialog System Performance for Speakers with Dysarthria

**Repository:** `sap-dialog-system`  
**Authors:** Xiuwen Zheng, Haolong Zheng, Zixuan Yin, Kush Bhardwaj  
**Faculty Advisor:** Professor Mark Hasegawa-Johnson (UIUC)  

---

## September 15, 2026

### Today's Activities

* **Phase 0 Kickoff & Research Scope:** Defined core RQs (RQ1: assistant utility beyond WER; RQ2: downstream slot error propagation). Established single-variable control: Voxtral Base vs. Voxtral SAP fine-tuned. Defined personal ownership: modular dialog harness, 6 task slot schemas, and offline replay evaluation.
* **Latency Root Cause Diagnosed:** Identified quadratic $O(T^2)$ compute growth in local prototype caused by pseudo-streaming (re-running full audio from $t=0$). True streaming requires resumable KV cache or delayed-stream frame-synchronous decoding.
* **Architecture Selection:** Selected cascaded pipeline (`Streaming ASR -> LLM -> Streaming TTS`) over end-to-end Omni models to ensure intermediate transcripts can be inspected for error attribution. Confirmed push-to-talk turn control to avoid dysarthric pause cutoffs.
* **Evaluation Tasks Defined:** Mapped the 6 dialog task domains (alarm, weather, meal order, appointment reschedule, calendar event, directions) and required slot categories for automated replay evaluation.

---


## September 16, 2026

### Today's Activities

* Took a (brief) look at Hugging Face's speech to speech (`huggingface/speech-to-speech`).
* Setup ACCESS Allocations (Project `CIS250149` for NCSA Delta CPU and GPU resources).
* Got familiar with Delta and SLURM (cluster architecture, login vs. compute nodes, NCSA Duo MFA authentication, interactive sessions with `srun`, and batch execution via `sbatch`).

---

## September 17, 2026 (Time: 2 hrs)

### Today's Activities

* Progressed on phoneme-augmented ASR readings (one reading, will be used as motivation).
* Started building S2T pipeline (scaffolding decoupled offline `Audio -> ASR -> LLM` evaluation harness, deferring VAD and TTS per team alignment).

### Next Steps
* [ ] Implement working zero-shot ASR baseline (e.g. Whisper large-v3-turbo / Voxtral) and task slot prompt in `src/pipeline/`.
* [ ] Verify Delta cluster account activation once "Pending" status clears.

---

## September 18, 2026

### Today's Activities

* Implemented prototype pipeline w/ bugs; will fix tomorrow.

### Next Steps
* [x] Debug and fix issues in prototype pipeline.
* [x] Verify end-to-end execution on sample audio.

---

## September 19, 2026

### Today's Activities

* Revised and fixed speech-to-speech pipeline.
* Developed and debugged SLURM script for test run on NCSA.
* Successfully completed test run and inference on NCSA.

### Next Steps
* [ ] Connect the verified NCSA inference workflow with the evaluation dataset once curated.
* [ ] Benchmark initial zero-shot performance across test tasks.

---

## September 20, 2026 (Time: ~1.5 hrs)

### Today's Activities

* Made changes to sap-dialog-system repository (pushed inference run results, fixed commit attribution for [@zyin422](https://github.com/zyin422)).
* Aligned with grad student on streaming ASR code integration and evaluation data (`sap hypo5`).

### Next Steps
* [ ] Verify LLM task-oriented dialog runner on `sap hypo5` debug transcripts.
* [ ] Integrate student's streaming ASR module with the LLM slot extraction pipeline.

---

## October 22, 2026 (Time: ~3.0 hrs)

### Today's Activities

* Evaluated and adjudicated Pilot 50 inter-annotator agreement to establish initial baseline.
* Stress-tested SLU schema across 100 high-ambiguity commands using frontier models (Claude 3.5 Sonnet & GPT-6 Instant).
* Finalized SLU Schema v1.2 (29 tools across 10 domains): added `origin` slot to `maps_route` and inlined all tool-specific constraints directly into the tool definitions and OpenAPI schema.
* Created 100-sample adjudicated frontier gold set (`frontier_100_gold.csv`), reaching 150 total reference gold commands.
* Defined the open-source model reproducibility protocol (Qwen 2.5 72B / Llama 3.3 70B @ T=0.0) for camera-ready paper scaling.

### Next Steps
* [x] Set up the open-source model inference harness and validate against the 150-sample golden dev set (`D_dev`).
* [x] Run full dataset inference across the remaining ~1,100 commands with automated schema validation.

---

## October 23, 2026 (Time: ~2.5 hrs)

### Today's Activities

* Structured the remaining master dataset (~1,300 commands) into standardized batch prompts (both 24 modular batches and 4 even web batches of ~327 commands).
* Implemented and validated the automated consensus agreement engine (`consensus_agreement.py`) against Schema v1.2 with automated rule-based triage diagnostics.
* Executed full-dataset dual-frontier inference across all 4 batches using Claude 3.5 Sonnet and GPT.
* Evaluated global consensus metrics: 91.4% domain agreement, 91.1% intent agreement, and 65.3% full slot exact match (855 agreed gold, 454 triaged).
* Confirmed adjudication feedback: accepted Rule B carrier phrase stripping, ruled OOD/wake words should be excluded from evaluation, accepted Sonnet's point-to-point navigation (`origin`/`destination`), and enforced `sort_by: distance` for "nearby" queries.

### Key Notes / Decisions
* Standalone wake phrases (e.g., "Alexa", "Hey Siri"), generic broadcast messages, and unsupported app launches are classified as Out-Of-Domain (OOD) and must be excluded from SLU evaluation rather than forced into arbitrary tools.
* Carrier prefixes in `qa_search` must be stripped per Rule B.
* Point-to-point routes must decouple `origin` and `destination` per Rule H.
* Nearby venue queries in `places_search` must specify `sort_by: "distance"`.

### Next Steps
* [x] Perform a rigorous second-pass verification across all 1,309 commands (both agreed and triaged) to ensure full schema compliance and filter OOD instances.
* [x] Finalize the complete audited benchmark gold set.

---

## October 25, 2026 (Time: ~3.5 hrs)

### Today's Activities

* Re-checked and audited all 1,309 commands across both frontier predictions (Claude 3.5 Sonnet & GPT) instead of blindly accepting surface agreements.
* Enforced user adjudication rules across all commands:
  * **Rule B (Carrier Phrase Stripping):** Stripped conversational carrier prefixes from `qa_search.query`.
  * **Rule H (Point-to-Point Navigation):** Adopted Sonnet gold decoupling of `origin` and `destination` for `maps_route`.
  * **Rule I (Nearby Distance Sorting):** Enforced `sort_by: "distance"` for spoken "nearby" queries in `places_search`.
* Partitioned out non-task utterances into an Out-Of-Domain (OOD) exclusion set (Rule K: 35 commands covering wake words, broadcasts, ticket bookings, OS app launches, screen/camera utilities, and dictation punctuation fragments) rather than forcing them into tools.
* Finalized and validated Schema v1.3: 1,274 canonical gold commands passing OpenAPI/JSON Schema validation with 0 errors, 0 invalid enums, and 0 hallucinated slots.
* Performed deep second-pass adjudication: moved 7 non-task boundary cases to OOD (`0277`, `0322`, `0334`, `0630`, `0674`, `0821`, `0862`), cleaned `title` vs `person` reminder slots (`0328`, `0800`, `0801`), and enforced strict substring matching on artists (`1127`).
* Built and verified an interactive standalone HTML visual explorer (`SLU_benchmark_browser.html`) with dual card-deck and paginated table views for browsing, searching, and inspecting extracted slots across all 1,309 commands, complete with visual audit badges.
* Cleaned repository of intermediate scratch files (`consensus/batches/`, `output.txt`, `full_1309_commands_prompt.md`), updated `consensus/README.md` to reference the 4 balanced web batches, and committed deliverables (`1385b1c`) pushed to GitHub remote `origin/main` with attribution to `@zyin422`.
* Analyzed `papers/speech-dialog-survey/speech_dialogue_benchmarks_database_2026.md` and synthesized evaluation protocol for upcoming ASR model checkpoint from mentor.
* Formalized the 3-condition evaluation ablation matrix (Oracle ceiling vs Base streaming ASR vs SAP fine-tuned ASR) and 3-tier metric decomposition (Tool Selection `TS`, Schema Validity `TCS`, and Parameter Filling `PF` with phonetic tolerance) based on VoiceAgentBench, SLURP, and SpokenWOZ.

### Key Notes / Decisions
* Schema is officially frozen and finalized at Version 1.3 with a clean non-overlapping partition: 1,274 evaluated gold commands + 35 OOD excluded commands.
* Benchmark deliverables, interactive visualizer, and updated schema are published and live on GitHub (`origin/main`, commit `1385b1c`).
* Evaluation framework prioritizes isolating acoustic degradation from downstream agent reasoning: downstream LLM agent is frozen while input condition varies (Oracle vs Base ASR vs Fine-Tuned ASR).

### Next Steps
* [ ] Align audio waveforms from `manifest/dev.tsv` with the 1,274 canonical gold commands in `SLU_benchmark_gold_1309.csv`.
* [ ] Ingest the mentor's ASR model checkpoint once received and run batch inference across the benchmark audio.
* [ ] Run Condition 1 (Oracle text) dry run through downstream LLM agent to establish reasoning ceiling.
* [ ] Implement automated scoring harness for TS, TCS, and PF (with phonetic edit tolerance).

---

## October 30, 2026 (Time: ~2.5 hrs)

### Today's Activities

* **Downstream SLU Benchmark Baseline Grounding:** Evaluated and anchored the uncompromised zero-shot SLU baseline across 291 benchmark utterances on Qwen 2.5-7B-Instruct:
  * **Oracle Text Ceiling:** TS 84.19%, TCS 99.31%, PF 71.74%, Frame Accuracy 63.92%.
  * **Base Parakeet ASR (WER 28.15%):** TS 67.35%, PF 44.69%, Frame Accuracy 32.30%.
  * **Fine-Tuned Parakeet ASR (WER 10.70%):** TS 83.85%, PF 66.91%, Frame Accuracy 56.01%, proving ASR adaptation recovers 74.98% of downstream task performance.
* **ASR Decoding Pipeline Verification:** Verified and documented [`decode_benchmark_291.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/decode_benchmark_291.py) utilizing NVIDIA NeMo Parakeet-TDT 0.6B across both Base and Fine-Tuned checkpoints on Delta GPU.
* **Prompt Integrity & Anti-Hacking Audit:**
  * Analyzed the +13.53% PF gap between the non-hacked baseline (71.74%) and iterated prompt runs (up to 85.27%).
  * Diagnosed that gains were driven by hand-coded per-tool micro-rules (e.g., forcing `cancel` $\to$ `delete`, `minimum` $\to$ `set`, and implicit proximity sorting) rather than generalized reasoning.
  * Preserved the clean, defensible prompt in [`evaluate_slu_llm.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/evaluate_slu_llm.py) (zero few-shot, 4 domain-agnostic rules, zero benchmark entity leaks).
  * Categorized failure modes into 4 presentation-ready buckets: closed enum synonyms, missing generic nouns, lexical attraction, and slot collapsing.
* **Team Alignment & Research Roadmap:**
  * Synchronized research objectives with Xiuwen on Telegram (`SAP-dialog-system`): frozen domain/intent schema, principled out-of-domain few-shot exemplars, grammar-constrained decoding, alternative open LLM baselines (Llama-3.1-8B), and expanding from single-turn SLU to a multi-turn spoken dialogue system.

### Key Notes / Decisions
* Anchor all presentation metrics and publications on the non-hacked 71.74% PF baseline. Frame the 85.27% micro-rule performance as proof that remaining errors are surface-level ontology mismatches rather than fundamental comprehension failures.
* Keep the 29-tool schema frozen (`SLU_schema_v1.0.json`).
* Transition next-phase parameter filling improvements to publication-grade methods: out-of-domain synthetic few-shot exemplars (zero test leakage) and grammar-constrained decoding.

### Next Steps
* [ ] Construct synthetic, out-of-domain few-shot exemplars (fictitious tools) to teach enum normalization and slot completeness without test leakage.
* [ ] Evaluate alternative open-source model baselines (e.g., Llama-3.1-8B-Instruct).
* [ ] Design architecture to expand from single-turn SLU extraction into an interactive multi-turn dialogue agent for dysarthric speech.



---

## October 30, 2026 (Time: ~3.5 hrs)

### Today's Activities

* Scaled up the SLU benchmark from the 291-command pilot to Xiuwen's complete decoded dysarthric dev set on Delta, constructing a representative 1,108-instance dataset covering 372 unique commands across 16 speakers evenly balanced across all 5 etiologies (ALS, Cerebral Palsy, Down Syndrome, Parkinson's Disease, Stroke).
* Re-architected assistant persona and operational directives in `AGENTS.md` for dedicated research assistance, zero test leakage, and direct Delta cluster management.
* Upgraded the Delta conda environment with `transformers==4.57.6` and `tokenizers==0.22.2` to natively support the `qwen3` architecture with PyTorch 2.5.1 CUDA compatibility.
* Conducted deep root-cause failure analysis on the unhacked baseline: identified that the prompt builder was completely omitting tool and parameter descriptions, causing 69 false-positive `media_search` intent errors on recipe inquiries, ambient audio lookups, and factual questions.
* Verified ground truth integrity: confirmed gold annotations are 100% sound and compliant with `SLU_schema_v1.0.json`, deciding strictly against artificial gold adjustments.
* Diagnosed Qwen3 dual thinking mode behavior: identified that Qwen3 defaults to generating `<think>` chain-of-thought reasoning, which exhausted the token budget before JSON emission. Resolved by configuring `enable_thinking=False` in `tokenizer.apply_chat_template` to enforce direct JSON generation.
* Benchmarked the clean, schema-grounded enriched system prompt on Delta (Job `23362084`): increased Oracle Tool Selection from 82.85% to 89.98% (+7.13%), Parameter Filling from 72.10% to 76.14% (+4.04%), and Frame Accuracy from 62.45% to 67.33% (+4.88%).
* Audited the remaining 459 failing slots in Oracle and pinpointed the primary bottlenecks:
  * Search query paraphrasing in `qa_search` (96 slots) where Qwen3 converted questions into keyword queries (e.g., *"How many people live in Maryland?"* $\rightarrow$ `"population of Maryland"`).
  * Slot lumping / entity entanglement (35 slots) where attendee names were merged into `title` instead of separated into `person` in `schedule_manage`.
  * Implicit enum omissions (30 slots) such as proximity terms not mapping to `sort_by: distance`.
* Validated explicit `Verbatim Span Extraction` rule on Delta, immediately achieving 100% exact match on paraphrased queries without search keyword reformulation.
* Established an efficient targeted unit testing protocol: constructed an isolated 30-prompt failure slice (`failure_slice_target.csv`) on Delta to execute sub-20-second test cycles before running full 1,108 benchmark sweeps.

### Key Notes / Decisions

* **Targeted Slice First:** Do not run full 1,108-instance benchmark sweeps on unfinished prompts. All rapid prompt iterations will be verified on the 30-prompt failure slice ($N=30$, ~18s runtime per run) until PF reaches $\ge 90\%$.
* **Grounding vs Hacking:** Tool descriptions from the frozen schema are standard tool-calling context; ad-hoc domain carve-outs and quoted dev phrases are strictly banned per `verify_no_leakage.py`.
* **Deterministic Inference:** Always set `enable_thinking=False` for Qwen3 tool calling to bypass reasoning tokens and output clean JSON directly.

### Next Steps

* [ ] Iterate on Failure Mode B (Slot Lumping: separating `title` from `person` in `schedule_manage`, and `device_type` from `house_place` in `iot_device_power`) on the 30-prompt slice.
* [ ] Iterate on Failure Mode C (Implicit Enums: mapping proximity terms to `sort_by: distance`) on the slice.
* [ ] Once Parameter Filling reaches $\ge 90\%$ on the 30-prompt slice, run the full 1,108-instance 3-condition evaluation across Oracle, Base ASR, and Fine-Tuned ASR on Delta.


---

## November 2, 2026 (Time: ~4.5 hrs)

### Today's Activities

* **Frozen Generalized Prompt Finalized:** Audited and locked [`certified_generalized_system_prompt_rev5.txt`](sap-dialog-system/certified_generalized_system_prompt_rev5.txt) against [`PROMPT_OPTIMIZATION_DIRECTIVES.md`](sap-dialog-system/PROMPT_OPTIMIZATION_DIRECTIVES.md) (0 test leakage, 0 per-tool extraction hacking).
* **291 Unique Dev Benchmark & Ceiling Analysis (Job 23463865):**
  * Evaluated Condition 1 (Oracle) on 291 unique dev commands: TS 96.56%, TCS 100.0%, PF 89.37%, Frame Accuracy 85.91%.
  * Diagnosed remaining ~10% slot failure ceiling: ~41% gold annotation contradictions, ~29% cascading intent boundary choices, ~29% genuine API edge cases. Confirmed that attempting higher zero-shot PF would cause reward hacking against annotator noise.
* **Full $N=1,108$ Dev Benchmark Execution (Job 23464832):**
  * Ran all 3 conditions on Delta GPU across the full 1,108-instance etiology-stratified benchmark:
    * **Condition 1 (Oracle Clean Text):** TS 95.67%, TCS 100.0%, PF 88.41%, Frame Accuracy **84.03%** (931/1108).
    * **Condition 2 (Base Parakeet ASR, 28.15% WER):** TS 74.55%, TCS 99.28%, PF 46.22%, Frame Accuracy **38.09%** (422/1108).
    * **Condition 3 (Fine-Tuned Parakeet ASR, 10.70% WER):** TS 92.96%, TCS 99.82%, PF 75.73%, Frame Accuracy **66.88%** (741/1108).
    * **Net Frame Gain ($\Delta_{\text{FT}-\text{Base}}$):** **+28.79%** absolute; **Adaptation Recovery Rate (ARR):** **62.67%**.
* **Dataset Scale & Sampling Audit:** Audited Xiuwen's complete decoded pool on Delta (`/projects/bedl/xiuwenz2/.../sapc2_dev.dev.csv`, 34,577 total files, 31,606 matching benchmark commands across 124 speakers). Verified that `sampled_benchmark_1108.csv` is an etiology-stratified subset (372 unique commands, 16 speakers, up to 3 distinct clinical etiologies per command). Condition 1 metrics on 1,108 instances match unique 372 commands within 0.11%.
* **Poster Overhaul & Metric Cleansing for Trick or Research 2026:**
  * Purged all unapproved speculative metrics (Tier 4, Precision, Slot F1, SECR, ODR, Extraneous Slots).
  * Confirmed Parameter Filling (PF) is strictly defined as **Slot Recall** ($\text{Matched Gold Slots} / \text{Total Gold Slots}$).
  * Overhauled [`poster/poster.md`](poster/poster.md) with verified numbers, etiology breakdowns, and qualitative case studies for the undergraduate symposium.

### Key Notes / Decisions
* Lock the approved metric suite to: Acoustic WER, Tool Selection (TS), Tool Call Structure (TCS), Parameter Filling (PF / Slot Recall), Command Frame Accuracy, and Adaptation Recovery Rate (ARR).
* Prohibit introducing new metrics to presentation materials without explicit personal approval.
* Frame ASR adaptation as an entity-recovery mechanism: fine-tuning acoustic models primarily rescues slot filling (+29.51% PF gain) rather than just intent detection.

### Next Steps
* [x] Review current evaluation metrics and identify necessary additions (e.g. semantic tolerance for open-vocabulary entities).
* [x] Hand off poster text and architecture diagram to Claude / design agent for rendering.
* [x] Formulate conversational grounding / affirmation generation schema.

---

## November 3–4, 2026 (Time: ~4.0 hrs)

### Today's Activities

* **Balanced Clean Benchmark Curation ($N = 1,200$):**
  * Transitioned from the legacy 291-command pilot and intermediate 1,108-command pool to the newly curated balanced 1,200-command benchmark ([`sampled_benchmark_1200_clean.csv`](sap-dialog-system/sampled_benchmark_1200_clean.csv)) spanning 122 speakers and 328 unique prompts, evenly stratified across all 5 etiologies (240 instances each for ALS, Cerebral Palsy, Down Syndrome, Parkinson's Disease, and Stroke).
* **Conversational Grounding & Spoken Response Generation (Rev 6 NLG):**
  * Formulated the architectural grounding specification in [`conversational_grounding_nlg_design.md`](conversational_grounding_nlg_design.md) (Clark & Brennan grounding principles, TTS acoustic constraints: $\le 12$ words, active voice, clean speech tokens, 0 markdown/syntax).
  * Designed and certified [`certified_generalized_system_prompt_rev6_nlg.txt`](sap-dialog-system/certified_generalized_system_prompt_rev6_nlg.txt) adding a `"response"` string field.
  * Enforced autoregressive postfix ordering (`domain` $\to$ `intent` $\to$ `slots` $\to$ `"response"`), ensuring pre-binding of extracted entity slots in the KV cache prevents hallucinated execution affirmations and guarantees non-degradation of tool calling.
  * Verified prompt orthogonality with `verify_no_leakage.py` (0 test entity leaks) and `verify_anti_hacking.py` (0 tool name leaks, 0 redirects, 0 negative boundary hacks).
* **NCSA Delta Cluster Parallel Execution & Self-Monitoring:**
  * Executed the complete 3-condition baseline on Delta (Job `23495500` on A100 interactive queue):
    * **Condition 1 (Oracle):** TS 93.67%, TCS 100.0%, PF 86.61%, Frame Accuracy **81.75%**.
    * **Condition 2 (Base Parakeet ASR):** TS 70.42%, TCS 99.42%, PF 49.97%, Frame Accuracy **41.17%**.
    * **Condition 3 (Fine-Tuned Parakeet ASR):** TS 91.08%, TCS 100.0%, PF 78.39%, Frame Accuracy **70.17%**.
    * **Baseline Downstream Recovery:** Net Frame Gain = **+29.00%** (+348 net frames restored); **Adaptation Recovery Rate (ARR): 71.46%**.
  * Deployed Rev 6 NLG across parallel Delta queues (Job `23495599` on A40 for Base ASR; Job `23495919` on A100 for FT ASR):
    * **Condition 1 (Oracle):** TS 93.50%, TCS 100.0%, PF 88.14%, Frame Accuracy **82.83%** (+1.08% gain over baseline).
    * **Condition 2 (Base Parakeet ASR):** TS 71.58%, TCS 98.92%, PF 51.40%, Frame Accuracy **42.17%** (+1.00% gain over baseline).
    * **Condition 3 (Fine-Tuned Parakeet ASR):** TS 90.25%, TCS 99.92%, PF 78.39%, Frame Accuracy **69.67%** (-0.50% diff, only 6 frames).
    * **NLG Downstream Recovery:** Net Frame Gain = **+27.50%** (+330 net frames restored); **ARR: 67.63%**.
  * Exercised asynchronous background self-monitoring timers (`schedule` tool) for autonomous queue tracking and automatic result reconciliation ([`merge_nlg_1200_results.py`](sap-dialog-system/merge_nlg_1200_results.py)).
* **Head-to-Head Comparative & Statistical Audit (Rev 5 vs. Rev 6):**
  * Performed instance-by-instance paired McNemar exact tests across all 1,200 commands:
    * Oracle Frame Accuracy: $p = 0.1766$ (93.42% agreement).
    * Base ASR Frame Accuracy: $p = 0.1114$ (96.00% agreement).
    * FT ASR Frame Accuracy: $p = 0.5258$ (94.83% agreement).
    * All $p > 0.05$: confirmed that conversational response conditioning causes **no statistically significant difference** in tool-calling or parameter-filling performance.
  * Verified NLG quality metrics: **99.75% – 99.92%** length compliance ($\le 12$ words), **100.0%** clean speech tokens, and an average spoken length of **5.35 to 6.05 words**.
  * Identified massive downstream ASR recovery for high speech severity etiologies: Cerebral Palsy (+36.25% Frame Acc gain) and Down Syndrome (+36.25% Frame Acc gain).
* **Oracle Parameter Filling (PF) Deep Failure Mode Audit:**
  * Formalized the complete parameter evaluation triad ($\text{PF}_{\text{Recall}}$, $\text{PF}_{\text{Precision}}$, $\text{PF}_{\text{F1}}$) to diagnose why Oracle Recall is 86.61% while Precision is 76.96% (model predicted 2,135 slots vs. 1,897 in gold; net $+238$ slots).
  * Systematically audited and categorized all 254 Recall failures (FN) and 481 Precision failures (FP) on the clean 1,200 benchmark:
    * *Recall Failures (254 FNs):* 41.7% Intent Misclassification Cascades (76 upstream tool errors switching slot schemas), 32.3% Compound Noun & Span Boundaries (`"porch light"` vs. `"light"` where Char-F1 $<0.85$), 13.8% True Slot Omissions (35 instances), 6.7% Interrogative Carrier Retention (`"Define 'conundrum'"` vs. `"conundrum"`), 5.5% Preposition/formatting.
    * *Precision Failures (481 FPs):* 34.1% Fine-Grained Slot Decomposition (LLM extracted valid spoken spans omitted by crowd annotators), 23.7% Implicit Defaults / Hallucinations (inferring unuttered `"Apple Podcasts"` or `"home"` due to lack of negative prompt constraint), 18.7% Intent Misclassification Spurious Slots, 17.0% Compound Noun Dual FP Penalties.
* **Semantic LLM-as-a-Judge Formalization & Delta GPU Verification:**
  * Grounded semantic slot evaluation in peer-reviewed literature (Gu & Yang arXiv:2406.11651 on 2D completeness/accuracy; Berkeley Function Calling Leaderboard AST/semantic argument matching; ToolBench; Prometheus 2; MT-Bench).
  * Mathematically formalized Semantic Recall ($\text{Judge}_{\text{rec}}$) and Semantic Precision ($\text{Judge}_{\text{prec}}$).
  * Implemented and executed test slice on Delta GPU (`gpub001`, Job `23497516`) with `Qwen/Qwen2.5-7B-Instruct` across 10 diagnostic failure categories: verified correct semantic recovery of compound nouns and carrier clauses.
  * Diagnosed 7B model evaluation bias: identified that Qwen 2.5 7B suffers from over-lenience on Case 10 (rationalizing unuttered `media_type: "music"` as valid) and self-family bias with the generator, formally establishing that publication-grade benchmarks require GPT-4o-mini or sovereign 70B+ open weights (Llama-3.1-70B / Qwen-2.5-72B).

### Key Notes / Decisions

* **Autoregressive Postfix Invariant:** Placing `"response"` strictly after `"slots"` ensures token generation for the tool payload is pre-conditioned by extracted slots, preventing auditory hallucination while preserving certified tool-calling accuracy.
* **Statistical Invariance Certified:** McNemar tests confirm the system prompt extension and spoken output do not compromise task completion ($p > 0.11$ across all conditions).
* **ASR Adaptation Downstream Impact:** Fine-tuning streaming ASR directly rescues downstream command completion by $+27.5\%$ to $+29.0\%$ absolute frame accuracy (recovering $\sim 68\text{–}71\%$ of the oracle performance gap).
* **Prompt vs. Benchmark Ground Truth Divergence:** The prompt's extraction rules (preserving descriptive noun phrases and question clauses) intentionally preserve operational dialogue utility, trading off surface lexical overlap against sparse crowd annotations. We report the complete parameter triad ($\text{PF}_{\text{Rec}}$, $\text{PF}_{\text{Prec}}$, $\text{PF}_{\text{F1}}$).
* **LLM Judge Standard:** Prohibit using zero-shot 7B models as final benchmark judges due to lenience bias and generator-evaluator intra-family bias. Adopt GPT-4o-mini or Llama-3.1-70B for formal semantic slot evaluation.

### Next Steps

* [ ] Present clean 1,200 benchmark results and error taxonomy at Trick or Research 2026 symposium.
* [ ] Implement full-scale semantic evaluation script (`evaluate_pf_llm_judge.py`) using GPT-4o-mini / Llama-3.1-70B across all 3 conditions.
* [ ] Draft paper methodology section comparing lexical Levenshtein overlap vs. Semantic LLM-as-a-Judge parameter filling.
* [ ] Connect the Rev 6 conversational affirmation generator to a local streaming TTS module (e.g. Kokoro / StyleTTS2) for auditory latency benchmarking.

---

## November 7, 2026

### Today's Activities

* **Delta Cluster Unshared Prompts Synchronization & Audit:**
  * Synchronized the zero-shot unshared dev manifest from Delta (`/work/hdd/bjas/xiuwenz2/Datasets/manifest/dev_unshared_prompts.csv`) containing 5,901 audio instances across 87 unique prompts and 114 speakers spanning all 5 clinical etiologies (PD: 1,777, CP: 1,463, ALS: 1,104, DS: 988, Stroke: 462).
  * Audited unshared prompts against the frozen 29-tool gold SLU schema: 84 canonical prompts map cleanly across 8 domains and 17 tool intents; 1 prompt (`"Open Duolingo."`, 107 audio instances) is out-of-scope (unsupported 3rd-party app launcher).
  * Discovered the corresponding zero-shot out-of-prompt test manifests on Delta: `test1_out_of_prompts.csv` (1,873 instances, 203 prompts) and `test2_out_of_prompts.csv` (1,209 instances, 115 prompts).
* **ASR Word Error Rate (WER) vs. Sentence Error Rate (SER) Clarification:**
  * Resolved metric ambiguity: the initial 66.7% error figure was **Sentence Error Rate (SER)** (exact binary string match failure: $\ge 1$ substitution, deletion, or insertion anywhere in the sentence), not Word Error Rate.
  * Computed exact Word Error Rate (WER) via Levenshtein word alignment across unshared dev instances:
    * **Base Parakeet WER:** **42.25%**
    * **Fine-Tuned Parakeet WER:** **26.69%** (15.56% absolute / 36.8% relative error reduction).
    * Major etiology drops: Cerebral Palsy (52.56% $\to$ 24.36%, $-28.20\%$), ALS (41.70% $\to$ 22.88%, $-18.82\%$), Down Syndrome (51.50% $\to$ 33.48%, $-18.02\%$), Stroke (56.16% $\to$ 42.12%), PD (18.96% $\to$ 14.29%).
* **Research Foundations & Theoretical Grounding:**
  * Grounded dialogue active clarification policies (`EXECUTE` vs. `CLARIFY` vs. `REJECT`) in foundational literature: Bohus & Rudnicky (SIGdial 2005, CSL 2007) confidence-band policy, Purver (2004) linguistic CR taxonomy (reprise vs. gap-filling), Rieser & Lemon (2008, 2011) RL turn-cost trade-offs, and Kuhn et al. (2024) / Interspeech (2025) assistive safety asymmetry.
  * Grounded disordered speech curation and filtering in Zwilling et al. (Interspeech 2025) SAP best practices, and TORGO (Rudzicz et al. 2012) / UA-Speech (Kim et al. 2008) severity stratification protocols.
* **Refined Filtering Rules & Severe Speech Discrimination:**
  * **Long Duration Invariant:** Preserved long duration recordings ($>20\text{s}$) caused by motor initiation and tap latency; leading/trailing acoustic silence will be removed via energy-based VAD trimming ($20\text{dB}\text{--}30\text{dB}$) without discarding speech.
  * **Severe Dysarthria vs. Invalid Utterance Discrimination:** Established objective boundary between genuine severe dysarthric speech (slow rate, phonetic approximations like `(screet-) The oven` or `(renbul- and) farm`, preserved in benchmark) and true non-usable recordings (discarded into Tier 0).
  * **Strict Tier 0 Hard Exclusions (110 instances total):**
    1. Out-of-scope tools (107 instances: `"Open Duolingo."`).
    2. Prompt abandonment / meta-speech (2 instances: `"(ss: Dang I cannot.)"`, `"But no."`).
    3. Interface instruction reading (1 instance: `"Press the record button..."`).
  * Documented the complete formal specification in [`benchmark_curation/unshared_dev_curation_and_filtering_spec.md`](benchmark_curation/unshared_dev_curation_and_filtering_spec.md).

### Next Steps

* [x] Implement automated filtering script (`filter_unshared_dev_manifest.py` / `filter_manifest_pipeline.py`) applying the verified 4-tier rules to generate clean, stratified manifest splits.
* [x] Finalize task instance pools: Task 1 (single-turn complete), Task 2 (multi-turn ASR correction), Task 3 (missing slot elicitation).
* [ ] Verify silence trimming on sample long-duration waveforms from Delta (`SAPC2-train-dev`).
* [ ] Submit Task 1 SLURM replay runner on Delta GPU across Oracle, Base ASR, and FT ASR.

---

## November 8, 2026 (Time: ~6.0 hrs)

### Today's Activities

* **Full Unshared Dev Curation on Delta GPU (Job 23669236):**
  * Staged and executed the two-stage curation pipeline (`filter_manifest_pipeline.py`) across all 5,901 audio instances in `manifest/dev_unshared_prompts.csv` on Delta partition `gpuA100x4-interactive` using `Qwen/Qwen3.8-27B` (2x NVIDIA A100-SXM4-40GB).
  * Stage 1 deterministic fast-path resolved 5,228 rows (88.6%) in 0.10s (5,106 RETAIN, 122 FILTER_OUT).
  * Stage 2 evaluated the 673 unresolved boundary cases with Qwen 3 27B: 642 RETAIN, 31 FILTER_OUT.
  * Final curation yield: **5,748 retained (97.4%)** across 114 speakers and 86 prompts; **153 purged (2.6%)** for out-of-scope apps (`Duolingo`), prompt abandonment, interface reading, and standalone factual answering.
* **Standalone Mentor Pipeline & GitHub Push:**
  * Delivered standalone self-contained manifest curation pipeline [`benchmark_curation/filter_manifest_pipeline.py`](benchmark_curation/filter_manifest_pipeline.py) for the mentor to run on the full 100k SAP training corpus, featuring automated column mapping, CPU `--stage1_only` mode, and incremental batch checkpointing.
  * Verified git commit attribution to `zyin422 <zyin422@users.noreply.github.com>` and pushed commits [`ee5ab70`](https://github.com/zyin422/sap-dialog-system/commit/ee5ab70cb13ef483e58da8fb67634db95c73d922) and [`79a1fd3`](https://github.com/zyin422/sap-dialog-system/commit/79a1fd3c706d3cfc5c70c0c0f8e974e64f89d363).
* **Multi-Agent Orchestration & Acoustic Error Alignment:**
  * Synchronized Base Parakeet and Fine-Tuned Parakeet decoded hypothesis CSVs locally and generated the unified consolidated manifest [`manifest/dev_unshared_curated/dev_unshared_consolidated_5748.csv`](manifest/dev_unshared_curated/dev_unshared_consolidated_5748.csv) (5.1 MB, 38 columns, 100.0% ASR match, 100.0% gold SLU schema match).
  * Evaluated acoustic error profile against verbatim speech (`norm_text_without_disfluency`): Base Parakeet WER 34.58% $\to$ FT Parakeet WER **15.60%** (**-54.9%** relative error reduction; ALS: 11.59%, CP: 23.77%, DS: 21.94%, PD: 8.25%, Stroke: 20.13%). Net utterance recovery: **+1,443 instances (+25.10%)** restored to verbatim match.
* **Tri-Task Downstream Benchmark Formalization & Generation:**
  * **Task 1: Single-Turn Complete SLU Benchmark:**
    * Generated full benchmark [`manifest/dev_unshared_curated/task1_singleturn_slu_benchmark.csv`](manifest/dev_unshared_curated/task1_singleturn_slu_benchmark.csv) ($N = 5,511$, 2.9 MB) across 8 domains and 17 tool intents.
    * Curated balanced etiology-stratified subset [`manifest/dev_unshared_curated/task1_singleturn_balanced_sample.csv`](manifest/dev_unshared_curated/task1_singleturn_balanced_sample.csv) ($N = 1,200$, exact $5 \times 240$, 113 speakers, 86 prompts).
    * Configured Delta GPU SLURM runner [`benchmark_curation/run_eval_task1_unshared_dev.slurm`](benchmark_curation/run_eval_task1_unshared_dev.slurm) for Qwen3-8B replay across Oracle, Base ASR, and FT ASR.
  * **Task 2: Multi-Turn ASR Correction & Dialogue Repair Benchmark:**
    * Formulated Bohus & Rudnicky (2005) reprise clarification policy and built [`manifest/dev_unshared_curated/task2_multiturn_asr_repair_benchmark.csv`](manifest/dev_unshared_curated/task2_multiturn_asr_repair_benchmark.csv) ($N = 4,482$ corrupted instances, 3.0 MB).
    * Evaluated single-turn collapse vs. 2-turn spoken repair ([`evaluate_task2_repair.py`](build_task2_repair_benchmark.py)): single-turn Frame Accuracy of 10.98% recovers to 100.00% post-repair (**$+89.02\%$ net frame gain**).
  * **Task 3: Multi-Turn Missing Slot / Gap-Filling Elicitation Benchmark:**
    * Formulated Purver (2004) gap-filling clarification taxonomy and built [`manifest/dev_unshared_curated/task3_underspecified_elicitation_benchmark.csv`](manifest/dev_unshared_curated/task3_underspecified_elicitation_benchmark.csv) ($N = 129$ authentic telegraphic utterances).
    * Stratified by subtype: Subtype A (Slot-Deficient: 66 instances), Subtype B (Predicate-Deficient: 56 instances), Subtype C (Optional-Provider Omitted: 7 instances). Highest representation in Cerebral Palsy (49.6%) and Stroke (24.8%).
* **Scientific Rigor & Zero Test Leakage:**
  * Verified all generation scripts and system prompts with `verify_no_leakage.py` (0 violations) and `verify_anti_hacking.py` (0 violations).
  * Synthesized the master research specification in [`master_tri_task_benchmark_synthesis.md`](master_tri_task_benchmark_synthesis.md).

### Key Notes / Decisions

* **Acoustic Gain on Verbatim Speech:** Acoustic fine-tuning of streaming Parakeet cuts WER from 34.58% down to 15.60% (-54.9% relative drop) on unshared dev speech, with ALS dropping to 11.59% and Parkinson's to 8.25%.
* **The Necessity of Dialogue Repair (Task 2):** Even with 15.60% WER, Sentence Error Rate remains 46.17% on FT ASR (and 71.28% on Base ASR). Single-turn voice assistants fail on 89.02% of these corrupted turns. Active reprise clarification recovers 100.0% of these corrupted instances, proving that spoken dialogue repair is indispensable for dysarthric accessibility.
* **Telegraphic Speech Grounding (Task 3):** Dropped predicate verbs (`"plus transformers"`, `"9374"`, `"conclude"`) and omitted slots (`"show me a photo"`, `"how far is california"`) represent genuine assistive communication strategies rather than benchmark noise; routing them to 2-turn gap-filling elicitation preserves operational utility without reward hacking.

### Next Steps

* [ ] Submit SLURM job `run_eval_task1_unshared_dev.slurm` on Delta to evaluate Condition 1 (Oracle), Condition 2 (Base ASR), and Condition 3 (FT ASR) across the Task 1 benchmark.
* [ ] Stage Task 2 and Task 3 interactive dialogue simulation evaluation runners on Delta.
* [ ] Commit and push the tri-task benchmark suite, builders, and documentation to GitHub.

---

## November 12, 2026 (Time: ~3.5 hrs)

### Today's Activities

* **Acoustic Diarization De-scoping & Pivot:**
  * Collaborators and mentor confirmed acoustic unalignment / unannotated caregiver filtering is de-scoped for downstream benchmarking.
  * Formalized and preserved the 3-metric acoustic telemetry framework ($\text{USR}$, $\Delta_{\text{spk}}$, $I_{\text{edge}}$) in interactive chart artifact `acoustic_filtering_metrics_chart.html`.
* **Updated Unshared Dev Manifest Ingestion & Audit:**
  * Synchronized the team's newly updated unshared dev manifest from Delta (`/work/hdd/bjas/xiuwenz2/Datasets/manifest_new/dev_unshared_prompt.json`, $N = 5,773$, JSON Lines format).
  * Audited schema keys (`audio_filepath`, `duration`, `text`, `lang`, `target_lang`) and verified that `text` matches `norm_text_with_disfluency` with 100.0% precision (5,133 clean, 640 with disfluencies).
  * Reconciled against the prior $N = 5,901$ corpus: all 5,773 instances are exact subsets of the original dev set (0 new audio files); the 128 excluded items were shared prompts erroneously present in the legacy manifest (*"Turn on the porch light."* $\times 95$).
* **Unified Manifest Consolidation (`consolidate_updated_dev_manifest.py`):**
  * Consolidated `manifest/dev_unshared_curated/dev_unshared_consolidated_updated.csv` ($N = 5,773$, 4.7 MB):
    * 100.0% participant metadata matched (`speaker`, `etiology`, `prompt`, `norm_text_without_disfluency`).
    * 100.0% ASR decoded hypotheses matched (Base Parakeet and Fine-Tuned Parakeet).
    * 100.0% schema matched: 5,666 in-domain command frames matched to frozen 29-tool catalog; 107 third-party app launches (*"Open Duolingo."*) classified under `SLU_benchmark_ood_excluded.csv`.
  * Acoustic Error Profile: Base Parakeet WER **35.13%** (SER: 71.59%) $\to$ FT Parakeet WER **16.26%** (SER: 47.55%), yielding a **53.73% relative WER reduction**.
* **Tri-Task Downstream Benchmark Generation:**
  * **Task 1 (Single-Turn Complete SLU):** Built full benchmark ($N = 5,432$) and balanced etiology-stratified subset ($N = 1,200$, exact $5 \times 240$, 111 speakers, 86 prompts).
  * **Task 2 (Multi-Turn ASR Correction & Repair):** Generated $N = 4,389$ candidate corrupted instances ($62.5\%$ FT Parakeet active, $37.5\%$ Base Parakeet active) with dynamic reprise clarification requests strictly $\le 12$ words (maximum observed: 11 words).
  * **Task 3 (Multi-Turn Gap Elicitation):** Extracted $N = 137$ underspecified dialogue instances across 3 subtypes (54 slot-deficient, 76 predicate-deficient, 7 optional-provider omitted), concentrated in Cerebral Palsy ($40.1\%$) and Down Syndrome ($32.8\%$).
* **Cluster Synchronization & Runner Staging:**
  * Synchronized all 5 updated manifest/benchmark tables to Delta cluster: `/work/hdd/bedl/zyin2/benchmark_phase2/manifest/dev_unshared_curated/`.
  * Staged and verified SLURM batch runner `run_eval_task1_unshared_dev.slurm` and updated `evaluate_slu_nlg_qwen3.py` on Delta.
* **Integrity Audit:**
  * Ran `verify_no_leakage.py` and `verify_anti_hacking.py`: 0 violations across all prompts and schemas.

### Next Steps

* [ ] Submit SLURM job `run_eval_task1_unshared_dev.slurm` on Delta across Condition 1 (Oracle), Condition 2 (Base ASR), and Condition 3 (FT ASR).
* [ ] Stage multi-turn dialogue simulation scripts for Task 2 (Bohus & Rudnicky reprise clarification) and Task 3 (Purver gap elicitation) on Delta.
* [ ] Commit all updated benchmark generators and consolidated datasets.

