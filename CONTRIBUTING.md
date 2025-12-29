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

### Quick Start (Recommended)

Use `make pr` for the fastest workflow:

```bash
# 1. Make your code changes
# 2. Create a PR with one command:
make pr m="feat: add your feature"

# This automatically:
# - Validates gh CLI + origin remote
# - Fast-forwards main (no rebase on main)
# - Creates branch: add-your-feature-12281430 (UTC timestamp)
# - Commits and pushes
# - Creates PR (or detects existing)
# - Returns to main
```

**Context-aware behavior:**
```bash
# On main → creates new branch + PR
make pr m="feat: add caching"

# On feature branch → commits + pushes; creates PR if none exists
make pr m="feat: add more logic"

# On feature branch, sync with main first:
make pr m="feat: stuff" sync=1  # Rebases on main, force-pushes safely
```

### Manual Workflow

If you prefer manual git commands:

```bash
# 1. Create a branch
git checkout -b feature/your-feature-name

# 2. Make your changes
# - Use Decimal for all money values
# - Add idempotency keys for financial operations
# - Never log credentials
# - Add comprehensive tests

# 3. Run quality checks
ruff format
ruff check
mypy src
pytest -q

# 4. Commit and push
git add -A
git commit -m "feat: your feature"
git push origin feature/your-feature-name

# 5. Open a PR on GitHub
```

### Batching Multiple Commits

For related changes, batch commits before creating a PR:

```bash
make commit m="feat: add base class"
make commit m="feat: add implementation"
make pr m="feat: complete feature"
```

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

## Deprecation Guidelines

When removing or changing public APIs, follow our [Deprecation Policy](DEPRECATION.md).

### When to Deprecate vs Remove

- **Deprecate first** if the feature has any external users
- **Immediate removal** only for security vulnerabilities (see DEPRECATION.md)
- **Never remove** without at least 2 minor versions of deprecation warnings

### How to Add Deprecation Warnings

Use the `@deprecated` decorator:

```python
from fin_infra.utils.deprecation import deprecated

@deprecated(
    version="1.2.0",
    reason="Use new_function() instead",
    removal_version="1.4.0"
)
def old_function():
    ...
```

For deprecated parameters:

```python
from fin_infra.utils.deprecation import deprecated_parameter

def my_function(new_param: str, old_param: str | None = None):
    if old_param is not None:
        deprecated_parameter(
            name="old_param",
            version="1.2.0",
            reason="Use new_param instead"
        )
        new_param = old_param
    ...
```

### Documentation Requirements

When deprecating a feature, you must:

1. Add `@deprecated` decorator or call `deprecated_parameter()`
2. Update the docstring with deprecation notice
3. Add entry to "Deprecated Features Registry" in DEPRECATION.md
4. Add entry to CHANGELOG.md under "Deprecated" section

### Migration Guide Requirements

For significant deprecations, create a migration guide:

1. Create `docs/migrations/v{version}.md`
2. Explain what changed and why
3. Provide before/after code examples
4. Link from the deprecation warning message

## Required Checks Before PR

- [ ] All money values use `Decimal`
- [ ] No hardcoded secrets
- [ ] Idempotency keys for financial operations
- [ ] `ruff check` passes
- [ ] `mypy src` passes
- [ ] `pytest` passes
- [ ] Deprecations follow the deprecation policy

Thank you for contributing!
