#!/bin/bash

#SBATCH --job-name s2t-eval
#SBATCH --output %x_%j.out
#SBATCH --mail-user zyin16@illinois.edu
#SBATCH --error %x_%j_error.txt
#SBATCH --mail-type=BEGIN,END,FAIL

#SBATCH --account=bedl-delta-gpu
#SBATCH --partition=gpuA40x4-interactive
#SBATCH --time=00:30:00

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gpu-bind=closest
#SBATCH --mem=50G

#SBATCH --constraint="scratch"

export WORK_DIR="/work/hdd/bedl/zyin2"
export HF_HOME="$WORK_DIR/hf_cache"

export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1

module reset
module load miniforge3-python
source activate "$WORK_DIR/conda_envs/sap_env"
srun "$WORK_DIR/conda_envs/sap_env/bin/python" -u s2t_pipeline.py
