from functools import lru_cache

from openai import OpenAI

from .config import settings
from .skill_loader import load_skill
from .tripadvisor_client import TripAdvisorClientError, get_tripadvisor_places


SKILL_PROMPT = load_skill(settings.skill_file_path)


def _format_tripadvisor_context(message: str) -> str:
    lower_message = message.lower()
    if not any(keyword in lower_message for keyword in ("hotel", "stay", "destination", "city", "where", "place", "area")):
        return ""

    category = "hotels" if any(keyword in lower_message for keyword in ("hotel", "stay")) else "destinations"
    try:
        places = get_tripadvisor_places(message, category=category)
    except TripAdvisorClientError:
        return ""

    if not places:
        return ""

    lines = ["TripAdvisor context:"]
    for place in places:
        parts = [place.name]
        if place.rating is not None:
            parts.append(f"rating={place.rating:.1f}")
        if place.review_count is not None:
            parts.append(f"reviews={place.review_count}")
        if place.address:
            parts.append(f"address={place.address}")
        lines.append("- " + "; ".join(parts))
    return "\n".join(lines)


@lru_cache
def get_client() -> OpenAI:
    provider = settings.model_provider.lower().strip()
    if provider == "ollama":
        return OpenAI(base_url=f"{settings.ollama_base_url.rstrip('/')}/v1", api_key="ollama")
    if provider == "qwen":
        if not settings.qwen_base_url:
            raise RuntimeError("QWEN_BASE_URL is not configured")
        return OpenAI(base_url=f"{settings.qwen_base_url.rstrip('/')}/v1", api_key=settings.qwen_api_key or "qwen")
    raise RuntimeError(f"Unsupported MODEL_PROVIDER: {settings.model_provider}")


def get_reply(message: str, history: list[dict[str, str]]) -> str:
    messages = [*history, {"role": "user", "content": message}]
    tripadvisor_context = _format_tripadvisor_context(message)
    if tripadvisor_context:
        messages.insert(-1, {"role": "system", "content": tripadvisor_context})

    client = get_client()
    model_name = settings.ollama_model if settings.model_provider.lower().strip() == "ollama" else settings.qwen_model
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": SKILL_PROMPT}, *messages],
    )
    content = response.choices[0].message.content if response.choices else None
    return content or "I'm sorry, I couldn't generate a reply right now."
