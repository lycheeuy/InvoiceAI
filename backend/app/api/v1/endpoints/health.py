from typing import Dict
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.logging import logger
from backend.app.db.session import get_db

router = APIRouter()


@router.get("/health", response_model=Dict[str, str], tags=["Health"])
def health_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Returns service health and database connectivity status.
    Credentials and connection details are never exposed.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
    }
