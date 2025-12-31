"""
API routes for v1 endpoints - Custom financial features.

This module demonstrates custom financial endpoints that complement the
auto-generated CRUD endpoints (available at /_sql/*).

Features covered:
- Health checks and feature status
- Banking integration (account linking, balance sync)
- Market data (quotes, historical prices)
- Credit monitoring (scores, reports)
- Brokerage (portfolio, positions, orders)
- Financial analytics (cash flow, net worth, insights)
- AI-powered categorization and insights

Note: Auto-generated CRUD endpoints are available at:
  /_sql/users - User management
  /_sql/accounts - Account management
  /_sql/transactions - Transaction management
  /_sql/positions - Investment positions
  /_sql/goals - Financial goals
  /_sql/budgets - Budget tracking
  /_sql/documents - Document management
  /_sql/net-worth-snapshots - Net worth snapshots
"""

from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from svc_infra.api.fastapi.dual.public import public_router

from fin_infra_template.settings import settings

# from svc_infra.api.fastapi.dual.protected import user_router  # For authenticated routes
# from svc_infra.db.sql.session import SqlSessionDep  # For database dependency


# ============================================================================
# Router Setup
# ============================================================================
# Using public_router from svc-infra for consistent dual-route registration
router = public_router()


# ============================================================================
# Health & Status Endpoints
# ============================================================================


@router.get("/ping")
async def ping():
    """Simple health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/status")
async def status():
    """
    Detailed service status including provider connectivity.

    Returns feature flags and provider configuration status.
    Useful for monitoring dashboards and client applications.
    """
    return {
        "status": "healthy",
        "service": "fin-infra-template",
        "version": "0.1.0",
        "environment": settings.app_env,
        "features": {
            "database": settings.database_configured,
            "cache": settings.cache_configured,
            "banking": settings.banking_configured,
            "market_data": settings.market_data_configured,
            "credit": settings.credit_configured,
            "brokerage": settings.brokerage_configured,
            "investments": settings.investments_configured,
            "tax": settings.enable_tax,
            "analytics": settings.enable_analytics,
            "budgets": settings.enable_budgets,
            "goals": settings.enable_goals,
            "documents": settings.enable_documents,
            "net_worth": settings.enable_net_worth,
            "recurring": settings.enable_recurring,
            "categorization": settings.enable_categorization,
            "insights": settings.enable_insights,
            "crypto_insights": settings.enable_crypto_insights,
            "rebalancing": settings.enable_rebalancing,
            "scenarios": settings.enable_scenarios,
            "ai_llm": settings.llm_configured,
        },
        "providers": {
            "banking": {
                "plaid": bool(settings.plaid_client_id and settings.plaid_secret),
                "teller": bool(settings.teller_api_key),
                "mx": bool(settings.mx_client_id and settings.mx_api_key),
            },
            "market_data": {
                "alphavantage": bool(settings.alphavantage_api_key),
                "polygon": bool(settings.polygon_api_key),
            },
            "credit": {
                "experian": bool(settings.experian_client_id and settings.experian_client_secret),
                "equifax": bool(settings.equifax_client_id and settings.equifax_client_secret),
                "transunion": bool(
                    settings.transunion_client_id and settings.transunion_client_secret
                ),
            },
            "brokerage": {
                "alpaca": bool(settings.alpaca_api_key and settings.alpaca_secret_key),
                "ib": bool(settings.ib_username and settings.ib_password),
                "snaptrade": bool(settings.snaptrade_client_id and settings.snaptrade_consumer_key),
            },
            "investments": {
                "plaid": bool(settings.plaid_client_id and settings.plaid_secret),
                "snaptrade": bool(settings.snaptrade_client_id and settings.snaptrade_consumer_key),
            },
            "tax": {
                "irs": bool(settings.irs_username and settings.irs_password),
                "taxbit": bool(settings.taxbit_client_id and settings.taxbit_client_secret),
            },
            "ai": {
                "google_gemini": bool(settings.google_api_key),
                "openai": bool(settings.openai_api_key),
            },
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/features")
async def features():
    """
    List all available features with detailed capability information.

    Useful for client applications to dynamically enable/disable UI features
    based on backend configuration.
    """
    return {
        "banking": {
            "enabled": settings.enable_banking,
            "configured": settings.banking_configured,
            "providers": ["plaid", "teller", "mx"],
            "capabilities": [
                "Link bank accounts",
                "Fetch account balances",
                "Retrieve transactions",
                "Get account details",
            ],
        },
        "market_data": {
            "enabled": settings.enable_market_data,
            "configured": settings.market_data_configured,
            "providers": ["alphavantage", "yahoo_finance", "polygon"],
            "capabilities": [
                "Real-time stock quotes",
                "Historical price data",
                "Market news",
                "Technical indicators",
            ],
        },
        "credit": {
            "enabled": settings.enable_credit,
            "configured": settings.credit_configured,
            "providers": ["experian", "equifax", "transunion"],
            "capabilities": [
                "Credit score monitoring",
                "Credit report retrieval",
                "Credit alerts",
                "Score factors analysis",
            ],
        },
        "brokerage": {
            "enabled": settings.enable_brokerage,
            "configured": settings.brokerage_configured,
            "providers": ["alpaca", "interactive_brokers", "snaptrade"],
            "capabilities": [
                "Portfolio management",
                "Order execution",
                "Position tracking",
                "Trade history",
            ],
        },
        "investments": {
            "enabled": settings.enable_investments,
            "configured": settings.investments_configured,
            "providers": ["plaid", "snaptrade"],
            "capabilities": [
                "Investment holdings (real-time)",
                "Cost basis tracking",
                "Real P/L calculations",
                "Asset allocation analysis",
                "Multi-account aggregation",
            ],
        },
        "analytics": {
            "enabled": settings.enable_analytics,
            "capabilities": [
                "Cash flow analysis",
                "Savings rate calculation",
                "Portfolio performance",
                "Spending insights",
            ],
        },
        "budgets": {
            "enabled": settings.enable_budgets,
            "capabilities": [
                "Budget creation",
                "Spending tracking",
                "Overspending alerts",
                "Budget vs actual reports",
            ],
        },
        "goals": {
            "enabled": settings.enable_goals,
            "capabilities": [
                "Goal creation",
                "Progress tracking",
                "Milestone management",
                "Goal recommendations",
            ],
        },
        "documents": {
            "enabled": settings.enable_documents,
            "capabilities": [
                "Document upload",
                "OCR text extraction",
                "AI document analysis",
                "Document search",
            ],
        },
        "insights": {
            "enabled": settings.enable_insights,
            "configured": settings.llm_configured,
            "capabilities": [
                "AI-generated insights",
                "Spending pattern analysis",
                "Savings recommendations",
                "Personalized tips",
            ],
        },
    }


# ============================================================================
# Banking Endpoints
# ============================================================================


@router.get("/banking/accounts")
async def list_bank_accounts():
    """
    Retrieve all linked bank accounts across providers.

    This endpoint aggregates accounts from Plaid, Teller, and MX.
    For detailed account information, use /_sql/accounts endpoint.
    """
    if not settings.enable_banking:
        raise HTTPException(status_code=503, detail="Banking feature is disabled")

    if not settings.banking_configured:
        raise HTTPException(status_code=503, detail="No banking providers configured")

    # TODO: Implement actual banking provider integration
    # from fin_infra.banking import easy_banking
    # banking = easy_banking(provider="plaid")
    # accounts = await banking.get_accounts(access_token)

    return {
        "message": "Banking integration ready",
        "providers": {
            "plaid": bool(settings.plaid_client_id),
            "teller": bool(settings.teller_api_key),
            "mx": bool(settings.mx_client_id),
        },
        "accounts": [
            {
                "id": "acc_demo_1",
                "provider": "plaid",
                "name": "Chase Checking",
                "type": "depository",
                "subtype": "checking",
                "balance": 5432.10,
                "currency": "USD",
                "last_synced": datetime.utcnow().isoformat(),
            },
            {
                "id": "acc_demo_2",
                "provider": "plaid",
                "name": "Amex Gold Card",
                "type": "credit",
                "subtype": "credit_card",
                "balance": -1234.56,
                "currency": "USD",
                "last_synced": datetime.utcnow().isoformat(),
            },
        ],
        "note": "This is demo data. Configure providers in .env for real data.",
    }


@router.post("/banking/link")
async def create_link_token():
    """
    Create a Plaid Link token for account linking.

    Returns a token that frontend can use to initialize Plaid Link.
    """
    if not settings.enable_banking:
        raise HTTPException(status_code=503, detail="Banking feature is disabled")

    if not (settings.plaid_client_id and settings.plaid_secret):
        raise HTTPException(status_code=503, detail="Plaid not configured")

    # TODO: Implement actual Plaid Link token creation
    # from fin_infra.banking.plaid import PlaidAdapter
    # plaid = PlaidAdapter(...)
    # link_token = await plaid.create_link_token(user_id)

    return {
        "link_token": "link-sandbox-demo-token",
        "expiration": (datetime.utcnow()).isoformat(),
        "note": "Configure PLAID_CLIENT_ID and PLAID_SECRET for real tokens",
    }


# ============================================================================
# Market Data Endpoints
# ============================================================================


@router.get("/market/quote/{symbol}")
async def get_quote(symbol: str):
    """
    Get real-time quote for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, TSLA)

    Returns quote with current price, change, volume, etc.
    """
    if not settings.enable_market_data:
        raise HTTPException(status_code=503, detail="Market data feature is disabled")

    if not settings.market_data_configured:
        raise HTTPException(status_code=503, detail="No market data providers configured")

    # TODO: Implement actual market data integration
    # from fin_infra.markets import easy_market
    # market = easy_market(provider="alphavantage")
    # quote = await market.quote(symbol)

    return {
        "symbol": symbol.upper(),
        "price": 175.43,
        "change": 2.34,
        "change_percent": 1.35,
        "volume": 54321000,
        "timestamp": datetime.utcnow().isoformat(),
        "provider": "alphavantage" if settings.alphavantage_api_key else "demo",
        "note": "Configure ALPHAVANTAGE_API_KEY for real-time data",
    }


@router.get("/market/historical/{symbol}")
async def get_historical(symbol: str, start_date: date, end_date: date):
    """
    Get historical price data for a symbol.

    Args:
        symbol: Stock ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns daily OHLCV data.
    """
    if not settings.enable_market_data:
        raise HTTPException(status_code=503, detail="Market data feature is disabled")

    # TODO: Implement actual historical data fetch
    return {
        "symbol": symbol.upper(),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "data": [
            {
                "date": "2024-01-15",
                "open": 173.50,
                "high": 176.20,
                "low": 172.80,
                "close": 175.43,
                "volume": 54321000,
            },
            # More data points...
        ],
        "note": "Configure market data provider for full historical data",
    }


# ============================================================================
# Credit Monitoring Endpoints
# ============================================================================


@router.get("/credit/score")
async def get_credit_score():
    """
    Retrieve current credit score from configured provider.

    Returns score, range, factors, and change from previous check.
    """
    if not settings.enable_credit:
        raise HTTPException(status_code=503, detail="Credit monitoring feature is disabled")

    if not settings.credit_configured:
        raise HTTPException(status_code=503, detail="No credit providers configured")

    # TODO: Implement actual credit score retrieval
    # from fin_infra.credit import easy_credit
    # credit = easy_credit(provider="experian")
    # score = await credit.get_score(user_id)

    return {
        "score": 742,
        "range": {"min": 300, "max": 850},
        "rating": "Good",
        "change": +5,
        "factors": [
            {"factor": "Payment History", "impact": "positive", "weight": 35},
            {"factor": "Credit Utilization", "impact": "positive", "weight": 30},
            {"factor": "Credit Age", "impact": "neutral", "weight": 15},
            {"factor": "Credit Mix", "impact": "positive", "weight": 10},
            {"factor": "Recent Inquiries", "impact": "neutral", "weight": 10},
        ],
        "provider": "experian" if settings.experian_client_id else "demo",
        "last_updated": datetime.utcnow().isoformat(),
        "note": "Configure EXPERIAN_CLIENT_ID and EXPERIAN_CLIENT_SECRET for real data",
    }


# ============================================================================
# Brokerage Endpoints
# ============================================================================


@router.get("/brokerage/portfolio")
async def get_portfolio():
    """
    Retrieve current investment portfolio from brokerage account.

    Returns positions, total value, gains/losses, and allocations.
    """
    if not settings.enable_brokerage:
        raise HTTPException(status_code=503, detail="Brokerage feature is disabled")

    if not settings.brokerage_configured:
        raise HTTPException(status_code=503, detail="No brokerage providers configured")

    # TODO: Implement actual brokerage integration
    # from fin_infra.brokerage import easy_brokerage
    # broker = easy_brokerage(provider="alpaca")
    # portfolio = await broker.get_portfolio()

    return {
        "total_value": 125432.18,
        "cash": 12543.00,
        "equity": 112889.18,
        "day_gain": 1234.56,
        "day_gain_pct": 0.99,
        "total_gain": 25432.18,
        "total_gain_pct": 25.43,
        "positions": [
            {
                "symbol": "AAPL",
                "quantity": 100,
                "cost_basis": 15000.00,
                "market_value": 17543.00,
                "gain_loss": 2543.00,
                "gain_loss_pct": 16.95,
            },
            {
                "symbol": "TSLA",
                "quantity": 50,
                "cost_basis": 12000.00,
                "market_value": 8750.00,
                "gain_loss": -3250.00,
                "gain_loss_pct": -27.08,
            },
        ],
        "provider": "alpaca" if settings.alpaca_api_key else "demo",
        "note": "Configure ALPACA_API_KEY and ALPACA_API_SECRET for real data",
    }


# ============================================================================
# Investments Endpoints
# ============================================================================


@router.get("/investments/holdings")
async def get_investment_holdings():
    """
    Retrieve investment holdings from connected accounts.

    Returns all holdings with real-time values, cost basis, and P/L.
    Supports both Plaid (401k, IRA) and SnapTrade (retail brokerage).
    """
    if not settings.enable_investments:
        raise HTTPException(status_code=503, detail="Investments feature is disabled")

    if not settings.investments_configured:
        raise HTTPException(
            status_code=503,
            detail="No investment providers configured (requires Plaid or SnapTrade)",
        )

    # TODO: Implement actual investments integration
    # from fin_infra.investments import easy_investments
    # investments = easy_investments(provider="plaid")
    # holdings = await investments.get_holdings(access_token)

    return {
        "holdings": [
            {
                "account_id": "acc_401k_123",
                "account_name": "Vanguard 401(k)",
                "security": {
                    "security_id": "VFIAX",
                    "ticker_symbol": "VFIAX",
                    "name": "Vanguard 500 Index Fund Admiral",
                    "type": "mutual_fund",
                    "close_price": 425.67,
                    "close_price_as_of": datetime.utcnow().isoformat(),
                },
                "quantity": 234.567,
                "institution_value": 99876.54,
                "institution_price": 425.67,
                "cost_basis": 85000.00,
                "currency": "USD",
                "unrealized_gain_loss": 14876.54,
                "unrealized_gain_loss_percent": 17.50,
            },
            {
                "account_id": "acc_ira_456",
                "account_name": "Fidelity Roth IRA",
                "security": {
                    "security_id": "AAPL",
                    "ticker_symbol": "AAPL",
                    "name": "Apple Inc",
                    "type": "equity",
                    "close_price": 175.43,
                    "close_price_as_of": datetime.utcnow().isoformat(),
                },
                "quantity": 100.0,
                "institution_value": 17543.00,
                "institution_price": 175.43,
                "cost_basis": 15000.00,
                "currency": "USD",
                "unrealized_gain_loss": 2543.00,
                "unrealized_gain_loss_percent": 16.95,
            },
        ],
        "total_value": 117419.54,
        "total_cost_basis": 100000.00,
        "total_unrealized_gain_loss": 17419.54,
        "total_unrealized_gain_loss_percent": 17.42,
        "provider": "plaid"
        if settings.plaid_client_id
        else "snaptrade"
        if settings.snaptrade_client_id
        else "demo",
        "last_updated": datetime.utcnow().isoformat(),
        "note": "Configure PLAID or SNAPTRADE credentials for real holdings data",
    }


@router.get("/investments/allocation")
async def get_asset_allocation():
    """
    Get asset allocation breakdown from investment holdings.

    Returns allocation by security type (equity, bond, cash, etc.)
    and optionally by sector.
    """
    if not settings.enable_investments:
        raise HTTPException(status_code=503, detail="Investments feature is disabled")

    if not settings.investments_configured:
        raise HTTPException(status_code=503, detail="No investment providers configured")

    # TODO: Implement actual allocation calculation
    # from fin_infra.investments import easy_investments
    # investments = easy_investments(provider="plaid")
    # allocation = await investments.get_allocation(access_token)

    return {
        "allocation_by_asset_class": [
            {
                "asset_class": "equity",
                "value": 70493.72,
                "percentage": 60.0,
            },
            {
                "asset_class": "mutual_fund",
                "value": 35246.86,
                "percentage": 30.0,
            },
            {
                "asset_class": "bond",
                "value": 11748.95,
                "percentage": 10.0,
            },
        ],
        "allocation_by_sector": [
            {
                "sector": "Technology",
                "value": 47013.53,
                "percentage": 40.0,
            },
            {
                "sector": "Healthcare",
                "value": 23506.77,
                "percentage": 20.0,
            },
            {
                "sector": "Financial",
                "value": 17630.08,
                "percentage": 15.0,
            },
            {
                "sector": "Consumer",
                "value": 14104.06,
                "percentage": 12.0,
            },
            {
                "sector": "Other",
                "value": 15265.10,
                "percentage": 13.0,
            },
        ],
        "total_value": 117419.54,
        "provider": "plaid" if settings.plaid_client_id else "demo",
        "calculated_at": datetime.utcnow().isoformat(),
        "note": "Based on current holdings and security metadata",
    }


@router.get("/investments/accounts")
async def get_investment_accounts():
    """
    List all investment accounts with aggregated metrics.

    Returns account details with total value, cost basis, and P/L per account.
    """
    if not settings.enable_investments:
        raise HTTPException(status_code=503, detail="Investments feature is disabled")

    if not settings.investments_configured:
        raise HTTPException(status_code=503, detail="No investment providers configured")

    # TODO: Implement actual accounts fetch
    # from fin_infra.investments import easy_investments
    # investments = easy_investments(provider="plaid")
    # accounts = await investments.get_investment_accounts(access_token)

    return {
        "accounts": [
            {
                "account_id": "acc_401k_123",
                "name": "Vanguard 401(k)",
                "type": "investment",
                "subtype": "401k",
                "institution": "Vanguard",
                "total_value": 99876.54,
                "total_cost_basis": 85000.00,
                "total_unrealized_gain_loss": 14876.54,
                "total_unrealized_gain_loss_percent": 17.50,
                "holdings_count": 5,
            },
            {
                "account_id": "acc_ira_456",
                "name": "Fidelity Roth IRA",
                "type": "investment",
                "subtype": "roth_ira",
                "institution": "Fidelity",
                "total_value": 17543.00,
                "total_cost_basis": 15000.00,
                "total_unrealized_gain_loss": 2543.00,
                "total_unrealized_gain_loss_percent": 16.95,
                "holdings_count": 3,
            },
        ],
        "total_value": 117419.54,
        "total_cost_basis": 100000.00,
        "total_unrealized_gain_loss": 17419.54,
        "provider": "plaid" if settings.plaid_client_id else "demo",
        "last_updated": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Analytics Endpoints
# ============================================================================


@router.get("/analytics/cash-flow")
async def get_cash_flow(start_date: date, end_date: date):
    """
    Calculate cash flow analysis for date range.

    Returns income, expenses, net cash flow, and trends.
    """
    if not settings.enable_analytics:
        raise HTTPException(status_code=503, detail="Analytics feature is disabled")

    # TODO: Implement actual cash flow calculation from transactions
    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "income": 8500.00,
        "expenses": 5234.56,
        "net_cash_flow": 3265.44,
        "savings_rate": 38.42,
        "categories": {
            "income": {
                "salary": 7500.00,
                "freelance": 800.00,
                "investments": 200.00,
            },
            "expenses": {
                "housing": 2000.00,
                "food": 800.00,
                "transportation": 500.00,
                "entertainment": 300.00,
                "other": 1634.56,
            },
        },
        "note": "Based on transactions in database",
    }


@router.get("/analytics/net-worth")
async def get_net_worth():
    """
    Calculate current net worth and historical trends.

    Returns assets, liabilities, net worth, and change over time.
    """
    if not settings.enable_net_worth:
        raise HTTPException(status_code=503, detail="Net worth tracking is disabled")

    # TODO: Implement actual net worth calculation
    return {
        "current": {
            "assets": 325432.18,
            "liabilities": 125000.00,
            "net_worth": 200432.18,
            "liquid_assets": 50000.00,
            "investment_assets": 125432.18,
            "real_estate": 150000.00,
        },
        "change": {
            "1_month": {"amount": 5432.10, "percent": 2.78},
            "3_months": {"amount": 12543.00, "percent": 6.68},
            "1_year": {"amount": 45321.18, "percent": 29.22},
        },
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Aggregated from accounts, positions, and manual assets",
    }


# ============================================================================
# Insights Endpoints (AI-Powered)
# ============================================================================


@router.get("/insights/feed")
async def get_insights_feed():
    """
    Get personalized financial insights feed.

    Returns AI-generated insights, recommendations, and alerts.
    Requires LLM configuration (Google Gemini or OpenAI).
    """
    if not settings.enable_insights:
        raise HTTPException(status_code=503, detail="Insights feature is disabled")

    if not settings.llm_configured:
        return {
            "insights": [],
            "note": "Configure GOOGLE_API_KEY or OPENAI_API_KEY for AI-powered insights",
        }

    # TODO: Implement actual AI insights generation
    # from fin_infra.insights import generate_insights
    # insights = await generate_insights(user_id, llm_provider=settings.google_model)

    return {
        "insights": [
            {
                "id": "insight_1",
                "type": "savings_opportunity",
                "title": "You could save $240/month on subscriptions",
                "description": (
                    "We detected 5 subscriptions totaling $240/month. "
                    "Consider canceling unused services like Netflix ($15.99) and Spotify ($9.99)."
                ),
                "priority": "high",
                "category": "subscriptions",
                "potential_savings": 240.00,
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "id": "insight_2",
                "type": "spending_pattern",
                "title": "Dining out spending up 35% this month",
                "description": (
                    "Your restaurant spending increased from $400 to $540 this month. "
                    "Try meal prepping to save an average of $150/month."
                ),
                "priority": "medium",
                "category": "food",
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "id": "insight_3",
                "type": "goal_progress",
                "title": "You're on track for your emergency fund goal! ",
                "description": (
                    "You've saved $8,500 toward your $10,000 emergency fund goal. "
                    "At your current rate, you'll reach it in 3 months."
                ),
                "priority": "low",
                "category": "goals",
                "created_at": datetime.utcnow().isoformat(),
            },
        ],
        "provider": settings.google_model if settings.google_api_key else settings.openai_model,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/insights/categorize")
async def categorize_transaction(description: str, amount: Decimal):
    """
    AI-powered transaction categorization.

    Args:
        description: Transaction description/merchant name
        amount: Transaction amount

    Returns suggested category, subcategory, and confidence.
    """
    if not settings.enable_categorization:
        raise HTTPException(status_code=503, detail="Categorization feature is disabled")

    if not settings.llm_configured:
        # Fallback to rule-based categorization
        return {
            "category": "uncategorized",
            "subcategory": None,
            "confidence": 0.0,
            "method": "none",
            "note": "Configure LLM provider for AI-powered categorization",
        }

    # TODO: Implement actual AI categorization
    # from fin_infra.categorization import categorize
    # result = await categorize(description, amount, llm=settings.google_model)

    return {
        "description": description,
        "amount": float(amount),
        "category": "food",
        "subcategory": "restaurants",
        "confidence": 0.95,
        "method": "ai",
        "reasoning": f"'{description}' is typically a restaurant based on common patterns",
        "provider": settings.google_model if settings.google_api_key else "demo",
    }


# ============================================================================
# Export router
# ============================================================================
# The router will be automatically discovered and mounted by setup_service_api()
# through the versions spec in main.py:
#   APIVersionSpec(tag="v1", routers_package="fin_infra_template.api.v1")
