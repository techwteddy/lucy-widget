import uuid
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anthropic
from api.config import settings
from api.models.chatbot import Chatbot
from api.models.conversation import Conversation
from api.models.message import Message
from api.services.embedder import embed
from api.services.retriever import similarity_search
from api.services.webhook_dispatcher import dispatch_event
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    chatbot_id: uuid.UUID, session_id: str, db: AsyncSession
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.chatbot_id == chatbot_id,
            Conversation.session_id == session_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(
            id=uuid.uuid4(),
            chatbot_id=chatbot_id,
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return conv


async def get_history(conversation_id: uuid.UUID, db: AsyncSession, limit: int = 10) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def save_message(conversation_id: uuid.UUID, role: str, content: str, db: AsyncSession) -> Message:
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc),
    )
    db.add(msg)

    # Increment conversation message_count
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv:
        conv.message_count = (conv.message_count or 0) + 1

    await db.commit()
    return msg


async def stream_response(
    chatbot_id: uuid.UUID,
    session_id: str,
    user_message: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Stream response tokens from Claude with RAG context."""
    # Get chatbot config
    result = await db.execute(select(Chatbot).where(Chatbot.id == chatbot_id, Chatbot.is_active == True))
    chatbot = result.scalar_one_or_none()
    if not chatbot:
        yield "Error: chatbot not found"
        return

    # Get or create conversation
    conv = await get_or_create_conversation(chatbot_id, session_id, db)
    is_new_conversation = conv.message_count == 0

    # Save user message
    await save_message(conv.id, "user", user_message, db)

    # Fire webhook for new conversations
    if is_new_conversation:
        try:
            await dispatch_event(
                chatbot_id=chatbot_id,
                event_type="conversation.started",
                data={"conversation_id": str(conv.id), "session_id": session_id},
                db=db,
            )
        except Exception as e:
            logger.warning(f"Webhook dispatch failed for conversation.started: {e}")

    # Build RAG context + check escalation triggers
    context_text = ""
    low_confidence = False
    try:
        query_embedding = await embed(user_message)
        chunks = await similarity_search(query_embedding, chatbot_id, settings.retrieval_top_k, db)
        if chunks:
            context_parts = [row.chunk_text for row, _ in chunks]
            context_text = "\n\n".join(context_parts)
            # Check RAG confidence — high distance means low relevance
            best_distance = min(dist for _, dist in chunks)
            if best_distance > settings.rag_low_confidence_threshold:
                low_confidence = True
        else:
            low_confidence = True
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")

    # Check for explicit escalation phrases
    escalation_phrases = ["talk to a human", "speak to someone", "real person", "human agent", "talk to support"]
    explicit_escalation = any(phrase in user_message.lower() for phrase in escalation_phrases)

    if low_confidence or explicit_escalation:
        reason = "explicit_request" if explicit_escalation else "low_rag_confidence"
        conv.needs_human_review = True
        conv.escalation_reason = reason
        await db.commit()

        # Send Slack notification if configured
        if hasattr(chatbot, "slack_webhook_url") and chatbot.slack_webhook_url:
            try:
                import httpx
                slack_payload = {
                    "text": f"Escalation needed for chatbot *{chatbot.name}*\n"
                    f"Reason: {reason}\n"
                    f"User message: {user_message[:200]}\n"
                    f"Conversation: {conv.id}",
                }
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(chatbot.slack_webhook_url, json=slack_payload)
            except Exception as e:
                logger.warning(f"Slack notification failed: {e}")

    # Build messages
    history = await get_history(conv.id, db, limit=10)
    messages = [
        {"role": m.role, "content": m.content}
        for m in history[:-1]  # exclude the user message we just saved
    ]

    user_content = user_message
    if context_text:
        user_content = f"Context from knowledge base:\n{context_text}\n\n---\n\nUser question: {user_message}"
    messages.append({"role": "user", "content": user_content})

    # Stream from Claude
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    full_response = ""

    try:
        async with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=chatbot.system_prompt,
            messages=messages,
        ) as stream:
            async for token in stream.text_stream:
                full_response += token
                yield token
    except Exception as e:
        logger.error(f"Claude streaming error: {e}")
        yield "\n\n[Error: An error occurred while generating a response]"

    # Save assistant response
    await save_message(conv.id, "assistant", full_response, db)

    # Fire webhook for message created
    try:
        await dispatch_event(
            chatbot_id=chatbot_id,
            event_type="message.created",
            data={
                "conversation_id": str(conv.id),
                "role": "assistant",
                "content": full_response[:500],  # Truncate for webhook payload
            },
            db=db,
        )
    except Exception as e:
        logger.warning(f"Webhook dispatch failed for message.created: {e}")
