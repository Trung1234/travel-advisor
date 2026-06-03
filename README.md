# Voice Travel Agent AI

A voice-first travel agent MVP powered by **Qwen** with **Ollama** support. Users can speak or type in a **Streamlit** UI; a **FastAPI** backend exposes an OpenAPI-documented API and runs the agent logic. A **travel consultant skill** defines how the agent recommends destinations, hotels, weather, and food, and the backend can enrich answers with **TripAdvisor** data for destination and hotel discovery.

## Status

**MVP scaffold implemented** — backend, frontend, skill file, and baseline tests are present.

## Stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit (Python) |
| API | FastAPI + OpenAPI |
| Agent | Qwen via provider abstraction; Ollama for local runtime |
| Retrieval | TripAdvisor API for destinations and hotels |
| Guidance | Travel consultant skill file (`skills/travel-consultant/SKILL.md`) |

## Architecture

```mermaid
flowchart LR
    User[Traveler] --> UI[Streamlit voice/chat UI<br/>frontend/app.py]
    UI -->|POST /api/v1/chat| API[FastAPI backend<br/>backend/main.py]
    API --> Memory[In-memory conversation store<br/>backend/memory.py]
    API --> Skill[Travel consultant skill<br/>skills/travel-consultant/SKILL.md]
    API --> Agent[Agent orchestration<br/>backend/agent.py]
    Agent --> Provider[Qwen / Ollama]
    Agent --> TripAdvisor[TripAdvisor API]
    Provider --> Agent
    TripAdvisor --> Agent
    Agent --> API
    API --> UI
    UI --> User
```

## Project layout

```
travel-advisor/
├── README.md
├── AGENTS.md
├── .env.example
├── requirements.txt
├── specs/
├── skills/travel-consultant/SKILL.md
├── backend/
├── frontend/
└── tests/
```

## Prerequisites

- Python 3.11+
- Qwen access or a local Ollama server
- TripAdvisor API credentials if you want destination/hotel enrichment

## Getting started

1. Create and activate a Python virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set provider and TripAdvisor variables.
4. Start Ollama locally if you are using the local runtime.
5. Start API:
   - `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
6. Start UI:
   - `streamlit run frontend/app.py`
7. Open the Streamlit URL and ask for trip advice.

## API

- Health check: `GET /health`
- Chat endpoint: `POST /api/v1/chat`
- Docs: `/docs`

## Testing

- Run: `pytest`

## Documentation

| File | Purpose |
| ------ | --------- |
| [AGENTS.md](AGENTS.md) | How AI agents should work in this repo |
| [specs/product-spec.md](specs/product-spec.md) | What we are building |
| [specs/implementation-plan.md](specs/implementation-plan.md) | How we build it |
| [specs/test-plan.md](specs/test-plan.md) | How we verify it |
| [specs/change-log.md](specs/change-log.md) | Spec and product changes |
| [specs/readme-notes.md](specs/readme-notes.md) | Notes on README-related updates |
