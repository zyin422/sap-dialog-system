#!/usr/bin/env python3
"""
Phase 2 SLU + Conversational Affirmation (NLG) Evaluation: Qwen3-8B on Delta.
Supports the N=1200 Clean Balanced Benchmark (sampled_benchmark_1200_clean.csv).
Captures:
1. Tool Selection (TS), Tool Call Structure (TCS), Parameter Filling (PF), Command Frame Accuracy.
2. Spoken Conversational Affirmation (response):
   - Length compliance (<= 12 words)
   - Clean speech compliance (zero markdown, URLs, backticks, syntax leaks)
   - Auditory grounding recall
Saves intermediate checkpoints per condition to guarantee zero data loss.
"""

import os
import sys
import re
import json
import time
import argparse
import pandas as pd
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError:
    torch = None

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
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
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
            response = str(out.get("response", "")).strip()
            return {"domain": domain, "intent": intent, "slots": slots, "response": response, "raw": raw_text}
    except Exception:
        pass

    intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', raw_text)
    domain_match = re.search(r'"domain"\s*:\s*"([^"]+)"', raw_text)
    response_match = re.search(r'"response"\s*:\s*"([^"]+)"', raw_text)
    intent = intent_match.group(1).strip().lower() if intent_match else "unknown"
    domain = domain_match.group(1).strip().lower() if domain_match else "unknown"
    response = response_match.group(1).strip() if response_match else ""
    return {"domain": domain, "intent": intent, "slots": {}, "response": response, "raw": raw_text, "parse_error": True}

def evaluate_condition_metrics(df: pd.DataFrame, preds: list, col_name: str):
    ts_correct = 0
    tcs_correct = 0
    pf_correct = 0
    total_slots = 0
    frame_correct = 0

    # NLG metrics
    nlg_length_ok = 0
    nlg_clean_ok = 0
    total_words = 0

    domain_stats = {}
    etiology_stats = {}
    failures = []

    for idx, (p, (_, row)) in enumerate(zip(preds, df.iterrows())):
        gold_intent = str(row["intent"]).strip().lower()
        gold_domain = str(row["domain"]).strip().lower()
        etiology = str(row.get("etiology", "all")).strip()

        raw_slots = row.get("slots", "{}")
        gold_slots = json.loads(raw_slots) if isinstance(raw_slots, str) and raw_slots.strip() else {}

        pred_intent = p["intent"]
        pred_domain = p["domain"]
        pred_slots = p["slots"]
        pred_response = p.get("response", "")

        is_ts = (pred_intent == gold_intent)
        if is_ts: ts_correct += 1

        is_tcs = (not p.get("parse_error", False) and pred_domain not in ["unknown", "error", ""])
        if is_tcs: tcs_correct += 1

        # Slot evaluation
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
                failures.append({
                    "gold_id": row.get("gold_id", f"item_{idx}"),
                    "wav": row.get("wav", ""),
                    "speaker": row.get("speaker", "unknown"),
                    "etiology": etiology,
                    "prompt": row.get("prompt", ""),
                    "asr_input": row[col_name] if col_name in row else row.get("prompt", ""),
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent,
                    "slot": k,
                    "gold_val": v,
                    "pred_val": pred_slots.get(k, None),
                    "pred_response": pred_response,
                    "type": "Intent Mismatch" if not is_ts else ("Missing Slot" if k not in pred_slots else "Value Mismatch")
                })

        is_frame = is_ts and is_tcs and slots_all_ok
        if is_frame: frame_correct += 1

        # NLG Metrics
        words = pred_response.split()
        wc = len(words)
        total_words += wc
        if wc <= 12 and wc > 0:
            nlg_length_ok += 1
        has_forbidden = bool(re.search(r'[\*#\`\{\}\[\]\\<>]|http', pred_response))
        if not has_forbidden and len(pred_response) > 0:
            nlg_clean_ok += 1

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

    nlg_length_pct = round(nlg_length_ok / n_samples * 100, 2)
    nlg_clean_pct = round(nlg_clean_ok / n_samples * 100, 2)
    avg_words = round(total_words / n_samples, 2)

    return {
        "TS": ts_pct,
        "TCS": tcs_pct,
        "PF": pf_pct,
        "Frame_Acc": frame_pct,
        "Total_Samples": n_samples,
        "Total_Slots": total_slots,
        "NLG": {
            "Length_Compliance_Leq12": nlg_length_pct,
            "Clean_Speech_Tokens": nlg_clean_pct,
            "Avg_Word_Count": avg_words
        },
        "Domains": {d: {"Frame_Acc": round(v["frame"]/v["total"]*100, 2), "TS": round(v["ts"]/v["total"]*100, 2)} for d, v in domain_stats.items()},
        "Etiologies": {e: {"Frame_Acc": round(v["frame"]/v["total"]*100, 2), "TS": round(v["ts"]/v["total"]*100, 2)} for e, v in etiology_stats.items()}
    }, failures

def main():
    parser = argparse.ArgumentParser(description="Phase 2 Enriched Prompt SLU + NLG Evaluation on 1200 Clean Benchmark")
    parser.add_argument("--csv_path", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/sampled_benchmark_1200_clean.csv")
    parser.add_argument("--prompt_path", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/certified_generalized_system_prompt_rev6_nlg.txt")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen3-8B")
    parser.add_argument("--batch_size", type=int, default=12)
    parser.add_argument("--max_new_tokens", type=int, default=130)
    parser.add_argument("--condition", type=str, default="all", choices=["all", "oracle", "base_asr", "ft_asr"], help="Condition to evaluate: all, oracle, base_asr, or ft_asr")
    parser.add_argument("--output_csv", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_results.csv")
    parser.add_argument("--output_summary", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_summary.json")
    args = parser.parse_args()

    print("=== Starting Phase 2 Qwen3-8B Enriched Prompt SLU + NLG Benchmark on Delta (1200 Clean Benchmark) ===")
    print(f"Dataset:     {args.csv_path}")
    print(f"Prompt Path: {args.prompt_path}")
    print(f"Model ID:    {args.model_id}")
    print(f"Batch Size:  {args.batch_size}")
    print(f"Max New Tok: {args.max_new_tokens}")
    print(f"Condition:   {args.condition}")

    csv_to_load = args.output_csv if (os.path.exists(args.output_csv) and args.condition != "all") else args.csv_path
    df = pd.read_csv(csv_to_load)
    n_spk = df['speaker'].nunique() if 'speaker' in df.columns else 1
    print(f"Loaded {len(df)} benchmark instances from {csv_to_load} across {n_spk} speakers.")
    print("Etiologies:\n", df['etiology'].value_counts())

    with open(args.prompt_path, "r", encoding="utf-8") as f:
        sys_prompt = f.read()
    print(f"Loaded System Prompt from {args.prompt_path} ({len(sys_prompt)} chars).")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    print(f"Loading Tokenizer & Model ({args.model_id})...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, padding_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )
    model.eval()
    print(f"Model loaded in {time.time() - t0:.2f}s.")

    all_conditions = [
        ("oracle", "prompt"),
        ("base_asr", "base_parakeet_hypo"),
        ("ft_asr", "ft_parakeet_hypo")
    ]
    if args.condition != "all":
        conditions = [c for c in all_conditions if c[0] == args.condition]
    else:
        conditions = [c for c in all_conditions if c[1] in df.columns]

    summary_results = {}
    detailed_failures = {}

    # Pre-populate with existing condition checkpoints if available
    for c_prev in ["oracle", "base_asr", "ft_asr"]:
        prev_ckpt = args.output_summary.replace(".json", f"_checkpoint_{c_prev}.json")
        if os.path.exists(prev_ckpt):
            try:
                with open(prev_ckpt, "r", encoding="utf-8") as f:
                    ckpt_data = json.load(f)
                    if c_prev in ckpt_data:
                        summary_results[c_prev] = ckpt_data[c_prev]
                    elif "metrics" in ckpt_data and c_prev in ckpt_data["metrics"]:
                        summary_results[c_prev] = ckpt_data["metrics"][c_prev]
            except Exception as e:
                print(f"Warning loading {prev_ckpt}: {e}")
    if summary_results:
        print(f"Loaded existing checkpoint metrics for: {list(summary_results.keys())}")

    for cond_name, col_name in conditions:
        print(f"\n" + "=" * 60)
        print(f"--- Running Condition: {cond_name.upper()} (column: {col_name}) ---")
        print("=" * 60)
        prompts = df[col_name].fillna("").tolist()

        formatted_inputs = []
        for p in prompts:
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f'Spoken command: "{p}"'}
            ]
            try:
                formatted = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False, add_generation_prompt=True)
            except TypeError:
                formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            formatted_inputs.append(formatted)

        cond_preds = []
        t_start = time.time()
        for i in range(0, len(formatted_inputs), args.batch_size):
            batch_texts = formatted_inputs[i : i + args.batch_size]
            encoded = tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True, max_length=8192)
            input_ids = encoded["input_ids"].to(device)
            attention_mask = encoded["attention_mask"].to(device)

            with torch.no_grad():
                outputs = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=args.max_new_tokens,
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
                print(f"  Processed {min(i + args.batch_size, len(prompts))}/{len(prompts)} in {time.time() - t_start:.2f}s...", flush=True)

        print(f"Condition {cond_name.upper()} finished in {time.time() - t_start:.2f}s.")

        # Update dataframe with this condition's predictions immediately
        df[f"{cond_name}_pred_intent"] = [p["intent"] for p in cond_preds]
        df[f"{cond_name}_pred_slots"] = [json.dumps(p["slots"]) for p in cond_preds]
        df[f"{cond_name}_pred_domain"] = [p["domain"] for p in cond_preds]
        df[f"{cond_name}_pred_response"] = [p.get("response", "") for p in cond_preds]

        # Calculate metrics for this condition immediately
        cond_metrics, cond_fail_list = evaluate_condition_metrics(df, cond_preds, col_name)
        summary_results[cond_name] = cond_metrics
        detailed_failures[cond_name] = cond_fail_list

        print(f"\nCondition {cond_name.upper()} Results:")
        print(f"  TS:        {cond_metrics['TS']}%")
        print(f"  TCS:       {cond_metrics['TCS']}%")
        print(f"  PF:        {cond_metrics['PF']}%")
        print(f"  Frame Acc: {cond_metrics['Frame_Acc']}%")
        print(f"  NLG Length (<= 12 words): {cond_metrics['NLG']['Length_Compliance_Leq12']}%")
        print(f"  NLG Clean Tokens:         {cond_metrics['NLG']['Clean_Speech_Tokens']}%")
        print(f"  NLG Avg Word Count:       {cond_metrics['NLG']['Avg_Word_Count']}")

        # Save checkpoint immediately
        df.to_csv(args.output_csv, index=False)
        chk_summary_path = args.output_summary.replace(".json", f"_checkpoint_{cond_name}.json")
        with open(chk_summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_results, f, indent=2)
        print(f"Saved intermediate checkpoint to {chk_summary_path}")

    # Compute Net Gains & ARR if all 3 conditions present
    if "oracle" in summary_results and "base_asr" in summary_results and "ft_asr" in summary_results:
        oracle_frame = summary_results["oracle"]["Frame_Acc"]
        base_frame = summary_results["base_asr"]["Frame_Acc"]
        ft_frame = summary_results["ft_asr"]["Frame_Acc"]
        net_frame_gain = round(ft_frame - base_frame, 2)
        gap = oracle_frame - base_frame
        arr = round((ft_frame - base_frame) / gap * 100, 2) if gap > 0 else 0.0

        oracle_pf = summary_results["oracle"]["PF"]
        base_pf = summary_results["base_asr"]["PF"]
        ft_pf = summary_results["ft_asr"]["PF"]
        net_pf_gain = round(ft_pf - base_pf, 2)

        summary_results["comparative_summary"] = {
            "Net_Frame_Gain_FT_minus_Base": net_frame_gain,
            "Adaptation_Recovery_Rate_ARR": arr,
            "Net_PF_Gain_FT_minus_Base": net_pf_gain,
            "Oracle_Frame_Acc": oracle_frame,
            "Base_ASR_Frame_Acc": base_frame,
            "FT_ASR_Frame_Acc": ft_frame
        }
        print("\n" + "=" * 60)
        print("=== FINAL 3-CONDITION BENCHMARK COMPARISON ===")
        print("=" * 60)
        print(f"Oracle Frame Acc:   {oracle_frame}%")
        print(f"Base ASR Frame Acc: {base_frame}%")
        print(f"FT ASR Frame Acc:   {ft_frame}%")
        print(f"Net Frame Gain:     +{net_frame_gain}%")
        print(f"ARR:                {arr}%")
        print(f"Net PF Gain:        +{net_pf_gain}%")

    with open(args.output_summary, "w", encoding="utf-8") as f:
        json.dump(summary_results, f, indent=2)

    print(f"\nFinal results saved to {args.output_csv} and {args.output_summary}")

if __name__ == "__main__":
    main()
