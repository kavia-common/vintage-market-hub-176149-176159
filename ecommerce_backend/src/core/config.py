from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables via Pydantic.

    This configuration centralizes application-level settings for database,
    security, CORS, payments, and file storage. Values are read from the
    environment at runtime.
    """

    # App metadata
    PROJECT_NAME: str = "Vintage Market Hub - Backend"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str

    # Security / JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # CORS
    CORS_ORIGINS: List[AnyHttpUrl] | List[str] = []

    # Payments
    PAYMENT_PROVIDER: str = "stripe"
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # File storage
    FILE_STORAGE_PROVIDER: str = "local"
    FILE_STORAGE_DIR: str = "./storage"

    # Misc
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        """Allow comma-separated strings or JSON-style lists for CORS origins."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        return []

# PUBLIC_INTERFACE
@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance to avoid repeated env parsing."""
    return Settings()
