import uuid
from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAIError

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.agent import get_reply
    from backend.config import settings
    from backend.memory import append_message, get_history
    from backend.schemas import ChatRequest, ChatResponse, HealthResponse
else:
    from .agent import get_reply
    from .config import settings
    from .memory import append_message, get_history
    from .schemas import ChatRequest, ChatResponse, HealthResponse

app = FastAPI(title="Travel Advisor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    history = get_history(conversation_id)

    try:
        reply = get_reply(payload.message, history)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate reply: {exc}")

    append_message(conversation_id, "user", payload.message)
    append_message(conversation_id, "assistant", reply)

    return ChatResponse(reply=reply, conversation_id=conversation_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000)
