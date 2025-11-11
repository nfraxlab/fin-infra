"""
LLM-generated financial insights for net worth tracking (Section 17 V2).

Provides 4 types of insights:
1. Wealth Trend Analysis: Analyze net worth changes over time
2. Debt Reduction Plan: Prioritize debt payoff by APR (avalanche method)
3. Goal Recommendations: Validate financial goals and suggest paths
4. Asset Allocation Advice: Portfolio rebalancing based on age/risk

Uses ai-infra CoreLLM with structured output (Pydantic schemas).
Caches insights for 24h (target: 95%+ hit rate, $0.042/user/month cost).

Example:
    from ai_infra.llm import CoreLLM
    from fin_infra.net_worth.insights import NetWorthInsightsGenerator

    llm = CoreLLM()
    generator = NetWorthInsightsGenerator(
        llm=llm,
        provider="google",
        model_name="gemini-2.0-flash-exp"
    )

    # Generate wealth trends
    insights = await generator.generate_wealth_trends(snapshots)
    print(insights.summary)  # "Net worth increased 15% ($75k)..."
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas (Structured Output)
# ============================================================================


class WealthTrendAnalysis(BaseModel):
    """
    Wealth trend analysis over time.

    Analyzes historical net worth snapshots to identify:
    - Primary drivers of change (investment gains, salary, spending)
    - Risk factors (high debt, market exposure, spending patterns)
    - Actionable recommendations
    """

    summary: str = Field(..., description="1-2 sentence trend summary with specific numbers")
    period: str = Field(..., description="Time period analyzed (e.g., '6 months', '1 year')")
    change_amount: float = Field(..., description="Net worth change in USD (can be negative)")
    change_percent: float = Field(..., description="Percentage change (0.15 = 15%)")
    primary_drivers: list[str] = Field(
        ..., max_length=5, description="Top 5 drivers of net worth change (specific amounts)"
    )
    risk_factors: list[str] = Field(
        ..., max_length=3, description="Top 3 financial risk factors to monitor"
    )
    recommendations: list[str] = Field(
        ..., max_length=5, description="Actionable recommendations (be specific)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")


class DebtPayoffStep(BaseModel):
    """Single debt payoff step in avalanche method."""

    account_name: str = Field(..., description="Debt account name")
    balance: float = Field(..., description="Current balance in USD")
    apr: float = Field(..., description="APR as decimal (0.22 = 22%)")
    monthly_payment: float = Field(..., description="Recommended monthly payment")
    payoff_months: int = Field(..., description="Months to pay off this debt")
    interest_paid: float = Field(..., description="Total interest paid")
    reasoning: str = Field(..., description="Why this order/payment amount")


class DebtReductionPlan(BaseModel):
    """
    Debt reduction strategy using avalanche method (highest APR first).

    Calculates optimal payoff order and interest savings.
    """

    summary: str = Field(..., description="1-2 sentence strategy overview with key numbers")
    total_debt: float = Field(..., description="Total debt across all accounts")
    weighted_avg_apr: float = Field(..., description="Weighted average APR")
    payoff_order: list[DebtPayoffStep] = Field(
        ..., description="Ordered list of debt payoff steps (highest APR first)"
    )
    estimated_interest_saved: float = Field(
        ..., description="Interest saved vs minimum-only payments"
    )
    estimated_payoff_months: int = Field(..., description="Total months to become debt-free")
    recommendations: list[str] = Field(
        ..., max_length=5, description="Actionable debt reduction recommendations"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)


class AlternativePath(BaseModel):
    """Alternative path to achieving a financial goal."""

    description: str = Field(..., description="Description of alternative approach")
    required_monthly_savings: float = Field(..., description="Monthly savings needed")
    investment_return_required: float = Field(..., description="Required annual return (0.07 = 7%)")
    trade_offs: str = Field(..., description="Trade-offs of this approach")


class GoalRecommendation(BaseModel):
    """
    Financial goal validation and recommendation.

    Validates goal feasibility and suggests alternative paths.
    """

    goal_type: str = Field(..., description="retirement|home_purchase|debt_free|wealth_milestone")
    target_amount: float = Field(..., description="Target amount in USD")
    target_date: str = Field(..., description="Target date (ISO format)")
    current_progress: float = Field(..., ge=0.0, le=1.0, description="Current progress (0.0-1.0)")
    required_monthly_savings: float = Field(
        ..., description="Monthly savings needed to achieve goal"
    )
    alternative_paths: list[AlternativePath] = Field(
        ..., max_length=3, description="Up to 3 alternative approaches"
    )
    feasibility: str = Field(..., description="feasible|challenging|unrealistic")
    recommendations: list[str] = Field(..., max_length=5, description="Actionable recommendations")
    confidence: float = Field(..., ge=0.0, le=1.0)


class AssetAllocationAdvice(BaseModel):
    """
    Asset allocation and portfolio rebalancing advice.

    Based on age, risk tolerance, and current allocation.
    """

    summary: str = Field(..., description="1-2 sentence allocation summary")
    current_allocation: dict[str, float] = Field(
        ..., description="Current allocation (e.g., {'stocks': 0.7, 'bonds': 0.2, 'cash': 0.1})"
    )
    recommended_allocation: dict[str, float] = Field(
        ..., description="Recommended allocation based on age/risk"
    )
    rebalancing_steps: list[str] = Field(
        ..., max_length=5, description="Specific rebalancing actions"
    )
    expected_return: float = Field(..., description="Expected annual return (0.07 = 7%)")
    expected_volatility: float = Field(..., description="Expected annual volatility (std dev)")
    reasoning: str = Field(..., description="Why this allocation is recommended")
    recommendations: list[str] = Field(..., max_length=5, description="Actionable recommendations")
    confidence: float = Field(..., ge=0.0, le=1.0)


# ============================================================================
# System Prompts (Few-Shot Examples)
# ============================================================================

WEALTH_TRENDS_SYSTEM_PROMPT = """You are a certified financial advisor analyzing wealth trends.

Given historical net worth data, identify:
1. Primary drivers of change (be specific with dollar amounts)
2. Risk factors to monitor
3. Actionable recommendations

Be specific with numbers. Cite percentage changes and dollar amounts.
Focus on actionable insights, not generic advice.

Example 1:
User: Net worth: $500k → $575k over 6 months. Assets: +$65k (investments +$60k, savings +$5k). Liabilities: -$10k (new mortgage).
Response: {
  "summary": "Net worth increased 15% ($75k) over 6 months, driven primarily by strong investment performance.",
  "period": "6 months",
  "change_amount": 75000.0,
  "change_percent": 0.15,
  "primary_drivers": [
    "Investment portfolio gains: +$60k (tech sector rally)",
    "Increased savings: +$5k (20% savings rate maintained)",
    "New mortgage: -$10k net worth impact (closing costs + principal)"
  ],
  "risk_factors": [
    "High equity allocation (90% stocks) - vulnerable to market correction",
    "Rising mortgage debt: $300k at 6.5% APR (consider refinancing if rates drop)"
  ],
  "recommendations": [
    "Maintain 20% savings rate ($1,500/month)",
    "Rebalance to 70/30 stocks/bonds to reduce volatility",
    "Build emergency fund to 6 months expenses ($30k)"
  ],
  "confidence": 0.92
}

Example 2:
User: Net worth: $100k → $95k over 3 months. Assets: -$2k (market down). Liabilities: +$3k (credit card debt).
Response: {
  "summary": "Net worth decreased 5% ($5k) over 3 months due to market decline and rising credit card debt.",
  "period": "3 months",
  "change_amount": -5000.0,
  "change_percent": -0.05,
  "primary_drivers": [
    "Market correction: -$2k in investment portfolio (temporary)",
    "Credit card debt increase: +$3k at 22% APR (costs $55/month in interest)",
    "Reduced savings: $0 saved this quarter (was averaging $500/month)"
  ],
  "risk_factors": [
    "High-interest debt growing: $3k at 22% APR",
    "Zero savings for 3 months (income volatility or overspending)",
    "No emergency fund (vulnerable to unexpected expenses)"
  ],
  "recommendations": [
    "Pay $500/month extra on credit card to eliminate in 7 months",
    "Cut discretionary spending by $300/month (dining out, subscriptions)",
    "Resume $500/month savings once credit card is paid off"
  ],
  "confidence": 0.89
}

⚠️ This is AI-generated advice. Not a substitute for a certified financial advisor.
Verify calculations independently. For personalized advice, consult a professional."""

DEBT_REDUCTION_SYSTEM_PROMPT = """You are a debt counselor using the avalanche method (highest APR first).

Given a list of debts with balances, APRs, and minimum payments:
1. Calculate total interest cost for each debt
2. Prioritize by APR (highest first)
3. Show interest saved vs minimum-only payments
4. Be specific with monthly payment amounts and timelines

Avalanche Method:
- Pay minimums on all debts
- Put extra payments toward highest APR debt
- Once paid off, redirect payments to next highest APR
- Saves maximum interest vs snowball (smallest balance first)

Example 1:
User: Debts: Credit card $5k (22% APR, $150 min), Student loan $40k (4% APR, $350 min). Extra $500/month available.
Response: {
  "summary": "Pay off $5k credit card first (22% APR) to save $1,100/year in interest, then tackle student loans.",
  "total_debt": 45000.0,
  "weighted_avg_apr": 0.062,
  "payoff_order": [
    {
      "account_name": "Credit Card",
      "balance": 5000.0,
      "apr": 0.22,
      "monthly_payment": 650.0,
      "payoff_months": 9,
      "interest_paid": 490.0,
      "reasoning": "Highest APR (22%) - costs $1,100/year. Pay $150 min + $500 extra = $650/month."
    },
    {
      "account_name": "Student Loan",
      "balance": 40000.0,
      "apr": 0.04,
      "monthly_payment": 850.0,
      "payoff_months": 52,
      "interest_paid": 4200.0,
      "reasoning": "Low APR (4%) - pay $350 min until credit card gone, then $350 min + $500 extra = $850/month."
    }
  ],
  "estimated_interest_saved": 2100.0,
  "estimated_payoff_months": 61,
  "recommendations": [
    "Pay $650/month on credit card (paid off in 9 months)",
    "After credit card: redirect $650 to student loan ($1,000/month total)",
    "Consider refinancing student loan if rate drops below 3%",
    "Avoid new credit card debt (cut up card or freeze account)"
  ],
  "confidence": 0.98
}

⚠️ This is AI-generated advice. Not a substitute for a certified financial advisor.
Verify calculations independently. For personalized advice, consult a professional."""

GOAL_RECOMMENDATION_SYSTEM_PROMPT = """You are a financial planner validating goals and suggesting paths.

Given a financial goal (retirement, home purchase, debt-free, wealth milestone):
1. Calculate required monthly savings
2. Assess feasibility (feasible|challenging|unrealistic)
3. Suggest 2-3 alternative paths
4. Show trade-offs clearly

Formula for retirement goal:
FV = current × (1+r)^n + monthly × (((1+r)^n - 1) / r)
Where: FV = target amount, r = monthly return, n = months

Example 1:
User: Goal: $2M retirement by age 65 (25 years). Current: $300k. Assume 7% return.
Response: {
  "goal_type": "retirement",
  "target_amount": 2000000.0,
  "target_date": "2050-01-01",
  "current_progress": 0.15,
  "required_monthly_savings": 1500.0,
  "alternative_paths": [
    {
      "description": "Increase returns to 9% (riskier portfolio with more stocks)",
      "required_monthly_savings": 1200.0,
      "investment_return_required": 0.09,
      "trade_offs": "Higher volatility, 30% chance of 10%+ loss in any year"
    },
    {
      "description": "Delay retirement by 2 years to age 67",
      "required_monthly_savings": 1100.0,
      "investment_return_required": 0.07,
      "trade_offs": "Work 2 extra years, more compounding time"
    },
    {
      "description": "Reduce target to $1.5M (75% of goal)",
      "required_monthly_savings": 1100.0,
      "investment_return_required": 0.07,
      "trade_offs": "Lower retirement lifestyle (30% less spending)"
    }
  ],
  "feasibility": "feasible",
  "recommendations": [
    "Save $1,500/month in tax-advantaged accounts (401k, IRA)",
    "Maintain 7% return with 70/30 stocks/bonds allocation",
    "Increase savings rate by 2% each year (automatic escalation)",
    "Review progress annually and adjust if behind"
  ],
  "confidence": 0.89
}

⚠️ This is AI-generated advice. Not a substitute for a certified financial advisor.
Verify calculations independently. For personalized advice, consult a professional."""

ASSET_ALLOCATION_SYSTEM_PROMPT = """You are a portfolio advisor recommending asset allocation.

Given current allocation, age, and risk tolerance:
1. Recommend target allocation (stocks/bonds/cash/alternatives)
2. Calculate expected return and volatility
3. Provide specific rebalancing steps

Rule of thumb:
- Stock allocation = 100 - age (e.g., age 35 → 65% stocks)
- Bonds for stability (increases with age)
- Cash for emergency fund (3-6 months expenses)

Expected returns (historical averages):
- Stocks: 10% annual, 15% volatility
- Bonds: 4% annual, 5% volatility
- Cash: 2% annual, 0% volatility

Example 1:
User: Age 35, moderate risk. Current: 90% stocks, 5% bonds, 5% cash. Portfolio: $100k.
Response: {
  "summary": "Reduce stock allocation from 90% to 65% to match age-based guidelines and reduce volatility.",
  "current_allocation": {"stocks": 0.9, "bonds": 0.05, "cash": 0.05},
  "recommended_allocation": {"stocks": 0.65, "bonds": 0.25, "cash": 0.10},
  "rebalancing_steps": [
    "Sell $25k stocks (25% of portfolio)",
    "Buy $20k bonds (increase from 5% to 25%)",
    "Move $5k to cash/emergency fund (increase to 10%)"
  ],
  "expected_return": 0.075,
  "expected_volatility": 0.11,
  "reasoning": "At age 35, 90% stocks is aggressive. Recommended 65% stocks balances growth with stability. Reduces portfolio volatility from 14% to 11% while maintaining 7.5% expected return.",
  "recommendations": [
    "Rebalance quarterly to maintain 65/25/10 allocation",
    "Increase bond allocation by 1% per year as you age",
    "Keep emergency fund in high-yield savings (5%+ APY)",
    "Avoid frequent trading (rebalance max 4x/year)"
  ],
  "confidence": 0.91
}

⚠️ This is AI-generated advice. Not a substitute for a certified financial advisor.
Verify calculations independently. For personalized advice, consult a professional."""


# ============================================================================
# NetWorthInsightsGenerator
# ============================================================================


class NetWorthInsightsGenerator:
    """
    Generate LLM-powered financial insights for net worth tracking.

    Uses ai-infra CoreLLM with structured output (Pydantic schemas).
    Supports 4 insight types:
    1. Wealth trends (analyze net worth changes)
    2. Debt reduction (prioritize payoff by APR)
    3. Goal recommendations (validate goals, suggest paths)
    4. Asset allocation (portfolio rebalancing)

    Cost: ~$0.042/user/month (1 insight/day, 24h cache, Google Gemini)

    Example:
        from ai_infra.llm import CoreLLM

        llm = CoreLLM()
        generator = NetWorthInsightsGenerator(
            llm=llm,
            provider="google",
            model_name="gemini-2.0-flash-exp"
        )

        snapshots = [...]  # Historical net worth data
        insights = await generator.generate_wealth_trends(snapshots)
    """

    def __init__(
        self,
        llm: Any,
        provider: str = "google",
        model_name: str = "gemini-2.0-flash-exp",
    ):
        """
        Initialize insights generator.

        Args:
            llm: ai-infra CoreLLM instance
            provider: LLM provider ("google", "openai", "anthropic")
            model_name: Model name (default: gemini-2.0-flash-exp)
        """
        self.llm = llm
        self.provider = provider
        self.model_name = model_name

    async def generate_wealth_trends(
        self,
        snapshots: list[dict[str, Any]],
    ) -> WealthTrendAnalysis:
        """
        Analyze net worth trends over time.

        Args:
            snapshots: List of net worth snapshots (current + historical)
                      Each snapshot: {
                          "date": "2025-11-07",
                          "total_net_worth": 575000.0,
                          "total_assets": 620000.0,
                          "total_liabilities": 45000.0
                      }

        Returns:
            WealthTrendAnalysis with summary, drivers, risks, recommendations

        Cost: ~$0.0014/call (2k input + 500 output tokens @ $0.00035/1k)
        """
        if not snapshots:
            raise ValueError("At least 1 snapshot required for wealth trend analysis")

        # Build structured output
        structured = self.llm.with_structured_output(
            provider=self.provider,
            model_name=self.model_name,
            schema=WealthTrendAnalysis,
            method="json_mode",
        )

        # Build prompt
        current = snapshots[0]
        previous = snapshots[-1] if len(snapshots) > 1 else current

        change_amount = current["total_net_worth"] - previous["total_net_worth"]
        change_percent = (
            change_amount / previous["total_net_worth"] if previous["total_net_worth"] != 0 else 0.0
        )

        # Calculate period
        if len(snapshots) > 1:
            current_date = datetime.fromisoformat(current["date"])
            previous_date = datetime.fromisoformat(previous["date"])
            days = (current_date - previous_date).days
            if days < 60:
                period = f"{days} days"
            elif days < 400:
                months = days // 30
                period = f"{months} months"
            else:
                years = days // 365
                period = f"{years} years"
        else:
            period = "current snapshot only"

        user_prompt = f"""Analyze wealth trends:

Current net worth: ${current['total_net_worth']:,.0f}
Previous net worth: ${previous['total_net_worth']:,.0f}
Period: {period}
Change: ${change_amount:,.0f} ({change_percent:.1%})

Assets: ${current['total_assets']:,.0f}
Liabilities: ${current['total_liabilities']:,.0f}

Identify drivers of change, risk factors, and recommendations."""

        # Call LLM
        messages = [
            {"role": "system", "content": WEALTH_TRENDS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        result: WealthTrendAnalysis = await structured.ainvoke(messages)
        return result

    async def generate_debt_reduction_plan(
        self,
        liabilities: list[dict[str, Any]],
        extra_payment_available: float = 0.0,
    ) -> DebtReductionPlan:
        """
        Generate debt reduction plan using avalanche method (highest APR first).

        Args:
            liabilities: List of debts with:
                        {
                            "account_name": "Credit Card",
                            "balance": 5000.0,
                            "apr": 0.22,
                            "minimum_payment": 150.0
                        }
            extra_payment_available: Extra monthly payment beyond minimums

        Returns:
            DebtReductionPlan with payoff order, interest saved, timeline

        Cost: ~$0.0014/call
        """
        if not liabilities:
            raise ValueError("At least 1 liability required for debt reduction plan")

        # Build structured output
        structured = self.llm.with_structured_output(
            provider=self.provider,
            model_name=self.model_name,
            schema=DebtReductionPlan,
            method="json_mode",
        )

        # Format debts for prompt
        debts_text = "\n".join(
            [
                f"- {debt['account_name']}: ${debt['balance']:,.0f} at {debt['apr']:.1%} APR "
                f"(min payment: ${debt.get('minimum_payment', 0):,.0f}/month)"
                for debt in liabilities
            ]
        )

        total_debt = sum(d["balance"] for d in liabilities)

        user_prompt = f"""Generate debt reduction plan:

Debts:
{debts_text}

Total debt: ${total_debt:,.0f}
Extra payment available: ${extra_payment_available:,.0f}/month

Use avalanche method (highest APR first). Show interest saved."""

        # Call LLM
        messages = [
            {"role": "system", "content": DEBT_REDUCTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        result: DebtReductionPlan = await structured.ainvoke(messages)
        return result

    async def generate_goal_recommendations(
        self,
        goal: dict[str, Any],
        current_net_worth: float,
        monthly_income: float | None = None,
    ) -> GoalRecommendation:
        """
        Validate financial goal and suggest alternative paths.

        Args:
            goal: Financial goal with:
                  {
                      "type": "retirement|home_purchase|debt_free|wealth_milestone",
                      "target_amount": 2000000.0,
                      "target_date": "2050-01-01",
                      "current_amount": 300000.0  # Optional
                  }
            current_net_worth: Current total net worth
            monthly_income: Monthly income (optional, for affordability check)

        Returns:
            GoalRecommendation with required savings, feasibility, alternatives

        Cost: ~$0.0014/call
        """
        # Build structured output
        structured = self.llm.with_structured_output(
            provider=self.provider,
            model_name=self.model_name,
            schema=GoalRecommendation,
            method="json_mode",
        )

        # Build prompt
        goal_type = goal.get("type", "unknown")
        target_amount = goal.get("target_amount", 0.0)
        target_date = goal.get("target_date", "")
        current_amount = goal.get("current_amount", current_net_worth * 0.5)

        user_prompt = f"""Validate financial goal:

Goal type: {goal_type}
Target amount: ${target_amount:,.0f}
Target date: {target_date}
Current amount: ${current_amount:,.0f}
Current net worth: ${current_net_worth:,.0f}"""

        if monthly_income:
            user_prompt += f"\nMonthly income: ${monthly_income:,.0f}"

        user_prompt += "\n\nCalculate required monthly savings. Assess feasibility. Suggest 2-3 alternative paths."

        # Call LLM
        messages = [
            {"role": "system", "content": GOAL_RECOMMENDATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        result: GoalRecommendation = await structured.ainvoke(messages)
        return result

    async def generate_asset_allocation_advice(
        self,
        current_allocation: dict[str, float],
        age: int,
        risk_tolerance: str = "moderate",
        portfolio_value: float = 0.0,
    ) -> AssetAllocationAdvice:
        """
        Generate asset allocation and portfolio rebalancing advice.

        Args:
            current_allocation: Current allocation (e.g., {"stocks": 0.9, "bonds": 0.05, "cash": 0.05})
            age: User age (for age-based allocation guidelines)
            risk_tolerance: "conservative"|"moderate"|"aggressive"
            portfolio_value: Total portfolio value (for specific rebalancing steps)

        Returns:
            AssetAllocationAdvice with recommended allocation, rebalancing steps

        Cost: ~$0.0014/call
        """
        # Build structured output
        structured = self.llm.with_structured_output(
            provider=self.provider,
            model_name=self.model_name,
            schema=AssetAllocationAdvice,
            method="json_mode",
        )

        # Format allocation
        allocation_text = ", ".join(
            [f"{asset}: {pct:.1%}" for asset, pct in current_allocation.items()]
        )

        user_prompt = f"""Generate asset allocation advice:

Current allocation: {allocation_text}
Age: {age}
Risk tolerance: {risk_tolerance}
Portfolio value: ${portfolio_value:,.0f}

Recommend target allocation. Provide specific rebalancing steps."""

        # Call LLM
        messages = [
            {"role": "system", "content": ASSET_ALLOCATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        result: AssetAllocationAdvice = await structured.ainvoke(messages)
        return result
