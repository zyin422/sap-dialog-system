# SAP Spoken Dialog System (Offline Pipeline)

An offline Speech-to-Text and Intent/Slot Extraction pipeline designed to evaluate spoken dialog systems and analyze the impact of ASR errors on downstream LLM task performance (such as for speakers with dysarthria).

## Architecture

The pipeline follows a modular, pluggable architecture:

```
Audio Files (.mp3 / .wav)
          │
          ▼
┌─────────────────────────────────┐
│       VoxtralRealtimeASR        │  (Speech-to-Text)
│ mistralai/Voxtral-Mini-4B-RT    │
└─────────────────────────────────┘
          │
          ▼  Transcripts
┌─────────────────────────────────┐
│            QwenLLM              │  (Intent & Slot Extraction, Conversational Reply)
│    Qwen/Qwen2.5-7B-Instruct     │
└─────────────────────────────────┘
          │
          ▼
     results.json
```

## Features

- **Modular Strategy Pattern**: Easily swap ASR (`BaseASR`) and LLM (`BaseLLM`) backends without altering pipeline orchestration.
- **Batch Processing**: Processes individual files or entire directories of audio recordings.
- **Structured Extraction**: Extracts task `intent`, entity `slots`, and conversational `response` formatted as JSON.
- **Evaluation Ready**: Outputs structured records for comparing ASR Word Error Rate (WER) against downstream intent/slot accuracy.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Pipeline

Place your audio files in the `audio/` directory and run:

```bash
python s2t_pipeline.py
```

The pipeline will transcribe each recording, feed the transcript to Qwen for intent/slot extraction, and export the structured log to `results.json`.

---

## SLU Schema Freeze & Pilot Annotation (Step 3)

The repository hosts the authoritative schema freeze assets and pilot evaluation suite under [`schema_freeze/`](schema_freeze/README.md).

### Quick Links
* **Interactive Annotation Webapp:** [`schema_freeze/pilot/slu_annotator.html`](schema_freeze/pilot/slu_annotator.html)
* **Annotator Guidelines:** [`schema_freeze/SLU_annotator_guidelines.md`](schema_freeze/SLU_annotator_guidelines.md)
* **Canonical Tool Catalog:** [`schema_freeze/canonical_tool_catalog.md`](schema_freeze/canonical_tool_catalog.md)
* **Dual-Annotator Handoff Brief:** [`schema_freeze/HANDOFF.md`](schema_freeze/HANDOFF.md)

### Instructions for Human Annotators
1. **Open the Webapp:**
   * Double-click `schema_freeze/pilot/slu_annotator.html` in Chrome, Safari, Edge, or Firefox. No installation or local server required.
2. **Select Identity:**
   * In the top-right header, select your annotator profile (**Annotator 1** or **Annotator 2**).
3. **Label the 50 Commands:**
   * Follow the 3-step decision flow:
     1. **Domain:** Choose 1 of 10 functional domains.
     2. **Intent:** Select the canonical tool/intent.
     3. **Slots:** Click categorical enum pills or highlight transcript text and click *"Paste Selection"* to extract verbatim spans (BaseNP prepositions/articles are automatically stripped).
   * Press `Ctrl+Enter` (or click *Save & Next*) to advance.
4. **Export CSV:**
   * Upon labeling all 50 commands, click **Download CSV** to generate `SLU_pilot_50_annotator1.csv` or `SLU_pilot_50_annotator2.csv`.
   * Submit the CSV for inter-annotator agreement computation ($\kappa$ / slot F1) and adjudication review.
