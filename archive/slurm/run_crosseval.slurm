#!/bin/bash

#SBATCH --job-name=cross-eval-calib
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
#SBATCH --time=01:00:00
#SBATCH --constraint="scratch"

# Output logs directed to your organized log directory
#SBATCH --output=logs/llm_only_eval/%x_%j.out
#SBATCH --error=logs/llm_only_eval/%x_%j_error.txt

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

# Phase 1: Calibrate Qwen-14B zero-shot on the 30 pilot prompts
echo "--- Running Phase 1: Pilot Calibration (30 commands) ---"
srun "$WORK_DIR/conda_envs/sap_env/bin/python" -u benchmark_curation/cross_model_eval.py \
    --phase calibrate \
    --model_id "Qwen/Qwen2.5-14B-Instruct" \
    --schema_path "benchmark_curation/schema_registry.json" \
    --output_path "benchmark_curation/calibration_results_qwen14b.json" \
    --temperature 0.0

# Phase 2: Full batch inference on all 405 unique commands (Uncomment when running all 405)
# echo "--- Running Phase 2: Batch Inference (405 commands) ---"
# srun "$WORK_DIR/conda_envs/sap_env/bin/python" -u benchmark_curation/cross_model_eval.py \
#     --phase autolabel \
#     --model_id "Qwen/Qwen2.5-14B-Instruct" \
#     --candidates_path "benchmark_curation/input_commands_compact.json" \
#     --gold_output_path "benchmark_curation/predictions_qwen14b.json" \
#     --temperature 0.0

echo "=== Delta Run Complete ==="