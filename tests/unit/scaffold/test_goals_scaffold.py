"""
Unit tests for fin_infra.scaffold.goals module.

Tests scaffold_goals_core() function with various flag combinations:
- Basic scaffold (no flags)
- With tenant_id
- With soft_delete (deleted_at)
- Without repository
- Custom filenames
- Overwrite protection
- Combined flags (tenant + soft_delete, tenant + no-repo, etc.)
"""

from fin_infra.scaffold.goals import scaffold_goals_core, _generate_substitutions


class TestGenerateSubstitutions:
    """Test _generate_substitutions() helper function."""

    def test_basic_substitutions(self):
        """Core variables present without flags."""
        subs = _generate_substitutions(include_tenant=False, include_soft_delete=False)

        assert subs["Entity"] == "Goal"
        assert subs["entity"] == "goal"
        assert subs["table_name"] == "goals"

        # Tenant fields should be empty
        assert subs["tenant_field"] == ""
        assert subs["tenant_arg"] == ""
        assert subs["tenant_arg_unique_index"] == ""
        assert subs["tenant_filter"] == ""

        # Soft delete fields should be empty
        assert subs["soft_delete_field"] == ""
        assert subs["soft_delete_filter"] == ""

    def test_tenant_substitutions(self):
        """Tenant flag generates tenant_id patterns."""
        subs = _generate_substitutions(include_tenant=True, include_soft_delete=False)

        assert "tenant_id" in subs["tenant_field"]
        assert "tenant_id: str" in subs["tenant_arg"]
        assert 'tenant_field="tenant_id"' in subs["tenant_arg_unique_index"]
        assert "tenant_id: str" in subs["tenant_arg_type"]
        assert "tenant_id=tenant_id" in subs["tenant_arg_val"]
        assert ".where(Goal.tenant_id == tenant_id)" in subs["tenant_filter"]

        # Schema fields
        assert "tenant_id: Optional[str] = None" in subs["tenant_field_create"]
        assert subs["tenant_field_update"] == ""  # Immutable
        assert "tenant_id: Optional[str] = None" in subs["tenant_field_read"]

    def test_soft_delete_substitutions(self):
        """Soft delete flag generates deleted_at patterns."""
        subs = _generate_substitutions(include_tenant=False, include_soft_delete=True)

        assert "deleted_at" in subs["soft_delete_field"]
        assert ".where(Goal.deleted_at.is_(None))" in subs["soft_delete_filter"]
        assert "goal.deleted_at = datetime.now(timezone.utc)" in subs["soft_delete_logic"]
        assert subs["soft_delete_default"] == "True"

    def test_combined_flags(self):
        """Both flags work together."""
        subs = _generate_substitutions(include_tenant=True, include_soft_delete=True)

        assert "tenant_id" in subs["tenant_field"]
        assert "deleted_at" in subs["soft_delete_field"]


class TestScaffoldGoalsCore:
    """Test scaffold_goals_core() main function."""

    def test_basic_scaffold(self, tmp_path):
        """Generate basic goals files without flags."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Check return structure
        assert "files" in result
        assert len(result["files"]) == 5  # models, schemas, repository, README, __init__

        # Check files exist
        assert (dest / "goal.py").exists()
        assert (dest / "goal_schemas.py").exists()
        assert (dest / "goal_repository.py").exists()
        assert (dest / "README.md").exists()
        assert (dest / "__init__.py").exists()

        # Check all files marked as "wrote"
        actions = {f["action"] for f in result["files"] if f["action"] != "ensured"}
        assert actions == {"wrote"}

    def test_with_tenant(self, tmp_path):
        """Scaffold with tenant_id field."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=True,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Check models contains tenant_id
        models_content = (dest / "goal.py").read_text()
        assert "tenant_id: Mapped[Optional[str]]" in models_content
        assert 'tenant_field="tenant_id"' in models_content  # For unique indexes

        # Check schemas contains tenant_id
        schemas_content = (dest / "goal_schemas.py").read_text()
        assert "tenant_id: Optional[str] = None" in schemas_content

    def test_with_soft_delete(self, tmp_path):
        """Scaffold with deleted_at field."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=True,
            with_repository=True,
            overwrite=False,
        )

        # Check models contains deleted_at
        models_content = (dest / "goal.py").read_text()
        assert "deleted_at: Mapped[datetime | None]" in models_content

        # Check repository uses soft delete logic
        repo_content = (dest / "goal_repository.py").read_text()
        assert "goal.deleted_at = datetime.now(timezone.utc)" in repo_content
        assert "# Soft delete" in repo_content

    def test_without_repository(self, tmp_path):
        """Scaffold without repository file."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=False,
            overwrite=False,
        )

        # Check files exist
        assert (dest / "goal.py").exists()
        assert (dest / "goal_schemas.py").exists()
        assert (dest / "README.md").exists()
        assert (dest / "__init__.py").exists()

        # Repository should NOT exist
        assert not (dest / "goal_repository.py").exists()

        # Return should have 4 files (no repository)
        assert len(result["files"]) == 4

    def test_custom_filenames(self, tmp_path):
        """Scaffold with custom filenames."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
            models_filename="my_goal_model.py",
            schemas_filename="my_goal_schemas.py",
            repository_filename="my_goal_repo.py",
        )

        # Check custom filenames exist
        assert (dest / "my_goal_model.py").exists()
        assert (dest / "my_goal_schemas.py").exists()
        assert (dest / "my_goal_repo.py").exists()
        assert (dest / "README.md").exists()
        assert (dest / "__init__.py").exists()

    def test_overwrite_protection(self, tmp_path):
        """Existing files are not overwritten by default."""
        dest = tmp_path / "goals"
        dest.mkdir()

        # Create existing file with custom content
        models_path = dest / "goal.py"
        models_path.write_text("# Custom content\n")

        # Scaffold with overwrite=False (default)
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Check models file was skipped
        models_result = next(f for f in result["files"] if "goal.py" in f["path"])
        assert models_result["action"] == "skipped"

        # Content should be unchanged
        assert models_path.read_text() == "# Custom content\n"

    def test_overwrite_enabled(self, tmp_path):
        """Existing files are overwritten when overwrite=True."""
        dest = tmp_path / "goals"
        dest.mkdir()

        # Create existing file with custom content
        models_path = dest / "goal.py"
        models_path.write_text("# Custom content\n")

        # Scaffold with overwrite=True
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=True,
        )

        # Check models file was overwritten
        models_result = next(f for f in result["files"] if "goal.py" in f["path"])
        assert models_result["action"] == "wrote"

        # Content should be replaced with template
        models_content = models_path.read_text()
        assert "# Custom content" not in models_content
        assert "class Goal(ModelBase)" in models_content

    def test_combined_tenant_and_soft_delete(self, tmp_path):
        """Scaffold with both tenant_id and deleted_at."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=True,
            include_soft_delete=True,
            with_repository=True,
            overwrite=False,
        )

        # Check models contains both fields
        models_content = (dest / "goal.py").read_text()
        assert "tenant_id: Mapped[Optional[str]]" in models_content
        assert "deleted_at: Mapped[datetime | None]" in models_content

        # Check repository uses both filters
        repo_content = (dest / "goal_repository.py").read_text()
        assert ".where(Goal.tenant_id == tenant_id)" in repo_content
        assert ".where(Goal.deleted_at.is_(None))" in repo_content

    def test_tenant_without_repository(self, tmp_path):
        """Scaffold with tenant but no repository."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=True,
            include_soft_delete=False,
            with_repository=False,
            overwrite=False,
        )

        # Check models and schemas have tenant_id
        models_content = (dest / "goal.py").read_text()
        schemas_content = (dest / "goal_schemas.py").read_text()

        assert "tenant_id: Mapped[Optional[str]]" in models_content
        assert "tenant_id: Optional[str] = None" in schemas_content

        # Repository should not exist
        assert not (dest / "goal_repository.py").exists()

    def test_creates_missing_directory(self, tmp_path):
        """Scaffold creates destination directory if missing."""
        dest = tmp_path / "nonexistent" / "goals"
        assert not dest.exists()

        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Directory and files should exist
        assert dest.exists()
        assert (dest / "goal.py").exists()

    def test_models_content_structure(self, tmp_path):
        """Generated models.py has correct structure."""
        dest = tmp_path / "goals"
        scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        models_content = (dest / "goal.py").read_text()

        # Check key elements
        assert "from sqlalchemy.orm import Mapped, mapped_column" in models_content
        assert "class Goal(ModelBase):" in models_content
        assert '__tablename__ = "goals"' in models_content
        assert "user_id: Mapped[Optional[str]]" in models_content
        assert "target_amount: Mapped[Decimal]" in models_content
        assert "current_amount: Mapped[Decimal]" in models_content
        assert "status: Mapped[str]" in models_content
        assert "priority: Mapped[int]" in models_content
        assert "percent_complete" in models_content
        assert "@property" in models_content

    def test_schemas_content_structure(self, tmp_path):
        """Generated goal_schemas.py has correct structure."""
        dest = tmp_path / "goals"
        scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        schemas_content = (dest / "goal_schemas.py").read_text()

        # Check key elements
        assert "from pydantic import BaseModel" in schemas_content
        assert "class GoalBase" in schemas_content
        assert "class GoalCreate" in schemas_content
        assert "class GoalUpdate" in schemas_content
        assert "class GoalRead" in schemas_content
        assert "validate_status" in schemas_content

    def test_repository_content_structure(self, tmp_path):
        """Generated goal_repository.py has correct structure."""
        dest = tmp_path / "goals"
        scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        repo_content = (dest / "goal_repository.py").read_text()

        # Check key elements
        assert "class GoalRepository:" in repo_content
        assert "async def create(" in repo_content
        assert "async def get(" in repo_content
        assert "async def list(" in repo_content
        assert "async def update(" in repo_content
        assert "async def delete(" in repo_content

        # Goal-specific methods
        assert "async def get_active(" in repo_content
        assert "async def get_by_status(" in repo_content
        assert "async def get_by_priority(" in repo_content
        assert "async def update_progress(" in repo_content

    def test_readme_content(self, tmp_path):
        """Generated README.md contains usage guide."""
        dest = tmp_path / "goals"
        scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        readme_content = (dest / "README.md").read_text()

        # Check key sections
        assert "# Goals Scaffold Templates" in readme_content
        assert "Template Variables" in readme_content
        assert "Goal" in readme_content
        assert "Repository" in readme_content
        assert "Example" in readme_content

    def test_init_file_created(self, tmp_path):
        """__init__.py is created or ensured."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Check __init__.py exists
        assert (dest / "__init__.py").exists()

        # Check in return value
        init_result = next(f for f in result["files"] if "__init__.py" in f["path"])
        assert init_result["action"] == "wrote"

    def test_path_object_input(self, tmp_path):
        """Function accepts Path objects for dest_dir."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=dest,  # Path object
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        assert (dest / "goal.py").exists()
        assert len(result["files"]) == 5

    def test_string_path_input(self, tmp_path):
        """Function accepts string paths for dest_dir."""
        dest = tmp_path / "goals"
        result = scaffold_goals_core(
            dest_dir=str(dest),  # String path
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        assert (dest / "goal.py").exists()
        assert len(result["files"]) == 5
