#!/usr/bin/env python3
"""
build_annotator_ui.py

Compiles a standalone, zero-dependency HTML5 annotation webapp for labeling the 50 pilot
SAP spoken language understanding commands across Domain, Intent, and typed Slots.
"""

import json
from pathlib import Path

def build_html():
    commands_path = Path("schema_freeze/pilot/commands_50.json")
    with open(commands_path, "r", encoding="utf-8") as f:
        commands = json.load(f)

    # 10 Domains and 28 Canonical Intents
    ontology = {
        "accessibility": {
            "name": "Accessibility",
            "icon": "♿",
            "description": "Assistive OS tools (speech dictation, UI magnification/zoom)",
            "intents": {
                "accessibility_dictation_toggle": {
                    "name": "Dictation Toggle",
                    "description": "Toggle continuous voice dictation listening state",
                    "slots": [
                        {"name": "state", "type": "enum", "required": True, "options": ["on", "off", "enable", "disable"], "hint": "Listening state"}
                    ]
                },
                "accessibility_ui_scale": {
                    "name": "UI Scale & Zoom",
                    "description": "Adjust visual UI zoom, text font size, or high-contrast display",
                    "slots": [
                        {"name": "direction", "type": "enum", "required": True, "options": ["up", "down", "in", "out"], "hint": "Scale or zoom direction (brighten/raise -> up, dim/lower -> down)"},
                        {"name": "ui_element", "type": "enum", "required": False, "options": ["zoom", "text_size", "high_contrast", "screen"], "hint": "Target visual element"}
                    ]
                }
            }
        },
        "calendar_alarm": {
            "name": "Calendar & Alarm",
            "icon": "⏰",
            "description": "Time, alarms, countdown timers, meetings, appointments, and task reminders",
            "intents": {
                "alarm_manage": {
                    "name": "Alarm & Timer Manage",
                    "description": "Set, cancel, snooze, or query wake-up alarms and countdown timers",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["set", "cancel", "query", "snooze"], "hint": "Alarm operation"},
                        {"name": "time", "type": "span", "required": False, "hint": "Clock time or timer duration (e.g. 7 am, 15 minutes)"},
                        {"name": "date", "type": "span", "required": False, "hint": "Calendar date (e.g. tomorrow, thursday)"},
                        {"name": "general_frequency", "type": "enum", "required": False, "options": ["daily", "weekdays", "weekends", "weekly", "monthly"], "hint": "Recurrence (normalize every day -> daily)"}
                    ]
                },
                "schedule_manage": {
                    "name": "Schedule Manage",
                    "description": "Calendar events, meetings, appointments, deadlines, and task reminders",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["create", "delete", "query", "update"], "hint": "Schedule action"},
                        {"name": "title", "type": "span", "required": False, "hint": "Event title, appointment name, or reminder task (e.g. dentist appointment, take out trash)"},
                        {"name": "date", "type": "span", "required": False, "hint": "Event date (e.g. friday, tomorrow, october 20th)"},
                        {"name": "time", "type": "span", "required": False, "hint": "Clock time or relative offset (e.g. 2 pm, tonight, noon)"},
                        {"name": "person", "type": "span", "required": False, "hint": "Meeting attendee or participant (e.g. sarah, fred placid)"}
                    ]
                }
            }
        },
        "communication": {
            "name": "Communication",
            "icon": "📞",
            "description": "Voice and video phone calls, SMS text messages, and electronic mail",
            "intents": {
                "call_make": {
                    "name": "Make Call",
                    "description": "Place voice or video telephone calls to a contact or phone number",
                    "slots": [
                        {"name": "recipient_name", "type": "span", "required": False, "hint": "Contact person or commercial business being called (e.g. amalia adamson)"},
                        {"name": "phone_number", "type": "span", "required": False, "hint": "Spoken digits or phone number (e.g. 555-0199, 1-800-642-7676)"}
                    ]
                },
                "call_manage": {
                    "name": "Manage Call",
                    "description": "In-call controls (answer, decline, hang up, mute, unmute, redial)",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["answer", "decline", "hang_up", "mute", "unmute", "redial"], "hint": "Call control action"}
                    ]
                },
                "messages_manage": {
                    "name": "Messages Manage",
                    "description": "Compose, send, read, or reply to SMS / instant text messages",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["send", "read", "reply"], "hint": "Messaging action"},
                        {"name": "recipient", "type": "span", "required": False, "hint": "Recipient contact name (e.g. mom, dyson bunker)"},
                        {"name": "message_body", "type": "span", "required": False, "hint": "Dictated message text (e.g. i am running late)"}
                    ]
                },
                "email_manage": {
                    "name": "Email Manage",
                    "description": "Compose, send, search, or read electronic mail",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["send", "read", "search"], "hint": "Email action"},
                        {"name": "recipient", "type": "span", "required": False, "hint": "Recipient contact or address (e.g. malachi janowski, dr smith)"},
                        {"name": "date", "type": "span", "required": False, "hint": "Date filter for search/query (e.g. yesterday, friday)"},
                        {"name": "message_body", "type": "span", "required": False, "hint": "Dictated email text"}
                    ]
                }
            }
        },
        "general_qa": {
            "name": "General QA & Utility",
            "icon": "🌐",
            "description": "World knowledge, definitions, math, weather, device finder, and orders",
            "intents": {
                "qa_search": {
                    "name": "QA Search (World Knowledge)",
                    "description": "Factual web queries, recipes, news, stocks, math, definitions, video app requests",
                    "slots": [
                        {"name": "query", "type": "span", "required": True, "hint": "Verbatim factual question string (e.g. recipe with cliantro, define ubiquitous)"}
                    ]
                },
                "weather_query": {
                    "name": "Weather Query",
                    "description": "Check meteorological conditions, forecasts, and temperatures",
                    "slots": [
                        {"name": "place_name", "type": "span", "required": False, "hint": "City, state, or region (e.g. chicago, australia)"},
                        {"name": "date", "type": "span", "required": False, "hint": "Forecast date (e.g. today, tomorrow, tonight)"},
                        {"name": "weather_aspect", "type": "span", "required": False, "hint": "Meteorological condition (e.g. rain, snow, temperature)"}
                    ]
                },
                "device_find": {
                    "name": "Find Device",
                    "description": "Trigger acoustic ping to locate a misplaced hardware device",
                    "slots": [
                        {"name": "device_type", "type": "span", "required": False, "hint": "Misplaced device noun phrase (e.g. phone, ipad)"}
                    ]
                },
                "order_manage": {
                    "name": "Order Manage",
                    "description": "E-commerce parcel tracking, delivery status, and returns",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["track", "cancel", "return", "status"], "hint": "Order action"}
                    ]
                }
            }
        },
        "health": {
            "name": "Health",
            "icon": "💊",
            "description": "Prescription clinical medications, dosages, side effects, and refills",
            "intents": {
                "health_medication_reminder": {
                    "name": "Medication Reminder",
                    "description": "Schedule prescription medication or supplement dosage reminders",
                    "slots": [
                        {"name": "medication", "type": "span", "required": True, "hint": "Prescription drug or supplement name (e.g. depakote, lisinopril)"},
                        {"name": "time", "type": "span", "required": False, "hint": "Intake time or meal reference (e.g. 1 pm, dinner time)"}
                    ]
                },
                "health_refill_query": {
                    "name": "Refill Query",
                    "description": "Inquire about remaining prescription refills or pharmacy status",
                    "slots": [
                        {"name": "medication", "type": "span", "required": True, "hint": "Prescription drug name (e.g. risperidone, valium)"}
                    ]
                },
                "health_info_query": {
                    "name": "Clinical Drug Info",
                    "description": "Inquire about clinical medication side effects, interactions, or dosage",
                    "slots": [
                        {"name": "medication", "type": "span", "required": True, "hint": "Prescription drug name (e.g. atorvastatin, ibuprofen)"},
                        {"name": "info_type", "type": "enum", "required": False, "options": ["side_effects", "dosage", "interactions", "refill"], "hint": "Clinical inquiry type"}
                    ]
                }
            }
        },
        "maps_places": {
            "name": "Maps & Places",
            "icon": "📍",
            "description": "Turn-by-turn driving navigation, traffic, local store search, and dining reservations",
            "intents": {
                "maps_route": {
                    "name": "Maps Route & Directions",
                    "description": "Driving directions, navigation, route distance, or commute traffic",
                    "slots": [
                        {"name": "destination", "type": "span", "required": True, "hint": "Target destination (e.g. chicago, home, walgreens)"},
                        {"name": "query_type", "type": "enum", "required": False, "options": ["directions", "distance", "traffic"], "hint": "Type of routing query (normalize navigate -> directions)"}
                    ]
                },
                "places_search": {
                    "name": "Places Search",
                    "description": "Search for nearby stores, commercial venues, restaurants, or opening hours",
                    "slots": [
                        {"name": "business_name", "type": "span", "required": False, "hint": "Commercial brand or venue name (e.g. starbucks, trader joe's)"},
                        {"name": "business_type", "type": "span", "required": False, "hint": "Category of business (e.g. pharmacy, coffee shop)"},
                        {"name": "sort_by", "type": "enum", "required": False, "options": ["rating", "distance", "relevance"], "hint": "Sorting filter"}
                    ]
                },
                "reservations_manage": {
                    "name": "Reservations Manage",
                    "description": "Book or inspect dining table reservations at venues",
                    "slots": [
                        {"name": "business_name", "type": "span", "required": False, "hint": "Restaurant or venue name (e.g. giordano's, diaz café)"},
                        {"name": "party_size", "type": "span", "required": False, "hint": "Number of guests (e.g. two, four people)"},
                        {"name": "date", "type": "span", "required": False, "hint": "Reservation date (e.g. tomorrow, friday)"},
                        {"name": "time", "type": "span", "required": False, "hint": "Reservation time (e.g. 7 pm, dinner)"}
                    ]
                }
            }
        },
        "media": {
            "name": "Media & Playback",
            "icon": "🎵",
            "description": "Streaming audio (music, podcasts, radio, audiobooks), playback controls, and volume",
            "intents": {
                "media_play": {
                    "name": "Media Play",
                    "description": "Stream music tracks, albums, podcasts, radio stations, or audiobooks",
                    "slots": [
                        {"name": "media_type", "type": "enum", "required": False, "options": ["music", "podcast", "radio", "audiobook"], "hint": "Media category"},
                        {"name": "title", "type": "span", "required": False, "hint": "Track, album, or episode title (e.g. blinding lights)"},
                        {"name": "artist", "type": "span", "required": False, "hint": "Musician, band, or creator (e.g. the weekend, ray charles)"},
                        {"name": "house_place", "type": "span", "required": False, "hint": "Target room (e.g. living room, kitchen)"}
                    ]
                },
                "media_control": {
                    "name": "Media Control",
                    "description": "Control playback session state (pause, resume, skip, scrub, seek, like)",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["pause", "resume", "stop", "next", "previous", "like", "dislike", "fast_forward", "rewind"], "hint": "Playback operation"},
                        {"name": "duration", "type": "span", "required": False, "hint": "Seek/scrub duration (e.g. 2 minutes, 15 seconds)"}
                    ]
                },
                "media_volume": {
                    "name": "Media Volume",
                    "description": "Adjust, set, or mute audio output volume level",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["up", "down", "mute", "unmute", "set"], "hint": "Volume direction"},
                        {"name": "change_amount", "type": "span", "required": False, "hint": "Offset or target level (e.g. minimum, maximum, eight)"}
                    ]
                }
            }
        },
        "notes_memory": {
            "name": "Notes & Memory",
            "icon": "📝",
            "description": "Checklists, shopping items, and personal associative memory facts",
            "intents": {
                "lists_manage": {
                    "name": "Lists Manage",
                    "description": "Create, add items to, or query shopping and to-do lists",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["create", "add", "remove", "query"], "hint": "List action"},
                        {"name": "item", "type": "span", "required": False, "hint": "Item noun phrase (e.g. milk, paper towels)"},
                        {"name": "list_name", "type": "span", "required": False, "hint": "Title of list (e.g. shopping list, grocery list)"}
                    ]
                },
                "memory_note_manage": {
                    "name": "Memory Note Manage",
                    "description": "Store or recall personal facts and notes lacking time anchors",
                    "slots": [
                        {"name": "action", "type": "enum", "required": True, "options": ["store", "recall"], "hint": "Memory action"},
                        {"name": "key", "type": "span", "required": False, "hint": "Verbatim key (e.g. locker combination, parking space). Never hallucinate an unuttered key!"},
                        {"name": "value", "type": "span", "required": False, "hint": "Verbatim stored content (e.g. 4412, orange, level four)"}
                    ]
                }
            }
        },
        "smart_home": {
            "name": "Smart Home",
            "icon": "🏠",
            "description": "Smart appliances, lighting, door locks, thermostat, and ambient sensors",
            "intents": {
                "iot_device_power": {
                    "name": "Device Power & Locks",
                    "description": "Discrete binary power control and door locks (lock -> on, unlock -> off)",
                    "slots": [
                        {"name": "device_type", "type": "span", "required": False, "hint": "Hardware appliance, fixture, or lock (e.g. living room light, front door)"},
                        {"name": "state", "type": "enum", "required": True, "options": ["on", "off"], "hint": "Binary state (lock -> on, unlock -> off)"},
                        {"name": "house_place", "type": "span", "required": False, "hint": "Room or zone (e.g. living room, den)"}
                    ]
                },
                "iot_device_adjust": {
                    "name": "Device Adjust (Scalar)",
                    "description": "Adjust continuous settings: brightness, temperature, color, or speed",
                    "slots": [
                        {"name": "device_type", "type": "span", "required": False, "hint": "Appliance or fixture (e.g. thermostat, heat, oven)"},
                        {"name": "setting", "type": "enum", "required": False, "options": ["brightness", "temperature", "color", "speed"], "hint": "Controlled setting"},
                        {"name": "direction", "type": "enum", "required": False, "options": ["up", "down"], "hint": "Adjustment direction (raise/brighten -> up, lower/dim -> down)"},
                        {"name": "value", "type": "span", "required": False, "hint": "Target setpoint (e.g. 72 degrees, 375 degrees)"}
                    ]
                },
                "iot_sensor_query": {
                    "name": "Sensor Query",
                    "description": "Inquire about current reading of ambient indoor environmental sensors",
                    "slots": [
                        {"name": "sensor_type", "type": "enum", "required": False, "options": ["temperature", "motion"], "hint": "Sensor modality"},
                        {"name": "room", "type": "span", "required": False, "hint": "Room name (e.g. living room, inside)"}
                    ]
                }
            }
        },
        "transport": {
            "name": "Transport & Travel",
            "icon": "🚗",
            "description": "Passenger travel logistics (taxis/rideshares, public transit schedules and tickets)",
            "intents": {
                "rideshare_book": {
                    "name": "Rideshare Book",
                    "description": "Order or hail a taxi, cab, or rideshare vehicle",
                    "slots": [
                        {"name": "destination", "type": "span", "required": False, "hint": "Target arrival point (e.g. airport, downtown)"}
                    ]
                },
                "transit_lookup": {
                    "name": "Transit Lookup",
                    "description": "Check schedules or book tickets for public transit, trains, buses, flights",
                    "slots": [
                        {"name": "transit_type", "type": "enum", "required": False, "options": ["train", "bus", "flight"], "hint": "Transit mode"},
                        {"name": "destination", "type": "span", "required": False, "hint": "Target destination city/stop (e.g. chicago, detroit michigan)"},
                        {"name": "route_or_station", "type": "span", "required": False, "hint": "Route, carrier, or station (e.g. red line, southwest airlines)"},
                        {"name": "time", "type": "span", "required": False, "hint": "Departure time (e.g. 2:45 pm, next train)"}
                    ]
                }
            }
        }
    }

    commands_json_str = json.dumps(commands)
    ontology_json_str = json.dumps(ontology)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SAP SLU Benchmark — Pilot 50 Annotator</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {{
      --background: #0f172a;
      --card: #1e293b;
      --card-hover: #334155;
      --border: #334155;
      --foreground: #f8fafc;
      --muted-foreground: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --primary-foreground: #ffffff;
      --accent: #10b981;
      --accent-foreground: #ffffff;
      --warning: #f59e0b;
      --danger: #ef4444;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --background: #f8fafc;
        --card: #ffffff;
        --card-hover: #f1f5f9;
        --border: #e2e8f0;
        --foreground: #0f172a;
        --muted-foreground: #64748b;
        --primary: #2563eb;
        --primary-hover: #1d4ed8;
        --primary-foreground: #ffffff;
        --accent: #059669;
        --accent-foreground: #ffffff;
        --warning: #d97706;
        --danger: #dc2626;
      }}
    }}
    body {{
      background-color: var(--background);
      color: var(--foreground);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .custom-scroll::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    .custom-scroll::-webkit-scrollbar-thumb {{
      background: var(--border);
      border-radius: 4px;
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col text-sm antialiased select-none">

  <!-- Top App Navigation Bar -->
  <header class="border-b border-[var(--border)] bg-[var(--card)] px-6 py-3 flex items-center justify-between sticky top-0 z-30 shadow-sm">
    <div class="flex items-center space-x-3">
      <div class="w-8 h-8 rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)] flex items-center justify-center font-bold text-base shadow-sm">
        SAP
      </div>
      <div>
        <h1 class="font-bold text-base tracking-tight leading-tight">SLU Schema Pilot Annotator</h1>
        <p class="text-xs text-[var(--muted-foreground)]">Step 3 Dual-Annotator Protocol (50 Stratified Commands)</p>
      </div>
    </div>

    <!-- Annotator Selector & Progress Tracker & Actions -->
    <div class="flex items-center space-x-4">
      <div class="flex items-center space-x-1.5 text-xs">
        <span class="text-[var(--muted-foreground)]">Annotator:</span>
        <select id="annotator-select" class="px-2 py-1 rounded-lg bg-[var(--background)] border border-[var(--border)] text-xs font-semibold text-[var(--foreground)] focus:outline-none">
          <option value="annotator1">Annotator 1</option>
          <option value="annotator2">Annotator 2</option>
          <option value="custom">Custom Name...</option>
        </select>
        <input type="text" id="annotator-custom-name" placeholder="Enter name" class="hidden px-2 py-1 rounded-lg bg-[var(--background)] border border-[var(--border)] text-xs text-[var(--foreground)] w-28 focus:outline-none">
      </div>

      <div class="h-5 w-[1px] bg-[var(--border)]"></div>

      <div class="flex items-center space-x-2 text-xs">
        <span class="text-[var(--muted-foreground)]">Progress:</span>
        <span id="progress-label" class="font-semibold text-[var(--foreground)]">0 / 50</span>
        <div class="w-28 bg-[var(--background)] h-2 rounded-full overflow-hidden border border-[var(--border)]">
          <div id="progress-bar" class="bg-[var(--accent)] h-full transition-all duration-300" style="width: 0%"></div>
        </div>
      </div>

      <div class="h-5 w-[1px] bg-[var(--border)]"></div>

      <button id="btn-export-csv" class="px-3 py-1.5 rounded-lg bg-[var(--accent)] hover:opacity-90 text-[var(--accent-foreground)] font-semibold text-xs flex items-center space-x-1.5 shadow-sm transition">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
        <span>Download CSV</span>
      </button>

      <button id="btn-toggle-drawer" class="px-3 py-1.5 rounded-lg border border-[var(--border)] hover:bg-[var(--card-hover)] text-[var(--foreground)] text-xs flex items-center space-x-1.5 transition">
        <span>Command List</span>
        <span id="drawer-badge" class="px-1.5 py-0.2 rounded bg-[var(--background)] text-[11px] font-mono">50</span>
      </button>
    </div>
  </header>

  <!-- Main Content Stage -->
  <main class="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col space-y-6">

    <!-- Top Row: Command Prompt Card (Left) and Live JSON Preview (Right) -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Current Utterance Prompt Card (7 Cols) -->
      <div class="lg:col-span-7 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm flex flex-col justify-between relative overflow-hidden">
        <div>
          <div class="flex items-center justify-between text-xs text-[var(--muted-foreground)] mb-2">
            <div class="flex items-center space-x-2">
              <span id="cmd-index-badge" class="px-2 py-0.5 rounded-full bg-[var(--background)] border border-[var(--border)] font-semibold text-[var(--foreground)]">Command 1 of 50</span>
              <span id="cmd-id-badge" class="font-mono text-[var(--muted-foreground)]">ID: #160</span>
              <span id="cmd-etiology-badge" class="px-2 py-0.5 rounded bg-blue-500/10 text-blue-500 font-medium">PD;DS;CP;Stroke</span>
            </div>
            <span id="status-pill" class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-500">Unlabeled</span>
          </div>

          <div class="my-3">
            <p class="text-xs uppercase tracking-wider text-[var(--muted-foreground)] font-semibold mb-1">Spoken Utterance Transcript</p>
            <h2 id="cmd-prompt-text" class="text-2xl font-bold tracking-tight text-[var(--foreground)] select-text leading-snug cursor-text p-3 rounded-xl bg-[var(--background)]/50 border border-[var(--border)]/50">
              "Loading prompt..."
            </h2>
          </div>
        </div>

        <p class="text-xs text-[var(--muted-foreground)] mt-2 flex items-center space-x-1.5">
          <svg class="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          <span>Highlight phrase & click <em>Paste Selection</em> in Step 3 (BaseNP rule: omit <em>a, the, to, at</em>).</span>
        </p>
      </div>

      <!-- Live JSON Inspector Card (5 Cols) -->
      <div class="lg:col-span-5 bg-[var(--card)] border border-[var(--border)] rounded-2xl p-5 shadow-sm flex flex-col justify-between">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <h3 class="font-semibold text-xs uppercase tracking-wider text-[var(--muted-foreground)]">Live JSON Output</h3>
          </div>
          <span class="text-[11px] font-mono text-emerald-500 font-medium px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">Valid JSON</span>
        </div>
        <pre id="json-preview" class="flex-1 p-3.5 rounded-xl bg-[var(--background)] border border-[var(--border)] font-mono text-xs text-blue-400 overflow-x-auto leading-relaxed custom-scroll min-h-[140px] flex items-center">&#123;
  "domain": "",
  "intent": "",
  "slots": &#123;&#125;
&#125;</pre>
        <div class="flex items-center justify-between text-[11px] text-[var(--muted-foreground)] mt-2 pt-2 border-t border-[var(--border)]">
          <span>Updates automatically as you click</span>
          <span>Shortcut: <kbd class="px-1.5 py-0.5 rounded bg-[var(--background)] border border-[var(--border)] font-mono text-[10px]">Ctrl+Enter</kbd> Save & Next</span>
        </div>
      </div>

    </div>

    <!-- Bottom Container: Expanded Full-Width Selection Menu -->
    <div class="w-full bg-[var(--card)] border border-[var(--border)] rounded-2xl p-6 shadow-sm flex flex-col space-y-6">

      <!-- Step 1: Choose Domain -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <span class="w-6 h-6 rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] text-xs flex items-center justify-center font-bold">1</span>
            <h3 class="font-semibold text-base">Select Domain (1 of 10)</h3>
          </div>
          <span id="selected-domain-label" class="text-xs text-[var(--muted-foreground)] italic">None selected</span>
        </div>

        <div id="domain-grid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          <!-- Dynamically populated domains -->
        </div>
      </div>

      <!-- Step 2: Choose Intent (Filtered by Domain) -->
      <div id="step-2-container" class="opacity-50 pointer-events-none transition-all duration-200 border-t border-[var(--border)] pt-5">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <span class="w-6 h-6 rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] text-xs flex items-center justify-center font-bold">2</span>
            <h3 class="font-semibold text-base">Select Canonical Intent</h3>
          </div>
          <span id="selected-intent-label" class="text-xs text-[var(--muted-foreground)] italic">Select a domain first</span>
        </div>

        <div id="intent-grid" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          <!-- Dynamically populated intents -->
        </div>
      </div>

      <!-- Step 3: Fill Slots (Scoped to Intent) -->
      <div id="step-3-container" class="opacity-50 pointer-events-none transition-all duration-200 border-t border-[var(--border)] pt-5">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <span class="w-6 h-6 rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] text-xs flex items-center justify-center font-bold">3</span>
            <h3 class="font-semibold text-base">Fill Intent Slots (Span vs. Enum)</h3>
          </div>
          <span class="text-xs text-[var(--muted-foreground)]">Zero-argument commands default to <code class="font-mono bg-[var(--background)] px-1 py-0.5 rounded text-[11px]">&#123;&#125;</code></span>
        </div>

        <div id="slots-container" class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <!-- Dynamically generated slot inputs -->
        </div>
      </div>

      <!-- Notes / Free-text -->
      <div class="border-t border-[var(--border)] pt-4">
        <label class="block text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-1.5">Annotator Notes (Optional)</label>
        <input type="text" id="input-notes" placeholder="Flag speech disfluencies, ambiguity, or notes for adjudication..." class="w-full px-3.5 py-2 rounded-xl bg-[var(--background)] border border-[var(--border)] focus:border-[var(--primary)] focus:outline-none text-sm transition">
      </div>

      <!-- Navigation Buttons Toolbar -->
      <div class="flex items-center justify-between pt-4 border-t border-[var(--border)]">
        <button id="btn-prev" class="px-4 py-2 rounded-xl border border-[var(--border)] hover:bg-[var(--card-hover)] font-medium text-xs flex items-center space-x-1.5 transition">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
          <span>Previous (<kbd class="font-mono">Alt+&larr;</kbd>)</span>
        </button>

        <div class="flex items-center space-x-3">
          <button id="btn-clear" class="px-3.5 py-2 rounded-xl border border-[var(--border)] hover:text-red-500 font-medium text-xs transition">
            Reset Item
          </button>
          <button id="btn-save-next" class="px-5 py-2.5 rounded-xl bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-[var(--primary-foreground)] font-semibold text-xs flex items-center space-x-2 shadow transition">
            <span>Save & Next</span>
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
          </button>
        </div>
      </div>

    </div>

  </main>

  <!-- Slide-out Drawer: All 50 Commands List -->
  <div id="command-drawer" class="fixed inset-y-0 right-0 w-96 bg-[var(--card)] border-l border-[var(--border)] shadow-2xl z-50 transform translate-x-full transition-transform duration-300 flex flex-col">
    <div class="p-4 border-b border-[var(--border)] flex items-center justify-between">
      <div>
        <h3 class="font-bold text-sm">All 50 Commands</h3>
        <p class="text-xs text-[var(--muted-foreground)]">Click any item to jump directly</p>
      </div>
      <button id="btn-close-drawer" class="p-1.5 rounded-lg hover:bg-[var(--card-hover)] text-[var(--muted-foreground)]">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>

    <div class="p-3 border-b border-[var(--border)]">
      <input type="text" id="drawer-search" placeholder="Filter commands..." class="w-full px-3 py-1.5 rounded-lg bg-[var(--background)] border border-[var(--border)] text-xs focus:outline-none">
    </div>

    <div id="drawer-list" class="flex-1 overflow-y-auto p-3 space-y-1.5 custom-scroll">
      <!-- Dynamically filled drawer items -->
    </div>
  </div>

  <div id="drawer-backdrop" class="fixed inset-0 bg-black/40 z-40 hidden backdrop-blur-xs transition-opacity"></div>

  <!-- Application Logic -->
  <script>
    const ONTOLOGY = {ontology_json_str};
    const DEFAULT_COMMANDS = {commands_json_str};
    const STORAGE_KEY = "sap_slu_pilot_50_labels_v1";

    let state = {{
      currentIndex: 0,
      commands: []
    }};

    // Initialize state from localStorage or default
    function initState() {{
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {{
        try {{
          state.commands = JSON.parse(saved);
        }} catch(e) {{
          console.error("Failed to parse saved state, fallback to defaults", e);
          state.commands = JSON.parse(JSON.stringify(DEFAULT_COMMANDS));
        }}
      }} else {{
        state.commands = JSON.parse(JSON.stringify(DEFAULT_COMMANDS));
      }}
    }}

    function saveState() {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.commands));
      updateProgress();
    }}

    function currentCmd() {{
      return state.commands[state.currentIndex];
    }}

    function updateProgress() {{
      const labeledCount = state.commands.filter(c => c.domain && c.intent).length;
      const total = state.commands.length;
      const pct = Math.round((labeledCount / total) * 100);

      document.getElementById("progress-label").textContent = `${{labeledCount}} / ${{total}} (${{pct}}%)`;
      document.getElementById("progress-bar").style.width = `${{pct}}%`;
    }}

    function renderDomainGrid() {{
      const grid = document.getElementById("domain-grid");
      grid.innerHTML = "";
      const cmd = currentCmd();

      Object.keys(ONTOLOGY).forEach(domKey => {{
        const dom = ONTOLOGY[domKey];
        const isSelected = cmd.domain === domKey;

        const btn = document.createElement("button");
        btn.className = `p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${{
          isSelected
            ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--foreground)] ring-2 ring-[var(--primary)]/30 font-semibold"
            : "border-[var(--border)] hover:border-[var(--card-hover)] hover:bg-[var(--card-hover)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        }}`;
        btn.innerHTML = `
          <div class="flex items-center justify-between w-full mb-1">
            <span class="text-base">${{dom.icon}}</span>
            ${{isSelected ? '<span class="w-2 h-2 rounded-full bg-[var(--primary)]"></span>' : ''}}
          </div>
          <div class="text-xs font-medium truncate">${{dom.name}}</div>
        `;

        btn.onclick = () => selectDomain(domKey);
        grid.appendChild(btn);
      }});

      document.getElementById("selected-domain-label").textContent = cmd.domain ? ONTOLOGY[cmd.domain].name : "None selected";
    }}

    function selectDomain(domKey) {{
      const cmd = currentCmd();
      if (cmd.domain !== domKey) {{
        cmd.domain = domKey;
        cmd.intent = ""; // reset intent
        cmd.slots = {{}}; // reset slots
      }}
      renderDomainGrid();
      renderIntentGrid();
      renderSlotsForm();
      updateJsonPreview();
      saveState();
    }}

    function renderIntentGrid() {{
      const container = document.getElementById("step-2-container");
      const grid = document.getElementById("intent-grid");
      const cmd = currentCmd();

      if (!cmd.domain) {{
        container.classList.add("opacity-50", "pointer-events-none");
        grid.innerHTML = "";
        document.getElementById("selected-intent-label").textContent = "Select a domain first";
        return;
      }}

      container.classList.remove("opacity-50", "pointer-events-none");
      grid.innerHTML = "";

      const intents = ONTOLOGY[cmd.domain].intents;
      Object.keys(intents).forEach(intentKey => {{
        const intent = intents[intentKey];
        const isSelected = cmd.intent === intentKey;

        const btn = document.createElement("button");
        btn.className = `p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${{
          isSelected
            ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--foreground)] ring-2 ring-[var(--primary)]/30 font-semibold"
            : "border-[var(--border)] hover:border-[var(--card-hover)] hover:bg-[var(--card-hover)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        }}`;
        btn.innerHTML = `
          <div class="flex items-center justify-between w-full mb-1">
            <span class="text-xs font-mono font-bold text-[var(--foreground)]">${{intentKey}}</span>
            ${{isSelected ? '<span class="w-2 h-2 rounded-full bg-[var(--primary)]"></span>' : ''}}
          </div>
          <p class="text-[11px] text-[var(--muted-foreground)] line-clamp-2">${{intent.description}}</p>
        `;

        btn.onclick = () => selectIntent(intentKey);
        grid.appendChild(btn);
      }});

      document.getElementById("selected-intent-label").textContent = cmd.intent || "Choose an intent";
    }}

    function selectIntent(intentKey) {{
      const cmd = currentCmd();
      if (cmd.intent !== intentKey) {{
        cmd.intent = intentKey;
        cmd.slots = {{}}; // reset slots
      }}
      renderIntentGrid();
      renderSlotsForm();
      updateJsonPreview();
      saveState();
    }}

    function renderSlotsForm() {{
      const container = document.getElementById("step-3-container");
      const form = document.getElementById("slots-container");
      const cmd = currentCmd();

      if (!cmd.domain || !cmd.intent) {{
        container.classList.add("opacity-50", "pointer-events-none");
        form.innerHTML = "";
        return;
      }}

      container.classList.remove("opacity-50", "pointer-events-none");
      form.innerHTML = "";

      const intentDef = ONTOLOGY[cmd.domain].intents[cmd.intent];
      if (!intentDef || !intentDef.slots || intentDef.slots.length === 0) {{
        form.innerHTML = `
          <div class="p-4 rounded-xl bg-[var(--background)] border border-[var(--border)] text-xs text-[var(--muted-foreground)] text-center">
            This tool requires zero arguments. Slots default to <code class="font-mono text-blue-400">&#123;&#125;</code>.
          </div>
        `;
        return;
      }}

      intentDef.slots.forEach(slot => {{
        const slotDiv = document.createElement("div");
        slotDiv.className = "p-3.5 rounded-xl bg-[var(--background)]/60 border border-[var(--border)] flex flex-col space-y-2";

        const currentValue = cmd.slots[slot.name] || "";

        if (slot.type === "enum") {{
          // Render as clickable option pills
          let optionsHtml = slot.options.map(opt => {{
            const isOptActive = currentValue === opt;
            return `
              <button type="button" class="px-2.5 py-1 rounded-lg text-xs font-medium border transition ${{
                isOptActive
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]"
                  : "bg-[var(--card)] border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:border-[var(--card-hover)]"
              }}" onclick="setEnumSlot('${{slot.name}}', '${{opt}}')">
                ${{opt}}
              </button>
            `;
          }}).join("");

          // Allow clearing
          if (currentValue) {{
            optionsHtml += `
              <button type="button" class="px-2 py-1 rounded-lg text-xs text-red-400 hover:text-red-300 font-mono" onclick="setEnumSlot('${{slot.name}}', '')">
                &times; clear
              </button>
            `;
          }}

          slotDiv.innerHTML = `
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-1.5">
                <span class="font-mono text-xs font-bold text-[var(--foreground)]">${{slot.name}}</span>
                <span class="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-400">Categorical Enum</span>
                ${{slot.required ? '<span class="text-[10px] text-amber-500 font-bold">*req</span>' : ''}}
              </div>
              <span class="text-[11px] text-[var(--muted-foreground)]">${{slot.hint || ""}}</span>
            </div>
            <div class="flex flex-wrap gap-1.5 pt-1">
              ${{optionsHtml}}
            </div>
          `;
        }} else {{
          // Extractive Span Input
          slotDiv.innerHTML = `
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-1.5">
                <span class="font-mono text-xs font-bold text-[var(--foreground)]">${{slot.name}}</span>
                <span class="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400">Extractive Span</span>
                ${{slot.required ? '<span class="text-[10px] text-amber-500 font-bold">*req</span>' : ''}}
              </div>
              <span class="text-[11px] text-[var(--muted-foreground)]">${{slot.hint || ""}}</span>
            </div>
            <div class="flex items-center space-x-2 pt-1">
              <input type="text" id="slot-input-${{slot.name}}" value="${{currentValue}}" placeholder="${{slot.hint || 'verbatim substring...'}}"
                class="flex-1 px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
                oninput="setSpanSlot('${{slot.name}}', this.value)">
              <button type="button" class="px-2.5 py-1.5 rounded-lg border border-[var(--border)] hover:bg-[var(--card-hover)] text-[11px] text-[var(--muted-foreground)] whitespace-nowrap"
                onclick="fillFromSelection('${{slot.name}}')" title="Paste highlighted transcript text">
                Paste Selection
              </button>
            </div>
          `;
        }}

        form.appendChild(slotDiv);
      }});
    }}

    window.setEnumSlot = function(slotName, val) {{
      const cmd = currentCmd();
      if (!val) {{
        delete cmd.slots[slotName];
      }} else {{
        cmd.slots[slotName] = val;
      }}
      renderSlotsForm();
      updateJsonPreview();
      saveState();
    }};

    window.setSpanSlot = function(slotName, val) {{
      const cmd = currentCmd();
      const trimmed = val.trim();
      if (!trimmed) {{
        delete cmd.slots[slotName];
      }} else {{
        cmd.slots[slotName] = trimmed.toLowerCase();
      }}
      updateJsonPreview();
      saveState();
    }};

    window.fillFromSelection = function(slotName) {{
      const sel = window.getSelection().toString().trim().toLowerCase();
      if (!sel) {{
        alert("Please highlight/select text in the transcript prompt first!");
        return;
      }}
      // Strip leading articles/prepositions per BaseNP rule
      const baseNP = sel.replace(/^(the|a|an|at|to|in|for|with|on)\\s+/i, '');
      const input = document.getElementById(`slot-input-${{slotName}}`);
      if (input) {{
        input.value = baseNP;
        setSpanSlot(slotName, baseNP);
      }}
    }};

    function updateJsonPreview() {{
      const cmd = currentCmd();
      const output = {{
        domain: cmd.domain || "",
        intent: cmd.intent || "",
        slots: cmd.slots || {{}}
      }};
      document.getElementById("json-preview").textContent = JSON.stringify(output, null, 2);

      // Update status pill
      const isDone = cmd.domain && cmd.intent;
      const statusPill = document.getElementById("status-pill");
      if (isDone) {{
        statusPill.className = "px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-500";
        statusPill.textContent = "Labeled";
      }} else {{
        statusPill.className = "px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-500";
        statusPill.textContent = "Unlabeled";
      }}
    }}

    function renderCurrentCommand() {{
      const cmd = currentCmd();
      document.getElementById("cmd-index-badge").textContent = `Command ${{state.currentIndex + 1}} of ${{state.commands.length}}`;
      document.getElementById("cmd-id-badge").textContent = `ID: #${{cmd.id}}`;
      document.getElementById("cmd-etiology-badge").textContent = cmd.etiology || "SAP";
      document.getElementById("cmd-prompt-text").textContent = `"${{cmd.prompt}}"`;
      document.getElementById("input-notes").value = cmd.notes || "";

      renderDomainGrid();
      renderIntentGrid();
      renderSlotsForm();
      updateJsonPreview();
      updateProgress();
      renderDrawerList();
    }}

    function goToIndex(idx) {{
      if (idx < 0 || idx >= state.commands.length) return;
      state.currentIndex = idx;
      renderCurrentCommand();
    }}

    function nextCommand() {{
      if (state.currentIndex < state.commands.length - 1) {{
        goToIndex(state.currentIndex + 1);
      }} else {{
        alert("You have reached the end of the 50 pilot commands! Check your annotations and export the CSV.");
      }}
    }}

    function prevCommand() {{
      if (state.currentIndex > 0) {{
        goToIndex(state.currentIndex - 1);
      }}
    }}

    function renderDrawerList(filterText = "") {{
      const list = document.getElementById("drawer-list");
      list.innerHTML = "";

      state.commands.forEach((cmd, idx) => {{
        if (filterText && !cmd.prompt.toLowerCase().includes(filterText.toLowerCase()) && !cmd.intent.toLowerCase().includes(filterText.toLowerCase())) {{
          return;
        }}

        const isCurrent = idx === state.currentIndex;
        const isDone = cmd.domain && cmd.intent;

        const item = document.createElement("div");
        item.className = `p-2.5 rounded-xl border cursor-pointer text-xs transition flex items-center justify-between ${{
          isCurrent
            ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--foreground)] font-semibold"
            : "border-[var(--border)] hover:bg-[var(--card-hover)] text-[var(--muted-foreground)]"
        }}`;

        item.innerHTML = `
          <div class="flex items-center space-x-2 truncate">
            <span class="w-5 text-right font-mono text-[11px]">${{idx + 1}}.</span>
            <span class="truncate max-w-[200px]">${{cmd.prompt}}</span>
          </div>
          <div class="flex items-center space-x-1.5 ml-2">
            ${{isDone ? '<span class="text-emerald-500 font-bold">&#10003;</span>' : '<span class="text-amber-500 text-[10px]">&#9679;</span>'}}
            <span class="font-mono text-[10px] truncate max-w-[70px]">${{cmd.intent || ""}}</span>
          </div>
        `;

        item.onclick = () => {{
          goToIndex(idx);
          toggleDrawer(false);
        }};

        list.appendChild(item);
      }});
    }}

    function toggleDrawer(open) {{
      const drawer = document.getElementById("command-drawer");
      const backdrop = document.getElementById("drawer-backdrop");
      if (open) {{
        drawer.classList.remove("translate-x-full");
        backdrop.classList.remove("hidden");
      }} else {{
        drawer.classList.add("translate-x-full");
        backdrop.classList.add("hidden");
      }}
    }}

    function getAnnotatorFilename() {{
      const select = document.getElementById("annotator-select");
      const selectVal = select ? select.value : "annotator1";
      if (selectVal === "custom") {{
        const customInput = document.getElementById("annotator-custom-name");
        const raw = customInput ? customInput.value.trim() : "";
        const clean = raw.toLowerCase().replace(/[^a-z0-9]/g, "_") || "custom";
        return `SLU_pilot_50_${{clean}}.csv`;
      }}
      return `SLU_pilot_50_${{selectVal}}.csv`;
    }}

    function exportCsv() {{
      const headers = ["id", "prompt", "domain", "intent", "slots_json", "notes"];
      const rows = state.commands.map(c => [
        c.id,
        `"${{c.prompt.replace(/"/g, '""')}}"`,
        c.domain || "",
        c.intent || "",
        `"${{JSON.stringify(c.slots || {{}}).replace(/"/g, '""')}}"`,
        `"${{(c.notes || "").replace(/"/g, '""')}}"`
      ]);

      const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\\n");
      const blob = new Blob([csvContent], {{ type: "text/csv;charset=utf-8;" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const filename = getAnnotatorFilename();
      link.setAttribute("href", url);
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      const labeledCount = state.commands.filter(c => c.domain && c.intent).length;
      alert(`Export Successful!\\n\\nSaved file: ${{filename}}\\nLabeled: ${{labeledCount}} / ${{state.commands.length}} commands.\\n\\nPlease save or send this file for agreement computation.`);
    }}

    // Annotator Selector Handlers
    const annotatorSelect = document.getElementById("annotator-select");
    const annotatorCustomName = document.getElementById("annotator-custom-name");

    if (annotatorSelect) {{
      annotatorSelect.onchange = (e) => {{
        const val = e.target.value;
        if (val === "custom") {{
          annotatorCustomName.classList.remove("hidden");
        }} else {{
          annotatorCustomName.classList.add("hidden");
        }}
        localStorage.setItem("sap_slu_annotator_choice", val);
      }};

      // Restore saved annotator choice
      const savedChoice = localStorage.getItem("sap_slu_annotator_choice");
      if (savedChoice) {{
        annotatorSelect.value = savedChoice;
        if (savedChoice === "custom") {{
          annotatorCustomName.classList.remove("hidden");
          annotatorCustomName.value = localStorage.getItem("sap_slu_annotator_custom") || "";
        }}
      }}
    }}

    if (annotatorCustomName) {{
      annotatorCustomName.oninput = (e) => {{
        localStorage.setItem("sap_slu_annotator_custom", e.target.value);
      }};
    }}

    // Event Listeners
    document.getElementById("btn-prev").onclick = prevCommand;
    document.getElementById("btn-save-next").onclick = nextCommand;
    document.getElementById("btn-clear").onclick = () => {{
      const cmd = currentCmd();
      cmd.domain = "";
      cmd.intent = "";
      cmd.slots = {{}};
      cmd.notes = "";
      renderCurrentCommand();
      saveState();
    }};

    document.getElementById("input-notes").oninput = (e) => {{
      currentCmd().notes = e.target.value;
      saveState();
    }};

    document.getElementById("btn-toggle-drawer").onclick = () => toggleDrawer(true);
    document.getElementById("btn-close-drawer").onclick = () => toggleDrawer(false);
    document.getElementById("drawer-backdrop").onclick = () => toggleDrawer(false);
    document.getElementById("drawer-search").oninput = (e) => renderDrawerList(e.target.value);
    document.getElementById("btn-export-csv").onclick = exportCsv;

    // Keyboard Shortcuts
    document.addEventListener("keydown", (e) => {{
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {{
        e.preventDefault();
        nextCommand();
      }} else if (e.altKey && e.key === "ArrowRight") {{
        e.preventDefault();
        nextCommand();
      }} else if (e.altKey && e.key === "ArrowLeft") {{
        e.preventDefault();
        prevCommand();
      }}
    }});

    // Boot
    initState();
    renderCurrentCommand();
  </script>
</body>
</html>
"""
    return html_content

def main():
    html = build_html()
    
    # Save to workspace
    ws_path = Path("schema_freeze/pilot/slu_annotator.html")
    ws_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ws_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved workspace webapp to: {ws_path}")

    # Save to artifact directory
    art_path = Path("/Users/zixuan/.gemini/antigravity/brain/d7a20471-35ed-4e09-afdc-7831b1009415/slu_annotator.html")
    with open(art_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved artifact webapp to: {art_path}")

if __name__ == "__main__":
    main()
