#!/usr/bin/env python3
"""
filter_manifest_pipeline.py

Speech Accessibility Project (SAP) Two-Stage Audio Manifest Filter
===================================================================
A robust, domain-agnostic, two-stage filtering pipeline to curate assistive
speech datasets (e.g. training, dev, or test manifests) for dialogue systems:

Architecture:
  - Stage 1 (Deterministic Fast-Path):
      Evaluates lexical overlap, numbers, and acoustic noise patterns.
      Instantly resolves ~85-90% of instances (verbatim matches to RETAIN,
      non-speech / abandonment / prompt reading to FILTER_OUT) with zero GPU compute.
  - Stage 2 (LLM-as-a-Judge with Qwen 3 27B):
      Evaluates the remaining ~10-15% ambiguous cases (digit-vs-word formats,
      stutters, telegraphic noun phrases, phoneme slurs, slot substitutions)
      using an in-context calibrated zero-leakage prompt.

Output Artifacts:
  1. <prefix>_audited_full.csv     : Complete manifest with audit metadata, stages, and rationales.
  2. <prefix>_clean_retained.csv   : Usable speech records (RETAIN) for ASR/SLU/dialogue training.
  3. <prefix>_purged.csv           : Discarded audio records (FILTER_OUT) for audit inspection.

Usage:
  # Run full two-stage pipeline on GPU (e.g. SLURM on Delta):
  python filter_manifest_pipeline.py \
      --input_manifest /path/to/manifest.csv \
      --output_dir /path/to/output \
      --model_id /work/hdd/bedl/zyin2/models/Qwen3.8-27B \
      --batch_size 8

  # Run Stage 1 deterministic fast-path only (no GPU required):
  python filter_manifest_pipeline.py \
      --input_manifest /path/to/manifest.csv \
      --output_dir /path/to/output \
      --stage1_only
"""

import os
import sys
import re
import csv
import time
import json
import argparse
from typing import Dict, Tuple, List, Any

# Number word dictionary for digit-to-word matching
NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety", "hundred", "thousand", "first", "second", "third", "fourth",
    "sixteenth", "eighteenth", "nineteenth"
}

# ---------------------------------------------------------------------------
# STAGE 1: Deterministic Fast-Path Filter
# ---------------------------------------------------------------------------

def run_stage1_quickfilter(prompt: str, spoken: str) -> Tuple[str, str]:
    """
    Evaluates an utterance using domain-agnostic deterministic heuristics.
    Returns: (decision, rationale)
      decision in ['KEEP', 'FILTER_OUT', 'UNRESOLVED']
    """
    raw_spoken = spoken.strip()
    
    # 1. Pure acoustic non-speech / ultra-short check
    s_clean = re.sub(r"\{[^}]*\}", "", raw_spoken)
    s_clean = re.sub(r"\([^)]*\)", "", s_clean)
    norm_s = re.sub(r"[^\w\s]", " ", s_clean.lower()).split()
    norm_p = re.sub(r"[^\w\s]", " ", prompt.lower()).split()

    if not norm_s or norm_s in [["uh"], ["um"], ["ah"], ["okay"]]:
        return "FILTER_OUT", "Acoustic non-speech / unintelligible audio artifact"

    # 2. Out-of-Scope tool intent (e.g. Duolingo study prompt)
    if "open duolingo" in prompt.lower() or "open duolingo" in raw_spoken.lower():
        return "FILTER_OUT", "Out-of-scope non-dialogue prompt"

    # 3. Explicit Refusal / UI Reading / Abandonment
    channel_main = re.sub(r"\(ss:.*?\)", "", raw_spoken).strip()
    channel_main_clean = re.sub(r"\([^)]*\)", "", channel_main).strip()

    abandonment_re = r"\b(press the record button|read the text|press record|say that again|i can't talk|i cannot speak|dang i cannot)\b"
    if re.search(abandonment_re, channel_main_clean if channel_main_clean else channel_main, re.IGNORECASE):
        p_set = set(norm_p)
        s_set = set(norm_s)
        overlap = len(p_set & s_set) / max(len(p_set), 1)
        if overlap < 0.85:
            return "FILTER_OUT", "Explicit refusal / UI reading / abandonment"

    # 4. Caregiver bracketed reading: [Prompt] Answer
    if re.search(r"\[.*?\]", raw_spoken):
        after_bracket = re.sub(r"\[.*?\]", "", raw_spoken).strip()
        after_words = re.sub(r"[^\w\s]", " ", after_bracket.lower()).split()
        if len(after_words) <= 4:
            return "FILTER_OUT", f"Caregiver prompt reading with isolated response: '{after_bracket}'"

    # 5. High-Confidence Complete Command Frame (KEEP)
    p_set = set(norm_p)
    s_set = set(norm_s)
    jaccard = len(p_set & s_set) / max(len(p_set | s_set), 1)
    token_recall = len(p_set & s_set) / max(len(p_set), 1)

    # Check numeric equality
    nums_p = set(re.findall(r"\b\d+\b", prompt.lower()) + [w for w in norm_p if w in NUMBER_WORDS])
    nums_s = set(re.findall(r"\b\d+\b", raw_spoken.lower()) + [w for w in norm_s if w in NUMBER_WORDS])

    if nums_p != nums_s:
        return "UNRESOLVED", f"Numeric token difference: prompt {nums_p} vs spoken {nums_s}"

    # Strict lexical match with length parity
    if token_recall >= 0.85 and jaccard >= 0.75 and len(norm_s) >= len(norm_p) - 1:
        return "KEEP", f"High-confidence lexical match (Jaccard: {jaccard:.2f}, Recall: {token_recall:.2f})"

    # 6. Ambiguous / edge cases -> Forward to Stage 2 LLM Judge
    return "UNRESOLVED", f"Ambiguous edge-case (Jaccard: {jaccard:.2f}, Recall: {token_recall:.2f})"


# ---------------------------------------------------------------------------
# STAGE 2: Zero-Leakage LLM-as-a-Judge (Qwen 3 27B)
# ---------------------------------------------------------------------------

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

def build_llm_prompt(target_prompt: str, spoken_text: str) -> str:
    return f"Target Prompt: {target_prompt}\nSpoken Transcription: {spoken_text}\nJSON Decision:"

def parse_llm_decision(raw_output: str) -> Tuple[str, str]:
    clean = re.sub(r'<think>.*?</think>', '', raw_output, flags=re.DOTALL).strip()
    match = re.search(r'\{[^{}]*"decision"\s*:\s*"([^"]+)"[^{}]*\}', clean, re.DOTALL)
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

    upper = clean.upper()
    if "FILTER_OUT" in upper or "FILTER OUT" in upper:
        return "FILTER_OUT", "Fallback extraction: FILTER_OUT"
    if any(k in upper for k in ["RETAIN", "KEEP", "UNDERSPECIFIED", "SLOT_DEVIATION", "VALID"]):
        return "RETAIN", "Fallback extraction: RETAIN"
    return "RETAIN", "Parse fallback (conservative preservation)"


def run_stage2_llm_judge(unresolved_rows: List[Dict[str, Any]], model_id: str, batch_size: int = 8, checkpoint_csv: str = None) -> List[Dict[str, Any]]:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    try:
        from transformers import Qwen3_5ForConditionalGeneration
        model_cls = Qwen3_5ForConditionalGeneration
    except ImportError:
        model_cls = AutoModelForCausalLM

    # Check if checkpoint already exists with all predictions
    if checkpoint_csv and os.path.exists(checkpoint_csv):
        cached_rows = []
        with open(checkpoint_csv, 'r', encoding='utf-8') as f:
            rdr = csv.DictReader(f)
            cached_rows = list(rdr)
        if len(cached_rows) == len(unresolved_rows):
            print(f"\n[Stage 2] Found complete checkpoint with {len(cached_rows)} predictions at {checkpoint_csv}. Resuming without re-computing!")
            return cached_rows

    print(f"\n[Stage 2] Loading LLM Judge checkpoint: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id

    model = model_cls.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()

    print(f"[Stage 2] Evaluating {len(unresolved_rows)} ambiguous instances (Batch Size: {batch_size})...")
    judged_rows = []

    for start_idx in range(0, len(unresolved_rows), batch_size):
        t0 = time.time()
        batch = unresolved_rows[start_idx : start_idx + batch_size]
        messages_batch = []
        for r in batch:
            p = r["prompt"]
            s = r["spoken_text"]
            user_msg = build_llm_prompt(p, s)
            messages_batch.append([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ])

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

        for i, r in enumerate(batch):
            gen_tokens = outputs[i, prompt_len:]
            gen_text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
            dec, rat = parse_llm_decision(gen_text)
            r_copy = dict(r)
            r_copy["final_decision"] = dec
            r_copy["pipeline_stage"] = "Stage 2: LLM Judge"
            r_copy["filter_rationale"] = rat
            judged_rows.append(r_copy)

        # Save checkpoint incrementally
        if checkpoint_csv:
            chk_fields = list(dict.fromkeys(list(judged_rows[0].keys())))
            with open(checkpoint_csv, 'w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=chk_fields, extrasaction='ignore')
                w.writeheader()
                w.writerows(judged_rows)

        elapsed = time.time() - t0
        done = min(start_idx + batch_size, len(unresolved_rows))
        print(f"  Processed {done}/{len(unresolved_rows)} ({done/len(unresolved_rows)*100:.1f}%) in {elapsed:.1f}s")

    return judged_rows


# ---------------------------------------------------------------------------
# Pipeline Orchestrator
# ---------------------------------------------------------------------------

def extract_fields(row: Dict[str, str]) -> Tuple[str, str]:
    prompt = row.get("prompt") or row.get("target_prompt") or row.get("target") or ""
    spoken = (
        row.get("spoken_text") or
        row.get("text") or
        row.get("normalized_transcript") or
        row.get("norm_text_with_disfluency") or
        row.get("norm_text_without_disfluency") or
        row.get("transcript") or
        ""
    )
    return prompt.strip(), spoken.strip()

def main():
    parser = argparse.ArgumentParser(description="Speech Accessibility Project (SAP) Two-Stage Audio Manifest Filter")
    parser.add_argument("--input_manifest", type=str, required=True, help="Path to input manifest CSV")
    parser.add_argument("--output_dir", type=str, default="filtered_manifest_output", help="Directory for output CSVs")
    parser.add_argument("--output_prefix", type=str, default="manifest_filtered", help="Prefix for output CSV files")
    parser.add_argument("--model_id", type=str, default="/work/hdd/bedl/zyin2/models/Qwen3.8-27B", help="Path or HuggingFace ID for Qwen 3 27B")
    parser.add_argument("--batch_size", type=int, default=8, help="Inference batch size")
    parser.add_argument("--stage1_only", action="store_true", help="Run only Stage 1 deterministic quickfilter")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("================================================================================")
    print("Speech Accessibility Project (SAP) Two-Stage Audio Manifest Filter")
    print(f"Input Manifest: {args.input_manifest}")
    print(f"Output Directory: {args.output_dir}")
    print("================================================================================")

    # 1. Ingest Manifest
    rows = []
    with open(args.input_manifest, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        orig_fieldnames = list(reader.fieldnames or [])
        for r in reader:
            rows.append(r)

    print(f"\n[Ingestion] Loaded {len(rows)} audio records.")

    # 2. Stage 1: Deterministic Fast-Path
    print("\n[Stage 1] Running Deterministic Fast-Path Filter...")
    t_start = time.time()
    
    stage1_resolved_keep = []
    stage1_resolved_purge = []
    unresolved_rows = []

    for r in rows:
        prompt, spoken = extract_fields(r)
        r_entry = dict(r)
        r_entry["prompt"] = prompt
        r_entry["spoken_text"] = spoken
        
        dec, rationale = run_stage1_quickfilter(prompt, spoken)
        if dec == "KEEP":
            r_entry["final_decision"] = "RETAIN"
            r_entry["pipeline_stage"] = "Stage 1: Quickfilter Fast-Path"
            r_entry["filter_rationale"] = rationale
            stage1_resolved_keep.append(r_entry)
        elif dec == "FILTER_OUT":
            r_entry["final_decision"] = "FILTER_OUT"
            r_entry["pipeline_stage"] = "Stage 1: Quickfilter Fast-Path"
            r_entry["filter_rationale"] = rationale
            stage1_resolved_purge.append(r_entry)
        else:
            r_entry["quickfilter_rationale"] = rationale
            unresolved_rows.append(r_entry)

    t_stage1 = time.time() - t_start
    total = len(rows)
    print(f"  Stage 1 Completed in {t_stage1:.2f}s:")
    print(f"    - Fast-Path RETAIN:     {len(stage1_resolved_keep):>6} ({len(stage1_resolved_keep)/total*100:5.1f}%)")
    print(f"    - Fast-Path FILTER_OUT: {len(stage1_resolved_purge):>6} ({len(stage1_resolved_purge)/total*100:5.1f}%)")
    print(f"    - Ambiguous UNRESOLVED: {len(unresolved_rows):>6} ({len(unresolved_rows)/total*100:5.1f}%)")

    # If Stage 1 only requested, write intermediate files and exit
    if args.stage1_only:
        unresolved_csv = os.path.join(args.output_dir, f"{args.output_prefix}_stage2_unresolved.csv")
        unres_fields = list(set(orig_fieldnames + ["prompt", "spoken_text", "quickfilter_rationale"]))
        with open(unresolved_csv, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=unres_fields)
            w.writeheader()
            w.writerows(unresolved_rows)
        print(f"\n[Stage 1 Only] Unresolved cases saved to: {unresolved_csv}")
        return

    # 3. Stage 2: LLM-as-a-Judge
    stage2_judged = []
    checkpoint_csv = os.path.join(args.output_dir, f"{args.output_prefix}_stage2_checkpoint.csv")
    if unresolved_rows:
        stage2_judged = run_stage2_llm_judge(unresolved_rows, args.model_id, args.batch_size, checkpoint_csv=checkpoint_csv)
    
    # 4. Consolidate and Save Outputs
    all_curated = stage1_resolved_keep + stage1_resolved_purge + stage2_judged
    out_fields = list(dict.fromkeys(orig_fieldnames + ["prompt", "spoken_text", "final_decision", "pipeline_stage", "filter_rationale", "quickfilter_rationale"]))

    full_csv = os.path.join(args.output_dir, f"{args.output_prefix}_audited_full.csv")
    clean_csv = os.path.join(args.output_dir, f"{args.output_prefix}_clean_retained.csv")
    purged_csv = os.path.join(args.output_dir, f"{args.output_prefix}_purged.csv")

    with open(full_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(all_curated)

    retained_rows = [r for r in all_curated if r.get("final_decision") == "RETAIN"]
    purged_rows = [r for r in all_curated if r.get("final_decision") == "FILTER_OUT"]

    with open(clean_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(retained_rows)

    with open(purged_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=out_fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(purged_rows)

    print("\n================================================================================")
    print("FINAL CURATION TELEMETRY")
    print("================================================================================")
    print(f"Total Input Audio Records:    {total:>6}")
    print(f"Retained for Training/Eval:   {len(retained_rows):>6} ({len(retained_rows)/total*100:5.1f}%)")
    print(f"Purged (Non-speech/Bad):      {len(purged_rows):>6} ({len(purged_rows)/total*100:5.1f}%)")
    print("\nArtifacts Saved:")
    print(f"  [Full Audited]: {full_csv}")
    print(f"  [Clean Set]:    {clean_csv}")
    print(f"  [Purged Set]:   {purged_csv}")
    print("================================================================================")

if __name__ == "__main__":
    main()
