# SCP MCP Server

**A Model Context Protocol Server for SCP Foundation Data**

Expose SCP Foundation Items to MCP clients with reproducible, versioned reads, strict licensing, and predictable tool/resource contracts. Built for seamless integration with AI agents and Large Language Models.

- **Protocol:** Model Context Protocol (MCP) 1.0+ - JSON-RPC 2.0 based with stateful connections
- **Framework:** FastMCP (Python) - High-performance MCP server framework  
- **Runtime:** Python 3.12
- **Storage:** LanceDB (versioned) - Vector database with automatic versioning and time-travel
- **Source dataset:** `scp-data` static dump (items/tales/GOI), updated daily
- **Transport:** STDIO (default), HTTP, SSE - Multiple transport protocols for flexibility

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/scp-data/scp-mcp.git
   cd scp-mcp
   ```

2. **Set up the environment:**
   ```bash
   make setup
   ```
   This will:
   - Create environment configuration files
   - Install dependencies with uv
   - Initialize the server environment

3. **Download SCP data:**
   ```bash
   make download
   ```

4. **Run the server:**
   ```bash
   make serve
   ```

### Alternative Setup (Manual)

```bash
# Install dependencies
uv sync

# Set up environment
make setup-env

# Initialize server
uv run scp-mcp init

# Download data
uv run scp-mcp sync

# Run server
uv run scp-mcp serve
```

## Usage

### MCP Client Integration

The server exposes tools and resources through the Model Context Protocol:

```python
from fastmcp import Client

async with Client("scp_server.py") as client:
    # Search for items
    results = await client.call_tool("search_items", {
        "query": "anomalous objects",
        "limit": 5
    })
    
    # Get item content  
    content = await client.call_tool("get_item_content", 
                                   {"identifier": "SCP-173"})
    
    # Access resources
    index = await client.read_resource("urn:scp:index:items")
```

### Available Tools

- **`search_items`** - Semantic search with intelligent ranking
- **`get_item`** - Retrieve specific item with flexible content inclusion  
- **`get_item_content`** - AI-optimized content retrieval
- **`get_related`** - Discover connected items through cross-references
- **`random_item`** - Serendipitous discovery with optional filtering
- **`sync_index`** - Trigger data refresh with detailed reporting
- **`version_info`** - System state and configuration transparency

### Available Resources

- **`urn:scp:index:items`** - Compact item catalog for discovery
- **`urn:scp:item:{SCP-XXXX}`** - Item metadata without heavy content
- **`urn:scp:item:{SCP-XXXX}/content`** - AI-optimized content view  
- **`urn:scp:series:{series}`** - Series-specific item collections

### Command Line Interface

```bash
# Server management
uv run scp-mcp serve                    # Start STDIO server
uv run scp-mcp serve --transport http   # Start HTTP server
uv run scp-mcp serve --debug            # Start with debug mode

# Data management  
uv run scp-mcp sync                     # Synchronize data
uv run scp-mcp sync --force             # Force full resync

# System information
uv run scp-mcp status                   # Show system status
uv run scp-mcp validate                 # Validate setup
uv run scp-mcp config                   # Show configuration
```

## Data Export Scripts

The project includes utility scripts for exporting SCP data to different formats for analysis, backup, or integration with other tools.

### JSON Export

Export SCP items as individual JSON files organized in a hierarchical folder structure:

```bash
# Export all items to ./data/staging/json/
./scripts/export_json.py

# Export single item
./scripts/export_json.py SCP-173
./scripts/export_json.py 682                    # Short form

# Export range of items  
./scripts/export_json.py 100-200               # Exports SCP-100 through SCP-200

# Export random items
./scripts/export_json.py --random 10           # Export 10 random items
./scripts/export_json.py -r 25                 # Short form

# Custom output directory
./scripts/export_json.py --output ./my_exports/ --random 5

# Get help
./scripts/export_json.py --help
```

### Markdown Export

Export SCP items as Markdown files with YAML frontmatter metadata:

```bash
# Export all items to ./data/staging/markdown/
./scripts/export_markdown.py

# Export single item  
./scripts/export_markdown.py SCP-682
./scripts/export_markdown.py 173               # Short form

# Export range of items
./scripts/export_markdown.py 1-50              # Exports SCP-001 through SCP-050

# Export random items
./scripts/export_markdown.py --random 10       # Export 10 random items
./scripts/export_markdown.py -r 5              # Short form

# Custom output directory
./scripts/export_markdown.py --output ./docs/ --random 3

# Get help
./scripts/export_markdown.py --help
```

### Export Features

Both export scripts provide:

- **Hierarchical Organization**: Files are organized in folders based on SCP identifier (e.g., SCP-1234 → `1/2/3/4/scp-1234.ext`)
- **Flexible Input Formats**: Accept `SCP-173`, `173`, `scp-173`, or ranges like `100-200`
- **Batch Processing**: Efficient handling of large exports with progress reporting
- **Content Conversion**: Markdown export includes HTML-to-Markdown conversion for better readability
- **Metadata Preservation**: All available metadata is preserved in appropriate formats

### Output Structure

**JSON Export:**
```
data/staging/json/
├── 1/7/3/scp-173.json          # SCP-173
├── 6/8/2/scp-682.json          # SCP-682  
├── 1/0/0/scp-100.json          # SCP-100
└── 1/0/0/-/j/scp-100-j.json    # SCP-100-J (joke)
```

**Markdown Export:**
```
data/staging/markdown/
├── 1/7/3/scp-173.md            # SCP-173 with YAML frontmatter
├── 6/8/2/scp-682.md            # SCP-682 with YAML frontmatter
└── 1/4/4/6/scp-1446.md         # SCP-1446 with YAML frontmatter
```

### YAML Frontmatter Structure

Markdown exports include structured metadata in YAML frontmatter:

```yaml
---
scp_id: "SCP-173"
title: "SCP-173"
link: "scp-173"
scp_number: 173
series: "series-1"
rating: 10129
author: "Lt Masipag"
created_at: "2008-07-25T20:49:00"
source_url: "https://scp-wiki.wikidot.com/scp-173"
tags:
  - "euclid"
  - "sculpture" 
  - "hostile"
references:
  - "scp-172"
  - "scp-174"
license: "CC BY-SA 3.0"
license_url: "https://creativecommons.org/licenses/by-sa/3.0/"
---

# SCP-173

## Content
[Converted markdown content here...]
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
make install-dev

# Set up pre-commit hooks (optional)
uv run pre-commit install
```

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Type checking  
make type-check

# Run all checks
make check
```

### Testing

```bash
# Run tests
make test

# Run with coverage
make test-cov

# Run fast tests only
make test-fast
```

### Available Make Targets

Run `make help` to see all available targets:

```
install              Install dependencies using uv
install-dev          Install development dependencies  
install-all          Install all optional dependencies
setup                Complete setup (environment + dependencies)
serve                Run production server (STDIO transport)
serve-http           Run HTTP server for testing
sync                 Synchronize SCP data
status               Show system status
format               Format code with black and isort
lint                 Run linting with ruff
test                 Run tests
build                Build distribution packages
clean                Clean build artifacts and cache
```

## Configuration

The project uses a layered environment configuration system:

- **`.env.template`** - Base defaults (committed)
- **`.env.local`** - Personal settings (gitignored)  
- **Environment variables** - Runtime overrides

Key settings:

```env
# API Keys (set in .env.local)
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
HUGGINGFACE_TOKEN=hf_your-token-here

# Performance
DEFAULT_SEARCH_LIMIT=25
BATCH_SIZE=1000
MAX_CONCURRENT_REQUESTS=50

# Storage
LANCEDB_PATH=./data/lancedb
SCP_DATA_PATH=./data/raw
HUGGINGFACE_CACHE_DIR=./models
```

See [ENV_README.md](ENV_README.md) for detailed configuration documentation.

## Architecture

### Data Model

The server stores SCP items in LanceDB with the following schema:

- **Identification**: `link`, `scp`, `scp_number`, `title`, `series`
- **Metadata**: `tags`, `rating`, `created_at`, `creator`, `url`  
- **Content**: `raw_source`, `raw_content`, `markdown` (AI-optimized)
- **References**: `images`, `hubs`, `references`, `history`
- **Processing**: `content_sha1`, `dataset_commit`

### MCP Compliance

- **Resources**: URI-addressed read-only data (`urn:scp:*` scheme)
- **Tools**: Schema-validated operations with JSON-RPC 2.0
- **Transport**: STDIO (default), HTTP, SSE protocols
- **Versioning**: Reproducible reads via embedded version metadata

### Licensing

All SCP content is licensed under **CC BY-SA 3.0** as mandated by the SCP Wiki. The server automatically includes proper attribution in responses containing substantial content excerpts.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make check test`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note**: SCP Foundation content accessed through this server is licensed under CC BY-SA 3.0. Any derivatives using SCP content must comply with this license.

## Links

- **SCP Foundation**: https://scp-wiki.wikidot.com/
- **SCP Data API**: https://scp-data.tedivm.com/
- **Model Context Protocol**: https://modelcontextprotocol.io/
- **FastMCP Framework**: https://github.com/jlowin/fastmcp
- **LanceDB**: https://lancedb.com/
