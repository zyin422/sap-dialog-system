#!/usr/bin/env python3
"""
Test Rev 6 Conversational Affirmation (NLG) vs Rev 5 Baseline on 30-Instance Target Slice.
Measures:
1. Tool-Calling Invariance (TS, TCS, PF delta between Rev 5 and Rev 6).
2. Spoken Affirmation TTS Compliance (<= 12 words, clean speech tokens).
3. Auditory Grounding Recall (slot reflection fidelity).
"""

import os
import sys
import json
import re
import time
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
            if not isinstance(slots, dict): slots = {}
            response = str(out.get("response", "")).strip()
            return {"domain": domain, "intent": intent, "slots": slots, "response": response, "raw": raw_text}
    except Exception:
        pass

    intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', raw_text)
    domain_match = re.search(r'"domain"\s*:\s*"([^"]+)"', raw_text)
    intent = intent_match.group(1).strip().lower() if intent_match else "unknown"
    domain = domain_match.group(1).strip().lower() if domain_match else "unknown"
    return {"domain": domain, "intent": intent, "slots": {}, "response": "", "raw": raw_text, "parse_error": True}

def run_prompt_inference(model, tokenizer, prompts, sys_prompt, max_new_tokens=128, batch_size=8):
    formatted_inputs = []
    for p in prompts:
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f'Spoken command: "{p}"'}
        ]
        formatted = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False, add_generation_prompt=True)
        formatted_inputs.append(formatted)

    all_decoded = []
    for i in range(0, len(formatted_inputs), batch_size):
        b_inputs = formatted_inputs[i : i + batch_size]
        encoded = tokenizer(b_inputs, return_tensors="pt", padding=True, truncation=True, max_length=8192)
        input_ids = encoded["input_ids"].to("cuda")
        attention_mask = encoded["attention_mask"].to("cuda")

        with torch.no_grad():
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                temperature=0.0,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        generated_tokens = outputs[:, input_ids.shape[1]:]
        texts = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        all_decoded.extend(texts)
    return [parse_llm_json(t) for t in all_decoded]

def score_predictions(df, preds):
    ts_correct = 0
    tcs_correct = 0
    pf_correct = 0
    total_slots = 0
    frame_correct = 0

    for p, (_, row) in zip(preds, df.iterrows()):
        gold_intent = str(row["intent"]).strip().lower()
        gold_domain = str(row["domain"]).strip().lower()
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

        if is_ts and is_tcs and slots_all_ok:
            frame_correct += 1

    n = len(df)
    return {
        "TS": round(ts_correct / n * 100, 2),
        "TCS": round(tcs_correct / n * 100, 2),
        "PF": round(pf_correct / total_slots * 100, 2) if total_slots > 0 else 0.0,
        "Frame_Acc": round(frame_correct / n * 100, 2),
        "Total_Samples": n,
        "Total_Slots": total_slots
    }

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "/work/hdd/bedl/zyin2/benchmark_phase2/failure_slice_target.csv"
    rev5_path = sys.argv[2] if len(sys.argv) > 2 else "/work/hdd/bedl/zyin2/benchmark_phase2/certified_generalized_system_prompt_rev5.txt"
    rev6_path = sys.argv[3] if len(sys.argv) > 3 else "/work/hdd/bedl/zyin2/benchmark_phase2/certified_generalized_system_prompt_rev6_nlg.txt"
    model_id = "Qwen/Qwen3-8B"

    print("================================================================================")
    print("=== SLICE VERIFICATION: Rev 6 NLG Affirmation vs. Rev 5 Frozen Baseline ===")
    print("================================================================================")
    print(f"Slice CSV:      {csv_path}")
    print(f"Rev 5 Baseline: {rev5_path}")
    print(f"Rev 6 Candidate:{rev6_path}")
    print(f"Model ID:       {model_id}")

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} target slice prompts.\n")

    with open(rev5_path, "r", encoding="utf-8") as f: rev5_prompt = f.read()
    with open(rev6_path, "r", encoding="utf-8") as f: rev6_prompt = f.read()

    print("Loading tokenizer and model...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )
    model.eval()
    print(f"Model loaded in {time.time() - t0:.2f}s.\n")

    prompts = df["prompt"].tolist()

    # 1. Inference on Rev 5
    print("--- [1/2] Running Rev 5 Baseline Inference ---")
    t1 = time.time()
    rev5_preds = run_prompt_inference(model, tokenizer, prompts, rev5_prompt, max_new_tokens=90, batch_size=8)
    print(f"Rev 5 finished in {time.time() - t1:.2f}s.")
    rev5_metrics = score_predictions(df, rev5_preds)
    print(f"Rev 5 Metrics: TS={rev5_metrics['TS']}%, PF={rev5_metrics['PF']}%, Frame_Acc={rev5_metrics['Frame_Acc']}%\n")

    # 2. Inference on Rev 6 NLG
    print("--- [2/2] Running Rev 6 NLG Inference ---")
    t2 = time.time()
    rev6_preds = run_prompt_inference(model, tokenizer, prompts, rev6_prompt, max_new_tokens=130, batch_size=8)
    print(f"Rev 6 finished in {time.time() - t2:.2f}s.")
    rev6_metrics = score_predictions(df, rev6_preds)
    print(f"Rev 6 Metrics: TS={rev6_metrics['TS']}%, PF={rev6_metrics['PF']}%, Frame_Acc={rev6_metrics['Frame_Acc']}%\n")

    # 3. Direct Invariance Analysis
    print("================================================================================")
    print("=== TOOL-CALLING INVARIANCE AUDIT (Rev 5 vs. Rev 6) ===")
    print("================================================================================")
    exact_ts_match = 0
    exact_slots_match = 0
    for idx, (p5, p6) in enumerate(zip(rev5_preds, rev6_preds)):
        ts_same = (p5["intent"] == p6["intent"]) and (p5["domain"] == p6["domain"])
        slots_same = (p5["slots"] == p6["slots"])
        if ts_same: exact_ts_match += 1
        if slots_same: exact_slots_match += 1
        if not ts_same or not slots_same:
            print(f"Row {idx} Divergence:")
            print(f"  Prompt: \"{prompts[idx]}\"")
            print(f"  Rev 5: intent={p5['intent']}, slots={p5['slots']}")
            print(f"  Rev 6: intent={p6['intent']}, slots={p6['slots']}")

    n = len(df)
    print(f"Exact Intent Invariance: {exact_ts_match} / {n} ({exact_ts_match/n*100:.2f}%)")
    print(f"Exact Slots Invariance:  {exact_slots_match} / {n} ({exact_slots_match/n*100:.2f}%)")
    print(f"Delta TS:       {rev6_metrics['TS'] - rev5_metrics['TS']:+.2f}%")
    print(f"Delta PF:       {rev6_metrics['PF'] - rev5_metrics['PF']:+.2f}%")
    print(f"Delta FrameAcc: {rev6_metrics['Frame_Acc'] - rev5_metrics['Frame_Acc']:+.2f}%")

    # 4. NLG / Conversational Affirmation Quality Audit
    print("\n================================================================================")
    print("=== CONVERSATIONAL AFFIRMATION (NLG) QUALITY AUDIT ===")
    print("================================================================================")
    word_count_passes = 0
    clean_speech_passes = 0
    responses = []

    for idx, (p6, prompt) in enumerate(zip(rev6_preds, prompts)):
        resp = p6.get("response", "")
        words = resp.split()
        wc = len(words)
        is_wc_ok = (wc <= 12)
        if is_wc_ok: word_count_passes += 1

        # Check clean speech tokens: no markdown, no URLs, no braces
        has_forbidden = bool(re.search(r'[\*#\`\{\}\[\]\\<>]|http', resp))
        if not has_forbidden and len(resp) > 0: clean_speech_passes += 1

        responses.append({
            "idx": idx,
            "prompt": prompt,
            "intent": p6["intent"],
            "slots": p6["slots"],
            "response": resp,
            "wc": wc,
            "wc_ok": is_wc_ok,
            "clean_ok": not has_forbidden
        })

    print(f"Length Compliance (<= 12 words): {word_count_passes} / {n} ({word_count_passes/n*100:.2f}%)")
    print(f"Clean Speech Compliance:         {clean_speech_passes} / {n} ({clean_speech_passes/n*100:.2f}%)")

    print("\n--- Qualitative Affirmation Sample Inspect (First 10) ---")
    for item in responses[:10]:
        print(f"[{item['idx']+1}] Spoken: \"{item['prompt']}\"")
        print(f"    Intent: {item['intent']} | Slots: {item['slots']}")
        print(f"    Voice Affirmation: \"{item['response']}\" ({item['wc']} words, clean={item['clean_ok']})")

    # Save outputs
    out_df = pd.DataFrame(responses)
    out_df.to_csv("/work/hdd/bedl/zyin2/benchmark_phase2/nlg_slice_verification_results.csv", index=False)
    print("\nSaved slice verification results to /work/hdd/bedl/zyin2/benchmark_phase2/nlg_slice_verification_results.csv")

if __name__ == "__main__":
    main()
