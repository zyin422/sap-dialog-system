#!/bin/bash

#SBATCH --job-name s2t-eval
#SBATCH --output %x_%j.out
#SBATCH --mail-user zyin16@illinois.edu
#SBATCH --error %x_%j_error.txt
#SBATCH --mail-type=BEGIN,END,FAIL

#SBATCH --account=bedl-delta-gpu
#SBATCH --partition=gpuA40x4
#SBATCH --time=00:20:00

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gpu-bind=closest
#SBATCH --mem=50G

#SBATCH --constraint="scratch"

export WORK_DIR="/work/hdd/bedl/zyin2"
export HF_HOME="$WORK_DIR/hf_cache"

module reset
module load python/3.11
source "$WORK_DIR/venvs/sap_env/bin/activate"

srun python3 s2t_pipeline.py