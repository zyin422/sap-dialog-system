#!/usr/bin/env python3
"""
build_sap_commands_dataset.py

Parses all prompt spreadsheets and text files from the Speech Accessibility Project
(speechaccessibility/PromptsAnnotationGuidelines) and compiles a unified, deduplicated
master dataset of voice commands (~1,100 - 1,300 commands) across all clinical cohorts:
- Parkinson's disease & ALS (PD)
- Down syndrome & Cerebral palsy (DS)
- Stroke (Stroke)

Outputs:
  - benchmark_curation/sap_commands_master.json
  - benchmark_curation/sap_commands_master.csv
"""

import csv
import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Base directory setup
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "benchmark_curation" else SCRIPT_DIR
PROMPTS_DIR = SCRIPT_DIR / "sap_prompts"
OUTPUT_JSON = SCRIPT_DIR / "sap_commands_master.json"
OUTPUT_CSV = SCRIPT_DIR / "sap_commands_master.csv"

# Category normalization and mapping for Block 1 & 10 core 35 commands
B1_B10_CATEGORY_MAP = {
    "find my phone": ("Phone", "device_find"),
    "what's on my shopping list": ("Tasks and planning", "lists_manage"),
    "hang up": ("Phone", "call_manage"),
    "make the text larger": ("Smart Home", "accessibility_ui_scale"),
    "hey siri": ("Wake Phrases", "wake_word_trigger"),
    "decrease volume to minimum": ("Media control", "media_volume"),
    "what's the temperature in the living room": ("Smart Home", "iot_sensor_query"),
    "add this music to favorites": ("Media control", "media_control"),
    "hey google": ("Wake Phrases", "wake_word_trigger"),
    "open reminders": ("Tasks and planning", "schedule_manage"),
    "what's on my calendar tomorrow": ("Tasks and planning", "schedule_manage"),
    "alexa": ("Wake Phrases", "wake_word_trigger"),
    "what restaurants are nearby": ("Online Search", "places_search"),
    "answer the call": ("Phone", "call_manage"),
    "turn off the tv": ("Smart Home", "iot_device_power"),
    "cortana": ("Wake Phrases", "wake_word_trigger"),
    "what's the time": ("News, weather, traffic", "weather_query"),
    "skip this song": ("Media control", "media_control"),
    "what's the weather like today": ("News, weather, traffic", "weather_query"),
    "stop listening": ("Wake Phrases", "wake_word_trigger"),
    "hey facebook": ("Wake Phrases", "wake_word_trigger"),
    "lower the temperature": ("Smart Home", "iot_device_adjust"),
    "stop the call": ("Phone", "call_manage"),
    "tell me the news": ("News, weather, traffic", "news_query"),
    "turn off heat": ("Smart Home", "iot_device_power"),
    "increase volume to maximum": ("Media control", "media_volume"),
    "start listening": ("Wake Phrases", "wake_word_trigger"),
    "turn on cooling": ("Smart Home", "iot_device_power"),
    "turn on all switches": ("Smart Home", "iot_device_power"),
    "call area code 053-621-4879": ("Phone", "call_make"),
    "please send this text": ("Text dictation", "messages_manage"),
    "reschedule my meeting": ("Tasks and planning", "schedule_manage"),
    "send a message": ("Phone", "messages_manage"),
    "make the screen brighter": ("Smart Home", "iot_device_adjust"),
    "is the pharmacy open": ("Online Search", "places_search"),
}

# Mapping domain categories to canonical tool heuristics
DOMAIN_TO_TOOL_HEURISTICS = {
    "Tasks and planning": "schedule_manage / alarm_manage / lists_manage",
    "News, weather, traffic": "weather_query / news_query / maps_route",
    "Online Search": "qa_search / places_search / order_manage",
    "Media control": "media_play / media_control / media_volume",
    "Phone": "call_make / call_manage / messages_manage",
    "Smart Home": "iot_device_power / iot_device_adjust / iot_sensor_query",
    "Trip and outdoor": "maps_route / transit_lookup / rideshare_book",
    "Text dictation": "messages_manage / email_manage / accessibility_dictation_toggle",
    "Broadcast": "messages_manage / iot_device_power",
    "Wake Phrases": "wake_word_trigger",
}


def parse_xlsx_sheets(file_path: Path) -> Dict[str, List[List[str]]]:
    """Parses all sheets in an xlsx file into text rows using built-in zipfile and XML."""
    with zipfile.ZipFile(file_path, "r") as z:
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                text = "".join(t.text for t in si.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t.text)
                shared_strings.append(text)

        wb_tree = ET.fromstring(z.read("xl/workbook.xml"))
        sheets_info = [
            (s.get("name"), s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
            for s in wb_tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheets/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")
        ]
        rels_tree = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            r.get("Id"): r.get("Target")
            for r in rels_tree.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        }

        all_sheets = {}
        for s_name, r_id in sheets_info:
            target = "xl/" + rel_map[r_id] if not rel_map[r_id].startswith("xl/") else rel_map[r_id]
            sheet_tree = ET.fromstring(z.read(target))
            rows = []
            for row in sheet_tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData/{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                row_data = []
                for c in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                    t = c.get("t")
                    v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                    val = v.text if v is not None else ""
                    if t == "s" and val:
                        val = shared_strings[int(val)]
                    row_data.append(val)
                rows.append(row_data)
            all_sheets[s_name] = rows
        return all_sheets


def clean_command_text(raw_text: str) -> Tuple[str, str]:
    """Returns normalized key (lowercase, no trailing punct) and canonical display text."""
    collapsed = " ".join(raw_text.strip().split())
    # Canonical text keeps original capitalization and ending punctuation
    key = collapsed.lower().rstrip(".!?")
    return key, collapsed


def build_master_dataset() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    commands: Dict[str, Dict[str, Any]] = {}

    def get_or_create(key: str, display_text: str) -> Dict[str, Any]:
        if key not in commands:
            commands[key] = {
                "key": key,
                "text": display_text,
                "clean_text": key,
                "cohorts": set(),
                "blocks": set(),
                "categories": set(),
                "participant_groups": set(),
                "sources": set(),
                "is_universal_b1_b10": False,
                "scores": [],
                "raw_variants": set(),
            }
        entry = commands[key]
        entry["raw_variants"].add(display_text)
        return entry

    # 1. Parkinson's disease & ALS: Block 1 & 10 (commands_b1_b10_PD.txt)
    pd_txt_path = PROMPTS_DIR / "commands_b1_b10_PD.txt"
    if pd_txt_path.exists():
        with open(pd_txt_path, "r", encoding="utf-8") as f:
            for line in f:
                t = line.strip()
                if not t:
                    continue
                k, cleaned = clean_command_text(t)
                item = get_or_create(k, cleaned)
                item["cohorts"].add("PD")
                item["blocks"].add("b1_b10")
                item["sources"].add("commands_b1_b10_PD.txt")
                item["is_universal_b1_b10"] = True
                item["participant_groups"].add("all (100%)")
                cat, _ = B1_B10_CATEGORY_MAP.get(k, ("General Command", "general"))
                item["categories"].add(cat)

    # 2. Down syndrome and Stroke: Block 1 & 10 (35 commands per block)
    for fname, cohort in [
        ("commands_b1_b10_DS_35perBlock.xlsx", "DS"),
        ("commands_b1_b10_Stroke_35perBlock.xlsx", "Stroke"),
    ]:
        fpath = PROMPTS_DIR / fname
        if not fpath.exists():
            continue
        sheets = parse_xlsx_sheets(fpath)
        for s_name, rows in sheets.items():
            for r in rows:
                if not r or not r[0].strip():
                    continue
                k, cleaned = clean_command_text(r[0].strip())
                item = get_or_create(k, cleaned)
                item["cohorts"].add(cohort)
                item["blocks"].add("b1_b10")
                item["sources"].add(fname)
                item["is_universal_b1_b10"] = True
                item["participant_groups"].add("all (100%)")
                cat, _ = B1_B10_CATEGORY_MAP.get(k, ("General Command", "general"))
                item["categories"].add(cat)

    # 3. Blocks 2-9 rotation lists (PD, DS, Stroke)
    b2_9_files = [
        ("commands_b2-9_PD.xlsx", "PD"),
        ("commands_b2-9_DS_35perBlock.xlsx", "DS"),
        ("commands_b2-9_Stroke_35perBlock.xlsx", "Stroke"),
    ]
    for fname, cohort in b2_9_files:
        fpath = PROMPTS_DIR / fname
        if not fpath.exists():
            continue
        sheets = parse_xlsx_sheets(fpath)
        for s_name, rows in sheets.items():
            for r in rows:
                if len(r) >= 3 and r[2].strip():
                    k, cleaned = clean_command_text(r[2].strip())
                    item = get_or_create(k, cleaned)
                    item["cohorts"].add(cohort)
                    item["blocks"].add(f"{cohort}:{s_name}")
                    item["sources"].add(fname)
                    
                    # Category normalization
                    cat = r[1].strip()
                    if cat.lower() == "text dictation":
                        cat = "Text dictation"
                    item["categories"].add(cat)

                    # Participant group / percentage
                    grp = r[0].strip()
                    if grp:
                        fmt_grp = f"{grp}%" if grp.isdigit() else grp
                        item["participant_groups"].add(fmt_grp)

                    # Optional perplexity / score
                    if len(r) > 3 and r[3].strip():
                        try:
                            item["scores"].append(float(r[3].strip()))
                        except ValueError:
                            pass

    # Convert dictionary to sorted list of records
    records = []
    # Sort order: Universal b1_b10 first, then by cohort count descending, then alphabetically
    sorted_keys = sorted(
        commands.keys(),
        key=lambda k: (
            not commands[k]["is_universal_b1_b10"],
            -len(commands[k]["cohorts"]),
            commands[k]["text"].lower(),
        ),
    )

    for idx, k in enumerate(sorted_keys, start=1):
        cmd = commands[k]
        sorted_cohorts = sorted(list(cmd["cohorts"]))
        sorted_blocks = sorted(list(cmd["blocks"]))
        sorted_cats = sorted(list(cmd["categories"]))
        sorted_groups = sorted(list(cmd["participant_groups"]))
        sorted_sources = sorted(list(cmd["sources"]))
        
        # Primary category resolution
        primary_cat = sorted_cats[0] if sorted_cats else "General Command"
        # If both Wake Phrases and another exists (e.g. from b1_b10 default vs b2-9 specific), prefer b2-9 specific
        if len(sorted_cats) > 1:
            non_wake = [c for c in sorted_cats if c != "Wake Phrases" and c != "General Command"]
            if non_wake:
                primary_cat = non_wake[0]

        words = cmd["text"].split()
        word_count = len(words)
        char_count = len(cmd["text"])
        avg_score = round(sum(cmd["scores"]) / len(cmd["scores"]), 4) if cmd["scores"] else None

        # Determine mapped canonical tool candidate
        tool_hint = B1_B10_CATEGORY_MAP.get(k, (None, None))[1]
        if not tool_hint:
            tool_hint = DOMAIN_TO_TOOL_HEURISTICS.get(primary_cat, "custom_intent")

        record = {
            "id": f"SAP-CMD-{idx:04d}",
            "text": cmd["text"],
            "clean_text": cmd["clean_text"],
            "category": primary_cat,
            "all_categories": sorted_cats,
            "cohorts": sorted_cohorts,
            "cohort_count": len(sorted_cohorts),
            "is_universal_b1_b10": cmd["is_universal_b1_b10"],
            "participant_groups": sorted_groups,
            "blocks": sorted_blocks,
            "block_count": len(sorted_blocks),
            "sources": sorted_sources,
            "word_count": word_count,
            "char_count": char_count,
            "complexity": "Short (1-3 words)" if word_count <= 3 else ("Medium (4-7 words)" if word_count <= 7 else "Long (8+ words)"),
            "tool_heuristic": tool_hint,
            "avg_perplexity": avg_score,
        }
        records.append(record)

    # Compute high-level statistics
    category_counts = Counter(r["category"] for r in records)
    cohort_combination_counts = Counter("+".join(r["cohorts"]) for r in records)
    complexity_counts = Counter(r["complexity"] for r in records)

    stats = {
        "total_unique_commands": len(records),
        "total_universal_b1_b10": sum(1 for r in records if r["is_universal_b1_b10"]),
        "cohorts": {
            "PD_total": sum(1 for r in records if "PD" in r["cohorts"]),
            "DS_total": sum(1 for r in records if "DS" in r["cohorts"]),
            "Stroke_total": sum(1 for r in records if "Stroke" in r["cohorts"]),
            "all_three_cohorts": sum(1 for r in records if len(r["cohorts"]) == 3),
            "combinations": dict(cohort_combination_counts),
        },
        "categories": dict(category_counts.most_common()),
        "complexity": dict(complexity_counts),
    }

    return records, stats


def export_files(records: List[Dict[str, Any]], stats: Dict[str, Any]) -> None:
    # 1. Export JSON
    payload = {
        "metadata": {
            "source": "https://github.com/speechaccessibility/PromptsAnnotationGuidelines",
            "description": "Speech Accessibility Project (SAP) Master Voice Command Inventory",
            "stats": stats,
        },
        "commands": records,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved {len(records)} records to {OUTPUT_JSON}")

    # 2. Export CSV
    fieldnames = [
        "id",
        "text",
        "clean_text",
        "category",
        "cohorts",
        "cohort_count",
        "is_universal_b1_b10",
        "participant_groups",
        "word_count",
        "char_count",
        "complexity",
        "tool_heuristic",
        "sources",
    ]
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({
                "id": r["id"],
                "text": r["text"],
                "clean_text": r["clean_text"],
                "category": r["category"],
                "cohorts": "; ".join(r["cohorts"]),
                "cohort_count": r["cohort_count"],
                "is_universal_b1_b10": "Yes" if r["is_universal_b1_b10"] else "No",
                "participant_groups": "; ".join(r["participant_groups"]),
                "word_count": r["word_count"],
                "char_count": r["char_count"],
                "complexity": r["complexity"],
                "tool_heuristic": r["tool_heuristic"],
                "sources": "; ".join(r["sources"]),
            })
    print(f"[OK] Saved {len(records)} records to {OUTPUT_CSV}")


def main() -> None:
    print(f"Compiling SAP Master Command Dataset from {PROMPTS_DIR}...")
    records, stats = build_master_dataset()
    export_files(records, stats)
    print("\n--- Summary Statistics ---")
    print(f"Total Unique Commands:   {stats['total_unique_commands']:,}")
    print(f"Universal (Blocks 1&10): {stats['total_universal_b1_b10']}")
    print(f"Shared by all 3 Cohorts: {stats['cohorts']['all_three_cohorts']}")
    print("\nCategory Distribution:")
    for cat, count in stats["categories"].items():
        print(f"  - {cat:24s}: {count:4d}")


if __name__ == "__main__":
    main()
