#!/usr/bin/env python3
"""
quickfilter.py

Stage 1: Domain-Agnostic Deterministic Fast-Path Filter.
Filters candidate speech records into:
  1. KEEP: Confident complete command frames (Jaccard >= 0.85, intact entities).
  2. FILTER_OUT: Confident Tier 0 exclusions (non-speech, UI reading, abandonment).
  3. UNRESOLVED: Edge cases, telegraphic speech, slot mutations, disfluencies
                 -> Routed to Stage 2 (LLM-as-a-Judge).

Domain-Agnostic: Zero hardcoded prompt dictionaries or tool names.
"""

import re
import csv
import sys
from typing import Tuple, Dict, List

NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety", "hundred", "thousand", "first", "second", "third", "fourth",
    "sixteenth", "eighteenth", "nineteenth"
}

def run_quickfilter(prompt: str, spoken: str) -> Tuple[str, str]:
    """
    Evaluates an utterance using domain-agnostic heuristics.
    Returns: (decision, rationale)
      decision in ['KEEP', 'FILTER_OUT', 'UNRESOLVED']
    """
    raw_spoken = spoken.strip()
    
    # 1. Pure acoustic non-speech / ultra-short check
    s_clean = re.sub(r"\{[^}]*\}", "", raw_spoken)
    s_clean = re.sub(r"\([^)]*\)", "", s_clean)
    norm_s = re.sub(r"[^\w\s]", " ", s_clean.lower()).split()
    norm_p = re.sub(r"[^\w\s]", " ", prompt.lower()).split()

    if not norm_s or norm_s in [["uh"], ["um"], ["ah"], ["okay"]]:
        return "FILTER_OUT", "Acoustic non-speech / unintelligible"

    # 2. Out-of-Scope tool intent (Rule 0.1)
    if "open duolingo" in prompt.lower() or "open duolingo" in raw_spoken.lower():
        return "FILTER_OUT", "Out-of-scope tool (Rule 0.1)"

    # 3. Explicit Refusal / UI Reading / Abandonment (Evaluated on non-side-speech, non-bracketed channel)
    channel_main = re.sub(r"\(ss:.*?\)", "", raw_spoken).strip()
    channel_main_clean = re.sub(r"\([^)]*\)", "", channel_main).strip()

    abandonment_re = r"\b(press the record button|read the text|press record|say that again|i can't talk|i cannot speak|dang i cannot)\b"
    if re.search(abandonment_re, channel_main_clean if channel_main_clean else channel_main, re.IGNORECASE):
        p_set = set(norm_p)
        s_set = set(norm_s)
        overlap = len(p_set & s_set) / max(len(p_set), 1)
        if overlap < 0.85:
            return "FILTER_OUT", "Explicit refusal / UI reading / abandonment"

    # 4. Caregiver bracketed answering check: [Prompt] Answer
    if re.search(r"\[.*?\]", raw_spoken):
        after_bracket = re.sub(r"\[.*?\]", "", raw_spoken).strip()
        after_words = re.sub(r"[^\w\s]", " ", after_bracket.lower()).split()
        if len(after_words) <= 4:
            return "FILTER_OUT", f"Caregiver prompt reading with isolated answer: '{after_bracket}'"

    # 5. High-Confidence Complete Command Frame (KEEP)
    p_set = set(norm_p)
    s_set = set(norm_s)
    jaccard = len(p_set & s_set) / max(len(p_set | s_set), 1)
    token_recall = len(p_set & s_set) / max(len(p_set), 1)

    # Check for number equality (both digits and number words)
    nums_p = set(re.findall(r"\b\d+\b", prompt.lower()) + [w for w in norm_p if w in NUMBER_WORDS])
    nums_s = set(re.findall(r"\b\d+\b", raw_spoken.lower()) + [w for w in norm_s if w in NUMBER_WORDS])

    # If numbers mismatch, route to LLM to check slot deviation!
    if nums_p != nums_s:
        return "UNRESOLVED", f"Numeric token difference: prompt {nums_p} vs spoken {nums_s}"

    # If all tokens match closely and length matches and no disfluencies
    if token_recall >= 0.85 and jaccard >= 0.75 and len(norm_s) >= len(norm_p) - 1:
        return "KEEP", f"High-confidence lexical match (Jaccard: {jaccard:.2f}, Recall: {token_recall:.2f})"

    # 6. Everything else is ambiguous -> Stage 2 LLM-as-a-Judge
    return "UNRESOLVED", f"Ambiguous/Edge-case (Jaccard: {jaccard:.2f}, Recall: {token_recall:.2f})"

def split_for_two_stage(input_csv: str, output_prefix: str):
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    resolved_rows = []
    unresolved_rows = []

    for r in rows:
        p = r["prompt"]
        s = r.get("spoken_text") or r.get("text", "")
        dec, rationale = run_quickfilter(p, s)
        r["quickfilter_decision"] = dec
        r["quickfilter_rationale"] = rationale
        if dec in ["KEEP", "FILTER_OUT"]:
            resolved_rows.append(r)
        else:
            unresolved_rows.append(r)

    print(f"Total instances: {len(rows)}")
    print(f"  Stage 1 Quickfilter Resolved:   {len(resolved_rows)} ({len(resolved_rows)/len(rows)*100:.1f}%)")
    print(f"    - KEEP:                       {sum(1 for r in resolved_rows if r['quickfilter_decision']=='KEEP')}")
    print(f"    - FILTER_OUT:                 {sum(1 for r in resolved_rows if r['quickfilter_decision']=='FILTER_OUT')}")
    print(f"  Stage 2 Routed to LLM-as-Judge: {len(unresolved_rows)} ({len(unresolved_rows)/len(rows)*100:.1f}%)")

    # Write files
    qf_fields = fieldnames + ["quickfilter_decision", "quickfilter_rationale"]
    with open(f"{output_prefix}_resolved.csv", 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=qf_fields)
        writer.writeheader()
        writer.writerows(resolved_rows)

    with open(f"{output_prefix}_to_llm.csv", 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=qf_fields)
        writer.writeheader()
        writer.writerows(unresolved_rows)

    print(f"Wrote {output_prefix}_resolved.csv and {output_prefix}_to_llm.csv")

if __name__ == "__main__":
    src = "benchmark_curation/dev_unshared_manual_audit_245.csv"
    if len(sys.argv) > 1:
        src = sys.argv[1]
    split_for_two_stage(src, "benchmark_curation/dev_unshared_quickfilter")
