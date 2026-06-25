import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import settings
from app.database import engine, Base
from app.milvus.client import disconnect_milvus
from app.milvus.schema import init_milvus_collection
from app.core.middleware import RequestLoggingMiddleware, limiter
from app.routers import auth, sessions, chat, documents, health
import structlog

logger = structlog.get_logger()

async def clean_stale_documents_periodically():
    """Periodically check and fail documents stuck in pending/processing state for over 15 minutes."""
    from app.database import async_session_maker
    from app.models.document import Document
    from sqlalchemy import update
    from datetime import datetime, timezone, timedelta

    logger.info("stale_document_cleaner_started")
    while True:
        try:
            async with async_session_maker() as db:
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=15)
                stmt = (
                    update(Document)
                    .where(
                        Document.status.in_(["pending", "processing"]),
                        Document.updated_at < cutoff_time
                    )
                    .values(
                        status="failed",
                        error_message="Ingestion timed out or server restarted during processing."
                    )
                )
                result = await db.execute(stmt)
                await db.commit()
                if result.rowcount > 0:
                    logger.info("cleaned_stale_documents", count=result.rowcount)
        except Exception as e:
            logger.error("stale_document_cleaner_failed", error=str(e))
        
        # Run every 5 minutes (300 seconds)
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Orchestrate start-up and shut-down lifespan events."""
    logger.info("starting_up_backend_services")

    # PostgreSQL table initialization is now managed externally via Alembic migrations.

    # 2. Initialize Milvus Collection
    try:
        init_milvus_collection()
        logger.info("milvus_collection_initialized_successfully")
    except Exception as e:
        logger.error("milvus_collection_initialization_failed", error=str(e))

    # 3. Start periodic background cleanup task
    cleanup_task = asyncio.create_task(clean_stale_documents_periodically())

    yield

    # 4. Shutdown: cancel task and close pymilvus connections
    logger.info("shutting_down_backend_services")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    disconnect_milvus()

# Instantiate FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Local RAG QA System with PostgreSQL & Milvus standalone",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware Configuration
# Restrict allow_origins to localhost frontend by default as required
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Request Logging Middleware
app.add_middleware(RequestLoggingMiddleware)

# SlowAPI Rate Limiting exception handler setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include Routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(health.router)

# Custom global exception handler for slowapi or general errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_global_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "code": "INTERNAL_SERVER_ERROR"
        }
    )
