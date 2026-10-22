# Speech Accessibility Project (SAP) — SLU Benchmark
# Canonical Tool Catalog & Detailed Signatures (29 Tools)

This document provides the exhaustive, detailed parameter definitions, slot types, inclusions, exclusions, and concrete examples for all **29 Canonical Tools (Intents)** across the **10 Functional Domains**.

For high-level annotation guidelines, 3-step decision flow, and the parameter quick-reference table, see [`SLU_annotator_guidelines.md`](file:///Users/zixuan/agy2-projects/sap-dialog-system/schema_freeze/SLU_annotator_guidelines.md).

---

## 1. Parameter Quick-Reference (Span vs. Enum Classification)

Every parameter in the SAP benchmark belongs strictly to one of two mutually exclusive types: **Categorical Enum** or **Extractive Span**.

### Categorical Enums (Closed Predefined Menus)
*Must be selected strictly from the allowed literals below. Never invent synonyms.*

| Parameter Name | Target Tools | Allowed Enum Values & Normalization Rules |
| :--- | :--- | :--- |
| `action` | Various | Scoped by tool:<br>• `alarm_manage`: `["set", "cancel", "query", "snooze"]`<br>• `schedule_manage`: `["create", "delete", "query", "update"]`<br>• `call_manage`: `["answer", "decline", "hang_up", "mute", "unmute", "redial"]`<br>• `messages_manage`: `["send", "read", "reply"]`<br>• `email_manage`: `["send", "read", "search"]`<br>• `order_manage`: `["track", "cancel", "return", "status"]`<br>• `media_control`: `["pause", "resume", "stop", "next", "previous", "like", "dislike", "fast_forward", "rewind"]`<br>• `media_volume`: `["up", "down", "mute", "unmute", "set"]`<br>• `lists_manage`: `["create", "add", "remove", "query"]`<br>• `memory_note_manage`: `["store", "recall"]` |
| `state` | `accessibility_dictation_toggle`<br>`iot_device_power` | `["on", "off", "enable", "disable"]`<br>*(Door locks: lock $\rightarrow$ `"on"`, unlock $\rightarrow$ `"off"`)* |
| `direction` | `accessibility_ui_scale`<br>`iot_device_adjust` | `["up", "down", "in", "out"]`<br>*(Normalize: brighten/raise $\rightarrow$ `"up"`, darken/dim/lower $\rightarrow$ `"down"`)* |
| `media_type` | `media_play`<br>`media_search` | `["music", "podcast", "radio", "audiobook", "movie", "tv_show"]` |
| `query_type` | `maps_route` | `["directions", "distance", "traffic"]`<br>*(Normalize: navigate/route $\rightarrow$ `"directions"`)* |
| `info_type` | `health_info_query` | `["side_effects", "dosage", "interactions", "refill"]` |
| `ui_element` | `accessibility_ui_scale` | `["zoom", "text_size", "high_contrast", "screen"]` |
| `setting` | `iot_device_adjust` | `["brightness", "temperature", "color", "speed"]` |
| `sort_by` | `places_search` | `["rating", "distance", "relevance"]` |
| `general_frequency`| `alarm_manage` | `["daily", "weekdays", "weekends", "weekly", "monthly"]`<br>*(Normalize: every day $\rightarrow$ `"daily"`)* |
| `transit_type` | `transit_lookup` | `["train", "bus", "flight"]` |
| `sensor_type` | `iot_sensor_query` | `["temperature", "motion", "lock", "contact"]` |

---

### Extractive Spans (Verbatim Substrings)
*Must be exact literal substrings from the transcript in lowercase. Apply BaseNP rule: exclude leading prepositions (`at`, `to`, `for`, `in`, `on`, `with`) and articles (`a`, `an`, `the`). Do NOT correct spelling or grammar. Never hallucinate unuttered entities.*

| Parameter Name | Target Tools | Extraction Rule & Concrete Examples |
| :--- | :--- | :--- |
| `device_type` | `iot_device_power`<br>`iot_device_adjust`<br>`device_find` | Target appliance, light, switch, lock, or finder hardware (e.g. `"living room light"`, `"t v"`, `"fan"`, `"thermostat"`, `"front door"`, `"phone"`). |
| `medication` | `health_*` | Exact prescription drug or supplement name (e.g. `"lisinopril"`, `"depakote"`, `"vitamin d"`). |
| `title` | `media_play`<br>`schedule_manage` | Media track/album/show title, or event/meeting/task description (e.g. `"blinding lights"`, `"dentist appointment"`, `"take out the trash"`, `"kerstin's recital"`). |
| `artist` | `media_play` | Musician, band, or podcast creator (e.g. `"taylor swift"`, `"the beatles"`, `"ray charles"`). |
| `destination` | `maps_route`<br>`rideshare_book`<br>`transit_lookup` | Target geographic location, city, street, or venue (e.g. `"chicago"`, `"home"`, `"walgreens"`, `"airport"`). |
| `origin` | `maps_route` | Starting geographic location or departure point (e.g. `"montreal, canada"`, `"home"`). |
| `recipient_name` | `call_make` | Recipient person or business being called (e.g. `"caleb neville"`, `"walgreens"`). |
| `recipient` | `messages_manage`<br>`email_manage` | Recipient contact name or email address (e.g. `"mom"`, `"malachi janowski"`, `"dr smith"`). |
| `person` | `schedule_manage` | Meeting attendee or participant name (e.g. `"sarah"`, `"nelida ausra"`, `"fred placid"`). |
| `phone_number` | `call_make` | Spoken telephone digits or numbers (e.g. `"555 0199"`, `"1-800-642-7676"`). |
| `message_body` | `messages_manage`<br>`email_manage` | Dictated text message or email content (e.g. `"i am running late"`). |
| `business_name` | `places_search`<br>`reservations_manage` | Commercial venue or brand name (e.g. `"starbucks"`, `"trader joe's"`, `"giordano's"`). |
| `business_type` | `places_search` | Category of commercial venue (e.g. `"pharmacy"`, `"italian restaurant"`, `"coffee shop"`). |
| `place_name` | `weather_query` | City, state, or region for weather queries (e.g. `"chicago"`, `"australia"`, `"miami"`). |
| `date` | Various | Calendar day or relative date expression (e.g. `"tomorrow"`, `"october 20th"`, `"friday"`, `"tonight"`). |
| `time` | Various | Clock time or meal timestamp (e.g. `"7 am"`, `"two thirty p m"`, `"dinner"`, `"noon"`). |
| `change_amount` | `media_volume` | Scalar volume offset or target level (e.g. `"two levels"`, `"maximum"`, `"eight"`). |
| `duration` | `media_control` | Scrubbing offset or seek duration (e.g. `"two minutes"`, `"15 seconds"`, `"thirty seconds"`). |
| `item` | `lists_manage` | List item noun phrase (e.g. `"milk"`, `"paper towels and cereal"`). |
| `list_name` | `lists_manage` | Title of list (e.g. `"grocery list"`, `"shopping list"`, `"dollar general shopping list"`). |
| `key` / `value` | `memory_note_manage` | Verbatim memory associative key and stored content (e.g. `key: "locker combination"`, `value: "4412"`). **Never hallucinate an unuttered key** (do not invent `"parking_space"` if unmentioned). |
| `party_size` | `reservations_manage` | Number of reservation guests (e.g. `"four"`, `"eight"`). |
| `query` | `qa_search` | Verbatim factual question text (e.g. `"who was the 16th president"`, `"how many grams in an ounce"`). |
| `route_or_station` | `transit_lookup` | Public line, flight airline, or station name (e.g. `"red line"`, `"southwest airlines"`, `"grand central"`). |
| `service` | `media_play` | Streaming app or service provider (e.g. `"hulu"`, `"paramount plus"`, `"spotify"`, `"apple music"`). |
| `genre` | `media_search` | Media category, genre, or style (e.g. `"horror"`, `"comedy"`, `"rock"`). |
| `house_place` / `room` | `media_play`<br>`smart_home` | Residential room or location (e.g. `"kitchen"`, `"living room"`, `"den"`). |
| `weather_aspect` | `weather_query` | Meteorological condition queried (e.g. `"rain"`, `"snow"`, `"temperature"`). |

---

---

## 2. Canonical Tool Catalog (29 Tools)

### Domain: `accessibility`

#### 1. `accessibility_dictation_toggle`
* **Description:** Toggle speech-to-text dictation listening state for motor-impaired users.
* **Inclusion:** Commands asking to start/stop listening, mute/unmute microphone for dictation.
* **Slots:**
  * `state` (**Categorical Enum**, required): `["on", "off", "enable", "disable"]`
* **Examples:**
  * *"Start listening."* $\rightarrow$ `{"state": "on"}`
  * *"Stop dictation."* $\rightarrow$ `{"state": "off"}`

#### 2. `accessibility_ui_scale`
* **Description:** Adjust visual interface zoom, text font size, or high-contrast display for visual impairment.
* **Inclusion:** Commands asking to make screen bigger, zoom in/out, increase font size.
* **Exclusion:** Does not apply to adjusting room lighting (route to `iot_device_adjust`).
* **Slots:**
  * `ui_element` (**Categorical Enum**, optional): `["zoom", "text_size", "high_contrast", "screen"]`
  * `direction` (**Categorical Enum**, required): `["up", "down", "in", "out"]`
* **Examples:**
  * *"Zoom in on the screen."* $\rightarrow$ `{"ui_element": "zoom", "direction": "in"}`
  * *"Make the text larger."* $\rightarrow$ `{"ui_element": "text_size", "direction": "up"}`

---

### Domain: `calendar_alarm`

#### 3. `alarm_manage`
* **Description:** Set, cancel, snooze, or query wake-up alarms and countdown timers.
* **Inclusion:** Commands containing `"alarm"`, `"wake up"`, `"timer"`, or relative countdown durations (*"set timer for 10 minutes"*).
* **Exclusion:** Meetings, appointments, calendar events, or task reminders route to `schedule_manage`.
* **Slots:**
  * `action` (**Categorical Enum**, required): `["set", "cancel", "query", "snooze"]`
  * `time` (**Extractive Span**, optional): Clock time or duration (*"seven thirty a m"*, *"ten minutes"*)
  * `date` (**Extractive Span**, optional): Date (*"tomorrow"*, *"thursday and friday"*). *(Note: Coordinated multi-day targets without explicit recurrence adverbs belong in `date`; do not infer frequency).*
  * `general_frequency` (**Categorical Enum**, optional): `["daily", "weekdays", "weekends", "weekly", "monthly"]`. *(Constraint: Populate ONLY when an explicit recurrence token is uttered like "daily", "weekdays", "every Tuesday").*
* **Examples:**
  * *"Wake me up tomorrow at 7 AM."* $\rightarrow$ `{"action": "set", "time": "7 am", "date": "tomorrow"}`
  * *"Set an alarm for 3:45 PM on Thursday and Friday."* $\rightarrow$ `{"action": "set", "time": "3:45 pm", "date": "thursday and friday"}`
  * *"Set an alarm for 6:30 PM Daily."* $\rightarrow$ `{"action": "set", "time": "6:30 pm", "general_frequency": "daily"}`
  * *"Set a timer for 15 minutes."* $\rightarrow$ `{"action": "set", "time": "15 minutes"}`
  * *"Snooze."* $\rightarrow$ `{"action": "snooze"}`

#### 4. `schedule_manage`
* **Description:** Create, reschedule, cancel, or inspect calendar events, appointments, and task reminders.
* **Inclusion:** Events, meetings, appointments, deadlines, and to-do reminders anchored to a date or time.
* **Slots:**
  * `action` (**Categorical Enum**, required): `["create", "delete", "query", "update"]`
  * `title` (**Extractive Span**, optional): Event title, appointment name, reminder task description, or generic event noun (*"dentist appointment"*, *"meeting"*, *"call"*, *"appointment"*, *"take out the trash"*). *(Constraint: When an utterance specifies a generic event type without a custom topic, e.g. "Cancel my meeting with Sanjiv", retain "meeting" in `title`).*
  * `date` (**Extractive Span**, optional): Date (*"friday"*, *"october 20th"*, *"tomorrow"*)
  * `time` (**Extractive Span**, optional): Time (*"two o'clock"*, *"2 pm"*, *"tonight"*, *"noon"*)
  * `person` (**Extractive Span**, optional): Attendee or participant name (*"sarah"*, *"fred placid"*, *"nelida ausra"*)
* **Examples:**
  * *"Add dentist appointment on Friday at 2 PM."* $\rightarrow$ `{"action": "create", "title": "dentist appointment", "date": "friday", "time": "2 pm"}`
  * *"Cancel my meeting with Sanjiv Lynne at 2:30 PM, Tuesday the 9th."* $\rightarrow$ `{"action": "delete", "title": "meeting", "person": "sanjiv lynne", "time": "2:30 pm", "date": "tuesday the 9th"}`
  * *"Remind me to take out the trash tonight."* $\rightarrow$ `{"action": "create", "title": "take out the trash", "time": "tonight"}`
  * *"What is on my calendar today?"* $\rightarrow$ `{"action": "query", "date": "today"}`
  * *"Delete my reminders for tomorrow."* $\rightarrow$ `{"action": "delete", "date": "tomorrow"}`
  * *"Reschedule my meeting with Fred Placid at 11:30, September 18th."* $\rightarrow$ `{"action": "update", "title": "meeting", "person": "fred placid", "time": "11:30", "date": "september 18th"}`

---

### Domain: `communication`

#### 5. `call_make`
* **Description:** Place voice or video telephone calls to a contact or phone number.
* **Slots:**
  * `recipient_name` (**Extractive Span**, optional): Person or business (*"caleb neville"*, *"walgreens"*)
  * `phone_number` (**Extractive Span**, optional): Digits (*"555 0199"*)
* **Examples:**
  * *"Call Caleb Neville."* $\rightarrow$ `{"recipient_name": "caleb neville"}`
  * *"Call 555-0123."* $\rightarrow$ `{"phone_number": "555-0123"}`

#### 6. `call_manage`
* **Description:** In-call handling: answer, decline, end, mute, or redial telephone calls.
* **Slots:**
  * `action` (**Categorical Enum**, required): `["answer", "decline", "hang_up", "mute", "unmute", "redial"]`
* **Examples:**
  * *"Hang up the call."* $\rightarrow$ `{"action": "hang_up"}`
  * *"Decline incoming call."* $\rightarrow$ `{"action": "decline"}`
  * *"Redial."* $\rightarrow$ `{"action": "redial"}`

#### 7. `messages_manage`
* **Description:** Compose, send, read, or manage SMS text messages.
* **Slots:**
  * `action` (**Categorical Enum**, required): `["send", "read", "reply"]`
  * `recipient` (**Extractive Span**, optional): Contact name (*"mom"*, *"john"*)
  * `message_body` (**Extractive Span**, optional): Dictated text (*"i am running late"*)
* **Examples:**
  * *"Please send this text."* $\rightarrow$ `{"action": "send"}`
  * *"Read my messages."* $\rightarrow$ `{"action": "read"}`

#### 8. `email_manage`
* **Description:** Compose, send, search, or read electronic mail.
* **Slots:**
  * `action` (**Categorical Enum**, required): `["send", "read", "search"]`
  * `recipient` (**Extractive Span**, optional): Recipient name or email (*"dr smith"*)
  * `date` (**Extractive Span**, optional): Date
  * `message_body` (**Extractive Span**, optional): Email body
* **Examples:**
  * *"Check my unread emails."* $\rightarrow$ `{"action": "read"}`
  * *"Send an email to Dr Smith."* $\rightarrow$ `{"action": "send", "recipient": "dr smith"}`

---

### Domain: `general_qa`

#### 9. `qa_search`
* **Description:** Open-domain factual web queries, encyclopedia knowledge, recipes, news briefings, stock prices, and math calculations.
* **Exclusion:** Local store searches route to `places_search`; driving route directions route to `maps_route`; weather queries route to `weather_query`.
* **Slots:**
  * `query` (**Extractive Span**, required): Full verbatim query string.
* **Examples:**
  * *"Who was the 16th president of the United States?"* $\rightarrow$ `{"query": "who was the 16th president of the united states"}`
  * *"How many grams in an ounce?"* $\rightarrow$ `{"query": "how many grams in an ounce"}`
  * *"How do I bake lasagna?"* $\rightarrow$ `{"query": "how do i bake lasagna"}`

#### 10. `weather_query`
* **Description:** Check meteorological weather conditions, forecasts, and temperature.
* **Slots:**
  * `place_name` (**Extractive Span**, optional): City/region (*"chicago"*, *"seattle"*)
  * `date` (**Extractive Span**, optional): Date (*"tomorrow"*, *"this weekend"*)
  * `weather_aspect` (**Extractive Span**, optional): Condition (*"rain"*, *"snow"*, *"temperature"*)
* **Examples:**
  * *"Is it going to rain in Chicago tomorrow?"* $\rightarrow$ `{"place_name": "chicago", "date": "tomorrow", "weather_aspect": "rain"}`
  * *"What is the weather today?"* $\rightarrow$ `{"date": "today"}`

#### 11. `device_find`
* **Description:** Trigger an audible acoustic ping to locate a misplaced hardware device.
* **Slots:**
  * `device_type` (**Extractive Span**, optional): Misplaced device (*"phone"*, *"ipad"*)
* **Examples:**
  * *"Find my phone."* $\rightarrow$ `{"device_type": "phone"}`

#### 12. `order_manage`
* **Description:** Manage e-commerce parcel tracking, delivery status, and returns.
* **Slots:**
  * `action` (**Categorical Enum**, required): `["track", "cancel", "return", "status"]`
* **Examples:**
  * *"Where is my package?"* $\rightarrow$ `{"action": "track"}`

---

### Domain: `health`

#### 13. `health_medication_reminder`
* **Description:** Schedule prescription medication or supplement dosage reminders.
* **Inclusion:** Explicitly mentions a medication, pill, vitamin, or supplement intake time.
* **Slots:**
  * `medication` (**Extractive Span**, required): Drug name (*"lisinopril"*, *"insulin"*, *"vitamin d"*)
  * `time` (**Extractive Span**, optional): Intake time (*"eight a m"*, *"dinner"*)
* **Examples:**
  * *"Remind me to take my Lisinopril at 8 AM."* $\rightarrow$ `{"medication": "lisinopril", "time": "8 am"}`

#### 14. `health_refill_query`
* **Description:** Inquire about remaining prescription refills or pharmacy status.
* **Slots:**
  * `medication` (**Extractive Span**, required): Drug name (*"atorvastatin"*)
* **Examples:**
  * *"Do I have any refills left on my Atorvastatin?"* $\rightarrow$ `{"medication": "atorvastatin"}`

#### 15. `health_info_query`
* **Description:** Inquire about clinical medication side effects, drug interactions, or dosage guidelines.
* **Slots:**
  * `medication` (**Extractive Span**, required): Drug name (*"ibuprofen"*)
  * `info_type` (**Categorical Enum**, optional): `["side_effects", "dosage", "interactions"]`
* **Examples:**
  * *"Can I take Ibuprofen with Tylenol?"* $\rightarrow$ `{"medication": "ibuprofen", "info_type": "interactions"}`

---

### Domain: `maps_places`

#### 16. `maps_route`
* **Description:** Request driving directions, navigation, route distance, or commute traffic conditions.
* **Slots:**
  * `destination` (**Extractive Span**, required): Target destination (*"chicago"*, *"home"*, *"nearest hospital"*)
  * `origin` (**Extractive Span**, optional): Starting location or departure point (*"montreal, canada"*, *"home"*)
  * `query_type` (**Categorical Enum**, optional): `["directions", "distance", "traffic"]` *(Phrases like "navigate to..." or "map a route" normalize to `"directions"`)*
* **Examples:**
  * *"Give me directions to Chicago."* $\rightarrow$ `{"destination": "chicago", "query_type": "directions"}`
  * *"Navigate to Walgreens."* $\rightarrow$ `{"destination": "walgreens", "query_type": "directions"}`
  * *"How far is Virginia?"* $\rightarrow$ `{"destination": "virginia", "query_type": "distance"}`
  * *"How far is Brattleboro, Vermont from Montreal, Canada?"* $\rightarrow$ `{"destination": "brattleboro, vermont", "origin": "montreal, canada", "query_type": "distance"}`
  * *"How is traffic on I-80?"* $\rightarrow$ `{"destination": "i-80", "query_type": "traffic"}`

#### 17. `places_search`
* **Description:** Search for nearby physical venues, stores, restaurants, or business hours and operating metadata.
* **Inclusion:** Inquiries about whether a business is open or closing times (e.g. *"When is Bed, Bath and Beyond open until?"*) belong to `places_search`, not `qa_search`.
* **Slots:**
  * `business_name` (**Extractive Span**, optional): Store name (*"starbucks"*, *"walgreens"*)
  * `business_type` (**Extractive Span**, optional): Category (*"pharmacy"*, *"italian restaurant"*)
  * `sort_by` (**Categorical Enum**, optional): `["rating", "distance", "relevance"]`
* **Examples:**
  * *"Find a pharmacy near me."* $\rightarrow$ `{"business_type": "pharmacy"}`
  * *"Where is the closest Starbucks?"* $\rightarrow$ `{"business_name": "starbucks", "sort_by": "distance"}`

#### 18. `reservations_manage`
* **Description:** Book or inspect dining table reservations at restaurants or venues.
* **Slots:**
  * `business_name` (**Extractive Span**, optional): Restaurant (*"giordano's"*)
  * `time` (**Extractive Span**, optional): Time (*"seven p m"*)
  * `party_size` (**Extractive Span**, optional): Number of people (*"four"*)
  * `date` (**Extractive Span**, optional): Date (*"tomorrow"*)
* **Examples:**
  * *"Book a table for 4 at Giordano's tomorrow at 7 PM."* $\rightarrow$ `{"business_name": "giordano's", "party_size": "4", "date": "tomorrow", "time": "7 pm"}`

---

### Domain: `media`

#### 19. `media_play`
* **Description:** Initiate playback of music, podcasts, radio stations, audiobooks, movies, or video streaming services.
* **Slots:**
  * `media_type` (**Categorical Enum**, optional): `["music", "podcast", "radio", "audiobook", "movie", "tv_show"]`
  * `title` (**Extractive Span**, optional): Track, album, movie, or episode title (*"billboard top 40"*, *"the daily"*, *"transformers"*)
  * `artist` (**Extractive Span**, optional): Musician or host (*"taylor swift"*, *"the beatles"*)
  * `service` (**Extractive Span**, optional): Streaming app or platform (*"hulu"*, *"paramount plus"*, *"spotify"*)
  * `house_place` (**Extractive Span**, optional): Room (*"living room"*)
* **Examples:**
  * *"Play music by The Beatles."* $\rightarrow$ `{"media_type": "music", "artist": "beatles"}`
  * *"Play 'Transformers' on Paramount Plus."* $\rightarrow$ `{"media_type": "movie", "title": "transformers", "service": "paramount plus"}`
  * *"Open Hulu."* $\rightarrow$ `{"service": "hulu"}`

#### 20. `media_search`
* **Description:** Search, browse, or recommend movies, shows, songs, albums, or audiobooks without immediate playback actuation.
* **Inclusion:** Commands asking to show, find, browse, or recommend media (*"Show me movies with Benicio Del Toro"*, *"Recommend a comedy podcast"*).
* **Slots:**
  * `media_type` (**Categorical Enum**, optional): `["movie", "tv_show", "music", "podcast", "audiobook"]`
  * `person` (**Extractive Span**, optional): Actor, director, or musician (*"benicio del toro"*, *"christopher nolan"*)
  * `genre` (**Extractive Span**, optional): Genre or category (*"comedy"*, *"action"*, *"documentary"*)
  * `title` (**Extractive Span**, optional): Franchise or title query (*"batman"*)
* **Examples:**
  * *"Show me movies with Benicio Del Toro."* $\rightarrow$ `{"media_type": "movie", "person": "benicio del toro"}`
  * *"Find comedy podcasts."* $\rightarrow$ `{"media_type": "podcast", "genre": "comedy"}`

#### 21. `media_control`
* **Description:** Control playback state (pause, resume, stop, next track, skip backward, fast forward, like, dislike).
* **Slots:**
  * `action` (**Categorical Enum**, required): `["pause", "resume", "stop", "next", "previous", "like", "dislike", "fast_forward", "rewind"]`
  * `duration` (**Extractive Span**, optional): Time scrubbed (*"two minutes"*, *"10 seconds"*)
* **Examples:**
  * *"Pause the music."* $\rightarrow$ `{"action": "pause"}`
  * *"Fast forward 2 minutes."* $\rightarrow$ `{"action": "fast_forward", "duration": "2 minutes"}`
  * *"Like this song."* $\rightarrow$ `{"action": "like"}`

#### 22. `media_volume`
* **Description:** Adjust or mute audio output volume level.
* **Slots:**
  * `action` (**Categorical Enum**, required): `["up", "down", "mute", "unmute", "set"]`
  * `change_amount` (**Extractive Span**, optional): Offset or target level (*"two levels"*, *"maximum"*, *"halfway"*)
* **Examples:**
  * *"Turn the volume up."* $\rightarrow$ `{"action": "up"}`
  * *"Decrease volume to minimum."* $\rightarrow$ `{"action": "down", "change_amount": "minimum"}`

---

### Domain: `notes_memory`

#### 23. `lists_manage`
* **Description:** Create, view, add items to, or remove items from shopping or to-do lists.
* **Slots:**
  * `action` (**Categorical Enum**, required): `["create", "add", "remove", "query"]`
  * `item` (**Extractive Span**, optional): Item noun phrase (*"milk"*, *"paper towels"*)
  * `list_name` (**Extractive Span**, optional): List name (*"grocery list"*)
* **Examples:**
  * *"Add milk to my grocery list."* $\rightarrow$ `{"action": "add", "item": "milk", "list_name": "grocery list"}`
  * *"What is on my shopping list?"* $\rightarrow$ `{"action": "query", "list_name": "shopping list"}`

#### 24. `memory_note_manage`
* **Description:** Store or recall user personal notes, memos, and facts that **lack a specific trigger date or time**.
* **Span Extraction Rules:**
  * `key` and `value` must be literal substrings from the command. Never hallucinate an unmentioned key (e.g. for *"Where did I park?"*, leave slots as `{"action": "recall"}`).
  * **Associative Attributes ($X$ is $Y$):** Extract both `key` and `value` (e.g. *"Our parking space is green"* $\rightarrow$ `key: "parking space"`, `value: "green"`).
  * **Declarative Clauses (Unkeyed):** For freeform clauses, do NOT fracture the phrase into an artificial key. Strip carrier prefixes (*"remember that"*) and store the entire statement in `value`, leaving `key` empty (e.g. *"Remember that we're out of batteries"* $\rightarrow$ `{"action": "store", "value": "we're out of batteries"}`).
* **Slots:**
  * `action` (**Categorical Enum**, required): `["store", "recall"]`
  * `key` (**Extractive Span**, optional): Verbatim subject/key of note (*"locker combination"*, *"parking space"*)
  * `value` (**Extractive Span**, optional): Verbatim content of note or full declarative clause (*"4412"*, *"we're out of batteries"*)
* **Examples:**
  * *"Remember that my locker combination is 4412."* $\rightarrow$ `{"action": "store", "key": "locker combination", "value": "4412"}`
  * *"Remember that I left my wallet and car keys on the counter."* $\rightarrow$ `{"action": "store", "value": "i left my wallet and car keys on the counter"}`
  * *"What is my locker combination?"* $\rightarrow$ `{"action": "recall", "key": "locker combination"}`
  * *"Where did I park?"* $\rightarrow$ `{"action": "recall"}`

---

### Domain: `smart_home`

#### 25. `iot_device_power`
* **Description:** Discrete binary power control: turn smart appliances and lighting on or off. Also handles smart door locks actuation.
* **Special Convention (Smart Door Locks):** Commands to lock/unlock route here with `state: "on"` for locking and `state: "off"` for unlocking. State inspection queries route to `iot_sensor_query`.
* **Slots:**
  * `device_type` (**Extractive Span**, optional): Hardware appliance or fixture (*"bedroom light"*, *"lamp"*, *"fan"*, *"front door"*)
  * `state` (**Categorical Enum**, required): `["on", "off"]`
  * `house_place` (**Extractive Span**, optional): Room (*"living room"*)
* **Examples:**
  * *"Turn on the living room lights."* $\rightarrow$ `{"device_type": "lights", "state": "on", "house_place": "living room"}`
  * *"Turn off the fan."* $\rightarrow$ `{"device_type": "fan", "state": "off"}`
  * *"Lock the front door."* $\rightarrow$ `{"device_type": "front door", "state": "on"}`
  * *"Unlock the front door."* $\rightarrow$ `{"device_type": "front door", "state": "off"}`

#### 26. `iot_device_adjust`
* **Description:** Adjust continuous smart device settings: brightness, temperature, color, or speed.
* **Slots:**
  * `device_type` (**Extractive Span**, optional): Appliance (*"thermostat"*, *"lamp"*)
  * `setting` (**Categorical Enum**, optional): `["brightness", "temperature", "color", "speed"]`
  * `direction` (**Categorical Enum**, optional): `["up", "down"]`
  * `value` (**Extractive Span**, optional): Target setting (*"72 degrees"*, *"warm white"*, *"50 percent"*)
* **Examples:**
  * *"Set the thermostat to 72 degrees."* $\rightarrow$ `{"device_type": "thermostat", "setting": "temperature", "value": "72 degrees"}`
  * *"Dim the living room light."* $\rightarrow$ `{"device_type": "light", "setting": "brightness", "direction": "down"}`

#### 27. `iot_sensor_query`
* **Description:** Inquire about ambient indoor sensor readings (temperature, motion) or state inspection of contact/lock sensors.
* **Inclusion:** Environmental readings (*"What's the temperature in the living room?"*) and interrogative status queries (*"Is the front door locked?"*).
* **Slots:**
  * `sensor_type` (**Categorical Enum**, optional): `["temperature", "motion", "lock", "contact"]`
  * `device_type` (**Extractive Span**, optional): Hardware target (*"front door"*, *"thermostat"*)
  * `room` (**Extractive Span**, optional): Room or area (*"living room"*, *"kitchen"*)
* **Examples:**
  * *"What is the temperature in the living room?"* $\rightarrow$ `{"sensor_type": "temperature", "room": "living room"}`
  * *"Is the front door locked?"* $\rightarrow$ `{"sensor_type": "lock", "device_type": "front door"}`

---

### Domain: `transport`

#### 28. `rideshare_book`
* **Description:** Order or hail a taxi, cab, or rideshare vehicle.
* **Slots:**
  * `destination` (**Extractive Span**, optional): Arrival point (*"downtown"*, *"airport"*)
* **Examples:**
  * *"Call me an Uber to the airport."* $\rightarrow$ `{"destination": "airport"}`

#### 29. `transit_lookup`
* **Description:** Check schedules or book tickets for public transit, trains, buses, subways, and flights.
* **Slots:**
  * `transit_type` (**Categorical Enum**, optional): `["train", "bus", "flight"]`
  * `destination` (**Extractive Span**, optional): Arrival city/stop (*"chicago"*, *"new york"*)
  * `route_or_station` (**Extractive Span**, optional): Public transit line, train station, or commercial airline carrier (*"red line"*, *"penn station"*, *"southwest airlines"*, *"jet blue"*)
  * `time` (**Extractive Span**, optional): Departure time or clock time (*"7 am"*, *"noon"*). *(Note: flight modifiers like "non-stop" or "round-trip" are not times and must NOT be extracted into `time`)*
* **Examples:**
  * *"When does the next train to Chicago leave?"* $\rightarrow$ `{"transit_type": "train", "destination": "chicago"}`
  * *"Check the schedule for the Red Line."* $\rightarrow$ `{"route_or_station": "red line"}`
  * *"Find non-stop flights to New York, New York on Jet Blue."* $\rightarrow$ `{"transit_type": "flight", "destination": "new york, new york", "route_or_station": "jet blue"}`
