# Unified Insights Feed

**Status**: ✅ Production-ready (Phase 3)  
**Module**: `fin_infra.insights`  
**Dependencies**: svc-infra (cache, logging), ai-infra (LLM for crypto insights)

---

## Overview

The Unified Insights Feed aggregates personalized financial insights from multiple sources into a single, priority-ranked feed. It surfaces actionable intelligence from:

- **Net Worth Tracking**: Significant changes, milestones, allocation shifts
- **Budget Management**: Overspending alerts, category warnings, spending patterns
- **Goal Progress**: Milestone achievements, progress updates, deadline warnings
- **Recurring Patterns**: Subscription changes, unexpected charges, trend analysis
- **Portfolio Analytics**: Asset allocation, rebalancing opportunities, risk metrics
- **Tax Optimization**: Estimated liabilities, document reminders, deduction opportunities
- **Crypto Holdings**: AI-powered portfolio analysis, market insights, risk assessments

The feed uses **priority-based filtering** and **category-based organization** to ensure users see the most important insights first.

---

## Architecture

### Core Components

```
src/fin_infra/insights/
├── models.py          # Pydantic models: Insight, InsightFeed
├── aggregator.py      # Multi-source aggregation logic
├── __init__.py        # Public API: aggregate_insights()
└── README.md          # Module documentation
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    aggregate_insights()                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
  [Net Worth]    [Budgets]      [Goals]
  [Recurring]    [Portfolio]    [Tax]
  [Crypto]
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
            ┌──────────────────┐
            │ Priority Sorting │
            │ (CRITICAL → LOW) │
            └────────┬─────────┘
                     │
                     ▼
           ┌─────────────────┐
           │  InsightFeed    │
           │ (paginated)     │
           └─────────────────┘
```

---

## Data Models

### `Insight` (Pydantic BaseModel)

```python
from fin_infra.insights.models import Insight, InsightPriority, InsightCategory

insight = Insight(
    id="unique_id",
    user_id="user_123",
    category=InsightCategory.GOAL,
    priority=InsightPriority.HIGH,
    title="Goal 'Emergency Fund' Achieved!",
    description="You've reached your $10,000 goal",
    action="Consider setting a new goal or increasing this one",
    value=Decimal("10000.00"),
    metadata={"goal_id": "goal_456"},
    expires_at=None,  # Optional: auto-expire insight after date
    created_at=datetime.now(),
)
```

**Fields**:
- `id` (str): Unique identifier (e.g., `"goal_456_1706345123.456"`)
- `user_id` (str): User identifier
- `category` (InsightCategory): One of 8 categories (see below)
- `priority` (InsightPriority): CRITICAL, HIGH, MEDIUM, LOW
- `title` (str): Short headline (max 100 chars)
- `description` (str): Detailed explanation (max 500 chars)
- `action` (str | None): Recommended next step (optional, max 200 chars)
- `value` (Decimal | None): Associated numeric value (optional)
- `metadata` (dict | None): Additional context (optional)
- `expires_at` (datetime | None): Auto-expire timestamp (optional)
- `created_at` (datetime): Creation timestamp (auto-set)

### `InsightCategory` (Enum)

```python
class InsightCategory(str, Enum):
    """Insight category for organization."""
    
    NET_WORTH = "net_worth"         # Net worth changes, allocation shifts
    BUDGET = "budget"               # Budget tracking, overspending alerts
    GOAL = "goal"                   # Goal progress, milestones
    RECURRING = "recurring"         # Subscription changes, recurring patterns
    PORTFOLIO = "portfolio"         # Asset allocation, rebalancing
    TAX = "tax"                     # Tax liabilities, deductions
    OPPORTUNITY = "opportunity"     # Financial opportunities (unused)
    ALERT = "alert"                 # Urgent notifications (unused)
```

**Usage**: Filter insights by category to show domain-specific feeds (e.g., "Budget Insights", "Portfolio Insights").

### `InsightPriority` (Enum)

```python
class InsightPriority(str, Enum):
    """Priority level for sorting."""
    
    CRITICAL = "critical"  # Urgent action required (e.g., overdraft risk)
    HIGH = "high"          # Important but not urgent (e.g., goal achieved)
    MEDIUM = "medium"      # Nice to know (e.g., 50% goal progress)
    LOW = "low"            # Informational (e.g., spending trends)
```

**Sorting**: Insights are always sorted CRITICAL → HIGH → MEDIUM → LOW (newest first within priority).

### `InsightFeed` (Pydantic BaseModel)

```python
from fin_infra.insights.models import InsightFeed

feed = InsightFeed(
    user_id="user_123",
    insights=[insight1, insight2, insight3],
    total=150,
    page=1,
    page_size=20,
    has_more=True,
)
```

**Fields**:
- `user_id` (str): User identifier
- `insights` (list[Insight]): Current page of insights
- `total` (int): Total count of insights (all priorities)
- `page` (int): Current page number (1-indexed)
- `page_size` (int): Number of insights per page
- `has_more` (bool): True if more pages exist

**Pagination**: Supports server-side pagination with configurable page size (default: 20).

---

## Public API

### `aggregate_insights()`

**Main entry point** for generating a unified insights feed from multiple financial data sources.

```python
from fin_infra.insights import aggregate_insights

feed = aggregate_insights(
    user_id="user_123",
    net_worth_snapshots=[snapshot1, snapshot2],
    budgets=[budget1, budget2],
    goals=[goal1, goal2],
    recurring_patterns=[pattern1, pattern2],
    portfolio_data={"positions": [...], "benchmarks": [...]},
    tax_data={"liabilities": [...], "documents": [...]},
    crypto_holdings=[holding1, holding2],
    priority_filter="high",  # Optional: filter by priority (high, medium, low, critical)
    page=1,
    page_size=20,
)

# Access insights
for insight in feed.insights:
    print(f"[{insight.priority}] {insight.title}: {insight.description}")
```

**Parameters**:
- `user_id` (str): User identifier (required)
- `net_worth_snapshots` (list[NetWorthSnapshot] | None): Net worth history (optional)
- `budgets` (list[Budget] | None): Active budgets (optional)
- `goals` (list[Goal] | None): Financial goals (optional)
- `recurring_patterns` (list[RecurringPattern] | None): Subscription/bill patterns (optional)
- `portfolio_data` (dict | None): Portfolio analytics data (optional)
- `tax_data` (dict | None): Tax-related data (optional)
- `crypto_holdings` (list[CryptoHolding] | None): Crypto portfolio (optional)
- `priority_filter` (str | None): Filter by priority level (optional)
- `page` (int): Page number (1-indexed, default: 1)
- `page_size` (int): Items per page (default: 20)

**Returns**: `InsightFeed` with paginated insights sorted by priority

**Example - Minimal Usage**:
```python
# Get high-priority insights only
feed = aggregate_insights(
    user_id="user_123",
    goals=[goal1, goal2],
    priority_filter="high",
)
```

**Example - Full Integration**:
```python
from fin_infra.insights import aggregate_insights
from fin_infra.networth import calculate_net_worth
from fin_infra.budgets import get_budgets
from fin_infra.goals import get_goals
from fin_infra.recurring import detect_recurring_patterns

# Gather data from various modules
net_worth_snapshots = calculate_net_worth(user_id="user_123")
budgets = get_budgets(user_id="user_123")
goals = get_goals(user_id="user_123")
recurring_patterns = detect_recurring_patterns(user_id="user_123")

# Generate unified feed
feed = aggregate_insights(
    user_id="user_123",
    net_worth_snapshots=net_worth_snapshots,
    budgets=budgets,
    goals=goals,
    recurring_patterns=recurring_patterns,
    page=1,
    page_size=50,
)

# Use insights in UI
print(f"Total insights: {feed.total}")
print(f"Showing: {len(feed.insights)} (page {feed.page}/{(feed.total + feed.page_size - 1) // feed.page_size})")
```

---

## Insight Generation Logic

### Net Worth Insights

**Generated from**: `net_worth_snapshots` parameter  
**Category**: `InsightCategory.NET_WORTH`

**Logic**:
1. **Significant Changes** (>5% month-over-month):
   - **Priority**: HIGH (if positive change), MEDIUM (if negative)
   - **Title**: "Net Worth Up 12% This Month" or "Net Worth Down 8% This Month"
   - **Description**: "$150,000 → $168,000 (+$18,000)"
   - **Action**: "Review spending patterns" (if negative) or "Keep up the momentum" (if positive)
   - **Value**: Change amount (e.g., `Decimal("18000.00")`)

**Example**:
```python
net_worth_snapshots = [
    NetWorthSnapshot(date=date(2025, 1, 1), total=Decimal("150000")),
    NetWorthSnapshot(date=date(2025, 2, 1), total=Decimal("168000")),
]

feed = aggregate_insights(user_id="user_123", net_worth_snapshots=net_worth_snapshots)
# Output: "Net Worth Up 12% This Month" (HIGH priority)
```

### Budget Insights

**Generated from**: `budgets` parameter  
**Category**: `InsightCategory.BUDGET`

**Logic**: Currently **stub implementation** (no insights generated yet). Production would:
1. Compare actual spending vs budget limits
2. Trigger overspending alerts (CRITICAL priority if >100% spent)
3. Warn about approaching limits (HIGH priority if >80% spent)

**Future Enhancement**:
```python
# Planned logic (NOT YET IMPLEMENTED)
if spent / budget_limit > 1.0:
    priority = InsightPriority.CRITICAL
    title = f"Budget Exceeded: {category}"
elif spent / budget_limit > 0.8:
    priority = InsightPriority.HIGH
    title = f"Approaching Budget Limit: {category}"
```

### Goal Insights

**Generated from**: `goals` parameter  
**Category**: `InsightCategory.GOAL`

**Logic**:
1. **Goal Achieved** (progress ≥100%):
   - **Priority**: HIGH
   - **Title**: "Goal '{goal.name}' Achieved!"
   - **Description**: "You've reached your ${target:,.2f} goal"
   - **Action**: "Consider setting a new goal or increasing this one"
   - **Value**: Current amount (Decimal)

2. **Goal Milestone** (progress ≥75%):
   - **Priority**: MEDIUM
   - **Title**: "Goal '{goal.name}' Almost There"
   - **Description**: "${current:,.2f} of ${target:,.2f} saved ({pct:.0f}%)"
   - **Action**: "${remaining:,.2f} more to reach your goal"
   - **Value**: Current amount (Decimal)

**Example**:
```python
goals = [
    Goal(
        id="goal_123",
        name="Emergency Fund",
        target_amount=10000.0,
        current_amount=10500.0,  # 105% achieved
    ),
    Goal(
        id="goal_456",
        name="Down Payment",
        target_amount=50000.0,
        current_amount=38000.0,  # 76% achieved
    ),
]

feed = aggregate_insights(user_id="user_123", goals=goals)
# Output:
# 1. "Goal 'Emergency Fund' Achieved!" (HIGH)
# 2. "Goal 'Down Payment' Almost There" (MEDIUM)
```

### Recurring Pattern Insights

**Generated from**: `recurring_patterns` parameter  
**Category**: `InsightCategory.RECURRING`

**Logic**:
1. **Active Subscriptions**:
   - **Priority**: MEDIUM
   - **Title**: "Active Subscription: {pattern.description}"
   - **Description**: "{frequency.capitalize()} charge of ${amount:,.2f}"
   - **Action**: "Review if still needed"
   - **Value**: Amount (Decimal)

**Example**:
```python
recurring_patterns = [
    RecurringPattern(
        description="Netflix Premium",
        amount=Decimal("19.99"),
        frequency="monthly",
        confidence=0.95,
    ),
    RecurringPattern(
        description="Gym Membership",
        amount=Decimal("49.99"),
        frequency="monthly",
        confidence=0.88,
    ),
]

feed = aggregate_insights(user_id="user_123", recurring_patterns=recurring_patterns)
# Output:
# 1. "Active Subscription: Netflix Premium" (MEDIUM) - $19.99/month
# 2. "Active Subscription: Gym Membership" (MEDIUM) - $49.99/month
```

### Portfolio Insights

**Generated from**: `portfolio_data` parameter  
**Category**: `InsightCategory.PORTFOLIO`

**Logic**:
1. **Rebalancing Opportunities** (portfolio_data["opportunities"]):
   - **Priority**: HIGH
   - **Title**: Opportunity title from data
   - **Description**: Opportunity description
   - **Action**: Opportunity action
   - **Value**: Opportunity value (Decimal or None)

**Example**:
```python
portfolio_data = {
    "total_value": Decimal("250000"),
    "opportunities": [
        {
            "title": "Tech Stocks Overweight",
            "description": "Your tech allocation is 45% vs target 30%",
            "action": "Consider rebalancing to target allocation",
            "value": Decimal("37500"),  # Amount to rebalance
        }
    ],
}

feed = aggregate_insights(user_id="user_123", portfolio_data=portfolio_data)
# Output: "Tech Stocks Overweight" (HIGH) - Rebalance $37,500
```

### Tax Insights

**Generated from**: `tax_data` parameter  
**Category**: `InsightCategory.TAX`

**Logic**: Currently **stub implementation** (no insights generated yet). Production would:
1. Estimate tax liabilities based on income/gains
2. Remind about missing documents
3. Suggest deduction opportunities

**Future Enhancement**:
```python
# Planned logic (NOT YET IMPLEMENTED)
if estimated_liability > 10000:
    priority = InsightPriority.HIGH
    title = "Estimated Tax Liability: ${liability:,.2f}"
    action = "Consider quarterly estimated payments"
```

### Crypto Insights (AI-Powered)

**Generated from**: `crypto_holdings` parameter  
**Category**: `InsightCategory.PORTFOLIO` (crypto-specific)  
**Source**: `fin_infra.crypto.insights.generate_crypto_insights()` using ai-infra CoreLLM

**Logic** (See `crypto.md` for full details):
1. **Rule-Based Insights**:
   - **Allocation**: "Your portfolio is heavily concentrated in Bitcoin (65%). Consider diversifying."
   - **Performance**: "Ethereum has gained 15% this week - consider taking profits."

2. **AI-Powered Insights** (if LLM provided):
   - Uses `ai_infra.llm.CoreLLM` for intelligent portfolio analysis
   - Natural language recommendations with financial disclaimers
   - Example: "Crypto represents 15% of your total portfolio, which is aggressive but manageable. Ensure you have 6 months emergency fund in stable assets."

**Example**:
```python
from fin_infra.crypto.insights import CryptoHolding
from ai_infra.llm import CoreLLM

crypto_holdings = [
    CryptoHolding(
        symbol="BTC",
        quantity=Decimal("0.5"),
        market_value=Decimal("25000"),
        cost_basis=Decimal("20000"),
    ),
    CryptoHolding(
        symbol="ETH",
        quantity=Decimal("10"),
        market_value=Decimal("15000"),
        cost_basis=Decimal("12000"),
    ),
]

# AI-powered insights (requires LLM)
llm = CoreLLM()
feed = aggregate_insights(
    user_id="user_123",
    crypto_holdings=crypto_holdings,
    llm=llm,  # Enable AI insights
)
# Output: Mix of rule-based + AI insights
```

---

## Priority Filtering

### Priority Levels (Sorted High → Low)

1. **CRITICAL** (Urgent action required):
   - Overdraft risk
   - Budget exceeded
   - Goal deadline missed
   - Large unexpected charges

2. **HIGH** (Important, action recommended):
   - Goal achieved (milestone celebration)
   - Significant net worth change (>5%)
   - Rebalancing opportunities
   - Tax deadlines approaching

3. **MEDIUM** (Nice to know, optional action):
   - Goal progress (50-75%)
   - Subscription reminders
   - Spending trends
   - Allocation recommendations

4. **LOW** (Informational):
   - General financial tips
   - Historical comparisons
   - Minor optimizations

### Using Priority Filters

```python
# Get only CRITICAL insights
feed = aggregate_insights(user_id="user_123", goals=goals, priority_filter="critical")

# Get HIGH + CRITICAL (most common use case)
feed = aggregate_insights(user_id="user_123", goals=goals, priority_filter="high")

# Get all insights (no filter)
feed = aggregate_insights(user_id="user_123", goals=goals)
```

**Filter Behavior**:
- `priority_filter="critical"`: Only CRITICAL insights
- `priority_filter="high"`: HIGH + CRITICAL insights
- `priority_filter="medium"`: MEDIUM + HIGH + CRITICAL insights
- `priority_filter="low"`: All insights (LOW + MEDIUM + HIGH + CRITICAL)
- `priority_filter=None`: All insights (default)

---

## Pagination

### Server-Side Pagination

```python
# Page 1 (first 20 insights)
feed_page1 = aggregate_insights(user_id="user_123", goals=goals, page=1, page_size=20)
print(f"Total: {feed_page1.total}, Has More: {feed_page1.has_more}")

# Page 2 (next 20 insights)
feed_page2 = aggregate_insights(user_id="user_123", goals=goals, page=2, page_size=20)

# Calculate total pages
total_pages = (feed_page1.total + feed_page1.page_size - 1) // feed_page1.page_size
```

**Pagination Details**:
- **Default page_size**: 20 insights per page
- **Page numbering**: 1-indexed (page=1 is first page)
- **has_more**: Boolean indicating if more pages exist
- **total**: Total count of insights (all pages)

### Mobile-Friendly Pagination

```python
# Load more pattern (append to existing list)
all_insights = []
page = 1
page_size = 10

while True:
    feed = aggregate_insights(user_id="user_123", goals=goals, page=page, page_size=page_size)
    all_insights.extend(feed.insights)
    
    if not feed.has_more:
        break
    
    page += 1

print(f"Loaded {len(all_insights)} total insights")
```

---

## Integration Examples

### Example 1: Dashboard Widget

**Use Case**: Show top 5 high-priority insights on dashboard

```python
from fin_infra.insights import aggregate_insights
from fin_infra.goals import get_goals

goals = get_goals(user_id="user_123")

feed = aggregate_insights(
    user_id="user_123",
    goals=goals,
    priority_filter="high",  # HIGH + CRITICAL only
    page=1,
    page_size=5,  # Top 5 insights
)

# Render in UI
for insight in feed.insights:
    print(f"🔔 [{insight.priority}] {insight.title}")
    print(f"   {insight.description}")
    if insight.action:
        print(f"   ➡️ {insight.action}")
```

**Output**:
```
🔔 [HIGH] Goal 'Emergency Fund' Achieved!
   You've reached your $10,000 goal
   ➡️ Consider setting a new goal or increasing this one

🔔 [HIGH] Net Worth Up 12% This Month
   $150,000 → $168,000 (+$18,000)
   ➡️ Keep up the momentum
```

### Example 2: Full Insights Feed Page

**Use Case**: Dedicated insights page with all categories

```python
from fin_infra.insights import aggregate_insights

# Gather all data sources
net_worth = get_net_worth_snapshots(user_id="user_123")
budgets = get_budgets(user_id="user_123")
goals = get_goals(user_id="user_123")
recurring = detect_recurring_patterns(user_id="user_123")
portfolio = get_portfolio_analytics(user_id="user_123")
crypto = get_crypto_holdings(user_id="user_123")

# Generate comprehensive feed
feed = aggregate_insights(
    user_id="user_123",
    net_worth_snapshots=net_worth,
    budgets=budgets,
    goals=goals,
    recurring_patterns=recurring,
    portfolio_data=portfolio,
    crypto_holdings=crypto,
    page=1,
    page_size=50,
)

# Group by category for UI organization
insights_by_category = {}
for insight in feed.insights:
    category = insight.category
    if category not in insights_by_category:
        insights_by_category[category] = []
    insights_by_category[category].append(insight)

# Render each category section
for category, insights in insights_by_category.items():
    print(f"\n## {category.upper()} ({len(insights)} insights)")
    for insight in insights:
        print(f"  - {insight.title}")
```

### Example 3: Real-Time Notifications

**Use Case**: Send push notifications for CRITICAL insights

```python
from fin_infra.insights import aggregate_insights
from svc_infra.webhooks import send_webhook

# Check for CRITICAL insights
feed = aggregate_insights(
    user_id="user_123",
    budgets=budgets,
    priority_filter="critical",
    page_size=100,
)

# Send notifications
for insight in feed.insights:
    send_webhook(
        event="insight.critical",
        payload={
            "user_id": insight.user_id,
            "title": insight.title,
            "description": insight.description,
            "action": insight.action,
        }
    )
```

### Example 4: Caching with svc-infra

**Use Case**: Cache insights feed for 5 minutes to reduce computation

```python
from svc_infra.cache import cache_read, cache_write
from fin_infra.insights import aggregate_insights

@cache_read(suffix="insights_feed", ttl=300)  # 5 minutes
def get_insights_feed(user_id: str, page: int = 1, page_size: int = 20):
    """Get cached insights feed."""
    # Gather data (these could also be cached separately)
    goals = get_goals(user_id=user_id)
    budgets = get_budgets(user_id=user_id)
    
    return aggregate_insights(
        user_id=user_id,
        goals=goals,
        budgets=budgets,
        page=page,
        page_size=page_size,
    )

# First call: generates insights and caches
feed1 = get_insights_feed(user_id="user_123")  # Cache MISS, computed

# Second call within 5 minutes: returns cached result
feed2 = get_insights_feed(user_id="user_123")  # Cache HIT, instant
```

---

## Production Considerations

### Performance Optimization

1. **Cache Individual Data Sources**:
   ```python
   @cache_read(suffix="goals", ttl=600)
   def get_goals(user_id: str):
       return query_goals_from_db(user_id)
   ```

2. **Parallel Data Fetching**:
   ```python
   import asyncio
   
   async def gather_data(user_id: str):
       goals, budgets, recurring = await asyncio.gather(
           fetch_goals(user_id),
           fetch_budgets(user_id),
           fetch_recurring(user_id),
       )
       return goals, budgets, recurring
   ```

3. **Incremental Updates** (Future):
   - Track last viewed timestamp
   - Only generate insights for new data since last view
   - Mark insights as "read" to hide from feed

### Monitoring & Logging

```python
from svc_infra.logging import setup_logging

setup_logging()

# Logs are automatically structured
feed = aggregate_insights(user_id="user_123", goals=goals)
# Log output:
# INFO: Generated 15 insights for user_123 (priorities: 2 HIGH, 8 MEDIUM, 5 LOW)
```

### Error Handling

```python
try:
    feed = aggregate_insights(user_id="user_123", goals=goals)
except Exception as e:
    # Log error and return empty feed
    logger.error(f"Failed to generate insights: {e}")
    feed = InsightFeed(user_id="user_123", insights=[], total=0, page=1, page_size=20)
```

### Data Validation

All models use **Pydantic V2** for automatic validation:

```python
from pydantic import ValidationError

try:
    insight = Insight(
        id="insight_123",
        user_id="user_123",
        category="INVALID_CATEGORY",  # ❌ Not in InsightCategory enum
        priority=InsightPriority.HIGH,
        title="Test",
        description="Test insight",
    )
except ValidationError as e:
    print(e.errors())
    # Output: [{'type': 'enum', 'loc': ('category',), 'msg': '...'}]
```

---

## Testing

### Unit Tests

```python
# tests/unit/insights/test_aggregator.py
from fin_infra.insights import aggregate_insights
from fin_infra.goals import Goal

def test_goal_achieved_insight():
    """Test HIGH priority insight for achieved goal."""
    goals = [
        Goal(
            id="goal_123",
            name="Emergency Fund",
            target_amount=10000.0,
            current_amount=10500.0,
        )
    ]
    
    feed = aggregate_insights(user_id="user_123", goals=goals)
    
    assert len(feed.insights) == 1
    assert feed.insights[0].priority == "high"
    assert "Achieved" in feed.insights[0].title
    assert feed.insights[0].category == "goal"

def test_priority_filtering():
    """Test priority filter behavior."""
    goals = [
        Goal(id="g1", name="G1", target_amount=100, current_amount=100),  # HIGH
        Goal(id="g2", name="G2", target_amount=100, current_amount=75),   # MEDIUM
    ]
    
    # Filter for HIGH only
    feed_high = aggregate_insights(user_id="u123", goals=goals, priority_filter="high")
    assert len(feed_high.insights) == 1
    assert feed_high.insights[0].priority == "high"
    
    # No filter: all insights
    feed_all = aggregate_insights(user_id="u123", goals=goals)
    assert len(feed_all.insights) == 2

def test_pagination():
    """Test pagination logic."""
    goals = [Goal(id=f"g{i}", name=f"G{i}", target_amount=100, current_amount=100) for i in range(50)]
    
    # Page 1
    feed_p1 = aggregate_insights(user_id="u123", goals=goals, page=1, page_size=20)
    assert len(feed_p1.insights) == 20
    assert feed_p1.has_more is True
    assert feed_p1.total == 50
    
    # Page 3 (last page)
    feed_p3 = aggregate_insights(user_id="u123", goals=goals, page=3, page_size=20)
    assert len(feed_p3.insights) == 10
    assert feed_p3.has_more is False
```

### Integration Tests

```python
# tests/integration/test_insights_api.py
from fastapi.testclient import TestClient
from your_app import app

client = TestClient(app)

def test_insights_endpoint():
    """Test FastAPI insights endpoint (future integration)."""
    response = client.get("/insights?user_id=user_123&page=1&page_size=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "insights" in data
    assert "total" in data
    assert data["page"] == 1
```

---

## Future Enhancements

### Phase 4: Advanced Features

1. **Smart Notifications**:
   - ML-based timing optimization (send insights when user is most engaged)
   - Deduplication (don't repeat similar insights)
   - User preference learning (suppress low-priority categories)

2. **Interactive Insights**:
   - Quick actions (e.g., "Mark as Read", "Remind Me Later", "Complete Goal")
   - Insight feedback (thumbs up/down to improve relevance)

3. **Personalization**:
   - User-specific thresholds (some users want 1% net worth changes, others 10%)
   - Custom categories (e.g., "Travel Savings", "Home Improvement")

4. **Expanded Tax Insights**:
   - Estimate tax liabilities based on YTD income
   - Suggest tax-loss harvesting opportunities
   - Remind about document upload deadlines

5. **Expanded Budget Insights**:
   - Overspending alerts (CRITICAL if >100%)
   - Category-specific warnings (HIGH if >80%)
   - Spending trend analysis (MEDIUM if 20% above average)

6. **Multi-Language Support**:
   - Localized insight titles/descriptions
   - Region-specific financial advice

---

## FAQ

**Q: How do I enable AI-powered crypto insights?**  
A: Pass a `CoreLLM` instance from ai-infra when calling `aggregate_insights()`. See `crypto.md` for details.

**Q: Can I filter insights by category?**  
A: Not directly in `aggregate_insights()`, but you can filter the returned `insights` list by `insight.category`.

**Q: How do I mark insights as read?**  
A: This feature is planned for Phase 4. Currently, insights have no read/unread state.

**Q: What if I don't have data for all sources?**  
A: Pass `None` for any optional parameter (net_worth_snapshots, budgets, etc.). Only provided data sources will generate insights.

**Q: How do I customize priority thresholds?**  
A: Priority logic is currently hardcoded in aggregator.py. Customization is planned for Phase 4 (user preferences).

**Q: Can I add custom insight categories?**  
A: Not currently. The 8 categories (NET_WORTH, BUDGET, GOAL, RECURRING, PORTFOLIO, TAX, OPPORTUNITY, ALERT) are fixed. Custom categories are planned for Phase 4.

**Q: How do I integrate with svc-infra caching?**  
A: Wrap `aggregate_insights()` with `@cache_read()` or cache individual data sources (goals, budgets, etc.). See "Integration Examples" section.

**Q: Are insights persisted to a database?**  
A: No. Insights are generated on-demand from current data. Database persistence is planned for Phase 4 (read/unread tracking, insight history).

---

## Related Documentation

- **Crypto Insights**: `crypto.md` (AI-powered crypto portfolio analysis)
- **Analytics**: `analytics.md` (rebalancing, scenario modeling)
- **Net Worth**: `networth.md` (net worth tracking)
- **Budgets**: `budgets.md` (budget management)
- **Goals**: `goals.md` (goal tracking)
- **Recurring Patterns**: `recurring.md` (subscription detection)
- **svc-infra Cache**: `svc-infra/docs/cache.md` (caching strategies)
- **ai-infra LLM**: `ai-infra/docs/llm.md` (CoreLLM usage)

---

**Last Updated**: 2025-01-27  
**Module Version**: Phase 3 (Production-ready)  
**Test Coverage**: 15 unit tests (aggregator logic, priority sorting, pagination)
