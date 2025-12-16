"""
Easy builder for financial planning conversation (Section 17 V2).

Simplifies LLM-powered multi-turn Q&A for financial planning.

Example:
    from fin_infra.conversation.ease import easy_financial_conversation

    # Minimal setup (Google Gemini default)
    conversation = easy_financial_conversation()

    # Custom provider
    conversation = easy_financial_conversation(provider="openai")

    # Custom LLM instance
    from ai_infra.llm import LLM
    llm = LLM(temperature=0.3)
    conversation = easy_financial_conversation(llm=llm)
"""

from typing import Any

from fin_infra.chat.planning import FinancialPlanningConversation


def easy_financial_conversation(
    llm: Any | None = None,
    cache: Any | None = None,
    provider: str = "google",
    model_name: str | None = None,
) -> FinancialPlanningConversation:
    """
    Easy builder for financial planning conversation.

    One-call setup with sensible defaults:
    - LLM: ai-infra LLM (Google Gemini default)
    - Cache: svc-infra cache (24h TTL)
    - Provider: Google (cheapest, $0.018/user/month)

    Args:
        llm: Optional ai-infra LLM instance (auto-created if None)
        cache: Optional svc-infra cache instance (auto-created if None)
        provider: LLM provider ("google", "openai", "anthropic")
        model_name: Optional model name override (uses provider defaults)

    Returns:
        FinancialPlanningConversation instance

    Cost: ~$0.018/user/month (2 conversations × 10 turns with cache)

    Examples:
        # Minimal setup (Google Gemini)
        conversation = easy_financial_conversation()

        response = await conversation.ask(
            user_id="user_123",
            question="How can I save more?",
            current_net_worth=575000.0
        )

        # Custom provider (OpenAI)
        conversation = easy_financial_conversation(provider="openai")

        # Custom LLM instance
        from ai_infra.llm import LLM
        llm = LLM(temperature=0.3)
        conversation = easy_financial_conversation(llm=llm)
    """
    # Auto-create LLM if not provided
    if llm is None:
        try:
            from ai_infra.llm import LLM

            llm = LLM()
        except ImportError:
            raise ImportError("ai-infra not installed. Install with: pip install ai-infra")

    # Auto-create cache if not provided
    if cache is None:
        try:
            from svc_infra.cache import get_cache

            cache = get_cache()
        except ImportError:
            raise ImportError(
                "svc-infra cache not configured. Initialize with: "
                "from svc_infra.cache import init_cache; init_cache(...)"
            )

    # Provider defaults
    default_models = {
        "google": "gemini-2.0-flash-exp",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-20241022",
    }

    if model_name is None:
        model_name = default_models.get(provider, "gemini-2.0-flash-exp")

    return FinancialPlanningConversation(
        llm=llm,
        cache=cache,
        provider=provider,
        model_name=model_name,
    )
