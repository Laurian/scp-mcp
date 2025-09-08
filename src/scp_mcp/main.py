"""Main entry point for the SCP MCP server."""

from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(name="SCP MCP Server")


@mcp.tool
def get_item(id: str) -> str:
    """Get an SCP item by ID.

    Args:
        id: The SCP item ID to retrieve

    Returns:
        The SCP item data
    """
    logger.info(f"Getting SCP item: {id}")
    return "OK"


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the SCP MCP server."""
    try:
        logger.info("Starting SCP MCP server on http://localhost:8000/mcp/...")
        mcp.run(transport="http", host="localhost", port=8000)
    except Exception as e:
        logger.error(f"Failed to start SCP MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
