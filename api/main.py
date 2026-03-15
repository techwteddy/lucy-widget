from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from api.config import settings
from api.models.database import engine
from api.models.base import Base
from api.routes import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Chatbot Widget API...")
    async with engine.begin() as conn:
        # Ensure pgvector extension exists (handled by migration in prod)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    if settings.demo_mode:
        from api.seed import seed_demo_data
        logger.info("DEMO_MODE enabled — seeding demo data...")
        await seed_demo_data()
    logger.info("Ready.")
    yield
    logger.info("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title="Chatbot Widget API",
    description="Embeddable AI chatbot widget backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Required for embeds on any website
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request_id = str(uuid.uuid4())[:8]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(api_router)
