#!/bin/bash
#SBATCH --job-name=qwen3-nlg-base
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA40x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48g
#SBATCH --time=00:55:00
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_phase2/run_qwen3_nlg_base_1200.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_phase2/run_qwen3_nlg_base_1200.log

source /sw/external/python/anaconda3/etc/profile.d/conda.sh
conda activate /u/zyin2/.conda/envs/nemo

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

cd /work/hdd/bedl/zyin2/benchmark_phase2

echo "=== Running Rev 6 NLG Condition 2 (Base ASR) on 1,200 Clean Benchmark ==="
date
hostname

python3 evaluate_slu_nlg_qwen3.py \
    --csv_path /work/hdd/bedl/zyin2/benchmark_phase2/sampled_benchmark_1200_clean.csv \
    --prompt_path /work/hdd/bedl/zyin2/benchmark_phase2/certified_generalized_system_prompt_rev6_nlg.txt \
    --model_id Qwen/Qwen3-8B \
    --batch_size 12 \
    --max_new_tokens 130 \
    --condition base_asr \
    --output_csv /work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_results.csv \
    --output_summary /work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_summary.json

echo "=== Finished Rev 6 NLG Base ASR Condition ==="
date
