import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date, text
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


@router.get("/chatbots/{chatbot_id}/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    chatbot_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Return messages for a specific conversation."""
    await _assert_owner(chatbot_id, user, db)

    # Verify conversation belongs to this chatbot
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.chatbot_id == chatbot_id,
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


# ------------------------------------------------------------------
# Time-series analytics
# ------------------------------------------------------------------


class TimeseriesPoint(BaseModel):
    date: str  # "2026-03-15"
    message_count: int


class TimeseriesResponse(BaseModel):
    chatbot_id: str
    days: int
    data: List[TimeseriesPoint]


@router.get(
    "/chatbots/{chatbot_id}/analytics/timeseries",
    response_model=TimeseriesResponse,
)
async def get_timeseries(
    chatbot_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Return daily message counts for the last N days."""
    await _assert_owner(chatbot_id, user, db)

    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Query: count messages per day
    result = await db.execute(
        select(
            func.date_trunc("day", Message.created_at).label("day"),
            func.count().label("cnt"),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.chatbot_id == chatbot_id,
            Message.created_at >= start_date,
        )
        .group_by(text("1"))
        .order_by(text("1"))
    )
    rows = result.all()

    # Build a lookup from date string → count
    counts = {}
    for row in rows:
        day_val = row[0]
        if hasattr(day_val, "strftime"):
            key = day_val.strftime("%Y-%m-%d")
        else:
            key = str(day_val)[:10]
        counts[key] = row[1]

    # Fill in zeros for missing days
    data = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        data.append(TimeseriesPoint(date=date_str, message_count=counts.get(date_str, 0)))

    return TimeseriesResponse(chatbot_id=str(chatbot_id), days=days, data=data)
