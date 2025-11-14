"""
Net Worth domain scaffold generation.

This module provides functions to scaffold fin-infra net worth domain code: models, schemas,
repository, and __init__.py. Uses templates from fin_infra.net_worth.scaffold_templates.

Typical usage:
    from fin_infra.scaffold.net_worth import scaffold_net_worth_core
    result = scaffold_net_worth_core(
        dest_dir=Path("src/my_project/net_worth"),
        include_tenant=True,
        include_soft_delete=False,
        with_repository=True,
        overwrite=False
    )
    print(result["files"])
"""

from pathlib import Path
from typing import Any, Dict

from svc_infra.utils import (
    render_template,
    write,
    ensure_init_py,
)


def _generate_substitutions(
    include_tenant: bool = False,
    include_soft_delete: bool = False,
) -> Dict[str, str]:
    """
    Generate template substitutions for net_worth domain.

    Returns dict with 17 variables used across all templates:
    - Core (3): Entity, entity, table_name
    - Tenant (10): tenant_field, tenant_arg, tenant_arg_unique_index, tenant_arg_type,
                   tenant_arg_type_comma, tenant_arg_val, tenant_dict_assign, tenant_doc,
                   tenant_filter, tenant_field_* (for schemas)
    - Soft delete (4): soft_delete_field, soft_delete_filter, soft_delete_logic,
                       soft_delete_default
    - Schema (3): tenant_field_create, tenant_field_update, tenant_field_read

    Args:
        include_tenant: If True, generate tenant_id field patterns
        include_soft_delete: If True, generate deleted_at field patterns (NOTE: Net worth
                            snapshots are immutable by design, soft delete not recommended)

    Returns:
        Dict mapping variable names to their substitution values
    """
    subs: Dict[str, str] = {
        "Entity": "NetWorthSnapshot",
        "entity": "net_worth_snapshot",
        "table_name": "net_worth_snapshots",
    }

    # Tenant patterns (10 variables)
    if include_tenant:
        subs["tenant_field"] = (
            "\n    # Multi-tenancy (nullable for simple testing, set to False in production)\n    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)"
        )
        subs["tenant_arg"] = ", tenant_id: str"
        subs["tenant_arg_unique_index"] = ', tenant_field="tenant_id"'
        subs["tenant_arg_type"] = "tenant_id: str"
        subs["tenant_arg_type_comma"] = ",\n        tenant_id: str"
        subs["tenant_arg_val"] = ", tenant_id=tenant_id"
        subs["tenant_dict_assign"] = '\n        data["tenant_id"] = tenant_id'
        subs["tenant_doc"] = "\n        tenant_id: Tenant identifier for multi-tenant applications."
        subs["tenant_filter"] = ".where(NetWorthSnapshot.tenant_id == tenant_id)"
        subs["tenant_field_create"] = "\n    tenant_id: Optional[str] = None"
        subs["tenant_field_update"] = ""  # tenant_id immutable after creation
        subs["tenant_field_read"] = "\n    tenant_id: Optional[str] = None"
    else:
        subs["tenant_field"] = ""
        subs["tenant_arg"] = ""
        subs["tenant_arg_unique_index"] = ""
        subs["tenant_arg_type"] = ""
        subs["tenant_arg_type_comma"] = ""
        subs["tenant_arg_val"] = ""
        subs["tenant_dict_assign"] = ""
        subs["tenant_doc"] = ""
        subs["tenant_filter"] = ""
        subs["tenant_field_create"] = ""
        subs["tenant_field_update"] = ""
        subs["tenant_field_read"] = ""

    # Soft delete patterns (4 variables)
    # NOTE: Net worth snapshots are immutable by design, soft delete is unusual
    if include_soft_delete:
        subs["soft_delete_field"] = (
            "\n    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)"
        )
        subs["soft_delete_filter"] = ".where(NetWorthSnapshot.deleted_at.is_(None))"
        subs["soft_delete_logic"] = """
        # Soft delete
        snapshot.deleted_at = datetime.now(timezone.utc)
        await session.commit()"""
        subs["soft_delete_default"] = "True"
    else:
        subs["soft_delete_field"] = ""
        subs["soft_delete_filter"] = ""
        subs["soft_delete_logic"] = """
        # Hard delete
        await session.delete(snapshot)
        await session.commit()"""
        subs["soft_delete_default"] = "False"

    return subs


def _generate_init_content(
    models_file: str,
    schemas_file: str,
    repo_file: str | None,
) -> str:
    """
    Generate __init__.py content with re-exports.

    Args:
        models_file: Filename of models file (e.g., "net_worth_snapshot.py")
        schemas_file: Filename of schemas file (e.g., "net_worth_snapshot_schemas.py")
        repo_file: Filename of repository file (optional)

    Returns:
        Python code for __init__.py with imports and __all__
    """
    # Extract module names (remove .py extension)
    models_module = models_file.replace(".py", "")
    schemas_module = schemas_file.replace(".py", "")

    exports = [
        "NetWorthSnapshot",
        "create_net_worth_snapshot_service",
        "NetWorthSnapshotBase",
        "NetWorthSnapshotRead",
        "NetWorthSnapshotCreate",
    ]

    lines = [
        '"""Net Worth Snapshot persistence layer (generated by fin-infra scaffold)."""',
        "",
        f"from .{models_module} import NetWorthSnapshot, create_net_worth_snapshot_service",
        f"from .{schemas_module} import NetWorthSnapshotBase, NetWorthSnapshotRead, NetWorthSnapshotCreate",
    ]

    if repo_file:
        repo_module = repo_file.replace(".py", "")
        lines.append(f"from .{repo_module} import NetWorthSnapshotRepository")
        exports.append("NetWorthSnapshotRepository")

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


def scaffold_net_worth_core(
    dest_dir: Path,
    include_tenant: bool = False,
    include_soft_delete: bool = False,
    with_repository: bool = True,
    overwrite: bool = False,
    models_filename: str = "net_worth_snapshot.py",
    schemas_filename: str = "net_worth_snapshot_schemas.py",
    repository_filename: str = "net_worth_snapshot_repository.py",
) -> Dict[str, Any]:
    """
    Scaffold net worth domain files: models, schemas, repository (optional), and __init__.py.

    Generates production-ready code from templates in fin_infra.net_worth.scaffold_templates:
    - models.py.tmpl → NetWorthSnapshot model (immutable, no updated_at field)
    - schemas.py.tmpl → NetWorthSnapshotBase, NetWorthSnapshotCreate, NetWorthSnapshotRead
                       (NO Update schema - snapshots are immutable)
    - repository.py.tmpl → NetWorthSnapshotRepository with time-series queries
                          (get_latest, get_by_date, get_by_date_range, get_trend, calculate_growth)
    - README.md → Complete usage guide with snapshot patterns

    Args:
        dest_dir: Destination directory (will be created if missing)
        include_tenant: Add tenant_id field for multi-tenancy
        include_soft_delete: Add deleted_at field (NOTE: Unusual for immutable snapshots)
        with_repository: Generate repository file (default True)
        overwrite: Overwrite existing files (default False, skip if present)
        models_filename: Output filename for models (default "net_worth_snapshot.py")
        schemas_filename: Output filename for schemas (default "net_worth_snapshot_schemas.py")
        repository_filename: Output filename for repository (default "net_worth_snapshot_repository.py")

    Returns:
        Dict with "files" key containing list of {"path": str, "action": "wrote"|"skipped"}

    Example:
        >>> from pathlib import Path
        >>> from fin_infra.scaffold.net_worth import scaffold_net_worth_core
        >>> result = scaffold_net_worth_core(
        ...     dest_dir=Path("src/my_app/net_worth"),
        ...     include_tenant=True,
        ...     include_soft_delete=False,
        ...     with_repository=True,
        ...     overwrite=False
        ... )
        >>> result
        {
            "files": [
                {"path": "src/my_app/net_worth/net_worth_snapshot.py", "action": "wrote"},
                {"path": "src/my_app/net_worth/net_worth_snapshot_schemas.py", "action": "wrote"},
                {"path": "src/my_app/net_worth/net_worth_snapshot_repository.py", "action": "wrote"},
                {"path": "src/my_app/net_worth/__init__.py", "action": "wrote"}
            ]
        }
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Generate substitutions (17 variables)
    subs = _generate_substitutions(include_tenant, include_soft_delete)

    # Render templates from fin_infra.net_worth.scaffold_templates package
    models_content = render_template(
        "fin_infra.net_worth.scaffold_templates", "models.py.tmpl", subs
    )
    schemas_content = render_template(
        "fin_infra.net_worth.scaffold_templates", "schemas.py.tmpl", subs
    )
    readme_content = render_template("fin_infra.net_worth.scaffold_templates", "README.md", subs)

    if with_repository:
        repository_content = render_template(
            "fin_infra.net_worth.scaffold_templates", "repository.py.tmpl", subs
        )

    # Track all file operations
    files = []

    # Render and write models
    models_result = write(dest_dir / models_filename, models_content, overwrite=overwrite)
    files.append(models_result)

    # Render and write schemas
    schemas_result = write(dest_dir / schemas_filename, schemas_content, overwrite=overwrite)
    files.append(schemas_result)

    # Render and write repository (optional)
    if with_repository:
        repo_result = write(dest_dir / repository_filename, repository_content, overwrite=overwrite)
        files.append(repo_result)

    # Render and write README
    readme_result = write(dest_dir / "README.md", readme_content, overwrite=overwrite)
    files.append(readme_result)

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
