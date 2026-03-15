"""Tests for DEMO_MODE functionality."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def _demo_mode_on():
    """Enable demo_mode on the real settings object."""
    from api.config import settings
    original = settings.demo_mode
    settings.demo_mode = True
    yield
    settings.demo_mode = original


@pytest.fixture
async def demo_client(mock_db, mock_redis, _demo_mode_on):
    """Test client with DEMO_MODE=true and mocked DB/Redis."""
    from httpx import AsyncClient, ASGITransport
    from api.main import app
    from api.dependencies import get_db, get_redis

    async def override_get_db():
        yield mock_db

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# --- Demo login ---

@pytest.mark.asyncio
async def test_demo_login_returns_token(demo_client):
    resp = await demo_client.post("/auth/demo-login")
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] == "demo-token"
    assert data["email"] == "demo@example.com"
    assert data["user_id"] == "demo-user-id"


@pytest.mark.asyncio
async def test_demo_login_404_when_disabled(client):
    resp = await client.post("/auth/demo-login")
    assert resp.status_code == 404


# --- Auth bypass ---

@pytest.mark.asyncio
async def test_auth_me_works_without_token_in_demo_mode(demo_client):
    resp = await demo_client.get("/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "demo@example.com"
    assert data["sub"] == "demo-user-id"


@pytest.mark.asyncio
async def test_auth_me_works_with_demo_token(demo_client):
    resp = await demo_client.get("/auth/me", headers={"Authorization": "Bearer demo-token"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "demo@example.com"


# --- Billing bypass ---

@pytest.mark.asyncio
async def test_demo_checkout_returns_mock_url(demo_client):
    resp = await demo_client.post("/billing/checkout", json={
        "plan": "pro",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
    })
    assert resp.status_code == 200
    assert resp.json()["checkout_url"] == "https://example.com/demo-checkout"


@pytest.mark.asyncio
async def test_demo_portal_returns_mock_url(demo_client):
    resp = await demo_client.post("/billing/portal", json={"return_url": "/dashboard"})
    assert resp.status_code == 200
    assert resp.json()["portal_url"] == "https://example.com/demo-portal"


# --- Chatbot endpoints work in demo mode ---

@pytest.mark.asyncio
async def test_list_chatbots_works_in_demo_mode(demo_client, mock_db):
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = result_mock

    resp = await demo_client.get("/api/v1/chatbots")
    assert resp.status_code == 200
    assert resp.json() == []


# --- Seed function ---

@pytest.mark.asyncio
async def test_seed_demo_data_creates_chatbot():
    """Test that seed_demo_data creates a chatbot when none exists."""
    from api.seed import seed_demo_data

    mock_session = AsyncMock()
    # Make session.add synchronous (it's not awaited in the code)
    mock_session.add = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result_mock

    with patch("api.seed.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await seed_demo_data()

    # Should have added chatbot + conversation + 2 messages = 4 add calls
    assert mock_session.add.call_count == 4
    assert mock_session.commit.call_count == 1


@pytest.mark.asyncio
async def test_seed_demo_data_skips_if_exists():
    """Test that seed_demo_data is idempotent."""
    from api.seed import seed_demo_data

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = MagicMock(id="existing-id")
    mock_session.execute.return_value = result_mock

    with patch("api.seed.AsyncSessionLocal") as mock_factory:
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await seed_demo_data()

    assert mock_session.add.call_count == 0
    assert mock_session.commit.call_count == 0
