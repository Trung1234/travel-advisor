from pathlib import Path

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


class RAGSettings(BaseSettings):
    enabled: bool = False
    provider: str = "azure"  # or "chroma" for local dev
    azure_search_endpoint: str | None = None
    azure_search_api_key: str | None = None
    index_name: str = "travel-docs"
    chunk_size: int = 600
    chunk_overlap: int = 50
    retrieval_top_k: int = 10

    model_config = SettingsConfigDict(env_prefix="RAG_", extra="ignore")


class Settings(BaseSettings):
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-12-01-preview"
    serpapi_api_key: str | None = None
    serpapi_limit: int = 5
    skill_file_path: str = "skills/travel-consultant/SKILL.md"
    cors_origins: list[str] = ["http://localhost:8501"]
    tts_engine: str = "pyttsx3"
    tts_voice: str | None = None
    tts_rate: int = 180
    tts_volume: float = 1.0
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl: int = 7200

    # RAG Configuration
    rag_settings: RAGSettings = RAGSettings()

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")


settings = Settings()
