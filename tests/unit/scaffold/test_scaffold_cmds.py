"""Unit tests for scaffold CLI commands.

Tests the scaffold command implementation directly using typer.testing.CliRunner
to ensure proper code coverage for CLI paths.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from fin_infra.cli.cmds.scaffold_cmds import cmd_scaffold

# Create a typer app for testing - register as default command (no subcommand name)
app = typer.Typer()
app.command()(cmd_scaffold)

runner = CliRunner()


class TestScaffoldCmdMissingDestDir:
    """Test error handling when --dest-dir is missing."""

    def test_missing_dest_dir_shows_error(self) -> None:
        """Test that missing --dest-dir produces appropriate error."""
        result = runner.invoke(app, ["budgets"])

        # typer/click handles missing required options - just verify non-zero exit
        assert result.exit_code != 0
        # Output contains error message (may have ANSI codes, check for "option" or "error")
        output_lower = result.output.lower()
        assert (
            "dest-dir" in output_lower
            or "required" in output_lower
            or "option" in output_lower
            or "error" in output_lower
            or "missing" in output_lower
        )


class TestScaffoldCmdUnknownDomain:
    """Test error handling for unknown domains."""

    def test_unknown_domain_shows_error(self) -> None:
        """Test that unknown domain produces error message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["unknown", "--dest-dir", tmpdir])

            assert result.exit_code != 0
            # Should mention invalid choice
            assert "invalid" in result.output.lower() or "not one of" in result.output.lower()


class TestScaffoldCmdValidDomains:
    """Test scaffold command with valid domains."""

    @pytest.mark.parametrize("domain", ["budgets", "goals"])
    def test_scaffold_creates_files(self, domain: str) -> None:
        """Test that valid domains create expected files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_path = Path(tmpdir) / domain

            result = runner.invoke(app, [domain, "--dest-dir", str(dest_path)])

            assert result.exit_code == 0, f"Failed: {result.output}"
            assert dest_path.exists()

            # Check success messages in output
            assert "Scaffold Results" in result.output or "Done" in result.output

    @pytest.mark.parametrize("domain", ["budgets", "goals"])
    def test_scaffold_with_all_flags(self, domain: str) -> None:
        """Test scaffold with all optional flags enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dest_path = Path(tmpdir) / domain

            result = runner.invoke(
                app,
                [
                    domain,
                    "--dest-dir",
                    str(dest_path),
                    "--include-tenant",
                    "--include-soft-delete",
                    "--with-repository",
                ],
            )

            assert result.exit_code == 0, f"Failed: {result.output}"

            # Verify files were created
            py_files = list(dest_path.glob("*.py"))
            assert len(py_files) >= 3, f"Expected at least 3 files, got {py_files}"
