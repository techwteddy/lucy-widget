from datetime import datetime, timezone
from calendar import monthrange

from .stripe_client import PLANS


def _quota_key(user_email: str) -> str:
    now = datetime.now(timezone.utc)
    return f"quota:{user_email}:{now.strftime('%Y-%m')}"


def _seconds_until_end_of_month() -> int:
    now = datetime.now(timezone.utc)
    _, days_in_month = monthrange(now.year, now.month)
    end = now.replace(day=days_in_month, hour=23, minute=59, second=59)
    return max(int((end - now).total_seconds()), 1)


async def get_message_count(redis, user_email: str) -> int:
    val = await redis.get(_quota_key(user_email))
    return int(val) if val else 0


async def increment_message_count(redis, user_email: str) -> int:
    key = _quota_key(user_email)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _seconds_until_end_of_month())
    return count


def get_plan_limit(plan_tier: str) -> int:
    plan = PLANS.get(plan_tier, PLANS["free"])
    return plan["messages_per_month"]


async def check_quota(redis, user_email: str, plan_tier: str) -> bool:
    count = await get_message_count(redis, user_email)
    limit = get_plan_limit(plan_tier)
    if limit == -1:
        return True
    return count < limit


async def get_user_plan(redis, user_email: str) -> str:
    """Look up plan tier by user email. Defaults to 'free' if not found."""
    plan = await redis.get(f"plan:{user_email}")
    return plan if plan else "free"
