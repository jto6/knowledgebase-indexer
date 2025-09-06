#!/usr/bin/env python3
"""
Test runner script for Knowledgebase Indexer tests.

Provides different test suites for different purposes:
- Quick commit tests: Fast tests for development feedback
- Unit tests: Component-level testing
- Integration tests: Full workflow testing
- All tests: Complete test suite
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_quick_tests():
    """Run quick commit tests for rapid feedback."""
    print("Running quick commit tests...")
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/test_quick_commit.py",
        "-v", "--tb=short"
    ]
    return subprocess.run(cmd).returncode


def run_unit_tests():
    """Run unit tests for all components."""
    print("Running unit tests...")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/",
        "-v", "--tb=short"
    ]
    return subprocess.run(cmd).returncode


def run_integration_tests():
    """Run integration tests (slower)."""
    print("Running integration tests...")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/integration/",
        "-v", "--tb=long"
    ]
    return subprocess.run(cmd).returncode


def run_all_tests():
    """Run all tests."""
    print("Running all tests...")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v", "--tb=short",
        "--durations=10"  # Show 10 slowest tests
    ]
    return subprocess.run(cmd).returncode


def run_tests_with_coverage():
    """Run all tests with coverage reporting."""
    print("Running tests with coverage...")
    
    # Install coverage if not available
    try:
        import coverage
    except ImportError:
        print("Installing coverage...")
        subprocess.run([sys.executable, "-m", "pip", "install", "coverage"])
    
    cmd = [
        sys.executable, "-m", "coverage", "run",
        "-m", "pytest", "tests/",
        "-v"
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        # Generate coverage report
        print("\nCoverage Report:")
        subprocess.run([sys.executable, "-m", "coverage", "report", "-m"])
        
        # Generate HTML coverage report
        subprocess.run([sys.executable, "-m", "coverage", "html"])
        print("HTML coverage report generated in htmlcov/")
    
    return result.returncode


def check_dependencies():
    """Check that required test dependencies are available."""
    required_packages = ["pytest", "pyyaml", "jsonschema"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Test runner for Knowledgebase Indexer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Suites:
  quick     - Fast tests for development feedback (< 30 seconds)
  unit      - Unit tests for all components (< 2 minutes) 
  integration - Full workflow tests (< 5 minutes)
  all       - All tests (< 10 minutes)
  coverage  - All tests with coverage reporting
  
Examples:
  python run_tests.py quick
  python run_tests.py unit
  python run_tests.py all --verbose
        """
    )
    
    parser.add_argument(
        "suite",
        choices=["quick", "unit", "integration", "all", "coverage"],
        help="Test suite to run"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Change to project directory
    project_dir = Path(__file__).parent
    import os
    os.chdir(project_dir)
    
    # Run selected test suite
    if args.suite == "quick":
        return run_quick_tests()
    elif args.suite == "unit":
        return run_unit_tests()
    elif args.suite == "integration":
        return run_integration_tests()
    elif args.suite == "coverage":
        return run_tests_with_coverage()
    elif args.suite == "all":
        # Run in sequence
        print("=" * 50)
        print("Running complete test suite")
        print("=" * 50)
        
        exit_code = 0
        
        print("\n1. Quick Tests")
        print("-" * 20)
        quick_result = run_quick_tests()
        if quick_result != 0:
            exit_code = quick_result
            print("❌ Quick tests failed!")
        else:
            print("✅ Quick tests passed!")
        
        print("\n2. Unit Tests")
        print("-" * 20)
        unit_result = run_unit_tests()
        if unit_result != 0:
            exit_code = unit_result
            print("❌ Unit tests failed!")
        else:
            print("✅ Unit tests passed!")
        
        print("\n3. Integration Tests")
        print("-" * 20)
        integration_result = run_integration_tests()
        if integration_result != 0:
            exit_code = integration_result
            print("❌ Integration tests failed!")
        else:
            print("✅ Integration tests passed!")
        
        print("\n" + "=" * 50)
        if exit_code == 0:
            print("🎉 All tests passed!")
        else:
            print("❌ Some tests failed!")
        print("=" * 50)
        
        return exit_code
    
    return 0


if __name__ == "__main__":
    sys.exit(main())