"""Unit tests for add_budgets() FastAPI helper.

Tests all 8 REST endpoints with mocked BudgetTracker.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fin_infra.budgets.add import add_budgets
from fin_infra.budgets.models import (
    Budget,
    BudgetCategory,
    BudgetPeriod,
    BudgetProgress,
    BudgetType,
)
from fin_infra.budgets.tracker import BudgetTracker


@pytest.fixture
def mock_tracker():
    """Create mock BudgetTracker."""
    tracker = MagicMock(spec=BudgetTracker)

    # Mock create_budget
    tracker.create_budget = AsyncMock(
        return_value=Budget(
            id="bud_123",
            user_id="user_123",
            name="November 2025",
            type=BudgetType.PERSONAL,
            period=BudgetPeriod.MONTHLY,
            categories={"Groceries": 600.0, "Restaurants": 200.0},
            start_date=datetime(2025, 11, 1),
            end_date=datetime(2025, 11, 30),
        )
    )

    # Mock get_budgets
    tracker.get_budgets = AsyncMock(
        return_value=[
            Budget(
                id="bud_123",
                user_id="user_123",
                name="November 2025",
                type=BudgetType.PERSONAL,
                period=BudgetPeriod.MONTHLY,
                categories={"Groceries": 600.0},
                start_date=datetime(2025, 11, 1),
                end_date=datetime(2025, 11, 30),
            )
        ]
    )

    # Mock get_budget
    tracker.get_budget = AsyncMock(
        return_value=Budget(
            id="bud_123",
            user_id="user_123",
            name="November 2025",
            type=BudgetType.PERSONAL,
            period=BudgetPeriod.MONTHLY,
            categories={"Groceries": 600.0},
            start_date=datetime(2025, 11, 1),
            end_date=datetime(2025, 11, 30),
        )
    )

    # Mock update_budget
    tracker.update_budget = AsyncMock(
        return_value=Budget(
            id="bud_123",
            user_id="user_123",
            name="Updated Budget",
            type=BudgetType.PERSONAL,
            period=BudgetPeriod.MONTHLY,
            categories={"Groceries": 700.0},
            start_date=datetime(2025, 11, 1),
            end_date=datetime(2025, 11, 30),
        )
    )

    # Mock delete_budget
    tracker.delete_budget = AsyncMock(return_value=None)

    # Mock get_budget_progress
    tracker.get_budget_progress = AsyncMock(
        return_value=BudgetProgress(
            budget_id="bud_123",
            current_period="November 2025",
            categories=[
                BudgetCategory(
                    category_name="Groceries",
                    budgeted_amount=600.0,
                    spent_amount=425.50,
                    remaining_amount=174.50,
                    percent_used=70.92,
                )
            ],
            total_budgeted=600.0,
            total_spent=425.50,
            total_remaining=174.50,
            percent_used=70.92,
            period_days_elapsed=15,
            period_days_total=30,
        )
    )

    return tracker


@pytest.fixture
def app_with_budgets(mock_tracker):
    """Create FastAPI app with budget endpoints."""
    app = FastAPI()
    add_budgets(app, tracker=mock_tracker)
    return app


@pytest.fixture
def client(app_with_budgets):
    """Create test client."""
    return TestClient(app_with_budgets)


class TestCreateBudget:
    """Test POST /budgets endpoint."""

    def test_create_budget_success(self, client, mock_tracker):
        """Test creating a budget successfully."""
        response = client.post(
            "/budgets",
            json={
                "user_id": "user_123",
                "name": "November 2025",
                "type": "personal",
                "period": "monthly",
                "categories": {"Groceries": 600.0, "Restaurants": 200.0},
                "rollover_enabled": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "bud_123"
        assert data["user_id"] == "user_123"
        assert data["name"] == "November 2025"
        assert data["type"] == "personal"

        # Verify tracker called
        mock_tracker.create_budget.assert_called_once()

    def test_create_budget_validation_error(self, client, mock_tracker):
        """Test create budget with validation error."""
        mock_tracker.create_budget.side_effect = ValueError("Invalid budget data")

        response = client.post(
            "/budgets",
            json={
                "user_id": "user_123",
                "name": "Test",
                "type": "personal",
                "period": "monthly",
                "categories": {},
            },
        )

        assert response.status_code == 400
        assert "Invalid budget data" in response.json()["detail"]


class TestListBudgets:
    """Test GET /budgets endpoint."""

    def test_list_budgets_success(self, client, mock_tracker):
        """Test listing budgets successfully."""
        response = client.get("/budgets?user_id=user_123")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "bud_123"

        # Verify tracker called
        mock_tracker.get_budgets.assert_called_once()

    def test_list_budgets_with_type_filter(self, client, mock_tracker):
        """Test listing budgets with type filter."""
        response = client.get("/budgets?user_id=user_123&type=personal")

        assert response.status_code == 200
        mock_tracker.get_budgets.assert_called_once()
        call_kwargs = mock_tracker.get_budgets.call_args.kwargs
        assert call_kwargs["type"] == BudgetType.PERSONAL


class TestGetBudget:
    """Test GET /budgets/{budget_id} endpoint."""

    def test_get_budget_success(self, client, mock_tracker):
        """Test getting a budget successfully."""
        response = client.get("/budgets/bud_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "bud_123"
        assert data["name"] == "November 2025"

        mock_tracker.get_budget.assert_called_once_with(budget_id="bud_123")

    def test_get_budget_not_found(self, client, mock_tracker):
        """Test getting non-existent budget."""
        mock_tracker.get_budget.side_effect = ValueError("Budget not found")

        response = client.get("/budgets/bud_999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUpdateBudget:
    """Test PATCH /budgets/{budget_id} endpoint."""

    def test_update_budget_success(self, client, mock_tracker):
        """Test updating a budget successfully."""
        response = client.patch(
            "/budgets/bud_123",
            json={
                "name": "Updated Budget",
                "categories": {"Groceries": 700.0},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Budget"

        mock_tracker.update_budget.assert_called_once()
        call_kwargs = mock_tracker.update_budget.call_args.kwargs
        assert call_kwargs["budget_id"] == "bud_123"
        assert "name" in call_kwargs["updates"]
        assert "categories" in call_kwargs["updates"]

    def test_update_budget_no_updates(self, client, mock_tracker):
        """Test update with no fields provided."""
        response = client.patch("/budgets/bud_123", json={})

        assert response.status_code == 400
        assert "No updates provided" in response.json()["detail"]

    def test_update_budget_not_found(self, client, mock_tracker):
        """Test updating non-existent budget."""
        mock_tracker.update_budget.side_effect = ValueError("Budget not found")

        response = client.patch(
            "/budgets/bud_999",
            json={"name": "Updated"},
        )

        assert response.status_code == 404


class TestDeleteBudget:
    """Test DELETE /budgets/{budget_id} endpoint."""

    def test_delete_budget_success(self, client, mock_tracker):
        """Test deleting a budget successfully."""
        response = client.delete("/budgets/bud_123")

        assert response.status_code == 204
        assert response.content == b""

        mock_tracker.delete_budget.assert_called_once_with(budget_id="bud_123")

    def test_delete_budget_not_found(self, client, mock_tracker):
        """Test deleting non-existent budget."""
        mock_tracker.delete_budget.side_effect = ValueError("Budget not found")

        response = client.delete("/budgets/bud_999")

        assert response.status_code == 404


class TestGetBudgetProgress:
    """Test GET /budgets/{budget_id}/progress endpoint."""

    def test_get_progress_success(self, client, mock_tracker):
        """Test getting budget progress successfully."""
        response = client.get("/budgets/bud_123/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["budget_id"] == "bud_123"
        assert data["current_period"] == "November 2025"
        assert len(data["categories"]) == 1
        assert data["categories"][0]["category_name"] == "Groceries"
        assert data["total_budgeted"] == 600.0
        assert data["total_spent"] == 425.50

        mock_tracker.get_budget_progress.assert_called_once_with(budget_id="bud_123")

    def test_get_progress_not_found(self, client, mock_tracker):
        """Test getting progress for non-existent budget."""
        mock_tracker.get_budget_progress.side_effect = ValueError("Budget not found")

        response = client.get("/budgets/bud_999/progress")

        assert response.status_code == 404


class TestListTemplates:
    """Test GET /budgets/templates/list endpoint."""

    @patch("fin_infra.budgets.add.list_templates")
    def test_list_templates_success(self, mock_list_templates, client):
        """Test listing budget templates successfully."""
        mock_list_templates.return_value = {
            "50_30_20": {
                "name": "50/30/20 Rule",
                "description": "50% needs, 30% wants, 20% savings",
                "type": "personal",
                "period": "monthly",
                "categories": {"Housing": 25.0, "Groceries": 10.0},
            }
        }

        response = client.get("/budgets/templates/list")

        assert response.status_code == 200
        data = response.json()
        assert "50_30_20" in data
        assert data["50_30_20"]["name"] == "50/30/20 Rule"

        mock_list_templates.assert_called_once()


class TestCreateFromTemplate:
    """Test POST /budgets/from-template endpoint."""

    @patch("fin_infra.budgets.add.apply_template")
    def test_create_from_template_success(self, mock_apply_template, client, mock_tracker):
        """Test creating budget from template successfully."""
        mock_apply_template.return_value = Budget(
            id="bud_456",
            user_id="user_123",
            name="50/30/20 Rule - November 2025",
            type=BudgetType.PERSONAL,
            period=BudgetPeriod.MONTHLY,
            categories={"Housing": 1250.0, "Groceries": 500.0},
            start_date=datetime(2025, 11, 1),
            end_date=datetime(2025, 11, 30),
        )

        response = client.post(
            "/budgets/from-template",
            json={
                "user_id": "user_123",
                "template_name": "50_30_20",
                "total_income": 5000.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "bud_456"
        assert data["categories"]["Housing"] == 1250.0

        mock_apply_template.assert_called_once()

    @patch("fin_infra.budgets.add.apply_template")
    def test_create_from_template_invalid(self, mock_apply_template, client):
        """Test creating from invalid template."""
        mock_apply_template.side_effect = ValueError("Template 'invalid' not found")

        response = client.post(
            "/budgets/from-template",
            json={
                "user_id": "user_123",
                "template_name": "invalid",
                "total_income": 5000.0,
            },
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()


class TestAddBudgetsFunction:
    """Test add_budgets() setup function."""

    @patch("fin_infra.budgets.add.easy_budgets")
    def test_add_budgets_creates_tracker(self, mock_easy_budgets):
        """Test add_budgets() creates tracker if not provided."""
        mock_tracker = MagicMock(spec=BudgetTracker)
        mock_easy_budgets.return_value = mock_tracker

        app = FastAPI()
        result = add_budgets(app, db_url="postgresql+asyncpg://localhost/db")

        # Verify easy_budgets called with db_url
        mock_easy_budgets.assert_called_once_with(db_url="postgresql+asyncpg://localhost/db")

        # Verify tracker stored on app.state
        assert app.state.budget_tracker == mock_tracker

        # Verify tracker returned
        assert result == mock_tracker

    def test_add_budgets_uses_provided_tracker(self, mock_tracker):
        """Test add_budgets() uses provided tracker."""
        app = FastAPI()
        result = add_budgets(app, tracker=mock_tracker)

        # Verify tracker stored on app.state
        assert app.state.budget_tracker == mock_tracker

        # Verify tracker returned
        assert result == mock_tracker

    def test_add_budgets_mounts_routes(self, mock_tracker):
        """Test add_budgets() mounts all routes."""
        app = FastAPI()
        add_budgets(app, tracker=mock_tracker)

        # Verify routes exist
        routes = [route.path for route in app.routes]
        assert "/budgets" in routes or any("/budgets" in r for r in routes)

    @patch("svc_infra.api.fastapi.docs.scoped.add_prefixed_docs")
    def test_add_budgets_registers_docs(self, mock_add_docs, mock_tracker):
        """Test add_budgets() registers scoped docs."""
        app = FastAPI()
        add_budgets(app, tracker=mock_tracker)

        # Verify add_prefixed_docs was called with correct args
        mock_add_docs.assert_called_once()
        call_args = mock_add_docs.call_args
        assert call_args.kwargs["prefix"] == "/budgets"
        assert call_args.kwargs["title"] == "Budget Management"


class TestIntegration:
    """Integration tests for full budget workflow."""

    @patch("fin_infra.budgets.add.easy_budgets")
    def test_full_budget_workflow(self, mock_easy_budgets, mock_tracker):
        """Test complete budget workflow from creation to deletion."""
        mock_easy_budgets.return_value = mock_tracker

        # Setup app
        app = FastAPI()
        add_budgets(app, db_url="sqlite+aiosqlite:///test.db")
        client = TestClient(app)

        # Step 1: List templates
        with patch("fin_infra.budgets.add.list_templates") as mock_list:
            mock_list.return_value = {"50_30_20": {"name": "50/30/20 Rule"}}
            response = client.get("/budgets/templates/list")
            assert response.status_code == 200

        # Step 2: Create from template
        with patch("fin_infra.budgets.add.apply_template") as mock_apply:
            mock_apply.return_value = Budget(
                id="bud_new",
                user_id="user_123",
                name="My Budget",
                type=BudgetType.PERSONAL,
                period=BudgetPeriod.MONTHLY,
                categories={"Food": 500.0},
                start_date=datetime(2025, 11, 1),
                end_date=datetime(2025, 11, 30),
            )
            response = client.post(
                "/budgets/from-template",
                json={
                    "user_id": "user_123",
                    "template_name": "50_30_20",
                    "total_income": 5000.0,
                },
            )
            assert response.status_code == 200

        # Step 3: Get budget
        response = client.get("/budgets/bud_123")
        assert response.status_code == 200

        # Step 4: Get progress
        response = client.get("/budgets/bud_123/progress")
        assert response.status_code == 200

        # Step 5: Update budget
        response = client.patch(
            "/budgets/bud_123",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200

        # Step 6: Delete budget
        response = client.delete("/budgets/bud_123")
        assert response.status_code == 204
