# Implementation plan — Travel Advisor MVP

**Prerequisite:** Specs approved. Do not start coding until product-spec and this plan are agreed.

**Order:** Work top to bottom. Check off items in `specs/change-log.md` when phases complete.

---

## Phase 0 — Repository setup

| # | Task | Output |
|---|------|--------|
| 0.1 | Confirm project root: `D:\travel-advisor` | Git repo initialized |
| 0.2 | Add `.gitignore` (Python, `.env`, `__pycache__`, `.venv`) | Ignored secrets |
| 0.3 | Add `.env.example` with documented variables | Template for developers |
| 0.4 | Add `requirements.txt` (pinned loosely or minimum versions) | Installable deps |

**Dependencies (planned):**

```
fastapi
uvicorn[standard]
streamlit
openai
httpx
pydantic-settings
python-dotenv
```

---

## Phase 1 — Travel consultant skill

| # | Task | Output |
|---|------|--------|
| 1.1 | Create `skills/travel-consultant/SKILL.md` | Skill matches product-spec §6.3 |
| 1.2 | Add short “WHEN” line at top for agent discovery | Consistent with other skills |

No code beyond the markdown skill file in this phase.

---

## Phase 2 — FastAPI backend

| # | Task | Output |
|---|------|--------|
| 2.1 | `backend/config.py` — settings from env | `Settings` class |
| 2.2 | `backend/skill_loader.py` — read SKILL.md | String for system prompt |
| 2.3 | `backend/agent.py` — Azure OpenAI chat call with skill + history | `get_reply(message, history)` |
| 2.4 | `backend/memory.py` — in-memory dict by `conversation_id` | MVP session store |
| 2.5 | `backend/main.py` — FastAPI app, CORS, routes | `/health`, `/api/v1/chat` |
| 2.6 | `backend/schemas.py` — Pydantic request/response models | OpenAPI types |

**Structure:**

```
backend/
├── __init__.py
├── main.py
├── config.py
├── schemas.py
├── skill_loader.py
├── agent.py
└── memory.py
```

**Run:** `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`

---

## Phase 3 — Streamlit frontend

| # | Task | Output |
|---|------|--------|
| 3.1 | `frontend/app.py` — chat UI with `st.chat_message` | Session messages |
| 3.2 | `frontend/api_client.py` — POST to `/api/v1/chat` via httpx | Error handling |
| 3.3 | Store `conversation_id` in `st.session_state` | Thread continuity |
| 3.4 | Page title and one-line instructions | US-1 |

**Run:** `streamlit run frontend/app.py`

---

## Phase 4 — Integration and polish

| # | Task | Output |
|---|------|--------|
| 4.1 | Verify end-to-end: UI → API → Azure OpenAI → UI | Demo-ready |
| 4.2 | README run instructions match actual commands | Docs accurate |
| 4.3 | Log completion in `specs/change-log.md` | Traceability |

---

## Phase 5 — Tests (see test-plan)

| # | Task | Output |
|---|------|--------|
| 5.1 | `tests/test_health.py` | Health endpoint |
| 5.2 | `tests/test_chat.py` — mock Azure OpenAI | Chat contract without live API |
| 5.3 | Manual scenarios from test-plan | Checklist signed off |

**Run tests:** `pytest` (add `pytest`, `pytest-asyncio` to dev deps if needed)

---

## Configuration defaults

| Setting | Default |
|---------|---------|
| API port | 8000 |
| Streamlit port | 8501 |
| `API_BASE_URL` | `http://localhost:8000` |
| `AZURE_OPENAI_API_VERSION` | `2024-02-15-preview` |

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Azure OpenAI rate limits / cost | Use an appropriately sized deployment; document usage |
| Hallucinated hotels/prices | Skill requires disclaimers; no “book now” claims |
| CORS issues locally | Allow `http://localhost:8501` in FastAPI |
| Skill file not found | Fail fast at startup with clear error |

---

## Definition of done (MVP)

- All Phase 0–5 tasks complete
- `specs/test-plan.md` manual + automated checks pass
- No scope from product-spec “Non-goals” included
