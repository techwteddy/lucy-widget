import uuid
from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, UUIDMixin, TimestampMixin


class Chatbot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chatbots"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    welcome_message: Mapped[str] = mapped_column(
        String(500), default="Hi! How can I help you today?"
    )
    primary_color: Mapped[str] = mapped_column(String(7), default="#3B82F6")
    position: Mapped[str] = mapped_column(String(20), default="bottom-right")
    title: Mapped[str] = mapped_column(String(100), default="Chat with us")
    api_key_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_email: Mapped[str | None] = mapped_column(String(200))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped["User | None"] = relationship(back_populates="chatbots")  # type: ignore[name-defined]
    knowledge_docs: Mapped[list["KnowledgeDoc"]] = relationship(back_populates="chatbot", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="chatbot", cascade="all, delete-orphan")
