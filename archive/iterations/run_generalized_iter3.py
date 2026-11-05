#!/usr/bin/env python3
"""
Generalized SLU Prompt — Iteration 3
Modifications in Canonical Tools and Parameters:
1. lists_manage.list_name: Enhanced parameter description to capture target list categories (shopping, grocery, to-do, gifts) when adding items.
2. places_search.sort_by: Enhanced parameter description to capture spatial proximity words ('distance' for nearby, closest, nearest).
3. health_medication_reminder vs schedule_manage: Clarified tool scopes so general task reminders (vet, reservations, errands) route to schedule_manage, while health_medication_reminder is strictly for medical pharmaceuticals.
4. qa_search vs media_search: Clarified that audio recognition (what song is this), release dates, and image/photo searches belong to qa_search, not media streaming catalogs.
5. schedule_manage.title: Clarified parameter description to explicitly accept generic category nouns (meeting, appointment, reminder, call) as the title.
"""

import os
import sys
import time
import json
import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def build_tools_catalog_iter3() -> str:
    catalog = """- accessibility_dictation_toggle [accessibility] - Enable or disable speech-to-text dictation mode: state: ['on', 'off', 'enable', 'disable']
- accessibility_ui_scale [accessibility] - Adjust screen display zoom, text magnification, or contrast: direction: ['up', 'down', 'in', 'out'], ui_element: ['zoom', 'text_size', 'high_contrast', 'screen']
- alarm_manage [calendar_alarm] - Set, query, snooze, or cancel clock alarms and countdown timers: action: ['set', 'cancel', 'query', 'snooze'], time (Clock time or timer duration), date (Alarm date), general_frequency: ['daily', 'weekdays', 'weekends', 'weekly', 'monthly']
- schedule_manage [calendar_alarm] - Create, delete, update, or view calendar appointments, meetings, events, and general task reminders (e.g. vet, reservations, errands): action: ['create', 'delete', 'query', 'update'], title (Event title, topic, task description, or generic event category noun like meeting, appointment, event, call, reminder), date (Calendar day or relative date expression), time (Clock time or meal timestamp), person (Attendee or participant name)
- call_make [communication] - Place outgoing voice or video telephone calls to a contact or business: recipient_name (Recipient person or business being called), phone_number (Telephone digits)
- call_manage [communication] - Manage active incoming or connected telephony calls: action: ['answer', 'decline', 'hang_up', 'mute', 'unmute', 'redial']
- messages_manage [communication] - Send, read, or reply to SMS or instant chat text messages: action: ['send', 'read', 'reply'], recipient (Recipient contact name or phone number), message_body (Dictated message text)
- email_manage [communication] - Compose, send, search, or read electronic mail messages: action: ['send', 'read', 'search'], recipient (Recipient email address or contact name), date (Date filter for email lookup), message_body (Dictated body content)
- qa_search [general_qa] - Answer open-domain factual, informational, recipe, encyclopedic, song release date, audio recognition, or web image queries: query (Core factual search query, stripped of conversational carrier prefixes)
- weather_query [general_qa] - Check meteorological weather conditions, forecasts, and temperature: place_name (Geographic city, state, or region ONLY; not dates), date (Forecast date, holiday, or relative day expression like today/tomorrow), weather_aspect (Specific meteorological condition like rain, temperature)
- device_find [general_qa] - Locate, ping, or ring a misplaced personal hardware device: device_type (Target misplaced hardware device noun phrase)
- order_manage [general_qa] - Track delivery status, view, or cancel commercial online merchandise orders: action: ['track', 'cancel', 'return', 'status']
- health_medication_reminder [health] - Schedule or view reminders specifically for taking prescription pharmaceutical drugs or medical supplements (strictly for medical drugs; NOT for appointments, pets, or general tasks): medication (Prescription drug or supplement name ONLY), time (Intake time or meal reference)
- health_refill_query [health] - Check prescription medication refill status or pharmacy availability: medication (Prescription drug name)
- health_info_query [health] - Inquire about prescription pharmaceutical drug dosages, contraindications, or adverse effects: medication (Prescription drug name), info_type: ['side_effects', 'dosage', 'interactions', 'refill']
- maps_route [maps_places] - Calculate navigation routes, driving directions, travel distances, and commute traffic: destination (Target geographic arrival point), origin (Starting geographic departure point), query_type: ['directions', 'distance', 'traffic']
- places_search [maps_places] - Search for local commercial establishments, points of interest, store hours, and facilities: business_name (Brand or venue title), business_type (Commercial or facility category), sort_by: ['rating', 'distance', 'relevance'] (Ordering criterion: select 'distance' for geographic proximity queries like nearby, nearest, closest)
- reservations_manage [maps_places] - Book, manage, or query dining reservations and hospitality appointments: business_name (Restaurant or hospitality venue title), time (Reservation timestamp), date (Reservation calendar day), party_size (Guest headcount)
- media_play [media] - Start or resume playback of specific songs, audiobooks, podcasts, videos, or streaming channels: media_type: ['music', 'podcast', 'radio', 'audiobook', 'movie', 'tv_show'], title (Track, album, show, or book title), artist (Musician, band, or host), service (Streaming app or platform), house_place (Residential playback room)
- media_search [media] - Browse or discover available playable streaming catalog titles on device (does not answer trivia, release dates, or audio recognition): media_type: ['movie', 'tv_show', 'music', 'podcast', 'audiobook'], person (Actor, director, musician, or podcast host), genre (Genre classification), title (Franchise or title search string)
- media_control [media] - Control active audio/video playback state: action: ['pause', 'resume', 'stop', 'next', 'previous', 'like', 'dislike', 'fast_forward', 'rewind'], duration (Scrubbing offset or seek duration)
- media_volume [media] - Adjust or mute hardware audio output volume level: action: ['up', 'down', 'mute', 'unmute', 'set'], change_amount (Offset step or target absolute level)
- lists_manage [notes_memory] - Create, view, add items to, or remove items from personal lists: action: ['create', 'add', 'remove', 'query'], item (Item noun phrase or conjunction phrase), list_name (Target list category, purpose, or collection title such as shopping, grocery, to-do, gifts; populated whenever a target list is referenced)
- memory_note_manage [notes_memory] - Store or recall personal factual notes, attributes, and user-specified memory items: action: ['store', 'recall'], key (Associative subject/attribute key for X-is-Y relations), value (Verbatim fact content or full unkeyed declarative clause)
- iot_device_power [smart_home] - Turn power on or off for smart home hardware devices, appliances, and fixtures: device_type (Appliance, fixture, or hardware device noun phrase), state: ['on', 'off'], house_place (Residential room location)
- iot_device_adjust [smart_home] - Adjust continuous settings on smart appliances (brightness, thermostat temperature, color): device_type (Target hardware appliance), setting: ['brightness', 'temperature', 'color', 'speed'], direction: ['up', 'down'], value (Target absolute setting with units)
- iot_sensor_query [smart_home] - Check readings, open/closed contact states, or detection from smart home sensors: sensor_type: ['temperature', 'motion', 'lock', 'contact'], device_type (Hardware device target), room (Room or residential zone)
- rideshare_book [transport] - Request hailing or dispatch of on-demand passenger vehicles: destination (Drop-off location)
- transit_lookup [transport] - Query departure timetables, schedule arrivals, and lines for public scheduled transit (buses, trains, commercial flights): transit_type: ['train', 'bus', 'flight'], destination (Arrival stop, station, or city), route_or_station (Public transit line name, station, or carrier), time (Departure or arrival timestamp)"""
    return catalog

def build_prompt_iter3(tools_str: str) -> str:
    rules = """UNIVERSAL EXTRACTION RULES:
1. Closed Tool Catalog: The 'intent' MUST be selected strictly from the 29 canonical tool names listed above. Never invent, modify, or substitute unlisted tool names.
2. Closed Enum Adherence: When a parameter declares a list of allowable options in brackets [...], select strictly from that list. If an utterance uses a synonymous phrasing (e.g. cancelling/dropping vs deleting), select the canonical enum that represents that semantic function.
3. Semantic Role Alignment: Assign extracted spans to parameters whose descriptive definition matches the semantic entity. Specifically, assign temporal and calendar expressions to date/time parameters, geographic entities to location parameters, and core action verbs to action parameters.
4. Minimal Slot Invariance: Extract only parameters that are explicitly mentioned or directly implied in the user utterance. If a parameter is not mentioned, omit that key from the 'slots' dictionary. Never invent default or unuttered values.
5. Constituent Span Preservation: For open-vocabulary text parameters, extract the complete descriptive noun phrase or clause constituent (preserving modifying adjectives, compound elements, and trailing prepositional qualifiers describing beneficiary or purpose) rather than truncating to an isolated head noun.
6. Verbatim Open-Text Hygiene: For free-text queries, titles, and search terms, extract the raw spoken words without appending unuttered trailing punctuation marks ('?', '.') and without enclosing phrases in quotation marks unless spoken.
7. Generic Concept Fallback: When an utterance specifies a generic category noun (such as an event type or list type) without a proper name or title, retain that generic noun in the corresponding naming/title parameter rather than omitting the slot."""

    sys_prompt = f"""You are the Spoken Language Understanding (SLU) agent for the Speech Accessibility Project (SAP).
Map each spoken voice command into a valid JSON tool call conforming to the 29-tool schema below.

CANONICAL TOOLS AND PARAMETERS:
{tools_str}

{rules}

OUTPUT FORMAT:
Respond with ONLY a valid JSON object:
{{
  "domain": "<domain_name>",
  "intent": "<tool_name>",
  "slots": {{
    "<parameter_name>": "<canonical_parameter_value>"
  }}
}}
"""
    return sys_prompt

def parse_llm_json(text: str) -> dict:
    fallback = {"domain": "error", "intent": "error", "slots": {}}
    if not text:
        return fallback
    clean = text.strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        clean = match.group(0)
    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            domain = str(data.get("domain", "")).strip().lower()
            intent = str(data.get("intent", "")).strip().lower()
            slots = data.get("slots", {})
            if not isinstance(slots, dict):
                slots = {}
            return {"domain": domain, "intent": intent, "slots": slots}
    except Exception:
        pass
    return fallback

def evaluate_predictions(predictions: list, df: pd.DataFrame) -> dict:
    total_commands = len(df)
    correct_intent = 0
    valid_structure = 0
    total_slots = 0
    correct_slots = 0
    frame_acc_correct = 0
    failures = []

    for idx, row in df.iterrows():
        p = predictions[idx]
        gold_intent = str(row["intent"]).strip().lower()
        pred_intent = p["intent"]

        gold_slots = {}
        if pd.notna(row["slots"]):
            try:
                gold_slots = json.loads(row["slots"]) if isinstance(row["slots"], str) else row["slots"]
            except Exception:
                gold_slots = {}
        pred_slots = p["slots"]

        if pred_intent != "error" and isinstance(pred_slots, dict):
            valid_structure += 1

        is_intent_correct = (pred_intent == gold_intent)
        if is_intent_correct:
            correct_intent += 1

        cmd_frame_perfect = is_intent_correct
        for k, v in gold_slots.items():
            total_slots += 1
            if not is_intent_correct:
                cmd_frame_perfect = False
                failures.append({
                    "id": row.get("gold_id", idx),
                    "prompt": row.get("prompt", ""),
                    "reason": "Intent Mismatch",
                    "slot": k,
                    "gold_val": v,
                    "pred_val": None,
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent
                })
            elif k not in pred_slots:
                cmd_frame_perfect = False
                failures.append({
                    "id": row.get("gold_id", idx),
                    "prompt": row.get("prompt", ""),
                    "reason": "Missing Slot",
                    "slot": k,
                    "gold_val": v,
                    "pred_val": None,
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent
                })
            else:
                pred_v_clean = str(pred_slots[k]).lower().strip()
                gold_v_clean = str(v).lower().strip()
                if pred_v_clean == gold_v_clean:
                    correct_slots += 1
                else:
                    cmd_frame_perfect = False
                    failures.append({
                        "id": row.get("gold_id", idx),
                        "prompt": row.get("prompt", ""),
                        "reason": "Value Mismatch",
                        "slot": k,
                        "gold_val": v,
                        "pred_val": pred_slots[k],
                        "gold_intent": gold_intent,
                        "pred_intent": pred_intent
                    })

        if cmd_frame_perfect:
            frame_acc_correct += 1

    return {
        "ts": correct_intent / total_commands if total_commands else 0,
        "tcs": valid_structure / total_commands if total_commands else 0,
        "pf": correct_slots / total_slots if total_slots else 0,
        "frame_acc": frame_acc_correct / total_commands if total_commands else 0,
        "pf_correct": correct_slots,
        "total_slots": total_slots,
        "failures": failures
    }

def main():
    csv_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/decoded_benchmark_291_results.csv"
    model_id = "Qwen/Qwen2.5-7B-Instruct"
    batch_size = 24

    print("=== Running Generalized SLU Prompt Iteration 3 ===")
    df = pd.read_csv(csv_path)
    tools_str = build_tools_catalog_iter3()
    sys_prompt = build_prompt_iter3(tools_str)

    print(f"System Prompt Length: {len(sys_prompt)} chars (~{len(sys_prompt)//4} tokens)")

    print(f"Loading Model {model_id} into VRAM...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, truncation_side="left")
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()
    print("Model ready in VRAM.\n")

    prompts_text = df["prompt"].fillna("").tolist()
    t_start = time.time()
    preds = []

    for i in range(0, len(prompts_text), batch_size):
        b_texts = prompts_text[i : i + batch_size]
        m_batch = [
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Spoken Transcript: \"{text}\""}
            ]
            for text in b_texts
        ]
        fmt = [tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=True) for m in m_batch]
        inps = tokenizer(fmt, return_tensors="pt", padding=True, truncation=True, max_length=4096)
        inps = {k: v.to(device) for k, v in inps.items()}
        with torch.no_grad():
            gen_ids = model.generate(
                **inps,
                max_new_tokens=96,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id
            )
        in_len = inps["input_ids"].shape[1]
        gen_tokens = gen_ids[:, in_len:]
        decoded = tokenizer.batch_decode(gen_tokens, skip_special_tokens=True)
        for dec in decoded:
            preds.append(parse_llm_json(dec))

    elapsed = time.time() - t_start
    eval_res = evaluate_predictions(preds, df)

    print(f"\n{'='*70}")
    print(f"ITERATION 3 EVALUATION RESULTS ({elapsed:.1f}s)")
    print(f"{'='*70}")
    print(f"  • Tool Selection (TS):    {eval_res['ts']*100:.2f}% ({int(eval_res['ts']*len(df))} / {len(df)} commands)")
    print(f"  • Structure (TCS):        {eval_res['tcs']*100:.2f}%")
    print(f"  • Parameter Filling (PF): {eval_res['pf']*100:.2f}% ({eval_res['pf_correct']} / {eval_res['total_slots']} slots)")
    print(f"  • Command Frame Accuracy: {eval_res['frame_acc']*100:.2f}% ({int(eval_res['frame_acc']*len(df))} / {len(df)} commands)")
    print(f"  • Total Slot Failures:    {len(eval_res['failures'])}")
    print(f"{'='*70}\n")

    out_dir = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291"
    out_summary = os.path.join(out_dir, "iter3_generalized_summary.json")
    out_csv = os.path.join(out_dir, "iter3_generalized_predictions.csv")

    df["iter3_pred_intent"] = [p["intent"] for p in preds]
    df["iter3_pred_slots"] = [json.dumps(p["slots"]) for p in preds]
    df["iter3_pred_domain"] = [p["domain"] for p in preds]
    df.to_csv(out_csv, index=False)

    summary_data = {
        "iteration": 3,
        "ts": eval_res["ts"],
        "tcs": eval_res["tcs"],
        "pf": eval_res["pf"],
        "frame_acc": eval_res["frame_acc"],
        "pf_correct": eval_res["pf_correct"],
        "total_slots": eval_res["total_slots"],
        "failures_count": len(eval_res["failures"]),
        "failures": eval_res["failures"]
    }
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    print(f"Saved predictions to: {out_csv}")
    print(f"Saved failure analysis to: {out_summary}")

if __name__ == "__main__":
    main()
