#!/bin/bash
#SBATCH --job-name=qwen3-ft-1200
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48g
#SBATCH --time=00:35:00
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_phase2/run_qwen3_ft_1200.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_phase2/run_qwen3_ft_1200.log

source /sw/external/python/anaconda3/etc/profile.d/conda.sh
conda activate /u/zyin2/.conda/envs/nemo

cd /work/hdd/bedl/zyin2/benchmark_phase2

echo "=== Running Final Condition 3 (FT ASR) on 1,200 Clean Benchmark ==="
python3 evaluate_slu_enriched_qwen3.py \
    --csv_path /work/hdd/bedl/zyin2/benchmark_phase2/sampled_benchmark_1200_clean.csv \
    --schema_path /work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json \
    --model_id Qwen/Qwen3-8B \
    --batch_size 12 \
    --condition ft_asr \
    --output_csv /work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_results.csv \
    --output_summary /work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_summary.json

echo "=== Benchmark Evaluation 100% Complete ==="
