#!/usr/bin/env python3
"""
browse_frontier.py

Interactive CLI tool to quickly inspect and browse the 100 curated high-ambiguity
frontier commands in schema_freeze/frontier_sample_100.csv (or frontier_100.csv).

Usage:
  python schema_freeze/browse_frontier.py
  python schema_freeze/browse_frontier.py --stats
  python schema_freeze/browse_frontier.py --score 6
  python schema_freeze/browse_frontier.py -d calendar_alarm
  python schema_freeze/browse_frontier.py -t boundary_timer_schedule
  python schema_freeze/browse_frontier.py -q "calories"
  python schema_freeze/browse_frontier.py --flip
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "schema_freeze" else SCRIPT_DIR

# File resolution
POSSIBLE_PATHS = [
    SCRIPT_DIR / "frontier_100.csv",
    SCRIPT_DIR / "frontier_sample_100.csv",
    REPO_ROOT / "schema_freeze" / "frontier_sample_100.csv",
]

CSV_PATH = next((p for p in POSSIBLE_PATHS if p.exists()), None)

# ANSI formatting
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
RESET = "\033[0m"


def load_frontier_data():
    if not CSV_PATH or not CSV_PATH.exists():
        print(f"Error: Could not find frontier_sample_100.csv in {SCRIPT_DIR}", file=sys.stderr)
        sys.exit(1)
    with open(CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def format_score_badge(score_str):
    try:
        s = int(score_str)
    except ValueError:
        return score_str
    if s >= 6:
        return f"{RED}{BOLD}Score {s}{RESET}"
    elif s == 5:
        return f"{YELLOW}{BOLD}Score {s}{RESET}"
    elif s == 4:
        return f"{CYAN}Score {s}{RESET}"
    else:
        return f"{DIM}Score {s}{RESET}"


def print_stats(rows):
    print(f"\n{BOLD}{CYAN}=== Frontier 100 Ambiguity Benchmark — Overview ==={RESET}")
    print(f"Dataset Path: {CSV_PATH}")
    print(f"Total Curated Commands: {BOLD}{len(rows)}{RESET}\n")

    # Ambiguity scores
    scores = Counter(r["ambiguity_score"] for r in rows)
    print(f"{BOLD}Ambiguity Score Distribution:{RESET}")
    for s in sorted(scores.keys(), key=lambda x: -int(x)):
        bar = "█" * scores[s]
        print(f"  Score {s}: {scores[s]:2d} items  {YELLOW}{bar}{RESET}")

    # Domain quotas
    domains = Counter(r["domain_quota"] for r in rows)
    print(f"\n{BOLD}Domain Quotas:{RESET}")
    for d, count in domains.most_common():
        print(f"  {d:20s}: {count:2d}")

    # Haiku predicted intents
    intents = Counter(r["haiku_intent"] for r in rows)
    print(f"\n{BOLD}Haiku Predicted Intents:{RESET}")
    for i, count in intents.most_common():
        print(f"  {i:26s}: {count:2d}")

    # Boundary tags
    boundary_tags = Counter()
    linguistic_tags = Counter()
    for r in rows:
        tags = [t.strip() for t in r["ambiguity_tags"].split(";") if t.strip()]
        for t in tags:
            if t.startswith("boundary_"):
                boundary_tags[t] += 1
            else:
                linguistic_tags[t] += 1

    print(f"\n{BOLD}Boundary Condition Crossovers (Disambiguation Challenges):{RESET}")
    for t, count in boundary_tags.most_common():
        print(f"  {t:38s}: {count:2d}")

    print(f"\n{BOLD}Linguistic Complexity Markers:{RESET}")
    for t, count in linguistic_tags.most_common():
        print(f"  {t:38s}: {count:2d}")
    print()


def interactive_flip_through(rows):
    total = len(rows)
    print(f"\n{BOLD}{CYAN}=== Interactive Flip-Through Mode ({total} commands) ==={RESET}")
    print(f"Press {BOLD}[Enter]{RESET} for next, {BOLD}[b]{RESET} for previous, {BOLD}[q]{RESET} to quit.\n")

    idx = 0
    while 0 <= idx < total:
        r = rows[idx]
        os.system("clear" if os.name == "posix" else "cls")
        print(f"{BOLD}{CYAN}[{idx + 1}/{total}] Command ID: {r['id']}{RESET}  —  {format_score_badge(r['ambiguity_score'])}")
        print(f"{DIM}{'─' * 70}{RESET}")
        print(f"\n  {BOLD}{GREEN}\"{r['prompt']}\"{RESET}\n")
        print(f"{DIM}{'─' * 70}{RESET}")
        print(f"  • {BOLD}Domain Quota:{RESET}    {YELLOW}{r['domain_quota']}{RESET}")
        print(f"  • {BOLD}Haiku Intent:{RESET}    {MAGENTA}{r['haiku_intent']}{RESET}")
        print(f"  • {BOLD}Ambiguity Score:{RESET} {r['ambiguity_score']}/6")
        
        tags = [t.strip() for t in r["ambiguity_tags"].split(";") if t.strip()]
        print(f"  • {BOLD}Tags:{RESET}")
        for t in tags:
            color = RED if t.startswith("boundary_") else CYAN
            print(f"      - {color}{t}{RESET}")
        print(f"\n{DIM}[Enter]: Next  |  [b]: Prev  |  [1-{total}]: Jump  |  [q]: Quit{RESET}")

        try:
            cmd = input(">> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if cmd == "q":
            break
        elif cmd == "b":
            idx = max(0, idx - 1)
        elif cmd.isdigit():
            target = int(cmd) - 1
            if 0 <= target < total:
                idx = target
        else:
            idx += 1

    print("\nExited interactive mode.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and search the 100 frontier ambiguity commands.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-q", "--query", type=str, help="Search substring in prompt")
    parser.add_argument("-d", "--domain", type=str, help="Filter by domain quota (e.g., general_qa, calendar_alarm)")
    parser.add_argument("-i", "--intent", type=str, help="Filter by haiku intent (e.g., qa_search, calendar_manage)")
    parser.add_argument("-s", "--score", type=int, help="Filter by ambiguity score (3, 4, 5, or 6)")
    parser.add_argument("-t", "--tag", type=str, help="Filter by ambiguity tag (e.g., boundary_timer_schedule)")
    parser.add_argument("--stats", action="store_true", help="Show summary statistics and tag counts")
    parser.add_argument("--flip", action="store_true", help="Launch interactive terminal flip-through viewer")
    parser.add_argument("-l", "--limit", type=int, default=100, help="Limit number of rows displayed (default: 100)")

    args = parser.parse_args()
    rows = load_frontier_data()

    if args.stats:
        print_stats(rows)
        return

    if args.flip:
        interactive_flip_through(rows)
        return

    # Filter rows
    filtered = rows

    if args.query:
        q = args.query.lower()
        filtered = [r for r in filtered if q in r["prompt"].lower()]

    if args.domain:
        d = args.domain.lower()
        filtered = [r for r in filtered if d in r["domain_quota"].lower()]

    if args.intent:
        it = args.intent.lower()
        filtered = [r for r in filtered if it in r["haiku_intent"].lower()]

    if args.score is not None:
        filtered = [r for r in filtered if int(r["ambiguity_score"]) == args.score]

    if args.tag:
        t = args.tag.lower()
        filtered = [r for r in filtered if t in r["ambiguity_tags"].lower()]

    print(f"\n{BOLD}Frontier 100 Sample — {len(filtered)} matching command(s):{RESET}")
    print(f"{DIM}{'#':<3} {'ID':<6} {'Score':<9} {'Domain':<16} {'Intent':<18} {'Prompt'}{RESET}")
    print(f"{DIM}{'─' * 100}{RESET}")

    for idx, r in enumerate(filtered[:args.limit], 1):
        num = f"{DIM}{idx:<3}{RESET}"
        cid = f"{r['id']:<6}"
        s_badge = f"{format_score_badge(r['ambiguity_score']):<18}"
        dom = f"{YELLOW}{r['domain_quota'][:15]:<16}{RESET}"
        intent = f"{MAGENTA}{r['haiku_intent'][:17]:<18}{RESET}"
        prompt = f"{BOLD}{r['prompt']}{RESET}"
        print(f"{num} {cid} {s_badge} {dom} {intent} {prompt}")

    if len(filtered) > args.limit:
        print(f"\n{DIM}... and {len(filtered) - args.limit} more items.{RESET}")
    print()


if __name__ == "__main__":
    main()
