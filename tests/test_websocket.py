"""WebSocket chat endpoint tests."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from fastapi import FastAPI, WebSocket, Depends
from api.routes.chat import router
from api.dependencies import get_db, get_redis


@pytest.fixture
def bot_id():
    return str(uuid.uuid4())


@pytest.fixture
def mock_chatbot(bot_id):
    """Create a mock Chatbot ORM object."""
    bot = MagicMock()
    bot.id = uuid.UUID(bot_id)
    bot.is_active = True
    bot.api_key_hash = None
    bot.owner_email = ""
    return bot


@pytest.fixture
def mock_db_with_bot(mock_db, mock_chatbot):
    """DB session that returns our mock chatbot on SELECT."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_chatbot
    mock_db.execute.return_value = result
    return mock_db


@pytest.fixture
def ws_app(mock_db_with_bot, mock_redis):
    """Minimal FastAPI app with just the chat router for WS testing."""
    test_app = FastAPI()

    async def override_get_db():
        yield mock_db_with_bot

    async def override_get_redis():
        return mock_redis

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_redis] = override_get_redis
    test_app.include_router(router)

    return test_app


def test_ws_connect_and_ping(ws_app, bot_id):
    """WebSocket connects and responds to ping with pong."""
    client = TestClient(ws_app)
    with client.websocket_connect(f"/ws/chat/{bot_id}?session_id=sess1") as ws:
        ws.send_text("ping")
        data = ws.receive_json()
        assert data == {"type": "pong"}


def test_ws_stream_response(ws_app, bot_id):
    """WebSocket sends start/token/end sequence for a message."""
    tokens = ["Hello", " ", "world", "!"]

    async def mock_stream(*args, **kwargs):
        for t in tokens:
            yield t

    with patch("api.routes.chat.stream_response", side_effect=mock_stream):
        client = TestClient(ws_app)
        with client.websocket_connect(f"/ws/chat/{bot_id}?session_id=sess2") as ws:
            ws.send_text("Hi there")

            msg = ws.receive_json()
            assert msg["type"] == "start"

            received_tokens = []
            while True:
                msg = ws.receive_json()
                if msg["type"] == "end":
                    break
                assert msg["type"] == "token"
                received_tokens.append(msg["content"])

            assert received_tokens == tokens


def test_ws_invalid_chatbot_closes_4004(ws_app, mock_redis):
    """WebSocket closes with 4004 for non-existent chatbot."""
    # Override DB to return no chatbot
    mock_db_empty = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_empty.execute.return_value = result

    async def override_get_db():
        yield mock_db_empty

    ws_app.dependency_overrides[get_db] = override_get_db

    fake_id = str(uuid.uuid4())
    client = TestClient(ws_app)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/chat/{fake_id}?session_id=s") as ws:
            ws.receive_json()


def test_ws_rate_limit(ws_app, bot_id, mock_redis):
    """WebSocket sends error and closes when rate limited."""
    mock_redis.incr = AsyncMock(return_value=11)
    mock_redis.ttl = AsyncMock(return_value=45)

    client = TestClient(ws_app)
    with client.websocket_connect(f"/ws/chat/{bot_id}?session_id=sess3") as ws:
        ws.send_text("hello")
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "Rate limit" in msg["content"]


def test_ws_stream_error_sends_error_message(ws_app, bot_id):
    """When stream_response raises, WebSocket sends error message."""

    async def mock_stream_error(*args, **kwargs):
        raise RuntimeError("LLM down")
        yield  # noqa: unreachable — makes it a generator

    with patch("api.routes.chat.stream_response", side_effect=mock_stream_error):
        client = TestClient(ws_app)
        with client.websocket_connect(f"/ws/chat/{bot_id}?session_id=sess4") as ws:
            ws.send_text("test")
            msg = ws.receive_json()
            assert msg["type"] == "start"
            msg = ws.receive_json()
            assert msg["type"] == "error"


def test_ws_multiple_messages(ws_app, bot_id):
    """WebSocket handles multiple consecutive messages in one session."""
    call_count = 0

    async def mock_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        yield f"Response {call_count}"

    with patch("api.routes.chat.stream_response", side_effect=mock_stream):
        client = TestClient(ws_app)
        with client.websocket_connect(f"/ws/chat/{bot_id}?session_id=sess5") as ws:
            # First message
            ws.send_text("msg1")
            assert ws.receive_json()["type"] == "start"
            token1 = ws.receive_json()
            assert token1["type"] == "token"
            assert token1["content"] == "Response 1"
            assert ws.receive_json()["type"] == "end"

            # Second message in same connection
            ws.send_text("msg2")
            assert ws.receive_json()["type"] == "start"
            token2 = ws.receive_json()
            assert token2["type"] == "token"
            assert token2["content"] == "Response 2"
            assert ws.receive_json()["type"] == "end"
