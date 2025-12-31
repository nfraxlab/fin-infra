# CLI Reference

Command-line tools for fin-infra template management.

## Table of Contents

- [Overview](#overview)
- [Database Commands](#database-commands)
- [Make Commands](#make-commands)
- [Testing Commands](#testing-commands)
- [Provider Testing](#provider-testing)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)

---

## Overview

The fin-infra template provides CLI tools from two sources:

1. **svc-infra CLI**: Database migrations, scaffolding
2. **Make commands**: Project automation

All commands assume you're in the `examples/` directory.

---

## Database Commands

**Provided by**: `svc-infra` (via `python -m svc_infra.db`)

### Initialize Migrations

First-time setup:

```bash
poetry run python -m svc_infra.db init --project-root .
```

Creates:
- `alembic.ini`
- `migrations/` directory
- `migrations/env.py`

### Create Migration

After modifying models:

```bash
poetry run python -m svc_infra.db revision \
  --autogenerate \
  -m "Add user preferences table" \
  --project-root .
```

### Apply Migrations

Upgrade to latest:

```bash
poetry run python -m svc_infra.db upgrade head --project-root .
```

Upgrade specific version:

```bash
poetry run python -m svc_infra.db upgrade abc123 --project-root .
```

Downgrade one version:

```bash
poetry run python -m svc_infra.db downgrade -1 --project-root .
```

Downgrade to base (empty database):

```bash
poetry run python -m svc_infra.db downgrade base --project-root .
```

### View Migration Status

Current version:

```bash
poetry run python -m svc_infra.db current --project-root .
```

Migration history:

```bash
poetry run python -m svc_infra.db history --project-root .
```

### One-Command Setup

For new databases (initializes + migrates):

```bash
poetry run python -m svc_infra.db setup-and-migrate --project-root .
```

### Database URL Override

Use different database:

```bash
poetry run python -m svc_infra.db upgrade head \
  --database-url postgresql+asyncpg://user:pass@localhost/testdb \
  --project-root .
```

---

## Make Commands

**Location**: `examples/Makefile`

### Development

**Install dependencies**:

```bash
make install
```

Runs: `poetry install`

**Run development server**:

```bash
make run
```

Runs: `poetry run python src/main.py`  
Server starts on: `http://localhost:8001`

**Run in background**:

```bash
make run-bg
```

Runs server in background, logs to `server.log`

**Stop background server**:

```bash
make stop
```

### Setup

**Complete setup** (install + database + test):

```bash
make setup
```

Equivalent to:
```bash
make install
make db-setup
make test-basic
```

### Database

**Setup database** (create tables):

```bash
make db-setup
```

Uses: `create_tables.py` (SQLAlchemy create_all)

**Run migrations**:

```bash
make migrate
```

Uses: `svc_infra.db setup-and-migrate`

**Reset database** (drop + recreate):

```bash
make db-reset
```

[!] **Warning**: Deletes all data!

### Testing

**Basic tests** (no API keys needed):

```bash
make test-basic
```

Tests:
- Categorization (local rules)
- Recurring detection
- Cashflows (NPV, IRR)

**Test with providers** (requires API keys):

```bash
make test-providers
```

Tests:
- Banking (Plaid sandbox)
- Market data (Alpha Vantage)
- Crypto (CoinGecko)

**All tests**:

```bash
make test
```

Runs: `poetry run pytest -q`

### Cleaning

**Clean build artifacts**:

```bash
make clean
```

Removes:
- `__pycache__/`
- `.pytest_cache/`
- `*.pyc`
- `.coverage`

**Clean database** (remove dev.db):

```bash
make clean-db
```

### Help

**List all commands**:

```bash
make help
```

Shows all available Make targets with descriptions.

---

## Testing Commands

### Unit Tests

Run all unit tests:

```bash
poetry run pytest -q
```

Run specific test file:

```bash
poetry run pytest tests/test_categorization.py -v
```

Run specific test:

```bash
poetry run pytest tests/test_categorization.py::test_categorize_coffee -v
```

### Acceptance Tests

Run acceptance tests (requires API keys):

```bash
poetry run pytest -m acceptance
```

Skip acceptance tests:

```bash
poetry run pytest -m "not acceptance"
```

### Coverage

Run with coverage report:

```bash
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Provider Testing

### Test Plaid Integration

```bash
# 1. Get link token
curl http://localhost:8001/banking/link

# 2. Use returned link_token in Plaid Link UI
# Sandbox credentials:
#   Username: user_good
#   Password: pass_good

# 3. Exchange public token (from Link flow)
curl -X POST http://localhost:8001/banking/exchange \
  -H "Content-Type: application/json" \
  -d '{"public_token": "public-sandbox-..."}'

# 4. Get accounts
curl "http://localhost:8001/banking/accounts?access_token=access-sandbox-..."
```

### Test Market Data

```bash
# Single quote
curl http://localhost:8001/market/quote/AAPL

# Multiple quotes
curl "http://localhost:8001/market/quotes?symbols=AAPL,GOOGL,MSFT"

# Historical data
curl "http://localhost:8001/market/history/AAPL?start_date=2024-01-01&end_date=2024-01-31"
```

### Test Crypto Data

```bash
# Single coin
curl http://localhost:8001/crypto/quote/BTC

# Multiple coins
curl "http://localhost:8001/crypto/quotes?symbols=BTC,ETH,SOL"
```

### Test Analytics

```bash
# Cash flow
curl http://localhost:8001/analytics/cash-flow/user_123

# Savings rate
curl http://localhost:8001/analytics/savings-rate/user_123

# AI advice (requires GOOGLE_GENAI_API_KEY)
curl http://localhost:8001/analytics/advice/user_123
```

### Test Categorization

```bash
# Single transaction
curl -X POST http://localhost:8001/categorize \
  -H "Content-Type: application/json" \
  -d '{"description": "STARBUCKS", "amount": 5.75}'

# Batch categorization
curl -X POST http://localhost:8001/categorize/batch \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {"description": "UBER", "amount": 15.50},
      {"description": "WHOLE FOODS", "amount": 125.30}
    ]
  }'
```

### Test Cashflows

```bash
# NPV
curl -X POST http://localhost:8001/cashflows/npv \
  -H "Content-Type: application/json" \
  -d '{"rate": 0.08, "cashflows": [-10000, 3000, 4000, 5000]}'

# IRR
curl -X POST http://localhost:8001/cashflows/irr \
  -H "Content-Type: application/json" \
  -d '{"cashflows": [-10000, 3000, 4000, 5000]}'

# Loan payment
curl -X POST http://localhost:8001/cashflows/pmt \
  -H "Content-Type: application/json" \
  -d '{"rate": 0.004167, "nper": 360, "pv": 200000}'
```

---

## Development Workflow

### Typical Development Session

```bash
# 1. Start development environment
cd examples
make setup  # First time only

# 2. Start server
make run

# 3. In another terminal, test endpoints
curl http://localhost:8001/market/quote/AAPL

# 4. Make code changes
# Edit src/main.py or capability files

# 5. Restart server (Ctrl+C, then make run again)
# Or use auto-reload (uvicorn --reload)

# 6. Run tests
make test

# 7. Commit changes
git add .
git commit -m "Add feature X"
```

### Adding New Model

```bash
# 1. Add model to src/main.py
# Example: Add UserPreferences model

# 2. Create migration
poetry run python -m svc_infra.db revision \
  --autogenerate \
  -m "Add user preferences" \
  --project-root .

# 3. Review migration file
cat migrations/versions/abc123_add_user_preferences.py

# 4. Apply migration
poetry run python -m svc_infra.db upgrade head --project-root .

# 5. Verify
poetry run python -m svc_infra.db current --project-root .
```

### Adding New Provider

```bash
# 1. Add provider credentials to .env
echo "NEW_PROVIDER_API_KEY=your_key" >> .env

# 2. Test connection
curl http://localhost:8001/new-capability/test

# 3. Write tests
# Create tests/test_new_provider.py

# 4. Run tests
poetry run pytest tests/test_new_provider.py -v
```

---

## Troubleshooting

### Command Not Found: `poetry`

**Solution**:
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Or via pip
pip install poetry

# Verify
poetry --version
```

### Command Not Found: `make`

**Solution** (macOS):
```bash
xcode-select --install
```

**Solution** (Linux):
```bash
sudo apt-get install build-essential  # Debian/Ubuntu
sudo yum install make gcc             # RHEL/CentOS
```

### Error: "No module named 'svc_infra'"

**Solution**:
```bash
# Install dependencies
cd examples
poetry install

# Verify installation
poetry run python -c "import svc_infra; print('OK')"
```

### Error: "ModuleNotFoundError: No module named 'src'"

**Solution**:
```bash
# Ensure PYTHONPATH includes current directory
export PYTHONPATH=.
poetry run python src/main.py

# Or run from examples/ directory
cd examples
poetry run python src/main.py
```

### Error: "Address already in use"

**Cause**: Port 8001 occupied by another process

**Solution**:
```bash
# Find process using port
lsof -i :8001

# Kill process
kill -9 <PID>

# Or use different port
poetry run python src/main.py --port 8002
```

### Database Locked (SQLite)

**Solution**:
```bash
# Close all connections to dev.db
make stop

# Or switch to PostgreSQL
# See docs/DATABASE.md
```

### Migration Conflicts

**Cause**: Multiple migration branches

**Solution**:
```bash
# View current state
poetry run python -m svc_infra.db current --project-root .

# View history with branches
poetry run python -m svc_infra.db history --project-root .

# Merge branches manually
poetry run python -m svc_infra.db merge heads --project-root .
```

---

## Advanced Commands

### Custom Database Migration

Create empty migration for manual changes:

```bash
poetry run python -m svc_infra.db revision \
  -m "Custom data migration" \
  --project-root .

# Edit generated file manually
vim migrations/versions/abc123_custom_data_migration.py
```

### Seed Test Data

```bash
# Create seed script
cat > scripts/seed.py << 'EOF'
import asyncio
from svc_infra.db.sql import get_async_session
from src.main import User, Budget

async def seed():
    async with get_async_session() as session:
        user = User(id="test_user", email="test@example.com")
        session.add(user)
        await session.commit()

asyncio.run(seed())
EOF

# Run seed script
poetry run python scripts/seed.py
```

### Export Environment Variables from .env

```bash
# Export all .env variables to shell
export $(cat .env | grep -v '^#' | xargs)

# Verify
echo $PLAID_CLIENT_ID
```

---

## Quick Reference

### Common Commands

```bash
# Setup
make setup                # Full setup (first time)
make install              # Install dependencies
make run                  # Start server

# Database
make db-setup             # Create tables (dev)
make migrate              # Run migrations (prod)
make db-reset             # Drop and recreate

# Testing
make test                 # All tests
make test-basic           # No API keys needed
make test-providers       # With API keys

# Cleanup
make clean                # Clean artifacts
make clean-db             # Remove dev.db
```

### Database Migrations

```bash
# Initialize
python -m svc_infra.db init --project-root .

# Create migration
python -m svc_infra.db revision --autogenerate -m "message" --project-root .

# Apply migrations
python -m svc_infra.db upgrade head --project-root .

# Check status
python -m svc_infra.db current --project-root .
```

---

## Next Steps

- **Configure providers**: See [PROVIDERS.md](PROVIDERS.md)
- **Try examples**: Check [USAGE.md](../USAGE.md)
- **Setup database**: Read [DATABASE.md](DATABASE.md)

---

**Questions?** Open an issue or check the main [README.md](../README.md).
