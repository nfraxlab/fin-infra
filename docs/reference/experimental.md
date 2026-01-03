# Experimental APIs

This page lists APIs that are considered experimental. Experimental APIs may change, be renamed, or be removed in minor versions without following the normal deprecation policy.

## What Does "Experimental" Mean?

Experimental APIs are:
- **Functional** and can be used in production at your own risk
- **Subject to change** without the standard 2-version deprecation period
- **Not yet battle-tested** in large-scale production environments
- **Seeking feedback** from early adopters

## Current Experimental APIs

### AI-Powered Categorization

**Status**: Experimental (since v0.1.80)

LLM-based transaction categorization with custom taxonomy support.

```python
from fin_infra.categorization import LLMCategorizer

categorizer = LLMCategorizer(taxonomy=custom_taxonomy)
category = await categorizer.categorize(transaction)
```

**Why experimental**:
- LLM provider integration is new
- Custom taxonomy format may evolve
- Accuracy benchmarks still being established

**Exports**:
- `LLMCategorizer`
- `CategoryTaxonomy`

### Cryptocurrency Module

**Status**: Experimental (since v0.1.75)

Cryptocurrency wallet and exchange integrations.

```python
from fin_infra.crypto import CryptoProvider

provider = CryptoProvider()
balance = await provider.get_balance(wallet_address)
```

**Why experimental**:
- Exchange APIs change frequently
- Blockchain integrations vary by chain
- Security model for key management evolving

**Exports**:
- `CryptoProvider`
- `WalletConnection`

### Tax Loss Harvesting

**Status**: Experimental (since v0.1.70)

Automated tax loss harvesting recommendations.

```python
from fin_infra.tax import find_tlh_opportunities

opportunities = await find_tlh_opportunities(
    positions=portfolio.positions,
    wash_sale_window=30
)
```

**Why experimental**:
- Tax rules vary by jurisdiction
- Wash sale detection algorithms being refined
- Integration with brokerage for execution is new

## Deprecated Aliases

The following are deprecated and will be removed:

| Deprecated | Replacement | Removal Version |
|------------|-------------|-----------------|
| `StockMarketData` | `MarketData` | v1.0.0 |

## Stability Tiers

| Tier | Meaning | Deprecation Policy |
|------|---------|-------------------|
| **Stable** | Production-ready, fully tested | 2+ minor versions notice |
| **Experimental** | Functional but may change | May change in any release |
| **Internal** | Not exported, implementation detail | No guarantees |

## Stable APIs

The following are considered stable:

- **Banking**: Plaid integration, account aggregation
- **Brokerage**: Alpaca integration, order management
- **Markets**: Market data feeds
- **Credit**: Credit score providers
- **Analytics**: Portfolio metrics, performance calculations
- **Cashflows**: NPV, IRR, PMT calculations

## Providing Feedback

If you're using experimental APIs, we want to hear from you:

- GitHub Issues: Report bugs or suggest improvements
- Discussions: Share use cases and patterns that work well
