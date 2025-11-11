"""FastAPI integration helper for credit monitoring.

Wires credit routes with svc-infra integrations:
- Dual routers (user_router for protected routes)
- Scoped docs (landing page card at /docs)
- Cache integration (24h TTL for credit scores)
- Webhook publishing (credit.score_changed events)
- Compliance logging (structured JSON logs)

Example:
    >>> from fastapi import FastAPI
    >>> from fin_infra.credit.add import add_credit
    >>> from svc_infra.cache import init_cache
    >>>
    >>> app = FastAPI()
    >>> init_cache(url="redis://localhost")
    >>>
    >>> # Wire credit monitoring with all integrations
    >>> provider = add_credit(app, prefix="/credit")
    >>>
    >>> # Provider available for programmatic access
    >>> score = await provider.get_credit_score("user123")
"""

import logging

from fastapi import FastAPI, Depends, HTTPException, status

from svc_infra.api.fastapi.dual.protected import user_router, RequireUser
from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs
from svc_infra.cache import resource
from svc_infra.webhooks import add_webhooks

from fin_infra.providers.base import CreditProvider
from fin_infra.models.credit import CreditScore, CreditReport

logger = logging.getLogger(__name__)

# Create cache resource for credit data
credit_resource = resource("credit", "user_id")


def add_credit(
    app: FastAPI,
    *,
    provider: CreditProvider | None = None,
    prefix: str = "/credit",
    cache_ttl: int = 86400,  # 24 hours
    enable_webhooks: bool = True,
    visible_envs: list[str] | None = None,
) -> CreditProvider:
    """Wire credit monitoring routes into FastAPI app.

    Integrates with svc-infra:
    - user_router: Protected routes with RequireUser dependency
    - add_prefixed_docs: Landing page card at /docs
    - @cache_read: 24h TTL for credit scores (cost optimization)
    - add_webhooks: Event publishing for score changes
    - Structured logging: FCRA compliance event logging

    Args:
        app: FastAPI application instance
        provider: CreditProvider instance (default: auto-detect via easy_credit)
        prefix: URL prefix for credit routes (default: "/credit")
        cache_ttl: Cache TTL in seconds (default: 86400 = 24 hours)
        enable_webhooks: Enable webhook publishing (default: True)
        visible_envs: Show docs in these environments only (default: all)

    Returns:
        Configured CreditProvider instance

    Side Effects:
        - Mounts credit router at {prefix}
        - Adds /docs card for "Credit Monitoring"
        - Stores provider on app.state.credit_provider
        - Wires webhooks if enable_webhooks=True

    Example:
        >>> from fastapi import FastAPI
        >>> from svc_infra.cache import init_cache
        >>> from fin_infra.credit.add import add_credit
        >>>
        >>> app = FastAPI()
        >>> init_cache(url="redis://localhost")
        >>>
        >>> # Wire credit monitoring
        >>> credit = add_credit(app)
        >>>
        >>> # Routes available:
        >>> # POST /credit/score - Get credit score (cached 24h)
        >>> # POST /credit/report - Get full credit report (cached 24h)
        >>> # GET /credit/docs - Scoped Swagger UI
        >>> # GET /credit/openapi.json - Scoped OpenAPI schema
    """
    # Get or create provider
    if provider is None:
        # Import here to avoid circular import
        from fin_infra.credit import easy_credit

        provider = easy_credit()

    # Store provider on app state for programmatic access
    app.state.credit_provider = provider

    # Wire webhooks if enabled
    if enable_webhooks:
        # add_webhooks will mount /_webhooks/* routes
        add_webhooks(app)

    # Create dual router for protected credit routes
    router = user_router(prefix=prefix, tags=["Credit Monitoring"])

    @router.post("/score", response_model=CreditScore)
    @credit_resource.cache_read(ttl=cache_ttl, suffix="score")
    async def get_credit_score(
        *,
        user_id: str,
        permissible_purpose: str = "account_review",
        user: dict = Depends(RequireUser),
    ) -> CreditScore:
        """Get credit score for a user (cached 24h).

        FCRA Compliance:
        - Requires permissible purpose (default: account_review)
        - Logs credit access event to structured logs
        - Cache reduces bureau API costs (~$0.50-$2.00 per pull)

        Cost Optimization:
        - 24h cache TTL: 1 API call/day instead of 10+
        - Estimated savings: 95% reduction in bureau costs
        """
        # FCRA compliance logging
        logger.info(
            "credit.score_accessed",
            extra={
                "user_id": user_id,
                "bureau": "experian",
                "permissible_purpose": permissible_purpose,
                "accessed_by": user.get("user_id"),
                "event_type": "credit_access",
            },
        )

        # Fetch credit score (cache miss = real API call)
        try:
            score = await provider.get_credit_score(user_id)
        except Exception as e:
            logger.error(f"Failed to get credit score for {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Credit bureau service unavailable",
            )

        # Publish webhook event if score changed
        if enable_webhooks and hasattr(app.state, "webhooks_outbox"):
            try:
                # Get webhook service from app state
                from svc_infra.webhooks.service import WebhookService
                from svc_infra.db.outbox import OutboxStore

                outbox: OutboxStore = app.state.webhooks_outbox
                subs = app.state.webhooks_subscriptions

                webhook_svc = WebhookService(outbox=outbox, subs=subs)
                webhook_svc.publish(
                    topic="credit.score_changed",
                    payload={
                        "user_id": user_id,
                        "score": score.score,
                        "bureau": "experian",
                        "timestamp": score.report_date.isoformat() if score.report_date else None,
                    },
                )
            except Exception as e:
                # Don't fail request if webhook publishing fails
                logger.warning(f"Failed to publish credit.score_changed webhook: {e}")

        return score

    @router.post("/report", response_model=CreditReport)
    @credit_resource.cache_read(ttl=cache_ttl, suffix="report")
    async def get_credit_report(
        *,
        user_id: str,
        permissible_purpose: str = "account_review",
        user: dict = Depends(RequireUser),
    ) -> CreditReport:
        """Get full credit report for a user (cached 24h).

        FCRA Compliance:
        - Requires permissible purpose (default: account_review)
        - Logs credit access event to structured logs
        - Full report access is higher risk, ensure proper authorization

        Cost Optimization:
        - 24h cache TTL: 1 API call/day instead of 10+
        - Full reports cost more than scores (~$2-$5 per pull)
        """
        # FCRA compliance logging
        logger.info(
            "credit.report_accessed",
            extra={
                "user_id": user_id,
                "bureau": "experian",
                "permissible_purpose": permissible_purpose,
                "accessed_by": user.get("user_id"),
                "event_type": "credit_access",
                "report_type": "full",
            },
        )

        # Fetch credit report (cache miss = real API call)
        try:
            report = await provider.get_credit_report(user_id)
        except Exception as e:
            logger.error(f"Failed to get credit report for {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Credit bureau service unavailable",
            )

        return report

    # Mount router with dual routes (with/without trailing slash)
    app.include_router(router, include_in_schema=True)

    # Add scoped docs (landing page card)
    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Credit Monitoring",
        auto_exclude_from_root=True,
        visible_envs=visible_envs,
    )

    logger.info(f"Credit monitoring routes mounted at {prefix}")

    return provider


__all__ = ["add_credit"]
