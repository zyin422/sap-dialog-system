#!/usr/bin/env python3
"""
consensus_agreement.py

Dual-Frontier Consensus Agreement & Triage Engine for the Speech Accessibility Project (SAP)
Spoken Language Understanding (SLU) Benchmark.

Compares predictions from Claude 3.5 Sonnet and GPT across batch outputs, calculates
agreement metrics (Domain Agreement, Intent Agreement, and Full Slot Exact Match),
validates against Schema v1.2 (SLU_schema_v1.0.json), automatically accepts full agreements
into consensus gold, and compiles structured triage queues for disagreements with automated
rule classification (Rules A-I).

Usage:
  python consensus_agreement.py --batch 1
  python consensus_agreement.py --batch-range 1-5
  python consensus_agreement.py --sonnet path/to/sonnet.csv --gpt path/to/gpt.csv
  python consensus_agreement.py --all
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCHEMA_DIR.parent
SCHEMA_JSON = SCHEMA_DIR / "SLU_schema_v1.0.json"
MASTER_INDEX = SCRIPT_DIR / "master_unlabeled_index.csv"
POSSIBLE_MASTER_CSVS = [
    REPO_ROOT / "benchmark_curation" / "sap_commands_master.csv",
    REPO_ROOT / "sap-dialog-system" / "benchmark_curation" / "sap_commands_master.csv",
]
MASTER_CSV = next((p for p in POSSIBLE_MASTER_CSVS if p.exists()), None)
PREDICTIONS_DIR = SCRIPT_DIR / "predictions"
AGREEMENTS_DIR = SCRIPT_DIR / "agreements"
DISAGREEMENTS_DIR = SCRIPT_DIR / "disagreements"

AGREEMENTS_DIR.mkdir(parents=True, exist_ok=True)
DISAGREEMENTS_DIR.mkdir(parents=True, exist_ok=True)

# ANSI terminal styles
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
RESET = "\033[0m"


def load_schema(schema_path: Path = SCHEMA_JSON) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Dict[str, Any]]]:
    """Loads the canonical schema and returns domain mappings and tool parameter definitions."""
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found at {schema_path}")
    with open(schema_path, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    tool_to_domain = {}
    tool_defs = {}
    for t in data["tools"]:
        name = t["name"]
        domain = t["domain"]
        tool_to_domain[name] = domain
        tool_defs[name] = {
            "parameters": t["parameters"]["properties"],
            "required": t["parameters"].get("required", [])
        }
    return data, tool_to_domain, tool_defs


def clean_quotes(text: str) -> str:
    """Replaces Unicode smart quotes and dashes with standard ASCII equivalents."""
    return (
        text.replace("“", "\"")
        .replace("”", "\"")
        .replace("‘", "'")
        .replace("’", "'")
        .replace("—", "-")
        .replace("–", "-")
    )


def normalize_id(raw_id: str) -> str:
    """Normalizes an ID into canonical 'SAP-CMD-XXXX' format or preserves numeric ID."""
    raw = raw_id.strip()
    if raw.startswith("SAP-CMD-"):
        return raw
    # If integer, pad to 4 digits with SAP-CMD- prefix if in master range
    if raw.isdigit():
        val = int(raw)
        return f"SAP-CMD-{val:04d}"
    return raw


def parse_slots_json(slots_raw: str) -> Dict[str, Any]:
    """Robustly parses slots_json string from CSV, handling CSV quote escaping and malformed JSON."""
    s = clean_quotes(slots_raw.strip())
    if not s:
        return {}
    # If wrapped in redundant outer quotes
    if s.startswith("\"") and s.endswith("\"") and len(s) > 1:
        s = s[1:-1].replace("\"\"", "\"")
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            # Normalize keys and values
            norm_dict = {}
            for k, v in data.items():
                k_clean = k.strip().lower()
                if isinstance(v, str):
                    v_clean = v.strip().lower()
                    if v_clean:  # omit empty strings
                        norm_dict[k_clean] = v_clean
                elif isinstance(v, list):
                    norm_dict[k_clean] = [x.strip().lower() if isinstance(x, str) else x for x in v]
                elif v is not None:
                    norm_dict[k_clean] = v
            return norm_dict
        return {}
    except Exception:
        # Fallback regex extraction of key-values
        pattern = re.findall(r'["\']?([a-zA-Z0-9_]+)["\']?\s*:\s*["\']([^"\']*)["\']', s)
        if pattern:
            return {k.strip().lower(): v.strip().lower() for k, v in pattern if v.strip()}
        return {"_raw_unparsed": s}


def load_prediction_csv(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """Loads and standardizes a model prediction CSV file."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Prediction file not found: {csv_path}")

    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        content = clean_quotes(f.read())

    reader = csv.DictReader(io.StringIO(content))
    data = {}
    for row in reader:
        # Resolve ID column
        id_key = next((k for k in row.keys() if k.lower() in ("id", "command_id", "cmd_id")), None)
        if not id_key or not row[id_key]:
            continue
        raw_id = row[id_key]
        norm_cmd_id = normalize_id(raw_id)

        domain = row.get("domain", "").strip().lower()
        intent = row.get("intent", "").strip().lower()
        slots_json_raw = row.get("slots_json", "{}")
        slots = parse_slots_json(slots_json_raw)

        data[norm_cmd_id] = {
            "raw_id": raw_id,
            "domain": domain,
            "intent": intent,
            "slots": slots,
            "slots_raw": slots_json_raw,
        }
    return data


def load_master_lookup() -> Dict[str, Dict[str, str]]:
    """Loads master command prompt and metadata by normalized ID and prompt text."""
    lookup = {}
    if MASTER_CSV and MASTER_CSV.exists():
        with open(MASTER_CSV, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                lookup[r["id"]] = r
                if r["id"].startswith("SAP-CMD-"):
                    num_key = str(int(r["id"].replace("SAP-CMD-", "")))
                    lookup[num_key] = r
    if MASTER_INDEX.exists():
        with open(MASTER_INDEX, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                lookup[r["id"]] = r
                if r["id"].startswith("SAP-CMD-"):
                    num_key = str(int(r["id"].replace("SAP-CMD-", "")))
                    lookup[num_key] = r
    return lookup


def validate_schema(
    record: Dict[str, Any],
    tool_to_domain: Dict[str, str],
    tool_defs: Dict[str, Dict[str, Any]]
) -> List[str]:
    """Validates record domain, intent, and slot parameters against Schema v1.2."""
    issues = []
    domain = record["domain"]
    intent = record["intent"]
    slots = record["slots"]

    if intent not in tool_to_domain:
        issues.append(f"Unknown intent: '{intent}'")
    else:
        canonical_domain = tool_to_domain[intent]
        if domain != canonical_domain:
            issues.append(f"Domain mismatch for {intent}: got '{domain}', expected '{canonical_domain}'")

        expected_params = tool_defs[intent]["parameters"]
        for s_key, s_val in slots.items():
            if s_key == "_raw_unparsed":
                issues.append("Unparseable JSON in slots")
                continue
            if s_key not in expected_params:
                issues.append(f"Hallucinated slot '{s_key}' for tool '{intent}'")
            else:
                p_def = expected_params[s_key]
                if "enum" in p_def:
                    allowed = [e.lower() for e in p_def["enum"]]
                    if isinstance(s_val, str) and s_val.lower() not in allowed:
                        issues.append(f"Invalid enum value '{s_val}' for slot '{s_key}' (allowed: {allowed})")
    return issues


def classify_disagreement(
    s_rec: Dict[str, Any],
    g_rec: Dict[str, Any],
    prompt: str
) -> Tuple[str, str, str]:
    """
    Classifies disagreement into functional categories and identifies applicable rules (A-I).
    Returns (disagreement_category, rule_tag, suggested_resolution).
    """
    s_dom, s_int, s_slots = s_rec["domain"], s_rec["intent"], s_rec["slots"]
    g_dom, g_int, g_slots = g_rec["domain"], g_rec["intent"], g_rec["slots"]

    if s_dom != g_dom:
        # Check Rule F: places opening hours vs qa_search
        if ("places_search" in (s_int, g_int)) and ("qa_search" in (s_int, g_int)):
            if any(w in prompt.lower() for w in ["open until", "hours", "when is", "open"]):
                return "DOMAIN_MISMATCH", "Rule F (Commercial Business Opening Hours)", "Route to maps_places.places_search"
        return "DOMAIN_MISMATCH", "Cross-Domain Ambiguity", f"Adjudicate between {s_dom} vs {g_dom}"

    if s_int != g_int:
        if set([s_int, g_int]) == set(["media_play", "media_search"]):
            if any(w in prompt.lower() for w in ["show me", "recommend", "movies with", "find"]):
                return "INTENT_MISMATCH", "Media Search vs Play", "Route to media.media_search (catalog browsing)"
            return "INTENT_MISMATCH", "Media Search vs Play", "Route to media.media_play (playback stream)"
        if set([s_int, g_int]) == set(["iot_device_power", "iot_sensor_query"]):
            if any(w in prompt.lower() for w in ["is the", "what's the", "check if"]):
                return "INTENT_MISMATCH", "IoT Sensor vs Power", "Route to smart_home.iot_sensor_query (state inspection)"
            return "INTENT_MISMATCH", "IoT Sensor vs Power", "Route to smart_home.iot_device_power (actuation toggle)"
        return "INTENT_MISMATCH", "Intent Boundary", f"Adjudicate between {s_int} vs {g_int}"

    # Domain and intent match, but slots differ
    all_keys = set(s_slots.keys()) | set(g_slots.keys())

    # Check Rule D: Generic event noun in schedule_manage
    if s_int == "schedule_manage":
        s_title = s_slots.get("title", "")
        g_title = g_slots.get("title", "")
        generic_nouns = ["meeting", "call", "appointment", "reminder"]
        if (s_title in generic_nouns and not g_title) or (g_title in generic_nouns and not s_title):
            matched_noun = s_title if s_title in generic_nouns else g_title
            return (
                "SLOT_DISCREPANCY",
                "Rule D (Generic Event Title Preservation)",
                f"Retain title: '{matched_noun}' per Schema v1.2 Rule D"
            )

    # Check Rule E: Alarm recurrence token constraint
    if s_int == "alarm_manage":
        s_freq = s_slots.get("general_frequency")
        g_freq = g_slots.get("general_frequency")
        if (s_freq and not g_freq) or (g_freq and not s_freq):
            # If coordinated days exist without recurrence markers
            if any(w in prompt.lower() for w in ["and friday", "and saturday", "on thursday", "on monday"]):
                if not any(w in prompt.lower() for w in ["every", "daily", "weekdays"]):
                    return (
                        "SLOT_DISCREPANCY",
                        "Rule E (Alarm Recurrence Token Constraint)",
                        "Omit general_frequency; keep coordinated days in date slot"
                    )

    # Check Rule H: origin vs destination in maps_route
    if s_int == "maps_route":
        if ("origin" in s_slots and "origin" not in g_slots) or ("origin" in g_slots and "origin" not in s_slots):
            return (
                "SLOT_DISCREPANCY",
                "Rule H (Maps Route Origin & Destination)",
                "Separate departure point into origin and target into destination"
            )

    # Check Rule A: Possessive or article stripping
    for k in all_keys:
        v_s = str(s_slots.get(k, ""))
        v_g = str(g_slots.get(k, ""))
        if v_s != v_g:
            for prefix in ["my ", "our ", "the ", "a ", "an ", "to ", "at "]:
                if v_s == prefix + v_g or v_g == prefix + v_s:
                    clean_val = v_g if v_s.startswith(prefix) else v_s
                    return (
                        "SLOT_DISCREPANCY",
                        "Rule A (BaseNP / Possessive Stripping)",
                        f"Strip prefix '{prefix.strip()}'; use '{clean_val}'"
                    )

    # Generic slot value or key discrepancy
    diff_keys = [k for k in all_keys if s_slots.get(k) != g_slots.get(k)]
    return (
        "SLOT_DISCREPANCY",
        f"Slot Value/Key Discrepancy ({', '.join(diff_keys)})",
        "Adjudicate between model slot extractions"
    )


def compare_batch(
    sonnet_path: Path,
    gpt_path: Path,
    output_prefix: str = "consensus"
) -> Dict[str, Any]:
    """Compares Sonnet and GPT prediction CSVs and partitions into agreements and triage."""
    _, tool_to_domain, tool_defs = load_schema()
    master_lookup = load_master_lookup()

    s_preds = load_prediction_csv(sonnet_path)
    g_preds = load_prediction_csv(gpt_path)

    common_ids = sorted(set(s_preds.keys()) & set(g_preds.keys()))
    if not common_ids:
        # Try matching by raw ID if normalized IDs did not overlap
        common_ids = sorted(set(s_preds.keys()))

    agreements = []
    disagreements = []
    schema_warnings = []

    domain_agreements = 0
    intent_agreements = 0
    slot_em_agreements = 0

    for cmd_id in common_ids:
        s_item = s_preds.get(cmd_id)
        g_item = g_preds.get(cmd_id)
        if not s_item or not g_item:
            continue

        meta = master_lookup.get(cmd_id, {})
        prompt = meta.get("text", meta.get("prompt", f"Utterance {cmd_id}"))

        # Schema validation
        s_issues = validate_schema(s_item, tool_to_domain, tool_defs)
        g_issues = validate_schema(g_item, tool_to_domain, tool_defs)
        if s_issues or g_issues:
            schema_warnings.append({
                "id": cmd_id,
                "sonnet_issues": s_issues,
                "gpt_issues": g_issues
            })

        dom_match = (s_item["domain"] == g_item["domain"])
        int_match = (s_item["intent"] == g_item["intent"])
        slots_match = (s_item["slots"] == g_item["slots"])

        if dom_match:
            domain_agreements += 1
        if dom_match and int_match:
            intent_agreements += 1
        if dom_match and int_match and slots_match:
            slot_em_agreements += 1

        if dom_match and int_match and slots_match:
            # Full consensus agreement
            agreements.append({
                "id": cmd_id,
                "prompt": prompt,
                "domain": s_item["domain"],
                "intent": s_item["intent"],
                "slots_json": json.dumps(s_item["slots"], ensure_ascii=False),
                "consensus_status": "AGREED",
                "notes": "Unanimous dual-frontier agreement"
            })
        else:
            cat, rule_tag, suggested_res = classify_disagreement(s_item, g_item, prompt)
            disagreements.append({
                "id": cmd_id,
                "prompt": prompt,
                "disagreement_type": cat,
                "suggested_rule": rule_tag,
                "sonnet_domain": s_item["domain"],
                "sonnet_intent": s_item["intent"],
                "sonnet_slots": json.dumps(s_item["slots"], ensure_ascii=False),
                "gpt_domain": g_item["domain"],
                "gpt_intent": g_item["intent"],
                "gpt_slots": json.dumps(g_item["slots"], ensure_ascii=False),
                "suggested_resolution": suggested_res,
                "adjudicated_domain": "",
                "adjudicated_intent": "",
                "adjudicated_slots_json": "",
                "adjudication_notes": ""
            })

    total = len(common_ids)
    stats = {
        "total": total,
        "domain_agreement_count": domain_agreements,
        "domain_agreement_rate": (domain_agreements / total * 100) if total else 0.0,
        "intent_agreement_count": intent_agreements,
        "intent_agreement_rate": (intent_agreements / total * 100) if total else 0.0,
        "slot_em_count": slot_em_agreements,
        "slot_em_rate": (slot_em_agreements / total * 100) if total else 0.0,
        "disagreement_count": len(disagreements),
        "schema_warning_count": len(schema_warnings)
    }

    # Save outputs
    agreed_path = AGREEMENTS_DIR / f"{output_prefix}_agreed.csv"
    with open(agreed_path, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["id", "prompt", "domain", "intent", "slots_json", "consensus_status", "notes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(agreements)

    triage_path = DISAGREEMENTS_DIR / f"{output_prefix}_triage.csv"
    with open(triage_path, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "id", "prompt", "disagreement_type", "suggested_rule",
            "sonnet_domain", "sonnet_intent", "sonnet_slots",
            "gpt_domain", "gpt_intent", "gpt_slots",
            "suggested_resolution", "adjudicated_domain", "adjudicated_intent",
            "adjudicated_slots_json", "adjudication_notes"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(disagreements)

    return {
        "stats": stats,
        "agreed_path": agreed_path,
        "triage_path": triage_path,
        "agreements": agreements,
        "disagreements": disagreements,
        "schema_warnings": schema_warnings
    }


def print_report(res: Dict[str, Any], title: str = "Consensus Evaluation"):
    """Prints a formatted terminal report of agreement statistics and triage items."""
    s = res["stats"]
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")
    print(f"Total Commands Compared: {BOLD}{s['total']}{RESET}")
    print(f"  • Domain Agreement:  {GREEN}{s['domain_agreement_count']}/{s['total']}{RESET} ({s['domain_agreement_rate']:.1f}%)")
    print(f"  • Intent Agreement:  {GREEN}{s['intent_agreement_count']}/{s['total']}{RESET} ({s['intent_agreement_rate']:.1f}%)")
    print(f"  • Slot EM Agreement: {YELLOW if s['slot_em_rate'] < 80 else GREEN}{s['slot_em_count']}/{s['total']}{RESET} ({s['slot_em_rate']:.1f}%)")
    print(f"  • Triage Queue:      {RED if s['disagreement_count'] > 0 else GREEN}{s['disagreement_count']} commands{RESET}")
    if s["schema_warning_count"]:
        print(f"  • Schema Violations: {RED}{s['schema_warning_count']} items flagged{RESET}")

    print(f"\n{BOLD}Saved Deliverables:{RESET}")
    print(f"  [Accepted Gold] {res['agreed_path']}")
    print(f"  [Triage Queue]  {res['triage_path']}")

    if res["disagreements"]:
        print(f"\n{BOLD}Triage Disagreements Summary:{RESET}")
        rule_counts = Counter(d["suggested_rule"] for d in res["disagreements"])
        for r, cnt in rule_counts.most_common():
            print(f"  {r:45s}: {cnt:2d}")

        print(f"\n{BOLD}Sample Triage Item (1 of {len(res['disagreements'])}):{RESET}")
        sample = res["disagreements"][0]
        print(f"  {BOLD}ID:{RESET} {sample['id']} — \"{sample['prompt']}\"")
        print(f"  {BOLD}Classification:{RESET} {YELLOW}{sample['suggested_rule']}{RESET}")
        print(f"  {CYAN}Sonnet:{RESET} {sample['sonnet_domain']}.{sample['sonnet_intent']} -> {sample['sonnet_slots']}")
        print(f"  {MAGENTA}GPT:   {RESET} {sample['gpt_domain']}.{sample['gpt_intent']} -> {sample['gpt_slots']}")
        print(f"  {GREEN}Suggested Resolution:{RESET} {sample['suggested_resolution']}")
    print()


def aggregate_master_deliverables():
    """Aggregates all individual batch agreement and triage files into cumulative deliverables."""
    cumulative_agreed_path = SCRIPT_DIR / "consensus_gold_cumulative.csv"
    cumulative_triage_path = SCRIPT_DIR / "consensus_triage_cumulative.csv"

    agreed_files = sorted(list(AGREEMENTS_DIR.glob("*_agreed.csv")))
    triage_files = sorted(list(DISAGREEMENTS_DIR.glob("*_triage.csv")))

    total_agreed = 0
    with open(cumulative_agreed_path, mode="w", newline="", encoding="utf-8") as out_f:
        fieldnames = ["id", "prompt", "domain", "intent", "slots_json", "consensus_status", "notes"]
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
        seen = set()
        for f in agreed_files:
            with open(f, mode="r", encoding="utf-8") as in_f:
                for row in csv.DictReader(in_f):
                    if row["id"] not in seen:
                        seen.add(row["id"])
                        writer.writerow(row)
                        total_agreed += 1

    total_triage = 0
    with open(cumulative_triage_path, mode="w", newline="", encoding="utf-8") as out_f:
        fieldnames = [
            "id", "prompt", "disagreement_type", "suggested_rule",
            "sonnet_domain", "sonnet_intent", "sonnet_slots",
            "gpt_domain", "gpt_intent", "gpt_slots",
            "suggested_resolution", "adjudicated_domain", "adjudicated_intent",
            "adjudicated_slots_json", "adjudication_notes"
        ]
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
        seen = set()
        for f in triage_files:
            with open(f, mode="r", encoding="utf-8") as in_f:
                for row in csv.DictReader(in_f):
                    if row["id"] not in seen:
                        seen.add(row["id"])
                        writer.writerow(row)
                        total_triage += 1

    print(f"\n{BOLD}{GREEN}=== Cumulative Consensus Aggregation Complete ==={RESET}")
    print(f"Cumulative Accepted Gold: {BOLD}{total_agreed}{RESET} -> {cumulative_agreed_path}")
    print(f"Cumulative Triage Queue:  {BOLD}{total_triage}{RESET} -> {cumulative_triage_path}\n")


def display_status():
    """Displays pipeline status across the 24 consensus batches and 1,194 commands."""
    batches_dir = SCRIPT_DIR / "batches"
    total_unlabeled = 1194
    if MASTER_INDEX.exists():
        with open(MASTER_INDEX, mode="r", encoding="utf-8") as f:
            total_unlabeled = len(list(csv.DictReader(f)))

    print(f"\n{BOLD}{CYAN}=== SAP SLU Consensus Annotation Status ==={RESET}")
    print(f"Total Benchmark Target:   1,309 commands")
    print(f"  • Reference Dev Gold:   115 master commands (150 gold prompts: 50 pilot + 100 frontier)")
    print(f"  • Consensus Annotation: {total_unlabeled} commands partitioned across 24 batches")
    print(f"{DIM}{'─' * 60}{RESET}")

    sonnet_batches = {p.stem for p in (PREDICTIONS_DIR / "sonnet").glob("batch_*.csv")}
    gpt_batches = {p.stem for p in (PREDICTIONS_DIR / "gpt").glob("batch_*.csv")}
    agreed_batches = {p.stem.replace("_agreed", "") for p in AGREEMENTS_DIR.glob("batch_*_agreed.csv")}

    print(f"{BOLD}{'Batch':<12} {'Commands':<10} {'Sonnet':<10} {'GPT':<10} {'Consensus Status'}{RESET}")
    for b in range(1, 25):
        b_name = f"batch_{b:02d}"
        count = 44 if b == 24 else 50
        s_ok = "✓ Ready" if b_name in sonnet_batches else "Pending"
        g_ok = "✓ Ready" if b_name in gpt_batches else "Pending"
        if b_name in agreed_batches:
            c_status = f"{GREEN}✓ Adjudicated{RESET}"
        elif b_name in sonnet_batches and b_name in gpt_batches:
            c_status = f"{YELLOW}Ready to Run Agreement{RESET}"
        elif b_name in sonnet_batches or b_name in gpt_batches:
            c_status = f"{CYAN}Awaiting 2nd Model{RESET}"
        else:
            c_status = f"{DIM}Unlabeled{RESET}"
        print(f"{b_name:<12} {count:<10} {s_ok:<10} {g_ok:<10} {c_status}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Dual-Frontier Consensus Agreement & Triage Script")
    parser.add_argument("--batch", type=int, help="Batch number to evaluate (e.g. 1)")
    parser.add_argument("--batch-range", type=str, help="Batch range to evaluate (e.g. 1-5)")
    parser.add_argument("--sonnet", type=str, help="Explicit path to Sonnet predictions CSV")
    parser.add_argument("--gpt", type=str, help="Explicit path to GPT predictions CSV")
    parser.add_argument("--all", action="store_true", help="Process all completed prediction batches in predictions/")
    parser.add_argument("--aggregate", action="store_true", help="Aggregate all agreed and triage batches into master consensus files")
    parser.add_argument("--status", action="store_true", help="Display global consensus labeling progress and coverage")

    args = parser.parse_args()

    if args.status:
        display_status()
        return

    if args.aggregate:
        aggregate_master_deliverables()
        return

    if args.sonnet and args.gpt:
        s_path = Path(args.sonnet)
        g_path = Path(args.gpt)
        res = compare_batch(s_path, g_path, output_prefix="custom_run")
        print_report(res, title=f"Consensus: {s_path.name} vs {g_path.name}")
        return

    if args.batch:
        b_str = f"batch_{args.batch:02d}"
        s_path = PREDICTIONS_DIR / "sonnet" / f"{b_str}.csv"
        g_path = PREDICTIONS_DIR / "gpt" / f"{b_str}.csv"
        if not s_path.exists() or not g_path.exists():
            print(f"Error: Prediction files for batch {args.batch} not found in {PREDICTIONS_DIR}", file=sys.stderr)
            print(f"Expected: {s_path} and {g_path}", file=sys.stderr)
            sys.exit(1)
        res = compare_batch(s_path, g_path, output_prefix=b_str)
        print_report(res, title=f"Consensus Batch {args.batch}")
        return

    if args.batch_range:
        parts = args.batch_range.split("-")
        start_b, end_b = int(parts[0]), int(parts[1])
        for b in range(start_b, end_b + 1):
            b_str = f"batch_{b:02d}"
            s_path = PREDICTIONS_DIR / "sonnet" / f"{b_str}.csv"
            g_path = PREDICTIONS_DIR / "gpt" / f"{b_str}.csv"
            if s_path.exists() and g_path.exists():
                res = compare_batch(s_path, g_path, output_prefix=b_str)
                print_report(res, title=f"Consensus Batch {b}")
            else:
                print(f"Skipping Batch {b}: missing predictions in {PREDICTIONS_DIR}")
        return

    if args.all:
        sonnet_files = sorted(list((PREDICTIONS_DIR / "sonnet").glob("batch_*.csv")))
        if not sonnet_files:
            print(f"No batch files found in {PREDICTIONS_DIR / 'sonnet'}")
            return
        processed = 0
        for s_path in sonnet_files:
            g_path = PREDICTIONS_DIR / "gpt" / s_path.name
            if g_path.exists():
                b_name = s_path.stem
                res = compare_batch(s_path, g_path, output_prefix=b_name)
                print_report(res, title=f"Consensus {b_name.replace('_', ' ').title()}")
                processed += 1
            else:
                print(f"Waiting for GPT predictions for {s_path.name}...")
        print(f"\n{BOLD}{GREEN}Processed {processed} batch pairs.{RESET}")
        aggregate_master_deliverables()
        return

    # Default demo test on historical batches if no arguments provided
    # Test on historical Batch 1 and Batch 2 in schema_freeze
    hist_s1 = SCHEMA_DIR / "sonnet5-5_batch1.csv"
    hist_g1 = SCHEMA_DIR / "gpt6-instant_batch1.csv"
    hist_s2 = SCHEMA_DIR / "sonnet5-5_batch2.csv"
    hist_g2 = SCHEMA_DIR / "gpt6-instant_batch2.csv"

    if hist_s1.exists() and hist_g1.exists():
        print(f"{BOLD}Testing agreement engine on Historical Batch 1 (Pilot Adjudication Set)...{RESET}")
        res1 = compare_batch(hist_s1, hist_g1, output_prefix="historical_batch1")
        print_report(res1, title="Frontier Calibration Batch 1 (Historical)")

    if hist_s2.exists() and hist_g2.exists():
        print(f"{BOLD}Testing agreement engine on Historical Batch 2 (Cross-Domain Stress Set)...{RESET}")
        res2 = compare_batch(hist_s2, hist_g2, output_prefix="historical_batch2")
        print_report(res2, title="Frontier Calibration Batch 2 (Historical)")


if __name__ == "__main__":
    main()
