from __future__ import annotations

from ..base import CreditProvider


class ExperianCredit(CreditProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def get_credit_score(
        self, user_id: str, **kwargs
    ) -> dict | None:  # pragma: no cover - placeholder
        return None
