#!/bin/bash
#SBATCH --job-name=opt20_bjas
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:55:00
#SBATCH --output=/u/zyin2/prompt_optimizer_20.log
#SBATCH --error=/u/zyin2/prompt_optimizer_20.log

echo "=== Starting 20-Iteration SLU Prompt Optimization on Delta (Account: bjas-delta-gpu) ==="
date
nvidia-smi

export HF_HOME=/work/hdd/bedl/zyin2/cache/huggingface
export TRANSFORMERS_CACHE=/work/hdd/bedl/zyin2/cache/huggingface

source /u/zyin2/.bashrc
conda activate nemo

cd /work/hdd/bedl/zyin2/dev_audio/benchmark_291
python3 prompt_optimizer_20.py

echo "=== 20-Iteration Optimization Finished ==="
date
