#!/usr/bin/env python3
"""
Clean Generalized SLU Prompt — Round 3 (Clean Iteration 12)
Abstract Semantic Boundary Refinement:
- Disambiguates domain-specific queries (medication side effects, reminders, calendar schedule, venue accessibility) from open-domain qa_search.
- Strict closed-enum mappings for accessibility_ui_scale (text_size vs zoom vs screen), order_manage (status vs return), media_volume (set vs mute), iot_device_power (on/off for lock/unlock).
- Universal constituent inflection preservation: enforces retaining spoken plural forms without lemmatization, and preserving leading determiners/quantifiers.
- ZERO benchmark phrases or entities (verified by verify_no_leakage.py).
"""

import os
import sys
import time
import json
import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def build_tools_catalog_clean_r3() -> str:
    catalog = """- accessibility_dictation_toggle [accessibility] - Enable or disable speech-to-text dictation input: state: ['on', 'off', 'enable', 'disable']
- accessibility_ui_scale [accessibility] - Adjust device display accessibility settings (screen display brightness, screen display zoom magnification, text font size, high contrast): direction: ['up', 'down', 'in', 'out'], ui_element: ['zoom', 'text_size', 'high_contrast', 'screen'] (select 'text_size' for text or font size; select 'zoom' for screen zoom or magnification; select 'screen' for screen display brightness; select 'high_contrast' for contrast)
- alarm_manage [calendar_alarm] - Set, query, snooze, view, or cancel clock alarms and countdown timers (handles clock wake-up alarms, countdown kitchen timers, and checking remaining timer duration; select 'query' for checking how much time remains on an active countdown timer; calendar events belong to schedule_manage): action: ['set', 'cancel', 'query', 'snooze'], time (Clock time or countdown duration), date (Alarm calendar date), general_frequency: ['daily', 'weekdays', 'weekends', 'weekly', 'monthly']
- schedule_manage [calendar_alarm] - Create, delete, update, or view calendar appointments, meetings, daily schedule, agendas, task reminders, and personal agendas (handles all calendar appointments, scheduled meetings, and checking personal schedule or task reminders; select 'delete' for cancel/delete/remove; select 'update' for reschedule/edit; select 'query' for checking reminders, upcoming meetings, or daily agenda): action: ['create', 'delete', 'query', 'update'], title (Event title, topic, task description, or generic event category noun like reminder, reminders, meeting, appointment), date (Calendar day, holiday, or relative date expression), time (Clock time or meal timestamp), person (Attendee or participant name)
- call_make [communication] - Place outgoing voice or video telephone calls to a contact or business: recipient_name (Recipient person or business being called; retain descriptive recipient phrases like nearest pharmacy, local dry cleaner, or contact names), phone_number (Telephone digits)
- call_manage [communication] - Manage active incoming or connected telephony and intercom calls: action: ['answer', 'decline', 'hang_up', 'mute', 'unmute', 'redial']
- messages_manage [communication] - Send, read, or reply to SMS or instant chat text messages: action: ['send', 'read', 'reply'], recipient (Recipient contact name or phone number), message_body (Dictated message text)
- email_manage [communication] - Compose, send, search, or read electronic mail messages (handles all email communication including asking about missed or received emails; select 'read' for checking or viewing missed emails; 'search' for searching inbox): action: ['send', 'read', 'search'], recipient (Recipient email address or contact name), date (Date filter for email lookup), message_body (Dictated body content)
- health_medication_reminder [health] - Schedule or view reminders specifically for taking prescription pharmaceutical drugs, pills, or medical supplements (strictly for medical drugs; general tasks, chores, and appointments belong to schedule_manage): medication (Prescription drug or supplement name ONLY), time (Intake time or meal reference)
- health_refill_query [health] - Check prescription medication refill status or pharmacy availability: medication (Prescription drug name)
- health_info_query [health] - Inquire about prescription pharmaceutical drug side effects, adverse reactions, dosages, contraindications, or interactions (all questions inquiring about medication side effects, drug dosages, or medical adverse effects route strictly here, never qa_search): medication (Prescription drug or supplement name), info_type: ['side_effects', 'dosage', 'interactions', 'refill']
- qa_search [general_qa] - Answer open-domain factual, general knowledge, travel suggestions (e.g. things to do in a city), world clock (current time in a distant city), calendar trivia, word definitions, cooking recipes, encyclopedic, song release dates, audio recognition (e.g. identifying what music is playing), virtual assistant speech (e.g. asking the assistant to sing), or web image queries (STRICTLY non-medical and non-domain: all medication side effects and dosages route to health_info_query; calendar and meeting inquiries route to schedule_manage; commercial store hours and wheelchair accessibility route to places_search; flight status routes to transit_lookup; road commute traffic routes to maps_route): query (Factual question clause, search topic, or word stripped of conversational carrier request prefixes and trailing punctuation; for playful assistant commands or coin toss queries retain the command phrase)
- weather_query [general_qa] - Check outdoor meteorological atmospheric conditions, weather forecasts, precipitation, rain, snow, and ambient temperature (strictly for outdoor meteorological atmospheric conditions; road commute traffic belongs to maps_route; world clock in cities belongs to qa_search; indoor room temperature belongs to iot_sensor_query): date (Forecast date, calendar day, or relative day expression for weather; never put into place_name), place_name (Geographic city, town, state, country, or region ONLY; omit if no geographic location is mentioned; never put dates or holidays here), weather_aspect (Specific meteorological condition asked about, e.g. rain, snow, temperature, wind, umbrella; omit if asking about general weather or conditions)
- device_find [general_qa] - Ring or locate a misplaced personal handheld electronic hardware gadget (phones, tablets, ear buds, remotes): device_type (Electronic device noun phrase)
- order_manage [general_qa] - Track delivery status, view, or report problems/returns for commercial online merchandise orders (handles order tracking, shipping status, cancellations, and reporting wrong or damaged items received; select 'status' for delivery arrival or shipping inquiries; select 'return' for wrong items or returns; select 'cancel' for cancellations): action: ['track', 'cancel', 'return', 'status']
- maps_route [maps_places] - Calculate navigation routes, driving directions, travel distances, and road/commute traffic conditions (handles all questions about road commute traffic, navigation routes, driving directions, and travel distances to any location, not weather_query): destination (Target geographic arrival point, destination city, or state; never use place_name), origin (Starting geographic departure point), query_type: ['directions', 'distance', 'traffic'] (always populate for maps_route: select 'directions' for navigation and routing requests; 'distance' for distance inquiries; 'traffic' for road traffic conditions)
- places_search [maps_places] - Search for local commercial establishments, venues, public points of interest, transit stops, commercial store operating hours (e.g. whether a business or pharmacy is currently open, store hours), and public venue accessibility status (e.g. wheelchair accessibility of a building or venue): business_name (Brand or venue title), business_type (Commercial, facility, or public place category; retain exact spoken noun form without singularizing plurals), sort_by: ['rating', 'distance', 'relevance'] (Ordering criterion: select 'distance' for proximity queries like nearby, nearest, closest; omit if no ranking or proximity criterion is requested)
- reservations_manage [maps_places] - Book, manage, or query dining reservations and hospitality appointments: business_name (Restaurant or hospitality venue title), time (Reservation timestamp), date (Reservation calendar day), party_size (Guest headcount)
- media_play [media] - Start or resume playback of specific songs, audiobooks, podcasts, videos, or streaming channels: media_type: ['music', 'podcast', 'radio', 'audiobook', 'movie', 'tv_show'] (select 'audiobook' when books or reading are requested; do not put streaming platforms here), title (Track, album, podcast show, or book title; omit carrier qualifiers), artist (Musician, band, or host), service (Streaming app or platform name), house_place (Residential playback room; extract ONLY the room name like kitchen, bedroom, office, living room, omitting trailing fixture words like 'speakers')
- media_search [media] - Browse or discover available playable streaming catalog titles on device (strictly for finding on-device playable streaming media; general trivia about movies, box office, theater showtimes, or web movie lists belong to qa_search): media_type: ['movie', 'tv_show', 'music', 'podcast', 'audiobook'], person (Actor, director, musician, or podcast host), genre (Genre classification), title (Franchise or title search string)
- media_control [media] - Control active audio/video playback state (pause, resume, stop, skip to next track or chapter, previous): action: ['pause', 'resume', 'stop', 'next', 'previous', 'like', 'dislike', 'fast_forward', 'rewind'] (use 'next' for skip/next track/chapter), duration (Scrubbing offset or seek duration)
- media_volume [media] - Adjust or mute hardware audio output volume level: action: ['up', 'down', 'mute', 'unmute', 'set'] (select 'set' for adjusting to a specific absolute level, minimum, or maximum; select 'mute' only when the user explicitly commands mute or silence; 'up'/'down' for relative adjustments), change_amount (Offset step or target absolute level)
- lists_manage [notes_memory] - Create, view, add items to, or remove items from personal lists: action: ['create', 'add', 'remove', 'query'], list_name (Target list full noun phrase title; when creating or querying a list, populate with the list name being created/queried), item (Complete item noun phrase or full coordinated list of items being added or removed, including beneficiary phrases; omit for list creation or query actions)
- memory_note_manage [notes_memory] - Store or recall personal factual notes, user memory, personal attributes, and remembered locations (e.g. storing or recalling personal details, colors, locations of items, parking spaces, locker combinations): action: ['store', 'recall'], key (Associative topic or attribute noun phrase), value (Fact content or stored value)
- iot_device_power [smart_home] - Turn power on or off, or physically lock/unlock smart home hardware devices, appliances, and fixtures: device_type (Fixture, appliance, or device type noun phrase as spoken, including determiners and modifiers; separate from room location), state: ['on', 'off'] (select 'on' for turn on, power up, or lock; select 'off' for turn off, power down, or unlock), house_place (Residential room or outdoor zone)
- iot_device_adjust [smart_home] - Adjust continuous physical settings on smart home household appliances (e.g. dimming or brightening physical light bulbs, setting thermostat temperature, adjusting fan speed; strictly for modifying settings, not for querying current readings; NOT the assistant device screen display): device_type (Target hardware appliance), setting: ['brightness', 'temperature', 'color', 'speed'], direction: ['up', 'down'], value (Target absolute setting with units)
- iot_sensor_query [smart_home] - Check readings, indoor room temperature, current thermostat settings, physical door/window open/closed states, or motion detection from smart home indoor residential hardware sensors (strictly for residential home sensors; commercial store hours and public venue wheelchair accessibility belong to places_search): sensor_type: ['temperature', 'motion', 'lock', 'contact'], device_type (Hardware device target), room (Room or residential zone)
- rideshare_book [transport] - Request hailing or dispatch of on-demand passenger vehicles: destination (Drop-off location)
- transit_lookup [transport] - Query departure timetables, schedule arrivals, public transit line routes, and commercial travel/flight status (finding commercial flights, trains, and buses, or checking flight status): transit_type: ['train', 'bus', 'flight'], destination (Arrival stop, station, or city), route_or_station (Public transit line name, station, or carrier), time (Departure or arrival timestamp)"""
    return catalog

def build_prompt_clean_r3(tools_str: str) -> str:
    rules = """UNIVERSAL EXTRACTION RULES:
1. Closed Tool Catalog: The 'intent' MUST be selected strictly from the 29 canonical tool names listed above. Never invent, modify, or substitute unlisted tool names.
2. Closed Enum Adherence: When a parameter declares a list of allowable options in brackets [...], select strictly from that list. Never output an unlisted verb, synonym, or out-of-vocabulary word:
   - For schedule_manage action, output 'delete' for cancel/delete/remove, 'update' for reschedule/edit, and 'query' for viewing/checking.
   - For iot_device_power state, output 'off' for unlock/turn off; output 'on' for lock/turn on.
   - For accessibility_ui_scale ui_element, output strictly 'text_size' for text or font size, 'zoom' for screen zoom or magnification, 'screen' for screen display brightness, and 'high_contrast' for contrast.
   - For media_volume action, output 'set' for target levels like minimum, maximum, or numerical levels; output 'mute' strictly for silence/mute commands.
   - For media_play media_type, output 'audiobook' when books or reading are requested.
   - For media_control action, output 'next' for skip or next track.
   - For order_manage action, output 'status' for arrival date or shipping inquiries; output 'return' for wrong items or returns.
   - For maps_route query_type, always populate: 'directions' for navigation/driving requests; 'distance' for distance inquiries; 'traffic' for road traffic conditions.
3. Domain Tool Routing vs Open-Domain QA: Specialised voice commands MUST route to their respective domain tools, never to qa_search:
   - Medication and pharmaceutical drug queries route to health_info_query.
   - Calendar events, appointments, reminders, and daily agenda inquiries route to schedule_manage.
   - Store operating hours and public venue wheelchair accessibility route to places_search.
   - Commercial travel and flight status route to transit_lookup.
   - Road traffic conditions, driving routes, and distance route to maps_route.
   - Personal memory notes and remembered locations route to memory_note_manage.
4. Semantic Role Alignment & Minimal Slot Invariance: Assign extracted spans to parameters whose descriptive definition matches the semantic entity. Assign temporal and calendar expressions (including holidays, days of the week, relative days) strictly to date/time parameters, never to place_name or location parameters. Extract only parameters that are explicitly mentioned or directly implied in the user utterance; omit unmentioned keys from 'slots'. Never invent default values.
5. Constituent Span & Inflection Preservation: For all free-text slots and category types (including business_type, item, list_name, device_type):
   - NEVER lemmatize or singularize plural nouns to singular forms (retain exact plural forms as spoken, such as restaurants, museums, shopping malls, switches).
   - Retain leading quantifiers and determiners (such as all lamps, both monitors) in device_type.
   - Retain meal timestamps exactly as spoken (e.g. breakfast time, dinner time).
   - In media_play house_place, extract only the room name, omitting trailing words like 'speakers'.
   - Retain complete coordinated lists of items in the item parameter.
   - Retain natural words without converting to snake_case.
6. Strict Free-Text Punctuation Hygiene: Spoken voice commands never contain written punctuation. For ALL free-text values (query, title, item, message), ALWAYS remove sentence-final punctuation marks ('?', '.', '!') and omit enclosing quotes. For qa_search query, extract the factual question clause or topic stripped of conversational carrier request prefixes (such as polite requests or opening carrier clauses). For virtual assistant playful commands or games (such as tossing a coin or singing), retain the full command phrase."""

    sys_prompt = f"""You are the Spoken Language Understanding (SLU) agent for the Speech Accessibility Project (SAP).
Map each spoken voice command into a valid JSON tool call conforming to the 29-tool schema below.

CANONICAL TOOLS AND PARAMETERS:
{tools_str}

{rules}

OUTPUT FORMAT:
Respond with ONLY a valid JSON object. All slot string values must be lowercase or title text WITHOUT trailing punctuation marks ('?', '.', '!'):
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
        if pd.notna(row.get("slots")):
            raw_s = str(row["slots"]).strip()
            if raw_s:
                try:
                    gold_slots = json.loads(raw_s)
                except Exception:
                    pass

        pred_slots = p.get("slots", {})

        is_intent_correct = (gold_intent == pred_intent)
        if is_intent_correct:
            correct_intent += 1

        is_struct_valid = bool(p.get("domain") != "error" and p.get("intent") != "error")
        if is_struct_valid:
            valid_structure += 1

        # Slot evaluation
        cmd_slots_count = len(gold_slots)
        cmd_correct_slots = 0

        for k, v in gold_slots.items():
            total_slots += 1
            if not is_intent_correct:
                failures.append({
                    "id": row.get("gold_id", f"idx_{idx}"),
                    "prompt": row.get("prompt", ""),
                    "reason": "Intent Mismatch",
                    "slot": k,
                    "gold_val": v,
                    "pred_val": None,
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent
                })
                continue

            if k not in pred_slots:
                failures.append({
                    "id": row.get("gold_id", f"idx_{idx}"),
                    "prompt": row.get("prompt", ""),
                    "reason": "Missing Slot",
                    "slot": k,
                    "gold_val": v,
                    "pred_val": None,
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent
                })
            else:
                pred_v = str(pred_slots[k]).strip().lower().rstrip("?.!")
                gold_v = str(v).strip().lower().rstrip("?.!")
                if pred_v == gold_v:
                    correct_slots += 1
                    cmd_correct_slots += 1
                else:
                    failures.append({
                        "id": row.get("gold_id", f"idx_{idx}"),
                        "prompt": row.get("prompt", ""),
                        "reason": "Value Mismatch",
                        "slot": k,
                        "gold_val": gold_v,
                        "pred_val": pred_v,
                        "gold_intent": gold_intent,
                        "pred_intent": pred_intent
                    })

        if is_intent_correct and (cmd_correct_slots == cmd_slots_count):
            frame_acc_correct += 1

    ts = correct_intent / total_commands if total_commands > 0 else 0.0
    tcs = valid_structure / total_commands if total_commands > 0 else 0.0
    pf = correct_slots / total_slots if total_slots > 0 else 0.0
    frame_acc = frame_acc_correct / total_commands if total_commands > 0 else 0.0

    return {
        "round": "clean_r3",
        "ts": ts,
        "tcs": tcs,
        "pf": pf,
        "frame_acc": frame_acc,
        "pf_correct": correct_slots,
        "total_slots": total_slots,
        "failures_count": len(failures),
        "failures": failures
    }

def main():
    csv_path = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/unique_benchmark_dev_291.csv"
    if not os.path.exists(csv_path):
        csv_path = "sap-dialog-system/unique_benchmark_dev_291.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    print(f"=== Running Clean Generalized SLU Prompt Round 3 (Clean Iteration 12) ===")
    print(f"Loaded {len(df)} benchmark commands from {csv_path}")

    tools_str = build_tools_catalog_clean_r3()
    sys_prompt = build_prompt_clean_r3(tools_str)
    print(f"System Prompt Length: {len(sys_prompt)} chars (~{len(sys_prompt)//4} tokens)")

    model_name = "Qwen/Qwen2.5-7B-Instruct"
    print(f"Loading Model {model_name} into VRAM...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_name, padding_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype=torch.bfloat16
    )
    # Strictly low-temperature deterministic greedy decoding
    model.generation_config.temperature = None
    model.generation_config.top_p = None
    model.generation_config.top_k = None
    model.generation_config.do_sample = False
    print(f"Model ready in VRAM with strictly low-temperature greedy decoding (do_sample=False).")

    prompts_to_process = df["prompt"].tolist()
    batch_size = 16
    predictions = []

    t_infer_start = time.time()
    for i in range(0, len(prompts_to_process), batch_size):
        batch_prompts = prompts_to_process[i:i+batch_size]
        batch_inputs = []
        for p in batch_prompts:
            user_text = f"Input Utterance: \"{p}\""
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text}
            ]
            batch_inputs.append(tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True))

        inputs = tokenizer(batch_inputs, return_tensors="pt", padding=True, truncation=True).to("cuda")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=180,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id
            )

        for j, out in enumerate(outputs):
            input_len = inputs["input_ids"][j].shape[0]
            gen_tokens = out[input_len:]
            gen_text = tokenizer.decode(gen_tokens, skip_special_tokens=True)
            parsed = parse_llm_json(gen_text)
            predictions.append(parsed)

    elapsed = time.time() - t_infer_start
    results = evaluate_predictions(predictions, df)

    print("\n" + "="*70)
    print(f"CLEAN ROUND 3 EVALUATION RESULTS ({elapsed:.1f}s)")
    print("="*70)
    print(f"  • Tool Selection (TS):    {results['ts']*100:.2f}% ({int(results['ts']*len(df))} / {len(df)} commands)")
    print(f"  • Structure (TCS):        {results['tcs']*100:.2f}%")
    print(f"  • Parameter Filling (PF): {results['pf']*100:.2f}% ({results['pf_correct']} / {results['total_slots']} slots)")
    print(f"  • Command Frame Accuracy: {results['frame_acc']*100:.2f}% ({int(results['frame_acc']*len(df))} / {len(df)} commands)")
    print(f"  • Total Slot Failures:    {results['failures_count']}")
    print("="*70 + "\n")

    # Save predictions
    df_out = df.copy()
    df_out["clean_r3_pred_intent"] = [p["intent"] for p in predictions]
    df_out["clean_r3_pred_slots"] = [json.dumps(p["slots"]) for p in predictions]
    df_out["clean_r3_pred_domain"] = [p["domain"] for p in predictions]

    out_csv = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/clean_r3_predictions.csv"
    if not os.path.exists(os.path.dirname(out_csv)):
        out_csv = "sap-dialog-system/clean_r3_predictions.csv"
    df_out.to_csv(out_csv, index=False)
    print(f"Saved predictions to: {out_csv}")

    out_json = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291/clean_r3_summary.json"
    if not os.path.exists(os.path.dirname(out_json)):
        out_json = "sap-dialog-system/clean_r3_summary.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved failure analysis to: {out_json}")

if __name__ == "__main__":
    main()
