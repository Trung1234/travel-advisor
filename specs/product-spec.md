# Product specification — Travel Advisor MVP

**Version:** 0.1.0  
**Status:** Draft (spec only, not implemented)

## 1. Summary

A web app where users describe a trip (destination, dates, budget, preferences) and receive AI-generated travel advice: destination ideas, hotel suggestions, weather outlook, and food recommendations.

## 2. Goals

- Deliver useful, conversational trip planning in one session.
- Separate UI (Streamlit) from API (FastAPI) for clarity and testability.
- Encode consultant behavior in a reusable **travel consultant skill** file.

## 3. Non-goals (MVP)

- Booking flights, hotels, or restaurants
- Storing user accounts or chat history in a database
- Guaranteed real-time weather or pricing data
- Multi-language support

## 4. Users

- **Traveler** — anyone planning a leisure or short business trip via the chat UI.

## 5. User stories

| ID | Story | Acceptance |
|----|--------|------------|
| US-1 | As a traveler, I open the app and see a chat interface | Streamlit loads; title and short instructions visible |
| US-2 | As a traveler, I send a message about my trip | Message appears in chat; loading state shown |
| US-3 | As a traveler, I receive destination recommendations | Reply includes 1–3 destinations with brief rationale |
| US-4 | As a traveler, I ask for hotels | Reply suggests options aligned with stated budget/style |
| US-5 | As a traveler, I ask about weather | Reply describes typical/seasonal weather; notes if dates unknown |
| US-6 | As a traveler, I ask for food spots | Reply lists areas or types of venues; optional dish ideas |
| US-7 | As a developer, I call the API directly | OpenAPI docs work; `POST /api/v1/chat` returns JSON |

## 6. Functional requirements

### 6.1 Streamlit UI

- Single-page chat with message history for the current browser session.
- Text input and send action (button or Enter).
- Display user and assistant messages in order.
- Show error banner if API is unreachable or returns an error.
- Optional sidebar: trip hints (destination, dates, budget) — **nice-to-have**, not required for MVP.

### 6.2 FastAPI backend

- **POST `/api/v1/chat`**
  - Request body: `{ "message": string, "conversation_id"?: string }`
  - Response body: `{ "reply": string, "conversation_id": string }`
- OpenAPI 3 schema auto-generated at `/docs` and `/openapi.json`.
- Health check: **GET `/health`** → `{ "status": "ok" }`.
- CORS enabled for local Streamlit origin.
- Load Azure OpenAI credentials from environment.
- Inject travel consultant skill content into the model context.

### 6.3 Travel consultant skill

File: `skills/travel-consultant/SKILL.md`

Must instruct the agent to:

- Act as a friendly, concise travel consultant.
- Ask clarifying questions when destination, dates, or budget are missing.
- Provide structured sections when relevant: **Destination**, **Hotels**, **Weather**, **Food**.
- Include practical tips (best time to visit, neighborhood notes).
- State limitations: recommendations are informational, not bookings; weather may be approximate without live APIs.
- Avoid unsafe advice and respect local laws/customs.

### 6.4 Azure OpenAI integration

- Use official OpenAI Python SDK.
- Azure endpoint, API key, deployment name, and API version are configurable via environment variables.
- Deployment: configurable via `AZURE_OPENAI_DEPLOYMENT` (the Azure deployment name for a capable GPT chat model).
- Single-turn or short multi-turn context within the same `conversation_id` (in-memory for MVP).

## 7. Non-functional requirements

| Area | Requirement |
|------|-------------|
| Simplicity | Minimal dependencies; no database for MVP |
| Latency | Target &lt; 15s for typical replies (depends on Azure OpenAI) |
| Security | API key server-side only; no key in Streamlit client |
| Config | `.env` for secrets; `.env.example` committed |

## 8. API contract (draft)

### POST `/api/v1/chat`

**Request**

```json
{
  "message": "I want a beach trip in Spain for 5 days in June, mid budget.",
  "conversation_id": "optional-uuid"
}
```

**Response 200**

```json
{
  "reply": "Here are some ideas for your June trip...",
  "conversation_id": "generated-or-echoed-uuid"
}
```

**Response 4xx/5xx**

```json
{
  "detail": "Human-readable error message"
}
```

## 9. Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Yes | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Azure deployment name for the GPT chat model |
| `AZURE_OPENAI_API_VERSION` | No | Azure OpenAI API version |
| `API_BASE_URL` | No | Used by Streamlit (default `http://localhost:8000`) |

## 10. Success criteria (MVP)

- [ ] User can complete a full chat flow in Streamlit without errors.
- [ ] API documented at `/docs` and matches this contract.
- [ ] Skill file exists and is loaded for every chat request.
- [ ] Manual test scenarios in `specs/test-plan.md` pass.

## 11. Future (post-MVP)

- Live weather API (e.g. OpenWeatherMap)
- Hotel/places search API
- Persistent conversations
- Docker Compose for one-command run
