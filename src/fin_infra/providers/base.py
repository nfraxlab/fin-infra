from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Sequence

from ..models import Quote, Candle


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
    def ticker(self, symbol_pair: str) -> Quote:
        pass

    @abstractmethod
    def ohlcv(self, symbol_pair: str, timeframe: str = "1d", limit: int = 100) -> Sequence[Candle]:
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
        self, symbol: str, qty: float, side: str, type_: str, time_in_force: str
    ) -> dict:
        pass

    @abstractmethod
    def positions(self) -> Iterable[dict]:
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
    def get_credit_score(self, user_id: str, **kwargs) -> dict | None:
        pass


class TaxProvider(ABC):
    """Provider for tax data and document retrieval."""

    @abstractmethod
    def get_tax_forms(self, user_id: str, tax_year: int, **kwargs) -> list[dict]:
        """Retrieve tax forms for a user and tax year."""
        pass

    @abstractmethod
    def get_tax_document(self, document_id: str, **kwargs) -> dict:
        """Retrieve a specific tax document by ID."""
        pass

    @abstractmethod
    def calculate_crypto_gains(self, transactions: list[dict], **kwargs) -> dict:
        """Calculate capital gains from crypto transactions."""
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
