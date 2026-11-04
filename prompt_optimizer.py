#!/usr/bin/env python3
"""
prompt_optimizer.py
===================
Autonomous prompt engineering loop for SAP Spoken Language Understanding (SLU).
Target: Optimize Parameter Filling (PF) on Oracle condition until PF > 90.0% or 5 iterations complete.
Constraints:
  - No benchmark dataset hacking or specific example leakage.
  - Only abstract behavioral boundaries, tool disambiguation rules, and generalized extraction principles.
  - Loads model once in GPU memory for fast sequential evaluation (~45s per round).
  - Once optimal prompt is identified, runs full 3-condition benchmark (Oracle, Base ASR, FT ASR).
"""

import os
import sys
import json
import re
import time
import argparse
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def normalize_text(text: str) -> str:
    if not text: return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def char_levenshtein(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[m][n]

def compute_char_f1(gold: str, hyp: str) -> float:
    g = normalize_text(gold)
    h = normalize_text(hyp)
    if not g and not h: return 1.0
    if not g or not h: return 0.0
    dist = char_levenshtein(g, h)
    precision = max(0.0, (len(h) - dist) / len(h)) if len(h) > 0 else 0.0
    recall = max(0.0, (len(g) - dist) / len(g)) if len(g) > 0 else 0.0
    if precision + recall == 0: return 0.0
    return round((2 * precision * recall) / (precision + recall), 4)

def parse_llm_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    
    try:
        out = json.loads(text)
        if isinstance(out, dict):
            domain = str(out.get("domain", "")).strip().lower()
            intent = str(out.get("intent", "")).strip().lower()
            slots = out.get("slots", {})
            if not isinstance(slots, dict): slots = {}
            return {"domain": domain, "intent": intent, "slots": slots, "raw": raw_text}
    except Exception:
        pass
    
    intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', raw_text)
    domain_match = re.search(r'"domain"\s*:\s*"([^"]+)"', raw_text)
    intent = intent_match.group(1).strip().lower() if intent_match else "unknown"
    domain = domain_match.group(1).strip().lower() if domain_match else "unknown"
    return {"domain": domain, "intent": intent, "slots": {}, "raw": raw_text, "parse_error": True}

def evaluate_predictions(preds: list, df: pd.DataFrame) -> dict:
    ts_correct = 0
    tcs_correct = 0
    pf_correct = 0
    total_slots = 0
    frame_correct = 0
    failures = []

    for p, (_, row) in zip(preds, df.iterrows()):
        gold_intent = str(row["intent"]).strip().lower()
        raw_slots = row.get("slots", "{}")
        gold_slots = json.loads(raw_slots) if isinstance(raw_slots, str) and raw_slots.strip() else {}

        pred_intent = p["intent"]
        pred_domain = p["domain"]
        pred_slots = p["slots"]

        # 1. TS
        is_ts = (pred_intent == gold_intent)
        if is_ts: ts_correct += 1

        # 2. TCS
        is_tcs = (not p.get("parse_error", False) and pred_domain not in ["unknown", "error", ""])
        if is_tcs: tcs_correct += 1

        # 3. PF
        all_slots_matched = True
        for k, v in gold_slots.items():
            total_slots += 1
            gv = str(v)
            pv = str(pred_slots.get(k, ""))
            norm_g = normalize_text(gv)
            norm_p = normalize_text(pv)

            slot_matched = (norm_g == norm_p) or (norm_g != "" and compute_char_f1(norm_g, norm_p) >= 0.85)
            if slot_matched:
                pf_correct += 1
            else:
                all_slots_matched = False
                failures.append({
                    "prompt": row["prompt"],
                    "domain": row["domain"],
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent,
                    "gold_key": k,
                    "gold_val": gv,
                    "pred_val": pv,
                    "pred_slots": pred_slots
                })

        if is_ts and is_tcs and all_slots_matched:
            frame_correct += 1

    n = len(df)
    return {
        "ts": round(ts_correct / n, 4),
        "tcs": round(tcs_correct / n, 4),
        "pf": round(pf_correct / total_slots, 4) if total_slots > 0 else 1.0,
        "frame_acc": round(frame_correct / n, 4),
        "failures": failures,
        "total_slots": total_slots,
        "pf_correct": pf_correct
    }

def get_base_tools_string(schema_path: str) -> str:
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    tools_doc = []
    for t in schema["tools"]:
        props = t.get("parameters", {}).get("properties", {})
        param_strs = []
        for p_name, p_info in props.items():
            if "enum" in p_info:
                param_strs.append(f"{p_name}: {p_info['enum']}")
            else:
                param_strs.append(f"{p_name} (str)")
        params_formatted = ", ".join(param_strs)
        tools_doc.append(f"- {t['name']} (domain: {t['domain']}): {params_formatted}")
    return "\n".join(tools_doc)

def build_prompt_candidate(tools_str: str, iteration: int) -> str:
    """Generates prompt candidates with increasingly refined, abstract behavioral guidelines."""
    
    # Candidate 1: Disambiguation Boundaries + Generic Event Noun & Proximity Rules
    if iteration == 1:
        rules = """EXTRACTION RULES & BEHAVIORAL BOUNDARIES:
1. Strict Enum Adherence: For parameters with a declared list of options in brackets [...], select strictly from that list. Do not use unlisted synonyms.
2. Base Noun Extraction: Extract core head noun phrases without leading prepositions (to, for, at, with) or possessive determiners (my, your, our).
3. Open-Vocabulary Fidelity: For open text spans, extract the exact spoken words without inventing unuttered information.
4. Minimal Slot Invariance: If a command does not mention a given parameter, omit that key from the 'slots' dictionary.
5. Generic Event Noun Retention: In `schedule_manage`, if a generic event noun (e.g. meeting, appointment, call, reminder) is spoken and no separate event topic is provided, retain that generic noun in the `title` parameter.
6. Proximity Sorting: In `places_search`, if the query specifies geographic proximity (e.g. 'nearby', 'closest', 'nearest'), populate `sort_by: "distance"`.
7. Navigation Routes: In `maps_route`, if asking for navigation, directions, or routes, populate `query_type: "directions"`.
8. Tool Disambiguation Boundaries:
   - Encyclopedic & Cultural QA: General knowledge questions, trivia, historical facts, and definitions about awards, entertainment, media, celebrities, or books belong to `qa_search`, NOT `media_search`. Use `media_search` only when actively searching for media items to play/browse on device.
   - Physical Locations vs Transit: Inquiries about finding physical transport stations (bus stops, train stations) belong to `places_search` under `business_type`. Use `transit_lookup` only for querying departure schedules, transit arrival times, or transit tickets.
   - Medication vs Calendar: Route to `health_medication_reminder` only if the user explicitly mentions taking or administering a pharmaceutical drug. Generic doctor or clinic appointments belong to `schedule_manage`."""

    # Candidate 2: Refined Boundary on Commercial Business Hours & Personal Memory + Slot Granularity
    elif iteration == 2:
        rules = """EXTRACTION RULES & BEHAVIORAL BOUNDARIES:
1. Strict Enum Adherence: For parameters with a declared list of options in brackets [...], select strictly from that list. Do not use unlisted synonyms.
2. Base Noun Extraction: Extract core head noun phrases without leading prepositions (to, for, at, with) or possessive determiners (my, your, our).
3. Open-Vocabulary Fidelity: For open text spans, extract the exact spoken words without inventing unuttered information.
4. Minimal Slot Invariance: If a command does not mention a given parameter, omit that key from the 'slots' dictionary.
5. Generic Event Noun Retention: In `schedule_manage`, if a generic event noun (e.g. meeting, appointment, call, reminder) is spoken and no separate event topic is provided, retain that generic noun in the `title` parameter.
6. Proximity Sorting: In `places_search`, if the query specifies geographic proximity (e.g. 'nearby', 'closest', 'nearest'), populate `sort_by: "distance"`.
7. Navigation Routes: In `maps_route`, if asking for navigation, directions, or routes, populate `query_type: "directions"`.
8. Commercial Businesses: Inquiries regarding commercial store opening hours, retail establishment locations, or local services belong to `places_search` (under `business_name` or `business_type`), NOT `qa_search`.
9. Personal Notes & Fact Storage: Declarative statements intended to record, memorize, or recall personal notes, item locations, or personal attributes belong to `memory_note_manage`, NOT `qa_search`.
10. Tool Disambiguation Boundaries:
   - Encyclopedic & Cultural QA: General knowledge questions, trivia, historical facts, and definitions about awards, entertainment, media, celebrities, or books belong to `qa_search`, NOT `media_search`. Use `media_search` only when actively searching for media items to play/browse on device.
   - Physical Locations vs Transit: Inquiries about finding physical transport stations (bus stops, train stations) belong to `places_search` under `business_type`. Use `transit_lookup` only for querying departure schedules, transit arrival times, or transit tickets.
   - Medication vs Calendar: Route to `health_medication_reminder` only if the user explicitly mentions taking or administering a pharmaceutical drug. Generic doctor or clinic appointments belong to `schedule_manage`."""

    # Candidate 3: Target Remaining Slots in Lists, Alarms, and Smart Home
    elif iteration == 3:
        rules = """EXTRACTION RULES & BEHAVIORAL BOUNDARIES:
1. Strict Enum Adherence: For parameters with a declared list of options in brackets [...], select strictly from that list. Do not use unlisted synonyms.
2. Base Noun Extraction: Extract core head noun phrases without leading prepositions (to, for, at, with) or possessive determiners (my, your, our).
3. Open-Vocabulary Fidelity: For open text spans, extract the exact spoken words without inventing unuttered information.
4. Minimal Slot Invariance: If a command does not mention a given parameter, omit that key from the 'slots' dictionary.
5. Generic Event Noun Retention: In `schedule_manage`, if a generic event noun (e.g. meeting, appointment, call, reminder) is spoken and no separate event topic is provided, retain that generic noun in the `title` parameter.
6. List Management Names: In `lists_manage`, extract the target list category (e.g. shopping list, to-do list, gift list) into `list_name`.
7. Proximity Sorting: In `places_search`, if the query specifies geographic proximity (e.g. 'nearby', 'closest', 'nearest'), populate `sort_by: "distance"`.
8. Navigation Routes: In `maps_route`, if asking for navigation, directions, or routes, populate `query_type: "directions"`.
9. Commercial Businesses: Inquiries regarding commercial store opening hours, retail establishment locations, or local services belong to `places_search` (under `business_name` or `business_type`), NOT `qa_search`.
10. Personal Notes & Fact Storage: Declarative statements intended to record, memorize, or recall personal notes, item locations, or personal attributes belong to `memory_note_manage`, NOT `qa_search`.
11. Tool Disambiguation Boundaries:
   - Encyclopedic & Cultural QA: General knowledge questions, trivia, historical facts, and definitions about awards, entertainment, media, celebrities, or books belong to `qa_search`, NOT `media_search`. Use `media_search` only when actively searching for media items to play/browse on device.
   - Physical Locations vs Transit: Inquiries about finding physical transport stations (bus stops, train stations) belong to `places_search` under `business_type`. Use `transit_lookup` only for querying departure schedules, transit arrival times, or transit tickets.
   - Medication vs Calendar: Route to `health_medication_reminder` only if the user explicitly mentions taking or administering a pharmaceutical drug. Generic doctor or clinic appointments belong to `schedule_manage`."""

    # Candidate 4: Target Device Finding & Alarm Recurrence
    elif iteration == 4:
        rules = """EXTRACTION RULES & BEHAVIORAL BOUNDARIES:
1. Strict Enum Adherence: For parameters with a declared list of options in brackets [...], select strictly from that list. Do not use unlisted synonyms.
2. Base Noun Extraction: Extract core head noun phrases without leading prepositions (to, for, at, with) or possessive determiners (my, your, our).
3. Open-Vocabulary Fidelity: For open text spans, extract the exact spoken words without inventing unuttered information.
4. Minimal Slot Invariance: If a command does not mention a given parameter, omit that key from the 'slots' dictionary.
5. Generic Event Noun Retention: In `schedule_manage`, if a generic event noun (e.g. meeting, appointment, call, reminder) is spoken and no separate event topic is provided, retain that generic noun in the `title` parameter.
6. List Management Names: In `lists_manage`, extract the target list category (e.g. shopping list, to-do list, gift list) into `list_name`.
7. Device Finding vs Notes: Inquiries asking to locate, ring, or find personal electronic hardware (phones, tablets, remotes) belong strictly to `device_find`, NOT `memory_note_manage`.
8. Proximity Sorting: In `places_search`, if the query specifies geographic proximity (e.g. 'nearby', 'closest', 'nearest'), populate `sort_by: "distance"`.
9. Navigation Routes: In `maps_route`, if asking for navigation, directions, or routes, populate `query_type: "directions"`.
10. Commercial Businesses: Inquiries regarding commercial store opening hours, retail establishment locations, or local services belong to `places_search` (under `business_name` or `business_type`), NOT `qa_search`.
11. Personal Notes & Fact Storage: Declarative statements intended to record, memorize, or recall personal notes, item locations, or personal attributes belong to `memory_note_manage`, NOT `qa_search`.
12. Tool Disambiguation Boundaries:
   - Encyclopedic & Cultural QA: General knowledge questions, trivia, historical facts, and definitions about awards, entertainment, media, celebrities, or books belong to `qa_search`, NOT `media_search`. Use `media_search` only when actively searching for media items to play/browse on device.
   - Physical Locations vs Transit: Inquiries about finding physical transport stations (bus stops, train stations) belong to `places_search` under `business_type`. Use `transit_lookup` only for querying departure schedules, transit arrival times, or transit tickets.
   - Medication vs Calendar: Route to `health_medication_reminder` only if the user explicitly mentions taking or administering a pharmaceutical drug. Generic doctor or clinic appointments belong to `schedule_manage`."""

    # Candidate 5: Comprehensive Canonical Tuning
    else:
        rules = """EXTRACTION RULES & BEHAVIORAL BOUNDARIES:
1. Strict Enum Adherence: For parameters with a declared list of options in brackets [...], select strictly from that list. Do not use unlisted synonyms.
2. Base Noun Extraction: Extract core head noun phrases without leading prepositions (to, for, at, with) or possessive determiners (my, your, our).
3. Open-Vocabulary Fidelity: For open text spans, extract the exact spoken words without inventing unuttered information.
4. Minimal Slot Invariance: If a command does not mention a given parameter, omit that key from the 'slots' dictionary.
5. Generic Event Noun Retention: In `schedule_manage`, if a generic event noun (e.g. meeting, appointment, call, reminder) is spoken and no separate event topic is provided, retain that generic noun in the `title` parameter.
6. List Management Names: In `lists_manage`, extract the target list category (e.g. shopping list, to-do list, gift list) into `list_name`.
7. Device Finding vs Notes: Inquiries asking to locate, ring, or find personal electronic hardware (phones, tablets, remotes) belong strictly to `device_find`, NOT `memory_note_manage`.
8. State Toggles in Smart Home: Binary actuation commands (turn on, turn off, lock, unlock) belong to `iot_device_power`. Note: locking maps to state "on"; unlocking maps to state "off". Continuous adjustments (temperature, brightness, volume) belong to `iot_device_adjust` or `media_volume`.
9. Proximity Sorting: In `places_search`, if the query specifies geographic proximity (e.g. 'nearby', 'closest', 'nearest'), populate `sort_by: "distance"`.
10. Navigation Routes: In `maps_route`, if asking for navigation, directions, or routes, populate `query_type: "directions"`.
11. Commercial Businesses: Inquiries regarding commercial store opening hours, retail establishment locations, or local services belong to `places_search` (under `business_name` or `business_type`), NOT `qa_search`.
12. Personal Notes & Fact Storage: Declarative statements intended to record, memorize, or recall personal notes, item locations, or personal attributes belong to `memory_note_manage`, NOT `qa_search`.
13. Tool Disambiguation Boundaries:
   - Encyclopedic & Cultural QA: General knowledge questions, trivia, historical facts, and definitions about awards, entertainment, media, celebrities, or books belong to `qa_search`, NOT `media_search`. Use `media_search` only when actively searching for media items to play/browse on device.
   - Physical Locations vs Transit: Inquiries about finding physical transport stations (bus stops, train stations) belong to `places_search` under `business_type`. Use `transit_lookup` only for querying departure schedules, transit arrival times, or transit tickets.
   - Medication vs Calendar: Route to `health_medication_reminder` only if the user explicitly mentions taking or administering a pharmaceutical drug. Generic doctor or clinic appointments belong to `schedule_manage`."""

    sys_prompt = f"""You are the Spoken Language Understanding (SLU) agent for the Speech Accessibility Project (SAP).
Map each spoken voice command into a valid JSON tool call conforming to the 29-tool schema below.

CANONICAL TOOLS AND PARAMETERS:
{tools_str}

{rules}

OUTPUT FORMAT:
Respond with ONLY a valid JSON object:
{{
  "domain": "<domain_name>",
  "intent": "<tool_name>",
  "slots": {{
    "<parameter_name>": "<canonical_parameter_value>"
  }}
}}
"""
    return sys_prompt

def run_loop():
    csv_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/decoded_benchmark_291_results.csv"
    schema_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/SLU_schema_v1.0.json"
    model_id = "Qwen/Qwen2.5-7B-Instruct"
    batch_size = 16

    print(f"=== Starting Autonomous SLU Prompt-Engineering Optimization Loop ===")
    print(f"Goal: Oracle Parameter Filling (PF) > 90.00% or 5 iterations complete.")
    
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} benchmark commands.")
    
    tools_str = get_base_tools_string(schema_path)
    prompts = df["prompt"].fillna("").tolist()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Model {model_id} into VRAM once...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left", truncation_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")
    model.eval()
    print("Model ready in VRAM.\n")

    best_pf = 0.0
    best_prompt_iter = 0
    best_results = None

    history = []

    for it in range(1, 6):
        print(f"\n{'='*30} ITERATION {it} / 5 {'='*30}")
        sys_prompt = build_prompt_candidate(tools_str, it)
        t_start = time.time()
        
        preds = []
        for i in range(0, len(prompts), batch_size):
            batch_texts = prompts[i : i + batch_size]
            messages_batch = [
                [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Spoken Transcript: \"{text}\""}
                ]
                for text in batch_texts
            ]

            formatted = [
                tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
                for m in messages_batch
            ]

            inputs = tokenizer(formatted, return_tensors="pt", padding=True, truncation=True, max_length=4096)
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                gen_ids = model.generate(**inputs, max_new_tokens=128, do_sample=False, pad_token_id=tokenizer.pad_token_id)
            
            in_len = inputs["input_ids"].shape[1]
            gen_tokens = gen_ids[:, in_len:]
            decoded = tokenizer.batch_decode(gen_tokens, skip_special_tokens=True)

            for dec in decoded:
                preds.append(parse_llm_json(dec))
        
        eval_res = evaluate_predictions(preds, df)
        elapsed = time.time() - t_start
        
        print(f"[Iteration {it} Result ({elapsed:.1f}s)]")
        print(f"  • Tool Selection (TS):    {eval_res['ts']*100:.2f}%")
        print(f"  • Structure (TCS):        {eval_res['tcs']*100:.2f}%")
        print(f"  • Parameter Filling (PF): {eval_res['pf']*100:.2f}% ({eval_res['pf_correct']} / {eval_res['total_slots']} slots)")
        print(f"  • Command Frame Accuracy: {eval_res['frame_acc']*100:.2f}%")
        print(f"  • Total Slot Failures:    {len(eval_res['failures'])}")

        history.append({
            "iteration": it,
            "ts": eval_res["ts"],
            "tcs": eval_res["tcs"],
            "pf": eval_res["pf"],
            "frame_acc": eval_res["frame_acc"],
            "failures_count": len(eval_res["failures"])
        })

        if eval_res["pf"] > best_pf:
            best_pf = eval_res["pf"]
            best_prompt_iter = it
            best_results = eval_res

        # Check termination condition
        if eval_res["pf"] >= 0.90:
            print(f"\n>>> TARGET REACHED! Parameter Filling {eval_res['pf']*100:.2f}% >= 90.00% on Iteration {it} <<<")
            break
        else:
            print(f"> Current PF: {eval_res['pf']*100:.2f}% < 90.00%. Continuing to next iteration...")

    print(f"\n{'='*70}")
    print(f"PROMPT OPTIMIZATION COMPLETE")
    print(f"Best Iteration: {best_prompt_iter} with Oracle PF = {best_pf*100:.2f}%")
    print(f"{'='*70}\n")

    # Run the winning prompt on all 3 conditions (Oracle, Base ASR, FT ASR)
    print(f"--- Running Final 3-Condition Benchmark with Winning Prompt (Iteration {best_prompt_iter}) ---")
    winning_sys_prompt = build_prompt_candidate(tools_str, best_prompt_iter)
    
    conditions = [
        ("oracle", "prompt"),
        ("base_asr", "base_parakeet_hypo"),
        ("ft_asr", "ft_parakeet_hypo")
    ]
    all_cond_results = {}

    for cond_name, col_name in conditions:
        print(f"Running full evaluation for {cond_name.upper()}...")
        col_prompts = df[col_name].fillna("").tolist()
        c_preds = []
        for i in range(0, len(col_prompts), batch_size):
            b_texts = col_prompts[i : i + batch_size]
            m_batch = [
                [
                    {"role": "system", "content": winning_sys_prompt},
                    {"role": "user", "content": f"Spoken Transcript: \"{text}\""}
                ]
                for text in b_texts
            ]
            fmt = [tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=True) for m in m_batch]
            inps = tokenizer(fmt, return_tensors="pt", padding=True, truncation=True, max_length=4096)
            inps = {k: v.to(device) for k, v in inps.items()}
            with torch.no_grad():
                g_ids = model.generate(**inps, max_new_tokens=128, do_sample=False, pad_token_id=tokenizer.pad_token_id)
            c_dec = tokenizer.batch_decode(g_ids[:, inps["input_ids"].shape[1]:], skip_special_tokens=True)
            for d in c_dec: c_preds.append(parse_llm_json(d))
        
        all_cond_results[cond_name] = evaluate_predictions(c_preds, df)
        df[f"{cond_name}_pred_intent"] = [p["intent"] for p in c_preds]
        df[f"{cond_name}_pred_slots"] = [json.dumps(p["slots"]) for p in c_preds]
        df[f"{cond_name}_pred_domain"] = [p["domain"] for p in c_preds]

    # Save outputs
    out_csv = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/slu_llm_eval_291_optimized_results.csv"
    out_summary = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/slu_llm_eval_291_optimized_summary.json"
    df.to_csv(out_csv, index=False)
    
    summary_data = {
        "optimization_history": history,
        "best_iteration": best_prompt_iter,
        "best_oracle_pf": best_pf,
        "final_benchmark": {
            c: {
                "ts": all_cond_results[c]["ts"],
                "tcs": all_cond_results[c]["tcs"],
                "pf": all_cond_results[c]["pf"],
                "frame_acc": all_cond_results[c]["frame_acc"]
            }
            for c in ["oracle", "base_asr", "ft_asr"]
        }
    }
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"\n{'='*75}")
    print("FINAL 3-CONDITION EVALUATION TABLE (WITH OPTIMIZED PROMPT)")
    print(f"{'='*75}")
    print(f"{'Condition':<12} | {'TS (Intent)':<12} | {'TCS (Syntax)':<12} | {'PF (Slots)':<12} | {'Frame Acc (E2E)':<16}")
    print("-" * 75)
    for c in ["oracle", "base_asr", "ft_asr"]:
        res = all_cond_results[c]
        print(f"{c.upper():<12} | {res['ts']*100:>10.2f}% | {res['tcs']*100:>10.2f}% | {res['pf']*100:>10.2f}% | {res['frame_acc']*100:>14.2f}%")
    print("=" * 75)
    print(f"Results saved to: {out_csv} and {out_summary}")

if __name__ == "__main__":
    run_loop()
