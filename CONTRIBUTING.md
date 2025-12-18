# Contributing to fin-infra

Thank you for your interest in contributing to fin-infra! This document provides guidelines and instructions for contributing.

## ⚠️ Financial Software Warning

**fin-infra is financial infrastructure. Bugs here can cause real money loss.**

Before contributing, please read and understand the quality standards in [.github/copilot-instructions.md](.github/copilot-instructions.md).

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build great software.

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/nfraxlab/fin-infra.git
cd fin-infra

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell

# Run tests
pytest -q

# Run linting
ruff check

# Run type checking
mypy src
```

## Financial Safety Requirements

### Money Calculations

**ALWAYS use Decimal for money. Never float.**

```python
# ✅ Correct
from decimal import Decimal

class Transaction(BaseModel):
    amount: Decimal

total = sum(Decimal(str(v)) for v in values)

# ❌ WRONG - Will cause rounding errors
class Transaction(BaseModel):
    amount: float  # $0.01 + $0.02 != $0.03
```

### Idempotency

All financial operations must be idempotent:

```python
# ✅ Correct - Required idempotency key
def submit_order(symbol: str, qty: Decimal, client_order_id: str):
    ...

# ❌ WRONG - Can cause double orders
def submit_order(symbol: str, qty: Decimal, client_order_id: str | None = None):
    ...
```

### Credential Safety

Never expose secrets:

```python
# ❌ WRONG - Logged everywhere
raise ValueError(f"Failed with key: {api_key}")

# ✅ Correct - No sensitive data
raise ValueError("Authentication failed")
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Use Decimal for all money values
- Add idempotency keys for financial operations
- Never log credentials
- Add comprehensive tests

### 3. Run Quality Checks

```bash
# All checks must pass
ruff format
ruff check
mypy src
pytest -q
```

### 4. Submit a Pull Request

## Code Standards

### Type Hints

All functions must have complete type hints:

```python
from decimal import Decimal

async def get_balance(account_id: str) -> Decimal:
    ...
```

### Testing

Test financial calculations with precision:

```python
from decimal import Decimal

def test_interest_calculation_precision():
    principal = Decimal("10000.00")
    rate = Decimal("0.05")
    result = calculate_interest(principal, rate)
    assert result == Decimal("500.00")  # Exact match required
```

## Project Structure

```
fin-infra/
├── src/fin_infra/     # Main package
│   ├── banking/       # Bank account aggregation
│   ├── brokerage/     # Trading integrations
│   ├── credit/        # Credit score providers
│   ├── markets/       # Market data
│   └── models/        # Data models
├── tests/
├── docs/
└── examples/
```

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format. This enables automated CHANGELOG generation.

**Format:** `type(scope): description`

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `perf:` Performance improvement
- `test:` Adding or updating tests
- `ci:` CI/CD changes
- `chore:` Maintenance tasks

**Examples:**
```
feat: add Plaid sandbox integration
fix: handle decimal precision in NPV calculation
docs: update brokerage API reference
refactor: extract transaction categorization to shared module
test: add unit tests for cashflow calculations
```

**Bad examples (will be grouped as "Other Changes"):**
```
Refactor code for improved readability  ← Missing type prefix!
updating docs                           ← Missing type prefix!
bug fix                                 ← Missing type prefix!
```

## Required Checks Before PR

- [ ] All money values use `Decimal`
- [ ] No hardcoded secrets
- [ ] Idempotency keys for financial operations
- [ ] `ruff check` passes
- [ ] `mypy src` passes
- [ ] `pytest` passes

Thank you for contributing!
