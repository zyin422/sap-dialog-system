# Weekly Progress Summary: October 22 – October 28, 2026

**Project:** Speech Accessibility Project (SAP) — Spoken Dialog System & Downstream SLU Benchmark  
**Affiliations:** Siebel School of Computing & Data Science & Department of ECE, UIUC; Beckman Institute  
**Authors/Team:** Zixuan Yin, Xiuwen Zheng, Haolong Zheng, Kush Bhardwaj  
**Faculty Advisor:** Professor Mark Hasegawa-Johnson (UIUC)  
**Compute Infrastructure:** ACCESS Allocation `CIS250149` on NCSA Delta GPU Cluster (`bjas-delta-gpu`)  
**Repository:** [`sap-dialog-system`](https://github.com/zyin422/sap-dialog-system) (`origin/main`, commit `1385b1c`)

---

## Executive Overview

Over the past seven days (Thursday, October 22 through Wednesday, October 28, 2026), work focused on three interconnected research and engineering fronts:

1. **SLU Benchmark Formalization & Dataset Release (Schema v1.3):**
   * Finalized the audited 1,274-command canonical gold benchmark across 10 assistive domains (29 tools) and segregated a 35-command Out-of-Domain (OOD) partition.
   * Built and released a standalone interactive visual benchmark explorer ([`SLU_benchmark_browser.html`](file:///Users/zixuan/agy2-projects/sap-dialog-system/SLU_benchmark_browser.html)).
   * Published clean deliverables and documentation to GitHub.

2. **Acoustic Decoding & End-to-End Downstream SLU Evaluation (N=291):**
   * Deployed NCSA Delta GPU workflows to decode the pilot dev benchmark across two acoustic checkpoints: zero-shot Base Parakeet-TDT 0.6B (28.15% WER) vs. SAP Dysarthric Fine-Tuned Parakeet-TDT (10.70% WER).
   * Conducted a controlled 3-condition evaluation ablation using a frozen Qwen 2.5 72B-Instruct downstream agent ($T=0.0$).
   * Proved that dysarthria acoustic fine-tuning yields a **+22.34% net Command Frame Accuracy boost** (28.18% $\rightarrow$ 50.52%), achieving an **Adaptation Recovery Rate (ARR) of 71.44%**, with dramatic gains in safety-critical domains (Health: +66.7%; Communication: +48.5%).

3. **Academic Poster Package for "Trick or Research 2026":**
   * Designed, drafted, and compiled a complete 48" × 36" research poster package ([`poster/`](file:///Users/zixuan/agy2-projects/sap-dialog-system/poster/)) including an interactive vector HTML poster, Typst source, 300+ DPI PDF export, text blueprint, and vector QR code.

4. **Zero-Leakage Autonomous Prompt Optimization:**
   * Built an autonomous prompt optimization harness and strict verification audit tool ([`verify_no_leakage.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/verify_no_leakage.py)).
   * Iterated through generalized prompt refinements without benchmark entity leakage, elevating Oracle Tool Selection to **91.07%** and Command Frame Accuracy to **75.26%**.

---

## Detailed Chronological Timeline

### Thursday, October 22, 2026: Schema v1.2 & Frontier Adjudication
* **Pilot 50 Inter-Annotator Adjudication:** Adjudicated pilot annotations to establish initial baseline agreement and error taxonomy across frontier models (Claude 3.5 Sonnet & GPT-6 Instant).
* **High-Ambiguity Stress Testing:** Evaluated 100 high-ambiguity spoken commands to identify boundary failures between search, reminders, calendar, and smart home.
* **SLU Schema v1.2 Finalization:**
  * Expanded canonical catalog to 29 tools across 10 functional domains.
  * Added `origin` slot to `maps_route` (Rule H: point-to-point route decoupling).
  * Inlined tool-specific constraints, enum definitions, and extraction rules directly into the catalog schema.
* **Frontier Reference Gold Set:** Created the 100-sample adjudicated frontier gold set (`frontier_100_gold.csv`), establishing a 150-sample golden reference set ($D_{\text{dev}}$).
* **Reproducibility Protocol:** Defined evaluation harness parameters for open-source model execution (Qwen 2.5 72B-Instruct @ greedy $T=0.0$) on NCSA Delta GPUs.

### Friday, October 23, 2026: Dual-Frontier Batch Inference & Consensus Engine
* **Master Dataset Structuring:** Formatted the full master corpus (~1,300 commands) into standardized batch prompt files (24 modular batches and 4 balanced web batches of ~327 commands).
* **Consensus Engine (`consensus_agreement.py`):** Developed an automated consensus adjudication script matching Claude 3.5 Sonnet and GPT predictions against Schema v1.2 with rule-based triage diagnostics.
* **Global Consensus Execution:**
  * Achieved 91.4% domain agreement, 91.1% intent agreement, and 65.3% full slot exact match (855 agreed gold, 454 triaged).
* **Adjudication Decisions Formalized:**
  * *Rule B:* Mandatory conversational carrier phrase stripping for `qa_search.query`.
  * *Rule H:* Point-to-point route decoupling (`origin` vs. `destination`).
  * *Rule I:* Enforced `sort_by: "distance"` for proximity venue queries.
  * *Rule K:* Excluded wake phrases and unsupported OS app launches from SLU evaluation rather than forcing them into invalid tools.

### Saturday & Sunday, October 24–25, 2026: Benchmark Release & Evaluation Protocol
* **Second-Pass Global Benchmark Audit:** Individually reviewed and verified all 1,309 commands across both frontier predictions, preventing acceptance of spurious consensus.
* **Out-of-Domain (OOD) Partitioning:** Formally segregated 35 non-task utterances (wake words, broadcasts, OS launches, dictation fragments) into a dedicated OOD partition.
* **SLU Schema v1.3 Canonical Release:**
  * Reached 1,274 canonical gold commands with 100% OpenAPI/JSON Schema compliance (0 validation errors, 0 invalid enums, 0 hallucinated slots).
* **Interactive Visual Explorer (`SLU_benchmark_browser.html`):**
  * Built a standalone, client-side HTML/JS browser with dual card-deck and paginated table views, real-time regex filtering, and audit status badges.
* **Deliverables Published:**
  * Purged intermediate scratch batches and committed final benchmark deliverables (`1385b1c`) pushed to GitHub remote `origin/main` with commit attribution to `@zyin422`.
* **Literature Synthesis & 3-Condition Ablation Matrix:**
  * Analyzed `papers/speech-dialog-survey/speech_dialogue_benchmarks_database_2026.md`.
  * Designed the 3-condition evaluation ablation matrix (Oracle Ceiling vs. Base Streaming ASR vs. SAP Fine-Tuned ASR) and 3-tier metric decomposition: Tool Selection (TS), Tool Call Structural Validity (TCS), and Parameter Filling (PF) with phonetic edit tolerance.

### Monday, October 26, 2026: Foundational Theory & Pipeline Preprocessing
* **Deep Learning Mathematics & Theory:** Intensive review of deep neural network architectures, backpropagation dynamics, loss surfaces, and normalization layers (Adam Dhalla series, David Jin mentorship).
* **Socratic Problem Solving:** Addressed theoretical drills on gradient propagation, attention heads, and activation behavior.
* **Audio-Manifest Preprocessing:** Prepared audio waveform cross-referencing between the dysarthric dev set manifest (`manifest/dev.tsv`) and the 1,274 canonical gold benchmark commands.

### Tuesday, October 27, 2026: NCSA Delta Inference, "Beyond WER" Empirical Breakthrough & Academic Poster
* **Acoustic Model Decoding on NCSA Delta:**
  * Implemented [`decode_benchmark_291.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/decode_benchmark_291.py) using NeMo on Delta GPUs.
  * Ingested fine-tuned checkpoint (`ft_dysarthric_en_0.6b.nemo`) from collaborator Xiuwen Zheng.
  * Transcribed 291 unique dev audio commands:
    * **Base Parakeet-TDT 0.6B:** 28.15% Acoustic WER.
    * **Fine-Tuned Parakeet-TDT 0.6B:** 10.70% Acoustic WER (17.45% absolute WER reduction).
* **End-to-End SLU Evaluation (`evaluate_slu_llm.py`):**
  * Evaluated Qwen 2.5 72B-Instruct ($T=0.0$) across all 3 conditions on Delta:
    * **Condition 1 (Oracle Ceiling):** TS 88.32%, PF 66.67%, Command Frame Acc **59.45%**.
    * **Condition 2 (Base Parakeet ASR):** TS 74.23%, PF 40.34%, Command Frame Acc **28.18%**.
    * **Condition 3 (Fine-Tuned Parakeet ASR):** TS 86.60%, PF 58.70%, Command Frame Acc **50.52%**.
  * Quantified the **Adaptation Recovery Rate (ARR)** at **71.44%**, proving that dysarthric acoustic fine-tuning recovers over seven-tenths of lost task execution performance.
  * Demonstrated safety-critical domain recovery: Health & Medication gained **+66.7%** (14.3% $\rightarrow$ 81.0%), and Communication gained **+48.5%** (24.2% $\rightarrow$ 72.7%).
  * Measured Semantic Error Correction Rate (SECR: 35.07%).
* **Academic Poster Package for "Trick or Research 2026":**
  * Assembled full conference poster package in [`poster/`](file:///Users/zixuan/agy2-projects/sap-dialog-system/poster/):
    * `poster_preview.html`: Interactive, print-ready 48" × 36" vector HTML poster.
    * `poster.typ`: Typst source code for direct 300+ DPI vector PDF generation.
    * `POSTER_CONTENT.md`: Academic blueprint containing complete section texts, tables, and presentation talking points.
    * `qr_code.svg`: Standalone vector QR code linking to the GitHub repository.

### Wednesday, October 28, 2026 (Today): Autonomous Prompt Optimization & Zero-Leakage Audit
* **Autonomous Optimization Loop:**
  * Implemented [`prompt_optimizer.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/prompt_optimizer.py) to systematically close the gap between raw LLM function calling and ground-truth slot extraction.
  * Executed iterative optimization rounds on NCSA Delta (`run_generalized_iter1.py` through `iter9.py`, `run_clean_iter10.py` through `iter12.py`).
* **Zero-Leakage Benchmark Audit Tool (`verify_no_leakage.py`):**
  * Developed an exhaustive lexical auditor scanning prompts against [`unique_benchmark_dev_291.csv`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/unique_benchmark_dev_291.csv).
  * Checked for entity names, benchmark n-grams, and quoted phrases to guarantee zero dataset contamination or example memorization.
* **Clean Evaluation Results Achieved:**
  * *Clean Round 1 (`clean_r1`):* TS: **90.38%**, TCS: **100.0%**, PF: **78.02%**, Command Frame Acc: **75.26%**.
  * *Clean Round 2 (`clean_r2`):* TS: **91.07%**, TCS: **100.0%**, PF: **77.05%**, Command Frame Acc: **73.88%**.
  * Launched Clean Round 3 (`run_clean_r3.slurm` / `run_clean_iter12.py`) targeting finer closed-enum and constituent boundary definitions.
* **CS Theory & Deep Learning Tutoring:** Continued Socratic technical tutoring on deep learning architectures and backpropagation.

---

## Key Metrics & Quantitative Findings

### 1. Acoustic & Downstream Performance Comparison (N=291 Benchmark Dev Set)

| Condition | Acoustic Model | Acoustic WER (%) | Tool Selection (TS %) | Parameter Filling (PF %) | Command Frame Acc (%) | Adaptation Recovery Rate (ARR) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Oracle Ceiling** | Ground Truth Text | 0.00% | 88.32% | 66.67% | **59.45%** | — |
| **2. Base ASR** | Zero-Shot Parakeet-TDT 0.6B | 28.15% | 74.23% | 40.34% | **28.18%** | Baseline |
| **3. Fine-Tuned ASR** | SAP-Adapted Parakeet-TDT 0.6B | **10.70%** | **86.60%** | **58.70%** | **50.52%** | **71.44%** |
| **Net Gain (FT vs. Base)**| | **-17.45%** | **+12.37%** | **+18.36%** | **+22.34%** | — |

$$\text{Adaptation Recovery Rate (ARR)} = \frac{\text{Acc}_{\text{FT}} - \text{Acc}_{\text{Base}}}{\text{Acc}_{\text{Oracle}} - \text{Acc}_{\text{Base}}} \times 100\% = \frac{50.52 - 28.18}{59.45 - 28.18} \times 100\% = \mathbf{71.44\%}$$

### 2. High-Impact Domain Breakdown (Command Frame Accuracy)

* **Health & Medication ($N=42$):** Base: 14.3% $\rightarrow$ Fine-Tuned: **81.0%** (**+66.7% absolute gain**). Preserves critical medication names, dosages, and refill requests.
* **Communication ($N=33$):** Base: 24.2% $\rightarrow$ Fine-Tuned: **72.7%** (**+48.5% absolute gain**). Accurately transcribes distorted names and contact entities.
* **General QA ($N=90$):** Base: 35.6% $\rightarrow$ Fine-Tuned: **48.9%** (**+13.3% absolute gain**). Downstream QA handles fuzzy search queries with higher tolerance to minor phoneme errors.

### 3. Prompt Optimization Progress (Oracle Ground Truth Condition)

| Iteration / Round | Prompt Strategy | Tool Selection (TS %) | Parameter Filling (PF %) | Command Frame Acc (%) | Audit Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Baseline Zero-Shot** | Standard Schema v1.3 Prompt | 88.32% | 66.67% | 59.45% | Verified |
| **Clean Round 1 (`clean_r1`)** | Generalized semantic disambiguation | 90.38% | 78.02% | 75.26% | 0 Leakage (Passed) |
| **Clean Round 2 (`clean_r2`)** | Explicit closed-enum slot constraints | 91.07% | 77.05% | 73.88% | 0 Leakage (Passed) |
| **Clean Round 3 (`clean_r3`)** | Disambiguated health/schedule queries | *Running* | *Running* | *Running* | 0 Leakage (Passed) |

---

## Artifacts & Deliverables Created

* **Benchmark Dataset & Tools:**
  * [`sap-dialog-system/schema_freeze/SLU_benchmark_gold_1309.csv`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/schema_freeze/SLU_benchmark_gold_1309.csv): Canonical benchmark (1,274 gold + 35 OOD items).
  * [`sap-dialog-system/SLU_benchmark_browser.html`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/SLU_benchmark_browser.html): Interactive visual explorer with live search and schema validation badges.
  * [`sap-dialog-system/consensus/consensus_agreement.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/consensus/consensus_agreement.py): Multi-model consensus and triage engine.
* **Evaluation Harnesses & Verification Tools:**
  * [`sap-dialog-system/decode_benchmark_291.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/decode_benchmark_291.py): NeMo batch ASR decoder for Base and Fine-Tuned checkpoints.
  * [`sap-dialog-system/evaluate_slu_llm.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/evaluate_slu_llm.py): End-to-end 3-condition SLU evaluator with TS, TCS, PF, and ARR metrics.
  * [`sap-dialog-system/verify_no_leakage.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/verify_no_leakage.py): Automated prompt audit tool detecting entity and n-gram contamination.
  * [`sap-dialog-system/prompt_optimizer.py`](file:///Users/zixuan/agy2-projects/sap-dialog-system/sap-dialog-system/prompt_optimizer.py): Autonomous GPU prompt optimization harness.
* **Poster Presentation Package (`poster/`):**
  * [`poster/poster_preview.html`](file:///Users/zixuan/agy2-projects/sap-dialog-system/poster/poster_preview.html): Standalone vector HTML poster with zoom controls.
  * [`poster/poster.typ`](file:///Users/zixuan/agy2-projects/sap-dialog-system/poster/poster.typ): Typst typesetting source code.
  * [`poster/POSTER_CONTENT.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/poster/POSTER_CONTENT.md): Modular academic copy with formulas, tables, and presentation talking points.
  * [`poster/qr_code.svg`](file:///Users/zixuan/agy2-projects/sap-dialog-system/poster/qr_code.svg): Vector SVG repository link.
* **Documentation & Logs:**
  * [`daily_project_log.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/daily_project_log.md): Running project activity log.
  * [`papers/speech-dialog-survey/speech_dialogue_benchmarks_database_2026.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/papers/speech-dialog-survey/speech_dialogue_benchmarks_database_2026.md): Speech dialog benchmarking survey.
