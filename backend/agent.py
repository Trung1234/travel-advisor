from functools import lru_cache

# pyrefly: ignore [missing-import]
from openai import OpenAI

from .config import settings
from .skill_loader import load_skill
from .serpapi_client import SerpApiClientError, get_serpapi_results


SKILL_PROMPT = load_skill(settings.skill_file_path)


# Keywords that signal the user wants grounded, factual info (travel logistics
# OR history/culture). When any of these appear, we fetch live search results so
# the model answers from real sources instead of hallucinating dates/names/figures.
SEARCH_TRIGGER_KEYWORDS = (
    # Travel logistics (EN)
    "hotel", "stay", "destination", "city", "where", "place", "area",
    "weather", "food", "dining", "restaurant", "eat", "tour", "landmark",
    # History & culture (EN)
    "history", "historical", "culture", "cultural", "heritage", "festival",
    "tradition", "traditional", "temple", "pagoda", "monument", "origin",
    "founded", "century", "dynasty", "unesco",
    # Travel logistics (VI)
    "khách sạn", "khach san", "ở đâu", "o dau", "điểm đến", "diem den",
    "thời tiết", "thoi tiet", "ẩm thực", "am thuc", "món", "mon", "quán", "quan an",
    "du lịch", "du lich", "tham quan",
    # History & culture (VI)
    "lịch sử", "lich su", "văn hóa", "van hoa", "di tích", "di tich",
    "lễ hội", "le hoi", "truyền thống", "truyen thong", "di sản", "di san",
    "nguồn gốc", "nguon goc", "danh lam", "thắng cảnh", "thang canh",
    "đền", "chùa", "chua", "miếu", "mieu", "quan họ", "quan ho",
)


def _format_serpapi_context(message: str) -> str:
    lower_message = message.lower()
    if not any(keyword in lower_message for keyword in SEARCH_TRIGGER_KEYWORDS):
        return ""

    try:
        results = get_serpapi_results(message)
    except SerpApiClientError:
        return ""

    if not results:
        return ""

    lines = [
        "Search context (live Google results — use these as the factual source; "
        "do NOT state specific dates, names, or figures that are not supported here):"
    ]
    for res in results:
        parts = [f"Title: {res.title}"]
        if res.snippet:
            parts.append(f"Snippet: {res.snippet}")
        if res.link:
            parts.append(f"Link: {res.link}")
        lines.append("- " + "; ".join(parts))
    return "\n".join(lines)


@lru_cache
def get_client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(
        api_key=settings.openai_api_key,
    )


def get_reply(message: str, history: list[dict[str, str]]) -> str:
    messages = [*history, {"role": "user", "content": message}]
    serpapi_context = _format_serpapi_context(message)
    if serpapi_context:
        messages.insert(-1, {"role": "system", "content": serpapi_context})

    client = get_client()
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": SKILL_PROMPT}, *messages],
    )
    content = response.choices[0].message.content if response.choices else None
    return content or "I'm sorry, I couldn't generate a reply right now."


def check_guardrails(message: str) -> bool:
    """
    Checks if a user query violates the guardrail rules (e.g. asking about programming/coding).
    Returns True if the message is valid (travel/sightseeing related).
    Returns False if it is invalid.
    """
    prohibited_keywords = {
        "code", "lập trình", "python", "javascript", "c++", "java", "html", "css",
        "programming", "software", "developer", "viết hàm", "thuật toán", "algorithm",
        "sql", "git", "class", "function", "coding", "viết code"
    }
    lower_message = message.lower()
    if any(kw in lower_message for kw in prohibited_keywords):
        return False

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict guardrail classifier for a Travel & Culture Consultant. "
                        "Output 'valid' if the user query is related to travel, sightseeing, trip planning, hotels, weather, "
                        "food/dining, landmarks, OR the history, culture, heritage, festivals, customs, or traditions of a "
                        "place or destination (e.g. 'lịch sử Bắc Ninh', 'văn hóa Hội An', 'nguồn gốc quan họ'). "
                        "Greetings and follow-up questions about a place are also 'valid'. "
                        "Output 'invalid' ONLY if the query is about programming, coding, software, engineering, abstract "
                        "mathematics, or general-knowledge topics with no connection to a place or trip. "
                        "Output ONLY 'valid' or 'invalid' with no other text."
                    )
                },
                {"role": "user", "content": message}
            ],
            temperature=0.0,
            max_tokens=5
        )
        result = response.choices[0].message.content.strip().lower()
        if "invalid" in result:
            return False
    except Exception:
        # Fallback to True to avoid completely blocking the user in case of connection failure
        return True
    return True
