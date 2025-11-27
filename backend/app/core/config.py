"""Centralized application settings using pydantic settings."""

from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
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
    uploads_dir: str = "storage/uploads"
    s3_bucket: str = "product-imports"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # Allow case-insensitive env var matching
        extra="ignore",  # Ignore extra env vars not defined in model
        populate_by_name=True,  # Allow both field name and alias
    )

    # @model_validator(mode="before")
    # @classmethod
    # def parse_allowed_hosts_before(cls, data: dict | list | None) -> dict | list | None:
    #     """Parse ALLOWED_HOSTS from comma-separated string before JSON parsing."""
    #     if isinstance(data, dict):
    #         # Check both uppercase and lowercase keys (case_sensitive=False)
    #         for key in ["ALLOWED_HOSTS", "allowed_hosts"]:
    #             if key in data:
    #                 value = data[key]
    #                 if isinstance(value, str):
    #                     if value.strip():
    #                         # Convert comma-separated string to list
    #                         data[key] = [
    #                             host.strip()
    #                             for host in value.split(",")
    #                             if host.strip()
    #                         ]
    #                     else:
    #                         # Empty string -> default
    #                         data[key] = ["*"]
    #                 elif value is None:
    #                     data[key] = ["*"]
    #                 # If it's already a list, leave it as is
    #                 break
    # return data

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
