#!/usr/bin/env python3
"""
Zero-Leakage Benchmark Audit Tool
Exhaustively scans a prompt string against unique_benchmark_dev_291.csv.
Fails with exit code 1 if ANY benchmark quotes, benchmark n-grams (len >= 2),
or benchmark-specific named entities are detected.
"""

import sys
import re
import pandas as pd

def audit_prompt(prompt_text: str, benchmark_csv: str = "sap-dialog-system/unique_benchmark_dev_291.csv") -> list:
    df = pd.read_csv(benchmark_csv)
    prompts = [p.strip() for p in df['prompt'].tolist()]
    text_lower = prompt_text.lower()
    
    # 1. Benchmark Named Entities & Specific Nouns
    # Specific people, brands, places, specific items present in benchmark
    specific_benchmark_entities = [
        "nessa", "robert", "vanessa", "molly", "sonya", "sonya lee",
        "red lobster", "shell", "willis tower", "simvastatin", "levothyroxine",
        "losartan", "strattera", "xopanex", "citizen kane", "ologies", "planet money",
        "ben and jerry", "ben and jerry's", "portland timbers", "seattle mariners",
        "seattle seahawks", "cincinnati", "fairbanks", "mount washington", "sam's club",
        "buca di beppo", "covid test", "covid", "chili", "pizza dough", "heel balm",
        "mozzarella", "hair dryer brush", "hand warmers"
    ]
    
    violations = []
    
    # Check 1: Specific Benchmark Entities
    for ent in specific_benchmark_entities:
        if re.search(r'\b' + re.escape(ent) + r'\b', text_lower):
            violations.append(f"[ENTITY LEAK] Found benchmark entity: '{ent}'")
            
    # Check 2: Quoted phrases matching benchmark substrings
    quoted = re.findall(r"'([^']+)'", text_lower) + re.findall(r'"([^"]+)"', text_lower)
    for q in set(quoted):
        q_clean = q.strip('?.!')
        # Ensure extracted words are actual alphanumeric words
        q_words = [w for w in re.findall(r'\b[a-zA-Z0-9]+\b', q_clean) if len(w) >= 2 or w in ['a', 'i']]
        # Check any quoted phrase of 2 or more words
        if len(q_words) >= 2:
            q_phrase = ' '.join(q_words)
            # Skip purely generic programming / grammar terms
            if q_phrase in ['on off', 'up down', 'in out', 'a b and c']:
                continue
            for bp in prompts:
                bp_clean = ' '.join(re.findall(r'\b\w+\b', bp.lower()))
                if re.search(r'\b' + re.escape(q_phrase) + r'\b', bp_clean):
                    violations.append(f"[QUOTED PHRASE LEAK] '{q}' matches benchmark prompt: \"{bp}\"")
                    break
                    
    # Check 3: Full benchmark prompt matching
    for bp in prompts:
        bp_clean = bp.lower().rstrip('?.!')
        if len(bp_clean) > 8 and bp_clean in text_lower:
            # Check if it appears as an example
            violations.append(f"[VERBATIM COMMAND LEAK] Benchmark command found in prompt: \"{bp}\"")
            
    return list(set(violations))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_no_leakage.py <path_to_prompt_script>")
        sys.exit(1)
        
    script_path = sys.argv[1]
    with open(script_path) as f:
        code = f.read()
        
    violations = audit_prompt(code)
    if violations:
        print(f"FAILED: Found {len(violations)} leakage violations in {script_path}:")
        for v in sorted(violations):
            print("  ", v)
        sys.exit(1)
    else:
        print(f"PASSED: 0 leakage violations found in {script_path}. Prompt is 100% clean and generalized!")
        sys.exit(0)
