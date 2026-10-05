#!/usr/bin/env python3
"""
extract_unique_commands.py

Extracts high-frequency candidate command templates from the SAP (Speech Accessibility Project)
development manifest, filters out spontaneous survey speech and standalone wake words,
and exports structured metadata for benchmark curation.

Input Manifest Files:
  - dev.tsv: Fairseq manifest (Line 0 is root path, lines 1..N contain audio_path\\tsample_frames)
  - dev.origin.wrd: Verbatim human transcriptions (contains survey prompts in square brackets)
  - dev.wrd.without.parentheses: Normalized intended text oracle (uppercase, disfluencies removed)

Filtering Rules:
  1. Discard spontaneous survey speech: dev.origin.wrd contains '[' or ']'
  2. Normalize text: lowercase and strip leading/trailing whitespace
  3. Discard standalone wake words: hey siri, alexa, hey google, cortana, hey facebook, computer
  4. Frequency threshold: retain templates with count >= min_count (default: 5)
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Standalone wake words to discard
STANDALONE_WAKE_WORDS: Set[str] = {
    "hey siri",
    "alexa",
    "hey google",
    "cortana",
    "hey facebook",
    "computer",
}


def extract_speaker_id(audio_path: str) -> str:
    """
    Extracts the speaker UUID from the audio file path.
    Expected audio filename format: <speaker_uuid>_<session>_<id>.wav
    Example:
      /projects/bczs/SAPC/data/processed/dev/02005a84-8847-4ef7-7b99-08dc286c108f_1063_3859.wav
      -> 02005a84-8847-4ef7-7b99-08dc286c108f
    """
    filename = os.path.basename(audio_path)
    return filename.split("_")[0]


def extract_candidate_commands(
    manifest_dir: Path,
    min_count: int = 5,
    wake_words: Set[str] = STANDALONE_WAKE_WORDS,
) -> Dict[str, Dict[str, Any]]:
    """
    Reads dev manifest files, applies filtering rules, and groups commands by canonical text.
    """
    tsv_path = manifest_dir / "dev.tsv"
    origin_wrd_path = manifest_dir / "dev.origin.wrd"
    clean_wrd_path = manifest_dir / "dev.wrd.without.parentheses"

    for p in [tsv_path, origin_wrd_path, clean_wrd_path]:
        if not p.is_file():
            raise FileNotFoundError(f"Manifest file not found: {p}")

    logger.info(f"Loading manifests from {manifest_dir}...")

    # 1. Load dev.tsv (skip header line 0: root directory)
    with open(tsv_path, "r", encoding="utf-8") as f:
        root_dir = f.readline().strip()
        tsv_lines = [line.strip().split("\t")[0] for line in f if line.strip()]

    # 2. Load dev.origin.wrd and dev.wrd.without.parentheses
    with open(origin_wrd_path, "r", encoding="utf-8") as f:
        origin_lines = [line.strip() for line in f]

    with open(clean_wrd_path, "r", encoding="utf-8") as f:
        clean_lines = [line.strip() for line in f]

    # Verify alignment
    total_audio_entries = len(tsv_lines)
    if not (total_audio_entries == len(origin_lines) == len(clean_lines)):
        raise ValueError(
            f"Manifest line count mismatch! dev.tsv audio lines: {total_audio_entries}, "
            f"dev.origin.wrd: {len(origin_lines)}, "
            f"dev.wrd.without.parentheses: {len(clean_lines)}"
        )

    logger.info(
        f"Verified line alignment across manifests: {total_audio_entries:,} audio records "
        f"(root dir in header: {root_dir})"
    )

    # Accumulate candidates
    groups: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "frequency": 0,
            "manifest_indices": [],
            "audio_paths": [],
            "speakers_set": set(),
        }
    )

    survey_filtered = 0
    wake_word_filtered = 0
    empty_filtered = 0

    for idx, (audio_path, origin_text, raw_clean_text) in enumerate(
        zip(tsv_lines, origin_lines, clean_lines)
    ):
        # Filtering Rule 1: Filter out spontaneous survey speech
        if "[" in origin_text or "]" in origin_text:
            survey_filtered += 1
            continue

        canonical_text = " ".join(raw_clean_text.lower().split())
        if not canonical_text:
            empty_filtered += 1
            continue

        if canonical_text in wake_words:
            wake_word_filtered += 1
            continue

        # Extract speaker ID from audio path
        speaker_id = extract_speaker_id(audio_path)

        entry = groups[canonical_text]
        entry["frequency"] += 1
        entry["manifest_indices"].append(idx)
        entry["audio_paths"].append(audio_path)
        entry["speakers_set"].add(speaker_id)

    logger.info(f"Filtering Summary:")
    logger.info(f"  - Total records processed:       {total_audio_entries:,}")
    logger.info(f"  - Survey speech filtered ([...]): {survey_filtered:,}")
    logger.info(f"  - Standalone wake words filtered: {wake_word_filtered:,}")
    if empty_filtered:
        logger.info(f"  - Empty strings filtered:         {empty_filtered:,}")
    logger.info(f"  - Total unique candidate phrases: {len(groups):,}")

    # Filtering Rule 4: Frequency Threshold (count >= min_count)
    candidates = [
        (text, data)
        for text, data in groups.items()
        if data["frequency"] >= min_count
    ]

    # Sort descending by frequency, then number of unique speakers, then canonical text
    candidates.sort(
        key=lambda item: (-item[1]["frequency"], -len(item[1]["speakers_set"]), item[0])
    )

    logger.info(
        f"  - Retained templates (count >= {min_count}): {len(candidates):,}"
    )

    # Build final schema dictionary
    results: Dict[str, Dict[str, Any]] = {}
    for rank, (canonical_text, data) in enumerate(candidates, start=1):
        cmd_id = f"cmd_{rank:04d}"
        sorted_speakers = sorted(list(data["speakers_set"]))
        results[cmd_id] = {
            "canonical_text": canonical_text,
            "frequency": data["frequency"],
            "unique_speakers": len(sorted_speakers),
            "manifest_indices": data["manifest_indices"],
            "speaker_ids": sorted_speakers,
            "audio_paths": data["audio_paths"],
        }

    return results


def main() -> None:
    # Determine default paths relative to repository root
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent if script_dir.name == "benchmark_curation" else script_dir

    default_manifest_dir = repo_root / "manifest"
    default_output_path = repo_root / "benchmark_curation" / "unique_candidate_commands.json"

    parser = argparse.ArgumentParser(
        description="Extract high-frequency candidate command templates from the SAP dev manifest."
    )
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=default_manifest_dir,
        help=f"Directory containing dev.tsv, dev.origin.wrd, dev.wrd.without.parentheses (default: {default_manifest_dir})",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=default_output_path,
        help=f"Path to output JSON file (default: {default_output_path})",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=5,
        help="Minimum frequency threshold across the dataset (default: 5)",
    )
    args = parser.parse_args()

    results = extract_candidate_commands(
        manifest_dir=args.manifest_dir,
        min_count=args.min_count,
    )

    # Ensure target output directory exists
    args.output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(args.output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Successfully saved {len(results)} command templates to: {args.output_path}")

    # Display top 5 sample entries for sanity checking
    print("\n--- Top 5 Extracted Commands Sample ---")
    for cmd_id in list(results.keys())[:5]:
        item = results[cmd_id]
        print(
            f"[{cmd_id}] \"{item['canonical_text']}\" | "
            f"Frequency: {item['frequency']} | "
            f"Unique Speakers: {item['unique_speakers']}"
        )


if __name__ == "__main__":
    main()
