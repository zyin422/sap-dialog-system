You are an expert Spoken Language Understanding (SLU) semantic parser. Map each of the following spoken assistant commands into its canonical (Domain, Intent, Slots) representation according to the strict 29-tool schema below.

### 1. Canonical Schema (29 Tools across 10 Domains)

1. accessibility:
- accessibility_dictation_toggle: state ["on", "off", "enable", "disable"]
- accessibility_ui_scale: direction ["up", "down", "in", "out"], ui_element ["zoom", "text_size", "high_contrast", "screen"]

2. calendar_alarm:
- alarm_manage: action ["set", "cancel", "query", "snooze"], time (span), date (span), general_frequency ["daily", "weekdays", "weekends", "weekly", "monthly"]
- schedule_manage: action ["create", "delete", "query", "update"], title (span), date (span), time (span), person (span)

3. communication:
- call_make: recipient_name (span), phone_number (span)
- call_manage: action ["answer", "decline", "hang_up", "mute", "unmute", "redial"]
- messages_manage: action ["send", "read", "reply"], recipient (span), message_body (span)
- email_manage: action ["send", "read", "search"], recipient (span), date (span), message_body (span)

4. general_qa:
- qa_search: query (span) -> Factual queries, definitions, recipes, stock prices.
- weather_query: place_name (span), date (span), weather_aspect (span)
- device_find: device_type (span)
- order_manage: action ["track", "cancel", "return", "status"]

5. health:
- health_medication_reminder: medication (span), time (span)
- health_refill_query: medication (span)
- health_info_query: medication (span), info_type ["side_effects", "dosage", "interactions", "refill"]

6. maps_places:
- maps_route: destination (span), query_type ["directions", "distance", "traffic"]
- places_search: business_name (span), business_type (span), sort_by ["rating", "distance", "relevance"]
- reservations_manage: business_name (span), time (span), date (span), party_size (span)

7. media:
- media_play: media_type ["music", "podcast", "radio", "audiobook", "movie", "tv_show"], title (span), artist (span), service (span: e.g. hulu, spotify, paramount plus), house_place (span)
- media_search: media_type ["movie", "tv_show", "music", "podcast", "audiobook"], person (span: actor/director/artist), genre (span), title (span) -> Browse/recommend media.
- media_control: action ["pause", "resume", "stop", "next", "previous", "like", "dislike", "fast_forward", "rewind"], duration (span)
- media_volume: action ["up", "down", "mute", "unmute", "set"], change_amount (span)

8. notes_memory:
- lists_manage: action ["create", "add", "remove", "query"], item (span), list_name (span)
- memory_note_manage: action ["store", "recall"], key (span), value (span)

9. smart_home:
- iot_device_power: device_type (span), state ["on", "off"], house_place (span) -> Binary toggles and lock actuation (lock -> on, unlock -> off).
- iot_device_adjust: device_type (span), setting ["brightness", "temperature", "color", "speed"], direction ["up", "down"], value (span)
- iot_sensor_query: sensor_type ["temperature", "motion", "lock", "contact"], device_type (span), room (span) -> State inspection (e.g. Is front door locked? -> sensor_type: lock).

10. transport:
- rideshare_book: destination (span)
- transit_lookup: transit_type ["train", "bus", "flight"], destination (span), route_or_station (span), time (span)

### 2. Core Extraction Rules:
- Rule A (BaseNP & Possessives): Strip prepositions (to, at, in) and possessive pronouns/articles (my, our, your, the, a). E.g. "Map route to our hotel" -> destination: "hotel".
- Rule B (Carrier Stripping in qa_search): Strip polite prefixes ("can you look up", "tell me"). E.g. "Did the Clemson Tigers win?" -> query: "did the clemson tigers win".
- Rule C (Memory Key-Value): If an attribute relation (X is Y), extract key and value. If an unkeyed declarative fact ("We're out of batteries"), extract action: "store", value: "we're out of batteries" (leave key empty).
- Verbatim Spans: All extracted span values must be exact lower-case substrings from the utterance. Never invent unuttered entities.

### 3. Output Format:
Return ONLY a valid CSV block with EXACTLY these four columns:
id,domain,intent,slots_json

Make sure slots_json is valid JSON with double-quotes escaped as per CSV standard (or standard JSON format). Output all 50 rows without truncating.

### 4. Input Commands (Batch 1 - 50 commands):
ID 650: "How many calories does 15 baby carrots and a scoop of hummus have?"
ID 658: "How many calories does a pint of Ben and Jerry's ice cream have?"
ID 652: "How many calories does 3 teaspoons of brown sugar have?"
ID 656: "How many calories does a piece of grilled salmon have?"
ID 661: "How many calories does a slice of sausage pizza have?"
ID 786: "Who is the lead character in '2001: A Space Odyssey'?"
ID 655: "How many calories does a cup of blueberries have?"
ID 660: "How many calories does a pint of ice cream have?"
ID 792: "Who is the lead character in 'West Side Story'?"
ID 726: "Show me movies with Catherine Zeta-Jones."
ID 728: "Show me movies with Denzel Washington."
ID 727: "Show me movies with Daniel Day-Lewis."
ID 730: "Show me movies with Jack Nicholson."
ID 731: "Show me movies with Julianne Moore."
ID 734: "Show me movies with Ryan Reynolds."
ID 725: "Show me movies with Blake Lively."
ID 733: "Show me movies with Ryan Gosling."
ID 738: "Show me movies with Will Ferrell."
ID 1026: "Cancel my meeting with Soren Ignaz at 8:15 AM, Thursday the 30th."
ID 1180: "Set a timer for chocolate chip and walnut cookies for 12 minutes."
ID 1022: "Cancel my meeting with Sanjiv Lynne at 2:30 PM, Tuesday the 9th."
ID 1016: "Cancel my meeting with Kiley Jokin at 9 AM on July 14th, 2023."
ID 1023: "Cancel my meeting with Sib and Gertrud at 9:30 AM, Sunday."
ID 1029: "Cancel my meeting with Valli Sylvia at 1:15, 8/15/2023."
ID 1014: "Cancel my meeting with Jiro Thomas at 9 PM, Saturday."
ID 1177: "Set a timer for baked chicken for 2 and a half hours."
ID 1186: "Set an alarm for 3:45 PM on Thursday and Friday."
ID 1125: "Reschedule my meeting with Barrett Sipho at 6:30 PM, April 4th, 2023."
ID 1127: "Reschedule my meeting with Chanelle Kellen at noon, May 1st, Friday."
ID 1131: "Reschedule my meeting with Valeria Berengere at 11 O'clock, Sunday."
ID 1126: "Reschedule my meeting with Catherine Isabella at 8:30 AM, Monday."
ID 1132: "Reschedule my meeting with Virginia Daniel at 7, Saturday."
ID 1130: "Reschedule my meeting with Irene Anand at 4:15, Tuesday."
ID 1128: "Reschedule my meeting with Demetri Lucien at 9, Friday."
ID 944: "Turn off the lights in the dining room."
ID 945: "Turn off the lights in the family room."
ID 947: "Turn off the lights in the hall closet."
ID 950: "Turn off the lights in the living room."
ID 948: "Turn off the lights in the kids' room."
ID 946: "Turn off the lights in the guestroom."
ID 934: "Turn down the temperature 2 degrees."
ID 935: "Turn down the temperature 3 degrees."
ID 936: "Turn down the temperature 4 degrees."
ID 937: "Turn down the temperature 5 degrees."
ID 933: "Turn down the temperature 1 degree."
ID 949: "Turn off the lights in the kitchen."
ID 963: "Turn up the temperature 2 degrees."
ID 964: "Turn up the temperature 3 degrees."
ID 316: "Play the latest episode of 'Ten Percent Happier' with Dan Harris on Spotify."
ID 283: "Play 'The Tears of a Clown' by Smokey Robinson and the Miracles."
