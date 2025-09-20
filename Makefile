# Default target - show help
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo "SCP MCP Server - Available Make Targets"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# Environment setup
.PHONY: setup-env
setup-env: ## Set up environment configuration (.env.local from template)
	@echo "Setting up environment configuration..."
	./scripts/setup-env.sh

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

