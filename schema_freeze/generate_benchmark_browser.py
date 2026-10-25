#!/usr/bin/env python3
"""
generate_benchmark_browser.py

Generates a standalone, feature-rich interactive HTML visual explorer for the
Speech Accessibility Project (SAP) SLU Benchmark Dataset (All 1,309 Commands).

Outputs:
  - schema_freeze/SLU_benchmark_browser.html
"""

import csv
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "schema_freeze" else SCRIPT_DIR
GOLD_CSV = SCRIPT_DIR / "SLU_benchmark_gold_1309.csv"
OOD_CSV = SCRIPT_DIR / "SLU_benchmark_ood_excluded.csv"
MASTER_CSV = REPO_ROOT / "benchmark_curation" / "sap_commands_master.csv"
HTML_OUTPUT = SCRIPT_DIR / "SLU_benchmark_browser.html"



AUDITED_NOTES = {
    # 0042
    'SAP-CMD-0042': {'tag': 'Zero-Slot Media Play', 'type': 'info', 'text': "Utterance asks to \"play more like this\" (seed recommendation). Mapped to media_play with {} as the schema lacks a seed_reference slot."},
    # 0125
    'SAP-CMD-0125': {'tag': 'System Help / Emergency', 'type': 'warning', 'text': "\"Get help.\" is an assistant help/emergency request. Mapped to qa_search(query=\"get help\") due to lack of a system_help tool."},
    # 0130
    'SAP-CMD-0130': {'tag': 'Assistant Persona Easter Egg', 'type': 'warning', 'text': "\"Hey Google, sing me a song.\" is an assistant chitchat/persona easter egg shoehorned into qa_search."},
    # 0262-0278: App launches
    'SAP-CMD-0262': {'tag': 'Rule J Streaming Service', 'type': 'info', 'text': "\"Open Apple TV.\" maps to media_play(service=\"apple tv\") via Rule J streaming platform launch."},
    'SAP-CMD-0263': {'tag': 'Rule K OOD App Launch', 'type': 'info', 'text': "\"Open Atlas Obscura.\" excluded as 3rd-party mobile/web app launch without conversational tool."},
    'SAP-CMD-0264': {'tag': 'Rule K OOD App Launch', 'type': 'info', 'text': "\"Open Candy Crush Saga.\" excluded as 3rd-party game app launch."},
    'SAP-CMD-0265': {'tag': 'Rule J Streaming Service', 'type': 'info', 'text': "\"Open Disney Plus.\" maps to media_play(service=\"disney plus\") via Rule J streaming platform launch."},
    'SAP-CMD-0266': {'tag': 'Rule K OOD App Launch', 'type': 'info', 'text': "\"Open Duolingo.\" excluded as 3rd-party app launch."},
    'SAP-CMD-0267': {'tag': 'Core PIM Tool', 'type': 'info', 'text': "\"Open email.\" maps to email_manage(action=\"read\")."},
    'SAP-CMD-0268': {'tag': 'Communication Platform', 'type': 'info', 'text': "\"Open Facebook Messenger.\" maps to messages_manage(action=\"read\")."},
    'SAP-CMD-0269': {'tag': 'Rule K OOD App Launch', 'type': 'info', 'text': "\"Open Grammarly.\" excluded as 3rd-party utility app launch."},
    'SAP-CMD-0270': {'tag': 'Rule J Streaming Service', 'type': 'info', 'text': "\"Open Hulu.\" maps to media_play(service=\"hulu\") via Rule J streaming platform launch."},
    'SAP-CMD-0271': {'tag': 'Rule K OOD App Launch', 'type': 'info', 'text': "\"Open Microsoft Word.\" excluded as 3rd-party desktop app launch."},
    'SAP-CMD-0272': {'tag': 'Core PIM Tool', 'type': 'info', 'text': "\"Open my Outlook Calendar.\" maps to schedule_manage(action=\"query\")."},
    'SAP-CMD-0273': {'tag': 'Rule J Streaming Service', 'type': 'info', 'text': "\"Open Netflix.\" maps to media_play(service=\"netflix\") via Rule J streaming platform launch."},
    'SAP-CMD-0274': {'tag': 'Rule J Streaming Service', 'type': 'info', 'text': "\"Open Paramount Plus.\" maps to media_play(service=\"paramount plus\") via Rule J streaming platform launch."},
    'SAP-CMD-0275': {'tag': 'Rule J Streaming Service', 'type': 'info', 'text': "\"Open Peacock.\" maps to media_play(service=\"peacock\") via Rule J streaming platform launch."},
    'SAP-CMD-0276': {'tag': 'Communication Platform', 'type': 'info', 'text': "\"Open What's App.\" maps to messages_manage(action=\"read\")."},
    'SAP-CMD-0277': {'tag': 'Anomaly / OOD Candidate', 'type': 'danger', 'text': "\"Open Yelp.\" is mapped to places_search with {}. Unlike media streaming (Rule J), places_search lacks a service/app slot. Inconsistent with Atlas Obscura OOD."},
    'SAP-CMD-0278': {'tag': 'Rule J Streaming Service', 'type': 'info', 'text': "\"Open YouTube.\" maps to media_play(service=\"youtube\") via Rule J streaming platform launch."},
    # 0322 & 0334
    'SAP-CMD-0322': {'tag': 'Screen Reader / OOD Candidate', 'type': 'danger', 'text': "\"Read this page.\" is an assistive screen-reader / TTS reading command (e.g. TalkBack/VoiceOver), NOT an open-domain factual query. Shoehorned into qa_search."},
    'SAP-CMD-0328': {'tag': 'Slot Misclassification', 'type': 'warning', 'text': "\"Remind me to take a break in 15 minutes.\" extracted title=\"reminder\" and person=\"me\". Contrast with 0329-0332 which extract title=\"take a break\"."},
    'SAP-CMD-0334': {'tag': 'Camera Scanner / OOD Candidate', 'type': 'danger', 'text': "\"Scan a QR code.\" is a camera scanning utility command shoehorned into qa_search."},
    # 0526
    'SAP-CMD-0526': {'tag': 'Verified Sound (0-Slot Weather)', 'type': 'success', 'text': "\"What's it like outside?\" has {}. Validated sound: \"outside\" is an adverbial contrast, not a place entity. Retrieval defaults to device context."},
    # Punctuation fragments
    'SAP-CMD-0630': {'tag': 'Punctuation Dictation Fragment', 'type': 'warning', 'text': "\"Dear customer service, comma.\" is an isolated prompt fragment from continuous dictation (cf. 1138), mapped to email_manage(action=\"send\")."},
    'SAP-CMD-0674': {'tag': 'Punctuation Dictation Fragment', 'type': 'warning', 'text': "\"Hi, exclamation point.\" is an isolated dictation fragment (cf. 1139), mapped to messages_manage(action=\"send\")."},
    'SAP-CMD-0800': {'tag': 'Generic Title vs Event Topic', 'type': 'warning', 'text': "\"Set a reminder for Kristin's recital.\" extracted title=\"reminder\" and person=\"kristin\", dropping \"recital\". Contrast with 0335."},
    'SAP-CMD-0801': {'tag': 'Slot Misclassification', 'type': 'danger', 'text': "\"Set a reminder for Shak's holiday party.\" extracted person=\"shak's holiday party\". An event was extracted into person."},
    'SAP-CMD-0820': {'tag': 'Punctuation Dictation Fragment', 'type': 'info', 'text': "\"Thank you. Period.\" isolated into OOD as a dictation punctuation fragment."},
    'SAP-CMD-0821': {'tag': 'Punctuation Dictation Fragment', 'type': 'warning', 'text': "\"Thanks, exclamation point\" is an isolated dictation fragment (cf. 1139). Contrast with 0820 which was excluded to OOD."},
    # 0822 to 0829
    'SAP-CMD-0822': {'tag': 'Schema Limitation (Timer Label)', 'type': 'warning', 'text': "\"Timer for bread.\" has slots={\"action\": \"set\"}. alarm_manage lacks a title/label slot in Schema v1.0, dropping \"bread\"."},
    'SAP-CMD-0823': {'tag': 'Schema Limitation (Timer Label)', 'type': 'warning', 'text': "\"Timer for chicken.\" alarm_manage lacks a title/label slot; label \"chicken\" was dropped."},
    'SAP-CMD-0824': {'tag': 'Schema Limitation (Timer Label)', 'type': 'warning', 'text': "\"Timer for chili.\" alarm_manage lacks a title/label slot; label \"chili\" was dropped."},
    'SAP-CMD-0825': {'tag': 'Schema Limitation (Timer Label)', 'type': 'warning', 'text': "\"Timer for cookies.\" alarm_manage lacks a title/label slot; label \"cookies\" was dropped."},
    'SAP-CMD-0826': {'tag': 'Schema Limitation (Timer Label)', 'type': 'warning', 'text': "\"Timer for covid test.\" alarm_manage lacks a title/label slot; label \"covid test\" was dropped."},
    'SAP-CMD-0827': {'tag': 'Schema Limitation (Timer Label)', 'type': 'warning', 'text': "\"Timer for diabetes pill.\" alarm_manage lacks a title/label slot; label \"diabetes pill\" was dropped."},
    'SAP-CMD-0828': {'tag': 'Schema Limitation (Timer Label)', 'type': 'warning', 'text': "\"Timer for meditation.\" alarm_manage lacks a title/label slot; label \"meditation\" was dropped."},
    'SAP-CMD-0829': {'tag': 'Schema Limitation (Timer Label)', 'type': 'warning', 'text': "\"Timer for yogurt maker.\" alarm_manage lacks a title/label slot; label \"yogurt maker\" was dropped."},
    'SAP-CMD-0862': {'tag': 'Punctuation Dictation Fragment', 'type': 'warning', 'text': "\"What time will you be home, question mark.\" is an isolated dictation fragment (cf. 1139) with spoken punctuation."},
    # 1196 to 1203
    'SAP-CMD-1196': {'tag': 'Schema Limitation (Timer Label)', 'type': 'info', 'text': "\"baked chicken\" timer label was dropped because alarm_manage only models duration time."},
    'SAP-CMD-1197': {'tag': 'Schema Limitation (Timer Label)', 'type': 'info', 'text': "\"bread\" timer label was dropped because alarm_manage only models duration time."},
    'SAP-CMD-1198': {'tag': 'Schema Limitation (Timer Label)', 'type': 'info', 'text': "\"chili\" timer label was dropped because alarm_manage only models duration time."},
    'SAP-CMD-1199': {'tag': 'Schema Limitation (Timer Label)', 'type': 'info', 'text': "\"chocolate chip and walnut cookies\" timer label was dropped because alarm_manage only models duration time."},
    'SAP-CMD-1200': {'tag': 'Schema Limitation (Timer Label)', 'type': 'info', 'text': "\"COVID-19 test\" timer label was dropped because alarm_manage only models duration time."},
    'SAP-CMD-1201': {'tag': 'Schema Limitation (Timer Label)', 'type': 'info', 'text': "\"Marina's timeout\" timer label was dropped because alarm_manage only models duration time."},
    'SAP-CMD-1202': {'tag': 'Schema Limitation (Timer Label)', 'type': 'info', 'text': "\"osteoporosis pill\" timer label was dropped because alarm_manage only models duration time."},
    'SAP-CMD-1203': {'tag': 'Schema Limitation (Timer Label)', 'type': 'info', 'text': "\"yogurt maker\" timer label was dropped because alarm_manage only models duration time."},
    # 1219, 1220
    'SAP-CMD-1219': {'tag': 'Dictation Prefix Stripping', 'type': 'info', 'text': "\"Start listening. What's the weather for the weekend?\" had the dictation prefix stripped; routed to weather_query."},
    'SAP-CMD-1220': {'tag': 'Dictation Prefix Stripping', 'type': 'info', 'text': "\"Start listening. What's today's news?\" had the dictation prefix stripped; routed to qa_search."},
}
for i in range(631, 639):
    AUDITED_NOTES[f'SAP-CMD-{i:04d}'] = {'tag': 'Definition Prefix Inconsistency', 'type': 'info', 'text': "Utterance has \"Define [word]\". Retained \"define\" in query, whereas 0983-0987 stripped it."},
for i in range(980, 983):
    AUDITED_NOTES[f'SAP-CMD-{i:04d}'] = {'tag': 'Definition Prefix Inconsistency', 'type': 'info', 'text': "Utterance has \"Define [word]\". Retained \"define\" and single quotes in query, whereas 0983-0987 stripped them."},
for i in range(983, 988):
    AUDITED_NOTES[f'SAP-CMD-{i:04d}'] = {'tag': 'Definition Prefix Inconsistency', 'type': 'info', 'text': "Utterance has \"Define [word]\". Stripped \"define\" from query per carrier stripping, unlike 0631-0638."},


def generate_browser():
    with open(GOLD_CSV, mode="r", encoding="utf-8") as f:
        gold_rows = list(csv.DictReader(f))

    with open(OOD_CSV, mode="r", encoding="utf-8") as f:
        ood_rows = list(csv.DictReader(f))

    master_meta = {}
    if MASTER_CSV.exists():
        with open(MASTER_CSV, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                master_meta[r["id"]] = r

    # Combine into unified dataset
    all_commands = []
    
    for r in gold_rows:
        cid = r["id"]
        meta = master_meta.get(cid, {})
        slots = json.loads(r["slots_json"])
        all_commands.append({
            "id": cid,
            "prompt": r["prompt"],
            "status": "Canonical Gold",
            "domain": r["domain"],
            "intent": r["intent"],
            "slots": slots,
            "slots_str": json.dumps(slots, indent=2, ensure_ascii=False),
            "source": r["adjudication_source"],
            "notes": r["adjudication_notes"],
            "cohorts": meta.get("cohorts", "Universal"),
            "category": meta.get("category", "General"),
            "word_count": int(meta.get("word_count", len(r["prompt"].split()))),
            "is_ood": False,
            "audit": AUDITED_NOTES.get(cid, None)
        })

    for r in ood_rows:
        cid = r["id"]
        meta = master_meta.get(cid, {})
        all_commands.append({
            "id": cid,
            "prompt": r["prompt"],
            "status": "OOD Excluded",
            "domain": "out_of_domain",
            "intent": "ood_excluded",
            "slots": {},
            "slots_str": "{}",
            "source": "Out-Of-Domain Exclusion",
            "notes": r["exclusion_reason"],
            "cohorts": meta.get("cohorts", "Universal"),
            "category": meta.get("category", "Wake Phrases / OS / Broadcast"),
            "word_count": int(meta.get("word_count", len(r["prompt"].split()))),
            "is_ood": True,
            "audit": AUDITED_NOTES.get(cid, None)
        })

    # Sort numerically by ID
    all_commands.sort(key=lambda x: int(x["id"].replace("SAP-CMD-", "")))

    commands_json = json.dumps(all_commands, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SAP SLU Benchmark Explorer (1,309 Commands)</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: rgba(0, 0, 0, 0.05); }}
    ::-webkit-scrollbar-thumb {{ background: rgba(140, 140, 140, 0.3); border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: rgba(140, 140, 140, 0.5); }}
    .badge-accessibility {{ background-color: #fef3c7; color: #92400e; border: 1px solid #fde68a; }}
    .badge-calendar_alarm {{ background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }}
    .badge-communication {{ background-color: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }}
    .badge-general_qa {{ background-color: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }}
    .badge-health {{ background-color: #ccfbf1; color: #115e59; border: 1px solid #99f6e4; }}
    .badge-maps_places {{ background-color: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }}
    .badge-media {{ background-color: #ede9fe; color: #5b21b6; border: 1px solid #ddd6fe; }}
    .badge-notes_memory {{ background-color: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; }}
    .badge-smart_home {{ background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }}
    .badge-transport {{ background-color: #e0f2fe; color: #075985; border: 1px solid #bae6fd; }}
    .badge-out_of_domain {{ background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }}
  </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen font-sans flex flex-col antialiased">

  <!-- Header -->
  <header class="bg-slate-800/90 backdrop-blur border-b border-slate-700 sticky top-0 z-40 px-6 py-4 shadow-lg">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="bg-cyan-500/20 text-cyan-400 font-bold px-2.5 py-0.5 rounded text-xs tracking-wider uppercase border border-cyan-500/30">Schema v1.3</span>
          <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            SAP SLU Benchmark Explorer
            <span class="text-xs text-slate-400 font-normal px-2 py-0.5 rounded-full bg-slate-700">1,309 Spoken Commands</span>
          </h1>
        </div>
        <p class="text-xs text-slate-400 mt-1">Dual-Frontier Adjudicated Ground Truth for Dysarthric Speech Understanding</p>
      </div>

      <!-- Quick Switcher -->
      <div class="flex items-center gap-2">
        <button id="viewDeckBtn" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-cyan-600 text-white shadow-sm hover:bg-cyan-500 transition">Deck View (Flip)</button>
        <button id="viewTableBtn" class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition">Table View</button>
        <button id="exportCsvBtn" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 border border-slate-600 hover:bg-slate-700 transition">Export CSV</button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-6 py-6 flex-1 w-full flex flex-col gap-6">

    <!-- KPI Cards -->
    <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <div class="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/80 shadow-sm">
        <div class="text-slate-400 text-xs font-medium">Total Commands</div>
        <div class="text-xl font-extrabold text-white mt-1">1,309</div>
        <div class="text-[10px] text-cyan-400 mt-0.5">100% Audited</div>
      </div>
      <div class="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/80 shadow-sm">
        <div class="text-slate-400 text-xs font-medium">Canonical Gold</div>
        <div class="text-xl font-extrabold text-emerald-400 mt-1">{len(gold_rows)}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">97.3% Task Scope</div>
      </div>
      <div class="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/80 shadow-sm">
        <div class="text-slate-400 text-xs font-medium">OOD Excluded</div>
        <div class="text-xl font-extrabold text-amber-400 mt-1">{len(ood_rows)}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">Wake/OS/Intercom/Dictation</div>
      </div>
      <div class="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/80 shadow-sm">
        <div class="text-slate-400 text-xs font-medium">Unanimous Agreed</div>
        <div class="text-xl font-extrabold text-blue-400 mt-1">855</div>
        <div class="text-[10px] text-slate-400 mt-0.5">66.7% Exact Match</div>
      </div>
      <div class="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/80 shadow-sm">
        <div class="text-slate-400 text-xs font-medium">Adjudicated Rules</div>
        <div class="text-xl font-extrabold text-purple-400 mt-1">426</div>
        <div class="text-[10px] text-slate-400 mt-0.5">Rules A–K Applied</div>
      </div>
      <div class="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700/80 shadow-sm">
        <div class="text-slate-400 text-xs font-medium">Domains / Tools</div>
        <div class="text-xl font-extrabold text-indigo-400 mt-1">10 / 29</div>
        <div class="text-[10px] text-slate-400 mt-0.5">Canonical Ontology</div>
      </div>
    </section>

    <!-- Filters & Search Bar -->
    <section class="bg-slate-800/60 p-4 rounded-xl border border-slate-700/80 shadow-sm flex flex-col gap-3.5">
      <!-- Search row -->
      <div class="flex flex-col sm:flex-row gap-3 items-center">
        <div class="relative flex-1 w-full">
          <input type="text" id="searchInput" placeholder="Search commands, IDs, tools, or slot values (e.g. 'flight', 'SAP-CMD-0012', 'thermostat')..."
                 class="w-full bg-slate-900/90 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent">
          <svg class="w-4 h-4 text-slate-400 absolute left-3 top-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
        </div>
        <div class="text-xs text-slate-400 whitespace-nowrap" id="matchCounter">Showing 1,309 of 1,309</div>
      </div>

      <!-- Filter Pills -->
      <div class="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-700/60 text-xs">
        <span class="text-slate-400 font-medium mr-1">Status:</span>
        <button data-filter-status="all" class="status-btn active px-2.5 py-1 rounded-md bg-cyan-600 text-white">All (1309)</button>
        <button data-filter-status="gold" class="status-btn px-2.5 py-1 rounded-md bg-slate-700/60 text-slate-300 hover:bg-slate-700">Canonical Gold ({len(gold_rows)})</button>
        <button data-filter-status="ood" class="status-btn px-2.5 py-1 rounded-md bg-slate-700/60 text-slate-300 hover:bg-slate-700">OOD Excluded ({len(ood_rows)})</button>
        <button data-filter-status="unanimous" class="status-btn px-2.5 py-1 rounded-md bg-slate-700/60 text-slate-300 hover:bg-slate-700">Unanimous (855)</button>
        <button data-filter-status="adjudicated" class="status-btn px-2.5 py-1 rounded-md bg-slate-700/60 text-slate-300 hover:bg-slate-700">Adjudicated (426)</button>
        <button data-filter-status="audited" class="status-btn px-2.5 py-1 rounded-md bg-amber-950/80 text-amber-300 border border-amber-700/80 hover:bg-amber-900 font-medium">🔍 Audited / Flagged ({len([c for c in all_commands if c.get("audit")])})</button>
      </div>

      <!-- Domain filter row -->
      <div class="flex flex-wrap items-center gap-1.5 text-xs">
        <span class="text-slate-400 font-medium mr-1">Domain:</span>
        <button data-filter-domain="all" class="domain-btn active px-2 py-0.5 rounded bg-slate-700 text-white text-[11px]">All Domains</button>
        <button data-filter-domain="media" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">media</button>
        <button data-filter-domain="smart_home" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">smart_home</button>
        <button data-filter-domain="calendar_alarm" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">calendar_alarm</button>
        <button data-filter-domain="general_qa" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">general_qa</button>
        <button data-filter-domain="maps_places" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">maps_places</button>
        <button data-filter-domain="communication" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">communication</button>
        <button data-filter-domain="health" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">health</button>
        <button data-filter-domain="notes_memory" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">notes_memory</button>
        <button data-filter-domain="accessibility" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">accessibility</button>
        <button data-filter-domain="transport" class="domain-btn px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-white text-[11px]">transport</button>
      </div>
    </section>

    <!-- Deck View (Flashcard Flip) -->
    <section id="deckView" class="flex flex-col items-center">
      <div class="w-full max-w-3xl bg-slate-800 border border-slate-700 rounded-2xl p-7 shadow-xl flex flex-col gap-5">
        <!-- Top bar of card -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span id="cardId" class="text-sm font-mono font-bold text-cyan-400 bg-cyan-950/60 px-2.5 py-1 rounded border border-cyan-800/80">SAP-CMD-0001</span>
            <span id="cardStatusBadge" class="text-xs px-2.5 py-0.5 rounded-full font-medium bg-emerald-900/60 text-emerald-300 border border-emerald-700/60">Canonical Gold</span>
          </div>
          <div class="flex items-center gap-2 text-xs text-slate-400">
            <span id="cardIndex">Command 1 of 1,309</span>
          </div>
        </div>

        <!-- Prompt Text -->
        <div class="py-4">
          <div class="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-1">Spoken Dysarthric Utterance</div>
          <h2 id="cardPrompt" class="text-2xl font-bold text-white tracking-wide leading-snug">"Add this music to favorites."</h2>
        </div>

        <!-- Auditor / Review Note Box -->
        <div id="cardAuditBox" class="hidden p-3.5 rounded-xl border text-xs">
          <div class="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px] mb-1" id="cardAuditTag"></div>
          <div class="text-slate-200 leading-relaxed font-normal" id="cardAuditText"></div>
        </div>

        <!-- Annotation Details Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-slate-700/80">
          <div>
            <div class="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-1">Target Intent</div>
            <div class="flex items-center gap-2 mt-1">
              <span id="cardDomainBadge" class="badge-media text-xs font-semibold px-2 py-0.5 rounded">media</span>
              <span id="cardIntent" class="text-sm font-mono font-semibold text-slate-200">media_control</span>
            </div>
            
            <div class="mt-4">
              <div class="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-1">Adjudication Source & Rationale</div>
              <div id="cardNotes" class="text-xs text-slate-300 mt-1 bg-slate-900/60 p-2.5 rounded border border-slate-700/60 leading-relaxed">
                Unanimously agreed by Claude 3.5 Sonnet & GPT
              </div>
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs uppercase tracking-wider text-slate-500 font-semibold">Extracted Slots JSON</span>
              <button id="copyJsonBtn" class="text-[11px] text-cyan-400 hover:text-cyan-300 transition">Copy JSON</button>
            </div>
            <pre id="cardSlots" class="bg-slate-900 text-cyan-300 p-3 rounded-lg text-xs font-mono overflow-x-auto border border-slate-700/80 min-h-[110px]">{{}}</pre>
          </div>
        </div>

        <!-- Navigation Controls -->
        <div class="flex items-center justify-between pt-4 border-t border-slate-700/80 mt-2">
          <div class="flex items-center gap-2">
            <button id="prevBtn" class="px-4 py-2 rounded-lg bg-slate-700 text-white text-xs font-medium hover:bg-slate-600 transition flex items-center gap-1.5">
              <span>←</span> Previous
            </button>
            <button id="nextBtn" class="px-4 py-2 rounded-lg bg-cyan-600 text-white text-xs font-medium hover:bg-cyan-500 transition flex items-center gap-1.5">
              Next <span>→</span>
            </button>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-xs text-slate-400">Jump to:</span>
            <input type="number" id="jumpInput" min="1" max="1309" value="1"
                   class="w-16 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-center text-white focus:outline-none focus:ring-1 focus:ring-cyan-500">
            <button id="copyPromptBtn" class="px-3 py-1.5 rounded-lg bg-slate-700/60 text-slate-300 text-xs hover:bg-slate-700 transition">Copy Utterance</button>
          </div>
        </div>
      </div>
      <div class="text-[11px] text-slate-500 mt-2">Tip: Use Left / Right Arrow keys on your keyboard to flip through commands</div>
    </section>

    <!-- Table View -->
    <section id="tableView" class="hidden flex flex-col gap-3">
      <div class="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-900 text-slate-400 uppercase tracking-wider text-[11px] border-b border-slate-700">
              <tr>
                <th class="px-3.5 py-3 font-semibold">ID</th>
                <th class="px-4 py-3 font-semibold">Spoken Utterance</th>
                <th class="px-3 py-3 font-semibold">Domain</th>
                <th class="px-3 py-3 font-semibold">Tool Intent</th>
                <th class="px-4 py-3 font-semibold">Slots JSON</th>
                <th class="px-3 py-3 font-semibold">Status / Source</th>
                <th class="px-3 py-3 font-semibold text-right">Deck View</th>
              </tr>
            </thead>
            <tbody id="tableBody" class="divide-y divide-slate-700/60 text-slate-200">
              <!-- Dynamically rendered -->
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Table Pagination -->
      <div class="flex items-center justify-between text-xs text-slate-400 px-1">
        <div id="tablePageInfo">Showing 1 to 50 of 1,309</div>
        <div class="flex items-center gap-2">
          <button id="tablePrevBtn" class="px-3 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 disabled:opacity-40">Previous</button>
          <span id="tablePageNumbers" class="text-white font-medium">Page 1</span>
          <button id="tableNextBtn" class="px-3 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 disabled:opacity-40">Next</button>
        </div>
      </div>
    </section>

  </main>

  <!-- Toast Notification -->
  <div id="toast" class="fixed bottom-6 right-6 bg-slate-800 text-white text-xs px-4 py-2.5 rounded-lg border border-cyan-500/40 shadow-xl opacity-0 transition-opacity duration-300 pointer-events-none z-50">
    Copied to clipboard!
  </div>

  <script>
    const COMMANDS = {commands_json};
    let filteredCommands = [...COMMANDS];
    let currentIndex = 0;
    let tablePage = 1;
    const pageSize = 50;

    let currentStatusFilter = 'all';
    let currentDomainFilter = 'all';
    let currentSearch = '';

    // DOM Elements
    const searchInput = document.getElementById('searchInput');
    const matchCounter = document.getElementById('matchCounter');
    const statusBtns = document.querySelectorAll('.status-btn');
    const domainBtns = document.querySelectorAll('.domain-btn');

    const viewDeckBtn = document.getElementById('viewDeckBtn');
    const viewTableBtn = document.getElementById('viewTableBtn');
    const exportCsvBtn = document.getElementById('exportCsvBtn');

    const deckView = document.getElementById('deckView');
    const tableView = document.getElementById('tableView');

    // Deck Elements
    const cardId = document.getElementById('cardId');
    const cardStatusBadge = document.getElementById('cardStatusBadge');
    const cardIndex = document.getElementById('cardIndex');
    const cardPrompt = document.getElementById('cardPrompt');
    const cardAuditBox = document.getElementById('cardAuditBox');
    const cardAuditTag = document.getElementById('cardAuditTag');
    const cardAuditText = document.getElementById('cardAuditText');
    const cardDomainBadge = document.getElementById('cardDomainBadge');
    const cardIntent = document.getElementById('cardIntent');
    const cardNotes = document.getElementById('cardNotes');
    const cardSlots = document.getElementById('cardSlots');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const jumpInput = document.getElementById('jumpInput');
    const copyPromptBtn = document.getElementById('copyPromptBtn');
    const copyJsonBtn = document.getElementById('copyJsonBtn');

    // Table Elements
    const tableBody = document.getElementById('tableBody');
    const tablePageInfo = document.getElementById('tablePageInfo');
    const tablePrevBtn = document.getElementById('tablePrevBtn');
    const tableNextBtn = document.getElementById('tableNextBtn');
    const tablePageNumbers = document.getElementById('tablePageNumbers');
    const toast = document.getElementById('toast');

    function showToast(msg) {{
      toast.textContent = msg;
      toast.classList.remove('opacity-0');
      setTimeout(() => toast.classList.add('opacity-0'), 1800);
    }}

    function applyFilters() {{
      filteredCommands = COMMANDS.filter(cmd => {{
        // Status filter
        if (currentStatusFilter === 'gold' && cmd.is_ood) return false;
        if (currentStatusFilter === 'ood' && !cmd.is_ood) return false;
        if (currentStatusFilter === 'unanimous' && !cmd.source.includes('Unanimous')) return false;
        if (currentStatusFilter === 'adjudicated' && !cmd.source.includes('Adjudicated')) return false;
        if (currentStatusFilter === 'audited' && !cmd.audit) return false;

        // Domain filter
        if (currentDomainFilter !== 'all' && cmd.domain !== currentDomainFilter) return false;

        // Search text
        if (currentSearch) {{
          const q = currentSearch.toLowerCase();
          const matchPrompt = cmd.prompt.toLowerCase().includes(q);
          const matchId = cmd.id.toLowerCase().includes(q);
          const matchIntent = cmd.intent.toLowerCase().includes(q);
          const matchDomain = cmd.domain.toLowerCase().includes(q);
          const matchSlots = cmd.slots_str.toLowerCase().includes(q);
          if (!matchPrompt && !matchId && !matchIntent && !matchDomain && !matchSlots) return false;
        }}
        return true;
      }});

      matchCounter.textContent = `Showing ${{filteredCommands.length}} of 1,309`;
      currentIndex = 0;
      tablePage = 1;
      renderDeck();
      renderTable();
    }}

    function getDomainBadgeClass(domain) {{
      return `badge-${{domain}}`;
    }}

    function renderDeck() {{
      if (filteredCommands.length === 0) {{
        cardId.textContent = "N/A";
        cardPrompt.textContent = "No matching commands found.";
        cardSlots.textContent = "{{}}";
        cardIndex.textContent = "0 of 0";
        cardNotes.textContent = "Try broadening your search or filter.";
        return;
      }}

      const cmd = filteredCommands[currentIndex];
      cardId.textContent = cmd.id;
      cardPrompt.textContent = `"${{cmd.prompt}}"`;
      cardIndex.textContent = `Command ${{currentIndex + 1}} of ${{filteredCommands.length}}`;
      jumpInput.value = currentIndex + 1;
      jumpInput.max = filteredCommands.length;

      cardDomainBadge.textContent = cmd.domain;
      cardDomainBadge.className = `text-xs font-semibold px-2 py-0.5 rounded ${{getDomainBadgeClass(cmd.domain)}}`;
      cardIntent.textContent = cmd.intent;
      cardNotes.textContent = cmd.notes;
      cardSlots.textContent = cmd.slots_str;

      if (cmd.audit) {{
        cardAuditBox.classList.remove('hidden');
        cardAuditTag.textContent = `🔍 ${{cmd.audit.tag}}`;
        cardAuditText.textContent = cmd.audit.text;
        if (cmd.audit.type === 'danger') {{
          cardAuditBox.className = 'p-3.5 rounded-xl border border-rose-500/60 bg-rose-950/40 text-xs';
          cardAuditTag.className = 'flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px] mb-1 text-rose-300';
        }} else if (cmd.audit.type === 'warning') {{
          cardAuditBox.className = 'p-3.5 rounded-xl border border-amber-500/60 bg-amber-950/40 text-xs';
          cardAuditTag.className = 'flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px] mb-1 text-amber-300';
        }} else if (cmd.audit.type === 'success') {{
          cardAuditBox.className = 'p-3.5 rounded-xl border border-emerald-500/60 bg-emerald-950/40 text-xs';
          cardAuditTag.className = 'flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px] mb-1 text-emerald-300';
        }} else {{
          cardAuditBox.className = 'p-3.5 rounded-xl border border-cyan-500/60 bg-cyan-950/40 text-xs';
          cardAuditTag.className = 'flex items-center gap-1.5 font-bold uppercase tracking-wider text-[11px] mb-1 text-cyan-300';
        }}
      }} else {{
        cardAuditBox.classList.add('hidden');
      }}

      if (cmd.is_ood) {{
        cardStatusBadge.textContent = "OOD Excluded";
        cardStatusBadge.className = "text-xs px-2.5 py-0.5 rounded-full font-medium bg-amber-900/60 text-amber-300 border border-amber-700/60";
      }} else if (cmd.source.includes("Unanimous")) {{
        cardStatusBadge.textContent = "Unanimous Gold";
        cardStatusBadge.className = "text-xs px-2.5 py-0.5 rounded-full font-medium bg-blue-900/60 text-blue-300 border border-blue-700/60";
      }} else {{
        cardStatusBadge.textContent = "Adjudicated Gold";
        cardStatusBadge.className = "text-xs px-2.5 py-0.5 rounded-full font-medium bg-purple-900/60 text-purple-300 border border-purple-700/60";
      }}

      prevBtn.disabled = currentIndex === 0;
      nextBtn.disabled = currentIndex === filteredCommands.length - 1;
    }}

    function renderTable() {{
      const start = (tablePage - 1) * pageSize;
      const end = Math.min(start + pageSize, filteredCommands.length);
      const pageItems = filteredCommands.slice(start, end);

      tableBody.innerHTML = pageItems.map(cmd => `
        <tr class="hover:bg-slate-700/30 transition">
          <td class="px-3.5 py-2.5 font-mono font-medium whitespace-nowrap">
            <button onclick="selectCommand('${{cmd.id}}')" class="text-cyan-400 hover:text-cyan-300 hover:underline font-mono focus:outline-none" title="Inspect in Card Deck">
              ${{cmd.id}}
            </button>
          </td>
          <td class="px-4 py-2.5 font-medium text-white max-w-sm truncate select-text" title="${{cmd.prompt}}">${{cmd.prompt}}</td>
          <td class="px-3 py-2.5 whitespace-nowrap"><span class="px-2 py-0.5 rounded text-[11px] font-semibold ${{getDomainBadgeClass(cmd.domain)}}">${{cmd.domain}}</span></td>
          <td class="px-3 py-2.5 font-mono text-[11px] text-slate-300 whitespace-nowrap select-text">${{cmd.intent}}</td>
          <td class="px-4 py-2.5 font-mono text-[11px] text-cyan-300 truncate max-w-xs select-text" title="${{cmd.slots_str}}">${{JSON.stringify(cmd.slots)}}</td>
          <td class="px-3 py-2.5 whitespace-nowrap text-[11px]">
            <div class="flex items-center gap-1.5">
              <span class="px-2 py-0.5 rounded ${{cmd.is_ood ? 'bg-amber-950 text-amber-400' : 'bg-emerald-950 text-emerald-400'}}">${{cmd.is_ood ? 'OOD' : 'Gold'}}</span>
              ${{cmd.audit ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold ${{cmd.audit.type === 'danger' ? 'bg-rose-950 text-rose-300 border border-rose-700' : cmd.audit.type === 'warning' ? 'bg-amber-950 text-amber-300 border border-amber-700' : cmd.audit.type === 'success' ? 'bg-emerald-950 text-emerald-300 border border-emerald-700' : 'bg-cyan-950 text-cyan-300 border border-cyan-700'}}" title="${{cmd.audit.text}}">Audited</span>` : ''}}
            </div>
          </td>
          <td class="px-3 py-2.5 whitespace-nowrap text-right">
            <button onclick="selectCommand('${{cmd.id}}')" class="px-2.5 py-1 rounded bg-slate-700/80 hover:bg-cyan-600 text-slate-200 hover:text-white border border-slate-600/80 hover:border-cyan-500 text-[11px] font-medium transition inline-flex items-center gap-1 focus:outline-none" title="Open in Deck View">
              <span>Card</span> <span class="text-[10px]">↗</span>
            </button>
          </td>
        </tr>
      `).join('');

      tablePageInfo.textContent = `Showing ${{start + 1}} to ${{end}} of ${{filteredCommands.length}}`;
      tablePageNumbers.textContent = `Page ${{tablePage}} of ${{Math.max(1, Math.ceil(filteredCommands.length / pageSize))}}`;
      tablePrevBtn.disabled = tablePage === 1;
      tableNextBtn.disabled = end >= filteredCommands.length;
    }}

    window.selectCommand = function(cid) {{
      if (window.getSelection && window.getSelection().toString().trim().length > 0) {{
        return;
      }}
      const idx = filteredCommands.findIndex(c => c.id === cid);
      if (idx !== -1) {{
        currentIndex = idx;
        renderDeck();
        switchView('deck');
      }}
    }};

    function switchView(view) {{
      if (view === 'deck') {{
        deckView.classList.remove('hidden');
        tableView.classList.add('hidden');
        viewDeckBtn.className = "px-3.5 py-1.5 rounded-lg text-xs font-medium bg-cyan-600 text-white shadow-sm transition";
        viewTableBtn.className = "px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition";
      }} else {{
        deckView.classList.add('hidden');
        tableView.classList.remove('hidden');
        viewTableBtn.className = "px-3.5 py-1.5 rounded-lg text-xs font-medium bg-cyan-600 text-white shadow-sm transition";
        viewDeckBtn.className = "px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-700 text-slate-300 hover:bg-slate-600 transition";
      }}
    }}

    // Event Listeners
    searchInput.addEventListener('input', (e) => {{
      currentSearch = e.target.value.trim();
      applyFilters();
    }});

    statusBtns.forEach(btn => {{
      btn.addEventListener('click', () => {{
        statusBtns.forEach(b => {{
          b.classList.remove('bg-cyan-600', 'text-white', 'active');
          b.classList.add('bg-slate-700/60', 'text-slate-300');
        }});
        btn.classList.add('bg-cyan-600', 'text-white', 'active');
        btn.classList.remove('bg-slate-700/60', 'text-slate-300');
        currentStatusFilter = btn.dataset.filterStatus;
        applyFilters();
      }});
    }});

    domainBtns.forEach(btn => {{
      btn.addEventListener('click', () => {{
        domainBtns.forEach(b => {{
          b.classList.remove('bg-slate-700', 'text-white', 'active');
          b.classList.add('bg-slate-800', 'text-slate-400');
        }});
        btn.classList.add('bg-slate-700', 'text-white', 'active');
        btn.classList.remove('bg-slate-800', 'text-slate-400');
        currentDomainFilter = btn.dataset.filterDomain;
        applyFilters();
      }});
    }});

    prevBtn.addEventListener('click', () => {{
      if (currentIndex > 0) {{
        currentIndex--;
        renderDeck();
      }}
    }});

    nextBtn.addEventListener('click', () => {{
      if (currentIndex < filteredCommands.length - 1) {{
        currentIndex++;
        renderDeck();
      }}
    }});

    jumpInput.addEventListener('change', (e) => {{
      const val = parseInt(e.target.value, 10);
      if (val >= 1 && val <= filteredCommands.length) {{
        currentIndex = val - 1;
        renderDeck();
      }}
    }});

    document.addEventListener('keydown', (e) => {{
      if (document.activeElement === searchInput || document.activeElement === jumpInput) return;
      if (e.key === 'ArrowLeft' || e.key === 'k') prevBtn.click();
      if (e.key === 'ArrowRight' || e.key === 'j') nextBtn.click();
    }});

    viewDeckBtn.addEventListener('click', () => switchView('deck'));
    viewTableBtn.addEventListener('click', () => switchView('table'));

    tablePrevBtn.addEventListener('click', () => {{
      if (tablePage > 1) {{ tablePage--; renderTable(); }}
    }});
    tableNextBtn.addEventListener('click', () => {{
      if (tablePage * pageSize < filteredCommands.length) {{ tablePage++; renderTable(); }}
    }});

    copyPromptBtn.addEventListener('click', () => {{
      const cmd = filteredCommands[currentIndex];
      navigator.clipboard.writeText(cmd.prompt);
      showToast("Copied spoken utterance to clipboard!");
    }});

    copyJsonBtn.addEventListener('click', () => {{
      const cmd = filteredCommands[currentIndex];
      navigator.clipboard.writeText(cmd.slots_str);
      showToast("Copied JSON slots to clipboard!");
    }});

    exportCsvBtn.addEventListener('click', () => {{
      const headers = ["id", "prompt", "domain", "intent", "slots_json", "status", "source", "notes"];
      const rows = filteredCommands.map(c => [
        c.id,
        `"${{c.prompt.replace(/"/g, '""')}}"`,
        c.domain,
        c.intent,
        `"${{JSON.stringify(c.slots).replace(/"/g, '""')}}"`,
        c.status,
        `"${{c.source.replace(/"/g, '""')}}"`,
        `"${{c.notes.replace(/"/g, '""')}}"`
      ]);
      const csvStr = [headers.join(','), ...rows.map(r => r.join(','))].join('\\n');
      const blob = new Blob([csvStr], {{ type: 'text/csv;charset=utf-8;' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sap_slu_benchmark_filtered_${{filteredCommands.length}}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }});

    // Initialize
    applyFilters();
  </script>
</body>
</html>
"""

    with open(HTML_OUTPUT, mode="w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[OK] Successfully generated Visual Benchmark Explorer: {HTML_OUTPUT}")
    print(f"File size: {HTML_OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    generate_browser()
