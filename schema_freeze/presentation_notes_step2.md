# Speech Accessibility Project (SAP) SLU Benchmark
## Step 2 Presentation Notes & Actionable Schema Recommendations

**Date:** October 15, 2026  
**Context:** Findings, Diagnostics, and Actionable Proposals from Step 2 (Coverage and Purity Screening Gate) across 1,300 evaluated spoken commands.

---

### Executive Summary for the Team
* **Baseline Health:** Core assistant tools (`weather_query`, `lists_manage`, `places_search`, `email_manage`, `media_play`, `calendar_manage`) exhibit $\ge 95\%$ crosswalk-aligned purity, proving the candidate architecture is solid.
* **Immediate Pruning:** Dead intent `contacts_manage` ($N = 0$) is queued to be formally dropped.
* **Core Triage Area:** `qa_search` absorbs 35% of prompt volume with only 28.8% raw purity, acting as an unconstrained sponge.
* **Clinical Affordances:** Novel assistive intents (`health_*`, `accessibility_*`) are mathematically verified as missing from mainstream mobile assistant taxonomies (MASSIVE/TOPv2).

---

### Category 1: Structural Schema Actions (`Merge` / `Drop` / `Split`)
*These represent physical additions, deletions, or consolidations of tool signatures in the candidate schema registry:*

#### 1. Drop Dead Intent
* **Drop `contacts_manage` ($N=0$):**
  * *Evidence:* Zero prompts in the dataset ever elicited adding, editing, or deleting an address book contact card.
  * *Action:* Prune `contacts_manage` from the registry. Its ghost parameters (`contact_name`, `email_address`) are dropped with it.

#### 2. Candidate Merges for Simplification
* **Merge `call_make` ($N=37$) and `call_manage` ($N=4$) $\rightarrow$ `telephony_manage` (or unified `call_manage`):**
  * *Rationale:* Combines dialing calls with in-call controls (mute, hang up, decline). Both deal with active carrier voice/video telephony. Consolidates telephony into a single CRUD/lifecycle tool parameterized by `action`.
* **Merge `reminder_manage` ($N=19$) and `calendar_manage` ($N=50$) $\rightarrow$ `schedule_manage`:**
  * *Rationale:* In natural speech, speakers use "remind me to...", "schedule", and "put on calendar" interchangeably for time-anchored tasks. If annotators struggle to separate meetings from reminders, merge them into a unified scheduling tool.
* **Merge `rideshare_book` ($N=1$) and `transit_lookup` ($N=39$) $\rightarrow$ `transport_transit_manage`:**
  * *Rationale:* `rideshare_book` is an isolated singleton with only 1 command (*"Call me an Uber"*). Merging it into public transit booking consolidates all passenger transportation logistics into one tool.
* **Merge `iot_sensor_query` ($N=3$) $\rightarrow$ `iot_device_adjust` (or `qa_search`):**
  * *Rationale:* Ambient temperature inquiries (*"What is the living room temperature?"*) have only 3 prompts. If a standalone sensor tool is unwarranted, fold it into IoT status adjustment or general QA.

#### 3. Sink Triage & Tool Preservation
* **Triage / Deconstruct `qa_search` ($N=455$, 34.87% of data):**
  * *Rationale:* Sinks 35% of the dataset with only 28.8% raw purity across 17 MASSIVE classes.
  * *Action:* Narrow scope to factual world knowledge, definitions, and calculations (aligning with `qa_factoid`). Prevent over-fracturing (do NOT create 17 tiny classes for movies, stocks, currency, recipes), but carve out conversational fallback/chitchat if present.
* **Preserve `order_manage` ($N=6$) and `device_find` ($N=1$) as Distinct Tools:**
  * *Rationale:* Do **NOT** merge these into `qa_search`. Although their volume is low, tracking an e-commerce package delivery or audibly pinging a misplaced phone requires specialized API actions, distinct from a web search engine.

---

### Category 2: Guideline & Boundary Refinements (`Refine Intent Boundaries`)
*These tools remain separate, but their written guidelines, inclusion/exclusion rules, and keyword cues must be sharpened to eliminate annotator ambiguity in Step 3:*

#### 1. `alarm_manage` vs. Calendar / Scheduling
* **The Confusion:** Countdown timers (*"timer for 10 minutes"*) were dumped into `calendar_set` by MASSIVE because it lacked a timer intent.
* **Refinement:** Explicit keyword and temporal rule:
  * `alarm_manage`: Exclusively handles clock alarms and countdown durations, triggered by explicit keywords (`"alarm"`, `"wake up"`, `"timer"`) or relative duration offsets (*"in 20 minutes"*).
  * `calendar_manage`: Exclusively handles appointment/meeting events anchored to a specific calendar date/time.

#### 2. `memory_note_manage` vs. Calendar / Reminders
* **The Confusion:** Cognitive memory storage (*"Remember that my locker combination is 4412"*) was misclassified into `calendar_set` (12) and `CREATE_REMINDER` (11).
* **Refinement:** Explicit time-anchor exclusion rule:
  * `memory_note_manage`: Strictly for notes, facts, and memos that **lack a specific trigger date or time**.
  * If a user utterance contains an explicit time anchor (*"Remind me at 3 PM to..."*), it is excluded from memory notes and routed to calendar/reminder.

#### 3. `media_play` vs. `media_control`
* **The Confusion:** Audio scrubbing commands (*"Fast forward 2 minutes"*, *"Skip backward 10 seconds"*, *"Skip to next chapter"*) were dumped into `play_audiobook` (16) by MASSIVE due to lack of a seek intent.
* **Refinement:** Sharp lifecycle boundary:
  * `media_play`: Strictly for **initiating playback** of a media entity (music, podcast, audiobook, radio station).
  * `media_control`: Strictly for **modifying ongoing playback** state, including play/pause/resume, track skipping, user likeness (like/dislike), and temporal scrubbing (fast-forward, rewind).

#### 4. `iot_device_power` vs. `iot_device_adjust`
* **The Confusion:** Utterances like *"Turn the living room light bright"* blend power and level adjustments.
* **Refinement:** Discrete vs. Continuous parameter rule:
  * `iot_device_power`: Strictly for **binary power toggles** (`{"on", "off"}`).
  * `iot_device_adjust`: Strictly for **continuous or multi-value adjustments** (`brightness`, `temperature`, `color`, `speed`).

#### 5. `health_*` and `accessibility_*` Clinical Shields
* **The Confusion:** Generic assistants lack health domains, forcing medication reminders into generic calendars and clinical drug queries into generic QA factoids.
* **Refinement:** Explicit clinical inclusion rule:
  * Any utterance specifying prescription drugs, dosage schedules, or pharmacy refills routes to `health_*` tools.
  * Any utterance modifying speech dictation or interface accessibility scaling routes to `accessibility_*` tools.
  * Both cohorts are shielded from deletion despite low support ($N \le 5$).

---

### Empirical Reference Data (Step 2 Diagnostics)

#### Communication Prompt Reality Check:
* *Telephony (`call_make`, $N=37$):* *"Call Aliz Kinsley"*, *"Call area code 053-621-4879"*. TOPv2 has zero telephony (`none`: 37). MASSIVE lacks a dedicated phone call tool (forced to `email_querycontact`: 37).
* *Messaging (`messages_manage`, $N=19$):* *"Please send this text"*, *"Read my messages"*. **$94.7\%$ pure in TOPv2** (`SEND_MESSAGE`: 17, `GET_MESSAGE`: 1). Only MASSIVE was confounded (`email_sendemail`: 18).

#### Media Control Reality Check:
* *Audio Scrubbing (`media_control`, $N=23$):* *"Skip to next chapter"*, *"Fast forward 2 minutes"*, *"Skip backward 10 seconds"*. MASSIVE dumped 16 of these into `play_audiobook` because it lacks a seek tool.

#### Low Purity Sink Breakdown (`qa_search`, $N=455$):
* Absorbs 131 factoid QA, 40 cooking recipes, 26 definitions, 25 social chitchat, 18 news updates, 17 movie showtimes, 16 calendar queries, 16 stock tickers, 15 music plays, and 10 math equations.
