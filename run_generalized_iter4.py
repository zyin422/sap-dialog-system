#!/usr/bin/env python3
"""
Generalized SLU Prompt — Iteration 4
Modifications in Canonical Tools and Parameters & Universal Rules:
1. weather_query: Placed 'date' before 'place_name' and clarified that holidays/relative dates belong to 'date', not 'place_name'. Specified that 'weather_aspect' is omitted for general weather queries.
2. lists_manage.list_name: Updated example to complete noun phrases (e.g. shopping list, gift list) to prevent truncating 'list'.
3. places_search: Clarified business_type preserves spoken form; added 'omit if no ranking requested' to sort_by to prevent false default relevance predictions.
4. accessibility_ui_scale vs iot_device_adjust: Clarified screen display settings (screen brightness, zoom) belong to accessibility_ui_scale, while physical household smart appliances belong to iot_device_adjust.
5. memory_note_manage vs device_find: Clarified personal notes and locations (parking spaces, parked car) belong to memory_note_manage, while device_find is strictly for physical electronic hardware gadgets.
6. qa_search: Clarified handling of world clock/current time, definitions, recipes, and sports scores; ensured query retains the spoken query phrase.
7. health_medication_reminder vs schedule_manage: Clarified that pills/pharmaceuticals belong to medication reminder, while general queries ('what are my reminders', reservations) belong to schedule_manage.
8. schedule_manage & media_volume: Explicitly documented enum semantic mappings in parameter brackets (cancel -> delete; reschedule -> update; minimum/maximum -> set).
9. Universal Rule 5 (Morphological & Format Hygiene): Explicitly required preserving plural/singular forms as uttered and natural spaces (no snake_casing).
10. Universal Rule 6 (Spoken Text Hygiene): Required stripping sentence-final punctuation ('?', '.', '!') from all free-text fields.
"""

import os
import sys
import time
import json
import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def build_tools_catalog_iter4() -> str:
    catalog = """- accessibility_dictation_toggle [accessibility] - Enable or disable speech-to-text dictation mode: state: ['on', 'off', 'enable', 'disable']
- accessibility_ui_scale [accessibility] - Adjust device display settings such as screen brightness, zoom magnification, text size, or contrast: direction: ['up', 'down', 'in', 'out'], ui_element: ['zoom', 'text_size', 'high_contrast', 'screen']
- alarm_manage [calendar_alarm] - Set, query, snooze, or cancel clock alarms, wake-up alarms, and countdown timers: action: ['set', 'cancel', 'query', 'snooze'], time (Clock time or timer duration), date (Alarm date), general_frequency: ['daily', 'weekdays', 'weekends', 'weekly', 'monthly']
- schedule_manage [calendar_alarm] - Create, delete, update, or view calendar appointments, meetings, events, and general task reminders (including 'what are my reminders', reservations, chores; not pills or clock alarms): action: ['create', 'delete', 'query', 'update'] (map 'cancel' to 'delete'; map 'reschedule' to 'update'), title (Event title, topic, task description, or generic category noun e.g. meeting, appointment, event, call, reminder; populate even if only the generic category noun is mentioned), date (Calendar day, holiday, or relative date expression), time (Clock time or meal timestamp), person (Attendee or participant name)
- call_make [communication] - Place outgoing voice or video telephone calls to a contact or business (triggered by 'call <recipient>'): recipient_name (Recipient person or business being called), phone_number (Telephone digits)
- call_manage [communication] - Manage active incoming or connected telephony calls: action: ['answer', 'decline', 'hang_up', 'mute', 'unmute', 'redial']
- messages_manage [communication] - Send, read, or reply to SMS or instant chat text messages: action: ['send', 'read', 'reply'], recipient (Recipient contact name or phone number), message_body (Dictated message text)
- email_manage [communication] - Compose, send, search, or read electronic mail messages: action: ['send', 'read', 'search'], recipient (Recipient email address or contact name), date (Date filter for email lookup), message_body (Dictated body content)
- qa_search [general_qa] - Answer open-domain factual, informational, current time/world clock, definition, recipe, encyclopedic, song release date, audio recognition, or web image queries: query (Core factual search query or question phrase, stripped of carrier wake phrases)
- weather_query [general_qa] - Check meteorological weather conditions, forecasts, and temperature: date (Forecast date, calendar day, holiday, or relative day expression like today, tomorrow, weekend; never put into place_name), place_name (Geographic city, town, state, country, or region ONLY; omit if no geographic location is mentioned; never put dates or holidays here), weather_aspect (Specific meteorological condition asked about, e.g. rain, snow, temperature, wind, umbrella; omit if asking about general weather or conditions)
- device_find [general_qa] - Locate, ping, or ring a misplaced personal physical hardware/electronic device (phones, tablets, remotes; NOT parking spaces or vehicles): device_type (Target misplaced hardware device noun phrase)
- order_manage [general_qa] - Track delivery status, view, or cancel commercial online merchandise orders: action: ['track', 'cancel', 'return', 'status']
- health_medication_reminder [health] - Schedule or view reminders specifically for taking prescription pharmaceutical drugs, pills, or medical supplements (strictly for medical pills/drugs; all general task reminders, dinner reservations, and appointments belong to schedule_manage): medication (Prescription drug or supplement name ONLY), time (Intake time or meal reference)
- health_refill_query [health] - Check prescription medication refill status or pharmacy availability: medication (Prescription drug name)
- health_info_query [health] - Inquire about prescription pharmaceutical drug dosages, contraindications, or adverse effects: medication (Prescription drug name), info_type: ['side_effects', 'dosage', 'interactions', 'refill']
- maps_route [maps_places] - Calculate navigation routes, driving directions, travel distances, and commute traffic: destination (Target geographic arrival point), origin (Starting geographic departure point), query_type: ['directions', 'distance', 'traffic']
- places_search [maps_places] - Search for local commercial establishments, points of interest, store hours, and facilities: business_name (Brand or venue title), business_type (Commercial or facility category as spoken), sort_by: ['rating', 'distance', 'relevance'] (Ordering criterion: select 'distance' for proximity queries like nearby, nearest, closest; omit if no ranking or proximity criterion is requested)
- reservations_manage [maps_places] - Book, manage, or query dining reservations and hospitality appointments: business_name (Restaurant or hospitality venue title), time (Reservation timestamp), date (Reservation calendar day), party_size (Guest headcount)
- media_play [media] - Start or resume playback of specific songs, audiobooks, podcasts, videos, or streaming channels: media_type: ['music', 'podcast', 'radio', 'audiobook', 'movie', 'tv_show'] (map 'book' or 'audio book' to 'audiobook'), title (Track, album, show, or book title; omit carrier qualifiers like 'the latest episode of'), artist (Musician, band, or host), service (Streaming app or platform e.g. youtube, spotify), house_place (Residential playback room)
- media_search [media] - Browse or discover available playable streaming catalog titles on device (does not answer trivia, release dates, or audio recognition): media_type: ['movie', 'tv_show', 'music', 'podcast', 'audiobook'], person (Actor, director, musician, or podcast host), genre (Genre classification), title (Franchise or title search string)
- media_control [media] - Control active audio/video playback state: action: ['pause', 'resume', 'stop', 'next', 'previous', 'like', 'dislike', 'fast_forward', 'rewind'], duration (Scrubbing offset or seek duration)
- media_volume [media] - Adjust or mute hardware audio output volume level: action: ['up', 'down', 'mute', 'unmute', 'set'] (select 'set' for adjusting to a specific absolute level or minimum/maximum; 'mute' to silence), change_amount (Offset step or target absolute level)
- lists_manage [notes_memory] - Create, view, add items to, or remove items from personal lists: action: ['create', 'add', 'remove', 'query'], item (Item noun phrase or conjunction phrase), list_name (Target list full noun phrase title, e.g. shopping list, grocery list, gift list, to-do list; extract the complete noun phrase)
- memory_note_manage [notes_memory] - Store or recall personal factual notes, personal locations (e.g. where car is parked, parking space, locker number), attributes, and user-specified memory items: action: ['store', 'recall'], key (Associative subject/attribute key e.g. parking space, park, locker), value (Verbatim fact content or stored value)
- iot_device_power [smart_home] - Turn power on or off for smart home hardware devices, appliances, and fixtures: device_type (Fixture, appliance, or device type noun phrase as spoken, e.g. light, fan, switches, heat; do not normalize heat to thermostat; separate from room location), state: ['on', 'off'], house_place (Residential room or outdoor zone e.g. porch, kitchen)
- iot_device_adjust [smart_home] - Adjust continuous physical settings on smart home household appliances (e.g. light brightness, thermostat temperature, fan speed; NOT device screen display): device_type (Target hardware appliance), setting: ['brightness', 'temperature', 'color', 'speed'], direction: ['up', 'down'], value (Target absolute setting with units)
- iot_sensor_query [smart_home] - Check readings, open/closed contact states, or detection from smart home sensors: sensor_type: ['temperature', 'motion', 'lock', 'contact'], device_type (Hardware device target), room (Room or residential zone)
- rideshare_book [transport] - Request hailing or dispatch of on-demand passenger vehicles: destination (Drop-off location)
- transit_lookup [transport] - Query departure timetables, schedule arrivals, and lines for public scheduled transit (buses, trains, commercial flights): transit_type: ['train', 'bus', 'flight'], destination (Arrival stop, station, or city), route_or_station (Public transit line name, station, or carrier), time (Departure or arrival timestamp)"""
    return catalog

def build_prompt_iter4(tools_str: str) -> str:
    rules = """UNIVERSAL EXTRACTION RULES:
1. Closed Tool Catalog: The 'intent' MUST be selected strictly from the 29 canonical tool names listed above. Never invent, modify, or substitute unlisted tool names.
2. Closed Enum Adherence: When a parameter declares a list of allowable options in brackets [...], select strictly from that list. If an utterance uses a synonymous phrasing (e.g. cancelling/dropping vs deleting, rescheduling vs updating, book vs audiobook, minimum vs set), select the canonical enum that represents that semantic function.
3. Semantic Role Alignment: Assign extracted spans to parameters whose descriptive definition matches the semantic entity. Specifically, assign temporal and calendar expressions (including holidays, days of the week, relative days) strictly to date/time parameters, never to place_name or location parameters.
4. Minimal Slot Invariance: Extract only parameters that are explicitly mentioned or directly implied in the user utterance. If a parameter is not mentioned, omit that key from the 'slots' dictionary. Never invent default or unuttered values.
5. Constituent Span & Morphology Preservation: For open-vocabulary text parameters, extract the complete descriptive noun phrase or clause constituent (preserving modifying adjectives, compound elements, and trailing prepositional qualifiers). Preserve verbatim morphological inflections (keep plural or singular forms exactly as uttered without lemmatizing or singularizing) and retain natural words without converting to snake_case or canonical abstractions.
6. Spoken Text Hygiene: Spoken voice commands do not contain written punctuation. For all free-text query, title, item, and message values, strip any sentence-final punctuation marks (such as '?', '.', '!') and omit enclosing quotes.
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

    print("=== Running Generalized SLU Prompt Iteration 4 ===")
    df = pd.read_csv(csv_path)
    tools_str = build_tools_catalog_iter4()
    sys_prompt = build_prompt_iter4(tools_str)

    print(f"System Prompt Length: {len(sys_prompt)} chars (~{len(sys_prompt)//4} tokens)")

    print(f"Loading Model {model_id} into VRAM...")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )
    model.eval()
    print("Model ready in VRAM.\n")

    prompts = df["prompt"].tolist()
    total = len(prompts)
    preds = []

    t_start = time.time()
    for i in range(0, total, batch_size):
        batch_prompts = prompts[i:i+batch_size]
        batch_texts = []
        for p in batch_prompts:
            msgs = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Spoken command: \"{p}\""}
            ]
            batch_texts.append(tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True))

        inps = tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True).to("cuda")
        with torch.no_grad():
            gen_ids = model.generate(
                **inps,
                max_new_tokens=150,
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
    print(f"ITERATION 4 EVALUATION RESULTS ({elapsed:.1f}s)")
    print(f"{'='*70}")
    print(f"  • Tool Selection (TS):    {eval_res['ts']*100:.2f}% ({int(eval_res['ts']*len(df))} / {len(df)} commands)")
    print(f"  • Structure (TCS):        {eval_res['tcs']*100:.2f}%")
    print(f"  • Parameter Filling (PF): {eval_res['pf']*100:.2f}% ({eval_res['pf_correct']} / {eval_res['total_slots']} slots)")
    print(f"  • Command Frame Accuracy: {eval_res['frame_acc']*100:.2f}% ({int(eval_res['frame_acc']*len(df))} / {len(df)} commands)")
    print(f"  • Total Slot Failures:    {len(eval_res['failures'])}")
    print(f"{'='*70}\n")

    out_dir = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291"
    out_summary = os.path.join(out_dir, "iter4_generalized_summary.json")
    out_csv = os.path.join(out_dir, "iter4_generalized_predictions.csv")

    df["iter4_pred_intent"] = [p["intent"] for p in preds]
    df["iter4_pred_slots"] = [json.dumps(p["slots"]) for p in preds]
    df["iter4_pred_domain"] = [p["domain"] for p in preds]
    df.to_csv(out_csv, index=False)

    summary_data = {
        "iteration": 4,
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
