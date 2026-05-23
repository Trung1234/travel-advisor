# Travel Advisor AI

A simple MVP travel consultant powered by Azure OpenAI. Users chat in a **Streamlit** UI; a **FastAPI** backend exposes an OpenAPI-documented API and runs the agent logic. A **skill file** defines how the agent recommends destinations, hotels, weather, and food.

## Status

**MVP scaffold implemented** — backend, frontend, skill file, and baseline tests are present.

## Stack

| Layer | Technology |
|-------|------------|
| UI | Streamlit (Python) |
| API | FastAPI + OpenAPI |
| Agent | Azure OpenAI via OpenAI Python SDK |
| Guidance | Travel consultant skill file (`skills/travel-consultant/SKILL.md`) |

## Architecture

```mermaid
flowchart LR
    User[Traveler] --> UI[Streamlit chat UI<br/>frontend/app.py]
    UI -->|POST /api/v1/chat| API[FastAPI backend<br/>backend/main.py]
    API --> Memory[In-memory conversation store<br/>backend/memory.py]
    API --> Skill[Travel consultant skill<br/>skills/travel-consultant/SKILL.md]
    API --> Agent[Agent wrapper<br/>backend/agent.py]
    Agent -->|Responses API| Azure[Azure OpenAI GPT deployment]
    Azure --> Agent
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
- Azure OpenAI resource endpoint, API key, and GPT deployment name

## Getting started

1. Create and activate a Python virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and `AZURE_OPENAI_DEPLOYMENT`.
4. Start API:
   - `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
5. Start UI:
   - `streamlit run frontend/app.py`
6. Open the Streamlit URL and ask for trip advice.

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
