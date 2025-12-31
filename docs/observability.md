# Financial Observability Integration

**Domain**: Observability & Monitoring  
**Status**: Production Ready  
**Dependencies**: svc-infra.obs (required)

## Overview

fin-infra extends svc-infra's observability stack with financial-specific route classification. This enables you to monitor financial provider endpoints separately from general API endpoints in your metrics and dashboards.

**Key Features**:
- 🏷 Automatic route classification for financial endpoints
-  Seamless integration with svc-infra's Prometheus/Grafana stack
- 🔌 No hardcoded endpoints - extensible prefix patterns
-  Filter metrics by route class: `financial`, `public`, `admin`, etc.

## Quick Start

### Option 1: Without Route Classification (Simple)

All routes automatically instrumented with basic labels:

```python
from fastapi import FastAPI
from svc_infra.obs import add_observability

app = FastAPI()

# All routes automatically instrumented - no manual registration needed
add_observability(app)

# Metrics for ALL routes available at /metrics
# Labels: route="/banking/accounts", route="/health", etc.
```

**Use this when:** You just want basic metrics on all routes without categorization.

### Option 2: With Route Classification (Recommended)

All routes automatically instrumented + categorized by type:

```python
from fastapi import FastAPI
from svc_infra.obs import add_observability
from fin_infra.obs import financial_route_classifier

app = FastAPI()

# All routes automatically instrumented + categorized
add_observability(app, route_classifier=financial_route_classifier)

# Metrics for ALL routes with category labels
# Labels: route="/banking/accounts|financial", route="/health|public", etc.
```

**Use this when:** You want to filter metrics by route category in Grafana (recommended for fin-infra apps).

### What Gets Instrumented?

**Important:** Both options automatically instrument **ALL routes** in your app. You don't need to manually register routes or list them.

The difference is **only in the labeling**:

### What Gets Instrumented?

**Important:** Both options automatically instrument **ALL routes** in your app. You don't need to manually register routes or list them.

The difference is **only in the labeling**:

| Option | Routes Instrumented | Route Label Format | Can Filter by Category? |
|--------|---------------------|-------------------|-------------------------|
| **Without classifier** | [OK] ALL (auto-discovered) | `route="/banking/accounts"` | [X] No |
| **With classifier** | [OK] ALL (auto-discovered) | `route="/banking/accounts\|financial"` | [OK] Yes |

**Example with classifier:**

```python
# These routes ALL get instrumented + labeled automatically:
GET /banking/accounts          → route="/banking/accounts|financial"
GET /market/quote/AAPL        → route="/market/quote/{symbol}|financial"
GET /crypto/price/BTC         → route="/crypto/price/{symbol}|financial"
GET /brokerage/positions      → route="/brokerage/positions|financial"

# Non-financial routes also get instrumented + labeled:
GET /health                    → route="/health|public"
GET /docs                      → route="/docs|public"
GET /admin/users               → route="/admin/users|public"
```

**Example without classifier:**

```python
# Same routes ALL get instrumented, just simpler labels:
GET /banking/accounts          → route="/banking/accounts"
GET /market/quote/AAPL        → route="/market/quote/{symbol}"
GET /health                    → route="/health"
```

## How It Works

### Route Classification

The `financial_route_classifier` detects financial routes using prefix patterns:

```python
FINANCIAL_ROUTE_PREFIXES = (
    "/banking",
    "/market",
    "/crypto",
    "/brokerage",
    "/credit",
    "/tax",
    "/cashflow",
    "/transaction",
    "/portfolio",
    "/wallet",
)
```

Any route starting with these prefixes is automatically classified as `financial`. All other routes are classified as `public`.

### svc-infra Integration

**Key Concept:** The `route_classifier` parameter is **optional** and only affects labeling, not which routes get instrumented.

svc-infra's `add_observability` automatically discovers and instruments **ALL routes** via ASGI middleware. The optional `route_classifier` callback lets you categorize routes:

```python
def route_classifier(route_path: str, method: str) -> str:
    # Returns route class: "financial", "public", "admin", etc.
    ...
```

**How it works:**

1. **svc-infra middleware intercepts ALL HTTP requests** (automatic, always happens)
2. **Metrics collected** for every request: count, duration, status code, etc.
3. **If `route_classifier` provided:** Call it to get category label
4. **Route label encoded** as `"{path}|{category}"` or just `"{path}"` (without classifier)
5. **Metrics exposed** at `/metrics` endpoint

**Without classifier:**
```promql
http_server_requests_total{route="/banking/accounts", method="GET", code="200"} 42
http_server_requests_total{route="/health", method="GET", code="200"} 1000
```

**With classifier:**
```promql
http_server_requests_total{route="/banking/accounts|financial", method="GET", code="200"} 42
http_server_requests_total{route="/health|public", method="GET", code="200"} 1000
```

**Why use route classification?**

With classification, you can filter metrics in Grafana by category:

```promql
# Total requests to ONLY financial endpoints (filter by |financial suffix)
sum(rate(http_server_requests_total{route=~".*\\|financial"}[5m]))

# Total requests to ONLY non-financial endpoints (filter by |public suffix)
sum(rate(http_server_requests_total{route=~".*\\|public"}[5m]))

# Total requests to ALL endpoints (no filter - works with or without classifier)
sum(rate(http_server_requests_total[5m]))

# P95 latency for financial routes only
histogram_quantile(0.95,
  rate(http_server_request_duration_seconds_bucket{route=~".*\\|financial"}[5m])
)
```

**Without classifier,** you'd need to manually list every financial route:

```promql
# [X] Without classifier - must manually list all financial routes
sum(rate(http_server_requests_total{route=~"/banking/.*|/market/.*|/crypto/.*"}[5m]))
```

## When to Use Each Option

### Use WITHOUT Route Classifier

[OK] **Good for:**
- Simple apps with few routes
- When you don't need to segment metrics by category
- Quick prototypes or demos
- When minimal configuration is desired

```python
# Simple setup - just observability, no categorization
add_observability(app)
```

### Use WITH Route Classifier

[OK] **Recommended for:**
- Production fintech applications
- Apps with mixed financial and non-financial routes
- When you need different SLOs per route category
- When building Grafana dashboards segmented by route type

```python
# Production setup - observability + categorization
add_observability(app, route_classifier=financial_route_classifier)
```

### Comparison Table

| Feature | Without Classifier | With Classifier |
|---------|-------------------|-----------------|
| **Routes instrumented** | [OK] ALL (auto-discovered) | [OK] ALL (auto-discovered) |
| **Manual route registration** | [X] Not needed | [X] Not needed |
| **Metrics collected** | [OK] Count, duration, status, size | [OK] Count, duration, status, size |
| **Route label format** | `route="/banking/accounts"` | `route="/banking/accounts\|financial"` |
| **Filter by category in Grafana** | [X] No - must list routes manually | [OK] Yes - filter by `\|financial`, `\|public` |
| **Setup complexity** | Simple (fewer imports) | Slightly more (one extra import) |
| **Best for** | Simple apps, prototypes | Production apps, segmented SLOs |

**Bottom line:** Both options instrument ALL routes automatically. Classifier just adds categorization for better Grafana filtering.

## Advanced Usage

### Compose with Custom Classifiers

If you need additional route classes (e.g., `admin`, `internal`), compose classifiers:

```python
from fin_infra.obs import financial_route_classifier, compose_classifiers

def admin_classifier(route_path: str, method: str) -> str:
    if route_path.startswith("/admin"):
        return "admin"
    return "public"

def internal_classifier(route_path: str, method: str) -> str:
    if route_path.startswith("/internal"):
        return "internal"
    return "public"

# Compose: try financial → admin → internal → default to public
classifier = compose_classifiers(
    financial_route_classifier,
    admin_classifier,
    internal_classifier,
    default="public",
)

add_observability(app, route_classifier=classifier)
```

Now your routes are classified with multiple categories:

```python
GET /banking/accounts    → financial
GET /admin/users         → admin
GET /internal/debug      → internal
GET /health              → public
```

### Custom Classifier Implementation

You can also implement your own classifier from scratch:

```python
from fin_infra.obs import financial_route_classifier

def my_classifier(route_path: str, method: str) -> str:
    # Try financial classification first
    cls = financial_route_classifier(route_path, method)
    if cls != "public":
        return cls

    # Add custom logic
    if route_path.startswith("/admin"):
        return "admin"
    if route_path.startswith("/api/v1"):
        return "api_v1"
    if route_path.startswith("/api/v2"):
        return "api_v2"

    return "public"

add_observability(app, route_classifier=my_classifier)
```

### Extending Financial Prefixes

If you add new financial capabilities with different prefixes, extend the prefix list:

```python
from fin_infra.obs.classifier import FINANCIAL_ROUTE_PREFIXES

# Add custom financial prefixes (before classification runs)
FINANCIAL_ROUTE_PREFIXES += (
    "/insurance",
    "/mortgage",
    "/loan",
)

# Now these routes will also be classified as financial
GET /insurance/quotes     → financial
GET /mortgage/rates       → financial
```

## Metrics Available

When using svc-infra's `add_observability`, these metrics are automatically collected:

### HTTP Metrics (with route classification)

```prometheus
# Request count (labeled by route class)
http_server_requests_total{method, route, code}

# Request duration (labeled by route class)
http_server_request_duration_seconds{route, method}

# In-flight requests (labeled by route class)
http_server_inflight_requests{route}

# Response size (labeled by route class)
http_server_response_size_bytes{route, method}

# Exception count (labeled by route class)
http_server_exceptions_total{route, method}
```

### Querying by Financial Routes

```promql
# Request rate for financial endpoints
sum(rate(http_server_requests_total{route=~".*\\|financial"}[5m])) by (method, code)

# Error rate for financial endpoints
sum(rate(http_server_requests_total{route=~".*\\|financial",code=~"5.."}[5m]))
  /
sum(rate(http_server_requests_total{route=~".*\\|financial"}[5m]))

# P95 latency for financial routes
histogram_quantile(0.95,
  sum(rate(http_server_request_duration_seconds_bucket{route=~".*\\|financial"}[5m])) by (le)
)

# Compare financial vs public route latency
histogram_quantile(0.95,
  sum(rate(http_server_request_duration_seconds_bucket[5m])) by (le, route)
) > 0
```

## Grafana Dashboard Panels

### Financial vs Non-Financial Request Rate

```json
{
  "targets": [
    {
      "expr": "sum(rate(http_server_requests_total{route=~\".*\\\\|financial\"}[5m]))",
      "legendFormat": "Financial Routes"
    },
    {
      "expr": "sum(rate(http_server_requests_total{route=~\".*\\\\|public\"}[5m]))",
      "legendFormat": "Public Routes"
    }
  ]
}
```

### Financial Endpoint Latency Heatmap

```json
{
  "targets": [
    {
      "expr": "sum(rate(http_server_request_duration_seconds_bucket{route=~\".*\\\\|financial\"}[5m])) by (le)",
      "format": "heatmap"
    }
  ]
}
```

### Top Financial Endpoints by Request Count

```json
{
  "targets": [
    {
      "expr": "topk(10, sum(rate(http_server_requests_total{route=~\".*\\\\|financial\"}[5m])) by (route))",
      "legendFormat": "{{route}}"
    }
  ]
}
```

## Integration Examples

### Full Production Setup

```python
from fastapi import FastAPI
from svc_infra.obs import add_observability
from svc_infra.logging import setup_logging
from fin_infra.obs import financial_route_classifier
from fin_infra.banking import add_banking
from fin_infra.markets import add_market_data

# Create app
app = FastAPI(title="Fintech API")

# Setup logging
setup_logging()

# Wire observability with financial route classification
shutdown = add_observability(
    app,
    route_classifier=financial_route_classifier,
    metrics_path="/metrics",
    skip_metric_paths=["/health", "/healthz"],
)

# Add financial capabilities
add_banking(app, provider="plaid")
add_market_data(app, provider="alphavantage")

# Metrics now available at /metrics with route classes
```

### Multi-Class Setup (Financial + Admin + Internal)

```python
from fin_infra.obs import financial_route_classifier, compose_classifiers

def admin_classifier(path: str, method: str) -> str:
    return "admin" if path.startswith("/admin") else "public"

def internal_classifier(path: str, method: str) -> str:
    return "internal" if path.startswith("/internal") else "public"

classifier = compose_classifiers(
    financial_route_classifier,
    admin_classifier,
    internal_classifier,
    default="public",
)

add_observability(app, route_classifier=classifier)
```

Now you can filter Grafana panels by:
- `route=~".*\\|financial"` - Financial provider endpoints
- `route=~".*\\|admin"` - Admin endpoints
- `route=~".*\\|internal"` - Internal endpoints
- `route=~".*\\|public"` - Everything else

## Testing

### Unit Test Example

```python
from fin_infra.obs import financial_route_classifier

def test_banking_routes_classified_as_financial():
    assert financial_route_classifier("/banking/accounts", "GET") == "financial"
    assert financial_route_classifier("/banking/transactions", "GET") == "financial"

def test_health_routes_classified_as_public():
    assert financial_route_classifier("/health", "GET") == "public"
    assert financial_route_classifier("/docs", "GET") == "public"
```

### Integration Test Example

```python
import pytest
from fastapi.testclient import TestClient
from svc_infra.obs import add_observability
from fin_infra.obs import financial_route_classifier

def test_financial_routes_emit_metrics(app):
    add_observability(app, route_classifier=financial_route_classifier)
    client = TestClient(app)

    # Make request to financial endpoint
    response = client.get("/banking/accounts")
    assert response.status_code == 200

    # Check metrics endpoint
    metrics = client.get("/metrics").text
    assert "http_server_requests_total" in metrics
    assert 'route="/banking/accounts|financial"' in metrics
```

## Architecture Decisions

**Key Design Principles**:

1. **No Hardcoded Endpoints**: Uses prefix patterns instead of specific paths
2. **Composable**: Can be combined with other route classifiers
3. **Extensible**: New financial prefixes can be added at runtime
4. **Zero Config**: Works out of the box with sensible defaults
5. **svc-infra Native**: Uses svc-infra's existing metrics infrastructure

## Comparison with svc-infra

| Feature | svc-infra | fin-infra Extension |
|---------|-----------|---------------------|
| Base metrics | [OK] HTTP, DB, HTTPX | [OK] Reuses all base metrics |
| Route classification | [OK] Optional via `route_classifier` | [OK] Provides `financial_route_classifier` |
| Financial prefix detection | [X] | [OK] Automatic |
| Grafana dashboards | [OK] Generic HTTP dashboard | [OK] Works with existing dashboards + route filters |
| Prometheus integration | [OK] | [OK] Reuses existing integration |
| OpenTelemetry | [!] Removed in latest | [!] N/A |

## Best Practices

### 1. Always Use Route Classification

```python
# [OK] GOOD: Enable route classification
add_observability(app, route_classifier=financial_route_classifier)

# [X] BAD: Skip route classification (can't filter by financial vs public)
add_observability(app)
```

### 2. Compose Classifiers for Multi-Tenant Apps

```python
# [OK] GOOD: Separate financial, admin, and public routes
classifier = compose_classifiers(
    financial_route_classifier,
    admin_classifier,
    tenant_classifier,
)

# [X] BAD: One giant if-elif chain
def massive_classifier(path, method):
    if path.startswith("/banking") or path.startswith("/market") or ...:
        return "financial"
    elif path.startswith("/admin"):
        return "admin"
    # ... 50 more elif statements
```

### 3. Filter Metrics in Grafana by Route Class

```promql
# [OK] GOOD: Filter by route class
sum(rate(http_server_requests_total{route=~".*\\|financial"}[5m]))

# [!] OKAY: Filter by specific route (less flexible)
sum(rate(http_server_requests_total{route="/banking/accounts"}[5m]))
```

### 4. Set SLOs per Route Class

```yaml
# SLO: Financial endpoints should have P95 latency < 500ms
- alert: FinancialEndpointsSlow
  expr: |
    histogram_quantile(0.95,
      rate(http_server_request_duration_seconds_bucket{route=~".*\\|financial"}[5m])
    ) > 0.5
  labels:
    severity: warning
    route_class: financial
```

## Troubleshooting

### Routes Not Classified as Financial

**Symptom**: Routes like `/banking/accounts` show up as `public` instead of `financial`.

**Cause**: Route prefix doesn't match any `FINANCIAL_ROUTE_PREFIXES`.

**Solution**: Check the prefix list and add your custom prefix:

```python
from fin_infra.obs.classifier import FINANCIAL_ROUTE_PREFIXES

# Add missing prefix
FINANCIAL_ROUTE_PREFIXES += ("/myfinance",)
```

### Metrics Not Showing Route Class

**Symptom**: Metrics show `route="/banking/accounts"` instead of `route="/banking/accounts|financial"`.

**Cause**: `route_classifier` not passed to `add_observability`.

**Solution**: Pass the classifier:

```python
add_observability(app, route_classifier=financial_route_classifier)
```

### Grafana Queries Return No Data

**Symptom**: Grafana panels with `route=~".*\\|financial"` show "No Data".

**Cause**: Regex escaping issue or no financial routes have been called yet.

**Solution**:
1. Verify the regex in Prometheus directly: `http_server_requests_total{route=~".*\\|financial"}`
2. Make some requests to financial endpoints to generate metrics
3. Check that route labels include the `|financial` suffix

## Related Documentation

- [svc-infra Observability Guide](../../svc-infra/docs/ops.md)
- [Banking Integration](./banking.md) - Financial endpoints for route classification
- [Market Data Integration](./market-data.md) - Financial endpoints for route classification

## Summary

[OK] **Use svc-infra for**: Base metrics, Prometheus setup, Grafana dashboards  
[OK] **Use fin-infra for**: Financial route classification, provider-specific labels  
[OK] **Integration**: One-liner: `add_observability(app, route_classifier=financial_route_classifier)`  
[OK] **Benefits**: Filter metrics by financial vs public routes in Grafana
