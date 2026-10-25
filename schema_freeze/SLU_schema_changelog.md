# Speech Accessibility Project (SAP) — SLU Schema Changelog

This document tracks the formal evolutionary changelog of the Spoken Language Understanding (SLU) canonical ontology and tool signatures across project milestones.

---

## Version 1.3 — Full-Dataset Consensus Finalization & OOD Partition (October 25, 2026)

### 1. Benchmark Gold Finalization (N=1,274 Evaluated Commands, N=35 OOD Excluded)
* **Dataset:** Complete audit and adjudication across all 1,309 master commands from `sap_commands_master.csv` (100% evaluated).
* **Consensus Performance:** 91.4% Domain Agreement, 91.1% Intent Agreement, 65.3% Unanimous Full Slot EM (855 commands auto-accepted into gold). All remaining triage items resolved under codified rules, second-pass curation, and user adjudication.
* **Strict Schema Validation:** All 1,274 canonical benchmark commands in `SLU_benchmark_gold_1309.csv` pass OpenAPI / JSON Schema validation with **zero errors, zero hallucinated slots, and zero invalid enums**.

### 2. Out-Of-Domain (OOD) Exclusion Policy (Rule K)
* **Rationale:** As established in project adjudication, non-task commands and utility requests targeting capabilities outside the 29 canonical tools lack conversational tool goals and must not be forced into arbitrary tools.
* **Excluded Partition ($N=35$):** Standalone wake words (*"Alexa."*, *"Hey Siri."*), intercom broadcasts (*"Broadcast '...' "*), event/movie ticket e-commerce (*"Buy tickets at 11 AM."*), third-party desktop OS app launches (*"Open Duolingo."*, *"Open Candy Crush Saga."*, *"Open Yelp."*), screen-reader / camera scanning utilities (*"Read this page."*, *"Scan a QR code."*), and isolated dictation calibration fragments (*"Thank you. Period."*, *"Dear customer service, comma."*, *"Hi, exclamation point."*, *"Thanks, exclamation point"*, *"What time will you be home, question mark."*) isolated into `SLU_benchmark_ood_excluded.csv`.

### 3. Codified Guideline Additions (Rules I, J, K)
* **Rule I (Nearby Distance Sorting in `places_search`):** Spoken inquiries searching for *"nearby"* commercial entities (*"Show me nearby cafes"*, *"nearby shopping malls"*) require `sort_by: "distance"`.
* **Rule J (Streaming Service Launches in `media_play`):** Spoken launches of video/music streaming platforms (*"Open Hulu"*, *"Open Disney Plus"*, *"Open Netflix"*) route to `media.media_play` with the service populated in `service`.
* **Rule K (Task-Oriented Scope Boundary):** Only task-oriented assistant commands targeting the 29 canonical tools are included in benchmark evaluation.

### 4. Intent-Specific Rule Localization in Schema Definitions
* **Architectural Rationale:** Rather than relying on monolithic global prompt instructions (which induce cross-tool prompt bleed, such as over-stripping dictation text or notes), intent-specific constraints (Rules B through J) are localized directly into parameter descriptions within `SLU_schema_v1.0.json` and `canonical_tool_catalog.md`.
* **Inlined Constraints:**
  * `qa_search.query`: Explicit carrier phrase stripping instruction (Rule B).
  * `places_search.sort_by` & `description`: Distance ranking requirement for "nearby" inquiries (Rule I) and commercial venue hours routing (Rule F).
  * `maps_route.origin` & `destination`: Starting location decoupling for point-to-point queries (Rule H).
  * `media_play.service` & `description`: Streaming app launch platform routing (Rule J).
  * `transit_lookup.route_or_station` & `time`: Commercial airline carrier retention and flight modifier exclusion from time (Rule G).
  * `memory_note_manage.key` & `value`: Declarative clause vs. keyed memory separation (Rule C).
  * `alarm_manage.general_frequency` & `date`: Explicit recurrence adverb constraint (Rule E).
  * `schedule_manage.title`: Generic event noun retention constraint (Rule D).
  * `rideshare_book.destination`: Aligned destination as optional to support destination-less taxi hails (e.g. *"Request a taxi ride"*).

### 5. Benchmark Refinements & Semantic Curation
* **Slot Disambiguation in `schedule_manage`:**
  * Cleaned `title` and `person` boundaries: In `SAP-CMD-0328` (*"Remind me to take a break in 15 minutes"*), set `title: "take a break"` and eliminated spurious reflexive `person: "me"` to harmonize with `0329`–`0332`.
  * Preserved full event noun phrases in `title` for `SAP-CMD-0800` (`title: "kristin's recital"`) and `SAP-CMD-0801` (`title: "shak's holiday party"`), eliminating misclassified attendee entities.
* **Extractive Substring Compliance:**
  * Cleaned `SAP-CMD-1127` (*"Play a Beatles song on Amazon music."*) to extract literal substring `artist: "beatles"`, stripping unuttered hallucinated article *"the"*.
* **OOD Partition Expansion ($N=35$):**
  * Transferred 7 non-task / out-of-scope utterances (`SAP-CMD-0277`, `0322`, `0334`, `0630`, `0674`, `0821`, `0862`) to `SLU_benchmark_ood_excluded.csv`.

---

## Version 1.2 — Dual-Frontier Stress-Test & Schema Freeze (October 22, 2026)

### 1. Empirical Dual-Frontier Calibration (Claude 3.5 Sonnet vs. GPT-6 Instant)
* **Dataset:** 100 high-ambiguity spoken commands spanning all 10 domains and 29 tools (0% overlap with Pilot 50).
* **Batch 1 (Commands 1–50):** 100% Domain Agreement, 100% Intent Agreement, 74.0% Slot EM. Disagreements partitioned into 2 systematic boundary patterns (generic meeting titles and alarm frequency inference).
* **Batch 2 (Commands 51–100):** 98.0% Domain Agreement, 98.0% Intent Agreement, 68.0% Slot EM. Tested cross-domain boundary cases in transport, maps, notes, and media.
* **Publication Reproducibility Protocol:** Closed-source frontier LLMs were used exclusively for inductive edge-case discovery and ontology calibration. For the final archival benchmark paper, gold ground-truth generation will be executed via a frozen, pinned open-weights model checkpoint (e.g., Qwen 2.5 72B / Llama 3.3 70B) at $T=0.0$ with exact seed, prompt, and system environment logged.

### 2. Schema Architectural Updates
* **Added `origin` to `maps_route` (Domain: `maps_places`):**
  * *Rationale:* Spoken navigation queries frequently specify explicit departure points (e.g., Prompt #383: *"How far is Brattleboro, Vermont from Montreal, Canada?"*). Adding an optional `origin` slot decouples the departure point (`origin: "montreal, canada"`) from the target destination (`destination: "brattleboro, vermont"`), avoiding loss of spatial information or artificial slot concatenation.
* **Formalized Airline Carrier in `route_or_station` (`transit_lookup`):**
  * *Rationale:* Affirmed parity with Pilot 50 Gold (#1291: *"on Southwest Airlines"* $\rightarrow$ `route_or_station: "southwest airlines"`). Commercial airline carriers (*"Jet Blue"*, *"Air Canada"*, *"American Airlines"*) belong in `route_or_station` alongside rail and bus lines.

### 3. Codified Guideline Rules (Rules D through H)
* **Rule D (Generic Event Noun Preservation in `schedule_manage`):**
  * When an utterance contains a generic event noun (*"meeting"*, *"call"*, *"appointment"*, *"reminder"*) without a custom topic (e.g., *"Cancel my meeting with Sanjiv Lynne"*), retain the noun in `title` (`title: "meeting"`). The noun carries inherent event category metadata required for calendar retrieval.
* **Rule E (Alarm Recurrence Token Constraint in `alarm_manage`):**
  * The `general_frequency` enum (`daily`, `weekdays`, `weekends`, `weekly`, `monthly`) must ONLY be populated when an explicit recurrence token or frequency adverb is uttered (e.g., *"daily"*, *"weekdays"*, *"every Thursday"*). Coordinated multi-day targets without explicit recurrence markers (e.g., *"on Thursday and Friday"*) belong strictly in `date` (`date: "thursday and friday"`), leaving `general_frequency` unpopulated.
* **Rule F (Business Hours & Metadata in `places_search`):**
  * Spoken inquiries regarding commercial venue opening hours, closing times, or operational status (e.g., Prompt #564: *"When is Bed, Bath and Beyond open until?"*) map to `maps_places.places_search` (`business_name: "bed, bath and beyond"`), NOT `general_qa.qa_search`. Operating hours are structured attributes of a local business entity.
* **Rule G (Transit Modifiers in `transit_lookup`):**
  * Spoken commercial airlines extract into `route_or_station`. General flight modifiers such as *"non-stop"* or *"round-trip"* are Outside (O) tokens and must NOT be forced into `time` (which is strictly reserved for clock/departure timestamps).
* **Rule H (Origin and Destination in `maps_route`):**
  * When navigation or distance queries specify both a starting point and a target (e.g., *"How far is X from Y?"*), extract the departure point into `origin` and the destination into `destination`.

---

## Version 1.1 — Post-Pilot Adjudication & Machine-Schema Freeze (October 22, 2026)

### 1. Architectural Changes (28 $\rightarrow$ 29 Tools)
* **Added `media_search` (Tool #20, Domain: `media`):**
  * *Motivation:* In pilot evaluation, movie browsing and recommendation commands (e.g. Prompt #724: *"Show me movies with Benicio Del Toro"*) were inappropriately dumped into `qa_search`. `media_search` decouples catalog discovery from streaming playback actuation.
  * *Slots:* `media_type` (Enum: `["movie", "tv_show", "music", "podcast", "audiobook"]`), `person` (Span), `genre` (Span), `title` (Span).
* **Extended `media_play` (Tool #19, Domain: `media`):**
  * Added `service` (Extractive Span) to support 3rd-party video/music streaming services (e.g., Prompt #252: *"Open Hulu"*, Prompt #286: *"Play 'Transformers' on Paramount Plus"*).
  * Expanded `media_type` enum to include `["movie", "tv_show"]`.
* **Extended `iot_sensor_query` (Tool #27, Domain: `smart_home`):**
  * Expanded `sensor_type` enum to include `"lock"` and `"contact"` (e.g. Prompt #103: *"Is the front door locked?"* $\rightarrow$ `{"device_type": "front door", "sensor_type": "lock"}`).
  * Decouples interrogative state inspection from binary actuation in `iot_device_power`.

### 2. Annotation Guideline Refinements (Rules A, B, C)
* **Rule A (BaseNP Possessive Stripping):** Expanded the BaseNP extraction rule to strip possessive pronouns (`my`, `our`, `your`, `his`, `her`) alongside leading prepositions and articles (e.g., Prompt #445: *"Map a route to our hotel"* $\rightarrow$ `destination: "hotel"`).
* **Rule B (Carrier Phrase Stripping in `qa_search`):** Standardized that `query` captures the core question, stripping conversational prefixes (*"can you look up"*, *"tell me"*, *"search google for"*), while preserving verbatim question syntax without hallucinating artificial slots.
* **Rule C (Declarative vs. Keyed Memory in `memory_note_manage`):**
  * *Associative Attributes ($X$ is $Y$):* Extract both `key` and `value` (e.g., *"Our parking space is green"* $\rightarrow$ `key: "parking space"`, `value: "green"`).
  * *Declarative Clauses (Unkeyed):* Store the full clause in `value` and leave `key` empty (e.g., Prompt #1118: *"Remember that we're out of batteries"* $\rightarrow$ `action: "store"`, `value: "we're out of batteries"`). Prevents fracturing grammatical clauses.

### 3. Generated Deliverables
* **`schema_freeze/SLU_schema_v1.0.json`:** Authoritative machine-readable OpenAPI / Function Calling JSON schema containing all 29 tools, parameter properties, and required constraints for LLM batch inference.
* **`schema_freeze/pilot/SLU_pilot_50_gold.csv`:** Adjudicated ground truth for all 50 pilot commands ($y^*$).
* **Preserved Raw Annotations:** [`SLU_pilot_50_zixuan.csv`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/pilot/SLU_pilot_50_zixuan.csv) and [`SLU_pilot_50_xiuwen.csv`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/pilot/SLU_pilot_50_xiuwen.csv) preserved untouched for inter-annotator agreement provenance.

---

## Version 1.0 — Human Pilot Benchmark Freeze (October 18, 2026)

### 1. Ontology Merges & Pruning (30 $\rightarrow$ 28 Tools)
* **Unified `schedule_manage`:** Merged `calendar_manage` ($N=50$) and `reminder_manage` ($N=19$) under `calendar_alarm` into a single tool, standardizing appointment names, meeting descriptions, and task reminders into a single `title` slot.
* **Dropped `contacts_manage`:** Removed dead intent with 0 occurrences across all 1,305 SAP prompts.
* **Door Locks to `iot_device_power`:** Standardized smart door lock control into binary power (`state: "on"` for lock, `"off"` for unlock).

### 2. Dual-Type Parameter Typing
* Explicitly partitioned all benchmark parameters into mutually exclusive **Categorical Enums** (closed sets: `action`, `state`, `direction`, `media_type`, `query_type`, `info_type`, `ui_element`, `setting`, `sort_by`, `general_frequency`, `transit_type`, `sensor_type`) and **Extractive Spans** (verbatim substrings).
* Codified the **BaseNP Extraction Rule** (strip leading prepositions and articles) and strict **No-Hallucination Rule** (never invent unuttered keys or values).

### 3. Pilot Benchmark Setup
* Downscaled pilot from 200 to 50 stratified commands (`SLU_pilot_50.csv`) across all 4 clinical cohorts (`PD`, `DS`, `CP`, `Stroke`) and 10 domains.
* Created zero-dependency HTML5/Tailwind webapp (`slu_annotator.html`) for dual-annotator blinding.

---

## Version 0.1 — Pre-Freeze Baseline (October 13, 2026)

* Initial uncurated schema crosswalk from Amazon MASSIVE and Meta TOPv2 mappings.
* 30 candidate intents and 45 loosely typed slots.
* High boundary confusion between calendar/reminder, power/adjust, and search fallback sinks (`qa_search` absorbed 35% of dataset).
