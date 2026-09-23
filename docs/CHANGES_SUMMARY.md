# Changes Summary

## New Features

### 1. Streaming Inference Mode
Added `--streaming` parameter for streaming inference:
```bash
python scripts/s2t_pipeline.py --streaming
```

**Benefits:**
- Chunk-based audio processing
- Real-time output
- Low latency (milliseconds)
- Memory efficient

### 2. Adjustable Delay Parameter
Added `--delay=X` to control inference latency:
```bash
python scripts/s2t_pipeline.py --streaming --delay=480
```

**Range:** 0-2000ms

**Common values:**
- `--delay=0`: Ultra-low latency ⚡
- `--delay=480`: Balanced (recommended) ✅
- `--delay=1000`: Best accuracy 🎯

## Code Changes

### File: `scripts/s2t_pipeline.py`

**Added parameters to VoxtralRealtimeASR:**
```python
def __init__(
    self,
    streaming: bool = False,
    transcription_delay_ms: int = 480
)
```

**New methods:**
- `_sync_delay_to_processor()`: Sync delay to processor
- `_transcribe_streaming()`: Streaming inference implementation
- `_transcribe_offline()`: Original offline inference

**Main program updates:**
- Parse `--streaming` flag
- Parse `--delay=X` parameter
- Pass parameters to ASR model

## Directory Reorganization

```
scripts/       → s2t_pipeline.py, run_pipeline.slurm, quick_test.sh
docs/          → All documentation
logs/          → Historical cascade logs
audio/         → Input audio files
```

## Technical Details

### Streaming Architecture
1. Audio padding at input
2. Chunk-based processing with generator
3. Real-time token decoding with TextIteratorStreamer
4. Thread-based inference for parallelism

### Delay Parameter
- Controls model output timing
- Balance between latency and accuracy
- Applied during model.generate()

## Backward Compatibility

✅ Fully backward compatible. Existing code works unchanged.

```bash
# Old way (still works)
python scripts/s2t_pipeline.py

# New way (recommended)
python scripts/s2t_pipeline.py --streaming
```
