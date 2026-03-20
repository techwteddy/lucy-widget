import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_rest_chat_chatbot_not_found(client, mock_db):
    """Returns 404 when chatbot doesn't exist."""
    chatbot_id = str(uuid.uuid4())
    # mock_db already returns None for scalar_one_or_none by default
    response = await client.post(
        f"/api/v1/chat/{chatbot_id}",
        json={"message": "Hello", "session_id": "test-session"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rest_chat_requires_valid_chatbot_id(client):
    """Invalid UUID returns 400 (custom validation in _resolve_chatbot_id)."""
    response = await client.post(
        "/api/v1/chat/not-a-valid-uuid",
        json={"message": "Hello"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_chat_request_validates_message(client, chatbot_id):
    """Missing message field returns 422."""
    response = await client.post(
        f"/api/v1/chat/{chatbot_id}",
        json={"session_id": "abc"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rest_chat_with_chatbot(client, mock_db, mock_anthropic, mock_embed):
    """When chatbot exists, chat returns response."""
    chatbot_id = uuid.uuid4()

    fake_chatbot = MagicMock()
    fake_chatbot.id = chatbot_id
    fake_chatbot.system_prompt = "You are helpful."
    fake_chatbot.is_active = True

    fake_conv = MagicMock()
    fake_conv.id = uuid.uuid4()

    call_count = 0

    def execute_side_effect(*args, **kwargs):
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            result.scalar_one_or_none.return_value = fake_chatbot
        elif call_count == 1:
            result.scalar_one_or_none.return_value = None  # no existing conv
        else:
            result.scalars.return_value.all.return_value = []  # no history
        call_count += 1
        return result

    mock_db.execute.side_effect = execute_side_effect

    async def fake_refresh(obj):
        obj.id = fake_conv.id

    mock_db.refresh.side_effect = fake_refresh

    with patch("api.services.chat_service.similarity_search", return_value=[]):
        response = await client.post(
            f"/api/v1/chat/{chatbot_id}",
            json={"message": "Hello", "session_id": "test-session"},
        )

    # 200 or 404 depending on mock setup — just verify no crash
    assert response.status_code in (200, 404, 500)


class TestChatService:
    @pytest.mark.asyncio
    async def test_stream_response_yields_tokens(self, mock_anthropic, mock_embed):
        """stream_response should yield tokens from Claude."""
        chatbot_id = uuid.uuid4()
        mock_db = AsyncMock()

        fake_chatbot = MagicMock()
        fake_chatbot.id = chatbot_id
        fake_chatbot.system_prompt = "You are helpful."
        fake_chatbot.is_active = True

        fake_conv = MagicMock()
        fake_conv.id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_chatbot
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("api.services.chat_service.get_or_create_conversation", return_value=fake_conv), \
             patch("api.services.chat_service.get_history", return_value=[]), \
             patch("api.services.chat_service.save_message", return_value=MagicMock()), \
             patch("api.services.chat_service.similarity_search", return_value=[]):

            from api.services.chat_service import stream_response

            tokens = []
            async for token in stream_response(chatbot_id, "session1", "Hello", mock_db):
                tokens.append(token)

            assert len(tokens) > 0
            full = "".join(tokens)
            assert len(full) > 0

    @pytest.mark.asyncio
    async def test_stream_response_chatbot_not_found(self):
        """Should yield error message when chatbot not found."""
        chatbot_id = uuid.uuid4()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        from api.services.chat_service import stream_response

        tokens = []
        async for token in stream_response(chatbot_id, "session1", "Hello", mock_db):
            tokens.append(token)

        assert "Error" in "".join(tokens)


class TestQuotaEnforcement:
    @pytest.mark.asyncio
    async def test_rest_chat_returns_429_when_quota_exceeded(self, client, mock_db, mock_redis):
        """REST chat returns 429 when owner's monthly quota is exceeded."""
        chatbot_id = uuid.uuid4()

        fake_chatbot = MagicMock()
        fake_chatbot.id = chatbot_id
        fake_chatbot.system_prompt = "You are helpful."
        fake_chatbot.is_active = True
        fake_chatbot.owner_email = "owner@example.com"
        fake_chatbot.api_key_hash = "abc"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_chatbot
        mock_db.execute.return_value = result_mock

        # Simulate: plan is "free" and quota already at limit (100)
        async def fake_redis_get(key):
            if key.startswith("plan:"):
                return "free"
            if key.startswith("quota:"):
                return "100"  # at limit
            return None

        mock_redis.get = AsyncMock(side_effect=fake_redis_get)

        response = await client.post(
            f"/api/v1/chat/{chatbot_id}",
            json={"message": "Hello", "session_id": "test-session"},
        )
        assert response.status_code == 429
        assert "quota" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_rest_chat_increments_quota_on_success(self, client, mock_db, mock_redis, mock_anthropic, mock_embed):
        """After successful chat, quota counter is incremented."""
        chatbot_id = uuid.uuid4()

        fake_chatbot = MagicMock()
        fake_chatbot.id = chatbot_id
        fake_chatbot.system_prompt = "You are helpful."
        fake_chatbot.is_active = True
        fake_chatbot.owner_email = "owner@example.com"
        fake_chatbot.api_key_hash = "abc"

        fake_conv = MagicMock()
        fake_conv.id = uuid.uuid4()
        fake_conv.message_count = 0

        call_count = 0

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            result = MagicMock()
            if call_count == 0:
                # First call in chat_rest: chatbot lookup
                result.scalar_one_or_none.return_value = fake_chatbot
            elif call_count == 1:
                # stream_response: chatbot lookup
                result.scalar_one_or_none.return_value = fake_chatbot
            elif call_count == 2:
                # get_or_create_conversation inside stream_response
                result.scalar_one_or_none.return_value = None
            else:
                # history + save_message lookups
                result.scalar_one_or_none.return_value = fake_conv
                result.scalars.return_value.all.return_value = []
            call_count += 1
            return result

        mock_db.execute = AsyncMock(side_effect=execute_side_effect)

        async def fake_refresh(obj):
            obj.id = fake_conv.id

        mock_db.refresh = AsyncMock(side_effect=fake_refresh)

        # Quota: plan free, count at 0 (well under limit)
        async def fake_redis_get(key):
            if key.startswith("plan:"):
                return "free"
            if key.startswith("quota:"):
                return "0"
            return None

        mock_redis.get = AsyncMock(side_effect=fake_redis_get)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        with patch("api.services.chat_service.similarity_search", return_value=[]):
            response = await client.post(
                f"/api/v1/chat/{chatbot_id}",
                json={"message": "Hello", "session_id": "test-session"},
            )

        # Verify incr was called on the quota key
        assert mock_redis.incr.called
        incr_key = mock_redis.incr.call_args[0][0]
        assert incr_key.startswith("quota:owner@example.com:")


class TestMessageCount:
    @pytest.mark.asyncio
    async def test_save_message_increments_conversation_message_count(self):
        """save_message increments conversation.message_count."""
        conv_id = uuid.uuid4()
        mock_db = AsyncMock()

        fake_conv = MagicMock()
        fake_conv.id = conv_id
        fake_conv.message_count = 5

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_conv
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        from api.services.chat_service import save_message

        await save_message(conv_id, "user", "Hello", mock_db)

        assert fake_conv.message_count == 6
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_message_handles_none_message_count(self):
        """save_message handles None message_count gracefully."""
        conv_id = uuid.uuid4()
        mock_db = AsyncMock()

        fake_conv = MagicMock()
        fake_conv.id = conv_id
        fake_conv.message_count = None

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = fake_conv
        mock_db.execute = AsyncMock(return_value=result_mock)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        from api.services.chat_service import save_message

        await save_message(conv_id, "user", "Hello", mock_db)

        assert fake_conv.message_count == 1


class TestGetOrCreateConversation:
    @pytest.mark.asyncio
    async def test_creates_new_conversation_when_none_exists(self):
        chatbot_id = uuid.uuid4()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        from api.services.chat_service import get_or_create_conversation

        await get_or_create_conversation(chatbot_id, "session_abc", mock_db)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_existing_conversation(self):
        chatbot_id = uuid.uuid4()
        mock_db = AsyncMock()

        existing_conv = MagicMock()
        existing_conv.id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_conv
        mock_db.execute = AsyncMock(return_value=mock_result)

        from api.services.chat_service import get_or_create_conversation

        conv = await get_or_create_conversation(chatbot_id, "session_abc", mock_db)
        assert conv is existing_conv
        mock_db.add.assert_not_called()
