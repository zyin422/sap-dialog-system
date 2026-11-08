#!/usr/bin/env python3
"""
Evaluate Two-Stage Filtering Pipeline against Manual Ground Truth (245 rows).
Stage 1: Quickfilter (Heuristic)
Stage 2: LLM-as-a-Judge (Qwen-2.5-14B-Instruct on Delta)
"""

import sys
import argparse
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage2_path", default="benchmark_curation/llm_judge_207_predictions_qwen27b.csv")
    parser.add_argument("--merged_output_path", default="benchmark_curation/dev_unshared_two_stage_predictions_245_qwen27b.csv")
    args = parser.parse_args()

    gold_path = "benchmark_curation/dev_unshared_manual_audit_245.csv"
    stage1_path = "benchmark_curation/dev_unshared_quickfilter_resolved.csv"
    stage2_path = args.stage2_path
    merged_output_path = args.merged_output_path

    df_gold = pd.read_csv(gold_path)
    df_s1 = pd.read_csv(stage1_path)
    df_s2 = pd.read_csv(stage2_path)

    print(f"Gold rows: {len(df_gold)}")
    print(f"Stage 1 (Quickfilter) resolved: {len(df_s1)}")
    print(f"Stage 2 (LLM Judge) resolved: {len(df_s2)}")

    # Map stage 1 predictions
    s1_dict = dict(zip(df_s1['id'], df_s1['quickfilter_decision']))
    s1_rationale = dict(zip(df_s1['id'], df_s1['quickfilter_rationale']))

    # Map stage 2 predictions
    s2_dict = dict(zip(df_s2['id'], df_s2['llm_decision']))
    s2_rationale = dict(zip(df_s2['id'], df_s2['llm_rationale']))

    # Build merged dataframe
    merged_rows = []
    for _, row in df_gold.iterrows():
        item_id = row['id']
        gold = str(row['user_override']).strip()
        
        if item_id in s1_dict:
            stage = "Stage 1 (Quickfilter)"
            pred = s1_dict[item_id]
            rationale = s1_rationale[item_id]
        elif item_id in s2_dict:
            stage = "Stage 2 (LLM Judge)"
            pred = s2_dict[item_id]
            rationale = s2_rationale[item_id]
        else:
            stage = "Unresolved"
            pred = "NOT_SURE"
            rationale = "Missing prediction"

        merged_rows.append({
            'id': item_id,
            'speaker': row['speaker'],
            'etiology': row['etiology'],
            'duration': row['duration'],
            'prompt': row['prompt'],
            'spoken_text': row['spoken_text'],
            'gold_decision': gold,
            'pipeline_stage': stage,
            'predicted_decision': pred,
            'pipeline_rationale': rationale,
            'is_match': (gold == pred)
        })

    df_merged = pd.DataFrame(merged_rows)
    df_merged.to_csv(merged_output_path, index=False)
    print(f"Merged predictions saved to {merged_output_path}")

    # Metrics
    labels = ["KEEP", "UNDERSPECIFIED", "SLOT_DEVIATION", "FILTER_OUT"]
    y_true = df_merged['gold_decision'].tolist()
    y_pred = df_merged['predicted_decision'].tolist()

    matches = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    total = len(y_true)
    acc = matches / total * 100.0

    print(f"\n==========================================")
    print(f"Overall Accuracy: {matches}/{total} ({acc:.2f}%)")
    print(f"==========================================")

    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, labels=labels, digits=4, zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=[f"True_{l}" for l in labels], columns=[f"Pred_{l}" for l in labels])
    print("Confusion Matrix:")
    print(cm_df.to_string())

    # Discrepancies
    discrepancies = df_merged[~df_merged['is_match']]
    print(f"\nTotal Discrepancies: {len(discrepancies)}")
    for _, row in discrepancies.iterrows():
        print(f"\nID {row['id']} [{row['pipeline_stage']}]:")
        print(f"  Prompt: \"{row['prompt']}\"")
        print(f"  Spoken: \"{row['spoken_text']}\"")
        print(f"  Gold:   {row['gold_decision']}")
        print(f"  Pred:   {row['predicted_decision']}")
        print(f"  Reason: {row['pipeline_rationale']}")

if __name__ == '__main__':
    main()
