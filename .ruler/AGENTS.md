# SCP MCP Server

**A Model Context Protocol Server for SCP Foundation Data**

Expose SCP Foundation Items to MCP clients with reproducible, versioned reads, strict licensing, and predictable tool/resource contracts. Built for seamless integration with AI agents and Large Language Models.

- **Protocol:** Model Context Protocol (MCP) 1.0+ - JSON-RPC 2.0 based with stateful connections
- **Framework:** FastMCP (Python) - High-performance MCP server framework
- **Runtime:** Python 3.12
- **Storage:** LanceDB (versioned) - Vector database with automatic versioning and time-travel
- **Source dataset:** `scp-data` static dump (items/tales/GOI), updated daily
- **Transport:** STDIO (default), HTTP, SSE - Multiple transport protocols for flexibility

---

## 1) Identifier & Addressing Policy

### Tools (inputs accepted)
All MCP tools accept flexible identifier formats and normalize them internally:
- `"SCP-XXXX"` (e.g., `"SCP-682"`) - Standard format
- Bare integers (e.g., `682`) - Numeric shorthand
- Canonical `link` slug (e.g., `"scp-682"`) - URL-safe format

All tool endpoints normalize these to a canonical `scp_label` and `link` for consistency.

### Resources (MCP URI-addressed)
MCP requires all resources to be uniquely identified by URIs. We use URNs to avoid collision with `scp://` (secure copy protocol) and ensure unambiguous addressing:

- `urn:scp:item:SCP-XXXX` — Single item metadata (e.g., `urn:scp:item:SCP-0682`)
- `urn:scp:item:682` — Equivalent numeric form for convenience
- `urn:scp:item:SCP-XXXX/content` — Full item content view with markdown
- `urn:scp:series:{n}` — Series slice (`1`, `2`, `joke`, `archive`, etc.)
- `urn:scp:index:items` — Compact item index (link + minimal metadata)

> **MCP Specification**: Resources are uniquely identified by URIs, while tools are named operations. URN stability across data ingests ensures reliable client integration.

---

## 2) Data Model (LanceDB table: `items`)

**Primary key:** `link` (canonical page slug as defined by upstream scp-data)

| field | type | notes |
|---|---|---|
| `link` | STRING | canonical page slug; primary key (e.g., `"scp-002"`) |
| `scp` | STRING | full SCP identifier (e.g., `"SCP-002"`) |
| `scp_number` | INT | numeric ID (e.g., `2`, `173`) |
| `title` | STRING | item title (often same as `scp` field) |
| `series` | STRING | series identifier (`"series-1"`, `"joke"`, etc.) |
| `tags` | LIST<STRING> | categorization tags (e.g., `["euclid", "alive", "horror"]`) |
| `rating` | INT | Wikidot community votes |
| `created_at` | TIMESTAMP | original publication date (ISO format) |
| `creator` | STRING? | original author username (optional) |
| `url` | STRING | canonical wiki URL |
| `domain` | STRING | source domain (`"scp-wiki.wikidot.com"`) |
| `page_id` | STRING? | Wikidot internal page ID (optional) |
| `raw_source` | STRING | original wikitext/markup (content files only) |
| `raw_content` | STRING | cleaned text body (content files only) |
| `markdown` | STRING | **AI-friendly markdown** generated from `raw_content` |
| `images` | LIST<STRING> | image URLs |
| `hubs` | LIST<STRING> | hub page references |
| `references` | LIST<STRING> | cross-referenced items |
| `history` | LIST<OBJECT> | edit history with author/date/comment |
| `content_file` | STRING | source file reference (index.json only) |
| `content_sha1` | STRING | SHA-1 hash for change detection (generated) |
| `dataset_commit` | STRING | upstream scp-data Git commit SHA (generated) |

**Architecture Notes**
- **Data Split**: Upstream provides two complementary datasets:
  - **`index.json`**: Complete metadata with `content_file` references (no content text)
  - **Content files**: Per-series JSON files (e.g., `content_series-1.json`) with full text content
- **Field Mapping**: Core fields (`link`, `scp`, `scp_number`, `title`, `series`, `tags`, `rating`, `created_at`, `creator`, `url`) are identical between index and content files
- **Content Fields**: `raw_content` and `raw_source` only exist in content files, not in index
- **Markdown Generation**: We transform `raw_content` into AI-friendly markdown during ingest for better LLM comprehension
- **Generated Fields**: `content_sha1` and `dataset_commit` are added during our processing pipeline
- **LanceDB Versioning**: Automatic table versioning enables time-travel queries and reproducible reads. Every operation creates a new version, preserving complete history

**Data Examples from Actual Files:**
```json
// From index.json (metadata only)
{
  "link": "scp-002",
  "scp": "SCP-002", 
  "content_file": "content_series-1.json"
}

// From content_series-1.json (includes content)
{
  "link": "scp-002",
  "scp": "SCP-002",
  "raw_content": "Item #: SCP-002...",
  "raw_source": "[[>]]\n[[module Rate]]..."
}
```

---

## 3) Ingest & Update Rules

**Efficient Change-Only Updates with LanceDB Versioning**

1. **Data Acquisition**: 
   - **Source**: Clone from `https://github.com/scp-data/scp-api.git` using sparse checkout
   - **Target Path**: `docs/data/scp` subdirectory only (efficient bandwidth usage)
   - **Versioning**: Directory named `scp-{timestamp}-{commit_id}` for unique identification
   - **Automation**: `make download` or `make data` targets handle acquisition automatically
   - **Storage**: Raw data stored in `data/raw/scp-{timestamp}-{commit_id}/`

2. **Content Processing**: For each item:
   - **Metadata Extraction**: Load base metadata from `index.json`
   - **Content Merging**: Merge with content from referenced file (e.g., `content_series-1.json`)
   - **Field Consolidation**: Combine fields, with content files taking precedence for overlapping data
   - **Markdown Generation**: Transform `raw_content` into **AI-optimized `markdown`** using our pipeline
   - **Change Detection**: Compute **`content_sha1 = sha1(raw_content)`** for efficient updates

3. **Smart Upserts**: Use LanceDB's `merge_insert` functionality keyed by `link`:
   - **Skip unchanged**: If existing row has same `content_sha1`, skip write (no new version created)
   - **Update changed**: Write all fields and stamp with current `dataset_commit`
   - **New items**: Insert with current metadata

4. **Version Management**: LanceDB automatically creates new versions for each table modification, enabling complete audit trails.

**LanceDB Features Leveraged:**
- **Merge-Insert Upserts**: Change-only writes minimize I/O and storage overhead
- **Automatic Versioning**: Every table modification creates a new version for complete auditability
- **Time-Travel Queries**: Access any historical state via `table.checkout(version)` and `table.restore()`
- **Version History**: Track all changes with `table.list_versions()` for operational transparency
- **Version Metadata**: Each version includes timestamp and operation details automatically

**Technical Notes:**
- **SHA-1 Collision Risk**: Negligible for article-length text; easily upgradeable to SHA-256 if needed
- **Version Retention**: Configurable cleanup policies (e.g., keep last 20 versions) prevent unbounded storage growth
- **Concurrent Access**: LanceDB handles concurrent reads during ingests without blocking

---

## 4) MCP Resources (Read-Only Data Sources)

**AI-Optimized Resource Endpoints for Contextual Data Access**

### `urn:scp:index:items`
**Compact item catalog for discovery and navigation**
- **Returns:** Lightweight list of `{link, scp, scp_number, title, rating, series}`
- **Use Case:** Browse available items, implement pagination, build selection interfaces
- **Versioning:** Includes `dataset_commit` for reproducible reads

### `urn:scp:item:{SCP-XXXX}`
**Item metadata without heavy content (default)**
- **Returns:** Full item row excluding `raw_content`, `raw_source`, `markdown` by default
- **Optimization:** Faster responses for metadata-only queries
- **Toggle:** Set `include_content=true` parameter for full content
- **Versioning:** Includes `dataset_commit`

### `urn:scp:item:{SCP-XXXX}/content`
**AI-optimized content view for LLM processing**
- **Returns:** `{markdown, raw_content, raw_source?, url, content_sha1}`
- **Primary:** **`markdown`** field optimized for AI comprehension
- **Fallback:** `raw_content` if markdown unavailable
- **Versioning:** Includes `dataset_commit`

### `urn:scp:series:{series}`
**Series-specific item collections**
- **Returns:** Array of index entries filtered by series (`1`, `2`, `joke`, `archive`, etc.)
- **Use Case:** Browse items within specific series or categories
- **Performance:** Pre-filtered for efficient series-based queries

**Resource Behavior & Guarantees**
- **Content Fallback**: If `raw_content` missing, automatically falls back to `raw_source` with `fallback=true` flag
- **Reproducibility**: All responses include `dataset_commit` for exact version tracking
- **URI Stability**: Resource URIs remain stable across data ingests for reliable client integration
- **Error Handling**: Missing resources return structured error responses with suggested alternatives

**MCP Compliance**: Resources are uniquely addressable by URI as required by the MCP specification. Our URN scheme prevents conflicts and ensures unambiguous resource identification.

---

## 5) MCP Tools (AI-Callable Operations)

**FastMCP-Powered Tool Endpoints for Intelligent Data Access**

### `search_items`
**Semantic search with intelligent ranking for AI agents**

**Parameters:**
```json
{
  "query": "string",           // Natural language or keyword search
  "tags": ["string"]?,         // Filter by categorization tags
  "series": "string"?,         // e.g., "Series I", "joke", "archive"
  "min_rating": 0?,           // Minimum community rating threshold
  "limit": 25,                // Results per page (max 100)
  "cursor": "opaque-string"?   // Pagination token
}
```

**Returns:**
```json
{
  "items": [
    {
      "link": "scp-682", 
      "scp": "SCP-682", 
      "scp_number": 682, 
      "title": "SCP-682", 
      "rating": 1247, 
      "series": "series-1"
    }
  ],
  "next_cursor": "opaque-string" | null,
  "dataset_commit": "abc123..."
}
```

**AI-Optimized Ranking:**
1. **Community Rating** (DESC) - Popular items first
2. **Semantic Relevance** - BM25/keyword matching score
3. **Numeric ID** - Deterministic tiebreaker

Results are deterministic across identical `dataset_commit` values for reproducible AI interactions.

### `get_item`
**Retrieve specific item with flexible content inclusion**
- **Input:** identifier (`"SCP-XXXX"` | `int` | `link`)
- **Returns:** Full item row (excludes heavy content by default)
- **Content Control:** Set `include_content=true` for full text inclusion
- **AI-Friendly:** Optimized for metadata analysis and content preview

### `get_item_content`
**AI-optimized content retrieval for LLM processing**
- **Input:** identifier (flexible format)
- **Returns:** `{markdown, raw_content, raw_source?, url, content_sha1, dataset_commit}`
- **Primary Field:** `markdown` - AI-friendly formatted content
- **Versioning:** Full reproducibility metadata included

### `get_related`
**Discover connected items through cross-references**
- **Input:** identifier, `include_hubs=true` (optional)
- **Returns:** `{items: [ItemHit], dataset_commit}`
- **Relationship Types:** References, hubs, backlinks for comprehensive context
- **AI Use Case:** Build knowledge graphs and contextual understanding

### `random_item`
**Serendipitous discovery with optional filtering**
- **Input:** `tags?: string[]`, `series?: string`
- **Returns:** `{item: ItemHit}`
- **AI Use Case:** Content exploration, example generation, creative inspiration

### `sync_index`
**Trigger data refresh with detailed reporting**
- **Action:** Pull latest upstream data and perform incremental ingest
- **Returns:** 
```json
{
  "dataset_commit": "def456...",
  "lancedb_version": 124,
  "updated": 23,
  "skipped": 4567,
  "processing_time_ms": 1250
}
```

### `version_info`
**System state and configuration transparency**
- **Returns:**
```json
{
  "dataset_commit": "abc123...",
  "current_lancedb_version": 123,
  "retention": {
    "enabled": true,
    "policy": "keep-last-20",
    "cleanup_schedule": "daily"
  },
  "server_info": {
    "fastmcp_version": "1.0.0",
    "lancedb_version": "0.13.0"
  }
}
```

**MCP Tool Architecture**: Tools are schema-validated operations that AI agents can invoke. FastMCP automatically generates JSON schemas from Python type hints, ensuring reliable AI integration with comprehensive error handling and parameter validation.

---

## 6) Pagination & Consistency Guarantees

**LanceDB-Powered Stable Pagination for AI Agents**

### Opaque Cursor Design
Cursors embed `{dataset_commit, lancedb_version, offset/hash}` ensuring pagination stability even during concurrent data ingests:

- **Stable Results**: Page through results consistently even if new data arrives
- **Version Isolation**: Each pagination session operates on a fixed dataset snapshot
- **Fresh Start**: Clients can drop cursors to get latest data in new searches

### Versioned Snapshots
- **Time-Travel Queries**: Clients can request specific `expected_commit` for reproducible results
- **Version Mismatch Handling**: Server returns HTTP 409 with `current_commit` if requested version unavailable
- **Cheap Snapshots**: LanceDB's time-travel makes historical access performant

### Consistency Models
- **Default**: Read from latest stable version
- **Pinned**: Read from specific LanceDB version for reproducibility
- **Eventually Consistent**: Optional mode for high-throughput scenarios

---

## 7) Error Handling & AI-Friendly Responses

**Intelligent Error Recovery for Autonomous Agents**

### `NotFound` Errors
- **Smart Suggestions**: Include nearest `scp_number` matches and fuzzy string matching for labels
- **Alternative Formats**: Suggest canonical identifiers when non-standard formats used
- **Context Preservation**: Maintain search context for iterative refinement

### `StaleCursor` Errors  
- **Clear Instructions**: Guide clients to restart pagination when cursor references pruned table version
- **Graceful Degradation**: Provide partial results when possible
- **Version Information**: Include current version info for client adaptation

### `MissingContent` Errors
- **Transparent Handling**: Return minimal metadata with `has_content=false` flag
- **Fallback Options**: Suggest alternative content sources when available
- **Structured Response**: Maintain consistent response format even for incomplete data

### AI-Optimized Error Format
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "SCP item not found",
    "suggestions": ["SCP-681", "SCP-683"],
    "context": {
      "query": "SCP-682X",
      "normalized_attempts": ["scp-682x", "682x"]
    }
  }
}
```

---

## 8) Licensing & Attribution (MANDATORY)

**CC BY-SA 3.0 Compliance for AI-Generated Content**

### Automatic Attribution
When returning substantial content excerpts, all responses include:

```json
{
  "content": "...",
  "attribution": {
    "title": "SCP-XXXX — Title",
    "url": "https://scp-wiki.wikidot.com/scp-xxxx",
    "authors": ["Display Name", "Author 2"],
    "license": "CC BY-SA 3.0",
    "notice": "Content from the SCP Wiki is licensed under CC BY-SA 3.0. Derivatives must be shared under the same license."
  }
}
```

### AI Usage Guidelines
- **Attribution Requirement**: AI-generated content using SCP data must include proper attribution
- **Share-Alike**: Derivative works must be released under CC BY-SA 3.0
- **Image Restrictions**: Not all images are CC BY-SA; many have separate licensing terms
- **Commercial Use**: Permitted with proper attribution and license compliance

### Implementation Notes
- **Automated Inclusion**: Attribution automatically attached to content responses
- **Configurable Thresholds**: Minimum content length for attribution requirements
- **License Validation**: Server validates license compliance for all distributed content


---

## 9) Operational Architecture & Performance

**Production-Ready FastMCP + LanceDB Deployment**

### Storage Architecture
```
data/
├── raw/
│   └── scp-{timestamp}-{commit_id}/     # Downloaded SCP data by commit
│       ├── items/                       # SCP items (main dataset)
│       │   ├── index.json               # Metadata index
│       │   ├── content_series-1.json    # Series 1 content
│       │   ├── content_series-2.json    # Series 2 content
│       │   ├── content_joke.json        # Joke SCPs
│       │   ├── content_explained.json   # Explained SCPs
│       │   └── content_*.json          # Other series/categories
│       ├── tales/                      # SCP tales by year
│       ├── goi/                        # Groups of Interest
│       └── hubs/                       # Hub pages
├── processed/                          # Transformed/merged data
├── staging/                           # Temporary processing
├── archive/                           # Historical data
└── lancedb/                           # LanceDB storage
    ├── items.lance                    # Main items table
    └── {other_tables}.lance           # Additional tables

models/                                # HuggingFace model cache (configurable)
├── .gitkeep                          # Keeps directory in git
└── {downloaded_models}/              # Cached models (gitignored)

cache/                                # Application cache
└── {cache_files}                     # Temporary cache files (gitignored)
```

### Database Indices & Performance
- **Primary Key**: Scalar index on `link` for O(1) upserts and lookups
- **Full-Text Search**: Optional FTS index on `markdown` field for semantic queries
- **Future Enhancement**: Vector embeddings index for semantic similarity (orthogonal to MCP core functionality)
- **Change Detection**: SHA-1 content hashing minimizes unnecessary writes

### FastMCP Server Configuration
```python
from fastmcp import FastMCP

mcp = FastMCP("SCP Foundation Server")

# Configure for production
mcp.add_middleware(TimingMiddleware())
mcp.add_middleware(LoggingMiddleware(include_payloads=True))
mcp.add_middleware(RateLimitingMiddleware(max_requests_per_second=50))

# Multiple transport support
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)  # Production
    # mcp.run()  # Development (STDIO)
```

### Environment Configuration System
**Layered Environment Management for Flexible Deployment**

The project uses a structured environment configuration system with multiple files for different purposes:

**Configuration Files:**
- **`.env.template`** - Base configuration template (committed to git)
  - Contains default values for all configuration options
  - Includes comprehensive sections: app, database, AI/ML, performance, security
  - Serves as the foundation for all environment setups
- **`.env.example`** - Documented example file (committed to git)
  - Shows how to override default settings with examples
  - Includes detailed comments and common development configurations
  - Demonstrates API key setup and customization options
- **`.env.local`** - Personal local settings (gitignored)
  - Your actual configuration with real API keys and custom settings
  - Created by copying `.env.template` and customizing
  - Never committed to version control for security
- **`.env.local.example`** - Personal settings template (gitignored)
  - Template showing how to structure personal configurations
  - Examples of real-world local development setups

**Loading Priority & Hierarchy:**
1. **`.env.template`** (base defaults) - Loaded first
2. **`.env.local`** (personal overrides) - Loaded second, overrides template values
3. **Environment variables** (system/runtime) - Loaded last, highest priority

**Key Configuration Categories:**
- **HuggingFace Models**: Default cache location `./models` with configurable paths
- **Database**: LanceDB storage location and performance settings
- **API Keys**: OpenAI, Anthropic, HuggingFace tokens (set in `.env.local`)
  - **OpenAI Configuration**: `OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_MODEL`
  - **Alternative Endpoints**: Support for OpenRouter, LocalAI, Ollama via `OPENAI_API_BASE`
- **Performance**: Rate limiting, batch sizes, caching configuration
- **Security**: CORS settings, authentication, license compliance
- **Development**: Debug flags, hot reload, profiling options

**Environment Setup:**
```bash
make setup-env    # Automated setup (recommended)
# OR
cp .env.template .env.local  # Manual setup
```

### Data Management & Build System
**Makefile Targets:**
- `make setup-env` - Set up environment configuration (.env.local from template)
- `make data` - Ensure SCP data is available (downloads if missing)
- `make download` - Force download of fresh SCP data
- `make clean-data` - Remove all downloaded SCP data (`data/raw/scp-*`)
- `make help` - Show all available targets with descriptions

**Download Script Features:**
- **Sparse Checkout**: Only downloads `docs/data/scp` subdirectory for efficiency
- **Shallow Clone**: Uses `--depth 1` to minimize bandwidth and storage
- **Atomic Operations**: Downloads to temp directory, then moves to final location
- **Commit Tracking**: Directory names include timestamp and commit ID for traceability
- **Cross-Platform**: Works with both modern and legacy Git versions

### Data Export Scripts
**Utility Scripts for Data Export and Analysis**

The project includes production-ready export scripts for extracting SCP data in various formats:

#### JSON Export (`scripts/export_json.py`)
```bash
# Export all items to hierarchical JSON structure
./scripts/export_json.py

# Export specific items or ranges
./scripts/export_json.py SCP-173          # Single item
./scripts/export_json.py 100-200          # Range export
./scripts/export_json.py --random 50      # Random sampling

# Custom output location
./scripts/export_json.py --output ./backup/ --random 100
```

#### Markdown Export (`scripts/export_markdown.py`)
```bash
# Export with YAML frontmatter metadata
./scripts/export_markdown.py --random 25

# All formats support flexible identifiers
./scripts/export_markdown.py 682          # SCP-682
./scripts/export_markdown.py scp-173      # Case insensitive
```

#### AI Summary Export (`scripts/export_summary.py`)
```bash
# Export AI-generated summaries with YAML frontmatter
./scripts/export_summary.py --random 10

# Skip existing files (default) or force regeneration
./scripts/export_summary.py --force SCP-173

# Custom endpoints and concurrency control
./scripts/export_summary.py --max-concurrent 3 --random 5

# Requires OpenAI API key and compatible endpoint
```

**Export Features:**
- **Hierarchical Organization**: Files organized by SCP identifier (e.g., `1/2/3/4/scp-1234.ext`)
- **Flexible Input**: Accepts `SCP-XXXX`, numeric, or `scp-xxxx` formats
- **Range Processing**: Intelligent range parsing (e.g., `1-999` for Series I)
- **Random Sampling**: Unbiased selection for testing and analysis
- **Progress Reporting**: Batch processing with status updates
- **Content Conversion**: HTML-to-Markdown transformation for readability
- **YAML Frontmatter**: Structured metadata in exports with full versioning information
- **Versioning Metadata**: Includes `dataset_commit` and `content_sha1` for reproducible reads and integrity verification
- **CC BY-SA 3.0 Compliance**: Automatic attribution inclusion

**AI Summary Export Additional Features:**
- **Skip Existing Files**: Automatically resumes interrupted runs by skipping completed summaries
- **Force Regeneration**: `--force` flag to overwrite existing summaries
- **Custom AI Endpoints**: Support for OpenAI-compatible APIs (OpenRouter, LocalAI, Ollama)
- **Rate Limiting**: Configurable concurrent API calls to respect service limits
- **Error Resilience**: Graceful handling of API failures without creating broken files
- **AI-Specific Metadata**: Includes `ai_generated: true` and `content_type: "ai_summary"` fields

**Output Structure:**
```
data/staging/
├── json/                           # Raw JSON exports
│   ├── 1/7/3/scp-173.json         # Hierarchical organization
│   └── 6/8/2/scp-682.json         # Complete metadata + content
├── markdown/                       # Markdown with YAML frontmatter
│   ├── 1/7/3/scp-173.md           # AI-friendly format
│   └── 6/8/2/scp-682.md           # Structured metadata header
└── summary/                        # AI-generated summaries
    ├── 1/7/3/scp-173.md           # AI summary with metadata
    └── 6/8/2/scp-682.md           # Concise AI-generated content
```

**Use Cases:**
- **Data Analysis**: Export subsets for statistical analysis
- **Content Migration**: Transfer data to other systems
- **Backup & Archival**: Create portable data snapshots
- **AI Training**: Generate structured datasets for ML workflows
- **Documentation**: Create human-readable SCP archives
- **AI Summaries**: Generate concise, AI-powered summaries for quick reference and analysis

### Content Processing Utilities
**Core Modules for Data Loading and Content Conversion**

The project includes specialized utility modules for handling SCP data processing and content transformation:

#### Data Loader (`src/scp_mcp/utils/data_loader.py`)
**Handles loading SCP data from the dataset files with flexible identifier support**

**Key Functions:**
```python
# Load complete SCP data with metadata and content
load_scp_data(scp_identifier: str) -> Optional[dict]
    # Accepts: "SCP-173", "173", "scp-173"
    # Returns: Full item dictionary with all available fields including dataset_commit and content_sha1

# Get all available SCP item IDs from index
get_all_item_ids() -> Optional[list[str]]
    # Returns: List of all SCP identifiers in dataset

# Generate hierarchical debug folder path
get_debug_folder_path(scp_item: dict) -> str
    # Input: SCP item dictionary
    # Returns: "1/7/3" for SCP-173, "6/8/2" for SCP-682

# Extract HTML content for conversion
get_scp_html_content(scp_identifier: str) -> Optional[str]
    # Returns: raw_content or raw_source HTML for processing
```

**Features:**
- **Flexible Identifier Resolution**: Normalizes various SCP ID formats
- **Automatic Content Merging**: Combines index metadata with content files
- **Versioning Field Generation**: Automatically adds `dataset_commit` and `content_sha1` fields
- **Hierarchical Path Generation**: Creates organized directory structures
- **Fallback Content Handling**: Uses raw_source when raw_content unavailable
- **Error Resilience**: Graceful handling of missing or malformed data

#### Content Converter (`src/scp_mcp/utils/content_converter.py`)
**Transforms SCP Foundation content from raw HTML to AI-friendly markdown format**

**Primary Function:**
```python
html_to_markdown(html_content: str) -> Optional[str]
    # Main entry point for HTML-to-Markdown conversion
    # Returns: AI-optimized markdown or None if conversion fails
```

**Conversion Pipeline:**
1. **HTML Cleanup**: Remove boilerplate elements (licensing, rating widgets, navigation)
2. **Interactive Element Removal**: Strip JavaScript, forms, and dynamic content
3. **Structure Preservation**: Maintain content hierarchy and formatting
4. **SCP-Specific Handling**: Process redacted text, classification bars, special formatting
5. **Markdown Optimization**: Convert to clean, readable markdown for AI consumption
6. **Error Recovery**: Robust fallback mechanisms for malformed HTML

**Advanced Features:**
- **Boilerplate Removal**: Strips 50+ types of non-content elements
- **Section Header Conversion**: Transforms HTML headers to proper markdown
- **Special Formatting**: Handles SCP-specific elements (DATA EXPUNGED, [REDACTED])
- **Table Conversion**: Converts HTML tables to markdown format
- **Image Processing**: Preserves images with proper markdown syntax
- **Whitespace Normalization**: Cleans excessive spacing while maintaining structure

**Content Processing Rules:**
- **Discard**: License boxes, rating widgets, navigation, ads, comments
- **Preserve**: Main content, images, tables, lists, blockquotes, headers
- **Transform**: HTML structure to markdown equivalents
- **Optimize**: For AI/LLM comprehension and processing

**Integration with Data Pipeline:**
- **Ingest Phase**: Converts `raw_content` to `markdown` field during processing
- **Export Scripts**: Used by markdown export for content transformation
- **MCP Resources**: Powers AI-optimized content delivery via `urn:scp:item:{id}/content`
- **Fallback Handling**: Graceful degradation when conversion fails

### Performance Optimizations
- **Change-Only Upserts**: Only write rows when `content_sha1` differs
- **Batch Processing**: Bulk ingest operations for efficiency
- **Concurrent Reads**: LanceDB allows reads during write operations
- **Version Cleanup**: Configurable retention policies prevent unbounded growth
- **Efficient Downloads**: Sparse checkout reduces bandwidth by ~90%

---

## 10) Usage Examples for AI Agents

**Practical Integration Patterns**

### Identifier Resolution
```python
# Flexible input formats
tool_input = "682"                    # → scp="SCP-682", link="scp-682"
tool_input = "SCP-682"               # → scp="SCP-682", link="scp-682"  
tool_input = "scp-682"               # → scp="SCP-682", link="scp-682"

# Resource URIs
metadata_uri = "urn:scp:item:SCP-682"         # Basic metadata
content_uri = "urn:scp:item:SCP-682/content"  # Full content for AI processing
```

### Search Operations
```python
# Find popular joke entries
search_params = {
    "query": "",
    "tags": ["joke"],
    "min_rating": 100,
    "limit": 25
}

# Natural language search
search_params = {
    "query": "dangerous reptilian entity",
    "series": "series-1",
    "limit": 10
}
```

### FastMCP Client Integration
```python
from fastmcp import Client

async def query_scp_data():
    async with Client("scp_server.py") as client:
        # Search for items
        results = await client.call_tool("search_items", {
            "query": "anomalous objects",
            "limit": 5
        })
        
        # Get detailed content
        content = await client.call_tool("get_item_content", 
                                       {"identifier": "SCP-173"})
        
        # Access resources
        index = await client.read_resource("urn:scp:index:items")
```

---

## 11) Technical References & Standards

**Foundation Technologies & Specifications**

### Core Technologies
- **[Model Context Protocol](https://modelcontextprotocol.io/)**: JSON-RPC 2.0 based protocol for AI-application integration
- **[FastMCP Framework](https://github.com/jlowin/fastmcp)**: Python framework for high-performance MCP servers
- **[LanceDB](https://lancedb.com/)**: Vector database with automatic versioning and time-travel capabilities
- **[SCP Data API](https://scp-data.tedivm.com/)**: Upstream dataset source with structured metadata and content

### MCP Specification Compliance
- **Resources**: URI-addressed read-only data sources (`urn:scp:*` scheme)
- **Tools**: Schema-validated operations with JSON-RPC 2.0 interface
- **Transport**: STDIO (default), HTTP, SSE protocols supported
- **Versioning**: Reproducible reads via embedded version metadata

### LanceDB Features Utilized
- **Automatic Versioning**: Every table modification creates new version
- **Time-Travel Queries**: Access historical data via `checkout(version)` and `restore()`
- **Merge-Insert Upserts**: Efficient change-only writes with conflict resolution
- **Concurrent Access**: Non-blocking reads during write operations

### Licensing & Attribution
- **Content License**: CC BY-SA 3.0 as mandated by SCP Wiki
- **Image Policy**: Separate licensing terms for visual content
- **Attribution Requirements**: Automatic inclusion in substantial content responses
- **AI Compliance**: Guidelines for AI-generated derivative works

**Architecture Philosophy**: Built for autonomous AI agents with emphasis on reproducibility, version consistency, and intelligent error handling while maintaining full compliance with SCP Foundation licensing requirements.
