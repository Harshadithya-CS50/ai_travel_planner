#  AI Travel Planner

An AI-powered travel planning system that combines **Knowledge Graphs**, **Semantic Web technologies**, and **Large Language Models** to generate personalised, budget-aware itineraries backed by reusable tourism ontologies.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Knowledge Base](#knowledge-base)
- [Technology Stack](#technology-stack)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The AI Travel Planner combines three components into a single coherent system:

1. **Knowledge Graph layer** — destinations, attractions, activities, cuisine, and costs are stored as RDF triples and queried via SPARQL, reusing established tourism ontologies (JourneyStar, SEGITTUR, Schema.org).
2. **Recommendation engine** — ranks destinations by activity overlap, cuisine preference, and daily budget using graph queries rather than hardcoded lookup tables.
3. **Itinerary generator** — produces a day-by-day plan with city-specific highlights drawn from the knowledge graph, with optional LLM enrichment via the Anthropic Claude API.

All three modules are exposed through a FastAPI REST interface with interactive Swagger docs.

---

## Features

-  **Semantic destination recommendations** — ranked by preference match score and budget
-  **Day-by-day itinerary generation** — city-specific highlights rotated across travel days
-  **Budget-aware filtering** — exclude destinations above a daily cost threshold
-  **Dietary preference support** — vegetarian, vegan, and other restrictions surfaced in notes
-  **Optional LLM enrichment** — Claude generates a narrative paragraph per day when an API key is present; gracefully skipped otherwise
-  **SPARQL-queryable knowledge graph** — extend or swap the ontology without touching application code
-  **REST API** — FastAPI with auto-generated OpenAPI / Swagger docs at `/docs`

---

## Architecture

```
┌─────────────────────────────────────────┐
│              REST API (FastAPI)          │
│         /recommend    /itinerary         │
└────────────────┬────────────────────────┘
                 │
     ┌───────────┴───────────┐
     │                       │
     ▼                       ▼
┌──────────────┐     ┌────────────────────┐
│ Recommender  │     │ Itinerary Generator│
│  Engine      │     │  + LLM Enrichment  │
└──────┬───────┘     └────────┬───────────┘
       │                      │
       └──────────┬───────────┘
                  ▼
     ┌────────────────────────┐
     │   Knowledge Graph      │
     │   (rdflib / RDF+OWL)   │
     │                        │
     │  City · Attraction      │
     │  Activity · Cuisine     │
     │  Budget · Season        │
     └────────────────────────┘
```

---

## Project Structure

```
ai-travel-planner/
│
├── app.py                        # FastAPI entry-point
├── requirements.txt              # Pinned dependencies
├── .env.example                  # Environment variable template
├── .gitignore
│
├── ontology/
│   └── tourism.ttl               # Generated RDF graph (created on first run)
│
└── planner/
    ├── kg_builder.py             # Build, persist, and query the knowledge graph
    ├── recommender.py            # Rank destinations by preference + budget
    └── itinerary_generator.py   # Day-by-day itinerary with optional LLM narrative
```

---

## Prerequisites

- Python **3.11+**

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-travel-planner.git
cd ai-travel-planner
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Build the knowledge graph

This step creates `ontology/tourism.ttl` from the seed data. Only needed once (or after changing `kg_builder.py`).

```bash
python planner/kg_builder.py
```

### 5. Start the API server

```bash
uvicorn app:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) to explore the interactive API.

---

## Configuration

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | No | Enables LLM day-narrative enrichment via Claude. If absent, itineraries are generated from the KG alone. |

> **Never commit `.env` to version control.** It is listed in `.gitignore` by default.

---

## Usage

### Running modules directly

```bash
# Rebuild and inspect the knowledge graph
python planner/kg_builder.py

# Test the recommender
python planner/recommender.py

# Test the itinerary generator
python planner/itinerary_generator.py
```

### Calling the API with curl

**Get destination recommendations:**

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "activities": ["Museum", "Wine"],
    "max_daily_budget_eur": 180
  }'
```

**Generate a 5-day itinerary:**

```bash
curl -X POST http://localhost:8000/itinerary \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Paris",
    "days": 5,
    "start_date": "2025-06-01",
    "budget_per_day_eur": 180,
    "preferences": ["Museum", "Wine"],
    "dietary": "vegetarian",
    "use_llm": false
  }'
```

---

## API Reference

### `POST /recommend`

Returns destinations ranked by preference match score.

| Field | Type | Required | Description |
|---|---|---|---|
| `activities` | `list[str]` | Yes | Preferred activities e.g. `["Museum", "Wine"]` |
| `cuisine` | `string` | No | Filter by cuisine style e.g. `"Italian"` |
| `max_daily_budget_eur` | `int` | No | Exclude destinations above this daily cost |

**Example response:**

```json
{
  "recommendations": [
    {
      "city": "Paris",
      "match_score": 2,
      "matched_activities": ["museum", "wine"],
      "avg_daily_cost_eur": 200,
      "best_season": "Spring"
    }
  ]
}
```

---

### `POST /itinerary`

Generates a day-by-day travel plan.

| Field | Type | Required | Description |
|---|---|---|---|
| `city` | `string` | Yes | Destination city |
| `days` | `int` | Yes | Number of travel days |
| `start_date` | `date` | No | ISO date string, defaults to today |
| `budget_per_day_eur` | `int` | No | Target daily spend |
| `preferences` | `list[str]` | No | Activity interests |
| `dietary` | `string` | No | Dietary restriction |
| `use_llm` | `bool` | No | Enable Claude narrative enrichment (requires API key) |

---

## Knowledge Base

The graph is seeded with four cities and can be extended by editing `kg_builder.py`:

| City | Cuisine | Avg. Cost/Day | Best Season |
|---|---|---|---|
| Paris | French | €200 | Spring |
| Rome | Italian | €150 | Autumn |
| Barcelona | Spanish | €130 | Spring |
| Kyoto | Japanese | €120 | Spring |

The ontology reuses concepts from:

- [JourneyStar Ontology](https://journey-star.dhlab.unibas.ch/) — RDF-star travel graph
- [SEGITTUR Tourism Ontology](https://ontologia.segittur.es/turismo/def/core/index-en.html) — destination semantics
- [Schema.org](https://schema.org) — `TouristAttraction`, `FoodEstablishment`
- [Wikidata](https://wikidata.org) — open linked destination data

To add a new city, append a destination dict to the `destinations` list in `kg_builder.py` and re-run it.

---

## Technology Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| Knowledge graph | rdflib (RDF / OWL / SPARQL) |
| LLM | Anthropic Claude (`claude-opus-4-5`) |
| LLM orchestration | LangChain + LangChain-Anthropic |
| Data | pandas, numpy |
| Testing | pytest, httpx |

---

## Roadmap

- [ ] Real-time flight and hotel price APIs (Skyscanner, Amadeus)
- [ ] GraphRAG pipeline — Neo4j + LangChain for multi-hop reasoning
- [ ] Reinforcement learning itinerary optimiser
- [ ] Voice interface (Whisper → planner → TTS)
- [ ] Geo-spatial reasoning (proximity-aware day routing)
- [ ] Multi-agent architecture — separate Flight, Hotel, Food, and Cost agents
- [ ] Explainable recommendations ("we suggested Rome because…")

---

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a Pull Request against `main`

Please keep pull requests focused — one feature or fix per PR.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
