# Running Guide

## Setup

```bash
pip install -r requirements.txt
```

## Basic Usage

```bash
# Offline inference
python scripts/s2t_pipeline.py

# Streaming inference (recommended)
python scripts/s2t_pipeline.py --streaming

# With custom delay
python scripts/s2t_pipeline.py --streaming --delay=480
```

## Delay Parameter Selection

| Use Case | Delay | Notes |
|----------|-------|-------|
| Real-time conversation | 0-200ms | Feels responsive |
| General purpose | 480ms | Default, balanced |
| Accuracy critical | 800-1000ms | Higher accuracy |

## View Results

```bash
# Pretty-print results
cat results.json | python -m json.tool

# Show only transcripts
python -c "
import json
with open('results.json') as f:
    for r in json.load(f):
        print(f'{r[\"audio_file\"]}: {r[\"asr_transcript\"]}')"
```

## Performance

| Operation | Time |
|-----------|------|
| Load models (first run) | ~30s |
| Load models (subsequent) | ~5s |
| Process 1 audio file (5s) | ~3-5s |
| Process 5 audio files | ~1-2 min |

## Troubleshooting

### Slow Performance
- First run downloads models (~3GB)
- Subsequent runs are much faster
- Consider using GPU if available

### Out of Memory
- Streaming mode uses less memory than offline
- Use `--streaming` for large files
- CPU mode will be slower but uses less memory

### Audio Quality Issues
- Ensure audio is clear and 16kHz or higher
- Remove background noise
- Test different delay values (0, 480, 1000)

### Wrong Transcription
- Audio quality affects ASR accuracy
- Try adjusting delay parameter
- Check if audio is in supported format (.mp3, .wav)

## HPC Submission

```bash
sbatch scripts/run_pipeline.slurm
```

Edit the SLURM script to customize:
- GPU allocation
- Time limits
- Job output directory

## File Structure

```
audio/              Input audio files
results.json        Output results
logs/              Historical logs
scripts/           Scripts directory
docs/              Documentation
```

## Output Format

```json
{
  "audio_file": "path/to/audio.mp3",
  "asr_transcript": "transcribed text",
  "llm_output": {
    "intent": "task_name",
    "slots": {"key": "value"},
    "response": "assistant response"
  }
}
```
