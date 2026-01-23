"""Benchmark comparison and historical performance analysis.

Provides real market data integration for portfolio vs benchmark comparisons.
Uses fin-infra's market data providers (easy_market) for historical prices.

Generic Applicability:
- Personal finance apps: Portfolio performance tracking
- Wealth management: Client reporting and benchmarking
- Robo-advisors: Automated performance attribution
- Investment platforms: Historical chart data
- Financial advisors: Performance comparison reports

Features:
- Real historical prices from market data providers (Yahoo Finance, Alpha Vantage)
- Time-series data for charting (normalized to 100)
- Alpha, beta, and Sharpe ratio calculations
- Multi-benchmark support (SPY, QQQ, VTI, BND, custom)
- Caching-friendly design (keyword-only arguments)

Examples:
    >>> from fin_infra.analytics.benchmark import (
    ...     get_benchmark_history,
    ...     compare_portfolio_to_benchmark,
    ... )
    >>>
    >>> # Get historical benchmark data for charting
    >>> history = await get_benchmark_history("SPY", period="1y")
    >>> print(f"SPY 1Y return: {history.total_return_percent:.2f}%")
    >>>
    >>> # Compare portfolio to benchmark
    >>> comparison = await compare_portfolio_to_benchmark(
    ...     portfolio_history=[...],  # List of portfolio snapshots
    ...     benchmark="SPY",
    ...     period="1y",
    ... )
    >>> print(f"Alpha: {comparison.alpha:.2f}%")
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from ..providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================


class BenchmarkDataPoint(BaseModel):
    """Single data point for benchmark time series."""

    model_config = ConfigDict(extra="forbid")

    date: dt.date = Field(..., description="Date of the data point")
    close: float = Field(..., description="Closing price")
    normalized: float = Field(..., description="Normalized value (starting at 100)")
    return_pct: float = Field(..., description="Return percentage from start")


class BenchmarkHistory(BaseModel):
    """Historical benchmark data for a given period.

    Designed for chart visualization with normalized values starting at 100.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., description="Benchmark ticker symbol (e.g., SPY)")
    period: str = Field(..., description="Time period (1m, 3m, 6m, 1y, ytd, all)")
    start_date: dt.date = Field(..., description="Start date of the period")
    end_date: dt.date = Field(..., description="End date of the period")
    data_points: list[BenchmarkDataPoint] = Field(
        default_factory=list, description="Time series data points"
    )
    start_price: float = Field(..., description="Starting price")
    end_price: float = Field(..., description="Ending price")
    total_return_percent: float = Field(..., description="Total return for period (%)")
    annualized_return_percent: float | None = Field(None, description="Annualized return (%)")


class PortfolioVsBenchmark(BaseModel):
    """Complete portfolio vs benchmark comparison with time series.

    Provides all data needed for performance comparison charts and summaries.
    """

    model_config = ConfigDict(extra="forbid")

    benchmark_symbol: str = Field(..., description="Benchmark ticker symbol")
    period: str = Field(..., description="Comparison period")
    start_date: dt.date = Field(..., description="Start date")
    end_date: dt.date = Field(..., description="End date")

    # Summary metrics
    portfolio_return_percent: float = Field(..., description="Portfolio total return (%)")
    benchmark_return_percent: float = Field(..., description="Benchmark total return (%)")
    alpha: float = Field(..., description="Excess return vs benchmark (%)")
    beta: float | None = Field(None, description="Portfolio beta vs benchmark")
    sharpe_ratio: float | None = Field(None, description="Portfolio Sharpe ratio")

    # Time series for charting
    portfolio_series: list[BenchmarkDataPoint] = Field(
        default_factory=list, description="Portfolio normalized time series"
    )
    benchmark_series: list[BenchmarkDataPoint] = Field(
        default_factory=list, description="Benchmark normalized time series"
    )


# ============================================================================
# Common Benchmarks (Reference Only)
# ============================================================================

# This is a reference list of commonly used benchmarks.
# fin-infra does NOT restrict which tickers can be used - any valid ticker works.
# Application layers (fin-api, fin-web) should define their own allowed lists.
COMMON_BENCHMARKS = {
    "SPY": "S&P 500 (SPDR)",
    "QQQ": "Nasdaq 100 (Invesco)",
    "VTI": "Total US Stock Market (Vanguard)",
    "BND": "Total Bond Market (Vanguard)",
    "VT": "Total World Stock (Vanguard)",
    "AGG": "US Aggregate Bond (iShares)",
    "IWM": "Russell 2000 (iShares)",
    "EFA": "EAFE International (iShares)",
    "VNQ": "Real Estate (Vanguard)",
    "GLD": "Gold (SPDR)",
}


# ============================================================================
# Period Parsing
# ============================================================================


def parse_period_to_days(period: str) -> int:
    """Parse period string to number of days.

    Args:
        period: Period string (1d, 1w, 1m, 3m, 6m, 1y, 2y, 5y, ytd, all)

    Returns:
        Number of calendar days

    Raises:
        ValueError: Invalid period format
    """
    period = period.lower().strip()

    if period == "ytd":
        today = dt.date.today()
        year_start = dt.date(today.year, 1, 1)
        return (today - year_start).days

    if period == "all" or period == "max":
        return 365 * 10  # 10 years max

    # Parse numeric periods
    if period.endswith("d"):
        return int(period[:-1])
    elif period.endswith("w"):
        return int(period[:-1]) * 7
    elif period.endswith("m"):
        return int(period[:-1]) * 30
    elif period.endswith("y"):
        return int(period[:-1]) * 365

    raise ValueError(
        f"Invalid period format: {period}. Use: 1d, 1w, 1m, 3m, 6m, 1y, 2y, 5y, ytd, all"
    )


def period_to_market_period(period: str) -> str:
    """Convert our period format to market provider period format.

    Args:
        period: Our period format (1m, 3m, 6m, 1y, ytd, all)

    Returns:
        Market provider period format (1mo, 3mo, 6mo, 1y, ytd, max)
    """
    period = period.lower().strip()

    # Map our periods to yahooquery/provider periods
    period_map = {
        "1d": "1d",
        "5d": "5d",
        "1w": "5d",
        "1m": "1mo",
        "3m": "3mo",
        "6m": "6mo",
        "1y": "1y",
        "2y": "2y",
        "5y": "5y",
        "10y": "10y",
        "ytd": "ytd",
        "all": "max",
        "max": "max",
    }

    return period_map.get(period, "1y")


# ============================================================================
# Core Functions
# ============================================================================


async def get_benchmark_history(
    symbol: str,
    *,
    period: str = "1y",
    market_provider: MarketDataProvider | None = None,
) -> BenchmarkHistory:
    """Fetch historical benchmark data with normalized values for charting.

    This function fetches real market data from fin-infra's market data providers
    and returns a time series normalized to 100 for easy comparison charting.

    Args:
        symbol: Benchmark ticker symbol (SPY, QQQ, VTI, BND, etc.)
        period: Time period (1d, 1w, 1m, 3m, 6m, 1y, 2y, 5y, ytd, all)
        market_provider: Optional market data provider instance.
                        If None, creates one using easy_market().

    Returns:
        BenchmarkHistory with normalized time series and summary metrics

    Raises:
        ValueError: Invalid symbol or period
        Exception: Market data provider errors

    Examples:
        >>> # Using auto-configured provider
        >>> history = await get_benchmark_history("SPY", period="1y")
        >>> print(f"SPY 1Y return: {history.total_return_percent:.2f}%")
        >>>
        >>> # With custom provider
        >>> from fin_infra.markets import easy_market
        >>> market = easy_market(provider="yahoo")
        >>> history = await get_benchmark_history("QQQ", period="6m", market_provider=market)
    """
    # Create market provider if not provided
    if market_provider is None:
        from ..markets import easy_market

        market_provider = easy_market()

    # Validate symbol
    symbol = symbol.upper()

    # Get market period format
    market_period = period_to_market_period(period)

    logger.info(f"[Benchmark] Fetching {symbol} history for period={period} ({market_period})")

    # Fetch historical candles from market provider
    candles = market_provider.history(symbol, period=market_period, interval="1d")

    if not candles:
        raise ValueError(f"No historical data returned for {symbol}")

    # Sort candles by timestamp (oldest first for normalization)
    candles_sorted = sorted(candles, key=lambda c: c.ts)

    # Get first and last prices for normalization
    first_candle = candles_sorted[0]
    last_candle = candles_sorted[-1]
    first_price = float(first_candle.close)
    last_price = float(last_candle.close)

    if first_price <= 0:
        raise ValueError(f"Invalid starting price for {symbol}: {first_price}")

    # Calculate total return
    total_return_pct = ((last_price - first_price) / first_price) * 100

    # Calculate annualized return
    days_in_period = parse_period_to_days(period)
    if days_in_period >= 365:
        years = days_in_period / 365
        annualized_return = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100
    else:
        annualized_return = None

    # Build normalized data points
    data_points: list[BenchmarkDataPoint] = []
    for candle in candles_sorted:
        # Convert timestamp to date
        candle_dt = dt.datetime.fromtimestamp(candle.ts / 1000, tz=dt.UTC)
        close_price = float(candle.close)

        # Normalize to 100
        normalized = (close_price / first_price) * 100
        return_pct = normalized - 100

        data_points.append(
            BenchmarkDataPoint(
                date=candle_dt.date(),
                close=close_price,
                normalized=round(normalized, 2),
                return_pct=round(return_pct, 2),
            )
        )

    # Determine start and end dates
    start_date = data_points[0].date if data_points else dt.date.today()
    end_date = data_points[-1].date if data_points else dt.date.today()

    logger.info(
        f"[Benchmark] {symbol}: {len(data_points)} points, "
        f"{start_date} to {end_date}, return={total_return_pct:.2f}%"
    )

    return BenchmarkHistory(
        symbol=symbol,
        period=period,
        start_date=start_date,
        end_date=end_date,
        data_points=data_points,
        start_price=first_price,
        end_price=last_price,
        total_return_percent=round(total_return_pct, 2),
        annualized_return_percent=round(annualized_return, 2) if annualized_return else None,
    )


async def compare_portfolio_to_benchmark(
    portfolio_values: Sequence[tuple[dt.date, float]],
    *,
    benchmark: str = "SPY",
    period: str | None = None,
    market_provider: MarketDataProvider | None = None,
    risk_free_rate: float = 0.03,
) -> PortfolioVsBenchmark:
    """Compare portfolio performance to a benchmark index.

    Takes portfolio historical values and compares them to benchmark performance,
    calculating alpha, beta, and providing normalized time series for charting.

    Args:
        portfolio_values: List of (date, value) tuples representing portfolio history.
                         Values should be total portfolio value on each date.
        benchmark: Benchmark ticker symbol (default: SPY)
        period: Time period override. If None, uses the date range from portfolio_values.
        market_provider: Optional market data provider instance.
        risk_free_rate: Annual risk-free rate for Sharpe calculation (default: 0.03 = 3%)

    Returns:
        PortfolioVsBenchmark with comparison metrics and time series

    Raises:
        ValueError: Invalid input or insufficient data

    Examples:
        >>> # Compare portfolio to S&P 500
        >>> portfolio_history = [
        ...     (date(2024, 1, 1), 100000),
        ...     (date(2024, 2, 1), 102000),
        ...     (date(2024, 3, 1), 105000),
        ...     # ...
        ... ]
        >>> comparison = await compare_portfolio_to_benchmark(
        ...     portfolio_history,
        ...     benchmark="SPY",
        ... )
        >>> print(f"Alpha: {comparison.alpha:.2f}%")
        >>> print(f"Portfolio: {comparison.portfolio_return_percent:.2f}%")
        >>> print(f"Benchmark: {comparison.benchmark_return_percent:.2f}%")
    """
    if not portfolio_values:
        raise ValueError("portfolio_values cannot be empty")

    # Sort by date
    sorted_values = sorted(portfolio_values, key=lambda x: x[0])
    start_date = sorted_values[0][0]
    end_date = sorted_values[-1][0]

    # Calculate portfolio return
    first_value = sorted_values[0][1]
    last_value = sorted_values[-1][1]

    if first_value <= 0:
        raise ValueError(f"Invalid starting portfolio value: {first_value}")

    portfolio_return_pct = ((last_value - first_value) / first_value) * 100

    # Calculate period from data range if not specified
    if period is None:
        days_diff = (end_date - start_date).days
        if days_diff <= 30:
            period = "1m"
        elif days_diff <= 90:
            period = "3m"
        elif days_diff <= 180:
            period = "6m"
        elif days_diff <= 365:
            period = "1y"
        else:
            period = "all"

    # Fetch benchmark history
    benchmark_history = await get_benchmark_history(
        benchmark,
        period=period,
        market_provider=market_provider,
    )

    benchmark_return_pct = benchmark_history.total_return_percent

    # Calculate alpha (simple excess return)
    alpha = portfolio_return_pct - benchmark_return_pct

    # Calculate beta (requires daily returns - simplified calculation)
    beta = _calculate_beta_simple(sorted_values, benchmark_history.data_points)

    # Calculate Sharpe ratio (simplified - uses portfolio return vs risk-free)
    # For proper Sharpe, would need daily returns and standard deviation
    sharpe = _calculate_sharpe_simple(
        portfolio_return_pct,
        risk_free_rate * 100,  # Convert to percentage
        period,
    )

    # Build normalized portfolio series
    portfolio_series: list[BenchmarkDataPoint] = []
    for value_date, value in sorted_values:
        normalized = (value / first_value) * 100
        return_pct = normalized - 100
        portfolio_series.append(
            BenchmarkDataPoint(
                date=value_date,
                close=value,
                normalized=round(normalized, 2),
                return_pct=round(return_pct, 2),
            )
        )

    return PortfolioVsBenchmark(
        benchmark_symbol=benchmark,
        period=period,
        start_date=start_date,
        end_date=end_date,
        portfolio_return_percent=round(portfolio_return_pct, 2),
        benchmark_return_percent=round(benchmark_return_pct, 2),
        alpha=round(alpha, 2),
        beta=round(beta, 2) if beta is not None else None,
        sharpe_ratio=round(sharpe, 2) if sharpe is not None else None,
        portfolio_series=portfolio_series,
        benchmark_series=benchmark_history.data_points,
    )


def _calculate_beta_simple(
    portfolio_values: Sequence[tuple[dt.date, float]],
    benchmark_points: Sequence[BenchmarkDataPoint],
) -> float | None:
    """Calculate simplified beta from value series.

    Uses simplified covariance/variance calculation. For proper beta,
    would need more sophisticated time series alignment and daily returns.

    Returns None if insufficient data.
    """
    if len(portfolio_values) < 5 or len(benchmark_points) < 5:
        return None

    # Calculate daily returns for portfolio
    portfolio_returns: list[float] = []
    for i in range(1, len(portfolio_values)):
        prev_val = portfolio_values[i - 1][1]
        curr_val = portfolio_values[i][1]
        if prev_val > 0:
            ret = (curr_val - prev_val) / prev_val
            portfolio_returns.append(ret)

    # Calculate daily returns for benchmark
    benchmark_returns: list[float] = []
    for i in range(1, len(benchmark_points)):
        prev_close = benchmark_points[i - 1].close
        curr_close = benchmark_points[i].close
        if prev_close > 0:
            ret = (curr_close - prev_close) / prev_close
            benchmark_returns.append(ret)

    if len(portfolio_returns) < 3 or len(benchmark_returns) < 3:
        return None

    # Use the shorter length for alignment
    n = min(len(portfolio_returns), len(benchmark_returns))
    p_returns = portfolio_returns[-n:]
    b_returns = benchmark_returns[-n:]

    # Calculate means
    p_mean = sum(p_returns) / n
    b_mean = sum(b_returns) / n

    # Calculate covariance and variance
    covariance = sum((p - p_mean) * (b - b_mean) for p, b in zip(p_returns, b_returns)) / n
    variance = sum((b - b_mean) ** 2 for b in b_returns) / n

    if variance == 0:
        return None

    return covariance / variance


def _calculate_sharpe_simple(
    portfolio_return_pct: float,
    risk_free_rate_pct: float,
    period: str,
) -> float | None:
    """Calculate simplified Sharpe ratio.

    Uses a simplified volatility estimate based on period.
    For proper Sharpe, would need daily return standard deviation.

    Args:
        portfolio_return_pct: Portfolio return percentage
        risk_free_rate_pct: Risk-free rate percentage (annualized)
        period: Time period for volatility estimation

    Returns:
        Simplified Sharpe ratio or None if cannot calculate
    """
    # Annualize the portfolio return if needed
    days = parse_period_to_days(period)

    if days < 30:
        return None  # Too short a period for meaningful Sharpe

    # Annualize return
    if days < 365:
        annualized_return = portfolio_return_pct * (365 / days)
    else:
        years = days / 365
        annualized_return = ((1 + portfolio_return_pct / 100) ** (1 / years) - 1) * 100

    # Excess return
    excess_return = annualized_return - risk_free_rate_pct

    # Estimate volatility (rough estimate: 15% for diversified portfolio)
    # This is a simplification - proper Sharpe needs actual std dev of returns
    estimated_volatility = 15.0

    if estimated_volatility == 0:
        return None

    return excess_return / estimated_volatility


# ============================================================================
# Utility Functions
# ============================================================================


def list_common_benchmarks() -> dict[str, str]:
    """Return dictionary of commonly used benchmark symbols and names.

    This is a REFERENCE list only. fin-infra allows ANY valid ticker
    to be used as a benchmark via get_benchmark_history().

    Application layers should define their own allowed lists if needed.

    Returns:
        Dict mapping symbol to full name (e.g., {"SPY": "S&P 500 (SPDR)"})
    """
    return COMMON_BENCHMARKS.copy()


def is_common_benchmark(symbol: str) -> bool:
    """Check if a symbol is in the common benchmarks reference list.

    Note: This does NOT validate whether a ticker is usable.
    Any valid stock/ETF ticker can be used with get_benchmark_history().
    This function only checks if it's in the commonly-used reference list.

    Args:
        symbol: Ticker symbol to check

    Returns:
        True if symbol is in the common benchmarks reference list
    """
    return symbol.upper() in COMMON_BENCHMARKS
