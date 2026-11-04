#!/bin/bash
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48g
#SBATCH --time=01:00:00
#SBATCH --job-name=qwen3_enriched_1108
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_phase2/run_qwen3_enriched_1108.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_phase2/run_qwen3_enriched_1108.log

echo "=== Starting Phase 2 Qwen3-8B Enriched Prompt SLU Benchmark on Delta (1108 Instances) ==="
date
hostname

source /sw/external/python/anaconda3/etc/profile.d/conda.sh
conda activate /u/zyin2/.conda/envs/nemo

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

cd /work/hdd/bedl/zyin2/benchmark_phase2

python3 evaluate_slu_enriched_qwen3.py \
    --csv_path /work/hdd/bedl/zyin2/benchmark_phase2/sampled_benchmark_1108.csv \
    --schema_path /work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json \
    --model_id Qwen/Qwen3-8B \
    --batch_size 8 \
    --max_new_tokens 90 \
    --condition all \
    --output_csv /work/hdd/bedl/zyin2/benchmark_phase2/enriched_eval_1108_results.csv \
    --output_summary /work/hdd/bedl/zyin2/benchmark_phase2/enriched_eval_1108_summary.json

echo "=== Finished Phase 2 Qwen3-8B Enriched Evaluation ==="
date
