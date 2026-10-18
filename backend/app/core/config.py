import os
from functools import lru_cache
from pathlib import Path
from typing import Set
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""

    PROJECT_NAME: str = "InvoiceAI"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/invoiceai"

    # Storage & Upload Rules
    FILE_STORAGE_PATH: str = "storage/invoices"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB in bytes
    ALLOWED_EXTENSIONS: str = "pdf,png,jpg,jpeg"

    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Gemini Configuration
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_extensions_set(self) -> Set[str]:
        return {ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
