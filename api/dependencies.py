import hashlib
import hmac
import uuid
from typing import AsyncGenerator, Optional
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis
from api.models.database import AsyncSessionLocal
from api.config import settings

_redis_pool: aioredis.Redis | None = None
_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_pool


def verify_api_key_hash(plain: str, stored_hash: str) -> bool:
    """Timing-safe API key hash comparison."""
    computed = hashlib.sha256(plain.encode()).hexdigest()
    return hmac.compare_digest(computed, stored_hash)


async def get_admin_key(x_admin_key: str = Header(...)) -> str:
    if not hmac.compare_digest(x_admin_key, settings.admin_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")
    return x_admin_key


async def get_admin_or_owner(
    chatbot_id: uuid.UUID,
    x_admin_key: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Authorize via admin key OR JWT owner of the chatbot.

    Returns the admin key string or the owner's email.
    """
    # 1. Try admin key first
    if x_admin_key is not None:
        if hmac.compare_digest(x_admin_key, settings.admin_key):
            return x_admin_key
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")

    # 2. Fall back to JWT
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from api.auth.middleware import _decode_token
    user = _decode_token(credentials.credentials)

    # 3. Verify ownership
    from api.models.chatbot import Chatbot
    result = await db.execute(
        select(Chatbot).where(
            Chatbot.id == chatbot_id,
            Chatbot.owner_email == user.email,
            Chatbot.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the owner of this chatbot")

    return user.email
