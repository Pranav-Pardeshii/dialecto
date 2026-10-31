from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/dialecto"

    # Groq AI
    GROQ_API_KEY: str = Field(default="mock-key")
    LLM_PRIMARY_MODEL: str = "openai/gpt-oss-120b"
    LLM_FALLBACK_MODELS: str = "llama-3.3-70b-versatile,llama-3.1-8b-instant"
    WHISPER_MODEL: str = "whisper-large-v3-turbo"
    LLM_TIMEOUT_S: float = 15.0

    # Security & CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    @property
    def fallback_models_list(self) -> list[str]:
        return [m.strip() for m in self.LLM_FALLBACK_MODELS.split(",") if m.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
