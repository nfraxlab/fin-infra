"""Base provider ABCs for fin-infra.

This module defines abstract base classes for all financial data providers.
These are the canonical ABCs - use these instead of fin_infra.clients.

Sync vs Async Pattern:
    Most providers use SYNCHRONOUS methods for simplicity. The exceptions are:
    - InvestmentProvider: Uses async methods (get_holdings, get_investment_accounts)

    If you need async, wrap sync providers with asyncio.to_thread():
        import asyncio
        result = await asyncio.to_thread(provider.quote, "AAPL")

Provider Categories:
    - MarketDataProvider: Stock/equity quotes and historical data
    - CryptoDataProvider: Cryptocurrency market data
    - BankingProvider: Bank account aggregation (Plaid, Teller, MX)
    - BrokerageProvider: Trading operations (Alpaca, Interactive Brokers)
    - CreditProvider: Credit scores and reports
    - TaxProvider: Tax documents and calculations
    - IdentityProvider: Identity verification
    - InvestmentProvider: Investment holdings (async)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any

from ..models import Candle, Quote


class MarketDataProvider(ABC):
    @abstractmethod
    def quote(self, symbol: str) -> Quote:
        pass

    @abstractmethod
    def history(
        self, symbol: str, *, period: str = "1mo", interval: str = "1d"
    ) -> Sequence[Candle]:
        pass


class CryptoDataProvider(ABC):
    @abstractmethod
    def ticker(self, symbol_pair: str) -> Any:
        pass

    @abstractmethod
    def ohlcv(self, symbol_pair: str, timeframe: str = "1d", limit: int = 100) -> Any:
        pass


class BankingProvider(ABC):
    """Abstract provider for bank account aggregation (Teller, Plaid, MX)."""

    @abstractmethod
    def create_link_token(self, user_id: str) -> str:
        """Create a link/connect token for user to authenticate with their bank."""
        pass

    @abstractmethod
    def exchange_public_token(self, public_token: str) -> dict:
        """Exchange public token for access token (Plaid flow)."""
        pass

    @abstractmethod
    def accounts(self, access_token: str) -> list[dict]:
        """Fetch accounts for an access token."""
        pass

    @abstractmethod
    def transactions(
        self, access_token: str, *, start_date: str | None = None, end_date: str | None = None
    ) -> list[dict]:
        """Fetch transactions for an access token within optional date range."""
        pass

    @abstractmethod
    def balances(self, access_token: str, account_id: str | None = None) -> dict:
        """Fetch current balances for all accounts or specific account."""
        pass

    @abstractmethod
    def identity(self, access_token: str) -> dict:
        """Fetch identity/account holder information."""
        pass


class BrokerageProvider(ABC):
    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        type_: str,
        time_in_force: str,
        limit_price: float | None = None,
        stop_price: float | None = None,
        client_order_id: str | None = None,
    ) -> dict:
        pass

    @abstractmethod
    def positions(self) -> Iterable[dict]:
        pass

    @abstractmethod
    def get_account(self) -> dict:
        """Get trading account information."""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> dict:
        """Get position for a specific symbol."""
        pass

    @abstractmethod
    def close_position(self, symbol: str) -> dict:
        """Close a position (market sell/cover)."""
        pass

    @abstractmethod
    def list_orders(self, status: str = "open", limit: int = 50) -> list[dict]:
        """List orders."""
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> dict:
        """Get order by ID."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> None:
        """Cancel an order."""
        pass

    @abstractmethod
    def get_portfolio_history(self, period: str = "1M", timeframe: str = "1D") -> dict:
        """Get portfolio value history."""
        pass

    @abstractmethod
    def create_watchlist(self, name: str, symbols: list[str] | None = None) -> dict:
        """Create a new watchlist."""
        pass

    @abstractmethod
    def list_watchlists(self) -> list[dict]:
        """List all watchlists."""
        pass

    @abstractmethod
    def get_watchlist(self, watchlist_id: str) -> dict:
        """Get a watchlist by ID."""
        pass

    @abstractmethod
    def delete_watchlist(self, watchlist_id: str) -> None:
        """Delete a watchlist."""
        pass

    @abstractmethod
    def add_to_watchlist(self, watchlist_id: str, symbol: str) -> dict:
        """Add a symbol to a watchlist."""
        pass

    @abstractmethod
    def remove_from_watchlist(self, watchlist_id: str, symbol: str) -> dict:
        """Remove a symbol from a watchlist."""
        pass


class IdentityProvider(ABC):
    @abstractmethod
    def create_verification_session(self, **kwargs) -> dict:
        pass

    @abstractmethod
    def get_verification_session(self, session_id: str) -> dict:
        pass


class CreditProvider(ABC):
    @abstractmethod
    def get_credit_score(self, user_id: str, **kwargs: Any) -> Any:
        pass

    @abstractmethod
    def get_credit_report(self, user_id: str, **kwargs: Any) -> Any:
        """Retrieve full credit report for a user."""
        pass


class TaxProvider(ABC):
    """Provider for tax data and document retrieval."""

    @abstractmethod
    def get_tax_forms(self, user_id: str, tax_year: int, **kwargs: Any) -> Any:
        """Retrieve tax forms for a user and tax year."""
        pass

    @abstractmethod
    def get_tax_documents(self, user_id: str, tax_year: int, **kwargs: Any) -> Any:
        """Retrieve tax documents for a user and tax year."""
        pass

    @abstractmethod
    def get_tax_document(self, document_id: str, **kwargs: Any) -> Any:
        """Retrieve a specific tax document by ID."""
        pass

    @abstractmethod
    def calculate_crypto_gains(self, *args: Any, **kwargs: Any) -> Any:
        """Calculate capital gains from crypto transactions."""
        pass

    @abstractmethod
    def calculate_tax_liability(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Calculate estimated tax liability."""
        pass


class InvestmentProvider(ABC):
    """Provider for investment holdings and portfolio data (Plaid, SnapTrade).

    This is a minimal ABC for type checking. The full implementation with
    all abstract methods is in fin_infra.investments.providers.base.InvestmentProvider.

    Abstract Methods (defined in full implementation):
        - get_holdings(access_token, account_ids) -> List[Holding]
        - get_transactions(access_token, start_date, end_date, account_ids) -> List[InvestmentTransaction]
        - get_securities(access_token, security_ids) -> List[Security]
        - get_investment_accounts(access_token) -> List[InvestmentAccount]

    Example:
        >>> from fin_infra.investments import easy_investments
        >>> provider = easy_investments(provider="plaid")
        >>> holdings = await provider.get_holdings(access_token)
    """

    @abstractmethod
    async def get_holdings(self, access_token: str, account_ids: list[str] | None = None) -> list:
        """Fetch holdings for investment accounts."""
        pass

    @abstractmethod
    async def get_investment_accounts(self, access_token: str) -> list:
        """Fetch investment accounts with aggregated holdings."""
        pass
