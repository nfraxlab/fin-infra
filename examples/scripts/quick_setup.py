#!/usr/bin/env python3
"""
Quick setup for fin-infra template project.

One-command setup that:
1. Validates models exist (via scaffold_models.py)
2. Runs database migrations (via alembic)

Target: Complete in < 30 seconds

Usage:
    python scripts/quick_setup.py                    # Full setup
    python scripts/quick_setup.py --skip-migrate     # Setup without migrations
    python scripts/quick_setup.py --check            # Check setup status only
    python scripts/quick_setup.py --help             # Show this help

Environment:
    SQL_URL: Database connection string (required)
             Example: postgresql+asyncpg://user:pass@localhost/dbname

Note:
    Currently uses alembic directly via poetry run. Will migrate to svc-infra's
    CLI command (python -m svc_infra.db setup-and-migrate) once it's implemented.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv not installed, try manual loading
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Strip inline comments (anything after #)
                    if "#" in value:
                        value = value.split("#")[0]
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def run_command(
    cmd: list[str], cwd: Path | None = None, check: bool = True
) -> tuple[int, str, str]:
    """
    Run a shell command and return (returncode, stdout, stderr).
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr


def check_sql_url() -> bool:
    """Check if SQL_URL is set."""
    sql_url = os.getenv("SQL_URL")
    if not sql_url:
        print("[X] SQL_URL environment variable not set")
        print("   Set it in .env or export it:")
        print('   export SQL_URL="postgresql+asyncpg://user:pass@localhost/dbname"')
        return False
    print(f"[OK] SQL_URL: {sql_url[:30]}...")
    return True


def check_models(project_root: Path) -> bool:
    """Check if models exist using scaffold_models.py."""
    print(" Checking models...")
    scaffold_script = project_root / "scripts" / "scaffold_models.py"

    if not scaffold_script.exists():
        print(f"[X] scaffold_models.py not found at {scaffold_script}")
        return False

    returncode, stdout, _stderr = run_command(
        [sys.executable, str(scaffold_script), "--check"],
        cwd=project_root,
        check=False,
    )

    if returncode == 0:
        print("[OK] All models exist")
        return True
    else:
        print("[!]  Some models missing or invalid")
        print(stdout)
        return False


def check_alembic_initialized(project_root: Path) -> bool:
    """Check if Alembic is initialized."""
    alembic_ini = project_root / "alembic.ini"
    migrations_dir = project_root / "migrations"

    if alembic_ini.exists() and migrations_dir.exists():
        return True
    return False


def setup_and_migrate(project_root: Path) -> bool:
    """
    Run database setup and migrations.

    This automatically:
    - Initializes Alembic (if needed)
    - Creates migration revision (if needed)
    - Applies migrations (upgrade to head)

    Note: Uses alembic directly for now. Will migrate to svc-infra CLI
    once python -m svc_infra.db is fully implemented.
    """
    print(" Running database setup and migrations...")

    # Check if alembic is initialized
    if not check_alembic_initialized(project_root):
        print("[X] Alembic not initialized. Run 'alembic init migrations' first.")
        return False

    # Run alembic upgrade via poetry to ensure correct environment
    returncode, stdout, stderr = run_command(
        ["poetry", "run", "alembic", "upgrade", "head"],
        cwd=project_root,
        check=False,
    )

    if returncode == 0:
        print("[OK] Database migrations complete")
        return True
    else:
        print("[X] Migrations failed")
        if stdout:
            print("STDOUT:", stdout)
        if stderr:
            print("STDERR:", stderr)
        return False


def check_setup_status(project_root: Path) -> dict:
    """Check the current setup status."""
    status = {}

    # Check SQL_URL
    status["sql_url"] = bool(os.getenv("SQL_URL"))

    # Check models
    scaffold_script = project_root / "scripts" / "scaffold_models.py"
    if scaffold_script.exists():
        returncode, _, _ = run_command(
            [sys.executable, str(scaffold_script), "--check"],
            cwd=project_root,
            check=False,
        )
        status["models"] = returncode == 0
    else:
        status["models"] = False

    # Check Alembic
    status["alembic"] = check_alembic_initialized(project_root)

    # Check migrations
    versions_dir = project_root / "migrations" / "versions"
    if versions_dir.exists():
        migrations = list(versions_dir.glob("*.py"))
        migrations = [
            m for m in migrations if m.name != "__init__.py" and "__pycache__" not in str(m)
        ]
        status["migrations"] = len(migrations) > 0
    else:
        status["migrations"] = False

    return status


def main():
    parser = argparse.ArgumentParser(
        description="Quick setup for fin-infra template project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Skip migration application (setup only)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check setup status only (non-destructive)",
    )

    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(" Quick Setup - fin-infra Template")
    print(f" Project root: {project_root}")
    print()

    start_time = time.time()

    # Check mode
    if args.check:
        print(" Checking setup status...")
        status = check_setup_status(project_root)

        print()
        print("Status:")
        print(f"   SQL_URL:    {'[OK]' if status['sql_url'] else '[X]'}")
        print(f"   Models:     {'[OK]' if status['models'] else '[X]'}")
        print(f"   Alembic:    {'[OK]' if status['alembic'] else '[X]'}")
        print(f"   Migrations: {'[OK]' if status['migrations'] else '[X]'}")
        print()

        all_good = all(status.values())
        if all_good:
            print("[OK] Setup complete!")
            return 0
        else:
            print("[!]  Setup incomplete")
            print("   Run: python scripts/quick_setup.py")
            return 1

    # Full setup
    print(" Running setup steps...")
    print()

    # Step 1: Check SQL_URL
    if not check_sql_url():
        return 1

    # Step 2: Check models
    if not check_models(project_root):
        print("[!]  Models check failed, but continuing...")

    # Step 3: Setup and migrate (unless skipped)
    # This uses svc-infra's setup-and-migrate which does:
    # - Initialize Alembic (if needed)
    # - Create migration revision (if needed)
    # - Apply migrations (upgrade to head)
    if not args.skip_migrate:
        if not setup_and_migrate(project_root):
            print("[X] Database setup and migrations failed")
            return 1
    else:
        print("⏭  Skipping migrations (--skip-migrate)")

    elapsed = time.time() - start_time
    print()
    print(f"[OK] Setup complete in {elapsed:.2f}s")

    if elapsed > 30:
        print("[!]  Setup took longer than 30s target")

    return 0


if __name__ == "__main__":
    sys.exit(main())
