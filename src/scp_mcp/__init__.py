"""SCP MCP Server - A Model Context Protocol Server for SCP Foundation Data.

This package provides a FastMCP-based server that exposes SCP Foundation
data through the Model Context Protocol (MCP) for AI agents and Large
Language Models.

Key Features:
- FastMCP framework for high-performance MCP server
- LanceDB for versioned, time-travel capable storage
- AI-optimized markdown content generation
- Flexible identifier formats (SCP-XXXX, numeric, link slugs)
- CC BY-SA 3.0 compliant attribution handling
- Reproducible reads with version tracking
"""

__version__ = "0.1.0"
__author__ = "SCP MCP Contributors"
__license__ = "MIT"

# Public API exports
from .config import Settings
from .models import ItemHit, SCPItem, SearchResult
from .server import SCPMCPServer

__all__ = [
    "SCPMCPServer",
    "SCPItem",
    "ItemHit",
    "SearchResult",
    "Settings",
    "__version__",
]
