from __future__ import annotations

from typing import Sequence

from .base import BankingClient
from ..models import Account


class PlaidClient(BankingClient):
    """Placeholder Plaid client. Real implementation will require plaid-python.

    This skeleton exists to define the surface and allow tests/imports to pass
    without pulling optional dependencies.
    """

    def __init__(self, *, client_id: str | None = None, secret: str | None = None):
        self._client_id = client_id
        self._secret = secret

    async def get_accounts(self, user_id: str) -> Sequence[Account]:  # pragma: no cover - stub
        return []

    async def get_transactions(
        self, account_id: str, *, start: str | None = None, end: str | None = None
    ):  # pragma: no cover - stub
        return []
