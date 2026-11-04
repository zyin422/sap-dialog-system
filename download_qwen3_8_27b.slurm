#!/bin/bash
#SBATCH --job-name=dl-qwen38
#SBATCH --account=bedl-delta-cpu
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32g
#SBATCH --time=02:00:00
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_phase2/download_qwen38.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_phase2/download_qwen38.log

source /sw/external/python/anaconda3/etc/profile.d/conda.sh
conda activate /u/zyin2/.conda/envs/nemo

export HF_HOME=/work/hdd/bedl/zyin2/cache/huggingface
export TRANSFORMERS_CACHE=/work/hdd/bedl/zyin2/cache/huggingface
export HF_HUB_ENABLE_HF_TRANSFER=1

echo "=== Downloading Qwen/Qwen3.8-27B to Delta Storage ==="
date
hostname

python3 - << 'EOF'
import os
import sys
from huggingface_hub import snapshot_download

repo_id = "Qwen/Qwen3.8-27B"
local_dir = "/work/hdd/bedl/zyin2/models/Qwen3.8-27B"

print(f"Starting snapshot_download for {repo_id} -> {local_dir}...")
snapshot_download(
    repo_id=repo_id,
    local_dir=local_dir,
    local_dir_use_symlinks=False,
    resume_download=True,
    max_workers=8
)
print("Download finished successfully!")
EOF

echo "=== Download Job Complete ==="
date
