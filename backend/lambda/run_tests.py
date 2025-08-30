#!/usr/bin/env python3
"""Test runner script for Lingible backend."""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} failed")
        if result.stderr:
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
        return False

    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run Lingible backend tests")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "all"],
        default="unit",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run only fast tests (skip slow markers)"
    )

    args = parser.parse_args()

    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)

    print("🧪 Lingible Backend Test Runner")
    print("=" * 50)

    # Build pytest command
    pytest_cmd = ["python", "-m", "pytest"]

    if args.type == "unit":
        pytest_cmd.extend(["-m", "unit"])
    elif args.type == "integration":
        pytest_cmd.extend(["-m", "integration"])
    # "all" runs all tests

    if args.coverage:
        pytest_cmd.extend([
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ])

    if args.verbose:
        pytest_cmd.append("-v")

    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])

    # Add test path
    pytest_cmd.append("tests/")

    # Run tests
    cmd_str = " ".join(pytest_cmd)
    success = run_command(cmd_str, f"Running {args.type} tests")

    if args.coverage and success:
        print("\n📊 Coverage report generated in htmlcov/index.html")

    # Run linting
    print("\n🔍 Running code quality checks...")

    lint_success = True
    lint_success &= run_command("black --check src/", "Black formatting check")
    lint_success &= run_command("flake8 src/", "Flake8 linting")
    lint_success &= run_command("mypy src/", "MyPy type checking")

    if success and lint_success:
        print("\n🎉 All tests and checks passed!")
        return 0
    else:
        print("\n💥 Some tests or checks failed!")
        return 1


if __name__ == "__main__":
    import os
    sys.exit(main())
