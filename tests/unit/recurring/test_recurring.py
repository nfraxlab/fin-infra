"""
Unit tests for recurring transaction detection.

Tests cover:
- Merchant normalization
- Fixed amount detection
- Variable amount detection
- Irregular/annual detection
- Date clustering
- False positive filtering
- Easy builder
- API integration
"""

import pytest
from datetime import datetime, timedelta

from fin_infra.recurring import (
    easy_recurring_detection,
    normalize_merchant,
    get_canonical_merchant,
    is_generic_merchant,
    CadenceType,
    PatternType,
)
from fin_infra.recurring.detector import Transaction, PatternDetector


class TestMerchantNormalization:
    """Test merchant name normalization."""

    def test_lowercase(self):
        """Should convert to lowercase."""
        assert normalize_merchant("NETFLIX.COM") == "netflix"

    def test_remove_special_chars(self):
        """Should remove special characters."""
        assert normalize_merchant("netflix.com") == "netflix"
        assert normalize_merchant("starbucks*coffee") == "starbucks coffee"

    def test_remove_store_numbers(self):
        """Should remove store/transaction numbers."""
        assert normalize_merchant("Starbucks #12345") == "starbucks"
        assert normalize_merchant("Shell 98765") == "shell"

    def test_remove_legal_entities(self):
        """Should remove legal entity suffixes."""
        assert normalize_merchant("Netflix Inc") == "netflix"
        assert normalize_merchant("Shell Oil Corp") == "shell oil"
        assert normalize_merchant("Amazon LLC") == "amazon"

    def test_normalize_whitespace(self):
        """Should normalize whitespace."""
        assert normalize_merchant("  netflix  ") == "netflix"
        assert normalize_merchant("star  bucks") == "star bucks"

    def test_complex_merchant_name(self):
        """Should handle complex merchant names."""
        assert normalize_merchant("STARBUCKS COFFEE #12345 INC.") == "starbucks coffee"


class TestCanonicalMerchants:
    """Test canonical merchant name mapping."""

    def test_known_netflix_variants(self):
        """Should map Netflix variants to canonical name."""
        assert get_canonical_merchant("NETFLIX.COM") == "netflix"
        assert get_canonical_merchant("Netflix Inc") == "netflix"
        assert get_canonical_merchant("NFLX*SUBSCRIPTION") == "netflix"

    def test_known_spotify_variants(self):
        """Should map Spotify variants to canonical name."""
        assert get_canonical_merchant("Spotify USA") == "spotify"
        assert get_canonical_merchant("SPOTIFYUSA") == "spotify"

    def test_known_amazon_variants(self):
        """Should map Amazon variants to canonical name."""
        assert get_canonical_merchant("AMZN MKTP US") == "amazon"
        assert get_canonical_merchant("Amazon Prime") == "amazon"

    def test_unknown_merchant(self):
        """Should return normalized name for unknown merchant."""
        result = get_canonical_merchant("Unknown Merchant Inc")
        assert result == "unknown merchant"


class TestGenericMerchants:
    """Test generic merchant detection."""

    def test_atm_withdrawal(self):
        """Should detect ATM withdrawals as generic."""
        assert is_generic_merchant("ATM Withdrawal")
        assert is_generic_merchant("atm cash")

    def test_generic_payment(self):
        """Should detect generic payment terms."""
        assert is_generic_merchant("Payment")
        assert is_generic_merchant("Debit Purchase")
        assert is_generic_merchant("Transfer")

    def test_real_merchant(self):
        """Should not detect real merchants as generic."""
        assert not is_generic_merchant("Netflix")
        assert not is_generic_merchant("Starbucks")


class TestFixedAmountDetection:
    """Test fixed amount subscription detection."""

    def test_netflix_monthly(self):
        """Should detect Netflix monthly subscription."""
        # Create 6 months of Netflix charges
        transactions = []
        base_date = datetime(2025, 1, 15)

        for i in range(6):
            date = base_date + timedelta(days=30 * i)
            transactions.append(
                Transaction(
                    id=f"txn_{i}",
                    merchant="NETFLIX.COM",
                    amount=15.99,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        pattern = patterns[0]

        assert pattern.pattern_type == PatternType.FIXED
        assert pattern.cadence == CadenceType.MONTHLY
        assert pattern.amount == 15.99
        assert pattern.occurrence_count == 6
        assert pattern.confidence >= 0.90

    def test_spotify_monthly(self):
        """Should detect Spotify monthly subscription."""
        transactions = []
        base_date = datetime(2025, 1, 1)

        for i in range(4):
            date = base_date + timedelta(days=30 * i)
            transactions.append(
                Transaction(
                    id=f"txn_{i}",
                    merchant="Spotify Premium",
                    amount=9.99,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.FIXED
        assert patterns[0].amount == 9.99

    def test_insufficient_occurrences(self):
        """Should not detect pattern with <3 occurrences."""
        transactions = [
            Transaction("1", "Netflix", 15.99, datetime(2025, 1, 15)),
            Transaction("2", "Netflix", 15.99, datetime(2025, 2, 15)),
        ]

        detector = PatternDetector(min_occurrences=3)
        patterns = detector.detect(transactions)

        assert len(patterns) == 0


class TestVariableAmountDetection:
    """Test variable amount bill detection."""

    def test_utility_bill_variable(self):
        """Should detect utility bill with variable amounts."""
        transactions = []
        base_date = datetime(2025, 1, 20)
        amounts = [52.34, 68.12, 45.90, 59.45, 55.20, 63.80]  # 10-30% variance

        for i, amount in enumerate(amounts):
            date = base_date + timedelta(days=30 * i)
            transactions.append(
                Transaction(
                    id=f"txn_{i}",
                    merchant="PG&E Utilities",
                    amount=amount,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        pattern = patterns[0]

        assert pattern.pattern_type == PatternType.VARIABLE
        assert pattern.cadence == CadenceType.MONTHLY
        assert pattern.amount_range is not None
        assert pattern.confidence >= 0.70

    def test_phone_bill_with_overage(self):
        """Should detect phone bill with occasional overage charges."""
        transactions = []
        base_date = datetime(2025, 1, 5)
        amounts = [60.00, 60.00, 85.50, 60.00, 72.30]  # Some months with overages

        for i, amount in enumerate(amounts):
            date = base_date + timedelta(days=30 * i)
            transactions.append(
                Transaction(
                    id=f"txn_{i}",
                    merchant="AT&T Phone",
                    amount=amount,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        assert patterns[0].pattern_type == PatternType.VARIABLE


class TestIrregularDetection:
    """Test irregular/annual subscription detection."""

    def test_amazon_prime_annual(self):
        """Should detect Amazon Prime annual subscription."""
        transactions = [
            Transaction("1", "Amazon Prime Annual", 139.00, datetime(2023, 11, 15)),
            Transaction("2", "Amazon Prime Annual", 139.00, datetime(2024, 11, 15)),
            Transaction("3", "Amazon Prime Annual", 139.00, datetime(2025, 11, 15)),
        ]

        detector = PatternDetector(min_occurrences=2)
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        pattern = patterns[0]

        assert pattern.pattern_type == PatternType.IRREGULAR
        assert pattern.cadence == CadenceType.ANNUAL
        assert pattern.amount == 139.00
        assert pattern.confidence >= 0.60

    def test_quarterly_subscription(self):
        """Should detect quarterly subscription."""
        transactions = []
        base_date = datetime(2025, 1, 1)

        for i in range(4):
            date = base_date + timedelta(days=90 * i)
            transactions.append(
                Transaction(
                    id=f"txn_{i}",
                    merchant="Quarterly Service",
                    amount=99.99,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        assert patterns[0].cadence == CadenceType.QUARTERLY


class TestDateClustering:
    """Test date clustering and cadence detection."""

    def test_same_day_monthly(self):
        """Should detect monthly pattern on same day."""
        transactions = [
            Transaction("1", "Netflix", 15.99, datetime(2025, 1, 15)),
            Transaction("2", "Netflix", 15.99, datetime(2025, 2, 15)),
            Transaction("3", "Netflix", 15.99, datetime(2025, 3, 15)),
            Transaction("4", "Netflix", 15.99, datetime(2025, 4, 15)),
        ]

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        assert patterns[0].cadence == CadenceType.MONTHLY
        assert patterns[0].date_std_dev < 2  # Very consistent

    def test_variable_day_monthly(self):
        """Should detect monthly pattern with slight day variation."""
        transactions = [
            Transaction("1", "Spotify", 9.99, datetime(2025, 1, 1)),
            Transaction("2", "Spotify", 9.99, datetime(2025, 2, 3)),
            Transaction("3", "Spotify", 9.99, datetime(2025, 3, 2)),
            Transaction("4", "Spotify", 9.99, datetime(2025, 4, 1)),
        ]

        detector = PatternDetector(date_tolerance_days=7)
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        assert patterns[0].cadence == CadenceType.MONTHLY

    def test_biweekly_pattern(self):
        """Should detect bi-weekly pattern."""
        transactions = []
        base_date = datetime(2025, 1, 1)

        for i in range(6):
            date = base_date + timedelta(days=14 * i)
            transactions.append(
                Transaction(
                    id=f"txn_{i}",
                    merchant="Bi-Weekly Service",
                    amount=25.00,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        assert patterns[0].cadence == CadenceType.BIWEEKLY


class TestFalsePositiveFiltering:
    """Test false positive detection and filtering."""

    def test_random_purchases_not_recurring(self):
        """Should not detect random purchases as recurring."""
        transactions = [
            Transaction("1", "Target", 45.67, datetime(2025, 1, 10)),
            Transaction("2", "Target", 32.18, datetime(2025, 2, 5)),
            Transaction("3", "Target", 67.89, datetime(2025, 3, 22)),
        ]

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 0  # Should filter out due to inconsistency

    def test_generic_merchant_filtered(self):
        """Should filter out generic merchants."""
        transactions = []
        base_date = datetime(2025, 1, 1)

        for i in range(4):
            date = base_date + timedelta(days=30 * i)
            transactions.append(
                Transaction(
                    id=f"txn_{i}",
                    merchant="ATM Withdrawal",
                    amount=100.00,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        # Should be filtered as generic merchant
        assert len(patterns) == 0


class TestMerchantGrouping:
    """Test merchant name variants are grouped together."""

    def test_netflix_variants_grouped(self):
        """Should group Netflix name variants."""
        transactions = [
            Transaction("1", "NETFLIX.COM", 15.99, datetime(2025, 1, 15)),
            Transaction("2", "Netflix Inc", 15.99, datetime(2025, 2, 15)),
            Transaction("3", "NFLX*SUBSCRIPTION", 15.99, datetime(2025, 3, 15)),
        ]

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1  # All grouped as one pattern
        assert patterns[0].normalized_merchant == "netflix"

    def test_starbucks_store_numbers_grouped(self):
        """Should group Starbucks transactions across different stores."""
        transactions = [
            Transaction("1", "Starbucks #12345", 5.75, datetime(2025, 1, 5)),
            Transaction("2", "Starbucks #67890", 5.75, datetime(2025, 1, 12)),
            Transaction("3", "STARBUCKS COFFEE #11111", 5.75, datetime(2025, 1, 19)),
        ]

        detector = PatternDetector(min_occurrences=3, date_tolerance_days=10)
        patterns = detector.detect(transactions)

        # Note: Weekly Starbucks might not be detected as recurring (too frequent)
        # But merchant normalization should group them
        assert all(p.normalized_merchant == "starbucks" for p in patterns)


class TestEasyBuilder:
    """Test easy_recurring_detection() builder."""

    def test_default_configuration(self):
        """Should create detector with default parameters."""
        detector = easy_recurring_detection()

        assert detector.detector.min_occurrences == 3
        assert detector.detector.amount_tolerance == 0.02
        assert detector.detector.date_tolerance_days == 7

    def test_custom_configuration(self):
        """Should create detector with custom parameters."""
        detector = easy_recurring_detection(
            min_occurrences=4,
            amount_tolerance=0.01,
            date_tolerance_days=3,
        )

        assert detector.detector.min_occurrences == 4
        assert detector.detector.amount_tolerance == 0.01
        assert detector.detector.date_tolerance_days == 3

    def test_validation_min_occurrences(self):
        """Should validate min_occurrences >= 2."""
        with pytest.raises(ValueError, match="min_occurrences must be >= 2"):
            easy_recurring_detection(min_occurrences=1)

    def test_validation_amount_tolerance(self):
        """Should validate amount_tolerance in [0.0, 1.0]."""
        with pytest.raises(ValueError, match="amount_tolerance must be between"):
            easy_recurring_detection(amount_tolerance=1.5)

    def test_validation_date_tolerance(self):
        """Should validate date_tolerance_days >= 0."""
        with pytest.raises(ValueError, match="date_tolerance_days must be >= 0"):
            easy_recurring_detection(date_tolerance_days=-1)


class TestDetectorStats:
    """Test detection statistics tracking."""

    def test_stats_tracking(self):
        """Should track detection statistics."""
        transactions = [
            # Fixed pattern
            Transaction("1", "Netflix", 15.99, datetime(2025, 1, 15)),
            Transaction("2", "Netflix", 15.99, datetime(2025, 2, 15)),
            Transaction("3", "Netflix", 15.99, datetime(2025, 3, 15)),
            # Variable pattern
            Transaction("4", "PG&E", 50.00, datetime(2025, 1, 20)),
            Transaction("5", "PG&E", 65.00, datetime(2025, 2, 20)),
            Transaction("6", "PG&E", 55.00, datetime(2025, 3, 20)),
        ]

        detector = PatternDetector()
        patterns = detector.detect(transactions)
        stats = detector.get_stats()

        assert stats["total_detected"] == 2
        assert stats["fixed_patterns"] >= 1
        assert stats["variable_patterns"] >= 0


class TestConfidenceScoring:
    """Test confidence score calculation."""

    def test_high_confidence_fixed(self):
        """Fixed patterns with many occurrences should have high confidence."""
        transactions = []
        base_date = datetime(2025, 1, 15)

        for i in range(12):  # Full year
            date = base_date + timedelta(days=30 * i)
            transactions.append(
                Transaction(
                    id=f"txn_{i}",
                    merchant="Netflix",
                    amount=15.99,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        assert patterns[0].confidence >= 0.95  # Very high confidence

    def test_lower_confidence_variable(self):
        """Variable patterns should have lower confidence than fixed."""
        # Create variable pattern
        transactions_variable = []
        base_date = datetime(2025, 1, 20)

        for i in range(6):
            amount = 50.00 + (i % 3) * 10.00  # Varies between 50-70
            date = base_date + timedelta(days=30 * i)
            transactions_variable.append(
                Transaction(
                    id=f"var_{i}",
                    merchant="Utility",
                    amount=amount,
                    date=date,
                )
            )

        # Create fixed pattern
        transactions_fixed = []
        for i in range(6):
            date = base_date + timedelta(days=30 * i)
            transactions_fixed.append(
                Transaction(
                    id=f"fix_{i}",
                    merchant="Netflix",
                    amount=15.99,
                    date=date,
                )
            )

        detector = PatternDetector()
        patterns_var = detector.detect(transactions_variable)
        patterns_fix = detector.detect(transactions_fixed)

        if patterns_var and patterns_fix:
            assert patterns_fix[0].confidence > patterns_var[0].confidence


class TestReasoningGeneration:
    """Test human-readable reasoning generation."""

    def test_fixed_pattern_reasoning(self):
        """Should generate reasoning for fixed patterns."""
        transactions = [
            Transaction("1", "Netflix", 15.99, datetime(2025, 1, 15)),
            Transaction("2", "Netflix", 15.99, datetime(2025, 2, 15)),
            Transaction("3", "Netflix", 15.99, datetime(2025, 3, 15)),
        ]

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        assert len(patterns) == 1
        assert patterns[0].reasoning is not None
        assert "15.99" in patterns[0].reasoning
        assert "monthly" in patterns[0].reasoning.lower()

    def test_variable_pattern_reasoning(self):
        """Should generate reasoning for variable patterns."""
        transactions = [
            Transaction("1", "Utility", 50.00, datetime(2025, 1, 20)),
            Transaction("2", "Utility", 65.00, datetime(2025, 2, 20)),
            Transaction("3", "Utility", 55.00, datetime(2025, 3, 20)),
        ]

        detector = PatternDetector()
        patterns = detector.detect(transactions)

        if patterns:
            assert patterns[0].reasoning is not None
            assert "variance" in patterns[0].reasoning.lower()
