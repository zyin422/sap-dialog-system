#!/bin/bash
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=2
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=00:45:00
#SBATCH --job-name=sap_llm_judge_851
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_filtering/llm_judge_851.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_filtering/llm_judge_851.log

# ==============================================================================
# Speech Accessibility Project (SAP)
# Stage 2: 4-Category LLM-as-a-Judge on Delta GPU (Qwen 3 27B)
# Evaluates 851 ambiguous / boundary cases from updated unshared dev manifest
# ==============================================================================

source /sw/external/python/anaconda3/etc/profile.d/conda.sh
conda activate /u/zyin2/.conda/envs/nemo

export HF_HOME=/u/zyin2/.cache/huggingface
export TRANSFORMERS_CACHE=/u/zyin2/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

echo "=============================================================================="
echo "Starting Stage 2 4-Category LLM-as-a-Judge Evaluation on Delta"
echo "Date:        $(date)"
echo "Host:        $(hostname)"
echo "Model:       /work/hdd/bedl/zyin2/models/Qwen3.8-27B"
echo "Input:       /work/hdd/bedl/zyin2/benchmark_filtering/dev_unshared_to_llm_851.csv"
echo "Output:      /work/hdd/bedl/zyin2/benchmark_filtering/dev_unshared_llm_judge_851_predictions.csv"
echo "=============================================================================="

nvidia-smi

python3 /work/hdd/bedl/zyin2/benchmark_filtering/llm_judge_4cat_delta.py \
    --input_csv /work/hdd/bedl/zyin2/benchmark_filtering/dev_unshared_to_llm_851.csv \
    --output_csv /work/hdd/bedl/zyin2/benchmark_filtering/dev_unshared_llm_judge_851_predictions.csv \
    --model_id /work/hdd/bedl/zyin2/models/Qwen3.8-27B \
    --batch_size 8

echo "=============================================================================="
echo "Stage 2 LLM-as-a-Judge Evaluation Finished Successfully"
echo "Date: $(date)"
echo "=============================================================================="
