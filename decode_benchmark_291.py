import os
import time
import pandas as pd
import torch
import nemo.collections.asr as nemo_asr

def main():
    csv_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/unique_benchmark_dev_291.csv"
    audio_dir = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/dev"
    output_csv = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/decoded_benchmark_291_results.csv"
    ft_ckpt = "/projects/bedl/xiuwenz2/Finetune_Nemo_ASR/dysarthric_en/exp/ft_dysarthric_en_0.6b/2026-04-19_20-49-23/checkpoints/ft_dysarthric_en_0.6b.nemo"
    base_model_name = "nvidia/parakeet-tdt-0.6b-v2"

    print("Loading benchmark metadata...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows.")

    audio_paths = [os.path.join(audio_dir, w) for w in df['wav']]
    for p in audio_paths[:3]:
        assert os.path.exists(p), f"Audio file not found: {p}"

    # 1. Base Model Decoding
    print(f"\n--- [1/2] Loading Base Model: {base_model_name} ---")
    t0 = time.time()
    base_model = nemo_asr.models.ASRModel.from_pretrained(model_name=base_model_name, map_location="cuda")
    base_model.eval()
    print(f"Base model loaded in {time.time() - t0:.2f}s.")

    print(f"Transcribing {len(audio_paths)} utterances with Base Model...")
    t1 = time.time()
    base_hypos = base_model.transcribe(audio=audio_paths, batch_size=32)
    # NeMo transcribe might return list of str or list of Hypothesis objects
    if hasattr(base_hypos[0], 'text'):
        base_hypos = [h.text for h in base_hypos]
    print(f"Base decoding completed in {time.time() - t1:.2f}s.")
    df['base_parakeet_hypo'] = base_hypos

    # Free memory
    del base_model
    torch.cuda.empty_cache()

    # 2. Fine-Tuned Model Decoding
    print(f"\n--- [2/2] Loading Fine-Tuned Checkpoint: {ft_ckpt} ---")
    t2 = time.time()
    ft_model = nemo_asr.models.ASRModel.restore_from(ft_ckpt, map_location="cuda")
    ft_model.eval()
    print(f"Fine-tuned model loaded in {time.time() - t2:.2f}s.")

    print(f"Transcribing {len(audio_paths)} utterances with FT Model...")
    t3 = time.time()
    ft_hypos = ft_model.transcribe(audio=audio_paths, batch_size=32)
    if hasattr(ft_hypos[0], 'text'):
        ft_hypos = [h.text for h in ft_hypos]
    print(f"FT decoding completed in {time.time() - t3:.2f}s.")
    df['ft_parakeet_hypo'] = ft_hypos

    df.to_csv(output_csv, index=False)
    print(f"\nSuccessfully wrote all decoded results to: {output_csv}")

if __name__ == "__main__":
    main()
