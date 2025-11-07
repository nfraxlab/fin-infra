# Conversation & AI Chat Architecture Audit

**Date**: 2025-11-07  
**Auditor**: Architecture Team  
**Scope**: Ensure all chat/conversation AI capabilities are centralized in `src/fin_infra/conversation/`

---

## Executive Summary

✅ **AUDIT PASSED**: All user-facing chat and conversation AI capabilities are properly centralized in `src/fin_infra/conversation/` with NO duplication.

### Key Findings

1. **✅ Single Source of Truth**: `src/fin_infra/conversation/` is the ONLY location for multi-turn user conversation with LLMs
2. **✅ Clear Boundary**: Other LLM usage (categorization, insights, normalization) is single-shot inference, NOT conversation
3. **✅ Proper Reuse**: All conversation code uses `ai-infra.llm.CoreLLM` (no duplication of LLM infrastructure)
4. **✅ Correct Imports**: `net_worth/ease.py` correctly imports from `fin_infra.conversation` (not duplicating code)

---

## 1. Conversation Capabilities Inventory

### 1.1 Root-Level Conversation Domain ✅ CORRECT LOCATION

**Path**: `src/fin_infra/conversation/`

**Files**:
- `planning.py` (~464 lines): `FinancialPlanningConversation` class
- `__init__.py`: Public API exports
- `ease.py`: `easy_financial_conversation()` builder

**Purpose**: General-purpose financial planning Q&A (NOT domain-specific)

**Features**:
- Multi-turn context management (10-turn history, 24h cache via svc-infra)
- Safety filters (SSN, passwords, account numbers)
- Session management (session_id, user_id)
- Follow-up question suggestions
- Source citations

**Scope**: Cross-domain (works for net worth, budgeting, spending, debt, tax, etc.)

**LLM Integration**:
```python
# Uses ai-infra CoreLLM (no duplication)
from ai_infra.llm import CoreLLM

structured = self.llm.with_structured_output(
    provider=self.provider,
    model_name=self.model_name,
    schema=ConversationResponse,
    method="json_mode",
)
response: ConversationResponse = await structured.ainvoke(messages)
```

**Cost**: ~$0.018/user/month (2 conversations × 10 turns with caching)

---

## 2. Other LLM Usage (NOT Conversation) ✅ CORRECT

### 2.1 Transaction Categorization (Single-Shot Inference)

**Path**: `src/fin_infra/categorization/llm_layer.py`

**Purpose**: Classify single transaction into spending category

**NOT Conversation Because**:
- ❌ No multi-turn context (one merchant → one category)
- ❌ No user dialogue (system categorizes, no back-and-forth)
- ❌ No session management (stateless classification)
- ✅ Correctly uses `ai-infra.llm.CoreLLM.achat()` for single inference

**Example**:
```python
# Single-shot: merchant name → category
response = await self.llm.achat(
    user_msg="Categorize: STARBUCKS",
    system=SYSTEM_PROMPT,
    output_schema=CategoryPrediction,
    ...
)
# Returns: {"category": "Coffee & Cafes", "confidence": 0.95}
```

**Verdict**: ✅ Correctly NOT in conversation/ (this is single-shot classification, not multi-turn chat)

---

### 2.2 Net Worth Insights (Single-Shot Analysis)

**Path**: `src/fin_infra/net_worth/insights.py`

**Purpose**: Generate financial insights from net worth snapshots

**NOT Conversation Because**:
- ❌ No multi-turn context (one snapshot → one insight)
- ❌ No user dialogue (system analyzes, no Q&A)
- ❌ No session management (stateless analysis)
- ✅ Correctly uses `ai-infra.llm.CoreLLM.with_structured_output()` for single inference

**Example**:
```python
# Single-shot: snapshots → insight
result: WealthTrendAnalysis = await structured.ainvoke(messages)
# Returns: {"summary": "Net worth increased 15%...", "recommendations": [...]}
```

**Verdict**: ✅ Correctly NOT in conversation/ (this is single-shot analysis, not multi-turn chat)

---

### 2.3 Merchant Normalization (Single-Shot Inference)

**Path**: `src/fin_infra/recurring/normalizers.py`

**Purpose**: Normalize merchant names (e.g., "AMZN*MARKETPLACE" → "Amazon")

**NOT Conversation Because**:
- ❌ No multi-turn context (one raw name → one normalized name)
- ❌ No user dialogue (system normalizes, no interaction)
- ❌ No session management (stateless normalization)
- ✅ Correctly uses `ai-infra.llm.CoreLLM.achat()` for single inference

**Example**:
```python
# Single-shot: raw name → normalized name
response = await self.llm.achat(
    user_msg="Normalize: AMZN*MKTP US*AB3CD4E5F",
    system=SYSTEM_PROMPT,
    output_schema=MerchantNormalized,
    ...
)
# Returns: {"normalized_name": "Amazon", "merchant_type": "E-commerce"}
```

**Verdict**: ✅ Correctly NOT in conversation/ (this is single-shot normalization, not multi-turn chat)

---

### 2.4 Subscription Insights (Single-Shot Analysis)

**Path**: `src/fin_infra/recurring/insights.py`

**Purpose**: Generate insights about user's subscriptions

**NOT Conversation Because**:
- ❌ No multi-turn context (one subscription list → one insight)
- ❌ No user dialogue (system analyzes, no Q&A)
- ❌ No session management (stateless analysis)
- ✅ Correctly uses `ai-infra.llm.CoreLLM.achat()` for single inference

**Example**:
```python
# Single-shot: subscriptions → insights
response = await self.llm.achat(
    user_msg="Analyze subscriptions: [...5 streaming services...]",
    system=SYSTEM_PROMPT,
    output_schema=SubscriptionInsights,
    ...
)
# Returns: {"summary": "You spend $65/month on streaming...", "recommendations": [...]}
```

**Verdict**: ✅ Correctly NOT in conversation/ (this is single-shot analysis, not multi-turn chat)

---

### 2.5 Variable Recurring Detection (Single-Shot Inference)

**Path**: `src/fin_infra/recurring/detectors_llm.py`

**Purpose**: Detect variable recurring patterns (e.g., fluctuating utility bills)

**NOT Conversation Because**:
- ❌ No multi-turn context (one transaction set → one pattern)
- ❌ No user dialogue (system detects, no interaction)
- ❌ No session management (stateless detection)
- ✅ Correctly uses `ai-infra.llm.CoreLLM.achat()` for single inference

**Example**:
```python
# Single-shot: transactions → pattern
response = await self.llm.achat(
    user_msg="Detect pattern: [ELECTRIC_CO $78, $82, $75, $79]",
    system=SYSTEM_PROMPT,
    output_schema=VariableRecurringPattern,
    ...
)
# Returns: {"is_variable_recurring": true, "pattern": "monthly_variable"}
```

**Verdict**: ✅ Correctly NOT in conversation/ (this is single-shot detection, not multi-turn chat)

---

### 2.6 Goal Tracking (Single-Shot Validation)

**Path**: `src/fin_infra/net_worth/goals.py`

**Purpose**: Validate financial goals and track progress

**NOT Conversation Because**:
- ❌ No multi-turn context (one goal → one validation)
- ❌ No user dialogue (system validates, no back-and-forth)
- ❌ No session management (stateless validation)
- ✅ Correctly uses `ai-infra.llm.CoreLLM.with_structured_output()` for single inference
- ✅ Correctly does LOCAL MATH first, then uses LLM for context (don't trust LLM for calculations)

**Example**:
```python
# Local calculation first
local_result = calculate_retirement_goal(...)  # FV = PV × (1+r)^n + PMT × ...

# Then LLM provides context around the numbers
structured = self.llm.with_structured_output(schema=GoalValidation)
result: GoalValidation = await structured.ainvoke(messages)
# Returns: {"feasibility": "feasible", "recommendations": [...], "confidence": 0.89}
```

**Verdict**: ✅ Correctly NOT in conversation/ (this is single-shot validation, not multi-turn chat)

---

## 3. Import Analysis ✅ NO DUPLICATION

### 3.1 Net Worth Easy Builder Imports Conversation Correctly

**File**: `src/fin_infra/net_worth/ease.py`

**Import**:
```python
from fin_infra.conversation import FinancialPlanningConversation
```

**Usage**:
```python
# Creates conversation instance (does NOT duplicate code)
conversation = FinancialPlanningConversation(
    llm=llm,
    cache=cache,  # Required for context storage
    provider=llm_provider,
    model_name=model_name,
)

# Passes to NetWorthTracker
tracker = NetWorthTracker(
    ...,
    conversation=conversation,  # Injects conversation capability
)
```

**Verdict**: ✅ Correctly imports from `fin_infra.conversation` (no duplication, proper reuse)

---

## 4. Architecture Boundary Validation ✅ CORRECT

### 4.1 Root-Level vs Domain-Specific Separation

**Root-Level** (`src/fin_infra/conversation/`):
- ✅ General-purpose financial planning Q&A
- ✅ Works across ALL fin-infra domains (net worth, budgeting, spending, debt)
- ✅ Reusable primitive (like svc-infra cache/api/jobs)
- ✅ Multi-turn dialogue with session management

**Domain-Specific** (e.g., `src/fin_infra/net_worth/`):
- ✅ Net worth calculation (aggregator.py)
- ✅ Net worth insights (insights.py) - single-shot analysis
- ✅ Goal tracking (goals.py) - single-shot validation
- ✅ Uses conversation by importing (ease.py)

**Follows svc-infra Pattern**:
- Root-level: `cache/`, `api/`, `jobs/`, `logging/` (cross-domain)
- Domain-specific: `auth/`, `payments/`, `webhooks/` (feature-specific)

**Verdict**: ✅ Architecture boundary is correct and consistent with svc-infra

---

## 5. AI-Infra Reuse Validation ✅ CORRECT

### 5.1 All Conversation Uses ai-infra CoreLLM

**File**: `src/fin_infra/conversation/planning.py`

**Imports**:
```python
# NO duplication - uses ai-infra
from ai_infra.llm import CoreLLM

# Uses CoreLLM.with_structured_output
structured = self.llm.with_structured_output(
    provider=self.provider,
    model_name=self.model_name,
    schema=ConversationResponse,
    method="json_mode",
)

# Uses CoreLLM.ainvoke
response: ConversationResponse = await structured.ainvoke(messages)
```

**Verdict**: ✅ Correctly reuses ai-infra (no LLM infrastructure duplication)

---

### 5.2 All Other LLM Usage Also Reuses ai-infra

**Categorization** (`categorization/llm_layer.py`):
```python
from ai_infra.llm import CoreLLM
response = await self.llm.achat(...)  # ✅ Uses ai-infra
```

**Insights** (`net_worth/insights.py`):
```python
from ai_infra.llm import CoreLLM
structured = self.llm.with_structured_output(...)  # ✅ Uses ai-infra
```

**Normalization** (`recurring/normalizers.py`):
```python
from ai_infra.llm import CoreLLM
response = await self.llm.achat(...)  # ✅ Uses ai-infra
```

**Goal Tracking** (`net_worth/goals.py`):
```python
from ai_infra.llm import CoreLLM
structured = self.llm.with_structured_output(...)  # ✅ Uses ai-infra
```

**Verdict**: ✅ ALL LLM usage correctly reuses ai-infra (zero duplication)

---

## 6. Conversation vs Single-Shot Criteria

### Definition: What Makes Something "Conversation"?

**Conversation** (belongs in `conversation/`):
- ✅ Multi-turn context (remembers previous exchanges)
- ✅ Session management (session_id, user tracking)
- ✅ User dialogue (back-and-forth Q&A)
- ✅ Context storage (cache previous turns)
- ✅ Follow-up questions (proactive engagement)

**Single-Shot Inference** (belongs in domain-specific modules):
- ✅ Stateless (one input → one output)
- ✅ No session (doesn't remember previous calls)
- ✅ No dialogue (system performs task, no Q&A)
- ✅ Deterministic context (same input → same output)

### Current Implementation Matches Criteria

| Module | Type | Multi-Turn? | Session? | Dialogue? | Location | Verdict |
|--------|------|-------------|----------|-----------|----------|---------|
| `conversation/planning.py` | Conversation | ✅ Yes | ✅ Yes | ✅ Yes | `conversation/` | ✅ CORRECT |
| `categorization/llm_layer.py` | Single-Shot | ❌ No | ❌ No | ❌ No | `categorization/` | ✅ CORRECT |
| `net_worth/insights.py` | Single-Shot | ❌ No | ❌ No | ❌ No | `net_worth/` | ✅ CORRECT |
| `net_worth/goals.py` | Single-Shot | ❌ No | ❌ No | ❌ No | `net_worth/` | ✅ CORRECT |
| `recurring/normalizers.py` | Single-Shot | ❌ No | ❌ No | ❌ No | `recurring/` | ✅ CORRECT |
| `recurring/insights.py` | Single-Shot | ❌ No | ❌ No | ❌ No | `recurring/` | ✅ CORRECT |
| `recurring/detectors_llm.py` | Single-Shot | ❌ No | ❌ No | ❌ No | `recurring/` | ✅ CORRECT |

**Verdict**: ✅ All modules are correctly categorized (conversation vs single-shot)

---

## 7. Documentation Alignment ✅ CORRECT

### 7.1 ADR-0021 Documents Conversation Scope

**File**: `src/fin_infra/docs/adr/0021-net-worth-llm-insights.md`

**Key Section**:
```markdown
### Layer 4: LLM Conversation (V2, Multi-Turn Q&A)

**⚠️ SCOPE UPDATE (2025-11-07)**: This layer has been **refactored to root-level** 
`src/fin_infra/conversation/` directory.

**Rationale**: Financial planning conversation is GENERAL (not net-worth-specific):
- Answers questions about: saving, budgeting, debt, refinancing, retirement, tax planning
- Uses net worth as ONE data source among many (also spending, income, goals, debt)
- Reusable across ALL fin-infra domains (budgeting, spending analysis, debt management)
- Follows svc-infra pattern: root-level primitives (cache, api, jobs) vs domain-specific (auth, payments)
```

**Verdict**: ✅ Documentation correctly reflects architectural decision

---

### 7.2 Plans.md Tracks Refactoring

**File**: `.github/plans.md`

**Key Section**:
```markdown
- [x] Implement: conversation/ (REFACTORED from net_worth/)
  - **REFACTORED**: Moved from `src/fin_infra/net_worth/conversation.py` to `src/fin_infra/conversation/` (root-level domain)
    - Rationale: Conversation is GENERAL (not net-worth-specific) - works across all fin-infra domains
    - Files created: `conversation/planning.py` (~464 lines), `conversation/__init__.py`, `conversation/ease.py`
    - Import updated in `net_worth/ease.py`: `from fin_infra.conversation import FinancialPlanningConversation`
```

**Verdict**: ✅ Plans correctly track refactoring from net_worth/ to conversation/

---

## 8. Recommendations for Future Development

### 8.1 Adding New LLM Features

**Decision Tree**:

```
Is this a multi-turn user dialogue?
├─ YES → Add to `src/fin_infra/conversation/`
│   └─ Examples: "Help me create a budget" (multi-turn), "Debt payoff advice" (back-and-forth)
│
└─ NO → Is it domain-specific or cross-domain?
    ├─ Domain-specific → Add to domain module (e.g., `net_worth/`, `categorization/`)
    │   └─ Examples: Net worth insights, transaction categorization
    │
    └─ Cross-domain → Create new root-level module
        └─ Examples: Risk scoring, fraud detection
```

### 8.2 Import Rules

**ALWAYS**:
```python
# ✅ CORRECT: Import ai-infra for LLM infrastructure
from ai_infra.llm import CoreLLM

# ✅ CORRECT: Import fin_infra.conversation for multi-turn dialogue
from fin_infra.conversation import FinancialPlanningConversation

# ✅ CORRECT: Import svc-infra for cache/jobs/webhooks
from svc_infra.cache import get_cache
```

**NEVER**:
```python
# ❌ WRONG: Don't duplicate LLM infrastructure
class MyCustomLLM:  # Use ai-infra.llm.CoreLLM instead!
    def chat(self, prompt): ...

# ❌ WRONG: Don't create parallel conversation classes
class BudgetingConversation:  # Use fin_infra.conversation instead!
    def ask(self, question): ...

# ❌ WRONG: Don't import conversation from domain-specific modules
from fin_infra.net_worth.conversation import ...  # Wrong path!
```

### 8.3 Testing Guidelines

**For Conversation** (`tests/unit/test_conversation.py`):
```python
# Mock ai-infra CoreLLM
@pytest.fixture
def mock_llm():
    llm = AsyncMock(spec=CoreLLM)
    # Mock with_structured_output
    structured = AsyncMock()
    structured.ainvoke.return_value = ConversationResponse(...)
    llm.with_structured_output.return_value = structured
    return llm

# Test multi-turn context
async def test_multi_turn_context(mock_llm, mock_cache):
    conversation = FinancialPlanningConversation(llm=mock_llm, cache=mock_cache)
    
    # First turn
    response1 = await conversation.ask("user_123", "How can I save more?")
    
    # Second turn (should use context)
    response2 = await conversation.ask("user_123", "What about my car loan?")
    
    # Verify context was loaded
    assert mock_cache.get.call_count == 2
```

**For Single-Shot Inference** (e.g., `tests/unit/test_insights.py`):
```python
# Mock ai-infra CoreLLM
@pytest.fixture
def mock_llm():
    llm = AsyncMock(spec=CoreLLM)
    structured = AsyncMock()
    structured.ainvoke.return_value = WealthTrendAnalysis(...)
    llm.with_structured_output.return_value = structured
    return llm

# Test single-shot (no context)
async def test_generate_wealth_trends(mock_llm):
    insights = NetWorthInsightsGenerator(llm=mock_llm)
    
    result = await insights.generate_wealth_trends(snapshots=[...])
    
    # Verify no session/context management
    assert llm.with_structured_output.call_count == 1  # Single call
```

---

## 9. Audit Checklist ✅ ALL PASSED

- [✅] **Single Source of Truth**: Only `src/fin_infra/conversation/` provides multi-turn user dialogue
- [✅] **No Duplication**: No parallel conversation classes in other modules
- [✅] **Correct Imports**: All modules import from `fin_infra.conversation` (not duplicating)
- [✅] **AI-Infra Reuse**: All LLM calls use `ai-infra.llm.CoreLLM` (no infrastructure duplication)
- [✅] **Clear Boundary**: Single-shot inference correctly placed in domain-specific modules
- [✅] **Architecture Alignment**: Follows svc-infra pattern (root-level vs domain-specific)
- [✅] **Documentation**: ADR-0021 and plans.md correctly document conversation scope
- [✅] **Future-Proof**: Decision tree and import rules documented for future development

---

## 10. Conclusion

**AUDIT RESULT**: ✅ **PASSED**

All chat and conversation AI capabilities are properly centralized in `src/fin_infra/conversation/` with:
- ✅ Zero duplication (single source of truth)
- ✅ Proper ai-infra reuse (no LLM infrastructure duplication)
- ✅ Clear architectural boundary (conversation vs single-shot inference)
- ✅ Correct imports (all modules reference `fin_infra.conversation`)
- ✅ Future-proof guidelines (decision tree, testing patterns)

**No Action Required**: Architecture is correct and consistent with project standards.

---

**Audit Complete**: 2025-11-07  
**Next Review**: When adding new LLM features (validate against decision tree)
