# Python environment setup
PYTHON := python3
UV := uv
VENV := .venv
VENV_BIN := $(VENV)/bin

# SCP data management targets
data/scp-%:
	@echo "Downloading SCP data..."
	./scripts/download_scp_folder.sh ./data/

# Convenience target that depends on having some scp data
.PHONY: data
data: | data/scp-check
	@echo "SCP data is available"

# Check if scp data exists, if not trigger download
.PHONY: data/scp-check
data/scp-check:
	@if [ -z "$$(ls -d ./data/scp-* 2>/dev/null)" ]; then \
		echo "No SCP data found, downloading..."; \
		./scripts/download_scp_folder.sh ./data/; \
	fi

# Always download fresh SCP data
.PHONY: download
download:
	@echo "Downloading fresh SCP data..."
	./scripts/download_scp_folder.sh ./data/

# Check if uv is installed, if not install it
.PHONY: check-uv
check-uv:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }

# Create virtual environment using uv
.PHONY: venv
venv: check-uv
	@echo "Creating virtual environment with uv..."
	uv venv $(VENV)

# Install dependencies
.PHONY: install
install: venv
	@echo "Installing dependencies..."
	uv pip install -e .

# Install development dependencies
.PHONY: install-dev
install-dev: venv
	@echo "Installing development dependencies..."
	uv pip install -e .[dev]

# Setup complete environment
.PHONY: setup
setup: install-dev
	@echo "Environment setup complete!"

# Run the MCP server
.PHONY: run
run: install
	@echo "Starting MCP server..."
	$(VENV_BIN)/python -m src.scp_mcp

# Run with development mode
.PHONY: run-dev
run-dev: install-dev
	@echo "Starting MCP server in development mode..."
	$(VENV_BIN)/python -m src.scp_mcp

# Clean environment
.PHONY: clean
clean:
	@echo "Cleaning environment..."
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Format code
.PHONY: format
format: install-dev
	@echo "Formatting code..."
	$(VENV_BIN)/black src/
	$(VENV_BIN)/isort src/

# Lint code
.PHONY: lint
lint: install-dev
	@echo "Linting code..."
	$(VENV_BIN)/flake8 src/
	$(VENV_BIN)/mypy src/

# Run tests
.PHONY: test
test: install-dev
	@echo "Running tests..."
	$(VENV_BIN)/pytest

# MCP CLI commands
.PHONY: mcp-install
mcp-install: install
	@echo "Installing SCP MCP server in Claude desktop app..."
	uv run mcp install src.scp_mcp

.PHONY: mcp-dev
mcp-dev: install-dev
	@echo "Installing SCP MCP server in development mode..."
	@echo "Development mode - use 'make mcp-run-dev' to run with inspector"

# Run MCP server using MCP CLI with inspector
.PHONY: mcp-run
mcp-run: install
	@echo "Running SCP MCP server via MCP CLI with inspector..."
	uv run mcp dev src.scp_mcp

# Run MCP server in development mode
.PHONY: mcp-run-dev
mcp-run-dev: install-dev
	@echo "Running SCP MCP server in development mode via MCP CLI..."
	uv run mcp dev src.scp_mcp

# Test MCP server (run with inspector to see tools)
.PHONY: mcp-test
mcp-test: install-dev
	@echo "Testing SCP MCP server - running with inspector..."
	@echo "Open http://localhost:5173 in your browser to see available tools"
	uv run mcp dev src.scp_mcp
