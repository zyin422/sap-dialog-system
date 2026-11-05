import pandas as pd

df = pd.read_csv('sap-dialog-system/all_explicit_failing_prompts.csv')

target_queries = [
    'umbrella',
    'things to do in Kansas City',
    "what's playing",
    'favorites',
    'volume to minimum',
    'Listen to CBS',
    'Crime Junkie',
    'Answer the door',
    'nearest coffee shop',
    'Brighten the screen',
    'conclude',
    'conundrum',
    'weather in Naples',
    'pizza dough'
]

indices = []
for q in target_queries:
    matches = df[df['prompt'].str.contains(q, case=False, na=False)]
    if len(matches) > 0:
        idx = matches.index[0]
        if idx not in indices:
            indices.append(idx)

# Fill up to 14 if needed
for i in range(len(df)):
    if i not in indices and df.iloc[i]['domain'] in ['general_qa', 'media', 'communication', 'accessibility']:
        indices.append(i)
        if len(indices) == 14:
            break

slice_df = df.iloc[indices]
slice_df.to_csv('sap-dialog-system/dynamic_slice_iter4.csv', index=False)
print(f"Created dynamic_slice_iter4.csv with {len(slice_df)} prompts:")
for idx, r in slice_df.iterrows():
    print(f"  [{r['domain']}.{r['intent']}] '{r['prompt']}' | {r['slots']}")
