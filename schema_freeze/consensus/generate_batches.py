#!/usr/bin/env python3
"""
generate_batches.py

Splits the 1,194 unlabeled commands from sap_commands_master.csv into 24 standardized
batch prompt files for Claude 3.5 Sonnet and GPT dual-frontier consensus annotation.

Outputs:
  - schema_freeze/consensus/master_unlabeled_index.csv
  - schema_freeze/consensus/batches/prompt_batch_01.md ... prompt_batch_24.md
"""

import csv
import json
import os
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_FREEZE = SCRIPT_DIR.parent
REPO_ROOT = SCHEMA_FREEZE.parent
MASTER_CSV = REPO_ROOT / "benchmark_curation" / "sap_commands_master.csv"
PILOT_GOLD = SCHEMA_FREEZE / "pilot" / "SLU_pilot_50_gold.csv"
FRONTIER_GOLD = SCHEMA_FREEZE / "frontier_100_gold.csv"
BATCHES_DIR = SCRIPT_DIR / "batches"
INDEX_CSV = SCRIPT_DIR / "master_unlabeled_index.csv"

BATCHES_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_HEADER_TEMPLATE = """You are an expert Spoken Language Understanding (SLU) semantic parser. Map each of the following spoken assistant commands into its canonical (Domain, Intent, Slots) representation according to the strict 29-tool schema below.

### 1. Canonical Schema (29 Tools across 10 Domains)

1. accessibility:
- accessibility_dictation_toggle: state ["on", "off", "enable", "disable"]
- accessibility_ui_scale: direction ["up", "down", "in", "out"], ui_element ["zoom", "text_size", "high_contrast", "screen"]

2. calendar_alarm:
- alarm_manage: action ["set", "cancel", "query", "snooze"], time (span), date (span), general_frequency ["daily", "weekdays", "weekends", "weekly", "monthly"]
- schedule_manage: action ["create", "delete", "query", "update"], title (span), date (span), time (span), person (span)

3. communication:
- call_make: recipient_name (span), phone_number (span)
- call_manage: action ["answer", "decline", "hang_up", "mute", "unmute", "redial"]
- messages_manage: action ["send", "read", "reply"], recipient (span), message_body (span)
- email_manage: action ["send", "read", "search"], recipient (span), date (span), message_body (span)

4. general_qa:
- qa_search: query (span) -> Factual queries, definitions, recipes, stock prices.
- weather_query: place_name (span), date (span), weather_aspect (span)
- device_find: device_type (span)
- order_manage: action ["track", "cancel", "return", "status"]

5. health:
- health_medication_reminder: medication (span), time (span)
- health_refill_query: medication (span)
- health_info_query: medication (span), info_type ["side_effects", "dosage", "interactions", "refill"]

6. maps_places:
- maps_route: destination (span), origin (span), query_type ["directions", "distance", "traffic"]
- places_search: business_name (span), business_type (span), sort_by ["rating", "distance", "relevance"]
- reservations_manage: business_name (span), time (span), date (span), party_size (span)

7. media:
- media_play: media_type ["music", "podcast", "radio", "audiobook", "movie", "tv_show"], title (span), artist (span), service (span: e.g. hulu, spotify, paramount plus), house_place (span)
- media_search: media_type ["movie", "tv_show", "music", "podcast", "audiobook"], person (span: actor/director/artist), genre (span), title (span) -> Browse/recommend media.
- media_control: action ["pause", "resume", "stop", "next", "previous", "like", "dislike", "fast_forward", "rewind"], duration (span)
- media_volume: action ["up", "down", "mute", "unmute", "set"], change_amount (span)

8. notes_memory:
- lists_manage: action ["create", "add", "remove", "query"], item (span), list_name (span)
- memory_note_manage: action ["store", "recall"], key (span), value (span)

9. smart_home:
- iot_device_power: device_type (span), state ["on", "off"], house_place (span) -> Binary toggles and lock actuation (lock -> on, unlock -> off).
- iot_device_adjust: device_type (span), setting ["brightness", "temperature", "color", "speed"], direction ["up", "down"], value (span)
- iot_sensor_query: sensor_type ["temperature", "motion", "lock", "contact"], device_type (span), room (span) -> State inspection (e.g. Is front door locked? -> sensor_type: lock).

10. transport:
- rideshare_book: destination (span)
- transit_lookup: transit_type ["train", "bus", "flight"], destination (span), route_or_station (span), time (span)

### 2. Core Extraction Rules:
- Rule A (BaseNP & Possessives): Strip prepositions (to, at, in, for, on, with) and possessive pronouns/articles (my, our, your, his, her, the, a, an). E.g. "Map route to our hotel" -> destination: "hotel".
- Rule B (Carrier Stripping in qa_search): Strip polite prefixes ("can you look up", "tell me", "search google for"). E.g. "Did the Clemson Tigers win?" -> query: "did the clemson tigers win".
- Rule C (Memory Key-Value in memory_note_manage): If an attribute relation (X is Y), extract key and value. If an unkeyed declarative fact ("We're out of batteries"), extract action: "store", value: "we're out of batteries" (leave key empty).
- Rule D (Generic Event Noun in schedule_manage): Retain generic event nouns ("meeting", "appointment", "call", "reminder") in title if uttered and no specific event topic is given (e.g. "Cancel my meeting with Sanjiv" -> title: "meeting", person: "sanjiv").
- Rule E (Alarm Recurrence Token Constraint in alarm_manage): Only populate general_frequency if an explicit recurrence marker is uttered ("daily", "weekdays", "every Thursday"). Coordinated days without recurrence markers ("on Thursday and Friday") belong strictly in the date slot; do not infer general_frequency: "weekly".
- Rule F (Business Hours & Metadata in places_search): Inquiries regarding commercial business opening/closing hours or operational status belong to maps_places.places_search (e.g. "When is Bed, Bath and Beyond open until?" -> business_name: "bed, bath and beyond"), NOT general_qa.qa_search.
- Rule G (Transit Modifiers in transit_lookup): Spoken commercial airlines extract into route_or_station (e.g. "Southwest Airlines", "Jet Blue"). General flight modifiers such as "non-stop" or "round-trip" are Outside (O) tokens and must NOT be forced into time.
- Rule H (Origin and Destination in maps_route): When navigation or distance queries specify both departure point and target (e.g. "How far is Brattleboro, Vermont from Montreal, Canada?"), extract the departure into origin and destination into destination.
- Rule I (Verbatim Spans & Zero-Argument Invariance): All extracted span values must be exact lower-case substrings from the utterance. Never invent unuttered entities. If a command has no parameter arguments, slots must be an empty JSON object {}.

### 3. Output Format:
Return ONLY a valid CSV block with EXACTLY these four columns:
id,domain,intent,slots_json

Make sure slots_json is valid JSON with double-quotes escaped as per CSV standard (e.g. "{""key"": ""value""}"). Output all rows without truncating.

### 4. Input Commands (Batch {batch_num} - {cmd_count} commands):
"""


def norm(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[\.,\?!\"\']', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('&', 'and')
    return text


def main():
    with open(PILOT_GOLD, mode="r", encoding="utf-8") as f:
        pilot = list(csv.DictReader(f))
    with open(FRONTIER_GOLD, mode="r", encoding="utf-8") as f:
        frontier = list(csv.DictReader(f))
    with open(MASTER_CSV, mode="r", encoding="utf-8") as f:
        master = list(csv.DictReader(f))

    gold_set = set()
    for r in pilot:
        gold_set.add(norm(r["prompt"]))
    for r in frontier:
        gold_set.add(norm(r["prompt"]))

    unlabeled = []
    for r in master:
        t_norm = norm(r["text"])
        ct_norm = norm(r["clean_text"])
        if t_norm not in gold_set and ct_norm not in gold_set:
            unlabeled.append(r)

    print(f"Total Master Commands: {len(master)}")
    print(f"Adjudicated Reference Gold: {len(master) - len(unlabeled)} master commands ({len(pilot)} pilot + {len(frontier)} frontier)")
    print(f"Remaining Unlabeled Commands: {len(unlabeled)}")

    batch_size = 50
    indexed_rows = []

    for i, row in enumerate(unlabeled):
        b_num = (i // batch_size) + 1
        b_idx = (i % batch_size) + 1
        b_id = f"batch_{b_num:02d}"
        indexed_rows.append({
            "batch_id": b_id,
            "batch_num": b_num,
            "batch_idx": b_idx,
            "id": row["id"],
            "text": row["text"],
            "clean_text": row["clean_text"],
            "category": row["category"],
            "cohorts": row["cohorts"],
            "word_count": row["word_count"],
            "complexity": row["complexity"],
            "tool_heuristic": row["tool_heuristic"]
        })

    with open(INDEX_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(indexed_rows[0].keys()))
        writer.writeheader()
        writer.writerows(indexed_rows)
    print(f"[OK] Wrote master index to {INDEX_CSV} ({len(indexed_rows)} rows)")

    # Group by batch_num and write batch prompt markdown files
    batches = {}
    for r in indexed_rows:
        b_num = r["batch_num"]
        batches.setdefault(b_num, []).append(r)

    for b_num, items in sorted(batches.items()):
        b_file = BATCHES_DIR / f"prompt_batch_{b_num:02d}.md"
        header = PROMPT_HEADER_TEMPLATE.replace("{batch_num}", str(b_num)).replace("{cmd_count}", str(len(items)))
        
        cmd_lines = []
        for it in items:
            cmd_lines.append(f'ID {it["id"]}: "{it["text"]}"')
        
        content = header + "\n".join(cmd_lines) + "\n"
        with open(b_file, mode="w", encoding="utf-8") as f:
            f.write(content)

    print(f"[OK] Generated {len(batches)} batch prompt files in {BATCHES_DIR}")


if __name__ == "__main__":
    main()
