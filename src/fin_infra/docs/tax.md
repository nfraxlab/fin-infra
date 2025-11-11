# Tax Data Integration

fin-infra provides interfaces for accessing tax documents, tax data, and tax calculations for fintech applications.

## Supported Providers

- **IRS e-File**: Direct IRS integration (coming soon)
- **TaxBit**: Crypto tax calculations
- **TurboTax**: Tax document import (coming soon)
- **H&R Block**: Tax document import (coming soon)

## Quick Setup

```python
from fin_infra.tax import easy_tax

# Auto-configured from environment variables
tax = easy_tax()
```

## Core Operations

### 1. Get Tax Documents
```python
from datetime import date

documents = await tax.get_tax_documents(
    user_id="user_123",
    tax_year=2024
)

for doc in documents:
    print(f"{doc.form_type}: {doc.name}")
    print(f"  Issuer: {doc.issuer}")
    print(f"  Download: {doc.download_url}")
```

### 2. Calculate Tax Liability
```python
liability = await tax.calculate_tax_liability(
    user_id="user_123",
    income=150000,
    deductions=25000,
    filing_status="single"
)

print(f"Taxable Income: ${liability.taxable_income}")
print(f"Total Tax: ${liability.total_tax}")
print(f"Effective Rate: {liability.effective_rate}%")
```

### 3. Crypto Tax Calculations
```python
crypto_taxes = await tax.calculate_crypto_taxes(
    user_id="user_123",
    transactions=crypto_transactions,
    tax_year=2024
)

print(f"Capital Gains: ${crypto_taxes.capital_gains}")
print(f"Short-term Gains: ${crypto_taxes.short_term_gains}")
print(f"Long-term Gains: ${crypto_taxes.long_term_gains}")
```

### 4. Tax Form Generation
```python
# Generate 1099-INT for interest income
form_1099 = await tax.generate_1099_int(
    user_id="user_123",
    interest_income=1250.00,
    tax_year=2024
)

# Download PDF
pdf_bytes = await tax.download_form(form_1099.form_id)
```

## Data Models

### TaxDocument
```python
from fin_infra.models.tax import TaxDocument

class TaxDocument:
    document_id: str
    user_id: str
    form_type: str  # W2, 1099-INT, 1099-DIV, 1099-B, etc.
    tax_year: int
    issuer: str
    download_url: str | None
    status: str  # pending, available, downloaded
    created_at: datetime
```

### TaxLiability
```python
class TaxLiability:
    taxable_income: Decimal
    total_tax: Decimal
    federal_tax: Decimal
    state_tax: Decimal
    effective_rate: Decimal
    marginal_rate: Decimal
```

## Tax-Loss Harvesting (Phase 2 Enhancement)

Identify opportunities to offset capital gains by selling losing positions while maintaining portfolio exposure.

### Overview

Tax-loss harvesting (TLH) is an investment strategy that:
1. Sells securities at a loss to offset capital gains
2. Reduces tax liability by claiming investment losses
3. Maintains portfolio exposure by purchasing similar (not substantially identical) securities

**IRS Wash Sale Rule**: Cannot repurchase the same or substantially identical security within 61 days (30 days before + 30 days after sale).

### Core Functions

```python
from fin_infra.tax.tlh import find_tlh_opportunities, simulate_tlh_scenario
from fin_infra.brokerage import easy_brokerage

# Get user's brokerage positions
brokerage = easy_brokerage()
positions = brokerage.get_positions(user_id="user_123")

# Find TLH opportunities
opportunities = find_tlh_opportunities(
    user_id="user_123",
    positions=positions,
    min_loss=100.00,  # Minimum loss to consider ($100)
    tax_rate=0.15,    # Capital gains tax rate (15% default)
    recent_trades=[]  # Optional: recent trades to check wash sale risk
)

for opp in opportunities:
    print(f"{opp.position_symbol}: ${opp.loss_amount:.2f} loss")
    print(f"  Tax savings: ${opp.potential_tax_savings:.2f}")
    print(f"  Replacement: {opp.replacement_ticker}")
    print(f"  Wash sale risk: {opp.wash_sale_risk}")
```

### TLH Models

**TLHOpportunity**:
```python
from pydantic import BaseModel
from decimal import Decimal

class TLHOpportunity(BaseModel):
    position_symbol: str           # Current holding (e.g., "AAPL")
    position_qty: Decimal          # Number of shares
    cost_basis: Decimal           # Original purchase price
    current_value: Decimal        # Current market value
    loss_amount: Decimal          # Unrealized loss (must be > 0)
    loss_percent: Decimal         # Loss percentage
    replacement_ticker: str       # Suggested replacement (e.g., "VGT")
    wash_sale_risk: str          # Risk level: none, low, medium, high
    potential_tax_savings: Decimal # Loss × tax_rate
    tax_rate: Decimal             # Applied tax rate (default 15%)
    last_purchase_date: datetime | None  # For wash sale checking
    explanation: str              # Human-readable reasoning
```

**TLHScenario**:
```python
class TLHScenario(BaseModel):
    total_loss_harvested: Decimal    # Sum of all losses
    total_tax_savings: Decimal       # Sum of all tax savings
    num_opportunities: int           # Count of opportunities
    avg_tax_rate: Decimal           # Weighted average tax rate
    wash_sale_risk_summary: dict[str, int]  # Count by risk level
    total_cost_basis: Decimal       # Sum of original costs
    total_current_value: Decimal    # Sum of current values
    recommendations: list[str]      # Actionable advice
    caveats: list[str]             # Legal disclaimers
```

### Wash Sale Risk Assessment

The system automatically checks wash sale rules:

| Risk Level | Days Since Purchase | Action |
|------------|-------------------|--------|
| **none** | >60 days or never | ✅ Safe to sell |
| **low** | 31-60 days | ⚠️ Caution: wait a few more days |
| **medium** | 16-30 days | ⚠️ Risk: IRS may disallow loss |
| **high** | 0-15 days | 🚫 Avoid: wash sale rule applies |

```python
from fin_infra.tax.tlh import _assess_wash_sale_risk
from datetime import datetime, timedelta

# Check wash sale risk for a position
last_purchase = datetime.now() - timedelta(days=45)
risk = _assess_wash_sale_risk("AAPL", last_purchase)
print(f"Wash sale risk: {risk}")  # "low" (31-60 days)
```

### Replacement Security Suggestions

Built-in rule-based mappings for common securities:

| Original | Replacement | Asset Class |
|----------|------------|-------------|
| AAPL, MSFT, GOOGL | VGT | Technology ETF |
| NVDA, AMD | SOXX | Semiconductor ETF |
| JPM, BAC, GS | XLF | Financial ETF |
| JNJ, PFE | XLV | Healthcare ETF |
| MRNA | XBI | Biotech ETF |
| BTC | ETH | Crypto (swap) |
| ETH | BTC | Crypto (swap) |
| Unknown | SPY | S&P 500 ETF (default) |

**For production**: Use ai-infra CoreLLM for intelligent replacements:

```python
from ai_infra.llm import CoreLLM

llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")

prompt = f"""Suggest a replacement security for {symbol} that:
1. Is NOT substantially identical under IRS wash sale rules
2. Provides similar market exposure
3. Has reasonable trading volume
Return only the ticker symbol."""

response = await llm.achat(
    messages=[{"role": "user", "content": prompt}],
    output_schema=None  # Natural language response
)
replacement = response.strip()
```

### Scenario Simulation

Simulate executing multiple TLH opportunities:

```python
# Find all opportunities
opportunities = find_tlh_opportunities(
    user_id="user_123",
    positions=positions,
    min_loss=100.00
)

# Simulate scenario
scenario = simulate_tlh_scenario(
    opportunities=opportunities,
    tax_rate=0.20  # Override: 20% tax rate
)

print(f"Total Tax Savings: ${scenario.total_tax_savings:.2f}")
print(f"Number of Trades: {scenario.num_opportunities}")
print(f"\nWash Sale Risk Summary:")
for risk, count in scenario.wash_sale_risk_summary.items():
    print(f"  {risk}: {count} positions")

print(f"\nRecommendations:")
for rec in scenario.recommendations:
    print(f"  • {rec}")
```

### FastAPI Endpoints

**GET /tax/tlh-opportunities**:
```python
# Query params:
# - user_id (required)
# - min_loss (optional, default: 100.00)
# - tax_rate (optional, default: 0.15)

# Example:
GET /tax/tlh-opportunities?user_id=user_123&min_loss=500&tax_rate=0.20

# Response:
[
  {
    "position_symbol": "AAPL",
    "position_qty": "100",
    "cost_basis": "15000.00",
    "current_value": "13500.00",
    "loss_amount": "1500.00",
    "loss_percent": "10.00",
    "replacement_ticker": "VGT",
    "wash_sale_risk": "none",
    "potential_tax_savings": "300.00",
    "tax_rate": "0.20",
    "last_purchase_date": null,
    "explanation": "Sell AAPL at $1,500 loss, buy VGT for similar tech exposure"
  }
]
```

**POST /tax/tlh-scenario**:
```python
# Request body:
{
  "opportunities": [...],  # List of TLHOpportunity objects
  "tax_rate": 0.20        # Optional override
}

# Response:
{
  "total_loss_harvested": "3500.00",
  "total_tax_savings": "700.00",
  "num_opportunities": 3,
  "avg_tax_rate": "0.20",
  "wash_sale_risk_summary": {
    "none": 2,
    "low": 1,
    "medium": 0,
    "high": 0
  },
  "total_cost_basis": "50000.00",
  "total_current_value": "46500.00",
  "recommendations": [
    "Consider executing TLH trades before year-end to maximize tax benefits",
    "1 position has low wash sale risk - wait a few more days before selling",
    "After selling, immediately purchase replacement securities to maintain exposure",
    "Remember to wait 31 days before repurchasing original securities"
  ],
  "caveats": [
    "Consult a tax professional before executing TLH trades",
    "Wash sale rules apply for 61 days (30 before + 30 after sale)",
    "Replacement securities may have different risk profiles",
    "Tax savings are estimates and depend on your specific tax situation"
  ]
}
```

### Use Cases

**1. Year-End Tax Planning**
```python
# Find all TLH opportunities before Dec 31
opportunities = find_tlh_opportunities(user_id, positions, min_loss=0)
scenario = simulate_tlh_scenario(opportunities)

if scenario.total_tax_savings > 1000:
    send_notification(
        user_id,
        title="Tax-Loss Harvesting Opportunity",
        message=f"Harvest losses before year-end to save ${scenario.total_tax_savings:.2f} in taxes"
    )
```

**2. Portfolio Rebalancing with TLH**
```python
# Combine rebalancing with TLH
opportunities = find_tlh_opportunities(user_id, positions)

# Filter for positions user wants to sell anyway
rebalancing_sells = get_rebalancing_sells(user_id)
tlh_candidates = [
    opp for opp in opportunities
    if opp.position_symbol in rebalancing_sells
]

# Execute TLH + rebalancing together
scenario = simulate_tlh_scenario(tlh_candidates)
```

**3. Wash Sale Monitoring**
```python
# Alert users about wash sale risks
for opp in opportunities:
    if opp.wash_sale_risk in ["high", "medium"]:
        send_alert(
            user_id,
            title="Wash Sale Risk",
            message=f"{opp.position_symbol}: Wait {days_until_safe} days to avoid wash sale rule"
        )
```

### Production Considerations

**Brokerage Integration**: TLH requires live position data:

```python
from fin_infra.brokerage import easy_brokerage

# Get positions from brokerage
brokerage = easy_brokerage(provider="alpaca")  # or "interactive_brokers"
positions = brokerage.get_positions(user_id)

# Find opportunities with recent trade data
recent_trades = brokerage.get_trades(user_id, days=90)
opportunities = find_tlh_opportunities(
    user_id,
    positions,
    recent_trades=recent_trades  # For wash sale checking
)
```

**Professional Disclaimer**: Always include tax professional disclaimer:

```python
DISCLAIMER = """
⚠️ Tax-Loss Harvesting Disclaimer:
This tool provides estimates only. Consult a certified tax professional before executing any tax-loss harvesting trades. The IRS wash sale rule is complex and depends on your specific situation. Replacement securities may have different risk profiles than original holdings.
"""

@app.get("/tax/tlh-opportunities")
async def get_tlh_opportunities(...):
    opportunities = find_tlh_opportunities(...)
    return {
        "opportunities": opportunities,
        "disclaimer": DISCLAIMER
    }
```

**Cost Tracking**: Track TLH execution costs vs. savings:

```python
# Track metrics
tlh_metrics = {
    "opportunities_found": len(opportunities),
    "total_tax_savings": scenario.total_tax_savings,
    "avg_savings_per_trade": scenario.total_tax_savings / scenario.num_opportunities,
    "wash_sale_risks": scenario.wash_sale_risk_summary,
}

# Log for analytics
logger.info("TLH analysis completed", extra=tlh_metrics)
```

## Compliance

### IRS Requirements
- Store tax documents for 7 years minimum
- Encrypt sensitive tax data
- Provide audit trail for all tax calculations
- Follow IRS e-File security standards
- **Tax-Loss Harvesting**: Comply with wash sale rules (IRC Section 1091)

### Data Security
```python
from fin_infra.security import encrypt_tax_data

# Encrypt before storing
encrypted_data = encrypt_tax_data(
    ssn="123-45-6789",
    key=settings.encryption_key
)
```

## Best Practices

1. **Data Retention**: Store tax documents for legal minimum period
2. **Encryption**: Encrypt all tax-related PII
3. **Audit Trail**: Log all tax calculations and document access
4. **Compliance**: Stay updated with IRS regulations
5. **Professional Review**: Recommend CPA review for complex situations

## Testing

```python
import pytest
from fin_infra.tax import easy_tax

@pytest.mark.asyncio
async def test_calculate_tax():
    tax = easy_tax()
    
    liability = await tax.calculate_tax_liability(
        user_id="test_user",
        income=100000,
        deductions=12000,
        filing_status="single"
    )
    
    assert liability.total_tax > 0
```

## Next Steps

- [Banking Integration](banking.md)
- [Brokerage Integration](brokerage.md)
- [Credit Scores](credit.md)
