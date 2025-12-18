"""
General-purpose financial planning conversation with LLM.

This is a ROOT-LEVEL capability (cross-domain primitive, like svc-infra cache/api).
NOT tied to net worth specifically - works across ALL fin-infra domains:
- Net worth tracking
- Budgeting (future)
- Spending analysis (future)
- Debt management (future)

Example:
    from fin_infra.conversation import FinancialPlanningConversation
    from ai_infra.llm import LLM
    from svc_infra.cache import get_cache

    llm = LLM()
    cache = get_cache()
    conversation = FinancialPlanningConversation(
        llm=llm,
        cache=cache,
        provider="google"
    )

    response = await conversation.ask(
        user_id="user_123",
        question="How can I save more money each month?",
        current_net_worth=575000.0
    )
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

from fin_infra.chat.ease import easy_financial_conversation
from fin_infra.chat.planning import (
    SENSITIVE_PATTERNS,
    ConversationContext,
    ConversationResponse,
    Exchange,
    FinancialPlanningConversation,
    is_sensitive_question,
)

__all__ = [
    "FinancialPlanningConversation",
    "ConversationResponse",
    "ConversationContext",
    "Exchange",
    "is_sensitive_question",
    "SENSITIVE_PATTERNS",
    "easy_financial_conversation",
    "add_financial_conversation",
]


def add_financial_conversation(
    app: "FastAPI",
    *,
    prefix: str = "/chat",
    conversation: FinancialPlanningConversation | None = None,
    provider: str = "google",
) -> FinancialPlanningConversation:
    """
    Wire AI-powered financial planning conversation to FastAPI app.

    Mounts REST endpoints for multi-turn financial Q&A with LLM integration
    (powered by ai-infra) and user authentication via svc-infra dual routers.

    Mounted Routes:
        POST {prefix}/ask
            Ask a financial planning question
            Request: {"question": str, "net_worth": float?, "context": dict?}
            Response: ConversationResponse with answer and follow-ups

        GET {prefix}/history
            Get conversation history for current user
            Response: List of past exchanges

        DELETE {prefix}/history
            Clear conversation history for current user
            Response: {"success": true}

    Args:
        app: FastAPI application instance
        prefix: URL prefix for chat routes (default: "/chat")
        conversation: Optional FinancialPlanningConversation instance
                     (auto-created with easy_financial_conversation if None)
        provider: LLM provider if auto-creating ("google", "openai", "anthropic")

    Returns:
        Configured FinancialPlanningConversation instance

    Examples:
        >>> from svc_infra.api.fastapi.ease import easy_service_app
        >>> from fin_infra.chat import add_financial_conversation
        >>>
        >>> app = easy_service_app(name="FinanceAPI")
        >>> conversation = add_financial_conversation(app)
        >>>
        >>> # Routes available:
        >>> # POST /chat/ask
        >>> # GET /chat/history
        >>> # DELETE /chat/history

    Integration:
        - Uses user_router (requires authentication)
        - Powered by ai-infra LLM (multi-provider support)
        - Uses svc-infra cache for conversation history (24h TTL)
        - Cost: ~$0.018/user/month with Google Gemini

    Safety:
        - Filters sensitive questions (SSN, passwords, account numbers)
        - Includes financial advice disclaimer in all responses
        - Logs all LLM calls for compliance (via svc-infra logging)
    """
    from pydantic import BaseModel, Field
    from svc_infra.api.fastapi.docs.scoped import add_prefixed_docs

    # Import svc-infra user router (requires auth)
    from svc_infra.api.fastapi.dual.protected import user_router

    # Auto-create conversation if not provided
    if conversation is None:
        conversation = easy_financial_conversation(provider=provider)

    # Request/Response models
    class AskRequest(BaseModel):
        question: str = Field(..., description="Financial planning question")
        net_worth: float | None = Field(None, description="Current net worth")
        context: dict[str, Any] | None = Field(None, description="Additional context")

    # Create router
    router = user_router(prefix=prefix, tags=["Financial Chat"])

    @router.post("/ask")
    async def ask_question(request: AskRequest) -> ConversationResponse:
        """
        Ask a financial planning question.

        The LLM provides personalized advice based on:
        - Your question and conversation history
        - Net worth and financial context
        - Best practices and strategies

        Safety: Filters sensitive questions (SSN, passwords, account numbers).
        """
        # TODO: Get user_id from svc-infra auth context
        user_id = "demo_user"  # Placeholder

        # Ask conversation
        response = await conversation.ask(
            user_id=user_id,
            question=request.question,
            current_net_worth=request.net_worth,
            **(request.context or {}),
        )
        return response

    @router.get("/history")
    async def get_history() -> list[Exchange]:
        """Get conversation history for current user."""
        # TODO: Get user_id from svc-infra auth context
        user_id = "demo_user"
        context = await conversation._get_context(user_id)
        return context.previous_exchanges if context else []

    @router.delete("/history")
    async def clear_history():
        """Clear conversation history for current user."""
        # TODO: Get user_id from svc-infra auth context
        user_id = "demo_user"
        await conversation._clear_context(user_id)
        return {"success": True}

    # Register scoped docs BEFORE mounting router
    add_prefixed_docs(
        app,
        prefix=prefix,
        title="Financial Chat",
        auto_exclude_from_root=True,
        visible_envs=None,
    )

    # Mount router
    app.include_router(router, include_in_schema=True)

    # Store on app.state for programmatic access
    app.state.financial_conversation = conversation

    print(f"Financial chat enabled (AI-powered Q&A with {provider})")

    return conversation
