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
    from plaid.model.item_remove_request import ItemRemoveRequest
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
        client_name: str | None = None,
    ) -> None:
        """Initialize Plaid client with either Settings object or individual parameters.

        Args:
            settings: Settings object (legacy pattern)
            client_id: Plaid client ID (preferred - from env or passed directly)
            secret: Plaid secret (preferred - from env or passed directly)
            environment: Plaid environment - sandbox, development, or production
            client_name: App name displayed in Plaid Link consent pane (default: "fin-infra")
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
            self._products = settings.plaid_products
            self._client_name = client_name or settings.plaid_client_name
        else:
            # Use default products when no settings object provided
            from ...settings import DEFAULT_PLAID_PRODUCTS

            self._products = DEFAULT_PLAID_PRODUCTS
            self._client_name = client_name or "fin-infra"

        # Map environment string to Plaid SDK host
        # Plaid retired the development.plaid.com hostname and merged
        # Development into Production (production.plaid.com).
        # Development keys are accepted by the Production host.
        env_str = environment or "sandbox"
        env_map: dict[str, str] = {
            "sandbox": plaid.Environment.Sandbox,
            "development": plaid.Environment.Production,
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

    def create_link_token(self, user_id: str, access_token: str | None = None) -> str:
        """Create a Plaid Link token for new connections or re-authentication.

        Args:
            user_id: Client-defined user ID for the Link session
            access_token: If provided, creates Link in update mode for re-authentication
                         (used when ITEM_LOGIN_REQUIRED error occurs)

        Returns:
            Link token string for Plaid Link initialization
        """
        # Build base request parameters
        request_params = {
            "user": LinkTokenCreateRequestUser(client_user_id=user_id),
            "client_name": self._client_name,
            "country_codes": [CountryCode("US")],
            "language": "en",
        }

        if access_token:
            # Update mode: re-authenticate existing connection
            # Don't include products - Plaid uses existing item's products
            request_params["access_token"] = access_token
        else:
            # New connection: specify products from settings
            # Configurable via PLAID_PRODUCTS env var (comma-separated)
            # Default: auth,transactions,investments (excludes costly unused products)
            product_list = [Products(p.strip()) for p in self._products.split(",") if p.strip()]
            request_params["products"] = product_list

        request = LinkTokenCreateRequest(**request_params)
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

    def remove_item(self, access_token: str) -> bool:
        """Remove a Plaid Item, revoking the access token.

        Calls Plaid's /item/remove endpoint which:
        - Invalidates the access_token permanently
        - Stops Plaid from maintaining the connection
        - Stops billing for this Item
        - Fires an ITEM_REMOVED webhook

        Args:
            access_token: The access token of the Item to remove.

        Returns:
            True if the Item was successfully removed.

        Raises:
            ValueError: If the token is invalid or already removed.
        """
        try:
            request = ItemRemoveRequest(access_token=access_token)
            self.client.item_remove(request)
            return True
        except plaid.ApiException as e:
            # ITEM_NOT_FOUND means already removed — treat as success
            if "ITEM_NOT_FOUND" in str(e):
                return True
            raise ValueError(f"Failed to remove Plaid item: {e}") from e
