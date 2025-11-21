"""
Unit tests for fin_infra.scaffold.holdings module.

Tests the scaffold_holdings_core() function and its helper functions, verifying:
- Template variable generation (_generate_substitutions)
- File creation and content rendering
- Overwrite protection
- Custom filenames
- All flag combinations (tenant, soft_delete, with_repository)
- Holdings specific features (mostly immutable snapshots, Update schema for notes only)
"""

import shutil
from pathlib import Path

import pytest

from fin_infra.scaffold.holdings import (
    scaffold_holdings_core,
    _generate_substitutions,
    _generate_init_content,
)


class TestGenerateSubstitutions:
    """Test _generate_substitutions helper function."""

    def test_basic_substitutions(self):
        """Test basic substitutions without any flags."""
        subs = _generate_substitutions(include_tenant=False, include_soft_delete=False)

        assert subs["Entity"] == "HoldingSnapshot"
        assert subs["entity"] == "holding_snapshot"
        assert subs["table_name"] == "holding_snapshots"

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
        assert subs["Entity"] == "HoldingSnapshot"

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


class TestScaffoldHoldingsCore:
    """Test scaffold_holdings_core main function."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for test output."""
        test_dir = tmp_path / "test_holdings"
        test_dir.mkdir()
        yield test_dir
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)

    def test_basic_scaffold(self, temp_dir):
        """Test basic scaffold without tenant or soft_delete."""
        result = scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Check files were created
        assert len(result["files"]) == 5  # models, schemas, repository, README, __init__

        # Check all files exist
        assert (temp_dir / "holding_snapshot.py").exists()
        assert (temp_dir / "holding_snapshot_schemas.py").exists()
        assert (temp_dir / "holding_snapshot_repository.py").exists()
        assert (temp_dir / "README.md").exists()
        assert (temp_dir / "__init__.py").exists()

        # Verify models content
        models_content = (temp_dir / "holding_snapshot.py").read_text()
        assert "class HoldingSnapshot(ModelBase):" in models_content
        assert "holding_snapshots" in models_content
        assert "tenant_id" not in models_content  # Tenant disabled
        assert "deleted_at" not in models_content  # Soft delete disabled
        assert "total_value" in models_content
        assert "holdings_data" in models_content
        assert "provider" in models_content

        # Verify schemas content
        schemas_content = (temp_dir / "holding_snapshot_schemas.py").read_text()
        assert "class HoldingSnapshotBase(BaseModel):" in schemas_content
        assert "class HoldingSnapshotCreate(HoldingSnapshotBase):" in schemas_content
        assert "class HoldingSnapshotRead(HoldingSnapshotBase, Timestamped):" in schemas_content
        assert "class HoldingSnapshotUpdate(BaseModel):" in schemas_content  # Update for notes
        assert "notes" in schemas_content

        # Verify repository content
        repo_content = (temp_dir / "holding_snapshot_repository.py").read_text()
        assert "class HoldingSnapshotRepository:" in repo_content
        assert "async def get_latest(" in repo_content
        assert "async def calculate_performance(" in repo_content
        assert "async def get_trend(" in repo_content

        # Verify __init__.py content
        init_content = (temp_dir / "__init__.py").read_text()
        assert "from .holding_snapshot import HoldingSnapshot" in init_content
        assert "HoldingSnapshotCreate" in init_content
        assert "HoldingSnapshotUpdate" in init_content
        assert "HoldingSnapshotRepository" in init_content

    def test_scaffold_with_tenant(self, temp_dir):
        """Test scaffold with tenant_id enabled."""
        result = scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=True,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        models_content = (temp_dir / "holding_snapshot.py").read_text()
        assert "tenant_id" in models_content

        schemas_content = (temp_dir / "holding_snapshot_schemas.py").read_text()
        assert "tenant_id" in schemas_content

    def test_scaffold_with_soft_delete(self, temp_dir):
        """Test scaffold with soft_delete enabled."""
        result = scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=True,
            with_repository=True,
            overwrite=False,
        )

        models_content = (temp_dir / "holding_snapshot.py").read_text()
        assert "deleted_at" in models_content

    def test_scaffold_without_repository(self, temp_dir):
        """Test scaffold without repository file."""
        result = scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=False,
            overwrite=False,
        )

        # Check files (no repository)
        assert len(result["files"]) == 4  # models, schemas, README, __init__
        assert (temp_dir / "holding_snapshot.py").exists()
        assert (temp_dir / "holding_snapshot_schemas.py").exists()
        assert not (temp_dir / "holding_snapshot_repository.py").exists()
        assert (temp_dir / "README.md").exists()

        # Verify __init__.py doesn't import repository
        init_content = (temp_dir / "__init__.py").read_text()
        assert "HoldingSnapshotRepository" not in init_content

    def test_custom_filenames(self, temp_dir):
        """Test scaffold with custom filenames."""
        result = scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
            models_filename="custom_models.py",
            schemas_filename="custom_schemas.py",
            repository_filename="custom_repo.py",
        )

        # Check custom filenames
        assert (temp_dir / "custom_models.py").exists()
        assert (temp_dir / "custom_schemas.py").exists()
        assert (temp_dir / "custom_repo.py").exists()

        # Verify __init__.py imports use custom names
        init_content = (temp_dir / "__init__.py").read_text()
        assert "from .custom_models import" in init_content
        assert "from .custom_schemas import" in init_content
        assert "from .custom_repo import" in init_content

    def test_overwrite_protection(self, temp_dir):
        """Test that existing files are not overwritten by default."""
        # First scaffold
        result1 = scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )
        assert all(f["action"] == "wrote" for f in result1["files"])

        # Second scaffold (should skip existing files)
        result2 = scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )
        assert all(f["action"] == "skipped" for f in result2["files"])

    def test_overwrite_enabled(self, temp_dir):
        """Test that overwrite=True replaces existing files."""
        # First scaffold
        scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        # Second scaffold with overwrite=True
        result = scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=True,
        )
        assert all(f["action"] == "wrote" for f in result["files"])


class TestGenerateInitContent:
    """Test _generate_init_content helper function."""

    def test_init_with_repository(self):
        """Test __init__.py generation with repository."""
        content = _generate_init_content(
            models_file="holding_snapshot.py",
            schemas_file="holding_snapshot_schemas.py",
            repo_file="holding_snapshot_repository.py",
        )

        assert "from .holding_snapshot import" in content
        assert "from .holding_snapshot_schemas import" in content
        assert "from .holding_snapshot_repository import HoldingSnapshotRepository" in content
        assert '"HoldingSnapshotRepository"' in content
        assert '"HoldingSnapshot"' in content
        assert '"HoldingSnapshotCreate"' in content
        assert '"HoldingSnapshotUpdate"' in content

    def test_init_without_repository(self):
        """Test __init__.py generation without repository."""
        content = _generate_init_content(
            models_file="holding_snapshot.py",
            schemas_file="holding_snapshot_schemas.py",
            repo_file=None,
        )

        assert "from .holding_snapshot import" in content
        assert "from .holding_snapshot_schemas import" in content
        assert "HoldingSnapshotRepository" not in content
        assert '"HoldingSnapshot"' in content
        assert '"HoldingSnapshotCreate"' in content
        assert '"HoldingSnapshotUpdate"' in content

    def test_init_with_custom_filenames(self):
        """Test __init__.py generation with custom filenames."""
        content = _generate_init_content(
            models_file="custom_models.py",
            schemas_file="custom_schemas.py",
            repo_file="custom_repo.py",
        )

        assert "from .custom_models import" in content
        assert "from .custom_schemas import" in content
        assert "from .custom_repo import" in content


class TestHoldingsSpecificFeatures:
    """Test holdings-specific features."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for test output."""
        test_dir = tmp_path / "test_holdings_features"
        test_dir.mkdir()
        yield test_dir
        if test_dir.exists():
            shutil.rmtree(test_dir)

    def test_update_schema_exists(self, temp_dir):
        """Test that Update schema exists (for notes field)."""
        scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        schemas_content = (temp_dir / "holding_snapshot_schemas.py").read_text()
        assert "class HoldingSnapshotUpdate(BaseModel):" in schemas_content
        assert "notes:" in schemas_content  # Only notes can be updated

    def test_repository_has_update_method(self, temp_dir):
        """Test that repository has update method (for notes)."""
        scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        repo_content = (temp_dir / "holding_snapshot_repository.py").read_text()
        assert "async def update(" in repo_content
        assert "notes" in repo_content

    def test_holdings_specific_fields(self, temp_dir):
        """Test holdings-specific fields in model."""
        scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        models_content = (temp_dir / "holding_snapshot.py").read_text()
        assert "total_value" in models_content
        assert "total_cost_basis" in models_content
        assert "total_unrealized_gain_loss" in models_content
        assert "holdings_count" in models_content
        assert "holdings_data" in models_content
        assert "provider" in models_content
        assert "provider_metadata" in models_content

    def test_performance_calculation_method(self, temp_dir):
        """Test repository has performance calculation method."""
        scaffold_holdings_core(
            dest_dir=temp_dir,
            include_tenant=False,
            include_soft_delete=False,
            with_repository=True,
            overwrite=False,
        )

        repo_content = (temp_dir / "holding_snapshot_repository.py").read_text()
        assert "async def calculate_performance(" in repo_content
        assert "absolute_return" in repo_content
        assert "percent_return" in repo_content
        assert "annualized_return" in repo_content
