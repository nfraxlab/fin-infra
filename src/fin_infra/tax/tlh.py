"""Tax-loss harvesting (TLH) logic for portfolio optimization.

Tax-loss harvesting identifies opportunities to sell securities at a loss to offset
capital gains and reduce tax liability. This module provides:
- Automatic detection of unrealized loss positions
- Wash sale rule compliance (IRS 30-day rule)
- Replacement security suggestions for maintaining market exposure
- Tax savings calculations based on current tax rates

Key Concepts:
- **Unrealized Loss**: Position where current price < cost basis
- **Wash Sale**: Buying "substantially identical" security 30 days before/after sale
- **Replacement Security**: Similar exposure without triggering wash sale
- **Tax Savings**: Loss amount × tax rate (offset against gains)

IRS Rules:
- Wash sale window: 30 days before + 30 days after sale (61-day total)
- Disallowed loss if wash sale occurs (loss deferred to new position basis)
- "Substantially identical": Same company stock, options, similar securities
- Replacement suggestions must have different exposure (e.g., sector ETF vs individual stock)

Example:
    >>> from fin_infra.tax.tlh import find_tlh_opportunities
    >>> from fin_infra.brokerage import easy_brokerage
    >>>
    >>> broker = easy_brokerage(mode="paper")
    >>> positions = broker.positions()
    >>>
    >>> # Find TLH opportunities (min $100 loss)
    >>> opportunities = find_tlh_opportunities(
    ...     user_id="user123",
    ...     positions=positions,
    ...     min_loss=100.0
    ... )
    >>>
    >>> for opp in opportunities:
    ...     print(f"{opp.position.symbol}: ${opp.loss_amount} loss")
    ...     print(f"  Replace with: {opp.replacement_ticker}")
    ...     print(f"  Tax savings: ${opp.potential_tax_savings} @ {opp.tax_rate}%")
    ...     print(f"  Wash sale risk: {opp.wash_sale_risk}")

Production Notes:
- Use svc-infra jobs to run daily TLH scans (cron: "0 9 * * 1-5" for weekday mornings)
- Cache results with 24h TTL (market prices change daily)
- Integrate with brokerage API for recent trades (wash sale checking)
- Use ai-infra CoreLLM for intelligent replacement suggestions (sector analysis, correlation)
- Add compliance logging for all TLH recommendations (audit trail)
- Consider state tax rates in addition to federal (varies by state)

Cost Considerations:
- Market data: Use fin_infra.markets for current prices (~$0.01/quote)
- LLM suggestions: Use ai-infra CoreLLM for replacements (~$0.001/suggestion)
- Target: <$0.05/user/month for TLH analysis
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from fin_infra.models.brokerage import Position


class TLHOpportunity(BaseModel):
    """Tax-loss harvesting opportunity for a single position.

    Represents a position with unrealized losses that can be harvested for tax benefits.
    Includes replacement security suggestions and wash sale risk assessment.
    """

    position_symbol: str = Field(description="Symbol of the position with losses")
    position_qty: Decimal = Field(description="Quantity held")
    cost_basis: Decimal = Field(description="Total cost basis (purchase price × qty)")
    current_value: Decimal = Field(description="Current market value")
    loss_amount: Decimal = Field(description="Unrealized loss (cost_basis - current_value)", gt=0)
    loss_percent: Decimal = Field(description="Loss percentage (loss_amount / cost_basis)")
    replacement_ticker: str = Field(
        description="Suggested replacement security (similar exposure, no wash sale)"
    )
    wash_sale_risk: str = Field(description="Wash sale risk level: 'none', 'low', 'medium', 'high'")
    potential_tax_savings: Decimal = Field(
        description="Estimated tax savings (loss_amount × tax_rate)", ge=0
    )
    tax_rate: Decimal = Field(
        default=Decimal("0.15"),
        description="Tax rate used for savings calculation (default: 15% capital gains)",
    )
    last_purchase_date: datetime | None = Field(
        None, description="Most recent purchase date for this security (wash sale checking)"
    )
    explanation: str = Field(
        description="Human-readable explanation of the opportunity and replacement rationale"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "position_symbol": "AAPL",
                "position_qty": "100",
                "cost_basis": "15000.00",
                "current_value": "13500.00",
                "loss_amount": "1500.00",
                "loss_percent": "0.10",
                "replacement_ticker": "VGT",
                "wash_sale_risk": "low",
                "potential_tax_savings": "225.00",
                "tax_rate": "0.15",
                "last_purchase_date": "2024-08-15T00:00:00Z",
                "explanation": "AAPL down 10% ($1,500 loss). Replace with VGT (tech ETF) to maintain sector exposure without wash sale. Estimated $225 tax savings @ 15%.",
            }
        }
    }

    @field_validator("wash_sale_risk")
    @classmethod
    def validate_wash_sale_risk(cls, v: str) -> str:
        """Validate wash sale risk level."""
        allowed = {"none", "low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"wash_sale_risk must be one of {allowed}, got '{v}'")
        return v


class TLHScenario(BaseModel):
    """Simulation results for a tax-loss harvesting scenario.

    Projects the outcome of executing multiple TLH opportunities, including
    total tax savings, portfolio impact, and risk assessment.
    """

    total_loss_harvested: Decimal = Field(description="Total unrealized losses to harvest", ge=0)
    total_tax_savings: Decimal = Field(
        description="Total estimated tax savings (all losses × tax_rate)", ge=0
    )
    num_opportunities: int = Field(description="Number of TLH opportunities in scenario", ge=0)
    avg_tax_rate: Decimal = Field(
        description="Average tax rate used across opportunities",
        ge=Decimal("0"),
        le=Decimal("1"),
    )
    wash_sale_risk_summary: dict[str, int] = Field(
        description="Count of opportunities by wash sale risk level"
    )
    total_cost_basis: Decimal = Field(description="Total cost basis of positions to be sold", ge=0)
    total_current_value: Decimal = Field(
        description="Total current value of positions to be sold", ge=0
    )
    recommendations: list[str] = Field(
        description="Actionable recommendations for executing the scenario"
    )
    caveats: list[str] = Field(
        default_factory=lambda: [
            "Consult a tax professional before executing TLH trades",
            "Wash sale rules apply for 61 days (30 before + 30 after sale)",
            "Replacement securities may have different risk profiles",
            "Tax savings are estimates and depend on your specific tax situation",
        ],
        description="Important caveats and disclaimers",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_loss_harvested": "5000.00",
                "total_tax_savings": "750.00",
                "num_opportunities": 3,
                "avg_tax_rate": "0.15",
                "wash_sale_risk_summary": {"none": 1, "low": 2, "medium": 0, "high": 0},
                "total_cost_basis": "45000.00",
                "total_current_value": "40000.00",
                "recommendations": [
                    "Execute TLH trades before year-end to capture tax benefits",
                    "Wait 31 days before repurchasing original securities",
                    "Consider replacement securities for maintaining market exposure",
                ],
            }
        }
    }


def find_tlh_opportunities(
    user_id: str,
    positions: list[Position],
    min_loss: Decimal = Decimal("100.0"),
    tax_rate: Decimal = Decimal("0.15"),
    recent_trades: list[dict] | None = None,
) -> list[TLHOpportunity]:
    """Find tax-loss harvesting opportunities from brokerage positions.

    Analyzes all positions for unrealized losses >= min_loss and suggests
    replacement securities. Checks wash sale risk based on recent trades.

    Args:
        user_id: User ID (for audit logging in production)
        positions: List of Position objects from brokerage provider
        min_loss: Minimum loss amount to consider (default: $100)
        tax_rate: Tax rate for savings calculation (default: 15% capital gains)
        recent_trades: Optional list of recent trades for wash sale checking
                      Each trade: {"symbol": str, "date": datetime, "side": "buy|sell"}

    Returns:
        List of TLHOpportunity objects, sorted by loss_amount descending

    Examples:
        Basic usage with brokerage positions:
            >>> from fin_infra.brokerage import easy_brokerage
            >>> broker = easy_brokerage(mode="paper")
            >>> positions = broker.positions()
            >>> opportunities = find_tlh_opportunities("user123", positions)

        With custom min loss and tax rate:
            >>> opportunities = find_tlh_opportunities(
            ...     "user123",
            ...     positions,
            ...     min_loss=Decimal("500"),  # Only losses >= $500
            ...     tax_rate=Decimal("0.20")   # 20% tax rate
            ... )

        With recent trades for wash sale checking:
            >>> trades = [
            ...     {"symbol": "AAPL", "date": datetime.now() - timedelta(days=20), "side": "buy"},
            ...     {"symbol": "MSFT", "date": datetime.now() - timedelta(days=45), "side": "buy"},
            ... ]
            >>> opportunities = find_tlh_opportunities("user123", positions, recent_trades=trades)

    Production Notes:
        - Use svc-infra cache with 24h TTL: @cache_read(ttl=86400)
        - Fetch recent_trades from brokerage API (last 90 days)
        - Use ai-infra CoreLLM for intelligent replacement suggestions
        - Log all recommendations to svc-infra audit log
        - Consider state tax rates in addition to federal
    """
    opportunities: list[TLHOpportunity] = []

    # Build recent trades lookup for wash sale checking
    recent_purchases: dict[str, datetime] = {}
    if recent_trades:
        for trade in recent_trades:
            if trade["side"] == "buy":
                symbol = trade["symbol"]
                trade_date = trade["date"]
                # Keep most recent purchase date per symbol
                if symbol not in recent_purchases or trade_date > recent_purchases[symbol]:
                    recent_purchases[symbol] = trade_date

    for position in positions:
        # Only long positions with losses
        if position.side != "long":
            continue

        # Calculate loss (unrealized_pl is negative for losses)
        # Skip if position has a gain (positive unrealized_pl)
        if position.unrealized_pl >= 0:
            continue

        loss_amount = abs(position.unrealized_pl)
        if loss_amount < min_loss:
            continue

        # Calculate loss percentage
        loss_percent = (
            loss_amount / position.cost_basis if position.cost_basis > 0 else Decimal("0")
        )

        # Assess wash sale risk
        last_purchase_date = recent_purchases.get(position.symbol)
        wash_sale_risk = _assess_wash_sale_risk(position.symbol, last_purchase_date)

        # Suggest replacement security
        replacement_ticker = _suggest_replacement(position.symbol, position.asset_class or "equity")

        # Calculate tax savings
        potential_savings = loss_amount * tax_rate

        # Build explanation
        explanation = (
            f"{position.symbol} down {loss_percent:.1%} (${loss_amount:,.2f} loss). "
            f"Replace with {replacement_ticker} to maintain exposure without wash sale. "
            f"Estimated ${potential_savings:,.2f} tax savings @ {tax_rate:.0%}."
        )

        opportunity = TLHOpportunity(
            position_symbol=position.symbol,
            position_qty=position.qty,
            cost_basis=position.cost_basis,
            current_value=position.market_value,
            loss_amount=loss_amount,
            loss_percent=loss_percent,
            replacement_ticker=replacement_ticker,
            wash_sale_risk=wash_sale_risk,
            potential_tax_savings=potential_savings,
            tax_rate=tax_rate,
            last_purchase_date=last_purchase_date,
            explanation=explanation,
        )
        opportunities.append(opportunity)

    # Sort by loss amount descending (highest losses first)
    opportunities.sort(key=lambda x: x.loss_amount, reverse=True)

    return opportunities


def simulate_tlh_scenario(
    opportunities: list[TLHOpportunity],
    tax_rate: Decimal | None = None,
) -> TLHScenario:
    """Simulate a tax-loss harvesting scenario with multiple opportunities.

    Projects the outcome of executing all provided TLH opportunities,
    including total tax savings, risk assessment, and recommendations.

    Args:
        opportunities: List of TLHOpportunity objects to simulate
        tax_rate: Override tax rate for scenario (if None, uses each opportunity's rate)

    Returns:
        TLHScenario with simulation results and recommendations

    Examples:
        Simulate all found opportunities:
            >>> opportunities = find_tlh_opportunities("user123", positions)
            >>> scenario = simulate_tlh_scenario(opportunities)
            >>> print(f"Total tax savings: ${scenario.total_tax_savings}")

        Simulate with custom tax rate:
            >>> scenario = simulate_tlh_scenario(opportunities, tax_rate=Decimal("0.20"))

        Simulate subset (only low-risk opportunities):
            >>> low_risk = [o for o in opportunities if o.wash_sale_risk in ["none", "low"]]
            >>> scenario = simulate_tlh_scenario(low_risk)

    Production Notes:
        - Cache scenarios with user_id + timestamp key
        - Log simulation parameters for audit trail
        - Include link to tax professional consultation
        - Add disclaimer about tax advice
    """
    if not opportunities:
        # Empty scenario
        return TLHScenario(
            total_loss_harvested=Decimal("0"),
            total_tax_savings=Decimal("0"),
            num_opportunities=0,
            avg_tax_rate=Decimal("0"),
            wash_sale_risk_summary={"none": 0, "low": 0, "medium": 0, "high": 0},
            total_cost_basis=Decimal("0"),
            total_current_value=Decimal("0"),
            recommendations=[],
        )

    # Calculate totals
    total_loss = sum((o.loss_amount for o in opportunities), start=Decimal("0"))
    total_cost_basis = sum((o.cost_basis for o in opportunities), start=Decimal("0"))
    total_current_value = sum((o.current_value for o in opportunities), start=Decimal("0"))

    # Calculate tax savings (override rate if provided)
    if tax_rate is not None:
        total_savings = total_loss * tax_rate
        avg_rate = tax_rate
    else:
        # Use individual opportunity rates
        total_savings = sum((o.potential_tax_savings for o in opportunities), start=Decimal("0"))
        avg_rate = sum((o.tax_rate for o in opportunities), start=Decimal("0")) / Decimal(
            len(opportunities)
        )

    # Count wash sale risk levels
    wash_sale_risk_summary = {"none": 0, "low": 0, "medium": 0, "high": 0}
    for opp in opportunities:
        wash_sale_risk_summary[opp.wash_sale_risk] += 1

    # Generate recommendations
    recommendations = _generate_tlh_recommendations(opportunities, wash_sale_risk_summary)

    return TLHScenario(
        total_loss_harvested=total_loss,
        total_tax_savings=total_savings,
        num_opportunities=len(opportunities),
        avg_tax_rate=avg_rate,
        wash_sale_risk_summary=wash_sale_risk_summary,
        total_cost_basis=total_cost_basis,
        total_current_value=total_current_value,
        recommendations=recommendations,
    )


def _assess_wash_sale_risk(symbol: str, last_purchase_date: datetime | None) -> str:
    """Assess wash sale risk based on most recent purchase date.

    IRS wash sale rule: Can't buy "substantially identical" security
    30 days before or after sale. Total 61-day window.

    Risk levels:
    - none: No recent purchase (>30 days ago or never)
    - low: Purchase 31-60 days ago (outside window but close)
    - medium: Purchase 16-30 days ago (inside window, some time left)
    - high: Purchase 0-15 days ago (inside window, recent)

    Args:
        symbol: Security symbol
        last_purchase_date: Most recent purchase date for this symbol (or None)

    Returns:
        Risk level string: "none", "low", "medium", "high"
    """
    if last_purchase_date is None:
        return "none"

    # Calculate days since last purchase
    now = datetime.now(timezone.utc)
    if last_purchase_date.tzinfo is None:
        last_purchase_date = last_purchase_date.replace(tzinfo=timezone.utc)

    days_since = (now - last_purchase_date).days

    if days_since > 60:
        return "none"  # Well outside 61-day window
    elif days_since > 30:
        return "low"  # Outside window but close
    elif days_since > 15:
        return "medium"  # Inside window, some time
    else:
        return "high"  # Inside window, very recent


def _suggest_replacement(symbol: str, asset_class: str) -> str:
    """Suggest replacement security for tax-loss harvesting.

    Provides a similar exposure without triggering wash sale.
    Uses simple rules based on common symbols and asset classes.

    Production: Use ai-infra CoreLLM for intelligent suggestions based on:
    - Sector/industry analysis
    - Correlation with original security
    - Market cap similarity
    - Volatility matching

    Args:
        symbol: Original security symbol
        asset_class: Asset class (us_equity, crypto, etc.)

    Returns:
        Replacement security ticker symbol

    Examples:
        >>> _suggest_replacement("AAPL", "us_equity")
        'VGT'  # Tech sector ETF
        >>> _suggest_replacement("TSLA", "us_equity")
        'ARKK'  # Innovation ETF
    """
    # Simple rule-based suggestions (v1)
    # TODO: Replace with ai-infra CoreLLM for intelligent suggestions
    replacements = {
        # Tech stocks → sector ETFs
        "AAPL": "VGT",  # Tech ETF
        "MSFT": "VGT",
        "GOOGL": "VGT",
        "GOOG": "VGT",
        "META": "VGT",
        "NVDA": "SOXX",  # Semiconductor ETF
        "AMD": "SOXX",
        # Auto/EV → sector alternatives
        "TSLA": "ARKK",  # Innovation ETF
        "F": "XLI",  # Industrials ETF
        "GM": "XLI",
        # Finance → sector ETF
        "JPM": "XLF",  # Financials ETF
        "BAC": "XLF",
        "GS": "XLF",
        # Healthcare → sector ETF
        "JNJ": "XLV",  # Healthcare ETF
        "PFE": "XLV",
        "MRNA": "XBI",  # Biotech ETF
        # Crypto → broad exposure
        "BTC": "ETH",  # Ethereum (different asset)
        "ETH": "BTC",  # Bitcoin (different asset)
    }

    # Return known replacement or generic ETF
    if symbol in replacements:
        return replacements[symbol]
    elif asset_class == "crypto":
        return "COIN"  # Coinbase stock (crypto exposure without direct coin)
    else:
        return "SPY"  # S&P 500 ETF (broad market)


def _generate_tlh_recommendations(
    opportunities: list[TLHOpportunity],
    wash_sale_risk_summary: dict[str, int],
) -> list[str]:
    """Generate actionable recommendations for TLH scenario.

    Args:
        opportunities: List of TLH opportunities
        wash_sale_risk_summary: Count of opportunities by risk level

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Timing recommendations
    now = datetime.now(timezone.utc)
    days_until_year_end = (datetime(now.year, 12, 31, tzinfo=timezone.utc) - now).days

    if days_until_year_end < 30:
        recommendations.append(
            f"Execute TLH trades within {days_until_year_end} days to capture "
            "tax benefits for current year"
        )
    else:
        recommendations.append(
            "Consider executing TLH trades before year-end to maximize current-year tax benefits"
        )

    # Wash sale risk recommendations
    high_risk_count = wash_sale_risk_summary.get("high", 0)
    medium_risk_count = wash_sale_risk_summary.get("medium", 0)

    if high_risk_count > 0:
        recommendations.append(
            f"WARNING: {high_risk_count} opportunity(ies) have HIGH wash sale risk. "
            "Wait additional days before selling or accept wash sale deferral."
        )

    if medium_risk_count > 0:
        recommendations.append(
            f"{medium_risk_count} opportunity(ies) have MEDIUM wash sale risk. "
            "Verify no purchases in past 30 days before executing."
        )

    # Replacement recommendations
    if len(opportunities) > 0:
        recommendations.append(
            f"After selling, purchase {len(opportunities)} replacement security(ies) "
            "to maintain market exposure while avoiding wash sale"
        )
        recommendations.append("Wait 31 days before repurchasing original securities if desired")

    # General advice
    recommendations.append(
        "Review replacement securities for similar risk/return profile to original positions"
    )

    return recommendations
