# Guideline: Migrating Short-Term Memory to Redis

This guide provides instructions and code templates to migrate the Voice Travel Agent MVP's short-term chat session memory from an in-memory dictionary to **Redis**. 

Currently, chat history is stored in an in-memory dictionary within [backend/memory.py](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/memory.py). This data is lost whenever the FastAPI backend restarts. Using Redis enables session persistence, cross-process data sharing, and horizontal scaling.

---

## 1. Overview of Changes

To implement Redis-based short-term memory, we will update the following components:
1. **Dependencies**: Add `redis` to [requirements.txt](file:///Users/macmini/Desktop/AIApp/travel-advisor/requirements.txt).
2. **Environment Variables**: Define `REDIS_URL` and `REDIS_TTL` in [.env](file:///Users/macmini/Desktop/AIApp/travel-advisor/.env) and [.env.example](file:///Users/macmini/Desktop/AIApp/travel-advisor/.env.example).
3. **Application Configuration**: Update [backend/config.py](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/config.py) to read the new Redis settings.
4. **Memory Layer**: Rewrite [backend/memory.py](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/memory.py) to use Redis lists (`RPUSH`, `LRANGE`) with JSON serialization/deserialization.
5. **Robustness**: Implement graceful fallback or descriptive error handling if the Redis server is unreachable.

---

## 2. Configuration & Environment Setup

### 2.1 Update [.env.example](file:///Users/macmini/Desktop/AIApp/travel-advisor/.env.example) & [.env](file:///Users/macmini/Desktop/AIApp/travel-advisor/.env)
Add the following configuration lines to your environment files:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_TTL=7200  # Session expiration in seconds (e.g., 2 hours)
```

### 2.2 Update [backend/config.py](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/config.py)
In corporate settings, define the defaults in `Settings` class:

```python
class Settings(BaseSettings):
    # ... (existing settings) ...
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl: int = 7200  # Default 2 hours TTL
```

---

## 3. Dependency Updates

Add `redis` to your [requirements.txt](file:///Users/macmini/Desktop/AIApp/travel-advisor/requirements.txt) file:

```txt
redis>=5.0.0
```

*Make sure to run `pip install -r requirements.txt` to install the package.*

---

## 4. Coding the Redis Memory Layer

We will modify [backend/memory.py](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/memory.py). Below is the recommended implementation using Redis list commands which allow efficient appending of messages.

### [backend/memory.py](file:///Users/macmini/Desktop/AIApp/travel-advisor/backend/memory.py) Template

```python
import json
import logging
from typing import Any
import redis
from .config import settings

logger = logging.getLogger("backend.memory")

# Initialize the Redis client
# Using decode_responses=True so that returned values are strings rather than bytes
try:
    redis_client = redis.Redis.from_url(
        settings.redis_url, 
        decode_responses=True,
        socket_timeout=2.0,
        socket_connect_timeout=2.0
    )
except Exception as exc:
    logger.error(f"Failed to initialize Redis client: {exc}")
    redis_client = None

def get_history(conversation_id: str) -> list[dict[str, str]]:
    """
    Retrieve conversation history from Redis.
    If Redis is unavailable, returns an empty list.
    """
    if redis_client is None:
        logger.warning("Redis client is not initialized. Returning empty history.")
        return []
        
    key = f"chat:{conversation_id}"
    try:
        # Retrieve all items in the Redis list
        messages_raw = redis_client.lrange(key, 0, -1)
        return [json.loads(msg) for msg in messages_raw]
    except redis.RedisError as exc:
        logger.error(f"Failed to fetch history from Redis for {conversation_id}: {exc}")
        return []

def append_message(conversation_id: str, role: str, content: str) -> None:
    """
    Append a new message to the conversation history in Redis and refresh key TTL.
    """
    if redis_client is None:
        logger.warning("Redis client is not initialized. Cannot store message.")
        return
        
    key = f"chat:{conversation_id}"
    message_data = json.dumps({"role": role, "content": content})
    
    try:
        # Push message to the end of the list
        redis_client.rpush(key, message_data)
        # Refresh key TTL to prevent orphaned sessions
        redis_client.expire(key, settings.redis_ttl)
    except redis.RedisError as exc:
        logger.error(f"Failed to append message to Redis for {conversation_id}: {exc}")
```

> [!TIP]
> **Graceful Degradation / In-Memory Fallback:**
> If you want the API to remain operational even when Redis is down, you can implement a dual-mode fallback that uses local memory (`dict`) if Redis operations fail or if Redis is unreachable.

---

## 5. Local Redis Development

For local testing, the easiest way to run Redis is via Docker:

```bash
# Start a Redis container
docker run --name travel-redis -p 6379:6379 -d redis

# Verify it is running
docker ps
```

---

## 6. Manual Verification & Testing

### 6.1 Inspecting Data in Redis
You can use `redis-cli` inside the Docker container or locally to monitor stored chat sessions:

```bash
# Connect to the local Redis instance
redis-cli

# List all active conversation keys
keys chat:*

# Fetch the messages for a specific conversation_id
lrange chat:<conversation_id> 0 -1

# Check remaining TTL (in seconds) for a conversation session
ttl chat:<conversation_id>
```

### 6.2 Testing Persistence Across FastAPI Restarts
1. Start the backend (`uvicorn backend.main:app`) and frontend (`streamlit run frontend/app.py`).
2. Exchange 2-3 messages in the Streamlit UI.
3. Stop/Kill the FastAPI backend server.
4. Restart the FastAPI backend server.
5. Send another message. The assistant should still have full context of the preceding messages in the thread, confirming that state is safely stored in Redis rather than inside the FastAPI memory space.

---

## 7. Automated Test Mocking

To ensure unit tests in [tests/test_chat.py](file:///Users/macmini/Desktop/AIApp/travel-advisor/tests/test_chat.py) pass without requiring a live running Redis database:

1. Use standard `unittest.mock` or a library like `fakeredis` in tests.
2. Example mock configuration:

```python
from unittest.mock import patch, MagicMock
import pytest

@pytest.fixture(autouse=True)
def mock_redis():
    with patch("backend.memory.redis_client") as mock_client:
        # Simulate an in-memory dict behavior on the mock if needed,
        # or mock lrange/rpush calls specifically.
        mock_client.lrange.return_value = []
        yield mock_client
```
