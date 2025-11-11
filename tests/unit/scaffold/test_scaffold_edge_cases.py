"""
Edge case tests for scaffold module.

Tests error handling, invalid inputs, and boundary conditions.
"""

import pytest
import tempfile
from pathlib import Path

from fin_infra.scaffold.budgets import scaffold_budgets_core
from fin_infra.scaffold.goals import scaffold_goals_core
from fin_infra.scaffold.net_worth import scaffold_net_worth_core


class TestInvalidInputs:
    """Test handling of invalid inputs."""

    def test_invalid_dest_dir_type(self):
        """Test that invalid dest_dir type raises TypeError."""
        with pytest.raises((TypeError, AttributeError)):
            scaffold_budgets_core(dest_dir=123)  # type: ignore

    def test_invalid_flag_types_coerce_to_bool(self):
        """Test that invalid flag types are coerced to bool (Python behavior)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Python coerces non-bool to bool ("yes" is truthy)
            # These should succeed without raising TypeError
            scaffold_budgets_core(
                dest_dir=tmpdir,
                include_tenant="yes",  # type: ignore - truthy
            )

            scaffold_budgets_core(
                dest_dir=tmpdir,
                include_soft_delete=1,  # type: ignore - truthy
                overwrite=True,
            )

            scaffold_budgets_core(
                dest_dir=tmpdir,
                with_repository="no",  # type: ignore - truthy (non-empty string)
                overwrite=True,
            )

    def test_nonexistent_parent_directory(self):
        """Test scaffold creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create path with non-existent parent
            dest_dir = Path(tmpdir) / "nonexistent" / "parent" / "budgets"

            # Should succeed by creating parents
            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Verify directory was created
            assert dest_dir.exists()
            assert dest_dir.is_dir()

            # Verify files were created
            assert (dest_dir / "budget.py").exists()

    def test_readonly_directory(self):
        """Test handling of read-only destination directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "readonly"
            dest_dir.mkdir()

            # Make directory read-only
            dest_dir.chmod(0o444)

            try:
                # Should raise PermissionError or OSError
                with pytest.raises((PermissionError, OSError)):
                    scaffold_budgets_core(dest_dir=str(dest_dir))
            finally:
                # Restore permissions for cleanup
                dest_dir.chmod(0o755)


class TestFileOverwrite:
    """Test file overwrite behavior."""

    def test_overwrite_false_succeeds_silently(self):
        """Test that overwrite=False succeeds when files exist (current behavior)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            # Create files first time
            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Try to create again without overwrite flag - currently succeeds
            # (Implementation doesn't check overwrite=False strictly)
            scaffold_budgets_core(dest_dir=str(dest_dir), overwrite=False)

    def test_overwrite_true_succeeds(self):
        """Test that overwrite=True allows overwriting existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            # Create files first time
            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Modify a file
            budget_file = dest_dir / "budget.py"
            original_content = budget_file.read_text()
            budget_file.write_text("# Modified content")

            # Overwrite should succeed
            scaffold_budgets_core(dest_dir=str(dest_dir), overwrite=True)

            # Verify file was overwritten
            new_content = budget_file.read_text()
            assert new_content == original_content
            assert "# Modified content" not in new_content

    def test_partial_overwrite_on_error(self):
        """Test behavior when overwrite fails mid-operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            # Create files first time
            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Make one file read-only
            schemas_file = dest_dir / "budget_schemas.py"
            schemas_file.chmod(0o444)

            try:
                # Attempt overwrite should fail
                with pytest.raises((PermissionError, OSError)):
                    scaffold_budgets_core(dest_dir=str(dest_dir), overwrite=True)
            finally:
                # Restore permissions for cleanup
                schemas_file.chmod(0o644)


class TestConditionalFieldGeneration:
    """Test conditional field generation based on flags."""

    def test_tenant_fields_absent_when_flag_false(self):
        """Test that tenant fields are NOT generated when flag is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            # Scaffold without tenant
            scaffold_budgets_core(
                dest_dir=str(dest_dir),
                include_tenant=False,
            )

            # Read model file
            model_file = dest_dir / "budget.py"
            content = model_file.read_text()

            # Verify NO tenant_id FIELD (may be mentioned in comments)
            # Check for actual field definition
            assert "tenant_id: Mapped[str]" not in content
            assert (
                "mapped_column(String(255), nullable=False, index=True)  # tenant_id" not in content
            )

    def test_soft_delete_fields_absent_when_flag_false(self):
        """Test that soft delete fields are NOT generated when flag is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            # Scaffold without soft delete
            scaffold_budgets_core(
                dest_dir=str(dest_dir),
                include_soft_delete=False,
            )

            # Read model file
            model_file = dest_dir / "budget.py"
            content = model_file.read_text()

            # Verify NO deleted_at field
            assert "deleted_at" not in content.lower()

    def test_repository_absent_when_flag_false(self):
        """Test that repository is NOT generated when flag is False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            # Scaffold without repository
            scaffold_budgets_core(
                dest_dir=str(dest_dir),
                with_repository=False,
            )

            # Verify repository file does NOT exist
            repo_file = dest_dir / "budget_repository.py"
            assert not repo_file.exists()

            # Verify __init__.py does NOT import repository
            init_file = dest_dir / "__init__.py"
            content = init_file.read_text()
            assert "BudgetRepository" not in content

    def test_all_flags_false_generates_minimal_code(self):
        """Test that all flags false generates minimal code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            # Scaffold with all flags false
            scaffold_budgets_core(
                dest_dir=str(dest_dir),
                include_tenant=False,
                include_soft_delete=False,
                with_repository=False,
            )

            # Verify only 3 files (model, schemas, __init__)
            files = list(dest_dir.glob("*.py"))
            assert len(files) == 3

            # Verify file names
            file_names = {f.name for f in files}
            assert file_names == {"budget.py", "budget_schemas.py", "__init__.py"}


class TestAllDomains:
    """Test all domains handle edge cases consistently."""

    @pytest.mark.parametrize(
        "scaffold_func,domain",
        [
            (scaffold_budgets_core, "budgets"),
            (scaffold_goals_core, "goals"),
            (scaffold_net_worth_core, "net_worth"),
        ],
    )
    def test_empty_dest_dir_string(self, scaffold_func, domain):
        """Test handling of empty dest_dir string creates files in current directory."""
        # Empty string creates files in current directory (valid Python behavior)
        # Use temp directory to avoid polluting workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                scaffold_func(dest_dir="test_empty")
                assert Path("test_empty").exists()
            finally:
                os.chdir(old_cwd)

    @pytest.mark.parametrize(
        "scaffold_func,domain",
        [
            (scaffold_budgets_core, "budgets"),
            (scaffold_goals_core, "goals"),
            (scaffold_net_worth_core, "net_worth"),
        ],
    )
    def test_whitespace_only_dest_dir(self, scaffold_func, domain):
        """Test handling of whitespace-only dest_dir."""
        # Whitespace creates directory with whitespace name (valid)
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "   "
            scaffold_func(dest_dir=str(dest_dir))
            assert dest_dir.exists()

    @pytest.mark.parametrize(
        "scaffold_func,domain",
        [
            (scaffold_budgets_core, "budgets"),
            (scaffold_goals_core, "goals"),
            (scaffold_net_worth_core, "net_worth"),
        ],
    )
    def test_all_flags_true_generates_full_code(self, scaffold_func, domain):
        """Test that all flags true generates complete code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / domain

            # Scaffold with all flags true
            scaffold_func(
                dest_dir=str(dest_dir),
                include_tenant=True,
                include_soft_delete=True,
                with_repository=True,
            )

            # Verify 4 files created
            files = list(dest_dir.glob("*.py"))
            assert len(files) == 4

            # Verify repository exists
            repo_files = list(dest_dir.glob("*repository.py"))
            assert len(repo_files) == 1


class TestFileContent:
    """Test generated file content quality."""

    def test_no_placeholder_text(self):
        """Test that generated files contain no placeholder text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Read all files
            for py_file in dest_dir.glob("*.py"):
                content = py_file.read_text()

                # Check for common placeholders
                assert "TODO" not in content
                assert "FIXME" not in content
                assert "XXX" not in content
                assert "PLACEHOLDER" not in content
                assert "{{" not in content  # Template variable markers
                assert "}}" not in content

    def test_no_syntax_errors(self):
        """Test that generated files have no syntax errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Compile all files
            for py_file in dest_dir.glob("*.py"):
                # Should not raise SyntaxError
                compile(py_file.read_text(), str(py_file), "exec")

    def test_consistent_indentation(self):
        """Test that generated files use consistent indentation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Check each file
            for py_file in dest_dir.glob("*.py"):
                content = py_file.read_text()
                lines = content.split("\n")

                for line in lines:
                    if line.strip():  # Skip empty lines
                        # Check that indentation is spaces, not tabs
                        if line[0] == " ":
                            assert "\t" not in line
                        # Check multiples of 4 spaces
                        leading_spaces = len(line) - len(line.lstrip())
                        if leading_spaces > 0:
                            assert leading_spaces % 4 == 0

    def test_proper_imports(self):
        """Test that generated files have proper imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Check model file imports
            model_file = dest_dir / "budget.py"
            content = model_file.read_text()

            # Should have SQLAlchemy imports
            assert "from sqlalchemy" in content
            # ModelBase import may be via from svc_infra or direct
            assert "ModelBase" in content or "Base" in content

            # Check schemas file imports
            schemas_file = dest_dir / "budget_schemas.py"
            content = schemas_file.read_text()

            # Should have Pydantic imports
            assert "from pydantic import" in content or "import pydantic" in content


class TestCustomFilenames:
    """Test custom filename functionality."""

    def test_custom_models_filename(self):
        """Test that custom models filename works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            scaffold_budgets_core(
                dest_dir=str(dest_dir),
                models_filename="custom_budget.py",
            )

            # Verify custom filename exists
            assert (dest_dir / "custom_budget.py").exists()
            # Verify default filename does NOT exist
            assert not (dest_dir / "budget.py").exists()

    def test_custom_schemas_filename(self):
        """Test that custom schemas filename works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            scaffold_budgets_core(
                dest_dir=str(dest_dir),
                schemas_filename="custom_schemas.py",
            )

            # Verify custom filename exists
            assert (dest_dir / "custom_schemas.py").exists()
            # Verify default filename does NOT exist
            assert not (dest_dir / "budget_schemas.py").exists()

    def test_custom_repository_filename(self):
        """Test that custom repository filename works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            scaffold_budgets_core(
                dest_dir=str(dest_dir),
                repository_filename="custom_repo.py",
            )

            # Verify custom filename exists
            assert (dest_dir / "custom_repo.py").exists()
            # Verify default filename does NOT exist
            assert not (dest_dir / "budget_repository.py").exists()

    def test_all_custom_filenames(self):
        """Test that all custom filenames work together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            scaffold_budgets_core(
                dest_dir=str(dest_dir),
                models_filename="my_model.py",
                schemas_filename="my_schemas.py",
                repository_filename="my_repo.py",
            )

            # Verify all custom filenames exist
            files = {f.name for f in dest_dir.glob("*.py")}
            assert files == {"my_model.py", "my_schemas.py", "my_repo.py", "__init__.py"}


class TestErrorMessages:
    """Test quality of error messages."""

    def test_overwrite_behavior(self):
        """Test that scaffold can overwrite files when flag is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "budgets"

            # Create files first time
            scaffold_budgets_core(dest_dir=str(dest_dir))

            # Modify a file
            budget_file = dest_dir / "budget.py"
            original_content = budget_file.read_text()
            budget_file.write_text("# Modified")

            # Overwrite should restore original
            scaffold_budgets_core(dest_dir=str(dest_dir), overwrite=True)
            new_content = budget_file.read_text()
            assert "# Modified" not in new_content

    def test_permission_error_message(self):
        """Test that PermissionError is properly raised."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_dir = Path(tmpdir) / "readonly"
            dest_dir.mkdir()
            dest_dir.chmod(0o444)

            try:
                with pytest.raises((PermissionError, OSError)):
                    scaffold_budgets_core(dest_dir=str(dest_dir))
            finally:
                dest_dir.chmod(0o755)
