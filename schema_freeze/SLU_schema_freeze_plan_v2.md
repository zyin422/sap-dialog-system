# SLU Schema Freeze Plan (domain, intent, slot) v2.0

Scope: determine and freeze the SLU schema (domain, intent, slot) for SAP command utterances before any large-scale labeling. Only SLU is in scope. The schema is then used to label the commands in the SAP prompt set and the SAPC2 test commands.

## 1. Decisions (fixed)

- Freeze the schema before large-scale labeling.
- Annotators: 1–4 people, with human adjudication of disagreements.
- LLMs for labeling: 2–3 of the strongest open-weight models available at the time of labeling, from different model families. Record the exact model name, version, checkpoint identifier, and inference settings (temperature 0, fixed prompt). Verify the current open-weight leaderboard before choosing, because the best model changes over time.
- Schema structure: three layers — domain, intent, slot — defined in a single registry file with names, definitions, and inclusion and exclusion rules.

## 2. Inputs

| Input | Location | Use |
|---|---|---|
| SAP registry (candidate schema) | `sap-dialog-system/benchmark_curation/schema_registry.json` | Starting point (10 domains, 30 intents, 45 slot names) |
| Current SAP labels | `label_candidates/claude-haiku-5-5_sap.csv` | 1,305 commands with labels; baseline for coverage tests |
| MASSIVE labels | `label_candidates/claude-haiku-5-5_massive.csv` | Reference taxonomy (18 domains, 60 intents, 55 slots) |
| TOPv2 labels | `label_candidates/claude-haiku-5-5_topv2_flat.csv` | Reference taxonomy (8 domains, 82 intents, 84 slots) |
| Commands | `label_candidates/claude-haiku-5-5_sap.csv` (`prompt` col) | 1,305 unique prompts to validate the schema against |

## 3. Steps

### Step 1: Crosswalk
- 2-tier structural mapping across the core architectural layers:
  1. **Domain:** Map the 10 SAP domains to MASSIVE (18) and TOPv2 (8) domains.
  2. **Intent:** Map every SAP tool to the closest MASSIVE and flattened TOPv2 intents.
  *(Note on Slots: In modern function-calling/tool-use SLU, parameters are strictly scoped properties of parent tool signatures rather than global BIO tokens. Flat slot crosswalks across disjoint tools create polysemy confounds. Slot alignment is formally decoupled from Step 1 and deferred to Step 6, where tool-scoped parameters `tool.slot` are audited directly on the adjudicated schema).*
- Classify all mappings into canonical buckets:
  1. `1-to-1`: Direct semantic equivalence.
  2. `1-to-Many`: Consolidated tool (e.g. `play_music`, `play_podcast` $\rightarrow$ `media_play`).
  3. `Many-to-1`: Ambiguous legacy intent split into multiple distinct SAP tools (e.g. MASSIVE `social_post` $\rightarrow$ split into `call_make` and `messages_manage`).
  4. `Many-to-Many`: Bidirectional restructuring (e.g. `calendar_manage` + `reminder_manage` $\rightarrow$ MASSIVE `calendar_set` / `calendar_query` / `calendar_remove`).
  5. `Novel [Assistive]`: Unique clinical/assistive capabilities (`health_*`, `accessibility_*`).
  6. `Out-of-Scope`: Legacy capabilities not elicited in SAP speech data (e.g. `takeaway`, `cooking`, games).
- Output: `crosswalk_sap_massive.csv`, `crosswalk_sap_topv2.csv` (Domain and Intent tiers).

### Step 2: Coverage and purity (Screening Gate)
- Commands per intent and per domain.
- Share of the `qa_search` fallback (currently 35% of commands).
- Compute **Domain Purity** and **Intent Purity** of SAP against established benchmarks (MASSIVE, TOPv2) as diagnostic standards (slots are excluded here; audited in Step 6).
- Action reference for intent purity:
  - $\text{Purity} \ge 0.85$ (High): Keep and lock.
  - $0.60 \le \text{Purity} < 0.85$ (Moderate): Disambiguation boundary rule.
  - $\text{Purity} < 0.50$ (Low): Split if high volume (like `qa_search`), or merge/remove if low support.
- **Screening Gate & Pre-annotation Revision:** Make immediate structural adjustments before human labeling:
  - Drop zero-frequency intents (e.g. `contacts_manage` with 0 commands).
  - Draft preliminary boundary rules for low-purity buckets (e.g. `qa_search`) informed by benchmark splits.
  - Protect rare assistive intents ($N \le 5$, e.g. `accessibility_dictation_toggle`) from premature deletion.
  - **Slot Type Specification:** Explicitly define every slot as an **Extractive Span** (verbatim copy, e.g. `song_name`) or **Categorical Enum** (predefined menu, e.g. `action: ["up", "down"]`), ensuring Step 3 annotators have unambiguous rules.

### Step 3: Pilot labeling for agreement
- Sample 200 commands using **purity-tiered stratified sampling**:
  - High purity ($\ge 0.85$): small sanity-check quota.
  - Moderate/Low purity ($< 0.85$): heavy quota to stress-test revised boundaries.
  - Rare assistive intents ($N \le 5$): 100% inclusion to protect clinical capabilities.
  - Stratified across clinical etiology cohorts (`PD`, `DS`, `CP`, `Stroke`).
- Each annotator labels the sample independently using candidate schema definitions and inclusion/exclusion rules.
- Each LLM labels the same sample with identical definitions and few-shot examples.
- Compute Krippendorff's alpha on **initial pre-adjudication labels** (reporting separate $\alpha$ for domain, intent, and slot presence).
- Adjudicate disagreements through discussion to produce the gold-standard ground truth for Step 4 and Step 5.
- Compute pairwise agreement between LLMs and between LLMs and the majority of humans.
- Gate: alpha ≥ 0.7 for domain and intent. Intents below 0.6 agreement are redefined.

### Step 4: Confusion analysis
- Build two separate confusion matrices against the **Adjudicated Gold Standard** from Step 3:
  1. **Human Confusion Matrix:** Human initial labels vs. Gold Standard (evaluates guideline and linguistic ambiguity).
  2. **LLM Confusion Matrix:** LLM initial predictions vs. Gold Standard (evaluates machine parseability and prompt sensitivity).
- Rank the top confused pairs $(I_A, I_B)$ by error count and review the exact mislabeled prompts.
- Apply the 3-way decision rubric:
  1. **Disambiguation Rule:** Semantic distinction is real, but phrasing overlaps (e.g., `iot_device_power` vs `iot_device_adjust` $\rightarrow$ binary toggle vs continuous scalar parameter).
  2. **Merge:** Semantic distinction is subjective and annotators fail to agree even after discussion (e.g., `calendar_manage` vs `reminder_manage` $\rightarrow$ unified `schedule_manage`).
  3. **Split:** An intent acts as an attractor sink absorbing unrelated commands (e.g., `qa_search`).

### Step 5: Active dataset audit & benchmark baseline
- **Active Dataset Audit (anchored on Gold Labels):**
  - Train a lightweight classifier / semantic similarity model on the **200 Adjudicated Human Gold Labels** from Step 3.
  - Predict on the remaining **1,105 Haiku-labeled commands** and flag discrepancies (where classifier prediction $\neq$ Haiku label).
  - Target human review strictly to the flagged prompts (~50–80 commands) to audit the full dataset without full manual re-annotation.
- **Benchmark Baseline:** Report clean-text intent classification $F_1$ upper-bound for the paper to evaluate downstream Voxtral ASR error propagation.
- *(Note: Classifier $F_1$ is not used as a circular gate to delete classes; structural changes are driven by Steps 2–4 and clinical necessity).*

### Step 6: Slot check
- Build the $30 \times 45$ **Intent × Slot usage matrix** (verify empirical sparsity and parameter distribution).
- **Prune Ghost Slots:** Remove parameter names in the registry with zero occurrences across all 1,305 prompts (e.g., `contact_name`, `order_id`, `email_address`).
- **Unify Singletons & Synonyms:**
  - Rename singleton slots to match existing taxonomy (e.g., `device` in `device_find` $\rightarrow$ `device_type`).
  - Standardize cross-intent parameter synonyms (e.g., `event_name` vs `title`).
- **Dual-Type Slot Audit:**
  - For **Categorical Enums**: verify values strictly belong to allowed schema enums (0% invalid enums).
  - For **Extractive Spans**: verify values match verbatim prompt substrings (0% hallucinated spans).
- **Tool-Scoped Benchmark Slot Alignment:** Audit and map parameters at the qualified `tool.slot` level against MASSIVE and TOPv2 counterparts for cross-benchmark evaluation.

### Step 7: Decision and revision
- Synthesize all findings from Steps 1–6 into final schema decisions (Keep, Merge, Split, Rename, Remove, or Out-of-Scope).
- Document every change in `SLU_schema_changelog.md` with the triggering test and empirical evidence:
  - Drops: Dead intents (`contacts_manage`) and ghost slots (`contact_name`, `order_id`, `email_address`).
  - Splits: Low-purity sinks (`qa_search` split into factual QA vs conversational/out-of-scope).
  - Boundary rules: Confused pairs from Step 4 (`iot_device_power` vs `iot_device_adjust`).
  - Unifications: Slot naming from Step 6 (`device` $\rightarrow$ `device_type`).
  - Protected rare intents: Validate clinical necessity before merging (`accessibility_dictation_toggle`).

### Step 8: Freeze
- Write the frozen schema as `SLU_schema_v1.0.json` with definitions, inclusion and exclusion rules, examples, and the changelog.
- Re-run the pilot on 50 new commands to confirm the revised definitions work. Gate: alpha ≥ 0.7 on this check.
- **Bounded Two-Phase Protocol:** Round 1 (Step 3: 200 commands) diagnoses flaws; Round 2 (Step 8: 50 commands) verifies the frozen definitions. Total human labeling is strictly bounded to 250 commands (prevents endless iteration loops).

## 4. Visualizations (one HTML report)

1. Coverage bar chart (commands per intent, log scale).
2. Domain → intent diagram (sankey or treemap).
3. Confusion matrix from Step 4, with agreement per intent.
4. Crosswalk sankey (SAP → MASSIVE and TOPv2), with purity per intent.
5. Intent × slot heatmap.
6. Learnability plot (F1 vs. support).
7. Embedding map (UMAP or t-SNE), colored by intent and by domain.
8. Schema graph (domain, intent, slot), with unused nodes marked.

## 5. Outputs

- `SLU_schema_v1.0.json`: frozen schema.
- `SLU_schema_changelog.md`: every change with reason and test result.
- `SLU_schema_validation_report.html`: plots and test results.
- `SLU_pilot_labels.csv`: pilot labels from annotators and LLMs, for reporting agreement.
- Methods note for the paper: annotators (number, role), LLMs (name, version, checkpoint, settings), agreement scores, and the decision log.

## 6. Order of execution

1. Step 1 (crosswalk).
2. Step 2 (coverage and purity).
3. Step 3 (pilot labeling).
4. Step 4 and Step 5 (confusion and learnability), in parallel.
5. Step 6 (slot check).
6. Step 7 (decisions).
7. Step 8 (freeze and re-check).
8. Visualizations and report, after Step 8.

Large-scale labeling starts only after Step 8 is passed.
