# 0028 — Advanced Features Design (Phase 3: Rebalancing, Insights, Crypto, Scenarios)

## Context

- **Phase 3** introduces four advanced financial features: Portfolio Rebalancing, Unified Insights Feed, Crypto Portfolio Insights (AI-powered), and Scenario Modeling.
- The codebase already provides foundational capabilities: banking (Plaid/Teller), markets (Alpha Vantage), categorization (ML + rules), net worth tracking, budgets, and goals.
- **Integration boundaries**: svc-infra provides backend infrastructure (API, cache, DB, logging), ai-infra provides LLM capabilities (CoreLLM), fin-infra provides financial logic.
- **Existing patterns**: `easy_*()` helpers for zero-config setup, `add_*()` helpers for FastAPI integration, Pydantic V2 models, comprehensive tests.

## Goals

- Define design patterns and trade-offs for Phase 3 features.
- Establish AI/LLM integration standards (when to use ai-infra CoreLLM vs rule-based logic).
- Document key architectural decisions (position_accounts workaround, compound interest formula, priority sorting).
- Ensure production-readiness with caching, cost management, and error handling guidelines.

## Non-goals

- Implement additional Phase 4 features (smart notifications, user preferences, multi-language support).
- Replace existing financial calculation libraries (use standard formulas: compound interest, FIFO/LIFO).
- Build custom LLM infrastructure (ai-infra CoreLLM handles all LLM calls).

## Decisions

### 1. Portfolio Rebalancing (`fin_infra.analytics.rebalancing`)

**Design**:
- **Algorithm**: Calculate target vs current allocation, generate trades to rebalance.
- **Tax Optimization**: Use FIFO or LIFO tax lot selection, estimate capital gains (15% rate), minimize taxable events.
- **Asset Class Mapping**: Use `position_accounts` parameter to map symbols to asset classes (e.g., `{"VTI": "stocks", "BTC": "crypto"}`).
  - **Rationale**: Positions don't inherently know their asset class; user/app must provide mapping.
  - **Alternative considered**: Hardcode asset class per symbol (rejected: not scalable, doesn't support new assets).
- **Trade Recommendations**: Generate BUY/SELL trades with quantities, reasoning, tax impact, and transaction costs.

**Production Considerations**:
- Cache rebalancing plans (1h TTL via svc-infra cache).
- Plans are recommendations, not automatic trades (users must review and execute via brokerage).
- Account for fractional shares (some brokerages support this).

**Tests**: 23 unit tests covering multi-asset portfolios, tax optimization, FIFO/LIFO, trade generation.

**Example**:
```python
plan = generate_rebalancing_plan(
    user_id="user_123",
    positions=[...],
    target_allocation={"stocks": 0.60, "crypto": 0.30, "bonds": 0.10},
    position_accounts={"VTI": "stocks", "BTC": "crypto", "AGG": "bonds"},
)
```

---

### 2. Unified Insights Feed (`fin_infra.insights`)

**Design**:
- **Multi-Source Aggregation**: Combine insights from net worth, budgets, goals, recurring patterns, portfolio, tax, and crypto.
- **Priority-Based Sorting**: CRITICAL > HIGH > MEDIUM > LOW (newest first within priority).
- **Category-Based Organization**: 8 categories (NET_WORTH, BUDGET, GOAL, RECURRING, PORTFOLIO, TAX, OPPORTUNITY, ALERT).
- **Pagination**: Server-side pagination with configurable page size (default: 20).

**Insight Generation Logic**:
- **Net Worth**: >5% month-over-month change triggers HIGH (positive) or MEDIUM (negative) insight.
- **Goals**: ≥100% progress → HIGH ("Goal Achieved"), ≥75% → MEDIUM ("Almost There").
- **Recurring**: Active subscriptions → MEDIUM ("Review if still needed").
- **Portfolio**: Rebalancing opportunities → HIGH.
- **Crypto**: AI-powered insights via ai-infra CoreLLM (see Crypto Insights section).

**Priority Filter Behavior**:
- `priority_filter="critical"`: Only CRITICAL insights.
- `priority_filter="high"`: HIGH + CRITICAL insights.
- `priority_filter="medium"`: MEDIUM + HIGH + CRITICAL insights.
- `priority_filter=None`: All insights.

**Production Considerations**:
- Cache individual data sources (goals, budgets, etc.) with appropriate TTLs.
- Insights are ephemeral (generated on-demand, not persisted to DB).
- Future: Add read/unread state, incremental updates, user preference filtering.

**Tests**: 15 unit tests covering aggregation logic, priority sorting, pagination, filtering.

**Example**:
```python
feed = aggregate_insights(
    user_id="user_123",
    goals=goals,
    budgets=budgets,
    recurring_patterns=recurring,
    priority_filter="high",
    page=1,
    page_size=20,
)
```

---

### 3. Crypto Portfolio Insights (`fin_infra.crypto.insights`)

**Design**:
- **Hybrid Approach**: Rule-based insights (allocation, performance) + AI-powered insights (risk, opportunities).
- **Rule-Based Insights** (deterministic, fast, no LLM):
  - **Allocation**: Concentration warnings (>50% in single asset), diversification suggestions.
  - **Performance**: Unrealized gains/losses, profit-taking opportunities (>20% gain).
- **AI-Powered Insights** (intelligent, personalized, uses ai-infra CoreLLM):
  - **LLM Provider**: ai-infra CoreLLM (NEVER custom LLM clients).
  - **Prompt Engineering**: Financial context (holdings, gains, total portfolio), safety disclaimers, output constraints.
  - **Natural Language**: Use natural dialogue (NO output_schema) for conversational recommendations.
  - **Safety**: Mandatory disclaimers ("Not financial advice"), no PII in prompts, no specific coin buy recommendations.

**AI Integration Standards** (MANDATORY for all LLM features):
- **Use ai-infra CoreLLM**: `from ai_infra.llm import CoreLLM; llm = CoreLLM()`
- **Structured vs Natural Dialogue**:
  - **Structured** (`output_schema=CategoryPrediction`): For data extraction, classification, validation.
  - **Natural** (no `output_schema`): For multi-turn conversation, explanations, recommendations.
- **Mock in Tests**: Always mock `CoreLLM.achat` with `unittest.mock.AsyncMock` (NEVER call real LLM in tests).
- **Cost Management**:
  - Track daily/monthly spend per user.
  - Cache LLM responses (24h TTL for insights, 7d for normalizations).
  - Target: <$0.10/user/month with caching.
  - Use cheaper models (Gemini Flash instead of GPT-4).

**Production Considerations**:
- **Graceful Degradation**: If LLM fails, fall back to rule-based insights only (pass `llm=None`).
- **Cost Optimization**: Cache crypto insights with 24h TTL (crypto advice changes slowly).
- **Compliance Logging**: Log all LLM calls (user_id, timestamp, prompt hash) via svc-infra structured logging.

**Tests**: 16 unit tests (all with mocked LLM calls, no real API usage).

**Example**:
```python
from ai_infra.llm import CoreLLM

llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")  # Cheap model
insights = await generate_crypto_insights(
    user_id="user_123",
    holdings=holdings,
    llm=llm,  # Optional: enables AI insights
    total_portfolio_value=total_portfolio_value,
)
```

---

### 4. Scenario Modeling (`fin_infra.analytics.scenarios`)

**Design**:
- **Projection Types**: 6 scenarios (retirement, savings goal, debt payoff, college savings, home purchase, investment).
- **Formula**: Future Value of Annuity (compound interest with contributions):
  ```
  FV = P(1+r)^n + PMT × [(1+r)^n - 1] / r
  ```
  Where: P = current_balance, PMT = monthly_contribution, r = monthly_return_rate, n = total_months.
- **Inflation Adjustment**: Apply inflation rate to final balance for purchasing power calculation.
- **Recommendations**: AI-generated suggestions based on goal achievement, contribution impact, return rate sensitivity.
  - **NOT LLM-generated** (rule-based logic with string templates).
  - Example: "Increasing contributions by $500/month adds $180,000 to your final balance."
- **Warnings**: Risk alerts for unrealistic returns, inflation impact, goal shortfall.

**Production Considerations**:
- Cache scenarios (24h TTL, deterministic calculations).
- Show conservative/moderate/aggressive projections (vary return rate).
- Always display inflation-adjusted values for long-term scenarios (>10 years).
- Visual charts: Use `data_points` array for line charts (balance over time).

**Tests**: 20 unit tests covering all 6 scenario types, compound interest accuracy, edge cases (negative contributions, zero balance).

**Example**:
```python
request = ScenarioRequest(
    type=ScenarioType.RETIREMENT,
    current_balance=50000,
    monthly_contribution=2000,
    years=30,
    annual_return_rate=0.07,
    goal_amount=1500000,
)

result = model_scenario(request)
print(f"Final Balance: ${result.final_balance:,.2f}")
print(f"Goal Achievement: {result.goal_achievement_pct:.1%}")
```

---

## Consequences

### Positive
- **Production-Ready**: All Phase 3 features have comprehensive tests, documentation, and examples.
- **Consistent Patterns**: All modules follow `easy_*()` and `add_*()` conventions for zero-config setup.
- **AI Integration**: Clear standards for when/how to use ai-infra CoreLLM (crypto insights: YES, scenario recommendations: NO).
- **Cost-Conscious**: LLM usage is optional, cached, and uses cheaper models (target: <$0.10/user/month).
- **Type Safety**: Pydantic V2 models, full mypy compliance, Decimal for financial calculations.

### Negative
- **position_accounts Complexity**: Users must manually map symbols to asset classes for rebalancing (not auto-detected).
  - **Mitigation**: Document clearly, provide examples, show error messages if mapping missing.
- **Budget Insights Stub**: Budget overspending insights not yet implemented (future enhancement).
- **No LLM Fallback for Scenarios**: Recommendations are rule-based strings, not intelligent AI suggestions.
  - **Rationale**: Scenarios are deterministic calculations; AI recommendations would be expensive and unnecessary.

### Risks
- **LLM Cost Overruns**: Without caching, crypto insights could cost $0.014 per generation (1 call per user per day = $0.42/month).
  - **Mitigation**: Mandatory 24h cache, use Gemini Flash ($0.001/1K tokens), nightly batch jobs.
- **Type Errors in Production**: mypy strictness may flag false positives (Pydantic optional fields, sum() type narrowing).
  - **Mitigation**: Added Pydantic mypy plugin, explicit type narrowing (`isinstance()`, `start=` param), `# type: ignore` for mock interfaces.

---

## Alternatives Considered

### Rebalancing: Automatic Trade Execution
**Rejected**: Rebalancing plans are recommendations, not automatic trades. Users must review and execute via brokerage API.  
**Rationale**: Legal/compliance risk (unauthorized trading), user trust (need review before execution), brokerage integration complexity.

### Insights Feed: Database Persistence
**Rejected**: Insights are generated on-demand, not stored in DB.  
**Rationale**: Ephemeral insights reduce storage costs, avoid stale data, simplify implementation. Future: Add read/unread state if needed.

### Crypto Insights: Rule-Based Only (No AI)
**Rejected**: AI-powered insights provide personalized, conversational recommendations that rule-based logic cannot match.  
**Rationale**: Users want strategic advice ("Should I take profits?"), not just data patterns. AI adds value. Cost is manageable with caching.

### Scenario Modeling: LLM-Generated Recommendations
**Rejected**: Scenarios use rule-based recommendation templates instead of LLM.  
**Rationale**: Deterministic calculations + string templates are cheaper, faster, and sufficient. LLM would add cost ($0.01/scenario) with minimal value gain.

---

## Follow-Ups (Phase 4)

### Insights Feed
- [ ] Add read/unread state (track last viewed timestamp, mark insights as read).
- [ ] Implement budget overspending insights (CRITICAL if >100%, HIGH if >80%).
- [ ] Add tax liability estimation insights (HIGH if >$10k estimated).
- [ ] User preference filtering (suppress low-priority categories per user).

### Crypto Insights
- [ ] Multi-turn conversation support (user asks follow-up questions about insights).
- [ ] Feedback loop (thumbs up/down on AI insights to improve relevance).
- [ ] Cost tracking dashboard (daily/monthly LLM spend per user).

### Rebalancing
- [ ] Auto-detect asset class from symbol (stocks/bonds/crypto heuristics).
- [ ] Multi-account rebalancing (taxable + IRA + 401k optimization).
- [ ] Fractional share support (explicit flag for brokerages that support it).

### Scenario Modeling
- [ ] LLM-powered "What if?" questions (e.g., "What if I lose my job for 6 months?").
- [ ] Monte Carlo simulations (probabilistic return rates instead of fixed rate).
- [ ] Visual scenario comparison (side-by-side conservative/moderate/aggressive).

---

## Documentation

- **insights.md**: Unified Insights Feed guide (694 lines, comprehensive).
- **analytics.md**: Updated with rebalancing + scenario modeling sections.
- **crypto.md**: New comprehensive guide with AI insights section (673 lines).
- **ADR 0028** (this document): Phase 3 design decisions and trade-offs.

---

## Testing Summary

| Module | Unit Tests | Coverage | Notes |
|--------|-----------|----------|-------|
| `rebalancing.py` | 23 | 100% | Multi-asset, tax optimization, FIFO/LIFO |
| `insights/aggregator.py` | 15 | 100% | Priority sorting, pagination, filtering |
| `crypto/insights.py` | 16 | 100% | All LLM calls mocked, no real API usage |
| `scenarios.py` | 20 | 100% | 6 scenario types, compound interest accuracy |
| **Total Phase 3** | **74** | **100%** | All tests passing in 0.18s |

**Quality Gates**:
- ✅ ruff format: 7 files reformatted
- ✅ ruff check: 3 linting errors fixed (unused imports/variables)
- ✅ mypy: 26 type errors fixed (Pydantic plugin, type narrowing, sum() start params)
- ✅ 281 tests passing (analytics + insights + crypto modules combined)

---

**Status**: ✅ Approved and Implemented (Phase 3 Complete)  
**Date**: 2025-01-27  
**Authors**: fin-infra maintainers  
**Reviewers**: svc-infra, ai-infra teams
