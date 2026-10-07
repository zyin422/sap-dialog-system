import sys, json, re, argparse, gc
from typing import Any, Dict, List, Optional, Set, Tuple
import torch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from s2t_pipeline import BaseLLM, LLMInstruct

BENCHMARK_SYSTEM_PROMPT = """You are an expert semantic parser mapping voice assistant commands into canonical hierarchical tool calls for a spoken dialog benchmark.

### 1. Objective:
Analyze the user's spoken command and map it to its exact canonical (Domain, Intent, Slots) representation.

### 2. Closed Schema Ontology:
You must categorize the command strictly into one of the following 10 domains and 30 canonical tools:

1. health
- health_medication_reminder: Schedule prescription medication or supplement dosage reminders. (Allowed slots: medication, time)
- health_refill_query: Inquire about remaining prescription refills or pharmacy status. (Allowed slots: medication)
- health_info_query: Inquire about clinical medication side effects or dosage. (Allowed slots: medication, info_type ["side_effects", "dosage"])

2. smart_home
- iot_device_power: Toggle binary power state of appliances, plugs, switches, TVs, fans, heaters, or simple lights. Also handles door lock states ('lock' -> state: 'on', 'unlock' -> state: 'off'). (Allowed slots: device_type, state ["on", "off"])
- iot_device_adjust: Adjust continuous scalar attributes of IoT devices like thermostats, dimmers, fans, or ovens. (Allowed slots: device_type, setting, direction ["lower", "raise"], value)
- iot_sensor_query: Check ambient environmental room sensors. (Allowed slots: room, sensor_type ["temperature"])

3. communication
- call_make: Place an outgoing voice or video call. (Allowed slots: recipient_name, phone_number)
- call_manage: Telephony in-call management. (Allowed slots: action ["answer", "hang_up", "redial"])
- messages_manage: Send or read SMS / instant text messages. (Allowed slots: action ["send", "read"], recipient, message_body)
- email_manage: Send, read, or search emails. (Allowed slots: action ["send", "read", "search"], recipient, date, message_body)
- contacts_manage: Address book contact management. (Allowed slots: action ["add", "search", "delete"], contact_name, phone_number, email_address)

4. media
- media_play: Stream music, albums, podcasts, audiobooks, or radio. (Allowed slots: media_type ["music", "podcast", "audiobook", "radio"], title, artist, house_place)
- media_control: Control media playback session. (Allowed slots: action ["skip", "pause", "resume", "replay", "like", "dislike"], target_type ["music", "podcast"], duration)
- media_volume: Adjust local device playback volume. (Allowed slots: action ["up", "down", "mute", "set_level"], change_amount)

5. calendar_alarm
- calendar_manage: Schedule, query, or cancel calendar meetings and events. (Allowed slots: action ["set", "query", "cancel"], event_name, date, time, person)
- alarm_manage: Set, inspect, cancel, or snooze alarms and timers. (Allowed slots: action ["set", "query", "cancel", "snooze"], time, date, general_frequency)
- reminder_manage: Set, query, or delete non-clinical daily task reminders. (Allowed slots: action ["set", "query", "delete"], title, date, time)

6. maps_places
- maps_route: Request driving directions, navigation, distance, or route traffic. (Allowed slots: destination, query_type ["navigation", "traffic", "distance"])
- places_search: Search for nearby local venues, stores, restaurants, or business hours. (Allowed slots: business_type, business_name, sort_by ["nearest"])
- reservations_manage: Book or inspect restaurant / venue table reservations. (Allowed slots: business_name, party_size, date, time)

7. transport
- rideshare_book: Order or hail a taxi, cab, or rideshare vehicle. (Allowed slots: destination)
- transit_lookup: Check schedules or book tickets for public transit, trains, buses, and flights. (Allowed slots: transit_type ["train", "bus", "flight"], route_or_station, destination, date, time)

8. accessibility
- accessibility_ui_scale: Adjust on-screen text size or screen brightness accommodations. (Allowed slots: ui_element ["text", "screen"], direction ["larger", "brighten", "darken"])
- accessibility_dictation_toggle: Toggle continuous voice dictation listening state. (Allowed slots: state ["start", "stop"])

9. notes_memory
- memory_note_manage: Save, recall, or clear cognitive memory aids like passcodes or parking spaces. (Allowed slots: action ["save", "query", "delete"], key ["pin", "parking_space", "note"], value)
- lists_manage: Create, read, or modify shopping and to-do lists. (Allowed slots: list_name, item, action ["add", "read", "remove"])

10. general_qa
- weather_query: Check meteorological weather conditions and forecasts. (Allowed slots: place_name, date, weather_aspect ["rain", "snow", "temperature"])
- order_manage: Manage e-commerce parcel tracking, cancellations, returns, and reports. (Allowed slots: action ["track_status", "cancel_order", "return_item", "report_issue"], order_id)
- device_find: Trigger an audible ping to locate a misplaced hardware device. (Allowed slots: device ["phone"])
- qa_search: Open factual web queries for world knowledge, recipes, news briefings, stock prices, and general definitions. (Allowed slots: query)

### 3. Extraction & Normalization Directives:
1. Select strictly from the canonical intent catalog above (<domain>_<action>).
2. Nominal Core Span Rule: Extract bare nominal entities. Strictly strip leading governing prepositions ('at', 'with', 'on', 'to', 'for', 'in') and determiners ('a', 'an', 'the').
3. Extract slot values verbatim as exact lowercase substrings from the command. Do not normalize spoken numbers to digits or alter spelling.
4. Never extract or hallucinate an entity that was not spoken in the command.
5. If the command requires no parameters or slots, 'slots' MUST be an empty object {}.
6. Wake words ('hey siri', 'alexa', 'ok google', 'cortana', 'hey facebook') are outside tokens (O). Never extract wake words into slot parameters.

### 4. Output Contract:
Respond ONLY with a valid, raw JSON object matching this exact schema:
{
  "domain": "<domain_name>",
  "intent": "<intent_name>",
  "slots": {
    "<slot_key>": "<verbatim_slot_value>"
  }
}
Do not include Markdown backticks, explanation, or any surrounding text."""


class CrossModelEvaluatorLLM(LLMInstruct):
    def __init__(
        self,
        model_id: str,
        system_prompt: str | None = None,
        device: str | None = None,
        temperature: float = 0.0
    ):
        super().__init__(model_id=model_id, device=device)
        self.system_prompt = system_prompt or BENCHMARK_SYSTEM_PROMPT
        self.temperature = temperature
    
    @torch.no_grad()
    def inference(self, transcript: str):
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Spoken Command: \"{transcript}\""}
        ]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
        prompt_length = inputs["input_ids"].shape[1]
        gen_wargs = {"max_new_tokens": 128, "do_sample": self.temperature > 0.0}
        if self.temperature > 0.0:
            gen_wargs["temperature"] = self.temperature
        outputs = self.model.generate(**inputs, **gen_wargs)[0][prompt_length:]
        
        decoded_outputs = self.tokenizer.decode(outputs, skip_special_tokens=True).strip()

        jstart = decoded_outputs.find("{")
        jend = decoded_outputs.rfind("}")

        if jstart == -1 or jend == -1:
            return {"domain": "parse_error", "intent": "parse_error", "slots": {}, "raw_output": decoded_outputs}

        clean_text = decoded_outputs[jstart:jend + 1]
        try:
            data = json.loads(clean_text)
            data.setdefault("domain", "unknown")
            data.setdefault("intent", "unknown")
            data.setdefault("slots", {})
            
            return data
        except Exception:
            return {"domain": "parse_error", "intent": "parse_error", "slots": {}, "raw_output": decoded_outputs}

def compute_accuracy(predictions: list, ground_truths: list) -> dict:
    """
    Computes Domain Accuracy, Intent Accuracy, and Exact Match (both match).
    """
    if not predictions:
        return {"domain_acc": 0.0, "intent_acc": 0.0, "exact_match": 0.0}

    domain_correct = 0
    intent_correct = 0
    exact_correct = 0

    for p, g in zip(predictions, ground_truths):
        pred_dom = str(p.get("domain", "")).strip().lower()
        gold_dom = str(g.get("domain", "")).strip().lower()

        pred_int = str(p.get("intent", "")).strip().lower()
        gold_int = str(g.get("intent", "")).strip().lower()

        dom_match = pred_dom == gold_dom
        int_match = pred_int == gold_int

        if dom_match:
            domain_correct += 1
        if int_match:
            intent_correct += 1
        if dom_match and int_match:
            exact_correct += 1

    total = len(predictions)
    return {
        "domain_acc": round(domain_correct / total, 4),
        "intent_acc": round(intent_correct / total, 4),
        "exact_match": round(exact_correct / total, 4),
    }


def compute_slot_metrics(predictions: list, ground_truths: list) -> dict:
    """
    Computes Micro-Averaged Precision, Recall, and F1 across all (slot_key, slot_value) pairs.
    Handles both 'target_slots' (from schema_registry) and 'slots' (from model outputs).
    """
    tp = 0
    fp = 0
    fn = 0

    for p, g in zip(predictions, ground_truths):
        pred_slots = p.get("slots", {}) if isinstance(p.get("slots"), dict) else {}
        gold_slots = g.get("target_slots", g.get("slots", {}))
        if not isinstance(gold_slots, dict):
            gold_slots = {}

        # Normalize (key, value) pairs into sets of tuples
        pred_set = {
            (str(k).strip().lower(), str(v).strip().lower())
            for k, v in pred_slots.items()
            if str(v).strip()
        }
        gold_set = {
            (str(k).strip().lower(), str(v).strip().lower())
            for k, v in gold_slots.items()
            if str(v).strip()
        }

        tp += len(pred_set & gold_set)
        fp += len(pred_set - gold_set)
        fn += len(gold_set - pred_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "slot_precision": round(precision, 4),
        "slot_recall": round(recall, 4),
        "slot_f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }

def print_discrepancy_table(itemized_records: list) -> None:
    """
    Prints a formatted CLI table showing any prompts where predictions differ from gold targets.
    """
    discrepancies = []
    for r in itemized_records:
        gold = r["gold"]
        pred = r["prediction"]

        dom_diff = str(pred.get("domain", "")).strip().lower() != str(gold.get("domain", "")).strip().lower()
        int_diff = str(pred.get("intent", "")).strip().lower() != str(gold.get("intent", "")).strip().lower()

        pred_slots = {
            (str(k).strip().lower(), str(v).strip().lower())
            for k, v in pred.get("slots", {}).items()
            if str(v).strip()
        }
        gold_slots = {
            (str(k).strip().lower(), str(v).strip().lower())
            for k, v in gold.get("slots", {}).items()
            if str(v).strip()
        }
        slot_diff = pred_slots != gold_slots

        if dom_diff or int_diff or slot_diff:
            diff_flags = []
            if dom_diff:
                diff_flags.append("DOMAIN")
            if int_diff:
                diff_flags.append("INTENT")
            if slot_diff:
                diff_flags.append("SLOTS")
            discrepancies.append((r, diff_flags))

    print("\n" + "=" * 105)
    print(f"                     PHASE 1 DISCREPANCY REPORT: {len(discrepancies)} / {len(itemized_records)} MISMATCHES")
    print("=" * 105)

    if not discrepancies:
        print("  🎉 PERFECT CALIBRATION: All 30 prompts matched domain, intent, and slots 100%!")
        print("=" * 105 + "\n")
        return

    for rec, flags in discrepancies:
        cmd_id = rec.get("command_id", "N/A")
        text = rec.get("canonical_text", "")
        gold = rec["gold"]
        pred = rec["prediction"]

        flag_str = ", ".join(flags)
        print(f"[{cmd_id}] \"{text}\"  -->  MISMATCH IN: [{flag_str}]")
        print(f"  • GOLD:   Domain: {gold.get('domain')} | Intent: {gold.get('intent')} | Slots: {gold.get('slots')}")
        print(f"  • PRED:   Domain: {pred.get('domain')} | Intent: {pred.get('intent')} | Slots: {pred.get('slots')}")
        print("-" * 105)
    print("=" * 105 + "\n")


def run_calibration(
    evaluator: CrossModelEvaluatorLLM,
    test_prompts: list,
    output_path: Path,
) -> dict:
    """
    Phase 1: Calibrate the LLM against the 30 human-verified pilot prompts.
    """
    print(f"\n[Phase 1] Starting calibration on {len(test_prompts)} pilot prompts using {evaluator.model_id}...")
    predictions = []
    itemized_records = []

    for i, item in enumerate(test_prompts, start=1):
        command_text = item["canonical_text"]
        print(f"  [{i:02d}/{len(test_prompts):02d}] Evaluating: \"{command_text}\"")

        pred = evaluator.inference(command_text)
        predictions.append(pred)
        print(f"       -> Pred: {pred.get('domain')}/{pred.get('intent')} | {pred.get('slots')}")

        record = {
            "command_id": item.get("command_id", f"cmd_{i:02d}"),
            "canonical_text": command_text,
            "gold": {
                "domain": item.get("domain", ""),
                "intent": item.get("intent", ""),
                "slots": item.get("target_slots", {}),
            },
            "prediction": pred,
        }
        itemized_records.append(record)

    # Calculate metrics
    acc_stats = compute_accuracy(predictions, test_prompts)
    slot_stats = compute_slot_metrics(predictions, test_prompts)

    print("\n" + "=" * 55)
    print("           CALIBRATION METRICS SUMMARY")
    print("=" * 55)
    print(f"  • Domain Accuracy:      {acc_stats['domain_acc'] * 100:.1f}%")
    print(f"  • Intent Accuracy:      {acc_stats['intent_acc'] * 100:.1f}%")
    print(f"  • Exact Match (Dom+Int):{acc_stats['exact_match'] * 100:.1f}%")
    print(f"  • Slot Precision:       {slot_stats['slot_precision'] * 100:.1f}%")
    print(f"  • Slot Recall:          {slot_stats['slot_recall'] * 100:.1f}%")
    print(f"  • Slot F1 Score:        {slot_stats['slot_f1'] * 100:.1f}%")
    print(f"  • TP / FP / FN:         {slot_stats['tp']} / {slot_stats['fp']} / {slot_stats['fn']}")
    print("=" * 55)

    # Discrepancy report
    print_discrepancy_table(itemized_records)

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    full_output = {
        "model_id": evaluator.model_id,
        "total_prompts": len(test_prompts),
        "metrics": {**acc_stats, **slot_stats},
        "itemized_results": itemized_records,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print(f"Calibration results successfully saved to: {output_path}")
    return full_output


def run_batch_autolabeling(
    evaluator1: CrossModelEvaluatorLLM,
    evaluator2: Optional[CrossModelEvaluatorLLM],
    candidates: dict,
    output_path: Path,
) -> dict:
    """
    Phase 2: Batch auto-labeling across candidate commands in unique_candidate_commands.json.
    Computes inter-model agreement (consensus) and flags discrepancies.
    """
    print(f"\n[Phase 2] Starting batch auto-labeling on {len(candidates)} candidate commands...")
    if isinstance(candidates, list):
        candidates = {item.get("command_id", f"cmd_{i:04d}"): item for i, item in enumerate(candidates, start=1)}

    labeled_results = {}
    consensus_count = 0
    disagreement_count = 0

    for idx, (cmd_id, cmd_meta) in enumerate(candidates.items(), start=1):
        text = cmd_meta["canonical_text"]
        if idx % 25 == 1 or idx == len(candidates):
            print(f"  [{idx:03d}/{len(candidates):03d}] Processing: \"{text}\"")

        pred1 = evaluator1.inference(text)
        pred2 = evaluator2.inference(text) if evaluator2 else None

        if pred2:
            # Check consensus: do both models agree on domain, intent, and slot keys?
            dom_agree = str(pred1.get("domain", "")).strip().lower() == str(pred2.get("domain", "")).strip().lower()
            int_agree = str(pred1.get("intent", "")).strip().lower() == str(pred2.get("intent", "")).strip().lower()
            slots1 = set(pred1.get("slots", {}).keys())
            slots2 = set(pred2.get("slots", {}).keys())
            slots_agree = slots1 == slots2

            is_consensus = dom_agree and int_agree and slots_agree
            if is_consensus:
                consensus_count += 1
                status = "consensus_accepted"
            else:
                disagreement_count += 1
                status = "flagged_disagreement"

            labeled_results[cmd_id] = {
                "canonical_text": text,
                "frequency": cmd_meta.get("frequency", 0),
                "unique_speakers": cmd_meta.get("unique_speakers", 0),
                "manifest_indices": cmd_meta.get("manifest_indices", []),
                "audio_paths": cmd_meta.get("audio_paths", []),
                "status": status,
                "model_1": {
                    "model_id": evaluator1.model_id,
                    "prediction": pred1,
                },
                "model_2": {
                    "model_id": evaluator2.model_id,
                    "prediction": pred2,
                },
                "canonical_annotation": pred1 if is_consensus else None,
            }
        else:
            # Single-model auto-labeling mode
            labeled_results[cmd_id] = {
                "canonical_text": text,
                "frequency": cmd_meta.get("frequency", 0),
                "unique_speakers": cmd_meta.get("unique_speakers", 0),
                "manifest_indices": cmd_meta.get("manifest_indices", []),
                "audio_paths": cmd_meta.get("audio_paths", []),
                "status": "single_model_labeled",
                "annotation": pred1,
            }

    print("\n" + "=" * 55)
    print("           PHASE 2 AUTO-LABELING SUMMARY")
    print("=" * 55)
    print(f"  • Total Candidates:      {len(candidates)}")
    if evaluator2:
        print(f"  • Consensus Accepted:    {consensus_count} ({consensus_count / len(candidates) * 100:.1f}%)")
        print(f"  • Flagged Disagreements: {disagreement_count} ({disagreement_count / len(candidates) * 100:.1f}%)")
    print("=" * 55)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labeled_results, f, indent=2)

    print(f"Gold schemas saved to: {output_path}")
    return labeled_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-Model Evaluation & Schema Calibration on Spoken Dialog Candidates."
    )
    parser.add_argument(
        "--phase",
        choices=["calibrate", "autolabel", "both"],
        default="calibrate",
        help="Execution phase: 'calibrate' (Phase 1 pilot 30), 'autolabel' (Phase 2 candidates), or 'both'",
    )
    parser.add_argument(
        "--model_id",
        "--model1",
        dest="model_id",
        default="Qwen/Qwen2.5-7B-Instruct",
        help="Primary model ID (default: Qwen/Qwen2.5-7B-Instruct)",
    )
    parser.add_argument(
        "--model2",
        default=None,
        help="Optional secondary model ID for cross-model consensus validation (e.g. Qwen/Qwen2.5-14B-Instruct)",
    )
    parser.add_argument(
        "--schema_path",
        type=Path,
        default=REPO_ROOT / "benchmark_curation" / "schema_registry.json",
        help="Path to schema registry JSON",
    )
    parser.add_argument(
        "--candidates_path",
        type=Path,
        default=REPO_ROOT / "benchmark_curation" / "unique_candidate_commands.json",
        help="Path to extracted candidate commands JSON",
    )
    parser.add_argument(
        "--output_path",
        type=Path,
        default=REPO_ROOT / "benchmark_curation" / "calibration_results_qwen7b.json",
        help="Path to save Phase 1 calibration results",
    )
    parser.add_argument(
        "--gold_output_path",
        type=Path,
        default=REPO_ROOT / "benchmark_curation" / "sap_gold_schemas.json",
        help="Path to save Phase 2 auto-labeled gold schemas",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Inference sampling temperature (default: 0.0 for greedy decoding)",
    )
    args = parser.parse_args()

    # Phase 1: Calibration
    if args.phase in ["calibrate", "both"]:
        if not args.schema_path.is_file():
            raise FileNotFoundError(f"Schema registry not found at: {args.schema_path}")

        with open(args.schema_path, "r", encoding="utf-8") as f:
            registry_data = json.load(f)

        test_prompts = registry_data.get("benchmark_pilot_30", [])
        if not test_prompts:
            raise ValueError(f"No 'benchmark_pilot_30' entries found in {args.schema_path}")

        print(f"Loading Evaluator Model 1: {args.model_id}...")
        evaluator1 = CrossModelEvaluatorLLM(
            model_id=args.model_id,
            temperature=args.temperature,
        )

        run_calibration(
            evaluator=evaluator1,
            test_prompts=test_prompts,
            output_path=args.output_path,
        )

    # Phase 2: Batch Auto-Labeling
    if args.phase in ["autolabel", "both"]:
        if not args.candidates_path.is_file():
            raise FileNotFoundError(f"Candidates file not found at: {args.candidates_path}")

        with open(args.candidates_path, "r", encoding="utf-8") as f:
            candidates_data = json.load(f)

        if "evaluator1" not in locals():
            print(f"Loading Evaluator Model 1: {args.model_id}...")
            evaluator1 = CrossModelEvaluatorLLM(
                model_id=args.model_id,
                temperature=args.temperature,
            )

        evaluator2 = None
        if args.model2:
            print(f"Loading Evaluator Model 2: {args.model2}...")
            evaluator2 = CrossModelEvaluatorLLM(
                model_id=args.model2,
                temperature=args.temperature,
            )

        run_batch_autolabeling(
            evaluator1=evaluator1,
            evaluator2=evaluator2,
            candidates=candidates_data,
            output_path=args.gold_output_path,
        )


if __name__ == "__main__":
    main()