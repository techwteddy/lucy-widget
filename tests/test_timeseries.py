import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
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
    result.all.return_value = []
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
async def test_timeseries_returns_30_days(client, mock_db):
    """Returns 30 days of data (mostly zeros) for owned chatbot."""
    cid = uuid.uuid4()

    chatbot_mock = MagicMock()
    chatbot_mock.id = cid
    chatbot_mock.owner_email = "user@example.com"
    chatbot_mock.is_active = True

    call_count = 0

    async def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            # _assert_owner returns chatbot
            result.scalar_one_or_none.return_value = chatbot_mock
        else:
            # timeseries query: no rows
            result.all.return_value = []
        call_count += 1
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    token = _make_token()
    resp = await client.get(
        f"/api/v1/chatbots/{cid}/analytics/timeseries?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chatbot_id"] == str(cid)
    assert data["days"] == 30
    assert len(data["data"]) == 30
    # All zeros since no messages
    assert all(p["message_count"] == 0 for p in data["data"])


@pytest.mark.asyncio
async def test_timeseries_counts_correct(client, mock_db):
    """Counts are correct for known inserted messages."""
    cid = uuid.uuid4()

    chatbot_mock = MagicMock()
    chatbot_mock.id = cid
    chatbot_mock.owner_email = "user@example.com"
    chatbot_mock.is_active = True

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    call_count = 0

    async def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            result.scalar_one_or_none.return_value = chatbot_mock
        else:
            # Return 2 days with messages
            result.all.return_value = [
                (today, 5),
                (today - timedelta(days=1), 3),
            ]
        call_count += 1
        return result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    token = _make_token()
    resp = await client.get(
        f"/api/v1/chatbots/{cid}/analytics/timeseries?days=7",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 7

    # Check today's entry has count 5
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    today_point = next((p for p in data["data"] if p["date"] == today_str), None)
    yesterday_point = next((p for p in data["data"] if p["date"] == yesterday_str), None)

    assert today_point is not None
    assert today_point["message_count"] == 5
    assert yesterday_point is not None
    assert yesterday_point["message_count"] == 3


@pytest.mark.asyncio
async def test_timeseries_requires_ownership(client, mock_db):
    """Returns 404 for chatbot owned by different user."""
    cid = uuid.uuid4()

    # _assert_owner returns None (not owner)
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    token = _make_token(email="hacker@example.com")
    resp = await client.get(
        f"/api/v1/chatbots/{cid}/analytics/timeseries?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    # _assert_owner raises 404
    assert resp.status_code == 404
