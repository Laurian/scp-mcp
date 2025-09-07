# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- `make venv` - Create virtual environment using uv
- `make install` - Install basic dependencies
- `make dev-install` - Install development dependencies including pre-commit hooks

### Code Quality
- `make lint` - Run ruff linting and format checks
- `make format` - Auto-format code with ruff
- `make typecheck` - Run mypy type checking
- `pytest tests/` - Run test suite

### Running the Application
- `make run` - Start the SCP MCP server (ensures data is available first)
- `python -m scp_mcp` - Run server directly from virtual environment
- `uv run python -m scp_mcp` - Run using uv (Python package manager)

### Data Management
- `make data` - Ensure SCP data exists (downloads if missing)
- `make download` - Always download fresh SCP data with new timestamp
- `make clean-data` - Remove all SCP data directories

## Architecture Overview

This is an MCP (Model Context Protocol) server that provides access to SCP Foundation data through semantic search and vector embeddings.

### Core Components

**Data Layer**: 
- SCP data stored in timestamped directories (`data/scp-<timestamp>-<commit>/`)
- Content organized by type: items/, tales/, goi/, hubs/
- Vector database using LanceDB for semantic search

**MCP Server** (`src/scp_mcp/main.py`):
- Entry point currently contains TODO stubs for server initialization
- Will handle MCP protocol communication
- Integrates with sentence-transformers for embeddings

**Dependencies**:
- `mcp>=0.1.0` - Model Context Protocol implementation
- `lancedb>=0.1.0` - Vector database for semantic search
- `sentence-transformers>=2.2.0` - Text embeddings
- `python-dotenv>=1.0.0` - Environment configuration

### Data Flow

1. SCP data downloaded from scp-api repository via download script
2. Data processed and indexed into LanceDB vector store
3. MCP server provides search/query interface over the indexed content
4. Embeddings generated using configurable transformer model (default: all-MiniLM-L6-v2)

### Configuration

Environment variables (see `.env.example`):
- `SCP_DB_PATH` - LanceDB storage path
- `SCP_DATA_DIR` - Raw SCP data directory
- `EMBEDDING_MODEL` - Sentence transformer model name
- `LOG_LEVEL` - Logging verbosity

### Development Notes

- Python 3.10-3.12 supported
- Uses uv for fast dependency management
- Ruff for linting/formatting with 88 character line length
- Project follows standard Python packaging with pyproject.toml

## Testing

```bash
# Run tests with pytest
uv run pytest tests/

# Run specific test
uv run pytest tests/test_specific.py::test_function

# Run with coverage
uv run pytest --cov=scp_mcp tests/
```

## Code Style

- **Python**: PEP 8 with 4-space indentation (per `.editorconfig`)
- **Line length**: 88 characters
- **Formatting**: Use ruff (replaces Black + isort)
- **Type hints**: Required for all functions
- **Docstrings**: Google style

## Project Structure

```
src/scp_mcp/     # Main package
tests/           # Test files
data/            # SCP data storage
scripts/         # Utility scripts
```

## Key Conventions

- Use `uv` for dependency management
- Environment variables in `.env` file (see `.env.example`)
- SCP data stored in timestamped directories: `data/scp-<timestamp>-<commit-id>/`
- LanceDB for vector storage in `data/scp_lancedb/`
- Error handling: Use exceptions, log with appropriate levels
- Imports: Standard library first, then third-party, then local
