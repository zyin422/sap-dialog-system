#!/bin/bash
#SBATCH --job-name=qwen38-judge
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=2
#SBATCH --cpus-per-task=16
#SBATCH --mem=64g
#SBATCH --time=01:00:00
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_phase2/run_qwen38_judge.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_phase2/run_qwen38_judge.log

source /sw/external/python/anaconda3/etc/profile.d/conda.sh
conda activate /u/zyin2/.conda/envs/nemo

export HF_HOME=/work/hdd/bedl/zyin2/cache/huggingface
export TRANSFORMERS_CACHE=/work/hdd/bedl/zyin2/cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PYTHONUNBUFFERED=1

cd /work/hdd/bedl/zyin2/benchmark_phase2

echo "=== Running Semantic LLM-as-a-Judge Evaluation with Qwen3.8-27B ==="
date
hostname
nvidia-smi

python3 evaluate_pf_llm_judge.py \
    --csv_path /work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_results.csv \
    --model_id /work/hdd/bedl/zyin2/models/Qwen3.8-27B \
    --device auto \
    --torch_dtype bfloat16 \
    --conditions oracle base_asr ft_asr \
    --output_json /work/hdd/bedl/zyin2/benchmark_phase2/semantic_judge_1200_summary.json \
    --audit_csv /work/hdd/bedl/zyin2/benchmark_phase2/semantic_judge_1200_audit_decisions.csv

echo "=== Semantic LLM Judge Evaluation Complete ==="
date
