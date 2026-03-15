import uuid
import secrets
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from api.dependencies import get_db, get_admin_key, get_admin_or_owner
from api.auth.middleware import get_optional_user, get_current_user, CurrentUser
from api.models.chatbot import Chatbot
from api.schemas.chatbot import (
    ChatbotCreate,
    ChatbotUpdate,
    ChatbotResponse,
    CreateChatbotResponse,
    WidgetConfig,
)
from datetime import datetime, timezone
from api.billing.chatbot_quota import check_chatbot_quota
from api.billing.quota import get_user_plan
from api.dependencies import get_redis
import redis.asyncio as aioredis

router = APIRouter()
logger = logging.getLogger(__name__)


def _hash_api_key(raw_key: str) -> str:
    """SHA-256 hash for randomly-generated API keys (not passwords)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


@router.get("/chatbots", response_model=list[ChatbotResponse])
async def list_chatbots(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Return chatbots owned by the authenticated user."""
    result = await db.execute(
        select(Chatbot).where(
            Chatbot.owner_email == user.email,
            Chatbot.is_active == True,
        )
    )
    return result.scalars().all()


def _make_chatbot(payload: ChatbotCreate, owner_email: Optional[str] = None) -> tuple[Chatbot, str]:
    raw_key = f"cbk_{secrets.token_urlsafe(32)}"
    chatbot = Chatbot(
        id=uuid.uuid4(),
        name=payload.name,
        system_prompt=payload.system_prompt,
        welcome_message=payload.welcome_message,
        primary_color=payload.primary_color,
        position=payload.position,
        title=payload.title,
        owner_email=owner_email or payload.owner_email,
        api_key_hash=_hash_api_key(raw_key),
        created_at=datetime.now(timezone.utc),
    )
    return chatbot, raw_key


def _chatbot_to_response(chatbot: Chatbot, raw_key: str) -> CreateChatbotResponse:
    return CreateChatbotResponse(
        id=chatbot.id,
        name=chatbot.name,
        system_prompt=chatbot.system_prompt,
        welcome_message=chatbot.welcome_message,
        primary_color=chatbot.primary_color,
        position=chatbot.position,
        title=chatbot.title,
        owner_email=chatbot.owner_email,
        is_active=chatbot.is_active,
        api_key=raw_key,
    )


@router.post("/chatbots", response_model=CreateChatbotResponse)
async def create_chatbot(
    payload: ChatbotCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_admin_key),
):
    """Admin endpoint — requires X-Admin-Key header."""
    chatbot, raw_key = _make_chatbot(payload)
    db.add(chatbot)
    await db.commit()
    await db.refresh(chatbot)
    return _chatbot_to_response(chatbot, raw_key)


@router.post("/chatbots/me", response_model=CreateChatbotResponse, status_code=status.HTTP_201_CREATED)
async def create_my_chatbot(
    payload: ChatbotCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """User endpoint — requires JWT bearer token. Sets owner_email from token."""
    plan_tier = await get_user_plan(redis_client, user.email)
    await check_chatbot_quota(user.email, plan_tier, db)
    chatbot, raw_key = _make_chatbot(payload, owner_email=user.email)
    db.add(chatbot)
    await db.commit()
    await db.refresh(chatbot)
    return _chatbot_to_response(chatbot, raw_key)


@router.get("/chatbots/{chatbot_id}", response_model=ChatbotResponse)
async def get_chatbot(
    chatbot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_admin_key),
):
    result = await db.execute(select(Chatbot).where(Chatbot.id == chatbot_id))
    chatbot = result.scalar_one_or_none()
    if not chatbot:
        raise HTTPException(status_code=404, detail="Not found")
    return chatbot


@router.get("/chatbots/{chatbot_id}/widget-config", response_model=WidgetConfig)
async def get_widget_config(
    chatbot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — returns display config only, no sensitive data."""
    result = await db.execute(
        select(Chatbot).where(Chatbot.id == chatbot_id, Chatbot.is_active == True)
    )
    chatbot = result.scalar_one_or_none()
    if not chatbot:
        raise HTTPException(status_code=404, detail="Not found")
    return WidgetConfig(
        id=chatbot.id,
        name=chatbot.name,
        welcome_message=chatbot.welcome_message,
        primary_color=chatbot.primary_color,
        position=chatbot.position,
        title=chatbot.title,
    )


@router.put("/chatbots/{chatbot_id}", response_model=ChatbotResponse)
async def update_chatbot(
    chatbot_id: uuid.UUID,
    payload: ChatbotUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_admin_or_owner),
):
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.execute(update(Chatbot).where(Chatbot.id == chatbot_id).values(**updates))
    await db.commit()

    result = await db.execute(select(Chatbot).where(Chatbot.id == chatbot_id))
    return result.scalar_one()


@router.delete("/chatbots/{chatbot_id}", status_code=204)
async def delete_chatbot(
    chatbot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_admin_or_owner),
):
    await db.execute(
        update(Chatbot).where(Chatbot.id == chatbot_id).values(is_active=False)
    )
    await db.commit()
