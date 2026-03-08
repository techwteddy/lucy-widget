import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    supabase_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    plan_tier: Mapped[str] = mapped_column(String(50), default="free")

    chatbots: Mapped[list["Chatbot"]] = relationship(back_populates="owner", cascade="all, delete-orphan")  # type: ignore[name-defined]
