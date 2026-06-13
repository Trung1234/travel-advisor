import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest
import redis

from backend.main import app
import backend.memory


@pytest.fixture
def mock_redis_ok():
    """Mocks redis_client with fully working operations using a local dict for storage."""
    redis_store = {}
    mock_client = MagicMock()

    def mock_lrange(key, start, end):
        messages = redis_store.get(key, [])
        if end == -1:
            return messages[start:]
        return messages[start:end+1]

    def mock_rpush(key, val):
        if key not in redis_store:
            redis_store[key] = []
        redis_store[key].append(val)
        return len(redis_store[key])

    mock_client.lrange.side_effect = mock_lrange
    mock_client.rpush.side_effect = mock_rpush

    with patch("backend.memory.redis_client", mock_client):
        yield mock_client


@pytest.fixture
def mock_redis_fail():
    """Mocks redis_client raising RedisError for all operations."""
    mock_client = MagicMock()
    mock_client.lrange.side_effect = redis.RedisError("Connection timed out")
    mock_client.rpush.side_effect = redis.RedisError("Connection timed out")

    with patch("backend.memory.redis_client", mock_client):
        yield mock_client


def test_chat_contract(monkeypatch, mock_redis_ok):
    def fake_get_reply(message: str, history: list[dict[str, str]]) -> str:
        return f"Mocked reply for: {message}"

    monkeypatch.setattr("backend.main.get_reply", fake_get_reply)

    client = TestClient(app)
    response = client.post("/api/v1/chat", json={"message": "Plan a trip to Spain"})

    assert response.status_code == 200
    payload = response.json()
    assert "reply" in payload
    assert "conversation_id" in payload
    assert payload["reply"].startswith("Mocked reply for:")


def test_chat_redis_persistence(monkeypatch, mock_redis_ok):
    def fake_get_reply(message: str, history: list[dict[str, str]]) -> str:
        return f"Response to: {message}"

    monkeypatch.setattr("backend.main.get_reply", fake_get_reply)

    client = TestClient(app)
    resp = client.post("/api/v1/chat", json={"message": "Hello, I am Trung"})
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    history = backend.memory.get_history(conv_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello, I am Trung"


def test_chat_redis_fallback(monkeypatch, mock_redis_fail):
    def fake_get_reply(message: str, history: list[dict[str, str]]) -> str:
        return f"Response to: {message}"

    monkeypatch.setattr("backend.main.get_reply", fake_get_reply)

    client = TestClient(app)
    resp = client.post("/api/v1/chat", json={"message": "Hello, this is fallback test"})
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    history = backend.memory.get_history(conv_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello, this is fallback test"
