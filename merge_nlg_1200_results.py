#!/usr/bin/env python3
"""
merge_nlg_1200_results.py
Reconciles parallel NLG evaluation outputs from Condition 2 (Base ASR on A40)
and Condition 3 (FT ASR on A100) into unified master CSV and summary JSON.
"""

import json
import os
import pandas as pd

def main():
    base_csv = "/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_results.csv"
    ft_csv = "/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_ft_results.csv"
    
    oracle_summary = "/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_summary_checkpoint_oracle.json"
    base_summary = "/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_summary_checkpoint_base_asr.json"
    ft_summary = "/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_ft_summary.json"
    if not os.path.exists(ft_summary):
        ft_summary = "/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_ft_summary_checkpoint_ft_asr.json"

    master_summary = "/work/hdd/bedl/zyin2/benchmark_phase2/clean_eval_1200_nlg_summary.json"

    print("=== Reconciling Parallel Rev 6 NLG Benchmark Runs ===")
    df_base = pd.read_csv(base_csv)
    df_ft = pd.read_csv(ft_csv)

    for col in ["ft_asr_pred_intent", "ft_asr_pred_slots", "ft_asr_pred_domain", "ft_asr_pred_response"]:
        if col in df_ft.columns:
            df_base[col] = df_ft[col]
            print(f"Merged column: {col}")

    df_base.to_csv(base_csv, index=False)
    print(f"Saved master CSV with all 3 conditions: {base_csv}")

    # Merge Summaries
    with open(oracle_summary, "r") as f:
        o_data = json.load(f)
    with open(base_summary, "r") as f:
        b_data = json.load(f)
    with open(ft_summary, "r") as f:
        f_data = json.load(f)

    summary = {
        "oracle": o_data.get("oracle", o_data),
        "base_asr": b_data.get("base_asr", b_data.get("metrics", {}).get("base_asr", b_data)),
        "ft_asr": f_data.get("ft_asr", f_data.get("metrics", {}).get("ft_asr", f_data))
    }

    o_acc = summary["oracle"]["Frame_Acc"]
    b_acc = summary["base_asr"]["Frame_Acc"]
    f_acc = summary["ft_asr"]["Frame_Acc"]
    net_frame = round(f_acc - b_acc, 2)
    gap = o_acc - b_acc
    arr = round((f_acc - b_acc) / gap * 100, 2) if gap > 0 else 0.0

    o_pf = summary["oracle"]["PF"]
    b_pf = summary["base_asr"]["PF"]
    f_pf = summary["ft_asr"]["PF"]
    net_pf = round(f_pf - b_pf, 2)

    summary["comparative_summary"] = {
        "Net_Frame_Gain_FT_minus_Base": net_frame,
        "Adaptation_Recovery_Rate_ARR": arr,
        "Net_PF_Gain_FT_minus_Base": net_pf,
        "Oracle_Frame_Acc": o_acc,
        "Base_ASR_Frame_Acc": b_acc,
        "FT_ASR_Frame_Acc": f_acc
    }

    with open(master_summary, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved master summary JSON: {master_summary}")

    print("\n" + "=" * 60)
    print("=== FINAL 3-CONDITION REV 6 SLU + NLG BENCHMARK RESULTS ===")
    print("=" * 60)
    print(f"Condition (oracle):   TS: {summary['oracle']['TS']}% | TCS: {summary['oracle']['TCS']}% | PF: {summary['oracle']['PF']}% | Frame: {o_acc}%")
    print(f"Condition (base_asr): TS: {summary['base_asr']['TS']}% | TCS: {summary['base_asr']['TCS']}% | PF: {summary['base_asr']['PF']}% | Frame: {b_acc}%")
    print(f"Condition (ft_asr):   TS: {summary['ft_asr']['TS']}% | TCS: {summary['ft_asr']['TCS']}% | PF: {summary['ft_asr']['PF']}% | Frame: {f_acc}%")
    print(f"--> Net Frame Gain:   +{net_frame}%")
    print(f"--> Adaptation Recovery Rate (ARR): {arr}%")
    print(f"--> Net PF Gain:      +{net_pf}%")
    print("=" * 60)

if __name__ == "__main__":
    main()
