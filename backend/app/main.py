from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.api.v1.endpoints.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hook: creates storage directories and logs startup."""
    storage_path = Path(settings.FILE_STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"InvoiceAI backend initialized. Storage path: {storage_path.resolve()}")
    yield
    logger.info("InvoiceAI backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount root health check and versioned API router
app.include_router(health_router, tags=["Health"])
app.include_router(api_router, prefix=settings.API_V1_STR)

from backend.app.core.handlers import register_exception_handlers
register_exception_handlers(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
