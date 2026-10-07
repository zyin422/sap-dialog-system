# Reference Specification: Amazon MASSIVE Taxonomy & BFCL Tool Wrapper

**Benchmark:** Speech Accessibility Project (SAP) Spoken Dialog Benchmark  
**Directory:** `sap-dialog-system/benchmark_curation`  
**Purpose:** Formal specification combining Amazon MASSIVE's closed voice-assistant taxonomy with Berkeley Function Calling Leaderboard (BFCL) typed JSON Schema wrappers.

---

## 1. Amazon MASSIVE Taxonomy Overview (FitzGerald et al., ACL 2022)

Amazon MASSIVE is a parallel 52-language spoken natural language understanding dataset localized from SLURP (EMNLP 2020). It defines a closed ontology of **18 Domains**, **60 Intents**, and **55 Slot Types**.

### 1.1 The 18 Canonical Domains
1. `alarm` — Alarm and timer management
2. `audio` — Audio volume and playback device controls
3. `calendar` — Calendar meeting, event scheduling, and agenda queries
4. `cooking` — Cooking instructions, recipes, and ingredient queries
5. `datetime` — Current time, date queries, and timezone conversions
6. `email` — Email messaging, inbox search, and contacts
7. `general` — General assistant interactions, greetings, jokes, device finding
8. `iot` — Smart home appliances, Hue lighting, plugs, and switches
9. `lists` — To-do lists, shopping lists, item management
10. `music` — Music metadata queries, likeness/favorites, track skipping
11. `news` — Headlines and topic-specific news updates
12. `play` — Streaming media playback (music, podcasts, audiobooks, radio)
13. `qa` — Knowledge queries (factoids, dictionary definitions, stock prices, currency)
14. `recommendation` — Nearby places, restaurants, events, and movie showtimes
15. `social` — Social messaging and telephony (audio/video calls)
16. `takeaway` — Food delivery and takeout ordering
17. `transport` — Taxis, public transit, flight tickets, and traffic conditions
18. `weather` — Forecasts, weather conditions, and temperature queries

---

### 1.2 The 60 Canonical Intents (Grouped by Domain)

| Domain | Intent (`<domain>_<action>`) | Description |
| :--- | :--- | :--- |
| **alarm** | `alarm_set` | Set a new alarm or timer |
| | `alarm_query` | Query upcoming alarms or timers |
| | `alarm_remove` | Cancel or remove an existing alarm |
| **audio** | `audio_volume_up` | Increase device volume |
| | `audio_volume_down` | Decrease device volume |
| | `audio_volume_mute` | Mute device audio |
| | `audio_volume_other` | Adjust volume to specific level or preset |
| **calendar** | `calendar_set` | Create an event or appointment |
| | `calendar_query` | Check events or agenda for date/time |
| | `calendar_remove` | Delete or cancel an event |
| **cooking** | `cooking_recipe` | Search for food recipe or cooking steps |
| | `cooking_query` | Query food ingredients or cooking times |
| **datetime** | `datetime_query` | Query current time or date |
| | `datetime_convert` | Convert time across timezones |
| **email** | `email_sendemail` | Send an email message |
| | `email_query` | Search or read emails |
| | `email_addcontact` | Save a new email contact |
| **general** | `general_quirky` | Small talk, assistant features ("find my phone") |
| | `general_greet` | Greetings and salutations |
| | `general_joke` | Tell a joke |
| | `general_dontunderstand`| Clarification fallback |
| **iot** | `iot_hue_lighton` | Turn on lights, lamps, bulbs |
| | `iot_hue_lightoff` | Turn off lights, lamps, bulbs |
| | `iot_hue_lightdim` | Dim or adjust brightness / temperature |
| | `iot_hue_lightchange` | Change lighting color |
| | `iot_hue_lightup` | Brighten lighting |
| | `iot_wemo_on` | Turn on smart plugs, switches, appliances, TV, AC |
| | `iot_wemo_off` | Turn off smart plugs, switches, appliances, TV, heat |
| | `iot_coffee` | Trigger coffee maker |
| | `iot_cleaning` | Trigger vacuum cleaner |
| **lists** | `lists_createoradd` | Create list or add items |
| | `lists_query` | Read or query list contents |
| | `lists_remove` | Remove item from list |
| **music** | `music_likeness` | Add song to favorites / like track |
| | `music_dislikeness` | Dislike current track |
| | `music_query` | Query currently playing song or artist info |
| | `music_settings` | Skip song, pause, or resume playback |
| **news** | `news_query` | Fetch news headlines or specific news topic |
| **play** | `play_music` | Stream music track, artist, album, playlist |
| | `play_audiobook` | Play audiobook |
| | `play_podcasts` | Stream podcast episode |
| | `play_game` | Start a voice game |
| | `play_radio` | Stream radio station |
| **qa** | `qa_factoid` | General factual knowledge query |
| | `qa_definition` | Word definition or spelling |
| | `qa_stock` | Stock ticker price query |
| | `qa_maths` | Arithmetic calculation |
| | `qa_currency` | Currency exchange query |
| **recommendation**| `recommendation_locations`| Find local business, cafe, restaurant |
| | `recommendation_movies` | Find movie showtimes or releases |
| | `recommendation_events` | Find local events or activities |
| **social** | `social_post` | Send message, make voice/video call, hang up |
| | `social_query` | Check received messages or call notifications |
| **takeaway** | `takeaway_order` | Order food delivery |
| | `takeaway_query` | Check order status or menu |
| **transport** | `transport_taxi` | Call or book taxi / rideshare |
| | `transport_ticket` | Search or book flight/train ticket |
| | `transport_traffic` | Query traffic conditions |
| | `transport_query` | Check transit schedule or arrival |
| **weather** | `weather_query` | Query weather forecast, conditions, temperature |

---

### 1.3 The 55 Canonical Slot Types in MASSIVE / SLURP
1. `alarm_type`
2. `app_name`
3. `artist_name`
4. `audiobook_author`
5. `audiobook_name`
6. `business_name`
7. `business_type`
8. `change_amount`
9. `coffee_type`
10. `color_type`
11. `cooking_type`
12. `currency_name`
13. `date`
14. `definition_word`
15. `device_setting`
16. `device_type`
17. `drink_type`
18. `email_address`
19. `email_folder`
20. `event_name`
21. `food_type`
22. `game_name`
23. `game_type`
24. `general_frequency`
25. `house_place`
26. `ingredient`
27. `joke_type`
28. `line_detail`
29. `list_name`
30. `meal_type`
31. `media_type`
32. `movie_name`
33. `movie_type`
34. `music_album`
35. `music_descriptor`
36. `music_genre`
37. `news_topic`
38. `order_type`
39. `personal_info`
40. `person`
41. `place_name`
42. `player_setting`
43. `podcast_descriptor`
44. `podcast_name`
45. `radio_name`
46. `relation`
47. `song_name`
48. `time`
49. `time_zone`
50. `timeofday`
51. `transport_agency`
52. `transport_descriptor`
53. `transport_name`
54. `transport_type`
55. `weather_descriptor`

---

## 2. SAP Clinical & Assistive Domain Extensions

Extracted from the Speech Accessibility Project dev manifest protocol:
1. `health`:
   - `health_refill_query` (slots: `medication`) — Check remaining prescription refills.
   - `health_medication_reminder` (slots: `medication`, `time`) — Schedule prescription intake reminders.
2. `accessibility`:
   - `accessibility_ui_scale` (slots: `ui_element`, `direction`) — Adjust UI zoom, font size, or screen brightness.
   - `accessibility_dictation_toggle` (slots: `state`) — Enable or disable voice dictation listening.

---

## 3. Verified BFCL (Berkeley Function Calling Leaderboard) Structural Wrapper

The official BFCL format (Gorilla LLM, UC Berkeley) uses an OpenAI-compatible JSON Schema definition:

```json
{
  "type": "function",
  "function": {
    "name": "tool_name",
    "description": "Clear natural language description explaining when to invoke this tool.",
    "parameters": {
      "type": "object",
      "properties": {
        "slot_key": {
          "type": "string",
          "description": "Description of the parameter and nominal extraction constraints."
        }
      },
      "required": ["mandatory_slot_key"],
      "additionalProperties": false
    }
  }
}
```

### Key Properties Enforced:
1. **`additionalProperties: false`**: Restricts the LLM from hallucinating unapproved parameters.
2. **`properties: {}`**: For tools with no arguments (e.g. `music_settings`), forces empty parameter extraction.
3. **Nominal Core Rule**: Parameter descriptions mandate extracting bare entities ($NP$), strictly excluding governing prepositions (`at`, `with`, `on`, `to`) and determiners (`a`, `an`, `the`).
