# ADR-0024: Budget Management Architecture

**Status**: Accepted  
**Date**: 2025-11-08  
**Deciders**: fin-infra team  
**Context**: Budget tracking with templates, alerts, and progress monitoring

## Context

Users need comprehensive budget management to control spending and achieve financial goals. Budget tracking must:
- Support multiple budget types (personal, household, business, project, custom)
- Work with various tracking periods (weekly, biweekly, monthly, quarterly, yearly)
- Provide pre-built templates for common budgeting strategies
- Track real-time spending progress with alerts
- Integrate seamlessly with transaction categorization
- Support rollover functionality for unused budget
- Provide REST API for application integration

**Use Cases**:
- **Personal Finance Apps**: Mint, YNAB, PocketGuard (budget tracking and spending limits)
- **Household Management**: Shared family budgets with category allocations
- **Business Expense Tracking**: Department budgets, project spending limits
- **Wealth Management**: Client budget planning and expense analysis
- **Banking Apps**: Built-in budgeting tools for account holders

**Current Limitations**:
- fin-infra has transaction categorization but no budget tracking
- No pre-built budget templates for common strategies
- No spending progress tracking or alert system
- svc-infra has infrastructure but no budget-specific logic

## Decision

Implement budget management with **4-layer architecture**:

### Layer 1: Budget CRUD Operations
Core database operations for budget lifecycle management.

**Components**:
- `BudgetTracker`: Main class for budget operations
- Database schema with async SQLAlchemy support
- Validation for budget types, periods, and categories
- Automatic end_date calculation based on period

**Database Schema**:
```python
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
    
    __table_args__ = (
        Index('idx_user_type', 'user_id', 'type'),
        Index('idx_user_period', 'user_id', 'start_date', 'end_date'),
    )
```

**Budget Types**:
- `PERSONAL`: Individual spending limits (most common use case)
- `HOUSEHOLD`: Shared family/roommate budgets (multi-user context)
- `BUSINESS`: Company/department budgets (small business accounting)
- `PROJECT`: Project-specific spending limits (freelancer projects, event planning)
- `CUSTOM`: User-defined classification (flexible for any use case)

**Budget Periods**:
- `WEEKLY`: 7-day cycles (Monday-Sunday by default)
- `BIWEEKLY`: 14-day cycles (aligns with biweekly paychecks)
- `MONTHLY`: Calendar month (most popular period, aligns with bills)
- `QUARTERLY`: 3-month periods (business quarterly budgets)
- `YEARLY`: 12-month periods (annual budgets, long-term planning)

**Period Calculation Algorithm**:
```python
def calculate_end_date(start_date: datetime, period: BudgetPeriod) -> datetime:
    if period == BudgetPeriod.WEEKLY:
        return start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif period == BudgetPeriod.BIWEEKLY:
        return start_date + timedelta(days=13, hours=23, minutes=59, seconds=59)
    elif period == BudgetPeriod.MONTHLY:
        # Last day of month
        next_month = start_date.replace(day=28) + timedelta(days=4)
        return next_month.replace(day=1) - timedelta(seconds=1)
    elif period == BudgetPeriod.QUARTERLY:
        # 3 months forward
        return (start_date + relativedelta(months=3)).replace(day=1) - timedelta(seconds=1)
    elif period == BudgetPeriod.YEARLY:
        # End of year
        return start_date.replace(month=12, day=31, hour=23, minute=59, second=59)
```

**CRUD Methods**:
```python
class BudgetTracker:
    async def create_budget(
        user_id: str,
        name: str,
        type: BudgetType,
        period: BudgetPeriod,
        categories: dict[str, float],
        start_date: Optional[datetime] = None,
        rollover_enabled: bool = False,
    ) -> Budget:
        """Create new budget with validation and ID generation"""
        
    async def get_budgets(
        user_id: str,
        type: Optional[BudgetType] = None
    ) -> list[Budget]:
        """List budgets with optional type filter"""
        
    async def get_budget(budget_id: str) -> Budget:
        """Get single budget by ID (raises ValueError if not found)"""
        
    async def update_budget(
        budget_id: str,
        updates: dict[str, Any]
    ) -> Budget:
        """Partial update of budget (name, categories, rollover_enabled)"""
        
    async def delete_budget(budget_id: str) -> None:
        """Delete budget (raises ValueError if not found)"""
        
    async def get_budget_progress(budget_id: str) -> BudgetProgress:
        """Calculate spending progress (TODO: integrate with categorization)"""
```

### Layer 2: Budget Templates
Pre-built budget allocations for common budgeting strategies.

**Template Design**:
Each template defines:
- **Percentages**: How income is allocated across categories
- **Category Groups**: Logical groupings (needs, wants, savings)
- **Description**: What the template is best suited for
- **Type**: Budget type (personal, business, etc.)
- **Period**: Recommended tracking period

**5 Core Templates**:

1. **50/30/20 Rule** (Most Popular):
   - 50% Needs: Housing, groceries, utilities, transportation, insurance
   - 30% Wants: Restaurants, entertainment, shopping, hobbies, travel
   - 20% Savings: Emergency fund, investments, debt paydown
   - **Use Case**: Balanced approach for stable income, recommended by financial experts

2. **Zero-Based Budget** (Every Dollar Assigned):
   - 60% Fixed Expenses: Rent, utilities, insurance, loan payments
   - 20% Variable Expenses: Groceries, gas, dining out
   - 10% Savings: Emergency fund, investments
   - 10% Discretionary: Fun money, hobbies, entertainment
   - **Use Case**: Total spending control, popular with YNAB users

3. **Envelope System** (Cash-Based Mentality):
   - 40% Bills: Rent, utilities, insurance, subscriptions
   - 30% Everyday Expenses: Groceries, gas, household items
   - 15% Savings: Emergency fund, goals
   - 15% Fun: Dining, entertainment, hobbies
   - **Use Case**: Visual spending limits, good for overspenders

4. **Pay Yourself First** (Savings Priority):
   - 30% Savings: High savings rate for financial independence
   - 40% Needs: Essential expenses
   - 20% Wants: Discretionary spending
   - 10% Giving: Charity, gifts, donations
   - **Use Case**: FIRE movement, aggressive savers, debt-free individuals

5. **Business Essentials** (Small Business/Freelancer):
   - 50% Operating Expenses: Rent, utilities, supplies, software
   - 20% Payroll: Salaries, contractor payments
   - 15% Marketing: Ads, website, content creation
   - 10% Savings: Business emergency fund
   - 5% Professional Services: Legal, accounting, consulting
   - **Use Case**: Small business owners, freelancers, startups

**Template Application**:
```python
async def apply_template(
    user_id: str,
    template_name: str,
    total_income: float,
    tracker: BudgetTracker,
    budget_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
) -> Budget:
    """
    Create budget from template by calculating category amounts.
    
    Algorithm:
    1. Load template metadata (percentages, categories, type, period)
    2. Calculate absolute amounts: category_amount = total_income * percentage
    3. Create Budget with calculated categories
    4. Return Budget instance
    """
    template = BUDGET_TEMPLATES[template_name]
    
    # Calculate category amounts
    categories = {
        category: round(total_income * (percentage / 100), 2)
        for category, percentage in template["categories"].items()
    }
    
    # Create budget
    return await tracker.create_budget(
        user_id=user_id,
        name=budget_name or f"{template['name']} - {datetime.now().strftime('%B %Y')}",
        type=template["type"],
        period=template["period"],
        categories=categories,
        start_date=start_date or datetime.now(),
        rollover_enabled=False,  # Default for templates
    )
```

### Layer 3: Budget Alerts & Progress Tracking
Real-time spending monitoring with configurable thresholds.

**Alert Thresholds**:
- **Warning** (80%): "Approaching budget limit" - Suggest reducing spending
- **Limit Reached** (100%): "Budget limit reached" - Stop optional spending
- **Overspending** (110%): "Overspending detected" - Review expenses, adjust budget

**Alert Logic**:
```python
class BudgetAlerts:
    def __init__(
        self,
        warning_threshold: float = 0.80,
        limit_threshold: float = 1.00,
        overspending_threshold: float = 1.10,
    ):
        self.warning_threshold = warning_threshold
        self.limit_threshold = limit_threshold
        self.overspending_threshold = overspending_threshold
    
    def check_budget(
        self,
        budget_id: str,
        spent_amount: float,
        budgeted_amount: float,
    ) -> list[BudgetAlert]:
        """Check if spending triggers any alerts"""
        alerts = []
        percent_used = spent_amount / budgeted_amount if budgeted_amount > 0 else 0
        
        if percent_used >= self.overspending_threshold:
            alerts.append(BudgetAlert(
                budget_id=budget_id,
                severity="critical",
                alert_type="overspending",
                message=f"Budget exceeded by {(percent_used - 1.0) * 100:.1f}%",
                percent_used=percent_used * 100,
            ))
        elif percent_used >= self.limit_threshold:
            alerts.append(BudgetAlert(
                budget_id=budget_id,
                severity="error",
                alert_type="limit_reached",
                message="Budget limit reached",
                percent_used=percent_used * 100,
            ))
        elif percent_used >= self.warning_threshold:
            alerts.append(BudgetAlert(
                budget_id=budget_id,
                severity="warning",
                alert_type="warning",
                message=f"Approaching budget limit ({percent_used * 100:.1f}%)",
                percent_used=percent_used * 100,
            ))
        
        return alerts
```

**Progress Calculation**:
```python
async def get_budget_progress(budget_id: str) -> BudgetProgress:
    """
    Calculate budget progress with category breakdown.
    
    Algorithm:
    1. Fetch budget from database
    2. TODO: Query transactions from categorization module
    3. Sum spent amounts per category
    4. Calculate remaining amounts and percentages
    5. Calculate period progress (days elapsed / total days)
    6. Return BudgetProgress with all metrics
    
    Note: Currently returns placeholder data. Full integration
    requires linking with transaction categorization module.
    """
    budget = await get_budget(budget_id)
    
    # TODO: Fetch actual spending data
    # transactions = await categorization.get_transactions(
    #     user_id=budget.user_id,
    #     start_date=budget.start_date,
    #     end_date=budget.end_date,
    # )
    # spent_by_category = calculate_spent_amounts(transactions)
    
    # Placeholder: Return 0 spent for now
    categories = [
        BudgetCategory(
            category_name=name,
            budgeted_amount=amount,
            spent_amount=0.0,  # TODO: Real data
            remaining_amount=amount,
            percent_used=0.0,
        )
        for name, amount in budget.categories.items()
    ]
    
    return BudgetProgress(
        budget_id=budget.id,
        current_period=budget.name,
        categories=categories,
        total_budgeted=sum(budget.categories.values()),
        total_spent=0.0,  # TODO: Real data
        total_remaining=sum(budget.categories.values()),
        percent_used=0.0,
        period_days_elapsed=calculate_days_elapsed(budget.start_date),
        period_days_total=calculate_period_days(budget.start_date, budget.end_date),
    )
```

### Layer 4: Easy Integration (Builder + FastAPI)
One-line setup for applications.

**Builder Pattern**:
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
    
    Features:
    - Automatic database URL from SQL_URL env var
    - Connection pooling with pre-ping (5 connections, 10 overflow)
    - Database-specific optimizations (PostgreSQL JIT off, SQLite thread safety)
    - 1-hour connection recycling
    
    Returns configured BudgetTracker ready for use.
    """
```

**FastAPI Integration**:
```python
def add_budgets(
    app: FastAPI,
    tracker: Optional[BudgetTracker] = None,
    db_url: Optional[str] = None,
    prefix: str = "/budgets",
) -> BudgetTracker:
    """
    Add budget management endpoints to FastAPI app.
    
    Features:
    - 8 REST endpoints (POST, GET list, GET single, PATCH, DELETE, progress, templates, from-template)
    - Automatic tracker creation via easy_budgets() if not provided
    - Stores tracker on app.state.budget_tracker
    - Registers scoped docs for landing page card
    - Returns tracker for programmatic access
    
    Endpoints:
    - POST /budgets: Create budget
    - GET /budgets: List budgets (filter by user_id, type)
    - GET /budgets/{budget_id}: Get single budget
    - PATCH /budgets/{budget_id}: Update budget (partial)
    - DELETE /budgets/{budget_id}: Delete budget (204 No Content)
    - GET /budgets/{budget_id}/progress: Get spending progress
    - GET /budgets/templates/list: List available templates
    - POST /budgets/from-template: Create from template
    """
```

## Consequences

### Positive

**Generic Design**:
- Works for ANY fintech application (personal finance, wealth management, business tools)
- Multiple budget types support different user contexts
- Flexible periods accommodate various pay schedules and planning horizons
- Custom type allows applications to define their own classifications

**Easy Integration**:
- `easy_budgets()` builder provides one-line setup with sensible defaults
- `add_budgets()` FastAPI helper mounts 8 REST endpoints automatically
- Pre-built templates eliminate manual category setup
- Clear separation: fin-infra (budget logic) + svc-infra (backend infrastructure)

**Extensibility**:
- Template system easily extensible (add new templates without code changes)
- Alert thresholds configurable per application
- Category structure flexible (any category names, any amounts)
- Database schema supports future enhancements (JSONB for metadata)

**Developer Experience**:
- Minimal code to get started (3-5 lines)
- Type-safe with full Pydantic models
- Comprehensive error messages (ValueError with context)
- Consistent patterns with other fin-infra modules (net_worth, recurring, analytics)

### Negative

**Transaction Integration Pending**:
- Progress tracking currently returns placeholder data (spent_amount = 0)
- Requires integration with categorization module for real spending data
- Workaround: Applications can calculate spending externally and display alongside budgets

**No Built-in Automation**:
- Budget creation requires manual API calls (no auto-creation from templates)
- No automatic rollover processing (applications must handle rollover logic)
- No automatic period renewal (applications must create new budgets)
- Mitigation: Document clear patterns for automation; future versions can add jobs

**Limited Multi-User Support**:
- Household budgets stored with single user_id (no built-in sharing)
- No permission system for shared budgets (who can edit/delete)
- Workaround: Applications handle multi-user access control separately

**No Spending Data Source**:
- Budget progress depends on external transaction data
- No built-in connection to banking/brokerage providers
- Applications must wire categorization → budgets integration
- Future: Add helper function to auto-link transactions

### Trade-offs

**Plain APIRouter vs. user_router**:
- Decision: Use plain `APIRouter` instead of svc-infra's `user_router`
- Reason: `user_router` requires database setup for auth, complicates unit testing
- Impact: Applications must add authentication separately if needed
- Benefit: Simpler testing, no auth dependencies in unit tests

**Rollover as Optional Feature**:
- Decision: Rollover disabled by default, opt-in per budget
- Reason: Not all budgeting strategies support rollover (zero-based budgets reset)
- Impact: Users must explicitly enable rollover when creating budgets
- Benefit: Clear expectations, avoids confusion about unused budget

**Period End Date Calculation**:
- Decision: Automatically calculate end_date from start_date + period
- Reason: Eliminates manual date calculations, prevents errors
- Impact: Users cannot customize period length (e.g., 10-day budget)
- Benefit: Consistency, correctness (handles month boundaries, leap years)

**Category Structure as JSON**:
- Decision: Store categories as JSON dict instead of separate table
- Reason: Simpler schema, flexible category names, faster queries
- Impact: No foreign key constraints on categories, harder to query by category
- Benefit: Flexibility, performance, easier to refactor

## Implementation Notes

### Database Migrations

Required Alembic migration for budgets table:
```python
# alembic/versions/xxx_create_budgets_table.py
def upgrade():
    op.create_table(
        'budgets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('period', sa.String(), nullable=False),
        sa.Column('categories', sa.JSON(), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('rollover_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_user_type', 'user_id', 'type'),
        sa.Index('idx_user_period', 'user_id', 'start_date', 'end_date'),
    )
```

### Testing Strategy

**Unit Tests** (tests/unit/budgets/):
- `test_tracker.py`: CRUD operations, validation, error handling (25 tests)
- `test_alerts.py`: Alert thresholds, severity levels (15 tests)
- `test_templates.py`: Template loading, application, category calculations (24 tests)
- `test_ease.py`: Builder function, database configuration (27 tests)
- `test_add.py`: FastAPI endpoints, request/response models (21 tests)

**Integration Tests** (tests/integration/):
- `test_budgets_api.py`: Full API workflow with TestClient
- End-to-end budget lifecycle (create → list → update → delete)
- Template application workflow

**Acceptance Tests** (tests/acceptance/):
- Real database integration (PostgreSQL, SQLite)
- Multi-budget scenarios
- Rollover functionality

### Future Enhancements

**v1.1: Transaction Linking**:
- Integrate with categorization module for automatic spending tracking
- Real-time progress updates as transactions are categorized
- Historical spending comparison (current vs. previous periods)

**v1.2: Budget Sharing**:
- Multi-user access for household budgets
- Permission system (owner, editor, viewer)
- Activity log (who changed what, when)

**v1.3: Analytics & Insights**:
- Spending trends over time
- Category insights (overspending patterns)
- Savings rate calculations
- Budget vs. actual reports

**v1.4: AI Recommendations**:
- LLM-powered budget suggestions based on spending patterns
- Anomaly detection (unusual spending spikes)
- Optimization recommendations (reallocate from underused categories)
- Goal-based budget adjustments

**v1.5: Automation**:
- Automatic budget creation from templates (scheduled jobs)
- Automatic period renewal (create next month's budget)
- Automatic rollover processing (end-of-period job)
- Webhook events for budget alerts

## References

- **Budget Module Code**: `src/fin_infra/budgets/`
- **Tests**: `tests/unit/budgets/`, `tests/integration/test_budgets_api.py`
- **Documentation**: `src/fin_infra/docs/budgets.md`
- **svc-infra**: Backend infrastructure (API, DB, cache, jobs)
- **Related ADRs**:
  - ADR-0018: Transaction Categorization
  - ADR-0020: Net Worth Tracking
  - ADR-0023: Analytics Module Design

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-06 | 5 budget types (personal, household, business, project, custom) | Cover all major use cases while keeping list manageable |
| 2025-11-06 | 5 budget periods (weekly, biweekly, monthly, quarterly, yearly) | Match common pay schedules and planning horizons |
| 2025-11-06 | 5 core templates (50/30/20, zero-based, envelope, pay-yourself-first, business) | Most popular budgeting strategies from financial literature |
| 2025-11-07 | Rollover as optional feature | Not all budgeting strategies support rollover |
| 2025-11-07 | Category structure as JSON dict | Flexibility and performance over relational structure |
| 2025-11-08 | Plain APIRouter instead of user_router | Simpler testing, no auth dependencies |
| 2025-11-08 | Progress tracking with placeholder data | Defer transaction integration to v1.1 |

## Acceptance Criteria

- [x] Budget CRUD operations work correctly (create, read, update, delete)
- [x] All 5 budget types supported (personal, household, business, project, custom)
- [x] All 5 budget periods supported with correct end_date calculation
- [x] 5 templates available and applicable with correct allocations
- [x] Alert system detects threshold violations (80%, 100%, 110%)
- [x] Progress tracking returns structured data (placeholder for v1.0)
- [x] Easy builder (`easy_budgets`) creates tracker with sensible defaults
- [x] FastAPI helper (`add_budgets`) mounts 8 REST endpoints
- [x] Unit tests passing (112+ tests across all modules)
- [x] Type checking clean (mypy passes)
- [x] Linting clean (ruff passes)
- [x] Documentation complete (budgets.md, ADR-0024)

## Status

**Accepted** ✅ - Implementation complete, all tests passing, documentation written.

**Next Steps**:
1. Deploy v1.0 with core CRUD and templates
2. Gather user feedback on template allocations
3. Plan v1.1 transaction integration with categorization module
4. Design multi-user budget sharing for v1.2
