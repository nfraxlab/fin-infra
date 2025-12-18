from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, cast

# Plaid SDK v25+ uses new API structure
try:
    import plaid
    from plaid.api import plaid_api
    from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
    from plaid.model.accounts_get_request import AccountsGetRequest
    from plaid.model.country_code import CountryCode
    from plaid.model.identity_get_request import IdentityGetRequest
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.transactions_get_request import TransactionsGetRequest

    PLAID_AVAILABLE = True
except Exception:  # pragma: no cover - dynamic import guard
    PLAID_AVAILABLE = False

from ...settings import Settings
from ..base import BankingProvider


class PlaidClient(BankingProvider):
    def __init__(
        self,
        settings: Settings | None = None,
        client_id: str | None = None,
        secret: str | None = None,
        environment: str | None = None,
    ) -> None:
        """Initialize Plaid client with either Settings object or individual parameters.

        Args:
            settings: Settings object (legacy pattern)
            client_id: Plaid client ID (preferred - from env or passed directly)
            secret: Plaid secret (preferred - from env or passed directly)
            environment: Plaid environment - sandbox, development, or production
        """
        if not PLAID_AVAILABLE:
            raise RuntimeError(
                "plaid-python SDK not available or import failed; check installed version (requires v25+)"
            )

        # Support both patterns: Settings object or individual params
        if settings is not None:
            # Legacy pattern with Settings object
            client_id = client_id or settings.plaid_client_id
            secret = secret or settings.plaid_secret
            environment = environment or settings.plaid_env

        # Map environment string to Plaid Environment enum
        # Note: Plaid only has Sandbox and Production (no Development in SDK)
        env_str = environment or "sandbox"
        env_map = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Sandbox,  # Map development to sandbox (Plaid SDK limitation)
            "production": plaid.Environment.Production,
        }

        if env_str not in env_map:
            raise ValueError(
                f"Invalid Plaid environment: '{env_str}'. "
                f"Must be one of: sandbox, development, production"
            )

        host = env_map[env_str]

        # Configure Plaid client (v8.0.0+ API)
        configuration = plaid.Configuration(
            host=host,
            api_key={
                "clientId": client_id,
                "secret": secret,
            },
        )
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)

    def create_link_token(self, user_id: str) -> str:
        request = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(client_user_id=user_id),
            client_name="fin-infra",
            products=[
                Products("auth"),  # Account/routing numbers for ACH
                Products("transactions"),  # Transaction history
                Products("liabilities"),  # Credit cards, loans, student loans
                Products("investments"),  # Brokerage, retirement accounts
                Products("assets"),  # Asset reports for lending/verification
                Products("identity"),  # Account holder info (name, email, phone)
            ],
            country_codes=[CountryCode("US")],
            language="en",
        )
        response = self.client.link_token_create(request)
        return cast("str", response["link_token"])

    def exchange_public_token(self, public_token: str) -> dict:
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = self.client.item_public_token_exchange(request)
        return {
            "access_token": response["access_token"],
            "item_id": response["item_id"],
        }

    def accounts(self, access_token: str) -> list[dict]:
        request = AccountsGetRequest(access_token=access_token)
        response = self.client.accounts_get(request)
        return [acc.to_dict() for acc in response["accounts"]]

    def transactions(
        self, access_token: str, *, start_date: str | None = None, end_date: str | None = None
    ) -> list[dict]:
        """Fetch transactions for an access token within optional date range."""
        # Default to last 30 days if not specified
        if not start_date or not end_date:
            end = datetime.now().date()
            start = end - timedelta(days=30)
            start_date = start_date or start.isoformat()
            end_date = end_date or end.isoformat()

        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
        )
        response = self.client.transactions_get(request)
        return [txn.to_dict() for txn in response["transactions"]]

    def balances(self, access_token: str, account_id: str | None = None) -> dict:
        """Fetch current balances for all accounts or specific account."""
        request = AccountsBalanceGetRequest(access_token=access_token)
        response = self.client.accounts_balance_get(request)
        accounts = [acc.to_dict() for acc in response["accounts"]]

        if account_id:
            # Filter to specific account
            for account in accounts:
                if account.get("account_id") == account_id:
                    return {"balances": [account.get("balances", {})]}
            return {"balances": []}

        # Return all balances
        return {"balances": [acc.get("balances", {}) for acc in accounts]}

    def identity(self, access_token: str) -> dict[Any, Any]:
        """Fetch identity/account holder information."""
        request = IdentityGetRequest(access_token=access_token)
        response = self.client.identity_get(request)
        return cast("dict[Any, Any]", response.to_dict())
