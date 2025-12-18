"""
FastAPI Integration for Goals Management

Provides REST API endpoints for comprehensive goal management:
- Full CRUD operations (create, read, update, delete)
- Milestone tracking and celebrations
- Funding allocation and management
- Progress monitoring and projections
- AI-powered goal validation

**Quick Start**:
```python
from fastapi import FastAPI
from fin_infra.goals import add_goals

app = FastAPI()

# Add all goal endpoints (one line!)
add_goals(app)
```

**Features**:
- svc-infra user_router integration (protected routes with auth)
- Scoped docs at /goals/docs (landing page card)
- Cache integration for expensive operations
- Webhook publishing for milestones
- Comprehensive CRUD + milestones + funding endpoints
"""

import logging
from datetime import datetime
from typing import Any, cast

from fastapi import Body, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from fin_infra.goals.funding import (
    get_goal_funding_sources,
    link_account_to_goal,
    remove_account_from_goal,
    update_account_allocation,
)
from fin_infra.goals.management import (
    create_goal,
    delete_goal,
    get_goal,
    get_goal_progress,
    list_goals,
    update_goal,
)
from fin_infra.goals.milestones import (
    add_milestone,
    check_milestones,
    get_milestone_progress,
)
from fin_infra.goals.models import GoalStatus

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def parse_iso_date(date_str: str | None) -> datetime | None:
    """Parse ISO date string to datetime object."""
    if date_str is None:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid date format: {date_str}. Expected ISO format (YYYY-MM-DD)")


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateGoalRequest(BaseModel):
    """Request body for creating a goal."""

    user_id: str = Field(..., description="User identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Goal name")
    goal_type: str = Field(..., description="Goal type (savings, debt, investment, etc.)")
    target_amount: float = Field(..., gt=0, description="Target amount")
    deadline: str | None = Field(None, description="Deadline (ISO date)")
    description: str | None = Field(None, description="Goal description")
    current_amount: float | None = Field(0.0, ge=0, description="Current amount")
    auto_contribute: bool | None = Field(False, description="Auto-contribute enabled")
    tags: list[str] | None = Field(None, description="Goal tags")


class UpdateGoalRequest(BaseModel):
    """Request body for updating a goal."""

    name: str | None = Field(None, min_length=1, max_length=200)
    target_amount: float | None = Field(None, gt=0)
    deadline: str | None = None
    description: str | None = None
    current_amount: float | None = Field(None, ge=0)
    status: GoalStatus | None = None
    auto_contribute: bool | None = None
    tags: list[str] | None = None


class AddMilestoneRequest(BaseModel):
    """Request body for adding a milestone."""

    amount: float = Field(..., gt=0, description="Milestone amount")
    description: str = Field(..., min_length=1, description="Milestone description")
    target_date: str | None = Field(None, description="Target date (ISO date)")


class LinkAccountRequest(BaseModel):
    """Request body for linking account to goal."""

    account_id: str = Field(..., description="Account identifier")
    allocation_percent: float = Field(..., gt=0, le=100, description="Allocation percentage")


class UpdateAllocationRequest(BaseModel):
    """Request body for updating allocation."""

    new_allocation_percent: float = Field(
        ..., gt=0, le=100, description="New allocation percentage"
    )


# ============================================================================
# FastAPI Integration
# ============================================================================


def add_goals(
    app: FastAPI,
    *,
    prefix: str = "/goals",
    include_in_schema: bool = True,
    visible_envs: list[str] | None = None,
) -> None:
    """
    Add goal management endpoints to FastAPI app.

    Integrates with svc-infra:
    - user_router: Protected routes with RequireUser dependency
    - add_prefixed_docs: Landing page card at /docs
    - Cache: For expensive progress calculations
    - Webhooks: For milestone notifications

    Args:
        app: FastAPI application instance
        prefix: URL prefix for goal routes (default: "/goals")
        include_in_schema: Include in OpenAPI schema (default: True)
        visible_envs: Show docs in these environments only (default: all)

    Side Effects:
        - Mounts goal router at {prefix}
        - Adds /docs card for "Goal Management"

    Example:
        >>> from fastapi import FastAPI
        >>> from fin_infra.goals import add_goals
        >>>
        >>> app = FastAPI()
        >>> add_goals(app)
        >>>
        >>> # Routes available:
        >>> # POST /goals - Create goal
        >>> # GET /goals - List goals
        >>> # GET /goals/{goal_id} - Get goal
        >>> # PATCH /goals/{goal_id} - Update goal
        >>> # DELETE /goals/{goal_id} - Delete goal
        >>> # GET /goals/{goal_id}/progress - Get progress
        >>> # POST /goals/{goal_id}/milestones - Add milestone
        >>> # GET /goals/{goal_id}/milestones - List milestones
        >>> # POST /goals/{goal_id}/funding - Link account
        >>> # GET /goals/{goal_id}/funding - List funding sources
        >>> # DELETE /goals/{goal_id}/funding/{account_id} - Remove account
        >>> # GET /goals/docs - Scoped Swagger UI
        >>> # GET /goals/openapi.json - Scoped OpenAPI schema
    """
    # Use svc-infra user_router for authentication (goals are user-specific)
    from svc_infra.api.fastapi.dual.protected import user_router

    router = user_router(prefix=prefix, tags=["Goal Management"])

    # ========================================================================
    # CRUD Endpoints
    # ========================================================================

    @router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
    async def create_goal_endpoint(body: CreateGoalRequest = Body(...)) -> dict:
        """
        Create a new financial goal.

        **Example Request**:
        ```json
        {
          "user_id": "user_123",
          "name": "Emergency Fund",
          "goal_type": "savings",
          "target_amount": 10000.0,
          "deadline": "2025-12-31",
          "description": "Build 6-month emergency fund"
        }
        ```

        **Example Response**:
        ```json
        {
          "id": "goal_user_123_1234567890",
          "user_id": "user_123",
          "name": "Emergency Fund",
          "type": "savings",
          "target_amount": 10000.0,
          "current_amount": 0.0,
          "status": "active",
          "deadline": "2025-12-31",
          "created_at": "2025-11-10T00:00:00Z"
        }
        ```
        """
        try:
            goal = create_goal(
                user_id=body.user_id,
                name=body.name,
                goal_type=body.goal_type,
                target_amount=body.target_amount,
                deadline=parse_iso_date(body.deadline),
                description=body.description,
                current_amount=body.current_amount or 0.0,
                auto_contribute=body.auto_contribute or False,
                tags=body.tags,
            )
            return goal
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.get("", response_model=list[dict])
    async def list_goals_endpoint(
        user_id: str | None = Query(
            None, description="User identifier (optional, returns all if not provided)"
        ),
        goal_type: str | None = Query(None, description="Filter by goal type"),
        status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    ) -> list[dict]:
        """
        List all goals for a user with optional filters.

        **Query Parameters**:
        - `user_id`: User identifier (optional - returns all goals if not provided)
        - `goal_type`: Filter by type (savings, debt, investment, etc.)
        - `status`: Filter by status (active, completed, paused, archived)

        **Example Request**:
        ```
        GET /goals?user_id=user_123&goal_type=savings&status=active
        GET /goals  (returns all goals)
        ```

        **Example Response**:
        ```json
        [
          {
            "id": "goal_user_123_1234567890",
            "user_id": "user_123",
            "name": "Emergency Fund",
            "type": "savings",
            "status": "active",
            "target_amount": 10000.0,
            "current_amount": 2500.0,
            "percent_complete": 25.0
          }
        ]
        ```
        """
        # If no user_id provided, return all goals
        if user_id:
            return list_goals(user_id=user_id, goal_type=goal_type, status=status_filter)
        else:
            # Return all goals with optional type/status filters
            from fin_infra.goals.management import _GOALS_STORE

            results = []
            for goal in _GOALS_STORE.values():
                if goal_type and goal["type"] != goal_type:
                    continue
                if status_filter and goal["status"] != status_filter:
                    continue
                results.append(goal)
            return results

    @router.get("/{goal_id}", response_model=dict)
    async def get_goal_endpoint(goal_id: str) -> dict:
        """
        Get a specific goal by ID.

        **Example Response**:
        ```json
        {
          "id": "goal_user_123_1234567890",
          "user_id": "user_123",
          "name": "Emergency Fund",
          "type": "savings",
          "target_amount": 10000.0,
          "current_amount": 2500.0,
          "status": "active",
          "deadline": "2025-12-31",
          "milestones": [...],
          "funding_sources": [...]
        }
        ```
        """
        try:
            return get_goal(goal_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found"
            )

    @router.patch("/{goal_id}", response_model=dict)
    async def update_goal_endpoint(goal_id: str, body: UpdateGoalRequest = Body(...)) -> dict:
        """
        Update a goal's fields.

        **Example Request**:
        ```json
        {
          "current_amount": 3000.0,
          "status": "active"
        }
        ```

        **Example Response**:
        ```json
        {
          "id": "goal_user_123_1234567890",
          "current_amount": 3000.0,
          "status": "active",
          "updated_at": "2025-11-10T00:00:00Z"
        }
        ```
        """
        try:
            updates = body.model_dump(exclude_unset=True)
            return update_goal(goal_id, updates)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found"
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_goal_endpoint(goal_id: str) -> None:
        """
        Delete a goal.

        **Response**: 204 No Content on success, 404 if not found.
        """
        try:
            delete_goal(goal_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found"
            )

    # ========================================================================
    # Progress Endpoint
    # ========================================================================

    @router.get("/{goal_id}/progress", response_model=dict)
    async def get_goal_progress_endpoint(goal_id: str) -> dict:
        """
        Get goal progress with projections and tracking metrics.

        **Example Response**:
        ```json
        {
          "goal_id": "goal_user_123_1234567890",
          "current_amount": 2500.0,
          "target_amount": 10000.0,
          "percent_complete": 25.0,
          "monthly_contribution_actual": 500.0,
          "monthly_contribution_target": 833.33,
          "projected_completion_date": "2026-06-10",
          "on_track": false,
          "milestones_reached": [...]
        }
        ```
        """
        try:
            return get_goal_progress(goal_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found"
            )

    # ========================================================================
    # Milestone Endpoints
    # ========================================================================

    @router.post("/{goal_id}/milestones", response_model=dict, status_code=status.HTTP_201_CREATED)
    async def add_milestone_endpoint(goal_id: str, body: AddMilestoneRequest = Body(...)) -> dict:
        """
        Add a milestone to a goal.

        **Example Request**:
        ```json
        {
          "amount": 5000.0,
          "description": "Halfway to target!",
          "target_date": "2026-01-01"
        }
        ```

        **Example Response**:
        ```json
        {
          "amount": 5000.0,
          "description": "Halfway to target!",
          "target_date": "2026-01-01",
          "reached": false,
          "reached_date": null
        }
        ```
        """
        try:
            milestone = add_milestone(
                goal_id=goal_id,
                amount=body.amount,
                description=body.description,
                target_date=parse_iso_date(body.target_date),
            )
            return milestone
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found"
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.get("/{goal_id}/milestones", response_model=list[dict])
    async def list_milestones_endpoint(goal_id: str) -> list[dict]:
        """
        List all milestones for a goal.

        **Example Response**:
        ```json
        [
          {
            "amount": 2500.0,
            "description": "25% complete!",
            "reached": true,
            "reached_date": "2025-10-01T00:00:00Z"
          },
          {
            "amount": 5000.0,
            "description": "Halfway there!",
            "reached": false,
            "reached_date": null
          }
        ]
        ```
        """
        try:
            # Get all milestones from the goal (check_milestones only returns newly reached ones)
            goal = get_goal(goal_id)
            milestones = goal.get("milestones", [])
            return cast("list[dict[Any, Any]]", milestones)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found"
            )

    @router.get("/{goal_id}/milestones/progress", response_model=dict)
    async def get_milestone_progress_endpoint(goal_id: str) -> dict:
        """
        Get milestone progress statistics.

        **Example Response**:
        ```json
        {
          "total_milestones": 4,
          "reached_count": 1,
          "remaining_count": 3,
          "next_milestone_amount": 5000.0,
          "next_milestone_description": "Halfway there!"
        }
        ```
        """
        try:
            # Check and update any newly reached milestones first
            check_milestones(goal_id)
            # Then return progress stats
            return get_milestone_progress(goal_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found"
            )

    # ========================================================================
    # Funding Endpoints
    # ========================================================================

    @router.post("/{goal_id}/funding", response_model=dict, status_code=status.HTTP_201_CREATED)
    async def link_account_endpoint(goal_id: str, body: LinkAccountRequest = Body(...)) -> dict:
        """
        Link an account to fund a goal.

        **Example Request**:
        ```json
        {
          "account_id": "checking_001",
          "allocation_percent": 50.0
        }
        ```

        **Example Response**:
        ```json
        {
          "goal_id": "goal_user_123_1234567890",
          "account_id": "checking_001",
          "allocation_percent": 50.0,
          "account_name": null
        }
        ```
        """
        try:
            source = link_account_to_goal(
                goal_id=goal_id,
                account_id=body.account_id,
                allocation_percent=body.allocation_percent,
            )
            return source.model_dump()
        except KeyError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.get("/{goal_id}/funding", response_model=list[dict])
    async def list_funding_sources_endpoint(goal_id: str) -> list[dict]:
        """
        List all funding sources for a goal.

        **Example Response**:
        ```json
        [
          {
            "goal_id": "goal_user_123_1234567890",
            "account_id": "checking_001",
            "allocation_percent": 50.0,
            "account_name": "Chase Checking"
          },
          {
            "goal_id": "goal_user_123_1234567890",
            "account_id": "savings_001",
            "allocation_percent": 30.0,
            "account_name": "Ally Savings"
          }
        ]
        ```
        """
        try:
            sources = get_goal_funding_sources(goal_id)
            return [s.model_dump() for s in sources]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Goal {goal_id} not found"
            )

    @router.patch("/{goal_id}/funding/{account_id}", response_model=dict)
    async def update_allocation_endpoint(
        goal_id: str, account_id: str, body: UpdateAllocationRequest = Body(...)
    ) -> dict:
        """
        Update allocation percentage for an existing account-goal link.

        **Example Request**:
        ```json
        {
          "new_allocation_percent": 70.0
        }
        ```
        """
        try:
            source = update_account_allocation(
                goal_id=goal_id,
                account_id=account_id,
                new_allocation_percent=body.new_allocation_percent,
            )
            return source.model_dump()
        except KeyError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.delete("/{goal_id}/funding/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def remove_account_endpoint(goal_id: str, account_id: str) -> None:
        """
        Remove an account from funding a goal.

        **Response**: 204 No Content on success, 404 if not found.
        """
        try:
            remove_account_from_goal(goal_id, account_id)
        except KeyError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Mount router
    app.include_router(router, include_in_schema=include_in_schema)

    logger.info(f"Goal management routes mounted at {prefix}")


__all__ = ["add_goals"]
