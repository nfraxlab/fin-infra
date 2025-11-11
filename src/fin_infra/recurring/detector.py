"""
Core recurring transaction detection engine.

V2: Adds optional LLM enhancement for merchant normalization (Layer 2)
and variable amount detection (Layer 4).

This module implements the 4-layer hybrid pattern detection:
- Layer 1: RapidFuzz merchant normalization (95% coverage, 80% accuracy, fast)
- Layer 2: LLM merchant normalization (5% edge cases, 90-95% accuracy, cached)
- Layer 3: Statistical pattern detection (90% coverage, mean ± 2σ)
- Layer 4: LLM variable detection (10% edge cases, 88% accuracy, semantic understanding)
- Layer 5: LLM insights (optional, on-demand via API)
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional, TYPE_CHECKING

from .models import CadenceType, PatternType, RecurringPattern
from .normalizer import get_canonical_merchant, is_generic_merchant

if TYPE_CHECKING:
    from .normalizers import MerchantNormalizer
    from .detectors_llm import VariableDetectorLLM
    from .insights import SubscriptionInsightsGenerator


class Transaction:
    """Simple transaction model for detection."""

    def __init__(
        self,
        id: str,
        merchant: str,
        amount: float,
        date: datetime,
    ):
        self.id = id
        self.merchant = merchant
        self.amount = amount
        self.date = date


class PatternDetector:
    """
    4-layer hybrid pattern detector for recurring transactions.

    Detects subscriptions and bills with multi-factor confidence scoring.

    V2: Optional LLM enhancement for merchant normalization (Layer 2)
    and variable amount detection (Layer 4).
    """

    def __init__(
        self,
        min_occurrences: int = 3,
        amount_tolerance: float = 0.02,
        date_tolerance_days: int = 7,
        merchant_normalizer: Optional[MerchantNormalizer] = None,
        variable_detector_llm: Optional[VariableDetectorLLM] = None,
    ):
        """
        Initialize pattern detector.

        Args:
            min_occurrences: Minimum number of transactions to detect pattern (default: 3)
            amount_tolerance: Amount variance tolerance for fixed patterns (default: 0.02 = 2%)
            date_tolerance_days: Date clustering tolerance in days (default: 7)
            merchant_normalizer: Optional LLM merchant normalizer (Layer 2)
            variable_detector_llm: Optional LLM variable amount detector (Layer 4)
        """
        self.min_occurrences = min_occurrences
        self.amount_tolerance = amount_tolerance
        self.date_tolerance_days = date_tolerance_days
        self.merchant_normalizer = merchant_normalizer
        self.variable_detector_llm = variable_detector_llm

        # Statistics
        self.stats = {
            "total_detected": 0,
            "fixed_patterns": 0,
            "variable_patterns": 0,
            "irregular_patterns": 0,
            "false_positives_filtered": 0,
            "llm_normalizations": 0,
            "llm_variable_detections": 0,
        }

    def detect(self, transactions: list[Transaction]) -> list[RecurringPattern]:
        """
        Detect all recurring patterns in transaction history.

        Args:
            transactions: List of Transaction objects

        Returns:
            List of RecurringPattern objects sorted by confidence (descending)
        """
        if not transactions:
            return []

        # Group transactions by normalized merchant
        grouped = self._group_by_merchant(transactions)

        patterns = []

        # Detect patterns for each merchant group
        for merchant_name, txns in grouped.items():
            if len(txns) < self.min_occurrences:
                continue

            # Try Layer 1: Fixed amount
            pattern = self._detect_fixed_pattern(merchant_name, txns)
            if pattern:
                patterns.append(pattern)
                self.stats["fixed_patterns"] += 1
                continue

            # Try Layer 2: Variable amount
            pattern = self._detect_variable_pattern(merchant_name, txns)
            if pattern:
                patterns.append(pattern)
                self.stats["variable_patterns"] += 1
                continue

            # Try Layer 3: Irregular/annual
            if len(txns) >= 2:  # Lower threshold for annual
                pattern = self._detect_irregular_pattern(merchant_name, txns)
                if pattern:
                    patterns.append(pattern)
                    self.stats["irregular_patterns"] += 1

        # Filter false positives
        patterns = [p for p in patterns if not self._is_false_positive(p)]
        self.stats["total_detected"] = len(patterns)

        # Sort by confidence (descending)
        return sorted(patterns, key=lambda x: x.confidence, reverse=True)

    def _group_by_merchant(self, transactions: list[Transaction]) -> dict[str, list[Transaction]]:
        """Group transactions by normalized merchant name."""
        groups: dict[str, list[Transaction]] = defaultdict(list)

        for txn in transactions:
            canonical = get_canonical_merchant(txn.merchant)
            groups[canonical].append(txn)

        return dict(groups)

    def _detect_fixed_pattern(
        self, merchant: str, txns: list[Transaction]
    ) -> RecurringPattern | None:
        """
        Detect fixed amount subscription pattern.

        Criteria:
        - Amount within tolerance (±2% or ±$0.50)
        - Regular cadence (monthly, bi-weekly, quarterly)
        - Min 3 occurrences
        """
        if len(txns) < self.min_occurrences:
            return None

        # Sort by date
        sorted_txns = sorted(txns, key=lambda t: t.date)
        amounts = [t.amount for t in sorted_txns]

        # Check amount consistency
        median_amount = statistics.median(amounts)
        tolerance = max(median_amount * self.amount_tolerance, 0.50)

        if not all(abs(amt - median_amount) <= tolerance for amt in amounts):
            return None  # Not fixed amount

        # Calculate amount variance
        amount_variance = statistics.stdev(amounts) / median_amount if len(amounts) > 1 else 0.0

        # Detect cadence
        cadence, date_std_dev = self._detect_cadence(sorted_txns)
        if not cadence:
            return None  # No regular cadence

        # Skip quarterly/annual for fixed patterns (those are IRREGULAR)
        if cadence in [CadenceType.QUARTERLY, CadenceType.ANNUAL]:
            return None

        # Calculate next expected date
        next_date = self._predict_next_date(sorted_txns, cadence)

        # Build pattern
        pattern = RecurringPattern(
            merchant_name=sorted_txns[0].merchant,  # Original name
            normalized_merchant=merchant,
            pattern_type=PatternType.FIXED,
            cadence=cadence,
            amount=median_amount,
            amount_range=None,
            amount_variance_pct=amount_variance,
            occurrence_count=len(sorted_txns),
            first_date=sorted_txns[0].date,
            last_date=sorted_txns[-1].date,
            next_expected_date=next_date,
            date_std_dev=date_std_dev,
            confidence=0.0,  # Will be calculated
            reasoning=None,
        )

        # Calculate confidence
        pattern.confidence = self._calculate_confidence(pattern)
        pattern.reasoning = self._generate_reasoning(pattern)

        return pattern

    def _detect_variable_pattern(
        self, merchant: str, txns: list[Transaction]
    ) -> RecurringPattern | None:
        """
        Detect variable amount bill pattern.

        Criteria:
        - Amount varies but within range (mean ± 2*std_dev)
        - Regular cadence
        - Min 3 occurrences
        """
        if len(txns) < self.min_occurrences:
            return None

        sorted_txns = sorted(txns, key=lambda t: t.date)
        amounts = [t.amount for t in sorted_txns]

        # Check if amounts vary (not fixed)
        median_amount = statistics.median(amounts)
        tolerance = max(median_amount * self.amount_tolerance, 0.50)
        is_fixed = all(abs(amt - median_amount) <= tolerance for amt in amounts)

        if is_fixed:
            return None  # Should be detected as fixed, not variable

        # Calculate amount statistics
        mean_amount = statistics.mean(amounts)
        std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0.0
        amount_variance = std_dev / mean_amount if mean_amount > 0 else 0.0

        # Variable bills should have 10-30% variance
        if amount_variance > 0.30:
            return None  # Too much variance (likely not recurring)

        # Calculate range (mean ± 2*std_dev)
        amount_range = (
            max(0, mean_amount - 2 * std_dev),
            mean_amount + 2 * std_dev,
        )

        # Detect cadence
        cadence, date_std_dev = self._detect_cadence(sorted_txns)
        if not cadence:
            return None

        # Skip quarterly/annual for variable patterns (those are IRREGULAR)
        if cadence in [CadenceType.QUARTERLY, CadenceType.ANNUAL]:
            return None

        # Predict next date
        next_date = self._predict_next_date(sorted_txns, cadence)

        pattern = RecurringPattern(
            merchant_name=sorted_txns[0].merchant,
            normalized_merchant=merchant,
            pattern_type=PatternType.VARIABLE,
            cadence=cadence,
            amount=None,
            amount_range=amount_range,
            amount_variance_pct=amount_variance,
            occurrence_count=len(sorted_txns),
            first_date=sorted_txns[0].date,
            last_date=sorted_txns[-1].date,
            next_expected_date=next_date,
            date_std_dev=date_std_dev,
            confidence=0.0,
            reasoning=None,
        )

        pattern.confidence = self._calculate_confidence(pattern)
        pattern.reasoning = self._generate_reasoning(pattern)

        return pattern

    def _detect_irregular_pattern(
        self, merchant: str, txns: list[Transaction]
    ) -> RecurringPattern | None:
        """
        Detect irregular/annual subscription pattern.

        Criteria:
        - Long cadence (quarterly, annual)
        - Amount within tolerance
        - Min 2 occurrences (lower threshold)
        """
        if len(txns) < 2:
            return None

        sorted_txns = sorted(txns, key=lambda t: t.date)
        amounts = [t.amount for t in sorted_txns]

        # Check amount consistency (slightly looser tolerance)
        median_amount = statistics.median(amounts)
        tolerance = max(median_amount * 0.05, 1.00)  # ±5% or ±$1

        if not all(abs(amt - median_amount) <= tolerance for amt in amounts):
            return None

        amount_variance = statistics.stdev(amounts) / median_amount if len(amounts) > 1 else 0.0

        # Detect cadence (quarterly or annual only)
        cadence, date_std_dev = self._detect_cadence(sorted_txns, irregular=True)
        if not cadence or cadence not in [CadenceType.QUARTERLY, CadenceType.ANNUAL]:
            return None

        next_date = self._predict_next_date(sorted_txns, cadence)

        pattern = RecurringPattern(
            merchant_name=sorted_txns[0].merchant,
            normalized_merchant=merchant,
            pattern_type=PatternType.IRREGULAR,
            cadence=cadence,
            amount=median_amount,
            amount_range=None,
            amount_variance_pct=amount_variance,
            occurrence_count=len(sorted_txns),
            first_date=sorted_txns[0].date,
            last_date=sorted_txns[-1].date,
            next_expected_date=next_date,
            date_std_dev=date_std_dev,
            confidence=0.0,
            reasoning=None,
        )

        pattern.confidence = self._calculate_confidence(pattern)
        pattern.reasoning = self._generate_reasoning(pattern)

        return pattern

    def _detect_cadence(
        self, txns: list[Transaction], irregular: bool = False
    ) -> tuple[CadenceType | None, float]:
        """
        Detect recurrence cadence from transaction dates.

        Returns:
            (cadence, std_dev) or (None, 0.0) if no pattern
        """
        if len(txns) < 2:
            return None, 0.0

        # Calculate days between consecutive transactions
        day_diffs = []
        for i in range(len(txns) - 1):
            days = (txns[i + 1].date - txns[i].date).days
            day_diffs.append(days)

        median_days = statistics.median(day_diffs)
        std_dev = statistics.stdev(day_diffs) if len(day_diffs) > 1 else 0.0

        # Detect cadence based on median days
        if 13 <= median_days <= 15:
            return CadenceType.BIWEEKLY, std_dev
        elif 28 <= median_days <= 32:
            return CadenceType.MONTHLY, std_dev
        elif 85 <= median_days <= 95:
            return CadenceType.QUARTERLY, std_dev
        elif 360 <= median_days <= 370:
            return CadenceType.ANNUAL, std_dev

        return None, 0.0

    def _predict_next_date(self, txns: list[Transaction], cadence: CadenceType) -> datetime:
        """Predict next expected transaction date based on cadence."""
        last_date = txns[-1].date

        cadence_days = {
            CadenceType.BIWEEKLY: 14,
            CadenceType.MONTHLY: 30,
            CadenceType.QUARTERLY: 90,
            CadenceType.ANNUAL: 365,
        }

        days = cadence_days.get(cadence, 30)
        return last_date + timedelta(days=days)

    def _calculate_confidence(self, pattern: RecurringPattern) -> float:
        """
        Calculate multi-factor confidence score.

        Base confidence by pattern type:
        - Fixed: 0.90
        - Variable: 0.70
        - Irregular: 0.60

        Adjustments:
        +0.05: Each occurrence beyond minimum (up to +0.10)
        +0.05: Date consistency (std dev < 2 days)
        +0.05: Amount consistency (variance < 1%)
        -0.10: High date variance (std dev > 5 days)
        -0.10: High amount variance (>10%)
        -0.05: Generic merchant name
        """
        # Base confidence
        base_confidence = {
            PatternType.FIXED: 0.90,
            PatternType.VARIABLE: 0.70,
            PatternType.IRREGULAR: 0.60,
        }
        confidence = base_confidence[pattern.pattern_type]

        # Occurrence bonus (more occurrences = higher confidence)
        min_occurrences = 2 if pattern.cadence == CadenceType.ANNUAL else 3
        extra_occurrences = pattern.occurrence_count - min_occurrences
        confidence += min(0.10, extra_occurrences * 0.05)

        # Date consistency bonus/penalty
        if pattern.date_std_dev < 2:
            confidence += 0.05
        elif pattern.date_std_dev > 5:
            confidence -= 0.10

        # Amount consistency bonus/penalty
        if pattern.amount_variance_pct < 0.01:
            confidence += 0.05
        elif pattern.amount_variance_pct > 0.10:
            confidence -= 0.10

        # Generic merchant penalty
        if is_generic_merchant(pattern.normalized_merchant):
            confidence -= 0.05

        return max(0.0, min(1.0, confidence))

    def _generate_reasoning(self, pattern: RecurringPattern) -> str:
        """Generate human-readable reasoning for detection."""
        if pattern.pattern_type == PatternType.FIXED:
            return (
                f"Fixed amount ${pattern.amount:.2f} charged {pattern.cadence.value} "
                f"(±{pattern.date_std_dev:.1f} days variance, "
                f"{pattern.occurrence_count} occurrences)"
            )
        elif pattern.pattern_type == PatternType.VARIABLE:
            min_amt, max_amt = pattern.amount_range or (0, 0)
            return (
                f"Variable amount ${min_amt:.2f}-${max_amt:.2f} charged {pattern.cadence.value} "
                f"({pattern.amount_variance_pct*100:.1f}% variance, "
                f"{pattern.occurrence_count} occurrences)"
            )
        else:  # IRREGULAR
            return (
                f"Irregular {pattern.cadence.value} charge of ${pattern.amount:.2f} "
                f"({pattern.occurrence_count} occurrences)"
            )

    def _is_false_positive(self, pattern: RecurringPattern) -> bool:
        """
        Check if pattern is likely a false positive.

        Criteria:
        - Too few occurrences
        - High variance for "fixed" patterns
        - Irregular date spacing
        - Generic merchant name
        """
        # Too few occurrences
        min_count = 2 if pattern.cadence == CadenceType.ANNUAL else 3
        if pattern.occurrence_count < min_count:
            self.stats["false_positives_filtered"] += 1
            return True

        # High variance for fixed patterns
        if pattern.pattern_type == PatternType.FIXED and pattern.amount_variance_pct > 0.10:
            self.stats["false_positives_filtered"] += 1
            return True

        # Irregular spacing for monthly patterns
        if pattern.cadence == CadenceType.MONTHLY and pattern.date_std_dev > 5:
            self.stats["false_positives_filtered"] += 1
            return True

        # Generic merchant (ATM, Payment, etc.)
        if is_generic_merchant(pattern.normalized_merchant):
            self.stats["false_positives_filtered"] += 1
            return True

        return False

    def get_stats(self) -> dict[str, Any]:
        """Get detection statistics."""
        return dict(self.stats)


class RecurringDetector:
    """
    High-level recurring transaction detector.

    Provides easy-to-use interface for detecting recurring patterns.

    V2: Optional LLM enhancement for merchant normalization (Layer 2),
    variable amount detection (Layer 4), and insights generation (Layer 5).
    """

    def __init__(
        self,
        min_occurrences: int = 3,
        amount_tolerance: float = 0.02,
        date_tolerance_days: int = 7,
        merchant_normalizer: Optional[MerchantNormalizer] = None,
        variable_detector_llm: Optional[VariableDetectorLLM] = None,
        insights_generator: Optional[SubscriptionInsightsGenerator] = None,
    ):
        """
        Initialize recurring detector.

        Args:
            min_occurrences: Minimum transactions to detect pattern (default: 3)
            amount_tolerance: Amount variance tolerance (default: 0.02 = 2%)
            date_tolerance_days: Date clustering tolerance (default: 7 days)
            merchant_normalizer: Optional LLM merchant normalizer (Layer 2, V2)
            variable_detector_llm: Optional LLM variable detector (Layer 4, V2)
            insights_generator: Optional LLM insights generator (Layer 5, V2)
        """
        self.detector = PatternDetector(
            min_occurrences=min_occurrences,
            amount_tolerance=amount_tolerance,
            date_tolerance_days=date_tolerance_days,
            merchant_normalizer=merchant_normalizer,
            variable_detector_llm=variable_detector_llm,
        )
        self.insights_generator = insights_generator

    def detect_patterns(self, transactions: list[dict]) -> list[RecurringPattern]:
        """
        Detect recurring patterns from transaction data.

        Args:
            transactions: List of transaction dicts with keys:
                         {id, merchant, amount, date}

        Returns:
            List of RecurringPattern objects
        """
        # Convert dicts to Transaction objects
        txn_objects = []
        for txn in transactions:
            txn_objects.append(
                Transaction(
                    id=txn.get("id", ""),
                    merchant=txn["merchant"],
                    amount=float(txn["amount"]),
                    date=txn["date"]
                    if isinstance(txn["date"], datetime)
                    else datetime.fromisoformat(txn["date"]),
                )
            )

        return self.detector.detect(txn_objects)

    def get_stats(self) -> dict[str, Any]:
        """Get detection statistics."""
        return self.detector.get_stats()
