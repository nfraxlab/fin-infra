"""fin-infra CLI entrypoint.

Run with: python -m fin_infra or fin-infra (if installed)
"""

from __future__ import annotations

from fin_infra.cli import app


def main() -> None:
    """Main CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
