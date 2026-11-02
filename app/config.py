"""Application configuration loaded from .env via pydantic-settings."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object; all values come from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ─────────────────────────────────────────────────────────────────
    app_name: str = "ContentForge"
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Google Gemini ────────────────────────────────────────────────────────
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="", validation_alias="GEMINI_MODEL")

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./contentforge.db"

    # ── JWT auth ─────────────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # ── Upload limits ────────────────────────────────────────────────────────
    max_upload_size: int = 10_485_760  # 10 MB

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
