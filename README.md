# SCP MCP

This project provides access to SCP Foundation data through a Model Context Protocol (MCP) server.

## Getting Started

### Prerequisites

- Git (required for downloading SCP data) from [scp-api](https://github.com/scp-data/scp-api)
- Make (for using the provided build targets)

### Data Management

The project uses timestamped SCP data directories in the format `data/scp-<timestamp>-<commit-id>`. Use the following Make targets to manage your data:

#### Available Make Targets

- **`make data`** - Ensures SCP data exists (downloads only if no `data/scp-*` directories are found)
- **`make download`** - Always downloads fresh SCP data, creating a new timestamped directory

#### Examples

```bash
# Ensure you have SCP data (downloads if missing)
make data

# Download fresh data (always runs, creates new timestamped directory)
make download

```

### Data Structure

The downloaded SCP data includes:

- **`items/`** - SCP articles organized by series and type
  - Series 1-9 content files
  - Special categories (archived, decommissioned, explained, international, joke)
  - SCP-001 proposals
- **`tales/`** - SCP tales organized by year (2008-2025)
- **`goi/`** - Groups of Interest content
- **`hubs/`** - Hub pages content

### Manual Data Download

You can also download data manually using the script directly:

```bash
./scripts/download_scp_folder.sh ./data/
```

This will create a new timestamped directory under `./data/` with the latest SCP Foundation content.

## Running the Server

Start the MCP server (loads items into LanceDB on first run):

```bash
make run
```

To force a reingestion of items without deleting the whole DB:

```bash
make reingest-items
# or directly:
uv run python -m scp_mcp --reingest-items
```

Optional flags:

- `--data-dir <path>` to override the SCP data directory used for ingest.

## Project Structure

```txt
scp-mcp/
├── data/                          # SCP data storage
│   └── scp-<timestamp>-<commit>/  # Timestamped data directories
├── scripts/
│   └── download_scp_folder.sh     # Data download script
├── Makefile                       # Build targets
└── README.md                      # This file
```
