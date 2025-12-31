# Tax Data Integration

Provides tax form aggregation, crypto tax calculations, and document management. Supports W-2, 1099-INT, 1099-DIV, 1099-B, 1099-MISC forms, and comprehensive crypto capital gains reporting.

## Quick Start

### Zero-Config Setup (Mock Provider)

```python
from fin_infra.tax import easy_tax

# Default mock provider for testing
tax = easy_tax()

# Get all tax documents
documents = tax.get_tax_documents(user_id="user_123", tax_year=2024)
for doc in documents:
    print(f"{doc.form_type}: {doc.issuer} (${doc.amount})")
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fin_infra.tax import add_tax_data

app = FastAPI()

# Add tax routes with authentication
tax_provider = add_tax_data(app, provider="mock", prefix="/tax")

# Routes registered:
# GET  /tax/documents?user_id=...&tax_year=2024
# GET  /tax/documents/{document_id}
# POST /tax/crypto-gains
# POST /tax/tax-liability
```

### Production Setup (IRS/TaxBit)

```bash
# IRS e-Services (6-8 weeks registration)
export IRS_EFIN="your_efin"
export IRS_TCC="your_tcc"
export IRS_CERT_PATH="/path/to/cert.pem"
export IRS_KEY_PATH="/path/to/key.pem"

# TaxBit (paid subscription $50-$200/month + per-user)
export TAXBIT_CLIENT_ID="your_client_id"
export TAXBIT_CLIENT_SECRET="your_client_secret"
```

```python
# Auto-detect credentials from env
tax = easy_tax(provider="irs")  # or "taxbit"
```

## Supported Tax Forms

### W-2: Wage and Tax Statement

**Fields**: 20 IRS boxes including wages, tips, federal/state/SS/Medicare withholding, retirement plan, box 12 codes.

```python
from fin_infra.models import TaxFormW2

w2 = TaxFormW2(
    document_id="w2_2024_user_123",
    user_id="user_123",
    tax_year=2024,
    issuer="Acme Corporation",
    issuer_ein="12-3456789",
    wages=75000.00,
    federal_income_tax_withheld=12000.00,
    social_security_wages=75000.00,
    social_security_tax_withheld=4650.00,
    medicare_wages=75000.00,
    medicare_tax_withheld=1087.50,
    retirement_plan=True,
    box_12_codes=["D:5000.00"],  # 401k deferrals
)
```

### 1099-INT: Interest Income

**Fields**: Interest income, early withdrawal penalty, federal tax withheld, tax-exempt interest.

```python
from fin_infra.models import TaxForm1099INT

interest = TaxForm1099INT(
    document_id="1099int_2024_user_123",
    user_id="user_123",
    tax_year=2024,
    issuer="Acme Bank",
    issuer_ein="98-7654321",
    interest_income=250.00,
    early_withdrawal_penalty=0.00,
)
```

### 1099-DIV: Dividends and Distributions

**Fields**: Ordinary dividends, qualified dividends, capital gain distributions, section 1250 gain, collectibles gain.

```python
from fin_infra.models import TaxForm1099DIV

dividends = TaxForm1099DIV(
    document_id="1099div_2024_user_123",
    user_id="user_123",
    tax_year=2024,
    issuer="Vanguard",
    issuer_ein="11-2233445",
    ordinary_dividends=500.00,
    qualified_dividends=400.00,
    total_capital_gain=50.00,
)
```

### 1099-B: Proceeds from Broker Transactions

**Fields**: Description, acquisition/sale dates, proceeds, cost basis, gain/loss, holding period, wash sale.

```python
from fin_infra.models import TaxForm1099B

broker = TaxForm1099B(
    document_id="1099b_2024_user_123",
    user_id="user_123",
    tax_year=2024,
    issuer="Coinbase",
    issuer_ein="55-6677889",
    description="0.5 BTC",
    date_acquired="2023-01-15",
    date_sold="2024-11-01",
    proceeds=35000.00,
    cost_basis=25000.00,
    gain_or_loss=10000.00,
    short_term=False,
)
```

### 1099-MISC: Miscellaneous Income

**Fields**: Rents, royalties, other income (staking/airdrops), fishing income, medical payments, crop insurance.

```python
from fin_infra.models import TaxForm1099MISC

misc = TaxForm1099MISC(
    document_id="1099misc_2024_user_123",
    user_id="user_123",
    tax_year=2024,
    issuer="Coinbase",
    issuer_ein="55-6677889",
    other_income=1200.00,  # Staking rewards
)
```

## Crypto Tax Calculations

### Capital Gains Calculation (FIFO/LIFO/HIFO)

```python
# Calculate crypto capital gains
report = tax.calculate_crypto_gains(
    user_id="user_123",
    tax_year=2024,
    cost_basis_method="FIFO"  # or "LIFO", "HIFO"
)

print(f"Total gain/loss: ${report.total_gain_loss:,.2f}")
print(f"Short-term: ${report.short_term_gain_loss:,.2f}")
print(f"Long-term: ${report.long_term_gain_loss:,.2f}")
print(f"Transactions: {report.transaction_count}")

# Form 8949 transactions
for tx in report.transactions:
    print(f"{tx.symbol}: {tx.transaction_type} {tx.quantity} @ ${tx.price} = ${tx.gain_or_loss}")
```

### Cost Basis Methods

- **FIFO** (First In, First Out): Default IRS method. Sells oldest assets first.
- **LIFO** (Last In, First Out): Sells newest assets first. May reduce short-term gains.
- **HIFO** (Highest In, First Out): Tax-loss harvesting. Sells highest-cost assets first to minimize gains.

**IRS Compliance**: All methods require detailed transaction records. FIFO is safest for audits.

### Transaction Types

```python
from fin_infra.models import CryptoTransaction

# Buy transaction
buy = CryptoTransaction(
    symbol="BTC",
    transaction_type="buy",
    date="2023-01-15",
    quantity=0.5,
    price=50000.00,
    cost_basis=25000.00,
)

# Sell transaction
sell = CryptoTransaction(
    symbol="BTC",
    transaction_type="sell",
    date="2024-11-01",
    quantity=0.5,
    price=70000.00,
    cost_basis=25000.00,
    gain_or_loss=10000.00,
)

# Staking rewards (reported on 1099-MISC)
staking = CryptoTransaction(
    symbol="ETH",
    transaction_type="staking_reward",
    date="2024-06-15",
    quantity=0.05,
    price=3000.00,
    cost_basis=150.00,  # Fair market value at receipt
)
```

## Tax Liability Estimation

```python
from fin_infra.models import TaxLiability

# Estimate tax liability
liability = tax.calculate_tax_liability(
    user_id="user_123",
    tax_year=2024,
    filing_status="single"  # or "married_joint", "married_separate", "head_of_household"
)

print(f"Gross income: ${liability.gross_income:,.2f}")
print(f"Deductions: ${liability.deductions:,.2f}")
print(f"Taxable income: ${liability.taxable_income:,.2f}")
print(f"Federal tax: ${liability.federal_tax:,.2f}")
print(f"State tax: ${liability.state_tax:,.2f}")
print(f"Effective rate: {liability.effective_tax_rate:.2f}%")
```

**Note**: MockTaxProvider uses simplified calculation (15% federal, 5% state). Production providers use actual IRS tax tables and state-specific rates.

## Document Management

### Download Tax Documents

```python
# Download PDF document
pdf_bytes = tax.download_document(document_id="w2_2024_user_123")

# Save to file
with open("w2_2024.pdf", "wb") as f:
    f.write(pdf_bytes)

# Or return to user via FastAPI
from fastapi import Response

@app.get("/tax/documents/{document_id}/download")
async def download_tax_doc(document_id: str):
    pdf_bytes = tax.download_document(document_id)
    return Response(content=pdf_bytes, media_type="application/pdf")
```

### Document Retention (IRS Compliance)

**IRS Requirement**: Keep tax records for **7 years** from filing date (26 U.S. Code § 6501).

**Integration with svc-infra Data Lifecycle**:

```python
from svc_infra.data import add_data_lifecycle, RetentionPolicy

# Configure 7-year retention for tax documents
add_data_lifecycle(
    app,
    policies=[
        RetentionPolicy(
            name="tax_document_retention",
            retention_period_days=7 * 365,  # 7 years
            scope="tax_documents",
            apply_to=["TaxDocument"],
        )
    ]
)
```

**Audit Trail**: Use svc-infra logging and observability to track document access:

```python
from svc_infra.logging import setup_logging
from svc_infra.obs import add_observability

setup_logging(level="INFO", fmt="json")
add_observability(app, metrics_path="/metrics")
```

## Provider Comparison

### Mock Provider (v1 - Default)

**Use Case**: Testing, local development, demos.

**Features**:
- [OK] Zero configuration
- [OK] Realistic hardcoded data (W-2 $75k wages, 5x 1099 forms)
- [OK] Full API coverage (all methods implemented)
- [OK] Instant responses

**Limitations**:
- [X] Static data (same for all users/years)
- [X] No real IRS integration
- [X] No document upload/parsing

**Setup**:
```python
tax = easy_tax()  # or easy_tax(provider="mock")
```

### IRS e-Services Provider (v2 - Not Yet Implemented)

**Use Case**: Production apps requiring official IRS integration.

**Features**:
- [OK] Official IRS API access
- [OK] Real-time form filing
- [OK] Electronic signature (PKI)
- [OK] Form validation

**Limitations**:
- [X] 6-8 week registration process
- [X] Requires EFIN (Electronic Filing Identification Number)
- [X] Requires TCC (Transmitter Control Code)
- [X] Requires PKI certificate
- [X] IP whitelist required
- [X] Annual renewal

**Registration**: [IRS e-Services](https://www.irs.gov/e-file-providers/e-services)

**Setup**:
```bash
export IRS_EFIN="your_efin"
export IRS_TCC="your_tcc"
export IRS_CERT_PATH="/path/to/cert.pem"
export IRS_KEY_PATH="/path/to/key.pem"
export IRS_BASE_URL="https://testwebsite.irs.gov/esvc"  # or production
```

```python
tax = easy_tax(provider="irs")
```

**Status**: Raises `NotImplementedError` (v2 placeholder).

### TaxBit Provider (v2 - Not Yet Implemented)

**Use Case**: Fintech apps requiring crypto tax reporting (Coinbase, Robinhood, etc.).

**Features**:
- [OK] Comprehensive crypto tax calculations (FIFO/LIFO/HIFO)
- [OK] Form 8949 generation
- [OK] Multi-exchange aggregation
- [OK] NFT and DeFi support
- [OK] Tax-loss harvesting recommendations

**Pricing**:
- **Small apps** (< 1,000 users): $50-$100/month + $1-$2/user
- **Medium apps** (1,000-10,000 users): $200-$500/month + $1-$2/user
- **Large apps** (> 10,000 users): Custom ($10k-$50k/month)

**Registration**: [TaxBit API](https://taxbit.com/products/api)

**Setup**:
```bash
export TAXBIT_CLIENT_ID="your_client_id"
export TAXBIT_CLIENT_SECRET="your_client_secret"
export TAXBIT_BASE_URL="https://api.taxbit.com"  # or sandbox
```

```python
tax = easy_tax(provider="taxbit")
```

**Status**: Raises `NotImplementedError` (v2 placeholder).

## FastAPI Routes

### GET /tax/documents

List all tax documents for a user and tax year.

**Query Parameters**:
- `user_id` (required): User identifier
- `tax_year` (optional): Tax year (default: current year - 1)

**Response**:
```json
[
  {
    "document_id": "w2_2024_user_123",
    "user_id": "user_123",
    "form_type": "W-2",
    "tax_year": 2024,
    "issuer": "Acme Corporation",
    "issuer_ein": "12-3456789",
    "download_url": "/tax/documents/w2_2024_user_123/download",
    "status": "available",
    "created_at": "2024-01-15T00:00:00Z"
  }
]
```

### GET /tax/documents/{document_id}

Get a specific tax document with full details.

**Response** (W-2 example):
```json
{
  "document_id": "w2_2024_user_123",
  "user_id": "user_123",
  "form_type": "W-2",
  "tax_year": 2024,
  "issuer": "Acme Corporation",
  "issuer_ein": "12-3456789",
  "wages": 75000.00,
  "federal_income_tax_withheld": 12000.00,
  "social_security_wages": 75000.00,
  "social_security_tax_withheld": 4650.00,
  "medicare_wages": 75000.00,
  "medicare_tax_withheld": 1087.50,
  "retirement_plan": true,
  "box_12_codes": ["D:5000.00"]
}
```

### POST /tax/crypto-gains

Calculate crypto capital gains with cost basis method.

**Request**:
```json
{
  "user_id": "user_123",
  "tax_year": 2024,
  "cost_basis_method": "FIFO"
}
```

**Response**:
```json
{
  "total_gain_loss": 11930.00,
  "short_term_gain_loss": 1930.00,
  "long_term_gain_loss": 10000.00,
  "transaction_count": 2,
  "cost_basis_method": "FIFO",
  "transactions": [
    {
      "symbol": "BTC",
      "transaction_type": "sell",
      "date": "2024-11-01",
      "quantity": 0.5,
      "price": 70000.00,
      "cost_basis": 25000.00,
      "gain_or_loss": 10000.00
    }
  ]
}
```

### POST /tax/tax-liability

Estimate tax liability based on income and deductions.

**Request**:
```json
{
  "user_id": "user_123",
  "tax_year": 2024,
  "filing_status": "single"
}
```

**Response**:
```json
{
  "gross_income": 88680.00,
  "deductions": 14600.00,
  "taxable_income": 74080.00,
  "federal_tax": 11112.00,
  "state_tax": 3704.00,
  "effective_tax_rate": 16.71
}
```

## Environment Variables Reference

### IRS e-Services Configuration

```bash
# Required
IRS_EFIN="123456"                    # Electronic Filing ID Number
IRS_TCC="12345"                      # Transmitter Control Code
IRS_CERT_PATH="/path/to/cert.pem"   # PKI certificate
IRS_KEY_PATH="/path/to/key.pem"     # PKI private key

# Optional
IRS_BASE_URL="https://testwebsite.irs.gov/esvc"  # Sandbox or production
```

### TaxBit Configuration

```bash
# Required
TAXBIT_CLIENT_ID="your_client_id"
TAXBIT_CLIENT_SECRET="your_client_secret"

# Optional
TAXBIT_BASE_URL="https://api.taxbit.com"  # Sandbox or production
```

## Integration Patterns

### Complete Fintech App (fin-infra + svc-infra)

```python
from fastapi import FastAPI
from svc_infra.api.fastapi.ease import easy_service_app
from svc_infra.logging import setup_logging
from svc_infra.cache import init_cache
from svc_infra.obs import add_observability
from svc_infra.data import add_data_lifecycle, RetentionPolicy
from fin_infra.tax import add_tax_data
from fin_infra.banking import add_banking
from fin_infra.brokerage import add_brokerage

# Backend infrastructure (svc-infra)
setup_logging(level="INFO", fmt="json")
app = easy_service_app(name="FinanceAPI")
init_cache(url="redis://localhost")
add_observability(app)

# Tax document retention (7 years IRS requirement)
add_data_lifecycle(
    app,
    policies=[
        RetentionPolicy(
            name="tax_retention",
            retention_period_days=7 * 365,
            scope="tax_documents",
        )
    ]
)

# Financial integrations (fin-infra)
add_tax_data(app, provider="mock", prefix="/tax")
add_banking(app, provider="plaid", prefix="/banking")
add_brokerage(app, provider="alpaca", prefix="/brokerage")
```

### Background Tax Calculations (svc-infra Jobs)

```python
from svc_infra.jobs import easy_jobs
from fin_infra.tax import easy_tax

worker, scheduler = easy_jobs(app)
tax = easy_tax(provider="taxbit")

@worker.task
async def calculate_year_end_taxes(user_id: str, tax_year: int):
    """Calculate tax liability at year-end."""
    report = tax.calculate_crypto_gains(user_id, tax_year, "FIFO")
    liability = tax.calculate_tax_liability(user_id, tax_year, "single")

    # Store results in database
    # Send email notification
    return {"report": report, "liability": liability}

# Schedule for all users on Jan 1st
@scheduler.scheduled_job("cron", month=1, day=1)
async def year_end_tax_batch():
    users = await get_all_users()
    for user in users:
        calculate_year_end_taxes.delay(user.id, 2024)
```

### Webhook Integration (svc-infra Webhooks)

```python
from svc_infra.webhooks import add_webhooks

# Send tax document notifications
add_webhooks(app, prefix="/webhooks")

@app.post("/tax/documents/notify")
async def notify_tax_document_ready(user_id: str, document_id: str):
    """Webhook notification when tax document is ready."""
    from svc_infra.webhooks import send_webhook

    document = tax.get_tax_document(document_id)
    await send_webhook(
        event="tax.document.ready",
        data={
            "user_id": user_id,
            "document_id": document_id,
            "form_type": document.form_type,
            "tax_year": document.tax_year,
            "download_url": f"/tax/documents/{document_id}/download"
        }
    )
```

## Testing

### Unit Tests

```python
import pytest
from fin_infra.tax import easy_tax

def test_mock_provider_w2():
    tax = easy_tax(provider="mock")
    docs = tax.get_tax_documents(user_id="user_123", tax_year=2024)

    w2 = next(d for d in docs if d.form_type == "W-2")
    assert w2.wages == 75000.00
    assert w2.federal_income_tax_withheld == 12000.00

def test_crypto_gains_calculation():
    tax = easy_tax(provider="mock")
    report = tax.calculate_crypto_gains("user_123", 2024, "FIFO")

    assert report.total_gain_loss == 11930.00
    assert report.short_term_gain_loss == 1930.00
    assert report.long_term_gain_loss == 10000.00
```

### FastAPI Tests

```python
from fastapi.testclient import TestClient
from fin_infra.tax import add_tax_data

def test_tax_documents_endpoint():
    app = FastAPI()
    add_tax_data(app, provider="mock")
    client = TestClient(app)

    response = client.get("/tax/documents?user_id=user_123&tax_year=2024")
    assert response.status_code == 200
    assert len(response.json()) == 5  # W-2 + 4x 1099 forms
```

## Error Handling

```python
from fin_infra.tax import easy_tax

tax = easy_tax(provider="mock")

try:
    doc = tax.get_tax_document("invalid_id")
except ValueError as e:
    print(f"Document not found: {e}")

try:
    tax = easy_tax(provider="irs")
except NotImplementedError as e:
    print(f"IRS provider not available: {e}")
    # Fall back to mock
    tax = easy_tax(provider="mock")
```

## Related Documentation

- [Banking Integration](./banking.md) - Link bank accounts for income verification
- [Brokerage Integration](./brokerage.md) - Investment account data for 1099-B
- [Data Lifecycle](../../svc-infra/docs/data-lifecycle.md) - 7-year retention policy
- [Webhooks](../../svc-infra/docs/webhooks.md) - Tax document notifications
