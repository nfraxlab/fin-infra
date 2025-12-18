"""
Financial cashflow calculations (NPV, IRR, loan amortization).

This module provides financial calculation functions commonly used in
investment analysis, loan calculations, and retirement planning.

Functions:
    - npv(): Net Present Value
    - irr(): Internal Rate of Return
    - pmt(): Loan payment calculation (from numpy-financial)
    - fv(): Future Value
    - pv(): Present Value

Example usage:
    from fin_infra.cashflows import npv, irr

    # Calculate NPV
    cashflows = [-10000, 3000, 4000, 5000]
    net_value = npv(0.08, cashflows)  # 8% discount rate

    # Calculate IRR
    rate = irr(cashflows)
"""

from typing import TYPE_CHECKING

import numpy_financial as npf

if TYPE_CHECKING:
    from fastapi import FastAPI

from .core import irr, npv

__all__ = ["npv", "irr", "pmt", "fv", "pv", "add_cashflows"]


def pmt(rate: float, nper: int, pv: float, fv: float = 0, when: str = "end") -> float:
    """
    Calculate loan payment amount.

    Args:
        rate: Interest rate per period (e.g., 0.05 for 5%)
        nper: Number of payment periods
        pv: Present value (loan amount)
        fv: Future value (default: 0)
        when: When payments are due ("end" or "begin")

    Returns:
        Payment amount per period (negative value indicates outflow)

    Example:
        >>> # $200,000 mortgage, 30 years, 5% annual interest
        >>> monthly_rate = 0.05 / 12
        >>> months = 30 * 12
        >>> payment = pmt(monthly_rate, months, 200000)
        >>> print(f"Monthly payment: ${-payment:.2f}")
        Monthly payment: $1073.64
    """
    when_val = 1 if when == "begin" else 0
    return float(npf.pmt(rate, nper, pv, fv, when_val))


def fv(rate: float, nper: int, pmt: float, pv: float = 0, when: str = "end") -> float:
    """
    Calculate future value of an investment.

    Args:
        rate: Interest rate per period
        nper: Number of payment periods
        pmt: Payment amount per period
        pv: Present value (initial investment)
        when: When payments are due ("end" or "begin")

    Returns:
        Future value

    Example:
        >>> # Save $500/month for 10 years at 7% annual return
        >>> monthly_rate = 0.07 / 12
        >>> months = 10 * 12
        >>> future = fv(monthly_rate, months, -500)
        >>> print(f"Future value: ${future:.2f}")
        Future value: $86920.42
    """
    when_val = 1 if when == "begin" else 0
    return float(npf.fv(rate, nper, pmt, pv, when_val))


def pv(rate: float, nper: int, pmt: float, fv: float = 0, when: str = "end") -> float:
    """
    Calculate present value of an investment.

    Args:
        rate: Interest rate per period
        nper: Number of payment periods
        pmt: Payment amount per period
        fv: Future value
        when: When payments are due ("end" or "begin")

    Returns:
        Present value

    Example:
        >>> # What's the value today of $100k in 20 years at 6% return?
        >>> annual_rate = 0.06
        >>> years = 20
        >>> present = pv(annual_rate, years, 0, 100000)
        >>> print(f"Present value: ${-present:.2f}")
        Present value: $31180.47
    """
    when_val = 1 if when == "begin" else 0
    return float(npf.pv(rate, nper, pmt, fv, when_val))


def add_cashflows(
    app: "FastAPI",
    *,
    prefix: str = "/cashflows",
) -> None:
    """
    Wire cashflow calculation endpoints to FastAPI app.

    Mounts REST endpoints for financial calculations (NPV, IRR, PMT, FV, PV)
    with svc-infra dual routers for consistent behavior.

    Mounted Routes:
        POST {prefix}/npv
            Calculate Net Present Value
            Request: {"rate": 0.08, "cashflows": [-10000, 3000, 4000, 5000]}
            Response: {"npv": 1234.56}

        POST {prefix}/irr
            Calculate Internal Rate of Return
            Request: {"cashflows": [-10000, 3000, 4000, 5000]}
            Response: {"irr": 0.123}

        POST {prefix}/pmt
            Calculate loan payment
            Request: {"rate": 0.004167, "nper": 360, "pv": 200000}
            Response: {"pmt": -1073.64}

        POST {prefix}/fv
            Calculate future value
            Request: {"rate": 0.005833, "nper": 120, "pmt": -500}
            Response: {"fv": 86920.42}

        POST {prefix}/pv
            Calculate present value
            Request: {"rate": 0.06, "nper": 20, "fv": 100000}
            Response: {"pv": -31180.47}

    Args:
        app: FastAPI application instance
        prefix: URL prefix for cashflow routes (default: "/cashflows")

    Examples:
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.cashflows import add_cashflows
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> add_cashflows(app)
        >>>
        >>> # Routes available:
        >>> # POST /cashflows/npv
        >>> # POST /cashflows/irr
        >>> # POST /cashflows/pmt
        >>> # POST /cashflows/fv
        >>> # POST /cashflows/pv

    Integration with svc-infra:
        - Uses public_router (no auth required - utility calculations)
        - Integrated with svc-infra observability
        - Scoped docs at {prefix}/docs
    """
    from pydantic import BaseModel, Field
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs

    # Import svc-infra public router (no auth - utility calculations)
    from svc_infra.api.fastapi.dual.public import public_router

    # Request/Response models
    class NPVRequest(BaseModel):
        rate: float = Field(..., description="Discount rate (e.g., 0.08 for 8%)")
        cashflows: list[float] = Field(..., description="Cashflow amounts by period")

    class IRRRequest(BaseModel):
        cashflows: list[float] = Field(..., description="Cashflow amounts by period")

    class PMTRequest(BaseModel):
        rate: float = Field(..., description="Interest rate per period")
        nper: int = Field(..., description="Number of payment periods")
        pv: float = Field(..., description="Present value (loan amount)")
        fv: float = Field(0, description="Future value")
        when: str = Field("end", description="When payments are due: 'end' or 'begin'")

    class FVRequest(BaseModel):
        rate: float = Field(..., description="Interest rate per period")
        nper: int = Field(..., description="Number of payment periods")
        pmt: float = Field(..., description="Payment amount per period")
        pv: float = Field(0, description="Present value")
        when: str = Field("end", description="When payments are due: 'end' or 'begin'")

    class PVRequest(BaseModel):
        rate: float = Field(..., description="Interest rate per period")
        nper: int = Field(..., description="Number of payment periods")
        pmt: float = Field(..., description="Payment amount per period")
        fv: float = Field(0, description="Future value")
        when: str = Field("end", description="When payments are due: 'end' or 'begin'")

    # Create router
    router = public_router(prefix=prefix, tags=["Cashflows"])

    @router.post("/npv")
    async def calculate_npv(request: NPVRequest):
        """Calculate Net Present Value."""
        result = npv(request.rate, request.cashflows)
        return {"npv": result}

    @router.post("/irr")
    async def calculate_irr(request: IRRRequest):
        """Calculate Internal Rate of Return."""
        result = irr(request.cashflows)
        return {"irr": result}

    @router.post("/pmt")
    async def calculate_pmt(request: PMTRequest):
        """Calculate loan payment."""
        result = pmt(request.rate, request.nper, request.pv, request.fv, request.when)
        return {"pmt": result}

    @router.post("/fv")
    async def calculate_fv(request: FVRequest):
        """Calculate future value."""
        result = fv(request.rate, request.nper, request.pmt, request.pv, request.when)
        return {"fv": result}

    @router.post("/pv")
    async def calculate_pv(request: PVRequest):
        """Calculate present value."""
        result = pv(request.rate, request.nper, request.pmt, request.fv, request.when)
        return {"pv": result}

    # Register scoped docs BEFORE mounting router
    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Cashflow Calculations",
        auto_exclude_from_root=True,
        visible_envs=None,
    )

    # Mount router
    app.include_router(router, include_in_schema=True)

    print("Cashflow calculations enabled (NPV, IRR, PMT, FV, PV)")
