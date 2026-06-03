from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    model_provider: str = "ollama"
    qwen_model: str = "qwen2.5:7b"
    qwen_base_url: str | None = None
    qwen_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    tripadvisor_api_key: str | None = None
    tripadvisor_base_url: str | None = None
    tripadvisor_endpoint: str = "/api/partners/v2/location_search"
    tripadvisor_limit: int = 5
    skill_file_path: str = "skills/travel-consultant/SKILL.md"
    cors_origins: list[str] = ["http://localhost:8501"]

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")


settings = Settings()
