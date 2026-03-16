from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from api.models.knowledge_doc import KnowledgeDoc

KB_LIMITS: dict[str, int] = {
    "free": 10 * 1024 * 1024,       # 10 MB
    "pro": 500 * 1024 * 1024,       # 500 MB
    "business": -1,                   # unlimited
}


@dataclass
class KBQuotaResult:
    allowed: bool
    current_bytes: int
    limit_bytes: int


async def check_knowledge_base_quota(
    chatbot_id,
    db: AsyncSession,
    plan_tier: str = "free",
) -> KBQuotaResult:
    """Check if a chatbot's knowledge base is within its plan limit."""
    limit = KB_LIMITS.get(plan_tier, KB_LIMITS["free"])
    if limit == -1:
        return KBQuotaResult(allowed=True, current_bytes=0, limit_bytes=-1)

    result = await db.execute(
        select(func.coalesce(func.sum(func.length(KnowledgeDoc.content_text)), 0)).where(
            KnowledgeDoc.chatbot_id == chatbot_id,
        )
    )
    current_bytes = result.scalar_one()

    return KBQuotaResult(
        allowed=current_bytes < limit,
        current_bytes=current_bytes,
        limit_bytes=limit,
    )
