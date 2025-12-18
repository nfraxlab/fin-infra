from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Cache / infra
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # Plaid
    plaid_client_id: str | None = Field(default=None, alias="PLAID_CLIENT_ID")
    plaid_secret: str | None = Field(default=None, alias="PLAID_SECRET")
    plaid_env: str = Field(default="sandbox", alias="PLAID_ENVIRONMENT")

    # Alpaca
    alpaca_api_key: str | None = Field(default=None, alias="ALPACA_API_KEY")
    alpaca_api_secret: str | None = Field(default=None, alias="ALPACA_API_SECRET")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets", alias="ALPACA_BASE_URL"
    )

    # Alpha Vantage / Market Data
    alphavantage_api_key: str | None = Field(default=None, alias="ALPHAVANTAGE_API_KEY")

    # Identity / Credit (placeholders)
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    experian_api_key: str | None = Field(default=None, alias="EXPERIAN_API_KEY")
    experian_environment: str = Field(default="sandbox", alias="EXPERIAN_ENVIRONMENT")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
