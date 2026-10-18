# SLU Schema Freeze: Agent Handoff Brief

**Timestamp:** October 18, 2026  
**Project:** Speech Accessibility Project (SAP) — Spoken Language Understanding (SLU) Benchmark  
**Working Directory:** `/Users/zixuan/agy2-projects/sap-dialog-system/`  
**Primary Hub:** `schema_freeze/`

---

## 1. Executive Summary & Current Operational State
* **Pilot Downscaled to 50 Commands:** To achieve immediate turn-around between exactly two human annotators, the pilot set was downscaled from 200 to **50 stratified commands** ([`pilot/SLU_pilot_50.csv`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/pilot/SLU_pilot_50.csv)), strictly enforcing Interpretation A (extractive/open-vocabulary spans), Interpretation B (arguments present; 0 zero-slot commands), and high-confusion boundary clusters.
* **Master Ontology (28 Tools across 10 Domains):**
  * Merged `calendar_manage` ($N=50$) and `reminder_manage` ($N=19$) into unified `schedule_manage` under `calendar_alarm`, unifying event and task reminder parameters into a single `title` slot.
  * Formally dropped dead intent `contacts_manage` ($N=0$), bringing active ontology to 28 tools.
  * Smart door locks mapped to `iot_device_power` (`state: "on"` for lock, `state: "off"` for unlock).
* **Guidelines & Catalog Decoupled:**
  * [`SLU_annotator_guidelines.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/SLU_annotator_guidelines.md): Streamlined 109-line guide with Master Ontology Map, 3-step decision flow, BaseNP span extraction rules, and categorical enum normalization.
  * [`canonical_tool_catalog.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/canonical_tool_catalog.md): Authoritative catalog containing the complete Parameter Quick-Reference (Enums & Spans) and full signatures for all 28 tools.
* **Zero-Dependency Labeling Webapp:**
  * [`pilot/slu_annotator.html`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/pilot/slu_annotator.html): Single-file HTML5/Tailwind webapp. Top row provides the spoken prompt and live JSON output side-by-side; full-width bottom section houses the 3-step decision flow (Domain $\to$ Intent $\to$ Slots), notes, and dual-annotator CSV export.

---

## 2. Directory Layout & Key Assets

```
schema_freeze/
├── README.md                      # Methodology status tracker & asset hub
├── HANDOFF.md                     # This handoff brief
├── SLU_schema_freeze_plan_v2.md   # Master 8-Step Freeze Plan
├── presentation_notes_step2.md    # Step 2 Coverage/Purity analysis & screening decisions
├── SLU_annotator_guidelines.md    # Concise annotator guidelines (109 lines)
├── canonical_tool_catalog.md      # Authoritative 28-tool catalog & parameter tables
├── crosswalks/
│   ├── crosswalk_sap_massive.csv  # Step 1 Crosswalk: Amazon MASSIVE
│   └── crosswalk_sap_topv2.csv    # Step 1 Crosswalk: Meta TOPv2
└── pilot/
    ├── slu_annotator.html         # Interactive zero-dependency labeling webapp
    ├── build_annotator_ui.py      # Webapp builder script
    ├── commands_50.json           # 50 stratified pilot commands (JSON)
    ├── SLU_pilot_50.csv           # 50 pilot commands with baseline references
    ├── SLU_pilot_50_annotator2.csv # Blinded pilot template for Annotator 2
    └── SLU_pilot_200.csv          # Previous 200-command sample (archived reference)
```

---

## 3. Human Annotator Protocol & Handoff Instructions

### Instructions for Annotator 1 & Annotator 2
1. **Open the Webapp:**
   * Double-click [`schema_freeze/pilot/slu_annotator.html`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/pilot/slu_annotator.html) in Chrome, Edge, Safari, or Firefox (no local web server or terminal commands required).
2. **Select Annotator Identity:**
   * In the top-right header, select **Annotator 1** or **Annotator 2** (or enter a custom name) from the dropdown. Progress and labels are automatically autosaved to browser `localStorage`.
3. **Annotate Each Command (3-Step Flow):**
   * **Step 1 (Domain):** Click the functional domain (1 of 10) in the grid.
   * **Step 2 (Canonical Intent):** Click the intended tool/intent from the filtered options.
   * **Step 3 (Slots):**
     * For **Categorical Enums**, click the desired pill option (or click clear).
     * For **Extractive Spans**, highlight text in the utterance transcript card and click **Paste Selection** (the BaseNP rule automatically strips leading articles `a, the` and prepositions `at, to, in, on, with`).
     * If no slots apply, slots automatically default to `{}`.
4. **Save & Advance:**
   * Click **Save & Next** (or press <kbd>Ctrl+Enter</kbd>) to move to the next item.
5. **Download & Export:**
   * Once 50/50 commands are labeled, click the green **Download CSV** button.
   * Annotator 1 downloads `SLU_pilot_50_annotator1.csv`.
   * Annotator 2 downloads `SLU_pilot_50_annotator2.csv`.
6. **Adjudication:**
   * Both CSVs are compared to calculate inter-annotator agreement (Cohen's $\kappa$ on Domain and Intent, F1 on slots).
   * Discrepancies are reviewed in a joint 30-minute adjudication session to establish Gold Standard $y^*$.
