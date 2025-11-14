"""Budget scaffold implementation.

Generates SQLAlchemy models, Pydantic schemas, and repository code for budgets
from templates. Uses svc-infra's template utilities to avoid duplication.

Typical usage:
    result = scaffold_budgets_core(
        dest_dir=Path("app/models"),
        include_tenant=True,
        include_soft_delete=True,
        with_repository=True,
        overwrite=False,
    )

    for file_info in result["files"]:
        print(f"{file_info['action']}: {file_info['path']}")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

# Use svc-infra's scaffold utilities to avoid duplication
from svc_infra.utils import render_template, write, ensure_init_py


def scaffold_budgets_core(
    dest_dir: Path,
    include_tenant: bool = False,
    include_soft_delete: bool = False,
    with_repository: bool = True,
    overwrite: bool = False,
    models_filename: Optional[str] = None,
    schemas_filename: Optional[str] = None,
    repository_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate budget persistence code from templates.

    Args:
        dest_dir: Destination directory for generated files (created if missing)
        include_tenant: Add tenant_id field for multi-tenancy (default: False)
        include_soft_delete: Add deleted_at field for soft deletes (default: False)
        with_repository: Generate repository implementation (default: True)
        overwrite: Overwrite existing files (default: False, skip if exists)
        models_filename: Custom filename for models (default: "budget.py")
        schemas_filename: Custom filename for schemas (default: "budget_schemas.py")
        repository_filename: Custom filename for repository (default: "budget_repository.py")

    Returns:
        Dictionary with "files" key containing list of file info dicts:
        [{"path": str, "action": "wrote|skipped", "reason": str}, ...]

    Example:
        >>> result = scaffold_budgets_core(
        ...     dest_dir=Path("app/models"),
        ...     include_tenant=True,
        ...     include_soft_delete=True,
        ... )
        >>> result["files"][0]
        {"path": "app/models/budget.py", "action": "wrote"}
    """
    # Set default filenames
    models_filename = models_filename or "budget.py"
    schemas_filename = schemas_filename or "budget_schemas.py"
    repository_filename = repository_filename or "budget_repository.py"

    # Ensure dest_dir is a Path object
    dest_dir = Path(dest_dir)

    # Generate template substitutions
    subs = _generate_substitutions(include_tenant, include_soft_delete)

    # Track all file operations
    files: List[Dict[str, Any]] = []

    # Render and write models
    models_content = render_template("fin_infra.budgets.scaffold_templates", "models.py.tmpl", subs)
    models_result = write(dest_dir / models_filename, models_content, overwrite)
    files.append(models_result)

    # Render and write schemas
    schemas_content = render_template(
        "fin_infra.budgets.scaffold_templates", "schemas.py.tmpl", subs
    )
    schemas_result = write(dest_dir / schemas_filename, schemas_content, overwrite)
    files.append(schemas_result)

    # Render and write repository (optional)
    if with_repository:
        repo_content = render_template(
            "fin_infra.budgets.scaffold_templates", "repository.py.tmpl", subs
        )
        repo_result = write(dest_dir / repository_filename, repo_content, overwrite)
        files.append(repo_result)

    # Generate __init__.py with re-exports
    init_content = _generate_init_content(
        models_filename,
        schemas_filename,
        repository_filename if with_repository else None,
    )
    init_result = ensure_init_py(
        dest_dir,
        overwrite=overwrite,
        paired=True,  # Generate re-exports
        content=init_content,
    )
    files.append(init_result)

    return {"files": files}


def _generate_substitutions(
    include_tenant: bool,
    include_soft_delete: bool,
) -> Dict[str, str]:
    """Generate template variable substitutions for budgets.

    Args:
        include_tenant: Whether to include tenant_id field
        include_soft_delete: Whether to include deleted_at field

    Returns:
        Dictionary mapping template variables to their values
    """
    return {
        # Core variables (always present)
        "Entity": "Budget",
        "entity": "budget",
        "table_name": "budgets",
        # Conditional field definitions
        "tenant_field": _tenant_field() if include_tenant else "",
        "soft_delete_field": _soft_delete_field() if include_soft_delete else "",
        # Conditional arguments for functions
        "tenant_arg": ", tenant_id: str" if include_tenant else "",
        "tenant_arg_unique_index": ', tenant_field="tenant_id"' if include_tenant else "",
        "tenant_default": '"tenant_id"' if include_tenant else "None",
        "tenant_arg_type": ", tenant_id: Optional[str] = None" if include_tenant else "",
        "tenant_arg_type_comma": ", tenant_id: Optional[str] = None" if include_tenant else "",
        "tenant_arg_val": ", tenant_id=tenant_id" if include_tenant else "",
        "tenant_doc": "        tenant_id: Optional tenant identifier for filtering\n"
        if include_tenant
        else "",
        # Conditional query filters
        "tenant_filter": _tenant_filter() if include_tenant else "",
        "soft_delete_filter": _soft_delete_filter() if include_soft_delete else "",
        "soft_delete_default": "False" if include_soft_delete else "None",
        # Conditional soft delete logic
        "soft_delete_logic": _soft_delete_logic()
        if include_soft_delete
        else _soft_delete_hard_delete_fallback(),
        # Conditional schema fields
        "tenant_field_create": _tenant_field_schema_create() if include_tenant else "",
        "tenant_field_update": _tenant_field_schema_update() if include_tenant else "",
        "tenant_field_read": _tenant_field_schema_read() if include_tenant else "",
    }


def _tenant_field() -> str:
    """Generate tenant_id field definition for SQLAlchemy model."""
    return """
    # multi-tenancy (nullable for simple testing, set to False in production)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
"""


def _soft_delete_field() -> str:
    """Generate deleted_at field definition for SQLAlchemy model."""
    return """
    # soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
"""


def _tenant_filter() -> str:
    """Generate tenant_id filter for repository queries."""
    return """
        if tenant_id is not None:
            stmt = stmt.where(Budget.tenant_id == tenant_id)
"""


def _soft_delete_filter() -> str:
    """Generate deleted_at filter for repository queries."""
    return """
        # Exclude soft-deleted records
        stmt = stmt.where(Budget.deleted_at.is_(None))
"""


def _soft_delete_logic() -> str:
    """Generate soft delete implementation for repository."""
    return """            # Soft delete: set deleted_at timestamp
            await self.update(budget_id, {"deleted_at": datetime.now(timezone.utc)}, tenant_id)
"""


def _soft_delete_hard_delete_fallback() -> str:
    """Generate hard delete when soft delete is not enabled."""
    return """            # Hard delete only (soft delete not enabled)
            await self.session.delete(budget)
"""


def _tenant_field_schema_create() -> str:
    """Generate tenant_id field for Pydantic create schema."""
    return """
    tenant_id: Optional[str] = None
"""


def _tenant_field_schema_update() -> str:
    """Generate tenant_id field for Pydantic update schema."""
    return """
    tenant_id: Optional[str] = None
"""


def _tenant_field_schema_read() -> str:
    """Generate tenant_id field for Pydantic read schema."""
    return """
    tenant_id: str
"""


def _generate_init_content(
    models_file: str,
    schemas_file: str,
    repo_file: Optional[str],
) -> str:
    """Generate __init__.py content with re-exports.

    Args:
        models_file: Filename of models file (e.g., "budget.py")
        schemas_file: Filename of schemas file (e.g., "budget_schemas.py")
        repo_file: Filename of repository file (optional)

    Returns:
        Python code for __init__.py with imports and __all__
    """
    # Extract module names (remove .py extension)
    models_module = models_file.replace(".py", "")
    schemas_module = schemas_file.replace(".py", "")

    exports = [
        "Budget",
        "create_budget_service",
        "BudgetBase",
        "BudgetRead",
        "BudgetCreate",
        "BudgetUpdate",
    ]

    lines = [
        '"""Budget persistence layer (generated by fin-infra scaffold)."""',
        "",
        f"from .{models_module} import Budget, create_budget_service",
        f"from .{schemas_module} import BudgetBase, BudgetRead, BudgetCreate, BudgetUpdate",
    ]

    if repo_file:
        repo_module = repo_file.replace(".py", "")
        lines.append(f"from .{repo_module} import BudgetRepository")
        exports.append("BudgetRepository")

    lines.extend(
        [
            "",
            "__all__ = [",
        ]
    )

    for export in exports:
        lines.append(f'    "{export}",')

    lines.append("]")

    return "\n".join(lines) + "\n"


__all__ = ["scaffold_budgets_core"]
