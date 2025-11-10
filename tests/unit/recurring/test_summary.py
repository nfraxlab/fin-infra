"""Unit tests for recurring transaction summary."""

import pytest
from datetime import datetime, timedelta

from fin_infra.recurring.summary import (
    RecurringItem,
    CancellationOpportunity,
    RecurringSummary,
    get_recurring_summary,
    _calculate_monthly_cost,
    _identify_cancellation_opportunities,
)
from fin_infra.recurring.models import RecurringPattern, PatternType, CadenceType


class TestCalculateMonthlyCost:
    """Test monthly cost calculation from different cadences."""
    
    def test_monthly_cadence(self):
        """Test monthly cadence returns amount as-is."""
        assert _calculate_monthly_cost(15.99, "monthly") == 15.99
        assert _calculate_monthly_cost(100.0, "MONTHLY") == 100.0
    
    def test_quarterly_cadence(self):
        """Test quarterly cadence divides by 3."""
        assert _calculate_monthly_cost(90.0, "quarterly") == 30.0
        assert _calculate_monthly_cost(300.0, "QUARTERLY") == 100.0
    
    def test_annual_cadence(self):
        """Test annual cadence divides by 12."""
        assert _calculate_monthly_cost(120.0, "annual") == 10.0
        assert _calculate_monthly_cost(1200.0, "ANNUAL") == 100.0
    
    def test_biweekly_cadence(self):
        """Test biweekly cadence multiplies by 26/12."""
        # 26 biweekly periods per year / 12 months
        assert _calculate_monthly_cost(100.0, "biweekly") == pytest.approx(216.67, rel=1e-2)
    
    def test_unknown_cadence_defaults_to_monthly(self):
        """Test unknown cadence defaults to monthly."""
        assert _calculate_monthly_cost(50.0, "unknown") == 50.0
        assert _calculate_monthly_cost(75.0, "weird") == 75.0


class TestIdentifyCancellationOpportunities:
    """Test cancellation opportunity detection."""
    
    def test_no_opportunities_with_few_subscriptions(self):
        """Test that no opportunities are found with minimal subscriptions."""
        subscriptions = [
            RecurringItem(
                merchant_name="Netflix",
                category="entertainment",
                amount=15.99,
                cadence="monthly",
                monthly_cost=15.99,
                is_subscription=True,
                next_charge_date="2025-12-15",
                confidence=0.98,
            )
        ]
        
        opportunities = _identify_cancellation_opportunities(subscriptions)
        assert len(opportunities) == 0
    
    def test_duplicate_streaming_services(self):
        """Test detection of multiple streaming services."""
        subscriptions = [
            RecurringItem(
                merchant_name="Netflix",
                category="entertainment",
                amount=15.99,
                cadence="monthly",
                monthly_cost=15.99,
                is_subscription=True,
                next_charge_date="2025-12-15",
                confidence=0.98,
            ),
            RecurringItem(
                merchant_name="Hulu",
                category="entertainment",
                amount=7.99,
                cadence="monthly",
                monthly_cost=7.99,
                is_subscription=True,
                next_charge_date="2025-12-10",
                confidence=0.95,
            ),
            RecurringItem(
                merchant_name="Disney Plus",
                category="entertainment",
                amount=10.99,
                cadence="monthly",
                monthly_cost=10.99,
                is_subscription=True,
                next_charge_date="2025-12-05",
                confidence=0.97,
            ),
        ]
        
        opportunities = _identify_cancellation_opportunities(subscriptions)
        
        # Should suggest canceling Hulu (cheapest, after keeping top 2)
        # Logic: Keep Netflix ($15.99) and Disney Plus ($10.99), suggest Hulu ($7.99)
        assert len(opportunities) == 1
        assert "Hulu" in opportunities[0].merchant_name
        assert "Multiple streaming services" in opportunities[0].reason
        assert opportunities[0].monthly_savings == 7.99
    
    def test_duplicate_cloud_storage(self):
        """Test detection of duplicate cloud storage services."""
        subscriptions = [
            RecurringItem(
                merchant_name="Dropbox",
                category="software",
                amount=9.99,
                cadence="monthly",
                monthly_cost=9.99,
                is_subscription=True,
                next_charge_date="2025-12-15",
                confidence=0.95,
            ),
            RecurringItem(
                merchant_name="Google Drive",
                category="software",
                amount=1.99,
                cadence="monthly",
                monthly_cost=1.99,
                is_subscription=True,
                next_charge_date="2025-12-10",
                confidence=0.98,
            ),
        ]
        
        opportunities = _identify_cancellation_opportunities(subscriptions)
        
        # Should suggest canceling Dropbox (more expensive)
        assert len(opportunities) == 1
        assert "Dropbox" in opportunities[0].merchant_name
        assert "Duplicate cloud storage" in opportunities[0].reason
        assert opportunities[0].monthly_savings == 9.99
    
    def test_low_confidence_subscriptions(self):
        """Test detection of low-confidence subscriptions."""
        subscriptions = [
            RecurringItem(
                merchant_name="Mystery Service",
                category="other",
                amount=25.00,
                cadence="monthly",
                monthly_cost=25.00,
                is_subscription=True,
                next_charge_date="2025-12-15",
                confidence=0.55,  # Low confidence
            )
        ]
        
        opportunities = _identify_cancellation_opportunities(subscriptions)
        
        assert len(opportunities) == 1
        assert "Mystery Service" in opportunities[0].merchant_name
        assert "Low detection confidence" in opportunities[0].reason
        assert opportunities[0].monthly_savings == 25.00


class TestGetRecurringSummary:
    """Test get_recurring_summary function."""
    
    def test_empty_patterns(self):
        """Test with no recurring patterns."""
        summary = get_recurring_summary("user_123", [])
        
        assert summary.user_id == "user_123"
        assert summary.total_monthly_cost == 0.0
        assert summary.total_monthly_income == 0.0
        assert len(summary.subscriptions) == 0
        assert len(summary.recurring_income) == 0
        assert len(summary.by_category) == 0
        assert len(summary.cancellation_opportunities) == 0
    
    def test_single_monthly_subscription(self):
        """Test with a single monthly subscription."""
        patterns = [
            RecurringPattern(
                merchant_name="NETFLIX.COM",
                normalized_merchant="netflix",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=15.99,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=12,
                first_date=datetime(2024, 1, 15),
                last_date=datetime(2024, 12, 15),
                next_expected_date=datetime(2025, 1, 15),
                date_std_dev=0.5,
                confidence=0.98,
            )
        ]
        
        summary = get_recurring_summary("user_123", patterns)
        
        assert summary.user_id == "user_123"
        assert summary.total_monthly_cost == 15.99
        assert len(summary.subscriptions) == 1
        assert summary.subscriptions[0].merchant_name == "netflix"
        assert summary.subscriptions[0].category == "entertainment"
        assert summary.subscriptions[0].monthly_cost == 15.99
        assert summary.by_category["entertainment"] == 15.99
    
    def test_quarterly_subscription(self):
        """Test with a quarterly subscription (normalized to monthly)."""
        patterns = [
            RecurringPattern(
                merchant_name="INSURANCE CO",
                normalized_merchant="insurance",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.QUARTERLY,
                amount=300.0,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=4,
                first_date=datetime(2024, 1, 1),
                last_date=datetime(2024, 10, 1),
                next_expected_date=datetime(2025, 1, 1),
                date_std_dev=1.0,
                confidence=0.95,
            )
        ]
        
        summary = get_recurring_summary("user_123", patterns)
        
        assert summary.total_monthly_cost == pytest.approx(100.0, rel=1e-2)
        assert summary.subscriptions[0].category == "insurance"
        assert summary.subscriptions[0].monthly_cost == pytest.approx(100.0, rel=1e-2)
    
    def test_annual_subscription(self):
        """Test with an annual subscription."""
        patterns = [
            RecurringPattern(
                merchant_name="AMAZON PRIME",
                normalized_merchant="amazon",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.ANNUAL,
                amount=139.0,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=2,
                first_date=datetime(2023, 6, 1),
                last_date=datetime(2024, 6, 1),
                next_expected_date=datetime(2025, 6, 1),
                date_std_dev=0.0,
                confidence=0.99,
            )
        ]
        
        summary = get_recurring_summary("user_123", patterns)
        
        # $139/year = $11.58/month
        assert summary.total_monthly_cost == pytest.approx(11.58, rel=1e-2)
    
    def test_variable_amount_pattern(self):
        """Test with variable amount pattern (uses average)."""
        patterns = [
            RecurringPattern(
                merchant_name="ELECTRIC COMPANY",
                normalized_merchant="electric",
                pattern_type=PatternType.VARIABLE,
                cadence=CadenceType.MONTHLY,
                amount=None,
                amount_range=(50.0, 150.0),
                amount_variance_pct=0.3,
                occurrence_count=12,
                first_date=datetime(2024, 1, 1),
                last_date=datetime(2024, 12, 1),
                next_expected_date=datetime(2025, 1, 1),
                date_std_dev=2.0,
                confidence=0.92,
            )
        ]
        
        summary = get_recurring_summary("user_123", patterns)
        
        # Average of range (50 + 150) / 2 = 100
        assert summary.total_monthly_cost == 100.0
        assert summary.subscriptions[0].category == "utilities"
    
    def test_multiple_subscriptions_by_category(self):
        """Test with multiple subscriptions grouped by category."""
        patterns = [
            RecurringPattern(
                merchant_name="NETFLIX",
                normalized_merchant="netflix",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=15.99,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=12,
                first_date=datetime(2024, 1, 15),
                last_date=datetime(2024, 12, 15),
                next_expected_date=datetime(2025, 1, 15),
                date_std_dev=0.5,
                confidence=0.98,
            ),
            RecurringPattern(
                merchant_name="SPOTIFY",
                normalized_merchant="spotify",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=9.99,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=12,
                first_date=datetime(2024, 1, 10),
                last_date=datetime(2024, 12, 10),
                next_expected_date=datetime(2025, 1, 10),
                date_std_dev=0.3,
                confidence=0.99,
            ),
            RecurringPattern(
                merchant_name="GYM MEMBERSHIP",
                normalized_merchant="gym",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=50.0,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=12,
                first_date=datetime(2024, 1, 1),
                last_date=datetime(2024, 12, 1),
                next_expected_date=datetime(2025, 1, 1),
                date_std_dev=0.0,
                confidence=0.95,
            ),
        ]
        
        summary = get_recurring_summary("user_123", patterns)
        
        assert summary.total_monthly_cost == pytest.approx(75.98, rel=1e-2)
        assert len(summary.subscriptions) == 3
        assert summary.by_category["entertainment"] == pytest.approx(25.98, rel=1e-2)
        assert summary.by_category["fitness"] == 50.0
    
    def test_recurring_income(self):
        """Test with recurring income (negative amounts)."""
        patterns = [
            RecurringPattern(
                merchant_name="EMPLOYER DIRECT DEPOSIT",
                normalized_merchant="paycheck",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.BIWEEKLY,
                amount=-2500.0,  # Negative = income
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=26,
                first_date=datetime(2024, 1, 5),
                last_date=datetime(2024, 12, 27),
                next_expected_date=datetime(2025, 1, 10),
                date_std_dev=0.0,
                confidence=1.0,
            )
        ]
        
        summary = get_recurring_summary("user_123", patterns)
        
        # Biweekly: $2500 * 26 / 12 = $5416.67/month
        assert summary.total_monthly_income == pytest.approx(5416.67, rel=1e-2)
        assert len(summary.recurring_income) == 1
        assert summary.recurring_income[0].is_subscription is False
    
    def test_mixed_expenses_and_income(self):
        """Test with both expenses and income."""
        patterns = [
            RecurringPattern(
                merchant_name="NETFLIX",
                normalized_merchant="netflix",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=15.99,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=12,
                first_date=datetime(2024, 1, 15),
                last_date=datetime(2024, 12, 15),
                next_expected_date=datetime(2025, 1, 15),
                date_std_dev=0.5,
                confidence=0.98,
            ),
            RecurringPattern(
                merchant_name="PAYCHECK",
                normalized_merchant="paycheck",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=-3000.0,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=12,
                first_date=datetime(2024, 1, 1),
                last_date=datetime(2024, 12, 1),
                next_expected_date=datetime(2025, 1, 1),
                date_std_dev=0.0,
                confidence=1.0,
            ),
        ]
        
        summary = get_recurring_summary("user_123", patterns)
        
        assert summary.total_monthly_cost == 15.99
        assert summary.total_monthly_income == 3000.0
        assert len(summary.subscriptions) == 1
        assert len(summary.recurring_income) == 1
    
    def test_custom_category_map(self):
        """Test with custom category mapping."""
        patterns = [
            RecurringPattern(
                merchant_name="ACME CORP SUBSCRIPTION",
                normalized_merchant="acme",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=99.99,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=6,
                first_date=datetime(2024, 6, 1),
                last_date=datetime(2024, 12, 1),
                next_expected_date=datetime(2025, 1, 1),
                date_std_dev=0.5,
                confidence=0.90,
            )
        ]
        
        category_map = {"acme": "business"}
        summary = get_recurring_summary("user_123", patterns, category_map)
        
        assert summary.subscriptions[0].category == "business"
        assert summary.by_category["business"] == 99.99
    
    def test_cancellation_opportunities_with_many_streaming(self):
        """Test that cancellation opportunities are identified."""
        patterns = [
            RecurringPattern(
                merchant_name="NETFLIX",
                normalized_merchant="netflix",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=15.99,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=12,
                first_date=datetime(2024, 1, 15),
                last_date=datetime(2024, 12, 15),
                next_expected_date=datetime(2025, 1, 15),
                date_std_dev=0.5,
                confidence=0.98,
            ),
            RecurringPattern(
                merchant_name="HULU",
                normalized_merchant="hulu",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=7.99,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=12,
                first_date=datetime(2024, 1, 10),
                last_date=datetime(2024, 12, 10),
                next_expected_date=datetime(2025, 1, 10),
                date_std_dev=0.3,
                confidence=0.95,
            ),
            RecurringPattern(
                merchant_name="DISNEY+",
                normalized_merchant="disney",
                pattern_type=PatternType.FIXED,
                cadence=CadenceType.MONTHLY,
                amount=10.99,
                amount_range=None,
                amount_variance_pct=0.0,
                occurrence_count=8,
                first_date=datetime(2024, 5, 1),
                last_date=datetime(2024, 12, 1),
                next_expected_date=datetime(2025, 1, 1),
                date_std_dev=0.8,
                confidence=0.92,
            ),
        ]
        
        summary = get_recurring_summary("user_123", patterns)
        
        # Should identify Hulu as cancellation opportunity (cheapest of 3 streaming services)
        # Logic: Keep Netflix ($15.99) and Disney+ ($10.99), suggest Hulu ($7.99)
        assert len(summary.cancellation_opportunities) >= 1
        hulu_opp = [o for o in summary.cancellation_opportunities if "hulu" in o.merchant_name.lower()]
        assert len(hulu_opp) == 1
        assert hulu_opp[0].monthly_savings == 7.99


class TestRecurringSummaryModel:
    """Test RecurringSummary Pydantic model."""
    
    def test_minimal_summary(self):
        """Test creating a minimal summary."""
        summary = RecurringSummary(
            user_id="user_123",
            total_monthly_cost=0.0,
        )
        
        assert summary.user_id == "user_123"
        assert summary.total_monthly_cost == 0.0
        assert summary.total_monthly_income == 0.0
        assert len(summary.subscriptions) == 0
        assert len(summary.recurring_income) == 0
        assert len(summary.by_category) == 0
        assert len(summary.cancellation_opportunities) == 0
        assert summary.generated_at is not None
    
    def test_json_serialization(self):
        """Test that summary can be serialized to JSON."""
        summary = RecurringSummary(
            user_id="user_123",
            total_monthly_cost=50.0,
            total_monthly_income=3000.0,
            by_category={"entertainment": 50.0},
        )
        
        json_data = summary.model_dump()
        
        assert json_data["user_id"] == "user_123"
        assert json_data["total_monthly_cost"] == 50.0
        assert json_data["total_monthly_income"] == 3000.0
        assert json_data["by_category"]["entertainment"] == 50.0
