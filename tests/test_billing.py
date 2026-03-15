import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from jose import jwt
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.dependencies import get_db, get_redis
from api.billing.quota import (
    get_message_count,
    increment_message_count,
    check_quota,
    get_plan_limit,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

JWT_SECRET = "dev-jwt-secret"


def _make_token(sub: str = "user-123", email: str = "test@example.com") -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(seconds=3600),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def mock_db():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    return session


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.ping = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
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


# ------------------------------------------------------------------
# Unit: plan limits
# ------------------------------------------------------------------

def test_get_plan_limit_free():
    assert get_plan_limit("free") == 100


def test_get_plan_limit_pro():
    assert get_plan_limit("pro") == 5000


def test_get_plan_limit_business():
    assert get_plan_limit("business") == 50000


# ------------------------------------------------------------------
# Unit: quota checks
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_quota_under_limit():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="50")
    result = await check_quota(redis, "user@example.com", "free")
    assert result is True


@pytest.mark.asyncio
async def test_check_quota_at_limit():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="100")
    result = await check_quota(redis, "user@example.com", "free")
    assert result is False


@pytest.mark.asyncio
async def test_increment_message_count():
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    count = await increment_message_count(redis, "user@example.com")
    assert count == 1
    redis.incr.assert_called_once()
    redis.expire.assert_called_once()


# ------------------------------------------------------------------
# Integration: billing routes
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_checkout_requires_auth(client):
    resp = await client.post(
        "/billing/checkout",
        json={"plan": "pro", "success_url": "http://ok", "cancel_url": "http://cancel"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(client):
    resp = await client.post(
        "/billing/webhook",
        content=b'{"type":"test"}',
        headers={
            "stripe-signature": "t=123,v1=bad",
            "content-type": "application/json",
        },
    )
    assert resp.status_code == 400


# ------------------------------------------------------------------
# Unit: webhook subscription handlers
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_subscription_created_sets_pro():
    from api.billing.routes import _handle_subscription_upsert

    redis = AsyncMock()
    subscription = {
        "id": "sub_123",
        "customer": "cus_abc",
        "status": "active",
        "items": {"data": [{"price": {"id": "price_pro_test"}}]},
    }
    with patch("api.billing.routes.PLAN_TIER_MAP", {"price_pro_test": "pro"}):
        await _handle_subscription_upsert(subscription, redis)

    redis.hset.assert_called_once_with(
        "subscription:cus_abc",
        mapping={
            "plan": "pro",
            "status": "active",
            "subscription_id": "sub_123",
            "price_id": "price_pro_test",
        },
    )
    redis.expire.assert_called_once_with("subscription:cus_abc", 86400 * 30)


@pytest.mark.asyncio
async def test_handle_subscription_upsert_ignores_inactive():
    from api.billing.routes import _handle_subscription_upsert

    redis = AsyncMock()
    subscription = {
        "id": "sub_456",
        "customer": "cus_def",
        "status": "past_due",
        "items": {"data": [{"price": {"id": "price_pro_test"}}]},
    }
    await _handle_subscription_upsert(subscription, redis)
    redis.hset.assert_not_called()


@pytest.mark.asyncio
async def test_handle_subscription_deleted_resets_to_free():
    from api.billing.routes import _handle_subscription_deleted

    redis = AsyncMock()
    subscription = {
        "id": "sub_789",
        "customer": "cus_ghi",
    }
    await _handle_subscription_deleted(subscription, redis)
    redis.hset.assert_called_once_with(
        "subscription:cus_ghi",
        mapping={
            "plan": "free",
            "status": "canceled",
        },
    )


@pytest.mark.asyncio
async def test_handle_subscription_trialing_sets_plan():
    from api.billing.routes import _handle_subscription_upsert

    redis = AsyncMock()
    subscription = {
        "id": "sub_trial",
        "customer": "cus_trial",
        "status": "trialing",
        "items": {"data": [{"price": {"id": "price_biz_test"}}]},
    }
    with patch("api.billing.routes.PLAN_TIER_MAP", {"price_biz_test": "business"}):
        await _handle_subscription_upsert(subscription, redis)

    redis.hset.assert_called_once()
    call_mapping = redis.hset.call_args[1]["mapping"]
    assert call_mapping["plan"] == "business"
    assert call_mapping["status"] == "trialing"


# ------------------------------------------------------------------
# Integration: GET /billing/status
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_billing_status_requires_auth(client):
    resp = await client.get("/billing/status")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_billing_status_returns_plan_info(client, mock_redis):
    token = _make_token(email="owner@example.com")

    async def fake_redis_get(key):
        if key.startswith("plan:"):
            return "pro"
        if key.startswith("quota:"):
            return "42"
        return None

    mock_redis.get = AsyncMock(side_effect=fake_redis_get)

    resp = await client.get(
        "/billing/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["messages_used"] == 42
    assert data["messages_limit"] == 5000


@pytest.mark.asyncio
async def test_billing_status_defaults_to_free(client, mock_redis):
    token = _make_token(email="new@example.com")

    mock_redis.get = AsyncMock(return_value=None)

    resp = await client.get(
        "/billing/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "free"
    assert data["messages_used"] == 0
    assert data["messages_limit"] == 100


# ------------------------------------------------------------------
# Unit: rate limiting
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_allows_under_limit():
    from api.routes.chat import _check_rate_limit

    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=5)
    redis.expire = AsyncMock()

    result = await _check_rate_limit(redis, "session-abc")
    assert result is None


@pytest.mark.asyncio
async def test_rate_limit_blocks_over_limit():
    from api.routes.chat import _check_rate_limit

    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=11)
    redis.ttl = AsyncMock(return_value=45)

    result = await _check_rate_limit(redis, "session-abc")
    assert result == 45


@pytest.mark.asyncio
async def test_rate_limit_sets_expire_on_first_call():
    from api.routes.chat import _check_rate_limit

    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()

    result = await _check_rate_limit(redis, "session-abc")
    assert result is None
    redis.expire.assert_called_once_with("rate:session-abc", 60)
