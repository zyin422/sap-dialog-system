#!/usr/bin/env python3
"""
generate_frontier_browser.py

Generates a standalone, feature-rich interactive web browser for the 100 frontier
ambiguity commands in schema_freeze/frontier_sample_100.csv.
"""

import csv
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "schema_freeze" else SCRIPT_DIR
CSV_PATH = SCRIPT_DIR / "frontier_sample_100.csv"
HTML_OUTPUT = SCRIPT_DIR / "frontier_100_browser.html"


def generate_html():
    with open(CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    # Process and enrich rows
    commands = []
    for idx, r in enumerate(raw_rows, 1):
        tags = [t.strip() for t in r["ambiguity_tags"].split(";") if t.strip()]
        boundary_tags = [t for t in tags if t.startswith("boundary_")]
        linguistic_tags = [t for t in tags if not t.startswith("boundary_")]
        
        score = int(r["ambiguity_score"])
        words = r["prompt"].split()

        commands.append({
            "index": idx,
            "id": r["id"],
            "prompt": r["prompt"],
            "domain_quota": r["domain_quota"],
            "haiku_intent": r["haiku_intent"],
            "ambiguity_score": score,
            "ambiguity_tags": tags,
            "boundary_tags": boundary_tags,
            "linguistic_tags": linguistic_tags,
            "word_count": len(words),
            "char_count": len(r["prompt"]),
        })

    commands_json_str = json.dumps(commands, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Frontier 100 Ambiguity Explorer</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    ::-webkit-scrollbar {{
      width: 8px;
      height: 8px;
    }}
    ::-webkit-scrollbar-track {{
      background: rgba(0, 0, 0, 0.1);
    }}
    ::-webkit-scrollbar-thumb {{
      background: rgba(140, 140, 140, 0.3);
      border-radius: 4px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
      background: rgba(140, 140, 140, 0.5);
    }}
    .highlight {{
      background-color: rgba(234, 179, 8, 0.35);
      color: inherit;
      font-weight: 600;
      border-radius: 2px;
      padding: 0 2px;
    }}
    .score-6 {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
    .score-5 {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}
    .score-4 {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }}
    .score-3 {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.4); }}
  </style>
</head>
<body class="bg-[var(--background,#0b0f19)] text-[var(--foreground,#f1f5f9)] antialiased min-h-screen flex flex-col font-sans text-sm">

  <!-- Header -->
  <header class="bg-[var(--card,#131b2e)] border-b border-[var(--border,#1e293b)] px-6 py-4 shadow-sm sticky top-0 z-30">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="px-2.5 py-1 rounded-md text-xs font-bold tracking-wider uppercase bg-red-500/20 text-red-400 border border-red-500/30">Frontier 100 Benchmark</span>
          <h1 class="text-xl md:text-2xl font-bold tracking-tight text-[var(--foreground,#ffffff)]">Curated Frontier Commands Inspector</h1>
        </div>
        <p class="text-xs text-[var(--muted-foreground,#94a3b8)] mt-1">
          High-ambiguity edge case commands from <code class="text-sky-300 font-mono">frontier_sample_100.csv</code> testing SLU boundary conditions & slot disambiguation.
        </p>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <button id="btn-mode-deck" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 text-white shadow-sm flex items-center gap-1.5 transition">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
          Card Flip Deck
        </button>
        <button id="btn-mode-table" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--secondary,#1e293b)] hover:bg-[var(--border,#334155)] border border-[var(--border,#334155)] text-[var(--muted-foreground,#94a3b8)] hover:text-white flex items-center gap-1.5 transition">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16"/></svg>
          Table View
        </button>
        <button id="btn-export-csv" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--secondary,#1e293b)] hover:bg-[var(--border,#334155)] border border-[var(--border,#334155)] text-[var(--foreground,#f1f5f9)] flex items-center gap-1.5 transition">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          Export CSV
        </button>
      </div>
    </div>
  </header>

  <!-- Metrics Strip -->
  <section class="bg-[var(--card,#131b2e)]/50 border-b border-[var(--border,#1e293b)] px-6 py-3">
    <div class="max-w-7xl mx-auto grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Total Sampled</div>
        <div class="text-lg font-bold text-white">100 <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-normal">commands</span></div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Score 6 (Peak)</div>
        <div class="text-lg font-bold text-red-400">13 <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-normal">(13%)</span></div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Score 5 (High)</div>
        <div class="text-lg font-bold text-amber-400">60 <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-normal">(60%)</span></div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Score 4 (Medium)</div>
        <div class="text-lg font-bold text-blue-400">20 <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-normal">(20%)</span></div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Domain Quotas</div>
        <div class="text-lg font-bold text-emerald-400">9 <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-normal">domains</span></div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Haiku Intents</div>
        <div class="text-lg font-bold text-purple-400">16 <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-normal">intents</span></div>
      </div>
    </div>
  </section>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto w-full px-6 py-6 flex-1 flex flex-col gap-5">

    <!-- Interactive Inspection Deck View (Flip-Through Mode) -->
    <section id="deck-view-container" class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] rounded-2xl p-6 shadow-xl flex flex-col gap-6 relative">
      <div class="flex items-center justify-between border-b border-[var(--border,#1e293b)] pb-4">
        <div class="flex items-center gap-3">
          <span id="deck-counter" class="text-xs font-mono font-bold px-2.5 py-1 rounded bg-blue-600/20 text-blue-400 border border-blue-500/30">1 / 100</span>
          <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-mono">Original ID: <strong id="deck-id" class="text-white">650</strong></span>
        </div>
        
        <div class="flex items-center gap-2">
          <span id="deck-score-badge" class="px-3 py-1 rounded-full text-xs font-bold score-6">Score 6/6</span>
          <span class="text-xs text-[var(--muted-foreground,#94a3b8)] hidden sm:inline">(Use <kbd class="px-1.5 py-0.5 rounded bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] text-white">←</kbd> <kbd class="px-1.5 py-0.5 rounded bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] text-white">→</kbd> arrow keys)</span>
        </div>
      </div>

      <!-- Main Command Prompt Card -->
      <div class="bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] rounded-xl p-6 flex flex-col justify-between gap-4 shadow-inner">
        <div>
          <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2 flex items-center justify-between">
            <span>Uttered Voice Command</span>
            <button id="btn-deck-copy" class="text-blue-400 hover:text-blue-300 text-xs flex items-center gap-1 transition">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/></svg>
              Copy Prompt
            </button>
          </div>
          <p id="deck-prompt" class="text-xl md:text-2xl font-bold text-white leading-relaxed">
            "How many calories does 15 baby carrots and a scoop of hummus have?"
          </p>
        </div>

        <!-- Annotation & Classification Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-[var(--border,#1e293b)]/70">
          <div class="bg-[var(--card,#131b2e)]/60 border border-[var(--border,#1e293b)] rounded-lg p-3">
            <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] font-semibold uppercase">Domain Quota</div>
            <div id="deck-domain" class="text-base font-semibold text-amber-400 mt-0.5">general_qa</div>
          </div>
          <div class="bg-[var(--card,#131b2e)]/60 border border-[var(--border,#1e293b)] rounded-lg p-3">
            <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] font-semibold uppercase">Haiku Predicted Intent</div>
            <div id="deck-intent" class="text-base font-semibold text-purple-400 font-mono mt-0.5">qa_search</div>
          </div>
        </div>
      </div>

      <!-- Boundary & Ambiguity Tags -->
      <div>
        <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2">Ambiguity Dimensions & Boundary Triggers</div>
        <div id="deck-tags-container" class="flex flex-wrap gap-2">
          <!-- Populated by JS -->
        </div>
      </div>

      <!-- Deck Navigation Bar -->
      <div class="flex items-center justify-between pt-2 border-t border-[var(--border,#1e293b)]">
        <button id="btn-deck-prev" class="px-4 py-2 rounded-lg bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] border border-[var(--border,#1e293b)] text-white text-xs font-semibold flex items-center gap-2 transition disabled:opacity-30 disabled:cursor-not-allowed">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
          Previous Command
        </button>

        <div class="flex items-center gap-2">
          <input id="deck-jump-input" type="number" min="1" max="100" value="1" class="w-14 bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] text-center text-xs py-1.5 rounded text-white font-mono outline-none" />
          <span class="text-xs text-[var(--muted-foreground,#94a3b8)]">/ 100</span>
          <button id="btn-deck-jump" class="px-2.5 py-1.5 rounded bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] border border-[var(--border,#1e293b)] text-xs text-blue-400">Go</button>
        </div>

        <button id="btn-deck-next" class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-2 transition disabled:opacity-30 disabled:cursor-not-allowed">
          Next Command
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
        </button>
      </div>
    </section>

    <!-- Search & Filters Panel -->
    <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] rounded-xl p-4 shadow-sm flex flex-col gap-4">
      <!-- Search Input -->
      <div class="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div class="relative flex-1">
          <input
            id="table-search"
            type="text"
            placeholder="Search prompts, domains, intents, or tags (e.g. 'calories', 'meeting', 'timer', 'boundary_qa')..."
            class="w-full bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] focus:border-blue-500 rounded-lg px-4 py-2.5 pl-10 text-sm text-[var(--foreground,#f1f5f9)] placeholder-[var(--placeholder,#64748b)] outline-none transition"
          />
          <svg class="w-4 h-4 absolute left-3.5 top-3.5 text-[var(--muted-foreground,#94a3b8)]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <button id="btn-clear-search" class="hidden absolute right-3 top-3 text-[var(--muted-foreground,#94a3b8)] hover:text-white text-xs">✕</button>
        </div>

        <div class="flex items-center gap-2">
          <label class="text-xs text-[var(--muted-foreground,#94a3b8)]">Sort:</label>
          <select id="sort-select" class="bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] text-xs rounded-lg px-2.5 py-1.5 text-[var(--foreground,#f1f5f9)] outline-none cursor-pointer">
            <option value="original">Original Sample Order</option>
            <option value="score-desc">Ambiguity Score (Highest first)</option>
            <option value="score-asc">Ambiguity Score (Lowest first)</option>
            <option value="domain">Domain Quota</option>
            <option value="alpha">Alphabetical (A-Z)</option>
          </select>
        </div>
      </div>

      <!-- Filter Row 1: Ambiguity Score Badges -->
      <div>
        <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2">Filter by Ambiguity Score:</div>
        <div id="score-filters" class="flex flex-wrap gap-2">
          <button data-score="all" class="score-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-600 text-white border border-blue-500">All (100)</button>
          <button data-score="6" class="score-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-red-400 border border-[var(--border,#1e293b)]">Score 6 (13)</button>
          <button data-score="5" class="score-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-amber-400 border border-[var(--border,#1e293b)]">Score 5 (60)</button>
          <button data-score="4" class="score-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-blue-400 border border-[var(--border,#1e293b)]">Score 4 (20)</button>
          <button data-score="3" class="score-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-slate-300 border border-[var(--border,#1e293b)]">Score 3 (7)</button>
        </div>
      </div>

      <!-- Filter Row 2: Domain Quota -->
      <div>
        <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2">Filter by Domain Quota:</div>
        <div id="domain-filters" class="flex flex-wrap gap-1.5">
          <!-- Populated by JS -->
        </div>
      </div>

      <!-- Filter Row 3: Boundary Crossover Tags -->
      <div>
        <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2">Filter by Boundary Condition:</div>
        <div id="boundary-filters" class="flex flex-wrap gap-1.5">
          <!-- Populated by JS -->
        </div>
      </div>
    </div>

    <!-- Active Filters & Table Status -->
    <div class="flex items-center justify-between text-xs text-[var(--muted-foreground,#94a3b8)] px-1">
      <div class="flex items-center gap-2">
        <span>Showing <strong id="filter-count" class="text-white font-semibold">100</strong> of <strong class="text-white">100</strong> commands</span>
        <button id="btn-reset-filters" class="hidden text-blue-400 hover:text-blue-300 underline cursor-pointer ml-2">Reset filters</button>
      </div>
    </div>

    <!-- Table View Container -->
    <div id="table-view-container" class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] rounded-xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-[var(--background,#0b0f19)]/60 text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] border-b border-[var(--border,#1e293b)]">
              <th class="py-3 px-4 w-12 text-center">#</th>
              <th class="py-3 px-4 w-16">ID</th>
              <th class="py-3 px-4 w-24">Score</th>
              <th class="py-3 px-4 w-36">Domain Quota</th>
              <th class="py-3 px-4 w-44">Haiku Intent</th>
              <th class="py-3 px-4">Uttered Prompt</th>
              <th class="py-3 px-4 w-28 text-right">Action</th>
            </tr>
          </thead>
          <tbody id="table-body" class="divide-y divide-[var(--border,#1e293b)]/40 text-xs">
            <!-- Populated by JS -->
          </tbody>
        </table>
      </div>
    </div>
  </main>

  <!-- Toast Notification -->
  <div id="toast" class="hidden fixed bottom-6 right-6 z-50 bg-blue-600 text-white px-4 py-2.5 rounded-xl shadow-lg text-xs font-medium flex items-center gap-2">
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
    <span id="toast-msg">Copied prompt to clipboard!</span>
  </div>

  <script>
    const COMMANDS = {commands_json_str};

    let state = {{
      deckIndex: 0,
      search: "",
      score: "all",
      domain: "all",
      boundary: "all",
      sortBy: "original",
      activeMode: "deck"
    }};

    // DOM Elements
    const deckView = document.getElementById("deck-view-container");
    const tableView = document.getElementById("table-view-container");
    const btnModeDeck = document.getElementById("btn-mode-deck");
    const btnModeTable = document.getElementById("btn-mode-table");
    
    // Deck elements
    const deckCounter = document.getElementById("deck-counter");
    const deckId = document.getElementById("deck-id");
    const deckScoreBadge = document.getElementById("deck-score-badge");
    const deckPrompt = document.getElementById("deck-prompt");
    const deckDomain = document.getElementById("deck-domain");
    const deckIntent = document.getElementById("deck-intent");
    const deckTagsContainer = document.getElementById("deck-tags-container");
    const btnDeckPrev = document.getElementById("btn-deck-prev");
    const btnDeckNext = document.getElementById("btn-deck-next");
    const btnDeckCopy = document.getElementById("btn-deck-copy");
    const deckJumpInput = document.getElementById("deck-jump-input");
    const btnDeckJump = document.getElementById("btn-deck-jump");

    // Table & Filter elements
    const tableSearch = document.getElementById("table-search");
    const btnClearSearch = document.getElementById("btn-clear-search");
    const sortSelect = document.getElementById("sort-select");
    const domainFiltersContainer = document.getElementById("domain-filters");
    const boundaryFiltersContainer = document.getElementById("boundary-filters");
    const scoreBtns = document.querySelectorAll(".score-btn");
    const filterCountEl = document.getElementById("filter-count");
    const btnResetFilters = document.getElementById("btn-reset-filters");
    const tableBody = document.getElementById("table-body");
    const btnExportCsv = document.getElementById("btn-export-csv");

    function initFilterPills() {{
      // Domain counts
      const domCounts = {{}};
      const bndCounts = {{}};
      COMMANDS.forEach(c => {{
        domCounts[c.domain_quota] = (domCounts[c.domain_quota] || 0) + 1;
        c.boundary_tags.forEach(b => {{
          bndCounts[b] = (bndCounts[b] || 0) + 1;
        }});
      }});

      // Domains
      let domHtml = `<button data-domain="all" class="dom-btn px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500">All (100)</button>`;
      for (const [dom, cnt] of Object.entries(domCounts)) {{
        domHtml += `<button data-domain="${{dom}}" class="dom-btn px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">${{dom}} (${{cnt}})</button>`;
      }}
      domainFiltersContainer.innerHTML = domHtml;

      // Boundaries
      let bndHtml = `<button data-boundary="all" class="bnd-btn px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500">All Boundaries</button>`;
      for (const [bnd, cnt] of Object.entries(bndCounts)) {{
        bndHtml += `<button data-boundary="${{bnd}}" class="bnd-btn px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-red-300 border border-[var(--border,#1e293b)]">${{bnd.replace('boundary_', '')}} (${{cnt}})</button>`;
      }}
      boundaryFiltersContainer.innerHTML = bndHtml;

      // Add listeners
      document.querySelectorAll(".dom-btn").forEach(btn => {{
        btn.addEventListener("click", () => {{
          state.domain = btn.getAttribute("data-domain");
          updateFilterStyles();
          renderTable();
        }});
      }});

      document.querySelectorAll(".bnd-btn").forEach(btn => {{
        btn.addEventListener("click", () => {{
          state.boundary = btn.getAttribute("data-boundary");
          updateFilterStyles();
          renderTable();
        }});
      }});
    }}

    function updateFilterStyles() {{
      // Scores
      scoreBtns.forEach(btn => {{
        const isSel = btn.getAttribute("data-score") === state.score;
        btn.className = isSel
          ? "score-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-600 text-white border border-blue-500"
          : "score-btn px-2.5 py-1 rounded-md text-xs font-semibold bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]";
      }});

      // Domains
      document.querySelectorAll(".dom-btn").forEach(btn => {{
        const isSel = btn.getAttribute("data-domain") === state.domain;
        btn.className = isSel
          ? "dom-btn px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500"
          : "dom-btn px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]";
      }});

      // Boundaries
      document.querySelectorAll(".bnd-btn").forEach(btn => {{
        const isSel = btn.getAttribute("data-boundary") === state.boundary;
        btn.className = isSel
          ? "bnd-btn px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500"
          : "bnd-btn px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-red-300 border border-[var(--border,#1e293b)]";
      }});

      const hasFilters = state.search || state.score !== "all" || state.domain !== "all" || state.boundary !== "all";
      btnResetFilters.classList.toggle("hidden", !hasFilters);
      btnClearSearch.classList.toggle("hidden", !state.search);
    }}

    function filterCommands() {{
      const q = state.search.toLowerCase().trim();
      let res = COMMANDS.filter(c => {{
        if (state.score !== "all" && c.ambiguity_score !== parseInt(state.score, 10)) return false;
        if (state.domain !== "all" && c.domain_quota !== state.domain) return false;
        if (state.boundary !== "all" && !c.boundary_tags.includes(state.boundary)) return false;
        if (q) {{
          const inPrompt = c.prompt.toLowerCase().includes(q);
          const inDomain = c.domain_quota.toLowerCase().includes(q);
          const inIntent = c.haiku_intent.toLowerCase().includes(q);
          const inTags = c.ambiguity_tags.some(t => t.toLowerCase().includes(q));
          const inId = c.id.includes(q);
          if (!inPrompt && !inDomain && !inIntent && !inTags && !inId) return false;
        }}
        return true;
      }});

      if (state.sortBy === "score-desc") {{
        res.sort((a, b) => b.ambiguity_score - a.ambiguity_score || a.index - b.index);
      }} else if (state.sortBy === "score-asc") {{
        res.sort((a, b) => a.ambiguity_score - b.ambiguity_score || a.index - b.index);
      }} else if (state.sortBy === "domain") {{
        res.sort((a, b) => a.domain_quota.localeCompare(b.domain_quota) || a.index - b.index);
      }} else if (state.sortBy === "alpha") {{
        res.sort((a, b) => a.prompt.localeCompare(b.prompt));
      }} else {{
        res.sort((a, b) => a.index - b.index);
      }}

      return res;
    }}

    function renderDeck() {{
      const cur = COMMANDS[state.deckIndex];
      if (!cur) return;

      deckCounter.textContent = `${{cur.index}} / 100`;
      deckId.textContent = cur.id;
      deckJumpInput.value = cur.index;

      // Score badge
      deckScoreBadge.className = `px-3 py-1 rounded-full text-xs font-bold score-${{cur.ambiguity_score}}`;
      deckScoreBadge.textContent = `Score ${{cur.ambiguity_score}}/6 Ambiguity`;

      deckPrompt.textContent = `"${{cur.prompt}}"`;
      deckDomain.textContent = cur.domain_quota;
      deckIntent.textContent = cur.haiku_intent;

      // Tags
      let tagsHtml = "";
      cur.boundary_tags.forEach(t => {{
        tagsHtml += `<span class="px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-red-500/15 text-red-400 border border-red-500/30">⚡ ${{t}}</span>`;
      }});
      cur.linguistic_tags.forEach(t => {{
        tagsHtml += `<span class="px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-blue-500/15 text-blue-300 border border-blue-500/30">${{t}}</span>`;
      }});
      deckTagsContainer.innerHTML = tagsHtml;

      btnDeckPrev.disabled = state.deckIndex <= 0;
      btnDeckNext.disabled = state.deckIndex >= COMMANDS.length - 1;
    }}

    function renderTable() {{
      const filtered = filterCommands();
      filterCountEl.textContent = filtered.length;

      let html = "";
      const q = state.search.toLowerCase().trim();

      filtered.forEach(c => {{
        const scoreClass = `score-${{c.ambiguity_score}}`;
        html += `
          <tr class="hover:bg-[var(--background,#0b0f19)]/60 transition cursor-pointer" onclick="jumpToDeckItem(${{c.index - 1}})">
            <td class="py-3 px-4 text-center font-mono text-[var(--muted-foreground,#94a3b8)]">${{c.index}}</td>
            <td class="py-3 px-4 font-mono text-[var(--muted-foreground,#94a3b8)]">${{c.id}}</td>
            <td class="py-3 px-4">
              <span class="px-2 py-0.5 rounded text-[11px] font-bold ${{scoreClass}}">Score ${{c.ambiguity_score}}</span>
            </td>
            <td class="py-3 px-4">
              <span class="text-amber-400 font-medium">${{c.domain_quota}}</span>
            </td>
            <td class="py-3 px-4">
              <span class="text-purple-400 font-mono text-[11px]">${{c.haiku_intent}}</span>
            </td>
            <td class="py-3 px-4 text-white font-medium leading-relaxed">
              ${{escapeHtml(c.prompt)}}
              <div class="flex flex-wrap gap-1 mt-1">
                ${{c.boundary_tags.map(b => `<span class="px-1.5 py-0.2 rounded text-[10px] bg-red-500/15 text-red-300 font-mono">${{b.replace('boundary_', '')}}</span>`).join('')}}
              </div>
            </td>
            <td class="py-3 px-4 text-right" onclick="event.stopPropagation()">
              <button onclick="copyPrompt('${{escapeHtml(c.prompt)}}')" title="Copy prompt" class="p-1.5 rounded hover:bg-[var(--border,#334155)] text-[var(--muted-foreground,#94a3b8)] hover:text-white transition">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/></svg>
              </button>
            </td>
          </tr>
        `;
      }});
      tableBody.innerHTML = html;
    }}

    function jumpToDeckItem(idx) {{
      state.deckIndex = idx;
      renderDeck();
      deckView.scrollIntoView({{ behavior: "smooth" }});
    }}

    function escapeHtml(str) {{
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, '&quot;');
    }}

    function showToast(msg) {{
      const t = document.getElementById("toast");
      document.getElementById("toast-msg").textContent = msg;
      t.classList.remove("hidden");
      setTimeout(() => t.classList.add("hidden"), 2000);
    }}

    function copyPrompt(text) {{
      navigator.clipboard.writeText(text).then(() => {{
        showToast("Copied prompt to clipboard!");
      }});
    }}

    function resetFilters() {{
      state.search = "";
      state.score = "all";
      state.domain = "all";
      state.boundary = "all";
      tableSearch.value = "";
      updateFilterStyles();
      renderTable();
    }}

    function exportCSV() {{
      const filtered = filterCommands();
      const headers = ["id", "prompt", "domain_quota", "haiku_intent", "ambiguity_score", "ambiguity_tags"];
      const lines = [headers.join(",")];
      filtered.forEach(c => {{
        lines.push([
          c.id,
          `"${{c.prompt.replace(/"/g, '""')}}"`,
          c.domain_quota,
          c.haiku_intent,
          c.ambiguity_score,
          `"${{c.ambiguity_tags.join('; ')}}"`
        ].join(","));
      }});
      const blob = new Blob([lines.join("\\n")], {{ type: "text/csv;charset=utf-8;" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `frontier_sample_${{filtered.length}}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`Exported ${{filtered.length}} commands to CSV!`);
    }}

    // Event Listeners
    btnDeckPrev.addEventListener("click", () => {{
      if (state.deckIndex > 0) {{
        state.deckIndex--;
        renderDeck();
      }}
    }});

    btnDeckNext.addEventListener("click", () => {{
      if (state.deckIndex < COMMANDS.length - 1) {{
        state.deckIndex++;
        renderDeck();
      }}
    }});

    btnDeckCopy.addEventListener("click", () => {{
      copyPrompt(COMMANDS[state.deckIndex].prompt);
    }});

    btnDeckJump.addEventListener("click", () => {{
      const val = parseInt(deckJumpInput.value, 10);
      if (val >= 1 && val <= 100) {{
        state.deckIndex = val - 1;
        renderDeck();
      }}
    }});

    deckJumpInput.addEventListener("keydown", (e) => {{
      if (e.key === "Enter") btnDeckJump.click();
    }});

    window.addEventListener("keydown", (e) => {{
      if (document.activeElement === tableSearch || document.activeElement === deckJumpInput) return;
      if (e.key === "ArrowLeft") {{
        btnDeckPrev.click();
      }} else if (e.key === "ArrowRight") {{
        btnDeckNext.click();
      }}
    }});

    tableSearch.addEventListener("input", (e) => {{
      state.search = e.target.value;
      updateFilterStyles();
      renderTable();
    }});

    btnClearSearch.addEventListener("click", () => {{
      state.search = "";
      tableSearch.value = "";
      updateFilterStyles();
      renderTable();
    }});

    sortSelect.addEventListener("change", (e) => {{
      state.sortBy = e.target.value;
      renderTable();
    }});

    scoreBtns.forEach(btn => {{
      btn.addEventListener("click", () => {{
        state.score = btn.getAttribute("data-score");
        updateFilterStyles();
        renderTable();
      }});
    }});

    btnResetFilters.addEventListener("click", resetFilters);
    btnExportCsv.addEventListener("click", exportCSV);

    btnModeDeck.addEventListener("click", () => {{
      deckView.scrollIntoView({{ behavior: "smooth" }});
    }});

    btnModeTable.addEventListener("click", () => {{
      tableView.scrollIntoView({{ behavior: "smooth" }});
    }});

    // Initialize
    initFilterPills();
    renderDeck();
    renderTable();
  </script>
</body>
</html>
"""

    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Generated Frontier 100 visual browser at {HTML_OUTPUT}")


if __name__ == "__main__":
    generate_html()
