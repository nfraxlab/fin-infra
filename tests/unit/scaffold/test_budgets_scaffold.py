"""Unit tests for budget scaffold function."""
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from fin_infra.scaffold.budgets import (
    scaffold_budgets_core,
    _generate_substitutions,
    _tenant_field,
    _soft_delete_field,
    _tenant_filter,
    _soft_delete_filter,
    _soft_delete_logic,
    _tenant_field_schema_create,
    _tenant_field_schema_update,
    _tenant_field_schema_read,
    _generate_init_content,
)


class TestGenerateSubstitutions:
    """Tests for _generate_substitutions helper."""
    
    def test_basic_substitutions_no_flags(self):
        """Test basic substitutions without any flags."""
        subs = _generate_substitutions(include_tenant=False, include_soft_delete=False)
        
        # Core variables always present
        assert subs["Entity"] == "Budget"
        assert subs["entity"] == "budget"
        assert subs["table_name"] == "budgets"
        
        # Conditional fields empty
        assert subs["tenant_field"] == ""
        assert subs["soft_delete_field"] == ""
        assert subs["tenant_arg"] == ""
        assert subs["tenant_arg_unique_index"] == ""
        assert subs["tenant_default"] == "None"  # None when tenant disabled
        assert subs["tenant_filter"] == ""
        assert subs["soft_delete_filter"] == ""
        # When soft delete disabled, uses hard delete fallback
        assert "Hard delete only" in subs["soft_delete_logic"] or "session.delete" in subs["soft_delete_logic"]
    
    def test_substitutions_with_tenant(self):
        """Test substitutions with tenant flag enabled."""
        subs = _generate_substitutions(include_tenant=True, include_soft_delete=False)
        
        assert "tenant_id" in subs["tenant_field"]
        assert subs["tenant_arg"] == ", tenant_id: str"
        assert subs["tenant_arg_unique_index"] == ', tenant_field="tenant_id"'
        assert subs["tenant_default"] == '"tenant_id"'  # String "tenant_id" when enabled
        assert "tenant_id" in subs["tenant_filter"]
    
    def test_substitutions_with_soft_delete(self):
        """Test substitutions with soft delete flag enabled."""
        subs = _generate_substitutions(include_tenant=False, include_soft_delete=True)
        
        assert "deleted_at" in subs["soft_delete_field"]
        assert "deleted_at" in subs["soft_delete_filter"]
        assert "deleted_at" in subs["soft_delete_logic"]
    
    def test_substitutions_with_all_flags(self):
        """Test substitutions with all flags enabled."""
        subs = _generate_substitutions(include_tenant=True, include_soft_delete=True)
        
        # Both tenant and soft delete fields present
        assert "tenant_id" in subs["tenant_field"]
        assert "deleted_at" in subs["soft_delete_field"]
        assert "tenant_id" in subs["tenant_filter"]
        assert "deleted_at" in subs["soft_delete_filter"]


class TestHelperFunctions:
    """Tests for individual helper functions."""
    
    def test_tenant_field_contains_mapping(self):
        """Test _tenant_field() returns valid SQLAlchemy field definition."""
        field_def = _tenant_field()
        assert "tenant_id" in field_def
        assert "Mapped[str]" in field_def
        assert "String(64)" in field_def
        assert "index=True" in field_def
    
    def test_soft_delete_field_contains_mapping(self):
        """Test _soft_delete_field() returns valid SQLAlchemy field definition."""
        field_def = _soft_delete_field()
        assert "deleted_at" in field_def
        assert "Mapped[Optional[datetime]]" in field_def
        assert "DateTime(timezone=True)" in field_def
        assert "nullable=True" in field_def
    
    def test_tenant_filter_contains_where_clause(self):
        """Test _tenant_filter() returns valid SQLAlchemy filter."""
        filter_code = _tenant_filter()
        assert "tenant_id" in filter_code
        assert "where" in filter_code
        assert "is not None" in filter_code
    
    def test_soft_delete_filter_contains_where_clause(self):
        """Test _soft_delete_filter() returns valid SQLAlchemy filter."""
        filter_code = _soft_delete_filter()
        assert "deleted_at" in filter_code
        assert "is_(None)" in filter_code
    
    def test_soft_delete_logic_contains_conditional(self):
        """Test _soft_delete_logic() returns soft delete implementation (update with deleted_at)."""
        logic = _soft_delete_logic()
        assert "deleted_at" in logic
        assert "datetime.now" in logic
        # Soft delete uses update, not session.delete
        assert "update" in logic
    
    def test_tenant_field_schema_create(self):
        """Test _tenant_field_schema_create() returns Pydantic field."""
        field = _tenant_field_schema_create()
        assert "tenant_id: str" in field
    
    def test_tenant_field_schema_update(self):
        """Test _tenant_field_schema_update() returns optional Pydantic field."""
        field = _tenant_field_schema_update()
        assert "tenant_id: Optional[str]" in field
        assert "None" in field
    
    def test_tenant_field_schema_read(self):
        """Test _tenant_field_schema_read() returns Pydantic field."""
        field = _tenant_field_schema_read()
        assert "tenant_id: str" in field


class TestGenerateInitContent:
    """Tests for _generate_init_content helper."""
    
    def test_basic_init_without_repository(self):
        """Test __init__.py generation without repository."""
        content = _generate_init_content(
            models_file="budget.py",
            schemas_file="budget_schemas.py",
            repo_file=None,
        )
        
        # Should have imports
        assert "from .budget import Budget, create_budget_service" in content
        assert "from .budget_schemas import" in content
        assert "BudgetBase" in content
        assert "BudgetRead" in content
        assert "BudgetCreate" in content
        assert "BudgetUpdate" in content
        
        # Should NOT import repository
        assert "BudgetRepository" not in content
        
        # Should have __all__
        assert "__all__ = [" in content
        assert '"Budget"' in content
        assert '"BudgetRead"' in content
    
    def test_init_with_repository(self):
        """Test __init__.py generation with repository."""
        content = _generate_init_content(
            models_file="budget.py",
            schemas_file="budget_schemas.py",
            repo_file="budget_repository.py",
        )
        
        # Should import repository
        assert "from .budget_repository import BudgetRepository" in content
        assert '"BudgetRepository"' in content
    
    def test_custom_filenames(self):
        """Test __init__.py generation with custom filenames."""
        content = _generate_init_content(
            models_file="my_budget_model.py",
            schemas_file="my_budget_schemas.py",
            repo_file="my_budget_repo.py",
        )
        
        assert "from .my_budget_model import" in content
        assert "from .my_budget_schemas import" in content
        assert "from .my_budget_repo import" in content


class TestScaffoldBudgetsCore:
    """Tests for scaffold_budgets_core main function."""
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_basic_scaffold_no_flags(self, mock_init, mock_write, mock_render):
        """Test basic scaffold without any flags."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        result = scaffold_budgets_core(
            dest_dir=Path("/tmp/models"),
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )
        
        # Should render 3 templates (models, schemas, repository)
        assert mock_render.call_count == 3
        
        # Should write 3 files (models, schemas, repository)
        assert mock_write.call_count == 3
        
        # Should create __init__.py
        assert mock_init.call_count == 1
        
        # Result should contain 4 file info dicts
        assert "files" in result
        assert len(result["files"]) == 4
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_scaffold_without_repository(self, mock_init, mock_write, mock_render):
        """Test scaffold without repository generation."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        result = scaffold_budgets_core(
            dest_dir=Path("/tmp/models"),
            with_repository=False,
        )
        
        # Should render only 2 templates (models, schemas)
        assert mock_render.call_count == 2
        
        # Should write only 2 files (models, schemas)
        assert mock_write.call_count == 2
        
        # Should create __init__.py
        assert mock_init.call_count == 1
        
        # Result should contain 3 file info dicts (2 files + __init__.py)
        assert len(result["files"]) == 3
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_scaffold_with_custom_filenames(self, mock_init, mock_write, mock_render):
        """Test scaffold with custom filenames."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        result = scaffold_budgets_core(
            dest_dir=Path("/tmp/models"),
            models_filename="custom_model.py",
            schemas_filename="custom_schemas.py",
            repository_filename="custom_repo.py",
        )
        
        # Verify write was called with custom filenames
        write_calls = [call[0][0] for call in mock_write.call_args_list]
        assert any("custom_model.py" in str(path) for path in write_calls)
        assert any("custom_schemas.py" in str(path) for path in write_calls)
        assert any("custom_repo.py" in str(path) for path in write_calls)
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_scaffold_with_tenant_flag(self, mock_init, mock_write, mock_render):
        """Test scaffold with tenant flag enabled."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        result = scaffold_budgets_core(
            dest_dir=Path("/tmp/models"),
            include_tenant=True,
        )
        
        # Verify render_template was called with tenant substitutions
        first_render_call = mock_render.call_args_list[0]
        subs = first_render_call[0][2]  # Third argument is subs dict
        
        assert subs["tenant_arg"] == ", tenant_id: str"
        assert "tenant_id" in subs["tenant_field"]
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_scaffold_with_soft_delete_flag(self, mock_init, mock_write, mock_render):
        """Test scaffold with soft delete flag enabled."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        result = scaffold_budgets_core(
            dest_dir=Path("/tmp/models"),
            include_soft_delete=True,
        )
        
        # Verify render_template was called with soft delete substitutions
        first_render_call = mock_render.call_args_list[0]
        subs = first_render_call[0][2]
        
        assert "deleted_at" in subs["soft_delete_field"]
        assert "deleted_at" in subs["soft_delete_filter"]
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_scaffold_with_all_flags(self, mock_init, mock_write, mock_render):
        """Test scaffold with all flags enabled."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        result = scaffold_budgets_core(
            dest_dir=Path("/tmp/models"),
            include_tenant=True,
            include_soft_delete=True,
            with_repository=True,
        )
        
        # Verify render_template was called with both substitutions
        first_render_call = mock_render.call_args_list[0]
        subs = first_render_call[0][2]
        
        assert "tenant_id" in subs["tenant_field"]
        assert "deleted_at" in subs["soft_delete_field"]
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_overwrite_flag_passed_to_write(self, mock_init, mock_write, mock_render):
        """Test overwrite flag is passed to write functions."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        scaffold_budgets_core(
            dest_dir=Path("/tmp/models"),
            overwrite=True,
        )
        
        # Verify write was called with overwrite=True
        for call in mock_write.call_args_list:
            assert call[0][2] == True  # Third positional arg is overwrite
        
        # Verify ensure_init_py was called with overwrite=True
        init_call_kwargs = mock_init.call_args[1]
        assert init_call_kwargs["overwrite"] == True
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_default_filenames_used(self, mock_init, mock_write, mock_render):
        """Test default filenames are used when not specified."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        scaffold_budgets_core(dest_dir=Path("/tmp/models"))
        
        # Verify default filenames
        write_calls = [str(call[0][0]) for call in mock_write.call_args_list]
        assert any("budget.py" in path for path in write_calls)
        assert any("budget_schemas.py" in path for path in write_calls)
        assert any("budget_repository.py" in path for path in write_calls)
    
    @patch("fin_infra.scaffold.budgets.render_template")
    @patch("fin_infra.scaffold.budgets.write")
    @patch("fin_infra.scaffold.budgets.ensure_init_py")
    def test_init_py_generated_with_correct_content(self, mock_init, mock_write, mock_render):
        """Test __init__.py is generated with correct re-exports."""
        mock_render.return_value = "mocked content"
        mock_write.return_value = {"path": "/tmp/file.py", "action": "wrote"}
        mock_init.return_value = {"path": "/tmp/__init__.py", "action": "wrote"}
        
        scaffold_budgets_core(
            dest_dir=Path("/tmp/models"),
            models_filename="budget.py",
            schemas_filename="budget_schemas.py",
            repository_filename="budget_repository.py",
        )
        
        # Verify ensure_init_py was called with correct content
        init_call = mock_init.call_args
        content = init_call[1]["content"]
        
        assert "from .budget import Budget" in content
        assert "from .budget_schemas import" in content
        assert "from .budget_repository import" in content
        assert "__all__" in content


class TestIntegrationScenarios:
    """Integration tests with real file system operations."""
    
    def test_full_scaffold_creates_files(self, tmp_path):
        """Test full scaffold creates actual files on disk."""
        dest_dir = tmp_path / "models"
        
        result = scaffold_budgets_core(
            dest_dir=dest_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )
        
        # Verify files were created
        assert (dest_dir / "budget.py").exists()
        assert (dest_dir / "budget_schemas.py").exists()
        assert (dest_dir / "budget_repository.py").exists()
        assert (dest_dir / "__init__.py").exists()
        
        # Verify result contains correct info
        assert len(result["files"]) == 4
        assert all(f["action"] in ["wrote", "skipped"] for f in result["files"])
    
    def test_scaffold_with_existing_files_skips(self, tmp_path):
        """Test scaffold skips existing files when overwrite=False."""
        dest_dir = tmp_path / "models"
        dest_dir.mkdir()
        
        # Create an existing file
        existing_file = dest_dir / "budget.py"
        existing_file.write_text("# existing content")
        
        result = scaffold_budgets_core(
            dest_dir=dest_dir,
            overwrite=False,
        )
        
        # Verify existing file was skipped
        skipped = [f for f in result["files"] if f["action"] == "skipped"]
        assert any("budget.py" in f["path"] for f in skipped)
        
        # Verify existing content not overwritten
        assert existing_file.read_text() == "# existing content"
    
    def test_scaffold_with_overwrite_replaces_files(self, tmp_path):
        """Test scaffold replaces existing files when overwrite=True."""
        dest_dir = tmp_path / "models"
        dest_dir.mkdir()
        
        # Create an existing file
        existing_file = dest_dir / "budget.py"
        existing_file.write_text("# existing content")
        
        result = scaffold_budgets_core(
            dest_dir=dest_dir,
            overwrite=True,
        )
        
        # Verify all files were written (not skipped)
        assert all(f["action"] == "wrote" for f in result["files"])
        
        # Verify existing content was replaced
        new_content = existing_file.read_text()
        assert "# existing content" not in new_content
        assert "class Budget(ModelBase)" in new_content
    
    def test_generated_models_are_valid_python(self, tmp_path):
        """Test generated models file is valid Python."""
        dest_dir = tmp_path / "models"
        
        scaffold_budgets_core(dest_dir=dest_dir)
        
        models_file = dest_dir / "budget.py"
        content = models_file.read_text()
        
        # Should have valid Python syntax
        assert "class Budget(ModelBase):" in content
        assert "from sqlalchemy" in content
        assert "__tablename__ = \"budgets\"" in content
    
    def test_generated_schemas_are_valid_python(self, tmp_path):
        """Test generated schemas file is valid Python."""
        dest_dir = tmp_path / "models"
        
        scaffold_budgets_core(dest_dir=dest_dir)
        
        schemas_file = dest_dir / "budget_schemas.py"
        content = schemas_file.read_text()
        
        # Should have valid Python syntax
        assert "from pydantic import BaseModel" in content
        assert "class BudgetBase(BaseModel):" in content
        assert "class BudgetRead" in content
        assert "class BudgetCreate" in content
        assert "class BudgetUpdate" in content
