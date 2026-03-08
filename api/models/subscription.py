from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDMixin, TimestampMixin


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_email: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(200))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(200))
    plan_tier: Mapped[str] = mapped_column(String(50), default="free")
    status: Mapped[str] = mapped_column(String(50), default="active")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
