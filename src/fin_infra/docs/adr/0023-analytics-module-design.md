# ADR-0023: Analytics Module Design

**Status**: Accepted  
**Date**: 2025-11-07  
**Authors**: fin-infra team

## Context

Fintech applications (personal finance, wealth management, banking, investment tracking) require comprehensive financial analytics: cash flow tracking, savings rate calculations, spending pattern analysis, portfolio performance metrics, and growth projections. Teams building these applications need production-ready analytics primitives that work across multiple use cases without reimplementing standard financial calculations.

**Requirements**:
1. **Cash flow analysis**: Income vs expenses with category breakdowns
2. **Savings rate**: Multiple calculation methods (gross, net, discretionary) with trends
3. **Spending insights**: Pattern detection, merchant analysis, anomaly detection
4. **AI-powered advice**: LLM-generated personalized spending recommendations
5. **Portfolio metrics**: Performance, allocation, returns (YTD, MTD, day change)
6. **Benchmark comparison**: Portfolio vs market indices (SPY, QQQ) with alpha/beta/Sharpe
7. **Growth projections**: Net worth forecasting with conservative/moderate/aggressive scenarios
8. **REST API**: FastAPI integration with OpenAPI documentation
9. **Generic design**: Serve ANY fintech app (not application-specific)
10. **Multi-provider**: Work with any banking/brokerage provider (Plaid, Teller, Alpaca, etc.)

## svc-infra Reuse Assessment

**MANDATORY: Complete BEFORE proposing solution**

### What was checked in svc-infra?
- [x] Searched svc-infra README for related functionality
- [x] Reviewed svc-infra modules: API (FastAPI ease, dual routers), cache, logging, observability, jobs
- [x] Checked svc-infra docs: API scaffolding, caching, observability, logging
- [x] Examined svc-infra source: `src/svc_infra/api/fastapi/`, `src/svc_infra/cache/`

### Findings
- **Does svc-infra provide this functionality?** Partially
- **What svc-infra provides**:
  - FastAPI scaffolding (`easy_service_app`, dual routers)
  - Caching decorators (`cache_read`, `cache_write`, TTL management)
  - HTTP utilities (retry with tenacity, timeout management)
  - Logging & observability (structured logs, Prometheus metrics)
  - Router patterns (`public_router`, `user_router`, `service_router`)
- **What svc-infra does NOT provide**:
  - Financial calculations (cash flow, savings rate, portfolio metrics, growth projections)
  - Financial data models (CashFlowAnalysis, SavingsRateData, PortfolioMetrics, etc.)
  - Provider integration patterns for financial APIs (banking, brokerage)
  - Domain-specific analytics logic (spending patterns, anomaly detection)

### Classification
- [x] Type C: Hybrid (use svc-infra for infrastructure, fin-infra for financial logic)

### Reuse Plan
```python
# Backend infrastructure (svc-infra)
from svc_infra.api.fastapi.dual.public import public_router  # No auth/DB dependencies
from svc_infra.cache import cache_read, cache_write, init_cache  # Caching
from svc_infra.logging import setup_logging  # Structured logging
from svc_infra.obs import add_observability  # Metrics/tracing

# Financial logic (fin-infra)
from fin_infra.analytics import easy_analytics, add_analytics  # Analytics engine
from fin_infra.analytics.models import (  # Financial models
    CashFlowAnalysis,
    SavingsRateData,
    SpendingInsight,
    PortfolioMetrics,
    GrowthProjection,
)
```

## ai-infra Reuse Assessment

**MANDATORY: Complete for LLM features**

### What was checked in ai-infra?
- [x] Reviewed ai-infra modules: llm (CoreLLM), conversation (FinancialPlanningConversation)
- [x] Checked ai-infra docs: LLM providers, structured output, conversation management
- [x] Examined ai-infra source: `src/ai_infra/llm/core.py`, `src/ai_infra/conversation/`

### Findings
- **Does ai-infra provide LLM infrastructure?** Yes (MUST USE)
- **What ai-infra provides**:
  - CoreLLM with multi-provider support (OpenAI, Anthropic, Google, etc.)
  - Structured output validation (`output_schema` parameter)
  - Conversation management (FinancialPlanningConversation)
  - Cost tracking, rate limiting, retry logic
- **What fin-infra provides**:
  - Financial-specific prompts (few-shot examples with merchant names, spending patterns)
  - Financial output schemas (PersonalizedSpendingAdvice, CategoryPrediction)
  - Financial context aggregation (spending data, account balances for LLM inputs)

### Reuse Plan
```python
# LLM infrastructure (ai-infra - MANDATORY)
from ai_infra.llm import CoreLLM  # Never build custom LLM client
from ai_infra.conversation import FinancialPlanningConversation  # Multi-turn dialogue

# Financial prompts and schemas (fin-infra)
from fin_infra.analytics.advice import generate_spending_advice  # Financial prompt
from fin_infra.analytics.models import PersonalizedSpendingAdvice  # Output schema
```

## Decision

**fin-infra will implement**:

1. **AnalyticsEngine**: Core calculation engine
   - `cash_flow()`: Income/expense aggregation with category breakdowns
   - `savings_rate()`: Multiple calculation methods (gross, net, discretionary)
   - `spending_insights()`: Pattern detection, merchant analysis, anomaly detection
   - `spending_advice()`: LLM-powered recommendations (uses ai-infra CoreLLM)
   - `portfolio()`: Performance metrics, asset allocation
   - `performance()`: Benchmark comparison (alpha, beta, Sharpe ratio)
   - `forecast_net_worth()`: Growth projections with compound interest

2. **FastAPI Integration**: `add_analytics()`
   - 7 RESTful endpoints with OpenAPI documentation
   - Uses svc-infra `public_router` (no auth/DB dependencies)
   - Request validation with Pydantic models
   - Exception handling (ValueError → HTTPException 400)
   - Registers scoped docs for landing page card

3. **Financial Models**: Pydantic schemas
   - `CashFlowAnalysis`: Income, expenses, net flow, category breakdowns
   - `SavingsRateData`: Rate, amount, trend, historical rates
   - `SpendingInsight`: Top merchants, category breakdown, anomalies, trends
   - `PersonalizedSpendingAdvice`: Observations, opportunities, habits, alerts (LLM output)
   - `PortfolioMetrics`: Total value, returns, allocation
   - `BenchmarkComparison`: Alpha, beta, Sharpe ratio
   - `GrowthProjection`: Conservative/moderate/aggressive scenarios

4. **Provider Abstraction**: Works with ANY provider
   - Banking: Plaid, Teller, MX (transactions, accounts)
   - Brokerage: Alpaca, Interactive Brokers, SnapTrade (holdings, performance)
   - Categorization: Rule-based or ML models
   - Market data: Alpha Vantage, Yahoo, Polygon (benchmarks)

5. **Calculation Methodologies**:
   - **Cash Flow**: `Net = Income - Expenses` (excludes transfers, pending)
   - **Savings Rate**:
     - GROSS: `(Income - Expenses) / Gross Income`
     - NET: `(Income - Expenses) / Net Income (after tax)`
     - DISCRETIONARY: `(Income - Expenses) / Discretionary Income (after necessities)`
   - **Anomaly Detection**: `(Current - Average) / Average > 0.25` (25% threshold)
   - **Trend Analysis**: Linear regression on last 6 months (slope > 0.1 = increasing)
   - **Portfolio Returns**: `(Current - Cost Basis) / Cost Basis`
   - **Alpha**: `Portfolio Return - (Risk-Free Rate + Beta * Benchmark Return)`
   - **Beta**: `Covariance(Portfolio, Benchmark) / Variance(Benchmark)`
   - **Sharpe Ratio**: `(Portfolio Return - Risk-Free Rate) / Portfolio StdDev`
   - **Growth Projections**: `FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]`

6. **Caching Strategy** (svc-infra):
   - Real-time metrics: 1 hour TTL (cash flow, savings rate, portfolio)
   - Historical insights: 24 hours TTL (spending insights, spending advice)
   - Projections: 7 days TTL (assumptions rarely change)
   - Keyword-only args for cache key stability

7. **AI Integration** (ai-infra):
   - `spending_advice()` uses ai-infra CoreLLM (MANDATORY)
   - Structured output with PersonalizedSpendingAdvice schema
   - 24h cache to minimize LLM costs (<$0.10/user/month)
   - Fallback to rule-based insights if LLM fails
   - Financial-specific prompts with few-shot examples (fin-infra)

**svc-infra will provide**:
- FastAPI routing (`public_router` for no-auth endpoints)
- Caching infrastructure (Redis, decorators, TTL)
- Logging (structured, environment-aware)
- Observability (Prometheus metrics, Grafana dashboards)
- HTTP utilities (retry logic, timeout management)

**ai-infra will provide**:
- LLM inference (CoreLLM with multi-provider support)
- Structured output validation (`output_schema`)
- Conversation management (FinancialPlanningConversation)
- Cost tracking, rate limiting, retry logic

## Consequences

### Positive
- **Reusability**: Serves ANY fintech app (personal finance, wealth management, banking, investment)
- **Production-ready**: Standard financial calculations with test coverage
- **Easy integration**: One-liner FastAPI setup (`add_analytics(app)`)
- **Multi-provider**: Works with Plaid, Teller, Alpaca, any provider
- **Caching**: Intelligent TTLs reduce provider API costs
- **AI-powered**: LLM advice via ai-infra (no custom LLM client)
- **Type-safe**: Full Pydantic models with OpenAPI validation
- **Scalable**: Stateless, horizontally scalable (no DB dependencies)
- **Generic design**: Not tied to specific applications or workflows
- **svc-infra integration**: Leverages battle-tested backend infrastructure
- **ai-infra integration**: Leverages production LLM infrastructure

### Negative
- **LLM costs**: Spending advice incurs LLM fees (mitigated by 24h cache, target <$0.10/user/month)
- **Provider dependencies**: Requires banking/brokerage providers for data
- **Calculation assumptions**: Projections based on assumptions (returns can't be predicted)
- **Cache invalidation**: User must force refresh after account changes

### Neutral
- Analytics module is read-only (no writes to banking/brokerage)
- All data comes from providers (no persistent storage)
- LLM advice requires ai-infra setup (optional, falls back to rule-based)

## Implementation Notes

### svc-infra Integration

**Modules to import**:
```python
from svc_infra.api.fastapi.dual.public import public_router  # No auth
from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs  # Landing page card
from svc_infra.cache import cache_read, cache_write, init_cache
from svc_infra.logging import setup_logging
from svc_infra.obs import add_observability
```

**Configuration**:
```python
# Backend setup (svc-infra)
setup_logging()
init_cache(url="redis://localhost", prefix="fin", version="1")
app = easy_service_app(name="FinanceAPI")
add_observability(app)

# Analytics (fin-infra)
analytics = add_analytics(app, prefix="/analytics")
```

**Example code**:
```python
from fastapi import FastAPI, HTTPException
from svc_infra.api.fastapi.dual.public import public_router
from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
from fin_infra.analytics import easy_analytics
from fin_infra.analytics.models import CashFlowAnalysis

def add_analytics(app: FastAPI, provider=None, prefix="/analytics"):
    analytics = provider or easy_analytics()
    router = public_router(prefix=prefix, tags=["Analytics"])
    
    @router.get("/cash-flow", response_model=CashFlowAnalysis)
    async def get_cash_flow(user_id: str, period_days: int = 30):
        try:
            return await analytics.cash_flow(user_id=user_id, period_days=period_days)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    app.include_router(router, include_in_schema=True)
    add_prefixed_docs(app, prefix=prefix, title="Analytics", auto_exclude_from_root=True)
    app.state.analytics = analytics
    return analytics
```

### ai-infra Integration

**Modules to import**:
```python
from ai_infra.llm import CoreLLM  # MANDATORY for LLM calls
from ai_infra.conversation import FinancialPlanningConversation  # Multi-turn
```

**Configuration**:
```python
# LLM setup (ai-infra)
llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")

# Analytics with LLM (fin-infra)
analytics = easy_analytics(llm=llm)
```

**Example code**:
```python
from ai_infra.llm import CoreLLM
from fin_infra.analytics import easy_analytics

# Spending advice with LLM (ai-infra provides CoreLLM)
analytics = easy_analytics()
advice = await analytics.spending_advice(
    user_id="user_123",
    period_days=30,
)

# fin-infra provides financial prompt + schema
# ai-infra provides LLM inference + structured output
# Result: PersonalizedSpendingAdvice with observations, opportunities, habits
```

### fin-infra Implementation

**New modules**:
- `src/fin_infra/analytics/`
  - `core.py`: AnalyticsEngine with 7 calculation methods
  - `add.py`: FastAPI integration with add_analytics()
  - `models.py`: Pydantic schemas (7 models)
  - `cash_flow.py`: Cash flow calculations
  - `spending.py`: Spending insights and advice (with LLM)
  - `portfolio.py`: Portfolio performance metrics
  - `projections.py`: Growth projections with compound interest

**Provider adapters**: None (uses existing banking, brokerage, categorization providers)

**Tests required**:
- Unit tests: `tests/unit/analytics/` (207 tests)
  - test_cash_flow.py (40 tests)
  - test_spending.py (60 tests)
  - test_portfolio.py (50 tests)
  - test_projections.py (57 tests)
- Integration tests: `tests/integration/test_analytics_api.py` (22 tests)
  - Test all 7 endpoints with TestClient
  - Request validation
  - Error handling
  - Provider integration
- Acceptance tests: `tests/acceptance/test_analytics.py`
  - Test with real providers (Plaid, Alpaca)
  - LLM integration (ai-infra CoreLLM)

**Coverage target**: >80% (currently 229 tests passing)

## Alternative Considered: Custom LLM Client

**Rejected**: Building custom LLM client in fin-infra

**Why rejected**:
- ai-infra already provides production-ready CoreLLM
- Duplicating LLM infrastructure violates DRY principle
- ai-infra handles multi-provider, retry, cost tracking, structured output
- fin-infra only needs to provide financial prompts and schemas

**Correct approach**: Use ai-infra CoreLLM, fin-infra provides prompts

## Alternative Considered: user_router for Authentication

**Rejected**: Using svc-infra `user_router` for analytics endpoints

**Why rejected**:
- `user_router` requires database dependency (user authentication)
- Analytics is read-only and doesn't need per-user auth at API level
- Applications can implement their own auth layer on top
- `public_router` with `user_id` as query param is simpler and more flexible

**Correct approach**: Use `public_router`, applications add auth if needed

## References

- **Analytics Documentation**: `src/fin_infra/docs/analytics.md`
- **svc-infra API Docs**: `svc-infra/src/svc_infra/api/fastapi/README.md`
- **svc-infra Cache Docs**: `svc-infra/src/svc_infra/cache/README.md`
- **ai-infra LLM Docs**: `ai-infra/src/ai_infra/llm/README.md`
- **Net Worth ADR**: `src/fin_infra/docs/adr/0020-net-worth-tracking.md`
- **Categorization ADR**: `src/fin_infra/docs/adr/0018-transaction-categorization.md`
- **LLM Insights ADR**: `src/fin_infra/docs/adr/0021-net-worth-llm-insights.md`

---

**Implementation Status**: ✅ Complete
**Test Coverage**: 229 tests (207 unit, 22 integration)
**Documentation**: ✅ analytics.md (500+ lines)
