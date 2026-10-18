# Speech Accessibility Project (SAP) — SLU Schema Freeze Hub

This directory contains the authoritative artifacts, crosswalks, guidelines, tool catalogs, and pilot datasets for the **8-step SLU Schema Freeze Methodology** defined in [`SLU_schema_freeze_plan_v2.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/SLU_schema_freeze_plan_v2.md).

---

## Directory Structure & Asset Index

```
schema_freeze/
├── README.md                      # This index and methodology status tracker
├── HANDOFF.md                     # Agent & annotator handoff protocol
├── SLU_schema_freeze_plan_v2.md   # Master 8-step schema freeze methodology
├── presentation_notes_step2.md    # Step 2 Presentation Notes & Screening Actions
├── SLU_annotator_guidelines.md    # Step 3 Concise Annotator Guidelines (109 lines)
├── canonical_tool_catalog.md      # Authoritative 28-tool catalog & parameter specs
├── crosswalks/                    # Step 1 Benchmark Crosswalk Tables
│   ├── crosswalk_sap_massive.csv  # SAP <-> Amazon MASSIVE (54 rows: Domain + Intent)
│   └── crosswalk_sap_topv2.csv    # SAP <-> Meta TOPv2 (49 rows: Domain + Intent)
└── pilot/                         # Step 3 Stratified Pilot Datasets & Interactive Webapp
    ├── slu_annotator.html         # Zero-dependency interactive annotation webapp
    ├── build_annotator_ui.py      # Webapp builder script
    ├── commands_50.json           # 50 Stratified pilot commands (JSON)
    ├── SLU_pilot_50.csv           # 50 Stratified commands with baseline references
    ├── SLU_pilot_50_annotator2.csv # Blinded pilot template for Annotator 2
    └── SLU_pilot_200.csv          # 200 Stratified pilot dataset (archived reference)
```

---

## Execution Status & Artifact Tracker

| Step | Milestone | Status | Key Artifacts | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Step 1** | **The Crosswalk** | **Complete** | [`crosswalks/crosswalk_sap_massive.csv`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/crosswalks/crosswalk_sap_massive.csv)<br>[`crosswalks/crosswalk_sap_topv2.csv`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/crosswalks/crosswalk_sap_topv2.csv) | 2-tier structural mapping (Domain & Intent) against Amazon MASSIVE (18 domains, 60 intents) and Meta TOPv2 (8 domains, 82 intents). |
| **Step 2** | **Screening Gate** | **Complete** | [`presentation_notes_step2.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/presentation_notes_step2.md) | Coverage & Aligned Purity ($P_{\text{align}}$) computed across 1,300 commands. Formulated Category 1 (Merge/Drop/Split) and Category 2 (Boundary Refinements). Consolidated `schedule_manage` and dropped dead intent `contacts_manage`. |
| **Step 3** | **Pilot Preparation** | **Ready for Annotation** | [`SLU_annotator_guidelines.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/SLU_annotator_guidelines.md)<br>[`canonical_tool_catalog.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/canonical_tool_catalog.md)<br>[`pilot/slu_annotator.html`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/pilot/slu_annotator.html)<br>[`pilot/SLU_pilot_50.csv`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/pilot/SLU_pilot_50.csv) | Concise guidelines (109 lines), standalone 28-tool catalog, and 50 stratified dysarthric command pilot with zero-dependency HTML5 annotation webapp for rapid dual-annotator turnaround. |
| **Step 4** | **Confusion Analysis** | Next | *Pending Step 3 Labels* | Separate Human and LLM confusion matrices against Adjudicated Gold Standard ($y^*$) using 3-way rubric. |
| **Step 5** | **Active Dataset Audit** | Next | *Pending Step 4* | Train classifier on Gold labels; audit only high-discrepancy prompts (~50–80) across the remaining dataset. |
| **Step 6** | **Slot Check** | Next | *Pending Step 4* | $28 \times 35$ Intent $\times$ Slot matrix, ghost slot pruning, singleton unification (`device` $\rightarrow$ `device_type`), and span/enum verification. |
| **Step 7** | **Changelog & Decision** | Next | `SLU_schema_changelog.md` | Formal audit trail of every schema change with triggering empirical tests. |
| **Step 8** | **Freeze & Verification** | Final | `SLU_schema_v1.0.json` | Final schema export and verification pilot ($\alpha \ge 0.70$). |
