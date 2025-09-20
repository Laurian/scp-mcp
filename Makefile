# Default target - show help
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo "SCP MCP Server - Available Make Targets"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Python environment setup
.PHONY: install
install: ## Install dependencies using uv
	@echo "Installing dependencies with uv..."
	uv sync

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	uv sync --extra dev

.PHONY: install-all
install-all: ## Install all optional dependencies (dev, server, ai)
	@echo "Installing all dependencies..."
	uv sync --all-extras

.PHONY: update
update: ## Update dependencies to latest versions
	@echo "Updating dependencies..."
	uv sync --upgrade

.PHONY: lock
lock: ## Generate/update uv.lock file
	@echo "Updating lock file..."
	uv lock

# Environment setup
.PHONY: setup-env
setup-env: ## Set up environment configuration (.env.local from template)
	@echo "Setting up environment configuration..."
	./scripts/setup-env.sh

.PHONY: setup
setup: setup-env install ## Complete setup (environment + dependencies)
	@echo "Running SCP MCP initialization..."
	uv run scp-mcp init

.PHONY: clean-data
clean-data: ## Remove all downloaded SCP data
	@echo "Cleaning data..."
	rm -rf data/raw/scp-*

# SCP data management targets
data/raw/scp-%:
	@echo "Downloading SCP data..."
	./scripts/download_scp_folder.sh ./data/raw/

# Convenience target that depends on having some scp data
.PHONY: data
data: | data/raw/scp-check ## Ensure SCP data is available (downloads if missing)
	@echo "SCP data is available"

# Check if scp data exists, if not trigger download
.PHONY: data/scp-check
data/raw/scp-check:
	@if [ -z "$$(ls -d ./data/raw/scp-* 2>/dev/null)" ]; then \
		echo "No SCP data found, downloading..."; \
		./scripts/download_scp_folder.sh ./data/raw/; \
	fi

# Always download fresh SCP data
.PHONY: download
download: ## Download fresh SCP data (always downloads latest)
	@echo "Downloading fresh SCP data..."
	./scripts/download_scp_folder.sh ./data/raw/

# Development targets
.PHONY: dev
dev: ## Run development server with auto-reload
	@echo "Starting development server..."
	uv run scp-mcp serve --debug

.PHONY: serve
serve: ## Run production server (STDIO transport)
	@echo "Starting SCP MCP server..."
	uv run scp-mcp serve

.PHONY: serve-http
serve-http: ## Run HTTP server for testing
	@echo "Starting HTTP server on http://localhost:8000..."
	uv run scp-mcp serve --transport http --port 8000

.PHONY: sync
sync: ## Synchronize SCP data
	@echo "Synchronizing SCP data..."
	uv run scp-mcp sync

.PHONY: status
status: ## Show system status
	uv run scp-mcp status

.PHONY: validate
validate: ## Validate setup and configuration
	uv run scp-mcp validate

# Code quality targets
.PHONY: format
format: ## Format code with black and isort
	@echo "Formatting code..."
	uv run black src/ tests/
	uv run isort src/ tests/

.PHONY: lint
lint: ## Run linting with ruff
	@echo "Running linter..."
	uv run ruff check src/ tests/

.PHONY: lint-fix
lint-fix: ## Run linting with auto-fix
	@echo "Running linter with auto-fix..."
	uv run ruff check --fix src/ tests/

.PHONY: type-check
type-check: ## Run type checking with mypy
	@echo "Running type checker..."
	uv run mypy src/

.PHONY: check
check: lint type-check ## Run all code quality checks

# Testing targets
.PHONY: test
test: ## Run tests
	@echo "Running tests..."
	uv run pytest

.PHONY: test-cov
test-cov: ## Run tests with coverage
	@echo "Running tests with coverage..."
	uv run pytest --cov=src/scp_mcp --cov-report=html --cov-report=term

.PHONY: test-fast
test-fast: ## Run tests (skip slow tests)
	@echo "Running fast tests..."
	uv run pytest -m "not slow"

# Build targets
.PHONY: build
build: ## Build distribution packages
	@echo "Building packages..."
	uv build

.PHONY: publish
publish: ## Publish to PyPI (requires authentication)
	@echo "Publishing to PyPI..."
	uv publish

.PHONY: publish-test
publish-test: ## Publish to Test PyPI
	@echo "Publishing to Test PyPI..."
	uv publish --repository testpypi

# Cleanup targets
.PHONY: clean
clean: ## Clean build artifacts and cache
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

.PHONY: clean-all
clean-all: clean clean-data ## Clean everything (build artifacts + data)
	@echo "Cleaning all artifacts and data..."
	rm -rf cache/
	rm -rf data/lancedb/
	rm -rf data/processed/
	rm -rf data/staging/

# Docker targets (for future containerization)
.PHONY: docker-build
docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t scp-mcp:latest .

.PHONY: docker-run
docker-run: ## Run Docker container
	@echo "Running Docker container..."
	docker run -it --rm -p 8000:8000 scp-mcp:latest

