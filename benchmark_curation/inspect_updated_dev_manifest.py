#!/usr/bin/env python3
"""
inspect_updated_dev_manifest.py
===============================
Inspects the updated unshared dev manifest from Delta:
/work/hdd/bjas/xiuwenz2/Datasets/manifest_new/dev_unshared_prompt.json

Validates JSON schema, key completeness, speaker/etiology distributions,
and overlap with existing dev_unshared_consolidated_5748.csv.
"""

import os
import sys
import json
import argparse
import pandas as pd
from collections import Counter

def inspect_manifest_data(data, baseline_csv_path=None):
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            items = data["data"]
        else:
            items = list(data.values())
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError(f"Unsupported data format: {type(data)}")

    total = len(items)
    print(f"Total entries: {total}")
    if total == 0:
        return

    sample = items[0]
    keys = list(sample.keys())
    print(f"Schema keys ({len(keys)}): {keys}")

    speakers = Counter()
    etiologies = Counter()
    prompts = set()
    audio_paths = set()
    missing_fields = Counter()

    for idx, item in enumerate(items):
        spk = item.get("speaker") or item.get("speaker_id") or "UNKNOWN"
        et = item.get("etiology") or "UNKNOWN"
        p = item.get("prompt") or item.get("canonical_text") or ""
        aud = item.get("audio_filepath") or item.get("audio_path") or ""

        speakers[spk] += 1
        etiologies[et] += 1
        if p:
            prompts.add(p)
        if aud:
            audio_paths.add(aud)

        for k in keys:
            if k not in item or item[k] is None:
                missing_fields[k] += 1

    print(f"\nDistinct Speakers: {len(speakers)}")
    print(f"Distinct Etiologies ({len(etiologies)}): {dict(etiologies)}")
    print(f"Distinct Prompts: {len(prompts)}")
    print(f"Distinct Audio Files: {len(audio_paths)}")

    if missing_fields:
        print(f"Missing Fields Summary: {dict(missing_fields)}")

    print("\nFirst 3 entries:")
    for i in range(min(3, total)):
        print(f"--- Entry {i+1} ---")
        for k in keys:
            val = items[i].get(k)
            val_str = str(val)[:100] + "..." if len(str(val)) > 100 else str(val)
            print(f"  {k}: {val_str}")

    if baseline_csv_path and os.path.exists(baseline_csv_path):
        df_base = pd.read_csv(baseline_csv_path)
        base_audios = set(df_base["audio_filepath"].dropna())
        overlap = audio_paths.intersection(base_audios)
        print(f"\nComparison with baseline ({os.path.basename(baseline_csv_path)}):")
        print(f"  Baseline audios: {len(base_audios)}")
        print(f"  Updated audios:  {len(audio_paths)}")
        print(f"  Audio Overlap:   {len(overlap)} ({len(overlap)/len(audio_paths)*100:.2f}%)")

def load_json_or_jsonl(path: str):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        first_char = f.read(1)
        f.seek(0)
        if first_char == "[":
            items = json.load(f)
        else:
            for line in f:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
    return items

def main():
    parser = argparse.ArgumentParser(description="Inspect updated dev manifest JSON")
    parser.add_argument("--json-path", type=str, required=True, help="Path to dev_unshared_prompt.json")
    parser.add_argument("--baseline-csv", type=str, default="manifest/dev_unshared_curated/dev_unshared_consolidated_5748.csv")
    args = parser.parse_args()

    data = load_json_or_jsonl(args.json_path)
    inspect_manifest_data(data, args.baseline_csv)

if __name__ == "__main__":
    main()
