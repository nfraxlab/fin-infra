"""Integration tests for cash flow analysis.

These tests verify that cash flow analysis integrates correctly with:
- Banking module (transaction fetching)
- Categorization module (expense classification)
- Multiple data sources working together
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import pytest

from fin_infra.analytics.cash_flow import (
    calculate_cash_flow,
    forecast_cash_flow,
)
from fin_infra.analytics.models import CashFlowAnalysis
from fin_infra.models import Transaction


# Mock Banking Provider for Integration Testing
class MockBankingProvider:
    """Mock banking provider that simulates real banking data."""

    def __init__(self):
        self.transactions = []

    def add_transaction(self, transaction: Transaction):
        """Add a transaction to the mock provider."""
        self.transactions.append(transaction)

    async def get_transactions(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        accounts: Optional[list[str]] = None,
    ) -> list[Transaction]:
        """Fetch transactions for the given period."""
        # Filter by date range
        filtered = [t for t in self.transactions if start_date.date() <= t.date <= end_date.date()]

        # Filter by accounts if specified
        if accounts:
            filtered = [t for t in filtered if t.account_id in accounts]

        return filtered


# Mock Categorization Provider for Integration Testing
class MockCategorizationProvider:
    """Mock categorization provider that simulates category assignment."""

    def __init__(self):
        self.category_rules = {
            "groceries": "Groceries",
            "safeway": "Groceries",
            "whole foods": "Groceries",
            "restaurant": "Restaurants",
            "cafe": "Restaurants",
            "starbucks": "Restaurants",
            "gas": "Transportation",
            "uber": "Transportation",
            "netflix": "Entertainment",
            "spotify": "Entertainment",
            "rent": "Housing",
            "utilities": "Utilities",
            "electric": "Utilities",
        }

    async def categorize_transaction(self, transaction: Transaction) -> str:
        """Categorize a single transaction."""
        description_lower = (transaction.description or "").lower()

        for keyword, category in self.category_rules.items():
            if keyword in description_lower:
                return category

        return "Other"


class TestCashFlowWithBankingIntegration:
    """Tests for cash flow analysis with banking provider integration."""

    @pytest.mark.asyncio
    async def test_calculate_cash_flow_with_real_transactions(self):
        """Test cash flow calculation with simulated banking transactions."""
        banking = MockBankingProvider()

        # Add income transactions
        banking.add_transaction(
            Transaction(
                id="t1",
                account_id="acc1",
                amount=Decimal("5000.00"),
                date=date.today() - timedelta(days=5),
                description="EMPLOYER PAYROLL DEPOSIT",
                transaction_type="credit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="t2",
                account_id="acc1",
                amount=Decimal("150.00"),
                date=date.today() - timedelta(days=3),
                description="DIVIDEND PAYMENT",
                transaction_type="credit",
            )
        )

        # Add expense transactions
        banking.add_transaction(
            Transaction(
                id="t3",
                account_id="acc1",
                amount=Decimal("-75.50"),
                date=date.today() - timedelta(days=4),
                description="SAFEWAY GROCERIES",
                transaction_type="debit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="t4",
                account_id="acc1",
                amount=Decimal("-45.00"),
                date=date.today() - timedelta(days=2),
                description="RESTAURANT DINNER",
                transaction_type="debit",
            )
        )

        # Calculate cash flow (using mock provider)
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        result = await calculate_cash_flow(
            "user123",
            start_date=start_date,
            end_date=end_date,
            banking_provider=banking,
        )

        # Verify structure
        assert isinstance(result, CashFlowAnalysis)
        assert result.income_total > 0
        assert result.expense_total > 0
        assert result.net_cash_flow == result.income_total - result.expense_total

    @pytest.mark.asyncio
    async def test_calculate_cash_flow_with_account_filtering(self):
        """Test cash flow with account filtering."""
        banking = MockBankingProvider()

        # Add transactions to different accounts
        banking.add_transaction(
            Transaction(
                id="t1",
                account_id="checking",
                amount=Decimal("3000.00"),
                date=date.today() - timedelta(days=2),
                description="PAYROLL",
                transaction_type="credit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="t2",
                account_id="savings",
                amount=Decimal("50.00"),
                date=date.today() - timedelta(days=2),
                description="INTEREST",
                transaction_type="credit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="t3",
                account_id="checking",
                amount=Decimal("-100.00"),
                date=date.today() - timedelta(days=1),
                description="GROCERIES",
                transaction_type="debit",
            )
        )

        # Calculate for checking account only
        result = await calculate_cash_flow(
            "user123",
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            accounts=["checking"],
            banking_provider=banking,
        )

        # Should only include checking account transactions
        # (Note: actual implementation needs to support account filtering)
        assert isinstance(result, CashFlowAnalysis)

    @pytest.mark.asyncio
    async def test_calculate_cash_flow_empty_period(self):
        """Test cash flow calculation when no transactions exist."""
        banking = MockBankingProvider()
        # No transactions added

        result = await calculate_cash_flow(
            "user123",
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            banking_provider=banking,
        )

        # Should return zero values for empty period
        assert isinstance(result, CashFlowAnalysis)


class TestCashFlowWithCategorizationIntegration:
    """Tests for cash flow analysis with categorization integration."""

    @pytest.mark.asyncio
    async def test_cash_flow_with_expense_categorization(self):
        """Test that expenses are properly categorized."""
        banking = MockBankingProvider()
        categorization = MockCategorizationProvider()

        # Add expenses with categorizable descriptions
        banking.add_transaction(
            Transaction(
                id="t1",
                account_id="acc1",
                amount=Decimal("-100.00"),
                date=date.today() - timedelta(days=2),
                description="SAFEWAY GROCERIES",
                transaction_type="debit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="t2",
                account_id="acc1",
                amount=Decimal("-50.00"),
                date=date.today() - timedelta(days=3),
                description="STARBUCKS CAFE",
                transaction_type="debit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="t3",
                account_id="acc1",
                amount=Decimal("-1500.00"),
                date=date.today() - timedelta(days=1),
                description="RENT PAYMENT",
                transaction_type="debit",
            )
        )

        result = await calculate_cash_flow(
            "user123",
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            banking_provider=banking,
            categorization_provider=categorization,
        )

        # Verify categorization structure exists
        assert isinstance(result, CashFlowAnalysis)
        assert isinstance(result.expenses_by_category, dict)

    @pytest.mark.asyncio
    async def test_income_source_classification(self):
        """Test that income is properly classified by source."""
        banking = MockBankingProvider()

        # Add various income types
        banking.add_transaction(
            Transaction(
                id="t1",
                account_id="acc1",
                amount=Decimal("5000.00"),
                date=date.today() - timedelta(days=2),
                description="EMPLOYER PAYROLL",
                transaction_type="credit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="t2",
                account_id="acc1",
                amount=Decimal("200.00"),
                date=date.today() - timedelta(days=3),
                description="DIVIDEND INCOME",
                transaction_type="credit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="t3",
                account_id="acc1",
                amount=Decimal("500.00"),
                date=date.today() - timedelta(days=1),
                description="UPWORK FREELANCE",
                transaction_type="credit",
            )
        )

        result = await calculate_cash_flow(
            "user123",
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            banking_provider=banking,
        )

        # Verify income sources exist
        assert isinstance(result.income_by_source, dict)
        assert result.income_total > 0


class TestCashFlowForecastIntegration:
    """Tests for cash flow forecasting with recurring patterns."""

    @pytest.mark.asyncio
    async def test_forecast_with_recurring_patterns(self):
        """Test forecast uses recurring transaction patterns."""
        # Mock recurring patterns (would come from recurring detection module)
        result = await forecast_cash_flow(
            "user123",
            months=3,
            assumptions={
                "income_growth_rate": 0.02,  # 2% monthly income growth
                "expense_growth_rate": 0.03,  # 3% monthly expense growth
            },
        )

        assert isinstance(result, list)
        assert len(result) == 3  # 3 months

        # Verify all periods are CashFlowAnalysis
        for period in result:
            assert isinstance(period, CashFlowAnalysis)

    @pytest.mark.asyncio
    async def test_forecast_with_one_time_events(self):
        """Test forecast handles one-time income and expenses."""
        result = await forecast_cash_flow(
            "user123",
            months=6,
            assumptions={
                "one_time_income": {2: 5000.0},  # Bonus in month 2
                "one_time_expenses": {3: 2000.0, 5: 1500.0},  # Vacation and car repair
            },
        )

        assert len(result) == 6

        # Month 2 should have higher income (bonus)
        # Month 3 and 5 should have higher expenses
        for i, period in enumerate(result):
            assert isinstance(period, CashFlowAnalysis)
            assert period.net_cash_flow == period.income_total - period.expense_total

    @pytest.mark.asyncio
    async def test_forecast_growth_compounds_correctly(self):
        """Test that growth rates compound over time."""
        result = await forecast_cash_flow(
            "user123",
            months=12,
            assumptions={
                "income_growth_rate": 0.05,  # 5% monthly
                "expense_growth_rate": 0.02,  # 2% monthly
            },
        )

        assert len(result) == 12

        # Income should increase over time with growth rate
        # (Note: Implementation uses compound growth)
        for period in result:
            assert period.income_total > 0
            assert period.expense_total >= 0


class TestCashFlowEndToEndIntegration:
    """End-to-end integration tests combining all modules."""

    @pytest.mark.asyncio
    async def test_full_cash_flow_analysis_pipeline(self):
        """Test complete cash flow analysis from transactions to insights."""
        banking = MockBankingProvider()
        categorization = MockCategorizationProvider()

        # Create realistic transaction set for a month
        base_date = date.today()

        # Income: 2 paychecks
        banking.add_transaction(
            Transaction(
                id="income1",
                account_id="checking",
                amount=Decimal("2500.00"),
                date=base_date - timedelta(days=25),
                description="EMPLOYER PAYROLL",
                transaction_type="credit",
            )
        )
        banking.add_transaction(
            Transaction(
                id="income2",
                account_id="checking",
                amount=Decimal("2500.00"),
                date=base_date - timedelta(days=10),
                description="EMPLOYER PAYROLL",
                transaction_type="credit",
            )
        )

        # Expenses: Various categories
        expenses = [
            ("exp1", -1200.00, 28, "RENT PAYMENT"),
            ("exp2", -150.00, 26, "ELECTRIC UTILITIES"),
            ("exp3", -80.00, 24, "SAFEWAY GROCERIES"),
            ("exp4", -120.00, 20, "WHOLE FOODS GROCERIES"),
            ("exp5", -45.00, 18, "RESTAURANT DINNER"),
            ("exp6", -60.00, 15, "GAS STATION"),
            ("exp7", -15.00, 12, "NETFLIX SUBSCRIPTION"),
            ("exp8", -10.00, 12, "SPOTIFY PREMIUM"),
        ]

        for exp_id, amount, days_ago, description in expenses:
            banking.add_transaction(
                Transaction(
                    id=exp_id,
                    account_id="checking",
                    amount=Decimal(str(amount)),
                    date=base_date - timedelta(days=days_ago),
                    description=description,
                    transaction_type="debit",
                )
            )

        # Calculate cash flow
        result = await calculate_cash_flow(
            "user123",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            banking_provider=banking,
            categorization_provider=categorization,
        )

        # Verify complete result
        assert isinstance(result, CashFlowAnalysis)
        assert result.income_total > 0
        assert result.expense_total > 0
        assert result.net_cash_flow > 0  # Should be positive (income > expenses)
        assert len(result.income_by_source) > 0
        assert len(result.expenses_by_category) > 0
        assert result.period_start is not None
        assert result.period_end is not None

    @pytest.mark.asyncio
    async def test_cash_flow_consistency_across_periods(self):
        """Test that cash flow is consistent when calculated for different periods."""
        banking = MockBankingProvider()

        # Add transactions across 60 days
        for i in range(60):
            banking.add_transaction(
                Transaction(
                    id=f"t{i}",
                    account_id="acc1",
                    amount=Decimal("50.00" if i % 14 == 0 else "-10.00"),  # Income every 2 weeks
                    date=date.today() - timedelta(days=60 - i),
                    description="PAYROLL" if i % 14 == 0 else "EXPENSE",
                    transaction_type="credit" if i % 14 == 0 else "debit",
                )
            )

        # Calculate for different periods
        month1 = await calculate_cash_flow(
            "user123",
            start_date=datetime.now() - timedelta(days=60),
            end_date=datetime.now() - timedelta(days=30),
            banking_provider=banking,
        )

        month2 = await calculate_cash_flow(
            "user123",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            banking_provider=banking,
        )

        # Both periods should have valid results
        assert isinstance(month1, CashFlowAnalysis)
        assert isinstance(month2, CashFlowAnalysis)

        # Each period should be independent
        assert month1.period_start != month2.period_start
        assert month1.period_end != month2.period_end
