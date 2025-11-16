"""
FastAPI Integration for Net Worth Tracking

Provides REST API endpoints for net worth tracking:
- GET /net-worth/current - Current net worth (cached 1h)
- GET /net-worth/snapshots - Historical snapshots
- GET /net-worth/breakdown - Asset/liability breakdown
- POST /net-worth/snapshot - Force snapshot creation

**Quick Start**:
```python
from fastapi import FastAPI
from fin_infra.net_worth import add_net_worth_tracking, easy_net_worth
from fin_infra.banking import easy_banking

app = FastAPI()

# Create tracker
banking = easy_banking(provider="plaid")
tracker = easy_net_worth(banking=banking)

# Add endpoints (one line!)
add_net_worth_tracking(app, tracker=tracker)
```

**Auto-wired Integration** (no tracker needed):
```python
from fastapi import FastAPI
from fin_infra.net_worth import add_net_worth_tracking

app = FastAPI()

# Endpoints added, tracker auto-created
tracker = add_net_worth_tracking(app)
```
"""

from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query

from fin_infra.net_worth.ease import NetWorthTracker, easy_net_worth
from fin_infra.net_worth.models import (
    ConversationResponse,
    GoalProgressResponse,
    NetWorthResponse,
    SnapshotHistoryResponse,
)


def add_net_worth_tracking(
    app: FastAPI,
    tracker: NetWorthTracker | None = None,
    prefix: str = "/net-worth",
    include_in_schema: bool = True,
) -> NetWorthTracker:
    """
    Add net worth tracking endpoints to FastAPI app.

    **Example - With Tracker**:
    ```python
    from fastapi import FastAPI
    from fin_infra.banking import easy_banking
    from fin_infra.net_worth import easy_net_worth, add_net_worth_tracking

    app = FastAPI()

    # Create providers + tracker
    banking = easy_banking(provider="plaid")
    tracker = easy_net_worth(banking=banking)

    # Add endpoints
    add_net_worth_tracking(app, tracker=tracker)
    ```

    **Example - Auto-wired** (no providers yet):
    ```python
    from fastapi import FastAPI
    from fin_infra.net_worth import add_net_worth_tracking

    app = FastAPI()

    # Add endpoints (tracker created with defaults)
    tracker = add_net_worth_tracking(app)

    # Later: wire up providers
    from fin_infra.banking import easy_banking
    banking = easy_banking(provider="plaid")
    tracker.aggregator.banking_provider = banking
    ```

    Args:
        app: FastAPI application instance
        tracker: NetWorthTracker instance (optional, will create default)
        prefix: URL prefix for endpoints (default: "/net-worth")
        include_in_schema: Include in OpenAPI schema (default: True)

    Returns:
        NetWorthTracker instance (for programmatic access)

    **Endpoints Added**:
    - `GET {prefix}/current` - Current net worth (cached 1h)
    - `GET {prefix}/snapshots` - Historical snapshots
    - `GET {prefix}/breakdown` - Asset/liability breakdown
    - `POST {prefix}/snapshot` - Force snapshot creation

    **Authentication**:
    All endpoints require user authentication (svc-infra user_router).
    User ID extracted from JWT token automatically.
    """
    # Create default tracker if not provided
    if tracker is None:
        # For now, create empty tracker (providers will be wired later)
        # TODO: Auto-detect providers from app.state
        tracker = easy_net_worth(
            banking=None,  # Will be set later
            brokerage=None,
            crypto=None,
        )

    # Store tracker on app state for access in routes
    app.state.net_worth_tracker = tracker

    # Use svc-infra user_router for authentication (net worth is user-specific)
    from svc_infra.api.fastapi.dual.protected import user_router

    router = user_router(prefix=prefix, tags=["Net Worth"])

    @router.get(
        "/current",
        response_model=NetWorthResponse,
        summary="Get Current Net Worth",
        description="Calculate current net worth from all providers (cached 1h)",
    )
    async def get_current_net_worth(
        user_id: str = Query(..., description="User identifier"),
        access_token: str = Query(None, description="Provider access token"),
        force_refresh: bool = Query(False, description="Skip cache, recalculate"),
        include_breakdown: bool = Query(True, description="Include asset/liability details"),
    ) -> NetWorthResponse:
        """
        Get current net worth.

        **Example Request**:
        ```
        GET /net-worth/current?user_id=user_123&access_token=plaid_token_abc
        ```

        **Example Response**:
        ```json
        {
          "snapshot": {
            "id": "snapshot_abc123",
            "user_id": "user_123",
            "total_net_worth": 55000.0,
            "total_assets": 60000.0,
            "total_liabilities": 5000.0,
            ...
          },
          "asset_allocation": {
            "cash": 10000.0,
            "investments": 45000.0,
            ...
          },
          "processing_time_ms": 1250
        }
        ```
        """
        start_time = datetime.utcnow()

        try:
            # Calculate net worth
            snapshot = await tracker.calculate_net_worth(
                user_id=user_id,
                access_token=access_token,
            )

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Build response
            from fin_infra.net_worth.calculator import (
                calculate_asset_allocation,
                calculate_liability_breakdown,
            )

            # Get asset details from snapshot (stored in aggregator)
            # Persistence: Asset/liability details stored in snapshot JSON fields or separate tables.
            # Generate with: fin-infra scaffold net_worth --dest-dir app/models/
            # For now, create empty lists for testing/examples.
            asset_details = []
            liability_details = []

            # Calculate breakdowns
            asset_allocation = calculate_asset_allocation(asset_details)
            liability_breakdown = calculate_liability_breakdown(liability_details)

            return NetWorthResponse(
                snapshot=snapshot,
                asset_allocation=asset_allocation,
                liability_breakdown=liability_breakdown,
                asset_details=asset_details if include_breakdown else [],
                liability_details=liability_details if include_breakdown else [],
                processing_time_ms=int(processing_time),
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/snapshots",
        response_model=SnapshotHistoryResponse,
        summary="Get Historical Snapshots",
        description="Retrieve historical net worth snapshots for charting",
    )
    async def get_snapshots(
        user_id: str = Query(..., description="User identifier"),
        days: int = Query(90, ge=1, le=730, description="Look back N days (max 2 years)"),
        granularity: str = Query(
            "daily",
            pattern="^(daily|weekly|monthly)$",
            description="Snapshot granularity",
        ),
    ) -> SnapshotHistoryResponse:
        """
        Get historical snapshots.

        **Example Request**:
        ```
        GET /net-worth/snapshots?user_id=user_123&days=90&granularity=daily
        ```

        **Example Response**:
        ```json
        {
          "snapshots": [
            {"snapshot_date": "2025-11-06", "total_net_worth": 55000.0, ...},
            {"snapshot_date": "2025-11-05", "total_net_worth": 54500.0, ...},
            ...
          ],
          "count": 90,
          "start_date": "2025-08-08",
          "end_date": "2025-11-06"
        }
        ```
        """
        try:
            # Get snapshots from tracker
            snapshots = await tracker.get_snapshots(
                user_id=user_id,
                days=days,
                granularity=granularity,
            )

            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            return SnapshotHistoryResponse(
                snapshots=snapshots,
                count=len(snapshots),
                start_date=start_date,
                end_date=end_date,
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/breakdown",
        summary="Get Asset/Liability Breakdown",
        description="Get detailed asset and liability breakdown for pie charts",
    )
    async def get_breakdown(
        user_id: str = Query(..., description="User identifier"),
        access_token: str = Query(None, description="Provider access token"),
    ):
        """
        Get asset/liability breakdown.

        Returns simplified breakdown for visualization (pie charts).

        **Example Response**:
        ```json
        {
          "assets": {
            "cash": 10000.0,
            "investments": 45000.0,
            "crypto": 5000.0,
            "real_estate": 0.0,
            "vehicles": 0.0,
            "other": 0.0
          },
          "liabilities": {
            "credit_cards": 5000.0,
            "mortgages": 0.0,
            "auto_loans": 0.0,
            "student_loans": 0.0,
            "personal_loans": 0.0,
            "lines_of_credit": 0.0
          }
        }
        ```
        """
        try:
            # Get current net worth
            snapshot = await tracker.calculate_net_worth(
                user_id=user_id,
                access_token=access_token,
            )

            return {
                "assets": {
                    "cash": snapshot.cash,
                    "investments": snapshot.investments,
                    "crypto": snapshot.crypto,
                    "real_estate": snapshot.real_estate,
                    "vehicles": snapshot.vehicles,
                    "other": snapshot.other_assets,
                },
                "liabilities": {
                    "credit_cards": snapshot.credit_cards,
                    "mortgages": snapshot.mortgages,
                    "auto_loans": snapshot.auto_loans,
                    "student_loans": snapshot.student_loans,
                    "personal_loans": snapshot.personal_loans,
                    "lines_of_credit": snapshot.lines_of_credit,
                },
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
        "/snapshot",
        summary="Force Snapshot Creation",
        description="Manually create snapshot (admin only)",
    )
    async def force_snapshot(
        user_id: str = Query(..., description="User identifier"),
        access_token: str = Query(None, description="Provider access token"),
    ):
        """
        Force snapshot creation.

        Creates snapshot immediately (bypasses schedule).
        Useful for testing or manual triggers.

        **Example Request**:
        ```
        POST /net-worth/snapshot?user_id=user_123&access_token=plaid_token_abc
        ```

        **Example Response**:
        ```json
        {
          "message": "Snapshot created successfully",
          "snapshot_id": "snapshot_abc123",
          "net_worth": 55000.0
        }
        ```
        """
        try:
            # Create snapshot
            snapshot = await tracker.create_snapshot(
                user_id=user_id,
                access_token=access_token,
            )

            return {
                "message": "Snapshot created successfully",
                "snapshot_id": snapshot.id,
                "net_worth": snapshot.total_net_worth,
                "snapshot_date": snapshot.snapshot_date,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ===========================
    # V2 LLM Endpoints (Optional)
    # ===========================

    @router.get(
        "/insights",
        summary="Generate Financial Insights (V2)",
        description="LLM-generated insights: wealth trends, debt reduction, goals, asset allocation (cached 24h)",
    )
    async def get_insights(
        user_id: str = Query(..., description="User identifier"),
        type: str = Query(
            ...,
            description="Insight type: wealth_trends, debt_reduction, goal_recommendations, asset_allocation",
        ),
        access_token: str = Query(None, description="Provider access token"),
        days: int = Query(90, ge=7, le=365, description="Historical data period"),
    ):
        """
        Generate LLM-powered financial insights.

        **Requires**: enable_llm=True in easy_net_worth()

        **Example Request**:
        ```
        GET /net-worth/insights?user_id=user_123&type=wealth_trends&days=90
        ```

        **Example Response**:
        ```json
        {
          "trend": "improving",
          "trend_percentage": 12.5,
          "key_drivers": ["Investment growth", "Debt reduction"],
          "recommendations": ["Consider increasing 401k...", "Refinance high-interest debt"],
          "risk_factors": ["Variable income"],
          "confidence": 0.92
        }
        ```
        """
        # Check if LLM enabled
        if tracker.insights_generator is None:
            raise HTTPException(
                status_code=503,
                detail="LLM insights not enabled. Set enable_llm=True in easy_net_worth()",
            )

        try:
            # Get snapshots
            snapshots = await tracker.get_snapshots(user_id=user_id, days=days)

            if not snapshots:
                raise HTTPException(
                    status_code=404, detail="No snapshots found. Create at least 1 snapshot first."
                )

            # Generate insights based on type
            if type == "wealth_trends":
                insights = await tracker.insights_generator.analyze_wealth_trends(
                    snapshots=snapshots
                )
            elif type == "debt_reduction":
                insights = await tracker.insights_generator.generate_debt_reduction_plan(
                    snapshots=snapshots
                )
            elif type == "goal_recommendations":
                insights = await tracker.insights_generator.recommend_goals(snapshots=snapshots)
            elif type == "asset_allocation":
                insights = await tracker.insights_generator.suggest_asset_allocation(
                    snapshots=snapshots
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid insight type: {type}. Must be: wealth_trends, debt_reduction, goal_recommendations, asset_allocation",
                )

            return insights.model_dump()

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
        "/conversation",
        response_model=ConversationResponse,
        summary="Financial Planning Conversation (V2)",
        description="Multi-turn Q&A about financial planning (context from previous exchanges)",
    )
    async def ask_question(
        user_id: str = Query(..., description="User identifier"),
        question: str = Query(..., min_length=3, max_length=500, description="User question"),
        session_id: str | None = Query(None, description="Conversation session ID"),
        access_token: str | None = Query(None, description="Provider access token"),
    ) -> ConversationResponse:
        """
        Ask financial planning questions with multi-turn context.

        **Requires**: enable_llm=True in easy_net_worth()

        **Example Request**:
        ```
        POST /net-worth/conversation?user_id=user_123&question=How+can+I+save+more?
        ```

        **Example Response**:
        ```json
        {
          "answer": "Based on your current net worth of $55,000...",
          "follow_up_questions": [
            "Would you like me to create a savings plan?",
            "Have you considered automating your savings?"
          ],
          "confidence": 0.89,
          "sources": ["current_net_worth", "conversation_history"]
        }
        ```
        """
        # Check if LLM enabled
        if tracker.conversation is None:
            raise HTTPException(
                status_code=503,
                detail="LLM conversation not enabled. Set enable_llm=True in easy_net_worth()",
            )

        try:
            # Get current snapshot for context
            snapshot = await tracker.calculate_net_worth(user_id=user_id, access_token=access_token)

            # Get goals for context (if goal_tracker available)
            goals = []
            if tracker.goal_tracker:
                # TODO: Implement get_goals() method
                pass

            # Ask question with context
            response = await tracker.conversation.ask(
                user_id=user_id,
                question=question,
                session_id=session_id,
                current_net_worth=snapshot.total_net_worth,
                goals=goals,
            )

            # Convert to API response format
            return ConversationResponse(
                answer=response.answer,
                follow_up_questions=response.follow_up_questions,
                confidence=response.confidence,
                sources=response.sources,
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
        "/goals",
        summary="Create/Validate Financial Goal (V2)",
        description="LLM-validated goal creation with savings calculations",
    )
    async def create_goal(
        user_id: str = Query(..., description="User identifier"),
        goal_type: str = Query(
            ..., description="Goal type: retirement, home_purchase, debt_free, wealth_milestone"
        ),
        target_amount: float = Query(..., gt=0, description="Target amount"),
        target_date: str | None = Query(None, description="Target date (YYYY-MM-DD)"),
        target_age: int | None = Query(
            None, ge=18, le=120, description="Target age (for retirement)"
        ),
        current_age: int | None = Query(
            None, ge=18, le=120, description="Current age (for retirement)"
        ),
        access_token: str | None = Query(None, description="Provider access token"),
    ):
        """
        Create and validate financial goal with LLM.

        **Requires**: enable_llm=True in easy_net_worth()

        **Example Request**:
        ```
        POST /net-worth/goals?user_id=user_123&goal_type=retirement&target_amount=2000000&target_age=65&current_age=35
        ```

        **Example Response**:
        ```json
        {
          "is_realistic": true,
          "confidence": 0.87,
          "required_monthly_savings": 1500.0,
          "assumptions": ["7% annual return", "3% inflation"],
          "risks": ["Market volatility"],
          "recommendations": ["Max out 401k contributions", "Consider Roth IRA"]
        }
        ```
        """
        # Check if LLM enabled
        if tracker.goal_tracker is None:
            raise HTTPException(
                status_code=503,
                detail="LLM goal tracking not enabled. Set enable_llm=True in easy_net_worth()",
            )

        try:
            # Get current snapshot for context
            snapshot = await tracker.calculate_net_worth(user_id=user_id, access_token=access_token)

            # Build goal dict
            goal_data = {
                "type": goal_type,
                "target_amount": target_amount,
                "current_amount": snapshot.total_net_worth,
            }

            if target_date:
                goal_data["target_date"] = target_date
            if target_age:
                goal_data["target_age"] = target_age
            if current_age:
                goal_data["current_age"] = current_age

            # Validate goal with LLM
            validation = await tracker.goal_tracker.validate_goal_with_llm(
                goal=goal_data, current_snapshot=snapshot
            )

            return validation.model_dump()

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get(
        "/goals/{goal_id}/progress",
        response_model=GoalProgressResponse,
        summary="Get Goal Progress Report (V2)",
        description="Weekly progress report with LLM recommendations",
    )
    async def get_goal_progress(
        goal_id: str,
        user_id: str = Query(..., description="User identifier"),
        access_token: str | None = Query(None, description="Provider access token"),
    ) -> GoalProgressResponse:
        """
        Get goal progress with LLM recommendations.

        **Requires**: enable_llm=True in easy_net_worth()

        **Example Request**:
        ```
        GET /net-worth/goals/goal_abc123/progress?user_id=user_123
        ```

        **Example Response**:
        ```json
        {
          "goal_id": "goal_abc123",
          "progress_percentage": 45.0,
          "on_track": true,
          "required_monthly_savings": 1500.0,
          "actual_monthly_savings": 1650.0,
          "estimated_completion_date": "2055-01-15",
          "recommendations": ["You're ahead of schedule!", "Consider increasing..."]
        }
        ```
        """
        # Check if LLM enabled
        if tracker.goal_tracker is None:
            raise HTTPException(
                status_code=503,
                detail="LLM goal tracking not enabled. Set enable_llm=True in easy_net_worth()",
            )

        try:
            # Get current snapshot
            snapshot = await tracker.calculate_net_worth(user_id=user_id, access_token=access_token)

            # Get historical snapshots for progress tracking
            snapshots = await tracker.get_snapshots(user_id=user_id, days=90)

            # Persistence: Goal retrieval via scaffolded goals repository.
            # Generate with: fin-infra scaffold goals --dest-dir app/models/
            # See docs/persistence.md for goal tracking patterns.
            # For now, return mock data.
            raise HTTPException(
                status_code=501,
                detail="Goal progress tracking not fully implemented. Need goal persistence layer.",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Mount router
    app.include_router(router, include_in_schema=include_in_schema)

    # Scoped docs removed (per architectural decision)
    # All net worth endpoints appear in main /docs

    return tracker
