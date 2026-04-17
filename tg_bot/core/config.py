from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(..., alias="BOT_TOKEN")
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")

    celery_broker_url: str = Field("redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field("redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    environment: str = Field("production", alias="ENVIRONMENT")

    rate_limit_requests: int = Field(10, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(60, alias="RATE_LIMIT_WINDOW")

    db_pool_size: int = Field(10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(20, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(30, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(1800, alias="DB_POOL_RECYCLE")

    gemini_max_retries: int = Field(3, alias="GEMINI_MAX_RETRIES")
    gemini_timeout: int = Field(30, alias="GEMINI_TIMEOUT")

    scraper_timeout: int = Field(60, alias="SCRAPER_TIMEOUT")
    scraper_max_retries: int = Field(3, alias="SCRAPER_MAX_RETRIES")


def get_settings() -> Settings:
    return Settings()
