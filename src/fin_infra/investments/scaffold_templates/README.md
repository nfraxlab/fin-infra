# Investment Holdings Scaffold Templates

Auto-generated SQLAlchemy models, Pydantic schemas, and repository pattern for investment holdings snapshot tracking.

## Overview

These templates generate production-ready persistence code for investment holdings snapshots with:
- **Point-in-time snapshots**: Immutable portfolio state captures at specific dates/times
- **Time-series analysis**: Track portfolio performance over time (daily, weekly, monthly, quarterly)
- **Provider agnostic**: Works with Plaid, SnapTrade, or any investment data provider
- **Full holdings data**: Stores complete JSON holdings data from provider API
- **Aggregated metrics**: Pre-calculated totals (value, cost basis, unrealized gains) for fast queries
- **Performance tracking**: Calculate returns, annualized returns, and growth metrics
- **Uniqueness constraint**: One snapshot per user per day
- **Multi-tenancy**: Optional tenant_id field for SaaS applications
- **Soft deletes**: Optional deleted_at field for safe deletion

## Why Historical Snapshots?

**Investment data providers (Plaid, SnapTrade, etc.) only provide current/live data:**
- ❌ No historical portfolio values from past dates
- ❌ No historical performance metrics
- ❌ Cannot answer "What was my portfolio worth 3 months ago?"

**Solution: Store periodic snapshots in your database**
- ✅ Track portfolio value changes over time
- ✅ Calculate performance metrics (returns, growth)
- ✅ Show trend charts and historical analysis
- ✅ Works even if user disconnects provider

## Template Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `${Entity}` | PascalCase entity name | `HoldingSnapshot` |
| `${entity}` | snake_case entity name | `holding_snapshot` |
| `${table_name}` | Database table name | `holding_snapshots` |
| `${tenant_field}` | Tenant field definition (if enabled) | `tenant_id: Mapped[str] = ...` |
| `${tenant_arg}` | Tenant arg in function signatures | `, tenant_id: str` |
| `${tenant_filter}` | SQLAlchemy WHERE clause | `.where(HoldingSnapshot.tenant_id == tenant_id)` |
| `${soft_delete_field}` | Soft delete field definition | `deleted_at: Mapped[Optional[datetime]] = ...` |

## Usage

### Generate Basic Holdings Model

```bash
fin-infra scaffold holdings --dest-dir src/my_app/models/holdings/
```

Creates:
- `src/my_app/models/holdings/holding_snapshot.py` - SQLAlchemy model
- `src/my_app/models/holdings/holding_snapshot_schemas.py` - Pydantic schemas (Create, Read, Update)
- `src/my_app/models/holdings/holding_snapshot_repository.py` - Repository pattern with time-series queries
- `src/my_app/models/holdings/__init__.py` - Package exports
- `src/my_app/models/holdings/README.md` - Integration guide

### With Multi-Tenancy

```bash
fin-infra scaffold holdings --dest-dir src/my_app/models/holdings/ --include-tenant
```

Adds:
- `tenant_id: Mapped[str]` field to model
- `tenant_id: str` to all Pydantic schemas
- Automatic tenant filtering in all queries
- Unique constraint: `(tenant_id, user_id, snapshot_date)`

### With Soft Deletes

```bash
fin-infra scaffold holdings --dest-dir src/my_app/models/holdings/ --include-soft-delete
```

Adds:
- `deleted_at: Mapped[Optional[datetime]]` field to model
- Automatic `deleted_at IS NULL` filtering in queries
- `soft` parameter in `delete()` method (default: True)

### Without Repository Pattern

```bash
fin-infra scaffold holdings --dest-dir src/my_app/models/holdings/ --no-with-repository
```

Creates only:
- `src/my_app/models/holdings/holding_snapshot.py` - SQLAlchemy model
- `src/my_app/models/holdings/holding_snapshot_schemas.py` - Pydantic schemas
- `src/my_app/models/holdings/__init__.py` - Package exports

## Integration

### 1. Run Migrations

```bash
# Create migration
svc-infra sql revision -m "add holding snapshots table" --autogenerate

# Apply migration
svc-infra sql upgrade head
```

### 2. Wire Automatic CRUD (Optional)

```python
from svc_infra.api.fastapi.db.sql import SqlResource, add_sql_resources
from my_app.models.holdings import (
    HoldingSnapshot,
    HoldingSnapshotRead,
    HoldingSnapshotCreate,
    HoldingSnapshotUpdate
)

add_sql_resources(app, [
    SqlResource(
        model=HoldingSnapshot,
        prefix="/holding-snapshots",
        tags=["Holdings"],
        ordering_default="-snapshot_date",
        allowed_order_fields=["snapshot_date", "total_value", "created_at"],
        read_schema=HoldingSnapshotRead,
        create_schema=HoldingSnapshotCreate,
        update_schema=HoldingSnapshotUpdate,  # Only notes field can be updated
    )
])
```

This provides automatic REST endpoints:
- `GET /holding-snapshots` - List snapshots with filtering, pagination, sorting
- `GET /holding-snapshots/{id}` - Get snapshot by ID
- `POST /holding-snapshots` - Create new snapshot
- `PATCH /holding-snapshots/{id}` - Update snapshot notes
- `DELETE /holding-snapshots/{id}` - Delete snapshot

### 3. Create Snapshots from Investment API

```python
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from my_app.models.holdings import create_holding_snapshot_service, HoldingSnapshotCreate

async def capture_holdings_snapshot(
    session: AsyncSession,
    user_id: str,
    holdings_data: list[dict],  # From Plaid/SnapTrade API
) -> None:
    """Capture current holdings as a snapshot for historical tracking."""
    
    # Calculate aggregated metrics
    total_value = sum(Decimal(str(h.get("institution_value", 0))) for h in holdings_data)
    total_cost_basis = sum(Decimal(str(h.get("cost_basis", 0))) for h in holdings_data if h.get("cost_basis"))
    total_unrealized_gain_loss = sum(Decimal(str(h.get("unrealized_gain_loss", 0))) for h in holdings_data if h.get("unrealized_gain_loss"))
    
    # Create snapshot
    service = create_holding_snapshot_service(session)
    snapshot = await service.create(HoldingSnapshotCreate(
        user_id=user_id,
        snapshot_date=datetime.now(timezone.utc),
        total_value=total_value,
        total_cost_basis=total_cost_basis if total_cost_basis else None,
        total_unrealized_gain_loss=total_unrealized_gain_loss if total_unrealized_gain_loss else None,
        holdings_count=len(holdings_data),
        holdings_data={"holdings": holdings_data},
        provider="plaid",  # or "snaptrade"
        notes="Automatic daily snapshot"
    ))
    
    await session.commit()
```

### 4. Schedule Daily Snapshots (Recommended)

```python
from svc_infra.jobs.easy import easy_jobs

@easy_jobs.cron("0 0 * * *")  # Daily at midnight
async def daily_holdings_snapshot():
    """Capture holdings snapshots for all users with investment accounts."""
    from sqlalchemy import select
    from my_app.models.user import User
    
    async with AsyncSession(engine) as session:
        # Get all users with Plaid/SnapTrade connections
        stmt = select(User).where(User.banking_providers.isnot(None))
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        for user in users:
            try:
                # Fetch current holdings from provider
                holdings = await fetch_holdings_from_provider(user)
                
                # Create snapshot
                await capture_holdings_snapshot(session, user.id, holdings)
            except Exception as e:
                logger.error(f"Failed to capture holdings for user {user.id}: {e}")
```

## Repository Methods

The generated repository includes these specialized methods:

### Time-Series Queries

```python
# Get latest snapshot
latest = await repo.get_latest(user_id="u123")

# Get snapshot for specific date
snapshot = await repo.get_by_date(user_id="u123", snapshot_date=date(2025, 1, 31))

# Get snapshots in date range
snapshots = await repo.get_by_date_range(
    user_id="u123",
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 31)
)

# Get last 12 months trend
trend = await repo.get_trend(user_id="u123", months=12)
```

### Performance Calculations

```python
# Calculate performance between two dates
performance = await repo.calculate_performance(
    user_id="u123",
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 31)
)

# Returns:
# {
#     "start_value": Decimal("100000.00"),
#     "end_value": Decimal("125000.00"),
#     "absolute_return": Decimal("25000.00"),
#     "percent_return": Decimal("25.00"),
#     "annualized_return": Decimal("25.00"),  # If >= 1 year
#     "start_date": date(2025, 1, 1),
#     "end_date": date(2025, 12, 31),
#     "days": 365
# }
```

## Model Schema

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique snapshot identifier |
| `user_id` | str | User who owns this snapshot |
| `snapshot_date` | datetime | When snapshot was taken (timezone-aware) |
| `total_value` | Decimal | Total portfolio value |
| `total_cost_basis` | Decimal (optional) | Total cost basis |
| `total_unrealized_gain_loss` | Decimal (optional) | Total unrealized P&L |
| `holdings_count` | int | Number of holdings |
| `holdings_data` | JSON | Complete holdings from provider |
| `provider` | str | Provider source (plaid, snaptrade) |
| `provider_metadata` | JSON (optional) | Provider-specific metadata |
| `notes` | str (optional) | User notes |
| `created_at` | datetime | When record was created |

### Constraints

- **Unique**: One snapshot per user per day `(user_id, snapshot_date)`
- **Immutable**: Snapshots cannot be updated (except notes field)
- **Indexes**: `user_id`, `snapshot_date` for fast time-series queries

## Best Practices

### 1. Capture Snapshots Daily
Run a scheduled job to capture holdings snapshots daily (or weekly for less active portfolios).

### 2. Store Full Provider Data
Always store the complete holdings JSON from the provider - you can extract additional fields later without re-fetching.

### 3. Pre-Calculate Aggregates
Store aggregated metrics (`total_value`, `total_cost_basis`) for fast queries without parsing JSON.

### 4. Use for Historical Analysis Only
For real-time data, always use provider API endpoints (e.g., `/v0/investments/holdings`).
Use snapshots only for historical trend analysis and performance tracking.

### 5. Clean Up Old Snapshots
Consider archiving or deleting snapshots older than N years based on your retention policy.

## Example: Portfolio Performance Dashboard

```python
from datetime import date, timedelta
from my_app.models.holdings import create_holding_snapshot_service

async def get_portfolio_performance_data(user_id: str):
    """Get data for portfolio performance dashboard."""
    async with AsyncSession(engine) as session:
        repo = create_holding_snapshot_service(session)
        
        # Get last 12 months trend
        snapshots = await repo.get_trend(user_id=user_id, months=12)
        
        # Calculate YTD performance
        today = date.today()
        year_start = date(today.year, 1, 1)
        ytd_performance = await repo.calculate_performance(
            user_id=user_id,
            start_date=year_start,
            end_date=today
        )
        
        # Get latest snapshot
        latest = await repo.get_latest(user_id=user_id)
        
        return {
            "current_value": latest.total_value if latest else 0,
            "ytd_return": ytd_performance["percent_return"],
            "ytd_absolute_return": ytd_performance["absolute_return"],
            "trend_data": [
                {
                    "date": s.snapshot_date,
                    "value": s.total_value,
                    "gain_loss": s.total_unrealized_gain_loss
                }
                for s in snapshots
            ]
        }
```

## Related Documentation

- **fin-infra Investments API**: `/investments/holdings` endpoint for live data
- **svc-infra Auto-CRUD**: Automatic REST endpoints with `add_sql_resources()`
- **svc-infra Jobs**: Schedule periodic snapshot jobs with `easy_jobs.cron()`
- **Plaid Investment API**: https://plaid.com/docs/api/products/investments/
- **SnapTrade API**: https://docs.snaptrade.com/
