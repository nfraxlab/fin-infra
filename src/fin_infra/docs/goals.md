# Goal Management

> **Comprehensive financial goal tracking with milestones, funding allocation, and progress monitoring**

## Overview

Goal management helps users set, track, and achieve financial objectives through structured goal setting, milestone tracking, and multi-account funding allocation. Supports multiple goal types for diverse fintech use cases.

```
Goal Types: Savings | Debt | Investment | Net Worth | Income | Custom
Goal Statuses: Active | Paused | Completed | Abandoned
Tracking: Progress monitoring, milestone checkpoints, funding sources
```

### Key Features

- **Multi-Type Goals**: Savings, debt payoff, investment targets, net worth milestones, income goals, and custom types
- **Milestone Tracking**: Set checkpoint amounts with target dates; auto-mark as reached when current amount exceeds milestone
- **Funding Allocation**: Link multiple accounts to goals with percentage-based allocation (e.g., 60% savings + 40% checking)
- **Progress Monitoring**: Real-time progress calculations with projected completion dates
- **Flexible Management**: Pause, resume, complete, or abandon goals; update targets and deadlines dynamically
- **REST API**: 13 endpoints for full CRUD operations, milestone management, and funding allocation
- **Generic Design**: Works for ANY fintech application (personal finance, wealth management, banking, budgeting)

### Use Cases

- **Personal Finance Apps** (Mint, YNAB, Personal Capital): Emergency fund savings, vacation goals, debt payoff tracking
- **Wealth Management** (Betterment, Wealthfront): Net worth milestones, investment targets, retirement planning
- **Banking Apps** (Chime, Revolut, N26): Goal-based savings accounts, automated transfers, progress tracking
- **Budgeting Tools** (Simplifi, PocketGuard): Spending goals, savings targets, financial milestone tracking
- **Investment Platforms** (Robinhood, Webull): Portfolio growth goals, investment return targets
- **Business Finance**: Revenue goals, debt reduction, cash reserve targets

---

## Quick Start

### 1. Basic Setup (Programmatic)

```python
from fin_infra.goals import easy_goals, GoalType, GoalStatus
from datetime import datetime, timedelta

# Create goal manager
manager = easy_goals()

# Create a savings goal
goal = await manager.create_goal(
    user_id="user_123",
    name="Emergency Fund",
    type=GoalType.SAVINGS,
    target_amount=10000.00,
    current_amount=2500.00,
    deadline=datetime.now() + timedelta(days=365),  # 1 year
    description="Build 6-month emergency fund",
    status=GoalStatus.ACTIVE,
)

print(f"Goal Created: {goal['name']}")
print(f"Target: ${goal['target_amount']:,.2f}")
print(f"Current: ${goal['current_amount']:,.2f}")
print(f"Progress: {goal['current_amount'] / goal['target_amount'] * 100:.1f}%")
```

### 2. Milestone Tracking

```python
from fin_infra.goals import add_milestone, check_milestones

# Add milestones at 25%, 50%, 75% of target
milestones = [
    {
        "amount": 2500.00,
        "description": "25% to emergency fund",
        "target_date": datetime.now() + timedelta(days=90),
    },
    {
        "amount": 5000.00,
        "description": "50% to emergency fund",
        "target_date": datetime.now() + timedelta(days=180),
    },
    {
        "amount": 7500.00,
        "description": "75% to emergency fund",
        "target_date": datetime.now() + timedelta(days=270),
    },
]

for milestone in milestones:
    await manager.add_milestone(goal_id=goal["id"], **milestone)

# Update current amount and check milestones
goal = await manager.update_goal(
    goal_id=goal["id"],
    current_amount=5500.00,  # Now at $5,500
)

# Check which milestones were reached
newly_reached = await manager.check_milestones(goal_id=goal["id"])
print(f"Newly Reached Milestones: {len(newly_reached)}")  # 2 (25% and 50%)

# Get milestone progress
progress = await manager.get_milestone_progress(goal_id=goal["id"])
print(f"Reached: {progress['reached_count']}/{progress['total_milestones']}")
print(f"Completion: {progress['percent_complete']:.1f}%")
```

### 3. Funding Allocation

```python
from fin_infra.goals import link_account_to_goal, get_goal_funding

# Link savings account to goal (60% allocation)
await manager.link_account_to_goal(
    goal_id=goal["id"],
    account_id="savings_001",
    account_name="High Yield Savings",
    allocation_percent=60.0,
)

# Link checking account to goal (40% allocation)
await manager.link_account_to_goal(
    goal_id=goal["id"],
    account_id="checking_001",
    account_name="Primary Checking",
    allocation_percent=40.0,
)

# Get funding breakdown
funding = await manager.get_goal_funding(goal_id=goal["id"])
print(f"Funding Sources: {len(funding)}")
for source in funding:
    print(f"  {source['account_name']}: {source['allocation_percent']}%")

# Update allocation (validation: total ≤ 100%)
await manager.update_account_allocation(
    goal_id=goal["id"],
    account_id="savings_001",
    allocation_percent=70.0,  # Increase savings allocation
)

# Remove account from goal
await manager.remove_account_from_goal(
    goal_id=goal["id"],
    account_id="checking_001",
)
```

### 4. FastAPI Integration

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from fin_infra.goals import add_goals, easy_goals

# Create app (svc-infra)
app = easy_service_app(name="FinanceAPI")

# Wire goals module (fin-infra)
manager = easy_goals()
add_goals(app, manager=manager, prefix="/goals")

# Now available:
# POST   /goals                          - Create goal
# GET    /goals                          - List goals (filter by user_id, type)
# GET    /goals/{goal_id}                - Get goal details
# PATCH  /goals/{goal_id}                - Update goal
# DELETE /goals/{goal_id}                - Delete goal
# GET    /goals/{goal_id}/progress       - Get progress
# POST   /goals/{goal_id}/milestones     - Add milestone
# GET    /goals/{goal_id}/milestones     - List milestones
# GET    /goals/{goal_id}/milestones/progress - Milestone progress
# POST   /goals/{goal_id}/funding        - Link account
# GET    /goals/{goal_id}/funding        - List funding sources
# PATCH  /goals/{goal_id}/funding/{account_id} - Update allocation
# DELETE /goals/{goal_id}/funding/{account_id} - Remove account
```

---

## Core Concepts

### Goal Types

Goals support 6 types for diverse financial objectives:

| Type | Description | Example Use Cases |
|------|-------------|-------------------|
| `SAVINGS` | General savings goal | Emergency fund, vacation, down payment |
| `DEBT` | Debt payoff goal | Credit card payoff, student loan elimination |
| `INVESTMENT` | Investment target | Portfolio growth, retirement savings |
| `NET_WORTH` | Net worth milestone | Reach $1M net worth, double net worth |
| `INCOME` | Income goal | Salary target, passive income milestone |
| `CUSTOM` | Custom goal type | Any other financial objective |

**Example: Savings Goal**
```python
goal = await manager.create_goal(
    user_id="user_123",
    name="Vacation Fund",
    type=GoalType.SAVINGS,
    target_amount=5000.00,
    current_amount=0.00,
    deadline=datetime(2026, 6, 1),
    description="Hawaii vacation summer 2026",
)
```

**Example: Debt Payoff Goal**
```python
goal = await manager.create_goal(
    user_id="user_123",
    name="Credit Card Payoff",
    type=GoalType.DEBT,
    target_amount=8500.00,  # Total debt
    current_amount=8500.00,  # Start at full debt
    deadline=datetime(2026, 12, 31),
    description="Pay off Chase Sapphire balance",
    # For debt goals: current_amount decreases toward 0
)
```

**Example: Net Worth Milestone**
```python
goal = await manager.create_goal(
    user_id="user_123",
    name="$500K Net Worth",
    type=GoalType.NET_WORTH,
    target_amount=500000.00,
    current_amount=350000.00,
    deadline=datetime(2028, 1, 1),
    description="Reach half-million net worth by 2028",
)
```

### Goal Statuses

Goals progress through 4 lifecycle statuses:

| Status | Description | Transitions |
|--------|-------------|-------------|
| `ACTIVE` | In progress, being tracked | → PAUSED, COMPLETED, ABANDONED |
| `PAUSED` | Temporarily suspended | → ACTIVE, ABANDONED |
| `COMPLETED` | Target achieved | Final state (no transitions) |
| `ABANDONED` | Goal given up | Final state (no transitions) |

**Status Management**
```python
# Pause goal temporarily
goal = await manager.update_goal(
    goal_id=goal["id"],
    status=GoalStatus.PAUSED,
)

# Resume goal
goal = await manager.update_goal(
    goal_id=goal["id"],
    status=GoalStatus.ACTIVE,
)

# Mark as completed (when target reached)
goal = await manager.update_goal(
    goal_id=goal["id"],
    status=GoalStatus.COMPLETED,
)

# Abandon goal
goal = await manager.update_goal(
    goal_id=goal["id"],
    status=GoalStatus.ABANDONED,
)
```

### Milestones

Milestones break goals into checkpoint amounts with optional target dates. They auto-mark as `reached=True` when `current_amount` exceeds the milestone amount.

**Milestone Structure**
```python
{
    "amount": 5000.00,                    # Checkpoint amount
    "description": "Halfway to goal",     # Descriptive text
    "target_date": "2025-12-31T00:00:00", # Optional target date
    "reached": False,                     # Auto-set to True when reached
    "reached_date": None,                 # Auto-set when reached
}
```

**Auto-Completion Logic**
```python
# Milestones automatically marked as reached
goal = await manager.update_goal(
    goal_id=goal["id"],
    current_amount=6000.00,  # Exceeds $5,000 milestone
)

# check_milestones() updates reached status
newly_reached = await manager.check_milestones(goal_id=goal["id"])
# Returns: [{"amount": 5000.00, "reached": True, "reached_date": "2025-11-09T..."}]

# Milestone progress stats
progress = await manager.get_milestone_progress(goal_id=goal["id"])
# Returns: {
#   "goal_id": "...",
#   "total_milestones": 4,
#   "reached_count": 2,
#   "percent_complete": 50.0,
#   "next_milestone": {"amount": 7500.00, ...},
# }
```

**Best Practices**
- Use 3-5 milestones per goal for motivation
- Space milestones evenly (25%, 50%, 75% of target)
- Include target dates to track timeline progress
- Call `check_milestones()` after updating `current_amount`

### Funding Allocation

Link multiple accounts to goals with percentage-based allocation. Supports:
- **Split funding**: Multiple accounts fund one goal
- **Shared accounts**: One account funds multiple goals
- **Validation**: Total allocation per goal ≤ 100%

**Funding Structure**
```python
{
    "account_id": "savings_001",
    "account_name": "High Yield Savings",
    "allocation_percent": 60.0,  # 60% of goal funded from this account
}
```

**Multi-Account Allocation**
```python
# Link 3 accounts to one goal
await manager.link_account_to_goal(
    goal_id=goal["id"],
    account_id="savings_001",
    account_name="High Yield Savings",
    allocation_percent=50.0,
)

await manager.link_account_to_goal(
    goal_id=goal["id"],
    account_id="checking_001",
    account_name="Primary Checking",
    allocation_percent=30.0,
)

await manager.link_account_to_goal(
    goal_id=goal["id"],
    account_id="investment_001",
    account_name="Brokerage Account",
    allocation_percent=20.0,
)

# Total: 50% + 30% + 20% = 100% ✅

# Validation error if exceeds 100%
await manager.link_account_to_goal(
    goal_id=goal["id"],
    account_id="another_account",
    allocation_percent=10.0,  # Would exceed 100%
)
# Raises: ValueError("Total allocation would exceed 100%")
```

**Shared Account Allocation**
```python
# One account can fund multiple goals
# savings_001 allocated to 3 goals:
# - Emergency fund: 60%
# - Vacation: 30%
# - Down payment: 40%
# Total from savings_001: 130% (OK - different goals)

# But total allocation PER GOAL must be ≤ 100%
```

---

## Progress Tracking

### Goal Progress

Progress calculated as `current_amount / target_amount * 100%`.

**Get Progress**
```python
progress = await manager.get_goal_progress(goal_id=goal["id"])

# Returns:
{
    "goal_id": "...",
    "current_amount": 6500.00,
    "target_amount": 10000.00,
    "percent_complete": 65.0,
    "status": "active",
    "deadline": "2025-11-09T00:00:00",
    "projected_completion_date": "2025-10-15T00:00:00",  # Based on trajectory
}
```

**Projected Completion Date**
- Calculated from recent progress trend
- Assumes linear growth based on last 30 days
- Updates dynamically as `current_amount` changes

### Milestone Progress

Track milestone completion separately from overall goal progress.

**Get Milestone Progress**
```python
progress = await manager.get_milestone_progress(goal_id=goal["id"])

# Returns:
{
    "goal_id": "...",
    "total_milestones": 4,
    "reached_count": 2,
    "percent_complete": 50.0,
    "next_milestone": {
        "amount": 7500.00,
        "description": "75% to emergency fund",
        "target_date": "2025-12-31T00:00:00",
        "reached": False,
    },
}
```

**Use Cases**
- Display progress bars with milestone markers
- Send notifications when milestones reached
- Gamification: badges/rewards for hitting milestones
- Motivation: visualize progress toward next checkpoint

---

## API Reference

### CRUD Operations

#### Create Goal
```http
POST /goals
Content-Type: application/json

{
  "user_id": "user_123",
  "name": "Emergency Fund",
  "type": "savings",
  "target_amount": 10000.00,
  "current_amount": 0.00,
  "deadline": "2026-11-09T00:00:00",
  "description": "Build 6-month emergency fund",
  "status": "active"
}

Response: 201 Created
{
  "id": "goal_abc123",
  "user_id": "user_123",
  "name": "Emergency Fund",
  "type": "savings",
  "target_amount": 10000.00,
  "current_amount": 0.00,
  "deadline": "2026-11-09T00:00:00",
  "description": "Build 6-month emergency fund",
  "status": "active",
  "created_at": "2025-11-09T12:00:00",
  "updated_at": "2025-11-09T12:00:00",
  "milestones": [],
}
```

#### List Goals
```http
GET /goals?user_id=user_123&type=savings

Response: 200 OK
[
  {
    "id": "goal_abc123",
    "user_id": "user_123",
    "name": "Emergency Fund",
    "type": "savings",
    ...
  },
  ...
]
```

**Query Parameters**
- `user_id` (optional): Filter by user
- `type` (optional): Filter by goal type (savings, debt, investment, net_worth, income, custom)

#### Get Goal
```http
GET /goals/{goal_id}

Response: 200 OK
{
  "id": "goal_abc123",
  "user_id": "user_123",
  "name": "Emergency Fund",
  "type": "savings",
  "target_amount": 10000.00,
  "current_amount": 2500.00,
  "deadline": "2026-11-09T00:00:00",
  "description": "Build 6-month emergency fund",
  "status": "active",
  "created_at": "2025-11-09T12:00:00",
  "updated_at": "2025-11-09T14:30:00",
  "milestones": [
    {
      "amount": 2500.00,
      "description": "25% to emergency fund",
      "target_date": "2025-12-09T00:00:00",
      "reached": True,
      "reached_date": "2025-11-15T10:00:00",
    },
    ...
  ],
}

Response: 404 Not Found (if goal not found)
```

#### Update Goal
```http
PATCH /goals/{goal_id}
Content-Type: application/json

{
  "current_amount": 3500.00,
  "status": "active"
}

Response: 200 OK
{
  "id": "goal_abc123",
  "current_amount": 3500.00,  # Updated
  "status": "active",
  ...
}

Response: 404 Not Found (if goal not found)
```

**Updatable Fields**
- `name`, `description`
- `target_amount`, `current_amount`
- `deadline`
- `status` (active, paused, completed, abandoned)

#### Delete Goal
```http
DELETE /goals/{goal_id}

Response: 204 No Content

Response: 404 Not Found (if goal not found)
```

### Progress Endpoints

#### Get Goal Progress
```http
GET /goals/{goal_id}/progress

Response: 200 OK
{
  "goal_id": "goal_abc123",
  "current_amount": 6500.00,
  "target_amount": 10000.00,
  "percent_complete": 65.0,
  "status": "active",
  "deadline": "2026-11-09T00:00:00",
  "projected_completion_date": "2026-09-15T00:00:00",
}

Response: 404 Not Found (if goal not found)
```

### Milestone Endpoints

#### Add Milestone
```http
POST /goals/{goal_id}/milestones
Content-Type: application/json

{
  "amount": 5000.00,
  "description": "Halfway to emergency fund",
  "target_date": "2025-12-31T00:00:00"
}

Response: 201 Created
{
  "amount": 5000.00,
  "description": "Halfway to emergency fund",
  "target_date": "2025-12-31T00:00:00",
  "reached": False,
  "reached_date": None,
}

Response: 404 Not Found (if goal not found)
```

#### List Milestones
```http
GET /goals/{goal_id}/milestones

Response: 200 OK
[
  {
    "amount": 2500.00,
    "description": "25% to emergency fund",
    "target_date": "2025-12-09T00:00:00",
    "reached": True,
    "reached_date": "2025-11-15T10:00:00",
  },
  {
    "amount": 5000.00,
    "description": "50% to emergency fund",
    "target_date": "2025-12-31T00:00:00",
    "reached": False,
    "reached_date": None,
  },
  ...
]

Response: 404 Not Found (if goal not found)
```

#### Get Milestone Progress
```http
GET /goals/{goal_id}/milestones/progress

Response: 200 OK
{
  "goal_id": "goal_abc123",
  "total_milestones": 4,
  "reached_count": 2,
  "percent_complete": 50.0,
  "next_milestone": {
    "amount": 5000.00,
    "description": "50% to emergency fund",
    "target_date": "2025-12-31T00:00:00",
    "reached": False,
  },
}

Response: 404 Not Found (if goal not found)
```

### Funding Endpoints

#### Link Account to Goal
```http
POST /goals/{goal_id}/funding
Content-Type: application/json

{
  "account_id": "savings_001",
  "account_name": "High Yield Savings",
  "allocation_percent": 60.0
}

Response: 201 Created
{
  "account_id": "savings_001",
  "account_name": "High Yield Savings",
  "allocation_percent": 60.0,
}

Response: 400 Bad Request (if total allocation exceeds 100%)
{
  "detail": "Total allocation would exceed 100%"
}

Response: 404 Not Found (if goal not found)
```

#### Get Goal Funding
```http
GET /goals/{goal_id}/funding

Response: 200 OK
[
  {
    "account_id": "savings_001",
    "account_name": "High Yield Savings",
    "allocation_percent": 60.0,
  },
  {
    "account_id": "checking_001",
    "account_name": "Primary Checking",
    "allocation_percent": 40.0,
  },
]

Response: 404 Not Found (if goal not found)
```

#### Update Account Allocation
```http
PATCH /goals/{goal_id}/funding/{account_id}
Content-Type: application/json

{
  "allocation_percent": 70.0
}

Response: 200 OK
{
  "account_id": "savings_001",
  "account_name": "High Yield Savings",
  "allocation_percent": 70.0,
}

Response: 400 Bad Request (if total allocation exceeds 100%)
Response: 404 Not Found (if goal or account not found)
```

#### Remove Account from Goal
```http
DELETE /goals/{goal_id}/funding/{account_id}

Response: 204 No Content

Response: 404 Not Found (if goal or account not found)
```

---

## Integration Patterns

### With svc-infra

Goals module uses svc-infra for backend infrastructure:

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.logging import setup_logging
from svc_infra.cache import init_cache
from svc_infra.obs import add_observability
from fin_infra.goals import add_goals, easy_goals

# Setup backend (svc-infra)
setup_logging()
app = easy_service_app(name="FinanceAPI")
init_cache(url="redis://localhost")
add_observability(app)

# Wire goals (fin-infra)
manager = easy_goals()
add_goals(app, manager=manager, prefix="/goals")
```

**svc-infra Integration**
- **API Framework**: Uses plain `APIRouter` (not `user_router` to avoid database dependencies)
- **Logging**: Structured logging via `setup_logging()`
- **Caching**: Optional caching for goal queries (TTL: 5 minutes)
- **Observability**: Prometheus metrics for API calls
- **Jobs**: Future: scheduled milestone checks via `easy_jobs()`

### With Other Modules

**Net Worth Tracking**
```python
from fin_infra.net_worth import easy_net_worth
from fin_infra.goals import easy_goals, GoalType

# Track net worth goal progress
net_worth_tracker = easy_net_worth()
goal_manager = easy_goals()

# Get current net worth
snapshot = await net_worth_tracker.calculate_net_worth(user_id="user_123")
current_net_worth = snapshot["net_worth"]

# Update net worth goal
goal = await goal_manager.update_goal(
    goal_id="net_worth_goal_123",
    current_amount=current_net_worth,
)

# Check if goal completed
if current_net_worth >= goal["target_amount"]:
    await goal_manager.update_goal(
        goal_id=goal["id"],
        status=GoalStatus.COMPLETED,
    )
```

**Budget Management**
```python
from fin_infra.budgets import easy_budgets
from fin_infra.goals import easy_goals, GoalType

# Link savings goal to budget category
budget_tracker = easy_budgets()
goal_manager = easy_goals()

# Create savings goal
goal = await goal_manager.create_goal(
    user_id="user_123",
    name="Vacation Fund",
    type=GoalType.SAVINGS,
    target_amount=5000.00,
    current_amount=0.00,
)

# Create budget with savings category
budget = await budget_tracker.create_budget(
    user_id="user_123",
    name="November 2025",
    categories={
        "Vacation Savings": 500.00,  # $500/month toward goal
        ...
    },
)

# Update goal monthly based on budget savings
monthly_savings = 500.00
goal = await goal_manager.update_goal(
    goal_id=goal["id"],
    current_amount=goal["current_amount"] + monthly_savings,
)
```

**Analytics**
```python
from fin_infra.analytics import easy_analytics
from fin_infra.goals import easy_goals

# Get savings rate to recommend goal contributions
analytics = easy_analytics()
goal_manager = easy_goals()

savings = await analytics.savings_rate(user_id="user_123", period="monthly")
monthly_savings = savings.monthly_savings_amount

# Recommend goal allocation
goals = await goal_manager.list_goals(user_id="user_123", status="active")
allocation_per_goal = monthly_savings / len(goals)

print(f"Monthly Savings: ${monthly_savings:,.2f}")
print(f"Recommended per goal: ${allocation_per_goal:,.2f}")
```

---

## Examples

### Example 1: Emergency Fund with Milestones

```python
from fin_infra.goals import easy_goals, GoalType, GoalStatus
from datetime import datetime, timedelta

manager = easy_goals()

# Create emergency fund goal (6 months expenses = $18,000)
goal = await manager.create_goal(
    user_id="user_123",
    name="6-Month Emergency Fund",
    type=GoalType.SAVINGS,
    target_amount=18000.00,
    current_amount=0.00,
    deadline=datetime.now() + timedelta(days=730),  # 2 years
    description="Save 6 months of expenses ($3,000/month)",
    status=GoalStatus.ACTIVE,
)

# Add milestones at 1, 2, 3, 4, 5, 6 months
for month in range(1, 7):
    await manager.add_milestone(
        goal_id=goal["id"],
        amount=month * 3000.00,
        description=f"{month} month{'s' if month > 1 else ''} of expenses saved",
        target_date=datetime.now() + timedelta(days=month * 60),  # ~60 days per $3k
    )

# Monthly update: Add $500 savings
for month in range(1, 13):  # 12 months
    current = goal["current_amount"] + 500.00
    goal = await manager.update_goal(
        goal_id=goal["id"],
        current_amount=current,
    )
    
    # Check milestones
    newly_reached = await manager.check_milestones(goal_id=goal["id"])
    if newly_reached:
        print(f"Month {month}: Reached {len(newly_reached)} milestone(s)!")
    
    # Progress
    progress = await manager.get_goal_progress(goal_id=goal["id"])
    print(f"Month {month}: ${current:,.2f} / ${goal['target_amount']:,.2f} ({progress['percent_complete']:.1f}%)")
```

### Example 2: Multi-Goal Funding Allocation

```python
from fin_infra.goals import easy_goals, GoalType
from datetime import datetime, timedelta

manager = easy_goals()

# Create 3 goals
emergency_fund = await manager.create_goal(
    user_id="user_123",
    name="Emergency Fund",
    type=GoalType.SAVINGS,
    target_amount=10000.00,
    current_amount=0.00,
    deadline=datetime.now() + timedelta(days=365),
)

vacation = await manager.create_goal(
    user_id="user_123",
    name="Hawaii Vacation",
    type=GoalType.SAVINGS,
    target_amount=5000.00,
    current_amount=0.00,
    deadline=datetime.now() + timedelta(days=180),
)

down_payment = await manager.create_goal(
    user_id="user_123",
    name="House Down Payment",
    type=GoalType.SAVINGS,
    target_amount=50000.00,
    current_amount=10000.00,
    deadline=datetime.now() + timedelta(days=1095),  # 3 years
)

# Allocate accounts to goals
# Emergency Fund: 100% from high-yield savings
await manager.link_account_to_goal(
    goal_id=emergency_fund["id"],
    account_id="savings_hysa",
    account_name="High Yield Savings",
    allocation_percent=100.0,
)

# Vacation: 60% checking + 40% savings
await manager.link_account_to_goal(
    goal_id=vacation["id"],
    account_id="checking_001",
    account_name="Primary Checking",
    allocation_percent=60.0,
)
await manager.link_account_to_goal(
    goal_id=vacation["id"],
    account_id="savings_hysa",
    account_name="High Yield Savings",
    allocation_percent=40.0,
)

# Down Payment: 50% savings + 30% investment + 20% checking
await manager.link_account_to_goal(
    goal_id=down_payment["id"],
    account_id="savings_hysa",
    account_name="High Yield Savings",
    allocation_percent=50.0,
)
await manager.link_account_to_goal(
    goal_id=down_payment["id"],
    account_id="investment_brokerage",
    account_name="Brokerage Account",
    allocation_percent=30.0,
)
await manager.link_account_to_goal(
    goal_id=down_payment["id"],
    account_id="checking_001",
    account_name="Primary Checking",
    allocation_percent=20.0,
)

# View all funding allocations
for goal_obj in [emergency_fund, vacation, down_payment]:
    funding = await manager.get_goal_funding(goal_id=goal_obj["id"])
    print(f"\n{goal_obj['name']} Funding:")
    for source in funding:
        print(f"  {source['account_name']}: {source['allocation_percent']}%")
```

### Example 3: Debt Payoff Goal

```python
from fin_infra.goals import easy_goals, GoalType, GoalStatus
from datetime import datetime, timedelta

manager = easy_goals()

# Credit card debt payoff (starts at full debt, decreases to 0)
debt_goal = await manager.create_goal(
    user_id="user_123",
    name="Credit Card Payoff",
    type=GoalType.DEBT,
    target_amount=0.00,  # Goal: $0 debt
    current_amount=8500.00,  # Start at $8,500 debt
    deadline=datetime.now() + timedelta(days=365),
    description="Pay off Chase Sapphire balance (22% APR)",
    status=GoalStatus.ACTIVE,
)

# Add payoff milestones (decreasing amounts)
milestones = [6000.00, 4000.00, 2000.00, 0.00]
for amount in milestones:
    await manager.add_milestone(
        goal_id=debt_goal["id"],
        amount=amount,
        description=f"Debt reduced to ${amount:,.2f}",
    )

# Monthly payments
monthly_payment = 750.00
for month in range(1, 13):
    current_debt = max(0, debt_goal["current_amount"] - monthly_payment)
    debt_goal = await manager.update_goal(
        goal_id=debt_goal["id"],
        current_amount=current_debt,
    )
    
    # Check milestones (debt decreasing)
    newly_reached = await manager.check_milestones(goal_id=debt_goal["id"])
    if newly_reached:
        print(f"Month {month}: Reached milestone! Debt now ${current_debt:,.2f}")
    
    # Check if paid off
    if current_debt == 0:
        await manager.update_goal(
            goal_id=debt_goal["id"],
            status=GoalStatus.COMPLETED,
        )
        print(f"Month {month}: DEBT PAID OFF! 🎉")
        break
```

---

## Best Practices

### Goal Design

1. **Set SMART Goals**
   - **S**pecific: Clear target amount and purpose
   - **M**easurable: Numeric target with progress tracking
   - **A**chievable: Realistic given income and expenses
   - **R**elevant: Aligns with financial priorities
   - **T**ime-bound: Clear deadline

2. **Use Appropriate Goal Types**
   - Savings goals: Start at $0, increase to target
   - Debt goals: Start at debt amount, decrease to $0
   - Net worth goals: Track overall wealth milestones
   - Income goals: Track salary/passive income targets

3. **Break Goals into Milestones**
   - Use 3-5 milestones per goal
   - Space evenly (25%, 50%, 75% of target)
   - Include target dates for timeline tracking
   - Celebrate milestone achievements

### Funding Allocation

1. **Prioritize Goals**
   - Emergency fund first (100% allocation)
   - Then retirement/long-term goals
   - Finally discretionary goals (vacation, etc.)

2. **Balance Risk and Liquidity**
   - Short-term goals (< 1 year): Checking/savings only
   - Medium-term goals (1-5 years): Mix savings + conservative investments
   - Long-term goals (5+ years): Higher investment allocation OK

3. **Review and Adjust**
   - Quarterly: Review allocation percentages
   - Annually: Rebalance based on account growth
   - As needed: Update when income/expenses change

### Progress Tracking

1. **Update Regularly**
   - Weekly: Update current_amount for active goals
   - Monthly: Review progress and adjust targets
   - Quarterly: Check milestone completion

2. **Automate When Possible**
   - Link to transaction categorization (auto-update from "savings" category)
   - Use webhooks to update from bank account balances
   - Schedule jobs to sync net worth goals with portfolio values

3. **Monitor and Adjust**
   - Behind schedule? Increase contributions or extend deadline
   - Ahead of schedule? Consider new stretch goals
   - Life changes? Pause goals temporarily, don't abandon

---

## Testing

### Unit Tests

Location: `tests/unit/goals/`

**test_management.py** (27 tests)
- CRUD operations: create, list, get, update, delete
- Filtering: by user_id, by goal type
- Validation: required fields, invalid values
- Edge cases: not found, duplicate IDs

**test_milestones.py** (28 tests, 2 skipped)
- Milestone CRUD: add, list, update, delete
- Auto-completion: check_milestones logic
- Progress tracking: reached_count, percent_complete
- Validation: target_date, reached_date logic
- Edge cases: no milestones, all reached, next milestone
- Skipped: 2 AsyncClient webhook tests (not implemented)

**test_funding.py** (29 tests)
- Funding CRUD: link, get, update, remove
- Allocation validation: total ≤ 100%
- Multi-account scenarios: split funding
- Shared accounts: one account, multiple goals
- Edge cases: not found, validation errors

**Run Unit Tests**
```bash
poetry run pytest tests/unit/goals -v
# Expected: 84 passed, 2 skipped
```

### Integration Tests

Location: `tests/integration/test_goals_api.py` (32 tests)

**Coverage**
- Helper: add_goals() mounts all routes correctly (1 test)
- CRUD: All 5 endpoints with edge cases (11 tests)
- Progress: Goal progress calculation (2 tests)
- Milestones: Add, list, progress endpoints (7 tests)
- Funding: Link, get, update, remove endpoints (9 tests)
- Lifecycle: Full workflows with multiple goals (3 tests)

**Run Integration Tests**
```bash
poetry run pytest tests/integration/test_goals_api.py -v
# Expected: 32 passed
```

**Full Test Suite**
```bash
poetry run pytest tests/unit/goals tests/integration/test_goals_api.py -v
# Expected: 116 passed, 2 skipped
```

---

## Architecture Decisions

See ADR: `src/fin_infra/docs/adr/0025-goals-module-refactoring.md`

**Key Decisions**
1. **Plain APIRouter**: Use plain FastAPI router (not svc-infra user_router) to avoid database dependencies
2. **In-Memory Storage**: Use dictionary stores for testing; production apps should use SQL/Mongo via svc-infra
3. **Auto-Completion**: Milestones auto-mark as reached when current_amount exceeds milestone amount
4. **Allocation Validation**: Total funding per goal ≤ 100%; no limit on total per account across goals
5. **Generic Design**: Support 6 goal types for diverse fintech use cases (not application-specific)

---

## Future Enhancements

### Planned Features

1. **Recurring Contributions** (Task 26)
   - Auto-update goals from scheduled transfers
   - Track contribution consistency
   - Alert if contribution missed

2. **Goal Templates** (Task 27)
   - Pre-built goal templates (emergency fund, retirement, vacation)
   - Quick setup with recommended milestones
   - Customizable parameters

3. **Goal Insights** (Task 28)
   - LLM-powered goal recommendations
   - Personalized advice on allocation
   - Risk assessment for timelines

4. **Goal Sharing** (Task 29)
   - Joint goals for households
   - Shared progress tracking
   - Multi-user funding allocation

5. **Goal History** (Task 30)
   - Track changes over time
   - Audit log for updates
   - Historical progress analysis

### Experimental Ideas

- **Gamification**: Badges, streaks, rewards for milestone completion
- **Social Features**: Compare progress with friends (anonymized)
- **Automation**: AI-driven rebalancing of funding allocation
- **Predictions**: ML-based completion date forecasting
- **Integration**: Link to employer 401k APIs for retirement goals

---

## Troubleshooting

### Common Issues

**Issue: Total allocation exceeds 100%**
```
Error: ValueError("Total allocation would exceed 100%")
```
**Solution**: Check current allocations with `get_goal_funding()` before adding new account. Update existing allocations if needed.

**Issue: Milestone not auto-reaching**
```
# Current amount exceeds milestone, but reached=False
```
**Solution**: Call `check_milestones(goal_id)` after updating `current_amount`. Milestones don't auto-update; must explicitly check.

**Issue: Goal not found (404)**
```
Error: 404 Not Found
```
**Solution**: Verify goal_id exists with `list_goals()`. Check user_id matches. Ensure goal wasn't deleted.

**Issue: Projected completion date inaccurate**
```
# Projected date doesn't match manual calculation
```
**Solution**: Projection assumes linear growth based on recent progress (last 30 days). Accuracy improves with more data points.

### Debug Tips

1. **Enable Debug Logging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Inspect Store State**
```python
from fin_infra.goals.management import _GOALS_STORE, _FUNDING_STORE
print(_GOALS_STORE)  # View all goals
print(_FUNDING_STORE)  # View all funding allocations
```

3. **Test Milestone Logic**
```python
# Manually check milestones
newly_reached = await manager.check_milestones(goal_id)
print(f"Newly reached: {newly_reached}")

# View all milestones
goal = await manager.get_goal(goal_id)
print(f"Milestones: {goal['milestones']}")
```

---

## Related Documentation

- **Analytics**: `src/fin_infra/docs/analytics.md` - Cash flow and savings rate for goal recommendations
- **Budgets**: `src/fin_infra/docs/budgets.md` - Budget categories linked to savings goals
- **Net Worth**: `src/fin_infra/docs/net-worth.md` - Net worth tracking for wealth milestone goals
- **ADR**: `src/fin_infra/docs/adr/0025-goals-module-refactoring.md` - Architecture decisions

---

## Summary

Goals module provides comprehensive financial goal tracking with:
- ✅ 6 goal types (savings, debt, investment, net_worth, income, custom)
- ✅ 4 lifecycle statuses (active, paused, completed, abandoned)
- ✅ Milestone tracking with auto-completion
- ✅ Multi-account funding allocation with validation
- ✅ Progress monitoring with projected completion dates
- ✅ 13 REST API endpoints for full CRUD operations
- ✅ 116 tests (84 unit + 32 integration, 2 skipped)
- ✅ Generic design for ANY fintech application

Perfect for personal finance apps, wealth management platforms, banking apps, budgeting tools, and investment platforms.
