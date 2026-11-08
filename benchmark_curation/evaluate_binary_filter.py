#!/usr/bin/env python3
"""
evaluate_binary_filter.py

Evaluates Two-Stage Binary Filtering (FILTER_OUT vs RETAIN) on the 245 Ground Truth Annotations:
- Stage 1: Quickfilter (Heuristic)
- Stage 2: Binary LLM-as-a-Judge (Qwen 3 27B)
"""

import sys
import argparse
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

def to_binary(decision: str) -> str:
    d = str(decision).strip().upper()
    if d == "FILTER_OUT":
        return "FILTER_OUT"
    return "RETAIN"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold_path", default="benchmark_curation/dev_unshared_manual_audit_245.csv")
    parser.add_argument("--stage1_path", default="benchmark_curation/dev_unshared_quickfilter_resolved.csv")
    parser.add_argument("--stage2_path", default="benchmark_curation/llm_judge_207_predictions_qwen27b_binary.csv")
    parser.add_argument("--merged_output_path", default="benchmark_curation/dev_unshared_binary_predictions_245.csv")
    args = parser.parse_args()

    df_gold = pd.read_csv(args.gold_path)
    df_s1 = pd.read_csv(args.stage1_path)
    df_s2 = pd.read_csv(args.stage2_path)

    print(f"Gold annotations: {len(df_gold)}")
    print(f"Stage 1 Quickfilter resolved: {len(df_s1)}")
    print(f"Stage 2 LLM Judge resolved: {len(df_s2)}")

    s1_dict = dict(zip(df_s1['id'], df_s1['quickfilter_decision'].map(to_binary)))
    s1_rat = dict(zip(df_s1['id'], df_s1['quickfilter_rationale']))

    s2_dict = dict(zip(df_s2['id'], df_s2['llm_decision'].map(to_binary)))
    s2_rat = dict(zip(df_s2['id'], df_s2['llm_rationale']))

    merged_rows = []
    for _, row in df_gold.iterrows():
        item_id = row['id']
        gold_4class = str(row['user_override']).strip()
        gold_bin = to_binary(gold_4class)

        if item_id in s1_dict:
            stage = "Stage 1 (Quickfilter)"
            pred_bin = s1_dict[item_id]
            rationale = s1_rat[item_id]
        elif item_id in s2_dict:
            stage = "Stage 2 (LLM Judge)"
            pred_bin = s2_dict[item_id]
            rationale = s2_rat[item_id]
        else:
            stage = "Unresolved"
            pred_bin = "RETAIN"
            rationale = "Missing prediction"

        merged_rows.append({
            'id': item_id,
            'speaker': row['speaker'],
            'etiology': row['etiology'],
            'prompt': row['prompt'],
            'spoken_text': row['spoken_text'],
            'gold_4class': gold_4class,
            'gold_binary': gold_bin,
            'pipeline_stage': stage,
            'predicted_binary': pred_bin,
            'pipeline_rationale': rationale,
            'is_match': (gold_bin == pred_bin)
        })

    df_merged = pd.DataFrame(merged_rows)
    df_merged.to_csv(args.merged_output_path, index=False)
    print(f"Merged binary predictions saved to {args.merged_output_path}")

    labels = ["RETAIN", "FILTER_OUT"]
    y_true = df_merged['gold_binary'].tolist()
    y_pred = df_merged['predicted_binary'].tolist()

    matches = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    total = len(y_true)
    acc = matches / total * 100.0

    print(f"\n==========================================")
    print(f"Binary Filtering Accuracy: {matches}/{total} ({acc:.2f}%)")
    print(f"==========================================")

    print("\nClassification Report (Binary):")
    print(classification_report(y_true, y_pred, labels=labels, digits=4, zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=[f"True_{l}" for l in labels], columns=[f"Pred_{l}" for l in labels])
    print("Confusion Matrix:")
    print(cm_df.to_string())

    # False purges (True RETAIN predicted as FILTER_OUT)
    false_purges = df_merged[(df_merged['gold_binary'] == 'RETAIN') & (df_merged['predicted_binary'] == 'FILTER_OUT')]
    print(f"\nFalse Purges (Critical Safety Metric - True RETAIN marked FILTER_OUT): {len(false_purges)}")
    for _, r in false_purges.iterrows():
        print(f"  [{r['id']}] ({r['gold_4class']})")
        print(f"    Prompt: \"{r['prompt']}\"")
        print(f"    Spoken: \"{r['spoken_text']}\"")
        print(f"    Reason: {r['pipeline_rationale']}")

    # False retentions (True FILTER_OUT predicted as RETAIN)
    false_retentions = df_merged[(df_merged['gold_binary'] == 'FILTER_OUT') & (df_merged['predicted_binary'] == 'RETAIN')]
    print(f"\nFalse Retentions (True FILTER_OUT marked RETAIN): {len(false_retentions)}")
    for _, r in false_retentions.iterrows():
        print(f"  [{r['id']}]")
        print(f"    Prompt: \"{r['prompt']}\"")
        print(f"    Spoken: \"{r['spoken_text']}\"")
        print(f"    Reason: {r['pipeline_rationale']}")

if __name__ == '__main__':
    main()
