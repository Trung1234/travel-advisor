from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from openai import AzureOpenAI

from .config import settings
from .skill_loader import load_skill


SKILL_PROMPT = load_skill(settings.skill_file_path)


def normalize_azure_endpoint(endpoint: str) -> str:
    parsed = urlsplit(endpoint)
    if not parsed.scheme or not parsed.netloc:
        return endpoint.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")


@lru_cache
def get_client() -> AzureOpenAI:
    if not settings.azure_openai_api_key or settings.azure_openai_api_key == "your-azure-openai-api-key":
        raise RuntimeError("AZURE_OPENAI_API_KEY is not configured")
    if not settings.azure_openai_endpoint or "your-resource-name" in settings.azure_openai_endpoint:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured")
    if not settings.azure_openai_deployment or settings.azure_openai_deployment == "your-gpt-deployment-name":
        raise RuntimeError("AZURE_OPENAI_DEPLOYMENT is not configured")

    endpoint = normalize_azure_endpoint(settings.azure_openai_endpoint)

    return AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=endpoint,
        api_version=settings.azure_openai_api_version,
    )


def get_reply(message: str, history: list[dict[str, str]]) -> str:
    messages = [*history, {"role": "user", "content": message}]
    client = get_client()
    response = client.responses.create(
        model=settings.azure_openai_deployment,
        instructions=SKILL_PROMPT,
        input=messages,
    )
    content = response.output_text
    return content or "I'm sorry, I couldn't generate a reply right now."
