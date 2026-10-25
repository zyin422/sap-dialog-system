# Speech Accessibility Project (SAP) — Final SLU Benchmark Dataset (v1.3)

## 1. Executive Summary & Benchmark Partition

* **Total Master Utterances:** 1,309 spoken commands from dysarthric speakers across all clinical cohorts (`DS`, `PD`, `Stroke`).
* **Canonical Benchmark Gold ($N=1274$):** Clean, task-oriented conversational commands across all 10 domains and 29 canonical tools, fully audited and verified against Schema v1.3. Saved to [`SLU_benchmark_gold_1309.csv`](./SLU_benchmark_gold_1309.csv).
* **Out-Of-Domain Excluded Set ($N=35$):** Pure wake phrases, generic intercom broadcasts, ticket e-commerce, unsupported desktop/mobile apps, assistive utility commands outside canonical tools, and isolated dictation punctuation fragments, isolated from evaluation. Saved to [`SLU_benchmark_ood_excluded.csv`](./SLU_benchmark_ood_excluded.csv).

---

## 2. Benchmark Domain & Tool Distributions (N=1274)

| Functional Domain | Tool / Intent Count | Percentage |
| :--- | :--- | :--- |
| **`general_qa`** | 417 commands | 32.7% |
| **`maps_places`** | 164 commands | 12.9% |
| **`media`** | 158 commands | 12.4% |
| **`calendar_alarm`** | 143 commands | 11.2% |
| **`smart_home`** | 100 commands | 7.8% |
| **`health`** | 91 commands | 7.1% |
| **`communication`** | 87 commands | 6.8% |
| **`notes_memory`** | 77 commands | 6.0% |
| **`transport`** | 31 commands | 2.4% |
| **`accessibility`** | 6 commands | 0.5% |

---

## 3. Adjudication Provenance & Rule Enforcements

* **Unanimous Dual-Frontier Agreement:** 855 commands (67.1%)
* **Adjudicated Consensus & Curated:** 419 commands (32.9%)

### Key Rule Resolutions Enforced:
1. **Rule B (Carrier Phrase Stripping):** Stripped polite conversational prefixes (`"show me"`, `"find me a"`, `"tell me"`) from `qa_search.query`.
2. **Rule K (OOD Exclusion):** 35 commands isolated from evaluation (5 pure wake words, 9 broadcasts, 8 ticket purchases, 6 desktop/mobile app opens, 2 screen/camera utilities, 5 dictation fragments).
3. **Rule H (Point-to-Point Navigation):** Adopted Sonnet gold separation of `origin` and `destination` in `maps_route`.
4. **Rule I (Nearby Venues):** Enforced `sort_by: "distance"` for all nearby venue searches in `places_search`.
5. **Rule D (Generic Meeting Title):** Retained generic nouns (`"meeting"`, `"appointment"`) in `schedule_manage.title`.
6. **Rule G (Transit Modifiers):** Decoupled flight modifiers (`"non-stop"`, `"round-trip"`) from transit parameters.
7. **Schema Invariant Parameter Typing:** Enforced clean extraction of `device_type`, `house_place`, and clock timestamps, and eliminated spurious attendee extractions in task reminders.
