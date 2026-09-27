from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    POSTGRES_USER: str = "civicpulse"
    POSTGRES_PASSWORD: str = "civicpulse_secret_pw"
    POSTGRES_DB: str = "civicpulse_db"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = (
        "postgresql+asyncpg://civicpulse:civicpulse_secret_pw@postgres:5432/civicpulse_db"
    )
    SYNC_DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379/0"

    # Rate Limiting & Caching
    RATE_LIMIT_PER_MINUTE: int = 60
    STATS_CACHE_TTL_SECONDS: int = 30
    TRIAGE_CACHE_TTL_SECONDS: int = 86400  # 24 hours

    # AI Triage
    TRIAGE_PROVIDER: str = "simulated"  # llm, ollama, rules, simulated
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"

    # Timeout & Retry settings for AI providers
    AI_TIMEOUT_SECONDS: float = 10.0
    AI_MAX_RETRIES: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()
