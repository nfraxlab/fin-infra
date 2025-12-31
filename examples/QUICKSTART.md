# Quick Start Guide

Get the fin-infra-template running in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Poetry installed (`pip install poetry`)

## Installation

```bash
# 1. Navigate to examples directory
cd examples

# 2. Install dependencies
poetry install

# 3. Copy environment template
cp .env.example .env

# 4. Run automated setup
python scripts/quick_setup.py

# 5. Start the server
make run
```

Server starts at **http://localhost:8001**

- OpenAPI docs: http://localhost:8001/docs
- Scoped banking docs: http://localhost:8001/banking/docs
- Scoped analytics docs: http://localhost:8001/analytics/docs
- Metrics: http://localhost:8001/metrics
- Health check: http://localhost:8001/_health

##  Key Configuration

Edit `.env` for provider configuration:

```bash
# Core Settings
APP_ENV=local              # Environment: local, dev, prod
API_PORT=8001              # Server port
SQL_URL=sqlite+aiosqlite:////tmp/fin_infra_template.db  # Database URL

# Banking Provider (Plaid Sandbox - FREE)
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox

# Market Data (Alpha Vantage - FREE TIER)
ALPHAVANTAGE_API_KEY=your_api_key

# Crypto Data (CoinGecko - NO KEY REQUIRED)
# Works out of the box, no configuration needed!

# Investment Holdings (Plaid Investment API or SnapTrade)
ENABLE_INVESTMENTS=true
# Uses Plaid credentials above for 401k/IRA, or configure SnapTrade:
# SNAPTRADE_CLIENT_ID=your_snaptrade_client_id
# SNAPTRADE_CONSUMER_KEY=your_snaptrade_consumer_key

# Optional: AI Features (Google Gemini)
# GOOGLE_API_KEY=your_api_key

# Optional: Caching (Redis)
# REDIS_URL=redis://localhost:6379/0

# Observability
METRICS_ENABLED=true
```

## 🗄 Database Setup

### Quick Start (Development)

Use the provided `create_tables.py` script:

```bash
poetry run python create_tables.py
```

This creates tables directly using SQLAlchemy (no migrations).

### Production Setup (Migrations)

For production use with migration history:

```bash
# Initialize Alembic (already done in template)
poetry run alembic upgrade head
```

**See [docs/DATABASE.md](docs/DATABASE.md)** for complete database documentation.

##  Testing Features

### Without Any Configuration (Works Out of the Box)

These features work without any API keys:

```bash
# Cashflow calculations
curl -X POST http://localhost:8001/cashflows/npv \
  -H "Content-Type: application/json" \
  -d '{"rate": 0.08, "cashflows": [-10000, 3000, 4000, 5000]}'

# Response: {"npv": 1234.56}

# Symbol normalization
curl http://localhost:8001/normalize/symbol/AAPL

# Response: {"ticker": "AAPL", "cusip": "037833100", ...}

# Crypto prices (via CoinGecko free tier)
curl http://localhost:8001/crypto/quote/BTC

# Response: {"symbol": "BTC", "price": 43250.50, ...}
```

### With Plaid Sandbox (Free Account Required)

Sign up for Plaid at https://dashboard.plaid.com/signup (free sandbox account):

```bash
# 1. Get your credentials from Plaid Dashboard
# 2. Add to .env:
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox

# 3. Restart server
make run

# 4. Test banking integration
curl http://localhost:8001/banking/link

# Response includes Plaid Link token and instructions
# Use sandbox credentials: username=user_good, password=pass_good
```

### With Alpha Vantage (Free API Key)

Get free API key from https://www.alphavantage.co/support/#api-key:

```bash
# 1. Add to .env:
ALPHAVANTAGE_API_KEY=your_api_key

# 2. Restart server
make run

# 3. Test market data
curl http://localhost:8001/market/quote/AAPL

# Response: {"symbol": "AAPL", "price": 182.50, "change": +2.30, ...}
```

### With AI Features (Google Gemini)

Get free API key from https://makersuite.google.com/app/apikey:

```bash
# 1. Add to .env:
GOOGLE_API_KEY=your_api_key

# 2. Restart server
make run

# 3. Test AI conversation
curl -X POST http://localhost:8001/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How can I save more money?", "net_worth": 50000.0}'

# Response: AI-powered financial advice with follow-up questions
```

##  Quick Feature Test

Run this script to test all enabled features:

```bash
# Test all configured providers
python scripts/test_providers.py

# Output shows which providers are configured and working:
# [OK] Banking (Plaid) - Connected
# [OK] Market Data (Alpha Vantage) - Working
# [OK] Crypto (CoinGecko) - Working
# [!]  Credit (Experian) - Not configured
# [!]  Brokerage (Alpaca) - Not configured
```

## 📚 Key Files Reference

### Application Code

- **`src/fin_infra_template/main.py`** - FastAPI app with ALL 20+ capabilities (1500+ lines, 150+ comments)
- **`src/fin_infra_template/settings.py`** - Environment configuration (Pydantic Settings)
- **`src/fin_infra_template/api/v1/routes.py`** - Custom business logic routes
- **`src/fin_infra_template/db/models.py`** - SQLAlchemy models
- **`src/fin_infra_template/db/schemas.py`** - Pydantic schemas

### Configuration

- **`.env`** - Environment variables (created from `.env.example`)
- **`.env.example`** - Template with all configuration options
- **`pyproject.toml`** - Dependencies and project metadata
- **`alembic.ini`** - Database migration configuration

### Scripts

- **`scripts/quick_setup.py`** - Automated setup (models + migrations)
- **`scripts/scaffold_models.py`** - Generate database models
- **`scripts/test_providers.py`** - Test provider connections
- **`create_tables.py`** - Quick table creation (dev mode)
- **`run.sh`** - Server startup script

### Documentation

- **`README.md`** - Complete overview (this directory)
- **`QUICKSTART.md`** - This file
- **`USAGE.md`** - Detailed usage examples
- **`docs/CAPABILITIES.md`** - All fin-infra features explained
- **`docs/DATABASE.md`** - Database setup guide
- **`docs/PROVIDERS.md`** - Provider configuration guide

##  Next Steps

1. **Enable more providers** - Add API keys for Experian, Alpaca, etc.
2. **Read USAGE.md** - Detailed examples for all 20+ features
3. **Explore main.py** - 150+ comments explaining every integration
4. **Add custom logic** - Extend `api/v1/routes.py` with your business logic
5. **Customize models** - Modify `db/models.py` for your domain

##  Common Issues

### Poetry not found

```bash
# Install Poetry
pip install poetry

# Or via official installer
curl -sSL https://install.python-poetry.org | python3 -
```

### Port already in use

```bash
# Find process using port 8001
lsof -i :8001

# Kill process
kill -9 <PID>

# Or change port in .env
API_PORT=8002
```

### Database locked error

```bash
# Remove existing database
rm -f /tmp/fin_infra_template.db

# Recreate tables
python create_tables.py
```

### Provider connection errors

```bash
# Verify credentials in .env
cat .env | grep PLAID

# Test specific provider
python scripts/test_providers.py --provider plaid

# Check provider status
curl http://localhost:8001/_health
```

## 📖 Learning Resources

- **Inline Documentation**: Read `main.py` - every feature is explained with comments
- **API Documentation**: Visit http://localhost:8001/docs for interactive API reference
- **Capability Docs**: Each capability has scoped docs (e.g., `/banking/docs`, `/analytics/docs`)
- **Usage Guide**: See [USAGE.md](USAGE.md) for copy-paste code examples
- **Provider Setup**: See [docs/PROVIDERS.md](docs/PROVIDERS.md) for credential setup

##  Production Deployment

Ready to deploy? Here's what you need:

1. **Use PostgreSQL** - Update `SQL_URL` to PostgreSQL connection string
2. **Enable Redis** - Set `REDIS_URL` for caching and jobs
3. **Production providers** - Switch from sandbox to production credentials
4. **Set APP_ENV=prod** - Enables production logging and security
5. **Configure secrets** - Use environment variables, not `.env` file
6. **Run migrations** - Use `alembic upgrade head` instead of `create_tables.py`

**See [docs/DATABASE.md](docs/DATABASE.md)** for production database setup.

---

**Need help?** Check [docs/](docs/) or open an issue on GitHub.
