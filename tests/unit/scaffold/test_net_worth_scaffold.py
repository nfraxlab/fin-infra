"""
Unit tests for fin_infra.scaffold.net_worth module.

Tests the scaffold_net_worth_core() function and its helper functions, verifying:
- Template variable generation (_generate_substitutions)
- File creation and content rendering
- Overwrite protection
- Custom filenames
- All flag combinations (tenant, soft_delete, with_repository)
- Net worth specific features (immutable snapshots, no Update schema)
"""

import shutil
from pathlib import Path

import pytest

from fin_infra.scaffold.net_worth import (
    scaffold_net_worth_core,
    _generate_substitutions,
    _generate_init_content,
)


class TestGenerateSubstitutions:
    """Test _generate_substitutions helper function."""

    def test_basic_substitutions(self):
        """Test basic substitutions without any flags."""
        subs = _generate_substitutions(include_tenant=False, include_soft_delete=False)

        assert subs["Entity"] == "NetWorthSnapshot"
        assert subs["entity"] == "net_worth_snapshot"
        assert subs["table_name"] == "net_worth_snapshots"

        # Tenant fields should be empty
        assert subs["tenant_field"] == ""
        assert subs["tenant_arg"] == ""
        assert subs["tenant_arg_type_comma"] == ""
        assert subs["tenant_dict_assign"] == ""

        # Soft delete should have hard delete logic
        assert subs["soft_delete_field"] == ""
        assert "Hard delete" in subs["soft_delete_logic"]
        assert subs["soft_delete_default"] == "False"

    def test_tenant_substitutions(self):
        """Test tenant-specific substitutions."""
        subs = _generate_substitutions(include_tenant=True, include_soft_delete=False)

        # Core variables unchanged
        assert subs["Entity"] == "NetWorthSnapshot"

        # Tenant patterns present
        assert "tenant_id" in subs["tenant_field"]
        assert "tenant_id: str" in subs["tenant_arg"]
        assert ",\n        tenant_id: str" == subs["tenant_arg_type_comma"]
        assert 'data["tenant_id"] = tenant_id' in subs["tenant_dict_assign"]
        assert "tenant_field" in subs["tenant_arg_unique_index"]

        # Schema field patterns
        assert "tenant_id" in subs["tenant_field_create"]
        assert subs["tenant_field_update"] == ""  # Immutable after creation
        assert "tenant_id" in subs["tenant_field_read"]

    def test_soft_delete_substitutions(self):
        """Test soft delete substitutions."""
        subs = _generate_substitutions(include_tenant=False, include_soft_delete=True)

        # Soft delete patterns present
        assert "deleted_at" in subs["soft_delete_field"]
        assert "deleted_at" in subs["soft_delete_filter"]
        assert "Soft delete" in subs["soft_delete_logic"]
        assert subs["soft_delete_default"] == "True"

    def test_combined_flags(self):
        """Test both tenant and soft_delete enabled."""
        subs = _generate_substitutions(include_tenant=True, include_soft_delete=True)

        # Both tenant and soft delete present
        assert "tenant_id" in subs["tenant_field"]
        assert "deleted_at" in subs["soft_delete_field"]
        assert subs["soft_delete_default"] == "True"


class TestScaffoldNetWorthCore:
    """Test scaffold_net_worth_core main function."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for test output."""
        test_dir = tmp_path / "test_net_worth"
        test_dir.mkdir()
        yield test_dir
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)

    def test_basic_scaffold(self, temp_dir):
        """Test basic scaffold without tenant or soft_delete."""
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Check return structure
        assert "files" in result
        assert len(result["files"]) == 5  # models, schemas, repository, readme, __init__

        # Check all files were created
        assert (temp_dir / "net_worth_snapshot.py").exists()
        assert (temp_dir / "net_worth_snapshot_schemas.py").exists()
        assert (temp_dir / "net_worth_snapshot_repository.py").exists()
        assert (temp_dir / "README.md").exists()
        assert (temp_dir / "__init__.py").exists()

        # Check file actions
        for file_info in result["files"]:
            assert file_info["action"] == "wrote"

    def test_with_tenant(self, temp_dir):
        """Test scaffold with tenant enabled."""
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=True,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Read models file and check tenant_id present
        models_content = (temp_dir / "net_worth_snapshot.py").read_text()
        assert "tenant_id" in models_content
        assert "Mapped[str]" in models_content

        # Read repository and check tenant filtering
        repo_content = (temp_dir / "net_worth_snapshot_repository.py").read_text()
        assert "tenant_id: str" in repo_content

    def test_with_soft_delete(self, temp_dir):
        """Test scaffold with soft_delete enabled."""
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=True,
            with_repository=True,
            overwrite=False,
        )

        # Read models file and check deleted_at present
        models_content = (temp_dir / "net_worth_snapshot.py").read_text()
        assert "deleted_at" in models_content

        # Read repository and check soft delete logic
        repo_content = (temp_dir / "net_worth_snapshot_repository.py").read_text()
        assert "deleted_at" in repo_content

    def test_without_repository(self, temp_dir):
        """Test scaffold without repository file."""
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=False,
            overwrite=False,
        )

        # Repository file should NOT be created
        assert not (temp_dir / "net_worth_snapshot_repository.py").exists()

        # Other files should still exist
        assert (temp_dir / "net_worth_snapshot.py").exists()
        assert (temp_dir / "net_worth_snapshot_schemas.py").exists()

        # Only 4 files: models, schemas, readme, __init__
        assert len(result["files"]) == 4

    def test_custom_filenames(self, temp_dir):
        """Test scaffold with custom filenames."""
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
            models_filename="my_snapshot.py",
            schemas_filename="my_schemas.py",
            repository_filename="my_repo.py",
        )

        # Custom filenames should be used
        assert (temp_dir / "my_snapshot.py").exists()
        assert (temp_dir / "my_schemas.py").exists()
        assert (temp_dir / "my_repo.py").exists()

        # Check __init__.py imports custom names
        init_content = (temp_dir / "__init__.py").read_text()
        assert "from .my_snapshot import" in init_content
        assert "from .my_schemas import" in init_content
        assert "from .my_repo import" in init_content

    def test_overwrite_protection(self, temp_dir):
        """Test that existing files are not overwritten by default."""
        # Create file first time
        scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Try to create again with overwrite=False
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # All files should be skipped
        for file_info in result["files"]:
            assert file_info["action"] == "skipped"

    def test_overwrite_enabled(self, temp_dir):
        """Test that existing files are overwritten when overwrite=True."""
        # Create file first time
        scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Create again with overwrite=True
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=True,
        )

        # All files should be written
        for file_info in result["files"]:
            assert file_info["action"] == "wrote"

    def test_combined_tenant_and_soft_delete(self, temp_dir):
        """Test scaffold with both tenant and soft_delete enabled."""
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=True,
            include_soft_delete=True,
            with_repository=True,
            overwrite=False,
        )

        # Read models file
        models_content = (temp_dir / "net_worth_snapshot.py").read_text()
        assert "tenant_id" in models_content
        assert "deleted_at" in models_content

        # Read repository
        repo_content = (temp_dir / "net_worth_snapshot_repository.py").read_text()
        assert "tenant_id" in repo_content
        assert "deleted_at" in repo_content

    def test_tenant_without_repository(self, temp_dir):
        """Test tenant flag without repository (edge case)."""
        result = scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=True,
            include_soft_delete=False,
            with_repository=False,
            overwrite=False,
        )

        # Models and schemas should have tenant_id
        models_content = (temp_dir / "net_worth_snapshot.py").read_text()
        assert "tenant_id" in models_content

        schemas_content = (temp_dir / "net_worth_snapshot_schemas.py").read_text()
        assert "tenant_id" in schemas_content

        # No repository file
        assert not (temp_dir / "net_worth_snapshot_repository.py").exists()

    def test_creates_missing_directory(self, tmp_path):
        """Test that scaffold creates destination directory if missing."""
        missing_dir = tmp_path / "does_not_exist" / "net_worth"

        result = scaffold_net_worth_core(
            dest_dir=missing_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Directory should be created
        assert missing_dir.exists()

        # Files should be present
        assert (missing_dir / "net_worth_snapshot.py").exists()

    def test_models_content_structure(self, temp_dir):
        """Test models file contains expected structure."""
        scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        models_content = (temp_dir / "net_worth_snapshot.py").read_text()

        # Check key components
        assert "class NetWorthSnapshot" in models_content
        assert "ModelBase" in models_content  # Should inherit from ModelBase
        assert '__tablename__ = "net_worth_snapshots"' in models_content
        assert "snapshot_date" in models_content
        assert "net_worth" in models_content
        assert "total_assets" in models_content
        assert "total_liabilities" in models_content

        # Check immutability (no updated_at field as actual column)
        # Note: "updated_at" may appear in comments, but not as a mapped_column
        assert "updated_at:" not in models_content or "no updated_at" in models_content.lower()

        # Check unique constraint
        assert "UniqueConstraint" in models_content or "unique" in models_content.lower()

    def test_schemas_content_structure(self, temp_dir):
        """Test schemas file contains expected structure."""
        scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        schemas_content = (temp_dir / "net_worth_snapshot_schemas.py").read_text()

        # Check schema classes
        assert "class NetWorthSnapshotBase" in schemas_content
        assert "class NetWorthSnapshotCreate" in schemas_content
        assert "class NetWorthSnapshotRead" in schemas_content

        # Check immutability (NO Update schema as actual class)
        # Note: "NetWorthSnapshotUpdate" may appear in comments explaining why it doesn't exist
        assert "class NetWorthSnapshotUpdate" not in schemas_content

        # Check field presence
        assert "snapshot_date" in schemas_content
        assert "net_worth" in schemas_content

    def test_repository_content_structure(self, temp_dir):
        """Test repository file contains expected structure."""
        scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        repo_content = (temp_dir / "net_worth_snapshot_repository.py").read_text()

        # Check repository class
        assert "class NetWorthSnapshotRepository" in repo_content

        # Check standard CRUD methods
        assert "async def create" in repo_content
        assert "async def get" in repo_content
        assert "async def list" in repo_content
        assert "async def delete" in repo_content

        # Check NO update method (immutable snapshots)
        assert "async def update" not in repo_content

        # Check time-series methods
        assert "get_latest" in repo_content or "get_by_date" in repo_content

    def test_readme_content(self, temp_dir):
        """Test README contains usage guide."""
        scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        readme_content = (temp_dir / "README.md").read_text()

        # Check sections
        assert "NetWorthSnapshot" in readme_content or "Net Worth" in readme_content
        assert "Usage" in readme_content or "Example" in readme_content

    def test_init_file_created(self, temp_dir):
        """Test __init__.py is created with correct exports."""
        scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        init_content = (temp_dir / "__init__.py").read_text()

        # Check imports
        assert "from .net_worth_snapshot import" in init_content
        assert "from .net_worth_snapshot_schemas import" in init_content
        assert "from .net_worth_snapshot_repository import" in init_content

        # Check __all__
        assert "__all__" in init_content
        assert "NetWorthSnapshot" in init_content
        assert "NetWorthSnapshotRepository" in init_content

    def test_path_object_input(self, tmp_path):
        """Test scaffold accepts Path object as dest_dir."""
        dest = tmp_path / "test_path_obj"

        result = scaffold_net_worth_core(
            dest_dir=dest,  # Pass Path object
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        assert dest.exists()
        assert (dest / "net_worth_snapshot.py").exists()

    def test_string_path_input(self, tmp_path):
        """Test scaffold accepts string path as dest_dir."""
        dest = str(tmp_path / "test_str_path")

        result = scaffold_net_worth_core(
            dest_dir=dest,  # Pass string path
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        assert Path(dest).exists()
        assert (Path(dest) / "net_worth_snapshot.py").exists()

    def test_immutable_snapshot_pattern(self, temp_dir):
        """Test that net_worth domain generates immutable snapshot pattern."""
        scaffold_net_worth_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Models should NOT have updated_at field (may appear in comments)
        models_content = (temp_dir / "net_worth_snapshot.py").read_text()
        assert "updated_at:" not in models_content or "no updated_at" in models_content.lower()

        # Schemas should NOT have Update schema class (may be mentioned in comments)
        schemas_content = (temp_dir / "net_worth_snapshot_schemas.py").read_text()
        assert "class NetWorthSnapshotUpdate" not in schemas_content

        # Repository should NOT have update() method
        repo_content = (temp_dir / "net_worth_snapshot_repository.py").read_text()
        assert "async def update(" not in repo_content

        # Should have time-series query methods
        assert "get_latest" in repo_content or "get_by_date" in repo_content


class TestGenerateInitContent:
    """Test _generate_init_content helper function."""

    def test_init_with_repository(self):
        """Test __init__.py generation with repository."""
        content = _generate_init_content(
            models_file="net_worth_snapshot.py",
            schemas_file="net_worth_snapshot_schemas.py",
            repo_file="net_worth_snapshot_repository.py",
        )

        assert "from .net_worth_snapshot import" in content
        assert "from .net_worth_snapshot_schemas import" in content
        assert "from .net_worth_snapshot_repository import NetWorthSnapshotRepository" in content
        assert "NetWorthSnapshotRepository" in content
        assert "__all__" in content

    def test_init_without_repository(self):
        """Test __init__.py generation without repository."""
        content = _generate_init_content(
            models_file="net_worth_snapshot.py",
            schemas_file="net_worth_snapshot_schemas.py",
            repo_file=None,
        )

        assert "from .net_worth_snapshot import" in content
        assert "from .net_worth_snapshot_schemas import" in content
        assert "NetWorthSnapshotRepository" not in content

    def test_init_custom_filenames(self):
        """Test __init__.py with custom filenames."""
        content = _generate_init_content(
            models_file="my_snapshot.py", schemas_file="my_schemas.py", repo_file="my_repo.py"
        )

        assert "from .my_snapshot import" in content
        assert "from .my_schemas import" in content
        assert "from .my_repo import" in content
