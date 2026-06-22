from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import httpx

from app.core.dependencies import get_db
from app.milvus.client import check_milvus_health
from app.config import settings
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/health", tags=["Health"])

async def check_postgres_health(db: AsyncSession) -> bool:
    try:
        # Run a simple ping query
        await db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("postgres_health_check_failed", error=str(e))
        return False

async def check_vllm_health() -> bool:
    if settings.MOCK_VLLM:
        return True
    try:
        url = f"{settings.VLLM_BASE_URL}/models"
        headers = {}
        if settings.HF_TOKEN and settings.HF_TOKEN != "hf_placeholder":
            headers["Authorization"] = f"Bearer {settings.HF_TOKEN}"
            
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url, headers=headers)
            return response.status_code == 200
    except Exception as e:
        logger.error("vllm_health_check_failed", error=str(e))
        return False

@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Perform a system health check.
    Checks connectivity to PostgreSQL, Milvus, and the vLLM server.
    """
    postgres_ok = await check_postgres_health(db)
    milvus_ok = check_milvus_health()
    vllm_ok = await check_vllm_health()

    overall_status = "ok"
    if not (postgres_ok and milvus_ok and vllm_ok):
        overall_status = "unhealthy"

    vllm_status = "ok"
    if settings.MOCK_VLLM:
        vllm_status = "ok (mocked)"
    elif not vllm_ok:
        vllm_status = "down"

    return {
        "status": overall_status,
        "postgres": "ok" if postgres_ok else "down",
        "milvus": "ok" if milvus_ok else "down",
        "vllm": vllm_status
    }
