"""
LLM-powered portfolio rebalancing recommendations.

Uses LLM to generate intelligent, personalized rebalancing suggestions
that consider:
- Portfolio diversification
- Risk tolerance
- Tax efficiency
- Investment goals
- Market conditions

Caching:
    Uses svc-infra's cache_read decorator for persistent caching.
    Cache key is based on portfolio STRUCTURE (symbols + 5% allocation buckets),
    not exact values. This means small price fluctuations don't trigger new LLM calls.
    TTL: 24 hours (rebalancing advice doesn't need real-time updates).
"""

from __future__ import annotations

import hashlib
import json
import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

# svc-infra caching - uses Redis in production, in-memory in dev
try:
    from svc_infra.cache import cache_read

    HAS_SVC_CACHE = True
except ImportError:
    HAS_SVC_CACHE = False
    cache_read = None  # type: ignore

if TYPE_CHECKING:
    from fin_infra.models.brokerage import Position

logger = logging.getLogger(__name__)

# Cache TTL: 24 hours - rebalancing advice doesn't change frequently
REBALANCE_CACHE_TTL = 86400


# ---------------------------------------------------------------------------
# Output Schema
# ---------------------------------------------------------------------------


class LLMTrade(BaseModel):
    """Single trade recommended by LLM."""

    symbol: str = Field(..., description="Security ticker symbol to trade")
    action: str = Field(..., description="'buy' or 'sell'")
    percentage_of_portfolio: float = Field(
        ..., description="Percentage of portfolio value for this trade (e.g., 5.0 = 5%)"
    )
    reasoning: str = Field(..., description="Clear explanation for this trade")


class LLMRebalancingPlan(BaseModel):
    """LLM-generated rebalancing recommendations."""

    summary: str = Field(
        ...,
        max_length=500,
        description="High-level summary of portfolio state and key recommendations",
    )
    analysis: str = Field(
        ...,
        max_length=800,
        description="Analysis of current portfolio: diversification, risk exposure, concerns",
    )
    trades: list[LLMTrade] = Field(
        default_factory=list,
        description="Recommended trades (max 5). Empty if portfolio is balanced.",
        max_length=5,
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Strategic recommendations beyond specific trades (max 3)",
        max_length=3,
    )
    risk_warnings: list[str] = Field(
        default_factory=list,
        description="Important risk warnings or concerns (max 3)",
        max_length=3,
    )
    is_balanced: bool = Field(
        False,
        description="True if portfolio is already well-balanced and no trades needed",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "summary": "Your portfolio is heavily concentrated in one stock (SBSI at 29%). Consider diversifying into broad index funds for better risk management.",
                "analysis": "Current allocation: 48% cash, 29% single stock (SBSI), 23% diversified funds/ETFs. High single-stock risk. Excessive cash position.",
                "trades": [
                    {
                        "symbol": "VTI",
                        "action": "buy",
                        "percentage_of_portfolio": 20.0,
                        "reasoning": "Deploy excess cash into total US stock market index for diversification",
                    },
                    {
                        "symbol": "SBSI",
                        "action": "sell",
                        "percentage_of_portfolio": 15.0,
                        "reasoning": "Reduce single-stock concentration risk from 29% to ~14%",
                    },
                ],
                "recommendations": [
                    "Consider tax-loss harvesting on underperforming positions",
                    "Set up automatic monthly investments into index funds",
                    "Review asset allocation quarterly",
                ],
                "risk_warnings": [
                    "29% concentration in SBSI exposes you to company-specific risk",
                    "48% cash is likely underperforming inflation long-term",
                ],
                "is_balanced": False,
            }
        }
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

REBALANCING_SYSTEM_PROMPT = """
You are an expert financial advisor optimizing investment portfolios.

CRITICAL RULES (in order of priority):
1. DEPLOY CASH FIRST: Before selling any position, use available cash to buy. Selling triggers taxes; buying with cash does not.
2. TAX AWARENESS: Positions with large unrealized gains should be sold last. Check cost_basis vs current value.
3. MATH ACCURACY: Verify percentages add up. If buying 20% of portfolio, calculate exact dollar amount from total value.
4. CONCENTRATION LIMITS: Any single stock >15% is risky. Broad ETFs (VTI, VOO) don't count as concentration.
5. CASH TARGET: Keep 2-5% cash for liquidity; excess cash loses to inflation.

TRADE LOGIC:
- If cash > 10%: Deploy into target allocation BEFORE any sells
- If position has gains > 20%: Avoid selling unless critically overweight
- Prefer buying broad index funds: VTI (US), VXUS (Intl), BND (Bonds)
- Limit to 5 trades maximum; prioritize highest-impact moves

ASSET CLASSIFICATION:
- "U S Dollar", "USD", "Cash" = Cash position
- Individual stocks (AAPL, SBSI, etc.) = Concentration risk if >15%
- ETFs (VTI, SPY, BND) = Diversified, lower risk
- Mutual funds (ending in X) = Check if broad or concentrated
- Crypto = High volatility, keep <5%

OUTPUT REQUIREMENTS:
- is_balanced=true only if allocation matches target within 5%
- Each trade must have clear reasoning tied to target allocation
- Dollar amounts must be mathematically correct
"""

REBALANCING_USER_PROMPT = """
User's current portfolio holdings:
{holdings_json}

Total portfolio value: ${total_value:,.2f}

Target allocation (if specified): {target_allocation}

Please analyze this portfolio and provide rebalancing recommendations.
Consider diversification, risk management, and tax efficiency.
If the portfolio is already well-balanced, indicate that no trades are needed.
"""


# ---------------------------------------------------------------------------
# Generator Class
# ---------------------------------------------------------------------------


class RebalancingInsightsGenerator:
    """
    LLM-powered portfolio rebalancing recommendations.

    Uses ai-infra LLM to generate intelligent trade recommendations
    based on portfolio analysis, diversification principles, and risk management.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model_name: str | None = "claude-3-5-haiku-latest",
        cache_ttl: int = 86400,  # 24 hours - portfolio structure rarely changes
        enable_cache: bool = True,
        max_cost_per_day: float = 0.10,
        max_cost_per_month: float = 2.00,
    ):
        """
        Initialize rebalancing generator.

        Args:
            provider: LLM provider ("google", "openai", "anthropic")
            model_name: Model override (default: provider-specific)
            cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
            enable_cache: Enable caching (default: True)
            max_cost_per_day: Daily budget cap in USD (default: $0.10)
            max_cost_per_month: Monthly budget cap in USD (default: $2.00)
        """
        from ai_infra.llm import LLM

        self.provider = provider
        self.model_name = model_name
        self.cache_ttl = cache_ttl
        self.enable_cache = enable_cache
        self.max_cost_per_day = max_cost_per_day
        self.max_cost_per_month = max_cost_per_month

        # Initialize LLM
        self.llm = LLM()

    async def generate(
        self,
        positions: list[Position],
        target_allocation: dict[str, Decimal] | None = None,
        user_id: str | None = None,
    ) -> LLMRebalancingPlan:
        """
        Generate LLM-powered rebalancing recommendations.

        Uses svc-infra caching to avoid redundant LLM calls.
        Cache key is based on portfolio STRUCTURE, not exact values.

        Args:
            positions: Current portfolio positions
            target_allocation: Optional target allocation by asset class
            user_id: Optional user ID for caching

        Returns:
            LLMRebalancingPlan with trades and recommendations
        """
        # Convert positions to serializable format
        holdings = self._positions_to_holdings(positions)

        if not holdings:
            return self._empty_portfolio_response()

        # Generate cache key from portfolio structure
        cache_key = self._generate_cache_key(holdings, target_allocation, user_id)

        # Use svc-infra cached function if available
        if self.enable_cache and HAS_SVC_CACHE:
            logger.info(f"[REBALANCE_CACHE] Checking cache, key={cache_key}")
            result = await _cached_rebalance_llm_call(
                cache_key=cache_key,
                holdings_json=json.dumps(holdings, sort_keys=True),
                target_allocation_json=json.dumps(
                    {k: float(v) for k, v in (target_allocation or {}).items()},
                    sort_keys=True,
                ),
                provider=self.provider,
                model_name=self.model_name,
            )
            if result is not None:
                return result  # type: ignore[no-any-return]
            # Fallback if cached call failed
            logger.warning("[REBALANCE_CACHE] Cached call returned None, trying direct")

        # Direct call (no cache or fallback)
        try:
            result = await self._call_llm(holdings, target_allocation)
            logger.info("Generated LLM rebalancing recommendations")
            return result
        except Exception as e:
            logger.error("LLM call failed for rebalancing: %s", e)
            return self._fallback_response(holdings)

    def _positions_to_holdings(self, positions: list[Position]) -> list[dict[str, Any]]:
        """Convert Position objects to serializable holdings list."""
        holdings = []
        for pos in positions:
            holding = {
                "symbol": pos.symbol,
                "name": getattr(pos, "name", pos.symbol),
                "quantity": float(pos.qty),
                "market_value": float(pos.market_value),
                "asset_class": getattr(pos, "asset_class", "unknown"),
            }
            # Calculate percentage (will be done after we have total)
            holdings.append(holding)

        # Calculate percentages
        total: float = sum(float(h["market_value"]) for h in holdings)
        if total > 0:
            for h in holdings:
                h["percentage"] = round(float(h["market_value"]) / total * 100, 2)

        # Sort by value descending
        holdings.sort(key=lambda x: x["market_value"], reverse=True)

        return holdings

    def _generate_cache_key(
        self,
        holdings: list[dict[str, Any]],
        target_allocation: dict[str, Decimal] | None,
        user_id: str | None,
    ) -> str:
        """Generate cache key from portfolio STRUCTURE, not current values.

        Rebalancing advice depends on:
        - Which holdings you have (symbols)
        - Approximate allocation buckets (not exact dollar amounts)
        - Target allocation

        It does NOT need to change when:
        - Stock prices fluctuate (daily noise)
        - Small quantity changes (<10%)
        """
        import json

        # Hash based on structure, not exact values:
        # - Symbols (what you own)
        # - Allocation buckets (5% increments) - not exact percentages
        # - Target allocation
        total_value = sum(h["market_value"] for h in holdings)

        cache_data = {
            # Symbols you own (sorted for consistency)
            "symbols": sorted(h["symbol"] for h in holdings if h["market_value"] > 0),
            # Allocation in 5% buckets (e.g., 48.5% -> 50%, 29% -> 30%)
            "allocations": {
                h["symbol"]: round(h["market_value"] / total_value * 20) * 5  # Round to nearest 5%
                for h in holdings
                if h["market_value"] / total_value > 0.02  # Only include >2% positions
            }
            if total_value > 0
            else {},
            # Target allocation
            "target": {k: float(v) for k, v in (target_allocation or {}).items()},
        }

        data_json = json.dumps(cache_data, sort_keys=True)
        # Security: B324 skip justified - MD5 used for cache key generation only.
        portfolio_hash = hashlib.md5(data_json.encode()).hexdigest()[:12]

        # Include user_id for user-specific caching
        if user_id:
            return f"rebalance:{user_id}:{portfolio_hash}"

        return f"rebalance:{portfolio_hash}"

    async def _call_llm(
        self,
        holdings: list[dict[str, Any]],
        target_allocation: dict[str, Decimal] | None,
    ) -> LLMRebalancingPlan:
        """Call LLM for rebalancing recommendations."""
        import json

        # Calculate total value
        total_value = sum(h["market_value"] for h in holdings)

        # Format holdings for prompt
        holdings_json = json.dumps(holdings, indent=2)

        # Format target allocation
        if target_allocation:
            target_str = ", ".join(f"{k}: {v}%" for k, v in target_allocation.items())
        else:
            target_str = "Not specified (recommend based on moderate risk tolerance)"

        user_prompt = REBALANCING_USER_PROMPT.format(
            holdings_json=holdings_json,
            total_value=total_value,
            target_allocation=target_str,
        )

        # Try with structured output first, fall back to raw content parsing
        import asyncio
        import time

        try:
            logger.info(f"Calling LLM: provider={self.provider}, model={self.model_name}")
            start_time = time.monotonic()
            response = await asyncio.wait_for(
                self.llm.achat(
                    user_msg=user_prompt,
                    provider=self.provider,
                    model_name=self.model_name,
                    system=REBALANCING_SYSTEM_PROMPT,
                    output_schema=LLMRebalancingPlan,
                    output_method="prompt",  # Use prompt for cross-provider compatibility
                    temperature=0.3,  # Some creativity for recommendations
                    max_tokens=4000,  # Increased for complex portfolio analysis
                ),
                timeout=60.0,  # 60 second timeout for Gemini (can be slow)
            )
            elapsed = time.monotonic() - start_time

            # ai-infra LLM.achat with output_schema returns the Pydantic model directly
            if isinstance(response, LLMRebalancingPlan):
                logger.info(
                    f"LLM returned structured LLMRebalancingPlan directly in {elapsed:.2f}s"
                )
                return response

        except TimeoutError:
            logger.error("LLM call timed out after 60 seconds")
            raise
        except ValueError as e:
            # ai-infra coerce_structured_result failed - try raw content parsing
            logger.warning("Structured output parsing failed: %s - trying raw content", e)
        except Exception as e:
            logger.error(f"LLM call failed with {type(e).__name__}: {e}")
            raise

        # Fall back to calling without output_schema and parsing manually
        logger.info("Attempting raw LLM call without output_schema")
        raw_response = await self.llm.achat(
            user_msg=user_prompt,
            provider=self.provider,
            model_name=self.model_name,
            system=REBALANCING_SYSTEM_PROMPT
            + "\n\nIMPORTANT: Respond with ONLY valid JSON, no markdown or explanation.",
            temperature=0.3,
            max_tokens=4000,  # Increased for complex portfolio analysis
        )

        # Parse raw content
        content = getattr(raw_response, "content", str(raw_response))
        if content:
            # Handle Gemini's list content format: [{'type': 'text', 'text': '...'}]
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "".join(text_parts) if text_parts else str(content)

            logger.debug(
                "Raw LLM content length=%d, first 500 chars: %s", len(content), content[:500]
            )
            logger.debug(
                "Raw LLM content last 200 chars: %s",
                content[-200:] if len(content) > 200 else content,
            )
            content = content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # Try to find JSON object in the content
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                data = json.loads(json_str)
                logger.info("Successfully parsed LLM JSON response manually")

                # Normalize data to match schema - handle missing fields and truncate lists
                normalized = self._normalize_llm_response(data)
                return LLMRebalancingPlan(**normalized)

        raise ValueError("Could not extract valid JSON from LLM response")

    def _normalize_llm_response(self, data: dict) -> dict:
        """Normalize LLM response to match schema requirements."""
        # Ensure required fields exist
        if "summary" not in data:
            # Try to use analysis as summary if available
            data["summary"] = data.get("analysis", "Portfolio analysis completed.")[:500]

        if "analysis" not in data:
            data["analysis"] = data.get("summary", "Analysis unavailable.")[:800]

        # Truncate summary and analysis to max lengths
        if len(data.get("summary", "")) > 500:
            data["summary"] = data["summary"][:497] + "..."
        if len(data.get("analysis", "")) > 800:
            data["analysis"] = data["analysis"][:797] + "..."

        # Truncate trades to max 5
        if "trades" in data and isinstance(data["trades"], list):
            data["trades"] = data["trades"][:5]
        else:
            data["trades"] = []

        # Truncate recommendations to max 3
        if "recommendations" in data and isinstance(data["recommendations"], list):
            data["recommendations"] = [
                str(r) if isinstance(r, str) else r.get("reasoning", str(r))
                for r in data["recommendations"]
            ][:3]
        else:
            data["recommendations"] = []

        # Truncate risk_warnings to max 3
        if "risk_warnings" in data and isinstance(data["risk_warnings"], list):
            data["risk_warnings"] = data["risk_warnings"][:3]
        else:
            data["risk_warnings"] = []

        # Ensure is_balanced is boolean
        data["is_balanced"] = bool(data.get("is_balanced", False))

        return data

    def _empty_portfolio_response(self) -> LLMRebalancingPlan:
        """Response for empty portfolio."""
        return LLMRebalancingPlan(
            summary="Your portfolio is empty. Add funds to start investing.",
            analysis="No holdings to analyze.",
            trades=[],
            recommendations=[
                "Open a brokerage account if you haven't already",
                "Consider starting with a low-cost index fund like VTI",
                "Set up automatic monthly contributions",
            ],
            risk_warnings=[],
            is_balanced=True,
        )

    def _fallback_response(self, holdings: list[dict[str, Any]]) -> LLMRebalancingPlan:
        """Fallback response when LLM unavailable."""
        total_value = sum(h["market_value"] for h in holdings)

        # Basic analysis
        top_holding = holdings[0] if holdings else None
        concentration_warning = None

        if top_holding and top_holding["percentage"] > 30:
            concentration_warning = (
                f"High concentration in {top_holding['symbol']} "
                f"({top_holding['percentage']:.1f}% of portfolio)"
            )

        # Calculate asset class breakdown
        cash_pct = sum(
            h["percentage"]
            for h in holdings
            if h.get("asset_class") in ["cash", "currency", "money_market"]
            or "dollar" in h["symbol"].lower()
        )

        warnings = []
        if concentration_warning:
            warnings.append(concentration_warning)
        if cash_pct > 30:
            warnings.append(f"High cash allocation ({cash_pct:.1f}%) may underperform inflation")

        return LLMRebalancingPlan(
            summary=f"Portfolio has {len(holdings)} holdings worth ${total_value:,.2f}. "
            "LLM analysis temporarily unavailable.",
            analysis="Basic analysis performed. Detailed recommendations require LLM.",
            trades=[],
            recommendations=[
                "Consider consulting a financial advisor for personalized advice",
                "Review your portfolio for diversification across asset classes",
            ],
            risk_warnings=warnings,
            is_balanced=True,  # Conservative default
        )


# ---------------------------------------------------------------------------
# Cached LLM Call (svc-infra caching)
# ---------------------------------------------------------------------------


async def _do_rebalance_llm_call_impl(
    cache_key: str,
    holdings_json: str,
    target_allocation_json: str,
    provider: str,
    model_name: str,
) -> LLMRebalancingPlan | None:
    """
    Actually call the LLM for rebalancing (no caching, called by cached wrapper).
    """
    import asyncio
    import time
    from decimal import Decimal

    from ai_infra.llm import LLM

    logger.info(f"[REBALANCE_CACHE] MISS - calling LLM (key={cache_key})")

    holdings = json.loads(holdings_json)
    target_allocation_raw = json.loads(target_allocation_json)
    target_allocation = (
        {k: Decimal(str(v)) for k, v in target_allocation_raw.items()}
        if target_allocation_raw
        else None
    )

    # Calculate total value
    total_value = sum(h["market_value"] for h in holdings)

    # Format holdings for prompt
    formatted_holdings_json = json.dumps(holdings, indent=2)

    # Format target allocation
    if target_allocation:
        target_str = ", ".join(f"{k}: {v}%" for k, v in target_allocation.items())
    else:
        target_str = "Not specified (recommend based on moderate risk tolerance)"

    user_prompt = REBALANCING_USER_PROMPT.format(
        holdings_json=formatted_holdings_json,
        total_value=total_value,
        target_allocation=target_str,
    )

    llm = LLM()

    try:
        logger.info(f"Calling LLM: provider={provider}, model={model_name}")
        start_time = time.monotonic()
        response = await asyncio.wait_for(
            llm.achat(
                user_msg=user_prompt,
                provider=provider,
                model_name=model_name,
                system=REBALANCING_SYSTEM_PROMPT,
                output_schema=LLMRebalancingPlan,
                output_method="prompt",
                temperature=0.3,
                max_tokens=4000,
            ),
            timeout=60.0,
        )
        elapsed = time.monotonic() - start_time

        if isinstance(response, LLMRebalancingPlan):
            logger.info(f"[REBALANCE_CACHE] LLM returned result in {elapsed:.2f}s")
            return response

        logger.warning("LLM response was not LLMRebalancingPlan: %s", type(response))
        return None

    except TimeoutError:
        logger.error("LLM call timed out after 60 seconds")
        return None
    except Exception as e:
        logger.error(f"LLM call failed: {type(e).__name__}: {e}")
        return None


# Apply svc-infra caching decorator if available
if HAS_SVC_CACHE and cache_read is not None:
    _cached_rebalance_llm_call = cache_read(
        key="rebalance:{cache_key}",
        ttl=REBALANCE_CACHE_TTL,
    )(_do_rebalance_llm_call_impl)
    logger.info("[REBALANCE_CACHE] Using svc-infra cache_read decorator")
else:
    # Fallback: no caching
    _cached_rebalance_llm_call = _do_rebalance_llm_call_impl
    logger.warning("[REBALANCE_CACHE] svc-infra cache not available, caching disabled")


# ---------------------------------------------------------------------------
# Convenience Function
# ---------------------------------------------------------------------------

# Module-level singleton to preserve cache across calls
_generator_instance: RebalancingInsightsGenerator | None = None


def _get_generator(provider: str, model_name: str) -> RebalancingInsightsGenerator:
    """Get or create singleton generator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = RebalancingInsightsGenerator(provider=provider, model_name=model_name)
    return _generator_instance


async def generate_rebalancing_plan_llm(
    positions: list[Position],
    target_allocation: dict[str, Decimal] | None = None,
    user_id: str | None = None,
    provider: str = "anthropic",
    model_name: str = "claude-3-5-haiku-latest",
) -> LLMRebalancingPlan:
    """
    Generate LLM-powered rebalancing recommendations.

    Convenience function that creates generator and calls it.

    Args:
        positions: Current portfolio positions
        target_allocation: Optional target allocation by asset class
        user_id: Optional user ID for caching
        provider: LLM provider to use
        model_name: Model name to use

    Returns:
        LLMRebalancingPlan with trades and recommendations
    """
    generator = _get_generator(provider=provider, model_name=model_name)
    return await generator.generate(positions, target_allocation, user_id)
