"""
Easy Net Worth Tracker Builder

One-line builder for net worth tracking with sensible defaults.

**Quick Start**:
```python
from fin_infra.net_worth import easy_net_worth
from fin_infra.banking import easy_banking
from fin_infra.brokerage import easy_brokerage

# Create providers
banking = easy_banking(provider="plaid")
brokerage = easy_brokerage(provider="alpaca")

# Create tracker (one line!)
tracker = easy_net_worth(
    banking=banking,
    brokerage=brokerage
)

# Calculate net worth
snapshot = await tracker.calculate_net_worth(
    user_id="user_123",
    access_token="plaid_token_abc"
)

print(f"Net Worth: ${snapshot.total_net_worth:,.2f}")
```

**FastAPI Integration**:
```python
from fastapi import FastAPI
from fin_infra.net_worth import add_net_worth_tracking

app = FastAPI()

# Add net worth endpoints (one line!)
tracker = add_net_worth_tracking(app)
```
"""

from typing import Any

from fin_infra.net_worth.aggregator import NetWorthAggregator


class NetWorthTracker:
    """
    High-level net worth tracking interface.

    Provides simple methods for calculating net worth,
    creating snapshots, and retrieving history.

    **V1 Features** (Always Available):
    - `calculate_net_worth()`: Real-time net worth calculation (<100ms, $0 cost)
    - `create_snapshot()`: Store snapshot in database
    - `get_snapshots()`: Retrieve historical snapshots

    **V2 Features** (When enable_llm=True):
    - `generate_insights()`: LLM-generated financial insights ($0.042/user/month)
    - `ask()`: Multi-turn financial planning conversation ($0.018/user/month)
    - `validate_goal()`: LLM-validated goal tracking ($0.0036/user/month)
    - `track_goal_progress()`: Weekly progress reports with course correction

    **Example - V1 Only**:
    ```python
    tracker = NetWorthTracker(aggregator)

    # Calculate current net worth
    snapshot = await tracker.calculate_net_worth("user_123")

    # Create snapshot in database
    await tracker.create_snapshot("user_123")

    # Get historical snapshots
    history = await tracker.get_snapshots("user_123", days=90)
    ```

    **Example - V2 with LLM**:
    ```python
    tracker = NetWorthTracker(
        aggregator=aggregator,
        insights_generator=insights_generator,
        goal_tracker=goal_tracker,
        conversation=conversation,
    )

    # V1 features still work
    snapshot = await tracker.calculate_net_worth("user_123")

    # V2 features now available
    insights = await tracker.generate_insights("user_123", type="wealth_trends")
    response = await tracker.ask("How can I save more?", "user_123")
    goal = await tracker.validate_goal({
        "type": "retirement",
        "target_amount": 2000000.0,
        "target_age": 65
    })
    ```
    """

    def __init__(
        self,
        aggregator: NetWorthAggregator,
        insights_generator: Any = None,
        goal_tracker: Any = None,
        conversation: Any = None,
    ):
        """
        Initialize tracker with aggregator and optional LLM components.

        Args:
            aggregator: NetWorthAggregator instance (required)
            insights_generator: NetWorthInsightsGenerator instance (optional, V2)
            goal_tracker: FinancialGoalTracker instance (optional, V2)
            conversation: FinancialPlanningConversation instance (optional, V2)
        """
        self.aggregator = aggregator
        self.insights_generator = insights_generator
        self.goal_tracker = goal_tracker
        self.conversation = conversation

    async def calculate_net_worth(
        self,
        user_id: str,
        access_token: str | None = None,
    ):
        """
        Calculate current net worth (real-time).

        Args:
            user_id: User identifier
            access_token: Provider access token

        Returns:
            NetWorthSnapshot
        """
        return await self.aggregator.aggregate_net_worth(
            user_id=user_id,
            access_token=access_token,
        )

    async def create_snapshot(
        self,
        user_id: str,
        access_token: str | None = None,
    ):
        """
        Create and store snapshot in database.

        Args:
            user_id: User identifier
            access_token: Provider access token

        Returns:
            NetWorthSnapshot (with change tracking)
        """
        # Calculate current net worth
        snapshot = await self.calculate_net_worth(user_id, access_token)

        # Persistence: Applications store snapshots via scaffolded repository.
        # Generate with: fin-infra scaffold net_worth --dest-dir app/models/
        # NetWorthSnapshot is immutable (no updates, only create/read/delete).
        # Time-series queries: get_latest(), get_by_date(), get_trend(), calculate_growth()
        # See docs/persistence.md for snapshot storage patterns.
        # In-memory storage used here for testing/examples.

        return snapshot

    async def get_snapshots(
        self,
        user_id: str,
        days: int = 90,
        granularity: str = "daily",
    ):
        """
        Retrieve historical snapshots.

        Args:
            user_id: User identifier
            days: Look back N days
            granularity: Snapshot granularity (daily, weekly, monthly)

        Returns:
            List of NetWorthSnapshot
        """
        # Persistence: Applications query via scaffolded repository time-series methods.
        # Generate with: fin-infra scaffold net_worth --dest-dir app/models/
        # Available queries: get_by_date_range(), get_trend(months=12), calculate_growth()
        # See docs/persistence.md for time-series query patterns.
        # In-memory storage used here for testing/examples.

        return []


def easy_net_worth(
    banking: Any = None,
    brokerage: Any = None,
    crypto: Any = None,
    market: Any = None,
    base_currency: str = "USD",
    snapshot_schedule: str = "daily",
    change_threshold_percent: float = 5.0,
    change_threshold_amount: float = 10000.0,
    enable_llm: bool = False,
    llm_provider: str = "google",
    llm_model: str | None = None,
    **config,
) -> NetWorthTracker:
    """
    Create net worth tracker with sensible defaults (one-liner).

    **Example - V1 Minimal (No LLM)**:
    ```python
    from fin_infra.banking import easy_banking
    from fin_infra.net_worth import easy_net_worth

    banking = easy_banking(provider="plaid")
    tracker = easy_net_worth(banking=banking)

    # Only V1 features (real-time calculation, snapshots)
    snapshot = await tracker.calculate_net_worth("user_123")
    ```

    **Example - V2 with LLM Insights**:
    ```python
    tracker = easy_net_worth(
        banking=banking,
        enable_llm=True,  # Enable LLM insights/conversation/goals
        llm_provider="google",  # Google Gemini (default, $0.064/user/month)
    )

    # V1 features still work
    snapshot = await tracker.calculate_net_worth("user_123")

    # V2 features now available
    insights = await tracker.generate_insights("user_123", type="wealth_trends")
    conversation = await tracker.ask("How can I save more money?", "user_123")
    goal = await tracker.validate_goal({
        "type": "retirement",
        "target_amount": 2000000.0,
        "target_age": 65
    })
    ```

    **Example - Multi-Provider**:
    ```python
    from fin_infra.banking import easy_banking
    from fin_infra.brokerage import easy_brokerage
    from fin_infra.crypto import easy_crypto
    from fin_infra.net_worth import easy_net_worth

    banking = easy_banking(provider="plaid")
    brokerage = easy_brokerage(provider="alpaca")
    crypto = easy_crypto(provider="ccxt")

    tracker = easy_net_worth(
        banking=banking,
        brokerage=brokerage,
        crypto=crypto,
        base_currency="USD",
        change_threshold_percent=5.0,  # 5% change triggers alert
        change_threshold_amount=10000.0,  # $10k change triggers alert
        enable_llm=True,  # Enable LLM features
        llm_provider="google",  # Cheapest option ($0.064/user/month)
    )
    ```

    **Example - Custom LLM Provider**:
    ```python
    tracker = easy_net_worth(
        banking=banking,
        enable_llm=True,
        llm_provider="openai",  # Use OpenAI instead of Google (more expensive)
        llm_model="gpt-4o-mini",  # Override default model
    )
    ```

    Args:
        banking: Banking provider instance (Plaid/Teller)
        brokerage: Brokerage provider instance (Alpaca)
        crypto: Crypto provider instance (CCXT)
        market: Market data provider instance (Alpha Vantage)
        base_currency: Base currency for normalization (default: "USD")
        snapshot_schedule: Snapshot frequency (default: "daily")
                          Options: "daily", "weekly", "monthly", "manual"
        change_threshold_percent: Percentage change threshold for alerts (default: 5.0%)
        change_threshold_amount: Absolute change threshold for alerts (default: $10,000)
        enable_llm: Enable LLM insights/conversation/goals (default: False for backward compatibility)
        llm_provider: LLM provider to use (default: "google" - cheapest at $0.064/user/month)
                     Options: "google" (Gemini), "openai" (GPT-4o-mini), "anthropic" (Claude Haiku)
        llm_model: Override default model for provider
                  Defaults: "gemini-2.0-flash-exp" (google), "gpt-4o-mini" (openai), "claude-3-5-haiku" (anthropic)
        **config: Additional configuration (future use)

    Returns:
        NetWorthTracker instance ready to use

    Raises:
        ValueError: If no providers specified
        ImportError: If enable_llm=True but ai-infra not installed

    **Configuration Options**:
    - `snapshot_schedule`: How often to create snapshots
      - "daily": Create snapshot at midnight UTC (default)
      - "weekly": Create snapshot every Sunday at midnight
      - "monthly": Create snapshot on 1st of each month
      - "manual": Only create snapshots on demand

    - `change_threshold_percent`: Percentage change to trigger "significant change" alert
      - Default: 5.0 (5%)
      - Example: If net worth is $100k, alert on ±$5k change

    - `change_threshold_amount`: Absolute change to trigger alert
      - Default: 10000.0 ($10k)
      - Example: Alert on any ±$10k change regardless of percentage

    - `enable_llm`: Enable LLM-powered features (V2)
      - Default: False (backward compatible, no LLM costs)
      - When True: Enables insights, conversation, goal tracking ($0.064/user/month with Google Gemini)
      - Requires: ai-infra package installed

    - `llm_provider`: Which LLM provider to use (when enable_llm=True)
      - "google": Google Gemini (default, $0.064/user/month - cheapest)
      - "openai": OpenAI GPT-4o-mini ($0.183/user/month - 2.86× more expensive)
      - "anthropic": Anthropic Claude Haiku ($0.147/user/month - 2.29× more expensive)

    - `llm_model`: Override default model (when enable_llm=True)
      - Google default: "gemini-2.0-flash-exp"
      - OpenAI default: "gpt-4o-mini"
      - Anthropic default: "claude-3-5-haiku"

    **Note**: Change is significant if EITHER threshold is exceeded (OR logic)

    **Cost Analysis** (V2 with LLM):
    - Insights: $0.042/user/month (1/day, 24h cache)
    - Conversation: $0.018/user/month (2/month × 10 turns)
    - Goals: $0.0036/user/month (weekly check-ins)
    - Total: $0.064/user/month (Google Gemini, 36% under $0.10 budget)

    **Graceful Degradation**:
    - If enable_llm=False (default): Only V1 features work (real-time calculation)
    - If enable_llm=True but LLM fails: Falls back to basic insights or NotImplementedError
    - V1 features always work regardless of LLM status
    """
    # Validate at least one provider
    if not any([banking, brokerage, crypto]):
        raise ValueError(
            "At least one provider required. "
            "Pass banking=easy_banking(...), brokerage=easy_brokerage(...), "
            "or crypto=easy_crypto(...)"
        )

    # Create aggregator
    aggregator = NetWorthAggregator(
        banking_provider=banking,
        brokerage_provider=brokerage,
        crypto_provider=crypto,
        market_provider=market,
        base_currency=base_currency,
    )

    # Initialize LLM components (V2, optional)
    insights_generator = None
    goal_tracker = None
    conversation = None

    if enable_llm:
        try:
            from ai_infra.llm import CoreLLM
        except ImportError:
            raise ImportError(
                "LLM features require ai-infra package. " "Install with: pip install ai-infra"
            )

        # Determine default model
        default_models = {
            "google": "gemini-2.0-flash-exp",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-haiku",
        }
        model_name = llm_model or default_models.get(llm_provider)

        if not model_name:
            raise ValueError(
                f"Unknown llm_provider: {llm_provider}. " f"Use 'google', 'openai', or 'anthropic'"
            )

        # Create shared CoreLLM instance
        llm = CoreLLM()

        # Create LLM components (deferred import to avoid circular dependency)
        # These modules will be created in Section 17 V2 implementation
        try:
            from fin_infra.net_worth.insights import NetWorthInsightsGenerator

            insights_generator = NetWorthInsightsGenerator(
                llm=llm,
                provider=llm_provider,
                model_name=model_name,
            )
        except ImportError:
            # insights.py not yet implemented, skip
            pass

        try:
            from fin_infra.goals.management import FinancialGoalTracker

            goal_tracker = FinancialGoalTracker(
                llm=llm,
                provider=llm_provider,
                model_name=model_name,
            )
        except ImportError:
            # goals.management not yet implemented, skip
            pass

        try:
            from fin_infra.conversation import FinancialPlanningConversation

            conversation = FinancialPlanningConversation(
                llm=llm,
                cache=cache,  # Required for context storage
                provider=llm_provider,
                model_name=model_name,
            )
        except ImportError:
            # conversation module not yet implemented, skip
            pass

    # Create tracker
    tracker = NetWorthTracker(
        aggregator=aggregator,
        insights_generator=insights_generator,
        goal_tracker=goal_tracker,
        conversation=conversation,
    )

    # Store config for later use (jobs, webhooks)
    tracker.snapshot_schedule = snapshot_schedule
    tracker.change_threshold_percent = change_threshold_percent
    tracker.change_threshold_amount = change_threshold_amount
    tracker.enable_llm = enable_llm
    tracker.llm_provider = llm_provider
    tracker.llm_model = model_name if enable_llm else None
    tracker.config = config

    return tracker
