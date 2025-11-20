"""Investment provider implementations.

This package contains provider-specific implementations for investment
aggregation APIs (Plaid, SnapTrade, etc.).
"""

from .base import InvestmentProvider

__all__ = ["InvestmentProvider"]
