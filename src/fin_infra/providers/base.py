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
