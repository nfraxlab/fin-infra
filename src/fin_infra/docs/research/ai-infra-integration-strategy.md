# ai-infra Integration Strategy for fin-infra

**Status**: Draft  
**Created**: 2025-06-15  
**Owner**: Development Team  

## Purpose

This document identifies opportunities to integrate ai-infra's LLM and AI capabilities into fin-infra capabilities, enhancing user experience with natural language interfaces, intelligent insights, and personalized recommendations.

**Key Principle**: ai-infra provides general AI infrastructure (LLM calls, structured output, agents); fin-infra implements financial-specific prompts, domain knowledge, and integration patterns.

---

## Executive Summary

### ai-infra Capabilities Overview

Based on exploration of `/Users/alikhatami/ide/infra/ai-infra/src/ai_infra/`:

**Core LLM Module** (`ai_infra.llm`):
- **CoreLLM**: Chat completion, agents, streaming, token management
- **Structured Output**: `with_structured_output(schema=Pydantic)` for guaranteed JSON parsing
- **Multi-Provider**: OpenAI (GPT-4o/5), Anthropic (Claude 3.5/3.7), Google (Gemini 2.5), xAI (Grok 3), Deepseek, MistralAI
- **Utilities**: Retry logic, fallback chains, HITL (human-in-the-loop) hooks, response validation

**Graph Module** (`ai_infra.graph`):
- Workflow orchestration with state management
- Multi-step financial analysis pipelines
- Conditional branching based on results

**MCP Module** (`ai_infra.mcp`):
- Model Context Protocol for external tool integration
- Potential for financial data retrieval tools

### Integration Status

| Section | Capability | ai-infra Status | Priority |
|---------|-----------|----------------|----------|
| 15 | Transaction Categorization | ✅ V2 plan complete (40+ items) | HIGH |
| 16 | Recurring Detection | ⚠️ Opportunities identified | MEDIUM |
| 17 | Net Worth Tracking | ⚠️ Opportunities identified | MEDIUM |
| 19 | Portfolio Analytics | ⚠️ Future opportunity | LOW |

---

## Section 15: Transaction Categorization (✅ Complete)

**Status**: V2 LLM integration plan added (40+ checklist items in `.github/plans.md`)

**ai-infra Integration**:
- Layer 4 LLM fallback for low-confidence predictions (sklearn confidence < 0.6)
- Few-shot prompting with 10-20 examples
- Structured output: `CategoryPrediction(category, confidence, reasoning)`
- Personalized categorization with user context injection
- Multi-provider support (Google Gemini default, OpenAI/Anthropic fallback)

**Cost Analysis**:
- Google Gemini 2.5 Flash: **$0.00005/txn** (recommended)
- OpenAI GPT-4o-mini: $0.0001/txn
- Anthropic Claude 3.5 Haiku: $0.0002/txn
- Cache hit rate: 90%+ (svc-infra.cache, 24h TTL) → effective cost < $0.00001/txn

**Checklist Status**: 40+ items added covering research, design, implementation, testing, docs

---

## Section 16: Recurring Transaction Detection

### Current Approach (v1)
Pattern-based detection using time-series analysis:
- Fixed amount matching (±5% variance)
- Merchant name consistency (exact or fuzzy match)
- Date clustering (monthly, bi-weekly, quarterly cadence)
- False positive rate target: <5%

**Limitations**:
- Rigid pattern matching (struggles with variable amounts)
- No semantic understanding (Netflix vs Disney+ both "streaming")
- Limited to known cadences (monthly/bi-weekly/quarterly)
- No proactive suggestions for new subscriptions
- No natural language explanations

### ai-infra Enhancement Opportunities

#### 1. Merchant Name Normalization (HIGH Priority)

**Problem**: "NETFLIX.COM", "Netflix", "NETFLIX INC" are same merchant  
**Current**: Fuzzy string matching (RapidFuzz)  
**ai-infra Solution**: Few-shot LLM normalization

```python
from ai_infra.llm import CoreLLM
from ai_infra.llm.utils.structured import with_structured_output

class MerchantNormalizer(Pydantic):
    normalized_name: str
    merchant_type: str  # "streaming", "utilities", "groceries"
    confidence: float

llm = CoreLLM(provider="google", model="gemini-2.5-flash")
normalizer = with_structured_output(llm, MerchantNormalizer)

# Few-shot prompt
prompt = """
Normalize merchant names to canonical form.

Examples:
- "NETFLIX.COM" → "Netflix" (streaming)
- "AMZN MKTP US" → "Amazon" (e-commerce)
- "SQ *COFFEE SHOP" → "Local Coffee Shop" (food & drink)

Merchant: "{merchant_raw}"
"""

result = normalizer.invoke(prompt.format(merchant_raw="NFLX*SUBSCRIPTION"))
# → MerchantNormalizer(normalized_name="Netflix", merchant_type="streaming", confidence=0.95)
```

**Benefits**:
- Semantic grouping (all streaming services recognized)
- Handles new merchant formats without regex updates
- Provides merchant categorization (useful for categorization system)

**Cost**: ~$0.00003/merchant (1K tokens) × cache hit 95% → **$0.0000015 effective**

#### 2. Variable Amount Detection (MEDIUM Priority)

**Problem**: Utility bills vary monthly ($45-$65), pattern matching fails  
**Current**: Fixed ±5% tolerance (too rigid)  
**ai-infra Solution**: LLM-based anomaly detection for "expected variance"

```python
class RecurringPattern(Pydantic):
    is_recurring: bool
    cadence: str  # "monthly", "bi-weekly", "variable"
    expected_range: tuple[float, float]
    reasoning: str

llm = CoreLLM(provider="google", model="gemini-2.5-flash")
detector = with_structured_output(llm, RecurringPattern)

# Historical transactions
transactions = [
    {"date": "2025-01-15", "merchant": "PG&E Utilities", "amount": 52.34},
    {"date": "2025-02-15", "merchant": "PG&E Utilities", "amount": 68.12},
    {"date": "2025-03-15", "merchant": "PG&E Utilities", "amount": 45.90},
    {"date": "2025-04-15", "merchant": "PG&E Utilities", "amount": 59.45},
]

prompt = """
Analyze these transactions and determine if they represent a recurring pattern.

Transactions: {transactions}

Consider:
- Date consistency (monthly, bi-weekly, etc.)
- Amount variability (fixed vs variable)
- Merchant name consistency

Classify as recurring if pattern exists, even with variable amounts (utilities, phone bills).
"""

result = detector.invoke(prompt.format(transactions=transactions))
# → RecurringPattern(
#     is_recurring=True, 
#     cadence="monthly", 
#     expected_range=(45.0, 70.0),
#     reasoning="Monthly on 15th with seasonal variation (winter heating, summer cooling)"
# )
```

**Benefits**:
- Detects variable recurring charges (utilities, phone bills, subscriptions with usage)
- Provides reasoning for transparency
- Handles seasonal patterns (heating in winter, cooling in summer)

**Cost**: ~$0.0001/detection (500 tokens for 10 transactions)

#### 3. Natural Language Insights (LOW Priority)

**Problem**: Users see "15 recurring transactions detected" with no explanation  
**Current**: Raw data lists  
**ai-infra Solution**: Generate natural language summaries

```python
class SubscriptionInsight(Pydantic):
    summary: str
    top_subscriptions: list[str]
    monthly_total: float
    recommendations: list[str]

llm = CoreLLM(provider="google", model="gemini-2.5-flash")
insights = with_structured_output(llm, SubscriptionInsight)

subscriptions = [
    {"name": "Netflix", "amount": 15.99, "cadence": "monthly"},
    {"name": "Spotify", "amount": 9.99, "cadence": "monthly"},
    {"name": "Amazon Prime", "amount": 14.99, "cadence": "monthly"},
    {"name": "Disney+", "amount": 7.99, "cadence": "monthly"},
    {"name": "HBO Max", "amount": 15.99, "cadence": "monthly"},
]

prompt = """
Analyze user's subscriptions and provide insights.

Subscriptions: {subscriptions}

Provide:
1. Summary of subscription spending
2. Top 3 most expensive subscriptions
3. Actionable recommendations (consolidation, cancellation, etc.)
"""

result = insights.invoke(prompt.format(subscriptions=subscriptions))
# → SubscriptionInsight(
#     summary="You have 5 streaming subscriptions totaling $64.95/month ($779.40/year).",
#     top_subscriptions=["Netflix ($15.99)", "HBO Max ($15.99)", "Amazon Prime ($14.99)"],
#     recommendations=[
#         "Consider consolidating streaming services - Disney+ bundle includes Hulu and ESPN+ for $19.99",
#         "You have 3 overlapping streaming services; canceling 1-2 could save $30/month",
#     ]
# )
```

**Benefits**:
- User-friendly explanations
- Actionable recommendations
- Personalized insights based on spending patterns

**Cost**: ~$0.0002/insight generation (1K tokens)

### Implementation Plan (Section 16 V2)

**Checklist to Add** (similar to Section 15 V2 structure):

```markdown
#### V2 Phase: LLM Enhancement (ai-infra)
- [ ] **Research (ai-infra check)**:
  - [ ] Check ai-infra.llm for structured output with Pydantic schemas
  - [ ] Review few-shot prompting best practices for merchant normalization
  - [ ] Classification: Type A (recurring detection is financial-specific, LLM is general AI)
  - [ ] Justification: Use ai-infra for LLM calls, fin-infra for financial prompts and domain logic
  - [ ] Reuse plan: CoreLLM for inference, structured output for Pydantic validation, svc-infra.cache for merchant normalization (1-week TTL)
- [ ] Research: Merchant name normalization with LLM (few-shot vs fine-tuning)
  - [ ] Zero-shot accuracy: 70-80% (poor for edge cases)
  - [ ] Few-shot accuracy: 90-95% (10-20 examples per merchant type)
  - [ ] Fine-tuning: 95-98% (requires 10k+ labeled pairs, overkill)
  - [ ] **Decision**: Few-shot with 20 examples (streaming, utilities, groceries, subscriptions)
- [ ] Research: Variable amount detection (LLM vs statistical methods)
  - [ ] Statistical (mean ± 2 std dev): Works for normal distributions
  - [ ] LLM: Understands semantic variance (utility bills seasonal, gym fees fixed)
  - [ ] **Decision**: Hybrid - statistical for initial filter, LLM for edge cases
- [ ] Research: Cost analysis for LLM-enhanced detection
  - [ ] Merchant normalization: $0.00003/merchant × 95% cache hit → $0.0000015 effective
  - [ ] Variable detection: $0.0001/detection (run only for ambiguous cases)
  - [ ] Insights generation: $0.0002/user/month (on-demand)
  - [ ] **Total**: <$0.001/user/month with caching
- [ ] Design: LLM-enhanced recurring detection architecture (ADR-0019)
  - [ ] Layer 1: Pattern-based detection (existing, fast, 80% coverage)
  - [ ] Layer 2: LLM merchant normalization (for grouped detection)
  - [ ] Layer 3: LLM variable amount detection (for utilities/variable subscriptions)
  - [ ] Layer 4: LLM insights generation (on-demand via API endpoint)
- [ ] Design: Easy builder signature update
  - [ ] `easy_recurring_detection(enable_llm=False, llm_provider="google", **config)`
  - [ ] Default: LLM disabled (backward compatible)
  - [ ] When enabled: Uses ai-infra.llm with structured output
- [ ] Implement: recurring/normalizers.py (LLM-based merchant normalization)
  - [ ] MerchantNormalizer class with CoreLLM + structured output
  - [ ] Few-shot prompt template (20 examples: streaming, utilities, groceries, etc.)
  - [ ] Cache normalized names (svc-infra.cache, 1-week TTL, 95% hit rate)
  - [ ] Fallback to fuzzy matching if LLM fails or disabled
- [ ] Implement: recurring/detectors.py Layer 2 (LLM variable detection)
  - [ ] VariableDetector class for ambiguous patterns
  - [ ] Call LLM only for transactions with >20% amount variance
  - [ ] Structured output: RecurringPattern(is_recurring, cadence, expected_range, reasoning)
  - [ ] Update detector.py to use LLM for edge cases
- [ ] Implement: recurring/insights.py (natural language summaries)
  - [ ] SubscriptionInsightsGenerator with CoreLLM
  - [ ] Generate monthly summary (total spend, top subscriptions, recommendations)
  - [ ] API endpoint: GET /recurring/insights (on-demand, not automatic)
  - [ ] Cache insights (svc-infra.cache, 1-day TTL)
- [ ] Tests: Unit tests (mocked CoreLLM responses)
  - [ ] test_merchant_normalizer(): "NFLX*SUB" → "Netflix" (streaming)
  - [ ] test_variable_detector(): Utility bills → is_recurring=True with expected_range
  - [ ] test_insights_generator(): 5 subscriptions → summary + recommendations
  - [ ] test_llm_fallback(): LLM disabled → uses fuzzy matching
  - [ ] test_caching(): Verify merchant normalization cached (1-week TTL)
- [ ] Tests: Acceptance tests (real LLM API calls)
  - [ ] test_google_gemini_normalization(): Real API call with test merchant names
  - [ ] test_variable_detection_accuracy(): Test with 100 real utility transactions
  - [ ] test_insights_generation(): Generate insights for test user's subscriptions
  - [ ] Mark with @pytest.mark.acceptance and skip if GOOGLE_API_KEY not set
- [ ] Verify: LLM enhancement improves detection accuracy
  - [ ] Baseline (pattern-only): 85% accuracy, 8% false positives
  - [ ] With LLM: Target 92%+ accuracy, <5% false positives
  - [ ] Variable detection: 70% → 88% for utility bills
- [ ] Docs: Update docs/recurring-detection.md with LLM section
  - [ ] Add "LLM Enhancement" section after pattern-based detection
  - [ ] Document merchant normalization with few-shot examples
  - [ ] Document variable amount detection for utilities
  - [ ] Document insights API with usage examples
  - [ ] Add cost analysis table (Google Gemini vs OpenAI vs Anthropic)
  - [ ] Add enable_llm=True configuration guide
```

**Estimated Effort**: 2-3 days (5 implementation tasks, 5 test tasks, 1 doc task)

---

## Section 17: Net Worth Tracking

### Current Approach (v1)
Aggregation-based net worth calculation:
- Fetch balances from all providers (banking, brokerage, crypto)
- Assets - Liabilities = Net Worth
- Historical snapshots (daily via svc-infra.jobs)
- Trend detection (simple percentage change)

**Limitations**:
- Raw numbers with no context ("Net worth: $125,342.18")
- No explanation of changes ("Why did it increase $5,000?")
- No actionable insights ("What should I do?")
- No goal tracking ("Am I on track for retirement?")
- No natural language queries ("How much did I gain this month?")

### ai-infra Enhancement Opportunities

#### 1. Natural Language Insights (HIGH Priority)

**Problem**: Users see "$125,342.18" with no explanation  
**Current**: Percentage change ("↑ 4.2%")  
**ai-infra Solution**: Generate narrative explanations

```python
class NetWorthInsight(Pydantic):
    summary: str
    primary_driver: str
    breakdown: dict[str, float]  # category → contribution
    recommendations: list[str]

llm = CoreLLM(provider="google", model="gemini-2.5-flash")
insights = with_structured_output(llm, NetWorthInsight)

# Historical snapshots
current = {
    "checking": 5000,
    "savings": 20000,
    "brokerage": 85000,
    "crypto": 8000,
    "credit_card": -3000,
    "mortgage": -250000,
}
previous = {
    "checking": 4800,
    "savings": 19500,
    "brokerage": 78000,
    "crypto": 10000,
    "credit_card": -3200,
    "mortgage": -250500,
}

prompt = """
Analyze net worth change and provide insights.

Current Net Worth: ${current_total:.2f}
Previous Net Worth: ${previous_total:.2f}
Change: ${change:.2f} ({pct:.1f}%)

Account Breakdown:
{breakdown}

Provide:
1. One-sentence summary explaining the change
2. Primary driver (which account changed most)
3. Breakdown of contributions by category
4. Actionable recommendations
"""

result = insights.invoke(prompt.format(
    current_total=sum(current.values()),
    previous_total=sum(previous.values()),
    change=sum(current.values()) - sum(previous.values()),
    pct=((sum(current.values()) / sum(previous.values())) - 1) * 100,
    breakdown={"Current": current, "Previous": previous},
))
# → NetWorthInsight(
#     summary="Your net worth increased by $8,200 (10.2%) this month, primarily due to stock market gains.",
#     primary_driver="brokerage account (+$7,000, 8.9% gain)",
#     breakdown={
#         "Investments": 7000,  # brokerage gain
#         "Crypto": -2000,     # crypto loss
#         "Cash": 700,         # checking + savings
#         "Debt": 500,         # mortgage paydown + credit card payoff
#     },
#     recommendations=[
#         "Strong brokerage performance - consider rebalancing if allocation exceeds target",
#         "Crypto declined 20% - evaluate if position size still aligns with risk tolerance",
#     ]
# )
```

**Benefits**:
- Human-readable explanations (not just numbers)
- Attribution analysis (which accounts drove change)
- Personalized recommendations
- User engagement (insights prompt action)

**Cost**: ~$0.0003/snapshot analysis (1.5K tokens)

#### 2. Goal Tracking with Natural Language (MEDIUM Priority)

**Problem**: Users set goal "save $50k for house down payment" but no progress tracking  
**Current**: Manual calculation  
**ai-infra Solution**: LLM-powered goal progress and recommendations

```python
class GoalProgress(Pydantic):
    goal_name: str
    target_amount: float
    current_progress: float
    percent_complete: float
    estimated_completion: str  # "6 months at current rate"
    recommendations: list[str]

llm = CoreLLM(provider="google", model="gemini-2.5-flash")
goal_tracker = with_structured_output(llm, GoalProgress)

goal = {
    "name": "House Down Payment",
    "target": 50000,
    "deadline": "2026-01-01",
}
net_worth_history = [
    {"date": "2025-01-01", "amount": 75000},
    {"date": "2025-02-01", "amount": 78000},
    {"date": "2025-03-01", "amount": 82000},
    {"date": "2025-04-01", "amount": 85000},
    {"date": "2025-05-01", "amount": 88000},
]

prompt = """
Analyze progress toward financial goal.

Goal: {goal_name}
Target: ${target_amount:,.2f}
Deadline: {deadline}

Net Worth History (last 5 months):
{history}

Calculate:
1. Current progress toward goal
2. Percent complete
3. Estimated completion date (linear projection)
4. Recommendations to accelerate progress
"""

result = goal_tracker.invoke(prompt.format(
    goal_name=goal["name"],
    target_amount=goal["target"],
    deadline=goal["deadline"],
    history=net_worth_history,
))
# → GoalProgress(
#     goal_name="House Down Payment",
#     target_amount=50000.0,
#     current_progress=13000.0,  # net worth gain (88k - 75k)
#     percent_complete=26.0,     # 13k / 50k
#     estimated_completion="15 months at current rate ($3,250/month savings)",
#     recommendations=[
#         "You're saving $3,250/month - increase by $900/month to hit goal by deadline",
#         "Consider high-yield savings account for down payment (5%+ APY vs 0.5% checking)",
#         "Target deadline is 8 months away; current rate will complete goal in 15 months (7 months late)",
#     ]
# )
```

**Benefits**:
- Automatic progress tracking (no manual calculation)
- Realistic projections based on historical data
- Actionable recommendations to stay on track
- Early warnings if goals won't be met

**Cost**: ~$0.0002/goal analysis (1K tokens)

#### 3. Natural Language Queries (LOW Priority)

**Problem**: Users can't ask "How much did my net worth grow last quarter?"  
**Current**: Manual chart navigation  
**ai-infra Solution**: LLM-powered Q&A over net worth history

```python
from ai_infra.llm import CoreLLM
from ai_infra.llm.agents import create_agent

# Create agent with net worth data access
llm = CoreLLM(provider="google", model="gemini-2.5-flash")
agent = create_agent(
    llm=llm,
    tools=[get_net_worth_history, calculate_net_worth_change],
    system_prompt="You are a financial assistant. Help users understand their net worth trends."
)

# User query
query = "How much did my net worth grow in Q1 2025?"

# Agent calls tools and generates response
response = agent.invoke(query)
# → "Your net worth grew by $13,000 (17.3%) in Q1 2025, increasing from $75,000 to $88,000. 
#    The growth was primarily driven by your brokerage account (+$10,000, 13.2% gain) and 
#    savings account (+$2,500). Your credit card balance also decreased by $500."

# Follow-up query
query = "What was my best month?"

response = agent.invoke(query)
# → "April 2025 was your best month with $4,000 growth (5.0%), driven by a strong stock market rally."
```

**Benefits**:
- Natural language interface (no chart navigation)
- Follow-up questions (conversational)
- Contextual responses (references previous queries)

**Cost**: ~$0.0005/query (2K tokens for context + response)

### Implementation Plan (Section 17 V2)

**Checklist to Add**:

```markdown
#### V2 Phase: LLM Insights (ai-infra)
- [ ] **Research (ai-infra check)**:
  - [ ] Check ai-infra.llm for structured output and narrative generation
  - [ ] Review ai-infra.llm.agents for conversational Q&A
  - [ ] Classification: Type A (net worth tracking is financial-specific, LLM is general AI)
  - [ ] Justification: Use ai-infra for LLM inference, fin-infra for financial context and data
  - [ ] Reuse plan: CoreLLM for insights generation, structured output for Pydantic models, agents for conversational queries, svc-infra.cache for insights (1-day TTL)
- [ ] Research: Natural language insight generation (templated vs dynamic)
  - [ ] Templated: "Net worth increased X% due to Y" (simple, fast, 95% accuracy)
  - [ ] Dynamic LLM: Contextual explanations with recommendations (slower, 98% accuracy)
  - [ ] **Decision**: Dynamic LLM with caching (1-day TTL, refresh on new snapshot)
- [ ] Research: Goal tracking with LLM (linear projection vs time-series forecasting)
  - [ ] Linear projection: Simple, transparent, 80% accuracy for short-term goals
  - [ ] Time-series (ARIMA/Prophet): Complex, 85% accuracy, overkill for personal finance
  - [ ] **Decision**: Linear projection with LLM-generated recommendations
- [ ] Research: Cost analysis for LLM-enhanced net worth tracking
  - [ ] Snapshot insights: $0.0003/snapshot × 30/month = $0.009/user/month
  - [ ] Goal tracking: $0.0002/goal × 3 goals = $0.0006/user/month
  - [ ] Conversational queries: $0.0005/query × 10/month = $0.005/user/month
  - [ ] **Total**: ~$0.015/user/month (<$0.20/year)
- [ ] Design: LLM-enhanced net worth architecture (ADR-0020)
  - [ ] Layer 1: Net worth calculation (existing, assets - liabilities)
  - [ ] Layer 2: LLM insights generation (narrative explanation of changes)
  - [ ] Layer 3: Goal progress tracking (LLM-powered projections)
  - [ ] Layer 4: Conversational Q&A (ai-infra.llm.agents for natural language queries)
- [ ] Design: Easy builder signature update
  - [ ] `easy_net_worth(enable_insights=False, llm_provider="google", **config)`
  - [ ] Default: Insights disabled (backward compatible)
  - [ ] When enabled: Generates insights on each snapshot
- [ ] Implement: net_worth/insights.py (LLM-based narrative generation)
  - [ ] NetWorthInsightsGenerator with CoreLLM + structured output
  - [ ] Generate insights on each snapshot (primary driver, breakdown, recommendations)
  - [ ] Cache insights (svc-infra.cache, 1-day TTL)
  - [ ] API endpoint: GET /net-worth/insights (latest snapshot)
- [ ] Implement: net_worth/goals.py (LLM-powered goal tracking)
  - [ ] GoalProgressTracker with linear projection + LLM recommendations
  - [ ] Calculate progress toward user-defined goals (savings, debt payoff, etc.)
  - [ ] API endpoint: GET /net-worth/goals (all goals with progress)
  - [ ] Webhook: Send alert if goal is off-track (via svc-infra.webhooks)
- [ ] Implement: net_worth/agent.py (conversational Q&A)
  - [ ] Create agent with tools: get_net_worth_history, calculate_change, get_snapshot
  - [ ] WebSocket endpoint: /net-worth/chat (real-time conversation)
  - [ ] Store conversation history (svc-infra.db, last 10 messages for context)
- [ ] Tests: Unit tests (mocked CoreLLM responses)
  - [ ] test_insights_generator(): Net worth change → narrative explanation
  - [ ] test_goal_tracker(): Goal + history → progress + recommendations
  - [ ] test_conversational_agent(): "How much did I gain?" → contextual response
  - [ ] test_insights_caching(): Verify insights cached (1-day TTL)
  - [ ] test_goal_alerts(): Off-track goal → webhook notification
- [ ] Tests: Acceptance tests (real LLM API calls)
  - [ ] test_google_gemini_insights(): Real API call with test snapshots
  - [ ] test_goal_tracking_accuracy(): Linear projection vs actual (±10% acceptable)
  - [ ] test_agent_conversation(): Multi-turn conversation with follow-ups
  - [ ] Mark with @pytest.mark.acceptance and skip if GOOGLE_API_KEY not set
- [ ] Verify: LLM insights improve user engagement
  - [ ] Measure: Users with insights enabled vs disabled (engagement metrics)
  - [ ] Target: 2x increase in net worth page views with insights
  - [ ] Target: 90%+ user satisfaction with insight quality (survey)
- [ ] Docs: Update docs/net-worth.md with insights section
  - [ ] Add "Natural Language Insights" section after calculation methodology
  - [ ] Document insights API with example responses
  - [ ] Document goal tracking with progress examples
  - [ ] Document conversational Q&A with sample queries
  - [ ] Add cost analysis table (Google Gemini vs OpenAI vs Anthropic)
  - [ ] Add enable_insights=True configuration guide
```

**Estimated Effort**: 3-4 days (6 implementation tasks, 5 test tasks, 1 doc task)

---

## Section 19: Portfolio Analytics (Future)

### Potential ai-infra Enhancements (Future Exploration)

**Note**: Section 19 is "Nice-to-have (Fast Follows)", not Must-have. Document briefly for future reference.

#### 1. Natural Language Portfolio Analysis

**Use Case**: "Explain my portfolio performance this quarter"  
**ai-infra Solution**: LLM-generated narratives from portfolio metrics

Example:
- Input: Portfolio returns (10.5%), benchmark (S&P 500: 8.2%), sector allocations
- Output: "Your portfolio outperformed the S&P 500 by 2.3% this quarter, driven by strong tech sector holdings (AAPL +15%, MSFT +12%). Your diversification reduced volatility - small-cap exposure limited downside risk."

#### 2. Conversational Risk Analysis

**Use Case**: "Is my portfolio too risky for my age?"  
**ai-infra Solution**: Agent with risk tolerance questionnaire + portfolio analysis tools

Example:
- Agent asks clarifying questions (age, goals, time horizon)
- Analyzes current allocation vs recommended (60/40 stocks/bonds for age 40)
- Provides personalized recommendations ("Reduce equity allocation by 10% to align with target")

#### 3. Intelligent Rebalancing Recommendations

**Use Case**: "What should I buy/sell to rebalance?"  
**ai-infra Solution**: LLM-powered rebalancing with tax optimization

Example:
- Input: Current positions, target allocation, tax lots
- Output: "Sell $2,000 AAPL (long-term gains, 15% tax) and buy $1,500 VTI, $500 BND. This rebalances to 60/40 while minimizing taxes (estimated $45 tax vs $120 with naive rebalancing)."

**Implementation**: Lower priority (Section 19 is nice-to-have)

---

## Cost Analysis Summary

### Per-User Monthly Costs (with ai-infra LLM)

| Feature | Cost/Event | Frequency | Monthly Cost | Cache Hit | Effective Cost |
|---------|-----------|-----------|--------------|-----------|----------------|
| **Transaction Categorization** | $0.00005 | 100 txns | $0.005 | 90% | **$0.0005** |
| **Merchant Normalization** | $0.00003 | 50 merchants | $0.0015 | 95% | **$0.000075** |
| **Recurring Detection** | $0.0001 | 10 detections | $0.001 | N/A | **$0.001** |
| **Net Worth Insights** | $0.0003 | 30 snapshots | $0.009 | 50% | **$0.0045** |
| **Goal Tracking** | $0.0002 | 3 goals | $0.0006 | N/A | **$0.0006** |
| **Conversational Queries** | $0.0005 | 10 queries | $0.005 | N/A | **$0.005** |
| **TOTAL** | — | — | — | — | **$0.012/user/month** |

**Annual Cost**: ~$0.14/user/year (negligible compared to provider API costs)

### Cost Optimization Strategies

1. **Aggressive Caching** (svc-infra.cache):
   - Transaction categories: 24h TTL (90% hit rate)
   - Merchant normalization: 1-week TTL (95% hit rate)
   - Net worth insights: 1-day TTL (50% hit rate)

2. **Provider Selection**:
   - Google Gemini 2.5 Flash: Cheapest ($0.00005/txn), recommended default
   - OpenAI GPT-4o-mini: 2x cost, fallback for Gemini failures
   - Anthropic Claude 3.5 Haiku: 4x cost, premium option for complex reasoning

3. **Lazy Evaluation**:
   - Insights generation: On-demand (not automatic for every snapshot)
   - Conversational Q&A: User-initiated (not background processing)

4. **Budget Caps** (svc-infra.billing integration):
   - Set per-user LLM budget: $0.10/month (10x above expected)
   - Alert if user exceeds: Email notification + temporary disable
   - Admin dashboard: Track LLM costs per user

---

## Implementation Priority

### Phase 1: Section 15 V2 (HIGH Priority) - COMPLETE
- ✅ V2 plan added to `.github/plans.md` (40+ items)
- ⏳ Implementation pending

### Phase 2: Section 16 V2 (MEDIUM Priority) - READY
- ⚠️ Checklist drafted in this document
- ⏳ Needs approval and addition to `.github/plans.md`
- **Estimated**: 2-3 days development + testing

### Phase 3: Section 17 V2 (MEDIUM Priority) - READY
- ⚠️ Checklist drafted in this document
- ⏳ Needs approval and addition to `.github/plans.md`
- **Estimated**: 3-4 days development + testing

### Phase 4: Section 19 (LOW Priority) - FUTURE
- ⚠️ Opportunities identified, no concrete plan
- ⏳ Wait for Section 19 must-have promotion (currently nice-to-have)

---

## Developer Experience (DX) Goals

### Easy Integration Pattern

All ai-infra enhancements should follow the same pattern as Section 15:

```python
# Without LLM (v1 - pattern-based, fast)
categorizer = easy_categorization(model="local")
category = categorizer.categorize("Starbucks")

# With LLM (v2 - higher accuracy, slower, costs $0.00005/call)
categorizer = easy_categorization(model="hybrid", llm_provider="google")
category = categorizer.categorize("Starbucks")  # Falls back to LLM if confidence < 0.6
```

**Key Principles**:
1. **Backward compatible**: LLM disabled by default (`enable_llm=False`)
2. **One-line upgrade**: Add `enable_llm=True` to unlock LLM features
3. **Transparent costs**: Log LLM API calls for budget tracking
4. **Graceful degradation**: Fall back to v1 logic if LLM fails
5. **Consistent API**: Same return types (Pydantic models) with or without LLM

### Configuration Example

```python
# fin-infra settings (Pydantic Settings from svc-infra)
from fin_infra.settings import FinInfraSettings

settings = FinInfraSettings(
    # Provider API keys (existing)
    plaid_client_id="...",
    teller_api_key="...",
    
    # LLM configuration (new)
    enable_llm=True,
    llm_provider="google",  # "google", "openai", "anthropic"
    llm_api_key="...",  # Auto-detected from GOOGLE_API_KEY, OPENAI_API_KEY, etc.
    llm_budget_cap=0.10,  # $0.10/user/month max
    
    # Feature flags (per-capability LLM toggle)
    llm_categorization=True,
    llm_recurring_detection=True,
    llm_net_worth_insights=True,
)
```

---

## Testing Strategy

### Unit Tests (Mocked LLM)

Mock ai-infra CoreLLM responses for fast, deterministic tests:

```python
@pytest.fixture
def mock_llm(mocker):
    """Mock ai-infra CoreLLM with structured output."""
    mock = mocker.patch("ai_infra.llm.CoreLLM")
    mock.return_value.invoke.return_value = CategoryPrediction(
        category="Coffee Shops",
        confidence=0.95,
        reasoning="Starbucks is a well-known coffee chain"
    )
    return mock

def test_llm_categorization(mock_llm):
    categorizer = easy_categorization(enable_llm=True)
    result = categorizer.categorize("Starbucks")
    
    assert result.category == "Coffee Shops"
    assert result.confidence == 0.95
    mock_llm.return_value.invoke.assert_called_once()
```

### Acceptance Tests (Real LLM API)

Test with real LLM providers in CI/CD (gated behind env vars):

```python
@pytest.mark.acceptance
@pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="Requires Google API key")
def test_google_gemini_categorization():
    """Test real Google Gemini API call."""
    categorizer = easy_categorization(enable_llm=True, llm_provider="google")
    result = categorizer.categorize("NFLX*SUBSCRIPTION")
    
    # Verify LLM understands Netflix abbreviation
    assert result.category == "Streaming Services"
    assert result.confidence > 0.8
    
    # Verify reasoning provided
    assert "Netflix" in result.reasoning
```

### Cost Tracking Tests

Verify LLM calls stay within budget:

```python
def test_llm_cost_tracking():
    """Verify LLM costs tracked per user."""
    categorizer = easy_categorization(enable_llm=True, llm_provider="google")
    
    # Categorize 100 transactions
    for txn in test_transactions:
        categorizer.categorize(txn.merchant)
    
    # Check cost tracking
    cost = categorizer.get_total_cost()
    assert cost < 0.01  # $0.01 for 100 calls with 90% cache hit
```

---

## Documentation Requirements

### Per-Capability Docs

Each capability with ai-infra integration needs:

1. **"Without LLM" section** (v1 baseline)
2. **"With LLM" section** (v2 enhanced)
3. **Cost comparison table** (Google vs OpenAI vs Anthropic)
4. **Configuration examples** (`enable_llm=True`)
5. **Accuracy benchmarks** (v1 baseline vs v2 LLM)

Example structure (from Section 15):

```markdown
# Transaction Categorization

## Without LLM (v1 - Pattern-Based)
- Approach: Hybrid (exact dict → regex → sklearn Naive Bayes)
- Accuracy: 90-95%
- Speed: 1000 pred/sec
- Cost: $0 (bundled model)

## With LLM (v2 - ai-infra Enhanced)
- Approach: Hybrid (exact → regex → sklearn → **LLM fallback**)
- Accuracy: 95-98% (+3-5% improvement)
- Speed: 500 pred/sec (slower due to API calls)
- Cost: $0.00005/txn (Google Gemini)

### Cost Comparison
| Provider | Cost/Transaction | Cache Hit 90% | Effective Cost |
|----------|-----------------|---------------|----------------|
| Google Gemini 2.5 Flash | $0.00005 | Yes | **$0.000005** |
| OpenAI GPT-4o-mini | $0.0001 | Yes | $0.00001 |
| Anthropic Claude 3.5 Haiku | $0.0002 | Yes | $0.00002 |

### Configuration
```python
categorizer = easy_categorization(
    model="hybrid",
    enable_llm=True,
    llm_provider="google",  # or "openai", "anthropic"
    llm_confidence_threshold=0.6,  # Use LLM if sklearn < 0.6
)
```
```

---

## Next Steps

### Immediate (Waiting for User)

1. **User Decision Required**:
   - Option A: Continue Section 15 v1 implementation (traditional ML baseline)
   - Option B: Add Section 16/17 V2 LLM plans to `.github/plans.md` (based on this doc)
   - Option C: Review Section 15 V2 plans and refine before implementation

### If Option B Selected (Add V2 Plans)

1. Copy Section 16 V2 checklist from this doc → `.github/plans.md` after Section 16
2. Copy Section 17 V2 checklist from this doc → `.github/plans.md` after Section 17
3. Update Section 16/17 status in plans tracking (research → design → implement)

### Future Work

1. **Section 19 ai-infra Integration** (when promoted to must-have)
2. **Cross-Capability Agents** (ai-infra.graph for multi-step workflows)
   - Example: "Help me create a budget" → queries net worth → analyzes spending → suggests categories
3. **Personalized Financial Advisor Agent** (ai-infra.llm.agents)
   - User: "Should I invest $10k in stocks or pay off my car loan?"
   - Agent: Analyzes net worth, debt interest rate, risk tolerance → provides recommendation

---

## Appendix: ai-infra Module Reference

### Explored Modules

**`ai_infra.llm.core`**:
- `BaseLLMCore`: Base class for LLM interactions
- `CoreLLM(provider, model, **kwargs)`: Main LLM client
- `.invoke(prompt)`: Single completion
- `.stream(prompt)`: Token streaming
- `.with_structured_output(schema)`: Pydantic schema validation

**`ai_infra.llm.providers.models`**:
- OpenAI: `OpenAIModel.GPT_4O`, `OpenAIModel.GPT_5_MINI`
- Anthropic: `AnthropicModel.CLAUDE_3_5_SONNET`, `AnthropicModel.CLAUDE_3_5_HAIKU`
- Google: `GoogleModel.GEMINI_2_5_FLASH` (default)
- xAI: `xAIModel.GROK_3`, `xAIModel.GROK_3_MINI`
- Deepseek: `DeepseekModel.DEEPSEEK_CHAT`
- MistralAI: `MistralModel.MISTRAL_MEDIUM`

**`ai_infra.llm.utils.structured`**:
- `with_structured_output(llm, schema: Type[BaseModel])`: Wrap LLM for Pydantic output
- `is_valid_response(response, schema)`: Validate JSON against schema

**`ai_infra.llm.utils`**:
- `with_retry(llm, max_retries=3)`: Automatic retry on failure
- `run_with_fallbacks(llm, fallback_llms)`: Try multiple providers

**`ai_infra.graph`**:
- Workflow orchestration (not explored in detail for Section 15-17)
- Potential for multi-step financial analysis pipelines

**`ai_infra.llm.agents`**:
- `create_agent(llm, tools, system_prompt)`: Create conversational agent
- Tool calling for data retrieval (net worth history, portfolio positions, etc.)

---

## Change Log

- **2025-06-15**: Initial draft - identified ai-infra opportunities for Sections 15-17
- **2025-06-15**: Added Section 16 V2 checklist (merchant normalization, variable detection, insights)
- **2025-06-15**: Added Section 17 V2 checklist (natural language insights, goal tracking, conversational Q&A)
- **2025-06-15**: Added cost analysis, DX patterns, testing strategy, documentation requirements

---

**Status**: ✅ Ready for user review and decision (Option A/B/C)
