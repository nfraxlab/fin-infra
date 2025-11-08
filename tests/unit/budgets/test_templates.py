"""Unit tests for budget templates.

Tests pre-built templates, apply_template(), custom templates, and validation.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from fin_infra.budgets.models import Budget, BudgetPeriod, BudgetType
from fin_infra.budgets.templates import (
    TEMPLATES,
    BudgetTemplate,
    apply_template,
    get_custom_templates,
    list_templates,
    save_custom_template,
)


class TestBudgetTemplate:
    """Test BudgetTemplate class initialization and validation."""

    def test_init_valid_template(self):
        """Test creating a valid budget template."""
        template = BudgetTemplate(
            name="Test Template",
            description="Test description",
            budget_type=BudgetType.PERSONAL,
            period=BudgetPeriod.MONTHLY,
            categories={"Food": 50.0, "Housing": 30.0, "Other": 20.0},
        )

        assert template.name == "Test Template"
        assert template.description == "Test description"
        assert template.budget_type == BudgetType.PERSONAL
        assert template.period == BudgetPeriod.MONTHLY
        assert template.categories == {"Food": 50.0, "Housing": 30.0, "Other": 20.0}

    def test_init_validates_total_percentage(self):
        """Test template validation requires categories sum to 100%."""
        with pytest.raises(ValueError, match="Category percentages must sum to 100"):
            BudgetTemplate(
                name="Invalid",
                description="Bad percentages",
                budget_type=BudgetType.PERSONAL,
                period=BudgetPeriod.MONTHLY,
                categories={"Food": 50.0, "Housing": 30.0},  # Only 80%
            )

    def test_init_allows_float_tolerance(self):
        """Test template allows 0.1% float tolerance."""
        # Should not raise (99.95% rounds to ~100%)
        template = BudgetTemplate(
            name="Float Test",
            description="Float tolerance",
            budget_type=BudgetType.PERSONAL,
            period=BudgetPeriod.MONTHLY,
            categories={"Food": 33.33, "Housing": 33.33, "Other": 33.34},  # 100.00%
        )
        assert template is not None

    def test_init_requires_categories(self):
        """Test template requires at least one category."""
        with pytest.raises(ValueError, match="Template must have at least one category"):
            BudgetTemplate(
                name="Empty",
                description="No categories",
                budget_type=BudgetType.PERSONAL,
                period=BudgetPeriod.MONTHLY,
                categories={},
            )


class TestBuiltInTemplates:
    """Test pre-built budget templates."""

    def test_all_templates_exist(self):
        """Test all 5 built-in templates are defined."""
        expected_templates = {"50_30_20", "zero_based", "envelope", "business", "project"}
        assert set(TEMPLATES.keys()) == expected_templates

    def test_50_30_20_template(self):
        """Test 50/30/20 rule template structure."""
        template = TEMPLATES["50_30_20"]

        assert template.name == "50/30/20 Rule"
        assert "50% needs, 30% wants, 20% savings" in template.description
        assert template.budget_type == BudgetType.PERSONAL
        assert template.period == BudgetPeriod.MONTHLY

        # Check key categories
        assert "Housing" in template.categories
        assert "Savings" in template.categories
        assert "Entertainment" in template.categories

        # Verify percentages sum to 100
        total = sum(template.categories.values())
        assert 99.9 <= total <= 100.1

    def test_zero_based_template(self):
        """Test zero-based budgeting template."""
        template = TEMPLATES["zero_based"]

        assert template.name == "Zero-Based Budget"
        assert "Every dollar allocated" in template.description
        assert template.budget_type == BudgetType.PERSONAL
        assert template.period == BudgetPeriod.MONTHLY

        # Check comprehensive categories
        assert "Mortgage/Rent" in template.categories
        assert "Debt Payments" in template.categories
        assert "Emergency Fund" in template.categories

        total = sum(template.categories.values())
        assert 99.9 <= total <= 100.1

    def test_envelope_template(self):
        """Test envelope system template."""
        template = TEMPLATES["envelope"]

        assert template.name == "Envelope System"
        assert "Cash-like category limits" in template.description
        assert template.budget_type == BudgetType.PERSONAL
        assert template.period == BudgetPeriod.BIWEEKLY  # Biweekly for paycheck cycles

        # Check envelope categories
        assert "Groceries" in template.categories
        assert "Miscellaneous" in template.categories

        total = sum(template.categories.values())
        assert 99.9 <= total <= 100.1

    def test_business_template(self):
        """Test small business budget template."""
        template = TEMPLATES["business"]

        assert template.name == "Small Business Budget"
        assert "business expense categories" in template.description
        assert template.budget_type == BudgetType.BUSINESS
        assert template.period == BudgetPeriod.MONTHLY

        # Check business categories
        assert "Payroll" in template.categories
        assert "Marketing" in template.categories
        assert "Contingency" in template.categories

        total = sum(template.categories.values())
        assert 99.9 <= total <= 100.1

    def test_project_template(self):
        """Test project budget template."""
        template = TEMPLATES["project"]

        assert template.name == "Project Budget"
        assert "Project-specific budget" in template.description
        assert template.budget_type == BudgetType.PROJECT
        assert template.period == BudgetPeriod.QUARTERLY

        # Check project categories
        assert "Personnel" in template.categories
        assert "Materials" in template.categories
        assert "Contractors" in template.categories

        total = sum(template.categories.values())
        assert 99.9 <= total <= 100.1


class TestApplyTemplate:
    """Test apply_template() function."""

    @pytest.fixture
    def mock_tracker(self):
        """Create mock BudgetTracker."""
        tracker = MagicMock()
        tracker.create_budget = AsyncMock(
            return_value=Budget(
                id="bud_123",
                user_id="user_123",
                name="50/30/20 Rule - November 2025",
                type=BudgetType.PERSONAL,
                period=BudgetPeriod.MONTHLY,
                categories={"Housing": 1250.0, "Groceries": 500.0},
                start_date=datetime(2025, 11, 1),
                end_date=datetime(2025, 11, 30),
            )
        )
        return tracker

    @pytest.mark.asyncio
    async def test_apply_template_50_30_20(self, mock_tracker):
        """Test applying 50/30/20 template with $5000 income."""
        await apply_template(
            user_id="user_123",
            template_name="50_30_20",
            total_income=5000.00,
            tracker=mock_tracker,
        )

        # Verify tracker.create_budget was called
        mock_tracker.create_budget.assert_called_once()
        call_kwargs = mock_tracker.create_budget.call_args.kwargs

        assert call_kwargs["user_id"] == "user_123"
        assert call_kwargs["type"] == BudgetType.PERSONAL
        assert call_kwargs["period"] == BudgetPeriod.MONTHLY

        # Check category amounts calculated from percentages
        categories = call_kwargs["categories"]
        assert categories["Housing"] == 1250.0  # 25% of 5000
        assert categories["Groceries"] == 500.0  # 10% of 5000
        assert categories["Savings"] == 750.0  # 15% of 5000

        # Budget name should include template name
        assert "50/30/20 Rule" in call_kwargs["name"]

    @pytest.mark.asyncio
    async def test_apply_template_zero_based(self, mock_tracker):
        """Test applying zero-based template."""
        await apply_template(
            user_id="user_123",
            template_name="zero_based",
            total_income=4000.00,
            tracker=mock_tracker,
        )

        call_kwargs = mock_tracker.create_budget.call_args.kwargs
        categories = call_kwargs["categories"]

        # Check zero-based allocations
        assert categories["Mortgage/Rent"] == 1200.0  # 30% of 4000
        assert categories["Groceries"] == 480.0  # 12% of 4000
        assert categories["Healthcare"] == 200.0  # 5% of 4000

    @pytest.mark.asyncio
    async def test_apply_template_business(self, mock_tracker):
        """Test applying business template with high income."""
        await apply_template(
            user_id="biz_123",
            template_name="business",
            total_income=50000.00,
            tracker=mock_tracker,
            budget_name="Q4 2025 Operations",
        )

        call_kwargs = mock_tracker.create_budget.call_args.kwargs

        assert call_kwargs["user_id"] == "biz_123"
        assert call_kwargs["name"] == "Q4 2025 Operations"
        assert call_kwargs["type"] == BudgetType.BUSINESS

        categories = call_kwargs["categories"]
        assert categories["Payroll"] == 17500.0  # 35% of 50000
        assert categories["Marketing"] == 5000.0  # 10% of 50000

    @pytest.mark.asyncio
    async def test_apply_template_with_start_date(self, mock_tracker):
        """Test applying template with custom start date."""
        start_date = datetime(2025, 12, 1)

        await apply_template(
            user_id="user_123",
            template_name="50_30_20",
            total_income=3000.00,
            tracker=mock_tracker,
            start_date=start_date,
        )

        call_kwargs = mock_tracker.create_budget.call_args.kwargs
        assert call_kwargs["start_date"] == start_date

    @pytest.mark.asyncio
    async def test_apply_template_invalid_name(self, mock_tracker):
        """Test applying non-existent template raises error."""
        with pytest.raises(ValueError, match="Template 'invalid_template' not found"):
            await apply_template(
                user_id="user_123",
                template_name="invalid_template",
                total_income=5000.00,
                tracker=mock_tracker,
            )

    @pytest.mark.asyncio
    async def test_apply_template_zero_income(self, mock_tracker):
        """Test applying template with zero income raises error."""
        with pytest.raises(ValueError, match="total_income must be positive"):
            await apply_template(
                user_id="user_123",
                template_name="50_30_20",
                total_income=0.00,
                tracker=mock_tracker,
            )

    @pytest.mark.asyncio
    async def test_apply_template_negative_income(self, mock_tracker):
        """Test applying template with negative income raises error."""
        with pytest.raises(ValueError, match="total_income must be positive"):
            await apply_template(
                user_id="user_123",
                template_name="50_30_20",
                total_income=-1000.00,
                tracker=mock_tracker,
            )

    @pytest.mark.asyncio
    async def test_apply_custom_template(self, mock_tracker):
        """Test applying user-defined custom template."""
        custom = BudgetTemplate(
            name="Custom Budget",
            description="My custom allocation",
            budget_type=BudgetType.PERSONAL,
            period=BudgetPeriod.MONTHLY,
            categories={"Rent": 50.0, "Food": 30.0, "Other": 20.0},
        )

        await apply_template(
            user_id="user_123",
            template_name="custom",
            total_income=2000.00,
            tracker=mock_tracker,
            custom_template=custom,
        )

        call_kwargs = mock_tracker.create_budget.call_args.kwargs
        categories = call_kwargs["categories"]

        assert categories["Rent"] == 1000.0  # 50% of 2000
        assert categories["Food"] == 600.0  # 30% of 2000
        assert categories["Other"] == 400.0  # 20% of 2000

    @pytest.mark.asyncio
    async def test_apply_template_rounds_to_cents(self, mock_tracker):
        """Test category amounts rounded to 2 decimal places."""
        await apply_template(
            user_id="user_123",
            template_name="50_30_20",
            total_income=3333.33,  # Awkward amount
            tracker=mock_tracker,
        )

        call_kwargs = mock_tracker.create_budget.call_args.kwargs
        categories = call_kwargs["categories"]

        # All amounts should be rounded to 2 decimals
        for amount in categories.values():
            assert amount == round(amount, 2)


class TestListTemplates:
    """Test list_templates() function."""

    def test_list_all_templates(self):
        """Test listing all built-in templates."""
        templates = list_templates()

        assert len(templates) == 5
        assert "50_30_20" in templates
        assert "zero_based" in templates
        assert "envelope" in templates
        assert "business" in templates
        assert "project" in templates

    def test_list_templates_structure(self):
        """Test template metadata structure."""
        templates = list_templates()

        template = templates["50_30_20"]
        assert "name" in template
        assert "description" in template
        assert "type" in template
        assert "period" in template
        assert "categories" in template

        assert template["name"] == "50/30/20 Rule"
        assert template["type"] == "personal"
        assert template["period"] == "monthly"
        assert isinstance(template["categories"], dict)


class TestCustomTemplates:
    """Test custom template save/get functions."""

    @pytest.fixture
    def mock_tracker(self):
        """Create mock BudgetTracker."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_save_custom_template_not_implemented(self, mock_tracker):
        """Test save_custom_template raises NotImplementedError until Task 17."""
        custom = BudgetTemplate(
            name="Custom",
            description="Test",
            budget_type=BudgetType.PERSONAL,
            period=BudgetPeriod.MONTHLY,
            categories={"Food": 50.0, "Other": 50.0},
        )

        with pytest.raises(NotImplementedError, match="Task 17 DB wiring"):
            await save_custom_template("user_123", custom, mock_tracker)

    @pytest.mark.asyncio
    async def test_get_custom_templates_not_implemented(self, mock_tracker):
        """Test get_custom_templates raises NotImplementedError until Task 17."""
        with pytest.raises(NotImplementedError, match="Task 17 DB wiring"):
            await get_custom_templates("user_123", mock_tracker)


class TestTemplatesIntegration:
    """Integration tests for template workflow."""

    @pytest.mark.asyncio
    async def test_full_template_workflow(self):
        """Test complete workflow: list templates, apply template, create budget."""
        # Step 1: List available templates
        templates = list_templates()
        assert "50_30_20" in templates

        # Step 2: Apply template
        mock_tracker = MagicMock()
        mock_tracker.create_budget = AsyncMock(
            return_value=Budget(
                id="bud_123",
                user_id="user_123",
                name="50/30/20 Rule - November 2025",
                type=BudgetType.PERSONAL,
                period=BudgetPeriod.MONTHLY,
                categories={"Housing": 1250.0, "Groceries": 500.0},
                start_date=datetime(2025, 11, 1),
                end_date=datetime(2025, 11, 30),
            )
        )

        budget = await apply_template(
            user_id="user_123",
            template_name="50_30_20",
            total_income=5000.00,
            tracker=mock_tracker,
        )

        # Step 3: Verify budget created
        assert budget.id == "bud_123"
        assert budget.user_id == "user_123"
        assert budget.type == BudgetType.PERSONAL

        # Verify tracker was called correctly
        mock_tracker.create_budget.assert_called_once()
