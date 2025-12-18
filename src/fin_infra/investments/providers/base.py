"""Abstract base class for investment aggregation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

# Import will work once models.py is fully implemented in Task 3
# For now, using TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import (
        AssetAllocation,
        Holding,
        InvestmentAccount,
        InvestmentTransaction,
        Security,
        SecurityType,
    )


class InvestmentProvider(ABC):
    """Abstract base class for investment aggregation providers.

    Provides READ-ONLY access to investment holdings, securities, and portfolio data.
    Implementations: PlaidInvestmentProvider, SnapTradeInvestmentProvider.
    """

    @abstractmethod
    async def get_holdings(
        self, access_token: str, account_ids: list[str] | None = None
    ) -> list[Holding]:
        """Fetch holdings for investment accounts.

        Args:
            access_token: Provider access token (Plaid access_token, SnapTrade connection_id)
            account_ids: Optional filter for specific accounts

        Returns:
            List of holdings with security details, quantity, cost basis, current value

        Example:
            >>> holdings = await provider.get_holdings(access_token)
            >>> for holding in holdings:
            ...     print(f"{holding.security.ticker_symbol}: {holding.quantity} @ ${holding.institution_price}")
        """
        pass

    @abstractmethod
    async def get_transactions(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        account_ids: list[str] | None = None,
    ) -> list[InvestmentTransaction]:
        """Fetch investment transactions within date range.

        Args:
            access_token: Provider access token
            start_date: Start date for transaction history
            end_date: End date for transaction history
            account_ids: Optional filter for specific accounts

        Returns:
            List of buy/sell/dividend transactions

        Example:
            >>> from datetime import date, timedelta
            >>> end = date.today()
            >>> start = end - timedelta(days=30)
            >>> transactions = await provider.get_transactions(access_token, start, end)
            >>> buys = [tx for tx in transactions if tx.transaction_type == "buy"]
        """
        pass

    @abstractmethod
    async def get_securities(self, access_token: str, security_ids: list[str]) -> list[Security]:
        """Fetch security details (ticker, name, type, current price).

        Args:
            access_token: Provider access token
            security_ids: List of security IDs to fetch (provider-specific IDs)

        Returns:
            List of security details with current market data

        Example:
            >>> securities = await provider.get_securities(access_token, ["security_id_1", "security_id_2"])
            >>> for security in securities:
            ...     print(f"{security.ticker_symbol}: ${security.close_price}")
        """
        pass

    @abstractmethod
    async def get_investment_accounts(self, access_token: str) -> list[InvestmentAccount]:
        """Fetch investment accounts with aggregated holdings.

        Args:
            access_token: Provider access token

        Returns:
            List of investment accounts with total value, cost basis, unrealized P&L

        Example:
            >>> accounts = await provider.get_investment_accounts(access_token)
            >>> for account in accounts:
            ...     print(f"{account.name}: ${account.total_value} (P&L: {account.total_unrealized_gain_loss_percent}%)")
        """
        pass

    # Helper methods (concrete - shared across all providers)

    def calculate_allocation(self, holdings: list[Holding]) -> AssetAllocation:
        """Calculate asset allocation by security type and sector.

        Groups holdings by security type (equity, bond, ETF, etc.) and calculates
        percentage breakdown of total portfolio value.

        Args:
            holdings: List of holdings to analyze

        Returns:
            AssetAllocation with percentage breakdowns

        Example:
            >>> allocation = provider.calculate_allocation(holdings)
            >>> print(f"Equities: {allocation.by_security_type['equity']}%")
            >>> print(f"Bonds: {allocation.by_security_type['bond']}%")
            >>> print(f"Cash: {allocation.cash_percent}%")
        """
        from ..models import AssetAllocation, SecurityType

        # Calculate total portfolio value
        total_value = sum(
            float(holding.institution_value) for holding in holdings if holding.institution_value
        )

        if total_value == 0:
            return AssetAllocation(
                by_security_type={},
                by_sector={},
                cash_percent=0.0,
            )

        # Group by security type
        type_values: dict[SecurityType, float] = {}
        sector_values: dict[str, float] = {}
        cash_value = 0.0

        for holding in holdings:
            sec_type = holding.security.type
            value = float(holding.institution_value or 0.0)

            if sec_type == SecurityType.cash:
                cash_value += value
            else:
                type_values[sec_type] = type_values.get(sec_type, 0.0) + value

                # Aggregate by sector if available
                if holding.security.sector:
                    sector_values[holding.security.sector] = (
                        sector_values.get(holding.security.sector, 0.0) + value
                    )

        # Calculate percentages
        by_type_percent = {
            sec_type: round((value / total_value) * 100, 2)
            for sec_type, value in type_values.items()
        }

        by_sector_percent = {
            sector: round((value / total_value) * 100, 2) for sector, value in sector_values.items()
        }

        cash_percent = round((cash_value / total_value) * 100, 2)

        return AssetAllocation(
            by_security_type=by_type_percent,
            by_sector=by_sector_percent,
            cash_percent=cash_percent,
        )

    def calculate_portfolio_metrics(self, holdings: list[Holding]) -> dict:
        """Calculate total value, cost basis, unrealized gain/loss.

        Aggregates holdings to calculate portfolio-level metrics.

        Args:
            holdings: List of holdings to analyze

        Returns:
            Dictionary with metrics:
                - total_value: Current market value of all holdings
                - total_cost_basis: Total cost basis (sum of purchase costs)
                - total_unrealized_gain_loss: Total P&L (value - cost_basis)
                - total_unrealized_gain_loss_percent: P&L percentage

        Example:
            >>> metrics = provider.calculate_portfolio_metrics(holdings)
            >>> print(f"Portfolio Value: ${metrics['total_value']:.2f}")
            >>> print(f"Total Gain/Loss: ${metrics['total_unrealized_gain_loss']:.2f}")
            >>> print(f"Return: {metrics['total_unrealized_gain_loss_percent']:.2f}%")
        """
        total_value = sum(
            float(holding.institution_value) for holding in holdings if holding.institution_value
        )
        total_cost_basis = sum(
            float(holding.cost_basis) for holding in holdings if holding.cost_basis
        )

        total_gain_loss = total_value - total_cost_basis
        # Use != 0 to handle short sales (negative cost basis)
        total_gain_loss_percent = (
            (total_gain_loss / total_cost_basis * 100) if total_cost_basis != 0 else 0.0
        )

        return {
            "total_value": round(total_value, 2),
            "total_cost_basis": round(total_cost_basis, 2),
            "total_unrealized_gain_loss": round(total_gain_loss, 2),
            "total_unrealized_gain_loss_percent": round(total_gain_loss_percent, 2),
        }

    def _normalize_security_type(self, provider_type: str) -> SecurityType:
        """Map provider-specific security types to standard SecurityType enum.

        Each provider uses different terminology for security types. This method
        normalizes them to a consistent enum.

        Args:
            provider_type: Provider-specific security type string

        Returns:
            Standardized SecurityType enum value

        Example mappings:
            Plaid: "equity" → SecurityType.equity
            Plaid: "mutual fund" → SecurityType.mutual_fund
            SnapTrade: "cs" → SecurityType.equity (common stock)
            SnapTrade: "etf" → SecurityType.etf

        Note:
            Override in provider-specific implementations for custom mappings.
        """
        from ..models import SecurityType

        # Default mappings (override in provider implementations as needed)
        mapping = {
            # Plaid types
            "equity": SecurityType.equity,
            "etf": SecurityType.etf,
            "mutual fund": SecurityType.mutual_fund,
            "bond": SecurityType.bond,
            "cash": SecurityType.cash,
            "derivative": SecurityType.derivative,
            # SnapTrade types (common abbreviations)
            "cs": SecurityType.equity,  # common stock
            "stock": SecurityType.equity,  # common stock (full word)
            "mf": SecurityType.mutual_fund,  # mutual fund
            "o": SecurityType.derivative,  # option
            # Fallback
            "other": SecurityType.other,
        }

        normalized = provider_type.lower().strip()
        return mapping.get(normalized, SecurityType.other)


__all__ = ["InvestmentProvider"]
