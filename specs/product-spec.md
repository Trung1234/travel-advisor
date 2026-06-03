# Product specification — Voice Travel Agent MVP

**Version:** 0.2.0  
**Status:** Draft (spec only, not implemented)

## 1. Summary

A voice-based travel agent where users speak about a trip and receive AI-generated travel advice through speech and text: destination ideas, hotel suggestions, weather outlook, and food recommendations.

## 2. Goals

- Deliver useful, conversational trip planning through voice-first interactions.
- Support a clear audio pipeline: speech input, transcription, reasoning, and spoken output.
- Separate UI (Streamlit) from API (FastAPI) for clarity and testability.
- Encode travel-agent behavior in a reusable **travel consultant skill** file.

## 3. Non-goals (MVP)

- Booking flights, hotels, or restaurants
- Storing user accounts or chat history in a database
- Guaranteed real-time weather or pricing data
- Multi-language support
- Full telephony/contact-center integration

## 4. Users

- **Traveler** — anyone planning a leisure or short business trip via voice or chat UI.

## 5. User stories

| ID | Story | Acceptance |
|----|--------|------------|
| US-1 | As a traveler, I open the app and see a voice travel interface | Streamlit loads; title and short instructions visible |
| US-2 | As a traveler, I speak about my trip | Audio can be captured and turned into a request |
| US-3 | As a traveler, I receive destination recommendations | Reply includes 1–3 destinations with brief rationale |
| US-4 | As a traveler, I ask for hotels | Reply suggests options aligned with stated budget/style |
| US-5 | As a traveler, I ask about weather | Reply describes typical/seasonal weather; notes if dates unknown |
| US-6 | As a traveler, I ask for food spots | Reply lists areas or types of venues; optional dish ideas |
| US-7 | As a developer, I call the API directly | OpenAPI docs work; `POST /api/v1/chat` returns JSON |

## 6. Functional requirements

### 6.1 Streamlit UI

- Single-page voice-first chat with message history for the current browser session.
- Text input remains available as a fallback alongside voice interaction.
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
- Support voice-agent orchestration in the application flow.
- Load model/provider settings from environment.
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

### 6.4 Model/provider integration

- Support **Qwen** as the primary model family.
- Support **Ollama** for local model execution.
- Provider, model name, and base URL are configurable via environment variables.
- Single-turn or short multi-turn context within the same `conversation_id` (in-memory for MVP).

## 7. Non-functional requirements

| Area | Requirement |
|------|-------------|
| Simplicity | Minimal dependencies; no database for MVP |
| Latency | Target &lt; 15s for typical replies (depends on local or hosted model runtime) |
| Security | API key / access credentials server-side only; no secrets in Streamlit client |
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
| `MODEL_PROVIDER` | Yes | `qwen` or `ollama` |
| `QWEN_MODEL` | Optional | Qwen model name when using hosted/local Qwen runtime |
| `OLLAMA_BASE_URL` | Optional | Ollama server URL (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | Optional | Ollama model name |
| `API_BASE_URL` | No | Used by Streamlit (default `http://localhost:8000`) |

## 10. Success criteria (MVP)

- [ ] User can complete a full voice-first chat flow in Streamlit without errors.
- [ ] API documented at `/docs` and matches this contract.
- [ ] Skill file exists and is loaded for every chat request.
- [ ] Manual test scenarios in `specs/test-plan.md` pass.

## 11. Future (post-MVP)

- Speech-to-text and text-to-speech UI polish
- Live weather API (e.g. OpenWeatherMap)
- Hotel/places search API
- Persistent conversations
- Docker Compose for one-command run
- Real-time voice streaming
