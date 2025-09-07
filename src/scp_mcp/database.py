"""LanceDB database interface for SCP data."""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import lancedb
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

from .models import SCPItem, VectorSearchResult

logger = logging.getLogger(__name__)


class SCPDatabase:
    """Database interface for SCP data using LanceDB."""

    def __init__(
        self,
        db_path: str = "./data/scp_lancedb",
        embedding_model: str = "all-MiniLM-L6-v2",
        data_dir: str = "./data"
    ):
        """Initialize the SCP database.

        Args:
            db_path: Path to LanceDB database
            embedding_model: Name of the sentence transformer model
            data_dir: Directory containing SCP data
        """
        self.db_path = Path(db_path)
        self.data_dir = Path(data_dir)
        self.embedding_model = SentenceTransformer(embedding_model)

        # Connect to LanceDB
        self.db = lancedb.connect(str(self.db_path))

        # Initialize tables
        self.scp_table = None
        self._initialize_tables()

    def _initialize_tables(self) -> None:
        """Initialize database tables if they don't exist."""
        try:
            self.scp_table = self.db.open_table("scp_items")
            logger.info("Opened existing SCP table")
        except Exception:
            logger.info("Creating new SCP table")
            self._create_scp_table()

    def _create_scp_table(self) -> None:
        """Create the SCP items table with vector embeddings."""
        # Create table with minimal initial data to establish schema
        import pyarrow as pa
        schema = pa.schema([
            pa.field("item_id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("content", pa.string()),
            pa.field("embedding", pa.list_(pa.float32())),
        ])

        # Create with a single dummy row to establish the table
        dummy_data = [{
            "item_id": "SCP-000",
            "title": "Dummy SCP",
            "content": "This is a dummy SCP for table initialization",
            "embedding": [0.0] * 384  # Match the embedding dimension
        }]

        self.scp_table = self.db.create_table("scp_items", data=dummy_data, schema=schema)
        logger.info("Created SCP table with schema")

    def load_scp_data(self, scp_data_path: Optional[str] = None) -> None:
        """Load SCP data from the data directory.

        Args:
            scp_data_path: Optional specific path to SCP data directory
        """
        if scp_data_path:
            scp_path = Path(scp_data_path)
        else:
            # Find the latest SCP data directory
            scp_dirs = list(self.data_dir.glob("scp-*"))
            if not scp_dirs:
                raise ValueError("No SCP data directories found. Run 'make data' first.")
            scp_path = max(scp_dirs, key=lambda x: x.stat().st_mtime)

        logger.info(f"Loading SCP data from {scp_path}")

        items = []
        items_path = scp_path / "items"

        if not items_path.exists():
            logger.warning(f"No items directory found in {scp_path}")
            return

        # Process different series and categories
        for series_dir in items_path.iterdir():
            if series_dir.is_dir():
                self._process_series_directory(series_dir, items)

        if items:
            self._insert_items(items)
            logger.info(f"Loaded {len(items)} SCP items")
        else:
            logger.warning("No SCP items found to load")

    def _process_series_directory(self, series_dir: Path, items: List[Dict[str, Any]]) -> None:
        """Process a series directory and extract SCP items."""
        series_name = series_dir.name

        for item_file in series_dir.glob("*.md"):
            try:
                item_data = self._parse_scp_file(item_file, series_name)
                if item_data:
                    items.append(item_data)
            except Exception as e:
                logger.error(f"Error processing {item_file}: {e}")

    def _parse_scp_file(self, file_path: Path, series: str) -> Optional[Dict[str, Any]]:
        """Parse an SCP markdown file and extract structured data."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract item ID from filename or content
            item_id = self._extract_item_id(file_path, content)
            if not item_id:
                return None

            # Extract title
            title = self._extract_title(content)

            # Extract object class
            object_class = self._extract_object_class(content)

            # Extract containment procedures
            containment_procedures = self._extract_section(content, "Special Containment Procedures")

            # Extract description
            description = self._extract_section(content, "Description")

            # Extract tags (if available in frontmatter or content)
            tags = self._extract_tags(content)

            # Create embedding for the content
            embedding = self.embedding_model.encode(content).tolist()

            return {
                "item_id": item_id,
                "title": title,
                "content": content,
                "object_class": object_class,
                "containment_procedures": containment_procedures,
                "description": description,
                "additional_notes": None,
                "tags": json.dumps(tags),
                "series": series,
                "category": self._categorize_item(item_id),
                "url": f"http://www.scp-wiki.net/{item_id.lower().replace(' ', '-')}",
                "created_date": None,
                "last_updated": None,
                "rating": None,
                "votes": None,
                "embedding": embedding,
            }

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None

    def _extract_item_id(self, file_path: Path, content: str) -> Optional[str]:
        """Extract the SCP item ID from filename or content."""
        # Try to extract from filename first
        filename = file_path.stem
        if filename.upper().startswith('SCP-'):
            return filename.upper()

        # Try to extract from content
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if 'SCP-' in line.upper():
                # Simple extraction - can be improved with regex
                parts = line.upper().split()
                for part in parts:
                    if part.startswith('SCP-'):
                        return part

        return None

    def _extract_title(self, content: str) -> str:
        """Extract the title from the content."""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('**'):
                return line[:200]  # Limit length
        return "Unknown Title"

    def _extract_object_class(self, content: str) -> Optional[str]:
        """Extract the object class from the content."""
        object_classes = ['Safe', 'Euclid', 'Keter', 'Thaumiel', 'Neutralized', 'Explained']
        content_upper = content.upper()

        for obj_class in object_classes:
            if obj_class.upper() in content_upper:
                return obj_class

        return None

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a specific section from the content."""
        lines = content.split('\n')
        in_section = False
        section_lines = []

        for line in lines:
            line_upper = line.upper()
            if section_name.upper() in line_upper and ('**' in line or '##' in line):
                in_section = True
                continue
            elif in_section:
                if line.strip() == '' and len(section_lines) > 0:
                    # End of section (double newline)
                    break
                section_lines.append(line)

        return '\n'.join(section_lines).strip() if section_lines else None

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from the content."""
        # This is a simplified implementation
        # In a real scenario, you might want to parse frontmatter or use more sophisticated extraction
        tags = []

        # Look for common SCP themes
        common_tags = [
            'humanoid', 'alive', 'sapient', 'sentient', 'predatory',
            'hostile', 'safe', 'euclid', 'keter', 'thaumiel',
            'teleportation', 'mind-affecting', 'compulsion', 'memetic',
            'infohazard', 'cognitohazard', 'temporal', 'spatial',
            'extradimensional', 'indestructible', 'regenerative'
        ]

        content_lower = content.lower()
        for tag in common_tags:
            if tag in content_lower:
                tags.append(tag)

        return tags

    def _categorize_item(self, item_id: str) -> str:
        """Categorize the SCP item based on its ID."""
        if not item_id:
            return "unknown"

        if '001' in item_id:
            return "001"
        elif 'J' in item_id:
            return "joke"
        elif 'EX' in item_id:
            return "explained"
        elif 'ARCHIVED' in item_id:
            return "archived"
        else:
            # Extract series number
            try:
                number = int(item_id.replace('SCP-', '').replace('-', ''))
                if number <= 999:
                    return "series-1"
                elif number <= 1999:
                    return "series-2"
                elif number <= 2999:
                    return "series-3"
                elif number <= 3999:
                    return "series-4"
                elif number <= 4999:
                    return "series-5"
                else:
                    return "series-6+"
            except ValueError:
                return "unknown"

    def _insert_items(self, items: List[Dict[str, Any]]) -> None:
        """Insert items into the database."""
        if not items:
            return

        # Convert to DataFrame for batch insertion
        df = pd.DataFrame(items)

        # Add to LanceDB table
        self.scp_table.add(df)
        logger.info(f"Inserted {len(items)} items into database")

    def vector_search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[VectorSearchResult]:
        """Perform vector search on SCP items.

        Args:
            query: Search query text
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            List of vector search results
        """
        # Generate embedding for the query
        query_embedding = self.embedding_model.encode(query)

        # Perform vector search
        results = self.scp_table.search(query_embedding).limit(limit).to_pandas()

        # Filter by threshold and convert to results
        search_results = []
        for idx, row in results.iterrows():
            if row.get('_distance', 1.0) < threshold:
                result = VectorSearchResult(
                    item_id=row['item_id'],
                    title=row['title'],
                    content_snippet=row['content'][:200] + '...' if len(row['content']) > 200 else row['content'],
                    score=1.0 - row.get('_distance', 0.0),
                    metadata={
                        'object_class': row.get('object_class'),
                        'series': row.get('series'),
                        'category': row.get('category'),
                    }
                )
                search_results.append(result)

        return search_results

    def get_item(self, item_id: str) -> Optional[SCPItem]:
        """Get a specific SCP item by ID.

        Args:
            item_id: The SCP item ID

        Returns:
            SCPItem if found, None otherwise
        """
        results = self.scp_table.search().where(f"item_id = '{item_id}'").limit(1).to_pandas()

        if len(results) == 0:
            return None

        row = results.iloc[0]

        return SCPItem(
            item_id=row['item_id'],
            title=row['title'],
            content=row['content'],
            object_class=row.get('object_class'),
            containment_procedures=row.get('containment_procedures'),
            description=row.get('description'),
            additional_notes=row.get('additional_notes'),
            tags=json.loads(row.get('tags', '[]')),
            series=row.get('series'),
            category=row.get('category'),
            url=row.get('url'),
            created_date=datetime.fromisoformat(row['created_date']) if row.get('created_date') else None,
            last_updated=datetime.fromisoformat(row['last_updated']) if row.get('last_updated') else None,
            rating=row.get('rating'),
            votes=row.get('votes'),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary containing database statistics
        """
        count = len(self.scp_table)

        # Get some sample data for analysis
        sample_df = self.scp_table.search().limit(100).to_pandas()

        stats = {
            'total_items': count,
            'object_classes': sample_df['object_class'].value_counts().to_dict() if 'object_class' in sample_df else {},
            'series': sample_df['series'].value_counts().to_dict() if 'series' in sample_df else {},
            'categories': sample_df['category'].value_counts().to_dict() if 'category' in sample_df else {},
        }

        return stats
