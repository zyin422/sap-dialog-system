#!/bin/bash
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=2
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=00:20:00
#SBATCH --job-name=qwen3_heldout100
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_filtering/qwen27b_heldout_100.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_filtering/qwen27b_heldout_100.log

export HF_HOME=/u/zyin2/.cache/huggingface
export TRANSFORMERS_CACHE=/u/zyin2/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

echo "=== Starting Qwen 3 27B Held-out 100 Evaluation on Delta ==="
date
nvidia-smi

/u/zyin2/.conda/envs/nemo/bin/python /work/hdd/bedl/zyin2/benchmark_filtering/llm_judge_delta.py \
    --input_csv /work/hdd/bedl/zyin2/benchmark_filtering/dev_unshared_heldout_test_100.csv \
    --output_csv /work/hdd/bedl/zyin2/benchmark_filtering/dev_unshared_heldout_test_100_predictions.csv \
    --model_id /work/hdd/bedl/zyin2/models/Qwen3.8-27B \
    --batch_size 8

echo "=== Qwen 3 27B Job Finished ==="
date
