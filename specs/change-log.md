# Change log — Travel Advisor

Record **spec and product** changes here. Implementation details can be noted briefly; use git commits for code history.

Format: newest first.

---

## [0.2.1] — 2026-05-23 — Switch backend to Azure OpenAI

**Type:** Spec change | Fix
**Scope:** product-spec | implementation-plan

### Changed

- Replaced standard OpenAI environment variables with Azure OpenAI variables.
- Backend now uses Azure OpenAI endpoint, deployment, API key, and API version configuration.
- README and env templates now document Azure OpenAI setup.

### Why

- The app is being configured to use Azure-hosted GPT deployments.

### Impact on implementation

- `AZURE_OPENAI_DEPLOYMENT` must be the Azure deployment name, not just the base model name.
- Existing local `.env` files using `OPENAI_API_KEY` / `OPENAI_MODEL` must be migrated.

---

## [0.2.0] — 2026-05-23 — MVP scaffold implemented

**Type:** Feature  
**Scope:** implementation-plan | test-plan

### Added (MVP scaffold)

- `.gitignore`, `.env.example`, `requirements.txt`
- `skills/travel-consultant/SKILL.md`
- `backend/` FastAPI modules (`main.py`, `config.py`, `schemas.py`, `skill_loader.py`, `agent.py`, `memory.py`)
- `frontend/` Streamlit app (`app.py`) and API client (`api_client.py`)
- `tests/test_health.py`, `tests/test_chat.py`

### Changed

- `README.md` updated from spec-only state to runnable MVP instructions

### Why

- Implement planned MVP architecture from approved specs for end-to-end travel chat flow

### Impact on implementation

- Project now has runnable backend/UI scaffold and baseline API contract tests

---

## [0.1.0] — 2026-05-23 — Initial specs (no code)

**Type:** Spec created  
**Author:** Spec-driven setup

### Added (initial spec set)

- `README.md` — project overview and planned stack
- `AGENTS.md` — instructions for AI coding agents
- `specs/product-spec.md` — MVP product requirements
- `specs/implementation-plan.md` — phased build plan
- `specs/test-plan.md` — automated and manual test cases
- `specs/change-log.md` — this file

### Decisions

- Project location: `D:\travel-advisor`
- Architecture: Streamlit UI + FastAPI backend + OpenAI + travel consultant skill file
- MVP excludes auth, database, and live third-party travel/weather APIs
- In-memory `conversation_id` for short multi-turn chats

### Not included yet

- Application source code (`backend/`, `frontend/`, `skills/`)
- `requirements.txt`, `.env.example`, tests

### Next steps

1. Review and approve specs
2. Implement per `implementation-plan.md` (skill → API → UI → tests)
3. Log future spec changes in this file before coding scope changes

---

## Template for future entries

```markdown
## [x.y.z] — YYYY-MM-DD — Short title

**Type:** Spec change | Feature | Fix  
**Scope:** product-spec | implementation-plan | test-plan

### Changed
- ...

### Why
- ...

### Impact on implementation
- ...
```
