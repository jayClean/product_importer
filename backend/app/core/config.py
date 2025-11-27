"""Centralized application settings using pydantic settings."""

from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
# Look for .env in the backend directory or project root
env_path = Path(__file__).parent.parent.parent / ".env"
if not env_path.exists():
    # Try project root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)


class Settings(BaseSettings):
    """Environment-aware configuration (DB URLs, secrets, broker settings)."""

    # Application settings
    app_name: str = "Acme Product Importer"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    # allowed_hosts: List[str] = Field(
    #     default=["*"],
    #     env="ALLOWED_HOSTS",
    #     description="Comma-separated list of allowed hosts",
    # )

    # Database settings
    database_url: str = Field(
        default="postgresql+psycopg://user:pass@localhost:5432/product_importer",
        env="DATABASE_URL",
        description="Database connection URL",
    )

    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL",
    )

    # Celery settings
    celery_broker_url: str | None = None
    celery_result_url: str | None = None

    # Storage settings
    uploads_dir: str = Field(
        default="storage/uploads",
        env="UPLOADS_DIR",
        description="Directory for storing uploaded CSV files (absolute or relative path)",
    )
    s3_bucket: str = "product-imports"

    # CORS settings - stored as string, converted to list via validator
    cors_origins_raw: str | None = Field(
        default=None,
        env="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins",
        exclude=True,  # Exclude from serialization
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # Allow case-insensitive env var matching
        extra="ignore",  # Ignore extra env vars not defined in model
        populate_by_name=True,  # Allow both field name and alias
    )

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string to list."""
        if self.cors_origins_raw is None or not self.cors_origins_raw.strip():
            # Default origins for local development
            # Include Vercel frontend for testing deployed frontend against localhost backend
            return [
                "http://localhost:5173",
                "http://localhost:3000",
                "https://product-importer-three.vercel.app",
            ]
        origins = [
            origin.strip().rstrip("/")  # Remove trailing slashes
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]
        return (
            origins
            if origins
            else [
                "http://localhost:5173",
                "http://localhost:3000",
                "https://product-importer-three.vercel.app",
            ]
        )

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v: str | None) -> str:
        """Fix Heroku DATABASE_URL format (postgres:// -> postgresql+psycopg://)."""
        if v is None:
            return "postgresql+psycopg://user:pass@localhost:5432/product_importer"
        # If already set, check if it needs fixing
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        return v

    @field_validator("uploads_dir", mode="after")
    @classmethod
    def resolve_uploads_dir(cls, v: str) -> str:
        """Resolve uploads_dir to absolute path for consistency across processes."""
        path = Path(v)
        # If relative path, resolve relative to backend directory
        if not path.is_absolute():
            # Get backend directory (where this config file is located)
            backend_dir = Path(__file__).parent.parent
            path = (backend_dir / v).resolve()
        else:
            path = path.resolve()
        # Ensure directory exists
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    # @field_validator("allowed_hosts", mode="before")
    # @classmethod
    # def parse_allowed_hosts(cls, v: str | List[str] | None) -> List[str]:
    #     """Parse ALLOWED_HOSTS from comma-separated string or list."""
    #     if v is None or (isinstance(v, str) and not v.strip()):
    #         return ["*"]
    #     if isinstance(v, str):
    #         hosts = [host.strip() for host in v.split(",") if host.strip()]
    #         return hosts if hosts else ["*"]
    #     if isinstance(v, list):
    #         return v if v else ["*"]
    #     return ["*"]


@lru_cache
def get_settings() -> Settings:
    """Provide singleton-like access for dependency injection."""
    return Settings()
