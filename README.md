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
│ mistralai/Voxtral-Mini-4B-RT   │
└─────────────────────────────────┘
          │
          ▼  Transcripts
┌─────────────────────────────────┐
│            QwenLLM              │  (Intent & Slot Extraction)
│    Qwen/Qwen2.5-1.5B-Instruct   │
└─────────────────────────────────┘
          │
          ▼
     results.json (Structured Logs)
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
