#!/bin/bash
#SBATCH --job-name=qwen3_eval
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --output=/u/zyin2/run_qwen3_phase2.log
#SBATCH --error=/u/zyin2/run_qwen3_phase2.log

echo "=== Starting Phase 2 Qwen3-8B Benchmark Evaluation on Delta ==="
date
hostname

export HF_HOME=/work/hdd/bedl/zyin2/cache/huggingface
export TRANSFORMERS_CACHE=/work/hdd/bedl/zyin2/cache/huggingface

source /u/zyin2/.bashrc
conda activate nemo

cd /work/hdd/bedl/zyin2/benchmark_phase2

python3 -u evaluate_qwen3_phase2.py \
    --csv_path /work/hdd/bedl/zyin2/benchmark_phase2/sampled_benchmark_1108.csv \
    --schema_path /work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json \
    --model_id Qwen/Qwen3-8B \
    --batch_size 32 \
    --output_csv /work/hdd/bedl/zyin2/benchmark_phase2/qwen3_eval_1108_results.csv \
    --output_summary /work/hdd/bedl/zyin2/benchmark_phase2/qwen3_eval_1108_summary.json

echo "=== Phase 2 Qwen3 Evaluation Complete ==="
date
