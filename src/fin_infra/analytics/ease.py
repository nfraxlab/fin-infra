"""Easy setup for analytics module.

Provides one-line setup with sensible defaults for all analytics capabilities:
cash flow, savings rate, spending insights, portfolio analytics, and growth projections.

Typical usage:
    analytics = easy_analytics()

    # Cash flow analysis
    cash_flow = await analytics.cash_flow(user_id="user123")

    # Savings rate
    savings = await analytics.savings_rate(user_id="user123")

    # Portfolio metrics
    portfolio = await analytics.portfolio_metrics(user_id="user123")
"""

from typing import Optional
from datetime import datetime, timedelta

from .cash_flow import calculate_cash_flow
from .savings import calculate_savings_rate, SavingsDefinition
from .spending import analyze_spending, generate_spending_insights
from .portfolio import calculate_portfolio_metrics, compare_to_benchmark
from .projections import project_net_worth, calculate_compound_interest
from .models import (
    CashFlowAnalysis,
    SavingsRateData,
    SpendingInsight,
    PersonalizedSpendingAdvice,
    PortfolioMetrics,
    BenchmarkComparison,
    GrowthProjection,
)


class AnalyticsEngine:
    """Unified analytics engine providing all analytics capabilities.

    This class provides a clean interface to all analytics functions with
    configured defaults and optional provider integrations.

    Attributes:
        default_period_days: Default analysis period (30 days)
        default_savings_definition: Default savings calculation method
        default_benchmark: Default portfolio benchmark (SPY)
        cache_ttl: Cache TTL for expensive operations (3600s = 1h)
    """

    def __init__(
        self,
        *,
        default_period_days: int = 30,
        default_savings_definition: SavingsDefinition = SavingsDefinition.NET,
        default_benchmark: str = "SPY",
        cache_ttl: int = 3600,
        banking_provider=None,
        brokerage_provider=None,
        categorization_provider=None,
        recurring_provider=None,
        net_worth_provider=None,
        market_provider=None,
    ):
        """Initialize analytics engine with configuration.

        Args:
            default_period_days: Default period for analyses (default: 30 days)
            default_savings_definition: Default savings calculation method
            default_benchmark: Default portfolio benchmark symbol (default: SPY)
            cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
            banking_provider: Optional banking data provider
            brokerage_provider: Optional brokerage data provider
            categorization_provider: Optional transaction categorization provider
            recurring_provider: Optional recurring transaction detector
            net_worth_provider: Optional net worth calculator
            market_provider: Optional market data provider
        """
        self.default_period_days = default_period_days
        self.default_savings_definition = default_savings_definition
        self.default_benchmark = default_benchmark
        self.cache_ttl = cache_ttl

        # Store providers for future use
        self.banking_provider = banking_provider
        self.brokerage_provider = brokerage_provider
        self.categorization_provider = categorization_provider
        self.recurring_provider = recurring_provider
        self.net_worth_provider = net_worth_provider
        self.market_provider = market_provider

    async def cash_flow(
        self,
        user_id: str,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period_days: Optional[int] = None,
    ) -> CashFlowAnalysis:
        """Analyze cash flow (income vs expenses).

        Args:
            user_id: User identifier
            start_date: Period start (default: period_days ago)
            end_date: Period end (default: today)
            period_days: Analysis period (default: self.default_period_days)

        Returns:
            CashFlowAnalysis with income, expenses, and net flow
        """
        if period_days is None:
            period_days = self.default_period_days

        if end_date is None:
            end_date = datetime.now()

        if start_date is None:
            start_date = end_date - timedelta(days=period_days)

        return await calculate_cash_flow(
            user_id,
            start_date=start_date,
            end_date=end_date,
            banking_provider=self.banking_provider,
            categorization_provider=self.categorization_provider,
        )

    async def savings_rate(
        self,
        user_id: str,
        *,
        definition: Optional[str | SavingsDefinition] = None,
        period: str = "monthly",
    ) -> SavingsRateData:
        """Calculate savings rate.

        Args:
            user_id: User identifier
            definition: Savings calculation method (default: self.default_savings_definition).
                       Can be string ("gross", "net", "discretionary") or SavingsDefinition enum.
            period: Analysis period ("monthly", "quarterly", "annual")

        Returns:
            SavingsRateData with rate, amounts, and trend
        """
        if definition is None:
            definition = self.default_savings_definition

        # Convert enum to string if needed (calculate_savings_rate accepts strings)
        definition_str = (
            definition.value if isinstance(definition, SavingsDefinition) else definition
        )

        return await calculate_savings_rate(
            user_id,
            definition=definition_str,
            period=period,
            banking_provider=self.banking_provider,
            categorization_provider=self.categorization_provider,
        )

    async def spending_insights(
        self,
        user_id: str,
        *,
        period_days: Optional[int] = None,
        include_trends: bool = True,
    ) -> SpendingInsight:
        """Analyze spending patterns and generate insights.

        Args:
            user_id: User identifier
            period_days: Analysis period (default: self.default_period_days)
            include_trends: Include trend analysis (default: True)

        Returns:
            SpendingInsight with patterns, anomalies, trends
        """
        if period_days is None:
            period_days = self.default_period_days

        # Convert period_days to period string format (e.g., "30d")
        period = f"{period_days}d"

        return await analyze_spending(
            user_id,
            period=period,
            banking_provider=self.banking_provider,
            categorization_provider=self.categorization_provider,
        )

    async def spending_advice(
        self,
        user_id: str,
        *,
        period_days: Optional[int] = None,
        user_context: Optional[dict] = None,
    ) -> PersonalizedSpendingAdvice:
        """Generate AI-powered personalized spending advice.

        Args:
            user_id: User identifier
            period_days: Analysis period (default: self.default_period_days)
            user_context: Optional user context (income, goals, etc.)

        Returns:
            PersonalizedSpendingAdvice with recommendations
        """
        if period_days is None:
            period_days = self.default_period_days

        # First get spending insights
        period = f"{period_days}d"
        spending_insight = await analyze_spending(
            user_id,
            period=period,
            banking_provider=self.banking_provider,
            categorization_provider=self.categorization_provider,
        )

        # Then generate personalized advice
        return await generate_spending_insights(
            spending_insight,
            user_context=user_context,
        )

    async def portfolio_metrics(
        self,
        user_id: str,
        *,
        accounts: Optional[list[str]] = None,
    ) -> PortfolioMetrics:
        """Calculate portfolio performance metrics.

        Args:
            user_id: User identifier
            accounts: Optional list of account IDs to include

        Returns:
            PortfolioMetrics with value, returns, allocation
        """
        return await calculate_portfolio_metrics(
            user_id,
            accounts=accounts,
            brokerage_provider=self.brokerage_provider,
            market_provider=self.market_provider,
        )

    async def benchmark_comparison(
        self,
        user_id: str,
        *,
        benchmark: Optional[str] = None,
        period: str = "1y",
        accounts: Optional[list[str]] = None,
    ) -> BenchmarkComparison:
        """Compare portfolio to benchmark index.

        Args:
            user_id: User identifier
            benchmark: Benchmark symbol (default: self.default_benchmark)
            period: Comparison period ("1y", "3y", "5y", "ytd", "max")
            accounts: Optional list of account IDs to include

        Returns:
            BenchmarkComparison with alpha, beta, returns
        """
        if benchmark is None:
            benchmark = self.default_benchmark

        return await compare_to_benchmark(
            user_id,
            benchmark=benchmark,
            period=period,
            accounts=accounts,
            brokerage_provider=self.brokerage_provider,
            market_provider=self.market_provider,
        )

    async def net_worth_projection(
        self,
        user_id: str,
        *,
        years: int = 30,
        assumptions: Optional[dict] = None,
    ) -> GrowthProjection:
        """Project net worth growth with scenarios.

        Args:
            user_id: User identifier
            years: Projection period in years (default: 30)
            assumptions: Optional custom assumptions (returns, inflation, etc.)

        Returns:
            GrowthProjection with scenarios and confidence intervals
        """
        return await project_net_worth(
            user_id,
            years=years,
            assumptions=assumptions,
            net_worth_provider=self.net_worth_provider,
            cash_flow_provider=self.banking_provider,
        )

    @staticmethod
    def compound_interest(
        principal: float,
        rate: float,
        periods: int,
        contribution: float = 0,
    ) -> float:
        """Calculate compound interest (utility method).

        Args:
            principal: Initial investment
            rate: Interest rate per period
            periods: Number of periods
            contribution: Periodic contribution

        Returns:
            Future value
        """
        return calculate_compound_interest(principal, rate, periods, contribution)


def easy_analytics(
    *,
    default_period_days: int = 30,
    default_savings_definition: SavingsDefinition = SavingsDefinition.NET,
    default_benchmark: str = "SPY",
    cache_ttl: int = 3600,
    banking_provider=None,
    brokerage_provider=None,
    categorization_provider=None,
    recurring_provider=None,
    net_worth_provider=None,
    market_provider=None,
) -> AnalyticsEngine:
    """Easy setup for analytics with sensible defaults.

    One-liner to get started:
        analytics = easy_analytics()
        cash_flow = await analytics.cash_flow(user_id="user123")

    With custom configuration:
        analytics = easy_analytics(
            default_period_days=90,
            default_benchmark="QQQ",
            cache_ttl=7200,
        )

    With provider integrations:
        analytics = easy_analytics(
            banking_provider=plaid,
            brokerage_provider=alpaca,
            categorization_provider=mx_categorizer,
        )

    Args:
        default_period_days: Default analysis period (default: 30 days)
        default_savings_definition: Savings calculation method (default: NET_SAVINGS)
        default_benchmark: Portfolio benchmark symbol (default: SPY)
        cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
        banking_provider: Optional banking data provider (Plaid, Teller, MX)
        brokerage_provider: Optional brokerage provider (Alpaca, IB)
        categorization_provider: Optional categorization engine
        recurring_provider: Optional recurring transaction detector
        net_worth_provider: Optional net worth calculator
        market_provider: Optional market data provider

    Returns:
        Configured AnalyticsEngine instance

    Examples:
        >>> # Basic usage
        >>> analytics = easy_analytics()
        >>> cash_flow = await analytics.cash_flow("user123")
        >>> savings = await analytics.savings_rate("user123")
        >>> portfolio = await analytics.portfolio_metrics("user123")

        >>> # Custom defaults
        >>> analytics = easy_analytics(
        ...     default_period_days=90,
        ...     default_benchmark="VTI",
        ... )
        >>> projection = await analytics.net_worth_projection("user123", years=40)

        >>> # With providers
        >>> from fin_infra.banking import easy_banking
        >>> from fin_infra.categorization import easy_categorization
        >>>
        >>> banking = easy_banking(provider="plaid")
        >>> categorizer = easy_categorization()
        >>>
        >>> analytics = easy_analytics(
        ...     banking_provider=banking,
        ...     categorization_provider=categorizer,
        ... )

    Generic use cases:
        - Personal finance apps: Complete analytics suite
        - Wealth management: Client portfolio & planning analysis
        - Investment platforms: Performance tracking & projections
        - Banking apps: Cash flow & savings insights
        - Budgeting tools: Spending analysis & recommendations
        - Financial advisors: Comprehensive client analytics
        - Robo-advisors: Automated portfolio & goal analysis
    """
    return AnalyticsEngine(
        default_period_days=default_period_days,
        default_savings_definition=default_savings_definition,
        default_benchmark=default_benchmark,
        cache_ttl=cache_ttl,
        banking_provider=banking_provider,
        brokerage_provider=brokerage_provider,
        categorization_provider=categorization_provider,
        recurring_provider=recurring_provider,
        net_worth_provider=net_worth_provider,
        market_provider=market_provider,
    )
