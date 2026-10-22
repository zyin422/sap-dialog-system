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
- Rule D (Generic Event Noun in schedule_manage): Retain generic event nouns ("meeting", "appointment", "call", "reminder") in title if uttered and no specific event topic is given (e.g. "Cancel my meeting with Sanjiv" -> title: "meeting", person: "sanjiv").
- Rule E (Alarm Recurrence Token Constraint in alarm_manage): Only populate general_frequency if an explicit recurrence marker is uttered ("daily", "weekdays", "every Thursday"). Coordinated days without recurrence markers ("on Thursday and Friday") belong strictly in the date slot; do not infer general_frequency: "weekly".
- Verbatim Spans: All extracted span values must be exact lower-case substrings from the utterance. Never invent unuttered entities.

### 3. Output Format:
Return ONLY a valid CSV block with EXACTLY these four columns:
id,domain,intent,slots_json

Make sure slots_json is valid JSON with double-quotes escaped as per CSV standard (or standard JSON format). Output all 50 rows without truncating.

### 4. Input Commands (Batch 2 - 50 commands):
ID 308: "Play the latest episode of 'If Books Could Kill' on Spotify."
ID 330: "Read 'The Lion, The Witch, and the Wardrobe' on Audiobook."
ID 318: "Play the latest episode of 'The NPR Newsroom' on Spotify."
ID 314: "Play the latest episode of 'Stand up Comedy' on Spotify."
ID 310: "Play the latest episode of 'Let's be Real' on Spotify."
ID 306: "Play the latest episode of "A Little Something Extra""
ID 315: "Play the latest episode of 'Stuff You Should Know'."
ID 309: "Play the latest episode of 'Joe Rogan' on Spotify."
ID 261: "Play 'Carol and Ava Detectives' on Audiobook."
ID 273: "Play 'Me and Bobby McGee' by Janis Joplin."
ID 276: "Play 'Stay with Me' by Sam Smith."
ID 319: "Play the latest episode of 'This American Life'."
ID 221: "Please send this text: "Hi, exclamation point. What time will you be home, question mark. Thanks, exclamation point.""
ID 822: "Open Gmail to send a message to Layne Banks."
ID 220: "Please send this email: "Dear customer service, comma. I am writing about the status of order number 384972, period. Do you have a tracking update, question mark. Thank you, period.""
ID 844: "Send a message to Hayri & Amador Teague."
ID 855: "Send an email to UPS Customer Service."
ID 122: "Did I miss any emails from yesterday?"
ID 849: "Send an email to Jasmine Witherspoon."
ID 219: "Please send this email to the group."
ID 843: "Send a message to Felicitas Sinagra."
ID 846: "Send a message to The Mounce Family."
ID 988: "Add meat for grilling, pre-cut vegetables, teriyaki sauce, and bamboo skewers to the shopping list."
ID 984: "Add ingredients for chili, pizza dough, shredded mozzarella, and heel balm to the shopping list."
ID 999: "Add vanilla mousse, mussels, non-fat Greek yogurt, and triple A batteries to the shopping list."
ID 981: "Add frozen strawberries, blueberries, a case of paper towels, and cereal to the shopping list."
ID 986: "Add laundry detergent, toothpaste, aluminum foil, and cranberry juice to the shopping list."
ID 1000: "Add whole pecans, eye drops, leeks, and 2 cartons of half-and-half to the shopping list."
ID 996: "Add spaghetti, frozen cauliflower, bananas, and 3 jars of salsa to the shopping list."
ID 967: "Add 3 pairs of socks, pears, apples, and carrots to the shopping list."
ID 998: "Add sugar, flour, flower seeds, and fertilizer to the shopping list."
ID 1107: "Remember that I left my wallet and car keys on the counter."
ID 134: "How many refills are left on my clindamycin risperidone?"
ID 175: "Set a reminder to take simvastatin at dinner time."
ID 168: "Set a reminder to take amoxicillin with lunch."
ID 170: "Set a reminder to take furosemide at bed time."
ID 176: "Set a reminder to take Spironolactone at 9 PM."
ID 172: "Set a reminder to take ibuprofen at 11:30 AM."
ID 171: "Set a reminder to take glipizide at 6:30 PM."
ID 173: "Set a reminder to take pantoprazole at 6 AM."
ID 1304: "How far is West Orange, New Jersey from here?"
ID 564: "When is Bed, Bath and Beyond open until?"
ID 383: "How far is Brattleboro, Vermont from Montreal, Canada?"
ID 1247: "Book a table for 2 at 3 Arts Club Café at RH Chicago."
ID 450: "Map a route to the closest car charging station."
ID 1255: "Book a table for 5 at Dry Dock Waterfront Grill."
ID 1308: "How much is a round-trip flight to Manchester, New Hampshire?"
ID 1293: "Find non-stop flights to New York, New York on Jet Blue."
ID 1287: "Find non-stop flights to Dublin, Ireland on Air Canada."
ID 1292: "Find non-stop flights to New York on American Airlines."
