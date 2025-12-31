"""
Centralized configuration management for fin-infra-template.

All configuration is loaded from environment variables (.env file).
Type-safe with Pydantic validation and defaults.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================================
    # Application
    # ========================================================================
    app_env: Literal["local", "dev", "test", "prod"] = Field(default="local")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="DEBUG")
    log_format: Literal["plain", "json"] = Field(default="plain")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8001)

    # ========================================================================
    # Database (svc-infra)
    # ========================================================================
    sql_url: str = Field(
        default="sqlite+aiosqlite:////tmp/fin_infra_template.db",
        description="Database connection string",
    )
    sql_pool_size: int = Field(default=5)
    sql_max_overflow: int = Field(default=10)
    sql_pool_timeout: int = Field(default=30)

    # ========================================================================
    # Cache - Redis (svc-infra)
    # ========================================================================
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_prefix: str = Field(default="fin_infra_template")
    cache_version: str = Field(default="v1")
    cache_default_ttl: int = Field(default=3600)

    # ========================================================================
    # Observability (svc-infra)
    # ========================================================================
    metrics_enabled: bool = Field(default=True)
    metrics_path: str = Field(default="/metrics")

    # ========================================================================
    # Security (svc-infra)
    # ========================================================================
    security_enabled: bool = Field(default=True)
    cors_enabled: bool = Field(default=True)
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:3001")

    # ========================================================================
    # Banking Providers (fin-infra)
    # ========================================================================
    enable_banking: bool = Field(default=False)

    # Plaid
    plaid_client_id: str | None = Field(default=None)
    plaid_secret: str | None = Field(default=None)
    plaid_env: Literal["sandbox", "development", "production"] = Field(default="sandbox")

    # Teller
    teller_api_key: str | None = Field(default=None)
    teller_certificate_path: str | None = Field(default=None)
    teller_private_key_path: str | None = Field(default=None)
    teller_env: Literal["sandbox", "production"] = Field(default="sandbox")

    # MX
    mx_client_id: str | None = Field(default=None)
    mx_api_key: str | None = Field(default=None)
    mx_env: Literal["sandbox", "production"] = Field(default="sandbox")

    # ========================================================================
    # Market Data Providers (fin-infra)
    # ========================================================================
    enable_market_data: bool = Field(default=True)

    # Alpha Vantage
    alphavantage_api_key: str | None = Field(default=None)

    # Polygon
    polygon_api_key: str | None = Field(default=None)

    # ========================================================================
    # Credit Score Providers (fin-infra)
    # ========================================================================
    enable_credit: bool = Field(default=False)

    # Experian
    experian_client_id: str | None = Field(default=None)
    experian_client_secret: str | None = Field(default=None)
    experian_base_url: str = Field(default="https://sandbox-us-api.experian.com")

    # Equifax
    equifax_client_id: str | None = Field(default=None)
    equifax_client_secret: str | None = Field(default=None)

    # TransUnion
    transunion_client_id: str | None = Field(default=None)
    transunion_client_secret: str | None = Field(default=None)

    # ========================================================================
    # Brokerage Providers (fin-infra)
    # ========================================================================
    enable_brokerage: bool = Field(default=False)

    # Alpaca
    alpaca_api_key: str | None = Field(default=None)
    alpaca_secret_key: str | None = Field(default=None)
    alpaca_env: Literal["paper", "live"] = Field(default="paper")

    # Interactive Brokers
    ib_username: str | None = Field(default=None)
    ib_password: str | None = Field(default=None)

    # SnapTrade
    snaptrade_client_id: str | None = Field(default=None)
    snaptrade_consumer_key: str | None = Field(default=None)

    # ========================================================================
    # Investment Holdings Providers (fin-infra)
    # ========================================================================
    enable_investments: bool = Field(default=False)

    # Plaid Investment API (uses same credentials as banking)
    # Already configured above in Banking Providers section

    # SnapTrade Investment API (uses same credentials as brokerage)
    # Already configured above in Brokerage Providers section

    # ========================================================================
    # Tax Data Providers (fin-infra)
    # ========================================================================
    enable_tax: bool = Field(default=True)

    # IRS
    irs_username: str | None = Field(default=None)
    irs_password: str | None = Field(default=None)

    # TaxBit
    taxbit_client_id: str | None = Field(default=None)
    taxbit_client_secret: str | None = Field(default=None)
    taxbit_base_url: str = Field(default="https://api.taxbit.com")

    # ========================================================================
    # AI/LLM Configuration (fin-infra)
    # ========================================================================
    enable_llm_insights: bool = Field(default=False)
    enable_llm_categorization: bool = Field(default=False)

    # Google Gemini
    google_api_key: str | None = Field(default=None)
    google_model: str = Field(default="gemini-1.5-flash")

    # OpenAI
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")

    # ========================================================================
    # Feature Flags (fin-infra)
    # ========================================================================
    enable_analytics: bool = Field(default=True)
    enable_budgets: bool = Field(default=True)
    enable_goals: bool = Field(default=True)
    enable_documents: bool = Field(default=True)
    enable_investments: bool = Field(default=True)
    enable_net_worth: bool = Field(default=True)
    enable_recurring: bool = Field(default=True)
    enable_categorization: bool = Field(default=True)
    enable_insights: bool = Field(default=True)
    enable_crypto_insights: bool = Field(default=False)
    enable_rebalancing: bool = Field(default=True)
    enable_scenarios: bool = Field(default=True)

    # ========================================================================
    # Timeouts & Resource Limits (svc-infra)
    # ========================================================================
    timeout_handler_seconds: int | None = Field(default=30)
    timeout_body_read_seconds: int | None = Field(default=10)
    request_max_size_mb: int | None = Field(default=10)
    graceful_shutdown_enabled: bool = Field(default=True)

    # ========================================================================
    # Rate Limiting (svc-infra)
    # ========================================================================
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests_per_minute: int = Field(default=100)

    # ========================================================================
    # Idempotency (svc-infra)
    # ========================================================================
    idempotency_enabled: bool = Field(default=True)
    idempotency_header: str = Field(default="Idempotency-Key")
    idempotency_ttl_seconds: int = Field(default=86400)

    # ========================================================================
    # Computed Properties
    # ========================================================================

    @property
    def database_configured(self) -> bool:
        """Check if database is configured."""
        return bool(self.sql_url)

    @property
    def cache_configured(self) -> bool:
        """Check if cache (Redis) is configured."""
        return bool(self.redis_url)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def banking_configured(self) -> bool:
        """Check if any banking provider is configured."""
        return self.enable_banking and (
            bool(self.plaid_client_id and self.plaid_secret)
            or bool(self.teller_api_key)
            or bool(self.mx_client_id and self.mx_api_key)
        )

    @property
    def market_data_configured(self) -> bool:
        """Check if market data is configured (Yahoo Finance works without key)."""
        return self.enable_market_data

    @property
    def credit_configured(self) -> bool:
        """Check if any credit provider is configured."""
        return self.enable_credit and bool(self.experian_client_id and self.experian_client_secret)

    @property
    def brokerage_configured(self) -> bool:
        """Check if any brokerage provider is configured."""
        return self.enable_brokerage and bool(self.alpaca_api_key and self.alpaca_secret_key)

    @property
    def investments_configured(self) -> bool:
        """Check if any investment holdings provider is configured."""
        # Investments can use Plaid (banking) or SnapTrade (brokerage) credentials
        return self.enable_investments and (
            bool(self.plaid_client_id and self.plaid_secret)
            or bool(self.snaptrade_client_id and self.snaptrade_consumer_key)
        )

    @property
    def llm_configured(self) -> bool:
        """Check if any LLM provider is configured."""
        return (self.enable_llm_insights or self.enable_llm_categorization) and (
            bool(self.google_api_key) or bool(self.openai_api_key)
        )

    @property
    def alpaca_paper_trading(self) -> bool:
        """Check if Alpaca is in paper trading mode."""
        return self.alpaca_env == "paper"

    @property
    def analytics_enabled(self) -> bool:
        """Check if analytics is enabled."""
        return self.enable_analytics

    @property
    def categorization_enabled(self) -> bool:
        """Check if categorization is enabled."""
        return self.enable_categorization

    @property
    def budgets_enabled(self) -> bool:
        """Check if budgets is enabled."""
        return self.enable_budgets

    @property
    def goals_enabled(self) -> bool:
        """Check if goals is enabled."""
        return self.enable_goals

    @property
    def net_worth_enabled(self) -> bool:
        """Check if net worth tracking is enabled."""
        return self.enable_net_worth

    @property
    def documents_enabled(self) -> bool:
        """Check if documents is enabled."""
        return self.enable_documents

    @property
    def insights_enabled(self) -> bool:
        """Check if insights feed is enabled."""
        return self.enable_insights


# Singleton instance
settings = Settings()
