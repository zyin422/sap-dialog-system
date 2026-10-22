#!/usr/bin/env python3
"""
generate_html_browser.py

Generates a standalone, fully-featured interactive HTML browser for the ~1,300 SAP
voice commands dataset.
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "benchmark_curation" else SCRIPT_DIR
JSON_PATH = SCRIPT_DIR / "sap_commands_master.json"
HTML_OUTPUT = SCRIPT_DIR / "sap_commands_browser.html"


def generate_html():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data["metadata"]
    commands = data["commands"]

    # Pre-encode JSON for script embedding
    commands_json_str = json.dumps(commands, ensure_ascii=False)
    stats_json_str = json.dumps(metadata.get("stats", {}), ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SAP Voice Commands Explorer (~1,300 Prompts)</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    /* Custom scrollbar and modal transitions */
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
      background-color: rgba(234, 179, 8, 0.3);
      color: inherit;
      font-weight: 600;
      border-radius: 2px;
      padding: 0 2px;
    }}
    .badge-pd {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
    .badge-ds {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
    .badge-stroke {{ background: rgba(236, 72, 153, 0.15); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.3); }}
    .badge-univ {{ background: rgba(16, 185, 129, 0.18); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }}
  </style>
</head>
<body class="bg-[var(--background,#0b0f19)] text-[var(--foreground,#f1f5f9)] antialiased min-h-screen flex flex-col font-sans text-sm">

  <!-- Header -->
  <header class="bg-[var(--card,#131b2e)] border-b border-[var(--border,#1e293b)] px-6 py-4 shadow-sm sticky top-0 z-30">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="px-2.5 py-1 rounded-md text-xs font-bold tracking-wider uppercase bg-blue-600/20 text-blue-400 border border-blue-500/30">SAP Dataset</span>
          <h1 class="text-xl md:text-2xl font-bold tracking-tight text-[var(--foreground,#ffffff)]">Speech Accessibility Project — Voice Commands Explorer</h1>
        </div>
        <p class="text-xs text-[var(--muted-foreground,#94a3b8)] mt-1">
          Interactive catalog of <span class="font-semibold text-blue-400" id="header-total-count">1,309</span> unique commands across Parkinson's/ALS, Down syndrome/CP, and Stroke cohorts (<a href="https://github.com/speechaccessibility/PromptsAnnotationGuidelines" target="_blank" class="underline hover:text-blue-300">speechaccessibility/PromptsAnnotationGuidelines</a>).
        </p>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <button id="btn-export-json" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--secondary,#1e293b)] hover:bg-[var(--border,#334155)] border border-[var(--border,#334155)] transition-colors flex items-center gap-1.5 text-[var(--foreground,#f1f5f9)]">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          Export JSON
        </button>
        <button id="btn-export-csv" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--secondary,#1e293b)] hover:bg-[var(--border,#334155)] border border-[var(--border,#334155)] transition-colors flex items-center gap-1.5 text-[var(--foreground,#f1f5f9)]">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          Export CSV
        </button>
        <button id="btn-copy-filtered" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--secondary,#1e293b)] hover:bg-[var(--border,#334155)] border border-[var(--border,#334155)] transition-colors flex items-center gap-1.5 text-[var(--foreground,#f1f5f9)]">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/></svg>
          Copy Prompts
        </button>
        <button id="btn-random-pick" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors flex items-center gap-1.5 shadow-sm">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
          Random Pick
        </button>
      </div>
    </div>
  </header>

  <!-- Metrics Bar -->
  <section class="bg-[var(--card,#131b2e)]/50 border-b border-[var(--border,#1e293b)] px-6 py-3">
    <div class="max-w-7xl mx-auto grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Total Commands</div>
        <div class="text-lg font-bold text-blue-400">1,309</div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Universal B1/B10</div>
        <div class="text-lg font-bold text-emerald-400">35 <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-normal">(100% read)</span></div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">All 3 Cohorts</div>
        <div class="text-lg font-bold text-purple-400">583 <span class="text-xs text-[var(--muted-foreground,#94a3b8)] font-normal">(shared)</span></div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">PD / ALS Cohort</div>
        <div class="text-lg font-bold text-sky-400">912</div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">DS / CP Cohort</div>
        <div class="text-lg font-bold text-violet-400">957</div>
      </div>
      <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] p-2.5 rounded-lg">
        <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Stroke Cohort</div>
        <div class="text-lg font-bold text-pink-400">958</div>
      </div>
    </div>
  </section>

  <!-- Main Content Layout -->
  <main class="max-w-7xl mx-auto w-full px-6 py-6 flex-1 flex flex-col gap-5">

    <!-- Search & Filter Controls -->
    <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] rounded-xl p-4 shadow-sm flex flex-col gap-4">
      
      <!-- Top Row: Full-text Search & Quick Toggles -->
      <div class="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div class="relative flex-1">
          <input
            id="search-input"
            type="text"
            placeholder="Search commands (e.g. 'alarm', 'temperature', 'remind me', 'text', 'play')..."
            class="w-full bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] focus:border-blue-500 rounded-lg px-4 py-2.5 pl-10 text-sm text-[var(--foreground,#f1f5f9)] placeholder-[var(--placeholder,#64748b)] outline-none transition"
          />
          <svg class="w-4 h-4 absolute left-3.5 top-3.5 text-[var(--muted-foreground,#94a3b8)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
          <button id="btn-clear-search" class="hidden absolute right-3 top-3 text-[var(--muted-foreground,#94a3b8)] hover:text-white text-xs">
            ✕
          </button>
        </div>

        <div class="flex items-center gap-3 flex-wrap">
          <div class="flex items-center gap-2 bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] rounded-lg px-3 py-1.5">
            <input type="checkbox" id="chk-exclude-wake" class="rounded border-gray-700 text-blue-600 focus:ring-0 cursor-pointer" />
            <label for="chk-exclude-wake" class="text-xs cursor-pointer select-none text-[var(--muted-foreground,#94a3b8)] hover:text-white">Hide Standalone Wake Phrases</label>
          </div>

          <div class="flex items-center gap-2">
            <label class="text-xs text-[var(--muted-foreground,#94a3b8)]">Sort:</label>
            <select id="sort-select" class="bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] text-xs rounded-lg px-2.5 py-1.5 text-[var(--foreground,#f1f5f9)] outline-none cursor-pointer">
              <option value="default">Default (Universal first, then shared)</option>
              <option value="alpha-asc">Alphabetical (A → Z)</option>
              <option value="alpha-desc">Alphabetical (Z → A)</option>
              <option value="category">Category</option>
              <option value="words-asc">Word count (Shortest first)</option>
              <option value="words-desc">Word count (Longest first)</option>
            </select>
          </div>

          <div class="flex items-center bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)] rounded-lg p-0.5">
            <button id="view-table-btn" class="px-2.5 py-1 rounded text-xs font-medium bg-blue-600 text-white transition">Table</button>
            <button id="view-grid-btn" class="px-2.5 py-1 rounded text-xs font-medium text-[var(--muted-foreground,#94a3b8)] hover:text-white transition">Cards</button>
          </div>
        </div>
      </div>

      <!-- Filter Row 1: Categories / Functional Domains -->
      <div>
        <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2">Filter by Category / Functional Domain:</div>
        <div id="category-pills" class="flex flex-wrap gap-1.5">
          <!-- Populated by JS -->
        </div>
      </div>

      <!-- Filter Row 2: Cohorts & Block Types -->
      <div class="flex flex-col md:flex-row gap-4 pt-2 border-t border-[var(--border,#1e293b)]/70">
        <div class="flex-1">
          <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2">Clinical Cohort:</div>
          <div id="cohort-pills" class="flex flex-wrap gap-1.5">
            <button data-cohort="all" class="cohort-pill px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500">All Cohorts</button>
            <button data-cohort="all3" class="cohort-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">All 3 Cohorts (583)</button>
            <button data-cohort="PD" class="cohort-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">Parkinson's/ALS (912)</button>
            <button data-cohort="DS" class="cohort-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">Down Syndrome/CP (957)</button>
            <button data-cohort="Stroke" class="cohort-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">Stroke (958)</button>
          </div>
        </div>

        <div>
          <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2">Schedule / Block:</div>
          <div id="block-pills" class="flex flex-wrap gap-1.5">
            <button data-block="all" class="block-pill px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500">All Prompts</button>
            <button data-block="univ" class="block-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">★ Universal Core (B1 & B10)</button>
            <button data-block="rotat" class="block-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">Rotation Lists (B2–B9)</button>
          </div>
        </div>

        <div>
          <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-2">Length:</div>
          <div id="length-pills" class="flex flex-wrap gap-1.5">
            <button data-len="all" class="len-pill px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500">All</button>
            <button data-len="short" class="len-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">Short (1-3w)</button>
            <button data-len="medium" class="len-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">Medium (4-7w)</button>
            <button data-len="long" class="len-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">Long (8+w)</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Active Filters & Count Status Bar -->
    <div class="flex items-center justify-between text-xs text-[var(--muted-foreground,#94a3b8)] px-1">
      <div class="flex items-center gap-2">
        <span>Showing <strong id="filter-count" class="text-white font-semibold">1,309</strong> of <strong class="text-white">1,309</strong> commands</span>
        <button id="btn-reset-filters" class="hidden text-blue-400 hover:text-blue-300 underline cursor-pointer ml-2">Reset all filters</button>
      </div>

      <div class="flex items-center gap-2">
        <span>Items per page:</span>
        <select id="page-size-select" class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] text-xs rounded px-2 py-0.5 text-[var(--foreground,#f1f5f9)] outline-none">
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="250">250</option>
          <option value="1309">All (1,309)</option>
        </select>
      </div>
    </div>

    <!-- Content Views -->
    <div id="table-view-container" class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] rounded-xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-[var(--background,#0b0f19)]/60 text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] border-b border-[var(--border,#1e293b)]">
              <th class="py-3 px-4 w-28">ID</th>
              <th class="py-3 px-4 w-28">Type</th>
              <th class="py-3 px-4 w-36">Cohorts</th>
              <th class="py-3 px-4 w-44">Category / Domain</th>
              <th class="py-3 px-4">Prompt Text</th>
              <th class="py-3 px-4 w-20 text-center">Words</th>
              <th class="py-3 px-4 w-24 text-right">Actions</th>
            </tr>
          </thead>
          <tbody id="table-body" class="divide-y divide-[var(--border,#1e293b)]/40 text-xs">
            <!-- Populated by JS -->
          </tbody>
        </table>
      </div>
    </div>

    <div id="grid-view-container" class="hidden grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- Populated by JS -->
    </div>

    <!-- Empty State -->
    <div id="empty-state" class="hidden bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] rounded-xl p-12 text-center">
      <svg class="w-12 h-12 mx-auto text-[var(--muted-foreground,#94a3b8)] mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      <div class="text-base font-semibold text-white">No commands found</div>
      <p class="text-xs text-[var(--muted-foreground,#94a3b8)] mt-1">Try adjusting your search query or relaxing category/cohort filters.</p>
      <button onclick="resetAllFilters()" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium">Clear All Filters</button>
    </div>

    <!-- Pagination Controls -->
    <div id="pagination-controls" class="flex items-center justify-between text-xs text-[var(--muted-foreground,#94a3b8)] py-2">
      <div id="page-info">Page 1 of 1</div>
      <div class="flex items-center gap-1.5">
        <button id="btn-prev-page" class="px-3 py-1.5 rounded bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] hover:bg-[var(--border,#1e293b)] disabled:opacity-40 disabled:cursor-not-allowed">Previous</button>
        <span id="page-buttons" class="flex items-center gap-1"></span>
        <button id="btn-next-page" class="px-3 py-1.5 rounded bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] hover:bg-[var(--border,#1e293b)] disabled:opacity-40 disabled:cursor-not-allowed">Next</button>
      </div>
    </div>
  </main>

  <!-- Detail Inspector Modal -->
  <div id="detail-modal" class="hidden fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
    <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
      <div class="px-6 py-4 border-b border-[var(--border,#1e293b)] flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span id="modal-id" class="px-2.5 py-1 rounded text-xs font-mono font-bold bg-blue-600/20 text-blue-400 border border-blue-500/30">SAP-CMD-0001</span>
          <span id="modal-type-badge" class="px-2 py-0.5 rounded text-xs font-medium badge-univ">★ Universal</span>
        </div>
        <button id="btn-close-modal" class="text-[var(--muted-foreground,#94a3b8)] hover:text-white p-1 rounded-lg">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="px-6 py-5 overflow-y-auto space-y-5">
        <div>
          <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-1">Command Prompt Text</div>
          <div class="flex items-start justify-between gap-3 bg-[var(--background,#0b0f19)] p-4 rounded-xl border border-[var(--border,#1e293b)]">
            <div id="modal-text" class="text-base font-semibold text-white"></div>
            <button id="btn-copy-modal-text" class="px-2.5 py-1.5 rounded-md text-xs bg-[var(--card,#131b2e)] hover:bg-[var(--border,#1e293b)] text-blue-400 border border-[var(--border,#1e293b)] flex-shrink-0 transition">
              Copy
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-[var(--background,#0b0f19)] p-3 rounded-lg border border-[var(--border,#1e293b)]">
            <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Functional Domain</div>
            <div id="modal-category" class="font-medium text-amber-400 mt-0.5">Tasks and planning</div>
          </div>
          <div class="bg-[var(--background,#0b0f19)] p-3 rounded-lg border border-[var(--border,#1e293b)]">
            <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Canonical Tool Candidate</div>
            <div id="modal-tool" class="font-mono text-xs text-purple-400 mt-0.5">schedule_manage</div>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-3">
          <div class="bg-[var(--background,#0b0f19)] p-3 rounded-lg border border-[var(--border,#1e293b)]">
            <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Clinical Cohorts</div>
            <div id="modal-cohorts" class="font-semibold text-white mt-0.5">PD, DS, Stroke</div>
          </div>
          <div class="bg-[var(--background,#0b0f19)] p-3 rounded-lg border border-[var(--border,#1e293b)]">
            <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Allocation</div>
            <div id="modal-alloc" class="font-semibold text-emerald-400 mt-0.5">all (100%)</div>
          </div>
          <div class="bg-[var(--background,#0b0f19)] p-3 rounded-lg border border-[var(--border,#1e293b)]">
            <div class="text-[11px] text-[var(--muted-foreground,#94a3b8)] uppercase font-semibold">Length</div>
            <div id="modal-length" class="text-xs text-white mt-0.5">5 words (28 chars)</div>
          </div>
        </div>

        <div>
          <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)] mb-1">Source Spreadsheets & Lists</div>
          <div id="modal-sources" class="text-xs font-mono bg-[var(--background,#0b0f19)] p-3 rounded-lg border border-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] max-h-24 overflow-y-auto"></div>
        </div>

        <div>
          <div class="flex items-center justify-between mb-1">
            <div class="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground,#94a3b8)]">JSON Schema View</div>
            <button id="btn-copy-modal-json" class="text-[11px] text-blue-400 hover:text-blue-300">Copy JSON</button>
          </div>
          <pre id="modal-json" class="text-[11px] font-mono bg-[var(--background,#0b0f19)] p-3 rounded-lg border border-[var(--border,#1e293b)] text-sky-300 overflow-x-auto max-h-36"></pre>
        </div>
      </div>

      <div class="px-6 py-3 border-t border-[var(--border,#1e293b)] bg-[var(--background,#0b0f19)]/40 flex justify-end">
        <button onclick="closeModal()" class="px-4 py-1.5 rounded-lg text-xs font-medium bg-[var(--card,#131b2e)] hover:bg-[var(--border,#1e293b)] text-white border border-[var(--border,#1e293b)]">Close</button>
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div id="toast" class="hidden fixed bottom-6 right-6 z-50 bg-blue-600 text-white px-4 py-2.5 rounded-xl shadow-lg text-xs font-medium flex items-center gap-2">
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
    <span id="toast-msg">Copied to clipboard!</span>
  </div>

  <!-- Embedded Dataset & Reactive App Logic -->
  <script>
    const ALL_COMMANDS = {commands_json_str};
    const STATS = {stats_json_str};

    // Category styling configurations
    const CATEGORY_COLORS = {{
      "Tasks and planning": "bg-blue-500/15 text-blue-400 border-blue-500/30",
      "News, weather, traffic": "bg-amber-500/15 text-amber-400 border-amber-500/30",
      "Online Search": "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
      "Media control": "bg-purple-500/15 text-purple-400 border-purple-500/30",
      "Phone": "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
      "Smart Home": "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
      "Trip and outdoor": "bg-rose-500/15 text-rose-400 border-rose-500/30",
      "Text dictation": "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
      "Broadcast": "bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/30",
      "Wake Phrases": "bg-slate-500/15 text-slate-400 border-slate-500/30",
      "General Command": "bg-teal-500/15 text-teal-400 border-teal-500/30"
    }};

    // State management
    let state = {{
      search: "",
      category: "all",
      cohort: "all",
      block: "all",
      length: "all",
      excludeWake: false,
      sortBy: "default",
      viewMode: "table",
      page: 1,
      pageSize: 50,
      activeModalCmd: null
    }};

    // DOM Elements
    const searchInput = document.getElementById("search-input");
    const btnClearSearch = document.getElementById("btn-clear-search");
    const categoryPillsContainer = document.getElementById("category-pills");
    const cohortPills = document.querySelectorAll(".cohort-pill");
    const blockPills = document.querySelectorAll(".block-pill");
    const lengthPills = document.querySelectorAll(".len-pill");
    const chkExcludeWake = document.getElementById("chk-exclude-wake");
    const sortSelect = document.getElementById("sort-select");
    const pageSizeSelect = document.getElementById("page-size-select");
    const viewTableBtn = document.getElementById("view-table-btn");
    const viewGridBtn = document.getElementById("view-grid-btn");
    const tableBody = document.getElementById("table-body");
    const tableViewContainer = document.getElementById("table-view-container");
    const gridViewContainer = document.getElementById("grid-view-container");
    const emptyState = document.getElementById("empty-state");
    const filterCountEl = document.getElementById("filter-count");
    const btnResetFilters = document.getElementById("btn-reset-filters");
    const paginationControls = document.getElementById("pagination-controls");
    const pageInfo = document.getElementById("page-info");
    const pageButtons = document.getElementById("page-buttons");
    const btnPrevPage = document.getElementById("btn-prev-page");
    const btnNextPage = document.getElementById("btn-next-page");

    // Modal elements
    const detailModal = document.getElementById("detail-modal");
    const btnCloseModal = document.getElementById("btn-close-modal");
    const modalId = document.getElementById("modal-id");
    const modalTypeBadge = document.getElementById("modal-type-badge");
    const modalText = document.getElementById("modal-text");
    const modalCategory = document.getElementById("modal-category");
    const modalTool = document.getElementById("modal-tool");
    const modalCohorts = document.getElementById("modal-cohorts");
    const modalAlloc = document.getElementById("modal-alloc");
    const modalLength = document.getElementById("modal-length");
    const modalSources = document.getElementById("modal-sources");
    const modalJson = document.getElementById("modal-json");
    const btnCopyModalText = document.getElementById("btn-copy-modal-text");
    const btnCopyModalJson = document.getElementById("btn-copy-modal-json");

    // Render Category Filter Pills
    function initCategoryPills() {{
      const cats = STATS.categories || {{}};
      let html = `<button data-cat="all" class="cat-pill px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500">All Categories (1,309)</button>`;
      for (const [cat, count] of Object.entries(cats)) {{
        html += `<button data-cat="${{cat}}" class="cat-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]">${{cat}} (${{count}})</button>`;
      }}
      categoryPillsContainer.innerHTML = html;

      document.querySelectorAll(".cat-pill").forEach(btn => {{
        btn.addEventListener("click", () => {{
          state.category = btn.getAttribute("data-cat");
          state.page = 1;
          updateFilterPillStyles();
          render();
        }});
      }});
    }}

    function updateFilterPillStyles() {{
      // Categories
      document.querySelectorAll(".cat-pill").forEach(btn => {{
        const isSelected = btn.getAttribute("data-cat") === state.category;
        btn.className = isSelected
          ? "cat-pill px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500"
          : "cat-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]";
      }});

      // Cohorts
      cohortPills.forEach(btn => {{
        const isSelected = btn.getAttribute("data-cohort") === state.cohort;
        btn.className = isSelected
          ? "cohort-pill px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500"
          : "cohort-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]";
      }});

      // Blocks
      blockPills.forEach(btn => {{
        const isSelected = btn.getAttribute("data-block") === state.block;
        btn.className = isSelected
          ? "block-pill px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500"
          : "block-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]";
      }});

      // Length
      lengthPills.forEach(btn => {{
        const isSelected = btn.getAttribute("data-len") === state.length;
        btn.className = isSelected
          ? "len-pill px-2.5 py-1 rounded-md text-xs font-medium bg-blue-600 text-white border border-blue-500"
          : "len-pill px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--background,#0b0f19)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)] border border-[var(--border,#1e293b)]";
      }});

      // Reset button visibility
      const isFiltered = state.search || state.category !== "all" || state.cohort !== "all" || state.block !== "all" || state.length !== "all" || state.excludeWake;
      btnResetFilters.classList.toggle("hidden", !isFiltered);
      btnClearSearch.classList.toggle("hidden", !state.search);
    }}

    function filterAndSortCommands() {{
      const q = state.search.toLowerCase().trim();
      let results = ALL_COMMANDS.filter(cmd => {{
        // Exclude standalone wake phrases
        if (state.excludeWake && cmd.category === "Wake Phrases") return false;

        // Query search
        if (q) {{
          const matchText = cmd.text.toLowerCase().includes(q) || cmd.clean_text.includes(q);
          const matchCat = cmd.category.toLowerCase().includes(q);
          const matchTool = cmd.tool_heuristic && cmd.tool_heuristic.toLowerCase().includes(q);
          const matchId = cmd.id.toLowerCase().includes(q);
          if (!matchText && !matchCat && !matchTool && !matchId) return false;
        }}

        // Category
        if (state.category !== "all" && cmd.category !== state.category) return false;

        // Cohort
        if (state.cohort === "all3") {{
          if (cmd.cohort_count !== 3) return false;
        }} else if (state.cohort !== "all") {{
          if (!cmd.cohorts.includes(state.cohort)) return false;
        }}

        // Block / Schedule
        if (state.block === "univ" && !cmd.is_universal_b1_b10) return false;
        if (state.block === "rotat" && cmd.is_universal_b1_b10) return false;

        // Length
        if (state.length === "short" && cmd.word_count > 3) return false;
        if (state.length === "medium" && (cmd.word_count < 4 || cmd.word_count > 7)) return false;
        if (state.length === "long" && cmd.word_count < 8) return false;

        return true;
      }});

      // Sort
      if (state.sortBy === "alpha-asc") {{
        results.sort((a, b) => a.text.localeCompare(b.text));
      }} else if (state.sortBy === "alpha-desc") {{
        results.sort((a, b) => b.text.localeCompare(a.text));
      }} else if (state.sortBy === "category") {{
        results.sort((a, b) => a.category.localeCompare(b.category) || a.text.localeCompare(b.text));
      }} else if (state.sortBy === "words-asc") {{
        results.sort((a, b) => a.word_count - b.word_count || a.text.localeCompare(b.text));
      }} else if (state.sortBy === "words-desc") {{
        results.sort((a, b) => b.word_count - a.word_count || a.text.localeCompare(b.text));
      }} else {{
        // default: universal first, then 3 cohorts, then alphabetical
        results.sort((a, b) => {{
          if (a.is_universal_b1_b10 !== b.is_universal_b1_b10) return a.is_universal_b1_b10 ? -1 : 1;
          if (a.cohort_count !== b.cohort_count) return b.cohort_count - a.cohort_count;
          return a.text.localeCompare(b.text);
        }});
      }}

      return results;
    }}

    function highlightText(text, q) {{
      if (!q) return escapeHtml(text);
      const safe = escapeHtml(text);
      const regex = new RegExp(`(${{escapeRegExp(q)}})`, "gi");
      return safe.replace(regex, '<span class="highlight">$1</span>');
    }}

    function escapeHtml(str) {{
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }}

    function escapeRegExp(string) {{
      return string.replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&");
    }}

    function render() {{
      const filtered = filterAndSortCommands();
      filterCountEl.textContent = filtered.length.toLocaleString();

      if (filtered.length === 0) {{
        tableViewContainer.classList.add("hidden");
        gridViewContainer.classList.add("hidden");
        paginationControls.classList.add("hidden");
        emptyState.classList.remove("hidden");
        return;
      }}

      emptyState.classList.add("hidden");
      paginationControls.classList.remove("hidden");

      // Pagination math
      const totalPages = Math.ceil(filtered.length / state.pageSize) || 1;
      if (state.page > totalPages) state.page = totalPages;
      const startIdx = (state.page - 1) * state.pageSize;
      const endIdx = startIdx + state.pageSize;
      const pageItems = filtered.slice(startIdx, endIdx);

      // Render pagination numbers
      pageInfo.textContent = `Showing ${{startIdx + 1}}–${{Math.min(endIdx, filtered.length)}} of ${{filtered.length}} (Page ${{state.page}} of ${{totalPages}})`;
      btnPrevPage.disabled = state.page <= 1;
      btnNextPage.disabled = state.page >= totalPages;

      let btnHtml = "";
      const maxButtons = 5;
      let startP = Math.max(1, state.page - 2);
      let endP = Math.min(totalPages, startP + maxButtons - 1);
      if (endP - startP < maxButtons - 1) startP = Math.max(1, endP - maxButtons + 1);

      for (let p = startP; p <= endP; p++) {{
        const isCurrent = p === state.page;
        btnHtml += `<button onclick="goToPage(${{p}})" class="px-2.5 py-1 rounded text-xs ${{isCurrent ? 'bg-blue-600 text-white font-semibold' : 'bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] hover:bg-[var(--border,#1e293b)] text-[var(--muted-foreground,#94a3b8)]'}}">${{p}}</button>`;
      }}
      pageButtons.innerHTML = btnHtml;

      if (state.viewMode === "table") {{
        tableViewContainer.classList.remove("hidden");
        gridViewContainer.classList.add("hidden");
        renderTable(pageItems);
      }} else {{
        tableViewContainer.classList.add("hidden");
        gridViewContainer.classList.remove("hidden");
        renderGrid(pageItems);
      }}
    }}

    function renderTable(items) {{
      const q = state.search.toLowerCase().trim();
      let html = "";
      items.forEach(cmd => {{
        const catClass = CATEGORY_COLORS[cmd.category] || "bg-gray-500/15 text-gray-400 border-gray-500/30";
        const typeBadge = cmd.is_universal_b1_b10
          ? '<span class="px-2 py-0.5 rounded text-[11px] font-medium badge-univ">★ B1/B10</span>'
          : '<span class="px-2 py-0.5 rounded text-[11px] font-medium text-[var(--muted-foreground,#94a3b8)] bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)]">Rotation</span>';

        let cohortsHtml = cmd.cohorts.map(c => {{
          const cls = c === 'PD' ? 'badge-pd' : (c === 'DS' ? 'badge-ds' : 'badge-stroke');
          return `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold ${{cls}}">${{c}}</span>`;
        }}).join(" ");

        html += `
          <tr class="hover:bg-[var(--background,#0b0f19)]/40 transition cursor-pointer" onclick="openDetailModal('${{cmd.id}}')">
            <td class="py-3 px-4 font-mono text-[11px] text-[var(--muted-foreground,#94a3b8)]">${{cmd.id}}</td>
            <td class="py-3 px-4">${{typeBadge}}</td>
            <td class="py-3 px-4 flex items-center gap-1">${{cohortsHtml}}</td>
            <td class="py-3 px-4">
              <span class="px-2 py-0.5 rounded text-[11px] font-medium border ${{catClass}}">${{cmd.category}}</span>
            </td>
            <td class="py-3 px-4 font-medium text-[var(--foreground,#f1f5f9)] leading-relaxed">
              ${{highlightText(cmd.text, q)}}
            </td>
            <td class="py-3 px-4 text-center text-[var(--muted-foreground,#94a3b8)] text-xs">${{cmd.word_count}}w</td>
            <td class="py-3 px-4 text-right" onclick="event.stopPropagation()">
              <button onclick="copyToClipboard('${{escapeHtml(cmd.text)}}')" title="Copy prompt" class="p-1.5 rounded hover:bg-[var(--border,#334155)] text-[var(--muted-foreground,#94a3b8)] hover:text-white transition">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/></svg>
              </button>
            </td>
          </tr>
        `;
      }});
      tableBody.innerHTML = html;
    }}

    function renderGrid(items) {{
      const q = state.search.toLowerCase().trim();
      let html = "";
      items.forEach(cmd => {{
        const catClass = CATEGORY_COLORS[cmd.category] || "bg-gray-500/15 text-gray-400 border-gray-500/30";
        const typeBadge = cmd.is_universal_b1_b10
          ? '<span class="px-2 py-0.5 rounded text-[11px] font-medium badge-univ">★ B1/B10 Universal</span>'
          : '<span class="px-2 py-0.5 rounded text-[11px] font-medium text-[var(--muted-foreground,#94a3b8)] bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)]">Rotation List</span>';

        let cohortsHtml = cmd.cohorts.map(c => {{
          const cls = c === 'PD' ? 'badge-pd' : (c === 'DS' ? 'badge-ds' : 'badge-stroke');
          return `<span class="px-1.5 py-0.5 rounded text-[10px] font-semibold ${{cls}}">${{c}}</span>`;
        }}).join(" ");

        html += `
          <div class="bg-[var(--card,#131b2e)] border border-[var(--border,#1e293b)] rounded-xl p-4 shadow-sm hover:border-blue-500/50 transition cursor-pointer flex flex-col justify-between" onclick="openDetailModal('${{cmd.id}}')">
            <div>
              <div class="flex items-center justify-between mb-2">
                <span class="font-mono text-[11px] text-[var(--muted-foreground,#94a3b8)]">${{cmd.id}}</span>
                <div class="flex items-center gap-1.5">${{typeBadge}}</div>
              </div>
              <p class="text-sm font-semibold text-white leading-snug mb-3">
                ${{highlightText(cmd.text, q)}}
              </p>
            </div>
            
            <div class="pt-3 border-t border-[var(--border,#1e293b)]/60 flex items-center justify-between">
              <span class="px-2 py-0.5 rounded text-[11px] font-medium border ${{catClass}}">${{cmd.category}}</span>
              <div class="flex items-center gap-1">${{cohortsHtml}}</div>
            </div>
          </div>
        `;
      }});
      gridViewContainer.innerHTML = html;
    }}

    function goToPage(p) {{
      state.page = p;
      render();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function openDetailModal(cmdId) {{
      const cmd = ALL_COMMANDS.find(c => c.id === cmdId);
      if (!cmd) return;
      state.activeModalCmd = cmd;

      modalId.textContent = cmd.id;
      modalTypeBadge.className = cmd.is_universal_b1_b10 ? "px-2 py-0.5 rounded text-xs font-medium badge-univ" : "px-2 py-0.5 rounded text-xs font-medium text-[var(--muted-foreground,#94a3b8)] bg-[var(--background,#0b0f19)] border border-[var(--border,#1e293b)]";
      modalTypeBadge.textContent = cmd.is_universal_b1_b10 ? "★ Universal Core (B1 & B10)" : "Rotation List (B2–B9)";
      modalText.textContent = `"${{cmd.text}}"`;
      modalCategory.textContent = cmd.category;
      modalTool.textContent = cmd.tool_heuristic || "None";
      modalCohorts.textContent = `${{cmd.cohorts.join(', ')}} (${{cmd.cohort_count}} cohort(s))`;
      modalAlloc.textContent = cmd.participant_groups.length ? cmd.participant_groups.join(', ') : "Rotation";
      modalLength.textContent = `${{cmd.word_count}} words (${{cmd.char_count}} chars) — ${{cmd.complexity}}`;
      modalSources.textContent = `Sources: ${{cmd.sources.join(', ')}}\nSheets: ${{cmd.blocks.join(', ')}}`;
      modalJson.textContent = JSON.stringify(cmd, null, 2);

      detailModal.classList.remove("hidden");
    }}

    function closeModal() {{
      detailModal.classList.add("hidden");
      state.activeModalCmd = null;
    }}

    function showToast(msg) {{
      const toast = document.getElementById("toast");
      document.getElementById("toast-msg").textContent = msg;
      toast.classList.remove("hidden");
      setTimeout(() => toast.classList.add("hidden"), 2200);
    }}

    function copyToClipboard(text) {{
      navigator.clipboard.writeText(text).then(() => {{
        showToast("Copied prompt to clipboard!");
      }});
    }}

    function resetAllFilters() {{
      state.search = "";
      state.category = "all";
      state.cohort = "all";
      state.block = "all";
      state.length = "all";
      state.excludeWake = false;
      searchInput.value = "";
      chkExcludeWake.checked = false;
      state.page = 1;
      updateFilterPillStyles();
      render();
    }}

    // Export functions
    function exportJSON() {{
      const filtered = filterAndSortCommands();
      const blob = new Blob([JSON.stringify(filtered, null, 2)], {{ type: "application/json" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sap_commands_filtered_${{filtered.length}}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`Exported ${{filtered.length}} commands to JSON!`);
    }}

    function exportCSV() {{
      const filtered = filterAndSortCommands();
      const headers = ["id", "text", "clean_text", "category", "cohorts", "is_universal_b1_b10", "word_count", "tool_heuristic"];
      const rows = [headers.join(",")];
      filtered.forEach(c => {{
        const row = [
          c.id,
          `"${{c.text.replace(/"/g, '""')}}"`,
          `"${{c.clean_text.replace(/"/g, '""')}}"`,
          `"${{c.category}}"`,
          `"${{c.cohorts.join('; ')}}"`,
          c.is_universal_b1_b10 ? "Yes" : "No",
          c.word_count,
          `"${{c.tool_heuristic}}"`
        ];
        rows.push(row.join(","));
      }});
      const blob = new Blob([rows.join("\\n")], {{ type: "text/csv;charset=utf-8;" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sap_commands_filtered_${{filtered.length}}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`Exported ${{filtered.length}} commands to CSV!`);
    }}

    function copyFilteredPrompts() {{
      const filtered = filterAndSortCommands();
      const plain = filtered.map(c => c.text).join("\\n");
      navigator.clipboard.writeText(plain).then(() => {{
        showToast(`Copied ${{filtered.length}} prompts to clipboard!`);
      }});
    }}

    function pickRandom() {{
      const filtered = filterAndSortCommands();
      if (!filtered.length) return;
      const pick = filtered[Math.floor(Math.random() * filtered.length)];
      openDetailModal(pick.id);
    }}

    // Event Listeners
    searchInput.addEventListener("input", (e) => {{
      state.search = e.target.value;
      state.page = 1;
      updateFilterPillStyles();
      render();
    }});

    btnClearSearch.addEventListener("click", () => {{
      state.search = "";
      searchInput.value = "";
      state.page = 1;
      updateFilterPillStyles();
      render();
    }});

    chkExcludeWake.addEventListener("change", (e) => {{
      state.excludeWake = e.target.checked;
      state.page = 1;
      updateFilterPillStyles();
      render();
    }});

    sortSelect.addEventListener("change", (e) => {{
      state.sortBy = e.target.value;
      render();
    }});

    pageSizeSelect.addEventListener("change", (e) => {{
      state.pageSize = parseInt(e.target.value, 10);
      state.page = 1;
      render();
    }});

    viewTableBtn.addEventListener("click", () => {{
      state.viewMode = "table";
      viewTableBtn.className = "px-2.5 py-1 rounded text-xs font-medium bg-blue-600 text-white transition";
      viewGridBtn.className = "px-2.5 py-1 rounded text-xs font-medium text-[var(--muted-foreground,#94a3b8)] hover:text-white transition";
      render();
    }});

    viewGridBtn.addEventListener("click", () => {{
      state.viewMode = "grid";
      viewGridBtn.className = "px-2.5 py-1 rounded text-xs font-medium bg-blue-600 text-white transition";
      viewTableBtn.className = "px-2.5 py-1 rounded text-xs font-medium text-[var(--muted-foreground,#94a3b8)] hover:text-white transition";
      render();
    }});

    cohortPills.forEach(btn => {{
      btn.addEventListener("click", () => {{
        state.cohort = btn.getAttribute("data-cohort");
        state.page = 1;
        updateFilterPillStyles();
        render();
      }});
    }});

    blockPills.forEach(btn => {{
      btn.addEventListener("click", () => {{
        state.block = btn.getAttribute("data-block");
        state.page = 1;
        updateFilterPillStyles();
        render();
      }});
    }});

    lengthPills.forEach(btn => {{
      btn.addEventListener("click", () => {{
        state.length = btn.getAttribute("data-len");
        state.page = 1;
        updateFilterPillStyles();
        render();
      }});
    }});

    btnPrevPage.addEventListener("click", () => {{
      if (state.page > 1) goToPage(state.page - 1);
    }});

    btnNextPage.addEventListener("click", () => {{
      const filtered = filterAndSortCommands();
      const totalPages = Math.ceil(filtered.length / state.pageSize);
      if (state.page < totalPages) goToPage(state.page + 1);
    }});

    btnResetFilters.addEventListener("click", resetAllFilters);
    btnCloseModal.addEventListener("click", closeModal);
    detailModal.addEventListener("click", (e) => {{
      if (e.target === detailModal) closeModal();
    }});

    window.addEventListener("keydown", (e) => {{
      if (e.key === "Escape") closeModal();
    }});

    btnCopyModalText.addEventListener("click", () => {{
      if (state.activeModalCmd) copyToClipboard(state.activeModalCmd.text);
    }});

    btnCopyModalJson.addEventListener("click", () => {{
      if (state.activeModalCmd) {{
        navigator.clipboard.writeText(JSON.stringify(state.activeModalCmd, null, 2)).then(() => {{
          showToast("Copied JSON snippet to clipboard!");
        }});
      }}
    }});

    document.getElementById("btn-export-json").addEventListener("click", exportJSON);
    document.getElementById("btn-export-csv").addEventListener("click", exportCSV);
    document.getElementById("btn-copy-filtered").addEventListener("click", copyFilteredPrompts);
    document.getElementById("btn-random-pick").addEventListener("click", pickRandom);

    // Initial setup
    initCategoryPills();
    render();
  </script>
</body>
</html>
"""
    with open(HTML_OUTPUT, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Successfully generated interactive web browser at {HTML_OUTPUT}")


if __name__ == "__main__":
    generate_html()
