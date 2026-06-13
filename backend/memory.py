from collections import defaultdict
import json
import logging
# pyrefly: ignore [missing-import]
import redis
from .config import settings

logger = logging.getLogger("backend.memory")

# Fallback in-memory store
_local_conversations: dict[str, list[dict[str, str]]] = defaultdict(list)

# Initialize the Redis client
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
    Falls back to in-memory store if Redis is unavailable or fails.
    """
    if redis_client is not None:
        key = f"chat:{conversation_id}"
        try:
            messages_raw = redis_client.lrange(key, 0, -1)
            # If we successfully read from Redis, return it
            return [json.loads(msg) for msg in messages_raw]
        except redis.RedisError as exc:
            logger.warning(
                f"Redis connection failed when fetching history for {conversation_id}: {exc}. "
                f"Falling back to in-memory storage."
            )
    
    # Fallback to local memory
    return _local_conversations[conversation_id]


def append_message(conversation_id: str, role: str, content: str) -> None:
    """
    Append a new message to the conversation history.
    Stores in Redis (with TTL) and always synchronizes to in-memory fallback.
    """
    # Always update the local fallback cache to keep it warm/up-to-date
    _local_conversations[conversation_id].append({"role": role, "content": content})

    if redis_client is not None:
        key = f"chat:{conversation_id}"
        message_data = json.dumps({"role": role, "content": content})
        try:
            redis_client.rpush(key, message_data)
            redis_client.expire(key, settings.redis_ttl)
        except redis.RedisError as exc:
            logger.warning(
                f"Redis connection failed when appending message for {conversation_id}: {exc}."
            )
