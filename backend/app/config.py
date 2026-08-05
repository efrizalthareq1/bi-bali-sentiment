"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_cookie_value(value: object) -> object:
    if isinstance(value, str):
        return value.strip().strip('"').strip("'")
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/sentiment.db"
    llm_provider: str = "none"  # openai | anthropic | none
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"
    cors_origins: str = "http://localhost:3000"
    enable_scheduler: bool = True
    news_sync_interval_minutes: int = 60
    analyze_interval_minutes: int = 5
    x_bearer_token: str = ""
    instagram_access_token: str = ""
    instagram_business_account_id: str = ""
    # Graph API rate-limits unique hashtag lookups (~30 / 7 days)
    instagram_hashtag_sync_limit: int = 15
    # Optional: monitor comments on an event account (default QRIS Summer Run)
    instagram_monitor_username: str = "qrissummerrun"
    # Opsi B: cookie sessionid (+ csrftoken) dari browser saat login IG
    instagram_session_id: str = ""
    instagram_csrf_token: str = ""
    instagram_ds_user_id: str = ""

    @field_validator("instagram_session_id", "instagram_csrf_token", "instagram_ds_user_id", mode="before")
    @classmethod
    def strip_instagram_cookies(cls, value: object) -> object:
        return _strip_cookie_value(value)
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_lookback_days: int = 30

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
