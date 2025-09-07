# Python environment setup
PYTHON := python3
UV := uv
VENV := .venv
VENV_BIN := $(VENV)/bin

# Virtual environment targets
.PHONY: venv
venv:
	@echo "Creating virtual environment..."
	$(UV) venv $(VENV)

.PHONY: install
install: venv
	@echo "Installing dependencies..."
	$(UV) pip install -e .

.PHONY: dev-install
dev-install: venv
	@echo "Installing development dependencies..."
	$(UV) pip install -e ".[dev]"

# Run targets
.PHONY: run
run: install data
	@echo "Running SCP MCP server..."
	$(VENV_BIN)/python -m scp_mcp

.PHONY: test
test: dev-install
	@echo "Running tests..."
	$(VENV_BIN)/python -m pytest tests/

.PHONY: lint
lint: dev-install
	@echo "Running linters..."
	$(VENV_BIN)/ruff check src/ tests/
	$(VENV_BIN)/ruff format --check src/ tests/

.PHONY: format
format: dev-install
	@echo "Formatting code..."
	$(VENV_BIN)/ruff check --fix src/ tests/
	$(VENV_BIN)/ruff format src/ tests/

.PHONY: typecheck
typecheck: dev-install
	@echo "Running type checker..."
	$(VENV_BIN)/mypy src/scp_mcp/

# Clean targets
.PHONY: clean
clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	rm -rf src/scp_mcp/__pycache__
	rm -rf src/scp_mcp/*.pyc
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

.PHONY: clean-data
clean-data:
	@echo "Cleaning data..."
	rm -rf data/scp-* data/scp_lancedb

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

