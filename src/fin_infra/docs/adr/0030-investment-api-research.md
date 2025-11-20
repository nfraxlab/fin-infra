# ADR 0030: Investment Holdings API Research

**Status**: Accepted  
**Date**: 2025-11-20  
**Owner**: fin-infra  
**Tags**: investments, providers, holdings, portfolio, plaid, snaptrade

## Context

fin-infra needs to provide READ-ONLY access to investment holdings and portfolio data to enable real P/L calculations, asset allocation analysis, and portfolio tracking. Current portfolio analytics (Module 1) only uses account balances without detailed holdings data (individual stocks/bonds/funds with quantity, cost basis, current value).

This module will serve:
- Personal finance apps (Mint, Personal Capital, etc.)
- Robo-advisors and wealth management platforms
- Investment tracking tools
- Portfolio analytics dashboards

Key requirements:
1. Access to detailed holdings (security, quantity, cost basis, current value)
2. Investment transaction history (buy/sell with dates, prices, fees)
3. Real-time or near-real-time data updates
4. Support for multiple account types (401k, IRA, retail brokerage)
5. Multi-provider architecture for maximum institution coverage

## svc-infra Reuse Assessment

**What was checked**:
- `svc-infra/src/svc_infra/billing/` - Usage tracking, subscriptions (NOT investment data)
- `svc-infra/src/svc_infra/cache/` - Cache infrastructure (REUSE for holdings/transactions caching)
- `svc-infra/src/svc_infra/db/` - Database utilities (REUSE for token storage)
- `svc-infra/src/svc_infra/logging/` - Structured logging (REUSE for provider call logging)
- `svc-infra/src/svc_infra/http/` - HTTP client with retry (REUSE for provider API calls)
- `svc-infra/src/svc_infra/security/` - Security primitives (REUSE for token encryption)

**Why svc-infra's solution wasn't suitable**:
- Investment aggregation providers (Plaid Investment API, SnapTrade) are financial domain-specific
- No generic backend infrastructure exists for holdings, securities, or portfolio data
- Provider-specific data structures require normalization (CUSIP, ISIN, ticker symbols)

**Classification**: Type C (Hybrid)
- Use svc-infra for infrastructure (caching, HTTP, security, logging)
- fin-infra implements provider integrations and data normalization

**Which svc-infra modules are being reused**:
```python
from svc_infra.cache import init_cache, cache_read, cache_write
from svc_infra.db import get_session  # For token storage
from svc_infra.logging import get_logger
from svc_infra.http import http_client_with_retry
from svc_infra.security import encrypt_token, decrypt_token
```

## Provider Research

### 1. Plaid Investment API

**Status**: PRIORITY 1 - IMPLEMENT FIRST

**Available Endpoints**:
- `/investments/holdings/get` - Holdings with security details, quantity, cost basis, current value
- `/investments/transactions/get` - Buy/sell transactions with dates, prices, fees
- `/investments/auth/get` - Investment account authentication

**Returned Data Structures**:

**Holdings**:
```json
{
  "accounts": [{
    "account_id": "...",
    "balances": {
      "available": 100.00,
      "current": 110.00,
      "limit": null
    },
    "name": "Plaid 401k",
    "type": "investment",
    "subtype": "401k"
  }],
  "holdings": [{
    "account_id": "...",
    "security_id": "...",
    "institution_price": 1.00,
    "institution_value": 1.00,
    "cost_basis": 1.00,
    "quantity": 1.00,
    "iso_currency_code": "USD",
    "unofficial_currency_code": null
  }],
  "securities": [{
    "security_id": "...",
    "cusip": "037833100",
    "isin": "US0378331005",
    "sedol": null,
    "ticker_symbol": "AAPL",
    "name": "Apple Inc.",
    "type": "equity",
    "close_price": 150.00,
    "close_price_as_of": "2025-11-19",
    "proxy_security_id": null,
    "institution_security_id": null,
    "institution_id": null
  }]
}
```

**Transactions**:
```json
{
  "investment_transactions": [{
    "investment_transaction_id": "...",
    "account_id": "...",
    "security_id": "...",
    "date": "2025-11-19",
    "name": "AAPL BUY",
    "quantity": 10.00,
    "amount": 1500.00,
    "price": 150.00,
    "fees": 0.00,
    "type": "buy",
    "subtype": "buy",
    "iso_currency_code": "USD",
    "unofficial_currency_code": null
  }]
}
```

**Data Quality**:
- Coverage: 15,000+ institutions (IRA, 401k, brokerage accounts)
- Update frequency: Daily for most institutions, real-time for some brokerages
- Historical depth: Varies by institution (typically 2+ years)
- Cost basis: Available for most accounts (depends on institution data)

**Security Types Supported**:
- `equity` - Common stock
- `etf` - Exchange-traded fund
- `mutual fund` - Mutual fund
- `derivative` - Options, futures
- `cash` - Cash/money market
- `other` - Miscellaneous

**Transaction Types Supported**:
- `buy` - Purchase of security
- `sell` - Sale of security
- `cancel` - Cancelled transaction
- `cash` - Cash transaction
- `fee` - Fee charged
- `transfer` - Transfer of holdings

**Best For**:
- Traditional investment accounts (401k, IRA, bank brokerage accounts)
- Applications requiring broad institutional coverage
- Daily data updates sufficient for most use cases

**SDK**: `plaid-python` (official, well-maintained)

**Pricing**: Per connection (~$0.10-0.30 per user/month in production)

**Auth Flow**: Link UI → public token → exchange for access token

**Rate Limits**: Generous (varies by endpoint, typically 1000s req/min)

**Security**: SOC 2 Type 2 compliant, bank-level encryption

---

### 2. SnapTrade API

**Status**: PRIORITY 1 - IMPLEMENT SECOND (HIGHEST VALUE for apps)

**Available Endpoints**:

**Investment Holdings (READ)**:
- `GET /accounts/{accountId}/positions` - Get positions/holdings for an account
- `GET /accounts/{accountId}/balances` - Get account balances
- `GET /accounts/{accountId}/orders` - Get order history
- `GET /accounts/{accountId}/transactions` - Get transaction history
- `GET /connections` - List connected brokerage accounts
- `GET /brokerageAuthorizations` - List user's brokerage connections

**Trading Operations (WRITE - for brokerage module)**:
- `POST /trade/impact` - Preview trade impact (estimated costs, P&L)
- `POST /trade/place` - Execute trade in user's existing account
- `GET /trade/{tradeId}` - Get trade status
- `POST /trade/{tradeId}/cancel` - Cancel pending order

**Returned Data Structures**:

**Positions/Holdings**:
```json
{
  "account": {
    "id": "...",
    "brokerage_name": "Robinhood",
    "account_type": "INDIVIDUAL",
    "sync_status": "SYNCED"
  },
  "positions": [{
    "symbol": {
      "id": "...",
      "symbol": "AAPL",
      "description": "Apple Inc.",
      "exchange": "NASDAQ",
      "type": "cs",
      "currency": "USD"
    },
    "quantity": 10.5,
    "price": 150.25,
    "market_value": 1577.63,
    "average_purchase_price": 145.00,
    "open_pnl": 55.13,
    "fractional_units": 0.5
  }]
}
```

**Transactions**:
```json
{
  "transactions": [{
    "id": "...",
    "account_id": "...",
    "symbol": "AAPL",
    "type": "BUY",
    "quantity": 10,
    "price": 145.00,
    "amount": 1450.00,
    "fees": 0.00,
    "settlement_date": "2025-11-22",
    "trade_date": "2025-11-19",
    "description": "Bought 10 AAPL @ $145.00"
  }]
}
```

**Data Quality**:
- Coverage: 125M+ retail brokerage accounts across 70+ brokerages
- Update frequency: Real-time or near-real-time for most retail brokerages
- Historical depth: Varies by brokerage (typically full history)
- Cost basis: `average_purchase_price` provided per position

**Supported Brokerages** (70+ total, key examples):
- **North America**: E*TRADE, TD Ameritrade, Wealthsimple, Questrade, Interactive Brokers
- **Europe**: Trading 212, Freetrade, eToro
- **Asia-Pacific**: Webull, Tiger Brokers
- **Read-only**: Robinhood (no developer API, OAuth read-only access)

**Per-Brokerage Capabilities**:

| Brokerage | Read Holdings | Execute Trades | Real-time | Notes |
|-----------|---------------|----------------|-----------|-------|
| E*TRADE | ✅ | ✅ | ✅ | Full support |
| Wealthsimple | ✅ | ✅ | ✅ | Full support |
| Questrade | ✅ | ✅ | ✅ | Full support |
| Webull | ✅ | ✅ | ✅ | Full support |
| Trading 212 | ✅ | ✅ | ✅ | Full support |
| Interactive Brokers | ✅ | ✅ | ✅ | Full support |
| Robinhood | ✅ | ❌ | ✅ | Read-only OAuth (no developer API) |
| TD Ameritrade | ✅ | ⚠️ | ✅ | Limited post-Schwab merger |

**Key Advantages**:
- **HYBRID provider**: Supports BOTH read (investments) and write (brokerage) operations
- **Existing accounts**: Trades in users' EXISTING accounts (vs Alpaca which creates new accounts)
- **Real-time data**: Near-instant updates vs Plaid's daily sync
- **Retail focus**: Covers retail brokerages that Plaid often doesn't (Robinhood, Wealthsimple, etc.)
- **Trading capabilities**: Same API for viewing AND trading (where supported)

**Best For**:
- Retail trading accounts with full read/write capabilities
- Applications requiring real-time portfolio updates
- Apps serving users with existing E*TRADE/Wealthsimple/Robinhood accounts
- Unified investment + trading experience

**CRITICAL for fin-infra**: Works with users' EXISTING accounts (aligns with fin-infra's mission to help apps integrate existing financial accounts)

**SDK**: `snaptrade-python-sdk` (official, actively maintained)

**Pricing**: Per connection (varies by tier, enterprise pricing available)

**Auth Flow**: SnapTrade Connect portal → OAuth → connection established

**Rate Limits**: Generous (custom per enterprise agreement)

**Security**: SOC 2 Type 2 compliant, bank-level encryption, OAuth (credentials never shared with app)

**Connection Method**:
1. App initiates connection via SnapTrade Connect URL
2. User authenticates directly with their brokerage (OAuth)
3. SnapTrade receives access token (app never sees credentials)
4. App calls SnapTrade API with connection_id to access data

---

### 3. Teller API

**Status**: FUTURE - Research for roadmap

**Current Focus**: Banking aggregation (checking/savings accounts)

**Investment Support**: Unknown (needs research)
- Teller documentation primarily focuses on banking accounts
- May not support investment holdings or securities data
- Check `/accounts` endpoint for investment account types

**Action Items**:
- [ ] Research if Teller supports investment account types
- [ ] Document any investment-specific endpoints if available
- [ ] Compare data structure to Plaid if investment support exists
- [ ] Determine if worth implementing vs Plaid/SnapTrade coverage

**Estimated Coverage**: Likely limited or none (banking-focused provider)

---

### 4. MX Platform

**Status**: FUTURE - Research for roadmap

**Current Focus**: Enterprise financial data aggregation

**Investment Support**: Likely available (research needed)
- MX is a comprehensive aggregation platform
- Likely supports investment accounts across 16,000+ institutions
- May overlap significantly with Plaid

**Action Items**:
- [ ] Document MX's investment aggregation capabilities
- [ ] Compare API structure to Plaid Investment API
- [ ] Analyze coverage overlap (which institutions Plaid doesn't cover)
- [ ] Evaluate SDK quality and ease of integration
- [ ] Determine pricing model (enterprise-only or per-connection)

**Estimated Coverage**: 16,000+ institutions (similar to Plaid)

---

### 5. Other Providers (FUTURE)

**Yodlee (Envestnet)**:
- Established aggregation provider
- Comprehensive investment data support
- Enterprise pricing
- Slower API responses reported by developers

**Finicity (Mastercard)**:
- Banking and investment aggregation
- Owned by Mastercard (enterprise focus)
- Good institutional coverage
- Complex pricing structure

**Alpaca** (EXCLUDED from investments module):
- Trading-only provider (no external account aggregation)
- Only works with NEW Alpaca-hosted accounts
- Covered by existing brokerage module
- NOT suitable for investment holdings module (can't read external accounts)

---

## Identified Gaps vs Real P/L Requirements

| Requirement | Plaid | SnapTrade | App Responsibility | Notes |
|-------------|-------|-----------|---------------------|-------|
| **Current value** | ✅ Yes (`institution_value`) | ✅ Yes (`market_value`) | - | Both provide real-time/daily |
| **Cost basis** | ✅ Yes (per holding) | ✅ Yes (`average_purchase_price`) | - | Available from providers |
| **Total return** | ✅ Calculated | ✅ Calculated (`open_pnl`) | Client-side | `value - cost_basis` |
| **Day change** | ❌ No | ⚠️ Real-time | App snapshots | Requires historical price tracking |
| **YTD/MTD returns** | ❌ No | ❌ No | App snapshots | Requires time-series data storage |
| **Beta/Sharpe ratio** | ❌ No | ❌ No | Market data module | Requires market benchmarks |
| **Dividend income** | ✅ Yes (transactions) | ✅ Yes (transactions) | - | Transaction type filtering |
| **Realized gains** | ✅ Yes (buy/sell tx) | ✅ Yes (tx history) | Client-side | Calculate from closed positions |
| **Unrealized gains** | ✅ Calculated | ✅ Provided (`open_pnl`) | - | Current vs cost basis |

**Key Findings**:
1. ✅ **Sufficient for basic P/L**: Both providers give current value and cost basis (essential)
2. ✅ **Transaction history**: Both provide buy/sell/dividend transactions for realized gains
3. ❌ **Day change tracking**: Requires app-side daily snapshots (not provider responsibility)
4. ❌ **Time-based returns**: Requires app-side time-series storage (YTD, MTD, 1Y, 5Y)
5. ❌ **Risk metrics**: Requires separate market data module (beta, Sharpe, volatility)

**Design Decision**: 
- Investments module provides holdings and transactions (sufficient for P/L)
- Apps are responsible for:
  - Daily snapshot storage (for day change tracking)
  - Time-series analysis (YTD/MTD returns)
  - Market data integration (beta, Sharpe ratio via separate module)

---

## Provider Comparison Matrix

| Feature | Plaid Investment | SnapTrade | Teller | MX | Alpaca |
|---------|------------------|-----------|--------|-----|--------|
| **Holdings data** | ✅ Yes | ✅ Yes | ❓ Unknown | ✅ Likely | ❌ No (new accounts only) |
| **Transactions** | ✅ Yes | ✅ Yes | ❓ Unknown | ✅ Likely | ✅ Yes (own accounts) |
| **Cost basis** | ✅ Yes | ✅ Yes (`avg_purchase_price`) | ❓ Unknown | ✅ Likely | ✅ Yes |
| **Trading capability** | ❌ No | ⚠️ Some brokerages* | ❌ No | ❌ No | ✅ Yes (new accounts) |
| **Update frequency** | Daily | Real-time | Daily | Daily | Real-time |
| **Institution coverage** | 15,000+ | 125M+ accounts (70+) | Limited | 16,000+ | N/A (own platform) |
| **Account types** | 401k, IRA, bank brokerage | Retail brokerage | Banking focus | All types | New accounts only |
| **Best for** | Traditional accounts | Retail traders | Banking | Enterprise | Paper/live trading |
| **Connection method** | Link UI (OAuth) | Portal/OAuth | Cert-based | OAuth | API keys |
| **SDK quality** | Excellent (official) | Excellent (official) | Good | Good | Excellent |
| **Pricing** | Per connection | Per connection | Per request | Enterprise | Free (trading commissions) |
| **Security** | SOC 2 Type 2 | SOC 2 Type 2 | Unknown | SOC 2 | SOC 2 |
| **Rate limits** | Generous (1000s/min) | Generous (custom) | 100 req/min | Custom | Generous |
| **Sandbox** | Full free sandbox | Developer sandbox | Full free sandbox | With account | Paper trading (free) |
| **Documentation** | Excellent | Excellent | Good | Good | Excellent |
| **Integration complexity** | Low | Low | Medium | Medium | Low |

**SnapTrade Trading Support** (varies by brokerage):
- ✅ **Full trading**: E*TRADE, Wealthsimple, Questrade, Webull, Trading 212, Interactive Brokers
- ❌ **Read-only**: Robinhood (no developer API, OAuth read-only access)
- ⚠️ **Limited**: TD Ameritrade (post-Schwab merger restrictions)

---

## Implementation Priority

**Phase 1: Core Providers (NOW)**
1. **Plaid Investment API** (IMPLEMENT FIRST)
   - Reason: Broadest institutional coverage (15,000+)
   - Best for: 401k, IRA, traditional brokerage accounts
   - Priority: CRITICAL (covers most users' retirement accounts)
   
2. **SnapTrade API** (IMPLEMENT SECOND - HIGHEST VALUE)
   - Reason: Covers retail brokerages Plaid doesn't (Robinhood, Wealthsimple, etc.)
   - Best for: Retail trading accounts with real-time updates
   - Priority: CRITICAL (covers most users' active trading accounts)
   - Bonus: Enables trading capability in brokerage module

**Phase 2: Extended Coverage (FUTURE)**
3. **Teller API** (if investment support exists)
   - Reason: Additional institution coverage, free tier for development
   - Priority: LOW (Plaid + SnapTrade likely sufficient)
   
4. **MX Platform** (enterprise customers)
   - Reason: Enterprise-grade aggregation, additional coverage
   - Priority: LOW (implement only if customer demand exists)

**Phase 3: Specialized Providers (ROADMAP)**
5. **Yodlee** (if customer demand)
6. **Finicity** (if customer demand)

**Excluded from Investments Module**:
- **Alpaca**: Trading-only (no external account aggregation), covered by brokerage module

---

## Strategic Insights

### Why SnapTrade is Critical for fin-infra

fin-infra's mission: **Help apps integrate users' EXISTING financial accounts**

**SnapTrade's unique value**:
1. ✅ Works with EXISTING retail brokerage accounts (Robinhood, E*TRADE, Wealthsimple, etc.)
2. ✅ Covers 125M+ retail accounts Plaid doesn't aggregate well
3. ✅ Real-time data (vs Plaid's daily sync)
4. ✅ HYBRID provider (read holdings AND execute trades in same account)
5. ✅ OAuth security (users authenticate directly, app never sees credentials)

**Alpaca's limitation**:
- ❌ Only works for NEW Alpaca-hosted accounts
- ❌ Requires users to onboard TO Alpaca (limited use case)
- ❌ Can't read users' existing E*TRADE/Robinhood/etc accounts
- ✅ Good for paper trading and apps that specifically use Alpaca platform

**Most apps should use**: Plaid (traditional accounts) + SnapTrade (retail accounts) = maximum user coverage

### Combined Coverage Strategy

**Plaid covers**:
- 401k accounts (employer retirement)
- IRA accounts (Fidelity, Vanguard, Schwab)
- Bank brokerage accounts (Chase YouInvest, Bank of America Merrill)
- Traditional brokerages with banking relationships

**SnapTrade covers**:
- Robinhood (NOT available via Plaid)
- Wealthsimple (Canadian retail)
- E*TRADE (better real-time than Plaid)
- Questrade, Webull, Trading 212
- Most retail brokerages with OAuth APIs

**Overlap**: Some brokerages available via both (E*TRADE, Interactive Brokers)
- Use SnapTrade for real-time, Plaid for daily is sufficient
- App can let users choose or auto-select based on account type

**Alpaca use case**: 
- Apps offering paper trading (simulated market)
- Apps that specifically onboard users TO Alpaca platform
- NOT for integrating existing accounts (different problem)

---

## Design Decisions

### 1. Provider Abstraction

Create `InvestmentProvider` ABC in `src/fin_infra/investments/providers/base.py`:

```python
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

class InvestmentProvider(ABC):
    """Abstract base class for investment aggregation providers."""
    
    @abstractmethod
    async def get_holdings(
        self, 
        access_token: str, 
        account_ids: Optional[List[str]] = None
    ) -> List[Holding]:
        """Fetch holdings for investment accounts.
        
        Args:
            access_token: Provider access token
            account_ids: Optional filter for specific accounts
            
        Returns:
            List of holdings with security details, quantity, cost basis, value
        """
        pass
    
    @abstractmethod
    async def get_transactions(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        account_ids: Optional[List[str]] = None
    ) -> List[InvestmentTransaction]:
        """Fetch investment transactions within date range.
        
        Args:
            access_token: Provider access token
            start_date: Start date for transaction history
            end_date: End date for transaction history
            account_ids: Optional filter for specific accounts
            
        Returns:
            List of buy/sell/dividend transactions
        """
        pass
    
    @abstractmethod
    async def get_securities(
        self,
        access_token: str,
        security_ids: List[str]
    ) -> List[Security]:
        """Fetch security details (ticker, name, type, current price).
        
        Args:
            access_token: Provider access token
            security_ids: List of security IDs to fetch
            
        Returns:
            List of security details
        """
        pass
    
    @abstractmethod
    async def get_investment_accounts(
        self,
        access_token: str
    ) -> List[InvestmentAccount]:
        """Fetch investment accounts with aggregated holdings.
        
        Args:
            access_token: Provider access token
            
        Returns:
            List of investment accounts with total value, cost basis, P&L
        """
        pass
    
    # Helper methods (concrete - shared across all providers)
    
    def calculate_allocation(self, holdings: List[Holding]) -> AssetAllocation:
        """Calculate asset allocation by security type and sector."""
        # Implementation in base class
        pass
    
    def calculate_portfolio_metrics(self, holdings: List[Holding]) -> dict:
        """Calculate total value, cost basis, unrealized gain/loss."""
        # Implementation in base class
        pass
    
    def _normalize_security_type(self, provider_type: str) -> SecurityType:
        """Map provider-specific security types to standard enum."""
        # Implementation in base class
        pass
```

### 2. Multi-Provider Support

**Priority 1: Plaid Implementation**
- File: `src/fin_infra/investments/providers/plaid.py`
- Class: `PlaidInvestmentProvider(InvestmentProvider)`
- SDK: `plaid-python`
- Endpoints: `/investments/holdings/get`, `/investments/transactions/get`

**Priority 2: SnapTrade Implementation**
- File: `src/fin_infra/investments/providers/snaptrade.py`
- Class: `SnapTradeInvestmentProvider(InvestmentProvider)`
- SDK: `snaptrade-python-sdk`
- Endpoints: `GET /accounts/{id}/positions`, `GET /accounts/{id}/transactions`
- Note: Same provider will be used in brokerage module for trading operations

**Future: Teller/MX**
- Design abstractions to accommodate if/when implemented

### 3. Data Normalization

**Challenge**: Each provider returns different data structures

**Solution**: Normalize to fin-infra models
- Plaid: `cusip/isin/sedol` → `Security.cusip/isin/sedol`
- SnapTrade: `symbol.symbol` → `Security.ticker_symbol`
- Plaid: `institution_value` → `Holding.institution_value`
- SnapTrade: `market_value` → `Holding.institution_value`
- Plaid: `type` (equity/etf/mutual fund) → `SecurityType` enum
- SnapTrade: `symbol.type` (cs/etf/mf) → `SecurityType` enum

**Implementation**: Provider-specific mappers in each provider class

### 4. Caching Strategy

**Holdings** (cache: 60 seconds):
- Reduce API calls during active browsing
- Balance freshness vs API costs
- SnapTrade: Real-time allows shorter TTL
- Plaid: Daily sync allows longer TTL

**Transactions** (cache: 300 seconds):
- Historical data changes infrequently
- 5-minute cache sufficient for most use cases
- Invalidate on date range change

**Securities** (cache: 3600 seconds):
- Security metadata (name, type, CUSIP) rarely changes
- Price updates handled separately (real-time or 60s)

**svc-infra integration**:
```python
from svc_infra.cache import cache_read, cache_write

# In provider implementation
async def get_holdings(self, access_token: str, account_ids: List[str]) -> List[Holding]:
    cache_key = f"holdings:{access_token}:{':'.join(account_ids or [])}"
    cached = await cache_read(cache_key)
    if cached:
        return cached
    
    # Fetch from provider API
    holdings = await self._fetch_holdings(access_token, account_ids)
    
    # Cache for 60 seconds
    await cache_write(cache_key, holdings, ttl=60)
    return holdings
```

---

## Consequences

### Positive

1. **Real P/L calculations**: Apps can display accurate portfolio performance
2. **Asset allocation**: Automatic breakdown by security type (equity, bond, ETF, etc.)
3. **Multi-provider flexibility**: Plaid + SnapTrade = maximum user coverage
4. **SnapTrade enables trading**: Same provider for read AND write (brokerage module)
5. **Real-time option**: SnapTrade provides real-time updates vs Plaid daily sync
6. **Existing account focus**: Aligns with fin-infra mission (integrate users' existing accounts)
7. **Future-proof**: Abstract base class allows easy addition of Teller/MX/others
8. **Production-ready**: Both Plaid and SnapTrade are SOC 2 compliant, battle-tested

### Negative

1. **Multiple SDK dependencies**: `plaid-python` + `snaptrade-python-sdk`
2. **API costs**: Per-connection pricing for both providers (Plaid ~$0.10-0.30/user/mo)
3. **Day change tracking**: Requires app-side daily snapshots (not provider responsibility)
4. **Time-series analysis**: Apps must store historical snapshots for YTD/MTD returns
5. **Provider-specific quirks**: SnapTrade trading varies by brokerage (Robinhood read-only)
6. **Coverage gaps**: Some institutions may not be supported by either provider

### Mitigations

1. **Lazy imports**: Only load provider SDKs when needed
2. **Caching**: Reduce API call frequency (60s holdings, 5min transactions)
3. **Clear documentation**: Guide apps on daily snapshot patterns
4. **Provider comparison**: ADR documents which provider covers which accounts
5. **Capability detection**: Document per-brokerage trading support (SnapTrade)
6. **Fallback patterns**: Try Plaid first, fall back to SnapTrade, handle missing data gracefully

---

## Real-World Usage Patterns

### Pattern 1: Personal Finance Dashboard (Plaid Only)

**User**: Has 401k (Fidelity) + IRA (Vanguard) + bank brokerage (Chase YouInvest)

**Solution**: Use Plaid Investment API
- Single provider covers all accounts
- Daily sync sufficient for retirement tracking
- Lower cost (one provider fee)

```python
from fin_infra.investments import easy_investments

investments = easy_investments(provider="plaid", api_key=plaid_key)
holdings = await investments.get_holdings(access_token)
allocation = investments.calculate_allocation(holdings)
metrics = investments.calculate_portfolio_metrics(holdings)
# Display: Total value, P&L, allocation breakdown
```

### Pattern 2: Retail Trading App (SnapTrade Only)

**User**: Has Robinhood + Webull + Wealthsimple (active trader)

**Solution**: Use SnapTrade
- Covers retail brokerages Plaid doesn't aggregate
- Real-time updates critical for active trading
- Same provider for viewing AND trading

```python
from fin_infra.investments import easy_investments
from fin_infra.brokerage import easy_brokerage

# View holdings (investments module)
investments = easy_investments(provider="snaptrade", client_id=st_client_id)
holdings = await investments.get_holdings(connection_id)

# Execute trade (brokerage module)
brokerage = easy_brokerage(provider="snaptrade", client_id=st_client_id)
order = await brokerage.submit_order(connection_id, symbol="AAPL", qty=10, side="buy")
```

### Pattern 3: Combined Coverage (Plaid + SnapTrade)

**User**: Has 401k (Fidelity) + Robinhood (active trading)

**Solution**: Use both providers for maximum coverage
- Plaid for 401k (traditional account)
- SnapTrade for Robinhood (retail brokerage)
- Merge holdings for unified view

```python
from fin_infra.investments import easy_investments

# Fetch from Plaid (401k)
plaid_inv = easy_investments(provider="plaid", api_key=plaid_key)
plaid_holdings = await plaid_inv.get_holdings(plaid_token)

# Fetch from SnapTrade (Robinhood)
st_inv = easy_investments(provider="snaptrade", client_id=st_client_id)
st_holdings = await st_inv.get_holdings(st_connection_id)

# Merge for unified portfolio view
all_holdings = plaid_holdings + st_holdings
total_metrics = plaid_inv.calculate_portfolio_metrics(all_holdings)
allocation = plaid_inv.calculate_allocation(all_holdings)
```

### Pattern 4: Paper Trading with Real Holdings (SnapTrade + Alpaca)

**User**: Has Robinhood (real account) + wants to paper trade strategies

**Solution**: SnapTrade for real holdings, Alpaca for paper trading
- View real Robinhood portfolio via SnapTrade
- Practice strategies in Alpaca paper account
- Compare paper vs real performance

```python
from fin_infra.investments import easy_investments
from fin_infra.brokerage import easy_brokerage

# Real holdings (SnapTrade)
st_inv = easy_investments(provider="snaptrade", client_id=st_client_id)
real_holdings = await st_inv.get_holdings(st_connection_id)

# Paper trading (Alpaca)
alpaca_broker = easy_brokerage(provider="alpaca", paper=True)
paper_positions = await alpaca_broker.positions()

# Compare strategies
real_total = sum(h.institution_value for h in real_holdings)
paper_total = sum(float(p['market_value']) for p in paper_positions)
```

### Pattern 5: Robo-Advisor (Plaid + SnapTrade + Optional Alpaca)

**User**: Has various accounts, wants automated portfolio management

**Solution**: Multi-provider strategy
- Plaid for 401k/IRA (view-only, manual rebalancing by user)
- SnapTrade for retail accounts (automated trading where supported)
- Alpaca for new managed accounts (if user opts in)

```python
from fin_infra.investments import easy_investments
from fin_infra.brokerage import easy_brokerage

# Aggregate all holdings
plaid_inv = easy_investments(provider="plaid", api_key=plaid_key)
st_inv = easy_investments(provider="snaptrade", client_id=st_client_id)

all_holdings = []
all_holdings += await plaid_inv.get_holdings(plaid_token)  # 401k/IRA (view-only)
all_holdings += await st_inv.get_holdings(st_connection_id)  # Robinhood (tradeable)

# Analyze allocation
allocation = plaid_inv.calculate_allocation(all_holdings)

# Rebalance tradeable accounts only (SnapTrade)
if allocation.equity_percent > 80:  # Too much equity
    st_broker = easy_brokerage(provider="snaptrade", client_id=st_client_id)
    # Execute rebalancing trades in Robinhood via SnapTrade
    await st_broker.submit_order(st_connection_id, symbol="BND", qty=100, side="buy")
```

**KEY INSIGHT**: Most apps want SnapTrade (existing accounts) not Alpaca (new accounts)

---

## Implementation Priority

**Order of implementation**:
1. **Plaid Investment Provider** (Week 1-2)
   - Covers most traditional accounts (401k, IRA)
   - Broadest institutional coverage
   - Well-documented, stable API
   
2. **SnapTrade Investment Provider** (Week 3-4)
   - Covers retail brokerages
   - Enables future trading capability
   - Real-time data advantage
   
3. **Brokerage Module Enhancement** (Week 5)
   - Add SnapTrade to brokerage module (reuse same provider class)
   - Document per-brokerage trading capabilities
   - Update easy_brokerage() to support SnapTrade
   
4. **Teller/MX** (Future - customer-driven)
   - Only if specific customer needs identified
   - Plaid + SnapTrade likely covers 95%+ of use cases

---

## Acceptance Criteria

- [x] Plaid Investment API capabilities documented
- [x] SnapTrade API capabilities documented
- [x] Teller API research plan documented
- [x] MX Platform research plan documented
- [x] Gaps identified (day change, YTD returns, risk metrics)
- [x] Provider comparison matrix created
- [x] Implementation priority established (Plaid first, SnapTrade second)
- [x] Real-world usage patterns documented
- [x] SnapTrade's strategic importance explained (existing accounts)
- [x] Alpaca exclusion rationale documented (new accounts only, not aggregation)
- [x] ADR 0030 created and accepted

---

## Related Documents

- ADR 0003: Banking Integration Architecture (similar provider pattern)
- ADR 0006: Brokerage Trade Execution (SnapTrade to be added for existing account trading)
- Module 1 analytics/portfolio.py (will consume this module's holdings data)
- .github/PLAN.md Module 2.1: Investment Holdings implementation tasks

---

## Next Steps

1. ✅ Complete Task 1 (Provider Research) - THIS DOCUMENT
2. ⏭️ Task 2: Create investments module structure
3. ⏭️ Task 3: Define Pydantic models (Security, Holding, InvestmentTransaction, etc.)
4. ⏭️ Task 4: Implement InvestmentProvider ABC
5. ⏭️ Task 5: Implement PlaidInvestmentProvider (FIRST)
6. ⏭️ Task 5b: Implement SnapTradeInvestmentProvider (SECOND, HIGH VALUE)
7. ⏭️ Task 6-11: easy_investments(), add_investments(), portfolio analytics, docs, ADRs

---

**Status**: ACCEPTED ✅  
**Next Action**: Begin Task 2 (create investments module structure)
