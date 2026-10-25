# Dual-Frontier Consensus Annotation Pipeline (Schema v1.2)

This directory hosts the automated Dual-Frontier Consensus Annotation harness to label the remaining **1,194 commands** from `sap_commands_master.csv` using **Claude 3.5 Sonnet** and **GPT**.

---

## 1. Benchmark Partition Summary

* **Target Benchmark Total:** 1,309 unique commands across all 10 domains and clinical cohorts (`DS`, `PD`, `Stroke`).
* **Reference Golden Dev Set ($D_{dev}$):** 115 master commands (150 gold prompts):
  * Pilot 50: `schema_freeze/pilot/SLU_pilot_50_gold.csv`
  * Frontier 100: `schema_freeze/frontier_100_gold.csv`
* **Remaining Unlabeled Commands:** **1,194 commands** partitioned into **4 balanced web batches** (~300 commands each in `web_batches_even4/`):
  * Batch 1: 300 commands
  * Batch 2: 300 commands
  * Batch 3: 300 commands
  * Batch 4: 294 commands
* **Metadata Index:** [`master_unlabeled_index.csv`](./master_unlabeled_index.csv)

---

## 2. Directory Structure

```
schema_freeze/consensus/
├── README.md                           # This guide
├── master_unlabeled_index.csv          # 1,194 commands mapped to batches & cohorts
├── generate_batches.py                 # Batch partitioning & prompt generator script
├── consensus_agreement.py              # Agreement calculation & triage engine
├── audit_and_adjudicate_full_dataset.py# Adjudication and schema validation script
├── web_batches_even4/                  # 4 balanced web prompt batches
│   ├── prompt_web_batch_01_of_04.md
│   ├── prompt_web_batch_02_of_04.md
│   ├── prompt_web_batch_03_of_04.md
│   └── prompt_web_batch_04_of_04.md
├── predictions/                        # Raw model outputs
│   ├── sonnet/                         # web_batch_01.csv ... 04.csv
│   └── gpt/                            # web_batch_01.csv ... 04.csv
├── agreements/                         # Accepted consensus gold outputs
│   └── web_batch_XX_agreed.csv
└── disagreements/                      # Structured triage queues with suggested rules
    └── web_batch_XX_triage.csv
```

---

## 3. Step-by-Step Annotation Protocol

### Step 1: Copy Batch Prompt
Open the target batch in `web_batches_even4/` (e.g., [`web_batches_even4/prompt_web_batch_01_of_04.md`](./web_batches_even4/prompt_web_batch_01_of_04.md)).
Each prompt includes:
1. Canonical 29-tool schema (10 domains) with Schema v1.2 signatures (including `origin` for `maps_route`).
2. Codified guideline rules (Rules A through I).
3. Exact CSV output schema (`id,domain,intent,slots_json`).
4. 50 input commands labeled with `ID SAP-CMD-XXXX: "..."`.

### Step 2: Run Through Frontier Models
Send the exact batch prompt to:
* **Model A:** Claude 3.5 Sonnet
* **Model B:** GPT (GPT-4o / GPT-4.5 / GPT-6 Instant)

### Step 3: Save Prediction Outputs
Save the resulting CSV outputs without altering row IDs:
* Sonnet output $\rightarrow$ `predictions/sonnet/batch_01.csv`
* GPT output $\rightarrow$ `predictions/gpt/batch_01.csv`

### Step 4: Run Consensus Agreement Script
Execute the agreement engine on the batch:
```bash
python schema_freeze/consensus/consensus_agreement.py --batch 1
```

The script will automatically:
1. Parse and normalize quotes and JSON slots.
2. Validate against `SLU_schema_v1.0.json` (checking allowed domain/intent/parameter names and enums).
3. Compute **Domain Agreement**, **Intent Agreement**, and **Full Slot Exact Match (EM)**.
4. Auto-accept unanimous matches into `agreements/batch_01_agreed.csv` (labeled as `AGREED`).
5. Route discrepancies into `disagreements/batch_01_triage.csv` with automated rule classification (Rules A-I) and suggested resolutions.

### Step 5: Check Status Across Batches
To inspect global progress at any time:
```bash
python schema_freeze/consensus/consensus_agreement.py --status
```

### Step 6: Batch Aggregation
To merge all processed batches into cumulative benchmark files:
```bash
python schema_freeze/consensus/consensus_agreement.py --aggregate
```
Outputs:
* `consensus_gold_cumulative.csv`
* `consensus_triage_cumulative.csv`

---

## 4. Codified Disagreement Resolution Rules (A through I)

| Rule | Trigger Condition | Canonical Resolution |
| :--- | :--- | :--- |
| **Rule A** | Possessive pronouns / prepositions in span | Strip `my`, `our`, `the`, `a`, `to`, `at`, `for` (e.g. `destination: "hotel"`) |
| **Rule B** | Carrier phrase in `qa_search` | Strip `tell me`, `can you look up`; keep core question syntax verbatim |
| **Rule C** | Associative vs declarative memory | Attribute ($X$ is $Y$) $\rightarrow$ `key` & `value`. Declarative statement $\rightarrow$ empty `key`, full statement in `value` |
| **Rule D** | Generic event noun in `schedule_manage` | Retain generic noun (`meeting`, `appointment`, `call`, `reminder`) in `title` slot |
| **Rule E** | Alarm recurrence without frequency marker | Coordinated days belong strictly in `date`; omit `general_frequency` unless explicit recurrence token uttered |
| **Rule F** | Business opening / closing hours | Route venue hours to `maps_places.places_search`, NOT `general_qa.qa_search` |
| **Rule G** | Commercial airlines & transit modifiers | Commercial airlines extract into `route_or_station`; `non-stop`/`round-trip` are Outside (O) tokens |
| **Rule H** | Departure vs arrival in `maps_route` | Separate departure point into `origin` and destination into `destination` |
| **Rule I** | Zero-argument invariance | If no parameters are uttered, `slots` MUST be `{}`. Never invent unuttered entities |
