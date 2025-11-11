"""
Route classifier for financial API endpoints.

This module provides a route classifier that works with svc-infra's
add_observability to automatically label financial routes in metrics.

The classifier uses prefix patterns to detect financial routes without
hardcoding specific endpoints, making it extensible as new providers
and capabilities are added.

Design Principles:
- No hardcoded endpoint paths - uses prefix patterns
- Extensible - adding new financial capability prefixes is trivial
- Compatible with svc-infra's RouteClassifier protocol
- Supports multi-level classification (financial, public, internal, admin)

Usage:
    >>> from svc_infra.obs import add_observability
    >>> from fin_infra.obs import financial_route_classifier
    >>>
    >>> # Automatic financial route classification
    >>> add_observability(app, route_classifier=financial_route_classifier)
    >>>
    >>> # Or compose with custom classifier
    >>> def my_classifier(route_path: str, method: str) -> str:
    ...     # Try financial classification first
    ...     cls = financial_route_classifier(route_path, method)
    ...     if cls != "public":
    ...         return cls
    ...     # Custom logic for other routes
    ...     if route_path.startswith("/admin"):
    ...         return "admin"
    ...     return "public"
    >>>
    >>> add_observability(app, route_classifier=my_classifier)
"""

from __future__ import annotations

# Financial capability prefix patterns (extensible)
FINANCIAL_ROUTE_PREFIXES = (
    "/banking",
    "/market",
    "/crypto",
    "/brokerage",
    "/credit",
    "/tax",
    "/cashflow",
    "/transaction",
    "/portfolio",
    "/wallet",
)


def financial_route_classifier(route_path: str, method: str) -> str:
    """
    Classify routes by financial domain without hardcoding specific endpoints.

    This classifier detects financial routes by prefix patterns and returns
    appropriate labels for metrics segmentation. It's designed to work with
    svc-infra's add_observability route_classifier parameter.

    Classification Logic:
    - Financial routes (e.g., /banking/*, /market/*) → "financial"
    - All other routes → "public"

    This allows Grafana dashboards to split metrics by route class:
    - Filter by route_class="financial" for financial provider SLOs
    - Filter by route_class="public" for general API endpoints

    Args:
        route_path: The route template path (e.g., "/banking/accounts/{id}")
        method: HTTP method (e.g., "GET", "POST")

    Returns:
        Route class label: "financial" or "public"

    Examples:
        >>> financial_route_classifier("/banking/accounts", "GET")
        'financial'
        >>> financial_route_classifier("/market/quote/{symbol}", "GET")
        'financial'
        >>> financial_route_classifier("/health", "GET")
        'public'
        >>> financial_route_classifier("/docs", "GET")
        'public'

    Note:
        If you need additional route classes (e.g., "admin", "internal"),
        compose this classifier with your own:

        >>> def my_classifier(path: str, method: str) -> str:
        ...     cls = financial_route_classifier(path, method)
        ...     if cls != "public":
        ...         return cls
        ...     if path.startswith("/admin"):
        ...         return "admin"
        ...     return "public"
    """
    # Normalize path for prefix matching (remove trailing slash)
    normalized = route_path.rstrip("/") or "/"

    # Check if route matches any financial prefix pattern
    for prefix in FINANCIAL_ROUTE_PREFIXES:
        if normalized.startswith(prefix):
            return "financial"

    # Default classification for non-financial routes
    return "public"


def compose_classifiers(
    *classifiers: callable,
    default: str = "public",
) -> callable:
    """
    Compose multiple route classifiers with fallback logic.

    This helper allows you to chain multiple classifiers and use the
    first non-default classification returned.

    Args:
        *classifiers: Route classifier functions to try in order
        default: Default classification to skip when chaining

    Returns:
        Composed classifier function

    Example:
        >>> from fin_infra.obs import financial_route_classifier, compose_classifiers
        >>>
        >>> def admin_classifier(path: str, method: str) -> str:
        ...     if path.startswith("/admin"):
        ...         return "admin"
        ...     return "public"
        >>>
        >>> # Try financial first, then admin, then default to public
        >>> classifier = compose_classifiers(
        ...     financial_route_classifier,
        ...     admin_classifier,
        ...     default="public"
        ... )
        >>>
        >>> add_observability(app, route_classifier=classifier)
    """

    def composed(route_path: str, method: str) -> str:
        for classifier in classifiers:
            cls = classifier(route_path, method)
            if cls != default:
                return cls
        return default

    return composed
