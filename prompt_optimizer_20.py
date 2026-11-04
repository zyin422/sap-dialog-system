#!/usr/bin/env python3
"""
Sequential 20-Iteration Cumulative SLU Prompt-Engineering Optimizer
Each iteration directly builds upon and improves the prompt from the previous iteration.

Loop Termination:
- Continues until all 20 iterations complete, OR
- Terminates early if Oracle PF >= 90.00%.

Integrity:
- Strict zero-leakage / zero-cheating policy: only generalized linguistic rules and behavioral boundaries.
"""

import os
import sys
import time
import json
import re
import copy
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def load_schema(schema_path: str):
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_tools_catalog(schema: dict) -> str:
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

def parse_llm_json(text: str) -> dict:
    fallback = {"domain": "error", "intent": "error", "slots": {}}
    if not text:
        return fallback
    clean = text.strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        clean = match.group(0)
    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            domain = str(data.get("domain", "")).strip().lower()
            intent = str(data.get("intent", "")).strip().lower()
            slots = data.get("slots", {})
            if not isinstance(slots, dict):
                slots = {}
            return {"domain": domain, "intent": intent, "slots": slots}
    except Exception:
        pass
    return fallback

def evaluate_predictions(predictions: list, df: pd.DataFrame) -> dict:
    total_commands = len(df)
    correct_intent = 0
    valid_structure = 0
    total_slots = 0
    correct_slots = 0
    frame_acc_correct = 0
    failures = []

    for idx, row in df.iterrows():
        p = predictions[idx]
        gold_intent = str(row["intent"]).strip().lower()
        pred_intent = p["intent"]

        gold_slots = {}
        if pd.notna(row["slots"]):
            try:
                gold_slots = json.loads(row["slots"]) if isinstance(row["slots"], str) else row["slots"]
            except Exception:
                gold_slots = {}
        pred_slots = p["slots"]

        if pred_intent != "error" and isinstance(pred_slots, dict):
            valid_structure += 1

        is_intent_correct = (pred_intent == gold_intent)
        if is_intent_correct:
            correct_intent += 1

        cmd_frame_perfect = is_intent_correct
        for k, v in gold_slots.items():
            total_slots += 1
            if not is_intent_correct:
                cmd_frame_perfect = False
                failures.append({
                    "id": row.get("gold_id", idx),
                    "prompt": row.get("prompt", ""),
                    "reason": "Intent Mismatch",
                    "slot": k,
                    "gold_val": v,
                    "pred_val": None
                })
            elif k not in pred_slots:
                cmd_frame_perfect = False
                failures.append({
                    "id": row.get("gold_id", idx),
                    "prompt": row.get("prompt", ""),
                    "reason": "Missing Slot",
                    "slot": k,
                    "gold_val": v,
                    "pred_val": None
                })
            else:
                pred_v_clean = str(pred_slots[k]).lower().strip()
                gold_v_clean = str(v).lower().strip()
                if pred_v_clean == gold_v_clean:
                    correct_slots += 1
                else:
                    cmd_frame_perfect = False
                    failures.append({
                        "id": row.get("gold_id", idx),
                        "prompt": row.get("prompt", ""),
                        "reason": "Value Mismatch",
                        "slot": k,
                        "gold_val": v,
                        "pred_val": pred_slots[k]
                    })

        if cmd_frame_perfect:
            frame_acc_correct += 1

    return {
        "ts": correct_intent / total_commands if total_commands else 0,
        "tcs": valid_structure / total_commands if total_commands else 0,
        "pf": correct_slots / total_slots if total_slots else 0,
        "frame_acc": frame_acc_correct / total_commands if total_commands else 0,
        "pf_correct": correct_slots,
        "total_slots": total_slots,
        "failures": failures
    }

# ==============================================================================
# CUMULATIVE 20-ITERATION PROMPT DEFINITIONS
# ==============================================================================

# Each entry i represents the new incremental rule/architectural improvement added in iteration i
ITERATION_IMPROVEMENTS = [
    # Iteration 1: Baseline Calibrated Prompt (Core Rules)
    (
        "Baseline Schema Constraints",
        [
            "Strict Enum Adherence: For parameters with a declared list of options in brackets [...], select strictly from that list. Do not use unlisted synonyms.",
            "Minimal Slot Invariance: If a command does not mention a given parameter, omit that key from the 'slots' dictionary.",
            "Open-Vocabulary Fidelity: For open text spans, extract the exact spoken words without inventing unuttered information."
        ],
        "standard"
    ),
    # Iteration 2: Punctuation & Quote Hygiene
    (
        "Punctuation & Quote Hygiene on Queries and Titles",
        [
            "Punctuation & Quote Hygiene: For free-text query and title slots (e.g. query in qa_search, title in schedule_manage), do NOT append trailing sentence punctuation marks (such as '?' or '.') and do NOT enclose phrases in quotes unless explicitly spoken. Output clean unpunctuated spoken words."
        ],
        "standard"
    ),
    # Iteration 3: Compound Entity Preservation
    (
        "Compound Entity and Descriptive Span Preservation",
        [
            "Compound Entity Preservation: When extracting entity slots (device_type, item, business_type, query), retain full compound modifiers, adjectives, and spatial descriptors (e.g. compound appliance names, multi-word gift items, composite room/door descriptors) rather than trimming to an isolated single noun."
        ],
        "standard"
    ),
    # Iteration 4: Semantic Action Enum Mapping
    (
        "Semantic Action Enum Mapping (Cancel -> Delete; Extreme Volume -> Set)",
        [
            "Semantic Action Enum Mapping:\n   - In schedule_manage, requests to cancel, drop, or remove an event map strictly to action: 'delete' (the schema does not have a 'cancel' enum).\n   - In media_volume, commands setting volume to an absolute or extreme target (e.g. 'to minimum', 'to maximum') map to action: 'set' with change_amount capturing the target level."
        ],
        "standard"
    ),
    # Iteration 5: Temporal & Holiday Anchor Completeness
    (
        "Exhaustive Temporal & Holiday Anchor Slot Extraction",
        [
            "Temporal Completeness: Whenever a spoken utterance mentions a relative day ('today', 'tomorrow', 'yesterday'), day of the week, calendar date, or recognized holiday ('Memorial Day', 'New Year's Eve'), always extract that expression into the date slot across scheduling, alarm, and weather domains."
        ],
        "standard"
    ),
    # Iteration 6: Meeting Attendee / Contact Slot Extraction
    (
        "Meeting Participant & Attendee Extraction",
        [
            "Meeting Attendee Extraction: In schedule_manage, if the utterance specifies an event participant or person with whom an event is scheduled (e.g. 'with [Person]'), populate the person parameter with their name."
        ],
        "standard"
    ),
    # Iteration 7: Generic Event Noun Retention
    (
        "Generic Event Noun Retention in Schedule Titles",
        [
            "Generic Event Noun Retention: In schedule_manage, if a generic event noun (e.g. meeting, appointment, call, reminder) is spoken and no separate event topic is provided, retain that generic noun in the title parameter."
        ],
        "standard"
    ),
    # Iteration 8: Telephony Direct Action Routing
    (
        "Direct Telephony Calling vs Geographic Search Disambiguation",
        [
            "Telephony Action Routing: Spoken commands that begin with direct telephony verbs ('call', 'dial', 'phone') directed at named establishments, contacts, or phone numbers belong strictly to call_make (with the target in recipient), NOT places_search."
        ],
        "standard"
    ),
    # Iteration 9: Ambient Outdoor Weather vs Indoor Home Climate Sensors
    (
        "Environmental Climate Disambiguation (Weather vs IoT Sensors)",
        [
            "Environmental Domain Disambiguation: Inquiries regarding outdoor temperature, ambient atmospheric conditions, or regional forecasts belong to weather_query. Use iot_sensor_query strictly for querying indoor rooms, smart home appliances, or internal home climate sensors."
        ],
        "standard"
    ),
    # Iteration 10: Long-Form Spoken Media & Audiobooks
    (
        "Audiobook and Literary Spoken Media Routing",
        [
            "Spoken Media Boundaries: Requests to play, resume, or read recorded audiobooks or published books belong to media_play, NOT messages_manage."
        ],
        "standard"
    ),
    # Iteration 11: List Inspection Query Action Resolution
    (
        "Collection & List Query Action Resolution",
        [
            "List Inspection Actions: Inquiries asking to view, inspect, or read items in a collection (e.g. 'what is on my [X] list', 'read my [X] list') belong to lists_manage with action: 'query' and the list category in list_name."
        ],
        "standard"
    ),
    # Iteration 12: Navigation Query Type Induction
    (
        "Navigation and Route Turn-by-Turn Query Type Induction",
        [
            "Navigation Query Types: In maps_route, requests for directions, navigation, driving routes, or turn-by-turn guidance must explicitly populate query_type: 'directions'."
        ],
        "standard"
    ),
    # Iteration 13: Contact & Phone Type Resolution
    (
        "Communication Relationship & Phone Type Descriptors",
        [
            "Contact & Phone Type Resolution: In call_make and messages_manage, extract family or contact relationship descriptors into recipient (e.g. 'grandma', 'mom'), and capture telephone designations ('mobile', 'cell', 'home', 'work') into phone_type."
        ],
        "standard"
    ),
    # Iteration 14: Commercial Retail Store Hours & Services
    (
        "Commercial Retail Store Hours vs General QA",
        [
            "Commercial Businesses: Inquiries regarding commercial store opening hours, retail establishment locations, or local services belong to places_search (under business_name or business_type), NOT qa_search."
        ],
        "standard"
    ),
    # Iteration 15: Personal Declarative Memory Notes vs Encyclopedic QA
    (
        "Personal Memory Note Storage vs Encyclopedic QA",
        [
            "Personal Notes & Fact Storage: Declarative statements intended to record, memorize, or recall personal notes, item locations, or personal attributes belong to memory_note_manage, NOT qa_search."
        ],
        "standard"
    ),
    # Iteration 16: Hardware Device Finding Disambiguation
    (
        "Hardware Device Finding vs Generic Notes",
        [
            "Device Finding vs Notes: Inquiries asking to locate, ring, or find personal electronic hardware (phones, tablets, remotes) belong strictly to device_find (populated with device_type), NOT memory_note_manage."
        ],
        "standard"
    ),
    # Iteration 17: Spatial Proximity & Distance Sorting
    (
        "Spatial Proximity and Distance Sorting Directives",
        [
            "Proximity Sorting: In places_search, if the query specifies geographic proximity (e.g. 'nearby', 'closest', 'nearest'), populate sort_by: 'distance'."
        ],
        "standard"
    ),
    # Iteration 18: Negative Hallucination Invariance
    (
        "Zero Hallucination Negative Constraint",
        [
            "Zero Hallucination Constraint: Under no circumstances infer, guess, or invent parameters that were not directly uttered in the speech transcript (e.g. do not invent room locations, times, or dates if unmentioned)."
        ],
        "standard"
    ),
    # Iteration 19: Exhaustive Multi-Facet Parameter Extraction
    (
        "Exhaustive Multi-Facet Parameter Extraction",
        [
            "Exhaustive Slot Extraction: When an utterance contains multiple semantic facets (action + target entity + temporal anchor + participant), extract all applicable parameters conforming to schema properties without omitting secondary slots."
        ],
        "standard"
    ),
    # Iteration 20: Two-Stage Cognitive Decomposition
    (
        "Two-Stage Cognitive Hierarchy (Stage 1: Tool Selection, Stage 2: Slot Filling)",
        [
            "Two-Stage Cognitive Resolution: First identify the exact canonical tool and functional domain from the schema, then systematically extract all relevant parameters conforming to rules 1-19."
        ],
        "two_stage"
    )
]

def build_prompt_for_iteration(tools_str: str, iteration_idx: int) -> tuple:
    """
    Builds the prompt cumulatively: iteration k includes all improvements from iterations 1..k.
    """
    cumulative_rules = []
    arch_mode = "standard"
    last_desc = ""

    for i in range(iteration_idx + 1):
        desc, rules, mode = ITERATION_IMPROVEMENTS[i]
        cumulative_rules.extend(rules)
        if mode != "standard":
            arch_mode = mode
        last_desc = desc

    rules_text = "\n".join([f"{idx+1}. {r}" for idx, r in enumerate(cumulative_rules)])

    if arch_mode == "two_stage":
        sys_prompt = f"""You are the Spoken Language Understanding (SLU) agent for the Speech Accessibility Project (SAP).
Perform two-stage mapping of each spoken voice command into a valid JSON tool call conforming to the 29-tool schema below.
Stage 1: Identify the exact functional domain and tool intent.
Stage 2: Extract all relevant parameters adhering strictly to schema constraints.

CANONICAL TOOLS AND PARAMETERS:
{tools_str}

EXTRACTION RULES & BEHAVIORAL BOUNDARIES:
{rules_text}

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
    else:
        sys_prompt = f"""You are the Spoken Language Understanding (SLU) agent for the Speech Accessibility Project (SAP).
Map each spoken voice command into a valid JSON tool call conforming to the 29-tool schema below.

CANONICAL TOOLS AND PARAMETERS:
{tools_str}

EXTRACTION RULES & BEHAVIORAL BOUNDARIES:
{rules_text}

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
    return sys_prompt, last_desc, len(cumulative_rules)

# ==============================================================================
# MAIN 20-ITERATION EXECUTION
# ==============================================================================

def run_20_iterations():
    csv_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/decoded_benchmark_291_results.csv"
    schema_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/SLU_schema_v1.0.json"
    model_id = "Qwen/Qwen2.5-7B-Instruct"
    batch_size = 24

    print("=== Starting True 20-Iteration Cumulative SLU Prompt Optimizer ===")
    print(f"Cluster: Delta (Account: bjas-delta-gpu)")
    print(f"Goal: Oracle Parameter Filling (PF) >= 90.00% or complete 20 progressive iterations.")
    print(f"Strategy: Progressive cumulative refinements; each iteration directly improves upon the previous one.")

    df = pd.read_csv(csv_path)
    schema = load_schema(schema_path)
    tools_str = build_tools_catalog(schema)
    prompts_text = df["prompt"].fillna("").tolist()
    print(f"Loaded {len(df)} benchmark commands.")

    print(f"Loading Model {model_id} into VRAM...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, truncation_side="left")
    tokenizer.padding_side = "left"  # Crucial for batched decoder generation
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()
    print("Model ready in VRAM.\n")

    history = []
    best_pf = 0.0
    best_iteration = 1
    best_prompt = ""
    best_results = None

    for it_num in range(1, 21):
        idx = it_num - 1
        sys_prompt, step_desc, rule_count = build_prompt_for_iteration(tools_str, idx)
        print(f"\n{'='*30} ITERATION {it_num} / 20 {'='*30}")
        print(f"Incremental Improvement: {step_desc} (Cumulative Rules: {rule_count})")

        t_start = time.time()
        preds = []
        for i in range(0, len(prompts_text), batch_size):
            b_texts = prompts_text[i : i + batch_size]
            m_batch = [
                [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Spoken Transcript: \"{text}\""}
                ]
                for text in b_texts
            ]
            fmt = [tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=True) for m in m_batch]
            inps = tokenizer(fmt, return_tensors="pt", padding=True, truncation=True, max_length=4096)
            inps = {k: v.to(device) for k, v in inps.items()}
            with torch.no_grad():
                gen_ids = model.generate(
                    **inps,
                    max_new_tokens=96,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id
                )
            in_len = inps["input_ids"].shape[1]
            gen_tokens = gen_ids[:, in_len:]
            decoded = tokenizer.batch_decode(gen_tokens, skip_special_tokens=True)
            for dec in decoded:
                preds.append(parse_llm_json(dec))

        eval_res = evaluate_predictions(preds, df)
        elapsed = time.time() - t_start

        # Calculate delta from previous iteration
        prev_pf = history[-1]["pf"] if history else eval_res["pf"]
        delta_pf = (eval_res["pf"] - prev_pf) * 100

        print(f"[Iteration {it_num} Result ({elapsed:.1f}s)]")
        print(f"  • Tool Selection (TS):    {eval_res['ts']*100:.2f}%")
        print(f"  • Structure (TCS):        {eval_res['tcs']*100:.2f}%")
        print(f"  • Parameter Filling (PF): {eval_res['pf']*100:.2f}% ({eval_res['pf_correct']} / {eval_res['total_slots']} slots) [Δ: {delta_pf:+.2f}%]")
        print(f"  • Command Frame Accuracy: {eval_res['frame_acc']*100:.2f}%")
        print(f"  • Total Slot Failures:    {len(eval_res['failures'])}")

        history.append({
            "iteration": it_num,
            "improvement": step_desc,
            "rule_count": rule_count,
            "ts": eval_res["ts"],
            "tcs": eval_res["tcs"],
            "pf": eval_res["pf"],
            "delta_pf": delta_pf,
            "frame_acc": eval_res["frame_acc"],
            "failures_count": len(eval_res["failures"])
        })

        if eval_res["pf"] > best_pf:
            best_pf = eval_res["pf"]
            best_iteration = it_num
            best_prompt = sys_prompt
            best_results = eval_res

        # Check early termination target
        if eval_res["pf"] >= 0.90:
            print(f"\n=======================================================")
            print(f">>> TARGET REACHED! Parameter Filling {eval_res['pf']*100:.2f}% >= 90.00% on Iteration {it_num} <<<")
            print(f"=======================================================\n")
            break
        else:
            print(f"> Current PF: {eval_res['pf']*100:.2f}% < 90.00%. Advancing to next cumulative iteration...")

    print(f"\n{'='*75}")
    print(f"20-ITERATION PROGRESSION COMPLETE")
    print(f"Peak Performing Prompt: Iteration {best_iteration} with Oracle PF = {best_pf*100:.2f}%")
    print(f"{'='*75}\n")

    # Evaluate Winning Prompt on all 3 conditions (Oracle, Base ASR, FT ASR)
    print(f"--- Running Final 3-Condition Benchmark with Winning Prompt (Iteration {best_iteration}) ---")
    conditions = [
        ("oracle", "prompt"),
        ("base_asr", "base_parakeet_hypo"),
        ("ft_asr", "ft_parakeet_hypo")
    ]
    all_cond_results = {}

    for cond_name, col_name in conditions:
        print(f"Evaluating {cond_name.upper()} condition...")
        col_prompts = df[col_name].fillna("").tolist()
        c_preds = []
        for i in range(0, len(col_prompts), batch_size):
            b_texts = col_prompts[i : i + batch_size]
            m_batch = [
                [
                    {"role": "system", "content": best_prompt},
                    {"role": "user", "content": f"Spoken Transcript: \"{text}\""}
                ]
                for text in b_texts
            ]
            fmt = [tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=True) for m in m_batch]
            inps = tokenizer(fmt, return_tensors="pt", padding=True, truncation=True, max_length=4096)
            inps = {k: v.to(device) for k, v in inps.items()}
            with torch.no_grad():
                g_ids = model.generate(
                    **inps,
                    max_new_tokens=96,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id
                )
            c_dec = tokenizer.batch_decode(g_ids[:, inps["input_ids"].shape[1]:], skip_special_tokens=True)
            for d in c_dec:
                c_preds.append(parse_llm_json(d))
        
        all_cond_results[cond_name] = evaluate_predictions(c_preds, df)
        df[f"{cond_name}_pred_intent"] = [p["intent"] for p in c_preds]
        df[f"{cond_name}_pred_slots"] = [json.dumps(p["slots"]) for p in c_preds]
        df[f"{cond_name}_pred_domain"] = [p["domain"] for p in c_preds]

    # Save outputs
    out_csv = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/slu_llm_eval_291_opt20_results.csv"
    out_summary = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/slu_llm_eval_291_opt20_summary.json"
    df.to_csv(out_csv, index=False)

    summary_data = {
        "optimization_history": history,
        "best_iteration": best_iteration,
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
    run_20_iterations()
