"""
SCP Data Loader Module

Handles loading SCP data from the dataset files.
This module provides utilities to load SCP items from the raw dataset structure.

Usage example:
    from scp_mcp.utils.data_loader import get_scp_html_content
    from scp_mcp.utils.content_converter import html_to_markdown

    # Load HTML content for an SCP
    html_content = get_scp_html_content("SCP-002")
    if html_content:
        # Convert to markdown
        markdown = html_to_markdown(html_content)
        if markdown:
            print(markdown)
"""

import hashlib
import json
from typing import Optional

from ..config import settings


def load_scp_data(scp_identifier: str) -> Optional[dict]:  # noqa: UP045
    """Load SCP data from the latest dataset.

    Args:
        scp_identifier: SCP identifier (e.g., "SCP-002", "002", "scp-002")

    Returns:
        Dict with SCP data including raw_content, dataset_commit, and content_sha1 fields, or None if not found
    """
    # Normalize identifier to SCP-XXXX format
    if scp_identifier.isdigit():
        scp_label = f"SCP-{int(scp_identifier):03d}"
    elif scp_identifier.lower().startswith("scp-"):
        # Convert to proper format (e.g., "scp-002" -> "SCP-002")
        num_part = scp_identifier[4:]
        if num_part.isdigit():
            scp_label = f"SCP-{int(num_part):03d}"
        else:
            scp_label = scp_identifier.upper()
    else:
        scp_label = scp_identifier.upper()
        if not scp_label.startswith("SCP-"):
            scp_label = f"SCP-{scp_label}"

    # Get the latest data directory
    items_path = settings.get_scp_items_path()
    if not items_path or not items_path.exists():
        return None

    # Extract dataset_commit from the directory name
    # Directory format: scp-{timestamp}-{commit_id}
    latest_dir = settings.get_latest_scp_data_dir()
    dataset_commit = None
    if latest_dir:
        dir_name = latest_dir.name
        # Extract commit ID from directory name (last part after final dash)
        parts = dir_name.split('-')
        if len(parts) >= 3:  # scp-timestamp-commit_id (at minimum)
            dataset_commit = parts[-1]  # Last part is the commit ID

    index_file = items_path / "index.json"
    if not index_file.exists():
        return None

    try:
        # Load index to find content file
        with open(index_file, 'r', encoding='utf-8') as f:  # noqa: UP015
            index_data = json.load(f)

        # Find the SCP in index
        if scp_label not in index_data:
            return None

        item_metadata = index_data[scp_label]
        content_file = item_metadata.get('content_file')

        if not content_file:
            return None

        # Load the content file
        content_file_path = items_path / content_file
        if not content_file_path.exists():
            return None

        with open(content_file_path, 'r', encoding='utf-8') as f:  # noqa: UP015
            content_data = json.load(f)

        # Get the specific item data
        if scp_label not in content_data:
            return None

        item_data = content_data[scp_label].copy()

        # Add dataset_commit if we extracted it
        if dataset_commit:
            item_data['dataset_commit'] = dataset_commit

        # Calculate and add content_sha1 if raw_content exists
        raw_content = item_data.get('raw_content')
        if raw_content:
            content_sha1 = hashlib.sha1(raw_content.encode('utf-8')).hexdigest()
            item_data['content_sha1'] = content_sha1

        return item_data

    except (json.JSONDecodeError, KeyError, IOError):  # noqa: UP024
        return None


def get_all_item_ids() -> Optional[list[str]]:  # noqa: UP045
    """Get all SCP item IDs from the index.json file.

    Returns:
        List of SCP item IDs (keys from index.json), or None if index not found
    """
    # Get the latest data directory
    items_path = settings.get_scp_items_path()
    if not items_path or not items_path.exists():
        return None

    index_file = items_path / "index.json"
    if not index_file.exists():
        return None

    try:
        # Load index and return keys
        with open(index_file, 'r', encoding='utf-8') as f:  # noqa: UP015
            index_data = json.load(f)

        return list(index_data.keys())

    except (json.JSONDecodeError, IOError):  # noqa: UP024
        return None


def get_debug_folder_path(scp_item: dict) -> str:
    """Generate a debug folder path for an SCP item by splitting its identifier.

    Args:
        scp_item: SCP item dictionary containing at least 'scp' or 'link' field

    Returns:
        Folder path string (e.g., "1/2/3/4" for "scp-1234")
    """
    # Try to get identifier from different possible fields
    scp_id = scp_item.get('scp') or scp_item.get('link') or scp_item.get('title', '')

    # Extract the numeric/alphanumeric part after "SCP-" or "scp-"
    if scp_id.upper().startswith('SCP-'):
        identifier_part = scp_id[4:]  # Remove "SCP-" prefix
    elif scp_id.lower().startswith('scp-'):
        identifier_part = scp_id[4:]  # Remove "scp-" prefix
    else:
        identifier_part = scp_id

    # Split by character and join with '/'
    if identifier_part:
        return '/'.join(list(identifier_part.lower()))
    else:
        return 'unknown'


def get_scp_html_content(scp_identifier: str) -> Optional[str]:  # noqa: UP045
    """Get HTML content for an SCP from the dataset.

    Args:
        scp_identifier: SCP identifier (e.g., "SCP-002", "002", "scp-002")

    Returns:
        HTML content string, or None if not found
    """
    scp_data = load_scp_data(scp_identifier)
    if not scp_data:
        return None

    # Get HTML content from raw_content field
    html_content = scp_data.get('raw_content')
    if not html_content:
        # Fallback to raw_source if raw_content is not available
        html_content = scp_data.get('raw_source')

    return html_content if html_content and html_content.strip() else None
