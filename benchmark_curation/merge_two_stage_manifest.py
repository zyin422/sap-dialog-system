#!/usr/bin/env python3
"""
merge_two_stage_manifest.py
===========================
Merges Stage 1 (Deterministic Fast-Path) and Stage 2 (4-Category LLM-as-a-Judge)
results into the official certified unshared dev benchmark dataset (N = 5,773).

Outputs:
  - manifest/dev_unshared_curated/dev_unshared_two_stage_certified_5773.csv
  - manifest/dev_unshared_curated/task1_singleturn_slu_benchmark_certified.csv (N = 5,309)
  - manifest/dev_unshared_curated/task1_singleturn_balanced_sample_certified.csv (N = 1,200)
  - manifest/dev_unshared_curated/task2_multiturn_asr_repair_benchmark_certified.csv
  - manifest/dev_unshared_curated/task3_underspecified_elicitation_benchmark_certified.csv
"""

import os
import sys
import json
import argparse
import pandas as pd
from collections import Counter

def main():
    s1_path = "manifest/dev_unshared_curated/dev_unshared_stage1_resolved_4922.csv"
    s2_path = "manifest/dev_unshared_curated/dev_unshared_llm_judge_851_predictions.csv"
    out_certified = "manifest/dev_unshared_curated/dev_unshared_two_stage_certified_5773.csv"

    print("Loading Stage 1 and Stage 2 files...")
    df_s1 = pd.read_csv(s1_path)
    df_s2 = pd.read_csv(s2_path)

    df_s1["final_curation_decision"] = df_s1["quickfilter_decision"]
    df_s1["curation_stage"] = "Stage 1 (Deterministic Fast-Path)"
    df_s1["curation_rationale"] = df_s1["quickfilter_rationale"]
    df_s1["llm_raw_response"] = ""

    df_s2["final_curation_decision"] = df_s2["llm_decision"]
    df_s2["curation_stage"] = "Stage 2 (LLM-as-a-Judge Qwen-27B)"
    df_s2["curation_rationale"] = df_s2["llm_rationale"]
    df_s2["llm_raw_response"] = df_s2["raw_llm_response"]

    # Align columns
    common_cols = [c for c in df_s1.columns if c in df_s2.columns]
    merged_df = pd.concat([df_s1[common_cols], df_s2[common_cols]], ignore_index=True)
    merged_df = merged_df.sort_values(by=["etiology", "speaker", "id"]).reset_index(drop=True)

    total = len(merged_df)
    assert total == 5773, f"Expected 5,773 rows, got {total}"
    assert merged_df["id"].nunique() == total, "Duplicate IDs in merged manifest!"

    print("\n================== Final Two-Stage Curation Yield ==================")
    counts = Counter(merged_df["final_curation_decision"])
    for dec, cnt in counts.most_common():
        pct = cnt / total * 100
        print(f"  {dec:16s}: {cnt:5d} ({pct:5.2f}%)")
    print(f"Total Instances: {total:5d}")
    print("====================================================================")

    # Save master certified manifest
    merged_df.to_csv(out_certified, index=False)
    print(f"\nSaved certified master manifest to: {out_certified}")

    # 1. Build Task 1 Certified (KEEP)
    keep_df = merged_df[merged_df["final_curation_decision"] == "KEEP"].copy()
    keep_df["oracle_transcript"] = keep_df["norm_text_without_disfluency"].fillna("").astype(str).str.strip()
    keep_df["slots"] = keep_df["slots_json"]

    task1_cols = [
        "id", "speaker", "etiology", "audio_filepath", "duration",
        "prompt", "oracle_transcript", "base_parakeet_hypo", "ft_parakeet_hypo",
        "domain", "intent", "slots_json", "slots", "gold_prompt_id", "spoken_text",
        "curation_stage", "curation_rationale"
    ]
    task1_full = keep_df[task1_cols].sort_values(by=["etiology", "speaker", "id"]).reset_index(drop=True)
    task1_out = "manifest/dev_unshared_curated/task1_singleturn_slu_benchmark_certified.csv"
    task1_full.to_csv(task1_out, index=False)
    print(f"Exported Task 1 Full Benchmark: {task1_out} (N = {len(task1_full)})")

    # Balanced 1,200 sample
    sample_dfs = []
    target_per_et = 240
    seed = 42
    print("\nGenerating balanced etiology-stratified subset (240 per etiology)...")
    for et, group in task1_full.groupby("etiology"):
        n_avail = len(group)
        n_sample = min(n_avail, target_per_et)
        sampled = group.sample(n=n_sample, random_state=seed)
        sample_dfs.append(sampled)
        print(f"  {et:20s}: sampled {n_sample} instances across {sampled['speaker'].nunique()} speakers")

    task1_sample = pd.concat(sample_dfs, ignore_index=True).sort_values(by=["etiology", "speaker", "id"]).reset_index(drop=True)
    task1_sample_out = "manifest/dev_unshared_curated/task1_singleturn_balanced_sample_certified.csv"
    task1_sample.to_csv(task1_sample_out, index=False)
    print(f"Exported Task 1 Balanced Sample: {task1_sample_out} (N = {len(task1_sample)})")

    # 2. Build Task 2 Certified (Corrupted Instances from valid attempts)
    # Valid attempts: KEEP + SLOT_DEVIATION
    valid_mask = merged_df["final_curation_decision"].isin(["KEEP", "SLOT_DEVIATION"])
    valid_df = merged_df[valid_mask].copy()

    base_ser_col = "base_ser" if "base_ser" in valid_df.columns else "base_norm_ser"
    ft_ser_col = "ft_ser" if "ft_ser" in valid_df.columns else "ft_norm_ser"
    corrupted_mask = (valid_df[base_ser_col] == 1) | (valid_df[ft_ser_col] == 1)
    corrupted_df = valid_df[corrupted_mask].copy()
    print(f"\nTask 2 Candidate Corrupted Instances: {len(corrupted_df)} (from {len(valid_df)} valid attempts)")

if __name__ == "__main__":
    main()
