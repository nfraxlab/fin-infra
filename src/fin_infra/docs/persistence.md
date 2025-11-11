# Persistence Guide

**fin-infra is a stateless library** - your application owns its database schema, migrations, and data storage. This design philosophy makes fin-infra flexible, framework-agnostic, and easy to integrate into any application architecture.

## Table of Contents

- [Why fin-infra is Stateless](#why-fin-infra-is-stateless)
- [Scaffold + add_sql_resources() Workflow](#scaffold--add_sql_resources-workflow)
- [When to Use Scaffold vs Manual Templates](#when-to-use-scaffold-vs-manual-templates)
- [Step-by-Step Scaffold Guide](#step-by-step-scaffold-guide)
- [Integration with svc-infra](#integration-with-svc-infra)
- [Multi-Tenancy Patterns](#multi-tenancy-patterns)
- [Soft Delete Patterns](#soft-delete-patterns)
- [Testing Strategies](#testing-strategies)
- [Example Workflows](#example-workflows)
- [Troubleshooting](#troubleshooting)

---

## Why fin-infra is Stateless

### Library vs Framework

**fin-infra is a library**, like `stripe-python` or `plaid-python`:
- ✅ Provides financial provider integrations (Plaid, Alpaca, market data)
- ✅ Provides financial calculations (NPV, IRR, portfolio analytics)
- ✅ Provides domain models (Transaction, Account, NetWorthSnapshot schemas)
- ✅ **Does NOT** manage your database
- ✅ **Does NOT** require specific database schema
- ✅ **Does NOT** run migrations on your behalf

**Contrast with frameworks** like Django or Rails:
- ❌ Impose ORM (ActiveRecord, Django ORM)
- ❌ Manage database migrations
- ❌ Couple application to framework database layer
- ❌ Require specific schema conventions

### Benefits of Stateless Design

1. **No Database Dependency**: Use any database (PostgreSQL, MySQL, SQLite, MongoDB) or no database at all
2. **Application Flexibility**: Choose your own ORM (SQLAlchemy, Prisma, raw SQL)
3. **No Version Coupling**: Upgrade fin-infra without database migration conflicts
4. **Testing Simplicity**: Mock provider responses, use in-memory storage for unit tests
5. **Deployment Freedom**: Deploy as library in monolith, microservice, serverless, or edge runtime

### Comparison: Libraries vs Frameworks

| Feature | fin-infra (Library) | stripe-python | plaid-python | Django (Framework) | Rails (Framework) |
|---------|---------------------|---------------|--------------|-------------------|-------------------|
| **Database Management** | ❌ No | ❌ No | ❌ No | ✅ Yes (ORM) | ✅ Yes (ActiveRecord) |
| **Schema Ownership** | ✅ Your app | ✅ Your app | ✅ Your app | ❌ Framework | ❌ Framework |
| **Migration Tool** | ✅ Your choice | ✅ Your choice | ✅ Your choice | ❌ Django migrations | ❌ Rails migrations |
| **ORM Flexibility** | ✅ Any ORM | ✅ Any ORM | ✅ Any ORM | ❌ Django ORM only | ❌ ActiveRecord only |
| **Provider Integrations** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Financial Calculations** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |

---

## Scaffold + add_sql_resources() Workflow

The **PRIMARY PATTERN** for persistence in fin-infra is:

1. **Scaffold** models/schemas/repository from templates
2. **Migrate** with svc-infra Alembic integration
3. **Wire CRUD** with ONE function call: `add_sql_resources()`

This pattern gives you production-ready CRUD APIs with **zero manual router code**.

### Complete Example: Budget CRUD in 3 Steps

#### Step 1: Generate Models with Scaffold CLI

```bash
# Scaffold budgets with multi-tenancy
fin-infra scaffold budgets --dest-dir app/models/budgets --include-tenant
```

**Generated files**:
```
app/models/budgets/
├── budget.py              # SQLAlchemy model (Budget)
├── budget_schemas.py      # Pydantic schemas (BudgetCreate, BudgetRead, BudgetUpdate)
├── budget_repository.py   # Repository pattern (BudgetRepository)
└── __init__.py            # Re-exports
```

**What you get**:
- ✅ SQLAlchemy model with `tenant_id` field, indexes, constraints
- ✅ Pydantic schemas for validation (Create, Read, Update)
- ✅ Repository with full CRUD: `create()`, `get()`, `list()`, `update()`, `delete()`
- ✅ Type hints and docstrings throughout
- ✅ Production-ready patterns (UUID primary keys, timestamps, soft delete support)

#### Step 2: Run svc-infra Migrations

```bash
# Create migration (auto-detects models)
svc-infra revision -m "add budgets table" --autogenerate

# Apply migration
svc-infra upgrade head
```

**What happens**:
- svc-infra discovers `Budget` model via `ModelBase` inheritance
- Alembic auto-generates migration from model changes
- Migration creates `budgets` table with all fields, indexes, constraints

#### Step 3: Wire CRUD with ONE Function Call

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource
from app.models.budgets import Budget

app = FastAPI()

# ONE FUNCTION CALL → Full CRUD API
add_sql_resources(app, [
    SqlResource(
        model=Budget,
        prefix="/budgets",
        search_fields=["name", "description"],
        order_fields=["name", "created_at"],
        soft_delete=False,
    )
])
```

**What you get** (automatic, zero code):

```
POST   /budgets/              # Create budget
GET    /budgets/              # List budgets (paginated, searchable, orderable)
GET    /budgets/{id}          # Get budget by ID
PATCH  /budgets/{id}          # Update budget
DELETE /budgets/{id}          # Delete budget
GET    /budgets/search        # Search budgets (q=name, category, etc)
```

### Benefits of This Workflow

- **Automatic Pagination**: `?page=1&page_size=20` (configurable)
- **Automatic Search**: `?q=groceries` searches across `search_fields`
- **Automatic Ordering**: `?order_by=name&order_dir=asc`
- **Automatic Filtering**: `?category=personal&active=true`
- **Automatic Soft Delete**: `?include_deleted=false` (if enabled)
- **OpenAPI Schema**: Full Swagger/ReDoc documentation auto-generated
- **Type Safety**: Pydantic validation on all requests/responses
- **Dependency Injection**: Easy to mock repository for testing

### Reference: svc-infra SqlResource Documentation

For full details on `add_sql_resources()` configuration, see:
- [svc-infra SQL README](https://github.com/your-org/svc-infra/blob/main/src/svc_infra/api/fastapi/db/sql/README.md)
- Available options: `search_fields`, `order_fields`, `filter_fields`, `soft_delete`, `tenant_field`, `permission_rules`

---

## When to Use Scaffold vs Manual Templates

### Use Scaffold CLI When:

✅ **Quick start**: Need working models/schemas/repository in seconds  
✅ **Standard patterns**: Budget, Goal, NetWorthSnapshot follow common patterns  
✅ **Rapid prototyping**: Iterate on schema quickly without manual boilerplate  
✅ **Learning**: Understand best practices from generated code  
✅ **Consistency**: Ensure all domains follow same conventions  

**Example scenarios**:
- New fintech startup building MVP
- Adding new domain to existing application
- Creating proof-of-concept with real database
- Teaching team svc-infra patterns

### Use Manual Templates When:

✅ **Full customization**: Need complex business logic not in scaffold templates  
✅ **Existing codebase**: Integrating fin-infra into legacy system with established patterns  
✅ **Complex schemas**: Many-to-many relationships, polymorphic associations, JSON fields  
✅ **Performance optimization**: Hand-tuned queries, custom indexes, materialized views  
✅ **Non-standard ORM**: Using Prisma, Tortoise ORM, raw SQL instead of SQLAlchemy  

**Example scenarios**:
- Migrating from Django/Rails to FastAPI
- Enterprise application with strict schema conventions
- High-performance trading platform requiring custom queries
- Using MongoDB or DynamoDB instead of SQL

### Hybrid Approach

**Scaffold first, customize later**:

```bash
# 1. Scaffold to get 80% of the way there
fin-infra scaffold budgets --dest-dir app/models/budgets

# 2. Customize generated files
# - Add custom fields (e.g., `budget.py`: add approval_workflow field)
# - Add custom methods (e.g., `budget_repository.py`: add get_pending_approval())
# - Add custom validation (e.g., `budget_schemas.py`: add business rules)

# 3. Maintain customizations through scaffold updates
# - Use version control to see scaffold changes
# - Merge updates while preserving customizations
```

---

## Step-by-Step Scaffold Guide

### 1. Choose Domain

Available domains:
- **budgets**: Monthly/yearly budgets with categories, rollover, tracking
- **goals**: Financial goals with progress tracking, milestones, status
- **net_worth**: Immutable snapshots with time-series queries, growth calculations

### 2. Run Scaffold Command with Flags

```bash
# Basic scaffold (no flags)
fin-infra scaffold budgets --dest-dir app/models/budgets

# With multi-tenancy (adds tenant_id field)
fin-infra scaffold budgets --dest-dir app/models/budgets --include-tenant

# With soft delete (adds deleted_at field)
fin-infra scaffold budgets --dest-dir app/models/budgets --include-soft-delete

# Combined flags
fin-infra scaffold budgets --dest-dir app/models/budgets \
    --include-tenant \
    --include-soft-delete

# Without repository (use svc-infra SqlRepository directly)
fin-infra scaffold budgets --dest-dir app/models/budgets --no-with-repository

# Custom filenames
fin-infra scaffold budgets --dest-dir app/models/budgets \
    --models-filename my_budget.py \
    --schemas-filename my_schemas.py \
    --repository-filename my_repo.py

# Overwrite existing files
fin-infra scaffold budgets --dest-dir app/models/budgets --overwrite
```

### 3. Review Generated Files

**budget.py** (SQLAlchemy model):
```python
from svc_infra.db.sql.models import ModelBase
from sqlalchemy import String, Numeric, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

class Budget(ModelBase):
    __tablename__ = "budgets"
    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    categories: Mapped[dict] = mapped_column(JSON, nullable=False)
    # ... more fields
```

**budget_schemas.py** (Pydantic schemas):
```python
from pydantic import BaseModel, Field
from datetime import datetime

class BudgetBase(BaseModel):
    name: str = Field(..., description="Budget name")
    period_start: datetime
    period_end: datetime
    categories: dict[str, float]

class BudgetCreate(BudgetBase):
    user_id: str

class BudgetRead(BudgetBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

class BudgetUpdate(BaseModel):
    name: str | None = None
    categories: dict[str, float] | None = None
```

**budget_repository.py** (Repository pattern):
```python
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

class BudgetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, budget: BudgetCreate) -> BudgetRead:
        """Create new budget."""
        # ... implementation
    
    async def get(self, budget_id: str) -> Optional[BudgetRead]:
        """Get budget by ID."""
        # ... implementation
    
    async def list(self, user_id: str, limit: int = 100) -> List[BudgetRead]:
        """List user's budgets."""
        # ... implementation
    
    async def update(self, budget_id: str, updates: BudgetUpdate) -> BudgetRead:
        """Update budget."""
        # ... implementation
    
    async def delete(self, budget_id: str, soft: bool = False) -> None:
        """Delete budget (soft or hard)."""
        # ... implementation
```

### 4. Customize for Your Needs

**Add custom fields**:
```python
# budget.py
class Budget(ModelBase):
    # ... existing fields ...
    
    # Add custom fields
    approval_status: Mapped[str] = mapped_column(String(50), default="pending")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
```

**Add custom methods**:
```python
# budget_repository.py
class BudgetRepository:
    # ... existing methods ...
    
    async def get_pending_approval(self, user_id: str) -> List[BudgetRead]:
        """Get budgets pending approval."""
        stmt = (
            select(Budget)
            .where(Budget.user_id == user_id)
            .where(Budget.approval_status == "pending")
        )
        result = await self.session.execute(stmt)
        budgets = result.scalars().all()
        return [self._to_schema(b) for b in budgets]
```

**Add custom validation**:
```python
# budget_schemas.py
from pydantic import field_validator

class BudgetCreate(BudgetBase):
    user_id: str
    
    @field_validator('categories')
    @classmethod
    def validate_categories(cls, v):
        if not v:
            raise ValueError("Must have at least one category")
        if any(amount < 0 for amount in v.values()):
            raise ValueError("Category amounts must be positive")
        if sum(v.values()) > 1_000_000:
            raise ValueError("Total budget cannot exceed $1,000,000")
        return v
```

### 5. Create Alembic Migration

```bash
# Auto-generate migration from model changes
svc-infra revision -m "add budgets table" --autogenerate

# Review generated migration in migrations/versions/
# Edit if needed (add custom indexes, constraints, etc)
```

### 6. Apply Migration

```bash
# Apply to database
svc-infra upgrade head

# Or rollback if needed
svc-infra downgrade -1
```

### 7. Use Repository in Application

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.budgets import BudgetRepository, BudgetCreate

async def get_session() -> AsyncSession:
    """Dependency for database session."""
    async with async_session_maker() as session:
        yield session

@app.post("/budgets")
async def create_budget(
    budget: BudgetCreate,
    session: AsyncSession = Depends(get_session),
):
    repo = BudgetRepository(session)
    return await repo.create(budget)
```

---

## Integration with svc-infra

### ModelBase Discovery Mechanism

All scaffolded models inherit from `svc_infra.db.sql.models.ModelBase`:

```python
from svc_infra.db.sql.models import ModelBase

class Budget(ModelBase):
    __tablename__ = "budgets"
    # ... fields
```

**Benefits**:
- ✅ Automatic Alembic discovery (no need to manually import models)
- ✅ Common base fields (id, created_at, updated_at)
- ✅ Consistent conventions across all models
- ✅ SQLAlchemy 2.0 modern style (Mapped, mapped_column)

### Alembic env.py Configuration

**svc-infra's `env.py`** (in your application's `migrations/` folder):

```python
# migrations/env.py
import os
from svc_infra.db.sql.models import ModelBase
from svc_infra.db.alembic import discover_and_import_models

# Discover models from environment variable
DISCOVER_PACKAGES = os.getenv("DISCOVER_PACKAGES", "app.models")
discover_and_import_models(DISCOVER_PACKAGES)

# Use ModelBase.metadata for autogenerate
target_metadata = ModelBase.metadata
```

### DISCOVER_PACKAGES Environment Variable

Tell svc-infra where to find your models:

```bash
# .env
DISCOVER_PACKAGES=app.models,another_package.models

# Or in your shell
export DISCOVER_PACKAGES=app.models

# Or inline with svc-infra command
DISCOVER_PACKAGES=app.models svc-infra revision -m "add budgets" --autogenerate
```

**How it works**:
1. svc-infra imports all modules in `DISCOVER_PACKAGES`
2. Any class inheriting from `ModelBase` is registered
3. Alembic compares `ModelBase.metadata` with database
4. Auto-generates migration with all changes

### Migration Workflow

```bash
# 1. Set discovery path (or use .env)
export DISCOVER_PACKAGES=app.models

# 2. Create migration (auto-detects changes)
svc-infra revision -m "add budgets table" --autogenerate

# 3. Review generated migration
cat migrations/versions/abc123_add_budgets_table.py

# 4. Edit migration if needed (add custom SQL, data migrations)
vim migrations/versions/abc123_add_budgets_table.py

# 5. Apply migration
svc-infra upgrade head

# 6. Check migration status
svc-infra current
svc-infra history

# 7. Rollback if needed
svc-infra downgrade -1          # Rollback one version
svc-infra downgrade abc123      # Rollback to specific version
```

---

## Multi-Tenancy Patterns

### When to Use --include-tenant Flag

Use multi-tenancy when:
- ✅ Building SaaS application with multiple customers
- ✅ Need data isolation between organizations
- ✅ Want to use PostgreSQL Row-Level Security (RLS)
- ✅ Application serves multiple teams/workspaces

**Example**: Budgeting SaaS where each company has separate budgets.

### Tenant Isolation Strategies

#### 1. Shared Database with tenant_id (Scaffold Default)

```bash
fin-infra scaffold budgets --dest-dir app/models/budgets --include-tenant
```

**Generated model**:
```python
class Budget(ModelBase):
    __tablename__ = "budgets"
    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Added
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # ... other fields
```

**Unique constraint** includes tenant:
```python
__table_args__ = (
    UniqueConstraint("tenant_id", "user_id", "name", name="uq_budget_tenant_user_name"),
)
```

**Repository queries** filter by tenant:
```python
async def list(self, tenant_id: str, user_id: str) -> List[BudgetRead]:
    stmt = (
        select(Budget)
        .where(Budget.tenant_id == tenant_id)  # Tenant isolation
        .where(Budget.user_id == user_id)
    )
    # ...
```

#### 2. Row-Level Security (RLS) with PostgreSQL

**Enable RLS on table**:
```sql
-- In migration or manual SQL
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their tenant's data
CREATE POLICY tenant_isolation ON budgets
    USING (tenant_id = current_setting('app.current_tenant')::text);
```

**Set tenant in application**:
```python
from sqlalchemy import text

async def set_tenant(session: AsyncSession, tenant_id: str):
    await session.execute(text(f"SET app.current_tenant = '{tenant_id}'"))

@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        async with async_session_maker() as session:
            await set_tenant(session, tenant_id)
    return await call_next(request)
```

#### 3. Separate Databases per Tenant

**Not recommended with scaffold** - use shared database with `tenant_id` instead.

If you need separate databases:
- Use connection pooling with tenant-specific DSNs
- Manage migrations per tenant database
- Consider operational complexity (backups, monitoring, scaling)

### Example: Multi-Tenant Budget Application

```python
# app/main.py
from fastapi import FastAPI, Header, HTTPException
from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource
from app.models.budgets import Budget

app = FastAPI()

# Multi-tenant CRUD (tenant_id from header)
add_sql_resources(app, [
    SqlResource(
        model=Budget,
        prefix="/budgets",
        tenant_field="tenant_id",  # Enable tenant isolation
        search_fields=["name"],
    )
])

# Custom endpoint with tenant isolation
@app.get("/budgets/summary")
async def get_budget_summary(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    session: AsyncSession = Depends(get_session),
):
    repo = BudgetRepository(session)
    budgets = await repo.list(tenant_id=x_tenant_id, user_id="current_user")
    return {"tenant_id": x_tenant_id, "count": len(budgets)}
```

---

## Soft Delete Patterns

### When to Use --include-soft-delete Flag

Use soft delete when:
- ✅ Need audit trail of deleted records
- ✅ Want to support "undo" or "restore" functionality
- ✅ Compliance requires retention of deleted data
- ✅ Need to preserve foreign key integrity after deletion

**Example**: Budgets that can be archived and later restored.

### Generated Code with Soft Delete

```bash
fin-infra scaffold budgets --dest-dir app/models/budgets --include-soft-delete
```

**Model with deleted_at**:
```python
class Budget(ModelBase):
    __tablename__ = "budgets"
    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # ... other fields
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # Added for soft delete
```

**Repository with soft delete support**:
```python
async def delete(self, budget_id: str, soft: bool = True) -> None:
    """Delete budget (soft by default, hard if soft=False)."""
    budget = await self.get(budget_id)
    if not budget:
        raise ValueError(f"Budget not found: {budget_id}")
    
    if soft:
        # Soft delete: set deleted_at timestamp
        budget.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
    else:
        # Hard delete: remove from database
        await self.session.delete(budget)
        await self.session.commit()

async def list(
    self,
    user_id: str,
    include_deleted: bool = False,
) -> List[BudgetRead]:
    """List budgets (exclude soft-deleted by default)."""
    stmt = select(Budget).where(Budget.user_id == user_id)
    
    if not include_deleted:
        stmt = stmt.where(Budget.deleted_at.is_(None))  # Filter soft-deleted
    
    # ... rest of query
```

### Query Filtering

**Default behavior** (exclude deleted):
```python
budgets = await repo.list(user_id="user123")
# Only returns budgets where deleted_at IS NULL
```

**Include deleted**:
```python
all_budgets = await repo.list(user_id="user123", include_deleted=True)
# Returns all budgets, including soft-deleted
```

**Only deleted**:
```python
async def list_deleted(self, user_id: str) -> List[BudgetRead]:
    """List only soft-deleted budgets."""
    stmt = (
        select(Budget)
        .where(Budget.user_id == user_id)
        .where(Budget.deleted_at.is_not(None))  # Only soft-deleted
    )
    # ...
```

### Hard Delete vs Soft Delete Tradeoffs

| Feature | Soft Delete | Hard Delete |
|---------|-------------|-------------|
| **Recoverability** | ✅ Can restore | ❌ Permanent loss |
| **Audit Trail** | ✅ Full history | ❌ No record |
| **Query Performance** | ❌ Slower (more rows) | ✅ Faster |
| **Storage** | ❌ More space | ✅ Less space |
| **Compliance** | ✅ Better (retention) | ❌ Worse |
| **Foreign Keys** | ✅ No cascade issues | ❌ Cascade deletes |
| **Unique Constraints** | ❌ Complex (need NULL) | ✅ Simple |

**Best practice**: Use soft delete by default, add hard delete option for cleanup:

```python
# Soft delete for normal operations
await repo.delete(budget_id, soft=True)

# Hard delete for admin cleanup (periodic job)
async def cleanup_old_deleted_budgets():
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    stmt = select(Budget).where(Budget.deleted_at < cutoff)
    old_budgets = await session.execute(stmt)
    for budget in old_budgets.scalars():
        await repo.delete(budget.id, soft=False)  # Hard delete
```

### Example: Recoverable Budget Deletion

```python
@app.delete("/budgets/{budget_id}")
async def delete_budget(
    budget_id: str,
    session: AsyncSession = Depends(get_session),
):
    repo = BudgetRepository(session)
    await repo.delete(budget_id, soft=True)  # Soft delete
    return {"message": "Budget deleted (can be restored)"}

@app.post("/budgets/{budget_id}/restore")
async def restore_budget(
    budget_id: str,
    session: AsyncSession = Depends(get_session),
):
    # Custom restore method
    stmt = select(Budget).where(Budget.id == budget_id)
    result = await session.execute(stmt)
    budget = result.scalars().first()
    
    if not budget:
        raise HTTPException(404, "Budget not found")
    if budget.deleted_at is None:
        raise HTTPException(400, "Budget not deleted")
    
    budget.deleted_at = None  # Restore
    await session.commit()
    return {"message": "Budget restored"}
```

---

## Testing Strategies

### Unit Tests with In-Memory Storage

Use the **tracker pattern** from fin-infra (BudgetTracker, NetWorthTracker):

```python
# tests/unit/test_budget_logic.py
import pytest
from fin_infra.budgets.tracker import BudgetTracker

@pytest.mark.asyncio
async def test_budget_creation():
    tracker = BudgetTracker()  # In-memory storage
    
    budget = await tracker.create_budget(
        user_id="user123",
        name="November 2025",
        period_start=datetime(2025, 11, 1),
        period_end=datetime(2025, 11, 30),
        categories={"Groceries": 600.00, "Dining": 200.00},
    )
    
    assert budget.user_id == "user123"
    assert budget.name == "November 2025"
    assert budget.categories["Groceries"] == 600.00
```

**Benefits**:
- ✅ Fast (no database I/O)
- ✅ Isolated (no test pollution)
- ✅ Simple (no fixtures or migrations)

### Integration Tests with Test Database

Use **aiosqlite** for fast in-memory SQL database:

```python
# tests/integration/test_budget_repository.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.budgets import Budget, BudgetRepository, BudgetCreate

@pytest.fixture
async def test_session():
    # Create in-memory SQLite database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Budget.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_budget_repository_create(test_session):
    repo = BudgetRepository(test_session)
    
    budget_create = BudgetCreate(
        user_id="user123",
        name="Test Budget",
        period_start=datetime(2025, 11, 1),
        period_end=datetime(2025, 11, 30),
        categories={"Groceries": 600.00},
    )
    
    budget = await repo.create(budget_create)
    
    assert budget.id is not None
    assert budget.user_id == "user123"
    assert budget.name == "Test Budget"
```

**Benefits**:
- ✅ Fast (in-memory SQLite)
- ✅ Real database (tests SQL queries)
- ✅ Isolated (each test gets clean DB)

### Acceptance Tests with Real Database

Use **PostgreSQL test container** for full integration:

```python
# tests/acceptance/test_budget_api.py
import pytest
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture
async def test_client(postgres_container):
    # Apply migrations to test database
    database_url = postgres_container.get_connection_url()
    # Run: svc-infra upgrade head
    
    client = TestClient(app)
    yield client

def test_budget_crud_e2e(test_client):
    # Create budget
    response = test_client.post("/budgets", json={
        "user_id": "user123",
        "name": "November 2025",
        "period_start": "2025-11-01T00:00:00Z",
        "period_end": "2025-11-30T23:59:59Z",
        "categories": {"Groceries": 600.00},
    })
    assert response.status_code == 200
    budget_id = response.json()["id"]
    
    # Get budget
    response = test_client.get(f"/budgets/{budget_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "November 2025"
    
    # List budgets
    response = test_client.get("/budgets")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
```

**Benefits**:
- ✅ Full integration (real PostgreSQL)
- ✅ Tests migrations
- ✅ Catches database-specific issues

### Fixture Patterns for Repositories

```python
# tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models.budgets import Budget, BudgetRepository

@pytest.fixture
async def budget_repo(test_session) -> BudgetRepository:
    """Fixture providing BudgetRepository."""
    return BudgetRepository(test_session)

@pytest.fixture
async def sample_budget(budget_repo) -> Budget:
    """Fixture providing a sample budget."""
    budget_create = BudgetCreate(
        user_id="user123",
        name="Test Budget",
        period_start=datetime(2025, 11, 1),
        period_end=datetime(2025, 11, 30),
        categories={"Groceries": 600.00},
    )
    return await budget_repo.create(budget_create)

# Use in tests
@pytest.mark.asyncio
async def test_budget_update(budget_repo, sample_budget):
    updated = await budget_repo.update(
        sample_budget.id,
        BudgetUpdate(name="Updated Budget")
    )
    assert updated.name == "Updated Budget"
```

---

## Example Workflows

### Personal Finance App (Single-Tenant)

**Architecture**:
- Single user per database
- PostgreSQL for persistence
- No tenant_id needed
- Soft delete for recoverability

**Scaffold**:
```bash
# Budgets (no tenant, with soft delete)
fin-infra scaffold budgets --dest-dir app/models/budgets --include-soft-delete

# Goals (no tenant, no soft delete)
fin-infra scaffold goals --dest-dir app/models/goals

# Net worth (no tenant, with soft delete)
fin-infra scaffold net_worth --dest-dir app/models/net_worth --include-soft-delete
```

**Wire CRUD**:
```python
from fastapi import FastAPI
from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource
from app.models.budgets import Budget
from app.models.goals import Goal
from app.models.net_worth import NetWorthSnapshot

app = FastAPI()

add_sql_resources(app, [
    SqlResource(model=Budget, prefix="/budgets", search_fields=["name"], soft_delete=True),
    SqlResource(model=Goal, prefix="/goals", search_fields=["name"]),
    SqlResource(model=NetWorthSnapshot, prefix="/net-worth", search_fields=["user_id"]),
])
```

### SaaS Budgeting Platform (Multi-Tenant)

**Architecture**:
- Multiple companies per database
- PostgreSQL with Row-Level Security (RLS)
- tenant_id required on all tables
- Soft delete for compliance

**Scaffold**:
```bash
# Budgets (with tenant and soft delete)
fin-infra scaffold budgets --dest-dir app/models/budgets \
    --include-tenant \
    --include-soft-delete

# Goals (with tenant)
fin-infra scaffold goals --dest-dir app/models/goals --include-tenant

# Net worth (with tenant and soft delete)
fin-infra scaffold net_worth --dest-dir app/models/net_worth \
    --include-tenant \
    --include-soft-delete
```

**Enable RLS**:
```sql
-- migrations/versions/abc123_enable_rls.py
def upgrade():
    op.execute("ALTER TABLE budgets ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON budgets
        USING (tenant_id = current_setting('app.current_tenant')::text)
    """)

def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON budgets")
    op.execute("ALTER TABLE budgets DISABLE ROW LEVEL SECURITY")
```

**Wire CRUD with Tenant Middleware**:
```python
from fastapi import FastAPI, Request, Header
from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource

app = FastAPI()

@app.middleware("http")
async def set_tenant_context(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        # Set tenant in session for RLS
        async with async_session_maker() as session:
            await session.execute(text(f"SET app.current_tenant = '{tenant_id}'"))
    return await call_next(request)

add_sql_resources(app, [
    SqlResource(
        model=Budget,
        prefix="/budgets",
        tenant_field="tenant_id",  # Enforce tenant isolation
        search_fields=["name"],
        soft_delete=True,
    ),
])
```

### Wealth Management App (Multi-Tenant, MySQL)

**Architecture**:
- Multiple advisors and clients
- MySQL for persistence
- tenant_id for advisor isolation
- Soft delete for audit trail

**Scaffold**:
```bash
# Use same scaffold commands as SaaS example
# MySQL works identically (ModelBase supports all major databases)
```

**Database URL**:
```bash
# .env
SQL_URL=mysql+aiomysql://user:pass@localhost/wealth_db
DISCOVER_PACKAGES=app.models
```

**Migrations**:
```bash
# Works identically with MySQL
svc-infra revision -m "add budgets" --autogenerate
svc-infra upgrade head
```

---

## Troubleshooting

### Common Scaffold Errors

#### Error: "Template not found"

**Cause**: Template package path incorrect in scaffold function.

**Solution**: Check template package name matches directory structure:
```python
# Correct:
render_template("fin_infra.budgets.scaffold_templates", "models.py.tmpl", subs)

# Incorrect:
render_template("fin_infra.budgets.templates", "models.py.tmpl", subs)
```

#### Error: "Failed to render template"

**Cause**: Missing variable in substitutions dict.

**Solution**: Ensure all template variables are defined:
```python
subs = {
    "Entity": "Budget",
    "entity": "budget",
    "table_name": "budgets",
    "tenant_field": "",  # Required even if empty
    "soft_delete_field": "",  # Required even if empty
    # ... all other variables
}
```

#### Error: "File already exists"

**Cause**: Scaffold won't overwrite by default.

**Solution**: Use `--overwrite` flag:
```bash
fin-infra scaffold budgets --dest-dir app/models/budgets --overwrite
```

### Migration Conflicts

#### Error: "Table already exists"

**Cause**: Migration created table, but running again.

**Solution**: Check migration history:
```bash
svc-infra current  # Show current version
svc-infra history  # Show all migrations

# If needed, mark migration as applied without running:
svc-infra stamp head
```

#### Error: "Multiple heads"

**Cause**: Conflicting migrations from different branches.

**Solution**: Merge migrations:
```bash
# Create merge migration
svc-infra merge heads -m "merge migrations"

# Apply merge
svc-infra upgrade head
```

### Type Checking Issues

#### Error: "Incompatible types in assignment"

**Cause**: mypy strictness with SQLAlchemy 2.0 Mapped types.

**Solution**: Use correct type hints:
```python
# Correct:
from sqlalchemy.orm import Mapped, mapped_column

class Budget(ModelBase):
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    optional_field: Mapped[str | None] = mapped_column(String(255), nullable=True)

# Incorrect (old SQLAlchemy 1.x style):
id = Column(String(255), primary_key=True)
```

#### Error: "Need type annotation"

**Cause**: Empty list without type hint.

**Solution**: Add type annotation:
```python
# Correct:
transactions: list[Transaction] = []

# Incorrect:
transactions = []  # mypy error: Need type annotation
```

### Performance Optimization

#### Slow Queries

**Problem**: List endpoint returns thousands of rows slowly.

**Solution**: Add pagination (automatic with `add_sql_resources`):
```python
# Client request:
GET /budgets?page=1&page_size=20

# Or use custom limits in repository:
async def list(self, user_id: str, limit: int = 100, offset: int = 0):
    stmt = (
        select(Budget)
        .where(Budget.user_id == user_id)
        .limit(limit)
        .offset(offset)
    )
```

#### Missing Indexes

**Problem**: Slow queries on foreign keys or search fields.

**Solution**: Add indexes in model:
```python
class Budget(ModelBase):
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Index
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Index
    
    __table_args__ = (
        Index("ix_budget_user_tenant", "user_id", "tenant_id"),  # Composite index
    )
```

#### N+1 Query Problem

**Problem**: Loading related data in loop.

**Solution**: Use eager loading:
```python
from sqlalchemy.orm import selectinload

async def list_with_details(self, user_id: str):
    stmt = (
        select(Budget)
        .where(Budget.user_id == user_id)
        .options(selectinload(Budget.transactions))  # Eager load
    )
```

---

## Summary

**fin-infra's persistence philosophy**:
1. **Stateless library** - Your app owns the database
2. **Scaffold CLI** - Generate production-ready models in seconds
3. **svc-infra integration** - Wire CRUD with ONE function call
4. **Flexible patterns** - Multi-tenancy, soft delete, custom logic
5. **Testing friendly** - In-memory, SQLite, PostgreSQL test strategies

**Getting started**:
```bash
# 1. Scaffold models
fin-infra scaffold budgets --dest-dir app/models/budgets --include-tenant

# 2. Run migrations
svc-infra revision -m "add budgets" --autogenerate
svc-infra upgrade head

# 3. Wire CRUD (one function call)
add_sql_resources(app, [SqlResource(model=Budget, prefix="/budgets")])

# Done! Full CRUD API ready 🚀
```

For more details, see:
- [svc-infra SQL README](https://github.com/your-org/svc-infra/blob/main/src/svc_infra/api/fastapi/db/sql/README.md)
- [Persistence Strategy (ADR)](./presistence-strategy.md)
- [Core vs Scaffold](./core-vs-scaffold.md)
