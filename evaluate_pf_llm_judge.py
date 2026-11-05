#!/usr/bin/env python3
"""
evaluate_pf_llm_judge.py
========================
Publication-Grade Semantic LLM-as-a-Judge for Parameter Filling (PF) in the
Speech Accessibility Project (SAP) Spoken Dialogue System Benchmark.

Evaluates semantic recall, precision, and F1 across all 3 conditions:
  Condition 1: Oracle Spoken Reference
  Condition 2: Base Parakeet ASR
  Condition 3: Fine-Tuned Parakeet ASR

Mitigates lexical boundary artifacts (compound nouns, prepositions, carrier phrases)
and crowd annotation sparsity while strictly penalizing unuttered hallucinations.
"""

import os
import re
import json
import argparse
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

JUDGE_SYSTEM_PROMPT = """You are an expert scientific evaluator for Spoken Language Understanding (SLU) and dialogue tool-calling parameters.
Evaluate the extracted parameter slot against the user's spoken utterance.

You will be given:
1. Spoken Utterance: Exact words spoken by the user.
2. Tool Name: Target tool / intent name.
3. Candidate Parameter:
   - For RECALL evaluation: You are provided the Gold Slot (key, gold_val) and Predicted Value (pred_val).
     Judge whether pred_val successfully captures the core semantic referent of gold_val in the context of the utterance.
     * RECALL PASS: pred_val preserves the entity referent even with valid descriptive modifiers (e.g. 'porch light' for 'light', 'with lunch' for 'lunch', 'Define conundrum' for 'conundrum').
     * RECALL FAIL: pred_val is missing, empty, refers to an entirely different entity, or corrupts factual meaning.
   - For PRECISION evaluation: You are provided the Predicted Slot (key, pred_val).
     Judge whether pred_val is explicitly grounded in words spoken in the utterance.
     * PRECISION PASS: pred_val is supported by tokens/phrases uttered by the user and serves as a valid argument.
     * PRECISION FAIL: pred_val is an unuttered implicit default or hallucination (e.g., extracting service='Apple Podcasts' or house_place='home' or media_type='music' when those words were never spoken).

Respond ONLY with valid JSON in this exact structure:
{
  "reasoning": "<1-2 sentence concise technical justification>",
  "verdict": true
}
"""

def normalize_text(text: Any) -> str:
    if text is None or pd.isna(text):
        return ""
    s = str(text).strip().lower()
    s = re.sub(r'[\'\".,?!;:()\[\]{}]', '', s)
    return " ".join(s.split())

def parse_json_safely(val: Any) -> Dict[str, Any]:
    if val is None or pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    s = str(val).strip()
    if not s or s.lower() == "nan" or s == "{}":
        return {}
    try:
        return json.loads(s)
    except Exception:
        # Fallback regex for loose json-like dicts
        try:
            fixed = s.replace("'", '"')
            return json.loads(fixed)
        except Exception:
            return {}

class SemanticLLMJudge:
    def __init__(self, model_id_or_path: str, device: str = "auto", torch_dtype=torch.bfloat16):
        print(f"[Judge Init] Loading model and tokenizer from: {model_id_or_path}", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_id_or_path, trust_remote_code=True)
        self.cache: Dict[Tuple, Tuple[bool, str]] = {}
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id_or_path,
                dtype=torch_dtype,
                device_map=device,
                trust_remote_code=True
            )
        except Exception as e:
            print(f"[Judge Init] AutoModelForCausalLM load failed ({e}), trying AutoModelForImageTextToText...", flush=True)
            try:
                from transformers import AutoModelForImageTextToText
                self.model = AutoModelForImageTextToText.from_pretrained(
                    model_id_or_path,
                    dtype=torch_dtype,
                    device_map=device,
                    trust_remote_code=True
                )
            except Exception as e2:
                print(f"[Judge Init] AutoModelForImageTextToText load failed ({e2}), falling back to AutoModel...", flush=True)
                from transformers import AutoModel
                self.model = AutoModel.from_pretrained(
                    model_id_or_path,
                    dtype=torch_dtype,
                    device_map=device,
                    trust_remote_code=True
                )
        self.model.eval()
        print(f"[Judge Init] Model loaded on devices: {self.model.hf_device_map if hasattr(self.model, 'hf_device_map') else self.model.device}", flush=True)

    def preload_cache(self, audit_csv_path: str):
        if not audit_csv_path or not os.path.exists(audit_csv_path):
            return
        try:
            df = pd.read_csv(audit_csv_path)
            loaded = 0
            for _, row in df.iterrows():
                eval_type = str(row.get("eval_type", "")).strip().lower()
                eval_key = "recall" if "recall" in eval_type else "precision"
                utt = str(row.get("utterance", "")).strip().lower()
                tool = str(row.get("tool", "")).strip().lower()
                slot = str(row.get("slot", "")).strip().lower()
                gold = normalize_text(str(row.get("gold", ""))) if pd.notna(row.get("gold")) else ""
                pred = normalize_text(str(row.get("pred", ""))) if pd.notna(row.get("pred")) else ""
                verdict = bool(row.get("verdict", False))
                reasoning = str(row.get("reasoning", ""))
                cache_key = (eval_key, utt, tool, slot, gold, pred)
                self.cache[cache_key] = (verdict, reasoning)
                loaded += 1
            print(f"[Judge Init] Preloaded {loaded} cached decisions ({len(self.cache)} unique keys) from {audit_csv_path}", flush=True)
        except Exception as e:
            print(f"[Judge Init] Warning: failed to preload cache from {audit_csv_path}: {e}", flush=True)

    def evaluate_item(self, eval_type: str, utterance: str, tool: str, slot_key: str,
                      gold_val: Optional[str] = None, pred_val: Optional[str] = None) -> Tuple[bool, str]:
        # Cache lookup
        norm_gold = normalize_text(gold_val) if gold_val else ""
        norm_pred = normalize_text(pred_val) if pred_val else ""
        cache_key = (eval_type, utterance.strip().lower(), tool.strip().lower(), slot_key.strip().lower(), norm_gold, norm_pred)
        if cache_key in self.cache:
            return self.cache[cache_key]

        if eval_type == "recall":
            slot_info = (
                f"Gold Value: \"{gold_val}\"\n"
                f"Predicted Value: \"{pred_val}\"\n"
                f"Does predicted value capture the referent of the gold value in the utterance?"
            )
        else:
            slot_info = (
                f"Predicted Value: \"{pred_val}\"\n"
                f"Is predicted value explicitly grounded in the spoken utterance?"
            )

        content = (
            f"You are an expert scientific evaluator for Spoken Language Understanding (SLU).\n"
            f"Evaluate whether the predicted parameter slot value matches the user's spoken utterance.\n\n"
            f"Output MUST be a valid JSON object starting with {{ and ending with }}:\n"
            f"{{\n"
            f"  \"verdict\": true,\n"
            f"  \"reasoning\": \"<concise explanation>\"\n"
            f"}}\n\n"
            f"EVALUATION TYPE: {eval_type.upper()}\n"
            f"Utterance: \"{utterance}\"\n"
            f"Tool: {tool}\n"
            f"Slot: {slot_key}\n"
            f"{slot_info}\n"
        )

        messages = [
            {"role": "user", "content": content}
        ]

        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=80,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id
            )
        raw_output = self.tokenizer.decode(output_ids[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

        # Parse JSON output and fallback regex
        verdict = False
        reasoning = raw_output
        try:
            m = re.search(r'\{.*\}', raw_output, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                verdict = bool(data.get("verdict", False))
                reasoning = data.get("reasoning", raw_output)
            else:
                m_verdict = re.search(r'"verdict":\s*(true|false)', raw_output, re.IGNORECASE)
                if m_verdict:
                    verdict = (m_verdict.group(1).lower() == "true")
                elif "true" in raw_output.lower() and "false" not in raw_output.lower():
                    verdict = True
        except Exception as e:
            m_verdict = re.search(r'"verdict":\s*(true|false)', raw_output, re.IGNORECASE)
            if m_verdict:
                verdict = (m_verdict.group(1).lower() == "true")
            elif "true" in raw_output.lower() and "false" not in raw_output.lower():
                verdict = True

        self.cache[cache_key] = (verdict, reasoning)
        return verdict, reasoning

def evaluate_condition_pf(df: pd.DataFrame, judge: SemanticLLMJudge,
                          intent_col: str, slots_col: str, prompt_col: str = "prompt") -> Dict[str, Any]:
    """
    Evaluates one experimental condition across all rows in df.
    """
    gold_total_slots = 0
    pred_total_slots = 0
    
    exact_rec_hits = 0
    semantic_rec_hits = 0
    
    exact_prec_hits = 0
    semantic_prec_hits = 0

    judge_recall_calls = 0
    judge_precision_calls = 0

    audit_log = []

    for idx, row in df.iterrows():
        utt = str(row[prompt_col]).strip()
        g_intent = str(row["intent"]).strip().lower()
        p_intent = str(row[intent_col]).strip().lower() if pd.notna(row[intent_col]) else ""

        g_slots = parse_json_safely(row["slots"])
        p_slots = parse_json_safely(row[slots_col])

        gold_total_slots += len(g_slots)
        pred_total_slots += len(p_slots)

        intent_match = (g_intent == p_intent)

        # 1. EVALUATE RECALL (Gold slots coverage)
        recall_decisions = {}
        for k, g_val in g_slots.items():
            g_val_str = str(g_val).strip()
            if not intent_match:
                # Upstream tool mismatch: slot unfulfilled
                continue

            if k in p_slots:
                p_val_str = str(p_slots[k]).strip()
                # Fast path: Exact or normalized match
                if normalize_text(g_val_str) == normalize_text(p_val_str):
                    exact_rec_hits += 1
                    semantic_rec_hits += 1
                    recall_decisions[k] = (True, "exact_match")
                else:
                    # Semantic Boundary / Discrepancy -> Invoke LLM Judge
                    judge_recall_calls += 1
                    verdict, reasoning = judge.evaluate_item(
                        eval_type="recall",
                        utterance=utt,
                        tool=g_intent,
                        slot_key=k,
                        gold_val=g_val_str,
                        pred_val=p_val_str
                    )
                    if verdict:
                        semantic_rec_hits += 1
                    recall_decisions[k] = (verdict, reasoning)
                    audit_log.append({
                        "row_id": row.get("gold_id", idx),
                        "eval_type": "recall",
                        "utterance": utt,
                        "tool": g_intent,
                        "slot": k,
                        "gold": g_val_str,
                        "pred": p_val_str,
                        "verdict": verdict,
                        "reasoning": reasoning
                    })
            else:
                # Omission
                pass

        # 2. EVALUATE PRECISION (Predicted slots validity)
        for k, p_val in p_slots.items():
            p_val_str = str(p_val).strip()
            if not intent_match:
                # Spurious slots on incorrect tool
                continue

            if k in g_slots:
                g_val_str = str(g_slots[k]).strip()
                # Fast path 1: Exact match with gold
                if normalize_text(p_val_str) == normalize_text(g_val_str):
                    exact_prec_hits += 1
                    semantic_prec_hits += 1
                elif k in recall_decisions and recall_decisions[k][0]:
                    # Short-circuit: already judged as preserving gold referent in this utterance
                    semantic_prec_hits += 1
                    audit_log.append({
                        "row_id": row.get("gold_id", idx),
                        "eval_type": "precision_inherited_recall",
                        "utterance": utt,
                        "tool": g_intent,
                        "slot": k,
                        "gold": g_val_str,
                        "pred": p_val_str,
                        "verdict": True,
                        "reasoning": f"Inherited from semantic recall pass: {recall_decisions[k][1]}"
                    })
                else:
                    # Evaluated by semantic recall previously: does it preserve referent?
                    judge_precision_calls += 1
                    verdict, reasoning = judge.evaluate_item(
                        eval_type="precision",
                        utterance=utt,
                        tool=g_intent,
                        slot_key=k,
                        pred_val=p_val_str
                    )
                    if verdict:
                        semantic_prec_hits += 1
                    audit_log.append({
                        "row_id": row.get("gold_id", idx),
                        "eval_type": "precision_modified",
                        "utterance": utt,
                        "tool": g_intent,
                        "slot": k,
                        "gold": g_val_str,
                        "pred": p_val_str,
                        "verdict": verdict,
                        "reasoning": reasoning
                    })
            else:
                # Extra slot not in gold crowd annotations
                judge_precision_calls += 1
                verdict, reasoning = judge.evaluate_item(
                    eval_type="precision",
                    utterance=utt,
                    tool=g_intent,
                    slot_key=k,
                    pred_val=p_val_str
                )
                if verdict:
                    semantic_prec_hits += 1
                audit_log.append({
                    "row_id": row.get("gold_id", idx),
                    "eval_type": "precision_extra",
                    "utterance": utt,
                    "tool": g_intent,
                    "slot": k,
                    "gold": None,
                    "pred": p_val_str,
                    "verdict": verdict,
                    "reasoning": reasoning
                })

        if (idx + 1) % 50 == 0 or (idx + 1) == len(df):
            print(f"[{intent_col.split('_')[0].upper()}] Row {idx + 1}/{len(df)} | ExactRec: {exact_rec_hits} | SemRec: {semantic_rec_hits} | ExactPrec: {exact_prec_hits} | SemPrec: {semantic_prec_hits} | Calls(Rec/Prec): {judge_recall_calls}/{judge_precision_calls}", flush=True)

    # Compute Metrics
    exact_rec = (exact_rec_hits / gold_total_slots) * 100.0 if gold_total_slots > 0 else 0.0
    exact_prec = (exact_prec_hits / pred_total_slots) * 100.0 if pred_total_slots > 0 else 0.0
    exact_f1 = (2 * exact_rec * exact_prec) / (exact_rec + exact_prec) if (exact_rec + exact_prec) > 0 else 0.0

    sem_rec = (semantic_rec_hits / gold_total_slots) * 100.0 if gold_total_slots > 0 else 0.0
    sem_prec = (semantic_prec_hits / pred_total_slots) * 100.0 if pred_total_slots > 0 else 0.0
    sem_f1 = (2 * sem_rec * sem_prec) / (sem_rec + sem_prec) if (sem_rec + sem_prec) > 0 else 0.0

    return {
        "gold_total_slots": gold_total_slots,
        "pred_total_slots": pred_total_slots,
        "exact_rec_hits": exact_rec_hits,
        "exact_prec_hits": exact_prec_hits,
        "exact_recall": exact_rec,
        "exact_precision": exact_prec,
        "exact_f1": exact_f1,
        "semantic_rec_hits": semantic_rec_hits,
        "semantic_prec_hits": semantic_prec_hits,
        "semantic_recall": sem_rec,
        "semantic_precision": sem_prec,
        "semantic_f1": sem_f1,
        "judge_recall_calls": judge_recall_calls,
        "judge_precision_calls": judge_precision_calls,
        "audit_log": audit_log
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate Semantic Parameter Filling via LLM-as-a-Judge")
    parser.add_argument("--csv_path", type=str, required=True, help="Path to evaluation results CSV")
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen3.8-27B", help="Model name or local directory path")
    parser.add_argument("--output_json", type=str, required=True, help="Path to output summary JSON")
    parser.add_argument("--audit_csv", type=str, default=None, help="Path to output detailed judge decisions CSV")
    parser.add_argument("--device", type=str, default="auto", help="Device map (auto, cuda:0, etc.)")
    parser.add_argument("--torch_dtype", type=str, default="bfloat16", choices=["bfloat16", "float16", "auto"])
    parser.add_argument("--conditions", nargs="+", default=["oracle", "base_asr", "ft_asr"],
                        help="List of conditions to evaluate (default: oracle base_asr ft_asr)")
    parser.add_argument("--preload_cache", type=str, default=None,
                        help="Optional path to existing audit decisions CSV to preload evaluation cache")
    args = parser.parse_args()

    dtype = torch.bfloat16 if args.torch_dtype == "bfloat16" else (torch.float16 if args.torch_dtype == "float16" else "auto")
    df = pd.read_csv(args.csv_path)
    print(f"Loaded {len(df)} benchmark instances from {args.csv_path}")

    judge = SemanticLLMJudge(args.model_id, device=args.device, torch_dtype=dtype)
    if args.preload_cache:
        judge.preload_cache(args.preload_cache)

    condition_specs = {
        "oracle": {
            "intent_col": "oracle_pred_intent",
            "slots_col": "oracle_pred_slots",
            "prompt_col": "prompt"
        },
        "base_asr": {
            "intent_col": "base_asr_pred_intent",
            "slots_col": "base_asr_pred_slots",
            "prompt_col": "prompt"
        },
        "ft_asr": {
            "intent_col": "ft_asr_pred_intent",
            "slots_col": "ft_asr_pred_slots",
            "prompt_col": "prompt"
        }
    }

    full_results = {}
    all_audits = []

    for cond in args.conditions:
        if cond not in condition_specs:
            print(f"[Warning] Unknown condition: {cond}, skipping.", flush=True)
            continue
        spec = condition_specs[cond]
        print(f"\n==========================================", flush=True)
        print(f"EVALUATING CONDITION: {cond.upper()}", flush=True)
        print(f"==========================================", flush=True)
        res = evaluate_condition_pf(
            df=df,
            judge=judge,
            intent_col=spec["intent_col"],
            slots_col=spec["slots_col"],
            prompt_col=spec["prompt_col"]
        )
        audits = res.pop("audit_log")
        for a in audits:
            a["condition"] = cond
            all_audits.append(a)

        full_results[cond] = res
        print(f"[{cond.upper()} Exact] Rec: {res['exact_recall']:.2f}% | Prec: {res['exact_precision']:.2f}% | F1: {res['exact_f1']:.2f}%", flush=True)
        print(f"[{cond.upper()} Sem  ] Rec: {res['semantic_recall']:.2f}% | Prec: {res['semantic_precision']:.2f}% | F1: {res['semantic_f1']:.2f}%", flush=True)
        print(f"[{cond.upper()} Calls] Recall Calls: {res['judge_recall_calls']} | Prec Calls: {res['judge_precision_calls']}", flush=True)

        # Save checkpoint after each condition, preserving existing keys in json
        os.makedirs(os.path.dirname(os.path.abspath(args.output_json)), exist_ok=True)
        disk_results = {}
        if os.path.exists(args.output_json):
            try:
                with open(args.output_json, "r") as f:
                    disk_results = json.load(f)
            except Exception:
                disk_results = {}
        disk_results.update(full_results)
        with open(args.output_json, "w") as f:
            json.dump(disk_results, f, indent=2)

        if args.audit_csv and all_audits:
            os.makedirs(os.path.dirname(os.path.abspath(args.audit_csv)), exist_ok=True)
            new_df = pd.DataFrame(all_audits)
            if os.path.exists(args.audit_csv):
                try:
                    old_df = pd.read_csv(args.audit_csv)
                    combined_df = pd.concat([old_df, new_df], ignore_index=True)
                    combined_df.drop_duplicates(subset=["row_id", "eval_type", "utterance", "tool", "slot", "gold", "pred", "condition"], inplace=True)
                    combined_df.to_csv(args.audit_csv, index=False)
                except Exception:
                    new_df.to_csv(args.audit_csv, index=False)
            else:
                new_df.to_csv(args.audit_csv, index=False)
        print(f"[Checkpoint] Saved {cond.upper()} progress ({len(all_audits)} audits) to disk.", flush=True)

if __name__ == "__main__":
    main()
