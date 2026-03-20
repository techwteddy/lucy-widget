import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from api.config import settings

# Ensure tests always use the dev JWT secret regardless of .env
settings.supabase_jwt_secret = "dev-jwt-secret"
settings.admin_key = "dev-admin-key"


@pytest.fixture
def mock_embed():
    """Returns a fixed 768-dim vector (async)."""
    with patch("api.services.embedder.embed", new_callable=AsyncMock) as m1, \
         patch("api.services.chat_service.embed", new_callable=AsyncMock) as m2:
        m1.return_value = [0.1] * 768
        m2.return_value = [0.1] * 768
        yield m1


@pytest.fixture
def mock_embed_batch():
    """Returns fixed 768-dim vectors for a batch (async)."""
    async def _batch(texts, **kwargs):
        return [[0.1] * 768 for _ in texts]

    with patch("api.services.embedder.embed_batch", new_callable=AsyncMock) as m1, \
         patch("api.services.doc_processor.embed_batch", new_callable=AsyncMock) as m2:
        m1.side_effect = _batch
        m2.side_effect = _batch
        yield m1


@pytest.fixture
def mock_anthropic():
    """Mock Claude streaming responses."""
    with patch("api.services.chat_service.anthropic.AsyncAnthropic") as m:
        client = AsyncMock()
        m.return_value = client

        stream = AsyncMock()
        stream.__aenter__ = AsyncMock(return_value=stream)
        stream.__aexit__ = AsyncMock(return_value=False)

        async def token_gen():
            for token in ["Hello", " ", "world", "!"]:
                yield token

        stream.text_stream = token_gen()
        client.messages.stream.return_value = stream
        yield client


@pytest.fixture
def mock_db():
    """Async mock DB session with properly configured execute return value."""
    session = AsyncMock()
    # Return a regular MagicMock so sync methods (scalar_one_or_none, scalars) work
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalar_one.return_value = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    return session


@pytest.fixture
def mock_redis():
    """Async mock Redis client."""
    r = AsyncMock()
    r.ping = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.ttl = AsyncMock(return_value=60)
    return r


@pytest.fixture
async def client(mock_db, mock_redis):
    """Test client with dependency overrides for DB and Redis."""
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


@pytest.fixture
def admin_headers():
    return {"X-Admin-Key": "dev-admin-key"}


@pytest.fixture
def chatbot_id():
    return str(uuid.uuid4())


@pytest.fixture
async def demo_client(mock_redis):
    """Test client with DEMO_MODE enabled and demo chatbot in mock DB."""
    from httpx import AsyncClient, ASGITransport
    from api.main import app
    from api.dependencies import get_db, get_redis
    from api.config import settings
    from api.seed import DEMO_CHATBOT_NAME, DEMO_OWNER_EMAIL
    from api.models.chatbot import Chatbot
    from api.models.conversation import Conversation
    from datetime import datetime, timezone
    import hashlib

    # Enable demo mode
    original_demo_mode = settings.demo_mode
    settings.demo_mode = True

    # Create a demo chatbot for the mock DB to return
    demo_chatbot_id = uuid.uuid4()
    demo_chatbot = Chatbot(
        id=demo_chatbot_id,
        name=DEMO_CHATBOT_NAME,
        owner_email=DEMO_OWNER_EMAIL,
        system_prompt="Demo prompt",
        welcome_message="Hello!",
        api_key_hash=hashlib.sha256(b"demo_key").hexdigest(),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    # Create a demo conversation
    demo_conversation = Conversation(
        id=uuid.uuid4(),
        chatbot_id=demo_chatbot_id,
        session_id="test-session",
        created_at=datetime.now(timezone.utc),
        message_count=0,
    )

    # Create a mock DB session that returns appropriate objects
    mock_db = AsyncMock()
    
    def make_result(obj):
        """Create a mock result that returns the given object."""
        result = MagicMock()
        result.scalar_one_or_none.return_value = obj
        result.scalar_one.return_value = obj
        result.scalars.return_value.all.return_value = [obj] if obj else []
        return result

    async def mock_execute(query):
        """Return appropriate mock data based on query type."""
        # Check the entity being selected by examining column_descriptions
        # SQLAlchemy queries have column_descriptions that tell us the table
        try:
            # For SELECT queries, check the entity
            if hasattr(query, 'column_descriptions') and query.column_descriptions:
                entity = query.column_descriptions[0].get('entity')
                entity_name = entity.__name__ if entity and hasattr(entity, '__name__') else str(entity)
                
                if 'Chatbot' in entity_name:
                    return make_result(demo_chatbot)
                elif 'Conversation' in entity_name:
                    return make_result(demo_conversation)
        except Exception:
            pass
        
        # Fallback: check string representation
        query_str = str(query)
        if "chatbot" in query_str.lower() and "conversation" not in query_str.lower():
            return make_result(demo_chatbot)
        elif "conversation" in query_str.lower():
            return make_result(demo_conversation)
        
        return make_result(None)
    
    mock_db.execute = mock_execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    async def override_get_db():
        yield mock_db

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    settings.demo_mode = original_demo_mode


@pytest.fixture
def demo_chatbot_id():
    """Return the string 'demo' for demo chatbot ID resolution tests."""
    return "demo"
