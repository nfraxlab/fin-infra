"""fin_infra: Financial Infrastructure Toolkit.

A comprehensive financial infrastructure library providing:
- Banking integration (Plaid, Teller, MX)
- Brokerage integration (Alpaca, Interactive Brokers)
- Market data (stocks, crypto, forex)
- Credit scores (Experian, Equifax, TransUnion)
- Financial calculations (NPV, IRR, PMT, FV, PV)
- Portfolio analytics (returns, allocation, benchmarking)
- Transaction categorization (rule-based + ML)
- Budget management and cash flow analysis
- Net worth tracking and goal management

Example:
    from fin_infra.banking import easy_banking
    from fin_infra.markets import easy_market

    banking = easy_banking()
    market = easy_market()
    quote = market.quote("AAPL")
"""

from __future__ import annotations

# Core modules - can be imported as `from fin_infra import banking`
from . import (
    analytics,
    banking,
    brokerage,
    budgets,
    cashflows,
    categorization,
    credit,
    crypto,
    investments,
    markets,
    net_worth,
    recurring,
    tax,
)

# Base exceptions
from .exceptions import (
    FinInfraError,
    ProviderError,
    ProviderNotFoundError,
    ValidationError,
)
from .version import __version__

__all__ = [
    "__version__",
    # Core modules
    "analytics",
    "banking",
    "brokerage",
    "budgets",
    "cashflows",
    "categorization",
    "credit",
    "crypto",
    "investments",
    "markets",
    "net_worth",
    "recurring",
    "tax",
    # Base errors
    "FinInfraError",
    "ProviderError",
    "ProviderNotFoundError",
    "ValidationError",
]
