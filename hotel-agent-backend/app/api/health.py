import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from app.core.database import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {
        "status": "alive",
        "service": "hotel-agent-backend",
    }


@router.get("/ready")
async def readiness() -> dict[str, str]:
    try:
        connected = await asyncio.wait_for(
            check_database_connection(),
            timeout=15,
        )

    except TimeoutError as exc:
        logger.exception("Database readiness check timed out")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service dependency timed out.",
        ) from exc

    except Exception as exc:
        logger.exception("Database readiness check failed")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not ready.",
        ) from exc

    if connected is not True:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not ready.",
        )

    return {
        "status": "ready",
        "database": "supabase-postgres",
    }
