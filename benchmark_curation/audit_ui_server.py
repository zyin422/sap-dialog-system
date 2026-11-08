#!/usr/bin/env python3
"""
Interactive Audit UI Server for Speech Accessibility Project (SAP) Unshared Dev Slices.
Allows real-time listening to audio recordings, fast categorization (KEEP, FILTER_OUT, NOT_SURE),
and immediate persistence to dev_unshared_manual_audit_245.csv.
"""

import os
import sys
import json
import csv
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "dev_unshared_manual_audit_245.csv")
AUDIO_DIR = os.path.join(BASE_DIR, "audio_245")
MANIFEST_PATH = os.path.join(os.path.dirname(BASE_DIR), "manifest", "dev_unshared_prompts.csv")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SAP Dev Unshared Audio Audit Workbench</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f1f5f9; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
  </style>
</head>
<body class="bg-[#f8fafc] text-slate-900 h-screen flex flex-col overflow-hidden antialiased select-none">

  <!-- TOP TELEMETRY BAR -->
  <header class="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0 shadow-sm">
    <div class="flex items-center gap-3">
      <div class="w-3 h-3 rounded-full bg-[#d97706]"></div>
      <h1 class="font-semibold text-sm tracking-wide text-slate-900">SAP AUDIT WORKBENCH</h1>
      <span class="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 mono border border-slate-200">dev_unshared_prompts.csv</span>
    </div>

    <!-- Live Telemetry Counters -->
    <div class="flex items-center gap-4 text-xs mono">
      <div>
        <span class="text-slate-500">PROG:</span>
        <span id="stat-progress" class="font-bold text-slate-900 ml-1">0 / 245 (0%)</span>
      </div>
      <div>
        <span class="text-slate-500">KEPT:</span>
        <span id="stat-kept" class="font-bold text-emerald-700 ml-1">0</span>
      </div>
      <div>
        <span class="text-slate-500">UNDERSPEC:</span>
        <span id="stat-underspec" class="font-bold text-indigo-700 ml-1">0</span>
      </div>
      <div>
        <span class="text-slate-500">SLOT_DEV:</span>
        <span id="stat-slotdev" class="font-bold text-amber-700 ml-1">0</span>
      </div>
      <div>
        <span class="text-slate-500">FILTERED:</span>
        <span id="stat-filtered" class="font-bold text-rose-700 ml-1">0</span>
      </div>
      <div>
        <span class="text-slate-500">NOT SURE:</span>
        <span id="stat-notsure" class="font-bold text-slate-700 ml-1">0</span>
      </div>
      <div>
        <span class="text-slate-500">PENDING:</span>
        <span id="stat-pending" class="font-bold text-slate-500 ml-1">245</span>
      </div>
    </div>
  </header>

  <!-- MAIN WORKBENCH LAYOUT -->
  <div class="flex flex-1 overflow-hidden">
    
    <!-- LEFT SIDEBAR: INSTANCE QUEUE -->
    <aside class="w-80 bg-white border-r border-slate-200 flex flex-col shrink-0">
      
      <!-- Filters -->
      <div class="p-3 border-b border-slate-200 space-y-2 bg-slate-50/70">
        <div class="flex items-center gap-1 overflow-x-auto pb-1 text-[11px] mono">
          <button onclick="setFilter('ALL')" id="flt-ALL" class="px-2 py-0.5 rounded bg-slate-900 text-white font-medium shadow-sm">All</button>
          <button onclick="setFilter('PENDING')" id="flt-PENDING" class="px-2 py-0.5 rounded bg-white text-slate-600 hover:bg-slate-100 border border-slate-200">Unrev</button>
          <button onclick="setFilter('KEEP')" id="flt-KEEP" class="px-2 py-0.5 rounded bg-white text-emerald-700 hover:bg-emerald-50 border border-slate-200">Keep</button>
          <button onclick="setFilter('UNDERSPECIFIED')" id="flt-UNDERSPECIFIED" class="px-2 py-0.5 rounded bg-white text-indigo-700 hover:bg-indigo-50 border border-slate-200">Underspec</button>
          <button onclick="setFilter('SLOT_DEVIATION')" id="flt-SLOT_DEVIATION" class="px-2 py-0.5 rounded bg-white text-amber-700 hover:bg-amber-50 border border-slate-200">SlotDev</button>
          <button onclick="setFilter('FILTER_OUT')" id="flt-FILTER_OUT" class="px-2 py-0.5 rounded bg-white text-rose-700 hover:bg-rose-50 border border-slate-200">Filtered</button>
          <button onclick="setFilter('NOT_SURE')" id="flt-NOT_SURE" class="px-2 py-0.5 rounded bg-white text-slate-700 hover:bg-slate-100 border border-slate-200">NotSure</button>
        </div>
        <select id="flt-etiology" onchange="renderList()" class="w-full bg-white border border-slate-300 rounded px-2 py-1 text-xs mono text-slate-700 focus:outline-none focus:border-amber-600">
          <option value="ALL">All Clinical Etiologies</option>
          <option value="Down Syndrome">Down Syndrome</option>
          <option value="Cerebral Palsy">Cerebral Palsy</option>
          <option value="Stroke">Stroke</option>
          <option value="Parkinson's Disease">Parkinson's Disease</option>
          <option value="ALS">ALS</option>
        </select>
      </div>

      <!-- Scrollable List -->
      <div id="instance-list" class="flex-1 overflow-y-auto divide-y divide-slate-100">
        <!-- List items injected dynamically -->
      </div>
    </aside>

    <!-- RIGHT INSPECTION & DECISION CANVAS -->
    <main class="flex-1 flex flex-col bg-[#f8fafc] overflow-y-auto p-8">
      
      <div class="max-w-4xl w-full mx-auto space-y-6">
        
        <!-- CARD: AUDIO METADATA & TELEMETRY -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span id="badge-index" class="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700 mono border border-slate-300">#1 / 245</span>
              <span id="badge-etiology" class="text-xs font-semibold px-2.5 py-1 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">Cerebral Palsy</span>
              <span id="badge-tag" class="text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200">TELEGRAPHIC_INCOMPLETE</span>
            </div>
            <div class="text-xs mono text-slate-500">
              <span id="meta-duration">2.34s</span> | <span id="meta-id">id</span>
            </div>
          </div>

          <!-- COMPARISON BOXES -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            
            <!-- TARGET PROMPT -->
            <div class="bg-slate-50 border border-slate-200 rounded-lg p-4 flex flex-col justify-between">
              <div>
                <div class="text-[11px] font-bold text-slate-500 tracking-wider mono uppercase mb-1">Target Prompt</div>
                <div id="view-prompt" class="text-base font-semibold text-slate-900 leading-relaxed">
                  "Make me a reservation at Baytown Brewery."
                </div>
              </div>
              <div class="mt-4 pt-2 border-t border-slate-200 flex items-center justify-between text-xs mono text-slate-500">
                <span>Gold Target</span>
                <span class="text-slate-600 font-medium">SLU Benchmark</span>
              </div>
            </div>

            <!-- HUMAN VERBATIM AUDIO TRANSCRIPT -->
            <div class="bg-amber-50/50 border border-amber-200 rounded-lg p-4 flex flex-col justify-between">
              <div>
                <div class="text-[11px] font-bold text-amber-800 tracking-wider mono uppercase mb-1">Actual Spoken Text (Verbatim)</div>
                <div id="view-spoken" class="text-base font-semibold text-amber-950 leading-relaxed">
                  "Make me a reservation."
                </div>
              </div>
              <div class="mt-4 pt-2 border-t border-amber-200 flex items-center justify-between text-xs mono text-amber-800">
                <span>Jaccard: <strong id="view-jaccard" class="text-amber-950">0.33</strong></span>
                <span>Len Ratio: <strong id="view-lenratio" class="text-amber-950">0.45</strong></span>
              </div>
            </div>

          </div>

          <!-- AUDIO PLAYER SECTION -->
          <div class="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold mono text-slate-700 flex items-center gap-2">
                <svg class="w-4 h-4 text-amber-600" fill="currentColor" viewBox="0 0 20 20"><path d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8v4l5-2-5-2z"/></svg>
                ACOUSTIC RECORDING
              </span>
              <div class="flex items-center gap-1.5 mono text-xs">
                <span class="text-[11px] text-slate-500 mr-1">Speed [ / ]:</span>
                <button type="button" onclick="setSpeed(1.0)" id="spd-1.0" class="px-2 py-0.5 rounded text-xs mono border border-slate-200 bg-white text-slate-700 hover:bg-slate-100">1.0x</button>
                <button type="button" onclick="setSpeed(1.25)" id="spd-1.25" class="px-2 py-0.5 rounded text-xs mono bg-amber-600 text-white font-bold shadow-sm">1.25x</button>
                <button type="button" onclick="setSpeed(1.5)" id="spd-1.5" class="px-2 py-0.5 rounded text-xs mono border border-slate-200 bg-white text-slate-700 hover:bg-slate-100">1.5x</button>
                <button type="button" onclick="setSpeed(1.75)" id="spd-1.75" class="px-2 py-0.5 rounded text-xs mono border border-slate-200 bg-white text-slate-700 hover:bg-slate-100">1.75x</button>
                <button type="button" onclick="setSpeed(2.0)" id="spd-2.0" class="px-2 py-0.5 rounded text-xs mono border border-slate-200 bg-white text-slate-700 hover:bg-slate-100">2.0x</button>
              </div>
            </div>
            
            <audio id="audio-player" controls class="w-full h-10 accent-[#d97706]" src=""></audio>
            
            <div class="flex items-center justify-between text-xs mono text-slate-500">
              <span>Speaker: <span id="meta-speaker" class="text-slate-700 font-medium">UUID</span></span>
              <span>Hotkeys: [Space] Play | [1/K] Keep | [2/U] Underspec | [3/D] SlotDev | [4/F] Filter | [5/N] NotSure | [ [ / ] ] Speed</span>
            </div>
          </div>

        </div>

        <!-- CARD: DECISION CONTROL PANEL -->
        <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div class="text-xs font-bold text-slate-500 tracking-wider mono uppercase">
            Curator Decision & Triage
          </div>

          <!-- Action Buttons -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            
            <!-- KEEP -->
            <button onclick="submitDecision('KEEP')" id="btn-keep" class="flex flex-col items-center justify-center p-3 rounded-xl border-2 border-slate-200 bg-white hover:bg-emerald-50 hover:border-emerald-600 transition-all group shadow-sm text-center">
              <div class="flex items-center gap-1.5 text-xs font-bold text-slate-800 group-hover:text-emerald-700">
                <svg class="w-4 h-4 text-emerald-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                <span>KEEP (COMPLETE)</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1 mono">Task 1 SLU [1 / K]</div>
            </button>

            <!-- UNDERSPECIFIED -->
            <button onclick="submitDecision('UNDERSPECIFIED')" id="btn-underspec" class="flex flex-col items-center justify-center p-3 rounded-xl border-2 border-slate-200 bg-white hover:bg-indigo-50 hover:border-indigo-600 transition-all group shadow-sm text-center">
              <div class="flex items-center gap-1.5 text-xs font-bold text-slate-800 group-hover:text-indigo-700">
                <svg class="w-4 h-4 text-indigo-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h10M4 18h7"/></svg>
                <span>UNDERSPECIFIED</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1 mono">Task 2A Slots [2 / U]</div>
            </button>

            <!-- SLOT DEVIATION -->
            <button onclick="submitDecision('SLOT_DEVIATION')" id="btn-slotdev" class="flex flex-col items-center justify-center p-3 rounded-xl border-2 border-slate-200 bg-white hover:bg-amber-50 hover:border-amber-600 transition-all group shadow-sm text-center">
              <div class="flex items-center gap-1.5 text-xs font-bold text-slate-800 group-hover:text-amber-700">
                <svg class="w-4 h-4 text-amber-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>
                <span>SLOT DEVIATION</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1 mono">Misread entity [3 / D]</div>
            </button>

            <!-- FILTER OUT -->
            <button onclick="submitDecision('FILTER_OUT')" id="btn-filter" class="flex flex-col items-center justify-center p-3 rounded-xl border-2 border-slate-200 bg-white hover:bg-rose-50 hover:border-rose-600 transition-all group shadow-sm text-center">
              <div class="flex items-center gap-1.5 text-xs font-bold text-slate-800 group-hover:text-rose-700">
                <svg class="w-4 h-4 text-rose-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                <span>FILTER OUT</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1 mono">Tier 0 Junk [4 / F]</div>
            </button>

            <!-- NOT SURE -->
            <button onclick="submitDecision('NOT_SURE')" id="btn-notsure" class="flex flex-col items-center justify-center p-3 rounded-xl border-2 border-slate-200 bg-white hover:bg-slate-100 hover:border-slate-500 transition-all group shadow-sm text-center">
              <div class="flex items-center gap-1.5 text-xs font-bold text-slate-800 group-hover:text-slate-900">
                <svg class="w-4 h-4 text-slate-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                <span>NOT SURE</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1 mono">Flag Review [5 / N]</div>
            </button>

          </div>

          <!-- Notes -->
          <div class="pt-2">
            <input type="text" id="input-notes" placeholder="Optional review note (e.g., 'caregiver prompt', 'severe apraxia block', 'stutter on 9374')..."
                   class="w-full bg-white border border-slate-300 rounded-lg px-4 py-2 text-xs text-slate-900 focus:outline-none focus:border-amber-600 mono">
          </div>

          <!-- Bottom Nav Controls -->
          <div class="flex items-center justify-between pt-2 border-t border-slate-200">
            <button onclick="prevItem()" class="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold mono flex items-center gap-2 text-slate-700 border border-slate-200">
              ← Previous [Left Arrow]
            </button>
            <div class="text-xs text-slate-500 mono">
              Current Decision: <strong id="label-current-decision" class="text-slate-700">UNREVIEWED</strong>
            </div>
            <button onclick="nextItem()" class="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold mono flex items-center gap-2 text-slate-700 border border-slate-200">
              Next [Right Arrow] →
            </button>
          </div>

        </div>

      </div>

    </main>
  </div>

  <script>
    let instances = [];
    let currentIndex = 0;
    let currentFilter = 'ALL';
    let currentSpeed = 1.25;
    const SPEEDS = [1.0, 1.25, 1.5, 1.75, 2.0];

    function setSpeed(spd) {
      currentSpeed = spd;
      const player = document.getElementById('audio-player');
      if (player) player.playbackRate = currentSpeed;
      SPEEDS.forEach(s => {
        const id = 'spd-' + (s % 1 === 0 ? s + '.0' : s);
        const el = document.getElementById(id);
        if (!el) return;
        if (Math.abs(s - spd) < 0.01) {
          el.className = 'px-2 py-0.5 rounded text-xs mono bg-amber-600 text-white font-bold shadow-sm';
        } else {
          el.className = 'px-2 py-0.5 rounded text-xs mono border border-slate-200 bg-white text-slate-700 hover:bg-slate-100';
        }
      });
    }

    function adjustSpeed(delta) {
      let idx = SPEEDS.findIndex(s => Math.abs(s - currentSpeed) < 0.01);
      if (idx === -1) idx = 1;
      let newIdx = idx + delta;
      if (newIdx < 0) newIdx = 0;
      if (newIdx >= SPEEDS.length) newIdx = SPEEDS.length - 1;
      setSpeed(SPEEDS[newIdx]);
    }

    async function loadInstances() {
      try {
        const res = await fetch('/api/instances');
        instances = await res.json();
        updateTelemetry();
        renderList();
        selectItem(0);
      } catch (e) {
        console.error('Failed to load instances', e);
      }
    }

    function updateTelemetry() {
      const total = instances.length;
      const kept = instances.filter(i => i.decision === 'KEEP').length;
      const underspec = instances.filter(i => i.decision === 'UNDERSPECIFIED').length;
      const slotdev = instances.filter(i => i.decision === 'SLOT_DEVIATION').length;
      const filtered = instances.filter(i => i.decision === 'FILTER_OUT').length;
      const notsure = instances.filter(i => i.decision === 'NOT_SURE').length;
      const reviewed = kept + underspec + slotdev + filtered + notsure;
      const pending = total - reviewed;
      const pct = Math.round((reviewed / total) * 100);

      document.getElementById('stat-progress').innerText = `${reviewed} / ${total} (${pct}%)`;
      document.getElementById('stat-kept').innerText = kept;
      document.getElementById('stat-underspec').innerText = underspec;
      document.getElementById('stat-slotdev').innerText = slotdev;
      document.getElementById('stat-filtered').innerText = filtered;
      document.getElementById('stat-notsure').innerText = notsure;
      document.getElementById('stat-pending').innerText = pending;
    }

    function setFilter(flt) {
      currentFilter = flt;
      ['ALL', 'PENDING', 'KEEP', 'UNDERSPECIFIED', 'SLOT_DEVIATION', 'FILTER_OUT', 'NOT_SURE'].forEach(f => {
        const el = document.getElementById('flt-' + f);
        if (!el) return;
        if (f === flt) {
          el.className = 'px-2 py-0.5 rounded bg-slate-900 text-white font-medium shadow-sm';
        } else {
          let textCol = 'text-slate-600 hover:bg-slate-100';
          if (f === 'KEEP') textCol = 'text-emerald-700 hover:bg-emerald-50';
          if (f === 'UNDERSPECIFIED') textCol = 'text-indigo-700 hover:bg-indigo-50';
          if (f === 'SLOT_DEVIATION') textCol = 'text-amber-700 hover:bg-amber-50';
          if (f === 'FILTER_OUT') textCol = 'text-rose-700 hover:bg-rose-50';
          if (f === 'NOT_SURE') textCol = 'text-slate-700 hover:bg-slate-100';
          el.className = `px-2 py-0.5 rounded bg-white ${textCol} border border-slate-200`;
        }
      });
      renderList();
    }

    function getFilteredList() {
      const etiology = document.getElementById('flt-etiology').value;
      return instances.filter(item => {
        if (etiology !== 'ALL' && item.etiology !== etiology) return false;
        if (currentFilter === 'PENDING') return !item.decision;
        if (currentFilter === 'KEEP') return item.decision === 'KEEP';
        if (currentFilter === 'UNDERSPECIFIED') return item.decision === 'UNDERSPECIFIED';
        if (currentFilter === 'SLOT_DEVIATION') return item.decision === 'SLOT_DEVIATION';
        if (currentFilter === 'FILTER_OUT') return item.decision === 'FILTER_OUT';
        if (currentFilter === 'NOT_SURE') return item.decision === 'NOT_SURE';
        return true;
      });
    }

    function renderList() {
      const listContainer = document.getElementById('instance-list');
      const filtered = getFilteredList();
      listContainer.innerHTML = '';

      if (filtered.length === 0) {
        listContainer.innerHTML = '<div class="p-6 text-center text-xs text-slate-400 mono">No instances match filter</div>';
        return;
      }

      filtered.forEach((item) => {
        const idx = instances.indexOf(item);
        const div = document.createElement('div');
        div.className = `p-3 cursor-pointer transition-colors border-b border-slate-100 ${idx === currentIndex ? 'bg-amber-50/70 border-l-4 border-amber-600 font-semibold' : 'hover:bg-slate-50'}`;
        div.onclick = () => selectItem(idx);

        let statusBadge = '<span class="w-2 h-2 rounded-full bg-slate-300"></span>';
        if (item.decision === 'KEEP') statusBadge = '<span class="w-2 h-2 rounded-full bg-emerald-600"></span>';
        else if (item.decision === 'UNDERSPECIFIED') statusBadge = '<span class="w-2 h-2 rounded-full bg-indigo-600"></span>';
        else if (item.decision === 'SLOT_DEVIATION') statusBadge = '<span class="w-2 h-2 rounded-full bg-amber-500"></span>';
        else if (item.decision === 'FILTER_OUT') statusBadge = '<span class="w-2 h-2 rounded-full bg-rose-600"></span>';
        else if (item.decision === 'NOT_SURE') statusBadge = '<span class="w-2 h-2 rounded-full bg-slate-500"></span>';

        div.innerHTML = `
          <div class="flex items-center justify-between text-xs mono mb-1">
            <span class="text-slate-500 font-normal">#${idx + 1} | ${item.etiology}</span>
            <div class="flex items-center gap-1.5">${statusBadge} <span class="text-[10px] text-slate-400 font-normal">${item.duration}s</span></div>
          </div>
          <div class="text-xs font-semibold text-slate-900 truncate">${item.prompt}</div>
          <div class="text-[11px] text-slate-500 truncate italic mt-0.5 font-normal">"${item.spoken_text}"</div>
        `;
        listContainer.appendChild(div);
      });
    }

    function selectItem(idx) {
      if (idx < 0 || idx >= instances.length) return;
      currentIndex = idx;
      const item = instances[idx];

      document.getElementById('badge-index').innerText = `#${idx + 1} / ${instances.length}`;
      document.getElementById('badge-etiology').innerText = item.etiology;
      document.getElementById('badge-tag').innerText = item.preliminary_tag;
      document.getElementById('meta-duration').innerText = `${item.duration}s`;
      document.getElementById('meta-id').innerText = item.id.substring(0, 16) + '...';
      document.getElementById('meta-speaker').innerText = item.speaker;

      document.getElementById('view-prompt').innerText = `"${item.prompt}"`;
      document.getElementById('view-spoken').innerText = `"${item.spoken_text}"`;
      document.getElementById('view-jaccard').innerText = item.jaccard_sim;
      document.getElementById('view-lenratio').innerText = item.len_ratio;
      document.getElementById('input-notes').value = item.notes || '';

      const decisionEl = document.getElementById('label-current-decision');
      decisionEl.innerText = item.decision || 'UNREVIEWED';
      if (item.decision === 'KEEP') decisionEl.className = 'text-emerald-700 font-bold';
      else if (item.decision === 'UNDERSPECIFIED') decisionEl.className = 'text-indigo-700 font-bold';
      else if (item.decision === 'SLOT_DEVIATION') decisionEl.className = 'text-amber-700 font-bold';
      else if (item.decision === 'FILTER_OUT') decisionEl.className = 'text-rose-700 font-bold';
      else if (item.decision === 'NOT_SURE') decisionEl.className = 'text-slate-600 font-bold';
      else decisionEl.className = 'text-slate-500 font-bold';

      // Highlight active button
      ['keep', 'underspec', 'slotdev', 'filter', 'notsure'].forEach(b => {
        const el = document.getElementById('btn-' + b);
        if (el) el.classList.remove('ring-2', 'ring-emerald-600', 'ring-indigo-600', 'ring-amber-600', 'ring-rose-600', 'ring-slate-600', 'bg-emerald-50', 'bg-indigo-50', 'bg-amber-50', 'bg-rose-50', 'bg-slate-100');
      });
      if (item.decision === 'KEEP') document.getElementById('btn-keep').classList.add('ring-2', 'ring-emerald-600', 'bg-emerald-50');
      if (item.decision === 'UNDERSPECIFIED') document.getElementById('btn-underspec').classList.add('ring-2', 'ring-indigo-600', 'bg-indigo-50');
      if (item.decision === 'SLOT_DEVIATION') document.getElementById('btn-slotdev').classList.add('ring-2', 'ring-amber-600', 'bg-amber-50');
      if (item.decision === 'FILTER_OUT') document.getElementById('btn-filter').classList.add('ring-2', 'ring-rose-600', 'bg-rose-50');
      if (item.decision === 'NOT_SURE') document.getElementById('btn-notsure').classList.add('ring-2', 'ring-slate-600', 'bg-slate-100');

      // Update Audio Player
      const player = document.getElementById('audio-player');
      player.src = `/audio/${item.id}`;
      player.load();
      player.playbackRate = currentSpeed;
      player.onloadedmetadata = () => {
        player.playbackRate = currentSpeed;
      };
      
      renderList();
    }

    async function submitDecision(decision) {
      const item = instances[currentIndex];
      const notes = document.getElementById('input-notes').value.trim();
      item.decision = decision;
      item.notes = notes;

      updateTelemetry();
      selectItem(currentIndex);

      try {
        await fetch('/api/decision', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: item.id, decision, notes })
        });
      } catch (e) {
        console.error('Error saving decision', e);
      }

      // Auto advance to next item
      setTimeout(() => {
        nextItem();
      }, 250);
    }

    function prevItem() {
      if (currentIndex > 0) selectItem(currentIndex - 1);
    }

    function nextItem() {
      if (currentIndex < instances.length - 1) selectItem(currentIndex + 1);
    }

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT') return;
      if (e.code === 'Space') {
        e.preventDefault();
        const player = document.getElementById('audio-player');
        if (player.paused) player.play();
        else player.pause();
      } else if (e.key === '1' || e.key === 'k' || e.key === 'K') {
        submitDecision('KEEP');
      } else if (e.key === '2' || e.key === 'u' || e.key === 'U') {
        submitDecision('UNDERSPECIFIED');
      } else if (e.key === '3' || e.key === 'd' || e.key === 'D') {
        submitDecision('SLOT_DEVIATION');
      } else if (e.key === '4' || e.key === 'f' || e.key === 'F') {
        submitDecision('FILTER_OUT');
      } else if (e.key === '5' || e.key === 'n' || e.key === 'N') {
        submitDecision('NOT_SURE');
      } else if (e.key === 'ArrowLeft' || e.key === 'p' || e.key === 'P') {
        prevItem();
      } else if (e.key === 'ArrowRight' || e.key === 'j' || e.key === 'J') {
        nextItem();
      } else if (e.key === '[' || e.key === '<') {
        adjustSpeed(-1);
      } else if (e.key === ']' || e.key === '>') {
        adjustSpeed(1);
      }
    });

    window.onload = loadInstances;
  </script>
</body>
</html>
"""

class AuditHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/audio/"):
            audio_id = parsed.path.replace("/audio/", "").strip()
            found_path = None
            if os.path.exists(AUDIO_DIR):
                for root, dirs, files in os.walk(AUDIO_DIR):
                    for f in files:
                        if audio_id in f and f.endswith(".wav"):
                            found_path = os.path.join(root, f)
                            break
                    if found_path:
                        break
            if found_path and os.path.exists(found_path):
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(os.path.getsize(found_path)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/api/instances":
            self.handle_get_instances()
        elif parsed.path.startswith("/audio/"):
            audio_id = parsed.path.replace("/audio/", "").strip()
            self.handle_get_audio(audio_id)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/decision":
            self.handle_post_decision()
        else:
            self.send_error(404, "Not Found")

    def handle_get_instances(self):
        if not os.path.exists(CSV_PATH):
            self.send_error(500, "Audit CSV not found")
            return
        instances = []
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                instances.append({
                    "id": row.get("id", ""),
                    "speaker": row.get("speaker", ""),
                    "etiology": row.get("etiology", ""),
                    "duration": row.get("duration", ""),
                    "prompt": row.get("prompt", ""),
                    "spoken_text": row.get("spoken_text", ""),
                    "jaccard_sim": row.get("jaccard_sim", ""),
                    "len_ratio": row.get("len_ratio", ""),
                    "preliminary_tag": row.get("preliminary_tag", ""),
                    "recommended_tier": row.get("recommended_tier", ""),
                    "decision": row.get("user_override", "").strip(),
                    "notes": row.get("notes", "").strip() if "notes" in row else ""
                })
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(instances).encode("utf-8"))

    def handle_post_decision(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len)
        data = json.loads(post_body.decode("utf-8"))
        target_id = data.get("id")
        decision = data.get("decision", "").strip()
        notes = data.get("notes", "").strip()

        # Update CSV
        rows = []
        fieldnames = []
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames)
            if "notes" not in fieldnames:
                fieldnames.append("notes")
            for row in reader:
                if row.get("id") == target_id:
                    row["user_override"] = decision
                    row["notes"] = notes
                rows.append(row)

        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "id": target_id, "decision": decision}).encode("utf-8"))

    def handle_get_audio(self, audio_id):
        # Look for local audio file in audio_245/
        # Check by ID or matching filename
        found_path = None
        if os.path.exists(AUDIO_DIR):
            for root, dirs, files in os.walk(AUDIO_DIR):
                for f in files:
                    if audio_id in f and f.endswith(".wav"):
                        found_path = os.path.join(root, f)
                        break
                if found_path:
                    break

        if not found_path or not os.path.exists(found_path):
            self.send_error(404, f"Audio file for {audio_id} not found locally in audio_245/")
            return

        file_size = os.path.getsize(found_path)
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with open(found_path, "rb") as f:
            self.wfile.write(f.read())

def run_server(port=8765):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, AuditHandler)
    print(f"SAP Audit Workbench running at http://127.0.0.1:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    port = 8765
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
