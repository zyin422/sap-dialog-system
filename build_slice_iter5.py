import pandas as pd

# Load failing prompts and sampled benchmark to create a comprehensive cross-domain evaluation slice
df_fails = pd.read_csv('sap-dialog-system/all_explicit_failing_prompts.csv')
df_full = pd.read_csv('sap-dialog-system/unique_benchmark_dev_291.csv')

# We want 25 prompts covering all 10 domains, drawing especially from diverse challenging tools
selected_indices = []

# Domain targets for 25 prompts:
# smart_home: 3
# maps_places: 3
# calendar_alarm: 3
# general_qa: 3
# media: 3
# notes_memory: 3
# communication: 3
# health: 2
# transport: 1
# accessibility: 1

domain_targets = {
    'smart_home': 3,
    'maps_places': 3,
    'calendar_alarm': 3,
    'general_qa': 3,
    'media': 3,
    'notes_memory': 3,
    'communication': 3,
    'health': 2,
    'transport': 1,
    'accessibility': 1
}

selected_rows = []
for domain, count in domain_targets.items():
    # Prefer from df_fails first
    sub_fails = df_fails[df_fails['domain'] == domain]
    if len(sub_fails) >= count:
        sample = sub_fails.sample(count, random_state=42)
        selected_rows.append(sample)
    else:
        selected_rows.append(sub_fails)
        needed = count - len(sub_fails)
        sub_full = df_full[df_full['domain'] == domain]
        # Exclude prompts already picked
        sub_full = sub_full[~sub_full['prompt'].isin(sub_fails['prompt'])]
        sample = sub_full.sample(min(needed, len(sub_full)), random_state=42)
        selected_rows.append(sample)

iter5_df = pd.concat(selected_rows, ignore_index=True)
iter5_df = iter5_df.drop_duplicates(subset=['prompt']).reset_index(drop=True)
iter5_df.to_csv('sap-dialog-system/dynamic_slice_iter5.csv', index=False)

print(f"Created dynamic_slice_iter5.csv with {len(iter5_df)} prompts across {iter5_df['domain'].nunique()} domains:")
for domain, group in iter5_df.groupby('domain'):
    print(f"\n--- Domain: {domain} ({len(group)}) ---")
    for idx, r in group.iterrows():
        print(f"  [{r['intent']}] '{r['prompt']}' | {r['slots']}")
