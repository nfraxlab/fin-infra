"""FastAPI integration for tax data.

add_tax_data() helper wires tax document routes to FastAPI app.
Uses svc-infra dual routers for consistent auth and OpenAPI docs.

Example:
    >>> from fastapi import FastAPI
    >>> from fin_infra.tax.add import add_tax_data
    >>>
    >>> app = FastAPI()
    >>> tax_provider = add_tax_data(app)
    >>>
    >>> # Routes mounted:
    >>> # GET /tax/documents?user_id=...&tax_year=2024
    >>> # GET /tax/documents/{document_id}
    >>> # POST /tax/crypto-gains
"""

from decimal import Decimal

from fastapi import Body, FastAPI, Query
from pydantic import BaseModel

from fin_infra.providers.base import TaxProvider
from fin_infra.tax.tlh import TLHOpportunity, TLHScenario


class CryptoGainsRequest(BaseModel):
    """Request body for crypto gains calculation."""

    user_id: str
    tax_year: int
    transactions: list[dict]  # List of crypto trades
    cost_basis_method: str = "FIFO"  # "FIFO", "LIFO", "HIFO"


class TaxLiabilityRequest(BaseModel):
    """Request body for tax liability estimation."""

    user_id: str
    tax_year: int
    income: Decimal
    deductions: Decimal
    filing_status: str  # "single", "married_joint", etc.
    state: str | None = None  # Two-letter state code (e.g., "CA")


class TLHScenarioRequest(BaseModel):
    """Request body for TLH scenario simulation."""

    opportunities: list[TLHOpportunity]
    tax_rate: Decimal | None = None


def add_tax_data(
    app: FastAPI,
    provider: TaxProvider | str | None = None,
    prefix: str = "/tax",
) -> TaxProvider:
    """Wire tax data routes to FastAPI app.

    Mounts tax document retrieval and crypto tax calculation endpoints.
    Uses svc-infra user_router for protected routes (requires authentication).

    Args:
        app: FastAPI application instance
        provider: Tax provider instance or name (default: "mock")
        prefix: URL prefix for routes (default: "/tax")

    Returns:
        Configured TaxProvider instance

    Routes:
        GET {prefix}/documents: List all tax documents for user and year
        GET {prefix}/documents/{document_id}: Get specific tax document
        POST {prefix}/crypto-gains: Calculate crypto capital gains
        POST {prefix}/tax-liability: Estimate tax liability

    Example:
        >>> from fastapi import FastAPI
        >>> from fin_infra.tax.add import add_tax_data
        >>>
        >>> app = FastAPI()
        >>> tax = add_tax_data(app, provider="mock", prefix="/tax")
        >>>
        >>> # Now routes are available:
        >>> # GET /tax/documents?user_id=user123&tax_year=2024
        >>> # GET /tax/documents/w2_2024_user123
        >>> # POST /tax/crypto-gains
        >>> # POST /tax/tax-liability
    """
    # Use svc-infra user_router for authentication (tax data is user-specific and sensitive)
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
    from svc_infra.api.fastapi.dual.protected import user_router

    # Initialize provider
    if provider is None:
        # Import here to avoid circular import
        from fin_infra.tax import easy_tax

        provider = easy_tax()
    elif isinstance(provider, str):
        from fin_infra.tax import easy_tax

        provider = easy_tax(provider=provider)

    # Create router with svc-infra user_router for authentication
    router = user_router(prefix=prefix, tags=["Tax Data"])

    @router.get("/documents")
    async def get_tax_documents(
        user_id: str = Query(..., description="User identifier"),
        tax_year: int = Query(..., description="Tax year (e.g., 2024)"),
    ):
        """Retrieve all tax documents for a user and tax year.

        Returns W-2, 1099-INT, 1099-DIV, 1099-B, 1099-MISC forms.

        Args:
            user_id: User identifier
            tax_year: Tax year (e.g., 2024)

        Returns:
            List of tax documents

        Example:
            GET /tax/documents?user_id=user123&tax_year=2024

            Response:
            [
              {
                "document_id": "w2_2024_user123",
                "user_id": "user123",
                "form_type": "W2",
                "tax_year": 2024,
                "issuer": "Acme Corporation",
                "wages": "75000.00",
                "federal_tax_withheld": "12000.00",
                ...
              },
              ...
            ]
        """
        return await provider.get_tax_documents(user_id, tax_year)

    @router.get("/documents/{document_id}")
    async def get_tax_document(document_id: str):
        """Retrieve a specific tax document by ID.

        Args:
            document_id: Document identifier (e.g., "w2_2024_user123")

        Returns:
            Tax document

        Example:
            GET /tax/documents/w2_2024_user123

            Response:
            {
              "document_id": "w2_2024_user123",
              "form_type": "W2",
              "wages": "75000.00",
              ...
            }
        """
        return await provider.get_tax_document(document_id)

    @router.post("/crypto-gains")
    async def calculate_crypto_gains(request: CryptoGainsRequest = Body(...)):
        """Calculate cryptocurrency capital gains/losses.

        Supports FIFO, LIFO, HIFO cost basis methods.
        Generates Form 8949 data and capital gains summary.

        Args:
            request: Crypto gains request with transactions

        Returns:
            CryptoTaxReport with gains/losses breakdown

        Example:
            POST /tax/crypto-gains
            {
              "user_id": "user123",
              "tax_year": 2024,
              "transactions": [
                {
                  "symbol": "BTC",
                  "type": "sell",
                  "date": "2024-06-20",
                  "quantity": 0.5,
                  "price": 60000.00,
                  "cost_basis": 40000.00
                }
              ],
              "cost_basis_method": "FIFO"
            }

            Response:
            {
              "user_id": "user123",
              "tax_year": 2024,
              "total_gain_loss": "10000.00",
              "short_term_gain_loss": "0.00",
              "long_term_gain_loss": "10000.00",
              "transaction_count": 1,
              "cost_basis_method": "FIFO",
              "transactions": [...]
            }
        """
        return await provider.calculate_crypto_gains(
            user_id=request.user_id,
            transactions=request.transactions,
            tax_year=request.tax_year,
            cost_basis_method=request.cost_basis_method,
        )

    @router.post("/tax-liability")
    async def calculate_tax_liability(request: TaxLiabilityRequest = Body(...)):
        """Estimate tax liability (basic calculation).

        NOT a substitute for professional tax advice.
        Uses simplified tax brackets (not actual IRS tables).

        Args:
            request: Tax liability request with income and deductions

        Returns:
            TaxLiability estimate

        Example:
            POST /tax/tax-liability
            {
              "user_id": "user123",
              "tax_year": 2024,
              "income": "100000.00",
              "deductions": "14600.00",
              "filing_status": "single",
              "state": "CA"
            }

            Response:
            {
              "user_id": "user123",
              "tax_year": 2024,
              "filing_status": "single",
              "gross_income": "100000.00",
              "deductions": "14600.00",
              "taxable_income": "85400.00",
              "federal_tax": "12810.00",
              "state_tax": "4270.00",
              "total_tax": "17080.00",
              "effective_tax_rate": "17.08"
            }
        """
        return await provider.calculate_tax_liability(
            user_id=request.user_id,
            income=request.income,
            deductions=request.deductions,
            filing_status=request.filing_status,
            tax_year=request.tax_year,
            state=request.state,
        )

    @router.get("/tlh-opportunities", response_model=list[TLHOpportunity])
    async def get_tlh_opportunities(
        user_id: str = Query(..., description="User identifier"),
        min_loss: Decimal = Query(
            Decimal("100.0"), description="Minimum loss amount to consider (default: $100)"
        ),
        tax_rate: Decimal = Query(
            Decimal("0.15"), description="Tax rate for savings calculation (default: 15%)"
        ),
    ):
        """Find tax-loss harvesting opportunities for a user's portfolio.

        Analyzes brokerage positions to identify securities with unrealized losses
        that can be sold to offset capital gains. Suggests replacement securities
        to maintain market exposure without triggering wash sale rules.

        ⚠️ **DISCLAIMER**: Not a substitute for professional tax or financial advice.
        Consult a certified tax professional before executing TLH trades.

        Args:
            user_id: User identifier
            min_loss: Minimum loss amount to consider (default: $100)
            tax_rate: Tax rate for savings calculation (default: 15% capital gains rate)

        Returns:
            List of TLHOpportunity objects sorted by loss amount descending

        Example:
            GET /tax/tlh-opportunities?user_id=user123&min_loss=100&tax_rate=0.15

            Response:
            [
              {
                "position_symbol": "AAPL",
                "position_qty": "100",
                "cost_basis": "15000.00",
                "current_value": "13500.00",
                "loss_amount": "1500.00",
                "loss_percent": "0.10",
                "replacement_ticker": "VGT",
                "wash_sale_risk": "none",
                "potential_tax_savings": "225.00",
                "tax_rate": "0.15",
                "explanation": "AAPL down 10.0% ($1,500.00 loss). Replace with VGT to maintain exposure without wash sale. Estimated $225.00 tax savings @ 15%."
              }
            ]
        """
        # Get brokerage positions for user
        # Production: Use fin_infra.brokerage to fetch actual positions
        # For now, return empty list (integration test will mock this)
        from fin_infra.tax.tlh import find_tlh_opportunities

        # Get brokerage positions for user
        # Production: Integrate with fin_infra.brokerage to fetch actual positions
        # Example:
        #   from fin_infra.brokerage import easy_brokerage
        #   broker = easy_brokerage(mode="paper")
        #   positions = broker.positions()  # Should accept user_id parameter
        # For now, return empty list (integration test will mock this)
        positions: list = []

        # TODO: Get recent trades for wash sale checking
        recent_trades = None

        opportunities = find_tlh_opportunities(
            user_id=user_id,
            positions=positions,
            min_loss=min_loss,
            tax_rate=tax_rate,
            recent_trades=recent_trades,
        )

        return opportunities

    @router.post("/tlh-scenario", response_model=TLHScenario)
    async def simulate_tlh_scenario_endpoint(request: TLHScenarioRequest = Body(...)):
        """Simulate a tax-loss harvesting scenario with multiple opportunities.

        Projects the outcome of executing provided TLH opportunities, including
        total tax savings, portfolio impact, and risk assessment.

        ⚠️ **DISCLAIMER**: Not a substitute for professional tax or financial advice.
        Consult a certified tax professional before executing TLH trades.

        Args:
            request: TLH scenario request with opportunities and optional tax rate override

        Returns:
            TLHScenario with simulation results and recommendations

        Example:
            POST /tax/tlh-scenario
            {
              "opportunities": [
                {
                  "position_symbol": "AAPL",
                  "position_qty": "100",
                  "cost_basis": "15000.00",
                  "current_value": "13500.00",
                  "loss_amount": "1500.00",
                  "loss_percent": "0.10",
                  "replacement_ticker": "VGT",
                  "wash_sale_risk": "none",
                  "potential_tax_savings": "225.00",
                  "tax_rate": "0.15",
                  "explanation": "..."
                }
              ],
              "tax_rate": null
            }

            Response:
            {
              "total_loss_harvested": "1500.00",
              "total_tax_savings": "225.00",
              "num_opportunities": 1,
              "avg_tax_rate": "0.15",
              "wash_sale_risk_summary": {"none": 1, "low": 0, "medium": 0, "high": 0},
              "total_cost_basis": "15000.00",
              "total_current_value": "13500.00",
              "recommendations": [
                "Consider executing TLH trades before year-end to maximize current-year tax benefits",
                "After selling, purchase 1 replacement security(ies) to maintain market exposure while avoiding wash sale",
                "Wait 31 days before repurchasing original securities if desired",
                "Review replacement securities for similar risk/return profile to original positions"
              ],
              "caveats": [
                "Consult a tax professional before executing TLH trades",
                "Wash sale rules apply for 61 days (30 before + 30 after sale)",
                "Replacement securities may have different risk profiles",
                "Tax savings are estimates and depend on your specific tax situation"
              ]
            }
        """
        from fin_infra.tax.tlh import simulate_tlh_scenario

        scenario = simulate_tlh_scenario(
            opportunities=request.opportunities,
            tax_rate=request.tax_rate,
        )

        return scenario

    # Register scoped docs BEFORE mounting router to keep docs public
    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Tax Data",
        auto_exclude_from_root=True,
        visible_envs=None,  # Show in all environments
    )

    # Mount router
    app.include_router(router, include_in_schema=True)

    # Store provider on app state
    app.state.tax_provider = provider

    return provider


__all__ = [
    "add_tax_data",
    "CryptoGainsRequest",
    "TaxLiabilityRequest",
    "TLHScenarioRequest",
]
