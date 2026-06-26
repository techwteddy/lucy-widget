import uuid
from pydantic import BaseModel
from typing import Optional


class ChatbotCreate(BaseModel):
    name: str
    system_prompt: str
    welcome_message: str = "Hi! How can I help you today?"
    primary_color: str = "#3B82F6"
    position: str = "bottom-right"
    title: str = "Chat with Lucy"
    owner_email: Optional[str] = None


class ChatbotUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    primary_color: Optional[str] = None
    position: Optional[str] = None
    title: Optional[str] = None


class ChatbotResponse(BaseModel):
    id: uuid.UUID
    name: str
    system_prompt: str
    welcome_message: str
    primary_color: str
    position: str
    title: str
    owner_email: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class CreateChatbotResponse(ChatbotResponse):
    api_key: str  # Only returned on creation


class WidgetConfig(BaseModel):
    id: uuid.UUID
    name: str
    welcome_message: str
    primary_color: str
    position: str
    title: str


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    chunk_count: int
    error_message: Optional[str]

    model_config = {"from_attributes": True}
