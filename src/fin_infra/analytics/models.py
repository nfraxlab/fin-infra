"""Pydantic models for analytics module.

All models use keyword-only arguments for cache key stability.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SavingsDefinition(str, Enum):
    """Savings rate calculation method."""

    GROSS = "gross"  # (Income - Expenses) / Income
    NET = "net"  # (Income - Taxes - Expenses) / (Income - Taxes)
    DISCRETIONARY = "discretionary"  # (Income - Fixed Expenses) / Income


class Period(str, Enum):
    """Time period for analysis."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TrendDirection(str, Enum):
    """Trend direction indicator."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class CashFlowAnalysis(BaseModel):
    """Cash flow analysis result.

    Keyword-only args for cache key stability.
    """

    model_config = ConfigDict(extra="forbid")

    income_total: float = Field(..., description="Total income for period")
    expense_total: float = Field(..., description="Total expenses for period")
    net_cash_flow: float = Field(..., description="Net cash flow (income - expenses)")
    income_by_source: dict[str, float] = Field(
        default_factory=dict, description="Income breakdown by source"
    )
    expenses_by_category: dict[str, float] = Field(
        default_factory=dict, description="Expenses breakdown by category"
    )
    period_start: datetime = Field(..., description="Analysis period start date")
    period_end: datetime = Field(..., description="Analysis period end date")


class SavingsRateData(BaseModel):
    """Savings rate calculation result.

    Keyword-only args for cache key stability.
    """

    model_config = ConfigDict(extra="forbid")

    savings_rate: float = Field(..., ge=0.0, le=1.0, description="Savings rate (0-1)")
    savings_amount: float = Field(..., description="Amount saved in period")
    income: float = Field(..., description="Total income for period")
    expenses: float = Field(..., description="Total expenses for period")
    period: Period = Field(..., description="Period type")
    definition: SavingsDefinition = Field(..., description="Calculation method used")
    trend: Optional[TrendDirection] = Field(None, description="Trend over time")


class SpendingAnomaly(BaseModel):
    """Spending anomaly detection result."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., description="Category with anomaly")
    current_amount: float = Field(..., description="Current period spending")
    average_amount: float = Field(..., description="Historical average spending")
    deviation_percent: float = Field(..., description="Deviation from average (%)")
    severity: str = Field(..., description="minor, moderate, or severe")


class SpendingInsight(BaseModel):
    """Spending insights and patterns.

    Keyword-only args for cache key stability.
    """

    model_config = ConfigDict(extra="forbid")

    top_merchants: list[tuple[str, float]] = Field(
        default_factory=list, description="Top merchants by spending [(merchant, amount)]"
    )
    category_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Spending by category"
    )
    spending_trends: dict[str, TrendDirection] = Field(
        default_factory=dict, description="Trends by category"
    )
    anomalies: list[SpendingAnomaly] = Field(
        default_factory=list, description="Detected spending anomalies"
    )
    period_days: int = Field(..., description="Analysis period in days")
    total_spending: float = Field(..., description="Total spending for period")


class PersonalizedSpendingAdvice(BaseModel):
    """LLM-generated personalized spending advice.

    Uses ai-infra CoreLLM for structured output generation.
    """

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., description="Overall spending summary in 1-2 sentences")
    key_observations: list[str] = Field(
        ..., description="3-5 key observations about spending patterns"
    )
    savings_opportunities: list[str] = Field(
        ..., description="Specific recommendations to reduce spending"
    )
    positive_habits: list[str] = Field(
        default_factory=list, description="Good spending habits to maintain"
    )
    alerts: list[str] = Field(
        default_factory=list, description="Urgent spending issues requiring attention"
    )
    estimated_monthly_savings: Optional[float] = Field(
        None, description="Potential monthly savings if recommendations followed"
    )


class AssetAllocation(BaseModel):
    """Asset allocation breakdown."""

    model_config = ConfigDict(extra="forbid")

    asset_class: str = Field(..., description="Asset class name (stocks, bonds, cash, etc.)")
    value: float = Field(..., description="Total value in this asset class")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of portfolio")


class PortfolioMetrics(BaseModel):
    """Portfolio performance metrics.

    Keyword-only args for cache key stability.
    """

    model_config = ConfigDict(extra="forbid")

    total_value: float = Field(..., description="Total portfolio value")
    total_return: float = Field(..., description="Total return (all-time)")
    total_return_percent: float = Field(..., description="Total return percentage")
    ytd_return: float = Field(..., description="Year-to-date return")
    ytd_return_percent: float = Field(..., description="YTD return percentage")
    mtd_return: float = Field(..., description="Month-to-date return")
    mtd_return_percent: float = Field(..., description="MTD return percentage")
    day_change: float = Field(..., description="Today's change")
    day_change_percent: float = Field(..., description="Today's change percentage")
    allocation_by_asset_class: list[AssetAllocation] = Field(
        default_factory=list, description="Asset allocation breakdown"
    )


class BenchmarkComparison(BaseModel):
    """Portfolio performance vs benchmark.

    Keyword-only args for cache key stability.
    """

    model_config = ConfigDict(extra="forbid")

    portfolio_return: float = Field(..., description="Portfolio return for period")
    portfolio_return_percent: float = Field(..., description="Portfolio return percentage")
    benchmark_return: float = Field(..., description="Benchmark return for period")
    benchmark_return_percent: float = Field(..., description="Benchmark return percentage")
    benchmark_symbol: str = Field(..., description="Benchmark ticker (e.g., SPY)")
    alpha: float = Field(..., description="Portfolio alpha (excess return)")
    beta: Optional[float] = Field(None, description="Portfolio beta (volatility vs benchmark)")
    period: str = Field(..., description="Comparison period (1y, 3y, 5y, etc.)")


class Scenario(BaseModel):
    """Growth projection scenario."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Scenario name (conservative, moderate, aggressive)")
    expected_return: float = Field(..., description="Expected annual return rate")
    projected_values: list[float] = Field(..., description="Projected values by year")
    final_value: float = Field(..., description="Final projected value")


class GrowthProjection(BaseModel):
    """Net worth growth projection with scenarios.

    Keyword-only args for cache key stability.
    """

    model_config = ConfigDict(extra="forbid")

    current_net_worth: float = Field(..., description="Current net worth")
    years: int = Field(..., description="Projection period in years")
    monthly_contribution: float = Field(..., description="Monthly contribution amount")
    scenarios: list[Scenario] = Field(..., description="Projection scenarios")
    assumptions: dict[str, Any] = Field(
        default_factory=dict, description="Assumptions used (inflation, returns, etc.)"
    )
    confidence_intervals: Optional[dict[str, tuple[float, float]]] = Field(
        None, description="95% confidence intervals by scenario"
    )
