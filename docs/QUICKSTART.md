# Quick Start

## Three Basic Commands

```bash
# Offline inference
python scripts/s2t_pipeline.py

# Streaming inference (recommended)
python scripts/s2t_pipeline.py --streaming

# Custom delay
python scripts/s2t_pipeline.py --streaming --delay=480
```

## Parameters

| Parameter | Description | Range |
|-----------|-------------|-------|
| `--streaming` | Enable streaming mode | - |
| `--delay=X` | Delay in milliseconds | 0-2000 |

## Delay Selection Guide

| Use Case | Recommended | Notes |
|----------|-------------|-------|
| Dialog system | 0-200ms | Feels real-time |
| Default (recommended) | 480ms | Balance between latency and accuracy |
| Accuracy-first | 800-1000ms | Best accuracy |

## View Results

```bash
# Pretty print
cat results.json | python -m json.tool

# Show transcripts only
python -c "
import json
with open('results.json') as f:
    for r in json.load(f):
        print(f'{r[\"audio_file\"]}: {r[\"asr_transcript\"]}')"
```

## File Locations

- Audio input: `audio/` directory
- Output results: `results.json`
- Scripts: `scripts/s2t_pipeline.py`
- Logs: `logs/` directory

## FAQ

**Q: Why is it slow?**  
A: First run downloads models (~3GB). Subsequent runs are much faster.

**Q: Does it use GPU?**  
A: Auto-selected. Uses CUDA if available, otherwise CPU (slower).

**Q: Do I need to reload models when changing parameters?**  
A: No. Delay parameter is applied at inference time.

**Q: Which is faster, streaming or offline?**  
A: Streaming is faster and more memory-efficient. Use streaming.

More docs:
- `RUN_GUIDE.md` - Detailed guide
- `STREAMING_WORKFLOW.md` - How streaming works
- `CHANGES_SUMMARY.md` - What changed
