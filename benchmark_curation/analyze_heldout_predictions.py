#!/usr/bin/env python3
"""
analyze_heldout_predictions.py

Analyzes Qwen 3 27B binary predictions on the held-out 100 sample from dev_unshared:
- Summarizes RETAIN vs FILTER_OUT distributions
- Breaks down decisions by etiology and slice type
- Inspects all FILTER_OUT instances and their rationales
"""

import sys
import pandas as pd

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "benchmark_curation/dev_unshared_heldout_test_100_predictions.csv"
    df = pd.read_csv(csv_path)

    print("==================================================")
    print(f"Held-Out Evaluation Summary (N = {len(df)})")
    print("==================================================")
    
    dec_col = "llm_decision" if "llm_decision" in df.columns else "predicted_binary"
    rat_col = "llm_rationale" if "llm_rationale" in df.columns else "pipeline_rationale"

    print("\nDecision Distribution:")
    print(df[dec_col].value_counts())
    print("\nPercentage:")
    print((df[dec_col].value_counts(normalize=True) * 100).round(1).astype(str) + "%")

    if "slice_type" in df.columns:
        print("\nDecision by Slice Type:")
        print(pd.crosstab(df['slice_type'], df[dec_col], margins=True))

    if "etiology" in df.columns:
        print("\nDecision by Etiology:")
        print(pd.crosstab(df['etiology'], df[dec_col], margins=True))

    filter_outs = df[df[dec_col] == "FILTER_OUT"]
    print(f"\n==================================================")
    print(f"Purged Instances (FILTER_OUT: {len(filter_outs)})")
    print("==================================================")
    for idx, r in filter_outs.iterrows():
        p = r.get("prompt", "")
        s = r.get("spoken_text") or r.get("text", "")
        rat = r.get(rat_col, "")
        et = r.get("etiology", "Unknown")
        sl = r.get("slice_type", "")
        print(f"\n[{et} | {sl}]")
        print(f"  Target: {p}")
        print(f"  Spoken: {s}")
        print(f"  Reason: {rat}")

if __name__ == "__main__":
    main()
