#!/usr/bin/env python3
"""
evaluate_slu_llm.py
===================
End-to-end Stage 2 SLU Evaluation Harness for the Speech Accessibility Project (SAP).
Evaluates Qwen 2.5 on 291 benchmark commands across 3 conditions:
  Condition 1: Oracle text (clean ground-truth prompt)
  Condition 2: Base Parakeet ASR hypothesis (WER: 28.15%)
  Condition 3: Fine-Tuned Parakeet ASR hypothesis (WER: 10.70%)

Produces:
  - Tool Selection (TS / Intent Accuracy)
  - Tool Call Structure (TCS Validity)
  - Parameter Filling (PF / Semantic Slot Accuracy)
  - Command Frame Accuracy (Strict End-to-End Success)
  - Downstream Degradation Gap (Delta_ASR)
  - Domain Adaptation Recovery Rate (%)
  - Semantic Error Correction Rate (SECR)
  - Over-Correction / Hallucination Rate (ODR)
  - Domain-by-Domain breakdown table across all 10 schema domains.
"""

import os
import sys
import json
import re
import time
import argparse
import pathlib
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
    # Strip markdown fences if present
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
            # Normalize keys
            domain = str(out.get("domain", "")).strip().lower()
            intent = str(out.get("intent", "")).strip().lower()
            slots = out.get("slots", {})
            if not isinstance(slots, dict):
                slots = {}
            return {"domain": domain, "intent": intent, "slots": slots, "raw": raw_text}
    except Exception:
        pass
    
    # Fallback heuristic regex
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
    parser = argparse.ArgumentParser(description="Stage 2 SLU LLM Benchmark Evaluation")
    parser.add_argument("--csv_path", type=str, default="/work/hdd/bedl/zyin2/dev_audio/benchmark_291/decoded_benchmark_291_results.csv")
    parser.add_argument("--schema_path", type=str, default="/work/hdd/bedl/zyin2/dev_audio/benchmark_291/SLU_schema_v1.0.json")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--output_csv", type=str, default="/work/hdd/bedl/zyin2/dev_audio/benchmark_291/slu_llm_eval_291_results.csv")
    parser.add_argument("--output_summary", type=str, default="/work/hdd/bedl/zyin2/dev_audio/benchmark_291/slu_llm_eval_291_summary.json")
    args = parser.parse_args()

    print(f"=== Starting SAP Stage 2 SLU LLM Evaluation ===")
    print(f"Input Data:  {args.csv_path}")
    print(f"Model ID:    {args.model_id}")
    print(f"Batch Size:  {args.batch_size}")

    df = pd.read_csv(args.csv_path)
    print(f"Loaded {len(df)} benchmark commands.")

    sys_prompt = build_system_prompt(args.schema_path)

    # Prepare inputs across 3 conditions
    # condition: (name, column_name)
    conditions = [
        ("oracle", "prompt"),
        ("base_asr", "base_parakeet_hypo"),
        ("ft_asr", "ft_parakeet_hypo")
    ]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    t0 = time.time()
    print(f"Loading Tokenizer & Model: {args.model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, padding_side="left", truncation_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto"
    )
    model.eval()
    print(f"Model successfully loaded in {time.time() - t0:.2f}s.")

    # Storage for predictions: condition -> list of parsed dicts
    predictions = {"oracle": [], "base_asr": [], "ft_asr": []}

    for cond_name, col_name in conditions:
        print(f"\n--- Running Inference for Condition: {cond_name.upper()} (Column: {col_name}) ---")
        t_start = time.time()
        cond_preds = []

        prompts = df[col_name].fillna("").tolist()

        # Batch inference
        for i in range(0, len(prompts), args.batch_size):
            batch_texts = prompts[i : i + args.batch_size]
            messages_batch = [
                [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Spoken Transcript: \"{text}\""}
                ]
                for text in batch_texts
            ]

            formatted_prompts = [
                tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
                for m in messages_batch
            ]

            inputs = tokenizer(formatted_prompts, return_tensors="pt", padding=True, truncation=True, max_length=4096)
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=128,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id
                )

            # Slice off input tokens
            input_lens = inputs["input_ids"].shape[1]
            generated_tokens = generated_ids[:, input_lens:]
            decoded_outputs = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)

            if i == 0:
                print(f"  [Sample 0 Raw Generation]: {repr(decoded_outputs[0])}")

            for dec in decoded_outputs:
                parsed = parse_llm_json(dec)
                cond_preds.append(parsed)

            if (i // args.batch_size) % 3 == 0 or (i + args.batch_size) >= len(prompts):
                print(f"  Processed {min(i + args.batch_size, len(prompts))}/{len(prompts)} utterances in {time.time() - t_start:.2f}s...")

        predictions[cond_name] = cond_preds
        print(f"Completed {cond_name.upper()} in {time.time() - t_start:.2f}s.")

    # Attach predictions to dataframe
    for cond_name in ["oracle", "base_asr", "ft_asr"]:
        df[f"{cond_name}_pred_intent"] = [p["intent"] for p in predictions[cond_name]]
        df[f"{cond_name}_pred_slots"] = [json.dumps(p["slots"]) for p in predictions[cond_name]]
        df[f"{cond_name}_pred_domain"] = [p["domain"] for p in predictions[cond_name]]

    # Compute Metrics
    print("\n" + "=" * 75)
    print("                    SCORING DOWNSTREAM SLU PERFORMANCE")
    print("=" * 75)

    summary_results = {}
    domain_breakdown = {}

    for cond_name in ["oracle", "base_asr", "ft_asr"]:
        preds = predictions[cond_name]
        ts_correct = 0
        tcs_correct = 0
        pf_correct = 0
        total_slots = 0
        frame_correct = 0

        # Slot error correction stats
        secr_eligible = 0  # ASR corrupted the extractive slot
        secr_repaired = 0  # LLM restored canonical slot
        extraneous_slots = 0

        for idx, (p, (_, row)) in enumerate(zip(preds, df.iterrows())):
            gold_intent = str(row["intent"]).strip().lower()
            gold_domain = str(row["domain"]).strip().lower()
            
            raw_slots = row.get("slots", "{}")
            gold_slots = json.loads(raw_slots) if isinstance(raw_slots, str) and raw_slots.strip() else {}

            pred_intent = p["intent"]
            pred_domain = p["domain"]
            pred_slots = p["slots"]

            # 1. Tool Selection (TS)
            is_ts = (pred_intent == gold_intent)
            if is_ts:
                ts_correct += 1

            # 2. Tool Call Structure (TCS)
            is_tcs = (not p.get("parse_error", False) and pred_domain not in ["unknown", "error", ""])
            if is_tcs:
                tcs_correct += 1

            # 3. Parameter Filling (PF)
            all_slots_matched = True
            for k, v in gold_slots.items():
                total_slots += 1
                gold_val_str = str(v)
                pred_val_str = str(pred_slots.get(k, ""))

                norm_g = normalize_text(gold_val_str)
                norm_p = normalize_text(pred_val_str)

                slot_matched = (norm_g == norm_p) or (norm_g != "" and compute_char_f1(norm_g, norm_p) >= 0.85)
                if slot_matched:
                    pf_correct += 1
                else:
                    all_slots_matched = False

                # SECR check for ASR conditions
                if cond_name in ["base_asr", "ft_asr"]:
                    asr_text = normalize_text(row["base_parakeet_hypo"] if cond_name == "base_asr" else row["ft_parakeet_hypo"])
                    if norm_g not in asr_text:
                        secr_eligible += 1
                        if slot_matched:
                            secr_repaired += 1

            # Extraneous slots check (ODR)
            for k in pred_slots:
                if k not in gold_slots:
                    extraneous_slots += 1

            # 4. Strict Command Frame Accuracy
            if is_ts and is_tcs and all_slots_matched:
                frame_correct += 1

        n = len(df)
        ts_acc = round(ts_correct / n, 4)
        tcs_acc = round(tcs_correct / n, 4)
        pf_acc = round(pf_correct / total_slots, 4) if total_slots > 0 else 1.0
        frame_acc = round(frame_correct / n, 4)
        secr = round(secr_repaired / secr_eligible, 4) if secr_eligible > 0 else 0.0

        summary_results[cond_name] = {
            "num_utterances": n,
            "tool_selection_acc": ts_acc,
            "tool_call_struct_validity": tcs_acc,
            "parameter_filling_acc": pf_acc,
            "command_frame_acc": frame_acc,
            "secr": secr,
            "secr_eligible_slots": secr_eligible,
            "secr_repaired_slots": secr_repaired,
            "extraneous_slots_count": extraneous_slots
        }

    # Comparative causal metrics
    oracle_frame = summary_results["oracle"]["command_frame_acc"]
    base_frame = summary_results["base_asr"]["command_frame_acc"]
    ft_frame = summary_results["ft_asr"]["command_frame_acc"]

    delta_base = round(oracle_frame - base_frame, 4)
    delta_ft = round(oracle_frame - ft_frame, 4)
    recovery_rate = round(((ft_frame - base_frame) / (oracle_frame - base_frame)) * 100, 2) if (oracle_frame - base_frame) > 0 else 0.0

    summary_results["comparative"] = {
        "degradation_gap_base": delta_base,
        "degradation_gap_ft": delta_ft,
        "adaptation_recovery_rate_pct": recovery_rate,
        "net_frame_accuracy_gain": round(ft_frame - base_frame, 4)
    }

    # Domain Breakdown
    for domain in sorted(df["domain"].unique()):
        dom_df = df[df["domain"] == domain]
        dom_summary = {}
        for c in ["oracle", "base_asr", "ft_asr"]:
            c_correct = 0
            for _, r in dom_df.iterrows():
                g_intent = str(r["intent"]).strip().lower()
                p_intent = str(r[f"{c}_pred_intent"]).strip().lower()
                g_slots = json.loads(r["slots"]) if isinstance(r["slots"], str) and r["slots"].strip() else {}
                p_slots = json.loads(r[f"{c}_pred_slots"]) if isinstance(r[f"{c}_pred_slots"], str) else {}
                
                slot_ok = True
                for k, v in g_slots.items():
                    if compute_char_f1(normalize_text(str(v)), normalize_text(str(p_slots.get(k, "")))) < 0.85:
                        slot_ok = False
                        break
                if g_intent == p_intent and slot_ok:
                    c_correct += 1
            dom_summary[f"{c}_frame_acc"] = round(c_correct / len(dom_df), 4)
        domain_breakdown[domain] = {
            "count": len(dom_df),
            "oracle": dom_summary["oracle_frame_acc"],
            "base_asr": dom_summary["base_asr_frame_acc"],
            "ft_asr": dom_summary["ft_asr_frame_acc"],
            "gain": round(dom_summary["ft_asr_frame_acc"] - dom_summary["base_asr_frame_acc"], 4)
        }
    summary_results["domain_breakdown"] = domain_breakdown

    # Print Table
    print(f"{'Condition':<12} | {'TS (Intent)':<12} | {'TCS (Syntax)':<12} | {'PF (Slots)':<12} | {'Frame Acc (E2E)':<16} | {'SECR (Recovery)':<15}")
    print("-" * 88)
    for c in ["oracle", "base_asr", "ft_asr"]:
        res = summary_results[c]
        secr_str = f"{res['secr']*100:.1f}% ({res['secr_repaired_slots']}/{res['secr_eligible_slots']})" if c != "oracle" else "N/A"
        print(f"{c.upper():<12} | {res['tool_selection_acc']*100:>10.2f}% | {res['tool_call_struct_validity']*100:>10.2f}% | {res['parameter_filling_acc']*100:>10.2f}% | {res['command_frame_acc']*100:>14.2f}% | {secr_str:>15}")
    print("-" * 88)
    print(f"Downstream ASR Degradation Gap (Base): -{delta_base*100:.2f}%")
    print(f"Downstream ASR Degradation Gap (FT):   -{delta_ft*100:.2f}%")
    print(f"Domain Adaptation Recovery Rate:       {recovery_rate:.2f}%")
    print(f"Net End-to-End Success Gain:          +{summary_results['comparative']['net_frame_accuracy_gain']*100:.2f}%\n")

    print(f"{'Domain':<18} | {'N':<4} | {'Oracle':<8} | {'Base ASR':<10} | {'FT ASR':<8} | {'Gain':<8}")
    print("-" * 65)
    for dom, v in domain_breakdown.items():
        print(f"{dom:<18} | {v['count']:<4} | {v['oracle']*100:>6.1f}% | {v['base_asr']*100:>8.1f}% | {v['ft_asr']*100:>6.1f}% | {v['gain']*100:>+6.1f}%")
    print("=" * 75 + "\n")

    # Save to disk
    df.to_csv(args.output_csv, index=False)
    with open(args.output_summary, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, indent=2)

    print(f"[Success] Detailed predictions saved to: {args.output_csv}")
    print(f"[Success] Metric summary saved to:       {args.output_summary}")

if __name__ == "__main__":
    main()
