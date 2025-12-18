"""Data normalization module for financial symbols and currencies."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

from fin_infra.normalization.currency_converter import (
    CurrencyConverter,
    CurrencyNotSupportedError,
)
from fin_infra.normalization.models import (
    CurrencyConversionResult,
    ExchangeRate,
    SymbolMetadata,
)
from fin_infra.normalization.symbol_resolver import (
    SymbolNotFoundError,
    SymbolResolver,
)

__all__ = [
    "SymbolResolver",
    "CurrencyConverter",
    "easy_normalization",
    "add_normalization",
    "SymbolMetadata",
    "ExchangeRate",
    "CurrencyConversionResult",
    "SymbolNotFoundError",
    "CurrencyNotSupportedError",
]


# Singleton instances (initialized lazily)
_resolver_instance: SymbolResolver | None = None
_converter_instance: CurrencyConverter | None = None


def easy_normalization(
    api_key: str | None = None,
) -> tuple[SymbolResolver, CurrencyConverter]:
    """
    Get configured symbol resolver and currency converter (one-liner setup).

    Returns singleton instances on subsequent calls for efficiency.

    Args:
        api_key: Optional API key for exchangerate-api.io (paid tier)

    Returns:
        Tuple of (SymbolResolver, CurrencyConverter)

    Example:
        >>> from fin_infra.normalization import easy_normalization
        >>> resolver, converter = easy_normalization()
        >>> ticker = await resolver.to_ticker("037833100")  # CUSIP → AAPL
        >>> eur = await converter.convert(100, "USD", "EUR")  # 92.0
    """
    global _resolver_instance, _converter_instance

    if _resolver_instance is None:
        _resolver_instance = SymbolResolver()

    if _converter_instance is None:
        _converter_instance = CurrencyConverter(api_key=api_key)

    return _resolver_instance, _converter_instance


def add_normalization(
    app: "FastAPI",
    *,
    prefix: str = "/normalize",
    api_key: str | None = None,
) -> tuple[SymbolResolver, CurrencyConverter]:
    """
    Wire normalization services (symbol resolution & currency conversion) to FastAPI app.

    Mounts REST endpoints for symbol normalization and currency conversion with
    svc-infra dual routers for consistent behavior.

    Mounted Routes:
        GET {prefix}/symbol/{identifier}
            Resolve any symbol identifier (ticker, CUSIP, ISIN, FIGI, etc.) to ticker
            Path: identifier - Symbol to resolve
            Response: {"ticker": "AAPL", "type": "ticker", "metadata": {...}}

        GET {prefix}/convert
            Convert amount between currencies using real-time exchange rates
            Query: amount (float), from_currency (str), to_currency (str)
            Response: {"amount": 100.0, "from": "USD", "to": "EUR", "result": 92.0, "rate": 0.92}

    Args:
        app: FastAPI application instance
        prefix: URL prefix for normalization routes (default: "/normalize")
        api_key: Optional API key for exchangerate-api.io (paid tier for more requests)

    Returns:
        Tuple of (SymbolResolver, CurrencyConverter) instances

    Examples:
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.normalization import add_normalization
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> resolver, converter = add_normalization(app)
        >>>
        >>> # Routes available:
        >>> # GET /normalize/symbol/037833100 → {"ticker": "AAPL", ...}
        >>> # GET /normalize/convert?amount=100&from_currency=USD&to_currency=EUR

    Integration with svc-infra:
        - Uses public_router (no auth required - utility endpoints)
        - Integrated with svc-infra observability (request metrics)
        - Scoped docs at {prefix}/docs for standalone documentation
    """
    # Import FastAPI dependencies
    from fastapi import HTTPException, Query
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs

    # Import svc-infra public router (no auth - utility endpoints)
    from svc_infra.api.fastapi.dual.public import public_router

    # Get normalization services
    resolver, converter = easy_normalization(api_key=api_key)

    # Create router
    router = public_router(prefix=prefix, tags=["Normalization"])

    @router.get("/symbol/{identifier}")
    async def resolve_symbol(identifier: str):
        """Resolve any symbol identifier to ticker."""
        try:
            ticker = await resolver.to_ticker(identifier)
            metadata = await resolver.get_metadata(ticker)
            return {
                "ticker": ticker,
                "identifier": identifier,
                "metadata": metadata.model_dump() if metadata else None,
            }
        except SymbolNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.get("/convert")
    async def convert_currency(
        amount: float = Query(..., description="Amount to convert"),
        from_currency: str = Query(
            ..., alias="from", description="Source currency code (e.g., USD)"
        ),
        to_currency: str = Query(..., alias="to", description="Target currency code (e.g., EUR)"),
    ):
        """Convert amount between currencies."""
        try:
            result = await converter.convert_with_details(amount, from_currency, to_currency)
            return {
                "amount": result.amount,
                "from_currency": result.from_currency,
                "to_currency": result.to_currency,
                "result": result.converted,
                "rate": result.rate,
                "timestamp": result.date.isoformat() if result.date else None,
            }
        except CurrencyNotSupportedError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Register scoped docs BEFORE mounting router
    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Normalization",
        auto_exclude_from_root=True,
        visible_envs=None,
    )

    # Mount router
    app.include_router(router, include_in_schema=True)

    # Store on app state
    app.state.symbol_resolver = resolver
    app.state.currency_converter = converter

    return resolver, converter
