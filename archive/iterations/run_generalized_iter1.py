#!/usr/bin/env python3
"""
Generalized SLU Prompt Baseline — Iteration 1
Evaluates the clean, tool-agnostic universal prompt with official schema parameter descriptions.
Outputs detailed evaluation metrics and granular failure mode breakdown.
"""

import os
import sys
import time
import json
import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def load_schema(schema_path: str):
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_tools_catalog_iter1(schema: dict) -> str:
    """Builds the canonical tools catalog using official parameter descriptions."""
    tools_doc = []
    for t in schema["tools"]:
        props = t.get("parameters", {}).get("properties", {})
        param_strs = []
        for p_name, p_info in props.items():
            desc = p_info.get("description", "")
            if "enum" in p_info:
                param_strs.append(f"{p_name}: {p_info['enum']}")
            elif desc:
                param_strs.append(f"{p_name} ({desc})")
            else:
                param_strs.append(f"{p_name} (str)")
        params_formatted = ", ".join(param_strs)
        tools_doc.append(f"- {t['name']} (domain: {t['domain']}): {params_formatted}")
    return "\n".join(tools_doc)

def build_prompt_iter1(tools_str: str) -> str:
    rules = """UNIVERSAL EXTRACTION RULES:
1. Closed Tool Catalog: The 'intent' MUST be selected strictly from the 29 canonical tool names listed above. Never invent, modify, or substitute unlisted tool names.
2. Closed Enum Adherence: When a parameter declares a list of allowable options in brackets [...], select strictly from that list. If an utterance uses a synonymous phrasing (e.g. cancelling/dropping vs deleting), select the canonical enum that represents that semantic function.
3. Semantic Role Alignment: Assign extracted spans to parameters whose descriptive definition matches the semantic entity. Specifically, assign temporal and calendar expressions to date/time parameters, geographic entities to location parameters, and core action verbs to action parameters.
4. Minimal Slot Invariance: Extract only parameters that are explicitly mentioned or directly implied in the user utterance. If a parameter is not mentioned, omit that key from the 'slots' dictionary. Never invent default or unuttered values.
5. Constituent Span Preservation: For open-vocabulary text parameters, extract the complete descriptive noun phrase or clause constituent (preserving modifying adjectives, compound elements, and trailing prepositional qualifiers describing beneficiary or purpose) rather than truncating to an isolated head noun.
6. Verbatim Open-Text Hygiene: For free-text queries, titles, and search terms, extract the raw spoken words without appending unuttered trailing punctuation marks ('?', '.') and without enclosing phrases in quotation marks unless spoken.
7. Generic Concept Fallback: When an utterance specifies a generic category noun (such as an event type or list type) without a proper name or title, retain that generic noun in the corresponding naming/title parameter rather than omitting the slot."""

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
                    "pred_val": None,
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent
                })
            elif k not in pred_slots:
                cmd_frame_perfect = False
                failures.append({
                    "id": row.get("gold_id", idx),
                    "prompt": row.get("prompt", ""),
                    "reason": "Missing Slot",
                    "slot": k,
                    "gold_val": v,
                    "pred_val": None,
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent
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
                        "pred_val": pred_slots[k],
                        "gold_intent": gold_intent,
                        "pred_intent": pred_intent
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

def main():
    csv_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/decoded_benchmark_291_results.csv"
    schema_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/SLU_schema_v1.0.json"
    model_id = "Qwen/Qwen2.5-7B-Instruct"
    batch_size = 24

    print("=== Running Generalized SLU Prompt Baseline (Iteration 1) ===")
    df = pd.read_csv(csv_path)
    schema = load_schema(schema_path)
    tools_str = build_tools_catalog_iter1(schema)
    sys_prompt = build_prompt_iter1(tools_str)

    print(f"System Prompt Length: {len(sys_prompt)} chars (~{len(sys_prompt)//4} tokens)")

    print(f"Loading Model {model_id} into VRAM...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, truncation_side="left")
    tokenizer.padding_side = "left"
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

    prompts_text = df["prompt"].fillna("").tolist()
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

    elapsed = time.time() - t_start
    eval_res = evaluate_predictions(preds, df)

    print(f"\n{'='*70}")
    print(f"ITERATION 1 EVALUATION RESULTS ({elapsed:.1f}s)")
    print(f"{'='*70}")
    print(f"  • Tool Selection (TS):    {eval_res['ts']*100:.2f}% ({int(eval_res['ts']*len(df))} / {len(df)} commands)")
    print(f"  • Structure (TCS):        {eval_res['tcs']*100:.2f}%")
    print(f"  • Parameter Filling (PF): {eval_res['pf']*100:.2f}% ({eval_res['pf_correct']} / {eval_res['total_slots']} slots)")
    print(f"  • Command Frame Accuracy: {eval_res['frame_acc']*100:.2f}% ({int(eval_res['frame_acc']*len(df))} / {len(df)} commands)")
    print(f"  • Total Slot Failures:    {len(eval_res['failures'])}")
    print(f"{'='*70}\n")

    # Save detailed outputs
    out_dir = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291"
    out_summary = os.path.join(out_dir, "iter1_generalized_summary.json")
    out_csv = os.path.join(out_dir, "iter1_generalized_predictions.csv")

    df["iter1_pred_intent"] = [p["intent"] for p in preds]
    df["iter1_pred_slots"] = [json.dumps(p["slots"]) for p in preds]
    df["iter1_pred_domain"] = [p["domain"] for p in preds]
    df.to_csv(out_csv, index=False)

    summary_data = {
        "iteration": 1,
        "ts": eval_res["ts"],
        "tcs": eval_res["tcs"],
        "pf": eval_res["pf"],
        "frame_acc": eval_res["frame_acc"],
        "pf_correct": eval_res["pf_correct"],
        "total_slots": eval_res["total_slots"],
        "failures_count": len(eval_res["failures"]),
        "failures": eval_res["failures"]
    }
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Saved predictions to: {out_csv}")
    print(f"Saved failure analysis to: {out_summary}")

if __name__ == "__main__":
    main()
