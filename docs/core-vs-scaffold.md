# Core Functions vs Scaffold: What fin-infra Provides vs What Apps Own

This guide clarifies the **separation of concerns** between fin-infra (the library) and your application. Understanding this distinction is critical for using fin-infra effectively.

## TL;DR

- **fin-infra provides**: Financial calculations, provider integrations, scaffold templates
- **Your app owns**: Database schema, persistence layer, API routes, business rules
- **Use core functions**: For financial logic decoupled from storage
- **Use scaffold**: To generate SQL persistence code (models/schemas/repositories)

---

## Table of Contents

- [fin-infra's Scope: What We Provide](#fin-infras-scope-what-we-provide)
- [Application Scope: What Apps Own](#application-scope-what-apps-own)
- [When to Use Core Functions vs Scaffold](#when-to-use-core-functions-vs-scaffold)
- [Examples: Core Functions Decoupled from Storage](#examples-core-functions-decoupled-from-storage)
- [Migration Guide: From TODO Comments to Core Functions](#migration-guide-from-todo-comments-to-core-functions)
- [Architecture Decision: Why This Separation?](#architecture-decision-why-this-separation)

---

## fin-infra's Scope: What We Provide

fin-infra is a **library** (like stripe-python or plaid-python), not a framework. We provide the financial intelligence layer, but **we don't manage your database or application logic**.

### 1. Provider Integrations

**What we provide**:
- Banking connections (Plaid, Teller, MX)
- Brokerage integrations (Alpaca, Interactive Brokers, SnapTrade)
- Market data (Alpha Vantage, CoinGecko, Yahoo Finance, Polygon)
- Credit scores (Experian, Equifax, TransUnion)
- Tax data (IRS, TaxBit, document parsers)

**Example**:
```python
from fin_infra.banking import easy_banking

banking = easy_banking(provider="plaid")
accounts = await banking.get_accounts("access_token")
transactions = await banking.get_transactions("account_id")
```

**What you own**: How you store accounts/transactions (SQL, Mongo, Redis, etc.)

### 2. Financial Calculations

**What we provide**:
- Time value of money: NPV, IRR, XNPV, XIRR, PMT, FV, PV
- Investment calculations: CAGR, Sharpe ratio, compound interest
- Tax calculations: FIFO/LIFO capital gains, crypto tax reports
- Loan calculations: Amortization schedules, APR

**Example**:
```python
from fin_infra.cashflows import npv, irr

cashflows = [-10000, 3000, 4000, 5000]
net_value = npv(0.08, cashflows)
rate = irr(cashflows)
```

**What you own**: Input data sources (where cashflows come from)

### 3. Budget Logic (Core Functions)

**What we provide** (`fin_infra.budgets.core`):
- `detect_overspending(budgeted: dict, actual: dict) -> dict`
- `calculate_rollover(previous_budget: dict, current_budget: dict) -> dict`
- `compare_periods(current: dict, previous: dict) -> dict`
- `compute_utilization_rate(spent: float, budgeted: float) -> float`

**Example**:
```python
from fin_infra.budgets.core import detect_overspending

overspending = detect_overspending(
    budgeted={"Groceries": 600.00, "Restaurants": 200.00},
    actual={"Groceries": 550.00, "Restaurants": 250.00},
)
# Returns: {"Restaurants": 50.00}  # Over by $50
```

**What you own**: Budget storage (SQL, Mongo, etc.), how you aggregate transactions

### 4. Goal Logic (Core Functions)

**What we provide** (`fin_infra.goals.core`):
- `check_goal_feasibility(target: float, target_date: date, current: float, income: float, expenses: float) -> dict`
- `calculate_required_monthly(target: float, target_date: date, current: float) -> float`
- `project_completion_date(target: float, current: float, monthly_contribution: float) -> date`
- `compute_progress_percentage(current: float, target: float) -> float`

**Example**:
```python
from fin_infra.goals.core import check_goal_feasibility

feasibility = check_goal_feasibility(
    target_amount=50000.00,
    target_date=date(2027, 12, 31),
    current_saved=10000.00,
    monthly_income=6000.00,
    monthly_expenses=4500.00,
)
# Returns: {
#   "feasible": True,
#   "required_monthly": 1333.33,
#   "available_monthly": 1500.00,
#   "months_to_goal": 30
# }
```

**What you own**: Goal storage, how you calculate monthly income/expenses

### 5. Net Worth Logic (Core Functions)

**What we provide** (`fin_infra.net_worth.core`):
- `aggregate_accounts(accounts: list) -> dict`
- `calculate_growth(snapshots: list) -> dict`
- `compute_liquid_net_worth(accounts: list) -> float`
- `calculate_debt_to_income(liabilities: float, income: float) -> float`

**Example**:
```python
from fin_infra.net_worth.core import aggregate_accounts, calculate_growth

# Aggregate accounts into net worth
net_worth = aggregate_accounts([
    {"type": "checking", "balance": 5000.00},
    {"type": "investment", "balance": 50000.00},
    {"type": "credit_card", "balance": -2000.00},
])
# Returns: {"assets": 55000.00, "liabilities": 2000.00, "net_worth": 53000.00}

# Calculate growth over time
growth = calculate_growth([
    {"date": "2025-01-01", "net_worth": 50000.00},
    {"date": "2025-11-01", "net_worth": 53000.00},
])
# Returns: {"absolute": 3000.00, "percentage": 6.0, "annualized": 7.2}
```

**What you own**: Account storage, snapshot storage, when to create snapshots

### 6. Transaction Categorization

**What we provide**:
- Rule-based categorization (merchant name → category)
- ML model inference (LLM-based with financial context)
- Category normalization (vendor-specific → standard categories)

**Example**:
```python
from fin_infra.categorization import easy_categorization

categorizer = easy_categorization()
category = await categorizer.categorize_transaction(
    merchant_name="Whole Foods Market",
    amount=125.50,
    description="WHOLEFDS #12345",
)
# Returns: "Groceries"
```

**What you own**: Transaction storage, how you apply categories (batch vs real-time)

### 7. Recurring Detection

**What we provide**:
- Pattern matching (same merchant, similar amount, regular interval)
- Subscription identification (Netflix, Spotify, etc.)
- Bill detection (utilities, rent, mortgage)

**Example**:
```python
from fin_infra.recurring import easy_recurring

recurring = easy_recurring()
subscriptions = await recurring.detect_recurring(transactions=[
    {"date": "2025-01-15", "merchant": "Netflix", "amount": 15.99},
    {"date": "2025-02-15", "merchant": "Netflix", "amount": 15.99},
    {"date": "2025-03-15", "merchant": "Netflix", "amount": 15.99},
])
# Returns: [{"merchant": "Netflix", "amount": 15.99, "frequency": "monthly", "confidence": 0.95}]
```

**What you own**: Transaction storage, how you notify users about subscriptions

### 8. Scaffold CLI

**What we provide**:
- Template-based code generation
- SQLAlchemy models with svc-infra's ModelBase
- Pydantic schemas (Create, Read, Update)
- Repository pattern with full CRUD
- Multi-tenancy and soft delete support

**Example**:
```bash
fin-infra scaffold budgets --dest-dir app/models/budgets --include-tenant
```

**What you own**: Customization of generated code, migrations, API routes

---

## Application Scope: What Apps Own

Your application is responsible for **all persistence, business logic, and presentation**.

### 1. Database Schema

**Your responsibility**:
- Choose database (PostgreSQL, MySQL, SQLite, MongoDB, etc.)
- Design schema (tables, indexes, constraints)
- Manage migrations (Alembic, Prisma, etc.)

**How fin-infra helps**: Scaffold CLI generates starting models that you customize.

**Example** (after scaffolding):
```python
# app/models/budgets/budget.py (your code, customized)
from svc_infra.db.sql.models import ModelBase

class Budget(ModelBase):
    __tablename__ = "budgets"
    
    # Scaffold-generated fields
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # ... other scaffold fields
    
    # YOUR CUSTOM FIELDS
    approval_status: Mapped[str] = mapped_column(String(50), default="pending")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_code: Mapped[str] = mapped_column(String(10), index=True)
```

### 2. Persistence Layer

**Your responsibility**:
- Repository implementations (CRUD operations)
- Query optimization (indexes, joins, caching)
- Transaction management (rollback, commit)

**How fin-infra helps**: Scaffold generates repository, or use svc-infra's `add_sql_resources()`.

**Example** (using scaffold-generated repository):
```python
# app/repositories/budget_repository.py (your code)
from app.models.budgets import BudgetRepository

repo = BudgetRepository(session)
budgets = await repo.list(user_id="user123")
```

**Example** (using svc-infra SqlResource):
```python
# app/main.py (your code)
from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource
from app.models.budgets import Budget

add_sql_resources(app, [
    SqlResource(model=Budget, prefix="/budgets", search_fields=["name"])
])
```

### 3. API Routes

**Your responsibility**:
- Endpoint design (REST, GraphQL, gRPC)
- Request/response validation
- Authentication/authorization
- Rate limiting

**How fin-infra helps**: svc-infra's `add_sql_resources()` generates CRUD routes automatically.

**Example** (custom route):
```python
# app/routers/budgets.py (your code)
from fastapi import APIRouter, Depends
from fin_infra.budgets.core import detect_overspending

router = APIRouter()

@router.get("/budgets/{budget_id}/overspending")
async def check_overspending(budget_id: str, repo=Depends(get_repo)):
    budget = await repo.get(budget_id)
    transactions = await get_transactions(budget.user_id, budget.period_start, budget.period_end)
    
    # fin-infra provides calculation logic
    overspending = detect_overspending(
        budgeted=budget.categories,
        actual=sum_by_category(transactions),
    )
    return {"overspending": overspending}
```

### 4. Business Rules

**Your responsibility**:
- Validation logic (budget limits, goal constraints)
- Workflows (approval processes, notifications)
- Authorization (who can see what)
- Audit trails

**Example**:
```python
# app/services/budget_service.py (your code)
from fin_infra.budgets.core import detect_overspending

class BudgetService:
    async def create_budget_with_approval(self, budget_data: dict):
        # YOUR BUSINESS LOGIC
        if budget_data["total_amount"] > 10000:
            budget_data["approval_status"] = "pending"
            await notify_manager(budget_data)
        else:
            budget_data["approval_status"] = "approved"
        
        # Use scaffold-generated repository
        budget = await self.repo.create(budget_data)
        
        # Use fin-infra core function for validation
        overspending = detect_overspending(
            budgeted=budget.categories,
            actual=self.get_historical_spending(budget.user_id),
        )
        
        if overspending:
            await send_warning_email(budget.user_id, overspending)
        
        return budget
```

### 5. UI Components

**Your responsibility**:
- Frontend framework (React, Vue, Svelte, etc.)
- UI/UX design
- State management
- Client-side validation

**How fin-infra helps**: fin-web provides example components (not a UI library).

---

## When to Use Core Functions vs Scaffold

### Use Core Functions When:

✅ **Need financial calculations**: Any time you need financial logic
```python
from fin_infra.budgets.core import detect_overspending
from fin_infra.goals.core import check_goal_feasibility
from fin_infra.cashflows import npv, irr
```

✅ **Need projections**: Forecasting, feasibility checks, growth calculations
```python
from fin_infra.goals.core import project_completion_date

completion = project_completion_date(
    target_amount=50000,
    current_saved=10000,
    monthly_contribution=1000,
)
```

✅ **Need provider integrations**: Banking, brokerage, market data
```python
from fin_infra.banking import easy_banking

banking = easy_banking(provider="plaid")
accounts = await banking.get_accounts("access_token")
```

✅ **Storage is app-specific**: In-memory, Redis, MongoDB, SQL, etc.
```python
# You fetch from YOUR database (any database)
budget = await my_mongo_db.budgets.find_one({"user_id": "user123"})

# fin-infra provides calculation
overspending = detect_overspending(budget["categories"], actual_spending)
```

### Use Scaffold When:

✅ **Need SQL persistence layer**: For budgets/goals/net-worth
```bash
fin-infra scaffold budgets --dest-dir app/models/budgets
```

✅ **Want reference implementation**: Learn best practices
```bash
# Generated code follows svc-infra conventions
# - ModelBase for Alembic discovery
# - Async repositories with type hints
# - Pydantic schemas for validation
```

✅ **Building typical CRUD app**: FastAPI + SQLAlchemy + PostgreSQL
```python
# Scaffold → migrate → ONE-LINER CRUD
add_sql_resources(app, [SqlResource(model=Budget, prefix="/budgets")])
```

✅ **Need multi-tenancy or soft delete**: Scaffold handles these patterns
```bash
fin-infra scaffold budgets --include-tenant --include-soft-delete
```

### Decision Tree

```
Do you need to store budgets/goals/net-worth in SQL?
├─ YES → Use scaffold to generate models/schemas/repositories
│         Then use core functions for calculations
│
└─ NO → Use core functions directly
        Store data however you want (Mongo, Redis, in-memory, etc.)
```

---

## Examples: Core Functions Decoupled from Storage

### Example 1: Budget Overspending Detection (Pure Function)

```python
from fin_infra.budgets.core import detect_overspending

# YOUR APP fetches from ITS OWN database (SQL, Mongo, Redis, whatever)
budget = my_app_db.get_budget(user_id="user123", month="2025-11")
transactions = my_app_db.get_transactions(user_id="user123", month="2025-11")

# YOUR APP aggregates transactions by category (your business logic)
actual_spending = sum_by_category(transactions)
# Example result: {"Groceries": 550.00, "Restaurants": 250.00, "Gas": 100.00}

# fin-infra provides calculation logic (pure function, no database access)
overspending = detect_overspending(
    budgeted=budget["categories"],  # {"Groceries": 600, "Restaurants": 200, "Gas": 150}
    actual=actual_spending,
)
# Returns: {"Restaurants": 50.00, "Gas": -50.00}  # Over by $50 on Restaurants, under by $50 on Gas

# YOUR APP decides what to do with the result
if overspending:
    await send_email_notification(user_id="user123", overspending=overspending)
    await log_audit_trail(user_id="user123", event="budget_overspending", data=overspending)
```

**Key point**: `detect_overspending()` is a **pure function** - no database access, no side effects. Your app controls data sources and actions.

### Example 2: Goal Feasibility Check (Pure Function)

```python
from fin_infra.goals.core import check_goal_feasibility
from datetime import date

# YOUR APP fetches goal from wherever you store it
goal = my_app_db.get_goal(goal_id="goal123")
# Example: {"target_amount": 50000, "target_date": "2027-12-31", "current_amount": 10000}

# YOUR APP calculates monthly cashflow (from your analytics service)
cashflow = my_app_analytics.get_avg_monthly_cashflow(user_id="user123")
# Example: {"income": 6000, "expenses": 4500}

# fin-infra provides financial logic (pure function)
feasibility = check_goal_feasibility(
    target_amount=goal["target_amount"],
    target_date=date.fromisoformat(goal["target_date"]),
    current_saved=goal["current_amount"],
    monthly_income=cashflow["income"],
    monthly_expenses=cashflow["expenses"],
)
# Returns: {
#   "feasible": True,
#   "required_monthly": 1333.33,
#   "available_monthly": 1500.00,
#   "months_to_goal": 30,
#   "surplus": 166.67
# }

# YOUR APP uses the result for UI or notifications
if not feasibility["feasible"]:
    await show_warning_message(goal_id="goal123", message="Goal not feasible with current income")
else:
    await update_goal_status(goal_id="goal123", status="on_track")
```

**Key point**: fin-infra does the math, your app does the storage and decision-making.

### Example 3: Net Worth Calculation (Pure Function)

```python
from fin_infra.net_worth.core import aggregate_accounts, calculate_growth

# YOUR APP fetches account balances from ITS OWN sources
accounts = my_app_db.get_all_accounts(user_id="user123")
# Example: [
#   {"type": "checking", "balance": 5000.00, "institution": "Chase"},
#   {"type": "investment", "balance": 50000.00, "institution": "Vanguard"},
#   {"type": "credit_card", "balance": -2000.00, "institution": "Amex"},
# ]

# fin-infra provides aggregation logic (pure function)
current_net_worth = aggregate_accounts(accounts)
# Returns: {"assets": 55000.00, "liabilities": 2000.00, "net_worth": 53000.00}

# YOUR APP saves the snapshot (if you want historical tracking)
snapshot = {
    "user_id": "user123",
    "date": date.today(),
    "net_worth": current_net_worth["net_worth"],
    "assets": current_net_worth["assets"],
    "liabilities": current_net_worth["liabilities"],
}
await my_app_db.save_net_worth_snapshot(snapshot)

# YOUR APP fetches historical snapshots
snapshots = my_app_db.get_net_worth_snapshots(user_id="user123", limit=12)

# fin-infra provides growth calculation (pure function)
growth = calculate_growth(snapshots)
# Returns: {"absolute": 3000.00, "percentage": 6.0, "annualized": 7.2}
```

**Key point**: fin-infra aggregates and calculates, but has no opinion on where data comes from or how it's stored.

### Example 4: Portfolio Performance with Custom Data Source

```python
from fin_infra.cashflows import xirr
from datetime import date

# YOUR APP fetches investment data from YOUR custom source (could be anything)
# Maybe you store in PostgreSQL, or query from a trading API, or load from CSV
investments = my_custom_data_source.get_user_investments(user_id="user123")

# YOUR APP formats data for fin-infra function
cashflows = [
    (date(2024, 1, 1), -10000),   # Initial investment
    (date(2024, 6, 1), -5000),    # Additional contribution
    (date(2025, 1, 1), -5000),    # Additional contribution
    (date(2025, 11, 8), 25000),   # Current value
]

# fin-infra provides XIRR calculation (pure function)
rate_of_return = xirr([cf[1] for cf in cashflows], [cf[0] for cf in cashflows])
# Returns: 0.234 (23.4% annualized return)

# YOUR APP stores the result wherever you want
await my_app_db.save_portfolio_metric(
    user_id="user123",
    metric="xirr",
    value=rate_of_return,
    as_of=date.today(),
)
```

**Key point**: fin-infra provides financial calculations, you control data sources and storage.

---

## Migration Guide: From TODO Comments to Core Functions

The TODO comments you saw in fin-infra code (before Task 11) were **intentional placeholders** showing where applications take over.

### Before (What TODO Comments Pointed To)

```python
# From fin_infra/budgets/tracker.py (in-memory example for testing)
class BudgetTracker:
    def __init__(self):
        self.budgets: list[Budget] = []  # TODO: Store budgets in SQL database
    
    async def create_budget(self, **kwargs) -> Budget:
        # TODO: Applications own database schema and persistence layer.
        # See docs/persistence.md for how to scaffold models/schemas/repositories.
        budget = Budget(id=str(uuid4()), **kwargs)
        self.budgets.append(budget)  # In-memory storage (testing only)
        return budget
```

### After (Using Scaffold + Core Functions)

#### Step 1: Scaffold the Models

```bash
# Generate production-ready SQL models
fin-infra scaffold budgets --dest-dir app/models/budgets --include-tenant
```

#### Step 2: Customize for Your Needs

```python
# app/models/budgets/budget.py (YOUR CODE, generated then customized)
from svc_infra.db.sql.models import ModelBase

class Budget(ModelBase):
    __tablename__ = "budgets"
    
    # Scaffold-generated (keep as-is or modify)
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    categories: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # YOUR CUSTOM FIELDS
    approval_workflow: Mapped[str] = mapped_column(String(50), default="auto_approve")
    company_policy_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

#### Step 3: Use Core Functions for Financial Logic

```python
# app/services/budget_service.py (YOUR CODE)
from fin_infra.budgets.core import detect_overspending, calculate_rollover
from app.models.budgets import BudgetRepository

class BudgetService:
    def __init__(self, session: AsyncSession):
        self.repo = BudgetRepository(session)
    
    async def check_budget_status(self, budget_id: str) -> dict:
        # YOUR APP: Fetch from YOUR database
        budget = await self.repo.get(budget_id)
        transactions = await self.get_transactions(budget.user_id, budget.period_start, budget.period_end)
        
        # fin-infra: Provide financial calculations
        overspending = detect_overspending(
            budgeted=budget.categories,
            actual=self.sum_by_category(transactions),
        )
        
        # YOUR APP: Business logic and notifications
        if overspending:
            await self.send_alert(budget.user_id, overspending)
        
        return {"budget": budget, "overspending": overspending}
```

#### Step 4: Wire CRUD with svc-infra

```python
# app/main.py (YOUR CODE)
from fastapi import FastAPI
from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource
from app.models.budgets import Budget

app = FastAPI()

# ONE-LINER: Full CRUD API
add_sql_resources(app, [
    SqlResource(
        model=Budget,
        prefix="/budgets",
        tenant_field="tenant_id",
        search_fields=["name"],
        soft_delete=False,
    )
])

# CUSTOM ENDPOINT: Using core functions
from app.services.budget_service import BudgetService

@app.get("/budgets/{budget_id}/status")
async def budget_status(budget_id: str, service: BudgetService = Depends()):
    return await service.check_budget_status(budget_id)
```

### Key Differences

| Aspect | Before (TODO) | After (Scaffold + Core) |
|--------|---------------|-------------------------|
| **Storage** | In-memory list | SQL database (YOUR choice) |
| **Models** | None (dict) | SQLAlchemy models (scaffold-generated) |
| **Calculations** | ❌ Missing | ✅ Core functions (`detect_overspending()`) |
| **CRUD** | Manual list operations | Repository or `add_sql_resources()` |
| **Production-ready** | ❌ No | ✅ Yes |

---

## Architecture Decision: Why This Separation?

### Problem: Framework Lock-In

**Bad approach** (what we DON'T do):
```python
# Hypothetical: If fin-infra was a framework (we're NOT doing this)
from fin_infra.orm import FinInfraModel, FinInfraORM

class Budget(FinInfraModel):  # ❌ Tied to fin-infra ORM
    name = FinInfraField(String)
    categories = FinInfraField(JSON)

db = FinInfraORM(url="postgresql://...")  # ❌ Tied to fin-infra database layer
```

**Problems**:
- Can't upgrade fin-infra without database migration risks
- Can't use your own ORM (Prisma, Django ORM, raw SQL)
- Can't use your own database (forced to use what fin-infra supports)
- Can't customize persistence (forced to follow fin-infra patterns)

### Solution: Library with Pure Functions

**Good approach** (what we DO):
```python
# fin-infra provides PURE FUNCTIONS (no database access)
from fin_infra.budgets.core import detect_overspending

# YOUR APP provides data (from any source)
budget = your_app_db.get_budget(budget_id)
transactions = your_app_db.get_transactions(user_id, date_range)

# fin-infra does the math, you control the data
overspending = detect_overspending(budget["categories"], sum_by_category(transactions))
```

**Benefits**:
- ✅ Upgrade fin-infra independently (no database coupling)
- ✅ Use any ORM (SQLAlchemy, Prisma, Mongo, raw SQL)
- ✅ Use any database (PostgreSQL, MySQL, SQLite, MongoDB, Redis)
- ✅ Customize persistence (your schema, your migrations, your patterns)
- ✅ Test easily (mock data, no database required)

### Scaffold: Best of Both Worlds

**Challenge**: Pure functions are flexible but give no guidance on persistence.

**Solution**: Scaffold CLI generates **starting code** that you own and customize.

```bash
# Generate reference implementation
fin-infra scaffold budgets --dest-dir app/models/budgets

# YOU customize the code (add fields, change logic, etc.)
# YOU run migrations (svc-infra Alembic)
# YOU own the database schema
```

**Benefits**:
- ✅ Quick start (don't write boilerplate)
- ✅ Best practices (follow svc-infra conventions)
- ✅ Flexibility (customize generated code)
- ✅ No lock-in (it's YOUR code after generation)

### Comparison: Libraries vs Frameworks

| Feature | fin-infra (Library) | Django (Framework) | Rails (Framework) |
|---------|---------------------|-------------------|------------------|
| **Database Management** | ❌ No | ✅ Yes (Django ORM) | ✅ Yes (ActiveRecord) |
| **Migrations** | ❌ No (use svc-infra) | ✅ Yes (built-in) | ✅ Yes (built-in) |
| **Schema Ownership** | ✅ Your app | ❌ Framework | ❌ Framework |
| **ORM Choice** | ✅ Any | ❌ Django ORM only | ❌ ActiveRecord only |
| **Financial Calculations** | ✅ Yes | ❌ No | ❌ No |
| **Provider Integrations** | ✅ Yes | ❌ No | ❌ No |
| **Scaffold** | ✅ Yes (optional) | ✅ Yes (required) | ✅ Yes (required) |
| **Lock-in Risk** | ✅ Low | ❌ High | ❌ High |

---

## Summary

### fin-infra Provides

1. **Financial calculations** (NPV, IRR, overspending, feasibility checks)
2. **Provider integrations** (Plaid, Alpaca, market data APIs)
3. **Core functions** (pure functions decoupled from storage)
4. **Scaffold CLI** (generate starting code for SQL persistence)

### Your App Owns

1. **Database schema** (tables, indexes, constraints)
2. **Persistence layer** (CRUD operations, queries, transactions)
3. **API routes** (REST endpoints, GraphQL, etc.)
4. **Business rules** (validation, workflows, notifications)
5. **UI components** (React, Vue, etc.)

### When to Use What

- **Use core functions**: For ALL financial calculations and provider integrations
- **Use scaffold**: When you need SQL persistence for budgets/goals/net-worth
- **Combine both**: Scaffold generates storage layer, core functions handle calculations

### The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR APPLICATION                          │
│                                                               │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  UI (React)   │  │  API Routes  │  │  Business Logic │  │
│  └───────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
│          │                  │                    │            │
│          └──────────────────┴────────────────────┘            │
│                             │                                 │
│                   ┌─────────▼──────────┐                      │
│                   │ Persistence Layer  │                      │
│                   │  (YOUR SCHEMA)     │                      │
│                   └─────────┬──────────┘                      │
│                             │                                 │
│               ┌─────────────┴───────────────┐                 │
│               │                             │                 │
│        ┌──────▼─────┐              ┌───────▼────────┐        │
│        │ PostgreSQL │              │ fin-infra core │        │
│        │ (your DB)  │              │   functions    │        │
│        └────────────┘              └────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

**Key insight**: fin-infra core functions are **pure** - they do math, not storage. Your app controls all data sources and persistence.

---

**Next Steps**:
- See [Persistence Guide](./persistence.md) for scaffold workflow
- See domain-specific docs for core functions: [Budgets](./budgets.md), [Goals](./goals.md), [Net Worth](./net-worth.md)
