#!/usr/bin/env python3
"""
llm_judge_4cat_delta.py
=======================
Runs Qwen 3 27B on Delta GPU cluster to perform 4-Category Dataset Filtering (Stage 2 LLM-as-a-Judge):
  1. KEEP           : Complete command frame intact (valid attempt, faithful slots, full proposition).
  2. UNDERSPECIFIED : Genuine communicative attempt with missing slot or dropped predicate verb.
  3. SLOT_DEVIATION : Genuine communicative attempt with mutated, substituted, or corrupted slot/digit.
  4. FILTER_OUT     : Non-attempt, prompt abandonment, protocol/UI reading, pure noise, factual answers.

Grounding: Formal 3-Axis Schema (formal_filtering_schema.md) & Bohus/Purver SDS Policies.
Zero benchmark test leakage: All 10 calibration exemplars are strictly disjoint from test prompts.
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
Your task is to classify whether a speaker's audio transcription given a target prompt belongs to one of FOUR mutually exclusive benchmark categories.

Follow a strict retention safety principle: individuals with motor speech disorders (dysarthria, ALS, Cerebral Palsy, Parkinson's, Stroke) often exhibit telegraphic speech, phonetic distortions, or false starts. Never discard authentic speech attempts.

Classify the candidate utterance into exactly ONE of the following FOUR categories:

1. KEEP (Complete Command Frame):
   The recording contains a genuine communicative attempt where BOTH the intent and all mandatory slots are articulated.
   - Includes full commands, natural spoken paraphrases, oral letter-by-letter spelling (e.g. "~K at westerly ~E ~D ~U dot"), and numbers verbalized as words (e.g. "nine thousand three hundred seventy four" for 9374).
   - Minor prepositional or morphological variations that preserve meaning belong in KEEP.

2. UNDERSPECIFIED (Telegraphic / Missing Slot / Missing Predicate):
   The recording contains a genuine communicative attempt, but mandatory information is omitted:
   - Slot-Deficient (Subtype A): Intent predicate is present, but mandatory slots are omitted (e.g. Target: "How much is a round-trip flight to Sedona?" -> Spoken: "How much is a flight?").
   - Predicate-Deficient (Subtype B): Carrier verb is omitted, but the focal entity is articulated (e.g. Target: "Explain 'ambivalence'" -> Spoken: "Ambivalence", Target: "Stream 'Interstellar' on HBO" -> Spoken: "Interstellar").
   - Optional-Provider Omitted (Subtype C): Explicit command spoken without optional streaming service.
   These route to proactive dialogue clarification (Task 3).

3. SLOT_DEVIATION (Mutated / Substituted Slot Values):
   The recording contains a genuine communicative attempt on the prompt, but the speaker substituted, mutated, or corrupted a specific slot value or numerical digit:
   - Number mutation (e.g. Target PIN: "9374" -> Spoken: "nine thousand and seventy-four" [9074]).
   - Entity mutation (e.g. Target username: "SabrinaK" -> Spoken: "Sabrina", Target: "MSNBC" -> Spoken: "NBC").
   - Time mutation (e.g. Target: "Friday" -> Spoken: "today", Target: "6:45" -> Spoken: "6:40").
   These are preserved for acoustic ASR evaluation, but excluded from gold tool execution benchmarks.

4. FILTER_OUT (Hard Discard / Unusable):
   The recording does NOT contain a valid communicative attempt on the target prompt. Purge if ANY apply:
   - Prompt Abandonment / Metatalk: The speaker gives up, complains, or converses with a bystander ("Dang I cannot", "Hold on").
   - Interface / Device Reading: The speaker reads screen instructions ("Press record button", "Click next to continue").
   - Pure Acoustic Artifact / Noise: The audio contains zero intelligible words (coughs, throat clearing, microphone rustle, silence).
   - Standalone Factual Answers: The prompt is an information request, but the speaker answers it factually (e.g. Target: "What is the capital of Peru?" -> Spoken: "Lima").
   - Total Semantic Drift: The spoken content is completely alien to the target stimulus with zero topical overlap.

Few-Shot Calibration Exemplars:
[Exemplar 1]
Target: Send an email to SabinaK@westerly.edu.
Spoken: Send an email to Sabina ~K at westerly ~E ~D ~U.
Decision: KEEP
Rationale: Full intent and entity articulated; oral character spelling is a valid spoken realization.

[Exemplar 2]
Target: Remember that my PIN is 9374.
Spoken: Remember my PIN is nine thousand three hundred and seventy four.
Decision: KEEP
Rationale: Full intent and entity articulated; verbalized number format matches numerical value 9374.

[Exemplar 3]
Target: How much is a round-trip flight to Sedona, Arizona?
Spoken: How much is a flight?
Decision: UNDERSPECIFIED
Rationale: Target intent present but mandatory destination slot is omitted; routes to gap elicitation.

[Exemplar 4]
Target: Explain the word 'ambivalence'.
Spoken: (kof-) Ambivalence.
Decision: UNDERSPECIFIED
Rationale: Telegraphic communicative attempt vocalizing the focal entity without carrier verb; routes to intent elicitation.

[Exemplar 5]
Target: Stream 'Interstellar' on HBO Max.
Spoken: (st-) Stream Interstellar.
Decision: UNDERSPECIFIED
Rationale: Core focal entity and intent articulated while omitting optional streaming platform; routes to service disambiguation.

[Exemplar 6]
Target: Remember that my PIN is 9374.
Spoken: Remember my PIN is nine thousand and seventy-four.
Decision: SLOT_DEVIATION
Rationale: Genuine communicative attempt, but numerical argument was mutated (9074 instead of 9374).

[Exemplar 7]
Target: Email SabrinaK@west.edu.
Spoken: Email Sabrina@west.edu.
Decision: SLOT_DEVIATION
Rationale: Communicative attempt, but username slot mutated by omitting required middle initial 'K'.

[Exemplar 8]
Target: What is the capital of Peru?
Spoken: Lima.
Decision: FILTER_OUT
Rationale: Standalone factual answer provided instead of issuing a query to the voice assistant.

[Exemplar 9]
Target: Schedule an eye exam for Monday at 2 PM.
Spoken: Click next to continue recording.
Decision: FILTER_OUT
Rationale: Speaker reads recording interface instructions aloud instead of attempting the prompt.

[Exemplar 10]
Target: Mute the kitchen speaker.
Spoken: I cannot do this, hold on.
Decision: FILTER_OUT
Rationale: Explicit prompt abandonment and metatalk without attempting the command.

Respond STRICTLY with valid JSON in this exact format:
{"decision": "KEEP" | "UNDERSPECIFIED" | "SLOT_DEVIATION" | "FILTER_OUT", "rationale": "<brief reason>"}"""

def build_prompt(target_prompt: str, spoken_text: str) -> str:
    return f"Target Prompt: {target_prompt}\nSpoken Transcription: {spoken_text}\nJSON Decision:"

def parse_decision(raw_output: str) -> Tuple[str, str]:
    clean_output = re.sub(r'<think>.*?</think>', '', raw_output, flags=re.DOTALL).strip()
    
    # 1. Search for JSON object
    match = re.search(r'\{[^{}]*"decision"\s*:\s*"([^"]+)"[^{}]*\}', clean_output, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            dec = data.get("decision", "").strip().upper()
            if dec in ["KEEP", "UNDERSPECIFIED", "SLOT_DEVIATION", "FILTER_OUT"]:
                return dec, data.get("rationale", "")
            # Aliases
            if dec in ["RETAIN", "COMPLETE", "VALID"]:
                return "KEEP", data.get("rationale", "")
        except:
            pass

    # 2. Fallback regex search
    upper = clean_output.upper()
    if "FILTER_OUT" in upper or "FILTER OUT" in upper:
        return "FILTER_OUT", "Regex fallback: FILTER_OUT"
    if "SLOT_DEVIATION" in upper or "SLOT DEVIATION" in upper:
        return "SLOT_DEVIATION", "Regex fallback: SLOT_DEVIATION"
    if "UNDERSPECIFIED" in upper:
        return "UNDERSPECIFIED", "Regex fallback: UNDERSPECIFIED"
    if "KEEP" in upper or "RETAIN" in upper:
        return "KEEP", "Regex fallback: KEEP"

    return "KEEP", "Parse fallback: default conservative keep"

def main():
    parser = argparse.ArgumentParser(description="Stage 2 4-Category LLM-as-a-Judge on Delta GPU")
    parser.add_argument("--input_csv", type=str, required=True, help="Path to input unresolved CSV")
    parser.add_argument("--output_csv", type=str, required=True, help="Path to output predictions CSV")
    parser.add_argument("--model_id", type=str, default="/work/hdd/bedl/zyin2/models/Qwen3.8-27B", help="Path or HF ID of judge model")
    parser.add_argument("--batch_size", type=int, default=8, help="Inference batch size")
    args = parser.parse_args()

    print("==============================================================================")
    print("Stage 2 4-Category LLM-as-a-Judge Evaluation on Delta GPU")
    print(f"Date:       {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input:      {args.input_csv}")
    print(f"Output:     {args.output_csv}")
    print(f"Model:      {args.model_id}")
    print(f"Batch Size: {args.batch_size}")
    print("==============================================================================")

    # Ingest rows
    rows = []
    with open(args.input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total_rows = len(rows)
    print(f"Total instances to judge: {total_rows}")
    if total_rows == 0:
        print("No instances to evaluate.")
        return

    # Check for existing checkpoint
    checkpoint_csv = args.output_csv + ".checkpoint"
    processed_ids = set()
    completed_rows = []
    if os.path.exists(checkpoint_csv):
        with open(checkpoint_csv, "r", encoding="utf-8") as f:
            c_reader = csv.DictReader(f)
            for r in c_reader:
                processed_ids.add(r["id"])
                completed_rows.append(r)
        print(f"Resuming from checkpoint: {len(processed_ids)} already processed.")

    remaining_rows = [r for r in rows if r["id"] not in processed_ids]
    print(f"Remaining instances to process: {len(remaining_rows)}")

    if not remaining_rows:
        print("All rows already evaluated in checkpoint. Finalizing output.")
        with open(args.output_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(completed_rows[0].keys()))
            writer.writeheader()
            writer.writerows(completed_rows)
        return

    # Load Model & Tokenizer
    print(f"\nLoading tokenizer and model: {args.model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id

    try:
        from transformers import Qwen3_5ForConditionalGeneration
        model = Qwen3_5ForConditionalGeneration.from_pretrained(
            args.model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
    except Exception:
        model = AutoModelForCausalLM.from_pretrained(
            args.model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )

    model.eval()
    print("Model loaded successfully.")

    # Process in batches
    batch_size = args.batch_size
    fieldnames = list(rows[0].keys())
    for extra in ["llm_decision", "llm_rationale", "raw_llm_response"]:
        if extra not in fieldnames:
            fieldnames.append(extra)

    # Initialize checkpoint file if not existing
    if not os.path.exists(checkpoint_csv):
        os.makedirs(os.path.dirname(checkpoint_csv), exist_ok=True)
        with open(checkpoint_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    start_time = time.time()
    for b_idx in range(0, len(remaining_rows), batch_size):
        batch = remaining_rows[b_idx:b_idx + batch_size]
        prompts = []
        for r in batch:
            user_msg = build_prompt(r.get("prompt", ""), r.get("spoken_text", ""))
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ]
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            prompts.append(text)

        inputs = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True, max_length=2048)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.01,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id
            )

        in_len = inputs["input_ids"].shape[1]
        out_batch = []
        for i, out_ids in enumerate(outputs):
            gen_ids = out_ids[in_len:]
            gen_text = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
            dec, rat = parse_decision(gen_text)
            
            row_dict = dict(batch[i])
            row_dict["llm_decision"] = dec
            row_dict["llm_rationale"] = rat
            row_dict["raw_llm_response"] = gen_text
            out_batch.append(row_dict)
            completed_rows.append(row_dict)

        # Append to checkpoint
        with open(checkpoint_csv, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerows(out_batch)

        elapsed = time.time() - start_time
        done_cnt = len(completed_rows)
        pct = done_cnt / total_rows * 100
        sec_per_item = elapsed / max(done_cnt - len(processed_ids), 1)
        remaining_sec = sec_per_item * (total_rows - done_cnt)
        print(f"[{done_cnt}/{total_rows} ({pct:.1f}%)] Decision batch done. Est remaining: {remaining_sec/60:.1f} min")

    # Final export
    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    with open(args.output_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(completed_rows)

    if os.path.exists(checkpoint_csv):
        os.remove(checkpoint_csv)

    print("\n==============================================================================")
    print(f"Stage 2 LLM-as-a-Judge Complete! Exported to: {args.output_csv}")
    print("Decision Breakdown:")
    from collections import Counter
    dec_counts = Counter(r["llm_decision"] for r in completed_rows)
    for dec, count in dec_counts.most_common():
        print(f"  {dec:16s}: {count:5d} ({count/total_rows*100:.2f}%)")
    print(f"Total Time: {(time.time() - start_time)/60:.2f} min")
    print("==============================================================================")

if __name__ == "__main__":
    main()
