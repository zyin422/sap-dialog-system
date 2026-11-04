#!/usr/bin/env python3
"""
Generalized SLU Prompt — Iteration 8
Modifications in Canonical Tools and Parameters & Universal Rules:
1. maps_route: Explicitly routes road and commute traffic inquiries ('how's the traffic to X') to maps_route with query_type='traffic'. Excluded road traffic from weather_query.
2. iot_sensor_query vs weather_query: Explicitly routed indoor room temperatures ('temperature in the living room', 'temperature inside') to iot_sensor_query; restricted weather_query strictly to outdoor weather.
3. alarm_manage vs schedule_manage: Hardened boundary ensuring all queries about active or scheduled alarms ('what alarms are set', 'do I have any alarms set', 'show me my alarms') route to alarm_manage.
4. media_volume: Included sound level adjustments ('turn down the sound', 'turn up volume').
5. transit_lookup & email_manage: Clarified routing for flight status ('is my flight on time') and inbox search ('did I miss any emails').
6. places_search.business_type: Explicitly instructed to keep exact spoken plurals ('restaurants', 'shopping malls', 'museums') without singularizing.
7. Universal Rule 6: Mandated stripping carrier imperative prefixes ('find me a', 'give me a') from search queries.
"""

import os
import sys
import time
import json
import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def build_tools_catalog_iter8() -> str:
    catalog = """- accessibility_dictation_toggle [accessibility] - Enable or disable speech-to-text dictation mode (e.g. 'start listening', 'stop listening'): state: ['on', 'off', 'enable', 'disable']
- accessibility_ui_scale [accessibility] - Adjust device display settings such as screen brightness, zoom magnification, text size, or contrast: direction: ['up', 'down', 'in', 'out'], ui_element: ['zoom', 'text_size', 'high_contrast', 'screen']
- alarm_manage [calendar_alarm] - Set, query, snooze, view, or cancel clock alarms, wake-up alarms, and countdown timers (ALL queries about alarms or timers e.g. 'what alarms are set', 'do I have any alarms set', 'show me my alarms', 'when is my next alarm', 'timer left' belong to alarm_manage, NEVER schedule_manage): action: ['set', 'cancel', 'query', 'snooze'], time (Clock time or timer duration), date (Alarm date), general_frequency: ['daily', 'weekdays', 'weekends', 'weekly', 'monthly']
- schedule_manage [calendar_alarm] - Create, delete, update, or view calendar appointments, meetings, events, and task reminders (strictly calendar events and reminders; NEVER clock alarms or countdown timers): action: ['create', 'delete', 'query', 'update'] (select 'delete' for cancel/delete/remove; select 'update' for reschedule/edit), title (Event title, topic, task description, or generic category noun e.g. reminders, meeting, appointment, event, call; populate even if only the generic category noun is mentioned), date (Calendar day, holiday, or relative date expression), time (Clock time or meal timestamp), person (Attendee or participant name)
- call_make [communication] - Place outgoing voice or video telephone calls to a contact or business (triggered by 'call <recipient>'): recipient_name (Recipient person or business being called), phone_number (Telephone digits)
- call_manage [communication] - Manage active incoming or connected telephony and doorbell intercom calls (e.g. 'answer the door', 'answer', 'decline', 'hang up', 'mute'): action: ['answer', 'decline', 'hang_up', 'mute', 'unmute', 'redial']
- messages_manage [communication] - Send, read, or reply to SMS or instant chat text messages: action: ['send', 'read', 'reply'], recipient (Recipient contact name or phone number), message_body (Dictated message text)
- email_manage [communication] - Compose, send, search, or read electronic mail messages (handles all email inbox search e.g. 'did I miss any emails from yesterday', search mail): action: ['send', 'read', 'search'], recipient (Recipient email address or contact name), date (Date filter for email lookup), message_body (Dictated body content)
- health_medication_reminder [health] - Schedule or view reminders specifically for taking prescription pharmaceutical drugs, pills, or medical supplements (strictly for medical pills/drugs; general task reminders and appointments belong to schedule_manage): medication (Prescription drug or supplement name ONLY), time (Intake time or meal reference)
- health_refill_query [health] - Check prescription medication refill status or pharmacy availability: medication (Prescription drug name)
- health_info_query [health] - Inquire about prescription pharmaceutical drug side effects, adverse reactions, dosages, contraindications, or interactions (all questions about prescription drug side effects and dosages route here, NOT qa_search): medication (Prescription drug name), info_type: ['side_effects', 'dosage', 'interactions', 'refill']
- qa_search [general_qa] - Answer open-domain factual, informational, current time/world clock (e.g. 'what time is it in X'), calendar trivia (e.g. 'when is Thanksgiving'), definition, recipe, encyclopedic, song release date, audio recognition, or web image queries (does NOT handle prescription drug side effects, store hours, flight status, or road traffic): query (Verbatim factual question clause or topic, stripped of carrier prefixes and trailing punctuation)
- weather_query [general_qa] - Check outdoor meteorological weather conditions, forecasts, precipitation, and outdoor ambient temperature (strictly for outdoor weather; indoor room temperatures belong to iot_sensor_query; road traffic belongs to maps_route; world clock belongs to qa_search): date (Forecast date, calendar day, or relative day expression for weather like today, tomorrow, weekend, or holiday weather; never put into place_name), place_name (Geographic city, town, state, country, or region ONLY; omit if no geographic location is mentioned; never put dates or holidays here), weather_aspect (Specific meteorological condition asked about, e.g. rain, snow, temperature, wind, umbrella; omit if asking about general weather or conditions)
- device_find [general_qa] - Ping, ring, or locate a misplaced personal handheld electronic gadget (phones, tablets, remotes, keys with trackers; strictly electronic hardware, never parking spots or vehicles): device_type (Electronic device noun phrase like phone, tablet, remote)
- order_manage [general_qa] - Track delivery status, view, or report problems/returns for commercial online merchandise orders: action: ['track', 'cancel', 'return', 'status']
- maps_route [maps_places] - Calculate navigation routes, driving directions, travel distances, and road/commute traffic conditions (handles all inquiries about traffic e.g. 'how's the traffic to X', directions, commute): destination (Target geographic arrival point), origin (Starting geographic departure point), query_type: ['directions', 'distance', 'traffic'] (select 'traffic' for traffic or commute conditions; select 'directions' for navigation and routing requests like navigate or directions; 'distance' for distance)
- places_search [maps_places] - Search for local commercial establishments, venues, public points of interest, transit stops (e.g. bus stop), store operating hours (e.g. 'when is Shell open until', 'is Red Lobster open today'), and facility accessibility status: business_name (Brand or venue title), business_type (Commercial, facility, or public place category; retain exact spoken noun form, keeping plurals e.g. 'restaurants', 'shopping malls', 'museums' exactly as uttered without singularizing), sort_by: ['rating', 'distance', 'relevance'] (Ordering criterion: select 'distance' for proximity queries like nearby, nearest, closest; omit if no ranking or proximity criterion is requested)
- reservations_manage [maps_places] - Book, manage, or query dining reservations and hospitality appointments: business_name (Restaurant or hospitality venue title), time (Reservation timestamp), date (Reservation calendar day), party_size (Guest headcount)
- media_play [media] - Start or resume playback of specific songs, audiobooks, podcasts, videos, or streaming channels: media_type: ['music', 'podcast', 'radio', 'audiobook', 'movie', 'tv_show'] (select 'audiobook' when books or reading are requested; do not put streaming services here), title (Track, album, podcast show, or book title; omit carrier qualifiers like 'the latest episode of'), artist (Musician, band, or host), service (Streaming app or platform e.g. youtube, spotify, pandora), house_place (Residential playback room e.g. office, living room; omit 'speakers')
- media_search [media] - Browse or discover available playable streaming catalog titles on device (strictly for finding on-device playable streaming media; general trivia about movies, box office, theater showtimes, or Wikipedia movie lists belong to qa_search): media_type: ['movie', 'tv_show', 'music', 'podcast', 'audiobook'], person (Actor, director, musician, or podcast host), genre (Genre classification), title (Franchise or title search string)
- media_control [media] - Control active audio/video playback state: action: ['pause', 'resume', 'stop', 'next', 'previous', 'like', 'dislike', 'fast_forward', 'rewind'], duration (Scrubbing offset or seek duration)
- media_volume [media] - Adjust or mute hardware audio output volume level (handles all volume and sound level adjustments e.g. 'turn down the sound', 'turn up volume', 'mute', 'decrease volume'): action: ['up', 'down', 'mute', 'unmute', 'set'] (select 'set' for adjusting to a specific numerical or minimum/maximum level; 'mute' only for silence), change_amount (Offset step or target absolute level)
- lists_manage [notes_memory] - Create, view, add items to, or remove items from personal lists: action: ['create', 'add', 'remove', 'query'], list_name (Target list full noun phrase title, e.g. shopping list, grocery list, gift list, to-do list; when creating or querying a list, populate with the list name being created/queried), item (Complete item noun phrase or full conjunction list of items being added or removed, including beneficiary phrases e.g. 'hair dryer brush for Nessa', 'paper towels and cereal'; omit for list creation or query actions)
- memory_note_manage [notes_memory] - Store or recall personal factual notes, user memory, attributes, and remembered personal locations (e.g. storing or asking where car is parked, parking space/spot color, locker combinations): action: ['store', 'recall'], key (Associative topic or attribute key e.g. park, parking space, locker; use 'park' for where parked queries), value (Verbatim fact content or stored value)
- iot_device_power [smart_home] - Turn power on or off, or lock/unlock smart home hardware devices, appliances, and fixtures: device_type (Fixture, appliance, or device type noun phrase as spoken, including quantifiers and modifiers e.g. front door, light, lights, fan, all switches, heat; do not normalize heat to thermostat; separate from room location), state: ['on', 'off'] (select 'on' for turn on, power up, or lock; select 'off' for turn off, power down, or unlock), house_place (Residential room or outdoor zone e.g. porch, kitchen, guestroom)
- iot_device_adjust [smart_home] - Adjust continuous physical settings on smart home household appliances (e.g. light brightness, thermostat temperature, fan speed; NOT device screen display): device_type (Target hardware appliance), setting: ['brightness', 'temperature', 'color', 'speed'], direction: ['up', 'down'], value (Target absolute setting with units)
- iot_sensor_query [smart_home] - Check readings, indoor room temperature (e.g. 'temperature in the living room', 'temperature inside'), physical door/window open/closed states, or detection from smart home indoor household security sensors (strictly for residential indoor sensors; outdoor weather belongs to weather_query): sensor_type: ['temperature', 'motion', 'lock', 'contact'], device_type (Hardware device target), room (Room or residential zone)
- rideshare_book [transport] - Request hailing or dispatch of on-demand passenger vehicles: destination (Drop-off location)
- transit_lookup [transport] - Query departure timetables, schedule arrivals, flight status, and lines for public scheduled transit (buses, trains, commercial flights e.g. 'is my flight on time'): transit_type: ['train', 'bus', 'flight'], destination (Arrival stop, station, or city), route_or_station (Public transit line name, station, or carrier), time (Departure or arrival timestamp)"""
    return catalog

def build_prompt_iter8(tools_str: str) -> str:
    rules = """UNIVERSAL EXTRACTION RULES:
1. Closed Tool Catalog: The 'intent' MUST be selected strictly from the 29 canonical tool names listed above. Never invent, modify, or substitute unlisted tool names.
2. Closed Enum Adherence: When a parameter declares a list of allowable options in brackets [...], select strictly from that list. Never output an unlisted verb or synonym (e.g. for schedule_manage action, output 'delete' rather than 'cancel', and 'update' rather than 'reschedule'; for iot_device_power state, output 'off' for unlock; for media_play media_type, output 'audiobook' rather than 'book'; for media_volume action, output 'set' for minimum/maximum).
3. Semantic Role Alignment: Assign extracted spans to parameters whose descriptive definition matches the semantic entity. Specifically, assign temporal and calendar expressions (including holidays, days of the week, relative days) strictly to date/time parameters, never to place_name or location parameters.
4. Minimal Slot Invariance: Extract only parameters that are explicitly mentioned or directly implied in the user utterance. If a parameter is not mentioned, omit that key from the 'slots' dictionary. Never invent default or unuttered values.
5. Constituent Span & Conjunction Preservation: For open-vocabulary text parameters, extract the complete descriptive noun phrase or clause constituent (preserving modifying adjectives, quantifiers like 'all switches', compound elements, and trailing prepositional qualifiers like 'for Nessa'). When multiple items are coordinated in a conjunction (e.g. 'A, B, and C'), extract the entire coordinated list span into the item slot rather than only the final item. Do not drop trailing constituent words such as 'time' in meal timestamps (e.g. preserve 'dinner time'). Preserve verbatim morphological inflections (keep plural or singular forms exactly as uttered without lemmatizing) and retain natural words without converting to snake_case.
6. Strict Spoken Punctuation Hygiene & Wh-Clause Preservation: Spoken voice commands never contain written punctuation. For ALL free-text values (query, title, item, message), ALWAYS remove sentence-final punctuation marks ('?', '.', '!') and omit enclosing quotes. Extract the complete question or query clause preserving wh-words ('what', 'how', 'when', 'who', 'where') and content words verbatim, stripping only carrier request prefixes (such as 'find me a', 'give me a', 'show me a') and assistant wake words ('Alexa', 'Hey Google'). Standalone voice control commands (e.g. 'Start listening', 'Stop listening') are never stripped.
7. Generic Concept Fallback: When an utterance specifies a generic concept or category noun (such as reminders, meeting, appointment, event, call, list name) without a specific proper title, retain that spoken category noun (e.g. reminders, meeting) in the corresponding naming or title parameter rather than omitting the slot."""

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

    print("=== Running Generalized SLU Prompt Iteration 8 ===")
    df = pd.read_csv(csv_path)
    tools_str = build_tools_catalog_iter8()
    sys_prompt = build_prompt_iter8(tools_str)

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
    print(f"ITERATION 8 EVALUATION RESULTS ({elapsed:.1f}s)")
    print(f"{'='*70}")
    print(f"  • Tool Selection (TS):    {eval_res['ts']*100:.2f}% ({int(eval_res['ts']*len(df))} / {len(df)} commands)")
    print(f"  • Structure (TCS):        {eval_res['tcs']*100:.2f}%")
    print(f"  • Parameter Filling (PF): {eval_res['pf']*100:.2f}% ({eval_res['pf_correct']} / {eval_res['total_slots']} slots)")
    print(f"  • Command Frame Accuracy: {eval_res['frame_acc']*100:.2f}% ({int(eval_res['frame_acc']*len(df))} / {len(df)} commands)")
    print(f"  • Total Slot Failures:    {len(eval_res['failures'])}")
    print(f"{'='*70}\n")

    out_dir = "/work/hdd/bedl/zyin2/dev_audio/benchmark_291"
    out_summary = os.path.join(out_dir, "iter8_generalized_summary.json")
    out_csv = os.path.join(out_dir, "iter8_generalized_predictions.csv")

    df["iter8_pred_intent"] = [p["intent"] for p in preds]
    df["iter8_pred_slots"] = [json.dumps(p["slots"]) for p in preds]
    df["iter8_pred_domain"] = [p["domain"] for p in preds]
    df.to_csv(out_csv, index=False)

    summary_data = {
        "iteration": 8,
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
