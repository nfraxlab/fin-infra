"""
Observability extensions for financial providers.

This module extends svc-infra's observability with financial-specific
route classification. Use the financial_route_classifier with svc-infra's
add_observability to label financial routes automatically.

Example:
    >>> from svc_infra.obs import add_observability
    >>> from fin_infra.obs import financial_route_classifier
    >>>
    >>> # Wire financial route classification with svc-infra
    >>> add_observability(app, route_classifier=financial_route_classifier)
"""

from .classifier import financial_route_classifier

__all__ = [
    "financial_route_classifier",
]
