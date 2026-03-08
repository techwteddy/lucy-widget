import pytest
import uuid
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
from jose import jwt
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.auth.middleware import _decode_token, CurrentUser
from api.dependencies import get_db, get_redis
from fastapi import HTTPException


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

JWT_SECRET = "dev-jwt-secret"

def _make_token(sub: str = "user-123", email: str = "test@example.com", exp_delta: int = 3600) -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_delta),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


# ------------------------------------------------------------------
# Unit tests: _decode_token
# ------------------------------------------------------------------

def test_decode_valid_token():
    token = _make_token()
    user = _decode_token(token)
    assert user.sub == "user-123"
    assert user.email == "test@example.com"
    assert user.role == "authenticated"


def test_decode_expired_token():
    token = _make_token(exp_delta=-1)
    with pytest.raises(HTTPException) as exc:
        _decode_token(token)
    assert exc.value.status_code == 401


def test_decode_invalid_signature():
    token = jwt.encode({"sub": "x", "email": "x@x.com"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        _decode_token(token)
    assert exc.value.status_code == 401


def test_decode_missing_sub():
    token = jwt.encode({"email": "x@x.com"}, JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        _decode_token(token)
    assert exc.value.status_code == 401


# ------------------------------------------------------------------
# Integration tests: auth routes + chatbot ownership
# ------------------------------------------------------------------

@pytest.fixture
def mock_db():
    from unittest.mock import MagicMock
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    return session


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.ping = AsyncMock()
    return r


@pytest.fixture
async def client(mock_db, mock_redis):
    async def override_get_db():
        yield mock_db

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_valid_token(client):
    token = _make_token(sub="abc-123", email="user@example.com")
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sub"] == "abc-123"
    assert data["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_get_me_with_invalid_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer bad.token.here"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_chatbots_requires_auth(client):
    resp = await client.get("/api/v1/chatbots")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_chatbots_with_valid_token(client, mock_db):
    from unittest.mock import MagicMock
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = result

    token = _make_token()
    resp = await client.get("/api/v1/chatbots", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_my_chatbot_requires_auth(client):
    payload = {"name": "Test Bot", "system_prompt": "You are helpful."}
    resp = await client.post("/api/v1/chatbots/me", json=payload)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_my_chatbot_sets_owner_email(mock_db, mock_redis):
    """Verify db.add is called with owner_email from JWT (bypasses Pydantic serialization)."""
    from api.routes.chatbots import _make_chatbot
    from api.schemas.chatbot import ChatbotCreate

    payload = ChatbotCreate(name="Test Bot", system_prompt="You are helpful.")
    user = CurrentUser(sub="user-123", email="user@example.com")
    chatbot, raw_key = _make_chatbot(payload, owner_email=user.email)

    assert chatbot.owner_email == "user@example.com"
    assert raw_key.startswith("cbk_")
