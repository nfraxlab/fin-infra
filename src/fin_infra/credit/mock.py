"""Mock credit provider for development and testing (v1).

This provider returns hardcoded data for development without requiring
real API credentials. Useful for:
- Local development
- Unit testing
- Demo environments

For production, use the real ExperianProvider from experian/provider.py.

Example:
    >>> from fin_infra.credit.mock import MockExperianProvider
    >>>
    >>> provider = MockExperianProvider()
    >>> score = provider.get_credit_score("user123")
    >>> print(score.score)  # 735 (mock data)
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from fin_infra.models.credit import (
    CreditAccount,
    CreditInquiry,
    CreditReport,
    CreditScore,
)
from fin_infra.providers.base import CreditProvider


class MockExperianProvider(CreditProvider):
    """Mock Experian provider for development (v1).

    Returns hardcoded credit data without making real API calls.
    Useful for local development and unit testing.

    Args:
        api_key: Ignored (no API calls made)
        environment: Ignored (no API calls made)
        **config: Ignored

    Example:
        >>> provider = MockExperianProvider()
        >>> score = provider.get_credit_score("user123")
        >>> print(score.score)  # 735 (mock)
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        environment: Literal["sandbox", "production"] = "sandbox",
        **config,
    ):
        self.api_key = api_key
        self.environment = environment
        self.config = config

    def get_credit_score(self, user_id: str, **kwargs) -> CreditScore:
        """Return mock credit score.

        Args:
            user_id: User identifier
            **kwargs: Ignored

        Returns:
            Mock CreditScore (FICO 8 score 735)
        """
        return CreditScore(
            user_id=user_id,
            score=735,
            score_model="FICO 8",
            bureau="experian",
            score_date=date.today(),
            factors=[
                "Credit card utilization is high (35%)",
                "No recent late payments",
                "Average age of accounts is good (8 years)",
                "Credit mix is diverse",
                "Recent hard inquiry detected",
            ],
            change=15,
        )

    def get_credit_report(self, user_id: str, **kwargs) -> CreditReport:
        """Return mock credit report.

        Args:
            user_id: User identifier
            **kwargs: Ignored

        Returns:
            Mock CreditReport with 3 accounts, 2 inquiries
        """
        score = self.get_credit_score(user_id)

        accounts = [
            CreditAccount(
                account_id="acc_cc_chase",
                account_type="credit_card",
                creditor_name="Chase Bank",
                account_status="open",
                balance=Decimal("3500.00"),
                credit_limit=Decimal("10000.00"),
                payment_status="current",
                opened_date=date(2018, 3, 15),
                last_payment_date=date(2025, 1, 1),
                monthly_payment=Decimal("150.00"),
            ),
            CreditAccount(
                account_id="acc_auto_ford",
                account_type="auto_loan",
                creditor_name="Ford Motor Credit",
                account_status="open",
                balance=Decimal("12000.00"),
                credit_limit=None,
                payment_status="current",
                opened_date=date(2022, 6, 1),
                last_payment_date=date(2025, 1, 1),
                monthly_payment=Decimal("450.00"),
            ),
            CreditAccount(
                account_id="acc_student_navient",
                account_type="student_loan",
                creditor_name="Navient",
                account_status="open",
                balance=Decimal("25000.00"),
                credit_limit=None,
                payment_status="current",
                opened_date=date(2015, 9, 1),
                last_payment_date=date(2025, 1, 1),
                monthly_payment=Decimal("300.00"),
            ),
        ]

        inquiries = [
            CreditInquiry(
                inquiry_id="inq_chase_2025",
                inquiry_type="hard",
                inquirer_name="Chase Bank",
                inquiry_date=date(2025, 1, 1),
                purpose="credit_card_application",
            ),
            CreditInquiry(
                inquiry_id="inq_ford_2024",
                inquiry_type="hard",
                inquirer_name="Ford Motor Credit",
                inquiry_date=date(2024, 12, 15),
                purpose="auto_loan",
            ),
        ]

        return CreditReport(
            user_id=user_id,
            bureau="experian",
            report_date=date.today(),
            score=score,
            accounts=accounts,
            inquiries=inquiries,
            public_records=[],
            consumer_statements=[],
        )

    def subscribe_to_changes(self, user_id: str, webhook_url: str, **kwargs) -> str:
        """Return mock subscription ID.

        Args:
            user_id: User identifier
            webhook_url: Ignored
            **kwargs: Ignored

        Returns:
            Mock subscription ID
        """
        return f"sub_mock_{user_id}"
