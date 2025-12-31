"""Alembic async migrations environment for fin-infra-template."""

from __future__ import annotations

import importlib
import logging
import os
import pathlib
import sys

from alembic import context
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine
from svc_infra.db.sql.utils import _ensure_ssl_default_async as _ensure_ssl_default
from svc_infra.db.sql.utils import get_database_url_from_env

# Logging
config = context.config
if config.config_file_name is not None:
    import logging.config as _lc

    _lc.fileConfig(config.config_file_name)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# sys.path bootstrap
script_loc = config.get_main_option("script_location") or os.path.dirname(__file__)
migrations_dir = pathlib.Path(script_loc).resolve()
project_root = migrations_dir.parent

# Add project root and src to path
for path in [project_root, project_root / "src"]:
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.append(path_str)

# Get database URL
env_dburl = os.getenv("SQL_URL", "").strip()
try:
    helper_dburl = get_database_url_from_env(required=False) or ""
except Exception:
    helper_dburl = ""
ini_dburl = (config.get_main_option("sqlalchemy.url") or "").strip()

effective_url = env_dburl or helper_dburl or ini_dburl
if not effective_url:
    raise RuntimeError(
        "No database URL found. Set SQL_URL environment variable or provide --database-url."
    )


def _coerce_to_async(u: URL) -> URL:
    """Convert synchronous database URLs to async equivalents."""
    dn = (u.drivername or "").lower()
    if "+asyncpg" in dn or "+aiomysql" in dn or "+aiosqlite" in dn:
        return u
    backend = (u.get_backend_name() or "").lower()
    if backend in ("postgresql", "postgres"):
        return u.set(drivername="postgresql+asyncpg")
    if backend == "mysql":
        return u.set(drivername="mysql+aiomysql")
    if backend == "sqlite":
        return u.set(drivername="sqlite+aiosqlite")
    return u


# Configure URL
u = make_url(effective_url)
u = _coerce_to_async(u)
u = _ensure_ssl_default(u)
config.set_main_option("sqlalchemy.url", u.render_as_string(hide_password=False))


def _collect_metadata() -> list[object]:
    """Discover all SQLAlchemy metadata objects from fin_infra_template.db.models."""
    found: list[object] = []

    # Import fin_infra_template models
    try:
        mod = importlib.import_module("fin_infra_template.db.models")
        context.config.print_stdout("[alembic env] Imported fin_infra_template.db.models")
    except Exception as e:
        context.config.print_stdout(
            f"[alembic env] ERROR importing fin_infra_template.db.models: {e}"
        )
        raise

    # Look for metadata objects
    for attr in ("metadata", "MetaData", "Base", "base"):
        obj = getattr(mod, attr, None)
        if obj is not None:
            md = getattr(obj, "metadata", None) or obj
            if hasattr(md, "tables") and md.tables:
                found.append(md)
                break

    # Get ModelBase metadata from svc-infra
    try:
        from svc_infra.db.sql.base import ModelBase

        mb_md = getattr(ModelBase, "metadata", None)
        if mb_md is not None and getattr(mb_md, "tables", {}):
            # Only add if not already in found
            if not any(id(md) == id(mb_md) for md in found):
                found.append(mb_md)
            context.config.print_stdout(
                f"[alembic env] Found ModelBase.metadata with {len(mb_md.tables)} tables"
            )
    except Exception as e:
        context.config.print_stdout(f"[alembic env] WARNING: Could not import ModelBase: {e}")

    total_tables = sum(len(getattr(md, "tables", {})) for md in found)
    context.config.print_stdout(
        f"[alembic env] Discovered {len(found)} metadata objects with {total_tables} tables total"
    )

    if total_tables == 0:
        raise RuntimeError(
            "No tables found! Make sure fin_infra_template.db.models is importing correctly."
        )

    return found


target_metadata = _collect_metadata()


def _do_run_migrations(connection):
    """Configure and run migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        version_table="alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in online mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.config.print_stdout(f"[alembic env] Connecting to database: {url}")

    engine = create_async_engine(url)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline mode not supported. Run migrations with online database connection.")
else:
    import asyncio as _asyncio

    _asyncio.run(run_migrations_online())
