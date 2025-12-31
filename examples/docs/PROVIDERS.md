# Provider Configuration Guide

Complete setup guide for all fin-infra provider integrations.

## Table of Contents

- [Overview](#overview)
- [Banking Providers](#banking-providers)
- [Market Data Providers](#market-data-providers)
- [Crypto Data Providers](#crypto-data-providers)
- [Credit Score Providers](#credit-score-providers)
- [Brokerage Providers](#brokerage-providers)
- [AI/LLM Providers](#aillm-providers)
- [Provider Comparison](#provider-comparison)
- [Cost Estimates](#cost-estimates)
- [Rate Limits](#rate-limits)
- [Troubleshooting](#troubleshooting)

---

## Overview

fin-infra supports **20+ provider integrations** across 6 domains. Most providers offer:

- **Free tier** for development/testing
- **Sandbox mode** for testing without real data
- **Production tier** with usage-based pricing

### Quick Start Priority

**Test without any API keys** (works immediately):
- [OK] Categorization (local rules)
- [OK] Recurring detection (local algorithms)
- [OK] Cashflows (numpy-financial calculations)
- [OK] Normalization (offline symbol resolution)

**Free tier** (sign up, add API key):
- [OK] Alpha Vantage (market data) - 100/day free
- [OK] CoinGecko (crypto data) - 50/min free
- [OK] Google Gemini (AI insights) - Free with limits

**Sandbox mode** (test with fake data):
- [OK] Plaid (banking) - Unlimited sandbox requests
- [OK] Alpaca (brokerage) - Paper trading free

**Production** (requires billing):
- Plaid ($0.05-0.30 per item/month)
- Alpha Vantage Pro ($50/month)
- Experian credit scores (contact for pricing)

---

## Banking Providers

### Plaid (Recommended)

**Best for**: Personal finance apps, lending platforms, wealth management  
**Coverage**: 10,000+ institutions in US/Canada  
**Data**: Accounts, transactions, balances, identity, income

#### Setup

1. **Sign up**: https://dashboard.plaid.com/signup
2. **Get credentials**: Dashboard → Keys
3. **Configure** `.env`:

```bash
# Sandbox (free unlimited testing)
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_sandbox_secret
PLAID_ENV=sandbox

# Development (100 items/day free)
# PLAID_ENV=development

# Production (billing required)
# PLAID_SECRET=your_production_secret
# PLAID_ENV=production
```

4. **Test connection**:

```bash
curl http://localhost:8001/banking/link
# Should return: {"link_token": "link-sandbox-...", ...}
```

#### Sandbox Credentials

Use these in Plaid Link UI for testing:

- **Username**: `user_good`
- **Password**: `pass_good`
- **MFA**: `1234` (if prompted)

#### Pricing

| Tier | Cost | Includes |
|------|------|----------|
| Sandbox | Free | Unlimited requests |
| Development | Free | 100 items |
| Production | $0.05-0.30/item/month | Based on product mix |

**Item** = one user's connection to one institution

#### Rate Limits

- Sandbox: Unlimited
- Development: 100 items total
- Production: 500 req/sec

### Teller (Alternative)

**Best for**: Easier integration, international support  
**Coverage**: 5,000+ institutions globally

#### Setup

```bash
TELLER_APP_ID=your_app_id
TELLER_API_KEY=your_api_key
TELLER_ENV=sandbox  # or production

# Certificate-based auth (optional)
TELLER_CERTIFICATE_PATH=/path/to/cert.pem
TELLER_PRIVATE_KEY_PATH=/path/to/key.pem
```

#### Pricing

- **Sandbox**: Free
- **Production**: $0.10/item/month

---

## Market Data Providers

### Alpha Vantage (Default)

**Best for**: Hobby projects, free tier apps  
**Coverage**: Global stocks, forex, crypto

#### Setup

1. **Sign up**: https://www.alphavantage.co/support/#api-key
2. **Get free API key**
3. **Configure** `.env`:

```bash
ALPHA_VANTAGE_API_KEY=your_api_key
```

4. **Test**:

```bash
curl http://localhost:8001/market/quote/AAPL
```

#### Pricing

| Tier | Cost | Rate Limit |
|------|------|------------|
| Free | $0 | 5 calls/min, 100/day |
| Premium | $50/month | 75 calls/min, 2000/day |
| Ultra | $250/month | 300 calls/min, 10000/day |

#### Rate Limits

- Free: 5 req/min, 100 req/day
- Premium: 75 req/min, 2000 req/day

### Yahoo Finance (Fallback)

**Best for**: No API key needed  
**Coverage**: Global stocks, ETFs, indices

#### Setup

No configuration needed! Auto-enabled if Alpha Vantage not configured.

#### Limitations

- Unofficial API (may break)
- Rate limited (~2000 req/hour)
- No guaranteed SLA

### Polygon (Premium)

**Best for**: Real-time data, production apps  
**Coverage**: US stocks, options, forex, crypto

#### Setup

```bash
POLYGON_API_KEY=your_api_key
```

#### Pricing

- **Free**: 5 calls/min
- **Starter** ($29/month): 100 calls/min
- **Developer** ($99/month): 1000 calls/min, real-time data

---

## Crypto Data Providers

### CoinGecko (Default)

**Best for**: Free crypto data  
**Coverage**: 10,000+ coins

#### Setup

```bash
# Free tier (50 calls/min, no key needed)
# Just works!

# Pro tier (500 calls/min)
COINGECKO_API_KEY=your_api_key
```

#### Test

```bash
curl http://localhost:8001/crypto/quote/BTC
```

#### Pricing

- **Free**: $0, 50 calls/min
- **Analyst** ($129/month): 500 calls/min
- **Pro** ($399/month): 2000 calls/min

### CCXT (Alternative)

**Best for**: Exchange-specific data, trading bots  
**Coverage**: 100+ exchanges

#### Setup

```bash
CCXT_EXCHANGE=binance  # or coinbase, kraken, etc.
CCXT_API_KEY=your_exchange_api_key  # If private data needed
CCXT_SECRET=your_exchange_secret
```

---

## Credit Score Providers

### Experian (Enterprise)

**Best for**: Lending platforms, credit monitoring  
**Coverage**: US credit reports

#### Setup

```bash
EXPERIAN_API_KEY=your_api_key
EXPERIAN_CLIENT_SECRET=your_client_secret
EXPERIAN_SUBCODE=your_subcode
EXPERIAN_ENV=sandbox  # or production
```

#### Pricing

Contact Experian sales (typically $1-5 per pull)

### Equifax (Planned)

Coming soon.

### TransUnion (Planned)

Coming soon.

---

## Brokerage Providers

### Alpaca (Default)

**Best for**: Paper trading, algo trading, robo-advisors  
**Coverage**: US stocks, ETFs, crypto

#### Setup

1. **Sign up**: https://alpaca.markets
2. **Get paper trading keys** (free)
3. **Configure** `.env`:

```bash
# Paper trading (free forever)
ALPACA_API_KEY=your_paper_api_key
ALPACA_SECRET_KEY=your_paper_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Live trading (requires funded account)
# ALPACA_API_KEY=your_live_api_key
# ALPACA_SECRET_KEY=your_live_secret_key
# ALPACA_BASE_URL=https://api.alpaca.markets
```

4. **Test**:

```bash
curl http://localhost:8001/brokerage/account
# Should return: {"buying_power": 100000, ...}
```

#### Pricing

- **Paper trading**: Free forever
- **Live trading**: Commission-free stock trades

### Interactive Brokers (Planned)

Coming soon.

### SnapTrade (Planned)

Coming soon.

---

## AI/LLM Providers

**Powered by ai-infra** (supports 10+ providers)

### Google Gemini (Recommended)

**Best for**: Free tier, fast, multimodal  
**Coverage**: Text, vision, code

#### Setup

1. **Get API key**: https://makersuite.google.com/app/apikey
2. **Configure** `.env`:

```bash
GOOGLE_GENAI_API_KEY=your_api_key
```

3. **Test AI insights**:

```bash
curl http://localhost:8001/analytics/advice/user_123
```

#### Pricing

- **Free tier**: 60 requests/min, 1500/day
- **Pay-as-you-go**: $0.00025/1K chars

### OpenAI (Alternative)

**Best for**: Advanced reasoning, function calling

#### Setup

```bash
OPENAI_API_KEY=your_api_key
```

#### Pricing

- **GPT-4**: $0.03/1K tokens (input), $0.06/1K (output)
- **GPT-3.5**: $0.0015/1K (input), $0.002/1K (output)

### Anthropic Claude (Alternative)

**Best for**: Long context, safety

#### Setup

```bash
ANTHROPIC_API_KEY=your_api_key
```

#### Pricing

- **Claude 3 Opus**: $15/1M tokens (input), $75/1M (output)
- **Claude 3 Sonnet**: $3/1M (input), $15/1M (output)

---

## Provider Comparison

### Banking

| Provider | Coverage | Free Tier | Production Cost | Sandbox |
|----------|----------|-----------|-----------------|---------|
| Plaid | 10K+ institutions | 100 items | $0.05-0.30/item/mo | [OK] |
| Teller | 5K+ institutions | No | $0.10/item/mo | [OK] |

### Market Data

| Provider | Coverage | Free Tier | Production Cost | Real-time |
|----------|----------|-----------|-----------------|-----------|
| Alpha Vantage | Global | 100/day | $50/mo (2000/day) | [X] (15min delay) |
| Yahoo Finance | Global | ~2000/hr | Free | [X] (15min delay) |
| Polygon | US | 5/min | $99/mo | [OK] |

### Crypto Data

| Provider | Coverage | Free Tier | Production Cost |
|----------|----------|-----------|-----------------|
| CoinGecko | 10K+ coins | 50/min | $129/mo (500/min) |
| CCXT | 100+ exchanges | Varies | Free (exchange fees apply) |

### AI/LLM

| Provider | Free Tier | Production Cost | Speed |
|----------|-----------|-----------------|-------|
| Google Gemini | 1500/day | $0.00025/1K | Fast |
| OpenAI GPT-3.5 | No | $0.002/1K | Fast |
| Anthropic Claude | No | $3/1M | Medium |

---

## Cost Estimates

### Development (Free)

```bash
# Total: $0/month
[OK] Plaid sandbox - Free
[OK] Alpha Vantage free tier - Free
[OK] CoinGecko free tier - Free
[OK] Google Gemini free tier - Free
[OK] Alpaca paper trading - Free
```

### Small Production App (1000 users)

```bash
# Assuming 50% user engagement
[OK] Plaid (500 items) - $25-150/mo
[OK] Alpha Vantage Premium - $50/mo
[OK] CoinGecko Pro - $0 (free tier sufficient)
[OK] Google Gemini pay-as-you-go - $5-10/mo
[OK] Alpaca live trading - $0 (commission-free)

Total: $80-210/month
```

### Medium Production App (10K users)

```bash
[OK] Plaid (5000 items) - $250-1500/mo
[OK] Polygon Developer - $99/mo
[OK] CoinGecko Analyst - $129/mo
[OK] Google Gemini - $20-50/mo
[OK] Alpaca - $0

Total: $500-1800/month
```

---

## Rate Limits

### Summary Table

| Provider | Free | Paid | Caching |
|----------|------|------|---------|
| Plaid | Unlimited | 500 req/sec | N/A |
| Alpha Vantage | 5/min, 100/day | 75/min | 1 min |
| CoinGecko | 50/min | 500/min | 1 min |
| Alpaca | N/A | 200 req/min | N/A |
| Google Gemini | 60/min | Same | 24hr (insights) |

### Optimization Strategies

1. **Cache aggressively**: fin-infra caches quotes (1min), analytics (24hr), normalizations (7days)
2. **Batch requests**: Use `/market/quotes?symbols=AAPL,GOOGL` instead of multiple calls
3. **Polling intervals**: Poll balances every 1-6 hours, not continuously
4. **Webhooks**: Use Plaid webhooks for transaction updates instead of polling

---

## Troubleshooting

### Error: "Provider not configured"

**Cause**: Missing environment variables

**Solution**:
```bash
# Check .env file exists
ls -la .env

# Verify required keys set
grep PLAID_CLIENT_ID .env

# Restart server after changes
make restart
```

### Error: "API rate limit exceeded"

**Cause**: Too many requests to free tier provider

**Solutions**:
- Wait for rate limit reset (check headers)
- Upgrade to paid tier
- Enable caching (already on by default)
- Reduce polling frequency

### Error: "Invalid API key"

**Cause**: Incorrect key or wrong environment

**Solutions**:
- Verify key in provider dashboard
- Check for extra spaces in `.env`
- Ensure correct environment (sandbox vs production)

### Error: "Sandbox credentials expired"

**Cause**: Plaid sandbox tokens expire

**Solution**:
```bash
# Generate new link token
curl http://localhost:8001/banking/link

# Complete Link flow again with new token
```

### Provider Fallbacks

fin-infra automatically falls back:

- **Market data**: Alpha Vantage → Yahoo Finance
- **Crypto data**: CoinGecko → CCXT (if configured)

Check logs for fallback messages:
```bash
poetry run python src/main.py 2>&1 | grep "fallback"
```

---

## Production Checklist

Before deploying to production:

- [ ] Switch all providers from sandbox to production
- [ ] Set production API keys in secure secrets manager (not `.env`)
- [ ] Enable rate limit monitoring
- [ ] Set up provider webhook handlers (Plaid, Stripe)
- [ ] Configure Redis for distributed caching
- [ ] Set up alerts for API quota exhaustion
- [ ] Review provider terms of service
- [ ] Test error handling for each provider
- [ ] Document provider SLAs for users
- [ ] Set up cost tracking dashboards

---

## Next Steps

- **Test providers**: See [USAGE.md](../USAGE.md) for examples
- **Configure database**: Check [DATABASE.md](DATABASE.md)
- **Explore features**: Read [CAPABILITIES.md](CAPABILITIES.md)

---

**Questions?** Open an issue or check the main [README.md](../README.md).
