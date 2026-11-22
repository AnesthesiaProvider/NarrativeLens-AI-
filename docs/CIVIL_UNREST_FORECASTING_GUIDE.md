# NarrativeLens AI — Civil Unrest Event Extraction & Predictive Forecasting Guide

> **Author**: NarrativeLens AI Research Team  
> **Module**: OSINT Narrative Intelligence & Escalation Forecasting  
> **Status**: Production / Live  
> **Dashboard Route**: `/civil-unrest`  
> **API Endpoints**: `/api/civil-unrest/*`

---

## 1. Executive Overview

Social media communications preceding major civil unrest events (protests, strikes, flashmobs, blockades, and riots) are typically **unstructured, noisy, multilingual, and highly colloquial**. They are characterized by:
* Heavy hashtag concentration (`#MetroShutdown`, `#PhillyGeneralStrike`, `#OccupyTheTracks`).
* Imperative mobilization calls ("Everyone meet at Central Station Plaza TOMORROW at 5:00 PM!").
* Tactical countermeasure coordination (umbrellas, gas masks, laser pointers, milk/saline eye wash).
* Choke point targeting (arterial bridges, container ports, highway on-ramps, government civic plazas).
* Operational security (OpSec) indicators (Signal/Telegram links, burner radios, scout signals).

The **Civil Unrest Event Extraction & Predictive Forecasting Engine** in NarrativeLens AI utilizes **Structured Few-Shot Prompt Engineering** and **Local LLM Contextual Reasoning** (powered by `qwen3:4b` or any compatible model) coupled with a **Zero-Hardcoding Dynamic OSINT Extraction Engine** to parse raw social media posts into validated tactical intelligence dossiers.

---

## 2. Dynamic Architecture (Zero Hardcoding)

Unlike brittle keyword matching systems or hardcoded responses, this engine operates with complete run-time configurability:

```
                            [ Incoming Noisy Social Post ]
                                          │
                                          ▼
                ┌──────────────────────────────────────────────────┐
                │      Dynamic Prompt Engineering Assembler        │
                │  - Model: qwen3:4b / llama3 / custom override    │
                │  - Temperature: User-tunable (0.0 to 1.0)        │
                │  - System Prompt: Custom OSINT Persona override  │
                │  - Custom Intelligence Instructions injection    │
                └─────────────────────────┬────────────────────────┘
                                          │
                       ┌──────────────────┴──────────────────┐
                       │                                     │
                       ▼                                     ▼
           ┌──────────────────────┐              ┌──────────────────────┐
           │   Ollama Local LLM   │              │ Dynamic OSINT Engine │
           │   Inference Engine   │ (If offline) │ (Air-Gapped Realtime │
           │ (Strict JSON Output) │─────────────►│  Statistical Parser) │
           └───────────┬──────────┘              └───────────┬──────────┘
                       │                                     │
                       └──────────────────┬──────────────────┘
                                          │
                                          ▼
                      ┌──────────────────────────────────────┐
                      │    Validated Pydantic Intelligence   │
                      │               Dossier                │
                      │  - Primary Event Categorization      │
                      │  - Actors, Targets & Demographics    │
                      │  - Venue Choke Point & Timelines     │
                      │  - Escalation Index & Weapons Risk   │
                      │  - De-Escalation Playbook & Forecast │
                      │  - Verbatim Raw LLM Token Trace      │
                      └──────────────────────────────────────┘
```

### Key Dynamic Components:
1. **Dynamic Prompt & Parameter Controls**: At run-time, analysts can select the model, adjust sampling temperature, inject domain-specific instructions (e.g. *"Focus on transit lines"*), or provide custom system prompts.
2. **Dynamic JSON Scenario Catalog**: Scenarios are not hardcoded in Python; they are loaded from [`backend/app/data/civil_unrest_scenarios.json`](file:///c:/Users/anshs/Documents/AI%20assignments/NLP%20PROJECT/HATE-SPEECH%20DECTECTION/backend/app/data/civil_unrest_scenarios.json). Users can add, update, or remove scenarios directly from the UI or API.
3. **Full LLM Output Transparency**: The engine returns the exact rendered prompt, verbatim model output, and internal chain-of-thought tokens directly in the API response and web dashboard.

---

## 3. Step-by-Step Setup & How to Run

### Step 1: Start the Backend Server
Run the root startup script:
```cmd
.\start.bat
```
Or start manually with the active virtual environment:
```powershell
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
* Interactive Swagger Docs: `http://127.0.0.1:8000/docs`
* Health Check: `http://127.0.0.1:8000/api/health`

### Step 2: (Optional) Launch Ollama for Local LLM Reasoning
If you want live local neural LLM reasoning:
1. Make sure [Ollama](https://ollama.com/) is installed and running (`http://127.0.0.1:11434`).
2. Pull the default model:
   ```bash
   ollama pull qwen3:4b
   ```
   *(Or pull `llama3.1:8b`, `mistral:7b`, etc.)*
> **Note**: If Ollama is not running, the system automatically and seamlessly falls back to the **OSINT Dynamic Statistical Extractor**, ensuring 100% operational uptime in air-gapped environments.

### Step 3: Start the Frontend Application
In a separate terminal:
```powershell
cd frontend
pnpm run dev
```
Open your browser at: **`http://localhost:5173/civil-unrest`**

---

## 4. How to Use the Dashboard (`/civil-unrest`)

### 1. One-Click Scenario Selection
At the top of the page, choose from the dynamic catalog of monitored real-world scenarios:
* **Transit Hub Blockade**: Coordinated rail track and bridge shutdown with umbrella shields and laser pointers.
* **General Labor Strike**: Municipal sanitation and transit worker walkout with picket lines.
* **Curfew Defiance**: Nighttime precinct rally defying municipal emergency declarations.
* **Counter-Protest Flashpoint**: Dual-faction assembly at a state legislative capitol.
* **Port Blockade**: Industrial shipping container terminal blockade.

Clicking any scenario automatically populates the text, metadata, and triggers immediate intelligence extraction.

### 2. Tuning Prompt Engineering Parameters
Click the **Prompt Engineering Controls** button in the header to expand the customization drawer:
* **Target Model**: Pick any discovered local Ollama model (`qwen3:4b`, `llama3.1:8b`, `mistral:7b`) or type a custom model identifier.
* **Sampling Temperature**: Set between `0.0` (deterministic schema adherence) and `1.0` (creative OSINT hypothesis exploration).
* **Special Intelligence Requirements**: Inject special analyst priorities (e.g., *"Highlight chemical irritants and transit choke points"*).
* **Custom System Prompt**: Override the default persona with your own specialized prompt.

### 3. Custom Social Media Ingestion
Paste any raw post into the text area:
* Set **Source Platform** (`Telegram`, `X / Twitter`, `Reddit`, `4chan`, `Discord`, or `Web Forum`).
* Provide optional **Author Handle** and **Location Hint**.
* Click **Extract & Forecast Unrest**.

### 4. Exploring the 5 Intelligence Tabs
Once analyzed, the dashboard presents:
* **Top Metric Badges**:
  * **Threat Level Assessment**: Color-coded badge (`CRITICAL`, `SEVERE`, `HIGH`, `MODERATE`, `LOW`) with an escalation progress bar.
  * **Overall Unrest Probability**: Calibrated probability percentage and mobilization scope (`LOCAL`, `CITYWIDE`, `REGIONAL`, `NATIONWIDE`).
  * **Primary Event Categorization**: Formal typology (`blockade`, `protest`, `strike`, `curfew_defiance`, etc.).
  * **Intelligence Engine**: Attribution showing which model and prompt technique executed the extraction.
* **Tab 1: Timeline & Location**:
  * Verbatim temporal expression vs normalized target window.
  * Temporal urgency badge (`IMMINENT <24h`, `ACTIVE`, `SCHEDULED`, `HISTORICAL`).
  * Imperative command callout (verbatim quotes of assembly orders).
  * Gathering landmark and venue coordinates.
* **Tab 2: Actors & Entities**:
  * Organizers & Factions (color-coded chips).
  * Targeted Institutions (precincts, city halls, transit authorities).
  * Security forces mentioned (riot squads, tactical units).
  * Target demographics called to mobilize.
* **Tab 3: Escalation Indicators**:
  * Weapons & physical clash risk gauge.
  * Protective gear & tactical countermeasures (respirators, laser pointers, shields, saline).
  * Critical physical infrastructure targeted.
  * Encrypted communication flags (Signal/Telegram links, radio scanners).
* **Tab 4: Predictive Forecast**:
  * Violence & destruction propensity score.
  * Forecasted peak unrest window.
  * Actionable public safety & de-escalation playbook (rerouting transit, liaison teams).
* **Tab 5: Prompt & LLM Transparency**:
  * Exact rendered prompt sent to the LLM.
  * Internal chain-of-thought reasoning tokens.
  * Verbatim raw model response (validating live execution).

### 5. Saving Custom Scenarios
Click **Save Current as Scenario** to name and store any analyzed post into the dynamic library for future evaluation or presentations.

---

## 5. REST API Integration Guide

### Endpoint 1: Single Post Extraction
```http
POST /api/civil-unrest/extract
Content-Type: application/json

{
  "text": "Everyone assemble at Central Station Plaza TOMORROW at 5:00 PM! We are shutting down the inbound train lines. Bring umbrellas and laser pointers! #MetroShutdown",
  "platform": "telegram",
  "author": "@MetroDirectAction",
  "location_hint": "Chicago, IL",
  "model": "qwen3:4b",
  "temperature": 0.1,
  "custom_prompt_instructions": "Focus on rail transit choke points"
}
```

#### Sample Response:
```json
{
  "event_id": "unrest-8f3a9e210b",
  "primary_event_type": "blockade",
  "event_summary": "Detected blockade mobilization targeting Public Transportation & Logistics Infrastructure with imminent urgency.",
  "actors": {
    "organizers": ["@MetroDirectAction", "#MetroShutdown"],
    "targets": ["Public Transportation & Logistics Infrastructure"],
    "counter_actors": [],
    "security_forces": ["Riot Police / Tactical Units"],
    "demographics": ["Citizens & Affinity Groups"]
  },
  "location": {
    "raw_location": "Central Station Plaza",
    "landmark_or_venue": "Central Station Plaza",
    "city": "Chicago",
    "state_region": null,
    "country": null,
    "geo_specificity": "high"
  },
  "timeline": {
    "raw_time_expression": "tomorrow at 5:00 pm",
    "normalized_target_time": null,
    "temporal_status": "imminent",
    "call_to_action": true,
    "call_to_action_text": "Everyone assemble at Central Station Plaza TOMORROW at 5:00 PM!"
  },
  "escalation": {
    "threat_level": "high",
    "escalation_score": 0.58,
    "weapons_or_clash_risk": false,
    "protective_gear_or_tactics": [
      "Crowd Umbrellas & Defensive Shields",
      "Laser Pointers"
    ],
    "infrastructure_targeting": [
      "Transit Stations, Rail Lines & Shipping Terminals"
    ],
    "virality_velocity": "surging",
    "tactical_coordination_flags": [
      "Encrypted Channels (Signal/Telegram)"
    ]
  },
  "forecast": {
    "overall_unrest_probability": 0.63,
    "mobilization_radius": "citywide",
    "predicted_peak_window": "tomorrow at 5:00 pm",
    "violence_propensity": 0.20,
    "recommended_interventions": [
      "Establish proactive civil liaison presence near Central Station Plaza",
      "Coordinate public transit detour plans for identified transport bottlenecks",
      "Monitor real-time encrypted coordination nodes for dynamic routing changes"
    ],
    "analytical_rationale": "High-urgency call to action with specialized tactical gear and transit choke point targeting."
  },
  "model_used": "qwen3:4b",
  "prompt_technique": "Few-Shot Chain-of-Thought with Strict JSON Schema Enforcement",
  "confidence": 0.89,
  "raw_prompt": "...",
  "raw_llm_response": "{...}",
  "reasoning_tokens": "..."
}
```

### Endpoint 2: Batch Stream Analysis
```http
POST /api/civil-unrest/batch
Content-Type: application/json

{
  "posts": [
    {
      "text": "Call to action: shutdown 5th Ave bridge tonight at 8 PM!",
      "platform": "twitter"
    },
    {
      "text": "Bring masks and barricade materials to City Hall square.",
      "platform": "telegram"
    }
  ]
}
```
Returns an aggregated threat summary, peak escalation score, and combined tactical indicator list across all posts.

### Endpoint 3: Dynamic Scenario Management
* `GET /api/civil-unrest/scenarios`: Returns all monitored scenarios.
* `POST /api/civil-unrest/scenarios`: Adds a custom scenario to the JSON repository.
* `GET /api/civil-unrest/models`: Lists installed Ollama models.

---

## 6. Real-World Demonstration & Pitch Script

When presenting or demonstrating this capability to professors, evaluators, or conference attendees, follow this 4-step walkthrough:

1. **The Problem Statement**:
   > *"Traditional keyword alerts fail on social media because agitators use coded slang, colloquial phrasing, and decentralized mobilization calls. NarrativeLens AI solves this by deploying prompt engineering to extract structured OSINT intelligence from noisy text in real time."*

2. **The Dynamic Prompt Demonstration**:
   > *"Open the Prompt Engineering drawer. Show that this is not hardcoded: we can switch models from Qwen to Llama, adjust temperature, and inject custom intelligence directives like 'Focus on port logistics'."*

3. **Live Execution & Indicator Extraction**:
   > *"Select the 'Metropolitan Transit Hub Blockade' scenario or paste live text. Notice how the engine automatically identifies: (1) Event Type: Blockade, (2) Target Landmark: Central Station Plaza, (3) Temporal Urgency: Imminent <24h, (4) Protective Gear: Umbrellas and Laser Pointers, and (5) Infrastructure Threat: Rail transit lines."*

4. **Forecasting & Actionable Interventions**:
   > *"Point to the Predictive Forecast tab. The AI synthesizes the overall escalation score into actionable de-escalation steps, such as transit rerouting and community liaison deployment, before violence breaks out."*
