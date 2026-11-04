import os
import sys
import json
import re
import time
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from evaluate_slu_enriched_qwen3 import build_enriched_system_prompt, parse_llm_json, compute_char_f1, normalize_text

model_id = "Qwen/Qwen3-8B"
schema_path = "/work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json" if os.path.exists("/work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json") else "sap-dialog-system/schema_freeze/SLU_schema_v1.0.json"
csv_path = sys.argv[1] if len(sys.argv) > 1 else ("failure_mode2_lumping.csv" if os.path.exists("failure_mode2_lumping.csv") else "sap-dialog-system/failure_mode2_lumping.csv")

print(f"=== Evaluating Failure Mode 2 / Target Failures on {csv_path} with Qwen3-8B ===")
df = pd.read_csv(csv_path)
print(f"Loaded {len(df)} prompts.")

sys_prompt = build_enriched_system_prompt(schema_path)

tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left")
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
model.eval()

prompts = df["prompt"].tolist()
formatted_inputs = []
for p in prompts:
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f'Spoken command: "{p}"'}
    ]
    formatted = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False, add_generation_prompt=True)
    formatted_inputs.append(formatted)

batch_size = 8
decoded = []
t0 = time.time()
for i in range(0, len(formatted_inputs), batch_size):
    b_inputs = formatted_inputs[i : i + batch_size]
    encoded = tokenizer(b_inputs, return_tensors="pt", padding=True, truncation=True, max_length=8192)
    input_ids = encoded["input_ids"].to("cuda")
    attention_mask = encoded["attention_mask"].to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=90,
            temperature=0.0,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )

    gen_tokens = outputs[:, input_ids.shape[1] :]
    b_decoded = tokenizer.batch_decode(gen_tokens, skip_special_tokens=True)
    decoded.extend(b_decoded)
    print(f"  Processed {min(i + batch_size, len(formatted_inputs))}/{len(formatted_inputs)} in {time.time() - t0:.2f}s...")

# Evaluation
total_prompts = len(df)
ts_correct = 0
frame_correct = 0
total_gold_slots = 0
pf_correct = 0

results = []
for idx, (p, raw) in enumerate(zip(prompts, decoded)):
    row = df.iloc[idx]
    gold_intent = str(row["intent"]).strip().lower()
    raw_slots = row["gold_slots"] if "gold_slots" in row else row.get("slots", "{}")
    if isinstance(raw_slots, dict):
        gold_slots = raw_slots
    elif isinstance(raw_slots, str):
        try:
            gold_slots = json.loads(raw_slots)
        except Exception:
            try:
                import ast
                gold_slots = ast.literal_eval(raw_slots)
            except Exception:
                gold_slots = {}
    else:
        gold_slots = {}

    parsed = parse_llm_json(raw)
    pred_intent = parsed["intent"]
    pred_slots = parsed["slots"]

    is_ts = (pred_intent == gold_intent)
    if is_ts:
        ts_correct += 1

    prompt_slots_ok = True
    slot_details = []
    for k, v in gold_slots.items():
        total_gold_slots += 1
        norm_g = normalize_text(str(v))
        norm_p = normalize_text(str(pred_slots.get(k, "")))

        matched = (norm_g == norm_p) or (norm_g != "" and compute_char_f1(norm_g, norm_p) >= 0.85)
        if matched:
            pf_correct += 1
            slot_details.append(f"  [OK] {k}: '{norm_p}'")
        else:
            prompt_slots_ok = False
            slot_details.append(f"  [FAIL] {k}: gold='{norm_g}' vs pred='{norm_p}'")

    is_frame = is_ts and prompt_slots_ok
    if is_frame:
        frame_correct += 1

    results.append({
        "prompt": p,
        "gold_intent": gold_intent,
        "pred_intent": pred_intent,
        "gold_slots": gold_slots,
        "pred_slots": pred_slots,
        "is_ts": is_ts,
        "is_frame": is_frame,
        "details": slot_details,
        "raw_json": raw
    })

print("\n" + "=" * 80)
print(f"SUMMARY ON {total_prompts} PROMPTS:")
print(f"  Tool Selection (TS):         {ts_correct}/{total_prompts} ({ts_correct/total_prompts*100:.1f}%)")
print(f"  Parameter Filling (PF):      {pf_correct}/{total_gold_slots} ({pf_correct/total_gold_slots*100:.1f}%)")
print(f"  Command Frame Accuracy:      {frame_correct}/{total_prompts} ({frame_correct/total_prompts*100:.1f}%)")
print("=" * 80)

print("\nDETAILED PER-PROMPT BREAKDOWN:")
for r in results:
    status = "PASS" if r["is_frame"] else "FAIL"
    print(f"\n[{status}] '{r['prompt']}'")
    print(f"       Intent: Gold='{r['gold_intent']}' | Pred='{r['pred_intent']}'")
    for d in r["details"]:
        print(f"     {d}")
    if not r["is_frame"]:
        print(f"       Raw Pred Slots: {r['pred_slots']}")
