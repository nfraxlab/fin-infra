"""Scaffold CLI commands for generating persistence layer code.

Provides the `fin-infra scaffold` command for generating SQLAlchemy models,
Pydantic schemas, and repository implementations from templates.

Usage:
    fin-infra scaffold budgets --dest-dir app/models/
    fin-infra scaffold budgets --dest-dir app/models/ --include-tenant --include-soft-delete
    fin-infra scaffold goals --dest-dir app/models/ --with-repository
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
import typer

# Lazy imports for scaffold functions (only imported when command runs)
# This avoids circular imports and speeds up CLI startup


def cmd_scaffold(
    domain: str = typer.Argument(
        ...,
        help="Domain to scaffold (budgets, goals, net_worth)",
        click_type=click.Choice(["budgets", "goals", "net_worth"], case_sensitive=False),
    ),
    dest_dir: Path = typer.Option(
        ...,
        "--dest-dir",
        "-d",
        resolve_path=True,
        help="Destination directory for generated files",
    ),
    include_tenant: bool = typer.Option(
        False,
        "--include-tenant/--no-include-tenant",
        help="Add tenant_id field for multi-tenancy",
    ),
    include_soft_delete: bool = typer.Option(
        False,
        "--include-soft-delete/--no-include-soft-delete",
        help="Add deleted_at field for soft deletes",
    ),
    with_repository: bool = typer.Option(
        True,
        "--with-repository/--no-with-repository",
        help="Generate repository pattern implementation (optional - apps can use svc-infra SqlRepository)",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite/--no-overwrite",
        help="Overwrite existing files",
    ),
    models_filename: Optional[str] = typer.Option(
        None,
        "--models-filename",
        help="Custom filename for models (default: {domain}.py)",
    ),
    schemas_filename: Optional[str] = typer.Option(
        None,
        "--schemas-filename",
        help="Custom filename for schemas (default: {domain}_schemas.py)",
    ),
    repository_filename: Optional[str] = typer.Option(
        None,
        "--repository-filename",
        help="Custom filename for repository (default: {domain}_repository.py)",
    ),
) -> None:
    """Generate SQLAlchemy models, Pydantic schemas, and repository code from templates.
    
    The scaffold command generates production-ready persistence layer code that works
    seamlessly with svc-infra's add_sql_resources() for automatic CRUD APIs.
    
    Examples:
        # Basic scaffold (models + schemas + repository)
        fin-infra scaffold budgets --dest-dir app/models/
        
        # With multi-tenancy and soft deletes
        fin-infra scaffold budgets --dest-dir app/models/ \\
            --include-tenant --include-soft-delete
        
        # Without repository (use svc-infra SqlRepository directly)
        fin-infra scaffold goals --dest-dir app/models/ \\
            --no-with-repository
        
        # Custom filenames
        fin-infra scaffold budgets --dest-dir app/models/ \\
            --models-filename custom_budget.py \\
            --schemas-filename custom_schemas.py
    
    After scaffolding, integrate with svc-infra:
        1. Run migrations: svc-infra revision -m "add budgets" --autogenerate
        2. Apply: svc-infra upgrade head
        3. Wire CRUD: add_sql_resources(app, [SqlResource(model=Budget, ...)])
    """
    # Import scaffold function based on domain
    if domain == "budgets":
        from fin_infra.scaffold.budgets import scaffold_budgets_core

        result = scaffold_budgets_core(
            dest_dir=dest_dir,
            include_tenant=include_tenant,
            include_soft_delete=include_soft_delete,
            with_repository=with_repository,
            overwrite=overwrite,
            models_filename=models_filename or "budget.py",
            schemas_filename=schemas_filename or "budget_schemas.py",
            repository_filename=repository_filename or "budget_repository.py",
        )
    elif domain == "goals":
        from fin_infra.scaffold.goals import scaffold_goals_core

        result = scaffold_goals_core(
            dest_dir=dest_dir,
            include_tenant=include_tenant,
            include_soft_delete=include_soft_delete,
            with_repository=with_repository,
            overwrite=overwrite,
            models_filename=models_filename or "goal.py",
            schemas_filename=schemas_filename or "goal_schemas.py",
            repository_filename=repository_filename or "goal_repository.py",
        )
    elif domain == "net_worth":
        from fin_infra.scaffold.net_worth import scaffold_net_worth_core

        result = scaffold_net_worth_core(
            dest_dir=dest_dir,
            include_tenant=include_tenant,
            include_soft_delete=include_soft_delete,
            with_repository=with_repository,
            overwrite=overwrite,
            models_filename=models_filename or "net_worth_snapshot.py",
            schemas_filename=schemas_filename or "net_worth_snapshot_schemas.py",
            repository_filename=repository_filename or "net_worth_snapshot_repository.py",
        )
    else:
        typer.secho(
            f"❌ Unknown domain: {domain}. Must be one of: budgets, goals, net_worth",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    # Display results
    typer.echo("")
    typer.secho("📦 Scaffold Results:", bold=True)
    typer.echo("")

    files = result.get("files", [])
    wrote_count = 0
    skipped_count = 0

    for file_info in files:
        path = file_info["path"]
        action = file_info.get("action", "unknown")

        if action == "wrote":
            typer.secho(f"  ✓ Created: {path}", fg=typer.colors.GREEN)
            wrote_count += 1
        elif action == "skipped":
            reason = file_info.get("reason", "unknown")
            typer.secho(f"  ⊘ Skipped: {path} ({reason})", fg=typer.colors.YELLOW)
            skipped_count += 1
        else:
            typer.secho(f"  ? Unknown action for: {path}", fg=typer.colors.MAGENTA)

    # Summary
    typer.echo("")
    typer.secho(f"✨ Done! Created {wrote_count} file(s), skipped {skipped_count}.", bold=True)
    typer.echo("")

    # Next steps
    if wrote_count > 0:
        # Map domain to entity name for help text
        entity_map = {
            "budgets": "Budget",
            "goals": "Goal",
            "net_worth": "NetWorthSnapshot",
        }
        entity_name = entity_map.get(domain, domain.capitalize())

        # Map domain to route prefix
        prefix_map = {
            "budgets": "/budgets",
            "goals": "/goals",
            "net_worth": "/net-worth",
        }
        route_prefix = prefix_map.get(domain, f"/{domain}")

        typer.secho("📝 Next Steps:", bold=True)
        typer.echo("")
        typer.echo("  1. Review generated files and customize as needed")
        typer.echo("  2. Run migrations:")
        typer.echo(f"     svc-infra revision -m 'add {domain}' --autogenerate")
        typer.echo("     svc-infra upgrade head")
        typer.echo("  3. Wire automatic CRUD with svc-infra:")
        typer.echo("     from svc_infra.api.fastapi.db.sql import add_sql_resources, SqlResource")
        typer.echo("     add_sql_resources(app, [")
        typer.echo(
            f"         SqlResource(model={entity_name}, prefix='{route_prefix}', search_fields=['name'])"
        )
        typer.echo("     ])")
        typer.echo("")
        typer.echo("  See generated README.md for detailed integration guide.")
        typer.echo("")


def register(app: typer.Typer) -> None:
    """Register scaffold command with the main CLI app.

    Args:
        app: Main Typer application instance
    """
    app.command("scaffold", help="Generate persistence layer code from templates")(cmd_scaffold)


__all__ = ["cmd_scaffold", "register"]
