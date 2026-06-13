# Class Diagram Specification — Voice Travel Agent

This document outlines the main classes, schemas, and configurations of the Voice Travel Agent system.

## Class Diagram

```mermaid
classDiagram
    class Settings {
        +azure_openai_api_key : str | None
        +azure_openai_endpoint : str | None
        +azure_openai_deployment : str | None
        +azure_openai_api_version : str
        +serpapi_api_key : str | None
        +serpapi_limit : int
        +skill_file_path : str
        +cors_origins : list~str~
        +tts_engine : str
        +tts_voice : str | None
        +tts_rate : int
        +tts_volume : float
        +redis_url : str
        +redis_ttl : int
    }

    class ChatRequest {
        +message : str
        +conversation_id : str | None
    }

    class ChatResponse {
        +reply : str
        +conversation_id : str
    }

    class HealthResponse {
        +status : str
    }

    class TTSRequest {
        +text : str
    }

    class TTSResponse {
        +content_type : str
        +filename : str
        +size_bytes : int
        +sample_rate : int | None
    }

    class SerpApiResult {
        +title : str
        +link : str
        +snippet : str | None
    }

    class SerpApiClient {
        +api_key : str | None
        +limit : int
        +enabled() bool
        +search(query : str) list~SerpApiResult~
    }

    class SerpApiClientError {
    }

    class ApiClientError {
    }

    SerpApiClient ..> SerpApiResult : creates
    SerpApiClient --> Settings : loads settings
    SerpApiClientError --|> RuntimeError : inherits
    ApiClientError --|> RuntimeError : inherits
```

## Descriptions

### 1. Configuration & Settings
- **[Settings](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/config.py#L15-L29)**: Responsible for reading all project settings from env files (`.env`, `.env.example`).

### 2. Request/Response Schemas (Pydantic Models)
- **[ChatRequest](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/schemas.py#L6-L8)**: Used for incoming chat requests. Strips whitespace and requires at least 1 character.
- **[ChatResponse](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/schemas.py#L11-L13)**: Holds reply content and matching conversation ID.
- **[HealthResponse](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/schemas.py#L16-L17)**: Body of the `/health` endpoint.
- **[TTSRequest](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/schemas.py#L20-L21)**: Stores text string to be synthesized.
- **[TTSResponse](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/schemas.py#L24-L29)**: Describes the generated audio metadata structure.

### 3. SerpAPI Client Layer
- **[SerpApiClient](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/serpapi_client.py#L21-L58)**: Calls SerpAPI Google Search API. Retrieves top pages to enrich the travel agent's response.
- **[SerpApiResult](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/serpapi_client.py#L11-L14)**: Dataclass encapsulating organic Google Search results (title, link, snippet).
