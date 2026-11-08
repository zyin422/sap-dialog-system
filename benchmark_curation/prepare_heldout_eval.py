#!/usr/bin/env python3
"""
Prepare 100 held-out evaluation instances from dev_unshared that were NOT in the 245 audit.
- Slice A: All 31 unresolved items from the 28 prompts completely unseen in the 245 audit.
- Slice B: 69 balanced held-out items across the 5 clinical etiologies (ALS, CP, PD, DS, Stroke).
"""

import pandas as pd
from benchmark_curation.quickfilter import run_quickfilter

def main():
    df_unshared = pd.read_csv("benchmark_curation/dev_unshared_filtered_5902.csv")
    df_245 = pd.read_csv("benchmark_curation/dev_unshared_manual_audit_245.csv")

    ids_245 = set(df_245['id'])
    prompts_245 = set(df_245['prompt'].unique())

    df_heldout = df_unshared[~df_unshared['id'].isin(ids_245)].copy()

    # Run quickfilter to find unresolved items
    unresolved_rows = []
    for _, r in df_heldout.iterrows():
        spoken = str(r.get('norm_text_with_disfluency') or r.get('text') or '').strip()
        dec, rat = run_quickfilter(r['prompt'], spoken)
        if dec == "UNRESOLVED":
            r_dict = r.to_dict()
            r_dict['spoken_text'] = spoken
            r_dict['quickfilter_rationale'] = rat
            unresolved_rows.append(r_dict)

    df_unres = pd.DataFrame(unresolved_rows)
    print(f"Total held-out unresolved instances: {len(df_unres)}")

    # Slice A: From unseen prompts (28 prompts)
    slice_a = df_unres[~df_unres['prompt'].isin(prompts_245)].copy()
    slice_a['slice_type'] = "Unseen Prompt"
    print(f"Slice A (Unseen Prompts): {len(slice_a)}")

    # Slice B: From seen prompts, balanced across etiologies
    slice_b_candidates = df_unres[df_unres['prompt'].isin(prompts_245)].copy()
    
    # Sample 69 instances balanced across etiologies
    target_count = 69
    sampled_b = []
    etiologies = slice_b_candidates['etiology'].unique()
    per_et = target_count // len(etiologies)
    
    for et in etiologies:
        sub = slice_b_candidates[slice_b_candidates['etiology'] == et]
        sample_size = min(len(sub), per_et)
        sampled_b.append(sub.sample(n=sample_size, random_state=42))

    df_b_sample = pd.concat(sampled_b)
    # If short of 69, fill with remaining
    if len(df_b_sample) < target_count:
        rem_needed = target_count - len(df_b_sample)
        rem_candidates = slice_b_candidates[~slice_b_candidates['id'].isin(df_b_sample['id'])]
        fill = rem_candidates.sample(n=rem_needed, random_state=42)
        df_b_sample = pd.concat([df_b_sample, fill])

    df_b_sample = df_b_sample.head(target_count).copy()
    df_b_sample['slice_type'] = "Held-Out Instance"
    print(f"Slice B (Held-Out Instances): {len(df_b_sample)}")

    # Combine into 100 test instances
    df_test_100 = pd.concat([slice_a, df_b_sample]).reset_index(drop=True)
    print(f"Total test instances: {len(df_test_100)}")
    print(df_test_100['slice_type'].value_counts())
    print("\nEtiology distribution:")
    print(df_test_100['etiology'].value_counts())

    output_path = "benchmark_curation/dev_unshared_heldout_test_100.csv"
    df_test_100.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")

if __name__ == '__main__':
    main()
