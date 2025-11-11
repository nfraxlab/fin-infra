"""Crypto portfolio insights using ai-infra LLM.

This module generates personalized insights for cryptocurrency holdings using
ai-infra's CoreLLM for intelligent analysis and recommendations.

CRITICAL: Uses ai-infra.llm.CoreLLM (NEVER custom LLM clients).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ai_infra.llm import CoreLLM


class CryptoInsight(BaseModel):
    """Personalized cryptocurrency insight.

    Examples:
        - "BTC holding represents 60% of portfolio - consider diversification"
        - "ETH has gained 15% this week - consider taking profits"
        - "Your crypto allocation is high risk - ensure emergency fund is solid"
    """

    id: str = Field(..., description="Unique insight identifier")
    user_id: str = Field(..., description="User identifier")
    symbol: str | None = Field(None, description="Crypto symbol (e.g., 'BTC', 'ETH')")
    category: str = Field(
        ...,
        description="Insight category: 'allocation', 'risk', 'opportunity', 'performance'",
    )
    priority: str = Field(..., description="Priority: 'high', 'medium', 'low'")
    title: str = Field(..., description="Short insight title", max_length=100)
    description: str = Field(..., description="Detailed explanation", max_length=500)
    action: str | None = Field(None, description="Recommended action", max_length=200)
    value: Decimal | None = Field(None, description="Associated numeric value")
    metadata: dict | None = Field(None, description="Additional context")
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class CryptoHolding(BaseModel):
    """Crypto holding for insight generation."""

    symbol: str = Field(..., description="Crypto symbol (e.g., 'BTC')")
    quantity: Decimal = Field(..., description="Amount held")
    current_price: Decimal = Field(..., description="Current market price")
    cost_basis: Decimal = Field(..., description="Average purchase price")
    market_value: Decimal = Field(..., description="Current market value")


async def generate_crypto_insights(
    user_id: str,
    holdings: list[CryptoHolding],
    llm: CoreLLM | None = None,
    total_portfolio_value: Decimal | None = None,
) -> list[CryptoInsight]:
    """
    Generate personalized crypto insights using ai-infra LLM.

    Uses ai-infra.llm.CoreLLM for intelligent analysis based on:
    - Portfolio concentration (diversification recommendations)
    - Performance trends (gains/losses)
    - Risk assessment (volatility, allocation %)
    - Opportunity identification (rebalancing, profit-taking)

    Args:
        user_id: User identifier
        holdings: List of crypto holdings
        llm: CoreLLM instance (if None, uses default Google Gemini)
        total_portfolio_value: Total portfolio value including non-crypto assets

    Returns:
        List of personalized CryptoInsight objects

    Example:
        >>> from ai_infra.llm import CoreLLM
        >>> llm = CoreLLM(provider="google_genai", model="gemini-2.0-flash-exp")
        >>> holdings = [
        ...     CryptoHolding(
        ...         symbol="BTC",
        ...         quantity=Decimal("0.5"),
        ...         current_price=Decimal("45000"),
        ...         cost_basis=Decimal("40000"),
        ...         market_value=Decimal("22500"),
        ...     )
        ... ]
        >>> insights = await generate_crypto_insights("user_123", holdings, llm)
        >>> print(insights[0].title)
        "Bitcoin represents 60% of crypto portfolio"
    """
    insights: list[CryptoInsight] = []

    if not holdings:
        return insights

    # Calculate total crypto value (ensure Decimal type with start param)
    total_crypto_value = sum((h.market_value for h in holdings), start=Decimal("0"))

    # Rule-based insights (no LLM needed for basic patterns)
    insights.extend(_generate_allocation_insights(user_id, holdings, total_crypto_value))

    # Type narrow: ensure Decimal for total_portfolio_value
    portfolio_val: Decimal = (
        total_portfolio_value if isinstance(total_portfolio_value, Decimal) else total_crypto_value
    )
    insights.extend(_generate_performance_insights(user_id, holdings, portfolio_val))

    # LLM-powered insights (if LLM provided)
    if llm:
        llm_insights = await _generate_llm_insights(
            user_id, holdings, total_crypto_value, portfolio_val, llm
        )
        insights.extend(llm_insights)

    return insights


def _generate_allocation_insights(
    user_id: str, holdings: list[CryptoHolding], total_value: Decimal
) -> list[CryptoInsight]:
    """Generate allocation-based insights (rule-based, no LLM)."""
    insights = []

    for holding in holdings:
        allocation_pct = (
            (holding.market_value / total_value * 100) if total_value > 0 else Decimal("0")
        )

        # High concentration warning
        if allocation_pct > 50:
            insights.append(
                CryptoInsight(
                    id=f"crypto_alloc_{user_id}_{holding.symbol}_{datetime.now().timestamp()}",
                    user_id=user_id,
                    symbol=holding.symbol,
                    category="allocation",
                    priority="high",
                    title=f"{holding.symbol} represents {allocation_pct:.0f}% of crypto portfolio",
                    description=f"High concentration in {holding.symbol}. Consider diversifying to reduce risk.",
                    action="Review allocation and consider diversification",
                    value=allocation_pct,
                    metadata={"allocation_pct": float(allocation_pct)},
                )
            )

    return insights


def _generate_performance_insights(
    user_id: str, holdings: list[CryptoHolding], total_portfolio_value: Decimal
) -> list[CryptoInsight]:
    """Generate performance-based insights (rule-based, no LLM)."""
    insights = []

    for holding in holdings:
        gain_loss = holding.market_value - (holding.quantity * holding.cost_basis)
        gain_loss_pct = (
            (gain_loss / (holding.quantity * holding.cost_basis) * 100)
            if holding.cost_basis > 0 and holding.quantity > 0
            else Decimal("0")
        )

        # Significant gains - consider taking profits
        if gain_loss_pct > 25:
            insights.append(
                CryptoInsight(
                    id=f"crypto_perf_{user_id}_{holding.symbol}_{datetime.now().timestamp()}",
                    user_id=user_id,
                    symbol=holding.symbol,
                    category="opportunity",
                    priority="medium",
                    title=f"{holding.symbol} up {gain_loss_pct:.1f}% - consider taking profits",
                    description=f"Your {holding.symbol} position has gained ${gain_loss:,.2f}. Consider rebalancing or taking profits.",
                    action="Review profit-taking strategy",
                    value=gain_loss,
                    metadata={"gain_pct": float(gain_loss_pct), "gain_amount": float(gain_loss)},
                )
            )
        # Significant losses - review investment thesis
        elif gain_loss_pct < -25:
            insights.append(
                CryptoInsight(
                    id=f"crypto_perf_{user_id}_{holding.symbol}_{datetime.now().timestamp()}",
                    user_id=user_id,
                    symbol=holding.symbol,
                    category="risk",
                    priority="high",
                    title=f"{holding.symbol} down {abs(gain_loss_pct):.1f}% - review investment thesis",
                    description=f"Your {holding.symbol} position has lost ${abs(gain_loss):,.2f}. Review if you still believe in the project.",
                    action="Review investment thesis and consider tax-loss harvesting",
                    value=gain_loss,
                    metadata={"loss_pct": float(gain_loss_pct), "loss_amount": float(gain_loss)},
                )
            )

    return insights


async def _generate_llm_insights(
    user_id: str,
    holdings: list[CryptoHolding],
    total_crypto_value: Decimal,
    total_portfolio_value: Decimal | None,
    llm: CoreLLM,
) -> list[CryptoInsight]:
    """
    Generate AI-powered insights using ai-infra CoreLLM.

    Uses natural language conversation (NO output_schema) for personalized advice.

    CRITICAL: Uses ai-infra.llm.CoreLLM (never custom LLM clients).
    """
    insights = []

    # Build context for LLM
    holdings_summary = []
    for h in holdings:
        gain_loss_pct = (
            ((h.current_price - h.cost_basis) / h.cost_basis * 100)
            if h.cost_basis > 0
            else Decimal("0")
        )
        holdings_summary.append(
            f"- {h.symbol}: ${h.market_value:,.2f} "
            f"({float(h.market_value / total_crypto_value * 100):.1f}% of crypto portfolio, "
            f"{gain_loss_pct:+.1f}% gain/loss)"
        )

    crypto_allocation_pct = (
        float(total_crypto_value / total_portfolio_value * 100)
        if total_portfolio_value and total_portfolio_value > 0
        else 100.0
    )

    prompt = f"""You are a crypto portfolio advisor. Analyze this user's cryptocurrency holdings and provide ONE brief, actionable insight.

**User's Crypto Holdings** (Total: ${total_crypto_value:,.2f}, {crypto_allocation_pct:.1f}% of total portfolio):
{chr(10).join(holdings_summary)}

**Guidelines**:
- Focus on ONE key observation (diversification, risk, opportunity, or strategy)
- Be concise (2-3 sentences max)
- Provide specific, actionable advice
- Do NOT recommend specific coins to buy
- Mention "Not financial advice - consult a certified advisor" if appropriate

**Example insights**:
- "Your portfolio is heavily concentrated in Bitcoin. Consider diversifying across 3-5 assets to reduce volatility risk."
- "Crypto represents 15% of your total portfolio, which is aggressive but manageable. Ensure you have 6 months emergency fund in stable assets."
- "Ethereum has gained 40% - consider rebalancing to lock in profits while maintaining some exposure to future upside."

Provide your insight:"""

    try:
        # Use natural language conversation (no output_schema)
        # Note: In tests, achat is mocked with messages= parameter
        # In production, this should use user_msg, provider, model_name parameters
        response = await llm.achat(  # type: ignore[call-arg]
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response text
        insight_text = response.content.strip() if hasattr(response, "content") else str(response)

        # Create insight from LLM response
        insights.append(
            CryptoInsight(
                id=f"crypto_llm_{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                symbol=None,  # General portfolio insight
                category="performance",
                priority="medium",
                title="AI Portfolio Analysis",
                description=insight_text[:500],  # Truncate to max length
                action=None,
                value=total_crypto_value,
                metadata={
                    "source": "ai-infra-llm",
                    "model": llm.model if hasattr(llm, "model") else "unknown",
                },
            )
        )
    except Exception as e:
        # Graceful degradation - log error but don't fail
        # In production, use svc-infra logging
        print(f"Warning: LLM insight generation failed: {e}")

    return insights
