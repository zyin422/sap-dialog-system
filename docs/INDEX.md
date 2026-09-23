# Documentation Index

Quick reference to all project documents.

## 🚀 Getting Started

**New to the project?** Start here:

1. Read `../README.md` (main overview)
2. Run: `python scripts/s2t_pipeline.py --streaming`
3. Check `QUICKSTART.md` for next steps

## 📚 Documents

| Document | Purpose | Length |
|----------|---------|--------|
| **QUICKSTART.md** | Quick start guide | 1 min |
| **RUN_GUIDE.md** | Detailed running guide & troubleshooting | 5 min |
| **STREAMING_WORKFLOW.md** | How streaming inference works | 10 min |
| **CHANGES_SUMMARY.md** | Recent code changes | 5 min |

## 🎯 Common Tasks

### Run inference
```bash
python scripts/s2t_pipeline.py --streaming
```

### View results
```bash
cat results.json | python -m json.tool
```

### Submit to HPC
```bash
sbatch scripts/run_pipeline.slurm
```

### Quick test
```bash
bash scripts/quick_test.sh streaming 480
```

## 📁 Project Structure

```
.
├── README.md              ← Main documentation
├── requirements.txt       ← Dependencies
├── audio/                 ← Input audio files
├── results.json           ← Output results
├── scripts/               ← Scripts
│   ├── s2t_pipeline.py    ← Core inference script
│   ├── quick_test.sh      ← Quick test
│   └── run_pipeline.slurm ← HPC submission
├── logs/                  ← Historical logs
└── docs/                  ← This directory
    ├── INDEX.md           ← This file
    ├── QUICKSTART.md      ← Quick start
    ├── RUN_GUIDE.md       ← Running guide
    ├── STREAMING_WORKFLOW.md ← Technical details
    └── CHANGES_SUMMARY.md ← What changed
```

## ⚙️ Key Parameters

| Parameter | Purpose | Examples |
|-----------|---------|----------|
| `--streaming` | Enable streaming mode | - |
| `--delay=X` | Latency (ms) | 0, 480, 1000 |

## 🔗 Quick Links

- **Main README:** `../README.md`
- **Quick Start:** `QUICKSTART.md`
- **Detailed Guide:** `RUN_GUIDE.md`
- **Core Script:** `../scripts/s2t_pipeline.py`

## 📝 Notes

- All code and docs are in English
- Project uses streaming inference for efficiency
- Supports both offline and streaming modes
- Output format is JSON

---

**Last updated:** September 2026
