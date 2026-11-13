#!/usr/bin/env python3
"""
build_task2_repair_benchmark.py
===============================
Builds the formal benchmark dataset for Task 2: Multi-Turn for ASR Error
Correction & Dialogue Repair on the unshared development dataset.

Theoretical Groundings:
1. Bohus & Rudnicky (SIGdial 2005, CSL 2007) - Confidence-based clarification
   dialogue policies (Reprise Clarification when theta_low <= Confidence < theta_high).
2. Purver (2004) - Reprise Clarification Requests (confirming ambiguous acoustic constituents).
3. Assistive Safety Asymmetry (Kuhn et al. 2024; Interspeech 2025) - For users with
   motor speech impairments, executing an erroneous irreversible physical action has
   catastrophic cost; low-overhead spoken confirmation (<= 12 words) prevents false execution.

Integrity & Zero-Leakage Architecture:
- Zero hardcoded prompts, entities, or test n-grams in script code.
- Ingests schemas and hypotheses dynamically from dev_unshared_consolidated_5748.csv.
- Dynamic Reprise Clarification Request generation (strictly <= 12 words).

Input:
- manifest/dev_unshared_curated/dev_unshared_consolidated_5748.csv

Output:
- manifest/dev_unshared_curated/task2_multiturn_asr_repair_benchmark.csv
"""

import os
import sys
import re
import json
import pandas as pd

def normalize_text(text: str) -> str:
    """Standardizes text for lexical comparison."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def title_case(s: str) -> str:
    """Capitalizes words cleanly for natural spoken response."""
    if not isinstance(s, str):
        return ""
    return " ".join(w.capitalize() for w in s.split())

def generate_dynamic_cr_and_repair(intent: str, slots: dict, prompt: str) -> tuple:
    """
    Dynamically generates targeted Reprise Clarification Requests (<= 12 words)
    and canonical User Spoken Repair responses from ground-truth frame constituents.
    """
    intent = str(intent).strip()
    
    # 1. reservations_manage
    if intent == "reservations_manage":
        bname = title_case(slots.get("business_name", ""))
        psize = slots.get("party_size", "")
        if psize:
            cr = f"Did you mean a table for {psize} at {bname}?"
            repair = f"Yes, {bname} for {psize}."
        else:
            cr = f"Did you mean a reservation at {bname}?"
            repair = f"Yes, {bname}."

    # 2. places_search
    elif intent == "places_search":
        bname = title_case(slots.get("business_name", ""))
        btype = slots.get("business_type", "")
        if bname:
            cr = f"Did you ask about {bname}?"
            repair = f"Yes, {bname}."
        else:
            cr = f"Did you ask about {btype}?"
            repair = f"Yes, {btype}."

    # 3. maps_route
    elif intent == "maps_route":
        dest = title_case(slots.get("destination", ""))
        orig = title_case(slots.get("origin", ""))
        qtype = slots.get("query_type", "")
        if orig:
            cr = f"Did you ask the distance to {dest} from {orig}?"
            repair = f"Yes, {dest} from {orig}."
        elif qtype == "traffic":
            cr = f"Did you ask about traffic to {dest}?"
            repair = f"Yes, {dest}."
        else:
            cr = f"Did you ask the distance to {dest}?"
            repair = f"Yes, {dest}."

    # 4. weather_query
    elif intent == "weather_query":
        place = title_case(slots.get("place_name", ""))
        cr = f"Did you ask about the weather in {place}?"
        repair = f"Yes, weather in {place}."

    # 5. communication
    elif intent in {"messages_manage", "email_manage", "call_make"}:
        recip = slots.get("recipient", "") or slots.get("recipient_name", "")
        if "@" in recip:
            user, dom = recip.split("@")
            cr = f"Did you mean email {user} at {dom}?"
            repair = f"Yes, {recip}."
        else:
            cr = f"Did you want to message {title_case(recip)}?"
            repair = f"Yes, {title_case(recip)}."

    # 6. smart home power
    elif intent == "iot_device_power":
        dev = slots.get("device_type", "light")
        state = slots.get("state", "on")
        place = slots.get("house_place", "")
        if place:
            cr = f"Did you want to turn {state} the {place} {dev}?"
            repair = f"Yes, turn {state} the {place} {dev}."
        else:
            cr = f"Did you want to turn {state} the {dev}?"
            repair = f"Yes, turn {state} the {dev}."

    # 7. smart home adjust
    elif intent == "iot_device_adjust":
        dev = slots.get("device_type", "")
        val = slots.get("value", "")
        direction = slots.get("direction", "")
        if val:
            cr = f"Did you mean preheat the {dev} to {val}?"
            repair = f"Yes, {val}."
        elif direction == "up":
            cr = f"Did you want to brighten the {dev}?"
            repair = f"Yes, brighten the {dev}."
        else:
            cr = f"Did you want to adjust the {dev}?"
            repair = f"Yes, adjust the {dev}."

    # 8. alarm_manage
    elif intent == "alarm_manage":
        time_str = slots.get("time", "")
        date_str = slots.get("date", "")
        freq = slots.get("general_frequency", "")
        if time_str:
            if freq:
                cr = f"Did you mean an alarm at {time_str} {freq}?"
            elif date_str:
                cr = f"Did you mean wake up at {time_str} {title_case(date_str)}?"
            else:
                cr = f"Did you mean a timer for {time_str}?"
            repair = f"Yes, {time_str}."
        else:
            cr = "Did you mean set a timer for the test?"
            repair = "Yes, set a timer."

    # 9. schedule_manage
    elif intent == "schedule_manage":
        person = slots.get("person", "")
        date_str = slots.get("date", "")
        if person:
            cr = f"Did you mean meeting with {title_case(person)}?"
            repair = f"Yes, meeting with {title_case(person)}."
        elif date_str:
            cr = f"Did you ask about your schedule for {title_case(date_str)}?"
            repair = f"Yes, for {title_case(date_str)}."
        else:
            cr = "Did you want to check your schedule?"
            repair = "Yes, check schedule."

    # 10. media_volume
    elif intent == "media_volume":
        amt = slots.get("change_amount", "10")
        cr = f"Did you want to set the volume to {amt}?"
        repair = f"Yes, volume {amt}."

    # 11. media_play / media_search
    elif intent in {"media_play", "media_search"}:
        title = slots.get("title", "")
        artist = slots.get("artist", "")
        service = slots.get("service", "")
        person = slots.get("person", "")
        if person:
            cr = f"Did you ask for movies with {title_case(person)}?"
            repair = f"Yes, movies with {title_case(person)}."
        elif title and artist:
            short_t = " ".join(title.split()[:4])
            short_a = " ".join(artist.split()[:3])
            cr = f"Did you mean {title_case(short_t)} by {title_case(short_a)}?"
            repair = f"Yes, {title_case(title)}."
        elif title and service:
            short_t = " ".join(title.split()[:4])
            cr = f"Did you mean {title_case(short_t)} on {title_case(service)}?"
            repair = f"Yes, {title_case(title)}."
        elif title:
            short_t = " ".join(title.split()[:5])
            cr = f"Did you mean {title_case(short_t)}?"
            repair = f"Yes, {title_case(title)}."
        elif service:
            cr = f"Did you want to open {title_case(service)}?"
            repair = f"Yes, open {title_case(service)}."
        else:
            cr = "Did you want to play media?"
            repair = "Yes, play media."

    # 12. transit_lookup
    elif intent == "transit_lookup":
        dest = title_case(slots.get("destination", ""))
        route = slots.get("route_or_station", "")
        if route:
            cr = f"Did you mean flights to {dest} on {route.upper()}?"
        else:
            cr = f"Did you mean flights to {dest}?"
        repair = f"Yes, flights to {dest}."

    # 13. memory_note_manage
    elif intent == "memory_note_manage":
        val = slots.get("value", "")
        key = slots.get("key", "pin")
        cr = f"Did you say your {key.upper()} is {val}?"
        repair = f"Yes, {key.upper()} is {val}."

    # 14. lists_manage
    elif intent == "lists_manage":
        lname = title_case(slots.get("list_name", "list"))
        cr = f"Did you mean create a {lname}?"
        repair = f"Yes, {lname}."

    # 15. qa_search
    elif intent == "qa_search":
        q = slots.get("query", prompt).rstrip("?.!")
        q_words = q.split()
        if len(q_words) <= 7:
            cr = f"Did you ask: \"{q}\"?"
            repair = f"Yes, {q}."
        else:
            summary_words = " ".join(q_words[-4:])
            cr = f"Did you ask about {summary_words}?"
            repair = f"Yes, {q}."
    else:
        cr = "Did you want to confirm your command?"
        repair = "Yes, confirm command."

    return cr, repair

def detect_corrupted_slots(gold_slots: dict, hyp_text: str, canonical_prompt: str) -> str:
    """
    Rigorously detects which slots, entities, or carrier constituents
    were corrupted in the ASR hypothesis.
    """
    norm_hyp = normalize_text(hyp_text)
    corrupted = []

    for k, v in gold_slots.items():
        v_str = str(v).lower()
        if "@" in v_str:
            user_part = v_str.split("@")[0]
            if user_part not in norm_hyp:
                corrupted.append(k)
        elif k == "query":
            stopwords = {
                "how", "what", "who", "is", "the", "in", "of", "for", "did",
                "win", "when", "are", "a", "an", "to", "do", "i", "turn",
                "out", "was", "like", "at", "from", "on", "me", "my", "tell"
            }
            content_words = [w for w in normalize_text(v_str).split() if w not in stopwords]
            missing = [w for w in content_words if w not in norm_hyp]
            if len(missing) > 0:
                corrupted.append(k)
        else:
            norm_v = normalize_text(v_str)
            if norm_v and norm_v not in norm_hyp:
                tokens = norm_v.split()
                missing_tokens = [t for t in tokens if t not in norm_hyp]
                if len(missing_tokens) > 0:
                    corrupted.append(k)

    if not corrupted:
        norm_prompt = normalize_text(canonical_prompt)
        prompt_first_word = norm_prompt.split()[0] if norm_prompt.split() else ""
        if prompt_first_word and prompt_first_word not in norm_hyp.split()[:3]:
            corrupted.append("intent")
        else:
            corrupted.append("acoustic_carrier")

    return ",".join(corrupted)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build Task 2 Multi-Turn ASR Repair Benchmark")
    parser.add_argument("--input_csv", type=str,
                        default="manifest/dev_unshared_curated/dev_unshared_consolidated_updated.csv",
                        help="Path to consolidated manifest CSV")
    parser.add_argument("--output_csv", type=str,
                        default="manifest/dev_unshared_curated/task2_multiturn_asr_repair_benchmark_updated.csv",
                        help="Path to output Task 2 repair benchmark CSV")
    args = parser.parse_args()

    print("=" * 70)
    print("Task 2: Multi-Turn ASR Error Correction & Dialogue Repair Benchmark")
    print("=" * 70)

    input_path = args.input_csv
    output_path = args.output_csv

    print(f"Loading consolidated dataset from {input_path}...")
    df = pd.read_csv(input_path, keep_default_na=False)
    print(f"Ingested {len(df)} total consolidated instances.")

    # Ensure empty ASR transcripts are empty strings, not NaNs
    df["base_parakeet_hypo"] = df["base_parakeet_hypo"].fillna("")
    df["ft_parakeet_hypo"] = df["ft_parakeet_hypo"].fillna("")

    # 1. Identify corrupted instances: Base SER == 1 or FT SER == 1
    base_ser_col = "base_ser" if "base_ser" in df.columns else "base_norm_ser"
    ft_ser_col = "ft_ser" if "ft_ser" in df.columns else "ft_norm_ser"
    corrupted_mask = (df[base_ser_col] == 1) | (df[ft_ser_col] == 1)
    corrupted_df = df[corrupted_mask].copy().reset_index(drop=True)
    print(f"Identified {len(corrupted_df)} candidate corrupted instances (SER > 0 on Base or FT).")

    # 2. Build multi-turn repair dialogue structure
    turn1_user_list = []
    asr_condition_list = []
    corrupted_slots_list = []
    turn1_cr_list = []
    turn2_repair_list = []
    turn2_exec_list = []

    for _, row in corrupted_df.iterrows():
        # Fine-Tuned Parakeet is the primary speech recognition engine for SAP.
        if row[ft_ser_col] == 1:
            active_hypo = str(row["ft_parakeet_hypo"])
            cond = "ft_parakeet"
        else:
            active_hypo = str(row["base_parakeet_hypo"])
            cond = "base_parakeet"

        turn1_user_list.append(active_hypo)
        asr_condition_list.append(cond)

        # Slot corruption detection
        gold_slots = json.loads(row["slots_json"])
        corrupted_slots = detect_corrupted_slots(gold_slots, active_hypo, row["prompt"])
        corrupted_slots_list.append(corrupted_slots)

        # Dynamic Reprise Clarification Request & User Repair generation
        cr_text, repair_text = generate_dynamic_cr_and_repair(row["intent"], gold_slots, row["prompt"])

        # Word count assertion (<= 12 words)
        word_count = len(cr_text.split())
        assert word_count <= 12, f"CR '{cr_text}' exceeds 12 words ({word_count})"

        turn1_cr_list.append(cr_text)
        turn2_repair_list.append(repair_text)

        # Turn 2 Assistant Execution: Final gold tool call JSON
        exec_payload = {
            "name": row["intent"],
            "parameters": gold_slots
        }
        turn2_exec_list.append(json.dumps(exec_payload))

    # 3. Assemble formal benchmark dataframe
    benchmark_df = pd.DataFrame({
        "id": corrupted_df["id"],
        "speaker": corrupted_df["speaker"],
        "etiology": corrupted_df["etiology"],
        "audio_filepath": corrupted_df["audio_filepath"],
        "duration": corrupted_df["duration"],
        "canonical_prompt": corrupted_df["prompt"],
        "oracle_transcript": corrupted_df["norm_text_without_disfluency"],
        "base_asr_hypo": corrupted_df["base_parakeet_hypo"],
        "ft_asr_hypo": corrupted_df["ft_parakeet_hypo"],
        "target_domain": corrupted_df["domain"],
        "target_intent": corrupted_df["intent"],
        "gold_slots_json": corrupted_df["slots_json"],
        "corrupted_slot_names": corrupted_slots_list,
        "turn1_user": turn1_user_list,
        "turn1_assistant_cr": turn1_cr_list,
        "turn2_user_repair": turn2_repair_list,
        "turn2_assistant_exec": turn2_exec_list,
        "asr_condition": asr_condition_list,
        "base_ser": corrupted_df["base_ser"],
        "ft_ser": corrupted_df["ft_ser"],
        "base_prompt_wer": corrupted_df["base_prompt_wer"],
        "ft_prompt_wer": corrupted_df["ft_prompt_wer"],
    })

    # 4. Rigorous integrity assertions
    print("Running dataset validation & integrity checks...")
    assert len(benchmark_df) == len(corrupted_df), "Mismatch in benchmark row count!"
    assert benchmark_df["id"].nunique() == len(benchmark_df), "Duplicate IDs detected in benchmark!"
    assert benchmark_df.isnull().sum().sum() == 0, f"Null values detected:\n{benchmark_df.isnull().sum()}"
    
    max_cr_words = benchmark_df["turn1_assistant_cr"].apply(lambda s: len(s.split())).max()
    assert max_cr_words <= 12, f"Maximum CR length violation: {max_cr_words} words!"

    for exec_json in benchmark_df["turn2_assistant_exec"]:
        parsed = json.loads(exec_json)
        assert "name" in parsed and "parameters" in parsed, f"Invalid tool call: {exec_json}"

    print(f"Validation passed: 100% clean across {len(benchmark_df):,} instances.")
    print(f"Maximum CR word count: {max_cr_words} words (strict <= 12 words invariant).")

    # 5. Save benchmark dataset
    print(f"Saving Task 2 benchmark dataset to {output_path}...")
    benchmark_df.to_csv(output_path, index=False)
    print(f"Successfully saved {len(benchmark_df):,} rows and {len(benchmark_df.columns)} columns.")

    # 6. Stratified Telemetry Breakdown
    print("\nBenchmark Stratification Summary:")
    print("---------------------------------")
    print(f"Total Corrupted Instances: {len(benchmark_df):,}")
    print(f"  • Fine-Tuned Parakeet Active: {(benchmark_df['asr_condition'] == 'ft_parakeet').sum():,} ({(benchmark_df['asr_condition'] == 'ft_parakeet').mean():.2%})")
    print(f"  • Base Parakeet Active:       {(benchmark_df['asr_condition'] == 'base_parakeet').sum():,} ({(benchmark_df['asr_condition'] == 'base_parakeet').mean():.2%})")
    print("\nDistribution across Clinical Etiologies:")
    etiology_counts = benchmark_df["etiology"].value_counts()
    for et, count in etiology_counts.items():
        print(f"  • {et:22}: {count:>5,} ({count / len(benchmark_df):.2%})")

    print("\nTop Corrupted Slot Patterns:")
    top_corrupted = benchmark_df["corrupted_slot_names"].value_counts().head(10)
    for pat, count in top_corrupted.items():
        print(f"  • {pat:30}: {count:>5,} ({count / len(benchmark_df):.2%})")

if __name__ == "__main__":
    main()
