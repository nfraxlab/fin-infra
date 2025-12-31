"""
Temporary FastAPI helper wrappers for fin-infra capabilities.

These functions provide add_*() style helpers until fin-infra Phase 3.5 is complete.
Each function wraps the existing easy_*() function and mounts routes using svc-infra dual routers.

NOTE: Some functions (add_analytics, add_documents, add_recurring_detection) exist in fin-infra
and are imported directly. Others are temporary wrappers.

TODO: Replace with proper fin-infra add_*() functions once Phase 3.5 is implemented.
"""

from typing import Any

from fastapi import FastAPI
from svc_infra.api.fastapi.dual.protected import user_router
from svc_infra.api.fastapi.dual.public import public_router

# Import the functions that already exist in fin-infra
from fin_infra.analytics.add import add_analytics
from fin_infra.budgets.add import add_budgets
from fin_infra.documents.add import add_documents
from fin_infra.goals.add import add_goals
from fin_infra.net_worth.add import add_net_worth_tracking
from fin_infra.recurring.add import add_recurring_detection

# Re-export them so they can be imported from this module
__all__ = [
    "add_analytics",
    "add_documents",
    "add_recurring_detection",
    "add_goals",
    "add_budgets",
    "add_net_worth_tracking",
]


def add_banking(app: FastAPI, provider: str | None = None, prefix: str = "/banking") -> Any:
    """Temporary wrapper - Mount banking routes."""
    from fin_infra.banking import easy_banking

    banking = easy_banking(provider=provider or "teller")
    router = public_router(prefix=prefix, tags=["Banking"])

    @router.get("/accounts")
    async def get_accounts():
        """Get all linked bank accounts."""
        return {"message": "Banking provider initialized", "provider": provider or "teller"}

    app.include_router(router)
    app.state.banking_provider = banking
    return banking


def add_crypto_data(app: FastAPI, provider: str | None = None, prefix: str = "/crypto") -> Any:
    """Temporary wrapper - Mount crypto data routes."""
    from fin_infra.crypto import easy_crypto

    crypto = easy_crypto(provider=provider or "coingecko")
    router = public_router(prefix=prefix, tags=["Crypto Data"])

    @router.get("/quote/{symbol}")
    async def get_crypto_quote(symbol: str):
        """Get cryptocurrency quote."""
        return crypto.quote(symbol)

    app.include_router(router)
    app.state.crypto_provider = crypto
    return crypto


def add_credit(app: FastAPI, provider: str | None = None, prefix: str = "/credit") -> Any:
    """Temporary wrapper - Mount credit score routes."""
    from fin_infra.credit import easy_credit

    credit = easy_credit(provider=provider or "experian")
    router = user_router(prefix=prefix, tags=["Credit Scores"])

    @router.get("/score")
    async def get_credit_score():
        """Get credit score."""
        return {"message": "Credit provider initialized", "provider": provider or "experian"}

    app.include_router(router)
    app.state.credit_provider = credit
    return credit


def add_brokerage(app: FastAPI, provider: str | None = None, prefix: str = "/brokerage") -> Any:
    """Temporary wrapper - Mount brokerage routes."""
    from fin_infra.brokerage import easy_brokerage

    brokerage = easy_brokerage(provider=provider or "alpaca")
    router = user_router(prefix=prefix, tags=["Brokerage"])

    @router.get("/portfolio")
    async def get_portfolio():
        """Get brokerage portfolio."""
        return {"message": "Brokerage provider initialized", "provider": provider or "alpaca"}

    app.include_router(router)
    app.state.brokerage_provider = brokerage
    return brokerage


def add_tax_data(app: FastAPI, provider: str | None = None, prefix: str = "/tax") -> Any:
    """Temporary wrapper - Mount tax data routes."""
    from fin_infra.tax import easy_tax

    tax = easy_tax(provider=provider or "mock")
    router = user_router(prefix=prefix, tags=["Tax Data"])

    @router.get("/documents")
    async def get_tax_documents():
        """Get tax documents."""
        return {"message": "Tax provider initialized", "provider": provider or "mock"}

    app.include_router(router)
    app.state.tax_provider = tax
    return tax


def add_categorization(app: FastAPI, prefix: str = "/categorize") -> Any:
    """Temporary wrapper - Mount categorization routes."""
    from fin_infra.categorization import easy_categorization

    categorizer = easy_categorization()
    router = public_router(prefix=prefix, tags=["Categorization"])

    @router.post("/predict")
    async def categorize_transaction(merchant: str, amount: float):
        """Categorize a transaction."""
        return {"message": "Categorization enabled", "merchant": merchant}

    app.include_router(router)
    app.state.categorization = categorizer
    return categorizer


def add_insights(app: FastAPI, prefix: str = "/insights") -> Any:
    """Temporary wrapper - Mount insights routes."""
    router = user_router(prefix=prefix, tags=["Insights"])

    @router.get("/feed")
    async def get_insights_feed():
        """Get personalized insights feed."""
        return {"insights": [], "message": "Insights module placeholder"}

    app.include_router(router)
    return None


# add_budgets, add_goals, add_net_worth_tracking are imported from fin-infra above


def add_financial_security(app: FastAPI) -> None:
    """Temporary wrapper - Add financial security middleware."""
    print("[!]  Financial security middleware placeholder (not yet implemented)")


def add_data_lifecycle(
    app: FastAPI, *, retention_days: int = 2555, prefix: str = "/lifecycle"
) -> None:
    """Temporary wrapper - Add data lifecycle tracking."""
    print(
        f"[!]  Data lifecycle tracking placeholder (retention: {retention_days} days, not yet implemented)"
    )


def add_normalization(app: FastAPI, prefix: str = "/normalize") -> Any:
    """Temporary wrapper - Mount normalization routes."""
    from fin_infra.normalization import easy_normalization

    normalizer = easy_normalization()
    router = public_router(prefix=prefix, tags=["Normalization"])

    @router.get("/symbol/{symbol}")
    async def normalize_symbol(symbol: str):
        """Normalize a stock symbol."""
        return {"symbol": symbol, "message": "Normalization enabled"}

    app.include_router(router)
    app.state.normalizer = normalizer
    return normalizer


def add_cashflows(app: FastAPI, prefix: str = "/cashflows") -> None:
    """Temporary wrapper - Mount cashflow calculation routes."""
    from fin_infra.cashflows.core import irr, npv

    router = public_router(prefix=prefix, tags=["Cashflows"])

    @router.post("/npv")
    async def calculate_npv(rate: float, cashflows: list[float]):
        """Calculate Net Present Value."""
        return {"npv": npv(rate, cashflows)}

    @router.post("/irr")
    async def calculate_irr(cashflows: list[float]):
        """Calculate Internal Rate of Return."""
        return {"irr": irr(cashflows)}

    app.include_router(router)
    print("[OK] Cashflow calculations enabled (NPV, IRR)")


def easy_financial_conversation(app: FastAPI, prefix: str = "/chat") -> None:
    """Temporary wrapper - Mount AI conversation routes."""
    router = user_router(prefix=prefix, tags=["AI Chat"])

    @router.post("/")
    async def ask_question(question: str):
        """Ask a financial planning question."""
        return {"answer": "AI conversation not yet configured", "question": question}

    app.include_router(router)
