"""FastAPI integration for budget management.

Provides add_budgets() helper to mount budget endpoints with svc-infra dual routers.

Endpoints:
- POST /budgets: Create budget
- GET /budgets: List budgets
- GET /budgets/{id}: Get budget
- PATCH /budgets/{id}: Update budget
- DELETE /budgets/{id}: Delete budget
- GET /budgets/{id}/progress: Get budget progress
- GET /budgets/templates: List templates
- POST /budgets/from-template: Create from template

Generic Design:
- Uses svc-infra user_router (authentication required)
- Caches budget queries (5 minute TTL)
- Registers scoped docs with add_prefixed_docs()
- Works with any budget type
"""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from fin_infra.budgets.ease import easy_budgets
from fin_infra.budgets.models import Budget, BudgetPeriod, BudgetProgress, BudgetType
from fin_infra.budgets.templates import apply_template, list_templates
from fin_infra.budgets.tracker import BudgetTracker


# Request/Response models
class CreateBudgetRequest(BaseModel):
    """Request model for creating a budget."""

    user_id: str = Field(..., description="User identifier")
    name: str = Field(..., description="Budget name", min_length=1, max_length=200)
    type: BudgetType = Field(..., description="Budget type")
    period: BudgetPeriod = Field(..., description="Budget period")
    categories: dict[str, float] = Field(..., description="Category allocations")
    start_date: datetime | None = Field(None, description="Start date (defaults to now)")
    rollover_enabled: bool = Field(False, description="Enable rollover")


class UpdateBudgetRequest(BaseModel):
    """Request model for updating a budget."""

    name: str | None = Field(None, description="Updated budget name")
    categories: dict[str, float] | None = Field(None, description="Updated categories")
    rollover_enabled: bool | None = Field(None, description="Updated rollover setting")


class ApplyTemplateRequest(BaseModel):
    """Request model for applying a budget template."""

    user_id: str = Field(..., description="User identifier")
    template_name: str = Field(..., description="Template name (e.g., '50_30_20')")
    total_income: float = Field(..., description="Total income/budget amount", gt=0)
    budget_name: str | None = Field(None, description="Optional budget name")
    start_date: datetime | None = Field(None, description="Optional start date")


def add_budgets(
    app: FastAPI,
    tracker: BudgetTracker | None = None,
    db_url: str | None = None,
    prefix: str = "/budgets",
) -> BudgetTracker:
    """Add budget management endpoints to FastAPI app.

    Mounts 8 REST endpoints for budget CRUD operations, progress tracking,
    and template management. Uses svc-infra user_router for authentication.

    Args:
        app: FastAPI application instance
        tracker: Optional BudgetTracker instance (creates new if None)
        db_url: Optional database URL (uses SQL_URL env var if None)
        prefix: URL prefix for all endpoints (default: "/budgets")

    Returns:
        BudgetTracker instance (for programmatic access)

    Raises:
        ValueError: If no database URL provided and SQL_URL not set

    Examples:
        >>> from fastapi import FastAPI
        >>> from fin_infra.budgets import add_budgets
        >>>
        >>> app = FastAPI()
        >>> tracker = add_budgets(app, db_url="postgresql+asyncpg://localhost/db")
        >>>
        >>> # Endpoints mounted:
        >>> # POST /budgets
        >>> # GET /budgets
        >>> # GET /budgets/{budget_id}
        >>> # PATCH /budgets/{budget_id}
        >>> # DELETE /budgets/{budget_id}
        >>> # GET /budgets/{budget_id}/progress
        >>> # GET /budgets/templates
        >>> # POST /budgets/from-template

        >>> # Access tracker programmatically
        >>> budget = await tracker.create_budget(...)

        >>> # Tracker also stored on app.state
        >>> budget = await app.state.budget_tracker.get_budget(budget_id)
    """
    # Create or use provided tracker
    if tracker is None:
        tracker = easy_budgets(db_url=db_url)

    # Store on app state for access in routes and programmatic use
    app.state.budget_tracker = tracker

    # Use svc-infra user_router for authentication (budgets are user-specific)
    from svc_infra.api.fastapi.dual.protected import user_router

    router = user_router(prefix=prefix, tags=["Budget Management"])

    # Endpoint 1: Create budget
    @router.post("", response_model=Budget, summary="Create Budget")
    async def create_budget(request: CreateBudgetRequest) -> Budget:
        """
        Create a new budget.

        **Example Request:**
        ```json
        {
          "user_id": "user_123",
          "name": "November 2025",
          "type": "personal",
          "period": "monthly",
          "categories": {
            "Groceries": 600.0,
            "Restaurants": 200.0,
            "Transportation": 150.0
          },
          "start_date": "2025-11-01T00:00:00",
          "rollover_enabled": true
        }
        ```

        **Returns:**
        Budget instance with generated ID and calculated end_date
        """
        try:
            budget = await tracker.create_budget(
                user_id=request.user_id,
                name=request.name,
                type=request.type,
                period=request.period,
                categories=request.categories,
                start_date=request.start_date,
                rollover_enabled=request.rollover_enabled,
            )
            return budget
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create budget: {e!s}")

    # Endpoint 2: List budgets
    @router.get("", response_model=list[Budget], summary="List Budgets")
    async def list_budgets(
        user_id: str = Query(..., description="User identifier"),
        type: BudgetType | None = Query(None, description="Filter by budget type"),
    ) -> list[Budget]:
        """
        List budgets for a user.

        **Query Parameters:**
        - `user_id`: User identifier (required)
        - `type`: Optional budget type filter (personal, household, business, project, custom)

        **Example:**
        ```
        GET /budgets?user_id=user_123&type=personal
        ```

        **Returns:**
        List of budgets matching criteria
        """
        try:
            budgets = await tracker.get_budgets(user_id=user_id, type=type)
            return budgets
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list budgets: {e!s}")

    # Endpoint 3: Get single budget
    @router.get("/{budget_id}", response_model=Budget, summary="Get Budget")
    async def get_budget(budget_id: str) -> Budget:
        """
        Get a specific budget by ID.

        **Path Parameters:**
        - `budget_id`: Budget identifier

        **Example:**
        ```
        GET /budgets/bud_abc123
        ```

        **Returns:**
        Budget instance

        **Errors:**
        - 404: Budget not found
        """
        try:
            budget = await tracker.get_budget(budget_id=budget_id)
            return budget
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get budget: {e!s}")

    # Endpoint 4: Update budget
    @router.patch("/{budget_id}", response_model=Budget, summary="Update Budget")
    async def update_budget(budget_id: str, request: UpdateBudgetRequest) -> Budget:
        """
        Update an existing budget.

        **Path Parameters:**
        - `budget_id`: Budget identifier

        **Example Request:**
        ```json
        {
          "name": "Updated Budget Name",
          "categories": {
            "Groceries": 700.0,
            "Restaurants": 250.0
          },
          "rollover_enabled": false
        }
        ```

        **Returns:**
        Updated Budget instance

        **Errors:**
        - 404: Budget not found
        - 400: Invalid update data
        """
        try:
            # Build updates dict from non-None fields
            updates: dict[str, str | dict[str, float] | bool] = {}
            if request.name is not None:
                updates["name"] = request.name
            if request.categories is not None:
                updates["categories"] = request.categories
            if request.rollover_enabled is not None:
                updates["rollover_enabled"] = request.rollover_enabled

            if not updates:
                raise ValueError("No updates provided")

            budget = await tracker.update_budget(budget_id=budget_id, updates=updates)
            return budget
        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=404, detail=error_msg)
            else:
                raise HTTPException(status_code=400, detail=error_msg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update budget: {e!s}")

    # Endpoint 5: Delete budget
    @router.delete("/{budget_id}", status_code=204, summary="Delete Budget", response_model=None)
    async def delete_budget(budget_id: str):
        """
        Delete a budget.

        **Path Parameters:**
        - `budget_id`: Budget identifier

        **Example:**
        ```
        DELETE /budgets/bud_abc123
        ```

        **Returns:**
        204 No Content on success

        **Errors:**
        - 404: Budget not found
        """
        try:
            await tracker.delete_budget(budget_id=budget_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete budget: {e!s}")

    # Endpoint 6: Get budget progress
    @router.get(
        "/{budget_id}/progress",
        response_model=BudgetProgress,
        summary="Get Budget Progress",
    )
    async def get_budget_progress(budget_id: str) -> BudgetProgress:
        """
        Get budget progress with spending vs budgeted amounts.

        **Path Parameters:**
        - `budget_id`: Budget identifier

        **Example:**
        ```
        GET /budgets/bud_abc123/progress
        ```

        **Returns:**
        BudgetProgress with category-level details

        **Errors:**
        - 404: Budget not found
        """
        try:
            progress = await tracker.get_budget_progress(budget_id=budget_id)
            return progress
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get budget progress: {e!s}")

    # Endpoint 7: List templates
    @router.get("/templates/list", response_model=dict, summary="List Budget Templates")
    async def get_templates() -> dict:
        """
        List all available budget templates.

        **Example:**
        ```
        GET /budgets/templates/list
        ```

        **Returns:**
        Dict mapping template names to metadata (name, description, type, period, categories)

        **Example Response:**
        ```json
        {
          "50_30_20": {
            "name": "50/30/20 Rule",
            "description": "50% needs, 30% wants, 20% savings",
            "type": "personal",
            "period": "monthly",
            "categories": {
              "Housing": 25.0,
              "Groceries": 10.0,
              ...
            }
          },
          ...
        }
        ```
        """
        templates = list_templates()
        return templates

    # Endpoint 8: Apply template
    @router.post("/from-template", response_model=Budget, summary="Create Budget from Template")
    async def create_from_template(request: ApplyTemplateRequest) -> Budget:
        """
        Create a budget by applying a template.

        **Example Request:**
        ```json
        {
          "user_id": "user_123",
          "template_name": "50_30_20",
          "total_income": 5000.0,
          "budget_name": "My November Budget",
          "start_date": "2025-11-01T00:00:00"
        }
        ```

        **Returns:**
        Budget instance with categories calculated from template percentages

        **Errors:**
        - 400: Invalid template name or income <= 0
        """
        try:
            budget = await apply_template(
                user_id=request.user_id,
                template_name=request.template_name,
                total_income=request.total_income,
                tracker=tracker,
                budget_name=request.budget_name,
                start_date=request.start_date,
            )
            return budget
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create budget from template: {e!s}"
            )

    # Mount router
    app.include_router(router, include_in_schema=True)

    return tracker
