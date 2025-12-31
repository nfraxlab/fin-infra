"""
Net Worth Tracking Module

Calculates net worth by aggregating balances from multiple financial providers
(banking, brokerage, crypto) with historical snapshots and change detection.

**Feature Status**:
    [OK] STABLE: Core calculation (works with provided data)
    [OK] STABLE: Banking integration (Plaid, Teller)
    [!]  INTEGRATION: Brokerage integration (requires provider setup)
    [!]  INTEGRATION: Crypto integration (requires provider setup)
    [!]  INTEGRATION: Currency conversion (pass exchange_rate manually)

**Key Features**:
- Multi-provider aggregation (banking + brokerage + crypto)
- Currency normalization (all currencies → USD)
- Historical snapshots (daily at midnight UTC)
- Change detection (>5% or >$10k triggers webhook)
- Asset allocation breakdown (pie charts)
- Easy integration with `easy_net_worth()`

**Quick Start**:
```python
from fin_infra.net_worth import easy_net_worth
from fin_infra.banking import easy_banking
from fin_infra.brokerage import easy_brokerage

# Create providers
banking = easy_banking(provider="plaid")
brokerage = easy_brokerage(provider="alpaca")

# Create net worth tracker
tracker = easy_net_worth(
    banking=banking,
    brokerage=brokerage,
    base_currency="USD"
)

# Calculate current net worth
snapshot = await tracker.calculate_net_worth(user_id="user_123")
print(f"Net Worth: ${snapshot.total_net_worth:,.2f}")
```

**FastAPI Integration**:
```python
from fastapi import FastAPI
from fin_infra.net_worth import add_net_worth_tracking

app = FastAPI()

# Add net worth endpoints
tracker = add_net_worth_tracking(app, prefix="/net-worth")
```

**Endpoints**:
- `GET /net-worth/current` - Current net worth (cached 1h)
- `GET /net-worth/snapshots` - Historical snapshots
- `GET /net-worth/breakdown` - Asset/liability breakdown
- `POST /net-worth/snapshot` - Force snapshot creation

**svc-infra Integration**:
- Database: Snapshot storage with retention policy
- Jobs: Daily snapshots at midnight UTC
- Cache: Current net worth (1h TTL)
- Webhooks: Significant change alerts (>5% or >$10k)
"""

from fin_infra.net_worth.add import add_net_worth_tracking
from fin_infra.net_worth.aggregator import NetWorthAggregator
from fin_infra.net_worth.calculator import (
    calculate_asset_allocation,
    calculate_change,
    calculate_liability_breakdown,
    calculate_net_worth,
    detect_significant_change,
    normalize_currency,
)
from fin_infra.net_worth.ease import NetWorthTracker, easy_net_worth
from fin_infra.net_worth.models import (
    AssetAllocation,
    AssetCategory,
    AssetDetail,
    LiabilityBreakdown,
    LiabilityCategory,
    LiabilityDetail,
    NetWorthRequest,
    NetWorthResponse,
    NetWorthSnapshot,
    SnapshotHistoryRequest,
    SnapshotHistoryResponse,
)

__all__ = [
    # Easy Integration
    "add_net_worth_tracking",
    "easy_net_worth",
    "NetWorthTracker",
    # Core Classes
    "NetWorthAggregator",
    # Calculation Functions
    "calculate_net_worth",
    "normalize_currency",
    "calculate_asset_allocation",
    "calculate_liability_breakdown",
    "calculate_change",
    "detect_significant_change",
    # DTOs
    "NetWorthSnapshot",
    "AssetAllocation",
    "LiabilityBreakdown",
    "AssetDetail",
    "LiabilityDetail",
    # Enums
    "AssetCategory",
    "LiabilityCategory",
    # API Models
    "NetWorthRequest",
    "NetWorthResponse",
    "SnapshotHistoryRequest",
    "SnapshotHistoryResponse",
]
