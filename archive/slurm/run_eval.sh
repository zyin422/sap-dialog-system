#!/bin/bash
set -e

# Delta Environment Paths
export WORK_DIR="/work/hdd/bedl/zyin2"
export HF_HOME="$WORK_DIR/hf_cache"

# Offline mode to prevent compute node network timeouts
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1

# Clean module environment and load Python
module reset
module load miniforge3-python

# Activate our specialized SAP conda environment
source activate "$WORK_DIR/conda_envs/sap_env"

echo "=== Environment Loaded ==="
echo "HF_HOME: $HF_HOME"
echo "Python:  $(which python)"
echo "=========================="

# Run LLM benchmark evaluation with unbuffered stdout
python -u conversation_llm_eval.py
