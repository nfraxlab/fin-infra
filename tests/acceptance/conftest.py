"""Pytest configuration for fin-infra acceptance tests.

This conftest automatically loads environment variables from .env file
to make acceptance tests work seamlessly with local development setup.
"""

import os
from pathlib import Path


def pytest_configure(config):
    """Load .env file before running acceptance tests."""
    # Find .env file in project root
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        # Simple .env parser (no dependencies needed)
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
