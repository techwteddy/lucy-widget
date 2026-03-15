from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from api.models.chatbot import Chatbot
from api.config import settings

CHATBOT_LIMITS = {
    "free": 1,
    "pro": 5,
    "business": -1,  # unlimited
}


async def check_chatbot_quota(owner_email: str, plan_tier: str, db: AsyncSession) -> None:
    """Raise HTTP 403 if user has hit their plan's chatbot limit."""
    if settings.demo_mode:
        return  # skip quota in demo mode

    limit = CHATBOT_LIMITS.get(plan_tier, 1)
    if limit == -1:
        return  # unlimited

    count_result = await db.execute(
        select(func.count()).where(
            Chatbot.owner_email == owner_email,
            Chatbot.is_active == True,
        )
    )
    count = count_result.scalar()
    if count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Plan limit reached: {plan_tier} plan allows {limit} chatbot(s). Upgrade to create more.",
        )
