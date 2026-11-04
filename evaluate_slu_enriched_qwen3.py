#!/usr/bin/env python3
"""
Phase 2 SLU Evaluation: Enriched Grounded System Prompt (Qwen3-8B)
Zero-leakage, schema-grounded evaluation across Oracle, Base ASR, and Fine-Tuned ASR.
Saves intermediate checkpoints per condition to guarantee zero data loss.
"""

import os
import sys
import re
import json
import time
import argparse
import pandas as pd
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError:
    torch = None

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def char_levenshtein(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[m][n]

def compute_char_f1(gold: str, hyp: str) -> float:
    g = normalize_text(gold)
    h = normalize_text(hyp)
    if not g and not h: return 1.0
    if not g or not h: return 0.0
    dist = char_levenshtein(g, h)
    precision = max(0.0, (len(h) - dist) / len(h)) if len(h) > 0 else 0.0
    recall = max(0.0, (len(g) - dist) / len(g)) if len(g) > 0 else 0.0
    if precision + recall == 0: return 0.0
    return round((2 * precision * recall) / (precision + recall), 4)

def parse_llm_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        out = json.loads(text)
        if isinstance(out, dict):
            domain = str(out.get("domain", "")).strip().lower()
            intent = str(out.get("intent", "")).strip().lower()
            slots = out.get("slots", {})
            if not isinstance(slots, dict):
                slots = {}
            return {"domain": domain, "intent": intent, "slots": slots, "raw": raw_text}
    except Exception:
        pass

    intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', raw_text)
    domain_match = re.search(r'"domain"\s*:\s*"([^"]+)"', raw_text)
    intent = intent_match.group(1).strip().lower() if intent_match else "unknown"
    domain = domain_match.group(1).strip().lower() if domain_match else "unknown"
    return {"domain": domain, "intent": intent, "slots": {}, "raw": raw_text, "parse_error": True}

CANONICAL_TOOL_DESCRIPTIONS = {
    # Accessibility
    "accessibility_dictation_toggle": "Toggle speech-to-text dictation listening state for accessibility assistance.",
    "accessibility_ui_scale": "Adjust visual display magnification, text font sizing, or high-contrast screen presentation.",
    # Calendar & Alarm
    "alarm_manage": "Set, cancel, snooze, or query time-based wake-up alarms and countdown timers.",
    "schedule_manage": "Create, update, cancel, or inspect calendar events, appointments, meetings, and personal task reminders (e.g. remind me to do a task, schedule an appointment, or add a reminder).",
    # Communication
    "call_make": "Voice telephony: every command that begins with 'call' or 'dial' invokes call_make to place an outgoing telephone call to the requested person, contact, or commercial business establishment (e.g. calling a contact, or calling a local store, nearby pharmacy, or nearest venue).",
    "call_manage": "Active call and visitor intercom management: handling incoming telephone calls, intercom rings, or door visitors (e.g. actions to answer, decline, hang up, mute, or redial).",
    "messages_manage": "Compose, send, read, or reply to SMS and instant chat messages.",
    "email_manage": "Compose, send, search, or read electronic mail messages.",
    # General QA
    "qa_search": "Open-domain question answering: questions asking what audio is currently playing (e.g. asking what song or album is playing), destination activity suggestions (e.g. tourist activities or things to do in a location), dictionary word definitions, and general knowledge questions.",
    "weather_query": "Retrieve meteorological weather forecasts, current conditions, precipitation, and outdoor temperatures for a location.",
    "device_find": "Ring or chime misplaced electronic accessories (e.g. phone, tablet, earbuds). Operates strictly by emitting audio chimes on pingable electronic hardware.",
    "order_manage": "Track shipment delivery status, manage returns, or inspect e-commerce parcel orders.",
    # Health
    "health_medication_reminder": "Schedule dosage or intake reminders for medications, prescriptions, and health supplements.",
    "health_refill_query": "Inquire about remaining prescription refills or pharmacy status for medications.",
    "health_info_query": "Medical inquiries regarding prescription pharmaceutical drugs: clinical guidance on side effects, drug interactions, or dosing instructions for medications.",
    # Maps & Places
    "maps_route": "Navigation, routing, and travel distance: driving directions, route planning, and travel distance inquiries between locations (e.g. questions asking how far a destination is from an origin, or navigation directives like navigate to or directions to).",
    "places_search": "Business venue discovery: directory search queries that find, locate, browse, or display commercial stores, restaurants, or opening hours.",
    "reservations_manage": "Book, modify, cancel, or inspect dining and table reservations at hospitality venues.",
    # Media
    "media_play": "Playback and narration: every command to play, listen to, stream, or read media content (such as music, songs, podcasts, radio stations, audiobooks, or spoken books) invokes media_play.",
    "media_search": "Media catalog discovery: finding, browsing, or listing media titles, movies, TV shows, music, or podcast content (e.g. commands asking to show or search for movies, actors, artists, or songs).",
    "media_control": "Executes playback transport controls: pause, resume, stop, next track, previous track, fast forward, rewind, or rating and favoriting actions (e.g. liking, thumbs up, or adding currently playing music to favorites).",
    "media_volume": "Adjust, mute, unmute, or set audio playback volume levels.",
    # Notes & Memory
    "lists_manage": "Create, view, add items to, or remove items from structured user lists (such as shopping, to-do, or reminder lists).",
    "memory_note_manage": "Store or recall personal memory items, user notes, declarative facts, and remembered personal locations (e.g. questions asking where the user left, placed, or situated personal items, or recalling stored notes).",
    # Smart Home
    "iot_device_power": "Turns heating systems, cooling units, domestic appliances (e.g. kettles, coffee makers, fans, heaters, lights), fixtures, or entrance barriers on or off. Commands to turn on, power on, activate, or boil an appliance map to iot_device_power with state 'on'.",
    "iot_device_adjust": "Modulates continuous temperature setpoints, lighting levels, or speeds to explicit numerical degrees or comparative directional adjustments (up or down). Always requires an explicit numerical degree or directional increment.",
    "iot_sensor_query": "Query real-time status readings from connected smart home hardware sensors (e.g. ambient temperature sensors, motion detectors, door or window contact sensors, or moisture sensors).",
    # Transport
    "rideshare_book": "Request, hail, or book a rideshare vehicle or taxi service to a destination.",
    "transit_lookup": "Lookup departure schedules, routes, or ticketing for public transit (trains, buses, flights)."
}

CANONICAL_PARAM_DESCRIPTIONS = {
    # accessibility_dictation_toggle
    ("accessibility_dictation_toggle", "state"): "Target dictation listening state: 'on' or 'enable' to activate, 'off' or 'disable' to deactivate.",

    # accessibility_ui_scale
    ("accessibility_ui_scale", "direction"): "Scaling direction: 'up'/'in' to increase magnification, 'down'/'out' to decrease.",
    ("accessibility_ui_scale", "ui_element"): "Target interface element: 'zoom', 'text_size', 'high_contrast', or 'screen'.",

    # alarm_manage
    ("alarm_manage", "action"): "Alarm or timer operation: 'set' to create, 'cancel' to dismiss, 'query' to inspect, or 'snooze' to defer.",
    ("alarm_manage", "time"): "Clock time or timer countdown duration.",
    ("alarm_manage", "date"): "Target calendar date for the alarm.",
    ("alarm_manage", "general_frequency"): "Recurrence schedule: 'daily', 'weekdays', 'weekends', 'weekly', or 'monthly'.",

    # schedule_manage
    ("schedule_manage", "action"): "Calendar operation: 'create' for new entries, 'delete' to cancel, 'query' to inspect, or 'update' to reschedule.",
    ("schedule_manage", "title"): "Calendar event topic or event category noun phrase (e.g. appointment, conference, discussion, session, meeting). Every calendar operation must populate title with the spoken event noun span.",
    ("schedule_manage", "date"): "Scheduled calendar date or relative day expression.",
    ("schedule_manage", "time"): "Scheduled clock time or time of day.",
    ("schedule_manage", "person"): "Name of any invited participant, attendee, or contact mentioned in the utterance (e.g. people introduced by 'with'). Must always be extracted whenever an attendee or person is named.",

    # call_make
    ("call_make", "recipient_name"): "Name or description of the contact, person, or business establishment to call (e.g. contact name, or business description like nearest hardware store, local pizza place, or neighborhood pharmacy).",
    ("call_make", "phone_number"): "Telephone number or dialing digits.",

    # call_manage
    ("call_manage", "action"): "Call management action: 'answer', 'decline', 'hang_up', 'mute', 'unmute', or 'redial'.",

    # messages_manage
    ("messages_manage", "action"): "Messaging action: 'send' to dispatch a new message, 'read' to inspect messages, or 'reply' to respond.",
    ("messages_manage", "recipient"): "Recipient contact name or phone number.",
    ("messages_manage", "message_body"): "Dictated text message content.",

    # email_manage
    ("email_manage", "action"): "Email action: 'send' to dispatch an email, 'read' to view messages, or 'search' to filter inbox.",
    ("email_manage", "recipient"): "Recipient contact name or email address.",
    ("email_manage", "date"): "Date expression used as an email search filter.",
    ("email_manage", "message_body"): "Dictated email body content verbatim. Retain all dictated punctuation words (such as comma, period, question mark) exactly as spoken.",

    # qa_search
    ("qa_search", "query"): "The complete natural language question clause or search payload. When the query begins with imperative search carrier directives (such as find me, search for, look up), strip that introductory directive and extract the search payload. For interrogative questions, extract the full question clause intact with question words; never reduce questions to isolated noun phrases.",

    # weather_query
    ("weather_query", "place_name"): "Geographic city, state, or region name (e.g. Chicago, Boston). Omit when no geographic location is specified.",
    ("weather_query", "date"): "Forecast date or relative day expression (e.g. today, tomorrow, Friday). Relative day terms (such as today or tomorrow) belong in date.",
    ("weather_query", "weather_aspect"): "Verbatim meteorological condition or weather item asked about (e.g. rain, snow, umbrella, temperature).",

    # device_find
    ("device_find", "device_type"): "Target misplaced portable electronic device noun phrase (e.g. phone, tablet, smartwatch).",

    # order_manage
    ("order_manage", "action"): "Order management action: 'track' for shipment tracking, 'cancel' to void an order, 'return' to initiate returns, or 'status' for order updates.",

    # health_medication_reminder
    ("health_medication_reminder", "medication"): "Name of the medication, pharmaceutical drug, or dietary supplement.",
    ("health_medication_reminder", "time"): "Scheduled intake time or meal reference.",

    # health_refill_query
    ("health_refill_query", "medication"): "Name of the prescription medication.",

    # health_info_query
    ("health_info_query", "medication"): "Name of the medication.",
    ("health_info_query", "info_type"): "Category of clinical information: 'side_effects', 'dosage', 'interactions', or 'refill'.",

    # maps_route
    ("maps_route", "destination"): "Primary target location, venue, address, or measured arrival endpoint.",
    ("maps_route", "origin"): "Starting departure location or reference origin.",
    ("maps_route", "query_type"): "Required navigation query modality enum ['directions', 'distance', 'traffic']. Must always be populated: select 'directions' for driving directions, route planning, or destination navigation; select 'distance' for travel distance inquiries; select 'traffic' for transit traffic conditions.",

    # places_search
    ("places_search", "business_name"): "Commercial venue or establishment name.",
    ("places_search", "business_type"): "Commercial category or establishment type noun phrase. Extract the verbatim category noun phrase spoken by the user (preserving plurals such as cafes, restaurants, or stores).",
    ("places_search", "sort_by"): "Required ranking preference enum ['rating', 'distance', 'relevance']. Must always be populated: select 'distance' when proximity, distance, or nearby/closest locations are requested; select 'rating' for top-rated; select 'relevance' for topical matching.",

    # reservations_manage
    ("reservations_manage", "business_name"): "Restaurant or hospitality venue name.",
    ("reservations_manage", "time"): "Reservation time.",
    ("reservations_manage", "date"): "Reservation calendar date.",
    ("reservations_manage", "party_size"): "Guest headcount or party size.",

    # media_play
    ("media_play", "media_type"): "Media content format enum ['music', 'podcast', 'radio', 'audiobook', 'movie', 'tv_show']: select 'audiobook' for spoken books or reading audiobooks; select 'music' for songs/tracks; select 'podcast' for podcasts; select 'radio' for radio broadcasts.",
    ("media_play", "title"): "Title of the media track, album, show, podcast, or program (e.g. podcast series name or album title, omitting episode descriptors such as latest episode or newest track).",
    ("media_play", "artist"): "Performing artist, creator, musician, or podcast host.",
    ("media_play", "service"): "Streaming app or platform service provider.",
    ("media_play", "house_place"): "Room or physical zone where playback should occur.",

    # media_search
    ("media_search", "media_type"): "Media category sought: 'movie', 'tv_show', 'music', 'podcast', or 'audiobook'.",
    ("media_search", "person"): "Actor, director, artist, or host.",
    ("media_search", "genre"): "Genre classification or category.",
    ("media_search", "title"): "Media title or search query.",

    # media_control
    ("media_control", "action"): "Playback control action enum ['pause', 'resume', 'stop', 'next', 'previous', 'like', 'dislike', 'fast_forward', 'rewind']: select 'like' when liking, favoriting, or adding currently playing media to favorites; select 'dislike' for thumbs down; otherwise select corresponding playback control action.",
    ("media_control", "duration"): "Offset duration for fast-forward or rewind scrubbing.",

    # media_volume
    ("media_volume", "action"): "Volume modification action enum ['up', 'down', 'mute', 'unmute', 'set']: select 'set' when adjusting volume to an absolute target level or extreme (e.g. to minimum, to maximum, or to a specific level/number); select 'up' or 'down' only for relative adjustments without a target level.",
    ("media_volume", "change_amount"): "Target volume level or relative adjustment amount.",

    # lists_manage
    ("lists_manage", "action"): "List operation: 'create' for new lists, 'add' for inserting items, 'remove' for deleting items, or 'query' for viewing, reading, or checking list contents.",
    ("lists_manage", "item"): "Item noun phrase to add or remove, including associated prepositional or descriptive modifiers (e.g. prepositional phrases like for someone or of something). Always preserve full prepositional phrases attached to the item.",
    ("lists_manage", "list_name"): "Target list container name (e.g. shopping list, to-do list). Required across all operations, including viewing or querying list contents.",

    # memory_note_manage
    ("memory_note_manage", "action"): "Required operation enum ['store', 'recall']: select 'store' when recording or saving a declarative statement, fact, or attribute value; select 'recall' when asking, inquiring, or searching for a remembered location, fact, or personal note.",
    ("memory_note_manage", "key"): "Associative topic or keyword span of the memory item. Extract the exact spoken word or span verbatim without nominalization or converting verbs to gerunds.",
    ("memory_note_manage", "value"): "Verbatim statement, detail, or value to record for the stored memory item.",

    # iot_device_power
    ("iot_device_power", "device_type"): "Target hardware device, domestic appliance, lighting fixture, heating or cooling system, or entrance barrier, retaining collective quantifiers (such as all or every).",
    ("iot_device_power", "state"): "Binary state enum ['on', 'off']: commands to turn on, power on, activate, boil, or lock map to 'on'; commands to turn off, power off, deactivate, or unlock map to 'off'.",
    ("iot_device_power", "house_place"): "Residential room, spatial zone, or physical area where the device is situated.",

    # iot_device_adjust
    ("iot_device_adjust", "device_type"): "Target hardware device, fixture, or appliance noun phrase, preserving leading spatial room descriptors and compound noun modifiers (e.g. kitchen lamp, bedroom ceiling fan).",
    ("iot_device_adjust", "setting"): "Continuous attribute enum ['brightness', 'temperature', 'color', 'speed']. For 'temperature', strictly represents continuous setpoint adjustments (degrees or warmer/cooler).",
    ("iot_device_adjust", "direction"): "Directional adjustment enum ['up', 'down']: select 'up' for increase, higher, brighter, warmer; select 'down' for decrease, lower, dimmer, cooler. Strictly applies to relative directional shifts.",
    ("iot_device_adjust", "value"): "Explicit numerical degree or level setting with units of measurement (e.g. 70 degrees, 50 percent). Strictly represents numerical quantities.",

    # iot_sensor_query
    ("iot_sensor_query", "sensor_type"): "Sensor modality inspected enum: 'temperature', 'motion', 'lock', or 'contact'.",
    ("iot_sensor_query", "device_type"): "Hardware device or fixture inspected.",
    ("iot_sensor_query", "room"): "Residential room or physical area.",

    # rideshare_book
    ("rideshare_book", "destination"): "Target drop-off arrival location or address.",

    # transit_lookup
    ("transit_lookup", "transit_type"): "Public transit modality: 'train', 'bus', or 'flight'.",
    ("transit_lookup", "destination"): "Target arrival station, terminal, or destination city.",
    ("transit_lookup", "route_or_station"): "Public transit line name, station, terminal, or transit carrier.",
    ("transit_lookup", "time"): "Scheduled departure or arrival time."
}

def build_enriched_system_prompt(schema_path: str) -> str:
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    tools_doc = []
    for t in schema["tools"]:
        t_name = t["name"]
        t_desc = CANONICAL_TOOL_DESCRIPTIONS.get(t_name, t.get("description", ""))
        props = t.get("parameters", {}).get("properties", {})
        param_strs = []

        for p_name, p_info in props.items():
            p_desc = CANONICAL_PARAM_DESCRIPTIONS.get((t_name, p_name), p_info.get("description", ""))
            if "enum" in p_info:
                enum_str = str(p_info['enum'])
                param_strs.append(f"{p_name} ({enum_str}: {p_desc})")
            else:
                param_strs.append(f"{p_name} (str: {p_desc})")

        params_formatted = "; ".join(param_strs)
        tools_doc.append(f"- {t_name} (domain: {t['domain']}):\n  Purpose: {t_desc}\n  Parameters: {params_formatted}")

    tools_str = "\n".join(tools_doc)

    sys_prompt = f"""You are the Spoken Language Understanding (SLU) agent for the Speech Accessibility Project (SAP).
Map each spoken voice command into a valid JSON tool call conforming strictly to the 29-tool schema below.

CANONICAL TOOLS AND PARAMETERS:
{tools_str}

EXTRACTION RULES:
1. Strict Schema Adherence: The 'intent' field must strictly match one of the canonical tool names specified in the schema header preceding the parenthetical domain. Never output parameter names, enum values, or operational verbs as the intent. Never invent tool names, modify prefixes, or generate tools outside this schema. For categorical parameters with bracketed allowed values [...], select the enum option that matches the user's intended operation or modality based on semantic equivalence. Entity parameters must extract the spoken topical nouns or referents (such as an event noun, item name, or device type) even when referred to by generic nouns rather than proper names; never omit an argument when its referent noun appears in the spoken utterance.
2. Verbatim Span Preservation: For open-text entity arguments, extract the verbatim words spoken by the user without summarization, lemmatization, or alteration. Preserve complete noun phrases along with prepositional and descriptive modifiers. Preserve spoken punctuation words (such as comma, period, question mark) verbatim as uttered without converting them to punctuation symbols.
3. Wake Word Stripping & Interrogative Question Preservation: Strip introductory conversational assistant wake words (such as Alexa, Cortana, Siri, Computer) and leading search carrier verbs (such as find me, search for, look up) from the start of an utterance. Every question clause (e.g. clauses starting with What, What's, When, Where, Who, How) must be preserved verbatim in its entirety; never strip question words or contractions like what's. Do not strip definition verbs like define.
4. Parameter Specialization & Semantic Typing: Populate each parameter slot strictly according to its defined parameter description below. Do not cross-populate slots with mismatched semantic entities.

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

def evaluate_condition_metrics(df: pd.DataFrame, preds: list, col_name: str):
    ts_correct = 0
    tcs_correct = 0
    pf_correct = 0
    total_slots = 0
    total_pred_slots = 0
    frame_correct = 0

    domain_stats = {}
    etiology_stats = {}
    failures = []

    for idx, (p, (_, row)) in enumerate(zip(preds, df.iterrows())):
        gold_intent = str(row["intent"]).strip().lower()
        gold_domain = str(row["domain"]).strip().lower()
        etiology = str(row.get("etiology", "all")).strip()

        raw_slots = row.get("slots", "{}")
        gold_slots = json.loads(raw_slots) if isinstance(raw_slots, str) and raw_slots.strip() else {}

        pred_intent = p["intent"]
        pred_domain = p["domain"]
        pred_slots = p["slots"]

        total_pred_slots += len(pred_slots)

        is_ts = (pred_intent == gold_intent)
        if is_ts: ts_correct += 1

        is_tcs = (not p.get("parse_error", False) and pred_domain not in ["unknown", "error", ""])
        if is_tcs: tcs_correct += 1

        slots_all_ok = True
        for k, v in gold_slots.items():
            total_slots += 1
            norm_g = normalize_text(str(v))
            norm_p = normalize_text(str(pred_slots.get(k, "")))

            matched = (norm_g == norm_p) or (norm_g != "" and compute_char_f1(norm_g, norm_p) >= 0.85)
            if matched:
                pf_correct += 1
            else:
                slots_all_ok = False
                failures.append({
                    "gold_id": row.get("gold_id", f"item_{idx}"),
                    "wav": row.get("wav", ""),
                    "speaker": row.get("speaker", "unknown"),
                    "etiology": etiology,
                    "prompt": row.get("prompt", ""),
                    "asr_input": row[col_name] if col_name in row else row.get("prompt", ""),
                    "gold_intent": gold_intent,
                    "pred_intent": pred_intent,
                    "slot": k,
                    "gold_val": v,
                    "pred_val": pred_slots.get(k, None),
                    "type": "Intent Mismatch" if not is_ts else ("Missing Slot" if k not in pred_slots else "Value Mismatch")
                })

        is_frame = is_ts and is_tcs and slots_all_ok
        if is_frame: frame_correct += 1

        # Domain stats
        if gold_domain not in domain_stats:
            domain_stats[gold_domain] = {"total": 0, "frame": 0, "ts": 0}
        domain_stats[gold_domain]["total"] += 1
        if is_frame: domain_stats[gold_domain]["frame"] += 1
        if is_ts: domain_stats[gold_domain]["ts"] += 1

        # Etiology stats
        if etiology not in etiology_stats:
            etiology_stats[etiology] = {"total": 0, "frame": 0, "ts": 0}
        etiology_stats[etiology]["total"] += 1
        if is_frame: etiology_stats[etiology]["frame"] += 1
        if is_ts: etiology_stats[etiology]["ts"] += 1

    n_samples = len(df)
    ts_pct = round(ts_correct / n_samples * 100, 2)
    tcs_pct = round(tcs_correct / n_samples * 100, 2)
    pf_recall = round(pf_correct / total_slots * 100, 2) if total_slots > 0 else 0.0
    pf_precision = round(pf_correct / total_pred_slots * 100, 2) if total_pred_slots > 0 else 0.0
    pf_f1 = round(2 * pf_precision * pf_recall / (pf_precision + pf_recall), 2) if (pf_precision + pf_recall) > 0 else 0.0
    frame_pct = round(frame_correct / n_samples * 100, 2)

    return {
        "TS": ts_pct,
        "TCS": tcs_pct,
        "PF": pf_recall,
        "PF_Recall": pf_recall,
        "PF_Precision": pf_precision,
        "PF_F1": pf_f1,
        "Frame_Acc": frame_pct,
        "Total_Samples": n_samples,
        "Total_Gold_Slots": total_slots,
        "Total_Pred_Slots": total_pred_slots,
        "Domains": {d: {"Frame_Acc": round(v["frame"]/v["total"]*100, 2), "TS": round(v["ts"]/v["total"]*100, 2)} for d, v in domain_stats.items()},
        "Etiologies": {e: {"Frame_Acc": round(v["frame"]/v["total"]*100, 2), "TS": round(v["ts"]/v["total"]*100, 2)} for e, v in etiology_stats.items()}
    }, failures

def main():
    parser = argparse.ArgumentParser(description="Phase 2 Enriched Prompt SLU Evaluation")
    parser.add_argument("--csv_path", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/sampled_benchmark_1108.csv")
    parser.add_argument("--schema_path", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/SLU_schema_v1.0.json")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen3-8B")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--max_new_tokens", type=int, default=90)
    parser.add_argument("--condition", type=str, default="all", choices=["all", "oracle", "base_asr", "ft_asr"], help="Condition to evaluate: all, oracle, base_asr, or ft_asr")
    parser.add_argument("--output_csv", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/enriched_eval_1108_results.csv")
    parser.add_argument("--output_summary", type=str, default="/work/hdd/bedl/zyin2/benchmark_phase2/enriched_eval_1108_summary.json")
    args = parser.parse_args()

    print("=== Starting Phase 2 Enriched Grounded SLU Evaluation on Delta ===")
    print(f"Dataset:     {args.csv_path}")
    print(f"Schema:      {args.schema_path}")
    print(f"Model ID:    {args.model_id}")
    print(f"Batch Size:  {args.batch_size}")
    print(f"Max New Tok: {args.max_new_tokens}")
    print(f"Condition:   {args.condition}")

    csv_to_load = args.output_csv if (os.path.exists(args.output_csv) and args.condition != "all") else args.csv_path
    df = pd.read_csv(csv_to_load)
    n_spk = df['speaker'].nunique() if 'speaker' in df.columns else 1
    print(f"Loaded {len(df)} benchmark instances from {csv_to_load} across {n_spk} speakers.")

    sys_prompt = build_enriched_system_prompt(args.schema_path)
    print(f"Built Enriched System Prompt ({len(sys_prompt)} chars).")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    print(f"Loading Tokenizer & Model ({args.model_id})...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, padding_side="left")
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )
    model.eval()
    print(f"Model loaded in {time.time() - t0:.2f}s.")

    all_conditions = [
        ("oracle", "prompt"),
        ("base_asr", "base_parakeet_hypo"),
        ("ft_asr", "ft_parakeet_hypo")
    ]
    if args.condition != "all":
        conditions = [c for c in all_conditions if c[0] == args.condition]
    else:
        conditions = [c for c in all_conditions if c[1] in df.columns]

    summary_results = {}
    detailed_failures = {}
    base_ckpt = args.output_summary.replace(".json", "_checkpoint_base_asr.json")
    if os.path.exists(base_ckpt) and args.condition != "all":
        try:
            with open(base_ckpt, "r") as f:
                prev_data = json.load(f)
                if "metrics" in prev_data:
                    summary_results.update(prev_data["metrics"])
                    print(f"Loaded existing checkpoint metrics for: {list(summary_results.keys())}")
        except Exception as e:
            print(f"Warning loading base checkpoint: {e}")

    for cond_name, col_name in conditions:
        print(f"\n" + "=" * 60)
        print(f"--- Running Condition: {cond_name.upper()} (column: {col_name}) ---")
        print("=" * 60)
        prompts = df[col_name].fillna("").tolist()

        formatted_inputs = []
        for p in prompts:
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f'Spoken command: "{p}"'}
            ]
            try:
                formatted = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False, add_generation_prompt=True)
            except TypeError:
                formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            formatted_inputs.append(formatted)

        cond_preds = []
        t_start = time.time()
        for i in range(0, len(formatted_inputs), args.batch_size):
            batch_texts = formatted_inputs[i : i + args.batch_size]
            encoded = tokenizer(batch_texts, return_tensors="pt", padding=True, truncation=True, max_length=8192)
            input_ids = encoded["input_ids"].to(device)
            attention_mask = encoded["attention_mask"].to(device)

            with torch.no_grad():
                outputs = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=args.max_new_tokens,
                    temperature=0.0,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id
                )

            gen_tokens = outputs[:, input_ids.shape[1] :]
            decoded = tokenizer.batch_decode(gen_tokens, skip_special_tokens=True)

            for raw in decoded:
                parsed = parse_llm_json(raw)
                cond_preds.append(parsed)

            if (i // args.batch_size) % 5 == 0 or (i + args.batch_size) >= len(prompts):
                print(f"  Processed {min(i + args.batch_size, len(prompts))}/{len(prompts)} in {time.time() - t_start:.2f}s...", flush=True)

        print(f"Condition {cond_name.upper()} finished in {time.time() - t_start:.2f}s.")

        # Update dataframe with this condition's predictions immediately
        df[f"{cond_name}_pred_intent"] = [p["intent"] for p in cond_preds]
        df[f"{cond_name}_pred_slots"] = [json.dumps(p["slots"]) for p in cond_preds]
        df[f"{cond_name}_pred_domain"] = [p["domain"] for p in cond_preds]

        # Calculate metrics for this condition immediately
        cond_metrics, cond_fail_list = evaluate_condition_metrics(df, cond_preds, col_name)
        summary_results[cond_name] = cond_metrics
        detailed_failures[cond_name] = cond_fail_list

        print(f"--> {cond_name.upper()} METRICS: TS: {cond_metrics['TS']}% | TCS: {cond_metrics['TCS']}% | PF Rec: {cond_metrics['PF_Recall']}% | PF Prec: {cond_metrics['PF_Precision']}% | PF F1: {cond_metrics['PF_F1']}% | Frame: {cond_metrics['Frame_Acc']}%")

        # Checkpoint: Save CSV and summary JSON immediately after EACH condition
        df.to_csv(args.output_csv, index=False)
        intermediate_summary = {
            "completed_conditions": list(summary_results.keys()),
            "metrics": summary_results
        }
        ckpt_path = args.output_summary.replace(".json", f"_checkpoint_{cond_name}.json")
        with open(ckpt_path, "w") as f:
            json.dump(intermediate_summary, f, indent=2)
        print(f"Checkpoint saved: {ckpt_path} and {args.output_csv}")

    # Compute Final ARR if all 3 conditions completed
    if all(c in summary_results for c in ["oracle", "base_asr", "ft_asr"]):
        o_acc = summary_results["oracle"]["Frame_Acc"]
        b_acc = summary_results["base_asr"]["Frame_Acc"]
        f_acc = summary_results["ft_asr"]["Frame_Acc"]
        arr = round(((f_acc - b_acc) / (o_acc - b_acc)) * 100, 2) if (o_acc - b_acc) > 0 else 0.0
        summary_results["ARR"] = arr

    summary_results["failures"] = detailed_failures

    with open(args.output_summary, "w") as f:
        json.dump(summary_results, f, indent=2)

    print("\n" + "=" * 80)
    print("                    ENRICHED PROMPT RESULTS SUMMARY")
    print("=" * 80)
    for c_name, c_res in summary_results.items():
        if c_name in ["oracle", "base_asr", "ft_asr"]:
            print(f"Condition ({c_name}): TS: {c_res['TS']}% | TCS: {c_res['TCS']}% | PF: {c_res['PF']}% | Frame: {c_res['Frame_Acc']}%")
    if "ARR" in summary_results:
        print(f"--> Adaptation Recovery Rate (ARR): {summary_results['ARR']}%")
    print(f"Final CSV:     {args.output_csv}")
    print(f"Final Summary: {args.output_summary}")

if __name__ == "__main__":
    main()
