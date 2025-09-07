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

