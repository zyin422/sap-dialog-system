import json
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "/work/hdd/bedl/zyin2/models/Qwen3.8-27B"
print(f"Loading tokenizer and model from {model_id}...")
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True
)
model.eval()

PROMPT_TEMPLATE = """You are an expert scientific evaluator for Spoken Language Understanding (SLU).
Evaluate whether the predicted parameter slot value matches the user's spoken utterance.

Output MUST be a valid JSON object starting with {{ and ending with }}:
{{
  "verdict": true,
  "reasoning": "<concise explanation>"
}}

EVALUATION TYPE: {eval_type}
Utterance: "{utterance}"
Tool: {tool}
Slot: {slot_key}
{slot_info}
"""

test_cases = [
    {
        "eval_type": "RECALL",
        "utterance": "Turn on the porch light.",
        "tool": "iot_device_power",
        "slot_key": "device_type",
        "slot_info": 'Gold: "light"\nPredicted: "porch light"\nDoes predicted value capture the referent of the gold value in the utterance?'
    },
    {
        "eval_type": "PRECISION",
        "utterance": "Listen to CBS.",
        "tool": "media_play",
        "slot_key": "service",
        "slot_info": 'Predicted: "CBS"\nIs predicted value explicitly grounded in the spoken utterance?'
    },
    {
        "eval_type": "RECALL",
        "utterance": "Define 'conundrum'.",
        "tool": "general_qa",
        "slot_key": "query",
        "slot_info": 'Gold: "conundrum"\nPredicted: "Define \'conundrum\'."\nDoes predicted value capture the referent of the gold value in the utterance?'
    },
    {
        "eval_type": "PRECISION",
        "utterance": "Play some music.",
        "tool": "media_play",
        "slot_key": "service",
        "slot_info": 'Predicted: "Apple Music"\nIs predicted value explicitly grounded in the spoken utterance?'
    }
]

for tc in test_cases:
    prompt = PROMPT_TEMPLATE.format(**tc)
    messages = [
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=64,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id
        )
    out = tokenizer.decode(output_ids[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    print("=" * 60, flush=True)
    print(f"CASE: {tc['eval_type']} | {tc['utterance']} | {tc['slot_key']}", flush=True)
    print(f"RAW OUTPUT:\n{out}", flush=True)
    print("=" * 60, flush=True)
