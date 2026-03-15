"""Seed demo data when DEMO_MODE is enabled."""
import logging
import uuid
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select
from api.models.database import AsyncSessionLocal
from api.models.chatbot import Chatbot
from api.models.conversation import Conversation
from api.models.message import Message

logger = logging.getLogger(__name__)

DEMO_CHATBOT_NAME = "Demo Assistant"
DEMO_OWNER_EMAIL = "demo@example.com"
DEMO_API_KEY = "cbk_demo_key_for_testing"
DEMO_SYSTEM_PROMPT = "You are a helpful assistant. Answer questions concisely and helpfully."


async def seed_demo_data() -> None:
    """Create demo chatbot with sample conversations. Idempotent."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Chatbot).where(
                Chatbot.name == DEMO_CHATBOT_NAME,
                Chatbot.owner_email == DEMO_OWNER_EMAIL,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.info("Demo chatbot already exists (id=%s), skipping seed.", existing.id)
            return

        chatbot_id = uuid.uuid4()
        chatbot = Chatbot(
            id=chatbot_id,
            name=DEMO_CHATBOT_NAME,
            system_prompt=DEMO_SYSTEM_PROMPT,
            welcome_message="Hi! I'm the demo assistant. Ask me anything!",
            primary_color="#3B82F6",
            position="bottom-right",
            title="Demo Chat",
            api_key_hash=hashlib.sha256(DEMO_API_KEY.encode()).hexdigest(),
            owner_email=DEMO_OWNER_EMAIL,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(chatbot)

        # Sample conversation
        convo_id = uuid.uuid4()
        convo = Conversation(
            id=convo_id,
            chatbot_id=chatbot_id,
            session_id="demo-session-001",
            message_count=2,
            created_at=datetime.now(timezone.utc),
        )
        session.add(convo)

        session.add(Message(
            id=uuid.uuid4(),
            conversation_id=convo_id,
            role="user",
            content="What can you help me with?",
            created_at=datetime.now(timezone.utc),
        ))
        session.add(Message(
            id=uuid.uuid4(),
            conversation_id=convo_id,
            role="assistant",
            content="I can answer questions, help with research, and assist with various tasks. How can I help you today?",
            created_at=datetime.now(timezone.utc),
        ))

        await session.commit()
        logger.info("Demo data seeded: chatbot=%s, conversation=%s", chatbot_id, convo_id)
