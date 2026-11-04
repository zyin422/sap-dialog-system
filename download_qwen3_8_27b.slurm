#!/bin/bash
#SBATCH --job-name=dl-qwen38
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32g
#SBATCH --time=01:00:00
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_phase2/download_qwen38.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_phase2/download_qwen38.log

source /sw/external/python/anaconda3/etc/profile.d/conda.sh
conda activate /u/zyin2/.conda/envs/nemo

export HF_HOME=/work/hdd/bedl/zyin2/cache/huggingface
export TRANSFORMERS_CACHE=/work/hdd/bedl/zyin2/cache/huggingface

echo "=== Downloading Qwen/Qwen3.8-27B to Delta Storage ==="
date
hostname

python3 -m pip install -U "huggingface_hub[cli]"

# Download full bfloat16 weights
huggingface-cli download Qwen/Qwen3.8-27B \
    --local-dir /work/hdd/bedl/zyin2/models/Qwen3.8-27B \
    --local-dir-use-symlinks False

echo "=== Download Complete ==="
date
