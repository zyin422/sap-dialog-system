import time
from pathlib import Path
import mlx.nn as nn
from mlx_voxtral import VoxtralForConditionalGeneration, VoxtralProcessor
from mlx_voxtral.quantization import voxtral_mixed_quantization_predicate

print("[1/5] Loading official Voxtral model...")
t0 = time.time()
model = VoxtralForConditionalGeneration.from_pretrained("mistralai/Voxtral-Mini-3B-2507")
print(f"      Model loaded in {time.time() - t0:.2f}s")

print("[2/5] Quantizing model to 4-bit in memory (saves ~4.5 GB RAM)...")
t_q = time.time()
nn.quantize(
    model,
    bits=4,
    group_size=64,
    class_predicate=lambda p, m: voxtral_mixed_quantization_predicate(p, m, {}, default_bits=4),
)
print(f"      Quantized in {time.time() - t_q:.2f}s")

print("[3/5] Loading processor...")
# Load from local cache if offline, otherwise from HuggingFace
cache_snapshots = list(
    Path.home().glob(".cache/huggingface/hub/models--mistralai--Voxtral-Mini-3B-2507/snapshots/*")
)
if cache_snapshots:
    processor = VoxtralProcessor.from_pretrained(str(cache_snapshots[0]))
else:
    processor = VoxtralProcessor.from_pretrained("mistralai/Voxtral-Mini-3B-2507")

print("[4/5] Preprocessing speech.mp3...")
inputs = processor.apply_transcrition_request(
    language="en",
    audio="speech.mp3"
)

print("[5/5] Generating transcription (capped at 128 tokens)...")
t_gen = time.time()
kwargs = vars(inputs) if hasattr(inputs, "__dict__") else dict(inputs)
outputs = model.generate(**kwargs, max_new_tokens=128, temperature=0.0)
print(f"      Inference completed in {time.time() - t_gen:.2f}s")

print("[+] Decoding transcript...")
transcription = processor.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
print("\n================== TRANSCRIPTION RESULT ==================")
print(transcription)
print("==========================================================")