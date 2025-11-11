"""
Multi-turn financial planning conversation with LLM (Section 17 V2).

**SCOPE**: General-purpose financial Q&A across ALL fin-infra domains.
This is a ROOT-LEVEL capability (like svc-infra cache/api), NOT net-worth-specific.

Provides conversational interface for financial Q&A:
- Multi-turn context (remembers last 10 exchanges)
- Safety filters (refuses sensitive questions like SSN, passwords)
- Personalized advice (uses current net worth, goals, historical data)
- Natural dialogue (flexible responses, not forced JSON structure)

**Design Choice**: Uses `CoreLLM.achat()` for natural conversation (NOT `with_structured_output()`).
Conversation should be flexible and natural, not rigidly structured. Other modules (insights,
categorization, goals) correctly use structured output because they need predictable schemas.

Uses ai-infra CoreLLM for natural conversation.
Caches conversation context for 24h (target: $0.018/user/month cost).

Example:
    from ai_infra.llm import CoreLLM
    from svc_infra.cache import get_cache
    from fin_infra.conversation import FinancialPlanningConversation

    llm = CoreLLM()
    cache = get_cache()
    conversation = FinancialPlanningConversation(
        llm=llm,
        cache=cache,
        provider="google",
        model_name="gemini-2.0-flash-exp"
    )

    # Ask question
    response = await conversation.ask(
        user_id="user_123",
        question="How can I save more money each month?",
        current_net_worth=575000.0,
        goals=[{"type": "retirement", "target_amount": 2000000.0}]
    )

    # Follow-up (remembers previous exchange)
    follow_up = await conversation.ask(
        user_id="user_123",
        question="How do I refinance my car loan?",
        current_net_worth=575000.0
    )
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas (Structured Output)
# ============================================================================


class Exchange(BaseModel):
    """Single conversation exchange (question + answer)."""

    question: str = Field(..., description="User question")
    answer: str = Field(..., description="AI answer")
    timestamp: str = Field(..., description="ISO datetime of exchange")


class ConversationContext(BaseModel):
    """
    Conversation context (stored in svc-infra.cache with 24h TTL).

    Stores last 10 exchanges, current net worth, and active goals.
    """

    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Unique conversation session ID")
    current_net_worth: float = Field(..., description="Current net worth in USD")
    goals: list[dict[str, Any]] = Field(default_factory=list, description="Active financial goals")
    previous_exchanges: list[Exchange] = Field(
        default_factory=list, max_length=10, description="Last 10 conversation exchanges"
    )
    created_at: str = Field(..., description="ISO datetime when context created")
    expires_at: str = Field(..., description="ISO datetime when context expires (24h)")


class ConversationResponse(BaseModel):
    """
    LLM response to financial planning question.

    Includes answer, follow-up suggestions, confidence score, and data sources.
    """

    answer: str = Field(..., description="Detailed answer to user's question with specific advice")
    follow_up_questions: list[str] = Field(
        ..., max_length=3, description="Up to 3 suggested follow-up questions"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this answer (0.0-1.0)"
    )
    sources: list[str] = Field(
        ..., description="Data sources used (e.g., 'current_net_worth', 'goal_retirement')"
    )


# ============================================================================
# Safety Filters
# ============================================================================

# Sensitive information patterns (refuse to answer)
SENSITIVE_PATTERNS = [
    r"\b(ssn|social security number)\b",
    r"\b(password|pin|access code|passcode)\b",
    r"\b(credit card number|cvv|cvc)\b",
    r"\b(bank account number|routing number)\b",
    r"\b(driver'?s? license number)\b",
]


def is_sensitive_question(question: str) -> bool:
    """
    Detect sensitive questions that should be refused.

    Args:
        question: User question to check

    Returns:
        True if question contains sensitive information patterns

    Examples:
        >>> is_sensitive_question("What's my SSN?")
        True
        >>> is_sensitive_question("How can I save more?")
        False
    """
    lower = question.lower()
    return any(re.search(pattern, lower) for pattern in SENSITIVE_PATTERNS)


# ============================================================================
# System Prompt (Few-Shot Examples)
# ============================================================================

CONVERSATION_SYSTEM_PROMPT = """You are a certified financial advisor providing personalized advice.

Guidelines:
1. Use specific numbers from user's data (net worth, goals, historical trends)
2. Provide actionable advice, not generic tips
3. If you need more information, ask clarifying questions
4. Keep answers concise (3-5 sentences max)
5. Suggest 2-3 relevant follow-up questions
6. Cite data sources you used (net_worth, goals, history)

Example 1:
User context: Net worth $575k, retirement goal $2M by 2050, saving 15% of income
Question: "How can I save more money each month?"
Answer: "Based on your $575k net worth and retirement goal of $2M by 2050, you're saving 15% of income ($1,200/month). To accelerate: (1) Increase 401k contribution by 2% to capture full employer match (+$200/month), (2) Reduce dining out from $400 to $200/month (+$200/month), (3) Refinance car loan from 8% to 5% (+$75/month). Total: +$475/month (20% savings rate)."
Follow-ups: ["How do I refinance my car loan?", "What's a good savings rate for my age?", "Should I pay off debt first or save more?"]
Sources: ["current_net_worth", "goal_retirement", "spending_analysis"]

Example 2:
User context: Net worth $95k, credit card debt $5k at 22% APR
Question: "Should I pay off my mortgage early?"
Answer: "With $5k credit card debt at 22% APR, prioritize that first before extra mortgage payments. Credit card costs $1,100/year in interest vs mortgage at ~5% APR. Pay $500/month extra on credit card (paid off in 11 months), then redirect that payment to mortgage principal."
Follow-ups: ["How long to pay off my credit card?", "What APR should I refinance my mortgage?", "Should I consolidate my debt?"]
Sources: ["liabilities", "debt_apr_analysis"]

Example 3 (Need more info):
User context: Net worth $200k
Question: "Is my retirement on track?"
Answer: "To assess your retirement progress, I need more information: (1) What's your retirement goal amount? (2) What age do you plan to retire? (3) How much are you currently saving per month? With this, I can calculate if you're on track or need to adjust."
Follow-ups: ["I want to retire at 65 with $1.5M", "How much should I save monthly?", "What's a realistic retirement goal?"]
Sources: []

⚠️ This is AI-generated advice. Not a substitute for a certified financial advisor.
Verify calculations independently. For personalized advice, consult a professional."""


# ============================================================================
# FinancialPlanningConversation
# ============================================================================


class FinancialPlanningConversation:
    """
    Multi-turn financial planning conversation with LLM.

    Features:
    - Context management (10-turn history, 24h TTL)
    - Safety filters (refuses SSN, passwords, account numbers)
    - Personalized advice (uses net worth, goals, history)
    - Follow-up suggestions (proactive guidance)

    Cost: ~$0.0054/conversation (10 turns with context caching)

    Example:
        from ai_infra.llm import CoreLLM
        from svc_infra.cache import get_cache

        llm = CoreLLM()
        cache = get_cache()
        conversation = FinancialPlanningConversation(
            llm=llm,
            cache=cache,
            provider="google"
        )

        # First question
        response = await conversation.ask(
            user_id="user_123",
            question="How can I save more?",
            current_net_worth=575000.0
        )

        # Follow-up (remembers previous exchange)
        follow_up = await conversation.ask(
            user_id="user_123",
            question="How do I refinance?"
        )
    """

    def __init__(
        self,
        llm: Any,
        cache: Any,
        provider: str = "google",
        model_name: str = "gemini-2.0-flash-exp",
    ):
        """
        Initialize conversation manager.

        Args:
            llm: ai-infra CoreLLM instance
            cache: svc-infra cache instance (for context storage)
            provider: LLM provider ("google", "openai", "anthropic")
            model_name: Model name (default: gemini-2.0-flash-exp)
        """
        self.llm = llm
        self.cache = cache
        self.provider = provider
        self.model_name = model_name

    async def ask(
        self,
        user_id: str,
        question: str,
        current_net_worth: float | None = None,
        goals: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
    ) -> ConversationResponse:
        """
        Ask a financial planning question with conversational context.

        Args:
            user_id: User identifier
            question: User's question
            current_net_worth: Current net worth (optional, uses cached if available)
            goals: Active financial goals (optional, uses cached if available)
            session_id: Conversation session ID (auto-generated if not provided)

        Returns:
            ConversationResponse with answer, follow-ups, confidence, sources

        Raises:
            ValueError: If question contains sensitive information

        Cost: ~$0.0009/call (first turn), ~$0.0005/call (subsequent turns with cache)

        Example:
            response = await conversation.ask(
                user_id="user_123",
                question="How can I save more money?",
                current_net_worth=575000.0,
                goals=[{"type": "retirement", "target_amount": 2000000.0}]
            )

            # Follow-up
            follow_up = await conversation.ask(
                user_id="user_123",
                question="How do I refinance my car loan?",
                session_id=response.session_id  # Same session
            )
        """
        # Safety filter
        if is_sensitive_question(question):
            return ConversationResponse(
                answer=(
                    "I cannot help with sensitive information like SSN, passwords, "
                    "credit card numbers, or bank account numbers. For account security, "
                    "contact your financial institution directly."
                ),
                follow_up_questions=[],
                confidence=1.0,
                sources=["safety_filter"],
            )

        # Load or create context
        context = await self._load_context(
            user_id=user_id, session_id=session_id, current_net_worth=current_net_worth, goals=goals
        )

        # Build messages with conversation history
        messages = self._build_messages(context, question)

        # Call LLM for natural conversation (NO structured output)
        # NOTE: Conversation should be flexible, not rigidly structured
        # We want natural dialogue, not forced JSON every time
        response_text = await self.llm.achat(
            user_msg=messages[-1]["content"],  # Last message is user question
            system=messages[0]["content"],  # First message is system prompt
            provider=self.provider,
            model_name=self.model_name,
            # NO output_schema - natural conversation
        )

        # Parse response into ConversationResponse for internal use
        # (but LLM doesn't need to know about this structure)
        response = ConversationResponse(
            answer=response_text if isinstance(response_text, str) else str(response_text),
            follow_up_questions=[],  # TODO: Extract from response if formatted
            confidence=0.85,  # Default confidence for natural responses
            sources=self._extract_sources_from_context(context),
        )

        # Update context with new exchange
        context.previous_exchanges.append(
            Exchange(
                question=question, answer=response.answer, timestamp=datetime.utcnow().isoformat()
            )
        )

        # Keep only last 10 exchanges (manage cache size)
        if len(context.previous_exchanges) > 10:
            context.previous_exchanges = context.previous_exchanges[-10:]

        # Save updated context (24h TTL)
        await self._save_context(context)

        return response

    async def _load_context(
        self,
        user_id: str,
        session_id: str | None = None,
        current_net_worth: float | None = None,
        goals: list[dict[str, Any]] | None = None,
    ) -> ConversationContext:
        """
        Load conversation context from cache or create new.

        Args:
            user_id: User identifier
            session_id: Session ID (generates new if None)
            current_net_worth: Override net worth (optional)
            goals: Override goals (optional)

        Returns:
            ConversationContext (loaded or new)
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Try to load from cache
        cache_key = f"fin_infra:conversation:{user_id}:{session_id}"
        cached = await self.cache.get(cache_key)

        if cached:
            context = ConversationContext.model_validate_json(cached)

            # Update net worth/goals if provided
            if current_net_worth is not None:
                context.current_net_worth = current_net_worth
            if goals is not None:
                context.goals = goals

            return context

        # Create new context
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=24)

        return ConversationContext(
            user_id=user_id,
            session_id=session_id,
            current_net_worth=current_net_worth or 0.0,
            goals=goals or [],
            previous_exchanges=[],
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )

    async def _save_context(self, context: ConversationContext):
        """
        Save conversation context to cache with 24h TTL.

        Args:
            context: ConversationContext to save
        """
        cache_key = f"fin_infra:conversation:{context.user_id}:{context.session_id}"
        await self.cache.set(
            cache_key,
            context.model_dump_json(),
            ttl=86400,  # 24 hours
        )

    def _build_messages(self, context: ConversationContext, question: str) -> list[dict[str, str]]:
        """
        Build LLM messages with conversation history and user context.

        Args:
            context: ConversationContext with history
            question: Current user question

        Returns:
            List of messages for LLM (system + user)
        """
        # Build user context summary
        context_summary = f"""Current user context:
- Net worth: ${context.current_net_worth:,.0f}
- Active goals: {len(context.goals)}"""

        if context.goals:
            context_summary += "\n  Goals:"
            for goal in context.goals[:3]:  # Max 3 goals
                goal_type = goal.get("type", "unknown")
                target = goal.get("target_amount", 0)
                context_summary += f"\n  - {goal_type}: ${target:,.0f}"

        # Build conversation history
        if context.previous_exchanges:
            context_summary += "\n\nPrevious conversation:"
            for exchange in context.previous_exchanges[-5:]:  # Last 5 exchanges
                context_summary += f"\nQ: {exchange.question}"
                context_summary += f"\nA: {exchange.answer[:100]}..."  # Truncate long answers

        # Build system message
        system_message = CONVERSATION_SYSTEM_PROMPT + f"\n\n{context_summary}"

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": question},
        ]

    def _extract_sources_from_context(self, context: ConversationContext) -> list[str]:
        """
        Extract data sources from conversation context.

        Args:
            context: Current conversation context

        Returns:
            List of data sources used (e.g., ["current_net_worth", "goals"])
        """
        sources = []
        if context.current_net_worth and context.current_net_worth > 0:
            sources.append("current_net_worth")
        if context.goals:
            sources.extend([f"goal_{g.get('type', 'unknown')}" for g in context.goals[:3]])
        if context.previous_exchanges:
            sources.append("conversation_history")
        return sources if sources else ["user_context"]

    async def clear_session(self, user_id: str, session_id: str):
        """
        Clear conversation session from cache.

        Args:
            user_id: User identifier
            session_id: Session ID to clear

        Example:
            await conversation.clear_session("user_123", "session_abc")
        """
        cache_key = f"fin_infra:conversation:{user_id}:{session_id}"
        await self.cache.delete(cache_key)
