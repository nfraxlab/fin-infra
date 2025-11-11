"""
Portfolio rebalancing engine for tax-efficient portfolio optimization.

Generates rebalancing plans that:
- Achieve target asset allocation
- Minimize tax impact (prefer tax-advantaged accounts, long-term holdings)
- Minimize transaction costs
- Provide actionable trade recommendations
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from fin_infra.models.brokerage import Position


class Trade(BaseModel):
    """Single trade in a rebalancing plan."""

    symbol: str = Field(..., description="Security ticker symbol")
    action: str = Field(..., description="Trade action: 'buy' or 'sell'")
    quantity: Decimal = Field(..., description="Number of shares to trade")
    current_price: Decimal = Field(..., description="Current market price per share")
    trade_value: Decimal = Field(..., description="Total trade value (quantity × price)")
    account_id: str | None = Field(None, description="Preferred account for execution")
    tax_impact: Decimal = Field(
        Decimal("0"), description="Estimated tax cost (capital gains for sells)"
    )
    transaction_cost: Decimal = Field(Decimal("0"), description="Estimated commission/fees")
    reasoning: str = Field(..., description="Why this trade is recommended")


class RebalancingPlan(BaseModel):
    """Complete portfolio rebalancing plan with tax optimization."""

    user_id: str = Field(..., description="User identifier")
    target_allocation: dict[str, Decimal] = Field(
        ..., description="Target asset class percentages (e.g., {'stocks': 60, 'bonds': 40})"
    )
    current_allocation: dict[str, Decimal] = Field(
        ..., description="Current asset class percentages"
    )
    trades: list[Trade] = Field(default_factory=list, description="Recommended trades")
    total_tax_impact: Decimal = Field(Decimal("0"), description="Total estimated tax cost")
    total_transaction_costs: Decimal = Field(Decimal("0"), description="Total commission/fees")
    total_rebalance_amount: Decimal = Field(
        Decimal("0"), description="Total dollar amount being rebalanced"
    )
    projected_allocation: dict[str, Decimal] = Field(
        ..., description="Expected allocation after executing trades"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Strategic recommendations"
    )
    warnings: list[str] = Field(default_factory=list, description="Risk warnings")
    created_at: datetime = Field(default_factory=datetime.now)


def generate_rebalancing_plan(
    user_id: str,
    positions: list[Position],
    target_allocation: dict[str, Decimal],
    position_accounts: dict[str, str] | None = None,
    account_types: dict[str, str] | None = None,
    commission_per_trade: Decimal = Decimal("0"),
    min_trade_value: Decimal = Decimal("100"),
) -> RebalancingPlan:
    """
    Generate a tax-efficient portfolio rebalancing plan.

    Args:
        user_id: User identifier
        positions: Current portfolio positions
        target_allocation: Target allocation by asset class (e.g., {'stocks': 60, 'bonds': 40})
        position_accounts: Map of symbol to account_id (e.g., {'VTI': 'acc1', 'BND': 'acc2'})
        account_types: Map of account_id to account type ('taxable', 'ira', '401k')
        commission_per_trade: Commission/fee per trade (default: $0)
        min_trade_value: Minimum trade size to execute (default: $100)

    Returns:
        RebalancingPlan with trades, tax impact, and recommendations

    Example:
        >>> positions = [
        ...     Position(symbol="VTI", qty=100, market_value=20000, account_id="acc1"),
        ...     Position(symbol="BND", qty=50, market_value=5000, account_id="acc1"),
        ... ]
        >>> target = {"stocks": Decimal("60"), "bonds": Decimal("40")}
        >>> plan = generate_rebalancing_plan("user_123", positions, target)
        >>> print(plan.trades)
    """
    # Calculate current portfolio value
    total_value = sum((Decimal(str(p.market_value)) for p in positions), start=Decimal("0"))

    # Handle empty or zero-value portfolio
    if total_value == 0:
        return RebalancingPlan(
            user_id=user_id,
            target_allocation=target_allocation,
            current_allocation={},
            projected_allocation={},
            trades=[],
            recommendations=["Portfolio has no value. Add funds before rebalancing."],
        )

    # Map symbols to asset classes (simplified mapping)
    asset_class_map = _get_asset_class_mapping()

    # Calculate current allocation
    current_allocation: dict[str, Decimal] = {}
    for position in positions:
        asset_class = asset_class_map.get(position.symbol, "other")
        position_value = Decimal(str(position.market_value))
        current_allocation[asset_class] = (
            current_allocation.get(asset_class, Decimal("0")) + position_value
        )

    # Convert to percentages
    current_allocation_pct = {
        asset_class: (value / total_value * 100)
        for asset_class, value in current_allocation.items()
    }

    # Calculate target values
    target_values = {
        asset_class: (pct / 100 * total_value) for asset_class, pct in target_allocation.items()
    }

    # Generate trades
    trades: list[Trade] = []
    total_tax_impact = Decimal("0")
    total_transaction_costs = Decimal("0")

    # Sort positions by tax efficiency (sell losers first, long-term holdings last)
    sorted_positions = _sort_positions_for_tax_efficiency(
        positions, position_accounts, account_types
    )

    for position in sorted_positions:
        asset_class = asset_class_map.get(position.symbol, "other")
        if asset_class not in target_values:
            continue

        position_value = Decimal(str(position.market_value))
        current_class_value = current_allocation.get(asset_class, Decimal("0"))
        target_class_value = target_values[asset_class]

        # Determine if we need to buy or sell
        difference = target_class_value - current_class_value

        if abs(difference) < min_trade_value:
            continue  # Skip small adjustments

        # Calculate trade
        current_price = position_value / Decimal(str(position.qty))
        quantity = abs(difference) / current_price

        # Round to reasonable share amounts
        quantity = quantity.quantize(Decimal("0.01"))

        if quantity == 0:
            continue

        action = "buy" if difference > 0 else "sell"
        trade_value = quantity * current_price

        # Get account info for this position
        account_id = position_accounts.get(position.symbol) if position_accounts else None

        # Calculate tax impact (only for sells in taxable accounts)
        tax_impact = Decimal("0")
        if action == "sell" and account_id:
            account_type = account_types.get(account_id, "taxable") if account_types else "taxable"
            if account_type == "taxable":
                # Use actual cost_basis from position
                cost_basis = Decimal(str(position.cost_basis))
                gain = position_value - cost_basis
                if gain > 0:
                    tax_impact = gain * Decimal("0.15")  # 15% capital gains rate

        # Calculate transaction cost
        transaction_cost = commission_per_trade

        # Generate reasoning
        reasoning = _generate_trade_reasoning(
            action, position.symbol, asset_class, difference, total_value
        )

        trade = Trade(
            symbol=position.symbol,
            action=action,
            quantity=quantity,
            current_price=current_price,
            trade_value=trade_value,
            account_id=account_id,
            tax_impact=tax_impact,
            transaction_cost=transaction_cost,
            reasoning=reasoning,
        )

        trades.append(trade)
        total_tax_impact += tax_impact
        total_transaction_costs += transaction_cost

        # Update current allocation for next iteration
        if action == "sell":
            current_allocation[asset_class] -= trade_value
        else:
            current_allocation[asset_class] += trade_value

    # Calculate projected allocation
    projected_allocation = {
        asset_class: (value / total_value * 100)
        for asset_class, value in current_allocation.items()
    }

    # Generate recommendations
    recommendations = _generate_recommendations(
        trades, total_tax_impact, total_transaction_costs, target_allocation
    )

    # Generate warnings
    warnings = _generate_warnings(trades, total_tax_impact)

    total_rebalance_amount = sum((trade.trade_value for trade in trades), start=Decimal("0"))

    return RebalancingPlan(
        user_id=user_id,
        target_allocation=target_allocation,
        current_allocation=current_allocation_pct,
        trades=trades,
        total_tax_impact=total_tax_impact,
        total_transaction_costs=total_transaction_costs,
        total_rebalance_amount=total_rebalance_amount,
        projected_allocation=projected_allocation,
        recommendations=recommendations,
        warnings=warnings,
    )


def _get_asset_class_mapping() -> dict[str, str]:
    """Map ticker symbols to asset classes."""
    return {
        # Stock ETFs
        "VTI": "stocks",
        "VOO": "stocks",
        "SPY": "stocks",
        "QQQ": "stocks",
        "VGT": "stocks",
        "AAPL": "stocks",
        "MSFT": "stocks",
        "GOOGL": "stocks",
        "AMZN": "stocks",
        # Bond ETFs
        "BND": "bonds",
        "AGG": "bonds",
        "TLT": "bonds",
        "VGIT": "bonds",
        # International
        "VXUS": "international",
        "VEA": "international",
        "VWO": "international",
        # Real Estate
        "VNQ": "realestate",
        # Commodities
        "GLD": "commodities",
        "SLV": "commodities",
        # Crypto
        "BTC": "crypto",
        "ETH": "crypto",
    }


def _sort_positions_for_tax_efficiency(
    positions: list[Position],
    position_accounts: dict[str, str] | None,
    account_types: dict[str, str] | None,
) -> list[Position]:
    """
    Sort positions for tax-efficient selling.

    Priority (sell first):
    1. Positions in tax-advantaged accounts (no tax impact)
    2. Positions with losses (tax-loss harvesting)
    3. Positions with short-term gains (already high tax)
    4. Positions with long-term gains (lowest priority)
    """

    def tax_priority(position: Position) -> tuple[int, Decimal]:
        # Get account info
        account_id = position_accounts.get(position.symbol) if position_accounts else None
        account_type = (
            account_types.get(account_id, "taxable") if account_types and account_id else "taxable"
        )

        # Tax-advantaged accounts first (priority 0)
        if account_type in ["ira", "401k", "roth_ira"]:
            return (0, Decimal("0"))

        # Calculate unrealized gain/loss from position
        unrealized_pl = Decimal(str(position.unrealized_pl))

        # Positions with losses (priority 1)
        if unrealized_pl < 0:
            return (1, unrealized_pl)  # More negative = higher priority

        # Short-term gains (priority 2, assume if no purchase_date)
        purchase_date = getattr(position, "purchase_date", None)
        if purchase_date is None or (datetime.now() - purchase_date).days < 365:
            return (2, unrealized_pl)

        # Long-term gains (priority 3, lowest priority)
        return (3, unrealized_pl)

    return sorted(positions, key=tax_priority)


def _generate_trade_reasoning(
    action: str, symbol: str, asset_class: str, difference: Decimal, total_value: Decimal
) -> str:
    """Generate human-readable reasoning for a trade."""
    diff_pct = abs(difference / total_value * 100)

    if action == "buy":
        return (
            f"Buy {symbol} to increase {asset_class} allocation "
            f"by {diff_pct:.1f}% towards target"
        )
    else:
        return (
            f"Sell {symbol} to decrease {asset_class} allocation "
            f"by {diff_pct:.1f}% towards target"
        )


def _generate_recommendations(
    trades: list[Trade],
    total_tax_impact: Decimal,
    total_transaction_costs: Decimal,
    target_allocation: dict[str, Decimal],
) -> list[str]:
    """Generate strategic recommendations for the rebalancing plan."""
    recommendations = []

    if not trades:
        recommendations.append("Portfolio is already well-balanced. No trades needed.")
        return recommendations

    # Tax efficiency
    if total_tax_impact > 0:
        recommendations.append(
            f"Total tax impact: ${total_tax_impact:.2f}. "
            "Consider executing sells in tax-advantaged accounts to minimize taxes."
        )
    else:
        recommendations.append(
            "No tax impact detected. Rebalancing is tax-free (likely in IRA/401k)."
        )

    # Transaction costs
    if total_transaction_costs > 0:
        recommendations.append(
            f"Total transaction costs: ${total_transaction_costs:.2f}. "
            "Consider consolidating trades to reduce fees."
        )

    # Timing
    recommendations.append(
        "Execute trades during market hours for best prices. "
        "Consider using limit orders to control execution prices."
    )

    # Tax-loss harvesting
    sell_trades = [t for t in trades if t.action == "sell" and t.tax_impact == 0]
    if sell_trades:
        recommendations.append(
            f"{len(sell_trades)} sell trades have no tax impact. "
            "Execute these first to free up capital."
        )

    return recommendations


def _generate_warnings(trades: list[Trade], total_tax_impact: Decimal) -> list[str]:
    """Generate risk warnings for the rebalancing plan."""
    warnings = []

    if total_tax_impact > 1000:
        warnings.append(
            f"High tax impact (${total_tax_impact:.2f}). "
            "Consult a tax professional before executing."
        )

    if len(trades) > 10:
        warnings.append(
            f"{len(trades)} trades required. "
            "Consider executing over multiple days to reduce market impact."
        )

    # Check for large position sells
    large_sells = [t for t in trades if t.action == "sell" and t.trade_value > 10000]
    if large_sells:
        warnings.append(
            f"{len(large_sells)} large position sales (>$10,000). "
            "Market impact may affect execution prices."
        )

    return warnings
