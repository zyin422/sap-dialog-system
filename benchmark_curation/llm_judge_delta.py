#!/usr/bin/env python3
"""
llm_judge_delta.py

Runs Qwen 3 27B on Delta GPU cluster to perform binary dataset filtering (Stage 2 LLM-as-a-Judge):
- "FILTER_OUT": Unusable, abandoned, unprompted speech, non-speech, or interface reading.
- "RETAIN": Genuine communicative attempt on the prompt (complete, telegraphic, slot deviations, or partials).

Zero hardcoded prompt dictionaries. Calibrated via in-context few-shot exemplars with zero benchmark leakage.
"""

import os
import sys
import json
import re
import csv
import time
import argparse
from typing import Dict, Tuple, List, Any
import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer

SYSTEM_PROMPT = """You are an expert spoken dialogue system judge for disordered speech in the Speech Accessibility Project (SAP).
Your task is to classify whether a speaker's audio transcription given a target prompt must be DISCARDED ("FILTER_OUT") or PRESERVED ("RETAIN").

Follow a strict retention safety principle: preserve authentic speech from individuals with motor speech disorders (dysarthria, ALS, Cerebral Palsy, Parkinson's, Stroke) unless the audio is completely unusable, non-compliant, or non-speech.

Classify the candidate utterance into exactly ONE binary tag:

1. FILTER_OUT (Hard Discard):
   The recording does NOT contain a valid communicative attempt on the target prompt. Purge if ANY of the following apply:
   - Non-Attempt / Prompt Abandonment: The speaker complains, vents, or gives up without attempting the command, or converses with a bystander without addressing the assistant.
   - Task Commentary / Stimulus Reading: The speaker reads the prompt aloud as a reading exercise or expresses meta-commentary about the recording study rather than commanding a voice assistant.
   - Interface / Device Reading: The speaker reads recording interface instructions or screen buttons aloud rather than attempting the prompt.
   - Pure Acoustic Artifact / Noise: The audio contains no intelligible words (e.g. pure silence, coughing, throat clearing, background microphone rustle).
   - Standalone Factual Answers: The target prompt is an information request or command, but the speaker answers it factually instead of issuing the command or query.
   - Total Semantic Drift: The spoken content is completely unrelated to the target stimulus with zero topical overlap.
   - Uninterpretable Isolated Fragments: Isolated function words or grammatical particles lacking any topical entity or predicate.

2. RETAIN (Preserve for Speech Benchmark):
   The recording contains a genuine communicative attempt on the target prompt and MUST be preserved. Retain if ANY of the following apply:
   - Full or Partial Commands: The user issued the complete command frame or a natural spoken paraphrase.
   - Telegraphic Speech: In severe dysarthria, speakers frequently omit carrier verbs and vocalize only the focal entity or core noun phrase. These are authentic communicative attempts and must be retained.
   - Slot Omissions or Variations: Omitting secondary qualifiers or modifiers while preserving the core entity or query intent.
   - Alternative Spoken Formats: Oral character-by-character spelling, phonetic abbreviations, or numbers spoken in word format.
   - Slot Deviations, Speech Errors, & Acoustic Slurs: Substituted words, misread parameters, or dysarthric phonetic distortions. These represent speech attempts required for acoustic modeling and robust error recovery.
   - Incidental Dysfluencies & Frustration: Stutters, repetitions, pauses, or brief frustration markers accompanying an attempt.

Few-Shot Calibration Exemplars:
[Exemplar 1]
Target: Mute the kitchen speaker.
Spoken: Kitchen speaker.
Decision: RETAIN
Rationale: Telegraphic communicative attempt vocalizing the focal entity; authentic assistive speech to retain.

[Exemplar 2]
Target: Navigate to St. Jude Hospital on Main Street.
Spoken: Navigate to St. Jude Hospital.
Decision: RETAIN
Rationale: Core entity and intent preserved despite omission of the street-level modifier.

[Exemplar 3]
Target: Schedule an eye exam for Monday at 2 PM.
Spoken: Eye exam for Monday at 4 PM.
Decision: RETAIN
Rationale: Genuine communicative attempt with a substituted time parameter; retain for acoustic and SLU evaluation.

[Exemplar 4]
Target: What is the capital of Peru?
Spoken: Lima.
Decision: FILTER_OUT
Rationale: Factual answer provided instead of querying the assistant.

[Exemplar 5]
Target: Schedule an eye exam for Monday at 2 PM.
Spoken: Click next to continue recording.
Decision: FILTER_OUT
Rationale: Reading interface instructions rather than attempting the prompt.

[Exemplar 6]
Target: Mute the kitchen speaker.
Spoken: I don't think this device is working at all, let me try later.
Decision: FILTER_OUT
Rationale: Prompt abandonment and metatalk without attempting the command.

[Exemplar 7]
Target: What is the capital of Peru?
Spoken: Where the?
Decision: FILTER_OUT
Rationale: Isolated function word fragment without entity or action predicate.

Respond STRICTLY with valid JSON in this exact format:
{"decision": "FILTER_OUT" | "RETAIN", "rationale": "<brief reason>"}"""

def build_prompt(target_prompt: str, spoken_text: str) -> str:
    user_content = f"Target Prompt: {target_prompt}\nSpoken Transcription: {spoken_text}\nJSON Decision:"
    return user_content

def parse_decision(raw_output: str) -> Tuple[str, str]:
    clean_output = re.sub(r'<think>.*?</think>', '', raw_output, flags=re.DOTALL).strip()
    
    match = re.search(r'\{[^{}]*"decision"\s*:\s*"([^"]+)"[^{}]*\}', clean_output, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            dec = data.get("decision", "").strip().upper()
            if dec in ["FILTER_OUT", "RETAIN"]:
                return dec, data.get("rationale", "")
            if dec in ["KEEP", "UNDERSPECIFIED", "SLOT_DEVIATION", "VALID"]:
                return "RETAIN", data.get("rationale", "")
        except:
            pass

    upper = clean_output.upper()
    if "FILTER_OUT" in upper or "FILTER OUT" in upper:
        return "FILTER_OUT", "Fallback regex extraction: FILTER_OUT"
    if any(k in upper for k in ["RETAIN", "KEEP", "UNDERSPECIFIED", "SLOT_DEVIATION", "VALID"]):
        return "RETAIN", "Fallback regex extraction: RETAIN"

    return "RETAIN", "Parse failure fallback (conservative retain)"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", type=str, default="/work/hdd/bedl/zyin2/benchmark_filtering/to_llm_207.csv")
    parser.add_argument("--output_csv", type=str, default="/work/hdd/bedl/zyin2/benchmark_filtering/llm_judge_207_binary_predictions.csv")
    parser.add_argument("--model_id", type=str, default="/work/hdd/bedl/zyin2/models/Qwen3.8-27B")
    parser.add_argument("--batch_size", type=int, default=8)
    args = parser.parse_args()

    print(f"Loading model: {args.model_id}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id

    try:
        from transformers import Qwen3_5ForConditionalGeneration
        print("Using Qwen3_5ForConditionalGeneration")
        model = Qwen3_5ForConditionalGeneration.from_pretrained(
            args.model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
    except Exception as e:
        print(f"Fallback to AutoModelForCausalLM due to: {e}")
        model = AutoModelForCausalLM.from_pretrained(
            args.model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )

    model.eval()

    rows = []
    with open(args.input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            rows.append(r)

    print(f"Loaded {len(rows)} instances to judge.")
    out_fieldnames = list(fieldnames) + ["llm_decision", "llm_rationale", "raw_llm_response"]

    results = []
    for start_idx in range(0, len(rows), args.batch_size):
        t0 = time.time()
        batch_rows = rows[start_idx : start_idx + args.batch_size]

        messages_batch = []
        for r in batch_rows:
            target_prompt = r.get("prompt", "")
            spoken_text = r.get("spoken_text", "")
            user_msg = build_prompt(target_prompt, spoken_text)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ]
            messages_batch.append(messages)

        prompt_texts = [
            tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            for m in messages_batch
        ]

        inputs = tokenizer(prompt_texts, return_tensors="pt", padding=True).to(model.device)
        prompt_len = inputs["input_ids"].shape[1]

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=128,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id
            )

        for i, r in enumerate(batch_rows):
            gen_tokens = outputs[i, prompt_len:]
            gen_text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
            dec, rat = parse_decision(gen_text)
            r["llm_decision"] = dec
            r["llm_rationale"] = rat
            r["raw_llm_response"] = gen_text
            results.append(r)

        print(f"  Processed {min(start_idx + args.batch_size, len(rows))}/{len(rows)} in {time.time()-t0:.1f}s")

    with open(args.output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote predictions to {args.output_csv}")

    has_gt = any("user_override" in r and r["user_override"] for r in results)
    if has_gt:
        def to_binary(d: str) -> str:
            return "FILTER_OUT" if str(d).strip().upper() == "FILTER_OUT" else "RETAIN"

        correct = sum(1 for r in results if to_binary(r.get("user_override", "")) == to_binary(r.get("llm_decision", "")))
        total = sum(1 for r in results if r.get("user_override"))
        print(f"\nBinary LLM-as-a-Judge Concordance on {total} instances: {correct/total*100:.2f}% ({correct}/{total})")

if __name__ == "__main__":
    main()
