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
    from ai_infra.llm import CoreLLM
    from svc_infra.cache import get_cache

    llm = CoreLLM()
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

from fin_infra.conversation.planning import (
    FinancialPlanningConversation,
    ConversationResponse,
    ConversationContext,
    Exchange,
    is_sensitive_question,
    SENSITIVE_PATTERNS,
)

__all__ = [
    "FinancialPlanningConversation",
    "ConversationResponse",
    "ConversationContext",
    "Exchange",
    "is_sensitive_question",
    "SENSITIVE_PATTERNS",
]
