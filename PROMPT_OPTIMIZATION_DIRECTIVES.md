# Strict Prompt Engineering & Anti-Hacking Directives

## Purpose
This document establishes the binding, non-negotiable standards for authoring and optimizing the Spoken Language Understanding (SLU) system prompt and schema descriptions. Every prompt modification must be audited against these rules before evaluation.

---

## The 5 Core Anti-Hacking Principles

### 1. Modular Schema Isolation (No Global Exception Tables)
* **Principle:** The global `EXTRACTION RULES` section must be strictly domain-agnostic, universal, and applicable equally to any arbitrary API tool call.
* **Strict Prohibitions:**
  * **Zero Tool Name-Dropping:** Never mention any tool name (e.g., `weather_query`, `schedule_manage`, `iot_device_power`, `maps_route`) inside `EXTRACTION RULES`.
  * **Zero Slot Name-Dropping:** Never reference specific slot names (e.g., `house_place`, `device_type`, `place_name`, `date`, `person`, `title`) inside `EXTRACTION RULES`.
  * **Zero Exception Sub-Bullets:** Never add tool-specific sub-bullets under global extraction rules to patch observed error modes.
* **Allowed in `EXTRACTION RULES`:** Strictly 4 universal linguistic principles:
  1. *Strict Schema Adherence:* Closed 29-tool constraint, semantic enum equivalence, mandatory categorical vs optional entity distinction.
  2. *Verbatim Span Preservation:* Preserve spoken spans without grammatical lemmatization or alteration; maintain complex noun phrases.
  3. *Directive Stripping vs. Question Clause Preservation:* Strip carrier imperative verbs (e.g., define, look up, show me); preserve interrogative question clauses intact (What, When, Where, Who, How).
  4. *Parameter Specialization & Semantic Typing:* Populate each parameter slot strictly according to its defined schema description without cross-populating mismatched semantic entities.

---

### 2. Positive Functional Scope Only (Zero Negative Redirects or Boundaries)
* **Principle:** Every tool and parameter description must state purely what it positively encompasses and accepts.
* **Strict Prohibitions:**
  * **Zero Cross-Tool Redirects:** No parenthetical or direct routing instructions (`"belongs in X"`, `"route to Y"`, `"use X instead"`, `"see Y for Z"`).
  * **Zero Negative Boundary Disclaimers:** Never add ad-hoc negative constraints aimed at steering the model away from a failure mode (`"does not handle turning devices on or off"`, `"does not include compound fixture nouns like front door"`, `"never accepts temporal words like today"`).

---

### 3. Lexical Orthogonality & Zero Benchmark Leakage
* **Principle:** System prompts must remain completely uncontaminated by the evaluation benchmark.
* **Strict Prohibitions:**
  * **Zero Test Entity Injections:** Never use benchmark named entities, brands, people, specific items, or phrases in docstrings or examples (`"parking space"`, `"where did I park"`, `"front door"`, `"heat, cooling"`, `"Sanjiv Lynne"`, `"Sonya Lee"`, `"CVS"`, `"Walgreens"`, `"conundrum"`, `"Naples"`, `"Rome"`).
  * **Generic Examples Only:** If generic illustrative examples are helpful in a parameter docstring, use standard, non-overlapping generic archetypes (e.g., `Seattle, Chicago` for geographic cities; `meeting, call` for calendar event types; `shopping list, to-do list` for list containers).

---

### 4. Standard API Documentation Parity (OpenAPI 3.0 / Matter / Google Assistant Actions)
* **Principle:** All tool and parameter descriptions must read like official public developer API specifications.
* **Required Documentation Components:**
  * **Semantic Role:** Clear definition of what real-world entity or action the parameter represents.
  * **Modality / Enum Criteria:** For enum parameters (e.g., `sort_by`, `query_type`, `state`), provide the positive semantic mapping criteria (e.g., `'distance'` for spatial proximity or nearby requests; `'rating'` for top-rated; `'relevance'` for topical matching).
  * **Categorical Requirement:** Specify when categorical operation modalities (e.g., `query_type`) are mandatory properties that must be selected from the enum.

---

### 5. Zero Asymmetric Co-occurrence Hacks
* **Principle:** Each parameter's definition must be modular and independently grounded in its semantic role.
* **Strict Prohibitions:**
  * Never write procedural co-occurrence rules to patch parsing interactions (`"must be extracted even when date, time, or other parameters follow"`, `"always retained even when participant attendees are present in person"`).
  * Ground role separation structurally (e.g., `title` is the event subject/category noun; `person` is the attendee participant).

---

## Verification Protocol Before Any Evaluation
Every candidate prompt must be manually audited line-by-line against these 5 principles before cluster execution:
1. [ ] Are `EXTRACTION RULES` 100% domain-agnostic with 0 tool or slot names?
2. [ ] Are all tool/parameter descriptions 100% positive without negative disclaimers?
3. [ ] Are all benchmark entities and test-slice phrasing 100% absent?
4. [ ] Does every parameter read like standard public API documentation?
5. [ ] Are there zero procedural co-occurrence patches?
