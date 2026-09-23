#!/bin/bash

#SBATCH --job-name s2t-pipeline
#SBATCH --output logs/%x_%j.out
#SBATCH --error logs/%x_%j_error.txt
#SBATCH --mail-type=BEGIN,END,FAIL

# GPU Configuration
#SBATCH --account=bedl-delta-gpu
#SBATCH --partition=gpuA40x4-interactive
#SBATCH --time=01:00:00

# Resource allocation
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gpu-bind=closest
#SBATCH --mem=50G

#SBATCH --constraint="scratch"

# Set work directory (modify as needed)
export WORK_DIR="/work/hdd/bczs/xiuwenz2/sap-dialog-system"
export HF_HOME="$WORK_DIR/.cache/hf"

# Optional: offline mode (comment out if online)
# export TRANSFORMERS_OFFLINE=1
# export HF_HUB_OFFLINE=1

cd "$WORK_DIR"

# Load environment
module reset
module load miniforge3-python
source activate sap_env

# Run inference with streaming mode
python -u scripts/s2t_pipeline.py --streaming --delay=480

echo "Pipeline complete. Results saved to results.json"
