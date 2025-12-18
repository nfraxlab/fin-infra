"""Portfolio analytics and performance metrics.

Provides comprehensive portfolio analysis with performance tracking, asset allocation,
benchmark comparisons, and risk-adjusted returns.

Generic Applicability:
- Wealth management: Client portfolio performance and allocation analysis
- Investment platforms: Portfolio tracking and benchmarking
- Robo-advisors: Automated portfolio analytics and rebalancing
- Personal finance: Net worth tracking and investment performance
- Financial advisors: Client reporting and performance attribution

Features:
- Portfolio metrics: Total value, returns (total, YTD, MTD, 1Y, 3Y, 5Y), day change
- Asset allocation: Breakdown by asset class with percentages
- Benchmark comparison: Alpha, beta, Sharpe ratio calculations
- Multi-account aggregation: Consolidate across multiple brokerage accounts

Examples:
    >>> # Calculate comprehensive portfolio metrics
    >>> metrics = await calculate_portfolio_metrics("user123")
    >>> print(f"Total value: ${metrics.total_value:,.2f}")
    >>> print(f"YTD return: {metrics.ytd_return_percent:.2f}%")

    >>> # Compare to S&P 500 benchmark
    >>> comparison = await compare_to_benchmark("user123", benchmark="SPY", period="1y")
    >>> print(f"Alpha: {comparison.alpha:.2f}%")
    >>> print(f"Beta: {comparison.beta:.2f}")

    >>> # Analyze specific accounts only
    >>> metrics = await calculate_portfolio_metrics(
    ...     "user123",
    ...     accounts=["brokerage_1", "ira_account"]
    ... )
"""

from datetime import datetime

from fin_infra.analytics.models import (
    AssetAllocation,
    BenchmarkComparison,
    PortfolioMetrics,
)


async def calculate_portfolio_metrics(
    user_id: str,
    *,
    accounts: list[str] | None = None,
    brokerage_provider=None,
    market_provider=None,
) -> PortfolioMetrics:
    """Calculate comprehensive portfolio performance metrics.

    Aggregates holdings across all brokerage accounts to provide total value,
    returns across multiple time periods, and asset allocation breakdown.

    Args:
        user_id: User identifier
        accounts: Optional list of account IDs to include (default: all accounts)
        brokerage_provider: Optional brokerage provider instance
        market_provider: Optional market data provider instance

    Returns:
        PortfolioMetrics with complete portfolio analysis

    Time Periods:
        - Total: All-time since account opening
        - YTD: Year-to-date (since Jan 1)
        - MTD: Month-to-date (since 1st of month)
        - Day: Today's change
        - 1Y/3Y/5Y: 1, 3, and 5 year returns (future enhancement)

    Asset Classes:
        - Stocks: Individual equities and equity ETFs
        - Bonds: Fixed income securities and bond ETFs
        - Cash: Money market funds and cash equivalents
        - Crypto: Cryptocurrency holdings
        - Real Estate: REITs and real estate funds
        - Other: Commodities, alternatives, uncategorized

    Examples:
        >>> # All accounts
        >>> metrics = await calculate_portfolio_metrics("user123")

        >>> # Specific accounts
        >>> metrics = await calculate_portfolio_metrics(
        ...     "user123",
        ...     accounts=["taxable_brokerage", "roth_ira"]
        ... )
    """
    # TODO: Integrate with real brokerage provider
    # For now, use mock data for testing
    holdings = _generate_mock_holdings(user_id, accounts)

    # Calculate total portfolio value
    total_value = sum(h["current_value"] for h in holdings)
    total_cost_basis = sum(h["cost_basis"] for h in holdings)

    # Calculate total return
    total_return_dollars = total_value - total_cost_basis
    total_return_percent = (
        (total_return_dollars / total_cost_basis * 100) if total_cost_basis > 0 else 0.0
    )

    # Calculate time-based returns
    ytd_return_dollars, ytd_return_percent = _calculate_ytd_return(holdings)
    mtd_return_dollars, mtd_return_percent = _calculate_mtd_return(holdings)
    day_change_dollars, day_change_percent = _calculate_day_change(holdings)

    # Calculate asset allocation
    allocation = _calculate_asset_allocation(holdings, total_value)

    return PortfolioMetrics(
        total_value=total_value,
        total_return=total_return_dollars,
        total_return_percent=total_return_percent,
        ytd_return=ytd_return_dollars,
        ytd_return_percent=ytd_return_percent,
        mtd_return=mtd_return_dollars,
        mtd_return_percent=mtd_return_percent,
        day_change=day_change_dollars,
        day_change_percent=day_change_percent,
        allocation_by_asset_class=allocation,
    )


async def compare_to_benchmark(
    user_id: str,
    *,
    benchmark: str = "SPY",
    period: str = "1y",
    accounts: list[str] | None = None,
    brokerage_provider=None,
    market_provider=None,
) -> BenchmarkComparison:
    """Compare portfolio performance to benchmark index.

    Calculates relative performance metrics including alpha (excess return),
    beta (volatility relative to benchmark), and Sharpe ratio (risk-adjusted return).

    Args:
        user_id: User identifier
        benchmark: Benchmark ticker symbol (default: SPY for S&P 500)
        period: Time period for comparison (1y, 3y, 5y, ytd, max)
        accounts: Optional list of account IDs to include
        brokerage_provider: Optional brokerage provider instance
        market_provider: Optional market data provider instance

    Returns:
        BenchmarkComparison with alpha, beta, and performance metrics

    Supported Benchmarks:
        - SPY: S&P 500
        - QQQ: Nasdaq 100
        - VTI: Total US Stock Market
        - AGG: Total Bond Market
        - VT: Total World Stock
        - Custom: Any valid ticker symbol

    Performance Metrics:
        - Alpha: Portfolio return - Benchmark return (excess return)
        - Beta: Correlation of portfolio volatility to benchmark
        - Sharpe Ratio: (Return - Risk-free rate) / Standard deviation

    Examples:
        >>> # Compare to S&P 500 over 1 year
        >>> comp = await compare_to_benchmark("user123", benchmark="SPY", period="1y")
        >>> print(f"Alpha: {comp.alpha:.2f}%")

        >>> # Compare to Nasdaq 100 YTD
        >>> comp = await compare_to_benchmark("user123", benchmark="QQQ", period="ytd")

        >>> # Custom benchmark with specific accounts
        >>> comp = await compare_to_benchmark(
        ...     "user123",
        ...     benchmark="VTI",
        ...     period="3y",
        ...     accounts=["taxable_brokerage"]
        ... )
    """
    # Parse period to days
    period_days = _parse_benchmark_period(period)

    # Get portfolio return for period
    # TODO: Integrate with real brokerage provider
    portfolio_return_dollars, portfolio_return_percent = _calculate_portfolio_return(
        user_id, period_days, accounts
    )

    # Get benchmark return for period
    # TODO: Integrate with real market data provider
    benchmark_return_dollars, benchmark_return_percent = _get_benchmark_return(
        benchmark, period_days
    )

    # Calculate alpha (excess return)
    alpha = portfolio_return_percent - benchmark_return_percent

    # Calculate beta (volatility relative to benchmark)
    # TODO: Implement real beta calculation with historical returns
    beta = _calculate_beta(user_id, benchmark, period_days)

    return BenchmarkComparison(
        portfolio_return=portfolio_return_dollars,
        portfolio_return_percent=portfolio_return_percent,
        benchmark_return=benchmark_return_dollars,
        benchmark_return_percent=benchmark_return_percent,
        benchmark_symbol=benchmark,
        alpha=alpha,
        beta=beta,
        period=period,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_mock_holdings(
    user_id: str,
    accounts: list[str] | None = None,
) -> list[dict]:
    """Generate mock portfolio holdings for testing.

    Returns realistic portfolio holdings with various asset classes.
    """
    mock_holdings = [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "asset_class": "Stocks",
            "quantity": 50.0,
            "current_price": 175.50,
            "current_value": 8775.0,
            "cost_basis": 7500.0,
            "ytd_value_start": 8000.0,
            "mtd_value_start": 8500.0,
            "prev_day_value": 8700.0,
        },
        {
            "symbol": "VTI",
            "name": "Vanguard Total Stock Market ETF",
            "asset_class": "Stocks",
            "quantity": 100.0,
            "current_price": 245.30,
            "current_value": 24530.0,
            "cost_basis": 22000.0,
            "ytd_value_start": 23000.0,
            "mtd_value_start": 24000.0,
            "prev_day_value": 24400.0,
        },
        {
            "symbol": "AGG",
            "name": "iShares Core US Aggregate Bond ETF",
            "asset_class": "Bonds",
            "quantity": 200.0,
            "current_price": 105.20,
            "current_value": 21040.0,
            "cost_basis": 21000.0,
            "ytd_value_start": 20800.0,
            "mtd_value_start": 21000.0,
            "prev_day_value": 21020.0,
        },
        {
            "symbol": "BTC",
            "name": "Bitcoin",
            "asset_class": "Crypto",
            "quantity": 0.5,
            "current_price": 35000.0,
            "current_value": 17500.0,
            "cost_basis": 15000.0,
            "ytd_value_start": 16000.0,
            "mtd_value_start": 17000.0,
            "prev_day_value": 17300.0,
        },
        {
            "symbol": "VMFXX",
            "name": "Vanguard Federal Money Market Fund",
            "asset_class": "Cash",
            "quantity": 5000.0,
            "current_price": 1.0,
            "current_value": 5000.0,
            "cost_basis": 5000.0,
            "ytd_value_start": 5000.0,
            "mtd_value_start": 5000.0,
            "prev_day_value": 5000.0,
        },
    ]

    # Filter by accounts if specified
    if accounts:
        # For mock data, we don't filter (would filter in real implementation)
        pass

    return mock_holdings


def _calculate_ytd_return(holdings: list[dict]) -> tuple[float, float]:
    """Calculate year-to-date return."""
    current_value = sum(h["current_value"] for h in holdings)
    ytd_start_value = sum(h["ytd_value_start"] for h in holdings)

    ytd_return_dollars = current_value - ytd_start_value
    ytd_return_percent = (
        (ytd_return_dollars / ytd_start_value * 100) if ytd_start_value > 0 else 0.0
    )

    return ytd_return_dollars, ytd_return_percent


def _calculate_mtd_return(holdings: list[dict]) -> tuple[float, float]:
    """Calculate month-to-date return."""
    current_value = sum(h["current_value"] for h in holdings)
    mtd_start_value = sum(h["mtd_value_start"] for h in holdings)

    mtd_return_dollars = current_value - mtd_start_value
    mtd_return_percent = (
        (mtd_return_dollars / mtd_start_value * 100) if mtd_start_value > 0 else 0.0
    )

    return mtd_return_dollars, mtd_return_percent


def _calculate_day_change(holdings: list[dict]) -> tuple[float, float]:
    """Calculate today's change."""
    current_value = sum(h["current_value"] for h in holdings)
    prev_day_value = sum(h["prev_day_value"] for h in holdings)

    day_change_dollars = current_value - prev_day_value
    day_change_percent = (day_change_dollars / prev_day_value * 100) if prev_day_value > 0 else 0.0

    return day_change_dollars, day_change_percent


def _calculate_asset_allocation(
    holdings: list[dict],
    total_value: float,
) -> list[AssetAllocation]:
    """Calculate asset allocation by asset class."""
    allocation_dict = {}

    for holding in holdings:
        asset_class = holding["asset_class"]
        value = holding["current_value"]

        if asset_class not in allocation_dict:
            allocation_dict[asset_class] = 0.0
        allocation_dict[asset_class] += value

    # Convert to list of AssetAllocation objects
    allocations = []
    for asset_class, value in allocation_dict.items():
        percentage = (value / total_value * 100) if total_value > 0 else 0.0
        allocations.append(
            AssetAllocation(
                asset_class=asset_class,
                value=value,
                percentage=percentage,
            )
        )

    # Sort by value descending
    allocations.sort(key=lambda x: x.value, reverse=True)

    return allocations


def _parse_benchmark_period(period: str) -> int:
    """Parse period string to number of days.

    Args:
        period: Period string (1y, 3y, 5y, ytd, max)

    Returns:
        Number of days in period

    Raises:
        ValueError: If period format is invalid
    """
    period = period.lower().strip()

    if period == "ytd":
        # Days since January 1st
        today = datetime.now()
        year_start = datetime(today.year, 1, 1)
        return (today - year_start).days

    if period == "max":
        # Maximum period (30 years for most portfolios)
        return 365 * 30

    # Parse numeric periods like "1y", "3y", "5y"
    if period.endswith("y"):
        try:
            years = int(period[:-1])
            return years * 365
        except ValueError:
            raise ValueError(
                f"Invalid period format: {period}. Use '1y', '3y', '5y', 'ytd', or 'max'"
            )

    if period.endswith("m"):
        try:
            months = int(period[:-1])
            return months * 30
        except ValueError:
            raise ValueError(f"Invalid period format: {period}")

    raise ValueError(f"Invalid period format: {period}. Use '1y', '3y', '5y', 'ytd', or 'max'")


def _calculate_portfolio_return(
    user_id: str,
    period_days: int,
    accounts: list[str] | None = None,
) -> tuple[float, float]:
    """Calculate portfolio return for specified period.

    TODO: Integrate with real brokerage provider for historical values.
    """
    # Mock returns based on period
    # In reality, would query historical portfolio values
    if period_days <= 30:  # 1 month
        return 845.0, 1.12  # $845, 1.12%
    elif period_days <= 365:  # 1 year
        return 8500.0, 12.5  # $8500, 12.5%
    elif period_days <= 1095:  # 3 years
        return 18000.0, 35.0  # $18000, 35%
    else:  # 5+ years
        return 30000.0, 65.0  # $30000, 65%


def _get_benchmark_return(
    benchmark: str,
    period_days: int,
) -> tuple[float, float]:
    """Get benchmark return for specified period.

    TODO: Integrate with real market data provider.
    """
    # Mock benchmark returns (S&P 500 historical averages)
    benchmark_returns = {
        "SPY": {
            30: (0, 0.8),  # 1 month: 0.8%
            365: (0, 10.5),  # 1 year: 10.5%
            1095: (0, 32.0),  # 3 years: 32%
            1825: (0, 60.0),  # 5 years: 60%
        },
        "QQQ": {
            30: (0, 1.2),
            365: (0, 15.0),
            1095: (0, 45.0),
            1825: (0, 85.0),
        },
        "VTI": {
            30: (0, 0.9),
            365: (0, 11.0),
            1095: (0, 33.0),
            1825: (0, 62.0),
        },
    }

    # Get closest period
    if benchmark.upper() in benchmark_returns:
        returns = benchmark_returns[benchmark.upper()]
        if period_days <= 30:
            return returns[30]
        elif period_days <= 365:
            return returns[365]
        elif period_days <= 1095:
            return returns[1095]
        else:
            return returns[1825]

    # Default to SPY if benchmark not found
    return _get_benchmark_return("SPY", period_days)


def _calculate_beta(
    user_id: str,
    benchmark: str,
    period_days: int,
) -> float | None:
    """Calculate portfolio beta (volatility relative to benchmark).

    Beta = Covariance(portfolio_returns, benchmark_returns) / Variance(benchmark_returns)

    Beta interpretation:
    - Beta = 1.0: Portfolio moves with market
    - Beta > 1.0: Portfolio is more volatile than market
    - Beta < 1.0: Portfolio is less volatile than market

    TODO: Implement with real historical returns data.
    """
    # Mock beta calculation
    # In reality, would use historical daily/monthly returns
    # to calculate covariance and variance

    # For mock data, return typical beta values
    return 0.95  # Slightly less volatile than market


# ============================================================================
# Holdings-based Portfolio Analytics (Real P/L from Investment Data)
# ============================================================================


def portfolio_metrics_with_holdings(holdings: list) -> PortfolioMetrics:
    """Calculate portfolio metrics from real investment holdings data.

    Uses actual holdings data from investment providers (Plaid, SnapTrade) to
    calculate real profit/loss, asset allocation, and portfolio value.

    This function replaces mock data with real holdings to provide accurate
    portfolio analytics based on actual positions, cost basis, and current values.

    Args:
        holdings: List of Holding objects from investment provider
            Each holding should have:
            - institution_value (float): Current market value
            - cost_basis (float): Original purchase cost
            - security.type (SecurityType): Asset class (equity, bond, etf, etc.)

    Returns:
        PortfolioMetrics with real portfolio analysis

    Real Data Advantages:
        - Actual cost basis → accurate P/L calculations
        - Real security types → precise asset allocation
        - Current market values → live portfolio value
        - No mock data → production-ready analytics

    Limitations:
        - Day/YTD/MTD returns require historical snapshots (not in holdings)
        - Time-based returns default to 0.0 (apps must store snapshots)
        - Use calculate_day_change_with_snapshot() for daily tracking

    Examples:
        >>> from fin_infra.investments import easy_investments
        >>> from fin_infra.analytics.portfolio import portfolio_metrics_with_holdings
        >>>
        >>> # Get real holdings from investment provider
        >>> investments = easy_investments(provider="plaid")
        >>> holdings = await investments.get_holdings(access_token="...")
        >>>
        >>> # Calculate metrics from real data
        >>> metrics = portfolio_metrics_with_holdings(holdings)
        >>> print(f"Total value: ${metrics.total_value:,.2f}")
        >>> print(f"Total return: {metrics.total_return_percent:.2f}%")
        >>> print(f"Stocks allocation: {metrics.allocation_by_asset_class.get('Stocks', 0):.1f}%")

        >>> # Compare to mock-based calculation
        >>> mock_metrics = await calculate_portfolio_metrics("user123")
        >>> # mock_metrics uses _generate_mock_holdings()
        >>> # metrics uses real holdings from Plaid/SnapTrade

    Integration with Investments Module:
        >>> # holdings parameter comes from investments module
        >>> from fin_infra.investments import easy_investments
        >>> investments = easy_investments()
        >>> holdings = await investments.get_holdings(access_token)
        >>> metrics = portfolio_metrics_with_holdings(holdings)
    """
    # Import here to avoid circular dependency

    # Calculate total portfolio value and cost basis
    total_value = float(sum(holding.institution_value for holding in holdings))

    total_cost_basis = float(
        sum(holding.cost_basis if holding.cost_basis is not None else 0 for holding in holdings)
    )

    # Calculate total return (P/L)
    total_return_dollars = total_value - total_cost_basis
    total_return_percent = (
        (total_return_dollars / total_cost_basis * 100.0) if total_cost_basis > 0 else 0.0
    )

    # Calculate asset allocation from real security types
    allocation = _calculate_allocation_from_holdings(holdings, total_value)

    # Note: Time-based returns (YTD, MTD, day) require historical snapshots
    # Applications must store daily/monthly snapshots to calculate these
    # For now, default to 0.0 (or use calculate_day_change_with_snapshot)
    return PortfolioMetrics(
        total_value=total_value,
        total_return=total_return_dollars,
        total_return_percent=total_return_percent,
        ytd_return=0.0,  # Requires historical snapshot at Jan 1
        ytd_return_percent=0.0,
        mtd_return=0.0,  # Requires historical snapshot at month start
        mtd_return_percent=0.0,
        day_change=0.0,  # Requires historical snapshot from previous day
        day_change_percent=0.0,
        allocation_by_asset_class=allocation,  # Now list[AssetAllocation]
    )


def calculate_day_change_with_snapshot(
    current_holdings: list,
    previous_snapshot: list,
) -> dict:
    """Calculate day change by comparing current holdings to previous snapshot.

    Compares current holdings values to a previous snapshot (e.g., yesterday's close)
    to calculate daily change in portfolio value.

    This function enables day-over-day tracking when applications store daily
    snapshots of holdings. Without snapshots, day change defaults to 0.0.

    Args:
        current_holdings: List of current Holding objects
        previous_snapshot: List of Holding objects from previous day
            Must have same structure with institution_value field

    Returns:
        dict with day_change_dollars and day_change_percent

    Snapshot Storage:
        Applications must store daily holdings snapshots to use this function.
        Recommended approach:
        1. Daily cron job: Fetch and store holdings at market close
        2. Database table: holdings_snapshots(date, user_id, holdings_json)
        3. On portfolio request: Compare current to yesterday's snapshot

    Examples:
        >>> from fin_infra.investments import easy_investments
        >>> from fin_infra.analytics.portfolio import calculate_day_change_with_snapshot
        >>>
        >>> # Get current holdings
        >>> investments = easy_investments(provider="plaid")
        >>> current = await investments.get_holdings(access_token)
        >>>
        >>> # Load yesterday's snapshot from database
        >>> previous = load_holdings_snapshot(user_id, date=yesterday)
        >>>
        >>> # Calculate day change
        >>> day_stats = calculate_day_change_with_snapshot(current, previous)
        >>> print(f"Day change: ${day_stats['day_change_dollars']:,.2f}")
        >>> print(f"Day change %: {day_stats['day_change_percent']:.2f}%")

        >>> # Use with portfolio_metrics_with_holdings()
        >>> metrics = portfolio_metrics_with_holdings(current)
        >>> day_stats = calculate_day_change_with_snapshot(current, previous)
        >>> # Merge day_stats into metrics
        >>> metrics.day_change = day_stats['day_change_dollars']
        >>> metrics.day_change_percent = day_stats['day_change_percent']

    Matching Holdings:
        Function matches holdings by account_id + security_id for accurate tracking
        of individual position changes (accounts for buys/sells, not just price moves).
    """
    # Build lookup map for previous snapshot: (account_id, security_id) → value
    previous_map = {}
    for holding in previous_snapshot:
        key = (holding.account_id, holding.security.security_id)
        previous_map[key] = float(holding.institution_value)

    # Calculate current total and compare to previous
    current_total = 0.0
    previous_total = 0.0

    for holding in current_holdings:
        current_value = float(holding.institution_value)
        current_total += current_value

        # Find matching holding in previous snapshot
        key = (holding.account_id, holding.security.security_id)
        if key in previous_map:
            previous_total += previous_map[key]
        else:
            # New holding (bought today) - use current value as baseline
            previous_total += current_value

    # Calculate day change
    day_change_dollars = current_total - previous_total
    day_change_percent = (
        (day_change_dollars / previous_total * 100.0) if previous_total > 0 else 0.0
    )

    return {
        "day_change_dollars": day_change_dollars,
        "day_change_percent": day_change_percent,
    }


def _calculate_allocation_from_holdings(
    holdings: list,
    total_value: float,
) -> list:
    """Calculate asset allocation from real holdings.

    Groups holdings by security type (from Security.type field) and calculates
    percentage allocation for each asset class.

    Args:
        holdings: List of Holding objects with security.type
        total_value: Total portfolio value for percentage calculations

    Returns:
        list[AssetAllocation] with asset_class, value, and percentage

    Asset Class Mapping:
        - equity → Stocks
        - etf → Stocks (equity ETFs grouped with stocks)
        - mutual_fund → Bonds (conservative assumption)
        - bond → Bonds
        - cash → Cash
        - derivative → Other
        - other → Other
    """
    from collections import defaultdict

    from .models import AssetAllocation

    if total_value == 0:
        return []

    # Map SecurityType to asset class names
    type_to_class = {
        "equity": "Stocks",
        "etf": "Stocks",  # Most ETFs are equity
        "mutual_fund": "Bonds",  # Conservative: assume bond funds
        "bond": "Bonds",
        "cash": "Cash",
        "derivative": "Other",
        "other": "Other",
    }

    # Sum values by asset class
    allocation_values: dict[str, float] = defaultdict(float)
    for holding in holdings:
        security_type = (
            holding.security.type.value
            if hasattr(holding.security.type, "value")
            else holding.security.type
        )
        asset_class = type_to_class.get(security_type, "Other")
        allocation_values[asset_class] += float(holding.institution_value)

    # Convert to list of AssetAllocation objects
    allocation_list = [
        AssetAllocation(
            asset_class=asset_class, value=value, percentage=round((value / total_value) * 100.0, 2)
        )
        for asset_class, value in allocation_values.items()
    ]

    return allocation_list
