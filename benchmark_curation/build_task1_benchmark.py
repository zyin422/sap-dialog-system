#!/usr/bin/env python3
"""
build_task1_benchmark.py
========================
Builds the official benchmark datasets for Task 1: Single-Turn Complete SLU Benchmark
on the unshared development set.

Ingests:
  manifest/dev_unshared_curated/dev_unshared_consolidated_5748.csv

Applies:
  Calibrated deterministic classification via benchmark_curation/filtering_engine.py:
  - Extracts intact command frames (KEEP)
  - Excludes underspecified / telegraphic instances (UNDERSPECIFIED)
  - Excludes phonetic / digit slot mutations (SLOT_DEVIATION)
  - Excludes prompt abandonment / metatalk (FILTER_OUT)

Exports:
  1. Full Task 1 Benchmark:
     manifest/dev_unshared_curated/task1_singleturn_slu_benchmark.csv (N = 5,511)
  2. Balanced Stratified Sample:
     manifest/dev_unshared_curated/task1_singleturn_balanced_sample.csv (N = 1,200, 240 per etiology)

Required Schema:
  - id, speaker, etiology, audio_filepath, duration
  - prompt: Canonical stimulus
  - oracle_transcript: Clean verbatim speech (norm_text_without_disfluency)
  - base_parakeet_hypo: Base ASR hypothesis
  - ft_parakeet_hypo: Fine-Tuned ASR hypothesis
  - domain, intent, slots_json
  - slots: Alias for slots_json (for evaluator compatibility)
  - gold_prompt_id, spoken_text (for traceability)
"""

import os
import sys
import json
import random
import argparse
import pandas as pd
from collections import Counter

# Ensure benchmark_curation is importable
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
if CURR_DIR not in sys.path:
    sys.path.insert(0, CURR_DIR)

from filtering_engine import classify_utterance

def resolve_path(p: str) -> str:
    if os.path.exists(p):
        return p
    alt = os.path.join(os.path.dirname(__file__), "..", p)
    if os.path.exists(alt):
        return alt
    alt2 = os.path.join(os.path.dirname(__file__), p)
    if os.path.exists(alt2):
        return alt2
    return p

def main():
    parser = argparse.ArgumentParser(description="Build Task 1 Single-Turn Complete SLU Benchmark")
    parser.add_argument("--input_csv", type=str,
                        default="manifest/dev_unshared_curated/dev_unshared_consolidated_5748.csv",
                        help="Path to consolidated 5,748 manifest")
    parser.add_argument("--output_full_csv", type=str,
                        default="manifest/dev_unshared_curated/task1_singleturn_slu_benchmark.csv",
                        help="Path to output full Task 1 benchmark CSV")
    parser.add_argument("--output_sample_csv", type=str,
                        default="manifest/dev_unshared_curated/task1_singleturn_balanced_sample.csv",
                        help="Path to output balanced stratified sample CSV")
    parser.add_argument("--target_per_etiology", type=int, default=240,
                        help="Target count per etiology for balanced sample (default: 240)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducible stratified sampling")
    args = parser.parse_args()

    input_path = resolve_path(args.input_csv)
    print(f"Loading input consolidated manifest from: {input_path}")
    df = pd.read_csv(input_path)
    total_candidates = len(df)
    print(f"Ingested {total_candidates} total consolidated instances.")

    # 1. Deterministic Tier Classification
    print("\nRunning calibrated benchmark tier classification...")
    tier_labels = []
    tier_rationales = []
    for idx, row in df.iterrows():
        label, rationale = classify_utterance(str(row["prompt"]), str(row["spoken_text"]))
        tier_labels.append(label)
        tier_rationales.append(rationale)

    df["benchmark_tier"] = tier_labels
    df["tier_rationale"] = tier_rationales

    tier_counts = Counter(tier_labels)
    print("\nBenchmark Tier Breakdown:")
    for tier, count in sorted(tier_counts.items(), key=lambda x: -x[1]):
        pct = count / total_candidates * 100
        print(f"  {tier:16s}: {count:5d} ({pct:5.2f}%)")

    # 2. Extract Complete Command Frames (KEEP)
    keep_df = df[df["benchmark_tier"] == "KEEP"].copy()
    print(f"\nExtracted {len(keep_df)} complete command frames for Task 1.")

    # Prepare standard fields
    keep_df["oracle_transcript"] = keep_df["norm_text_without_disfluency"].fillna("").astype(str).str.strip()
    keep_df["base_parakeet_hypo"] = keep_df["base_parakeet_hypo"].fillna("").astype(str).str.strip()
    keep_df["ft_parakeet_hypo"] = keep_df["ft_parakeet_hypo"].fillna("").astype(str).str.strip()
    keep_df["slots"] = keep_df["slots_json"]

    output_columns = [
        "id",
        "speaker",
        "etiology",
        "audio_filepath",
        "duration",
        "prompt",
        "oracle_transcript",
        "base_parakeet_hypo",
        "ft_parakeet_hypo",
        "domain",
        "intent",
        "slots_json",
        "slots",
        "gold_prompt_id",
        "spoken_text"
    ]

    # Verify column presence
    for col in output_columns:
        if col not in keep_df.columns:
            raise ValueError(f"Missing required column: {col}")

    task1_full = keep_df[output_columns].copy()

    # Sort full dataset by etiology, speaker, id
    task1_full = task1_full.sort_values(by=["etiology", "speaker", "id"]).reset_index(drop=True)

    # Export full benchmark
    out_full_path = resolve_path(args.output_full_csv)
    os.makedirs(os.path.dirname(out_full_path), exist_ok=True)
    task1_full.to_csv(out_full_path, index=False)
    print(f"Exported official full Task 1 benchmark to: {out_full_path} (N = {len(task1_full)})")

    # 3. Stratified Balanced Sampling (240 per etiology = 1,200)
    print(f"\nGenerating balanced, etiology-stratified subset ({args.target_per_etiology} per etiology)...")
    target_etiologies = ["ALS", "Cerebral Palsy", "Down Syndrome", "Parkinson's Disease", "Stroke"]
    sampled_records = []

    for et in target_etiologies:
        et_df = task1_full[task1_full["etiology"] == et].copy()
        if len(et_df) < args.target_per_etiology:
            raise ValueError(f"Insufficient instances for {et}: {len(et_df)} < {args.target_per_etiology}")

        # Deterministic shuffle
        et_df = et_df.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)

        # Enforce speaker cap and uniform prompt round-robin
        max_spk = 30 if et == "Stroke" else 20
        spk_counts = {}
        selected_et = []
        picked_ids = set()

        pool_by_prompt = {}
        for r in et_df.to_dict("records"):
            pool_by_prompt.setdefault(r["prompt"], []).append(r)

        prompts_list = list(pool_by_prompt.keys())
        # Sort prompts deterministically
        prompts_list.sort()

        while len(selected_et) < args.target_per_etiology:
            added_any = False
            for p in prompts_list:
                if len(selected_et) >= args.target_per_etiology:
                    break
                candidates = pool_by_prompt[p]
                for c in candidates:
                    cid = c["id"]
                    if cid in picked_ids:
                        continue
                    spk = c["speaker"]
                    if spk_counts.get(spk, 0) < max_spk:
                        selected_et.append(c)
                        picked_ids.add(cid)
                        spk_counts[spk] = spk_counts.get(spk, 0) + 1
                        added_any = True
                        break
            if not added_any:
                max_spk += 5

        print(f"  {et:20s}: sampled {len(selected_et)} instances across {len(spk_counts)} speakers "
              f"and {len(set(r['prompt'] for r in selected_et))} unique prompts (spk max={max(spk_counts.values())}, min={min(spk_counts.values())})")
        sampled_records.extend(selected_et)

    sample_df = pd.DataFrame(sampled_records)[output_columns]
    sample_df = sample_df.sort_values(by=["etiology", "speaker", "id"]).reset_index(drop=True)

    out_sample_path = resolve_path(args.output_sample_csv)
    sample_df.to_csv(out_sample_path, index=False)
    print(f"Exported official balanced sample to: {out_sample_path} (N = {len(sample_df)})")

    # 4. Summary Validation Checks
    print("\n================== Verification Metrics ==================")
    print(f"Task 1 Full Benchmark Count:     {len(task1_full)}")
    print(f"Task 1 Balanced Sample Count:    {len(sample_df)}")
    print(f"Total Unique Speakers (Full):    {task1_full['speaker'].nunique()}")
    print(f"Total Unique Speakers (Sample):  {sample_df['speaker'].nunique()}")
    print(f"Total Unique Prompts (Full):     {task1_full['prompt'].nunique()}")
    print(f"Total Unique Prompts (Sample):   {sample_df['prompt'].nunique()}")
    print(f"Total Tool Intents Covered:      {task1_full['intent'].nunique()}")
    print(f"Total Domains Covered:           {task1_full['domain'].nunique()}")

    # Check for NaN or empty fields
    for col in ["id", "speaker", "etiology", "audio_filepath", "duration", "prompt", "oracle_transcript", "domain", "intent", "slots_json"]:
        assert task1_full[col].isnull().sum() == 0, f"Null values found in {col} of full benchmark"
        assert sample_df[col].isnull().sum() == 0, f"Null values found in {col} of sample benchmark"

    print("All assertions passed: 0 null fields, schemas fully intact.")

if __name__ == "__main__":
    main()
