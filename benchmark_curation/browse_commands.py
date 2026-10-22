#!/usr/bin/env python3
"""
browse_commands.py

Interactive CLI tool to browse, search, and inspect the ~1,300 voice commands
in the Speech Accessibility Project (SAP) prompt inventory.

Usage Examples:
  python benchmark_curation/browse_commands.py --stats
  python benchmark_curation/browse_commands.py -q "weather"
  python benchmark_curation/browse_commands.py -c "Smart Home"
  python benchmark_curation/browse_commands.py --cohort PD --universal
  python benchmark_curation/browse_commands.py --random 5
  python benchmark_curation/browse_commands.py --inspect SAP-CMD-0005
"""

import argparse
import json
import random
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "benchmark_curation" else SCRIPT_DIR
MASTER_JSON = SCRIPT_DIR / "sap_commands_master.json"

# ANSI color codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def load_dataset():
    if not MASTER_JSON.exists():
        print(f"Error: Master file not found at {MASTER_JSON}. Run build_sap_commands_dataset.py first.", file=sys.stderr)
        sys.exit(1)
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["metadata"], data["commands"]


def print_stats(metadata, commands):
    stats = metadata.get("stats", {})
    print(f"\n{BOLD}{CYAN}=== Speech Accessibility Project (SAP) Voice Commands Inventory ==={RESET}")
    print(f"Source: {metadata.get('source', '')}")
    print(f"Total Unique Voice Commands: {BOLD}{stats.get('total_unique_commands', len(commands)):,}{RESET}")
    print(f"Universal Prompts (Blocks 1 & 10): {stats.get('total_universal_b1_b10', 'N/A')}")
    print(f"Shared across all 3 clinical cohorts: {stats.get('cohorts', {}).get('all_three_cohorts', 'N/A')}\n")

    print(f"{BOLD}Breakdown by Clinical Cohort:{RESET}")
    cohorts = stats.get("cohorts", {})
    print(f"  • Parkinson's & ALS (PD): {cohorts.get('PD_total', 'N/A')} commands")
    print(f"  • Down Syndrome & CP (DS): {cohorts.get('DS_total', 'N/A')} commands")
    print(f"  • Stroke:                  {cohorts.get('Stroke_total', 'N/A')} commands")
    print(f"  • Combinations:")
    for combo, count in cohorts.get("combinations", {}).items():
        print(f"      - {combo:20s}: {count:4d}")

    print(f"\n{BOLD}Breakdown by Functional Domain / Category:{RESET}")
    for cat, count in stats.get("categories", {}).items():
        bar = "█" * int(count / 15)
        print(f"  {cat:24s} | {count:4d} | {DIM}{bar}{RESET}")

    print(f"\n{BOLD}Complexity (Word Count):{RESET}")
    for comp, count in stats.get("complexity", {}).items():
        print(f"  {comp:24s} | {count:4d}")
    print()


def inspect_command(cmd):
    print(f"\n{BOLD}{CYAN}---------------- Command Details: {cmd['id']} ----------------{RESET}")
    print(f"{BOLD}Prompt Text:{RESET}        {GREEN}\"{cmd['text']}\"{RESET}")
    print(f"{BOLD}Normalized Key:{RESET}     {cmd['clean_text']}")
    print(f"{BOLD}Category / Domain:{RESET}  {YELLOW}{cmd['category']}{RESET}")
    print(f"{BOLD}Canonical Tool:{RESET}     {MAGENTA}{cmd['tool_heuristic']}{RESET}")
    print(f"{BOLD}Clinical Cohorts:{RESET}   {', '.join(cmd['cohorts'])} ({cmd['cohort_count']} cohort(s))")
    print(f"{BOLD}Universal (B1/B10):{RESET} {'Yes (Read by 100% of participants)' if cmd['is_universal_b1_b10'] else 'No (Rotation schedule)'}")
    print(f"{BOLD}Allocation Groups:{RESET}  {', '.join(cmd['participant_groups']) if cmd['participant_groups'] else 'None'}")
    print(f"{BOLD}Length:{RESET}             {cmd['word_count']} words, {cmd['char_count']} chars ({cmd['complexity']})")
    if cmd.get("avg_perplexity") is not None:
        print(f"{BOLD}Avg Perplexity:{RESET}     {cmd['avg_perplexity']}")
    print(f"{BOLD}Source Files:{RESET}       {', '.join(cmd['sources'])}")
    print(f"{BOLD}Block Sheets:{RESET}       {', '.join(cmd['blocks'])}")
    print(f"{CYAN}------------------------------------------------------------{RESET}\n")


def format_command_row(cmd):
    cid = f"{DIM}{cmd['id']}{RESET}"
    text = f"{BOLD}{cmd['text']}{RESET}"
    cat = f"{YELLOW}[{cmd['category']}]{RESET}"
    cohorts = f"{CYAN}{'/'.join(cmd['cohorts'])}{RESET}"
    univ = f"{GREEN}★ Univ{RESET}" if cmd["is_universal_b1_b10"] else f"{DIM}Rotat{RESET}"
    return f"{cid}  {univ:8s}  {cohorts:12s}  {cat:26s}  {text}"


def main():
    parser = argparse.ArgumentParser(
        description="Browse, filter, and inspect ~1,300 SAP voice commands.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-q", "--query", type=str, help="Full-text substring search in commands")
    parser.add_argument("-c", "--category", type=str, help="Filter by category / domain (e.g., 'Smart Home', 'Tasks')")
    parser.add_argument("--cohort", type=str, choices=["PD", "DS", "Stroke", "all3"], help="Filter by cohort")
    parser.add_argument("-u", "--universal", action="store_true", help="Only show universal Block 1 & 10 commands")
    parser.add_argument("-r", "--random", type=int, metavar="N", help="Pick N random commands from the filtered set")
    parser.add_argument("-i", "--inspect", type=str, metavar="ID", help="Inspect full details for command ID (e.g., SAP-CMD-0001)")
    parser.add_argument("-l", "--limit", type=int, default=50, help="Maximum number of items to display (default: 50, 0 for all)")
    parser.add_argument("-s", "--stats", action="store_true", help="Show summary statistics dashboard")
    parser.add_argument("--json", action="store_true", help="Output filtered results as raw JSON")

    args = parser.parse_args()

    metadata, commands = load_dataset()

    if args.stats:
        print_stats(metadata, commands)
        if not (args.query or args.category or args.cohort or args.universal or args.inspect or args.random):
            return

    if args.inspect:
        target_id = args.inspect.strip().upper()
        match = next((c for c in commands if c["id"].upper() == target_id), None)
        if match:
            inspect_command(match)
        else:
            print(f"Command with ID '{args.inspect}' not found.", file=sys.stderr)
        return

    # Filter logic
    filtered = commands

    if args.query:
        q = args.query.lower()
        filtered = [c for c in filtered if q in c["text"].lower() or q in c["clean_text"]]

    if args.category:
        c_filter = args.category.lower()
        filtered = [c for c in filtered if c_filter in c["category"].lower()]

    if args.cohort:
        if args.cohort == "all3":
            filtered = [c for c in filtered if len(c["cohorts"]) == 3]
        else:
            filtered = [c for c in filtered if args.cohort in c["cohorts"]]

    if args.universal:
        filtered = [c for c in filtered if c["is_universal_b1_b10"]]

    if args.random:
        n = min(args.random, len(filtered))
        filtered = random.sample(filtered, n)

    if args.json:
        print(json.dumps(filtered, indent=2))
        return

    total_matches = len(filtered)
    limit = args.limit if args.limit > 0 else total_matches
    display_items = filtered[:limit]

    print(f"\n{BOLD}Found {total_matches:,} matching command(s){RESET}" + (f" (displaying first {len(display_items)}):" if total_matches > len(display_items) else ":"))
    print(f"{DIM}ID           Type      Cohorts       Category                    Prompt Text{RESET}")
    print(f"{DIM}{'-'*100}{RESET}")
    for cmd in display_items:
        print(format_command_row(cmd))

    if total_matches > len(display_items):
        print(f"\n{DIM}... and {total_matches - len(display_items)} more items. Use --limit 0 to view all, or narrow with -q, -c, --cohort.{RESET}\n")
    else:
        print()


if __name__ == "__main__":
    main()
