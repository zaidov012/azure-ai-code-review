#!/usr/bin/env python3
"""
Test runner script for Azure DevOps AI PR Review Extension.

This script runs all tests with proper configuration and generates coverage reports.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, cwd=None, env=None):
    """Run a command and return the result."""
    print(f"\n▶ Running: {' '.join(cmd)}")
    print("=" * 80)
    
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env or os.environ.copy(),
        capture_output=False,
        text=True
    )
    
    print("=" * 80)
    
    if result.returncode != 0:
        print(f"❌ Command failed with exit code {result.returncode}")
        return False
    else:
        print(f"✅ Command succeeded")
        return True


def run_python_tests(args):
    """Run Python tests with pytest."""
    print("\n" + "=" * 80)
    print("🐍 Running Python Tests")
    print("=" * 80)
    
    repo_root = Path(__file__).parent.parent
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    if args.verbose:
        cmd.append("-v")
    
    if args.coverage:
        cmd.extend([
            "--cov=task/src_python/src",
            "--cov-report=term-missing",
            "--cov-report=html:coverage/html",
            "--cov-report=xml:coverage/coverage.xml",
        ])
    
    if args.markers:
        cmd.extend(["-m", args.markers])
    
    if args.test_path:
        cmd.append(args.test_path)
    else:
        cmd.append("tests/")
    
    if args.parallel:
        cmd.extend(["-n", "auto"])
    
    success = run_command(cmd, cwd=repo_root)
    
    if args.coverage and success:
        print("\n📊 Coverage report generated:")
        print(f"   HTML: {repo_root / 'coverage' / 'html' / 'index.html'}")
        print(f"   XML:  {repo_root / 'coverage' / 'coverage.xml'}")
    
    return success


def run_typescript_tests(args):
    """Run TypeScript tests with Jest."""
    print("\n" + "=" * 80)
    print("📘 Running TypeScript Tests")
    print("=" * 80)
    
    repo_root = Path(__file__).parent.parent
    task_dir = repo_root / "task"
    
    if not (task_dir / "node_modules").exists():
        print("\n⚠️  Node modules not found. Installing dependencies...")
        npm_install = run_command(["npm", "install"], cwd=task_dir)
        if not npm_install:
            print("❌ Failed to install npm dependencies")
            return False
    
    # Build Jest command
    cmd = ["npm", "test"]
    
    if args.coverage:
        cmd = ["npm", "run", "test:coverage"]
    
    success = run_command(cmd, cwd=task_dir)
    
    if args.coverage and success:
        print(f"\n📊 Coverage report generated: {task_dir / 'coverage' / 'index.html'}")
    
    return success


def run_linters(args):
    """Run linters and code quality tools."""
    print("\n" + "=" * 80)
    print("🔍 Running Linters")
    print("=" * 80)
    
    repo_root = Path(__file__).parent.parent
    success = True
    
    # Run flake8
    if args.lint_python:
        print("\n▶ Running flake8...")
        flake8_success = run_command(
            [sys.executable, "-m", "flake8", "task/src_python/src/", "tests/", "--max-line-length=100"],
            cwd=repo_root
        )
        success = success and flake8_success
    
    # Run black check
    if args.lint_python:
        print("\n▶ Running black...")
        black_success = run_command(
            [sys.executable, "-m", "black", "--check", "task/src_python/src/", "tests/"],
            cwd=repo_root
        )
        success = success and black_success
    
    # Run mypy
    if args.type_check:
        print("\n▶ Running mypy...")
        mypy_success = run_command(
            [sys.executable, "-m", "mypy", "task/src_python/src/", "--ignore-missing-imports"],
            cwd=repo_root
        )
        success = success and mypy_success
    
    return success


def setup_test_environment():
    """Set up test environment variables."""
    print("\n⚙️  Setting up test environment...")
    
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    print("✅ Test environment configured")


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("\n📦 Checking dependencies...")
    
    # Map package names to their import names
    required_packages = {
        "pytest": "pytest",
        "pytest-cov": "pytest_cov",
        "pytest-mock": "pytest_mock",
        "pyyaml": "yaml",  # pyyaml imports as 'yaml'
        "requests": "requests",
    }
    
    missing = []
    for package, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("\nInstall missing packages with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    print("✅ All dependencies installed")
    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Run tests for Azure DevOps AI PR Review Extension"
    )
    
    parser.add_argument(
        "--python",
        action="store_true",
        help="Run Python tests"
    )
    
    parser.add_argument(
        "--typescript",
        action="store_true",
        help="Run TypeScript tests"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests (Python and TypeScript)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage reports"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--markers",
        type=str,
        help="Run tests matching given mark expression (e.g., 'integration')"
    )
    
    parser.add_argument(
        "--test-path",
        type=str,
        help="Run specific test file or directory"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run all linters"
    )
    
    parser.add_argument(
        "--lint-python",
        action="store_true",
        help="Run Python linters (flake8, black)"
    )
    
    parser.add_argument(
        "--type-check",
        action="store_true",
        help="Run type checking (mypy)"
    )
    
    parser.add_argument(
        "--no-deps-check",
        action="store_true",
        help="Skip dependency check"
    )
    
    args = parser.parse_args()
    
    # Default to running all tests if no specific test type is specified
    if not any([args.python, args.typescript, args.all, args.lint, args.lint_python, args.type_check]):
        args.all = True
    
    print("=" * 80)
    print("🧪 Azure DevOps AI PR Review Extension - Test Runner")
    print("=" * 80)
    
    # Check dependencies
    if not args.no_deps_check and not check_dependencies():
        return 1
    
    # Setup test environment
    setup_test_environment()
    
    all_success = True
    
    # Run linters
    if args.lint or args.lint_python or args.type_check:
        lint_success = run_linters(args)
        all_success = all_success and lint_success
    
    # Run Python tests
    if args.python or args.all:
        python_success = run_python_tests(args)
        all_success = all_success and python_success
    
    # Run TypeScript tests
    if args.typescript or args.all:
        ts_success = run_typescript_tests(args)
        all_success = all_success and ts_success
    
    # Print summary
    print("\n" + "=" * 80)
    if all_success:
        print("✅ All tests passed!")
        print("=" * 80)
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
