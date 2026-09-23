#!/bin/bash

# Streaming ASR Pipeline Test - Multi-Latency Analysis
# Tests the full pipeline with streaming ASR mode at different latency values
# Latencies: 80ms, 480ms, 2400ms

set -e

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "════════════════════════════════════════════════════════════"
echo "🎙️  SAP Dialog System - Streaming ASR Latency Test"
echo "════════════════════════════════════════════════════════════"
echo "📍 Working directory: $(pwd)"
echo ""

# Check dependencies
echo "📋 Checking dependencies..."
if ! python -c "import torch, transformers, librosa" 2>/dev/null; then
    echo "❌ Dependencies missing. Installing..."
    pip install -r requirements.txt
fi
echo "✅ Dependencies OK"
echo ""

# Check audio files
echo "🎵 Checking audio files..."
if [ ! -d "audio" ] || [ -z "$(ls audio/*.mp3 audio/*.wav 2>/dev/null)" ]; then
    echo "❌ No audio files found in: $PROJECT_ROOT/audio/"
    echo "   Place .mp3 or .wav files in audio/ directory"
    exit 1
fi
AUDIO_COUNT=$(ls audio/*.{mp3,wav} 2>/dev/null | wc -l)
echo "✅ Found $AUDIO_COUNT audio files"
echo ""

# Define latency values to test
LATENCIES=(80 480 2400)
RESULTS_DIR="test_results"
mkdir -p "$RESULTS_DIR"

echo "🚀 Starting multi-latency test suite..."
echo "   Testing latencies: ${LATENCIES[@]}ms"
echo ""

# Run inference for each latency
for DELAY in "${LATENCIES[@]}"; do
    echo "────────────────────────────────────────────────────────────"
    echo "⏱️  Testing with delay: ${DELAY}ms"
    echo "────────────────────────────────────────────────────────────"

    # Run the pipeline with streaming mode
    python scripts/s2t_pipeline.py --streaming --delay=$DELAY

    # Save results for this latency
    if [ -f "results.json" ]; then
        cp results.json "$RESULTS_DIR/results_${DELAY}ms.json"
        echo "✅ Saved results for ${DELAY}ms latency"
    fi
    echo ""
done

echo "════════════════════════════════════════════════════════════"
echo "✅ All latency tests complete!"
echo "════════════════════════════════════════════════════════════"
echo ""

# Compare results across latencies
echo "📊 Performance Comparison:"
echo ""

python -c "
import json
import os
from pathlib import Path

latencies = [80, 480, 2400]
results_dir = 'test_results'

for delay in latencies:
    result_file = Path(results_dir) / f'results_{delay}ms.json'
    if result_file.exists():
        with open(result_file) as f:
            results = json.load(f)
        print(f'[{delay}ms Latency]')
        print(f'  Files processed: {len(results)}')

        if results:
            # Show first result as example
            r = results[0]
            audio_name = Path(r['audio_file']).name
            print(f'  Sample: {audio_name}')
            print(f'    Transcript: {r[\"asr_transcript\"][:60]}...')
            if 'intent' in r.get('llm_output', {}):
                print(f'    Intent: {r[\"llm_output\"][\"intent\"]}')
        print()
"

echo "📁 Detailed results by latency:"
echo "  test_results/results_80ms.json"
echo "  test_results/results_480ms.json"
echo "  test_results/results_2400ms.json"
echo ""
echo "🔍 View comparison: ls -lh test_results/"
