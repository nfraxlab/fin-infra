"""Plaid Investment API provider implementation.

Provides read-only access to investment holdings, transactions, and securities data
from 15,000+ financial institutions via the Plaid Investment API.

Best for: Traditional investment accounts (401k, IRA, bank brokerage accounts).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast

try:
    import plaid
    from plaid.api import plaid_api
    from plaid.api_client import ApiClient
    from plaid.configuration import Configuration
    from plaid.exceptions import ApiException
    from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
    from plaid.model.investments_holdings_get_response import InvestmentsHoldingsGetResponse
    from plaid.model.investments_transactions_get_request import (
        InvestmentsTransactionsGetRequest,
    )
    from plaid.model.investments_transactions_get_response import (
        InvestmentsTransactionsGetResponse,
    )

    HAS_PLAID = True
except ImportError:  # pragma: no cover
    HAS_PLAID = False
    plaid_api = None
    plaid = None
    ApiClient = None
    Configuration = None
    ApiException = Exception
    InvestmentsHoldingsGetRequest = Any
    InvestmentsTransactionsGetRequest = Any
    InvestmentsHoldingsGetResponse = Any
    InvestmentsTransactionsGetResponse = Any

from ..models import (
    Holding,
    InvestmentAccount,
    InvestmentTransaction,
    Security,
    TransactionType,
)
from .base import InvestmentProvider


def _require_plaid() -> None:
    """Raise ImportError if plaid-python is not installed."""
    if not HAS_PLAID:
        raise ImportError(
            "Plaid support requires the 'plaid-python' package. "
            "Install with: pip install fin-infra[plaid] or pip install fin-infra[banking]"
        )


class PlaidInvestmentProvider(InvestmentProvider):
    """Plaid Investment API provider.

    Provides read-only access to investment holdings, transactions, and securities
    from bank-connected investment accounts (401k, IRA, brokerage).

    Coverage:
        - 15,000+ financial institutions
        - Traditional investment accounts (401k, IRA, bank brokerage)
        - Daily updates (some institutions support real-time)

    Rate Limits:
        - Development: 100 requests per minute
        - Production: 600 requests per minute
        - Holdings endpoint: Daily refresh recommended
        - Transactions endpoint: Paginated, use start_date/end_date to limit

    Example:
        >>> from fin_infra.investments import easy_investments
        >>> provider = easy_investments(provider="plaid")
        >>> holdings = await provider.get_holdings(access_token)
        >>> for holding in holdings:
        ...     print(f"{holding.security.ticker_symbol}: {holding.quantity} @ ${holding.institution_price}")
    """

    def __init__(
        self,
        client_id: str,
        secret: str,
        environment: str = "sandbox",
    ):
        """Initialize Plaid Investment provider.

        Args:
            client_id: Plaid client ID
            secret: Plaid secret key
            environment: Plaid environment ('sandbox', 'development', 'production')

        Raises:
            ValueError: If client_id or secret is missing
            ImportError: If plaid-python is not installed
        """
        _require_plaid()

        if not client_id or not secret:
            raise ValueError("client_id and secret are required for Plaid provider")

        self.client_id = client_id
        self.secret = secret
        self.environment = environment

        # Configure Plaid client
        configuration = Configuration(
            host=self._get_plaid_host(environment),
            api_key={
                "clientId": client_id,
                "secret": secret,
            },
        )
        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

    def _get_plaid_host(self, environment: str) -> str:
        """Get Plaid API host for environment."""
        hosts = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Sandbox,  # Map development to sandbox
            "production": plaid.Environment.Production,
        }
        return cast("str", hosts.get(environment.lower(), plaid.Environment.Sandbox))

    async def get_holdings(
        self, access_token: str, account_ids: list[str] | None = None
    ) -> list[Holding]:
        """Fetch investment holdings from Plaid.

        Retrieves holdings with security details, quantity, cost basis, and current value.

        Args:
            access_token: Plaid access token for the user
            account_ids: Optional filter for specific investment accounts

        Returns:
            List of holdings with security details and P&L calculations

        Raises:
            ApiException: If Plaid API call fails
            ValueError: If access_token is invalid

        Example:
            >>> holdings = await provider.get_holdings(access_token)
            >>> for holding in holdings:
            ...     pnl = holding.unrealized_gain_loss
            ...     print(f"{holding.security.ticker_symbol}: P&L ${pnl}")
        """
        try:
            request = InvestmentsHoldingsGetRequest(
                access_token=access_token,
            )
            if account_ids:
                request.options = {"account_ids": account_ids}

            response: InvestmentsHoldingsGetResponse = self.client.investments_holdings_get(request)

            # Build security lookup map
            securities_map = {
                sec.security_id: self._transform_security(sec.to_dict())
                for sec in response.securities
            }

            # Transform holdings
            holdings = []
            for plaid_holding in response.holdings:
                holding_dict = plaid_holding.to_dict()
                security = securities_map.get(holding_dict["security_id"])

                if security:
                    holding = self._transform_holding(holding_dict, security)
                    holdings.append(holding)

            return holdings

        except ApiException as e:
            raise self._transform_error(e)

    async def get_transactions(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        account_ids: list[str] | None = None,
    ) -> list[InvestmentTransaction]:
        """Fetch investment transactions from Plaid.

        Retrieves buy/sell/dividend transactions within the specified date range.

        Args:
            access_token: Plaid access token for the user
            start_date: Start date for transaction history
            end_date: End date for transaction history
            account_ids: Optional filter for specific investment accounts

        Returns:
            List of investment transactions

        Raises:
            ApiException: If Plaid API call fails
            ValueError: If date range is invalid

        Example:
            >>> from datetime import date, timedelta
            >>> end = date.today()
            >>> start = end - timedelta(days=30)
            >>> transactions = await provider.get_transactions(access_token, start, end)
            >>> buys = [tx for tx in transactions if tx.transaction_type == TransactionType.buy]
        """
        if start_date > end_date:
            raise ValueError("start_date must be before end_date")

        try:
            request = InvestmentsTransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
            )
            if account_ids:
                request.options = {"account_ids": account_ids}

            response: InvestmentsTransactionsGetResponse = self.client.investments_transactions_get(
                request
            )

            # Build security lookup map
            securities_map = {
                sec.security_id: self._transform_security(sec.to_dict())
                for sec in response.securities
            }

            # Transform transactions
            transactions = []
            for plaid_tx in response.investment_transactions:
                tx_dict = plaid_tx.to_dict()
                security = securities_map.get(tx_dict.get("security_id"))

                if security:
                    transaction = self._transform_transaction(tx_dict, security)
                    transactions.append(transaction)

            return transactions

        except ApiException as e:
            raise self._transform_error(e)

    async def get_securities(self, access_token: str, security_ids: list[str]) -> list[Security]:
        """Fetch security details from Plaid holdings.

        Note: Plaid doesn't have a dedicated securities endpoint.
        This method fetches holdings and extracts unique securities.

        Args:
            access_token: Plaid access token for the user
            security_ids: List of security IDs to fetch (Plaid security_id values)

        Returns:
            List of security details

        Raises:
            ApiException: If Plaid API call fails

        Example:
            >>> securities = await provider.get_securities(access_token, ["sec_123", "sec_456"])
            >>> for security in securities:
            ...     print(f"{security.ticker_symbol}: ${security.close_price}")
        """
        try:
            request = InvestmentsHoldingsGetRequest(access_token=access_token)
            response: InvestmentsHoldingsGetResponse = self.client.investments_holdings_get(request)

            # Filter securities by requested IDs
            securities = []
            for plaid_sec in response.securities:
                sec_dict = plaid_sec.to_dict()
                if sec_dict["security_id"] in security_ids:
                    security = self._transform_security(sec_dict)
                    securities.append(security)

            return securities

        except ApiException as e:
            raise self._transform_error(e)

    async def get_investment_accounts(self, access_token: str) -> list[InvestmentAccount]:
        """Fetch investment accounts with aggregated holdings.

        Returns accounts with total value, cost basis, and unrealized P&L.

        Args:
            access_token: Plaid access token for the user

        Returns:
            List of investment accounts with holdings and computed metrics

        Raises:
            ApiException: If Plaid API call fails

        Example:
            >>> accounts = await provider.get_investment_accounts(access_token)
            >>> for account in accounts:
            ...     print(f"{account.name}: ${account.total_value}")
            ...     print(f"  P&L: {account.total_unrealized_gain_loss_percent:.2f}%")
        """
        try:
            request = InvestmentsHoldingsGetRequest(access_token=access_token)
            response: InvestmentsHoldingsGetResponse = self.client.investments_holdings_get(request)

            # Build security lookup map
            securities_map = {
                sec.security_id: self._transform_security(sec.to_dict())
                for sec in response.securities
            }

            # Group holdings by account
            accounts_map: dict[str, dict[str, Any]] = {}
            for plaid_holding in response.holdings:
                holding_dict = plaid_holding.to_dict()
                account_id = holding_dict["account_id"]
                security = securities_map.get(holding_dict["security_id"])

                if security:
                    holding = self._transform_holding(holding_dict, security)

                    if account_id not in accounts_map:
                        # Find account metadata
                        plaid_account = next(
                            (acc for acc in response.accounts if acc.account_id == account_id),
                            None,
                        )
                        accounts_map[account_id] = {
                            "account": plaid_account.to_dict() if plaid_account else {},
                            "holdings": [],
                        }

                    accounts_map[account_id]["holdings"].append(holding)

            # Transform to InvestmentAccount models
            investment_accounts = []
            for account_id, data in accounts_map.items():
                account_dict = data["account"]
                holdings = data["holdings"]

                investment_account = InvestmentAccount(
                    account_id=account_id,
                    name=account_dict.get(
                        "name", account_dict.get("official_name", "Unknown Account")
                    ),
                    type=account_dict.get("type", "investment"),
                    subtype=account_dict.get("subtype"),
                    balances={
                        "current": Decimal(str(account_dict.get("balances", {}).get("current", 0))),
                        "available": Decimal(
                            str(account_dict.get("balances", {}).get("available") or 0)
                        ),
                    },
                    holdings=holdings,
                )
                investment_accounts.append(investment_account)

            return investment_accounts

        except ApiException as e:
            raise self._transform_error(e)

    # Helper methods for data transformation

    def _transform_security(self, plaid_security: dict[str, Any]) -> Security:
        """Transform Plaid security data to Security model."""
        # Handle close_price - Plaid may return None for securities without recent pricing
        close_price_raw = plaid_security.get("close_price")
        close_price = Decimal(str(close_price_raw)) if close_price_raw is not None else Decimal("0")

        return Security(
            security_id=plaid_security["security_id"],
            cusip=plaid_security.get("cusip"),
            isin=plaid_security.get("isin"),
            sedol=plaid_security.get("sedol"),
            ticker_symbol=plaid_security.get("ticker_symbol"),
            name=plaid_security.get("name") or "Unknown Security",
            type=self._normalize_security_type(plaid_security.get("type", "other")),
            sector=plaid_security.get("sector"),
            close_price=close_price,
            close_price_as_of=plaid_security.get("close_price_as_of"),
            exchange=plaid_security.get("market_identifier_code"),
            currency=plaid_security.get("iso_currency_code", "USD"),
        )

    def _transform_holding(self, plaid_holding: dict[str, Any], security: Security) -> Holding:
        """Transform Plaid holding data to Holding model."""
        return Holding(
            account_id=plaid_holding["account_id"],
            security=security,
            quantity=Decimal(str(plaid_holding.get("quantity", 0))),
            institution_price=Decimal(str(plaid_holding.get("institution_price", 0))),
            institution_value=Decimal(str(plaid_holding.get("institution_value", 0))),
            cost_basis=Decimal(str(plaid_holding.get("cost_basis")))
            if plaid_holding.get("cost_basis")
            else None,
            currency=plaid_holding.get("iso_currency_code", "USD"),
            unofficial_currency_code=plaid_holding.get("unofficial_currency_code"),
        )

    def _transform_transaction(
        self, plaid_transaction: dict[str, Any], security: Security
    ) -> InvestmentTransaction:
        """Transform Plaid investment transaction to InvestmentTransaction model."""
        # Map Plaid transaction type to our enum
        plaid_type = plaid_transaction.get("type", "other")
        transaction_type = self._normalize_transaction_type(plaid_type)

        # Handle date field - Plaid SDK's to_dict() converts it to a date object
        transaction_date_value = plaid_transaction["date"]
        if isinstance(transaction_date_value, date):
            transaction_date = transaction_date_value
        else:
            transaction_date = date.fromisoformat(transaction_date_value)

        return InvestmentTransaction(
            transaction_id=plaid_transaction["investment_transaction_id"],
            account_id=plaid_transaction["account_id"],
            security=security,
            transaction_date=transaction_date,
            name=plaid_transaction.get("name", ""),
            transaction_type=transaction_type,
            subtype=plaid_transaction.get("subtype"),
            quantity=Decimal(str(plaid_transaction.get("quantity", 0))),
            amount=Decimal(str(plaid_transaction.get("amount", 0))),
            price=Decimal(str(plaid_transaction.get("price", 0))),
            fees=Decimal(str(plaid_transaction.get("fees", 0))),
            currency=plaid_transaction.get("iso_currency_code", "USD"),
            unofficial_currency_code=plaid_transaction.get("unofficial_currency_code"),
        )

    def _normalize_transaction_type(self, plaid_type: str) -> TransactionType:
        """Map Plaid transaction types to TransactionType enum."""
        mapping = {
            "buy": TransactionType.buy,
            "sell": TransactionType.sell,
            "dividend": TransactionType.dividend,
            "interest": TransactionType.interest,
            "fee": TransactionType.fee,
            "tax": TransactionType.tax,
            "transfer": TransactionType.transfer,
            "split": TransactionType.split,
            "merger": TransactionType.merger,
            "cancel": TransactionType.cancel,
        }
        return mapping.get(plaid_type.lower(), TransactionType.other)

    def _transform_error(self, error: ApiException) -> Exception:
        """Transform Plaid API exceptions to meaningful errors."""
        error_code = getattr(error, "error_code", None)
        error_message = getattr(error, "display_message", str(error))

        # Map common Plaid errors
        if error_code == "INVALID_ACCESS_TOKEN":
            return ValueError(f"Invalid Plaid access token: {error_message}")
        elif error_code == "ITEM_LOGIN_REQUIRED":
            return ValueError(f"User needs to re-authenticate with bank: {error_message}")
        elif error_code == "PRODUCT_NOT_READY":
            return ValueError(f"Investment data not yet available: {error_message}")
        elif error_code == "RATE_LIMIT_EXCEEDED":
            return ValueError(f"Plaid rate limit exceeded: {error_message}")
        else:
            return Exception(f"Plaid API error: {error_message}")


__all__ = ["PlaidInvestmentProvider"]
