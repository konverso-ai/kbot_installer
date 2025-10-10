# Makefile for kbot-installer project
# Uses uv for Python package management and execution

.PHONY: help install install-dev lint lint-fix format check test test-cov clean

# Default target - Show help with all available targets and their descriptions
help:
	@echo "Available targets:"
	@echo ""
	@echo "  check        - Run formatter then linter to check for issues"
	@echo "  clean        - Remove all Python cache files and temporary directories"
	@echo "  format       - Format code according to style guidelines"
	@echo "  install      - Install only production dependencies"
	@echo "  install-dev  - Install all dependencies including development tools"
	@echo "  lint         - Run code linter to check for issues (no fixes)"
	@echo "  lint-fix     - Run code linter and automatically fix issues"
	@echo "  test         - Run all tests using pytest"
	@echo "  test-cov     - Run tests with coverage report (HTML and terminal output)"
	@echo ""
	@echo "Usage examples:"
	@echo "  make test                    # Run all tests"
	@echo "  make test PKG=provider       # Run tests for provider package only"
	@echo "  make test PKG=auth           # Run tests for auth package only"
	@echo "  make test PKG=auth/pygit_authentication  # Run tests for specific subpackage"
	@echo "  make test-cov PKG=provider   # Run provider tests with coverage"
	@echo "  make test-cov PKG=auth       # Run auth tests with coverage"
	@echo ""
	@echo "Available packages:"
	@echo "  - provider (main package)"
	@echo "  - auth (includes pygit_authentication and http_auth subpackages)"
	@echo "  - factory"
	@echo "  - versioner"
	@echo "  - http_client"
	@echo "  - url_manager"

# Install production dependencies
install:
	uv sync

# Install all dependencies (production + lint + test)
install-dev:
	uv sync --all-packages --all-groups --all-extras

# Run ruff linter (check only, no fixes)
lint:
	uv run ruff check .

# Run ruff linter with automatic fixes
lint-fix:
	uv run ruff check --fix .

# Run ruff formatter
format:
	uv run ruff format .

# Run formatter then linter (correct order: format first, then check)
check: format lint

# Run tests with pytest (using -B to prevent __pycache__)
# Usage: make test [PKG=package_name]
test:
ifdef PKG
	@echo "Running tests for package: $(PKG)"
	@if [ -d "$(PKG)/tests" ]; then \
		uv run python -B -m pytest $(PKG)/tests/ -v; \
	elif [ -d "$(PKG)" ]; then \
		echo "No tests directory found in $(PKG), searching for test files..."; \
		uv run python -B -m pytest $(PKG)/ -v; \
	else \
		echo "Package $(PKG) not found!"; \
		exit 1; \
	fi
else
	@echo "Running all tests"
	uv run python -B -m pytest -v
endif


# Run tests with coverage report (using -B to prevent __pycache__)
# Usage: make test-cov [PKG=package_name]
test-cov:
ifdef PKG
	@echo "Running tests with coverage for package: $(PKG)"
	@if [ -d "$(PKG)/tests" ]; then \
		uv run python -B -m pytest $(PKG)/tests/ --cov=$(PKG) --cov-report=html --cov-report=term -v; \
	elif [ -d "$(PKG)" ]; then \
		echo "No tests directory found in $(PKG), searching for test files..."; \
		uv run python -B -m pytest $(PKG)/ --cov=$(PKG) --cov-report=html --cov-report=term -v; \
	else \
		echo "Package $(PKG) not found!"; \
		exit 1; \
	fi
else
	@echo "Running all tests with coverage"
	uv run python -B -m pytest --cov=. --cov-report=html --cov-report=term -v
endif


# Clean Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	find . -name "htmlcov" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null || true
