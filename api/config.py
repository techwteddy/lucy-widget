from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://chatbot:chatbot@localhost:5432/chatbot_widget"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    admin_key: str = "dev-admin-key"
    secret_key: str = "dev-secret-key"
    environment: str = "development"

    # Widget defaults
    default_system_prompt: str = (
        "You are a helpful assistant. Answer questions concisely and helpfully "
        "based on the provided context. If you don't know something, say so."
    )

    # Supabase auth
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = "dev-jwt-secret"

    # Stripe billing
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_business_price_id: str = ""

    # Demo mode — bypasses auth and Stripe
    demo_mode: bool = False

    @model_validator(mode='after')
    def _check_dev_defaults(self) -> 'Settings':
        if self.environment != "development":
            dev_defaults = []
            if self.admin_key == "dev-admin-key":
                dev_defaults.append("admin_key")
            if self.secret_key == "dev-secret-key":
                dev_defaults.append("secret_key")
            if self.supabase_jwt_secret == "dev-jwt-secret":
                dev_defaults.append("supabase_jwt_secret")
            if dev_defaults:
                raise ValueError(
                    f"Dev defaults not allowed in {self.environment}: {', '.join(dev_defaults)}"
                )
        return self

    # Gemini embedding
    gemini_api_key: str = ""

    # RAG settings
    embedding_model: str = "gemini-embedding-2-preview"
    embedding_dim: int = 768
    retrieval_top_k: int = 5
    chunk_size: int = 400
    chunk_overlap: int = 50
    rag_low_confidence_threshold: float = 0.7


settings = Settings()
