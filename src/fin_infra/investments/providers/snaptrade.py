"""SnapTrade Investment API provider implementation.

Provides read-only access to investment holdings, transactions, and securities data
from 125M+ retail brokerage accounts across 70+ brokerages via the SnapTrade API.

Best for: Retail brokerage accounts (E*TRADE, Wealthsimple, Webull, Robinhood).
Also supports trading operations for most brokerages (see brokerage module).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast

import httpx

from ..models import (
    Holding,
    InvestmentAccount,
    InvestmentTransaction,
    Security,
    TransactionType,
)
from .base import InvestmentProvider


class SnapTradeInvestmentProvider(InvestmentProvider):
    """SnapTrade Investment API provider.

    Provides read-only access to investment holdings, transactions, and securities
    from retail brokerage accounts (E*TRADE, Wealthsimple, Webull, Robinhood, etc.).

    Coverage:
        - 125M+ retail brokerage accounts
        - 70+ brokerages (E*TRADE, Wealthsimple, Questrade, Webull, Trading 212, etc.)
        - Real-time or near real-time data for most brokerages

    Authentication:
        - Uses user_id + user_secret (not access_token like Plaid)
        - Users connect via SnapTrade Connection Portal (OAuth flow)
        - Each user gets unique user_id and user_secret after connection

    Trading Capability:
        - Some brokerages support trading (E*TRADE, Wealthsimple, Webull)
        - Robinhood is READ-ONLY (no developer API, OAuth access only)
        - Use get_brokerage_capabilities() to check per brokerage

    Rate Limits:
        - Free tier: 100 requests per minute
        - Production: Contact SnapTrade for limits
        - Real-time data for most endpoints

    Example:
        >>> from fin_infra.investments import easy_investments
        >>> provider = easy_investments(provider="snaptrade")
        >>> # After user connects via SnapTrade portal, you have user_id/user_secret
        >>> holdings = await provider.get_holdings(user_id, user_secret)
        >>> for holding in holdings:
        ...     print(f"{holding.security.ticker_symbol}: {holding.quantity} @ ${holding.institution_price}")
    """

    def __init__(
        self,
        client_id: str,
        consumer_key: str,
        base_url: str = "https://api.snaptrade.com/api/v1",
    ):
        """Initialize SnapTrade Investment provider.

        Args:
            client_id: SnapTrade client ID
            consumer_key: SnapTrade consumer key (secret)
            base_url: SnapTrade API base URL (default: production)

        Raises:
            ValueError: If client_id or consumer_key is missing
        """
        if not client_id or not consumer_key:
            raise ValueError("client_id and consumer_key are required for SnapTrade provider")

        self.client_id = client_id
        self.consumer_key = consumer_key
        self.base_url = base_url.rstrip("/")

        # Create httpx client for async requests
        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "clientId": client_id,
                "Signature": consumer_key,
            },
            timeout=30.0,
        )

    def _auth_headers(self, user_id: str, user_secret: str) -> dict[str, str]:
        """Build authentication headers for SnapTrade API requests.

        SECURITY: User secrets are passed in headers, NOT URL params.
        URL params are logged in access logs, browser history, and proxy logs.
        Headers are not logged by default in most web servers.

        Args:
            user_id: SnapTrade user ID
            user_secret: SnapTrade user secret (sensitive!)

        Returns:
            Dict with authentication headers
        """
        return {
            "userId": user_id,
            "userSecret": user_secret,
        }

    async def get_holdings(
        self,
        access_token: str,
        account_ids: list[str] | None = None,
    ) -> list[Holding]:
        """Fetch investment holdings from SnapTrade.

        Note: SnapTrade uses user_id + user_secret, passed as access_token in format "user_id:user_secret"

        Args:
            access_token: Combined "user_id:user_secret" string
            account_ids: Optional filter for specific brokerage accounts

        Returns:
            List of holdings with security details and P&L calculations

        Raises:
            ValueError: If access_token format is invalid or API call fails

        Example:
            >>> # access_token format: "user_123:secret_abc"
            >>> holdings = await provider.get_holdings("user_123:secret_abc")
            >>> for holding in holdings:
            ...     pnl = holding.unrealized_gain_loss
            ...     print(f"{holding.security.ticker_symbol}: P&L ${pnl}")
        """
        user_id, user_secret = self._parse_access_token(access_token)
        auth_headers = self._auth_headers(user_id, user_secret)

        try:
            # Get all accounts
            accounts_url = f"{self.base_url}/accounts"
            response = await self.client.get(accounts_url, headers=auth_headers)
            response.raise_for_status()
            accounts = await response.json()

            # Filter accounts if specified
            if account_ids:
                accounts = [acc for acc in accounts if acc["id"] in account_ids]

            # Fetch positions for each account
            all_holdings = []
            for account in accounts:
                account_id = account["id"]
                positions_url = f"{self.base_url}/accounts/{account_id}/positions"
                pos_response = await self.client.get(positions_url, headers=auth_headers)
                pos_response.raise_for_status()
                positions = await pos_response.json()

                # Transform each position to Holding
                for position in positions:
                    holding = self._transform_holding(position, account_id)
                    all_holdings.append(holding)

            return all_holdings

        except httpx.HTTPStatusError as e:
            raise self._transform_error(e)
        except Exception as e:
            raise ValueError(f"SnapTrade API error: {e!s}")

    async def get_transactions(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        account_ids: list[str] | None = None,
    ) -> list[InvestmentTransaction]:
        """Fetch investment transactions from SnapTrade.

        Args:
            access_token: Combined "user_id:user_secret" string
            start_date: Start date for transaction history
            end_date: End date for transaction history
            account_ids: Optional filter for specific brokerage accounts

        Returns:
            List of investment transactions

        Raises:
            ValueError: If date range is invalid or API call fails

        Example:
            >>> from datetime import date, timedelta
            >>> end = date.today()
            >>> start = end - timedelta(days=30)
            >>> transactions = await provider.get_transactions("user:secret", start, end)
            >>> buys = [tx for tx in transactions if tx.transaction_type == TransactionType.buy]
        """
        if start_date > end_date:
            raise ValueError("start_date must be before end_date")

        user_id, user_secret = self._parse_access_token(access_token)
        auth_headers = self._auth_headers(user_id, user_secret)

        try:
            # Get all accounts
            accounts_url = f"{self.base_url}/accounts"
            response = await self.client.get(accounts_url, headers=auth_headers)
            response.raise_for_status()
            accounts = await response.json()

            # Filter accounts if specified
            if account_ids:
                accounts = [acc for acc in accounts if acc["id"] in account_ids]

            # Fetch transactions for each account
            all_transactions = []
            for account in accounts:
                account_id = account["id"]
                transactions_url = f"{self.base_url}/accounts/{account_id}/transactions"
                # Date params are non-sensitive, only auth goes in headers
                tx_params = {
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                }
                tx_response = await self.client.get(
                    transactions_url, params=tx_params, headers=auth_headers
                )
                tx_response.raise_for_status()
                transactions = await tx_response.json()

                # Transform each transaction
                for transaction in transactions:
                    inv_tx = self._transform_transaction(transaction, account_id)
                    all_transactions.append(inv_tx)

            return all_transactions

        except httpx.HTTPStatusError as e:
            raise self._transform_error(e)
        except Exception as e:
            raise ValueError(f"SnapTrade API error: {e!s}")

    async def get_securities(self, access_token: str, security_ids: list[str]) -> list[Security]:
        """Fetch security details from SnapTrade positions.

        Note: SnapTrade doesn't have a dedicated securities endpoint.
        This method fetches positions and extracts unique securities.

        Args:
            access_token: Combined "user_id:user_secret" string
            security_ids: List of security symbols to fetch (ticker symbols)

        Returns:
            List of security details

        Raises:
            ValueError: If API call fails

        Example:
            >>> securities = await provider.get_securities("user:secret", ["AAPL", "GOOGL"])
            >>> for security in securities:
            ...     print(f"{security.ticker_symbol}: ${security.close_price}")
        """
        _user_id, _user_secret = self._parse_access_token(access_token)

        try:
            # Get all holdings to extract securities
            holdings = await self.get_holdings(access_token)

            # Extract unique securities matching requested symbols
            securities_map = {}
            for holding in holdings:
                if holding.security.ticker_symbol in security_ids:
                    securities_map[holding.security.ticker_symbol] = holding.security

            return list(securities_map.values())

        except Exception as e:
            raise ValueError(f"SnapTrade API error: {e!s}")

    async def get_investment_accounts(self, access_token: str) -> list[InvestmentAccount]:
        """Fetch investment accounts with aggregated holdings.

        Returns accounts with total value, cost basis, and unrealized P&L.

        Args:
            access_token: Combined "user_id:user_secret" string

        Returns:
            List of investment accounts with holdings and computed metrics

        Raises:
            ValueError: If API call fails

        Example:
            >>> accounts = await provider.get_investment_accounts("user:secret")
            >>> for account in accounts:
            ...     print(f"{account.name}: ${account.total_value}")
            ...     print(f"  P&L: {account.total_unrealized_gain_loss_percent:.2f}%")
        """
        user_id, user_secret = self._parse_access_token(access_token)
        auth_headers = self._auth_headers(user_id, user_secret)

        try:
            # Get all accounts
            accounts_url = f"{self.base_url}/accounts"
            response = await self.client.get(accounts_url, headers=auth_headers)
            response.raise_for_status()
            accounts = await response.json()

            # Fetch holdings for each account
            investment_accounts = []
            for account in accounts:
                account_id = account["id"]

                # Get positions for this account
                positions_url = f"{self.base_url}/accounts/{account_id}/positions"
                pos_response = await self.client.get(positions_url, headers=auth_headers)
                pos_response.raise_for_status()
                positions = await pos_response.json()

                # Transform positions to holdings
                holdings = []
                for position in positions:
                    holding = self._transform_holding(position, account_id)
                    holdings.append(holding)

                # Get account balances
                balances_url = f"{self.base_url}/accounts/{account_id}/balances"
                bal_response = await self.client.get(balances_url, headers=auth_headers)
                bal_response.raise_for_status()
                balances = await bal_response.json()

                # Create InvestmentAccount
                investment_account = InvestmentAccount(
                    account_id=account_id,
                    name=account.get("name", account.get("brokerage_name", "Unknown")),
                    type=account.get("type", "investment"),
                    subtype=account.get("account_type"),
                    balances={
                        "current": Decimal(str(balances.get("total", {}).get("amount", 0))),
                        "available": Decimal(str(balances.get("cash", {}).get("amount", 0))),
                    },
                    holdings=holdings,
                )
                investment_accounts.append(investment_account)

            return investment_accounts

        except httpx.HTTPStatusError as e:
            raise self._transform_error(e)
        except Exception as e:
            raise ValueError(f"SnapTrade API error: {e!s}")

    async def list_connections(self, access_token: str) -> list[dict[str, Any]]:
        """List brokerage connections for a user.

        Returns which brokerages the user has connected (E*TRADE, Robinhood, etc.).

        Args:
            access_token: Combined "user_id:user_secret" string

        Returns:
            List of connection dicts with brokerage info

        Example:
            >>> connections = await provider.list_connections("user:secret")
            >>> for conn in connections:
            ...     print(f"Connected: {conn['brokerage_name']}")
        """
        user_id, user_secret = self._parse_access_token(access_token)
        auth_headers = self._auth_headers(user_id, user_secret)

        try:
            url = f"{self.base_url}/connections"
            response = await self.client.get(url, headers=auth_headers)
            response.raise_for_status()
            return cast("list[dict[str, Any]]", await response.json())

        except httpx.HTTPStatusError as e:
            raise self._transform_error(e)
        except Exception as e:
            raise ValueError(f"SnapTrade API error: {e!s}")

    def get_brokerage_capabilities(self, brokerage_name: str) -> dict[str, Any]:
        """Get capabilities for a specific brokerage.

        Important: Robinhood is READ-ONLY (no trading support).
        Most other brokerages support trading operations.

        Args:
            brokerage_name: Name of brokerage (e.g., "Robinhood", "E*TRADE")

        Returns:
            Dict with capabilities:
                - supports_trading (bool): Whether trading is supported
                - supports_options (bool): Whether options trading is supported
                - connection_type (str): "oauth" or "credentials"
                - read_only (bool): Whether account is read-only

        Example:
            >>> caps = provider.get_brokerage_capabilities("Robinhood")
            >>> if not caps["supports_trading"]:
            ...     print("Robinhood is read-only, no trading available")
        """
        # Known brokerage capabilities
        # Source: SnapTrade documentation and API limitations
        capabilities = {
            "Robinhood": {
                "supports_trading": False,  # No developer API
                "supports_options": False,
                "connection_type": "oauth",
                "read_only": True,
            },
            "E*TRADE": {
                "supports_trading": True,
                "supports_options": True,
                "connection_type": "oauth",
                "read_only": False,
            },
            "Wealthsimple": {
                "supports_trading": True,
                "supports_options": False,
                "connection_type": "oauth",
                "read_only": False,
            },
            "Questrade": {
                "supports_trading": True,
                "supports_options": True,
                "connection_type": "oauth",
                "read_only": False,
            },
            "Webull": {
                "supports_trading": True,
                "supports_options": True,
                "connection_type": "credentials",
                "read_only": False,
            },
            "Trading 212": {
                "supports_trading": True,
                "supports_options": False,
                "connection_type": "credentials",
                "read_only": False,
            },
        }

        # Default capabilities for unknown brokerages
        default = {
            "supports_trading": True,  # Most brokerages support trading
            "supports_options": False,
            "connection_type": "oauth",
            "read_only": False,
        }

        return capabilities.get(brokerage_name, default)

    # Helper methods for data transformation

    def _parse_access_token(self, access_token: str) -> tuple[str, str]:
        """Parse combined access_token into user_id and user_secret.

        Args:
            access_token: Combined "user_id:user_secret" string

        Returns:
            Tuple of (user_id, user_secret)

        Raises:
            ValueError: If format is invalid
        """
        try:
            user_id, user_secret = access_token.split(":", 1)
            return user_id, user_secret
        except ValueError:
            raise ValueError("Invalid access_token format. Expected 'user_id:user_secret'")

    def _transform_holding(self, snaptrade_position: dict[str, Any], account_id: str) -> Holding:
        """Transform SnapTrade position data to Holding model."""
        symbol_data = snaptrade_position.get("symbol", {})

        # Create Security from symbol data
        security = Security(
            security_id=symbol_data.get("id", symbol_data.get("symbol", "")),
            ticker_symbol=symbol_data.get("symbol"),
            name=symbol_data.get("description", symbol_data.get("symbol")),
            type=self._normalize_security_type(symbol_data.get("type", "other")),
            close_price=Decimal(str(snaptrade_position.get("price", 0))),
            currency=snaptrade_position.get("currency", "USD"),
        )

        # SnapTrade uses "average_purchase_price" for cost basis
        avg_price = snaptrade_position.get("average_purchase_price")
        quantity = Decimal(str(snaptrade_position.get("units", 0)))
        cost_basis = Decimal(str(avg_price)) * quantity if avg_price is not None else None

        return Holding(
            account_id=account_id,
            security=security,
            quantity=quantity,
            institution_price=Decimal(str(snaptrade_position.get("price", 0))),
            institution_value=Decimal(str(snaptrade_position.get("value", 0))),
            cost_basis=cost_basis,
            currency=snaptrade_position.get("currency", "USD"),
        )

    def _transform_transaction(
        self, snaptrade_tx: dict[str, Any], account_id: str
    ) -> InvestmentTransaction:
        """Transform SnapTrade transaction to InvestmentTransaction model."""
        symbol_data = snaptrade_tx.get("symbol", {})

        # Create Security from symbol data
        security = Security(
            security_id=symbol_data.get("id", symbol_data.get("symbol", "")),
            ticker_symbol=symbol_data.get("symbol"),
            name=symbol_data.get("description", symbol_data.get("symbol")),
            type=self._normalize_security_type(symbol_data.get("type", "other")),
            close_price=Decimal(str(snaptrade_tx.get("price", 0))),
            currency=snaptrade_tx.get("currency", "USD"),
        )

        # Parse transaction type
        tx_type = snaptrade_tx.get("type", "other")
        transaction_type = self._normalize_transaction_type(tx_type)

        return InvestmentTransaction(
            transaction_id=snaptrade_tx.get("id", ""),
            account_id=account_id,
            security=security,
            transaction_date=date.fromisoformat(snaptrade_tx["date"]),
            name=snaptrade_tx.get("description", ""),
            transaction_type=transaction_type,
            quantity=Decimal(str(snaptrade_tx.get("units", 0))),
            amount=Decimal(str(snaptrade_tx.get("amount", 0))),
            price=Decimal(str(snaptrade_tx.get("price", 0))),
            fees=Decimal(str(snaptrade_tx.get("fee", 0))),
            currency=snaptrade_tx.get("currency", "USD"),
        )

    def _normalize_transaction_type(self, snaptrade_type: str) -> TransactionType:
        """Map SnapTrade transaction types to TransactionType enum."""
        mapping = {
            "buy": TransactionType.buy,
            "sell": TransactionType.sell,
            "dividend": TransactionType.dividend,
            "interest": TransactionType.interest,
            "fee": TransactionType.fee,
            "tax": TransactionType.tax,
            "deposit": TransactionType.transfer,
            "withdrawal": TransactionType.transfer,
            "split": TransactionType.split,
            "merger": TransactionType.merger,
            "cancel": TransactionType.cancel,
        }
        return mapping.get(snaptrade_type.lower(), TransactionType.other)

    def _transform_error(self, error: httpx.HTTPStatusError) -> Exception:
        """Transform SnapTrade HTTP errors to meaningful exceptions."""
        status_code = error.response.status_code
        error_message = error.response.text

        try:
            error_data = error.response.json()
            error_message = error_data.get("message", error_message)
        except Exception:
            pass  # Use text if JSON parsing fails

        # Map common HTTP status codes
        if status_code == 401:
            return ValueError(f"Invalid SnapTrade credentials: {error_message}")
        elif status_code == 403:
            return ValueError(f"Access forbidden: {error_message}")
        elif status_code == 404:
            return ValueError(f"Resource not found: {error_message}")
        elif status_code == 429:
            return ValueError(f"SnapTrade rate limit exceeded: {error_message}")
        else:
            return Exception(f"SnapTrade API error ({status_code}): {error_message}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup httpx client."""
        await self.client.aclose()


__all__ = ["SnapTradeInvestmentProvider"]
