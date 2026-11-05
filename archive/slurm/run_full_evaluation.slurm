#!/bin/bash

#SBATCH --job-name=sap-full-eval
#SBATCH --mail-user=zyin16@illinois.edu
#SBATCH --mail-type=BEGIN,END,FAIL

# Hardware: 1x NVIDIA A40 GPU (48GB VRAM) on Delta
#SBATCH --account=bedl-delta-gpu
#SBATCH --partition=gpuA40x4
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gpu-bind=closest
#SBATCH --mem=50G
#SBATCH --time=02:00:00
#SBATCH --constraint="scratch"

# Output logs directed to logs directory
#SBATCH --output=logs/full_eval_%x_%j.out
#SBATCH --error=logs/full_eval_%x_%j_error.txt

# Offline environment setup (pre-cached HF weights on Delta)
export WORK_DIR="/work/hdd/bedl/zyin2"
export HF_HOME="$WORK_DIR/hf_cache"
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1

# Clean module environment and activate existing conda env
module reset
module load miniforge3-python
source activate "$WORK_DIR/conda_envs/sap_env"

echo "=== Delta Job Initialized ==="
echo "Node:    $(hostname)"
echo "GPU:     $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"
echo "Python:  $(which python)"
echo "HF_HOME: $HF_HOME"
echo "============================="

# Paths for evaluation
BASE_CSV=${1:-"/projects/bedl/xiuwenz2/Finetune_Nemo_ASR/dysarthric_en/eval/parakeet-tdt-0.6b-v2/sapc2_test1.test1.merged.csv"}
FT_CSV=${2:-"/projects/bedl/xiuwenz2/Finetune_Nemo_ASR/dysarthric_en/eval/ft_dysarthric_en_0.6b/sapc2_test1.test1.merged.csv"}
OUTPUT_JSON=${3:-"eval_results/sapc2_evaluation_report.json"}

echo "--- Executing End-to-End ASR & SLU Evaluation Pipeline ---"
echo "Base ASR CSV: $BASE_CSV"
echo "FT ASR CSV:   $FT_CSV"
echo "Output:       $OUTPUT_JSON"

srun "$WORK_DIR/conda_envs/sap_env/bin/python" -u evaluate_asr_llm_pipeline.py \
    --base_csv "$BASE_CSV" \
    --ft_csv "$FT_CSV" \
    --gold_csv "schema_freeze/SLU_benchmark_gold_1309.csv" \
    --schema_json "schema_freeze/SLU_schema_v1.0.json" \
    --output_json "$OUTPUT_JSON"

echo "=== Delta Run Complete ==="
