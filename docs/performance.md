# Performance Baselines

> **Last Updated**: January 4, 2026
>
> **Environment**: macOS, Python 3.11, Apple Silicon

This document establishes baseline performance metrics for fin-infra to track regressions and improvements.

---

## Import Time

| Metric | Value | Notes |
|--------|-------|-------|
| Full package import | ~2,560ms | `import fin_infra` |

The import time is higher than other packages due to:
- NumPy and Pandas for financial calculations
- Multiple provider SDKs (Plaid, market data)
- ML dependencies for categorization
- Data validation models (Pydantic)

**Recommendation**: Use selective imports for faster startup:
```python
# Slower (full package)
from fin_infra import cashflows  # ~2500ms

# Faster (direct import)
from fin_infra.cashflows import npv, irr, pmt  # ~200ms
```

---

## Cashflow Calculations

| Function | Latency | Throughput | Notes |
|----------|---------|------------|-------|
| `npv()` | 0.006ms | ~160,000/sec | Net Present Value |
| `irr()` | 0.190ms | ~5,000/sec | Internal Rate of Return (iterative) |
| `pmt()` | 0.016ms | ~60,000/sec | Loan payment calculation |
| `pv()` | <0.01ms | ~100,000/sec | Present Value |
| `fv()` | <0.01ms | ~100,000/sec | Future Value |

**IRR performance notes**:
- Uses Newton-Raphson iteration
- Typical convergence: 5-10 iterations
- Edge cases (multiple roots) may take longer

---

## Transaction Categorization

| Operation | Latency | Notes |
|-----------|---------|-------|
| Engine initialization | <1ms | Rule loading |
| Rule-based categorization | <0.1ms | Pattern matching |
| ML-based categorization | ~10ms | Model inference |
| LLM-based categorization | ~500ms | API call to LLM |

**Recommendation**: Use rule-based for high throughput, LLM for accuracy.

---

## Market Data Providers

| Provider | Quote Latency | History Latency | Notes |
|----------|---------------|-----------------|-------|
| Yahoo Finance | ~200ms | ~500ms | Free, no API key |
| Alpha Vantage | ~300ms | ~800ms | Requires API key |

**Rate limits**:
- Yahoo Finance: Unofficial, ~2000 requests/hour
- Alpha Vantage: 5 requests/minute (free tier)

---

## Banking Providers

| Provider | Operation | Latency | Notes |
|----------|-----------|---------|-------|
| Plaid | Link token | ~500ms | Initial setup |
| Plaid | Get accounts | ~1000ms | Cached after first call |
| Plaid | Get transactions | ~2000ms | Pagination may be needed |

---

## Memory Usage

| Component | Memory | Notes |
|-----------|--------|-------|
| Base import | ~150MB | NumPy, Pandas, etc. |
| Categorization engine | +5MB | Rules loaded |
| Market data cache (1000 quotes) | +10MB | In-memory storage |
| Transaction history (10000 txns) | +20MB | Depends on metadata |

---

## Batch Processing

| Operation | Single | Batch (100) | Notes |
|-----------|--------|-------------|-------|
| NPV calculation | 0.006ms | 0.6ms | Linear scaling |
| IRR calculation | 0.19ms | 19ms | Linear scaling |
| Categorization | 0.1ms | 10ms | Can be parallelized |

**Parallel processing example**:
```python
from concurrent.futures import ThreadPoolExecutor
from fin_infra.cashflows import npv

cashflow_sets = [[-1000, 200, 300, 400, 500] for _ in range(1000)]

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(lambda cf: npv(0.10, cf), cashflow_sets))
```

---

## Recommendations

### For Financial Calculations

1. **Pre-calculate** common values (NPV tables, amortization schedules)
2. **Use NumPy arrays** for batch calculations
3. **Cache expensive calculations** (IRR, complex projections)

### For Transaction Processing

1. **Use rule-based categorization** for >90% of transactions
2. **Fallback to LLM** only for uncategorized transactions
3. **Batch similar transactions** for efficiency

### For Market Data

1. **Cache quotes** with appropriate TTL (1-5 minutes)
2. **Use bulk endpoints** when fetching multiple symbols
3. **Handle rate limits** with exponential backoff

---

## Running Your Own Benchmarks

```bash
# Install benchmark dependencies
pip install pytest-benchmark

# Run benchmark suite
pytest benchmarks/ --benchmark-only

# Profile specific functions
python -m cProfile -s cumtime scripts/benchmark_cashflows.py
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-04 | Initial baseline measurements |
