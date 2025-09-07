"""SCP MCP Server - A FastMCP server for SCP Foundation data using LanceDB."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .server import SCPServer
from .database import SCPDatabase
from .models import SCPItem, SearchResult

__all__ = ["SCPServer", "SCPDatabase", "SCPItem", "SearchResult"]
