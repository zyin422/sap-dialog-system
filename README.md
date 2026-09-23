# SAP Spoken Dialog System

Offline speech-to-text and intent/slot extraction pipeline. Supports both offline and streaming inference modes.

## 🚀 Quick Start

```bash
# Offline inference (simple)
python scripts/s2t_pipeline.py

# Streaming inference (recommended - faster & more memory efficient)
python scripts/s2t_pipeline.py --streaming

# Custom delay parameter (milliseconds)
python scripts/s2t_pipeline.py --streaming --delay=480
```

## 📁 Project Structure

```
sap-dialog-system/
├── README.md                 # Main documentation
├── requirements.txt          # Dependencies
├── audio/                    # Input audio files (.mp3 or .wav)
├── results.json              # Output results
│
├── scripts/                  # Scripts
│   ├── s2t_pipeline.py       # Main inference script
│   ├── run_pipeline.slurm    # HPC submission script
│   └── quick_test.sh         # Quick test script
│
├── logs/                     # Log files
│   └── s2t-eval_*.out/txt
│
└── docs/                     # Documentation
    ├── QUICKSTART.md         # Quick start guide (3 min)
    ├── RUN_GUIDE.md          # Detailed guide
    ├── STREAMING_WORKFLOW.md # Streaming inference explanation
    └── CHANGES_SUMMARY.md    # Recent changes
```

## 🎯 Three Usage Modes

| Mode | Command | Features | Latency |
|------|---------|----------|---------|
| Offline | `python scripts/s2t_pipeline.py` | Simple & direct | High |
| Streaming (recommended) | `python scripts/s2t_pipeline.py --streaming` | Real-time output | Low ⚡ |
| Custom delay | `python scripts/s2t_pipeline.py --streaming --delay=X` | Adjustable latency | Configurable |

## 📝 Core Features

### ASR (Speech-to-Text)
- Model: `Voxtral-Mini-4B-Realtime-2602`
- Streaming & offline inference modes
- Adjustable delay parameter (0-2000ms)

### LLM (Intent & Slot Extraction)
- Model: `Qwen2.5-7B-Instruct`
- Output: JSON format with intent, slots, response

## 📊 Output Format

```json
[
  {
    "audio_file": "audio/example.mp3",
    "asr_transcript": "transcribed text",
    "llm_output": {
      "intent": "task intent",
      "slots": {"key": "value"},
      "response": "natural language response"
    }
  }
]
```

## 📚 Documentation

| Document | Content |
|----------|---------|
| `docs/QUICKSTART.md` | ⭐ Quick start (3 min) |
| `docs/RUN_GUIDE.md` | Detailed guide & troubleshooting |
| `docs/STREAMING_WORKFLOW.md` | Streaming inference explanation |
| `docs/CHANGES_SUMMARY.md` | Recent changes |

## 🔧 Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run inference
python scripts/s2t_pipeline.py --streaming --delay=480

# View results
cat results.json | python -m json.tool

# Quick test
bash scripts/quick_test.sh streaming 480

# Submit to HPC
sbatch scripts/run_pipeline.slurm
```

## ⏱️ Performance Estimate

- Model loading: ~30s (first time) / ~5s (subsequent)
- Process one 5s audio: ~3-5s
- Process 5 audio files: ~1-2 min

## 💾 Requirements

- Python 3.8+
- PyTorch >= 2.4.0
- Transformers >= 4.14.0
- See `requirements.txt` for details

## 📞 FAQ

**Q: Offline or streaming?**  
A: Use streaming (`--streaming`). It's faster, more memory-efficient, and shows intermediate results.

**Q: Which delay to use?**  
A: Default `--delay=480` is best. Special cases:
- Dialog system: 0-200ms (feels real-time)
- Default: 480ms (recommended)
- Accuracy-first: 800-1000ms

**Q: More questions?**  
A: Check `docs/RUN_GUIDE.md` for FAQ section.

---

**Get started:** `python scripts/s2t_pipeline.py --streaming`
