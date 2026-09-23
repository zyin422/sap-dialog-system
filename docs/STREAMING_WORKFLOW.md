# Streaming Inference Explanation

## Architecture

```
Audio File (.mp3/.wav)
    ↓
Load with Librosa (16kHz)
    ↓
Streaming Inference Core
  ① Audio padding
  ② Chunk processing generator
  ③ Model inference in thread
  ④ Main thread collects output
    ↓
Transcription → LLM Processing → JSON Output
```

## How It Works

### Step 1: Audio Padding
Pad silence at end to signal completion:
```python
xaudio = np.pad(audio, (0, pad))
```

### Step 2: First Chunk Processing
Process first audio chunk with special flags:
```python
first_chunk_inputs = processor(
    audio[: num_samples_first_chunk],
    is_streaming=True,
    is_first_audio_chunk=True
)
```

### Step 3: Audio Generator
Lazy-load remaining chunks as generator:
```python
def input_features_generator():
    yield first_chunk_inputs.input_features
    while has_more_chunks:
        chunk = next_audio_chunk()
        inputs = processor(chunk, is_streaming=True, ...)
        yield inputs.input_features
```

### Step 4: Text Streamer
Real-time token decoding:
```python
streamer = TextIteratorStreamer(tokenizer)
```

### Step 5: Inference Thread
Run in separate thread to avoid blocking:
```python
thread = Thread(target=model.generate, kwargs={
    "input_features": input_features_generator(),
    "streamer": streamer
})
thread.start()
```

### Step 6: Main Thread Collects
Main thread waits for output:
```python
for text_chunk in streamer:
    parts.append(text_chunk)
thread.join()
```

## Key Concepts

### Generator Pattern
- Delays loading until needed
- Saves memory (don't need full audio in memory)
- Enables streaming processing

### Threading
- Inference thread: processes chunks, generates tokens
- Main thread: waits for output, collects results
- Prevents deadlock and allows parallelism

### Delay Parameter
- Balances latency vs accuracy
- Lower delay = faster output but might be less accurate
- Higher delay = better accuracy but slower response

## Offline vs Streaming

| Aspect | Offline | Streaming |
|--------|---------|-----------|
| Loading | Full audio at once | Chunk by chunk |
| Latency | High | Low ⚡ |
| Memory | More | Less |
| Output | All at end | Partial during process |

## Example Timeline

```
Time:    0ms     100ms    200ms    300ms    400ms    500ms
Main:    create  wait     get"我"  get"要" get"设" get"置"
Thread:  start   process  emit"我" emit"要" emit"设" emit"置"
Gener:   yield1  yield2   yield3
Result:  "我要设置"
```

## When to Use

Use streaming when:
- ✅ Processing long audio files
- ✅ Need low latency
- ✅ Memory constrained
- ✅ Real-time applications

Use offline when:
- Short audio files (< 5s)
- Simplicity preferred
- Performance not critical
