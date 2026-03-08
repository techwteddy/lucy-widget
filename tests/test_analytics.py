import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from jose import jwt
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.dependencies import get_db, get_redis


JWT_SECRET = "dev-jwt-secret"


def _make_token(email: str = "user@example.com") -> str:
    payload = {
        "sub": "user-123",
        "email": email,
        "role": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(seconds=3600),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture
def mock_db():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = 0
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
async def test_analytics_requires_auth(client):
    cid = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/chatbots/{cid}/analytics")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_analytics_returns_404_for_unknown_chatbot(client, mock_db):
    """Returns 404 when chatbot doesn't exist or isn't owned by user."""
    cid = str(uuid.uuid4())
    token = _make_token()
    resp = await client.get(
        f"/api/v1/chatbots/{cid}/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analytics_returns_stats(client, mock_db):
    """Returns analytics stats for owned chatbot."""
    from api.models.chatbot import Chatbot as ChatbotModel

    cid = uuid.uuid4()
    chatbot_mock = MagicMock(spec=ChatbotModel)
    chatbot_mock.id = cid
    chatbot_mock.owner_email = "user@example.com"
    chatbot_mock.is_active = True

    call_count = 0

    def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            # First call: assert_owner returns chatbot
            result.scalar_one_or_none.return_value = chatbot_mock
        elif call_count == 1:
            # Second call: conversation count
            result.scalar_one.return_value = 5
        else:
            # Third call: message count
            result.scalar_one.return_value = 12
        call_count += 1
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    token = _make_token()
    resp = await client.get(
        f"/api/v1/chatbots/{cid}/analytics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_conversations" in data
    assert "total_messages" in data
    assert "avg_messages_per_conversation" in data


@pytest.mark.asyncio
async def test_conversations_requires_auth(client):
    cid = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/chatbots/{cid}/conversations")
    assert resp.status_code == 401
