import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, health
from app.api.admin import api_keys as admin_keys
from app.api.admin import models as admin_models
from app.api.admin import usage as admin_usage
from app.api.admin import users as admin_users
from app.api.user import keys as user_keys
from app.api.user import usage as user_usage
from app.api.v1 import chat, completions, embeddings, messages, models
from app.core.config import settings
from app.core.logging import logger
from app.database.init_db import init_db
from app.database.session import async_session_factory
from app.middleware.error_handler import register_error_handlers
from app.middleware.request_id import RequestIDMiddleware
from app.services.health_checker import health_checker


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} on Apple Silicon M5 (16 GB Unified Memory)...")
    async with async_session_factory() as session:
        await init_db(session)

    health_checker.start()
    yield
    # Shutdown
    health_checker.stop()
    logger.info("AI Gateway shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Universal AI Model Gateway optimized for Apple Silicon M5 (16 GB Unified Memory).",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Register Error Handlers
register_error_handlers(app)

# 2. Middlewares
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time", "Retry-After"],
)

# 3. Mount OpenAI & Anthropic Public API (/v1)
app.include_router(health.router)
app.include_router(models.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(completions.router, prefix=settings.API_V1_STR)
app.include_router(embeddings.router, prefix=settings.API_V1_STR)
app.include_router(messages.router)

# 4. Mount Management API (/api)
app.include_router(auth.router)
app.include_router(admin_models.router)
app.include_router(admin_users.router)
app.include_router(admin_keys.router)
app.include_router(admin_usage.router)
app.include_router(user_keys.router)
app.include_router(user_usage.router)

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend_dist")
if not os.path.exists(static_dir):
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend_dist")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
