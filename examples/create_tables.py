#!/usr/bin/env python
"""
Simple script to create database tables for the fin-infra-template example.

For demonstration purposes only. In production, use Alembic migrations via `make setup`.
"""

import asyncio
import sys
from pathlib import Path

# Add examples/src to path so we can import fin_infra_template
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fin_infra_template.db.base import Base
from fin_infra_template.db.models import (  # noqa: F401 - needed for metadata
    Account,
    Budget,
    Document,
    Goal,
    NetWorthSnapshot,
    Position,
    Transaction,
    User,
)


def get_engine():
    """Get async database engine from environment."""
    import os

    from sqlalchemy.ext.asyncio import create_async_engine

    db_url = os.getenv("SQL_URL", "sqlite+aiosqlite:////tmp/fin_infra_template.db")
    return create_async_engine(db_url, echo=False)


async def create_tables():
    """Create all tables defined in Base.metadata."""
    engine = get_engine()
    print(" Creating tables for fin-infra-template...")
    print(f"   Database: {engine.url}")

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    table_names = list(Base.metadata.tables.keys())
    print(f"\n[OK] Created {len(table_names)} database tables successfully!")
    print(f"   Tables: {', '.join(table_names)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
