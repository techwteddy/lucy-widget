import pytest
import uuid
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from jose import jwt

JWT_SECRET = "dev-jwt-secret"


def _make_token(sub: str = "user-123", email: str = "owner@example.com", exp_delta: int = 3600) -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_delta),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


SAMPLE_CHATBOT = {
    "name": "Test Bot",
    "system_prompt": "You are a helpful assistant.",
    "welcome_message": "Hello!",
    "primary_color": "#3B82F6",
    "position": "bottom-right",
    "title": "Test Chat",
    "owner_email": "test@example.com",
}


@pytest.mark.asyncio
async def test_create_chatbot_requires_admin_key(client):
    """Without X-Admin-Key header, should get 422."""
    response = await client.post("/api/v1/chatbots", json=SAMPLE_CHATBOT)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_chatbot_with_valid_admin_key(client, mock_db, admin_headers):
    """With valid admin key and mock DB, chatbot creation should work."""
    fake_id = uuid.uuid4()

    # The refresh call will populate chatbot attributes
    async def fake_refresh(obj):
        obj.id = fake_id
        obj.name = SAMPLE_CHATBOT["name"]
        obj.system_prompt = SAMPLE_CHATBOT["system_prompt"]
        obj.welcome_message = SAMPLE_CHATBOT["welcome_message"]
        obj.primary_color = SAMPLE_CHATBOT["primary_color"]
        obj.position = SAMPLE_CHATBOT["position"]
        obj.title = SAMPLE_CHATBOT["title"]
        obj.owner_email = SAMPLE_CHATBOT["owner_email"]
        obj.is_active = True

    mock_db.refresh.side_effect = fake_refresh

    response = await client.post("/api/v1/chatbots", json=SAMPLE_CHATBOT, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    # API key should be in response (only on creation)
    assert "api_key" in data
    assert data["api_key"].startswith("cbk_")
    assert data["name"] == SAMPLE_CHATBOT["name"]


@pytest.mark.asyncio
async def test_create_chatbot_returns_api_key_once(client, mock_db, admin_headers):
    """API key is returned on creation and starts with cbk_."""
    fake_id = uuid.uuid4()

    async def fake_refresh(obj):
        obj.id = fake_id
        obj.name = "Bot"
        obj.system_prompt = "Help."
        obj.welcome_message = "Hi!"
        obj.primary_color = "#000000"
        obj.position = "bottom-right"
        obj.title = "Chat"
        obj.owner_email = None
        obj.is_active = True

    mock_db.refresh.side_effect = fake_refresh

    response = await client.post(
        "/api/v1/chatbots",
        json={"name": "Bot", "system_prompt": "Help."},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["api_key"].startswith("cbk_")


@pytest.mark.asyncio
async def test_widget_config_public_endpoint(client, mock_db):
    """Widget config endpoint should not require auth and returns 404 when not found."""
    chatbot_id = str(uuid.uuid4())
    # Default mock_db returns None for scalar_one_or_none → 404
    response = await client.get(f"/api/v1/chatbots/{chatbot_id}/widget-config")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_widget_config_returns_config_when_found(client, mock_db):
    """Widget config returns display fields when chatbot exists."""
    chatbot_id = uuid.uuid4()

    fake_chatbot = MagicMock()
    fake_chatbot.id = chatbot_id
    fake_chatbot.name = "My Bot"
    fake_chatbot.welcome_message = "Hello!"
    fake_chatbot.primary_color = "#3B82F6"
    fake_chatbot.position = "bottom-right"
    fake_chatbot.title = "Chat"
    fake_chatbot.is_active = True

    mock_db.execute.return_value.scalar_one_or_none.return_value = fake_chatbot

    response = await client.get(f"/api/v1/chatbots/{chatbot_id}/widget-config")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Bot"
    assert "api_key_hash" not in data  # Sensitive field must not be exposed
    assert "welcome_message" in data
    assert "primary_color" in data


@pytest.mark.asyncio
async def test_get_chatbot_requires_admin_key(client, chatbot_id):
    """GET /chatbots/{id} requires X-Admin-Key header."""
    response = await client.get(f"/api/v1/chatbots/{chatbot_id}")
    assert response.status_code == 422  # Missing header


@pytest.mark.asyncio
async def test_chatbot_create_payload_validation(client, admin_headers):
    """Missing required system_prompt should return 422."""
    response = await client.post("/api/v1/chatbots", json={"name": "only name"}, headers=admin_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chatbot_update_no_fields_returns_400(client, admin_headers, chatbot_id):
    """Empty update payload should return 400."""
    response = await client.put(
        f"/api/v1/chatbots/{chatbot_id}",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 400


# ------------------------------------------------------------------
# W1: JWT owner can PUT/DELETE their own chatbot
# ------------------------------------------------------------------


def _fake_chatbot(chatbot_id: uuid.UUID, owner_email: str = "owner@example.com") -> MagicMock:
    bot = MagicMock()
    bot.id = chatbot_id
    bot.name = "My Bot"
    bot.system_prompt = "Help."
    bot.welcome_message = "Hi!"
    bot.primary_color = "#3B82F6"
    bot.position = "bottom-right"
    bot.title = "Chat"
    bot.owner_email = owner_email
    bot.is_active = True
    return bot


@pytest.mark.asyncio
async def test_jwt_owner_can_update_chatbot(client, mock_db):
    """JWT owner should be able to PUT their own chatbot."""
    cid = uuid.uuid4()
    bot = _fake_chatbot(cid)

    # get_admin_or_owner does a select to verify ownership — return the chatbot
    # Then update_chatbot does two more selects (update + re-fetch)
    mock_db.execute.return_value.scalar_one_or_none.return_value = bot
    mock_db.execute.return_value.scalar_one.return_value = bot

    token = _make_token(email="owner@example.com")
    response = await client.put(
        f"/api/v1/chatbots/{cid}",
        json={"name": "Updated Bot"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_jwt_non_owner_cannot_update_chatbot(client, mock_db):
    """JWT user who is NOT the owner should get 403."""
    cid = uuid.uuid4()

    # Ownership check returns None (not owner)
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    token = _make_token(email="hacker@example.com")
    response = await client.put(
        f"/api/v1/chatbots/{cid}",
        json={"name": "Hacked Bot"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_jwt_owner_can_delete_chatbot(client, mock_db):
    """JWT owner should be able to DELETE (soft-delete) their own chatbot."""
    cid = uuid.uuid4()
    bot = _fake_chatbot(cid)
    mock_db.execute.return_value.scalar_one_or_none.return_value = bot

    token = _make_token(email="owner@example.com")
    response = await client.delete(
        f"/api/v1/chatbots/{cid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_jwt_non_owner_cannot_delete_chatbot(client, mock_db):
    """JWT user who is NOT the owner should get 403 on DELETE."""
    cid = uuid.uuid4()
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    token = _make_token(email="hacker@example.com")
    response = await client.delete(
        f"/api/v1/chatbots/{cid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_key_still_works_for_update(client, mock_db, admin_headers):
    """Admin key should still grant access to PUT."""
    cid = uuid.uuid4()
    bot = _fake_chatbot(cid)
    mock_db.execute.return_value.scalar_one.return_value = bot

    response = await client.put(
        f"/api/v1/chatbots/{cid}",
        json={"name": "Admin Updated"},
        headers=admin_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_key_still_works_for_delete(client, mock_db, admin_headers):
    """Admin key should still grant access to DELETE."""
    cid = uuid.uuid4()
    response = await client.delete(
        f"/api/v1/chatbots/{cid}",
        headers=admin_headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_no_auth_returns_401_for_update(client):
    """No auth header at all should return 401."""
    cid = uuid.uuid4()
    response = await client.put(
        f"/api/v1/chatbots/{cid}",
        json={"name": "No Auth"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_no_auth_returns_401_for_delete(client):
    """No auth header at all should return 401."""
    cid = uuid.uuid4()
    response = await client.delete(f"/api/v1/chatbots/{cid}")
    assert response.status_code == 401
