#!/bin/bash
#SBATCH --job-name=qwen3-task1-slu
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64g
#SBATCH --time=01:30:00
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_phase2/run_task1_unshared_dev.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_phase2/run_task1_unshared_dev.log

# ==============================================================================
# Speech Accessibility Project (SAP)
# Task 1: Single-Turn Complete SLU Benchmark Runner (Qwen3-8B + Rev 6 NLG)
# ==============================================================================

source /sw/external/python/anaconda3/etc/profile.d/conda.sh
conda activate /u/zyin2/.conda/envs/nemo

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export HF_HOME=/u/zyin2/.cache/huggingface
export TRANSFORMERS_CACHE=/u/zyin2/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

cd /work/hdd/bedl/zyin2/benchmark_phase2

# Allow overriding dataset via first argument (defaults to updated full Task 1 benchmark)
INPUT_CSV=${1:-"/work/hdd/bedl/zyin2/benchmark_phase2/manifest/dev_unshared_curated/task1_singleturn_slu_benchmark_updated.csv"}
PROMPT_PATH=${2:-"/work/hdd/bedl/zyin2/benchmark_phase2/certified_generalized_system_prompt_rev6_nlg.txt"}
MODEL_ID=${3:-"Qwen/Qwen3-8B"}
CONDITION=${4:-"all"}

BASENAME=$(basename "$INPUT_CSV" .csv)
OUTPUT_CSV="/work/hdd/bedl/zyin2/benchmark_phase2/eval_results/${BASENAME}_eval_results.csv"
OUTPUT_SUMMARY="/work/hdd/bedl/zyin2/benchmark_phase2/eval_results/${BASENAME}_eval_summary.json"

mkdir -p /work/hdd/bedl/zyin2/benchmark_phase2/eval_results

echo "=============================================================================="
echo "Starting Task 1 Single-Turn Complete SLU Benchmark Evaluation on Delta"
echo "Date:        $(date)"
echo "Host:        $(hostname)"
echo "Input CSV:   ${INPUT_CSV}"
echo "Prompt:      ${PROMPT_PATH}"
echo "Model ID:    ${MODEL_ID}"
echo "Condition:   ${CONDITION}"
echo "Output CSV:  ${OUTPUT_CSV}"
echo "Summary:     ${OUTPUT_SUMMARY}"
echo "=============================================================================="

nvidia-smi

python3 evaluate_slu_nlg_qwen3.py \
    --csv_path "${INPUT_CSV}" \
    --prompt_path "${PROMPT_PATH}" \
    --model_id "${MODEL_ID}" \
    --batch_size 16 \
    --max_new_tokens 130 \
    --condition "${CONDITION}" \
    --output_csv "${OUTPUT_CSV}" \
    --output_summary "${OUTPUT_SUMMARY}"

echo "=============================================================================="
echo "Task 1 SLU Benchmark Evaluation Finished Successfully"
echo "Date: $(date)"
echo "=============================================================================="
