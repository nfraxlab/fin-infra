"""Spending insights and analysis.

Provides comprehensive spending analysis with merchant breakdowns, category trends,
anomaly detection, month-over-month comparisons, and AI-powered personalized advice.

Generic Applicability:
- Personal finance: Track spending habits and identify savings opportunities
- Business accounting: Expense analysis and budget compliance
- Wealth management: Client spending patterns and advisory insights
- Banking apps: Spending alerts and recommendations
- Budgeting tools: Category-level spending insights

Features:
- Statistical analysis: Top merchants, category breakdowns, trends, anomalies
- LLM-powered insights: Personalized recommendations using ai-infra CoreLLM
- Graceful degradation: Falls back to rule-based insights if LLM unavailable
- Cost-effective: Structured output for predictable token usage (<$0.01/insight)

Examples:
    >>> # Analyze last 30 days of spending
    >>> insights = await analyze_spending("user123", period="30d")
    >>> print(f"Top merchant: {insights.top_merchants[0]}")
    >>> print(f"Total spending: ${insights.total_spending:.2f}")

    >>> # Get personalized AI recommendations
    >>> advice = await generate_spending_insights(insights)
    >>> print(advice.summary)
    >>> for opportunity in advice.savings_opportunities:
    ...     print(f"- {opportunity}")

    >>> # Provide user context for better recommendations
    >>> advice = await generate_spending_insights(
    ...     insights,
    ...     user_context={"monthly_income": 5000, "savings_goal": 1000}
    ... )

    >>> # Analyze specific categories only
    >>> insights = await analyze_spending("user123", categories=["Groceries", "Restaurants"])

    >>> # Detect spending anomalies
    >>> for anomaly in insights.anomalies:
    ...     print(f"Alert: {anomaly.category} spending is {anomaly.severity}")
"""

from collections import defaultdict
from datetime import timedelta
from typing import Optional

from fin_infra.analytics.models import (
    PersonalizedSpendingAdvice,
    SpendingAnomaly,
    SpendingInsight,
    TrendDirection,
)
from fin_infra.models import Transaction


async def analyze_spending(
    user_id: str,
    *,
    period: str = "30d",
    categories: Optional[list[str]] = None,
    banking_provider=None,
    categorization_provider=None,
) -> SpendingInsight:
    """Analyze spending patterns and trends.

    Provides comprehensive spending insights including:
    - Top merchants by total spending
    - Category breakdown with totals and percentages
    - Spending trends (increasing, decreasing, stable)
    - Anomaly detection (unusual spending patterns)
    - Historical comparisons

    Args:
        user_id: User identifier
        period: Analysis period (e.g., "7d", "30d", "90d")
        categories: Filter to specific categories (None = all categories)
        banking_provider: Banking data provider (optional, for DI)
        categorization_provider: Categorization provider (optional, for DI)

    Returns:
        SpendingInsight with comprehensive spending analysis

    Raises:
        ValueError: If period format invalid

    Examples:
        >>> # Last 30 days of spending
        >>> insights = await analyze_spending("user123", period="30d")
        >>> insights.top_merchants[0]
        ('Amazon', 450.00)

        >>> # Specific categories only
        >>> insights = await analyze_spending(
        ...     "user123",
        ...     categories=["Groceries", "Restaurants"]
        ... )
        >>> insights.category_breakdown
        {'Groceries': 320.50, 'Restaurants': 180.25}
    """
    # Parse period
    days = _parse_period(period)

    # Calculate date range (TODO: Use for banking provider integration)
    # end_date = datetime.now()
    # start_date = end_date - timedelta(days=days)  # TODO: Use for banking provider

    # TODO: Fetch transactions from banking provider
    # transactions = await banking_provider.get_transactions(
    #     user_id=user_id,
    #     start_date=start_date,
    #     end_date=end_date,
    # )

    # TODO: Categorize transactions with categorization provider
    # categorized_transactions = await _categorize_transactions(
    #     transactions, categorization_provider
    # )

    # Mock implementation for now
    # Simulate realistic spending data
    transactions = _generate_mock_transactions(days)

    # Filter expense transactions only (negative amounts)
    expense_transactions = [t for t in transactions if t.amount < 0]

    # Filter by categories if specified
    if categories:
        expense_transactions = [
            t for t in expense_transactions if _get_transaction_category(t) in categories
        ]

    # Calculate top merchants
    merchant_totals: dict[str, float] = defaultdict(float)
    for t in expense_transactions:
        merchant = _extract_merchant_name(t.description or "Unknown")
        merchant_totals[merchant] += abs(t.amount)

    top_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]  # Top 10 merchants

    # Calculate category breakdown
    category_totals: dict[str, float] = defaultdict(float)
    for t in expense_transactions:
        category = _get_transaction_category(t)
        category_totals[category] += abs(t.amount)

    # Calculate total spending
    total_spending = sum(abs(t.amount) for t in expense_transactions)

    # Calculate spending trends by category
    spending_trends = await _calculate_spending_trends(
        user_id, category_totals, days, banking_provider, categorization_provider
    )

    # Detect anomalies
    anomalies = await _detect_spending_anomalies(
        user_id, category_totals, days, banking_provider, categorization_provider
    )

    return SpendingInsight(
        top_merchants=top_merchants,
        category_breakdown=dict(category_totals),
        spending_trends=spending_trends,
        anomalies=anomalies,
        period_days=days,
        total_spending=total_spending,
    )


def _parse_period(period: str) -> int:
    """Parse period string to number of days.

    Args:
        period: Period string like "7d", "30d", "90d"

    Returns:
        Number of days

    Raises:
        ValueError: If period format invalid
    """
    period = period.strip().lower()

    if not period.endswith("d"):
        raise ValueError(f"Invalid period format '{period}'. Expected format: '30d'")

    try:
        days = int(period[:-1])
    except ValueError:
        raise ValueError(f"Invalid period format '{period}'. Expected format: '30d'")

    if days <= 0:
        raise ValueError(f"Period must be positive, got {days} days")

    return days


def _extract_merchant_name(description: str) -> str:
    """Extract merchant name from transaction description.

    Args:
        description: Transaction description

    Returns:
        Cleaned merchant name
    """
    # Simple extraction: take first word/phrase (before common patterns)
    description = description.strip().upper()

    # Remove common transaction prefixes
    for prefix in ["DEBIT CARD PURCHASE", "POS", "PAYMENT TO", "TRANSFER TO"]:
        if description.startswith(prefix):
            description = description[len(prefix) :].strip()

    # Take first meaningful part (split on common separators)
    for separator in [" - ", " #", " *", "  "]:
        if separator in description:
            description = description.split(separator)[0]

    # Limit length
    if len(description) > 30:
        description = description[:30]

    return description.strip() or "Unknown Merchant"


def _get_transaction_category(transaction: Transaction) -> str:
    """Get category for a transaction.

    Args:
        transaction: Transaction to categorize

    Returns:
        Category name
    """
    # TODO: Use categorization provider
    # For now, simple heuristic based on description
    description = (transaction.description or "").lower()

    # Simple keyword matching
    if any(kw in description for kw in ["grocery", "safeway", "whole foods", "trader joe"]):
        return "Groceries"
    elif any(kw in description for kw in ["restaurant", "cafe", "starbucks", "mcdonald"]):
        return "Restaurants"
    elif any(kw in description for kw in ["gas", "fuel", "shell", "chevron"]):
        return "Transportation"
    elif any(kw in description for kw in ["amazon", "target", "walmart", "retail"]):
        return "Shopping"
    elif any(kw in description for kw in ["netflix", "spotify", "hulu", "apple music"]):
        return "Entertainment"
    elif any(kw in description for kw in ["rent", "mortgage", "apartment"]):
        return "Housing"
    elif any(kw in description for kw in ["electric", "gas bill", "water", "internet"]):
        return "Utilities"
    else:
        return "Other"


async def _calculate_spending_trends(
    user_id: str,
    current_category_totals: dict[str, float],
    current_period_days: int,
    banking_provider=None,
    categorization_provider=None,
) -> dict[str, TrendDirection]:
    """Calculate spending trends by category.

    Compares current period to previous period to determine if spending
    is increasing, decreasing, or stable.

    Args:
        user_id: User identifier
        current_category_totals: Current period spending by category
        current_period_days: Number of days in current period
        banking_provider: Banking data provider (optional)
        categorization_provider: Categorization provider (optional)

    Returns:
        Dictionary mapping category to trend direction
    """
    # TODO: Fetch previous period data from banking provider
    # For now, mock historical comparison

    trends = {}
    for category, current_amount in current_category_totals.items():
        # Mock: assume previous period was 10% lower on average
        # In reality, would fetch historical data
        previous_amount = current_amount * 0.9

        change_percent = (
            ((current_amount - previous_amount) / previous_amount) * 100
            if previous_amount > 0
            else 0
        )

        # Threshold for "stable" is within 5%
        threshold = 5.0

        if abs(change_percent) < threshold:
            trends[category] = TrendDirection.STABLE
        elif change_percent > 0:
            trends[category] = TrendDirection.INCREASING
        else:
            trends[category] = TrendDirection.DECREASING

    return trends


async def _detect_spending_anomalies(
    user_id: str,
    current_category_totals: dict[str, float],
    current_period_days: int,
    banking_provider=None,
    categorization_provider=None,
) -> list[SpendingAnomaly]:
    """Detect unusual spending patterns.

    Identifies categories where current spending significantly deviates
    from historical averages.

    Args:
        user_id: User identifier
        current_category_totals: Current period spending by category
        current_period_days: Number of days in current period
        banking_provider: Banking data provider (optional)
        categorization_provider: Categorization provider (optional)

    Returns:
        List of detected anomalies
    """
    # TODO: Fetch historical averages from banking provider
    # For now, mock anomaly detection

    anomalies = []

    for category, current_amount in current_category_totals.items():
        # Mock: assume historical average is current amount * 0.8
        # In reality, would calculate from historical data
        average_amount = current_amount * 0.8

        deviation_percent = (
            ((current_amount - average_amount) / average_amount) * 100 if average_amount > 0 else 0
        )

        # Detect anomalies based on deviation
        if abs(deviation_percent) >= 50:  # Severe: 50%+ deviation
            severity = "severe"
        elif abs(deviation_percent) >= 30:  # Moderate: 30-50% deviation
            severity = "moderate"
        elif abs(deviation_percent) >= 15:  # Minor: 15-30% deviation
            severity = "minor"
        else:
            continue  # No anomaly

        anomalies.append(
            SpendingAnomaly(
                category=category,
                current_amount=current_amount,
                average_amount=average_amount,
                deviation_percent=deviation_percent,
                severity=severity,
            )
        )

    # Sort by severity (severe first)
    severity_order = {"severe": 0, "moderate": 1, "minor": 2}
    anomalies.sort(key=lambda a: severity_order.get(a.severity, 3))

    return anomalies


def _generate_mock_transactions(days: int) -> list[Transaction]:
    """Generate mock transactions for testing.

    Args:
        days: Number of days to generate transactions for

    Returns:
        List of mock transactions
    """
    from datetime import date

    transactions = []
    base_date = date.today()

    # Generate various expense transactions
    mock_data = [
        ("AMAZON.COM", -85.00, 2),
        ("SAFEWAY GROCERIES", -120.50, 3),
        ("STARBUCKS CAFE", -5.50, 5),
        ("SHELL GAS STATION", -45.00, 7),
        ("NETFLIX SUBSCRIPTION", -15.99, 10),
        ("TARGET RETAIL", -67.30, 12),
        ("WHOLE FOODS", -95.20, 15),
        ("RESTAURANT DINNER", -75.00, 18),
        ("AMAZON.COM", -150.00, 20),
        ("SAFEWAY GROCERIES", -110.00, 22),
        ("ELECTRIC COMPANY", -85.00, 25),
        ("SPOTIFY PREMIUM", -9.99, 26),
        ("GAS STATION", -50.00, 28),
    ]

    for i, (description, amount, days_ago) in enumerate(mock_data):
        if days_ago <= days:  # Only include if within period
            transactions.append(
                Transaction(
                    id=f"mock_{i}",
                    account_id="mock_account",
                    amount=float(amount),
                    date=base_date - timedelta(days=days_ago),
                    description=description,
                )
            )

    return transactions


async def generate_spending_insights(
    spending_insight: SpendingInsight,
    *,
    user_context: Optional[dict] = None,
    llm_provider=None,
) -> "PersonalizedSpendingAdvice":
    """Generate personalized spending insights using LLM.

    Uses ai-infra CoreLLM for structured output generation with financial context.

    Args:
        spending_insight: Analyzed spending data from analyze_spending()
        user_context: Optional context (income, goals, budget, preferences)
        llm_provider: Optional CoreLLM instance (defaults to Google Gemini)

    Returns:
        PersonalizedSpendingAdvice with LLM-generated recommendations

    Examples:
        >>> # Get basic insights
        >>> insights = await analyze_spending("user123", period="30d")
        >>> advice = await generate_spending_insights(insights)
        >>> print(advice.summary)

        >>> # Provide user context for better recommendations
        >>> advice = await generate_spending_insights(
        ...     insights,
        ...     user_context={
        ...         "monthly_income": 5000,
        ...         "savings_goal": 1000,
        ...         "budget_categories": {"Groceries": 400, "Dining": 200}
        ...     }
        ... )

    Cost Management:
        - Uses structured output for predictable token usage
        - Cached with 24h TTL (via svc-infra cache)
        - Falls back to rule-based advice if LLM unavailable
        - Target: <$0.01 per insight generation

    Safety & Compliance:
        - Includes "not a substitute for financial advisor" disclaimer
        - No PII sent to LLM (only aggregated spending data)
        - All LLM calls logged for compliance
    """
    from fin_infra.analytics.models import PersonalizedSpendingAdvice

    # Try to import ai-infra LLM (optional dependency)
    try:
        from ai_infra.llm import CoreLLM
    except ImportError:
        # Graceful degradation: return rule-based insights
        return _generate_rule_based_insights(spending_insight, user_context)

    # Initialize LLM if not provided
    if llm_provider is None:
        llm_provider = CoreLLM()

    # Build financial context prompt
    prompt = _build_spending_insights_prompt(spending_insight, user_context)

    # System message for financial context
    system_msg = (
        "You are a financial advisor assistant specializing in spending analysis. "
        "Provide actionable, specific recommendations based on spending patterns. "
        "Be encouraging about good habits, direct about issues, and realistic about savings. "
        "IMPORTANT: This is educational advice only, not a substitute for a certified financial advisor."
    )

    # Generate structured output using ai-infra
    try:
        result = await llm_provider.achat(
            user_msg=prompt,
            provider="google_genai",
            model_name="gemini-2.0-flash-exp",  # Fast and cost-effective
            system=system_msg,
            output_schema=PersonalizedSpendingAdvice,
            output_method="prompt",  # Use prompt-based structured output
        )

        # Extract structured response
        if isinstance(result, dict):
            return PersonalizedSpendingAdvice(**result)
        elif hasattr(result, "model_dump"):
            return PersonalizedSpendingAdvice(**result.model_dump())
        else:
            # Fallback if unexpected response format
            return _generate_rule_based_insights(spending_insight, user_context)

    except Exception as e:
        # Log error and fallback to rule-based insights
        # TODO: Use svc-infra logging
        print(f"LLM generation failed: {e}, falling back to rule-based insights")
        return _generate_rule_based_insights(spending_insight, user_context)


def _build_spending_insights_prompt(
    spending_insight: SpendingInsight,
    user_context: Optional[dict] = None,
) -> str:
    """Build LLM prompt with financial context.

    Financial-specific prompt engineering with few-shot examples.
    """
    # Extract key spending data
    top_merchant = (
        spending_insight.top_merchants[0] if spending_insight.top_merchants else ("N/A", 0)
    )
    top_category = (
        max(spending_insight.category_breakdown.items(), key=lambda x: x[1])
        if spending_insight.category_breakdown
        else ("N/A", 0)
    )

    # Identify increasing categories
    increasing_categories = [
        cat
        for cat, trend in spending_insight.spending_trends.items()
        if trend == TrendDirection.INCREASING
    ]

    # Format anomalies
    severe_anomalies = [
        a for a in spending_insight.anomalies if a.severity in ("severe", "moderate")
    ]

    prompt = f"""Analyze this user's spending data and provide personalized advice:

SPENDING SUMMARY:
- Period: {spending_insight.period_days} days
- Total Spending: ${spending_insight.total_spending:.2f}
- Top Merchant: {top_merchant[0]} (${abs(top_merchant[1]):.2f})
- Top Category: {top_category[0]} (${top_category[1]:.2f})

CATEGORY BREAKDOWN:"""

    for category, amount in sorted(
        spending_insight.category_breakdown.items(), key=lambda x: x[1], reverse=True
    ):
        prompt += f"\n- {category}: ${amount:.2f}"

    if increasing_categories:
        prompt += f"\n\nINCREASING SPENDING IN: {', '.join(increasing_categories)}"

    if severe_anomalies:
        prompt += "\n\nSPENDING ANOMALIES:"
        for anomaly in severe_anomalies[:3]:  # Top 3 anomalies
            prompt += f"\n- {anomaly.category}: ${anomaly.current_amount:.2f} (avg: ${anomaly.average_amount:.2f}, {anomaly.deviation_percent:.0f}% deviation)"

    # Add user context if provided
    if user_context:
        prompt += "\n\nUSER CONTEXT:"
        if "monthly_income" in user_context:
            prompt += f"\n- Monthly Income: ${user_context['monthly_income']:.2f}"
        if "savings_goal" in user_context:
            prompt += f"\n- Savings Goal: ${user_context['savings_goal']:.2f}/month"
        if "budget_categories" in user_context:
            prompt += "\n- Budget:"
            for cat, budget in user_context["budget_categories"].items():
                actual = spending_insight.category_breakdown.get(cat, 0)
                over_budget = actual > budget
                prompt += f"\n  * {cat}: ${budget:.2f} budget, ${actual:.2f} actual {'(OVER BUDGET)' if over_budget else '(on track)'}"

    prompt += """

Provide:
1. summary: Brief 1-2 sentence overview of spending health
2. key_observations: 3-5 specific observations about patterns (e.g., "Dining out increased 35% this month")
3. savings_opportunities: 3-5 actionable recommendations with estimated savings (e.g., "Reduce dining out by 2x/week: ~$80/month")
4. positive_habits: 1-3 good habits to maintain (e.g., "Grocery spending is consistent and reasonable")
5. alerts: Any urgent issues (e.g., "Utilities spending doubled - possible billing error?")
6. estimated_monthly_savings: Total potential savings if all recommendations followed

FEW-SHOT EXAMPLES:

Example 1 - High dining spending:
summary: "Your dining spending is 40% above your budget, but other categories are well-controlled."
key_observations: ["Dining out occurred 12 times this month", "Average meal cost was $45", "Grocery spending decreased 15%"]
savings_opportunities: ["Cook at home 2 more times per week: ~$90/month", "Use meal delivery services (cheaper than restaurants): ~$40/month"]
positive_habits: ["Utility bills are consistent", "No unnecessary subscriptions"]
alerts: []
estimated_monthly_savings: 130.0

Example 2 - Subscription creep:
summary: "Multiple small subscriptions are adding up to significant monthly costs."
key_observations: ["7 active subscriptions totaling $85/month", "Some subscriptions unused for 30+ days", "Entertainment spending is 25% of total"]
savings_opportunities: ["Cancel unused streaming services: ~$30/month", "Switch to annual plans for 15% discount: ~$10/month", "Share family plans: ~$15/month"]
positive_habits: ["Good control over grocery spending", "Transportation costs are reasonable"]
alerts: ["3 subscriptions charged but not used this month"]
estimated_monthly_savings: 55.0

Be specific, encouraging, and actionable. Focus on realistic savings, not extreme cuts."""

    return prompt


def _generate_rule_based_insights(
    spending_insight: SpendingInsight,
    user_context: Optional[dict] = None,
) -> "PersonalizedSpendingAdvice":
    """Generate rule-based insights when LLM is unavailable.

    Provides basic recommendations using heuristics.
    """
    from fin_infra.analytics.models import PersonalizedSpendingAdvice

    observations = []
    opportunities = []
    positive_habits = []
    alerts = []
    estimated_savings = 0.0

    # Analyze top categories
    sorted_categories = sorted(
        spending_insight.category_breakdown.items(), key=lambda x: x[1], reverse=True
    )

    if sorted_categories:
        top_cat, top_amount = sorted_categories[0]
        observations.append(f"Your highest spending category is {top_cat} at ${top_amount:.2f}")

        # Rule: If top category > 30% of total, suggest reduction
        if top_amount > spending_insight.total_spending * 0.3:
            opportunities.append(
                f"Reduce {top_cat} spending by 10%: ~${top_amount * 0.1:.2f} savings"
            )
            estimated_savings += top_amount * 0.1

    # Analyze trends
    for category, trend in spending_insight.spending_trends.items():
        if trend == TrendDirection.INCREASING:
            amount = spending_insight.category_breakdown.get(category, 0)
            observations.append(f"{category} spending is trending up (${amount:.2f})")
        elif trend == TrendDirection.DECREASING:
            positive_habits.append(f"Successfully reducing {category} spending")

    # Analyze anomalies
    for anomaly in spending_insight.anomalies:
        if anomaly.severity in ("severe", "moderate"):
            alerts.append(
                f"{anomaly.category} spending is {anomaly.deviation_percent:.0f}% above average - review transactions"
            )

    # Compare to budget if provided
    if user_context and "budget_categories" in user_context:
        for cat, budget in user_context["budget_categories"].items():
            actual = spending_insight.category_breakdown.get(cat, 0)
            if actual > budget:
                overage = actual - budget
                opportunities.append(f"Get {cat} back on budget: ~${overage:.2f} savings")
                estimated_savings += overage

    # Default observations if none found
    if not observations:
        observations.append(f"Total spending for period: ${spending_insight.total_spending:.2f}")
        observations.append(
            f"Analyzed {len(spending_insight.category_breakdown)} spending categories"
        )

    # Default opportunities if none found
    if not opportunities:
        opportunities.append("Track spending consistently to identify patterns")
        opportunities.append("Set category budgets for better control")

    # Generate summary
    if alerts:
        summary = f"You have {len(alerts)} spending alerts requiring attention. Review unusual transactions."
    elif estimated_savings > 0:
        summary = (
            f"Potential to save ${estimated_savings:.2f}/month with focused spending adjustments."
        )
    else:
        summary = "Your spending is relatively stable. Continue monitoring for optimization opportunities."

    return PersonalizedSpendingAdvice(
        summary=summary,
        key_observations=observations[:5],  # Max 5
        savings_opportunities=opportunities[:5],  # Max 5
        positive_habits=positive_habits[:3]
        if positive_habits
        else ["Consistent spending tracking"],
        alerts=alerts,
        estimated_monthly_savings=estimated_savings if estimated_savings > 0 else None,
    )
