import os
import sys
import json
import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM

sys.path.insert(0, "/work/hdd/bedl/zyin2/benchmark_phase2")
from evaluate_slu_enriched_qwen3 import build_enriched_system_prompt, parse_llm_json, compute_char_f1, normalize_text

schema_path = "/work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json" if os.path.exists("/work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json") else "sap-dialog-system/schema_freeze/SLU_schema_v1.0.json"
model_id = "Qwen/Qwen3-8B"

print("=== Loading Qwen3-8B and Schema for Condition A & B Representative Evaluation ===")
sys_prompt = build_enriched_system_prompt(schema_path)

tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left")
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")
model.eval()

reps = [
    {
        "gold_id": "SAP-CMD-0304",
        "description": "Voice Telephony with Proper Name (Communication)",
        "oracle": "Please call Kathy Bianco.",
        "base": "Please call Cassie Bianco.",
        "ft": "please call kathy bianco",
        "gold_intent": "call_make",
        "gold_slots": {"recipient_name": "kathy bianco"}
    },
    {
        "gold_id": "SAP-CMD-0318",
        "description": "Climate Control with Severe Acoustic Distortion (Smart Home)",
        "oracle": "Raise the temperature.",
        "base": "Wait, change this to me.",
        "ft": "raise the temperature",
        "gold_intent": "iot_device_adjust",
        "gold_slots": {"setting": "temperature", "direction": "up"}
    },
    {
        "gold_id": "SAP-CMD-0197",
        "description": "Media Volume Command (Media)",
        "oracle": "Increase the volume.",
        "base": "And volume.",
        "ft": "increase the volume",
        "gold_intent": "media_volume",
        "gold_slots": {"action": "up"}
    }
]

for rep in reps:
    print("\n" + "=" * 78)
    print(f"CASE: {rep['gold_id']} | {rep['description']}")
    print(f"Gold Intent: {rep['gold_intent']} | Gold Slots: {rep['gold_slots']}")
    print("=" * 78)

    conditions = [
        ("Oracle Clean Text", rep["oracle"]),
        ("Condition A (Base ASR)", rep["base"]),
        ("Condition B (Fine-Tuned ASR)", rep["ft"])
    ]

    for cond_name, text in conditions:
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f'Spoken command: "{text}"'}
        ]
        formatted = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False, add_generation_prompt=True)
        encoded = tokenizer([formatted], return_tensors="pt", padding=True, truncation=True, max_length=8192).to("cuda")

        with torch.no_grad():
            outputs = model.generate(
                **encoded,
                max_new_tokens=90,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        gen = outputs[0][encoded["input_ids"].shape[1]:]
        raw = tokenizer.decode(gen, skip_special_tokens=True).strip()
        parsed = parse_llm_json(raw)

        ts_ok = (parsed["intent"] == rep["gold_intent"])
        pf_ok = True
        slot_status = {}
        for k, v in rep["gold_slots"].items():
            norm_g = normalize_text(str(v))
            norm_p = normalize_text(str(parsed["slots"].get(k, "")))
            match = (norm_g == norm_p) or (norm_g != "" and compute_char_f1(norm_g, norm_p) >= 0.85)
            slot_status[k] = (match, parsed["slots"].get(k, None))
            if not match:
                pf_ok = False

        frame_ok = ts_ok and pf_ok

        print(f"\n  [{cond_name}]")
        print(f"  Input Utterance:   \"{text}\"")
        print(f"  Predicted Intent:  '{parsed['intent']}' (Domain: '{parsed['domain']}') -> TS: {'PASS' if ts_ok else 'FAIL'}")
        print(f"  Predicted Slots:   {parsed['slots']}")
        for k, (s_match, s_val) in slot_status.items():
            print(f"    * Slot '{k}': expected '{rep['gold_slots'][k]}' vs pred '{s_val}' -> {'PASS' if s_match else 'FAIL'}")
        print(f"  Command Frame:     {'SUCCESS' if frame_ok else 'FAILED'}")

print("\n=== Representative Evaluation Completed Successfully ===")
