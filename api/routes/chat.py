import uuid
import logging
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis
from api.dependencies import get_db, get_redis, verify_api_key_hash
from api.models.chatbot import Chatbot
from api.schemas.chat import ChatRequest, ChatResponse
from api.services.chat_service import stream_response, get_or_create_conversation
from api.billing.quota import check_quota, increment_message_count, get_user_plan
from api.config import settings
from api.seed import DEMO_CHATBOT_NAME, DEMO_OWNER_EMAIL

router = APIRouter()
logger = logging.getLogger(__name__)

RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 60


async def _resolve_chatbot_id(chatbot_id: str, db: AsyncSession) -> uuid.UUID:
    """Resolve chatbot_id string to UUID. Handles 'demo' as special case."""
    if chatbot_id == "demo":
        if not settings.demo_mode:
            raise HTTPException(status_code=404, detail="Demo mode not enabled")
        result = await db.execute(
            select(Chatbot).where(
                Chatbot.name == DEMO_CHATBOT_NAME,
                Chatbot.owner_email == DEMO_OWNER_EMAIL,
            )
        )
        demo_chatbot = result.scalar_one_or_none()
        if not demo_chatbot:
            raise HTTPException(status_code=404, detail="Demo chatbot not found")
        return demo_chatbot.id
    try:
        return uuid.UUID(chatbot_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chatbot ID format")


async def _check_rate_limit(
    redis_client: aioredis.Redis, session_id: str
) -> int | None:
    """Check per-session rate limit. Returns seconds to wait if exceeded, None if OK."""
    key = f"rate:{session_id}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, RATE_LIMIT_WINDOW)
    if count > RATE_LIMIT_MAX:
        ttl = await redis_client.ttl(key)
        return max(ttl, 1)
    return None


@router.post("/chat/{chatbot_id}", response_model=ChatResponse)
async def chat_rest(
    chatbot_id: str,
    request: ChatRequest,
    api_key: str | None = None,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """Non-streaming REST chat endpoint."""
    resolved_id = await _resolve_chatbot_id(chatbot_id, db)
    result = await db.execute(select(Chatbot).where(Chatbot.id == resolved_id, Chatbot.is_active == True))
    chatbot = result.scalar_one_or_none()
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")

    if api_key and not verify_api_key_hash(api_key, chatbot.api_key_hash):
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Per-session rate limit
    retry_after = await _check_rate_limit(redis_client, request.session_id)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(retry_after)},
        )

    # Quota enforcement
    owner_email = chatbot.owner_email or ""
    if owner_email:
        plan_tier = await get_user_plan(redis_client, owner_email)
        allowed = await check_quota(redis_client, owner_email, plan_tier)
        if not allowed:
            raise HTTPException(status_code=429, detail="Monthly message quota exceeded")

    full_response = ""
    async for token in stream_response(resolved_id, request.session_id, request.message, db):
        full_response += token

    # Increment quota counter after successful response
    if owner_email:
        await increment_message_count(redis_client, owner_email)

    conv = await get_or_create_conversation(resolved_id, request.session_id, db)
    return ChatResponse(
        response=full_response,
        session_id=request.session_id,
        conversation_id=str(conv.id),
    )


@router.websocket("/ws/chat/{chatbot_id}")
async def chat_websocket(
    websocket: WebSocket,
    chatbot_id: str,
    session_id: str = "default",
    api_key: str | None = None,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """WebSocket streaming chat endpoint."""
    # Resolve chatbot_id (handles "demo" string)
    try:
        resolved_id = await _resolve_chatbot_id(chatbot_id, db)
    except HTTPException:
        await websocket.close(code=4004)
        return

    result = await db.execute(select(Chatbot).where(Chatbot.id == resolved_id, Chatbot.is_active == True))
    chatbot = result.scalar_one_or_none()

    if not chatbot:
        await websocket.close(code=4004)
        return

    if api_key and not verify_api_key_hash(api_key, chatbot.api_key_hash):
        await websocket.close(code=4003)
        return

    await websocket.accept()
    logger.info(f"WS connected: chatbot={chatbot_id} session={session_id}")

    owner_email = chatbot.owner_email or ""

    try:
        while True:
            user_message = await websocket.receive_text()

            if user_message.strip() == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Per-session rate limit
            retry_after = await _check_rate_limit(redis_client, session_id)
            if retry_after is not None:
                await websocket.send_json({
                    "type": "error",
                    "content": "Rate limit exceeded",
                })
                await websocket.close(code=4029)
                return

            # Quota enforcement
            if owner_email:
                plan_tier = await get_user_plan(redis_client, owner_email)
                allowed = await check_quota(redis_client, owner_email, plan_tier)
                if not allowed:
                    await websocket.send_json({"type": "error", "content": "Monthly message quota exceeded"})
                    await websocket.close(code=4029)
                    return

            await websocket.send_json({"type": "start"})

            try:
                async for token in stream_response(resolved_id, session_id, user_message, db):
                    await websocket.send_json({"type": "token", "content": token})
                await websocket.send_json({"type": "end"})

                # Increment quota counter after successful response
                if owner_email:
                    await increment_message_count(redis_client, owner_email)
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await websocket.send_json({"type": "error", "content": "An error occurred"})

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"WS error: {e}", exc_info=True)
