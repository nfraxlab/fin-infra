# Goals Scaffold Templates

Auto-generated SQLAlchemy models, Pydantic schemas, and repository pattern for financial goal tracking.

## Overview

These templates generate production-ready persistence code for financial goals with:
- **Progress tracking**: Track current_amount vs target_amount with automatic percent_complete
- **Status management**: active, achieved, abandoned, paused states
- **Priority ranking**: High-priority goals (1=highest) to low-priority goals
- **Milestones**: JSON-based milestone tracking (e.g., "Halfway there!")
- **Categories**: emergency_fund, retirement, vacation, education, etc.
- **Multi-tenancy**: Optional tenant_id field for SaaS applications
- **Soft deletes**: Optional deleted_at field for safe deletion

## Template Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `${Entity}` | PascalCase entity name | `Goal` |
| `${entity}` | snake_case entity name | `goal` |
| `${table_name}` | Database table name | `goals` |
| `${tenant_field}` | Tenant field definition (if enabled) | `tenant_id: Mapped[str] = ...` |
| `${tenant_arg}` | Tenant arg in function signatures | `, tenant_id: str` |
| `${tenant_arg_unique_index}` | Tenant arg for unique indexes | `, tenant_field="tenant_id"` |
| `${tenant_arg_type}` | Optional tenant arg | `, tenant_id: Optional[str] = None` |
| `${tenant_arg_type_comma}` | Optional tenant arg with comma | `, tenant_id: Optional[str] = None` |
| `${tenant_arg_val}` | Tenant kwarg pass-through | `, tenant_id=tenant_id` |
| `${tenant_doc}` | Tenant parameter docstring | `tenant_id: Tenant identifier` |
| `${tenant_filter}` | SQLAlchemy WHERE clause | `.where(Goal.tenant_id == tenant_id)` |
| `${tenant_field_create}` | Pydantic create schema field | `tenant_id: str` |
| `${tenant_field_update}` | Pydantic update schema field | `tenant_id: Optional[str] = None` |
| `${soft_delete_field}` | Soft delete field definition | `deleted_at: Mapped[Optional[datetime]] = ...` |
| `${soft_delete_filter}` | Soft delete WHERE clause | `.where(Goal.deleted_at.is_(None))` |
| `${soft_delete_logic}` | Soft/hard delete implementation | `if soft: ... else: ...` |
| `${soft_delete_default}` | Default soft delete value | `False` or `None` |

## Usage

### Generate Basic Goals Model

```bash
fin-infra goals --dest-dir app/models/
```

Creates:
- `app/models/goal.py` - SQLAlchemy model
- `app/models/goal_schemas.py` - Pydantic schemas
- `app/models/goal_repository.py` - Repository pattern
- `app/models/__init__.py` - Package exports

### With Multi-Tenancy

```bash
fin-infra goals --dest-dir app/models/ --include-tenant
```

Adds:
- `tenant_id: Mapped[str]` field to model
- `tenant_id: str` to all Pydantic schemas
- Automatic tenant filtering in all queries
- Unique constraint: `(tenant_id, user_id, name)`

### With Soft Deletes

```bash
fin-infra goals --dest-dir app/models/ --include-soft-delete
```

Adds:
- `deleted_at: Mapped[Optional[datetime]]` field to model
- Automatic `deleted_at IS NULL` filtering in queries
- `soft` parameter in `delete()` method (default: True)

### Without Repository Pattern

```bash
fin-infra goals --dest-dir app/models/ --no-with-repository
```

Creates only:
- `app/models/goal.py` - SQLAlchemy model
- `app/models/goal_schemas.py` - Pydantic schemas
- `app/models/__init__.py` - Package exports

## Integration

### 1. Run Migrations

```bash
# Create migration
svc-infra revision -m "add goals table" --autogenerate

# Apply migration
svc-infra upgrade head
```

### 2. Wire Automatic CRUD (Optional)

```python
from svc_infra.api.fastapi.db.sql import SqlResource, add_sql_resources
from app.models.goal import Goal

# In your FastAPI app setup
add_sql_resources(app, [
    SqlResource(
        model=Goal,
        prefix="/goals",
        search_fields=["name", "description"],
        soft_delete=True,  # if --include-soft-delete used
    )
])
```

### 3. Use Repository Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.goal_repository import GoalRepository
from app.models.goal_schemas import GoalCreate
from datetime import datetime, timezone
from decimal import Decimal

async with AsyncSession(engine) as session:
    repo = GoalRepository(session)
    
    # Create goal
    goal = await repo.create(GoalCreate(
        user_id="user_123",
        name="Emergency Fund",
        description="Build 6-month emergency fund",
        target_amount=Decimal("10000.00"),
        current_amount=Decimal("2500.00"),
        target_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
        status="active",
        priority=1,
        category="emergency_fund",
        milestones=[
            {"amount": 5000, "label": "Halfway there!"},
            {"amount": 7500, "label": "Three-quarters done"}
        ]
    ))
    
    # Update progress
    updated_goal = await repo.update_progress(goal.id, Decimal("5000.00"))
    print(f"Progress: {updated_goal.percent_complete}%")  # 50.00%
    
    # List active goals
    active_goals = await repo.get_active("user_123")
    
    # Get high-priority goals (priority <= 2)
    priorities = await repo.get_by_priority("user_123", min_priority=2)
    
    await session.commit()
```

## Goal-Specific Features

### Status Lifecycle

- **active**: Goal is currently being worked on
- **achieved**: Target amount reached
- **abandoned**: User gave up on goal
- **paused**: Temporarily suspended

### Priority System

- Priority 1 = Highest importance (e.g., emergency fund)
- Priority 2-3 = Medium importance (e.g., vacation, car)
- Priority 4+ = Low importance (e.g., luxury items)

Repository methods sort by priority (1 first) then target_date.

### Progress Tracking

The `percent_complete` property calculates completion percentage:
- Formula: `(current_amount / target_amount) * 100`
- Automatically updated on read
- Used for progress bars, insights, etc.

### Milestones

Store structured milestone data in JSON:

```python
milestones = [
    {"amount": 2500, "label": "25% Complete", "reached_at": "2025-03-15T10:00:00Z"},
    {"amount": 5000, "label": "Halfway there!"},
    {"amount": 7500, "label": "Three-quarters done"}
]
```

Application logic can:
- Track when milestones are reached
- Celebrate progress with notifications
- Visualize progress in UI

## Customization

### Add Custom Fields

Edit `goal.py` to add domain-specific fields:

```python
# Add custom fields
contribution_schedule: Mapped[str] = mapped_column(
    String(32),
    nullable=True,
    doc="weekly, biweekly, monthly"
)

auto_contribute: Mapped[bool] = mapped_column(
    Boolean,
    default=False,
    doc="Auto-transfer from checking to goal"
)
```

### Add Custom Repository Methods

Edit `goal_repository.py`:

```python
async def get_overdue(
    self,
    user_id: str,
    tenant_id: Optional[str] = None
) -> List[GoalRead]:
    """Get goals past target_date that are still active."""
    now = datetime.now(timezone.utc)
    stmt = select(GoalModel).where(
        GoalModel.user_id == user_id,
        GoalModel.status == "active",
        GoalModel.target_date < now
    )
    # Add tenant/soft delete filters...
    result = await self.session.execute(stmt)
    return [_to_pydantic(g) for g in result.scalars().all()]
```

### Integrate with fin_infra

Use existing fin-infra modules:

```python
from fin_infra.analytics.insights import generate_goal_insights
from fin_infra.goals.management import FinancialGoalTracker

# Generate insights
insights = await generate_goal_insights(user_id, goals)

# Track goal progress
tracker = FinancialGoalTracker(llm=llm)
validation = await tracker.validate_goal(goal_data)
```

## Example: Personal Finance App

### Use Case: Emergency Fund Goal

```python
# User creates goal via API
goal = await repo.create(GoalCreate(
    user_id="user_alice",
    name="Emergency Fund",
    description="Save 6 months of expenses ($30k)",
    target_amount=Decimal("30000.00"),
    current_amount=Decimal("5000.00"),
    target_date=datetime(2026, 6, 30, tzinfo=timezone.utc),
    status="active",
    priority=1,
    category="emergency_fund",
    milestones=[
        {"amount": 10000, "label": "First $10k saved"},
        {"amount": 20000, "label": "Two-thirds there!"},
        {"amount": 30000, "label": "Goal achieved!"}
    ]
))

# User makes progress
await repo.update_progress(goal.id, Decimal("7500.00"))

# Check status
goal = await repo.get(goal.id)
print(f"Progress: {goal.percent_complete}%")  # 25.00%
print(f"Remaining: ${goal.target_amount - goal.current_amount}")  # $22,500.00

# User reaches goal
await repo.update_progress(goal.id, Decimal("30000.00"))
# Status automatically updates to 'achieved'
```

### Use Case: Retirement Planning

```python
# Multiple retirement goals
goals = [
    GoalCreate(
        user_id="user_bob",
        name="401(k) Max Contribution",
        target_amount=Decimal("23000.00"),  # 2025 limit
        target_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
        priority=1,
        category="retirement"
    ),
    GoalCreate(
        user_id="user_bob",
        name="Roth IRA Max Contribution",
        target_amount=Decimal("7000.00"),  # 2025 limit
        target_date=datetime(2025, 12, 31, tzinfo=timezone.utc),
        priority=2,
        category="retirement"
    ),
]

for goal_create in goals:
    await repo.create(goal_create)

# Get all retirement goals
retirement_goals = await repo.list(
    user_id="user_bob",
    category="retirement"
)
```

## See Also

- [Budgets Scaffold Templates](../../budgets/scaffold_templates/README.md) - Similar pattern for budget tracking
- [Net Worth Scaffold Templates](../../net_worth/scaffold_templates/README.md) - Snapshot-based net worth tracking
- [svc-infra Persistence Guide](https://github.com/your-org/svc-infra/blob/main/docs/persistence.md) - Base patterns and utilities
- [fin-infra Persistence Strategy](../../docs/presistence-strategy.md) - Overall architecture and decisions
