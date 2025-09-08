import json
import os
import re
from pathlib import Path
from typing import List, Set

from dotenv import load_dotenv
from langchain.schema import Document

load_dotenv()


class Items:
    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or self._find_latest_data_dir()

    def _find_latest_data_dir(self) -> str:
        """Find the latest SCP data directory based on timestamp."""
        base_dir_str = os.getenv("SCP_DATA_DIR", "./data")
        base_dir = Path(base_dir_str)

        if not base_dir.exists():
            raise FileNotFoundError("No data directory found")

        scp_dirs = []
        pattern = re.compile(r'^scp-(\d+)-([a-f0-9]+)$')

        for d in base_dir.iterdir():
            if d.is_dir():
                match = pattern.match(d.name)
                if match:
                    timestamp = int(match.group(1))
                    scp_dirs.append((timestamp, d))

        if not scp_dirs:
            raise FileNotFoundError("No SCP data directories found")

        latest_dir = max(scp_dirs, key=lambda x: x[0])[1]
        return str(latest_dir / "items")

    def _get_unique_content_files(self) -> Set[str]:
        """Extract unique content_file values from index.json."""
        index_path = Path(self.data_dir) / "index.json"

        if not index_path.exists():
            raise FileNotFoundError(f"index.json not found at {index_path}")

        content_files = set()

        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        for item_data in index_data.values():
            if 'content_file' in item_data:
                content_files.add(item_data['content_file'])

        return content_files

    def load_items(self) -> List[Document]:
        """Load all SCP items and convert them to LangChain Documents."""
        documents = []
        content_files = self._get_unique_content_files()

        for content_file in content_files:
            content_path = Path(self.data_dir) / content_file

            if not content_path.exists():
                continue

            try:
                with open(content_path, 'r', encoding='utf-8') as f:
                    content_data = json.load(f)

                for item_id, item_data in content_data.items():
                    doc = self._create_document(item_id, item_data)
                    documents.append(doc)

            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading {content_file}: {e}")
                continue

        return documents

    def _create_document(self, item_id: str, item_data: dict) -> Document:
        """Create a LangChain Document from item data."""
        content_parts = []

        if 'title' in item_data:
            content_parts.append(f"Title: {item_data['title']}")

        if 'raw_content' in item_data:
            content_parts.append(f"Content: {item_data['raw_content']}")
        elif 'raw_source' in item_data:
            content_parts.append(f"Source: {item_data['raw_source']}")

        page_content = '\n\n'.join(content_parts)

        metadata = {
            'item_id': item_id,
            'scp': item_data.get('scp', item_id),
            'title': item_data.get('title', ''),
            'url': item_data.get('url', ''),
            'creator': item_data.get('creator', ''),
            'created_at': item_data.get('created_at', ''),
            'rating': item_data.get('rating', 0),
            'tags': item_data.get('tags', []),
            'series': item_data.get('series', ''),
            'object_class': self._get_object_class_from_tags(item_data.get('tags', [])),
        }

        return Document(page_content=page_content, metadata=metadata, id=item_id)

    def _get_object_class_from_tags(self, tags: list) -> str:
        """Extract object class from tags based on common SCP object class patterns."""
        if not hasattr(self, '_object_classes'):
            self._object_classes = self._discover_object_classes()

        for tag in tags:
            if tag.lower() in self._object_classes:
                return tag.title()

        return ''

    def _discover_object_classes(self) -> set:
        """Discover object classes from all items in the dataset."""
        object_classes = set()
        known_patterns = {
            'safe', 'euclid', 'keter', 'thaumiel', 'apollyon', 'archon',
            'explained', 'neutralized', 'decommissioned', 'esoteric-class',
            'pending', 'uncontained', 'maksur'
        }

        try:
            index_path = Path(self.data_dir) / "index.json"
            if index_path.exists():
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)

                for item_data in index_data.values():
                    tags = item_data.get('tags', [])
                    for tag in tags:
                        if tag.lower() in known_patterns:
                            object_classes.add(tag.lower())

        except (json.JSONDecodeError, FileNotFoundError):
            pass

        # Fallback to common object classes if discovery fails
        if not object_classes:
            object_classes = {'safe', 'euclid', 'keter', 'explained'}

        return object_classes
