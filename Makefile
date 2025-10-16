# Makefile for Knowledgebase Indexer project
# Provides convenient commands for development, testing, and maintenance

.PHONY: help install test test-quick test-unit test-integration test-all test-coverage clean lint format check docs

# Default target
help:
	@echo "Knowledgebase Indexer - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install        - Install dependencies and set up development environment"
	@echo "  install-dev    - Install additional development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test-quick     - Run quick commit tests (< 30 seconds)"
	@echo "  test-unit      - Run unit tests (< 2 minutes)"
	@echo "  test-integration - Run integration tests (< 5 minutes)" 
	@echo "  test-all       - Run complete test suite (< 10 minutes)"
	@echo "  test-coverage  - Run tests with coverage reporting"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           - Run linting checks (flake8, pylint)"
	@echo "  format         - Format code (black, isort)"
	@echo "  format-check   - Check code formatting without making changes"
	@echo "  check          - Run all code quality checks"
	@echo ""
	@echo "Documentation:"
	@echo "  docs           - Generate documentation"
	@echo "  docs-serve     - Serve documentation locally"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean          - Clean temporary files and caches"
	@echo "  clean-all      - Clean everything including virtual environment"
	@echo "  sample-files   - Generate sample configuration and keyword files"

# Installation and setup
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed successfully"

install-dev: install
	@echo "Installing development dependencies..."
	pip install pytest pytest-cov black isort flake8 pylint mypy
	@echo "✅ Development dependencies installed"

# Testing commands
test-quick:
	@echo "Running quick commit tests..."
	python run_tests.py quick

test-unit:
	@echo "Running unit tests..."
	python run_tests.py unit

test-integration:
	@echo "Running integration tests..."
	python run_tests.py integration

test-all:
	@echo "Running complete test suite..."
	python run_tests.py all

test-coverage:
	@echo "Running tests with coverage reporting..."
	python run_tests.py coverage

# Alternative pytest commands for more control
pytest-quick:
	pytest tests/test_quick_commit.py -v -m quick

pytest-unit:
	pytest tests/unit/ -v -m "not slow"

pytest-integration:  
	pytest tests/integration/ -v -m "slow or integration"

pytest-all:
	pytest tests/ -v

pytest-debug:
	pytest tests/ -v -s --tb=long --log-cli-level=DEBUG

# Code quality
lint:
	@echo "Running linting checks..."
	@echo "Checking with flake8..."
	flake8 --max-line-length=100 --extend-ignore=E203,W503 *.py handlers/ tests/
	@echo "Checking with pylint..."
	-pylint *.py handlers/
	@echo "✅ Linting complete"

format:
	@echo "Formatting code..."
	black --line-length=100 *.py handlers/ tests/
	isort --profile black --line-length=100 *.py handlers/ tests/
	@echo "✅ Code formatted"

format-check:
	@echo "Checking code formatting..."
	black --check --line-length=100 *.py handlers/ tests/
	isort --check-only --profile black --line-length=100 *.py handlers/ tests/
	@echo "✅ Code formatting check complete"

type-check:
	@echo "Running type checking..."
	mypy *.py handlers/ --ignore-missing-imports
	@echo "✅ Type checking complete"

check: format-check lint type-check
	@echo "✅ All code quality checks passed"

# Documentation
docs:
	@echo "Generating documentation..."
	# Add documentation generation commands here
	@echo "✅ Documentation generated"

docs-serve:
	@echo "Serving documentation locally..."
	# Add documentation serving commands here
	@echo "Documentation available at http://localhost:8000"

# Sample file generation
sample-files:
	@echo "Generating sample files..."
	mkdir -p configs
	python kbi.py --sample-config
	python kbi.py --sample-keywords
	@echo "✅ Sample files generated"

# Demonstration and examples
demo:
	@echo "Running demonstration..."
	@echo "1. Generating sample files..."
	$(MAKE) sample-files
	@echo "2. Running index generation with debug output..."
	python kbi.py --debug
	@echo "✅ Demonstration complete"

# Performance testing
benchmark:
	@echo "Running performance benchmarks..."
	python -m pytest tests/ -m "not slow" --durations=0
	@echo "✅ Benchmark complete"

# Security scanning
security-check:
	@echo "Running security checks..."
	pip install safety bandit
	safety check
	bandit -r *.py handlers/
	@echo "✅ Security check complete"

# Maintenance and cleanup
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "tests.log" -delete
	rm -f *.mm
	@echo "✅ Cleanup complete"

clean-all: clean
	@echo "Cleaning all generated files and virtual environment..."
	rm -rf venv/
	rm -rf .tox/
	rm -rf *.egg-info/
	@echo "✅ Complete cleanup finished"

# Development workflow
dev-setup: install-dev
	@echo "Setting up development environment..."
	$(MAKE) sample-files
	$(MAKE) test-quick
	@echo "✅ Development environment ready"

pre-commit: format lint type-check test-quick
	@echo "✅ Pre-commit checks completed successfully"

# CI/CD helpers
ci-test: install-dev
	@echo "Running CI test suite..."
	$(MAKE) check
	$(MAKE) test-all
	@echo "✅ CI test suite completed"

# Help for specific commands
help-testing:
	@echo "Testing Command Details:"
	@echo "======================="
	@echo "test-quick     : Runs basic functionality tests in < 30 seconds"
	@echo "test-unit      : Runs component-level tests in < 2 minutes"
	@echo "test-integration : Runs full workflow tests in < 5 minutes"
	@echo "test-all       : Runs complete test suite with reporting"
	@echo "test-coverage  : Generates HTML coverage report in htmlcov/"

help-quality:
	@echo "Code Quality Command Details:"
	@echo "============================"
	@echo "lint           : Checks code style with flake8 and pylint"
	@echo "format         : Formats code with black and sorts imports with isort"
	@echo "format-check   : Verifies code formatting without making changes"
	@echo "type-check     : Runs mypy for static type checking"
	@echo "check          : Runs all quality checks in sequence"