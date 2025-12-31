# Building Fintech APIs with fin-infra + svc-infra

**Status**: Production Ready  
**Last Updated**: November 2025

## Overview

This guide shows you how to build production-ready fintech APIs by combining two complementary packages:

- **svc-infra**: Backend infrastructure (API framework, auth, DB, cache, observability, jobs)
- **fin-infra**: Financial data providers (banking, market data, credit, brokerage, tax)

**Key Principle**: Don't reinvent the wheel. Use svc-infra for all backend infrastructure, fin-infra only for financial-specific integrations.

## Quick Start

### Minimal Example

```python
from fastapi import FastAPI
from svc_infra.logging import setup_logging
from svc_infra.obs import add_observability
from fin_infra.banking import add_banking
from fin_infra.markets import add_market_data
from fin_infra.obs import financial_route_classifier

# Setup backend infrastructure (svc-infra)
setup_logging()
app = FastAPI(title="Fintech API")
add_observability(app, route_classifier=financial_route_classifier)

# Add financial capabilities (fin-infra)
add_banking(app, provider="plaid")
add_market_data(app, provider="alphavantage")

# Done! All routes auto-instrumented with metrics
```

See [examples/demo_api/](../examples/demo_api/) for a complete working demo.

## Architecture Patterns

### Layer Separation

```
┌─────────────────────────────────────────────────────┐
│ Your Application                                    │
│ - Business logic                                    │
│ - Custom endpoints                                  │
│ - Domain models                                     │
└────────────┬────────────────────────────────────────┘
             │
             ├────────────────────┬────────────────────
             │                    │
┌────────────▼──────────┐  ┌──────▼─────────────────┐
│ fin-infra             │  │ svc-infra              │
│ (Financial Layer)     │  │ (Infrastructure Layer) │
├───────────────────────┤  ├────────────────────────┤
│ [OK] Banking providers  │  │ [OK] FastAPI scaffolding │
│ [OK] Market data        │  │ [OK] Auth & sessions     │
│ [OK] Credit scores      │  │ [OK] Database & ORM      │
│ [OK] Brokerage          │  │ [OK] Caching (Redis)     │
│ [OK] Tax data           │  │ [OK] Observability       │
│ [OK] Cashflow calcs     │  │ [OK] Background jobs     │
│ [OK] Provider adapters  │  │ [OK] Webhooks            │
│                       │  │ [OK] Rate limiting       │
│                       │  │ [OK] Logging             │
└───────────────────────┘  └────────────────────────┘
```

### Integration Patterns

**Pattern 1: Direct Provider Usage**
```python
from fin_infra.banking import easy_banking

banking = easy_banking(provider="plaid")
accounts = await banking.get_accounts(access_token)
```

**Pattern 2: FastAPI Integration**
```python
from fin_infra.banking import add_banking

# Mounts routes at /banking/*
banking = add_banking(app, provider="plaid", prefix="/banking")
```

**Pattern 3: Custom Endpoints with Providers**
```python
from fin_infra.banking import easy_banking
from fin_infra.markets import easy_market

banking = easy_banking()
market = easy_market()

@app.get("/portfolio/summary")
async def get_portfolio(token: str):
    accounts = await banking.get_accounts(token)
    # Custom business logic combining multiple providers
    return {"accounts": accounts, ...}
```

## Step-by-Step Setup

### 1. Install Packages

```bash
pip install svc-infra fin-infra

# Or with Poetry
poetry add svc-infra fin-infra
```

### 2. Setup Backend Infrastructure (svc-infra)

```python
from svc_infra.logging import setup_logging
from svc_infra.obs import add_observability
from svc_infra.security.add import add_security

# Logging
setup_logging()

# FastAPI app
from fastapi import FastAPI
app = FastAPI(title="My Fintech API")

# Observability (metrics, tracing)
add_observability(app)

# Security headers, CORS
add_security(app)
```

### 3. Add Financial Capabilities (fin-infra)

```python
from fin_infra.banking import add_banking
from fin_infra.markets import add_market_data
from fin_infra.credit import add_credit_monitoring

# Banking
banking = add_banking(app, provider="plaid")

# Market Data
market = add_market_data(app, provider="alphavantage")

# Credit Scores (optional)
credit = add_credit_monitoring(app, provider="experian")
```

### 4. Add Custom Business Logic

```python
@app.get("/dashboard")
async def get_dashboard(user_id: str):
    """Custom endpoint combining multiple providers."""
    # Use fin-infra providers
    accounts = await banking.get_accounts(user_id)
    credit_score = await credit.get_score(user_id)

    # Business logic
    total_balance = sum(a.balance for a in accounts)

    return {
        "balance": total_balance,
        "credit_score": credit_score,
        "last_updated": datetime.now(),
    }
```

### 5. Run the API

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Complete Production Example

```python
from fastapi import FastAPI, Depends
from svc_infra.api.fastapi import setup_service_api, ServiceInfo, APIVersionSpec
from svc_infra.logging import setup_logging
from svc_infra.obs import add_observability
from svc_infra.security.add import add_security
from svc_infra.api.fastapi.ops.add import add_probes, add_maintenance_mode
from fin_infra.banking import add_banking
from fin_infra.markets import add_market_data
from fin_infra.credit import add_credit_monitoring
from fin_infra.obs import financial_route_classifier

# 1. Logging
setup_logging()

# 2. Create production-grade FastAPI app
app = setup_service_api(
    service=ServiceInfo(
        name="fintech-api",
        description="Production fintech API",
        release="1.0.0",
    ),
    versions=[
        APIVersionSpec(tag="v1", routers_package="myapp.api.v1"),
    ],
)

# 3. Add svc-infra infrastructure
add_observability(app, route_classifier=financial_route_classifier)
add_security(app)
add_probes(app)  # Kubernetes health checks
add_maintenance_mode(app)  # Graceful degradation

# 4. Add fin-infra providers
banking = add_banking(app, provider="plaid")
market = add_market_data(app, provider="alphavantage")
credit = add_credit_monitoring(app, provider="experian")

# 5. Custom endpoints
@app.get("/v1/dashboard")
async def get_dashboard():
    """Combined financial dashboard."""
    return {
        "banking": banking.get_summary(),
        "market": market.get_indices(),
        "credit": await credit.get_score(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Feature Matrix

### What Each Package Provides

| Feature | Package | Status |
|---------|---------|--------|
| **API Framework** | svc-infra | [OK] Use `setup_service_api` or `easy_service_app` |
| **Auth & Sessions** | svc-infra | [OK] Use `add_auth_users` |
| **Database & Migrations** | svc-infra | [OK] Use `svc-infra db` CLI |
| **Caching** | svc-infra | [OK] Use `init_cache` |
| **Observability** | svc-infra | [OK] Use `add_observability` |
| **Background Jobs** | svc-infra | [OK] Use `easy_jobs` |
| **Webhooks** | svc-infra | [OK] Use `add_webhooks` |
| **Rate Limiting** | svc-infra | [OK] Middleware available |
| **Logging** | svc-infra | [OK] Use `setup_logging` |
| **Security Headers** | svc-infra | [OK] Use `add_security` |
| **Banking** | fin-infra | [OK] Use `add_banking` or `easy_banking` |
| **Market Data** | fin-infra | [OK] Use `add_market_data` or `easy_market` |
| **Credit Scores** | fin-infra | [OK] Use `add_credit_monitoring` or `easy_credit` |
| **Brokerage** | fin-infra | [OK] Use `add_brokerage` or `easy_brokerage` |
| **Tax Data** | fin-infra | [!] Coming soon |
| **Cashflow Calculations** | fin-infra | [OK] Direct functions: `npv`, `irr`, etc. |
| **Financial Route Classification** | fin-infra | [OK] Use `financial_route_classifier` |

## Common Patterns

### Pattern: Personal Finance App (Mint Clone)

```python
from svc_infra.api.fastapi import setup_service_api, ServiceInfo
from svc_infra.obs import add_observability
from fin_infra.banking import add_banking
from fin_infra.markets import add_market_data
from fin_infra.credit import add_credit_monitoring
from fin_infra.obs import financial_route_classifier

app = setup_service_api(service=ServiceInfo(name="mint-clone"))
add_observability(app, route_classifier=financial_route_classifier)

# Financial features
add_banking(app)  # Connect bank accounts, transactions
add_market_data(app)  # Stock/crypto prices for investments
add_credit_monitoring(app)  # Track credit score

# Custom endpoints for budgeting, spending analysis, etc.
```

### Pattern: Investment Platform (Robinhood Clone)

```python
from svc_infra.api.fastapi import setup_service_api, ServiceInfo
from svc_infra.obs import add_observability
from fin_infra.brokerage import add_brokerage
from fin_infra.markets import add_market_data
from fin_infra.obs import financial_route_classifier

app = setup_service_api(service=ServiceInfo(name="trading-app"))
add_observability(app, route_classifier=financial_route_classifier)

# Financial features
add_brokerage(app, provider="alpaca")  # Paper/live trading
add_market_data(app)  # Real-time quotes

# Custom endpoints for portfolio, watchlists, etc.
```

### Pattern: Credit Monitoring (Credit Karma Clone)

```python
from svc_infra.api.fastapi import setup_service_api, ServiceInfo
from svc_infra.obs import add_observability
from fin_infra.credit import add_credit_monitoring
from fin_infra.banking import add_banking
from fin_infra.obs import financial_route_classifier

app = setup_service_api(service=ServiceInfo(name="credit-monitor"))
add_observability(app, route_classifier=financial_route_classifier)

# Financial features
add_credit_monitoring(app)  # Credit scores, reports
add_banking(app)  # Financial profile

# Custom endpoints for credit alerts, recommendations, etc.
```

## Testing

### Unit Tests

```python
import pytest
from fin_infra.banking import easy_banking

def test_get_accounts():
    banking = easy_banking(provider="fake")
    accounts = banking.get_accounts("test_token")
    assert len(accounts) > 0
```

### Integration Tests (with svc-infra patterns)

```python
from fastapi.testclient import TestClient
from myapp import app

client = TestClient(app)

def test_banking_endpoint():
    response = client.get("/banking/accounts")
    assert response.status_code == 200
    data = response.json()
    assert "accounts" in data
```

### Acceptance Tests (with real providers)

```python
import pytest
import os

@pytest.mark.acceptance
@pytest.mark.skipif(not os.getenv("PLAID_CLIENT_ID"), reason="Plaid not configured")
def test_plaid_integration():
    from fin_infra.banking import easy_banking

    banking = easy_banking(provider="plaid")
    # Test with sandbox credentials
    ...
```

## Configuration

### Environment Variables

```env
# svc-infra
APP_ENV=production
LOG_LEVEL=INFO
METRICS_ENABLED=true
SQL_URL=postgresql://...
REDIS_URL=redis://...

# fin-infra
PLAID_CLIENT_ID=...
PLAID_SECRET=...
ALPHAVANTAGE_API_KEY=...
EXPERIAN_USERNAME=...
```

### Settings Pattern (Pydantic)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # svc-infra
    app_env: str = "local"
    log_level: str = "INFO"

    # fin-infra
    plaid_client_id: str
    plaid_secret: str
    alphavantage_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

# Copy app
COPY . .

# Run
CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fintech-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: fintech-api:latest
        env:
        - name: APP_ENV
          value: "production"
        - name: PLAID_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: fintech-secrets
              key: plaid-client-id
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
```

## Observability

### Metrics

```promql
# Financial endpoint request rate
sum(rate(http_server_requests_total{route=~".*\\|financial"}[5m]))

# Financial endpoint P95 latency
histogram_quantile(0.95,
  rate(http_server_request_duration_seconds_bucket{route=~".*\\|financial"}[5m])
)

# Error rate by route class
sum(rate(http_server_requests_total{code=~"5..", route=~".*\\|financial"}[5m]))
/ sum(rate(http_server_requests_total{route=~".*\\|financial"}[5m]))
```

### Logs

```json
{
  "timestamp": "2025-11-06T12:34:56.789Z",
  "level": "INFO",
  "message": "Banking request completed",
  "provider": "plaid",
  "method": "get_accounts",
  "duration_ms": 234.56,
  "user_id": "u-123"
}
```

## Best Practices

### 1. Always Use svc-infra for Backend Infrastructure

```python
# [OK] GOOD: Use svc-infra for logging
from svc_infra.logging import setup_logging

# [X] BAD: Don't create custom logging (fin-infra doesn't provide it)
import logging
logging.basicConfig(...)  # NO!
```

### 2. Use fin-infra Only for Financial Integrations

```python
# [OK] GOOD: Use fin-infra for banking
from fin_infra.banking import add_banking

# [X] BAD: Don't use fin-infra for generic caching (use svc-infra)
from fin_infra.cache import ...  # Doesn't exist!
```

### 3. Compose with Route Classification

```python
# [OK] GOOD: Compose financial classifier with custom classifiers
from fin_infra.obs import financial_route_classifier, compose_classifiers

def admin_classifier(path, method):
    return "admin" if path.startswith("/admin") else "public"

classifier = compose_classifiers(
    financial_route_classifier,
    admin_classifier,
)

add_observability(app, route_classifier=classifier)
```

### 4. Use Easy Builders for Development

```python
# [OK] GOOD for development: Use easy_* builders
from fin_infra.banking import easy_banking
banking = easy_banking()

# [OK] GOOD for production: Use add_* FastAPI helpers
from fin_infra.banking import add_banking
banking = add_banking(app)
```

### 5. Handle Provider Errors Gracefully

```python
from fin_infra.banking import easy_banking, ProviderError

banking = easy_banking()

try:
    accounts = await banking.get_accounts(token)
except ProviderError as e:
    logger.error(f"Banking provider error: {e}")
    # Fallback logic or user-friendly error
```

## Troubleshooting

### Issue: Missing svc-infra Features

**Problem**: Looking for feature X in fin-infra

**Solution**: Check svc-infra first! fin-infra only provides financial-specific integrations.

### Issue: Provider Not Configured

**Problem**: `ProviderNotConfiguredError: Missing PLAID_CLIENT_ID`

**Solution**: Add credentials to `.env` file or environment variables.

### Issue: Metrics Not Showing Route Class

**Problem**: Metrics show `route="/banking/accounts"` instead of `route="/banking/accounts|financial"`

**Solution**: Pass `route_classifier` to `add_observability`:

```python
from fin_infra.obs import financial_route_classifier
add_observability(app, route_classifier=financial_route_classifier)
```

## Related Documentation

- [fin-infra Documentation](../docs/)
- [svc-infra Documentation](https://github.com/Aliikhatami94/svc-infra/tree/main/docs)
- [Demo API Example](../examples/demo_api/)
- [Banking Integration](./banking.md)
- [Market Data Integration](./market-data.md)
- [Observability Guide](./observability.md)

## Summary

[OK] **Use svc-infra** for all backend infrastructure (API, auth, DB, cache, jobs, webhooks)  
[OK] **Use fin-infra** for financial data integrations (banking, market, credit, brokerage)  
[OK] **Compose both** for production-ready fintech APIs  
[OK] **Follow patterns** in examples/demo_api/ and svc-infra/examples/
