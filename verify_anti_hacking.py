#!/usr/bin/env python3
"""
Rigorous Anti-Hacking & Structural Integrity Linter
Enforces:
1. Zero Tool Name Leaks in Global EXTRACTION RULES:
   EXTRACTION RULES must be purely universal, domain-agnostic linguistic principles.
   No tool names (e.g. weather_query, schedule_manage, iot_device_power) may appear in EXTRACTION RULES.
2. Zero Cross-Tool Redirects:
   No tool or parameter docstring may redirect to another tool ("belongs in X", "route to Y", "use X instead").
3. Zero Test Leakage:
   Runs verify_no_leakage.py checks for benchmark entity and n-gram contamination.
"""

import os
import sys
import re
import json
import importlib.util

def check_prompt_integrity(script_path: str = "sap-dialog-system/archive/evaluate_slu_enriched_qwen3.py",
                           schema_path: str = "sap-dialog-system/schema_freeze/SLU_schema_v1.0.json"):
    # Resolve script path if moved to archive
    if not os.path.exists(script_path):
        alt_path = os.path.join(os.path.dirname(script_path), "archive", os.path.basename(script_path))
        if os.path.exists(alt_path):
            script_path = alt_path

    # Load schema tools
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    tool_names = [t["name"] for t in schema["tools"]]

    # Load the module dynamically
    spec = importlib.util.spec_from_file_location("eval_mod", script_path)
    eval_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(eval_mod)

    sys_prompt = eval_mod.build_enriched_system_prompt(schema_path)

    violations = []

    # 1. Check EXTRACTION RULES section
    rules_match = re.search(r"EXTRACTION RULES:\s*(.*?)\s*OUTPUT FORMAT:", sys_prompt, re.DOTALL)
    if not rules_match:
        violations.append("[STRUCTURE ERROR] Could not find 'EXTRACTION RULES:' section preceding 'OUTPUT FORMAT:'.")
    else:
        rules_text = rules_match.group(1)
        for t in tool_names:
            if re.search(r"\b" + re.escape(t) + r"\b", rules_text, re.IGNORECASE):
                violations.append(f"[RULE HACKING] Tool name '{t}' explicitly referenced inside EXTRACTION RULES! Global rules must be domain-agnostic.")

    # 2. Check for cross-tool redirects in tool and parameter descriptions
    redirect_patterns = [
        r"belongs\s+in\s+[a-z_]+",
        r"route\s+to\s+[a-z_]+",
        r"use\s+[a-z_]+\s+instead",
        r"for\s+[a-z_]+,\s+see\s+[a-z_]+",
        r"do\s+not\s+handle\s+[a-z_]+"
    ]
    for pattern in redirect_patterns:
        matches = re.findall(pattern, sys_prompt, re.IGNORECASE)
        for m in matches:
            violations.append(f"[CROSS-TOOL REDIRECT] Found prohibited redirect phrase: '{m}'")

    # 3. Check for specific benchmark leaks (importing verify_no_leakage logic)
    import verify_no_leakage
    leakage = verify_no_leakage.audit_prompt(sys_prompt)
    if leakage:
        violations.extend(leakage)

    if violations:
        print(f"FAILED: {len(violations)} anti-hacking violation(s) detected in {script_path}:")
        for v in violations:
            print(f"  ❌ {v}")
        sys.exit(1)
    else:
        print(f"PASSED: 0 anti-hacking violations found in {script_path}. Prompt is 100% modular, clean, and un-hacked!")
        sys.exit(0)

if __name__ == "__main__":
    script = sys.argv[1] if len(sys.argv) > 1 else "sap-dialog-system/archive/evaluate_slu_enriched_qwen3.py"
    schema = sys.argv[2] if len(sys.argv) > 2 else "sap-dialog-system/schema_freeze/SLU_schema_v1.0.json"
    check_prompt_integrity(script, schema)
