import pytest
import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
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


def _fake_chatbot(chatbot_id: uuid.UUID, owner_email: str = "owner@example.com") -> MagicMock:
    bot = MagicMock()
    bot.id = chatbot_id
    bot.name = "My Bot"
    bot.owner_email = owner_email
    bot.is_active = True
    return bot


# ------------------------------------------------------------------
# Existing tests (updated for get_admin_or_owner)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_document_requires_auth(client, chatbot_id):
    """Without any auth header, should get 401."""
    content = b"Test document content"
    response = await client.post(
        f"/api/v1/chatbots/{chatbot_id}/documents",
        files={"file": ("test.txt", BytesIO(content), "text/plain")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client, admin_headers, chatbot_id):
    response = await client.post(
        f"/api/v1/chatbots/{chatbot_id}/documents",
        files={"file": ("test.doc", BytesIO(b"content"), "application/msword")},
        headers=admin_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_file_too_large(client, admin_headers, chatbot_id):
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB
    response = await client.post(
        f"/api/v1/chatbots/{chatbot_id}/documents",
        files={"file": ("big.txt", BytesIO(large_content), "text/plain")},
        headers=admin_headers,
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_list_documents_requires_auth(client, chatbot_id):
    """Without any auth header, should get 401."""
    response = await client.get(f"/api/v1/chatbots/{chatbot_id}/documents")
    assert response.status_code == 401


def test_extract_text_from_txt():
    """Test text extraction from plain text files."""
    from api.routes.documents import _extract_text
    content = b"Hello, world!\nSecond line."
    result = _extract_text(content, "test.txt")
    assert "Hello" in result
    assert "Second line" in result


def test_extract_text_preserves_content():
    """Text extraction should preserve all content."""
    from api.routes.documents import _extract_text
    text = "Important content here. More content. Final sentence."
    result = _extract_text(text.encode(), "document.txt")
    assert result == text


# ------------------------------------------------------------------
# W1: JWT owner can access document endpoints
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jwt_owner_can_list_documents(client, mock_db):
    """JWT owner should be able to list documents for their chatbot."""
    cid = uuid.uuid4()
    bot = _fake_chatbot(cid)
    mock_db.execute.return_value.scalar_one_or_none.return_value = bot
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    token = _make_token(email="owner@example.com")
    response = await client.get(
        f"/api/v1/chatbots/{cid}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_jwt_non_owner_cannot_list_documents(client, mock_db):
    """JWT user who is NOT the owner should get 403."""
    cid = uuid.uuid4()
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    token = _make_token(email="hacker@example.com")
    response = await client.get(
        f"/api/v1/chatbots/{cid}/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_jwt_owner_can_delete_document(client, mock_db):
    """JWT owner should be able to delete a document."""
    cid = uuid.uuid4()
    doc_id = uuid.uuid4()
    bot = _fake_chatbot(cid)
    mock_db.execute.return_value.scalar_one_or_none.return_value = bot

    token = _make_token(email="owner@example.com")
    response = await client.delete(
        f"/api/v1/chatbots/{cid}/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_jwt_non_owner_cannot_delete_document(client, mock_db):
    """JWT user who is NOT the owner should get 403 on DELETE."""
    cid = uuid.uuid4()
    doc_id = uuid.uuid4()
    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    token = _make_token(email="hacker@example.com")
    response = await client.delete(
        f"/api/v1/chatbots/{cid}/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_key_still_works_for_list_documents(client, mock_db, admin_headers):
    """Admin key should still grant access to list documents."""
    cid = uuid.uuid4()
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    response = await client.get(
        f"/api/v1/chatbots/{cid}/documents",
        headers=admin_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_key_still_works_for_delete_document(client, mock_db, admin_headers):
    """Admin key should still grant access to delete documents."""
    cid = uuid.uuid4()
    doc_id = uuid.uuid4()

    response = await client.delete(
        f"/api/v1/chatbots/{cid}/documents/{doc_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_no_auth_returns_401_for_delete_document(client):
    """No auth header at all should return 401."""
    cid = uuid.uuid4()
    doc_id = uuid.uuid4()
    response = await client.delete(f"/api/v1/chatbots/{cid}/documents/{doc_id}")
    assert response.status_code == 401
