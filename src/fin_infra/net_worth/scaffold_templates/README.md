# Net Worth Scaffold Templates

Auto-generated SQLAlchemy models, Pydantic schemas, and repository pattern for net worth snapshot tracking.

## Overview

These templates generate production-ready persistence code for net worth snapshots with:
- **Point-in-time snapshots**: Immutable financial state captures at specific dates
- **Time-series analysis**: Track net worth growth over time (daily, weekly, monthly)
- **Breakdown tracking**: Categorize assets and liabilities (cash, stocks, real estate, loans, etc.)
- **Growth calculations**: Automatic calculation of absolute and percentage growth
- **Uniqueness constraint**: One snapshot per user per day
- **Multi-tenancy**: Optional tenant_id field for SaaS applications
- **Soft deletes**: Optional deleted_at field for safe deletion

## Template Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `${Entity}` | PascalCase entity name | `NetWorthSnapshot` |
| `${entity}` | snake_case entity name | `net_worth_snapshot` |
| `${table_name}` | Database table name | `net_worth_snapshots` |
| `${tenant_field}` | Tenant field definition (if enabled) | `tenant_id: Mapped[str] = ...` |
| `${tenant_arg}` | Tenant arg in function signatures | `, tenant_id: str` |
| `${tenant_arg_unique_index}` | Tenant arg for unique indexes | `, tenant_field="tenant_id"` |
| `${tenant_arg_type}` | Optional tenant arg | `, tenant_id: Optional[str] = None` |
| `${tenant_arg_type_comma}` | Optional tenant arg with comma | `, tenant_id: Optional[str] = None` |
| `${tenant_arg_val}` | Tenant kwarg pass-through | `, tenant_id=tenant_id` |
| `${tenant_doc}` | Tenant parameter docstring | `tenant_id: Tenant identifier` |
| `${tenant_filter}` | SQLAlchemy WHERE clause | `.where(NetWorthSnapshot.tenant_id == tenant_id)` |
| `${tenant_field_create}` | Pydantic create schema field | `tenant_id: str` |
| `${soft_delete_field}` | Soft delete field definition | `deleted_at: Mapped[Optional[datetime]] = ...` |
| `${soft_delete_filter}` | Soft delete WHERE clause | `.where(NetWorthSnapshot.deleted_at.is_(None))` |
| `${soft_delete_logic}` | Soft/hard delete implementation | `if soft: ... else: ...` |
| `${soft_delete_default}` | Default soft delete value | `False` or `None` |

## Usage

### Generate Basic Net Worth Model

```bash
fin-infra net_worth --dest-dir app/models/
```

Creates:
- `app/models/net_worth_snapshot.py` - SQLAlchemy model
- `app/models/net_worth_snapshot_schemas.py` - Pydantic schemas
- `app/models/net_worth_snapshot_repository.py` - Repository pattern
- `app/models/__init__.py` - Package exports

### With Multi-Tenancy

```bash
fin-infra net_worth --dest-dir app/models/ --include-tenant
```

Adds:
- `tenant_id: Mapped[str]` field to model
- `tenant_id: str` to all Pydantic schemas
- Automatic tenant filtering in all queries
- Unique constraint: `(tenant_id, user_id, snapshot_date)`

### With Soft Deletes

```bash
fin-infra net_worth --dest-dir app/models/ --include-soft-delete
```

Adds:
- `deleted_at: Mapped[Optional[datetime]]` field to model
- Automatic `deleted_at IS NULL` filtering in queries
- `soft` parameter in `delete()` method (default: True)

### Without Repository Pattern

```bash
fin-infra net_worth --dest-dir app/models/ --no-with-repository
```

Creates only:
- `app/models/net_worth_snapshot.py` - SQLAlchemy model
- `app/models/net_worth_snapshot_schemas.py` - Pydantic schemas
- `app/models/__init__.py` - Package exports

## Integration

### 1. Run Migrations

```bash
# Create migration
svc-infra revision -m "add net worth snapshots table" --autogenerate

# Apply migration
svc-infra upgrade head
```

### 2. Wire Automatic CRUD (Optional)

```python
from svc_infra.api.fastapi.db.sql import SqlResource, add_sql_resources
from app.models.net_worth_snapshot import NetWorthSnapshot

# In your FastAPI app setup
add_sql_resources(app, [
    SqlResource(
        model=NetWorthSnapshot,
        prefix="/net-worth-snapshots",
        search_fields=["user_id"],
        soft_delete=True,  # if --include-soft-delete used
    )
])
```

### 3. Use Repository Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.net_worth_snapshot_repository import NetWorthSnapshotRepository
from app.models.net_worth_snapshot_schemas import NetWorthSnapshotCreate
from datetime import datetime, timezone, date
from decimal import Decimal

async with AsyncSession(engine) as session:
    repo = NetWorthSnapshotRepository(session)
    
    # Create snapshot
    snapshot = await repo.create(NetWorthSnapshotCreate(
        user_id="user_123",
        snapshot_date=datetime.now(timezone.utc),
        total_assets=Decimal("150000.00"),
        total_liabilities=Decimal("50000.00"),
        net_worth=Decimal("100000.00"),  # Must equal total_assets - total_liabilities
        liquid_net_worth=Decimal("75000.00"),
        asset_breakdown={
            "cash": 10000.00,
            "stocks": 50000.00,
            "real_estate": 200000.00,
            "retirement": 40000.00
        },
        liability_breakdown={
            "credit_cards": 2000.00,
            "student_loans": 15000.00,
            "mortgage": 180000.00
        }
    ))
    
    # Get latest snapshot
    latest = await repo.get_latest("user_123")
    print(f"Current net worth: ${latest.net_worth}")
    
    # Get snapshot for specific date
    jan_snapshot = await repo.get_by_date("user_123", date(2025, 1, 31))
    
    # Get time series (last 12 months)
    trend = await repo.get_trend("user_123", months=12)
    for snap in trend:
        print(f"{snap.snapshot_date.date()}: ${snap.net_worth}")
    
    # Calculate growth
    growth = await repo.calculate_growth(
        "user_123",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 1, 1)
    )
    print(f"Growth: ${growth['absolute_growth']} ({growth['percent_growth']}%)")
    
    await session.commit()
```

## Net Worth Snapshot Patterns

### Daily Snapshots

Capture net worth daily for high-frequency tracking:

```python
from datetime import datetime, timezone
from decimal import Decimal

# Daily snapshot at end of day
snapshot = await repo.create(NetWorthSnapshotCreate(
    user_id="user_alice",
    snapshot_date=datetime.now(timezone.utc),
    total_assets=Decimal("152000.00"),
    total_liabilities=Decimal("51000.00"),
    net_worth=Decimal("101000.00")
))
```

**Use cases**:
- Day traders tracking portfolio value
- Apps showing daily net worth changes
- High-frequency wealth monitoring

### Weekly Snapshots

Capture net worth weekly (every Sunday):

```python
from datetime import datetime, timezone

# Weekly snapshot (Sunday at 11:59 PM)
if datetime.now().weekday() == 6:  # Sunday
    snapshot = await repo.create(...)
```

**Use cases**:
- Personal finance apps with weekly check-ins
- Budget tracking with weekly reviews
- Moderate-frequency wealth monitoring

### Monthly Snapshots

Capture net worth monthly (last day of month):

```python
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

# Monthly snapshot (last day of month)
today = datetime.now(timezone.utc)
next_month = today + relativedelta(months=1)
last_day = next_month.replace(day=1) - timedelta(days=1)

if today.date() == last_day.date():
    snapshot = await repo.create(...)
```

**Use cases**:
- Retirement planning (long-term tracking)
- Monthly financial reviews
- Low-frequency wealth monitoring

## Time Series Querying

### Get Recent Trend

```python
# Last 12 months
trend = await repo.get_trend("user_123", months=12)

# Plot net worth over time
import matplotlib.pyplot as plt

dates = [s.snapshot_date.date() for s in trend]
net_worths = [float(s.net_worth) for s in trend]

plt.plot(dates, net_worths)
plt.title("Net Worth Trend (12 Months)")
plt.xlabel("Date")
plt.ylabel("Net Worth ($)")
plt.show()
```

### Get Date Range

```python
from datetime import date

# Q1 2025 snapshots
q1_snapshots = await repo.get_by_date_range(
    "user_123",
    start_date=date(2025, 1, 1),
    end_date=date(2025, 3, 31)
)

# Calculate average Q1 net worth
avg_net_worth = sum(s.net_worth for s in q1_snapshots) / len(q1_snapshots)
print(f"Q1 2025 Average Net Worth: ${avg_net_worth}")
```

### Compare Year-over-Year

```python
from datetime import date

# Compare Jan 2024 vs Jan 2025
growth = await repo.calculate_growth(
    "user_123",
    start_date=date(2024, 1, 31),
    end_date=date(2025, 1, 31)
)

print(f"YoY Growth: ${growth['absolute_growth']} ({growth['percent_growth']}%)")
# Output: YoY Growth: $25000.00 (33.33%)
```

## Growth Calculation Patterns

### Absolute Growth

```python
growth = await repo.calculate_growth(
    "user_123",
    start_date=date(2024, 1, 1),
    end_date=date(2025, 1, 1)
)

print(f"Absolute Growth: ${growth['absolute_growth']}")
# Output: Absolute Growth: $25000.00
```

### Percentage Growth

```python
print(f"Percentage Growth: {growth['percent_growth']}%")
# Output: Percentage Growth: 33.33%
```

### Annualized Growth Rate

```python
# Calculate annualized return
days = growth['days']
years = days / 365.25
annualized = (1 + growth['percent_growth'] / 100) ** (1 / years) - 1

print(f"Annualized Growth Rate: {annualized * 100:.2f}%")
```

## Integration with fin_infra

### Use Existing Net Worth Tracker

```python
from fin_infra.net_worth.tracker import NetWorthTracker
from sqlalchemy.ext.asyncio import AsyncSession

async with AsyncSession(engine) as session:
    tracker = NetWorthTracker(session)
    
    # Automatically creates snapshot from accounts
    snapshot = await tracker.create_snapshot("user_123")
    
    # Uses generated repository under the hood
    latest = await tracker.get_latest("user_123")
```

### Integrate with Account Aggregation

```python
from fin_infra.banking import easy_banking
from decimal import Decimal

# Get account balances from Plaid
banking = easy_banking(provider="plaid")
accounts = await banking.get_accounts(access_token)

# Calculate totals
total_assets = sum(Decimal(str(acc.balance)) for acc in accounts if acc.type in ["depository", "investment"])
total_liabilities = sum(abs(Decimal(str(acc.balance))) for acc in accounts if acc.type == "credit")

# Create snapshot
snapshot = await repo.create(NetWorthSnapshotCreate(
    user_id="user_123",
    snapshot_date=datetime.now(timezone.utc),
    total_assets=total_assets,
    total_liabilities=total_liabilities,
    net_worth=total_assets - total_liabilities,
    accounts_data={acc.account_id: acc.balance for acc in accounts}
))
```

## Customization

### Add Custom Fields

Edit `net_worth_snapshot.py` to add domain-specific fields:

```python
# Add custom fields
investment_return: Mapped[Decimal] = mapped_column(
    Numeric(15, 2),
    nullable=True,
    doc="Investment returns for the period"
)

cash_flow: Mapped[Decimal] = mapped_column(
    Numeric(15, 2),
    nullable=True,
    doc="Net cash flow (income - expenses)"
)
```

### Add Custom Repository Methods

Edit `net_worth_snapshot_repository.py`:

```python
async def get_highest_net_worth(
    self,
    user_id: str,
    tenant_id: Optional[str] = None
) -> Optional[NetWorthSnapshotRead]:
    """Get snapshot with highest net worth for user."""
    stmt = (
        select(NetWorthSnapshotModel)
        .where(NetWorthSnapshotModel.user_id == user_id)
        # Add tenant/soft delete filters...
        .order_by(NetWorthSnapshotModel.net_worth.desc())
        .limit(1)
    )
    result = await self.session.execute(stmt)
    db_snapshot = result.scalar_one_or_none()
    return _to_pydantic(db_snapshot) if db_snapshot else None
```

## Example: Personal Finance Dashboard

### Use Case: Monthly Net Worth Tracking

```python
from datetime import date, datetime, timezone
from decimal import Decimal

# User creates monthly snapshots
for month in range(1, 13):  # Jan - Dec 2025
    snapshot = await repo.create(NetWorthSnapshotCreate(
        user_id="user_charlie",
        snapshot_date=datetime(2025, month, 1, tzinfo=timezone.utc),
        total_assets=Decimal(str(100000 + month * 5000)),  # Growing
        total_liabilities=Decimal(str(50000 - month * 1000)),  # Decreasing
        net_worth=Decimal(str(50000 + month * 6000)),
        asset_breakdown={
            "cash": 10000 + month * 500,
            "stocks": 60000 + month * 3000,
            "real_estate": 200000,
        },
        liability_breakdown={
            "mortgage": 45000 - month * 1000,
            "credit_cards": 5000
        }
    ))

# Analyze year-end
growth = await repo.calculate_growth(
    "user_charlie",
    start_date=date(2025, 1, 1),
    end_date=date(2025, 12, 1)
)

print(f"2025 Growth: ${growth['absolute_growth']} ({growth['percent_growth']}%)")
# Output: 2025 Growth: $66000.00 (132.00%)
```

### Use Case: Retirement Planning Dashboard

```python
# Track retirement progress over 30 years
import asyncio
from datetime import date

async def project_retirement():
    # Historical snapshots (past 10 years)
    historical = await repo.get_by_date_range(
        "user_dave",
        start_date=date(2015, 1, 1),
        end_date=date(2025, 1, 1)
    )
    
    # Calculate average annual growth
    growth_10y = await repo.calculate_growth(
        "user_dave",
        start_date=date(2015, 1, 1),
        end_date=date(2025, 1, 1)
    )
    
    annual_growth_rate = growth_10y['percent_growth'] / 10  # Simple average
    
    # Project next 20 years
    current_net_worth = (await repo.get_latest("user_dave")).net_worth
    future_net_worth = current_net_worth * (1 + annual_growth_rate / 100) ** 20
    
    print(f"Current Net Worth: ${current_net_worth}")
    print(f"Projected Net Worth (20 years): ${future_net_worth:.2f}")
    print(f"Annual Growth Rate: {annual_growth_rate:.2f}%")

asyncio.run(project_retirement())
```

## See Also

- [Budgets Scaffold Templates](../../budgets/scaffold_templates/README.md) - Budget tracking patterns
- [Goals Scaffold Templates](../../goals/scaffold_templates/README.md) - Financial goal tracking
- [svc-infra Persistence Guide](https://github.com/your-org/svc-infra/blob/main/docs/persistence.md) - Base patterns and utilities
- [fin-infra Persistence Strategy](../../docs/presistence-strategy.md) - Overall architecture and decisions
- [fin-infra Net Worth Module](../../net_worth/README.md) - Higher-level net worth tracking utilities
