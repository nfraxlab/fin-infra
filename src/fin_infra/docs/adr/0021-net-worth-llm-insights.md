# ADR-0021: LLM-Enhanced Net Worth Insights & Recommendations

**Status**: Accepted  
**Date**: 2025-11-07  
**Deciders**: Architecture Team  
**Related**: [ADR-0020: Net Worth Tracking](./0020-net-worth-tracking.md)

## Context

Net Worth Tracking V1 (Section 17) provides real-time calculation and historical snapshots, but users need:
1. **Actionable insights**: "What's driving my net worth changes?"
2. **Financial guidance**: "Should I pay off my mortgage early?"
3. **Goal tracking**: "Am I on track for retirement?"
4. **Personalized advice**: "How can I optimize my portfolio?"

LLMs can generate these insights, but we must:
- Use ai-infra for general LLM infrastructure (avoid duplication)
- Keep costs <$0.10/user/month (10× safety margin over $0.01 baseline)
- Provide graceful degradation when LLM is disabled
- Validate financial calculations (don't blindly trust LLM math)

## Decision

We will implement a **4-layer hybrid architecture** that combines fast V1 calculations with optional LLM insights:

### Layer 1: Real-time Net Worth Calculation (V1, Always Enabled)
- **Purpose**: Fast, deterministic net worth calculation
- **Latency**: <100ms (no LLM calls)
- **Cost**: $0/user/month (pure math)
- **Cache**: 1h TTL for current net worth

**API**:
```python
GET /net-worth/current
Response: {
  "total_net_worth": 575000.0,
  "total_assets": 620000.0,
  "total_liabilities": 45000.0,
  "change_from_previous": {"amount": 15000.0, "percent": 0.027},
  "last_updated": "2025-11-07T14:30:00Z"
}
```

### Layer 2: LLM Insights Generation (V2, On-Demand)
- **Purpose**: Generate natural language insights from net worth data
- **Latency**: 500-2000ms (LLM call)
- **Cost**: $0.042/user/month (24h cache, 1 generation/day)
- **Cache**: 24h TTL for insights

**Types**:
1. **Wealth Trends**: Analyze net worth changes over time
2. **Debt Reduction**: Prioritize debt payoff by APR (avalanche method)
3. **Goal Recommendations**: Validate financial goals and suggest paths
4. **Asset Allocation**: Portfolio rebalancing advice based on age/risk

**API**:
```python
GET /net-worth/insights?type=wealth_trends
Response: {
  "summary": "Net worth increased 15% ($75k) over 6 months, driven by investment gains.",
  "key_findings": [
    "Investment portfolio up $60k (strong market performance)",
    "Salary increase added $20k to savings",
    "New mortgage reduced net worth by $5k"
  ],
  "recommendations": [
    "Maintain current savings rate (20% of income)",
    "Rebalance portfolio if equity allocation exceeds 80%"
  ],
  "confidence": 0.92
}
```

### Layer 3: LLM Goal Tracking (V2, Weekly Check-Ins)
- **Purpose**: Validate goals, track progress, suggest course corrections
- **Latency**: Background job (via svc-infra.jobs)
- **Cost**: $0.0036/user/month (weekly check-ins)
- **Trigger**: Weekly scheduler (Sun 00:00 UTC) + on-demand via API

**Goal Types**:
1. **RetirementGoal**: Target amount, age, current savings, monthly contribution
2. **HomePurchaseGoal**: Home price, down payment %, target date, savings rate
3. **DebtFreeGoal**: Total debt, target date, monthly payment, weighted APR
4. **WealthMilestone**: Target net worth, target date, historical growth rate

**API**:
```python
POST /net-worth/goals
Request: {
  "type": "retirement",
  "target_amount": 2000000.0,
  "target_age": 65,
  "monthly_contribution": 1500.0
}
Response: {
  "goal_id": "retire_2050",
  "feasibility": "feasible",
  "required_monthly_savings": 1500.0,
  "projected_completion": "2050-01-01",
  "confidence": 0.89
}

GET /net-worth/goals/{goal_id}/progress
Response: {
  "status": "on_track",
  "current_progress": 0.38,
  "variance_from_target": 90,  # days ahead
  "recommendations": [...],
  "confidence": 0.91
}
```

### Layer 4: LLM Conversation (V2, Multi-Turn Q&A)

**⚠️ SCOPE UPDATE (2025-11-07)**: This layer has been **refactored to root-level** `src/fin_infra/conversation/` directory.

**Rationale**: Financial planning conversation is GENERAL (not net-worth-specific):
- Answers questions about: saving, budgeting, debt, refinancing, retirement, tax planning
- Uses net worth as ONE data source among many (also spending, income, goals, debt)
- Reusable across ALL fin-infra domains (budgeting, spending analysis, debt management)
- Follows svc-infra pattern: root-level primitives (cache, api, jobs) vs domain-specific (auth, payments)

**Architecture Boundary**:
- ✅ **Root-level** (`conversation/`): General financial Q&A, multi-turn context, safety filters
- ✅ **Domain-specific** (`net_worth/`): Net worth calculation, insights, goal tracking

See `src/fin_infra/conversation/` for full implementation.

---

**Original Layer 4 Specification** (now implemented in `conversation/`):

- **Purpose**: Answer financial planning questions with context
- **Latency**: 500-2000ms (LLM call)
- **Cost**: $0.018/user/month (2 conversations/month, 10 turns each)
- **Context**: Last 10 exchanges, current net worth, active goals

**Features**:
- Multi-turn context (remembers previous questions)
- Safety filters (refuse SSN, passwords, account numbers)
- Follow-up questions (clarifications, related topics)
- Source citations (net worth data, goal details)

**API**:
```python
POST /net-worth/conversation
Request: {
  "question": "How can I save more money each month?",
  "session_id": "conv_abc123"  # Optional, for multi-turn
}
Response: {
  "answer": "Based on your $60k net worth and $5k/month income, you're saving 15% ($750/month). To increase savings: (1) Reduce dining out from $400 to $200/month (+$200), (2) Cancel unused subscriptions ($50/month), (3) Refinance car loan from 8% to 5% (+$75/month). Total: +$325/month (21% savings rate).",
  "follow_up_questions": [
    "How do I refinance my car loan?",
    "What subscriptions should I cancel?",
    "Is 21% a good savings rate?"
  ],
  "confidence": 0.88,
  "sources": ["current_net_worth", "spending_analysis"]
}
```

**Implementation**: See `src/fin_infra/conversation/planning.py` for `FinancialPlanningConversation` class.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                              │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 1: Real-Time Net Worth Calculation (V1)               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ NetWorthAggregator                                      │  │
│  │ - Fetch balances from all providers (banking/brokerage)│  │
│  │ - Normalize currencies to USD                          │  │
│  │ - Calculate total assets - total liabilities           │  │
│  │ - Cache result (1h TTL)                                │  │
│  └────────────────────────────────────────────────────────┘  │
│  Latency: <100ms  |  Cost: $0                                │
└──────────────┬───────────────────────────────────────────────┘
               │
               ├─► If insights needed (Layer 2)
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 2: LLM Insights Generation (V2, Optional)             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ NetWorthInsightsGenerator                              │  │
│  │ - Input: Net worth snapshots (current + historical)    │  │
│  │ - LLM: ai-infra CoreLLM + structured output            │  │
│  │ - Output: Pydantic schema (WealthTrendAnalysis, etc.)  │  │
│  │ - Cache: 24h TTL                                       │  │
│  └────────────────────────────────────────────────────────┘  │
│  Latency: 500-2000ms  |  Cost: $0.042/user/month             │
└──────────────┬───────────────────────────────────────────────┘
               │
               ├─► If goal tracking needed (Layer 3)
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 3: LLM Goal Tracking (V2, Weekly Background)          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ FinancialGoalTracker                                    │  │
│  │ - Validate goals (required savings, timeline)          │  │
│  │ - Track progress (weekly check-ins via svc-infra.jobs)│  │
│  │ - Generate reports (GoalProgressReport)                │  │
│  │ - Course correction (if off-track)                     │  │
│  └────────────────────────────────────────────────────────┘  │
│  Latency: Background  |  Cost: $0.0036/user/month            │
└──────────────┬───────────────────────────────────────────────┘
               │
               ├─► If conversation needed (Layer 4)
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│  Layer 4: LLM Conversation (V2, Multi-Turn Q&A)              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ FinancialPlanningConversation                           │  │
│  │ - Context: Last 10 exchanges + net worth + goals       │  │
│  │ - Storage: svc-infra.cache (24h TTL)                   │  │
│  │ - Safety: Filter sensitive questions (SSN, passwords)  │  │
│  │ - Output: ConversationResponse + follow-ups            │  │
│  └────────────────────────────────────────────────────────┘  │
│  Latency: 500-2000ms  |  Cost: $0.018/user/month             │
└──────────────────────────────────────────────────────────────┘
```

## Implementation Details

### Structured Output Schemas

All LLM responses use Pydantic V2 for validation:

```python
from pydantic import BaseModel, Field

class WealthTrendAnalysis(BaseModel):
    summary: str = Field(..., description="1-2 sentence trend summary")
    period: str = Field(..., description="Time period analyzed")
    change_amount: float = Field(..., description="Net worth change in USD")
    change_percent: float = Field(..., description="Percentage change")
    primary_drivers: list[str] = Field(..., max_length=5)
    risk_factors: list[str] = Field(..., max_length=3)
    confidence: float = Field(..., ge=0.0, le=1.0)

class DebtReductionPlan(BaseModel):
    summary: str
    total_debt: float
    weighted_avg_apr: float
    payoff_order: list[DebtPayoffStep]
    estimated_interest_saved: float
    estimated_payoff_months: int
    confidence: float = Field(..., ge=0.0, le=1.0)

class GoalProgressReport(BaseModel):
    goal_id: str
    status: str = Field(..., description="on_track|ahead|behind|off_track")
    current_progress: float  # 0.0 to 1.0
    projected_completion: str  # ISO date
    variance_from_target: float  # Days ahead/behind
    recommendations: list[str]
    confidence: float = Field(..., ge=0.0, le=1.0)

class ConversationResponse(BaseModel):
    answer: str
    follow_up_questions: list[str] = Field(..., max_length=3)
    confidence: float = Field(..., ge=0.0, le=1.0)
    sources: list[str]  # Data sources used (net_worth, goals, etc.)
```

### ai-infra Integration

```python
from ai_infra.llm import CoreLLM

class NetWorthInsightsGenerator:
    def __init__(
        self,
        llm: CoreLLM,
        provider: str = "google",
        model_name: str = "gemini-2.0-flash-exp",
    ):
        self.llm = llm
        self.provider = provider
        self.model_name = model_name
    
    async def generate_wealth_trends(
        self,
        snapshots: list[NetWorthSnapshot],
    ) -> WealthTrendAnalysis:
        # Build structured output with Pydantic schema
        structured = self.llm.with_structured_output(
            provider=self.provider,
            model_name=self.model_name,
            schema=WealthTrendAnalysis,
            method="json_mode",
        )
        
        # Build prompt with few-shot examples
        prompt = self._build_wealth_trends_prompt(snapshots)
        
        # Call LLM
        result: WealthTrendAnalysis = structured.invoke([
            {"role": "system", "content": WEALTH_TRENDS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])
        
        return result
```

### svc-infra Integration

**Cache** (insights caching):
```python
from svc_infra.cache import get_cache

cache = get_cache()

# Cache insights for 24 hours
cache_key = f"net_worth:insights:{user_id}:{insight_type}"
cached = await cache.get(cache_key)
if cached:
    return WealthTrendAnalysis.model_validate_json(cached)

insights = await generator.generate_wealth_trends(snapshots)
await cache.set(cache_key, insights.model_dump_json(), ttl=86400)
```

**Jobs** (weekly goal check-ins):
```python
from svc_infra.jobs import get_scheduler

scheduler = get_scheduler()

async def check_all_goals():
    users = await get_users_with_goals()
    for user in users:
        for goal in user.goals:
            report = await goal_tracker.track_progress(goal, user.snapshots)
            if report.status == "off_track":
                await send_webhook(user.id, "goal.off_track", report)

# Run every Sunday at 00:00 UTC
scheduler.add_task(
    name="weekly_goal_check",
    func=check_all_goals,
    interval=604800,  # 7 days in seconds
)
```

**Webhooks** (goal progress alerts):
```python
from svc_infra.webhooks import send_webhook

if report.status == "off_track":
    await send_webhook(
        user_id=user_id,
        event="net_worth.goal_off_track",
        data={
            "goal_id": goal.id,
            "goal_type": goal.type,
            "current_progress": report.current_progress,
            "variance_days": report.variance_from_target,
            "recommendations": report.recommendations,
        }
    )
```

### Easy Builder Update

```python
def easy_net_worth(
    banking: BankingProvider | None = None,
    brokerage: BrokerageProvider | None = None,
    crypto: CryptoProvider | None = None,
    market: MarketProvider | None = None,
    enable_llm: bool = False,
    llm_provider: str = "google",
    llm_model: str | None = None,
    **config,
) -> NetWorthTracker:
    """
    One-call setup for net worth tracking.
    
    V1 Parameters (Always Enabled):
        banking, brokerage, crypto: Provider instances for account aggregation
        market: Market data provider for currency conversion and quotes
        base_currency: Default "USD"
        
    V2 Parameters (LLM Enhancement):
        enable_llm: Enable LLM insights/conversation/goals (default: False)
        llm_provider: "google" (default, cheapest), "openai", "anthropic"
        llm_model: Override default model (gemini-2.0-flash-exp, gpt-4o-mini, etc.)
        
    Returns:
        NetWorthTracker with aggregator + calculator + optional LLM components
        
    Cost (V2 with LLM):
        - Insights: $0.042/user/month (24h cache)
        - Conversation: $0.018/user/month (2 conversations)
        - Goals: $0.0036/user/month (weekly check-ins)
        - Total: $0.064/user/month (<$0.10 target)
    """
    # Validate at least one provider
    if not any([banking, brokerage, crypto]):
        raise ValueError("At least one provider required (banking, brokerage, or crypto)")
    
    # Create aggregator + calculator (V1, always enabled)
    aggregator = NetWorthAggregator(
        banking=banking,
        brokerage=brokerage,
        crypto=crypto,
        market=market,
        **config,
    )
    
    # Create LLM components (V2, optional)
    insights_generator = None
    goal_tracker = None
    conversation = None
    
    if enable_llm:
        from ai_infra.llm import CoreLLM
        llm = CoreLLM()
        
        insights_generator = NetWorthInsightsGenerator(
            llm=llm,
            provider=llm_provider,
            model_name=llm_model or _default_model(llm_provider),
        )
        
        goal_tracker = FinancialGoalTracker(
            llm=llm,
            provider=llm_provider,
            model_name=llm_model or _default_model(llm_provider),
        )
        
        conversation = FinancialPlanningConversation(
            llm=llm,
            provider=llm_provider,
            model_name=llm_model or _default_model(llm_provider),
        )
    
    return NetWorthTracker(
        aggregator=aggregator,
        insights_generator=insights_generator,
        goal_tracker=goal_tracker,
        conversation=conversation,
    )
```

## Cost Analysis

### Google Gemini (Default, Cheapest)

**Model**: gemini-2.0-flash-exp  
**Pricing**: $0.00035/1K input tokens, $0.0014/1K output tokens

| Component | Frequency | Input Tokens | Output Tokens | Cost/Call | Monthly Cost |
|-----------|-----------|--------------|---------------|-----------|--------------|
| Insights | 1/day (24h cache) | 2,000 | 500 | $0.0014 | $0.042 |
| Conversation | 2/month (10 turns) | 2,500 | 300 | $0.0009 | $0.018 |
| Goal Tracking | 1/week (4/month) | 1,500 | 300 | $0.0009 | $0.0036 |
| **Total** | - | - | - | - | **$0.064** |

**Target**: <$0.10/user/month ✅ **WITHIN BUDGET** (36% safety margin)

### Alternative Providers

| Provider | Model | Cost/1K Tokens | Monthly Cost | Over Budget |
|----------|-------|----------------|--------------|-------------|
| Google | gemini-2.0-flash-exp | $0.00035 | $0.064 | ✅ 36% margin |
| OpenAI | gpt-4o-mini | $0.0010 | $0.183 | ⚠️ 83% over |
| Anthropic | claude-3-5-haiku | $0.00080 | $0.147 | ⚠️ 47% over |

**Recommendation**: Use Google Gemini as default, allow provider override for premium tiers

## Graceful Degradation

### LLM Disabled (Default)
```python
# V1-only behavior (backward compatible)
tracker = easy_net_worth(banking=banking_provider)
net_worth = await tracker.get_current_net_worth()  # Works
insights = await tracker.get_insights()  # Returns None or raises NotImplementedError
```

### LLM Enabled but Fails
```python
# Fallback to V1 when LLM errors
try:
    insights = await generator.generate_wealth_trends(snapshots)
except Exception as e:
    logger.warning(f"LLM insights failed: {e}")
    # Return basic insights from V1 calculations
    insights = WealthTrendAnalysis(
        summary=f"Net worth changed {change_percent:.1%} to ${current_net_worth:,.0f}",
        period=f"{len(snapshots)} months",
        change_amount=change_amount,
        change_percent=change_percent,
        primary_drivers=["Calculation only (LLM unavailable)"],
        risk_factors=[],
        confidence=0.5,  # Low confidence (no LLM analysis)
    )
```

### API Responses
```python
# GET /net-worth/insights (when LLM disabled)
Response: {
  "error": "LLM insights not enabled. Set enable_llm=True to use this feature.",
  "fallback": {
    "change_amount": 15000.0,
    "change_percent": 0.027,
    "period": "6 months"
  }
}
```

## Validation & Safety

### Financial Calculations Validation

**DON'T trust LLM for math**:
```python
# ❌ BAD: Let LLM calculate payoff timeline
prompt = "Calculate how long to pay off $45k debt at $1,200/month with 6.2% APR"
result = llm.invoke(prompt)  # LLM might give wrong answer

# ✅ GOOD: Calculate locally, ask LLM for advice
payoff_months = calculate_debt_payoff(45000, 1200, 0.062)  # 42 months
prompt = f"Given {payoff_months} months to pay off $45k debt, what advice would you give?"
result = llm.invoke(prompt)  # LLM provides context, not calculations
```

**Validation Strategy**:
1. **Calculate locally**: Use Python for all math (interest, returns, payoff schedules)
2. **LLM for context**: Ask LLM to explain/advise based on our calculations
3. **Validate LLM output**: Check confidence scores, reject <0.7 confidence
4. **Cross-check numbers**: If LLM mentions numbers, verify they match our data

### Safety Filters

**Sensitive Information**:
```python
SENSITIVE_PATTERNS = [
    r"\b(ssn|social security number)\b",
    r"\b(password|pin|access code)\b",
    r"\b(credit card number|cvv)\b",
    r"\b(bank account number|routing number)\b",
]

def is_sensitive(question: str) -> bool:
    lower = question.lower()
    return any(re.search(pattern, lower) for pattern in SENSITIVE_PATTERNS)

if is_sensitive(question):
    return ConversationResponse(
        answer="I cannot help with sensitive information like SSN, passwords, or account numbers.",
        follow_up_questions=[],
        confidence=1.0,
        sources=[]
    )
```

**Disclaimer**:
All LLM responses include:
```
⚠️ This is AI-generated advice. Not a substitute for a certified financial advisor.
Verify calculations independently. For personalized advice, consult a professional.
```

## Alternatives Considered

### Alternative 1: Use OpenAI GPT-4o-mini Instead of Gemini

**Pros**:
- More widely adopted (larger user base)
- Better documentation and examples
- Slightly better reasoning on complex questions

**Cons**:
- 2.86× more expensive ($0.183 vs $0.064/user/month)
- Still over budget even with caching
- No significant accuracy improvement for financial advice

**Decision**: ❌ Rejected due to cost (83% over budget)

### Alternative 2: Self-Host Open Source LLM (Llama 3.1 70B)

**Pros**:
- $0 API costs after infrastructure setup
- Full control over model and data
- No rate limits

**Cons**:
- High infrastructure costs ($500-$1000/month for GPU instances)
- Complex deployment and maintenance
- Lower quality vs Gemini/GPT for financial advice
- Not cost-effective until >10,000 users

**Decision**: ❌ Rejected for V2 (revisit at scale)

### Alternative 3: Hybrid (V1 Only, No LLM)

**Pros**:
- $0 cost
- No dependency on external LLM APIs
- Simpler implementation

**Cons**:
- No natural language insights (just raw numbers)
- No conversational interface
- No goal validation/recommendations
- Less engaging user experience

**Decision**: ❌ Rejected (LLM provides significant value for <$0.10/user/month)

### Alternative 4: Pre-Computed Insights (No LLM, Template-Based)

**Pros**:
- $0 cost
- Deterministic output
- Fast (<10ms)

**Cons**:
- Generic advice (not personalized)
- Limited to predefined templates
- No conversation capability
- Less engaging than LLM

**Decision**: ❌ Rejected (use as fallback when LLM disabled)

## Consequences

### Positive

1. **User Value**: Natural language insights, conversational interface, personalized advice
2. **Cost Effective**: <$0.10/user/month (10× safety margin)
3. **Graceful Degradation**: V1 works when LLM disabled (backward compatible)
4. **Reuse**: Leverages ai-infra (CoreLLM), svc-infra (cache/jobs/webhooks)
5. **Validation**: Local math + LLM context (safe, accurate)

### Negative

1. **LLM Dependency**: Requires ai-infra dependency (adds complexity)
2. **Latency**: 500-2000ms for insights (vs <100ms for V1)
3. **Cost**: $0.064/user/month (vs $0 for V1)
4. **Rate Limits**: Google Gemini free tier has rate limits (15 RPM)
5. **Disclaimer Needed**: AI advice not a substitute for certified financial advisor

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM costs exceed budget | Cache aggressively (24h TTL), monitor costs, disable if >$0.10 |
| LLM gives bad advice | Validate calculations locally, add disclaimers, log all LLM outputs |
| Rate limits hit | Use multiple providers (Google → OpenAI fallback), queue requests |
| Context overflow (10-turn limit) | Summarize older exchanges, drop least relevant context |
| Sensitive data leakage | Filter questions (SSN, passwords), don't send PII to LLM |

## References

- [ADR-0020: Net Worth Tracking (V1)](./0020-net-worth-tracking.md)
- [ai-infra CoreLLM Documentation](../../../ai-infra/src/ai_infra/llm/README.md)
- [svc-infra Cache Documentation](../../../svc-infra/src/svc_infra/cache/README.md)
- [svc-infra Jobs Scheduler](../../../svc-infra/src/svc_infra/jobs/README.md)
- [Research: Net Worth LLM Insights](../research/net-worth-llm-insights.md)

---

**Status**: ✅ Accepted  
**Next Steps**: Implement insights.py, conversation.py, goals.py per this architecture
