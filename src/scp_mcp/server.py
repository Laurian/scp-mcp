"""FastMCP server implementation for SCP Foundation data."""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastmcp import FastMCP, Context

from .database import SCPDatabase
from .models import SCPItem, VectorSearchResult, SearchQuery

logger = logging.getLogger(__name__)


class SCPServer:
    """MCP server for SCP Foundation data."""

    def __init__(
        self,
        db_path: str = "./data/scp_lancedb",
        data_dir: str = "./data",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """Initialize the SCP MCP server.

        Args:
            db_path: Path to LanceDB database
            data_dir: Directory containing SCP data
            embedding_model: Name of the sentence transformer model
        """
        self.db_path = db_path
        self.data_dir = data_dir
        self.embedding_model = embedding_model

        # Initialize database
        self.db = SCPDatabase(
            db_path=db_path,
            data_dir=data_dir,
            embedding_model=embedding_model
        )

        # Initialize FastMCP server
        self.mcp = FastMCP(
            "scp-mcp",
            version="0.1.0"
        )

        # Register tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.mcp.tool()
        async def search_scp_items(
            query: str,
            limit: int = 10,
            threshold: float = 0.7
        ) -> List[Dict[str, Any]]:
            """Search for SCP items using vector similarity.

            Args:
                query: Search query text
                limit: Maximum number of results (1-100)
                threshold: Minimum similarity threshold (0.0-1.0)

            Returns:
                List of matching SCP items with similarity scores
            """
            try:
                results = self.db.vector_search(query, limit=limit, threshold=threshold)

                # Convert to serializable format
                return [
                    {
                        "item_id": result.item_id,
                        "title": result.title,
                        "content_snippet": result.content_snippet,
                        "score": float(result.score),
                        "metadata": result.metadata
                    }
                    for result in results
                ]
            except Exception as e:
                logger.error(f"Error searching SCP items: {e}")
                return []

        @self.mcp.tool()
        async def get_scp_item(item_id: str) -> Optional[Dict[str, Any]]:
            """Get a specific SCP item by ID.

            Args:
                item_id: The SCP item ID (e.g., 'SCP-001', 'SCP-173')

            Returns:
                The SCP item details or None if not found
            """
            try:
                item = self.db.get_item(item_id)
                if item:
                    return item.dict()
                return None
            except Exception as e:
                logger.error(f"Error getting SCP item {item_id}: {e}")
                return None

        @self.mcp.tool()
        async def get_scp_stats() -> Dict[str, Any]:
            """Get database statistics.

            Returns:
                Database statistics including total items, object classes, series, etc.
            """
            try:
                return self.db.get_stats()
            except Exception as e:
                logger.error(f"Error getting SCP stats: {e}")
                return {"error": str(e)}

        @self.mcp.tool()
        async def load_scp_data(scp_data_path: Optional[str] = None) -> Dict[str, Any]:
            """Load SCP data from the data directory.

            Args:
                scp_data_path: Optional specific path to SCP data directory.
                             If not provided, uses the latest available data.

            Returns:
                Status of the loading operation
            """
            try:
                self.db.load_scp_data(scp_data_path)
                stats = self.db.get_stats()
                return {
                    "status": "success",
                    "message": f"Loaded {stats.get('total_items', 0)} SCP items",
                    "stats": stats
                }
            except Exception as e:
                logger.error(f"Error loading SCP data: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }

        @self.mcp.tool()
        async def find_similar_scp_items(
            item_id: str,
            limit: int = 5,
            threshold: float = 0.6
        ) -> List[Dict[str, Any]]:
            """Find SCP items similar to a given item.

            Args:
                item_id: The reference SCP item ID
                limit: Maximum number of similar items to return
                threshold: Minimum similarity threshold

            Returns:
                List of similar SCP items
            """
            try:
                # Get the reference item
                reference_item = self.db.get_item(item_id)
                if not reference_item:
                    return []

                # Use the item's content as search query
                results = self.db.vector_search(
                    reference_item.content,
                    limit=limit + 1,  # +1 to exclude the item itself
                    threshold=threshold
                )

                # Filter out the reference item itself and convert to serializable format
                similar_items = []
                for result in results:
                    if result.item_id != item_id:
                        similar_items.append({
                            "item_id": result.item_id,
                            "title": result.title,
                            "content_snippet": result.content_snippet,
                            "score": float(result.score),
                            "metadata": result.metadata
                        })

                return similar_items[:limit]

            except Exception as e:
                logger.error(f"Error finding similar SCP items: {e}")
                return []

    async def initialize(self) -> None:
        """Initialize the server and load data if available."""
        logger.info("Initializing SCP MCP server...")

        # Check if we have SCP data available
        data_path = Path(self.data_dir)
        scp_dirs = list(data_path.glob("scp-*"))

        if scp_dirs:
            logger.info(f"Found {len(scp_dirs)} SCP data directories, loading latest...")
            self.db.load_scp_data()
            stats = self.db.get_stats()
            logger.info(f"Database initialized with {stats.get('total_items', 0)} SCP items")
        else:
            logger.warning("No SCP data directories found. Run 'make data' to download SCP data.")

    def run(self, host: str = "localhost", port: int = 8000) -> None:
        """Run the MCP server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        # Initialize the server
        asyncio.run(self.initialize())

        # Run the MCP server
        logger.info(f"Starting SCP MCP server on {host}:{port}")
        self.mcp.run(host=host, port=port)


# Convenience function to create and run the server
def main():
    """Main entry point for the SCP MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = SCPServer()
    server.run()


if __name__ == "__main__":
    main()
