# Budget Management

> **Multi-type budget tracking with templates, alerts, and progress monitoring**

## Overview

Budget management helps users control spending by setting category limits, tracking progress, and receiving alerts when approaching limits. Supports multiple budget types for different use cases:

```
Budget Types: Personal | Household | Business | Project | Custom
Budget Periods: Weekly | Biweekly | Monthly | Quarterly | Yearly
```

### Key Features

- **Multi-Type Budgets**: Personal, household, business, project, and custom budget classifications
- **Flexible Periods**: Weekly, biweekly, monthly, quarterly, and yearly tracking periods
- **Category-Based**: Set spending limits per category (groceries, dining, transportation, etc.)
- **Pre-Built Templates**: 50/30/20 Rule, Zero-Based, Envelope System, Pay Yourself First, Business Essentials
- **Progress Tracking**: Real-time spent vs. budgeted amounts with percentage calculations
- **Smart Alerts**: Warn at 80%, alert at 100%, notify on 110% overspending
- **Rollover Support**: Unused budget carries over to next period (optional)
- **REST API**: 8 endpoints for full CRUD operations and template management
- **Generic Design**: Works for ANY fintech application (personal finance, wealth management, business tools)

### Use Cases

- **Personal Finance Apps**: Mint, YNAB, PocketGuard (budget tracking and spending limits)
- **Household Management**: Shared family budgets with category allocations
- **Business Expense Tracking**: Department budgets, project spending limits
- **Wealth Management**: Client budget planning and expense analysis
- **Banking Apps**: Built-in budgeting tools for account holders

---

## Quick Start

### 1. Basic Setup (Programmatic)

```python
from fin_infra.budgets import easy_budgets, BudgetType, BudgetPeriod
from datetime import datetime

# Create tracker with database
tracker = easy_budgets(db_url="postgresql+asyncpg://localhost/mydb")

# Create a personal monthly budget
budget = await tracker.create_budget(
    user_id="user_123",
    name="November 2025",
    type=BudgetType.PERSONAL,
    period=BudgetPeriod.MONTHLY,
    categories={
        "Groceries": 600.00,
        "Restaurants": 200.00,
        "Transportation": 150.00,
        "Entertainment": 100.00,
    },
    start_date=datetime(2025, 11, 1),
    rollover_enabled=True,  # Unused budget carries over
)

print(f"Budget Created: {budget.name}")
print(f"Total Budgeted: ${sum(budget.categories.values()):,.2f}")
```

### 2. Using Templates

```python
from fin_infra.budgets import apply_template

# Create budget from 50/30/20 template
budget = await apply_template(
    user_id="user_123",
    template_name="50_30_20",
    total_income=5000.00,  # Monthly income
    tracker=tracker,
    budget_name="November 2025 - 50/30/20",
    start_date=datetime(2025, 11, 1),
)

# Template automatically allocates:
# - 50% ($2,500) to Needs (Housing, Groceries, Utilities, Transportation, Insurance)
# - 30% ($1,500) to Wants (Restaurants, Entertainment, Shopping, Hobbies)
# - 20% ($1,000) to Savings (Emergency Fund, Investments, Debt Paydown)

print(f"Budget: {budget.name}")
for category, amount in budget.categories.items():
    print(f"  {category}: ${amount:,.2f}")
```

### 3. FastAPI Integration

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from fin_infra.budgets import add_budgets, easy_budgets

# Create app (svc-infra)
app = easy_service_app(name="FinanceAPI")

# Add budget management
tracker = add_budgets(
    app,
    db_url="postgresql+asyncpg://localhost/mydb",
    prefix="/budgets",  # Default prefix
)

# Endpoints available:
# POST   /budgets                    - Create budget
# GET    /budgets                    - List budgets (filter by user_id, type)
# GET    /budgets/{budget_id}        - Get single budget
# PATCH  /budgets/{budget_id}        - Update budget (partial)
# DELETE /budgets/{budget_id}        - Delete budget (204 No Content)
# GET    /budgets/{budget_id}/progress - Get spending progress
# GET    /budgets/templates/list     - List available templates
# POST   /budgets/from-template      - Create from template
```

### 4. API Usage (cURL Examples)

```bash
# Create budget
curl -X POST "http://localhost:8000/budgets" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "name": "November 2025",
    "type": "personal",
    "period": "monthly",
    "categories": {
      "Groceries": 600.00,
      "Restaurants": 200.00
    },
    "start_date": "2025-11-01T00:00:00",
    "rollover_enabled": true
  }'

# List budgets for user
curl -X GET "http://localhost:8000/budgets?user_id=user_123"

# Get budget progress
curl -X GET "http://localhost:8000/budgets/bud_123/progress"

# List available templates
curl -X GET "http://localhost:8000/budgets/templates/list"

# Create from template
curl -X POST "http://localhost:8000/budgets/from-template" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "template_name": "50_30_20",
    "total_income": 5000.00,
    "budget_name": "November 2025"
  }'
```

---

## Core Concepts

### Budget Types

Budget types classify the purpose and scope of spending limits:

| Type | Description | Use Cases |
|------|-------------|-----------|
| **Personal** | Individual spending limits | Personal finance apps, student budgets |
| **Household** | Shared family/roommate budgets | Family expense tracking, shared living costs |
| **Business** | Company/department budgets | Small business accounting, startup expenses |
| **Project** | Project-specific spending limits | Freelancer project budgets, event planning |
| **Custom** | User-defined budget classification | Any custom use case |

**Example**: Personal budget for groceries vs. Business budget for office supplies.

### Budget Periods

Budget periods define the tracking timeframe:

| Period | Duration | Reset Frequency | Use Cases |
|--------|----------|-----------------|-----------|
| **Weekly** | 7 days | Every Monday | Weekly allowances, short-term goals |
| **Biweekly** | 14 days | Every other Monday | Biweekly paycheck budgets |
| **Monthly** | 1 month | 1st of month | Most common period, aligns with bills |
| **Quarterly** | 3 months | Start of quarter | Business quarterly budgets |
| **Yearly** | 12 months | Start of year | Annual budgets, long-term planning |

**Period Calculation**:
```python
# Monthly budget: November 1-30 (30 days)
start_date = datetime(2025, 11, 1)
end_date = datetime(2025, 11, 30, 23, 59, 59)

# Weekly budget: Monday-Sunday
start_date = datetime(2025, 11, 3)  # Monday
end_date = datetime(2025, 11, 9, 23, 59, 59)  # Sunday
```

### Categories

Categories organize spending into logical groups. Common categories:

**Needs (Essential)**:
- Housing (rent, mortgage, HOA fees)
- Groceries (food, household supplies)
- Utilities (electricity, water, gas, internet)
- Transportation (gas, car payment, public transit)
- Insurance (health, auto, home, life)
- Healthcare (doctor visits, prescriptions, copays)

**Wants (Discretionary)**:
- Restaurants (dining out, takeout, coffee)
- Entertainment (movies, concerts, streaming services)
- Shopping (clothes, gadgets, home decor)
- Hobbies (sports, crafts, gaming)
- Travel (vacations, weekend trips)

**Savings & Debt**:
- Emergency Fund (3-6 months expenses)
- Investments (401k, IRA, brokerage)
- Debt Paydown (credit cards, loans)

**Custom Categories**: Users can define any category names.

### Rollover

Rollover allows unused budget to carry over to the next period:

**Example**:
```
November Budget: $600 (Groceries)
November Spent: $450
Unused: $150

With Rollover Enabled:
December Budget: $600 + $150 = $750

With Rollover Disabled:
December Budget: $600 (resets)
```

**Use Cases**:
- Saving up for large purchases (vacation, furniture)
- Reward frugal spending
- Envelope budgeting systems

---

## Budget Templates

### 50/30/20 Rule

The **50/30/20 Rule** allocates income across needs, wants, and savings:

- **50% Needs**: Essential expenses (housing, groceries, utilities, transportation, insurance)
- **30% Wants**: Discretionary spending (restaurants, entertainment, shopping, hobbies)
- **20% Savings**: Financial goals (emergency fund, investments, debt paydown)

**Example**: $5,000/month income
```python
from fin_infra.budgets import apply_template

budget = await apply_template(
    user_id="user_123",
    template_name="50_30_20",
    total_income=5000.00,
    tracker=tracker,
)

# Allocations:
# Needs (50% = $2,500):
#   Housing: $1,250, Groceries: $500, Utilities: $200,
#   Transportation: $300, Insurance: $250

# Wants (30% = $1,500):
#   Restaurants: $400, Entertainment: $300, Shopping: $400,
#   Hobbies: $200, Travel: $200

# Savings (20% = $1,000):
#   Emergency Fund: $300, Investments: $500, Debt Paydown: $200
```

### Zero-Based Budget

**Zero-Based Budgeting** allocates every dollar of income to a specific category (Income - Expenses = $0).

- **60% Fixed Expenses**: Rent, utilities, insurance, loan payments
- **20% Variable Expenses**: Groceries, gas, dining out
- **10% Savings**: Emergency fund, investments
- **10% Discretionary**: Fun money, hobbies, entertainment

**Example**: $4,500/month income
```python
budget = await apply_template(
    user_id="user_123",
    template_name="zero_based",
    total_income=4500.00,
    tracker=tracker,
)

# Allocations:
# Fixed (60% = $2,700):
#   Rent: $1,500, Utilities: $200, Insurance: $300,
#   Car Payment: $400, Phone: $100, Internet: $80, Subscriptions: $120

# Variable (20% = $900):
#   Groceries: $500, Gas: $200, Restaurants: $150, Personal Care: $50

# Savings (10% = $450):
#   Emergency Fund: $250, Retirement: $200

# Discretionary (10% = $450):
#   Entertainment: $200, Hobbies: $150, Shopping: $100
```

### Envelope System

**Envelope System** divides cash into physical or virtual envelopes for each category.

- **40% Bills**: Rent, utilities, insurance, subscriptions
- **30% Everyday Expenses**: Groceries, gas, household items
- **15% Savings**: Emergency fund, goals
- **15% Fun**: Dining, entertainment, hobbies

**Example**: $3,000/month income
```python
budget = await apply_template(
    user_id="user_123",
    template_name="envelope",
    total_income=3000.00,
    tracker=tracker,
)

# Allocations:
# Bills (40% = $1,200):
#   Rent: $800, Utilities: $150, Insurance: $150, Subscriptions: $100

# Everyday (30% = $900):
#   Groceries: $500, Gas: $200, Household: $100, Personal Care: $100

# Savings (15% = $450):
#   Emergency Fund: $300, Goals: $150

# Fun (15% = $450):
#   Restaurants: $200, Entertainment: $150, Hobbies: $100
```

### Pay Yourself First

**Pay Yourself First** prioritizes savings before expenses.

- **30% Savings**: High savings rate for financial independence
- **40% Needs**: Essential expenses
- **20% Wants**: Discretionary spending
- **10% Giving**: Charity, gifts, donations

**Example**: $6,000/month income
```python
budget = await apply_template(
    user_id="user_123",
    template_name="pay_yourself_first",
    total_income=6000.00,
    tracker=tracker,
)

# Allocations:
# Savings (30% = $1,800):
#   Emergency Fund: $600, Retirement: $800, Investments: $400

# Needs (40% = $2,400):
#   Housing: $1,200, Groceries: $500, Utilities: $250,
#   Transportation: $300, Insurance: $150

# Wants (20% = $1,200):
#   Restaurants: $400, Entertainment: $300, Shopping: $300, Travel: $200

# Giving (10% = $600):
#   Charity: $400, Gifts: $200
```

### Business Essentials

**Business Essentials** template for small business/freelancer budgets.

- **50% Operating Expenses**: Rent, utilities, supplies, software
- **20% Payroll**: Salaries, contractor payments
- **15% Marketing**: Ads, website, content creation
- **10% Savings**: Business emergency fund
- **5% Professional Services**: Legal, accounting, consulting

**Example**: $10,000/month revenue
```python
budget = await apply_template(
    user_id="user_123",
    template_name="business_essentials",
    total_income=10000.00,
    tracker=tracker,
)

# Allocations:
# Operating (50% = $5,000):
#   Rent: $2,000, Utilities: $500, Supplies: $1,000,
#   Software: $800, Insurance: $700

# Payroll (20% = $2,000):
#   Salaries: $1,500, Contractors: $500

# Marketing (15% = $1,500):
#   Ads: $800, Website: $400, Content: $300

# Savings (10% = $1,000):
#   Emergency Fund: $1,000

# Professional (5% = $500):
#   Accounting: $300, Legal: $200
```

---

## Budget Progress Tracking

### Real-Time Progress

Track spending against budget limits in real-time:

```python
from fin_infra.budgets import BudgetTracker

tracker = easy_budgets(db_url="...")

# Get budget progress
progress = await tracker.get_budget_progress(budget_id="bud_123")

print(f"Budget: {progress.current_period}")
print(f"Total: ${progress.total_spent:.2f} / ${progress.total_budgeted:.2f}")
print(f"Overall: {progress.percent_used:.1f}% used")
print(f"Days Remaining: {progress.period_days_total - progress.period_days_elapsed}")

# Category breakdown
for category in progress.categories:
    print(f"\n{category.category_name}:")
    print(f"  Budgeted: ${category.budgeted_amount:.2f}")
    print(f"  Spent: ${category.spent_amount:.2f}")
    print(f"  Remaining: ${category.remaining_amount:.2f}")
    print(f"  Progress: {category.percent_used:.1f}%")
```

### Progress Model

**BudgetProgress** structure:
```python
@dataclass
class BudgetProgress:
    budget_id: str
    current_period: str  # "November 2025"
    categories: list[BudgetCategory]
    total_budgeted: float
    total_spent: float
    total_remaining: float
    percent_used: float
    period_days_elapsed: int
    period_days_total: int

@dataclass
class BudgetCategory:
    category_name: str
    budgeted_amount: float
    spent_amount: float
    remaining_amount: float
    percent_used: float
```

### Example Progress Output

```json
{
  "budget_id": "bud_123",
  "current_period": "November 2025",
  "categories": [
    {
      "category_name": "Groceries",
      "budgeted_amount": 600.00,
      "spent_amount": 425.50,
      "remaining_amount": 174.50,
      "percent_used": 70.92
    },
    {
      "category_name": "Restaurants",
      "budgeted_amount": 200.00,
      "spent_amount": 180.25,
      "remaining_amount": 19.75,
      "percent_used": 90.13
    }
  ],
  "total_budgeted": 800.00,
  "total_spent": 605.75,
  "total_remaining": 194.25,
  "percent_used": 75.72,
  "period_days_elapsed": 15,
  "period_days_total": 30
}
```

---

## Budget Alerts

### Alert Types

Budget alerts notify users when spending approaches or exceeds limits:

| Alert Type | Threshold | Message | Action |
|------------|-----------|---------|--------|
| **Warning** | 80% | "Approaching budget limit" | Suggest reducing spending |
| **Limit Reached** | 100% | "Budget limit reached" | Stop optional spending |
| **Overspending** | 110% | "Overspending detected" | Review expenses, adjust budget |

### Alert Configuration

```python
from fin_infra.budgets import BudgetAlerts

alerts = BudgetAlerts(
    warning_threshold=0.80,  # Warn at 80%
    limit_threshold=1.00,    # Alert at 100%
    overspending_threshold=1.10,  # Critical at 110%
)

# Check if alerts triggered
budget_alerts = alerts.check_budget(
    budget_id="bud_123",
    spent_amount=540.00,
    budgeted_amount=600.00,
)

for alert in budget_alerts:
    print(f"{alert.severity}: {alert.message}")
    # Example: "WARNING: Groceries budget at 90.0%"
```

### Alert Integration

**Webhook Events**:
```python
# Budget alert webhook payload
{
  "event": "budget.alert",
  "budget_id": "bud_123",
  "user_id": "user_123",
  "category": "Groceries",
  "alert_type": "warning",
  "percent_used": 85.5,
  "spent_amount": 513.00,
  "budgeted_amount": 600.00,
  "remaining_amount": 87.00,
  "timestamp": "2025-11-15T14:30:00Z"
}
```

**Email/Push Notifications** (via svc-infra):
```python
from svc_infra.notifications import send_notification

# Send alert notification
await send_notification(
    user_id="user_123",
    channel="email",
    template="budget_warning",
    data={
        "category": "Groceries",
        "percent_used": 85.5,
        "remaining": 87.00,
    },
)
```

---

## API Reference

### POST /budgets

Create a new budget.

**Request Body**:
```json
{
  "user_id": "user_123",
  "name": "November 2025",
  "type": "personal",
  "period": "monthly",
  "categories": {
    "Groceries": 600.00,
    "Restaurants": 200.00
  },
  "start_date": "2025-11-01T00:00:00",
  "rollover_enabled": true
}
```

**Response** (201 Created):
```json
{
  "id": "bud_abc123",
  "user_id": "user_123",
  "name": "November 2025",
  "type": "personal",
  "period": "monthly",
  "categories": {
    "Groceries": 600.00,
    "Restaurants": 200.00
  },
  "start_date": "2025-11-01T00:00:00",
  "end_date": "2025-11-30T23:59:59",
  "rollover_enabled": true,
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-01T10:00:00Z"
}
```

### GET /budgets

List budgets for a user (with optional type filter).

**Query Parameters**:
- `user_id` (required): User identifier
- `type` (optional): Filter by budget type

**Example**:
```bash
GET /budgets?user_id=user_123&type=personal
```

**Response** (200 OK):
```json
[
  {
    "id": "bud_abc123",
    "user_id": "user_123",
    "name": "November 2025",
    "type": "personal",
    "period": "monthly",
    "categories": {...},
    "start_date": "2025-11-01T00:00:00",
    "end_date": "2025-11-30T23:59:59",
    "rollover_enabled": true,
    "created_at": "2025-11-01T10:00:00Z",
    "updated_at": "2025-11-01T10:00:00Z"
  }
]
```

### GET /budgets/{budget_id}

Get a single budget by ID.

**Response** (200 OK):
```json
{
  "id": "bud_abc123",
  "user_id": "user_123",
  "name": "November 2025",
  "type": "personal",
  "period": "monthly",
  "categories": {
    "Groceries": 600.00,
    "Restaurants": 200.00
  },
  "start_date": "2025-11-01T00:00:00",
  "end_date": "2025-11-30T23:59:59",
  "rollover_enabled": true,
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-01T10:00:00Z"
}
```

**Errors**:
- 404: Budget not found

### PATCH /budgets/{budget_id}

Update a budget (partial updates).

**Request Body** (all fields optional):
```json
{
  "name": "Updated Budget Name",
  "categories": {
    "Groceries": 700.00,
    "Restaurants": 250.00
  },
  "rollover_enabled": false
}
```

**Response** (200 OK):
```json
{
  "id": "bud_abc123",
  "user_id": "user_123",
  "name": "Updated Budget Name",
  "type": "personal",
  "period": "monthly",
  "categories": {
    "Groceries": 700.00,
    "Restaurants": 250.00
  },
  "start_date": "2025-11-01T00:00:00",
  "end_date": "2025-11-30T23:59:59",
  "rollover_enabled": false,
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-15T14:30:00Z"
}
```

**Errors**:
- 400: No updates provided or validation error
- 404: Budget not found

### DELETE /budgets/{budget_id}

Delete a budget.

**Response** (204 No Content):
No response body.

**Errors**:
- 404: Budget not found

### GET /budgets/{budget_id}/progress

Get budget progress with spending breakdown.

**Response** (200 OK):
```json
{
  "budget_id": "bud_abc123",
  "current_period": "November 2025",
  "categories": [
    {
      "category_name": "Groceries",
      "budgeted_amount": 600.00,
      "spent_amount": 425.50,
      "remaining_amount": 174.50,
      "percent_used": 70.92
    },
    {
      "category_name": "Restaurants",
      "budgeted_amount": 200.00,
      "spent_amount": 180.25,
      "remaining_amount": 19.75,
      "percent_used": 90.13
    }
  ],
  "total_budgeted": 800.00,
  "total_spent": 605.75,
  "total_remaining": 194.25,
  "percent_used": 75.72,
  "period_days_elapsed": 15,
  "period_days_total": 30
}
```

**Errors**:
- 404: Budget not found

### GET /budgets/templates/list

List all available budget templates.

**Response** (200 OK):
```json
{
  "50_30_20": {
    "name": "50/30/20 Rule",
    "description": "50% needs, 30% wants, 20% savings",
    "type": "personal",
    "period": "monthly",
    "categories": {
      "Housing": 25.0,
      "Groceries": 10.0,
      "Utilities": 4.0,
      "Transportation": 6.0,
      "Insurance": 5.0,
      "Restaurants": 8.0,
      "Entertainment": 6.0,
      "Shopping": 8.0,
      "Hobbies": 4.0,
      "Travel": 4.0,
      "Emergency Fund": 6.0,
      "Investments": 10.0,
      "Debt Paydown": 4.0
    }
  },
  "zero_based": {...},
  "envelope": {...},
  "pay_yourself_first": {...},
  "business_essentials": {...}
}
```

### POST /budgets/from-template

Create a budget from a template.

**Request Body**:
```json
{
  "user_id": "user_123",
  "template_name": "50_30_20",
  "total_income": 5000.00,
  "budget_name": "November 2025 - 50/30/20",
  "start_date": "2025-11-01T00:00:00"
}
```

**Response** (201 Created):
```json
{
  "id": "bud_def456",
  "user_id": "user_123",
  "name": "November 2025 - 50/30/20",
  "type": "personal",
  "period": "monthly",
  "categories": {
    "Housing": 1250.00,
    "Groceries": 500.00,
    "Utilities": 200.00,
    "Transportation": 300.00,
    "Insurance": 250.00,
    "Restaurants": 400.00,
    "Entertainment": 300.00,
    "Shopping": 400.00,
    "Hobbies": 200.00,
    "Travel": 200.00,
    "Emergency Fund": 300.00,
    "Investments": 500.00,
    "Debt Paydown": 200.00
  },
  "start_date": "2025-11-01T00:00:00",
  "end_date": "2025-11-30T23:59:59",
  "rollover_enabled": false,
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-01T10:00:00Z"
}
```

**Errors**:
- 400: Invalid template name or income amount

---

## Implementation Details

### Database Schema

```python
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BudgetModel(Base):
    __tablename__ = "budgets"
    
    id = Column(String, primary_key=True)  # "bud_abc123"
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # personal, household, business, project, custom
    period = Column(String, nullable=False)  # weekly, biweekly, monthly, quarterly, yearly
    categories = Column(JSON, nullable=False)  # {"Groceries": 600.00, ...}
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    rollover_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

### Tracker Architecture

```python
class BudgetTracker:
    def __init__(self, db_engine: AsyncEngine):
        self.db_engine = db_engine
        self.session_maker = async_sessionmaker(db_engine, expire_on_commit=False)
    
    async def create_budget(...) -> Budget:
        """Create new budget with validation"""
        # Validate inputs
        # Calculate end_date from start_date + period
        # Generate unique ID
        # Store in database
        pass
    
    async def get_budgets(user_id: str, type: Optional[BudgetType] = None) -> list[Budget]:
        """List budgets with optional type filter"""
        pass
    
    async def get_budget(budget_id: str) -> Budget:
        """Get single budget by ID"""
        pass
    
    async def update_budget(budget_id: str, updates: dict) -> Budget:
        """Partial update of budget"""
        pass
    
    async def delete_budget(budget_id: str) -> None:
        """Delete budget"""
        pass
    
    async def get_budget_progress(budget_id: str) -> BudgetProgress:
        """Calculate spending progress"""
        # TODO: Fetch transactions from categorization module
        # TODO: Calculate spent amounts per category
        # TODO: Calculate percentages and remaining amounts
        pass
```

### Easy Builder

```python
def easy_budgets(
    db_url: Optional[str] = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> BudgetTracker:
    """
    Easy setup for BudgetTracker with sensible defaults.
    
    Args:
        db_url: Database URL (falls back to SQL_URL env var)
        pool_size: Connection pool size (default: 5)
        max_overflow: Max overflow connections (default: 10)
        pool_pre_ping: Test connections before use (default: True)
        echo: Log SQL statements (default: False)
    
    Returns:
        Configured BudgetTracker instance
    """
    database_url = db_url or os.getenv("SQL_URL")
    if not database_url:
        raise ValueError("Database URL required (db_url or SQL_URL env var)")
    
    engine = create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        echo=echo,
        pool_recycle=3600,
        connect_args=_get_connect_args(database_url),
    )
    
    return BudgetTracker(db_engine=engine)
```

### FastAPI Helper

```python
def add_budgets(
    app: FastAPI,
    tracker: Optional[BudgetTracker] = None,
    db_url: Optional[str] = None,
    prefix: str = "/budgets",
) -> BudgetTracker:
    """
    Add budget management endpoints to FastAPI app.
    
    Args:
        app: FastAPI application instance
        tracker: BudgetTracker instance (creates via easy_budgets if not provided)
        db_url: Database URL (used if tracker not provided)
        prefix: URL prefix for budget routes (default: "/budgets")
    
    Returns:
        BudgetTracker instance for programmatic access
    """
    if tracker is None:
        tracker = easy_budgets(db_url=db_url)
    
    app.state.budget_tracker = tracker
    
    # Create router
    from fastapi import APIRouter
    router = APIRouter(prefix=prefix, tags=["Budget Management"])
    
    # Mount 8 endpoints
    # ... (endpoint definitions)
    
    app.include_router(router, include_in_schema=True)
    
    # Register scoped docs
    try:
        from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
        add_prefixed_docs(
            app,
            prefix=prefix,
            title="Budget Management",
            auto_exclude_from_root=True,
            visible_envs=None,
        )
    except ImportError:
        pass
    
    return tracker
```

---

## Testing

### Unit Tests

```python
# tests/unit/budgets/test_tracker.py
@pytest.mark.asyncio
async def test_create_budget():
    tracker = easy_budgets(db_url="sqlite+aiosqlite:///:memory:")
    
    budget = await tracker.create_budget(
        user_id="user_123",
        name="November 2025",
        type=BudgetType.PERSONAL,
        period=BudgetPeriod.MONTHLY,
        categories={"Groceries": 600.00},
        start_date=datetime(2025, 11, 1),
    )
    
    assert budget.id.startswith("bud_")
    assert budget.name == "November 2025"
    assert budget.categories["Groceries"] == 600.00
```

### Integration Tests

```python
# tests/integration/test_budgets_api.py
from fastapi.testclient import TestClient

def test_budget_workflow():
    app = FastAPI()
    add_budgets(app, db_url="sqlite+aiosqlite:///:memory:")
    client = TestClient(app)
    
    # Create budget
    response = client.post("/budgets", json={
        "user_id": "user_123",
        "name": "November 2025",
        "type": "personal",
        "period": "monthly",
        "categories": {"Groceries": 600.00},
        "start_date": "2025-11-01T00:00:00",
    })
    assert response.status_code == 200
    budget_id = response.json()["id"]
    
    # List budgets
    response = client.get("/budgets?user_id=user_123")
    assert len(response.json()) == 1
    
    # Delete budget
    response = client.delete(f"/budgets/{budget_id}")
    assert response.status_code == 204
```

---

## Troubleshooting

### Common Issues

**Issue**: "Database URL required"
```
ValueError: Database URL required (db_url or SQL_URL env var)
```
**Solution**: Provide `db_url` parameter or set `SQL_URL` environment variable:
```python
tracker = easy_budgets(db_url="postgresql+asyncpg://localhost/mydb")
# OR
export SQL_URL="postgresql+asyncpg://localhost/mydb"
```

**Issue**: "Budget not found"
```
ValueError: Budget with ID bud_123 not found
```
**Solution**: Verify budget ID exists in database:
```python
budgets = await tracker.get_budgets(user_id="user_123")
print([b.id for b in budgets])
```

**Issue**: "Invalid template name"
```
ValueError: Template 'invalid_name' not found
```
**Solution**: List available templates:
```python
from fin_infra.budgets import list_templates
templates = list_templates()
print(templates.keys())  # ['50_30_20', 'zero_based', 'envelope', 'pay_yourself_first', 'business_essentials']
```

**Issue**: "No updates provided"
```
ValueError: No updates provided
```
**Solution**: Provide at least one field to update:
```python
await tracker.update_budget(
    budget_id="bud_123",
    updates={"name": "Updated Name"}  # At least one field
)
```

### Debug Mode

Enable SQL logging to debug database issues:
```python
tracker = easy_budgets(
    db_url="postgresql+asyncpg://localhost/mydb",
    echo=True,  # Log all SQL statements
)
```

### Performance Tips

**Use connection pooling for high-traffic apps**:
```python
tracker = easy_budgets(
    db_url="postgresql+asyncpg://localhost/mydb",
    pool_size=20,  # Increase pool size
    max_overflow=40,  # Allow more overflow connections
)
```

**Cache budget progress calculations**:
```python
from svc_infra.cache import cache_read

@cache_read(ttl=300)  # Cache for 5 minutes
async def get_cached_progress(budget_id: str):
    return await tracker.get_budget_progress(budget_id)
```

---

## Future Enhancements

### Planned Features

1. **Automatic Transaction Linking**: Integrate with categorization module to automatically fetch spending data
2. **Budget Sharing**: Share household budgets with family members (multi-user access)
3. **Budget History**: Track budget changes over time (version history)
4. **Budget Analytics**: Spending trends, category insights, savings rate calculations
5. **Budget Recommendations**: AI-powered suggestions based on spending patterns
6. **Budget Forecasting**: Predict end-of-period spending based on current trends
7. **Budget Goals**: Link budgets to financial goals (save $10k for vacation)
8. **Budget Notifications**: SMS/email alerts for budget warnings via svc-infra

### Roadmap

- **v1.0** (Current): Core CRUD, templates, alerts, API ✅
- **v1.1**: Transaction linking, automatic spending tracking
- **v1.2**: Budget sharing, multi-user access
- **v1.3**: Analytics, insights, forecasting
- **v1.4**: AI recommendations, goal linking

---

## Additional Resources

- **Source Code**: `src/fin_infra/budgets/`
- **Tests**: `tests/unit/budgets/`, `tests/integration/test_budgets_api.py`
- **ADR**: [ADR-0024: Budget Management Design](adr/0024-budget-management-design.md)
- **svc-infra**: Backend infrastructure (API, DB, cache, jobs)
- **fin-infra**: Financial providers (banking, brokerage, market data)

### Related Modules

- **Categorization**: Transaction category assignment (feeds spending data to budgets)
- **Net Worth**: Total wealth calculation (budgets help control spending)
- **Analytics**: Financial insights and trends (budget performance analysis)
- **Goals**: Financial goal tracking (budgets help achieve goals)

### Support

For questions, issues, or feature requests:
- GitHub Issues: `fin-infra/issues`
- Documentation: `src/fin_infra/docs/`
- ADRs: `src/fin_infra/docs/adr/`
