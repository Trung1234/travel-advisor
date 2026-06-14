# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGSettings(BaseSettings):
    """RAG-specific configuration settings"""

    # Core settings
    enabled: bool = False
    provider: str = "azure"  # "azure" or "chroma"

    # Azure AI Search
    azure_search_endpoint: str | None = None
    azure_search_api_key: str | None = None
    azure_search_index_name: str = "travel-docs"

    # Chroma (local development)
    chroma_persist_dir: str = "./chroma_db"

    # Embedding settings
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072

    # Chunking settings
    chunk_size: int = 600
    chunk_overlap: int = 50
    min_chunk_size: int = 300

    # Retrieval settings
    retrieval_top_k: int = 10
    vector_weight: float = 0.7
    keyword_weight: float = 0.3

    # Performance settings
    batch_size: int = 100
    connection_timeout: int = 30

    model_config = SettingsConfigDict(env_prefix="RAG_", extra="ignore")