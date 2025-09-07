"""Main entry point for the SCP MCP server."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from .database import LanceDBManager
from .ingest_items import ingest_items

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the SCP MCP server."""
    try:
        # TODO: Initialize MCP server
        # TODO: Load SCP data
        # TODO: Start MCP server

        logger.info("SCP MCP server initialized successfully")

    except Exception as e:
        logger.error(f"Failed to start SCP MCP server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
