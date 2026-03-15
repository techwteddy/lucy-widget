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


SAMPLE_CHATBOT = {
    "name": "Test Bot",
    "system_prompt": "You are a helpful assistant.",
}


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.ping = AsyncMock()
    r.get = AsyncMock(return_value=None)  # default: free plan
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    return r


@pytest.fixture
def mock_db():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = MagicMock()
    result.scalar.return_value = 0
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    return session


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
async def test_free_plan_can_create_first_chatbot(client, mock_db, mock_redis):
    """Free plan user with 0 chatbots can create one."""
    fake_id = uuid.uuid4()

    # Redis returns None → free plan
    mock_redis.get = AsyncMock(return_value=None)

    call_count = 0

    async def fake_execute(*args, **kwargs):
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            # Quota check: count of active chatbots = 0
            result.scalar.return_value = 0
        call_count += 1
        return result

    mock_db.execute = AsyncMock(side_effect=fake_execute)

    async def fake_refresh(obj):
        obj.id = fake_id
        obj.name = SAMPLE_CHATBOT["name"]
        obj.system_prompt = SAMPLE_CHATBOT["system_prompt"]
        obj.welcome_message = "Hi! How can I help you today?"
        obj.primary_color = "#3B82F6"
        obj.position = "bottom-right"
        obj.title = "Chat with us"
        obj.owner_email = "user@example.com"
        obj.is_active = True

    mock_db.refresh.side_effect = fake_refresh

    token = _make_token()
    resp = await client.post(
        "/api/v1/chatbots/me",
        json=SAMPLE_CHATBOT,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["api_key"].startswith("cbk_")


@pytest.mark.asyncio
async def test_free_plan_blocked_at_limit(client, mock_db, mock_redis):
    """Free plan user with 1 chatbot gets HTTP 403 on create."""
    # Redis returns None → free plan
    mock_redis.get = AsyncMock(return_value=None)

    async def fake_execute(*args, **kwargs):
        result = MagicMock()
        # Quota check: count of active chatbots = 1 (at limit for free)
        result.scalar.return_value = 1
        return result

    mock_db.execute = AsyncMock(side_effect=fake_execute)

    token = _make_token()
    resp = await client.post(
        "/api/v1/chatbots/me",
        json=SAMPLE_CHATBOT,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "Plan limit reached" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_business_plan_unlimited_chatbots(client, mock_db, mock_redis):
    """Business plan user with 10 chatbots can still create (unlimited)."""
    fake_id = uuid.uuid4()

    # Redis returns "business" plan
    mock_redis.get = AsyncMock(return_value="business")

    async def fake_refresh(obj):
        obj.id = fake_id
        obj.name = SAMPLE_CHATBOT["name"]
        obj.system_prompt = SAMPLE_CHATBOT["system_prompt"]
        obj.welcome_message = "Hi! How can I help you today?"
        obj.primary_color = "#3B82F6"
        obj.position = "bottom-right"
        obj.title = "Chat with us"
        obj.owner_email = "user@example.com"
        obj.is_active = True

    mock_db.refresh.side_effect = fake_refresh

    token = _make_token()
    resp = await client.post(
        "/api/v1/chatbots/me",
        json=SAMPLE_CHATBOT,
        headers={"Authorization": f"Bearer {token}"},
    )
    # Business plan has unlimited chatbots — no quota check query needed
    assert resp.status_code == 201
