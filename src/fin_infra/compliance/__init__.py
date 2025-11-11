"""Compliance tracking and event logging for financial data handling.

This module provides helpers for logging compliance events (PII access, data erasure, etc.)
using svc-infra's structured logging and observability.

Example:
    from fastapi import FastAPI
    from fin_infra.compliance import add_compliance_tracking

    app = FastAPI()
    add_compliance_tracking(app)

    # Events automatically logged:
    # - banking.token_created
    # - banking.data_accessed
    # - credit.report_accessed
    # - erasure.completed
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response

__all__ = ["add_compliance_tracking", "log_compliance_event"]

logger = logging.getLogger(__name__)


def log_compliance_event(
    app: "FastAPI",
    event: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Log a compliance event with structured context.

    Args:
        app: FastAPI application instance
        event: Event name (e.g., "banking.data_accessed")
        context: Additional context (user_id, endpoint, provider, etc.)

    Example:
        >>> log_compliance_event(
        ...     app,
        ...     "banking.token_created",
        ...     {"user_id": "user123", "provider": "plaid"}
        ... )
    """
    ctx = context or {}
    ctx["compliance_event"] = event
    ctx["timestamp"] = datetime.utcnow().isoformat()

    # Log with compliance context as extra field
    logger.info(
        f"Compliance event: {event}",
        extra=ctx,  # Pass directly as extra, not nested
    )


def add_compliance_tracking(
    app: "FastAPI",
    *,
    track_banking: bool = True,
    track_credit: bool = True,
    track_brokerage: bool = True,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> None:
    """Enable compliance event tracking for financial data access.

    This middleware logs compliance events using svc-infra's structured logging.
    Events are logged as JSON with compliance context for audit trails.

    Args:
        app: FastAPI application instance
        track_banking: Track banking endpoint access (default: True)
        track_credit: Track credit endpoint access (default: True)
        track_brokerage: Track brokerage endpoint access (default: True)
        on_event: Optional callback for custom event handling

    Tracked Events:
        - banking.data_accessed: GET /banking/* endpoints
        - credit.report_accessed: GET /credit/* endpoints
        - brokerage.data_accessed: GET /brokerage/* endpoints

    Example:
        >>> from fastapi import FastAPI
        >>> from fin_infra.compliance import add_compliance_tracking
        >>>
        >>> app = FastAPI()
        >>> add_compliance_tracking(app)
        >>>
        >>> # Custom event handler
        >>> def custom_handler(event: str, context: dict):
        ...     print(f"Compliance event: {event}")
        >>>
        >>> add_compliance_tracking(app, on_event=custom_handler)

    Integration:
        Works with svc-infra observability for metrics and alerting:

        >>> from svc_infra.obs import add_observability
        >>> add_observability(app)  # Metrics + logs
        >>> add_compliance_tracking(app)  # Compliance events

    Querying Logs (Grafana Loki example):
        {app="finance-api"} |= "compliance_event" | json | event="banking.data_accessed"
    """

    @app.middleware("http")
    async def compliance_tracking_middleware(request: "Request", call_next: Callable) -> "Response":
        """Middleware to track compliance events for financial endpoints."""
        path = request.url.path
        method = request.method

        # Track only GET requests (data access)
        if method != "GET":
            return await call_next(request)

        # Determine if path is a compliance-tracked endpoint
        event = None
        if track_banking and path.startswith("/banking"):
            event = "banking.data_accessed"
        elif track_credit and path.startswith("/credit"):
            event = "credit.report_accessed"
        elif track_brokerage and path.startswith("/brokerage"):
            event = "brokerage.data_accessed"

        # Execute request
        response = await call_next(request)

        # Log compliance event if applicable (only on successful responses)
        if event and 200 <= response.status_code < 300:
            context = {
                "endpoint": path,
                "method": method,
                "status_code": response.status_code,
                "user_id": getattr(request.state, "user_id", None),
                "ip_address": request.client.host if request.client else None,
            }

            log_compliance_event(app, event, context)

            # Custom callback
            if on_event:
                on_event(event, context)

        return response

    logger.info(
        "Compliance tracking enabled",
        extra={
            "track_banking": track_banking,
            "track_credit": track_credit,
            "track_brokerage": track_brokerage,
        },
    )
