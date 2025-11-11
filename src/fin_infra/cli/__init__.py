"""fin-infra CLI package.

Provides command-line tools for fin-infra functionality.
"""

import typer

from .cmds import scaffold_cmds

# Create main CLI app
app = typer.Typer(
    name="fin-infra",
    help="Financial infrastructure CLI - scaffold code, manage providers, etc.",
    add_completion=False,
)

# Register commands
scaffold_cmds.register(app)

__all__ = ["app"]
