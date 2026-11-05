import asyncio
import time
import soundfile as sf
import numpy as np
from scipy.signal import resample

from src.asr.streaming_asr import VoxtralStreamingASREngine


async def main():

    # 1. Load MP3 file using pydub
    data, orig_rate = sf.read("speech.mp3")

    # 2. Define target sample rate (e.g., 16000 Hz)
    target_rate = 16000
    num_output_samples = int(len(data) * target_rate / orig_rate)

    # 3. Resample using SciPy
    downsampled_data = resample(data, num_output_samples)

    audio_data, sr = downsampled_data, target_rate
    
    print("==================================================")
    print("   Voxtral Realtime Streaming ASR Demo (Phase 0)  ")
    print("==================================================")

    # 1. Initialize Streaming Engine (quantized to 4-bit)
    engine = VoxtralStreamingASREngine(
        model_id_or_path="mistralai/Voxtral-Mini-3B-2507",
        quantize=True,
        interim_interval_sec=1.0,  # Emit interim hypothesis every 1 second of audio
    )

    # 2. Read test audio file to simulate live microphone
    audio_path = "speech.mp3"
    print(f"\nLoading test audio from {audio_path}...")
    total_sec = len(audio_data) / sr
    print(f"Total audio duration: {total_sec:.2f}s (Sample Rate: {sr}Hz)")

    # 3. Simulate streaming audio in 500ms chunks
    chunk_duration_sec = 0.5
    chunk_size = int(sr * chunk_duration_sec)

    print("\n--- Starting Simulated Live Streaming Turn ---")
    t_turn_start = time.time()

    for offset in range(0, len(audio_data), chunk_size):
        chunk = audio_data[offset : offset + chunk_size]
        is_final = (offset + chunk_size) >= len(audio_data)

        # Feed chunk into streaming ASR engine
        hypothesis = await engine.transcribe_chunk(chunk, is_final=is_final)

        if hypothesis:
            status = "FINAL" if hypothesis.is_final else "INTERIM"
            print(
                f"[{hypothesis.audio_duration_sec:4.1f}s audio | {hypothesis.latency_ms:5.1f}ms latency] "
                f"[{status:7}] {hypothesis.text}"
            )

        # Simulate real-time streaming pace (optional, can be commented out for batch speed)
        await asyncio.sleep(0.05)

    print(f"\n--- Turn Finished in {time.time() - t_turn_start:.2f}s ---")


if __name__ == "__main__":
    asyncio.run(main())
