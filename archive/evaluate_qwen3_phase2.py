#!/usr/bin/env python3
"""
evaluate_qwen3_phase2.py
========================
Phase 2 SLU Evaluation Harness for Speech Accessibility Project (SAP).
Evaluates Qwen 3-8B on sampled benchmark (N=1108, ~3 speakers/prompt across 5 etiologies)
across 3 conditions:
  Condition 1: Oracle text
  Condition 2: Base Parakeet ASR hypothesis
  Condition 3: Fine-Tuned Parakeet ASR hypothesis

Computes:
  - TS, TCS, PF (Char-F1 >= 0.85), Command Frame Acc
  - ARR (Adaptation Recovery Rate)
  - Domain breakdown (10 domains)
  - Clinical Etiology breakdown (Stroke, Down Syndrome, ALS, Cerebral Palsy, Parkinson's)
  - Detailed error taxonomy dump (Intent errors, Missing slots, Value mismatches)
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
    if not text:
        return ""
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
            if not isinstance(slots, dict):
                slots = {}
            return {"domain": domain, "intent": intent, "slots": slots, "raw": raw_text}
    except Exception:
        pass

    intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', raw_text)
    domain_match = re.search(r'"domain"\s*:\s*"([^"]+)"', raw_text)
    intent = intent_match.group(1).strip().lower() if intent_match else "unknown"
    domain = domain_match.group(1).strip().lower() if domain_match else "unknown"
    return {"domain": domain, "intent": intent, "slots": {}, "raw": raw_text, "parse_error": True}

def build_system_prompt(schema_path: str) -> str:
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

    tools_str = "\n".join(tools_doc)

    sys_prompt = f"""You are the Spoken Language Understanding (SLU) agent for the Speech Accessibility Project (SAP).
Map each spoken voice command into a valid JSON tool call conforming to the 29-tool schema below.

CANONICAL TOOLS AND PARAMETERS:
{tools_str}

EXTRACTION RULES:
1. Strict Enum Adherence: If a parameter specifies allowed options in brackets [...], select strictly from that list. Do not use unlisted synonyms.
2. Base Noun Phrase Extraction: For entity span arguments, extract the core noun phrase without leading conversational prepositions (e.g., to, for, with) or possessive determiners (e.g., my, our).
3. Open-Vocabulary Fidelity: For open text spans, extract the exact spoken words without inventing unuttered information.
4. Minimal Slot Invariance: If a command does not mention a given parameter, omit that key from the 'slots' dictionary. Never invent unmentioned arguments.

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

def main():
    parser = argparse.ArgumentParser(description="Phase 2 Qwen3-8B SLU Evaluation")
    parser.add_argument("--csv_path", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/sampled_benchmark_1108.csv")
    parser.add_argument("--schema_path", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen3-8B")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--output_csv", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/qwen3_eval_1108_results.csv")
    parser.add_argument("--output_summary", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/qwen3_eval_1108_summary.json")
    args = parser.parse_args()

    print(f"=== Starting Phase 2 SLU Evaluation on Delta ===")
    print(f"Dataset:     {args.csv_path}")
    print(f"Model ID:    {args.model_id}")
    print(f"Batch Size:  {args.batch_size}")

    df = pd.read_csv(args.csv_path)
    print(f"Loaded {len(df)} benchmark instances across {df['speaker'].nunique()} speakers.")

    sys_prompt = build_system_prompt(args.schema_path)

    conditions = [
        ("oracle", "prompt"),
        ("base_asr", "base_parakeet_hypo"),
        ("ft_asr", "ft_parakeet_hypo")
    ]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    t0 = time.time()
    print(f"Loading Tokenizer & Model ({args.model_id})...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, padding_side="left", truncation_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
    model.eval()
    print(f"Model loaded in {time.time() - t0:.2f}s.")

    predictions = {}
    for cond_name, col_name in conditions:
        print(f"\n--- Running Condition: {cond_name.upper()} (column: {col_name}) ---")
        prompts = df[col_name].fillna("").tolist()

        formatted_inputs = []
        for p in prompts:
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f'Spoken command: "{p}"'}
            ]
            formatted_inputs.append(tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True))

        cond_preds = []
        t_start = time.time()
        for i in range(0, len(formatted_inputs), args.batch_size):
            batch_texts = formatted_inputs[i : i + args.batch_size]
            encoded = tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True, max_length=2048)
            input_ids = encoded["input_ids"].to(device)
            attention_mask = encoded["attention_mask"].to(device)

            with torch.no_grad():
                outputs = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=160,
                    temperature=0.0,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id
                )

            gen_tokens = outputs[:, input_ids.shape[1] :]
            decoded = tokenizer.batch_decode(gen_tokens, skip_special_tokens=True)

            for raw in decoded:
                parsed = parse_llm_json(raw)
                cond_preds.append(parsed)

            if (i // args.batch_size) % 5 == 0 or (i + args.batch_size) >= len(prompts):
                print(f"  Processed {min(i + args.batch_size, len(prompts))}/{len(prompts)} in {time.time() - t_start:.2f}s...")

        predictions[cond_name] = cond_preds
        print(f"Condition {cond_name.upper()} finished in {time.time() - t_start:.2f}s.")

    for cond_name in ["oracle", "base_asr", "ft_asr"]:
        df[f"{cond_name}_pred_intent"] = [p["intent"] for p in predictions[cond_name]]
        df[f"{cond_name}_pred_slots"] = [json.dumps(p["slots"]) for p in predictions[cond_name]]
        df[f"{cond_name}_pred_domain"] = [p["domain"] for p in predictions[cond_name]]

    print("\n" + "=" * 80)
    print("                     EVALUATING BENCHMARK METRICS")
    print("=" * 80)

    summary_results = {}
    detailed_failures = {}

    for cond_name, col_name in conditions:
        preds = predictions[cond_name]
        ts_correct = 0
        tcs_correct = 0
        pf_correct = 0
        total_slots = 0
        frame_correct = 0

        cond_failures = []
        domain_stats = {}
        etiology_stats = {}

        for idx, (p, (_, row)) in enumerate(zip(preds, df.iterrows())):
            gold_intent = str(row["intent"]).strip().lower()
            gold_domain = str(row["domain"]).strip().lower()
            etiology = str(row["etiology"]).strip()

            raw_slots = row.get("slots", "{}")
            gold_slots = json.loads(raw_slots) if isinstance(raw_slots, str) and raw_slots.strip() else {}

            pred_intent = p["intent"]
            pred_domain = p["domain"]
            pred_slots = p["slots"]

            is_ts = (pred_intent == gold_intent)
            if is_ts: ts_correct += 1

            is_tcs = (not p.get("parse_error", False) and pred_domain not in ["unknown", "error", ""])
            if is_tcs: tcs_correct += 1

            slots_all_ok = True
            for k, v in gold_slots.items():
                total_slots += 1
                norm_g = normalize_text(str(v))
                norm_p = normalize_text(str(pred_slots.get(k, "")))

                matched = (norm_g == norm_p) or (norm_g != "" and compute_char_f1(norm_g, norm_p) >= 0.85)
                if matched:
                    pf_correct += 1
                else:
                    slots_all_ok = False
                    cond_failures.append({
                        "gold_id": row["gold_id"],
                        "wav": row["wav"],
                        "speaker": row["speaker"],
                        "etiology": etiology,
                        "prompt": row["prompt"],
                        "asr_input": row[col_name],
                        "gold_intent": gold_intent,
                        "pred_intent": pred_intent,
                        "slot": k,
                        "gold_val": v,
                        "pred_val": pred_slots.get(k, None),
                        "type": "Intent Mismatch" if not is_ts else ("Missing Slot" if k not in pred_slots else "Value Mismatch")
                    })

            is_frame = is_ts and is_tcs and slots_all_ok
            if is_frame: frame_correct += 1

            # Domain stats
            if gold_domain not in domain_stats:
                domain_stats[gold_domain] = {"total": 0, "frame": 0, "ts": 0}
            domain_stats[gold_domain]["total"] += 1
            if is_frame: domain_stats[gold_domain]["frame"] += 1
            if is_ts: domain_stats[gold_domain]["ts"] += 1

            # Etiology stats
            if etiology not in etiology_stats:
                etiology_stats[etiology] = {"total": 0, "frame": 0, "ts": 0}
            etiology_stats[etiology]["total"] += 1
            if is_frame: etiology_stats[etiology]["frame"] += 1
            if is_ts: etiology_stats[etiology]["ts"] += 1

        n_samples = len(df)
        ts_pct = round(ts_correct / n_samples * 100, 2)
        tcs_pct = round(tcs_correct / n_samples * 100, 2)
        pf_pct = round(pf_correct / total_slots * 100, 2) if total_slots > 0 else 0.0
        frame_pct = round(frame_correct / n_samples * 100, 2)

        summary_results[cond_name] = {
            "TS": ts_pct,
            "TCS": tcs_pct,
            "PF": pf_pct,
            "Frame_Acc": frame_pct,
            "Total_Samples": n_samples,
            "Total_Slots": total_slots,
            "Domains": {d: {"Frame_Acc": round(v["frame"]/v["total"]*100, 2), "TS": round(v["ts"]/v["total"]*100, 2)} for d, v in domain_stats.items()},
            "Etiologies": {e: {"Frame_Acc": round(v["frame"]/v["total"]*100, 2), "TS": round(v["ts"]/v["total"]*100, 2)} for e, v in etiology_stats.items()}
        }
        detailed_failures[cond_name] = cond_failures

    # Compute ARR
    o_acc = summary_results["oracle"]["Frame_Acc"]
    b_acc = summary_results["base_asr"]["Frame_Acc"]
    f_acc = summary_results["ft_asr"]["Frame_Acc"]
    arr = round(((f_acc - b_acc) / (o_acc - b_acc)) * 100, 2) if (o_acc - b_acc) > 0 else 0.0
    summary_results["ARR"] = arr
    summary_results["failures"] = detailed_failures

    # Save results
    df.to_csv(args.output_csv, index=False)
    with open(args.output_summary, "w") as f:
        json.dump(summary_results, f, indent=2)

    print("\n" + "=" * 80)
    print("                    FINAL BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Condition 1 (Oracle):   TS: {summary_results['oracle']['TS']}% | TCS: {summary_results['oracle']['TCS']}% | PF: {summary_results['oracle']['PF']}% | Frame: {summary_results['oracle']['Frame_Acc']}%")
    print(f"Condition 2 (Base ASR): TS: {summary_results['base_asr']['TS']}% | TCS: {summary_results['base_asr']['TCS']}% | PF: {summary_results['base_asr']['PF']}% | Frame: {summary_results['base_asr']['Frame_Acc']}%")
    print(f"Condition 3 (FT ASR):   TS: {summary_results['ft_asr']['TS']}% | TCS: {summary_results['ft_asr']['TCS']}% | PF: {summary_results['ft_asr']['PF']}% | Frame: {summary_results['ft_asr']['Frame_Acc']}%")
    print(f"--> Adaptation Recovery Rate (ARR): {arr}%")
    print(f"Saved CSV:     {args.output_csv}")
    print(f"Saved Summary: {args.output_summary}")

if __name__ == "__main__":
    main()
