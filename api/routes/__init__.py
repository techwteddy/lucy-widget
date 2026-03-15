from fastapi import APIRouter
from .health import router as health_router
from .chatbots import router as chatbots_router
from .documents import router as documents_router
from .chat import router as chat_router
from .widget import router as widget_router
from .analytics import router as analytics_router
from api.auth import auth_router
from api.billing.routes import router as billing_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(billing_router)
api_router.include_router(chatbots_router, prefix="/api/v1", tags=["chatbots"])
api_router.include_router(documents_router, prefix="/api/v1", tags=["documents"])
api_router.include_router(chat_router, prefix="/api/v1", tags=["chat"])
api_router.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])
api_router.include_router(widget_router, tags=["widget"])
