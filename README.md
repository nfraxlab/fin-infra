# fin-infra

[![PyPI](https://img.shields.io/pypi/v/fin-infra.svg)](https://pypi.org/project/fin-infra/)
[![Docs](https://img.shields.io/badge/docs-reference-blue)](.)

Financial infrastructure toolkit for fintech applications. fin-infra provides production-ready building blocks for banking connections, market data, credit scores, tax data, brokerage integrations, and cashflow analysis—everything needed to build comprehensive personal finance management applications.

## What is fin-infra?

fin-infra is the **financial data layer** for fintech apps. While `svc-infra` handles generic backend operations (auth, API scaffolding, database, billing), `fin-infra` is purpose-built for financial applications where users need to:

- Connect bank accounts and pull transaction history
- Link brokerage accounts and view portfolio holdings
- Check credit scores and monitor credit reports
- Access tax documents and data
- View real-time market data (stocks, crypto, forex)
- Perform financial calculations (NPV, IRR, loan amortization)

**Architecture**: fin-infra builds on top of svc-infra's generic modules to provide financial-specific features. For example, document management uses svc-infra's base CRUD operations (upload, list, get, delete) and adds OCR extraction for tax forms and AI-powered financial analysis. This layered approach eliminates duplication while maintaining clear domain separation.

## Status

Alpha. Core functionality is stable, but the surface is intentionally small while we stabilize models and provider contracts.

## Documentation

| Area | What it covers | Guide |
| --- | --- | --- |
| **API Integration** | **Building fintech APIs with fin-infra + svc-infra** | **[API Guide](docs/api.md)** |
| **Persistence** | **Scaffold models/schemas/repositories, svc-infra integration** | **[Persistence Guide](docs/persistence.md)** |
| **Core vs Scaffold** | **Understanding what fin-infra provides vs what apps own** | **[Core vs Scaffold](docs/core-vs-scaffold.md)** |
| **Analytics** | **Cash flow, savings rate, spending insights, portfolio metrics** | **[Analytics](docs/analytics.md)** |
| **Budgets** | **Multi-type budget tracking with templates and alerts** | **[Budget Management](docs/budgets.md)** |
| **Goals** | **Financial goal tracking with milestones and progress** | **[Goals](docs/goals.md)** |
| **Documents** | **Tax forms, bank statements with OCR and AI analysis** | **[Document Management](docs/documents.md)** |
| **Insights** | **Unified insights feed with priority aggregation** | **[Insights Feed](docs/insights.md)** |
| **Investments** | **Holdings, portfolio data, real P/L with cost basis** | **[Investment Holdings](docs/investments.md)** |
| Banking | Account aggregation, transactions, statements | [Banking](docs/banking.md) |
| Market Data | Stocks, crypto, forex quotes and historical data | [Market Data](docs/market-data.md) |
| Crypto | Crypto market data and AI-powered insights | [Crypto](docs/crypto.md) |
| Credit Scores | Credit reports and monitoring | [Credit](docs/credit.md) |
| Brokerage | Trading accounts and portfolio data | [Brokerage](docs/brokerage.md) |
| Tax Data | Tax documents, crypto gains, tax-loss harvesting | [Tax](docs/tax.md), [Tax Data](docs/tax-data.md) |
| Cashflows | NPV, IRR, loan calculations | [Cashflows](docs/cashflows.md) |
| Net Worth | Net worth tracking and LLM insights | [Net Worth](docs/net-worth.md) |
| Categorization | Transaction categorization | [Categorization](docs/categorization.md) |
| Recurring Detection | Recurring transaction detection | [Recurring Detection](docs/recurring-detection.md) |
| Normalization | Data normalization and symbol resolution | [Normalization](docs/normalization.md) |
| Observability | Metrics and route classification | [Observability](docs/observability.md) |
| **Compliance** | **PII boundaries, GLBA/FCRA/PCI-DSS, data lifecycle** | **[Compliance](docs/compliance.md)** |
| Security | Financial security and PII handling | [Security](docs/security.md) |
| Caching | Caching, rate limits, retries | [Caching](docs/caching-rate-limits-retries.md) |
| Providers | Provider integrations overview | [Providers](docs/providers.md) |

## Quick Start

### Installation

```bash
# From PyPI (when published)
pip install fin-infra

# For backend infrastructure (auth, API, DB, cache, jobs), also install:
pip install svc-infra

# For development
git clone https://github.com/your-org/fin-infra
cd fin-infra
poetry install
```

**Note**: fin-infra provides ONLY financial data integrations. For backend infrastructure (API framework, auth, database, caching, jobs), you need [svc-infra](https://github.com/Aliikhatami94/svc-infra). Applications typically use both packages together.

### One-Call Setup

```python
from fin_infra.banking import easy_banking
from fin_infra.markets import easy_market, easy_crypto
from fin_infra.credit import easy_credit
from fin_infra.cashflows import npv, irr

# Banking
banking = easy_banking()
accounts = await banking.get_accounts("access_token")
transactions = await banking.get_transactions("account_id")

# Investment Holdings
from fin_infra.investments import easy_investments

investments = easy_investments(provider="plaid")
holdings = await investments.get_holdings(access_token="...")  # Real cost basis
allocation = await investments.get_allocation(access_token="...")  # Asset allocation

# Market Data
market = easy_market()
quote = market.quote("AAPL")

crypto = easy_crypto()
ticker = crypto.ticker("BTC/USDT")

# Credit Scores
credit = easy_credit()
score = await credit.get_credit_score("user_123")

# Cashflows
cashflows = [-1000, 300, 300, 300, 300]
net_value = npv(0.08, cashflows)
rate_of_return = irr(cashflows)
```

### With FastAPI (fin-infra + svc-infra)

```python
from fastapi import FastAPI
from svc_infra.obs import add_observability
from fin_infra.obs import financial_route_classifier
from fin_infra.banking import add_banking
from fin_infra.markets import add_market_data

# Create app with backend framework (svc-infra)
app = FastAPI(title="Fintech API")

# Add financial capabilities (fin-infra)
add_banking(app, provider="plaid")
from fin_infra.investments import add_investments
add_investments(app, provider="plaid")  # Investment holdings & portfolio data
add_market_data(app, provider="alphavantage")

# Option 1: Basic observability (all routes auto-instrumented)
add_observability(app)

# Option 2: With route classification (recommended for production)
# All routes auto-instrumented + categorized for filtering in Grafana
add_observability(app, route_classifier=financial_route_classifier)
```

**What gets instrumented?**

Both options automatically instrument **ALL routes** in your app:
- ✅ Financial routes: `/banking/*`, `/market/*`, `/crypto/*`
- ✅ Non-financial routes: `/health`, `/docs`, `/admin/*`

**The difference:** Route classification adds category labels (`|financial`, `|public`) for filtering metrics in Grafana.

**Without classifier:**
```promql
# Metrics: route="/banking/accounts"
http_server_requests_total{route="/banking/accounts", method="GET"} 42
```

**With classifier:**
```promql
# Metrics: route="/banking/accounts|financial" (can filter by |financial)
http_server_requests_total{route="/banking/accounts|financial", method="GET"} 42

# Filter all financial routes in Grafana:
sum(rate(http_server_requests_total{route=~".*\\|financial"}[5m]))
```

See [Observability Guide](docs/observability.md) for more details.

## Persistence

fin-infra is a **stateless library** - applications own their database schema, migrations, and data storage.

Generate production-ready models, schemas, and repositories for your application:

```bash
# Scaffold budgets with multi-tenancy
fin-infra scaffold budgets --dest-dir app/models/ --include-tenant

# Scaffold goals
fin-infra scaffold goals --dest-dir app/models/

# Scaffold net-worth snapshots
fin-infra scaffold net-worth --dest-dir app/models/ --include-soft-delete
```

**What you get:**
- ✅ SQLAlchemy models (with svc-infra's `ModelBase`)
- ✅ Pydantic schemas (Create, Read, Update)
- ✅ Repository pattern (full CRUD with async support)
- ✅ Type hints and docstrings throughout
- ✅ Production-ready patterns (UUID primary keys, timestamps, indexes)

**Wire CRUD with ONE function call:**

```python
from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource
from app.models.budgets import Budget

# ONE FUNCTION CALL → Full CRUD API
add_sql_resources(app, [
    SqlResource(
        model=Budget,
        prefix="/budgets",
        search_fields=["name", "description"],
        order_fields=["name", "created_at"],
        soft_delete=False,
    )
])

# Automatic endpoints:
# POST   /budgets/              # Create budget
# GET    /budgets/              # List budgets (paginated, searchable, orderable)
# GET    /budgets/{id}          # Get budget by ID
# PATCH  /budgets/{id}          # Update budget
# DELETE /budgets/{id}          # Delete budget
# GET    /budgets/search        # Search budgets
```

**See [Persistence Guide](docs/persistence.md) for the complete workflow.**

## Architecture Overview

```
fin-infra/
├── src/fin_infra/
│   ├── banking/            # Bank account aggregation
│   │   ├── plaid/          # Plaid provider
│   │   └── teller/         # Teller provider
│   ├── brokerage/          # Trading account connections
│   ├── credit/             # Credit score providers
│   ├── markets/            # Market data (stocks/crypto)
│   ├── tax/                # Tax data and documents
│   ├── cashflows/          # Financial calculations
│   ├── obs/                # Observability (route classification)
│   ├── models/             # Pydantic data models
│   ├── providers/          # Provider implementations
│   └── docs/               # Packaged documentation
├── tests/
│   ├── unit/               # Fast unit tests
│   └── acceptance/         # Provider integration tests
└── examples/               # Example applications
```

**Architecture Documentation:**
- [Core vs Scaffold](docs/core-vs-scaffold.md) - What fin-infra provides vs what apps own
- [Persistence Guide](docs/persistence.md) - Complete scaffold workflow

## Configuration

fin-infra uses environment variables for provider credentials:

```bash
# Banking providers
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox

# Market data providers
ALPHAVANTAGE_API_KEY=your_api_key

# Credit providers (v2: OAuth 2.0)
EXPERIAN_CLIENT_ID=your_client_id
EXPERIAN_CLIENT_SECRET=your_client_secret
EXPERIAN_BASE_URL=https://sandbox-us-api.experian.com  # or production URL
```

## Development

```bash
# Install dependencies
poetry install

# Format code
make format

# Run linting
make lint

# Type check
make type

# Run tests
make unit      # Unit tests only
make accept    # Acceptance tests
make test      # All tests
```

## Acceptance Tests and CI

Acceptance tests are marked with `@pytest.mark.acceptance` and are excluded by default.

### Running locally

Export any required API keys (only Alpha Vantage is needed by default):
- `ALPHAVANTAGE_API_KEY` – required for Alpha Vantage market data tests

Run acceptance tests:
```bash
poetry run pytest -q -m acceptance
```

### GitHub Actions Secrets

The acceptance workflow in `.github/workflows/acceptance.yml` expects:
- `ALPHAVANTAGE_API_KEY` – add it under Repository Settings → Secrets and variables → Actions → New repository secret

If the secret isn't configured, acceptance tests will still run and CoinGecko tests (public) will pass, but Alpha Vantage tests will be skipped.

## Contributing

- Keep APIs small and typed. Prefer Pydantic models for IO boundaries.
- Add or update tests for any behavior changes. Keep `pytest` passing and `mypy` clean.

## License

MIT