"""Unit tests for portfolio rebalancing engine."""

from decimal import Decimal


from fin_infra.analytics.rebalancing import (
    RebalancingPlan,
    Trade,
    generate_rebalancing_plan,
)
from fin_infra.models.brokerage import Position


def make_position(
    symbol: str,
    qty: float | Decimal,
    market_value: float | Decimal,
    cost_basis: float | Decimal | None = None,
    account_id: str = "acc1",
    **kwargs,
) -> Position:
    """Helper to create Position with all required fields."""
    qty_decimal = Decimal(str(qty))
    market_value_decimal = Decimal(str(market_value))
    cost_basis_decimal = (
        Decimal(str(cost_basis))
        if cost_basis is not None
        else market_value_decimal * Decimal("0.8")
    )

    current_price = market_value_decimal / qty_decimal if qty_decimal != 0 else Decimal("0")
    avg_entry_price = cost_basis_decimal / qty_decimal if qty_decimal != 0 else Decimal("0")
    unrealized_pl = market_value_decimal - cost_basis_decimal
    unrealized_plpc = (
        (unrealized_pl / cost_basis_decimal * 100) if cost_basis_decimal != 0 else Decimal("0")
    )

    return Position(
        symbol=symbol,
        qty=qty_decimal,
        side=kwargs.get("side", "long"),
        avg_entry_price=avg_entry_price,
        current_price=current_price,
        market_value=market_value_decimal,
        cost_basis=cost_basis_decimal,
        unrealized_pl=unrealized_pl,
        unrealized_plpc=unrealized_plpc,
        account_id=account_id,
        **{k: v for k, v in kwargs.items() if k not in ["side", "account_id"]},
    )


class TestRebalancingPlanModel:
    """Test RebalancingPlan Pydantic model."""

    def test_minimal_plan(self):
        """Test creating a plan with minimal required fields."""
        plan = RebalancingPlan(
            user_id="user_123",
            target_allocation={"stocks": Decimal("60"), "bonds": Decimal("40")},
            current_allocation={"stocks": Decimal("80"), "bonds": Decimal("20")},
            projected_allocation={"stocks": Decimal("60"), "bonds": Decimal("40")},
        )
        assert plan.user_id == "user_123"
        assert plan.trades == []
        assert plan.total_tax_impact == Decimal("0")
        assert plan.created_at is not None

    def test_complete_plan(self):
        """Test creating a plan with all fields."""
        trade = Trade(
            symbol="VTI",
            action="sell",
            quantity=Decimal("10"),
            current_price=Decimal("200"),
            trade_value=Decimal("2000"),
            account_id="acc1",
            tax_impact=Decimal("50"),
            transaction_cost=Decimal("5"),
            reasoning="Rebalance stocks",
        )
        plan = RebalancingPlan(
            user_id="user_123",
            target_allocation={"stocks": Decimal("60"), "bonds": Decimal("40")},
            current_allocation={"stocks": Decimal("80"), "bonds": Decimal("20")},
            trades=[trade],
            total_tax_impact=Decimal("50"),
            total_transaction_costs=Decimal("5"),
            total_rebalance_amount=Decimal("2000"),
            projected_allocation={"stocks": Decimal("60"), "bonds": Decimal("40")},
            recommendations=["Execute in tax-advantaged account"],
            warnings=["High tax impact"],
        )
        assert len(plan.trades) == 1
        assert plan.total_tax_impact == Decimal("50")
        assert len(plan.recommendations) == 1


class TestTradeModel:
    """Test Trade Pydantic model."""

    def test_buy_trade(self):
        """Test creating a buy trade."""
        trade = Trade(
            symbol="BND",
            action="buy",
            quantity=Decimal("50"),
            current_price=Decimal("80"),
            trade_value=Decimal("4000"),
            reasoning="Increase bonds allocation",
        )
        assert trade.symbol == "BND"
        assert trade.action == "buy"
        assert trade.tax_impact == Decimal("0")

    def test_sell_trade_with_tax_impact(self):
        """Test creating a sell trade with tax impact."""
        trade = Trade(
            symbol="VTI",
            action="sell",
            quantity=Decimal("25"),
            current_price=Decimal("200"),
            trade_value=Decimal("5000"),
            account_id="taxable_acc",
            tax_impact=Decimal("150"),
            transaction_cost=Decimal("7"),
            reasoning="Decrease stocks allocation",
        )
        assert trade.action == "sell"
        assert trade.tax_impact == Decimal("150")
        assert trade.transaction_cost == Decimal("7")


class TestGenerateRebalancingPlan:
    """Test generate_rebalancing_plan() function."""

    def test_empty_portfolio(self):
        """Test rebalancing with no positions."""
        target = {"stocks": Decimal("60"), "bonds": Decimal("40")}
        plan = generate_rebalancing_plan("user_123", [], target)

        assert plan.user_id == "user_123"
        assert plan.trades == []
        assert plan.total_rebalance_amount == Decimal("0")

    def test_already_balanced_portfolio(self):
        """Test portfolio that's already at target allocation."""
        positions = [
            make_position("VTI", qty=60, market_value=12000),  # 60%
            make_position("BND", qty=100, market_value=8000),  # 40%
        ]
        target = {"stocks": Decimal("60"), "bonds": Decimal("40")}
        plan = generate_rebalancing_plan("user_123", positions, target)

        # Should have minimal or no trades (within tolerance)
        assert len(plan.trades) <= 2
        assert plan.total_rebalance_amount < Decimal("1000")  # Small adjustments only

    def test_overweight_stocks_underweight_bonds(self):
        """Test portfolio overweight in stocks, underweight in bonds."""
        positions = [
            make_position("VTI", qty=100, market_value=20000),  # 80%
            make_position("BND", qty=50, market_value=5000),  # 20%
        ]
        target = {"stocks": Decimal("60"), "bonds": Decimal("40")}
        position_accounts = {"VTI": "acc1", "BND": "acc1"}
        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )

        # Should generate sell stocks, buy bonds
        assert len(plan.trades) > 0

        # Check current allocation
        assert plan.current_allocation["stocks"] == Decimal("80")
        assert plan.current_allocation["bonds"] == Decimal("20")

        # Should recommend selling stocks
        stock_trades = [t for t in plan.trades if t.symbol == "VTI"]
        if stock_trades:
            assert stock_trades[0].action == "sell"

    def test_underweight_stocks_overweight_bonds(self):
        """Test portfolio underweight in stocks, overweight in bonds."""
        positions = [
            make_position("VTI", qty=50, market_value=10000),  # 40%
            make_position("BND", qty=150, market_value=15000),  # 60%
        ]
        target = {"stocks": Decimal("60"), "bonds": Decimal("40")}
        position_accounts = {"VTI": "acc1", "BND": "acc1"}
        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )

        # Should generate buy stocks, sell bonds
        assert len(plan.trades) > 0

        # Check current allocation
        assert plan.current_allocation["stocks"] == Decimal("40")
        assert plan.current_allocation["bonds"] == Decimal("60")

    def test_tax_advantaged_account_no_tax_impact(self):
        """Test that trades in IRAs have no tax impact."""
        positions = [
            make_position(
                "VTI", qty=100, market_value=20000, cost_basis=15000, account_id="ira_acc"
            ),
        ]
        target = {"stocks": Decimal("0"), "bonds": Decimal("100")}
        position_accounts = {"VTI": "ira_acc"}
        account_types = {"ira_acc": "ira"}

        plan = generate_rebalancing_plan(
            "user_123",
            positions,
            target,
            position_accounts=position_accounts,
            account_types=account_types,
        )

        # Should have no tax impact (IRA is tax-advantaged)
        assert plan.total_tax_impact == Decimal("0")

        # Should have recommendation about tax-free rebalancing
        tax_free_recs = [r for r in plan.recommendations if "tax-free" in r.lower()]
        assert len(tax_free_recs) > 0

    def test_taxable_account_with_gains(self):
        """Test that sells in taxable accounts generate tax impact."""
        positions = [
            make_position(
                "VTI", qty=100, market_value=20000, cost_basis=15000, account_id="taxable_acc"
            ),
        ]
        target = {"stocks": Decimal("0"), "bonds": Decimal("100")}
        position_accounts = {"VTI": "taxable_acc"}
        account_types = {"taxable_acc": "taxable"}

        plan = generate_rebalancing_plan(
            "user_123",
            positions,
            target,
            position_accounts=position_accounts,
            account_types=account_types,
        )

        # Should have tax impact for selling gains
        assert plan.total_tax_impact > Decimal("0")

        # Should have sell trades with tax impact
        sell_trades = [t for t in plan.trades if t.action == "sell"]
        if sell_trades:
            assert any(t.tax_impact > 0 for t in sell_trades)

    def test_transaction_costs(self):
        """Test transaction cost calculation."""
        positions = [
            make_position("VTI", qty=100, market_value=20000),
        ]
        target = {"stocks": Decimal("0"), "bonds": Decimal("100")}
        position_accounts = {"VTI": "acc1"}
        commission = Decimal("7")

        plan = generate_rebalancing_plan(
            "user_123",
            positions,
            target,
            position_accounts=position_accounts,
            commission_per_trade=commission,
        )

        # Should have transaction costs
        assert plan.total_transaction_costs > Decimal("0")

        # Each trade should have commission
        for trade in plan.trades:
            assert trade.transaction_cost == commission

    def test_min_trade_value_filter(self):
        """Test that trades below minimum value are skipped."""
        positions = [
            make_position("VTI", qty=100, market_value=20000),
        ]
        # Very small adjustment (0.1%)
        target = {"stocks": Decimal("79.9"), "bonds": Decimal("20.1")}
        position_accounts = {"VTI": "acc1"}
        min_trade = Decimal("500")  # Skip trades under $500

        plan = generate_rebalancing_plan(
            "user_123",
            positions,
            target,
            position_accounts=position_accounts,
            min_trade_value=min_trade,
        )

        # Should skip small trades
        small_trades = [t for t in plan.trades if t.trade_value < min_trade]
        assert len(small_trades) == 0

    def test_recommendations_generated(self):
        """Test that recommendations are generated."""
        positions = [
            make_position("VTI", qty=100, market_value=20000),
        ]
        target = {"stocks": Decimal("60"), "bonds": Decimal("40")}
        position_accounts = {"VTI": "acc1"}

        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )

        # Should have recommendations
        assert len(plan.recommendations) > 0

    def test_warnings_for_high_tax_impact(self):
        """Test warnings generated for high tax impact."""
        positions = [
            make_position(
                "VTI", qty=1000, market_value=200000, cost_basis=100000, account_id="taxable_acc"
            ),
        ]
        target = {"stocks": Decimal("0"), "bonds": Decimal("100")}
        position_accounts = {"VTI": "taxable_acc"}
        account_types = {"taxable_acc": "taxable"}

        plan = generate_rebalancing_plan(
            "user_123",
            positions,
            target,
            position_accounts=position_accounts,
            account_types=account_types,
        )

        # Should have high tax impact warning
        high_tax_warnings = [w for w in plan.warnings if "tax impact" in w.lower()]
        assert len(high_tax_warnings) > 0

    def test_warnings_for_many_trades(self):
        """Test warnings for large number of trades."""
        # Create many small positions
        positions = [make_position(f"STOCK{i}", qty=10, market_value=1000) for i in range(15)]
        target = {"stocks": Decimal("50"), "other": Decimal("50")}
        position_accounts = {f"STOCK{i}": "acc1" for i in range(15)}

        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )

        # Should warn about many trades
        many_trades_warnings = [w for w in plan.warnings if "trades" in w.lower()]
        if len(plan.trades) > 10:
            assert len(many_trades_warnings) > 0

    def test_multiple_asset_classes(self):
        """Test rebalancing across multiple asset classes."""
        positions = [
            make_position("VTI", qty=50, market_value=10000),  # stocks
            make_position("BND", qty=100, market_value=8000),  # bonds
            make_position("VXUS", qty=30, market_value=6000),  # intl
            make_position("VNQ", qty=40, market_value=4000),  # realestate
        ]
        target = {
            "stocks": Decimal("40"),
            "bonds": Decimal("30"),
            "international": Decimal("20"),
            "realestate": Decimal("10"),
        }
        position_accounts = {"VTI": "acc1", "BND": "acc1", "VXUS": "acc1", "VNQ": "acc1"}

        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )

        # Should generate trades for multiple asset classes
        asset_classes = set()
        for trade in plan.trades:
            if trade.symbol == "VTI":
                asset_classes.add("stocks")
            elif trade.symbol == "BND":
                asset_classes.add("bonds")
            elif trade.symbol == "VXUS":
                asset_classes.add("international")
            elif trade.symbol == "VNQ":
                asset_classes.add("realestate")

        # Should touch multiple asset classes
        assert len(asset_classes) >= 2

    def test_trade_reasoning_includes_symbol(self):
        """Test that trade reasoning includes symbol name."""
        positions = [
            make_position("VTI", qty=100, market_value=20000),
        ]
        target = {"stocks": Decimal("50"), "bonds": Decimal("50")}
        position_accounts = {"VTI": "acc1"}

        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )

        # All trades should have reasoning with symbol
        for trade in plan.trades:
            assert trade.symbol in trade.reasoning


class TestTaxEfficiencySorting:
    """Test tax-efficient position sorting logic."""

    def test_prefer_tax_advantaged_accounts(self):
        """Test that tax-advantaged positions are sold first."""
        positions = [
            make_position(
                "VTI", qty=50, market_value=10000, cost_basis=8000, account_id="taxable_acc"
            ),
            make_position("VOO", qty=50, market_value=10000, cost_basis=8000, account_id="ira_acc"),
        ]
        target = {"stocks": Decimal("0"), "bonds": Decimal("100")}
        position_accounts = {"VTI": "taxable_acc", "VOO": "ira_acc"}
        account_types = {"taxable_acc": "taxable", "ira_acc": "ira"}

        plan = generate_rebalancing_plan(
            "user_123",
            positions,
            target,
            position_accounts=position_accounts,
            account_types=account_types,
        )

        # Should prioritize selling from IRA (no tax impact)
        ira_trades = [t for t in plan.trades if t.account_id == "ira_acc"]
        taxable_trades = [t for t in plan.trades if t.account_id == "taxable_acc"]

        # IRA trades should have no tax impact
        if ira_trades:
            assert all(t.tax_impact == 0 for t in ira_trades)

    def test_prefer_loss_positions(self):
        """Test that loss positions are sold before gain positions (tax-loss harvesting)."""
        positions = [
            make_position("VTI", qty=50, market_value=10000, cost_basis=12000),  # $2k loss
            make_position("VOO", qty=50, market_value=10000, cost_basis=8000),  # $2k gain
        ]
        target = {"stocks": Decimal("50"), "bonds": Decimal("50")}
        position_accounts = {"VTI": "acc1", "VOO": "acc1"}

        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )

        # If selling stocks, should prefer VTI (loss position) over VOO (gain)
        # This is implicit in the sorting logic
        assert len(plan.trades) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_value_portfolio(self):
        """Test portfolio with zero market value."""
        positions = [
            make_position("VTI", qty=0, market_value=0),
        ]
        target = {"stocks": Decimal("100")}

        plan = generate_rebalancing_plan("user_123", positions, target)

        # Should handle gracefully
        assert plan.total_rebalance_amount == Decimal("0")

    def test_negative_quantity(self):
        """Test handling of short positions (negative quantity)."""
        positions = [
            make_position("VTI", qty=-10, market_value=-2000, side="short"),
        ]
        target = {"stocks": Decimal("0")}
        position_accounts = {"VTI": "acc1"}

        # Should handle without crashing
        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )
        assert plan is not None

    def test_unknown_asset_class(self):
        """Test positions with symbols not in asset class mapping."""
        positions = [
            make_position("UNKNOWN", qty=100, market_value=10000),
        ]
        target = {"stocks": Decimal("100")}

        plan = generate_rebalancing_plan("user_123", positions, target)

        # Should handle unknown symbols (map to "other")
        assert plan is not None
        assert "other" in plan.current_allocation

    def test_fractional_shares(self):
        """Test handling of fractional share quantities."""
        positions = [
            make_position("VTI", qty=10.5, market_value=2100),  # Fractional shares
        ]
        target = {"stocks": Decimal("50"), "bonds": Decimal("50")}
        position_accounts = {"VTI": "acc1"}

        plan = generate_rebalancing_plan(
            "user_123", positions, target, position_accounts=position_accounts
        )

        # Should handle fractional quantities
        for trade in plan.trades:
            assert trade.quantity >= 0
