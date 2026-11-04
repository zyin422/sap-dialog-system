import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "Qwen/Qwen2.5-7B-Instruct"
print(f"Loading judge model: {model_id}...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
print("Judge model loaded successfully.")

JUDGE_SYSTEM_PROMPT = """You are an expert semantic evaluator for Spoken Language Understanding (SLU) tool calling.
Evaluate parameter filling (slot extraction) against the user's spoken command.

You will be given:
1. Spoken Utterance: The exact words spoken by the user.
2. Tool Name: The intended tool API.
3. Candidate Slots:
   - For RECALL evaluation: You are given Gold Slot (key, gold_val) and Predicted Value (pred_val).
     Judge whether pred_val successfully captures the semantic referent of gold_val in the context of the utterance.
     RULE: If pred_val preserves the core referent even with valid descriptive modifiers (e.g., 'porch light' for 'light', 'with lunch' for 'lunch', or 'Define conundrum' for 'conundrum'), mark as RECALL: PASS.
     Mark RECALL: FAIL only if pred_val is missing, refers to a different entity, or alters the factual meaning.
   - For PRECISION evaluation: You are given Predicted Slot (key, pred_val).
     Judge whether pred_val is explicitly grounded in the spoken utterance.
     RULE: If pred_val is supported by words spoken in the utterance and is a valid parameter, mark PRECISION: PASS.
     Mark PRECISION: FAIL if pred_val is an implicit hallucination or unmentioned default (e.g. inferring service='Apple Podcasts' or place='home' when not spoken).

Respond with a JSON object:
{
  "reasoning": "<1-2 sentence explanation>",
  "recall_pass": true/false (if evaluating recall),
  "precision_pass": true/false (if evaluating precision)
}
"""

test_cases = [
    {
        "id": "case_1_boundary_compound",
        "type": "recall",
        "utterance": "Turn on the porch light.",
        "tool": "iot_device_power",
        "slot_key": "device_type",
        "gold_val": "light",
        "pred_val": "porch light"
    },
    {
        "id": "case_2_interrogative_carrier",
        "type": "recall",
        "utterance": "Define 'conundrum'.",
        "tool": "qa_search",
        "slot_key": "query",
        "gold_val": "conundrum",
        "pred_val": "Define 'conundrum'."
    },
    {
        "id": "case_3_preposition",
        "type": "recall",
        "utterance": "Take enalapril with lunch.",
        "tool": "health_medication_reminder",
        "slot_key": "time",
        "gold_val": "lunch",
        "pred_val": "with lunch"
    },
    {
        "id": "case_4_true_omission",
        "type": "recall",
        "utterance": "What are my reminders?",
        "tool": "schedule_manage",
        "slot_key": "title",
        "gold_val": "reminders",
        "pred_val": None
    },
    {
        "id": "case_5_intent_mismatch_loss",
        "type": "recall",
        "utterance": "When is Thanksgiving this year?",
        "tool": "qa_search",
        "slot_key": "query",
        "gold_val": "when is thanksgiving this year",
        "pred_val": None
    },
    {
        "id": "case_6_precision_extra_valid",
        "type": "precision",
        "utterance": "Remind me to take a break in 15 minutes.",
        "tool": "schedule_manage",
        "slot_key": "date",
        "pred_val": "in 15 minutes",
        "gold_val": None
    },
    {
        "id": "case_7_precision_hallucinated_default",
        "type": "precision",
        "utterance": "Turn on heat.",
        "tool": "iot_device_power",
        "slot_key": "house_place",
        "pred_val": "home",
        "gold_val": None
    },
    {
        "id": "case_8_precision_hallucinated_service",
        "type": "precision",
        "utterance": "Play the latest episode of 'Planet Money'.",
        "tool": "media_play",
        "slot_key": "service",
        "pred_val": "Apple Podcasts",
        "gold_val": None
    },
    {
        "id": "case_9_precision_boundary_dual",
        "type": "precision",
        "utterance": "Turn on the porch light.",
        "tool": "iot_device_power",
        "slot_key": "device_type",
        "pred_val": "porch light",
        "gold_val": "light"
    },
    {
        "id": "case_10_precision_unmentioned_media_type",
        "type": "precision",
        "utterance": "Alexa, play more like this.",
        "tool": "media_play",
        "slot_key": "media_type",
        "pred_val": "music",
        "gold_val": None
    }
]

print("\n" + "="*70)
print("RUNNING LLM JUDGE ON REPRESENTATIVE BENCHMARK SLICE")
print("="*70)

for tc in test_cases:
    if tc["type"] == "recall":
        user_prompt = f"""EVALUATE RECALL:
Utterance: "{tc['utterance']}"
Tool: {tc['tool']}
Slot Key: {tc['slot_key']}
Gold Value: "{tc['gold_val']}"
Candidate Predicted Value: "{tc['pred_val']}"
Does candidate predicted value capture the referent of gold value?"""
    else:
        user_prompt = f"""EVALUATE PRECISION:
Utterance: "{tc['utterance']}"
Tool: {tc['tool']}
Slot Key: {tc['slot_key']}
Candidate Predicted Value: "{tc['pred_val']}"
Is candidate predicted value explicitly grounded in the utterance and appropriate for this parameter?"""

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.01,
            do_sample=False
        )
    output = tokenizer.decode(generated_ids[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

    print(f"\n--- [{tc['id'].upper()}] ({tc['type'].upper()}) ---")
    print(f"Utterance: '{tc['utterance']}' | Slot: '{tc['slot_key']}'")
    print(f"Gold: '{tc['gold_val']}' | Pred: '{tc['pred_val']}'")
    print(f"Judge Decision: {output}")
