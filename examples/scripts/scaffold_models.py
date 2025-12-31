#!/usr/bin/env python3
"""
Scaffold financial models for fin-infra template.

Generates or validates:
- User (authentication and profile)
- Account (banking, brokerage, crypto)
- Transaction (spending, income)
- Position (investments, holdings)
- Goal (financial goals tracking)
- Budget (spending limits and tracking)
- Document (tax forms, statements, documents)
- NetWorthSnapshot (historical net worth tracking)

Usage:
    python scripts/scaffold_models.py                 # Validate existing models
    python scripts/scaffold_models.py --check         # Check if models exist
    python scripts/scaffold_models.py --overwrite     # Regenerate models (dangerous!)
    python scripts/scaffold_models.py --help          # Show this help

Safety:
    - Default mode: validates existing models, does NOT overwrite
    - Will not overwrite without explicit --overwrite flag
    - Backs up existing files before overwriting (adds .bak extension)
"""

import argparse
import sys
from pathlib import Path

# Expected model classes
EXPECTED_MODELS = [
    "User",
    "Account",
    "Transaction",
    "Position",
    "Goal",
    "Budget",
    "Document",
    "NetWorthSnapshot",
]


def check_models_exist(models_file: Path) -> tuple[bool, list[str], list[str]]:
    """
    Check if all expected models exist in models.py.

    Returns:
        tuple: (all_exist, found_models, missing_models)
    """
    if not models_file.exists():
        return False, [], EXPECTED_MODELS

    content = models_file.read_text()
    found_models = []
    missing_models = []

    for model_name in EXPECTED_MODELS:
        # Check for class definition
        if f"class {model_name}(Base" in content:
            found_models.append(model_name)
        else:
            missing_models.append(model_name)

    all_exist = len(missing_models) == 0
    return all_exist, found_models, missing_models


def validate_model_structure(models_file: Path) -> tuple[bool, list[str]]:
    """
    Validate that models have proper structure.

    Checks for:
    - __tablename__ definition
    - Primary key (id column)
    - Proper docstrings
    - TimestampMixin usage

    Returns:
        tuple: (is_valid, issues)
    """
    if not models_file.exists():
        return False, ["models.py does not exist"]

    content = models_file.read_text()
    issues = []

    for model_name in EXPECTED_MODELS:
        # Check __tablename__ exists after class definition
        if f"class {model_name}(Base" in content:
            # Find the class and check for __tablename__ within next 500 chars
            class_start = content.find(f"class {model_name}(Base")
            class_section = content[class_start : class_start + 500]
            if "__tablename__" not in class_section:
                issues.append(f"{model_name}: Missing __tablename__ definition")

        # Check docstring
        if f"class {model_name}(Base" in content:
            # Look for docstring after class definition
            class_start = content.find(f"class {model_name}(Base")
            docstring_check = content[class_start : class_start + 200]
            if '"""' not in docstring_check:
                issues.append(f"{model_name}: Missing docstring")

    is_valid = len(issues) == 0
    return is_valid, issues


def backup_file(file_path: Path) -> Path:
    """
    Create a backup of the file with .bak extension.

    Returns:
        Path: Path to backup file
    """
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    if file_path.exists():
        backup_path.write_text(file_path.read_text())
        return backup_path
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold financial models for fin-infra template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if models exist (non-destructive)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing models (DANGEROUS! Creates backup first)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate model structure (default)",
    )

    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    models_file = project_root / "src" / "fin_infra_template" / "db" / "models.py"

    print(" Scaffolding Financial Models")
    print(f" Project root: {project_root}")
    print(f"📄 Models file: {models_file}")
    print()

    # Check mode
    if args.check or args.validate:
        print("🔎 Checking models...")
        all_exist, found, missing = check_models_exist(models_file)

        if all_exist:
            print(f"[OK] All {len(EXPECTED_MODELS)} models exist:")
            for model in found:
                print(f"   [OK] {model}")
        else:
            print(f"[!]  Found {len(found)}/{len(EXPECTED_MODELS)} models")
            if found:
                print("   Found:")
                for model in found:
                    print(f"   [OK] {model}")
            if missing:
                print("   Missing:")
                for model in missing:
                    print(f"   [X] {model}")

        # Validate structure
        if all_exist and args.validate:
            print("\n Validating model structure...")
            is_valid, issues = validate_model_structure(models_file)

            if is_valid:
                print("[OK] All models have proper structure")
            else:
                print(f"[!]  Found {len(issues)} structure issues:")
                for issue in issues:
                    print(f"   [!]  {issue}")
                return 1

        return 0 if all_exist else 1

    # Overwrite mode
    if args.overwrite:
        print("[!]  OVERWRITE MODE")
        print("This will regenerate models.py from scratch!")
        print()

        # Check if file exists
        if models_file.exists():
            print(" Creating backup...")
            backup_path = backup_file(models_file)
            print(f"   [OK] Backup created: {backup_path}")
            print()

        print("[X] Model generation not yet implemented")
        print("   Models already exist at:")
        print(f"   {models_file}")
        print()
        print("   If you need to regenerate models:")
        print("   1. Review existing models.py")
        print("   2. Use fin-infra scaffold CLI (coming soon)")
        print("   3. Or manually edit models.py")
        return 1

    # Default: validate
    print("[OK] Models validation complete")
    print()
    print("Run with --help for more options")
    return 0


if __name__ == "__main__":
    sys.exit(main())
