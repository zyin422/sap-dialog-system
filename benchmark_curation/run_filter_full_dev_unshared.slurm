#!/bin/bash
#SBATCH --account=bjas-delta-gpu
#SBATCH --partition=gpuA100x4-interactive
#SBATCH --nodes=1
#SBATCH --gpus=2
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=00:30:00
#SBATCH --job-name=sap_filter_dev
#SBATCH --output=/work/hdd/bedl/zyin2/benchmark_filtering/filter_dev_unshared.log
#SBATCH --error=/work/hdd/bedl/zyin2/benchmark_filtering/filter_dev_unshared.log

export HF_HOME=/u/zyin2/.cache/huggingface
export TRANSFORMERS_CACHE=/u/zyin2/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

echo "=== Starting Full SAP Dev-Unshared Two-Stage Filtering on Delta ==="
date
nvidia-smi

/u/zyin2/.conda/envs/nemo/bin/python /work/hdd/bedl/zyin2/benchmark_filtering/filter_manifest_pipeline.py \
    --input_manifest /work/hdd/bedl/zyin2/benchmark_filtering/dev_unshared_prompts.csv \
    --output_dir /work/hdd/bedl/zyin2/benchmark_filtering/dev_unshared_curated \
    --output_prefix dev_unshared \
    --model_id /work/hdd/bedl/zyin2/models/Qwen3.8-27B \
    --batch_size 8

echo "=== Curation Complete ==="
date
