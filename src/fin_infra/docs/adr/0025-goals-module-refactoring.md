# ADR-0025: Goals Module Refactoring and Expansion

**Status**: Accepted
**Date**: 2025-11-09
**Authors**: fin-infra team

## Context

The existing goals module (Section 17 V2) provided LLM-powered goal validation and progress tracking for 4 goal types (retirement, home purchase, debt-free, wealth milestone). However, it lacked:
- CRUD operations for goal management
- Milestone tracking with checkpoints
- Funding allocation across multiple accounts
- FastAPI integration for REST API access
- Comprehensive test coverage
- Generic design for multiple fintech use cases

The refactoring aimed to transform goals into a production-ready module with full CRUD capabilities, flexible milestone tracking, multi-account funding allocation, and REST API endpoints suitable for ANY fintech application (personal finance, wealth management, banking, budgeting, investment platforms).

## svc-infra Reuse Assessment

**MANDATORY: Complete BEFORE proposing solution**

### What was checked in svc-infra?
- [x] Searched svc-infra README for related functionality
- [x] Reviewed svc-infra modules: api/fastapi, cache, jobs, logging, obs
- [x] Checked svc-infra docs: API scaffolding, dual routers, observability
- [x] Examined svc-infra source: src/svc_infra/api/fastapi/dual/, src/svc_infra/cache/

### Findings
- **Does svc-infra provide this functionality?** Partially
- **What svc-infra provides:**
  - FastAPI scaffolding and routing (dual routers for trailing slash handling)
  - Caching with Redis (cache_read, cache_write decorators)
  - Job scheduling for periodic tasks (easy_jobs)
  - Logging and observability (setup_logging, add_observability)
  - HTTP utilities (retry logic, timeout management)
- **What fin-infra must implement:**
  - Financial goal data models (Goal, Milestone, FundingSource)
  - Goal CRUD operations (create, read, update, delete)
  - Milestone tracking logic (auto-completion, progress calculation)
  - Funding allocation logic (validation, multi-account support)
  - Goal progress calculations (percent complete, projected dates)
  - REST API endpoints specific to goal management

### Classification
- [x] Type C: Hybrid (use svc-infra for infrastructure, fin-infra for financial domain logic)

### Reuse Plan
```python
# Backend infrastructure from svc-infra
from svc_infra.api.fastapi.ease import easy_service_app  # App creation
from svc_infra.logging import setup_logging  # Structured logging
from svc_infra.cache import init_cache, cache_read, cache_write  # Caching
from svc_infra.obs import add_observability  # Metrics and tracing

# Financial domain logic from fin-infra
from fin_infra.goals import add_goals, easy_goals  # Goal management
from fin_infra.goals.models import Goal, Milestone, FundingSource, GoalType, GoalStatus
from fin_infra.goals.management import FinancialGoalTracker
```

## Decision

### 1. Router Architecture: Plain APIRouter (Not user_router)

**Decision**: Use plain `fastapi.APIRouter` instead of svc-infra's `user_router` for goals endpoints.

**Rationale**:
- **Avoid Database Dependencies**: `user_router` requires database setup for authentication, adding unnecessary complexity for goals module testing and integration.
- **Match Budgets Pattern**: Budgets module successfully uses plain APIRouter; maintain consistency.
- **Future Migration Path**: Can upgrade to `user_router` when authentication is needed without changing core logic.

**Implementation**:
```python
# src/fin_infra/goals/add.py
from fastapi import APIRouter  # Plain router

def add_goals(app: FastAPI, manager=None, prefix="/goals"):
    router = APIRouter(prefix=prefix, tags=["Goal Management"])
    # Define endpoints...
    app.include_router(router, include_in_schema=True)
```

**Trade-offs**:
- ✅ Simpler testing (no database mock needed)
- ✅ Faster integration (no auth setup required)
- ✅ Consistent with budgets module
- ⚠️ No automatic authentication (must add manually when needed)
- ⚠️ No dual router trailing slash handling (but goals endpoints don't have this issue)

### 2. Data Models: Comprehensive Pydantic Schemas

**Decision**: Expand goal models to include 6 goal types, 4 statuses, milestone tracking, and funding sources.

**Goal Types**:
- `SAVINGS`: General savings (emergency fund, vacation, down payment)
- `DEBT`: Debt payoff (credit card, student loan)
- `INVESTMENT`: Investment targets (portfolio growth)
- `NET_WORTH`: Net worth milestones ($1M net worth)
- `INCOME`: Income goals (salary target, passive income)
- `CUSTOM`: Custom goal types

**Goal Statuses**:
- `ACTIVE`: In progress, being tracked
- `PAUSED`: Temporarily suspended
- `COMPLETED`: Target achieved
- `ABANDONED`: Goal given up

**Milestone Model**:
```python
class Milestone(BaseModel):
    amount: float  # Checkpoint amount
    target_date: Optional[datetime]  # Target date
    description: str  # Milestone description
    reached: bool = False  # Auto-set when current_amount > amount
    reached_date: Optional[datetime]  # Auto-set when reached
```

**Funding Source Model**:
```python
class FundingSource(BaseModel):
    account_id: str  # Linked account ID
    account_name: str  # Display name
    allocation_percent: float  # % of goal funded (0-100)
```

**Rationale**:
- **Generic Design**: 6 goal types cover diverse fintech use cases (personal finance, wealth management, banking)
- **Lifecycle Management**: 4 statuses support complete goal lifecycle (active → paused → completed/abandoned)
- **Progress Tracking**: Milestones provide checkpoint motivation and gamification opportunities
- **Flexible Funding**: Multi-account allocation supports complex scenarios (e.g., 60% savings + 40% checking)

### 3. Milestone Auto-Completion Logic

**Decision**: Milestones auto-mark as `reached=True` when `current_amount` exceeds `milestone.amount`.

**Implementation**:
```python
def check_milestones(goal_id: str) -> list[dict]:
    """Check and mark reached milestones. Returns newly reached milestones."""
    goal = get_goal(goal_id)
    newly_reached = []
    
    for milestone in goal.get("milestones", []):
        if not milestone["reached"] and goal["current_amount"] >= milestone["amount"]:
            milestone["reached"] = True
            milestone["reached_date"] = datetime.now()
            newly_reached.append(milestone)
    
    return newly_reached
```

**Rationale**:
- **Automation**: Reduces manual tracking burden
- **Real-time Updates**: Progress reflects immediately when current_amount updated
- **Motivation**: Users see checkpoints reached automatically
- **Flexible**: Can be triggered on-demand or scheduled via svc-infra jobs

**Trade-offs**:
- ✅ Automatic progress tracking
- ✅ Simplifies client logic
- ⚠️ Requires explicit `check_milestones()` call after amount updates (not fully automatic)

### 4. Funding Allocation Validation

**Decision**: Total allocation per goal must be ≤ 100%; no limit on total allocation per account across goals.

**Validation Logic**:
```python
def link_account_to_goal(goal_id: str, account_id: str, allocation_percent: float):
    funding = get_goal_funding(goal_id)
    total = sum(f["allocation_percent"] for f in funding)
    
    if total + allocation_percent > 100:
        raise ValueError("Total allocation would exceed 100%")
    
    # Link account...
```

**Example Scenarios**:
```python
# Valid: Multiple accounts fund one goal (total ≤ 100%)
link_account_to_goal(goal_id="emergency", account_id="savings", allocation_percent=60.0)
link_account_to_goal(goal_id="emergency", account_id="checking", allocation_percent=40.0)
# Total: 100% ✅

# Valid: One account funds multiple goals (no cross-goal limit)
link_account_to_goal(goal_id="emergency", account_id="savings", allocation_percent=60.0)
link_account_to_goal(goal_id="vacation", account_id="savings", allocation_percent=30.0)
link_account_to_goal(goal_id="down_payment", account_id="savings", allocation_percent=40.0)
# Total from savings across all goals: 130% ✅ (different goals)

# Invalid: Exceeds 100% for single goal
link_account_to_goal(goal_id="emergency", account_id="savings", allocation_percent=60.0)
link_account_to_goal(goal_id="emergency", account_id="checking", allocation_percent=50.0)
# Total: 110% ❌ ValueError
```

**Rationale**:
- **Per-Goal Limit**: Each goal can't have > 100% funding (logical constraint)
- **No Cross-Goal Limit**: Same account can fund multiple goals (realistic scenario)
- **Flexibility**: Users can allocate accounts as needed across priorities

### 5. Storage: In-Memory for Testing, External for Production

**Decision**: Use in-memory dictionaries for development/testing; production apps use svc-infra SQL/Mongo.

**Implementation**:
```python
# Development/Testing (goals/management.py)
_GOALS_STORE: dict[str, dict] = {}
_FUNDING_STORE: dict[str, list[dict]] = {}

# Production (via svc-infra)
from svc_infra.db import add_sql_db

app = easy_service_app(name="FinanceAPI")
add_sql_db(app, url="postgresql+asyncpg://localhost/mydb")
# Goals stored in SQL tables via SQLAlchemy models
```

**Rationale**:
- **Simple Testing**: No database setup required for unit/integration tests
- **Fast Iteration**: In-memory storage speeds up development
- **Production Ready**: svc-infra provides SQL/Mongo when needed
- **Clear Separation**: Test code doesn't depend on database infrastructure

### 6. API Design: 13 RESTful Endpoints

**Decision**: Provide comprehensive REST API with 13 endpoints grouped into CRUD, progress, milestones, and funding.

**Endpoint Structure**:
```
CRUD Operations (5 endpoints):
- POST   /goals                    - Create goal (201)
- GET    /goals                    - List goals with filters (200)
- GET    /goals/{goal_id}          - Get goal details (200/404)
- PATCH  /goals/{goal_id}          - Update goal (200/404)
- DELETE /goals/{goal_id}          - Delete goal (204/404)

Progress Tracking (1 endpoint):
- GET    /goals/{goal_id}/progress - Get progress (200/404)

Milestone Management (3 endpoints):
- POST   /goals/{goal_id}/milestones         - Add milestone (201/404)
- GET    /goals/{goal_id}/milestones         - List milestones (200/404)
- GET    /goals/{goal_id}/milestones/progress - Milestone progress (200/404)

Funding Allocation (4 endpoints):
- POST   /goals/{goal_id}/funding                  - Link account (201/400/404)
- GET    /goals/{goal_id}/funding                  - List funding (200/404)
- PATCH  /goals/{goal_id}/funding/{account_id}     - Update allocation (200/400/404)
- DELETE /goals/{goal_id}/funding/{account_id}     - Remove account (204/404)
```

**Rationale**:
- **RESTful Design**: Standard HTTP methods and status codes
- **Comprehensive**: All operations supported (no gaps)
- **Hierarchical**: Milestones and funding are sub-resources of goals
- **Consistent**: Matches analytics and budgets API patterns

## Consequences

### Positive
- ✅ **Production-Ready**: Full CRUD operations with REST API
- ✅ **Flexible Tracking**: Milestones and funding allocation for complex scenarios
- ✅ **Generic Design**: Works for ANY fintech application (personal finance, wealth management, banking, budgeting)
- ✅ **Comprehensive Testing**: 116 tests (84 unit + 32 integration, 2 skipped)
- ✅ **svc-infra Integration**: Uses svc-infra for logging, caching, observability (no duplication)
- ✅ **Consistent Patterns**: Matches budgets and analytics module designs
- ✅ **Clear Separation**: Financial logic in fin-infra, infrastructure in svc-infra

### Negative
- ⚠️ **No Built-In Auth**: Plain APIRouter requires manual authentication (can upgrade to user_router later)
- ⚠️ **Manual Milestone Checks**: Must call `check_milestones()` explicitly (not fully automatic)
- ⚠️ **In-Memory Storage**: Production apps must implement SQL/Mongo storage (svc-infra provides this)

### Neutral
- ℹ️ **6 Goal Types**: More than original 4, covers broader use cases
- ℹ️ **13 API Endpoints**: Comprehensive but requires more documentation
- ℹ️ **Allocation Validation**: Per-goal limit (≤100%) but no cross-goal limit

## Implementation Notes

### svc-infra Integration

**Required Imports**:
```python
# API Framework
from svc_infra.api.fastapi.ease import easy_service_app

# Logging
from svc_infra.logging import setup_logging

# Caching (optional, for goal queries)
from svc_infra.cache import init_cache, cache_read

# Observability
from svc_infra.obs import add_observability

# Jobs (future: scheduled milestone checks)
from svc_infra.jobs import easy_jobs
```

**Example Integration**:
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

# Optional: Schedule milestone checks (future)
# from svc_infra.jobs import easy_jobs
# worker, scheduler = easy_jobs(app, db_url="...")
# scheduler.add_job(check_all_milestones, trigger="interval", hours=24)
```

### fin-infra Implementation

**New Modules**:
- `src/fin_infra/goals/models.py`: Pydantic data models (Goal, Milestone, FundingSource, enums)
- `src/fin_infra/goals/management.py`: Core CRUD logic (create, read, update, delete, milestones, funding)
- `src/fin_infra/goals/add.py`: FastAPI integration (13 endpoints, router setup)
- `src/fin_infra/goals/__init__.py`: Public API exports (easy_goals, add_goals, models)

**Test Coverage**:
- `tests/unit/goals/test_management.py`: 27 tests (CRUD, filtering, validation)
- `tests/unit/goals/test_milestones.py`: 28 tests, 2 skipped (milestone logic, auto-completion)
- `tests/unit/goals/test_funding.py`: 29 tests (allocation logic, validation)
- `tests/integration/test_goals_api.py`: 32 tests (API endpoints, full lifecycle)

**Code Quality**:
- ✅ `ruff format` passes
- ✅ `ruff check` passes (no errors)
- ✅ `mypy` passes (full type coverage)

## References

- **Related ADRs**:
  - ADR-0023: Analytics Module Design (similar API pattern)
  - ADR-0024: Budget Management Design (uses plain APIRouter like goals)
- **svc-infra Modules**:
  - `src/svc_infra/api/fastapi/ease.py`: easy_service_app
  - `src/svc_infra/api/fastapi/dual/`: Dual routers (not used but available)
  - `src/svc_infra/cache/`: Caching decorators
- **External Docs**:
  - FastAPI docs: https://fastapi.tiangolo.com/
  - Pydantic docs: https://docs.pydantic.dev/

## Example Integrations

### Integration 1: Goals + Net Worth Tracking

```python
from fin_infra.net_worth import easy_net_worth
from fin_infra.goals import easy_goals, GoalType, GoalStatus

# Track net worth goal progress
net_worth_tracker = easy_net_worth()
goal_manager = easy_goals()

# Create net worth milestone goal
goal = await goal_manager.create_goal(
    user_id="user_123",
    name="$1M Net Worth",
    type=GoalType.NET_WORTH,
    target_amount=1000000.00,
    current_amount=750000.00,
    deadline=datetime(2028, 1, 1),
)

# Scheduled job: Update goal from net worth snapshots
async def update_net_worth_goals():
    snapshot = await net_worth_tracker.calculate_net_worth(user_id="user_123")
    current_net_worth = snapshot["net_worth"]
    
    # Update all net worth goals
    goals = await goal_manager.list_goals(user_id="user_123", type=GoalType.NET_WORTH)
    for goal in goals:
        await goal_manager.update_goal(
            goal_id=goal["id"],
            current_amount=current_net_worth,
        )
        
        # Check milestones
        await goal_manager.check_milestones(goal_id=goal["id"])
        
        # Mark completed if reached
        if current_net_worth >= goal["target_amount"]:
            await goal_manager.update_goal(
                goal_id=goal["id"],
                status=GoalStatus.COMPLETED,
            )

# Schedule with svc-infra jobs
from svc_infra.jobs import easy_jobs
worker, scheduler = easy_jobs(app, db_url="...")
scheduler.add_job(update_net_worth_goals, trigger="cron", hour=0)  # Daily at midnight
```

### Integration 2: Goals + Budget Savings

```python
from fin_infra.budgets import easy_budgets
from fin_infra.goals import easy_goals, GoalType

# Link savings goal to budget category
budget_tracker = easy_budgets()
goal_manager = easy_goals()

# Create vacation savings goal
goal = await goal_manager.create_goal(
    user_id="user_123",
    name="Hawaii Vacation",
    type=GoalType.SAVINGS,
    target_amount=5000.00,
    current_amount=0.00,
    deadline=datetime(2026, 6, 1),
)

# Create budget with vacation savings category
budget = await budget_tracker.create_budget(
    user_id="user_123",
    name="November 2025",
    categories={
        "Vacation Savings": 500.00,  # $500/month toward goal
        "Groceries": 600.00,
        "Restaurants": 200.00,
    },
    start_date=datetime(2025, 11, 1),
)

# Monthly job: Update goal from budget savings
async def update_savings_goals():
    # Get budget progress
    progress = await budget_tracker.get_budget_progress(budget_id=budget["id"])
    
    # Get amount saved in "Vacation Savings" category
    category_progress = progress["category_progress"]["Vacation Savings"]
    amount_saved = category_progress["spent"]  # For savings category, "spent" = saved
    
    # Update goal
    await goal_manager.update_goal(
        goal_id=goal["id"],
        current_amount=goal["current_amount"] + amount_saved,
    )
    
    # Check milestones
    await goal_manager.check_milestones(goal_id=goal["id"])

# Schedule with svc-infra jobs
from svc_infra.jobs import easy_jobs
worker, scheduler = easy_jobs(app, db_url="...")
scheduler.add_job(update_savings_goals, trigger="cron", day=1, hour=0)  # First of month
```

### Integration 3: Goals + Analytics Recommendations

```python
from fin_infra.analytics import easy_analytics
from fin_infra.goals import easy_goals

# Get savings rate to recommend goal contributions
analytics = easy_analytics()
goal_manager = easy_goals()

# Calculate user's savings rate
savings = await analytics.savings_rate(user_id="user_123", period="monthly")
monthly_savings = savings.monthly_savings_amount

# Get active goals
goals = await goal_manager.list_goals(user_id="user_123", status="active")

# Recommend allocation per goal
allocation_per_goal = monthly_savings / len(goals) if goals else 0

print(f"Monthly Savings: ${monthly_savings:,.2f}")
print(f"Active Goals: {len(goals)}")
print(f"Recommended per goal: ${allocation_per_goal:,.2f}")

# Update funding allocations based on recommendations
for goal in goals:
    # Calculate suggested monthly contribution
    progress = await goal_manager.get_goal_progress(goal_id=goal["id"])
    months_remaining = (goal["deadline"] - datetime.now()).days / 30
    required_monthly = (goal["target_amount"] - goal["current_amount"]) / months_remaining
    
    print(f"\nGoal: {goal['name']}")
    print(f"  Required monthly: ${required_monthly:,.2f}")
    print(f"  Available: ${allocation_per_goal:,.2f}")
    print(f"  Status: {'On track' if allocation_per_goal >= required_monthly else 'Need more'}")
```

## Migration Path

For teams upgrading from Section 17 V2 goals to refactored goals:

### Step 1: Update Imports
```python
# Before (Section 17 V2)
from fin_infra.goals.management import FinancialGoalTracker, GoalValidation, GoalProgressReport

# After (Refactored)
from fin_infra.goals import easy_goals, GoalType, GoalStatus
from fin_infra.goals.models import Goal, Milestone, FundingSource
```

### Step 2: Update Goal Creation
```python
# Before (Section 17 V2)
goal = {
    "type": "retirement",
    "target_amount": 2000000.0,
    "target_age": 65,
    "current_age": 40,
}
validation = await tracker.validate_goal(goal)

# After (Refactored)
goal = await manager.create_goal(
    user_id="user_123",
    name="Retirement Savings",
    type=GoalType.INVESTMENT,  # or GoalType.NET_WORTH
    target_amount=2000000.0,
    current_amount=300000.0,
    deadline=datetime(2050, 1, 1),
)
```

### Step 3: Update Progress Tracking
```python
# Before (Section 17 V2)
progress = await tracker.track_progress(goal, current_net_worth=575000.0)

# After (Refactored)
goal = await manager.update_goal(
    goal_id=goal["id"],
    current_amount=575000.0,
)
progress = await manager.get_goal_progress(goal_id=goal["id"])
```

### Step 4: Add Milestone Tracking (New Feature)
```python
# New in refactored goals
await manager.add_milestone(
    goal_id=goal["id"],
    amount=500000.0,
    description="Quarter million saved",
    target_date=datetime(2027, 1, 1),
)

await manager.check_milestones(goal_id=goal["id"])
```

### Step 5: Add Funding Allocation (New Feature)
```python
# New in refactored goals
await manager.link_account_to_goal(
    goal_id=goal["id"],
    account_id="401k_account",
    account_name="Employer 401k",
    allocation_percent=70.0,
)

await manager.link_account_to_goal(
    goal_id=goal["id"],
    account_id="ira_account",
    account_name="Roth IRA",
    allocation_percent=30.0,
)
```

## ADR Approval Checklist

- [x] svc-infra reuse assessment is complete and thorough
- [x] Classification (Type C: Hybrid) is clearly identified
- [x] svc-infra imports are documented (easy_service_app, setup_logging, init_cache, add_observability)
- [x] No duplication of svc-infra functionality (uses svc-infra for all infrastructure)
- [x] Integration examples provided (3 examples: net worth, budgets, analytics)
- [x] Migration path documented for Section 17 V2 users
- [x] Test coverage comprehensive (116 tests: 84 unit + 32 integration)
- [x] Code quality verified (ruff format, ruff check, mypy all passing)
