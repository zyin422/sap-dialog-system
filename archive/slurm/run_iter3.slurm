#!/bin/bash
#SBATCH --job-name=slu_iter3
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=00:15:00
#SBATCH --output=/u/zyin2/run_iter3.log
#SBATCH --error=/u/zyin2/run_iter3.log

echo "=== Starting Iteration 3 Evaluation on Delta (Account: bjas-delta-gpu) ==="
date

export HF_HOME=/work/hdd/bedl/zyin2/cache/huggingface
export TRANSFORMERS_CACHE=/work/hdd/bedl/zyin2/cache/huggingface

source /u/zyin2/.bashrc
conda activate nemo

cd /work/hdd/bedl/zyin2/dev_audio/benchmark_291
python3 run_generalized_iter3.py

echo "=== Iteration 3 Complete ==="
date
