from functools import lru_cache

# pyrefly: ignore [missing-import]
from openai import AzureOpenAI

from .config import settings
from .skill_loader import load_skill
from .serpapi_client import SerpApiClientError, get_serpapi_results
from .rag.rag_client import get_rag_context, RAGClientError


SKILL_PROMPT = load_skill(settings.skill_file_path)


def _format_serpapi_context(message: str) -> str:
    lower_message = message.lower()
    if not any(keyword in lower_message for keyword in ("hotel", "stay", "destination", "city", "where", "place", "area", "weather", "food", "dining", "restaurant", "eat")):
        return ""

    try:
        results = get_serpapi_results(message)
    except SerpApiClientError:
        return ""

    if not results:
        return ""

    lines = ["Search context:"]
    for res in results:
        parts = [f"Title: {res.title}"]
        if res.snippet:
            parts.append(f"Snippet: {res.snippet}")
        if res.link:
            parts.append(f"Link: {res.link}")
        lines.append("- " + "; ".join(parts))
    return "\n".join(lines)


def _format_rag_context(message: str) -> str:
    """Get RAG context from verified knowledge base. Graceful fallback if RAG is disabled or fails."""
    if not settings.rag_settings.enabled:
        return ""

    try:
        context = get_rag_context(message)
        return context.formatted_for_prompt()
    except RAGClientError:
        return ""


@lru_cache
def get_client() -> AzureOpenAI:
    if not settings.azure_openai_api_key:
        raise RuntimeError("AZURE_OPENAI_API_KEY is not configured")
    if not settings.azure_openai_endpoint:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured")
    return AzureOpenAI(
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )


def get_reply(message: str, history: list[dict[str, str]]) -> str:
    messages = [*history, {"role": "user", "content": message}]

    # RAG context (structured, cited information from verified knowledge base)
    rag_context = _format_rag_context(message)
    if rag_context:
        messages.insert(-1, {"role": "system", "content": f"[VERIFIED KNOWLEDGE]\n{rag_context}"})

    # SerpAPI context (fresh web data)
    serpapi_context = _format_serpapi_context(message)
    if serpapi_context:
        messages.insert(-1, {"role": "system", "content": serpapi_context})

    client = get_client()
    response = client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[{"role": "system", "content": SKILL_PROMPT}, *messages],
    )
    content = response.choices[0].message.content if response.choices else None
    return content or "I'm sorry, I couldn't generate a reply right now."
