import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from api.dependencies import get_db
from api.auth.middleware import get_current_user, CurrentUser
from api.models.chatbot import Chatbot
from api.models.conversation import Conversation
from api.models.message import Message

router = APIRouter()
logger = logging.getLogger(__name__)


async def _assert_owner(chatbot_id: uuid.UUID, user: CurrentUser, db: AsyncSession) -> Chatbot:
    result = await db.execute(
        select(Chatbot).where(
            Chatbot.id == chatbot_id,
            Chatbot.owner_email == user.email,
            Chatbot.is_active == True,
        )
    )
    chatbot = result.scalar_one_or_none()
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return chatbot


@router.get("/chatbots/{chatbot_id}/analytics")
async def get_analytics(
    chatbot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Return per-chatbot analytics: message count, conversation count, avg messages per conversation."""
    await _assert_owner(chatbot_id, user, db)

    # Total conversations
    conv_result = await db.execute(
        select(func.count()).select_from(Conversation).where(Conversation.chatbot_id == chatbot_id)
    )
    total_conversations = conv_result.scalar_one() or 0

    # Total messages (user messages only for meaningful count)
    msg_result = await db.execute(
        select(func.count()).select_from(Message).join(
            Conversation, Message.conversation_id == Conversation.id
        ).where(
            Conversation.chatbot_id == chatbot_id,
            Message.role == "user",
        )
    )
    total_messages = msg_result.scalar_one() or 0

    avg_messages = round(total_messages / total_conversations, 1) if total_conversations > 0 else 0.0

    return {
        "chatbot_id": str(chatbot_id),
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "avg_messages_per_conversation": avg_messages,
    }


@router.get("/chatbots/{chatbot_id}/conversations")
async def list_conversations(
    chatbot_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Return recent conversations for a chatbot."""
    await _assert_owner(chatbot_id, user, db)

    result = await db.execute(
        select(Conversation)
        .where(Conversation.chatbot_id == chatbot_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    convs = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "session_id": c.session_id,
            "message_count": c.message_count,
            "created_at": c.created_at.isoformat(),
        }
        for c in convs
    ]
