#!/usr/bin/env uv run python
"""
Import SCP items into LanceDB database.

This script reads SCP items from the latest raw dataset, loads additional content
from staging directories (markdown, summaries), and imports them into a LanceDB
database with the proper schema.

Usage:
    python scripts/import.py                     # Import all items
    python scripts/import.py SCP-173            # Import single item
    python scripts/import.py 173-682            # Import range
    python scripts/import.py --random 10        # Import 10 random items
    python scripts/import.py --db-name test     # Custom database name

Database structure:
    ./data/lancedb/{db-name}/    # LanceDB database directory

Features:
    - Imports from latest data/raw/scp-{timestamp}-{commit}/ directory
    - Reads markdown content from data/staging/markdown/ (strips YAML frontmatter)
    - Reads AI summaries from data/staging/summary/ (strips YAML frontmatter)
    - Uses schema from src/scp_mcp/models.py (SCPItem)
    - Supports dry-run, random sampling with seed, and range imports
"""

import argparse
import hashlib
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional  # noqa: UP035

# Add src to path so we can import our modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    import lancedb
    import pyarrow as pa

    from scp_mcp.models import HistoryEntry, SCPItem
    from scp_mcp.utils.data_loader import (
        get_all_item_ids,
        get_debug_folder_path,
        load_scp_data,
    )
except ImportError as e:
    print(f"ERROR: Could not import required modules: {e}")
    print("Please make sure you have installed the required dependencies:")
    print("  pip install lancedb pyarrow pydantic python-dotenv")
    print("Or run: uv sync")
    sys.exit(1)


def normalize_scp_id(scp_id: str) -> str:
    """Normalize SCP identifier to standard format."""
    if scp_id.isdigit():
        return f"SCP-{int(scp_id):03d}"
    elif scp_id.lower().startswith("scp-"):
        return scp_id.upper()
    elif not scp_id.upper().startswith("SCP-"):
        return f"SCP-{scp_id.upper()}"
    else:
        return scp_id.upper()


def get_items_to_import(args) -> List[str]:  # noqa: UP006
    """Get list of item IDs to import based on command line arguments."""
    all_items = get_all_item_ids()
    if not all_items:
        print("ERROR: Could not load item IDs from index.json")
        return []

    if args.random:
        # Import random items
        if args.random > len(all_items):
            print(f"WARNING: Requested {args.random} random items but only {len(all_items)} available")
            return all_items

        # Set random seed for deterministic sampling if provided
        if args.seed is not None:
            random.seed(args.seed)
            print(f"Using random seed: {args.seed}")

        return random.sample(all_items, args.random)

    elif args.item_or_range:
        # Check if it's a range (contains dash and looks like numbers)
        if '-' in args.item_or_range and re.match(r'^\d+-\d+$', args.item_or_range):
            # Parse range
            start_str, end_str = args.item_or_range.split('-', 1)
            start_num = int(start_str)
            end_num = int(end_str)

            if start_num > end_num:
                start_num, end_num = end_num, start_num

            # Filter items in range
            items_in_range = []
            for item_id in all_items:
                # Extract number from SCP identifier
                match = re.search(r'SCP-(\d+)', item_id.upper())
                if match:
                    item_num = int(match.group(1))
                    if start_num <= item_num <= end_num:
                        items_in_range.append(item_id)

            if not items_in_range:
                print(f"WARNING: No items found in range {start_num}-{end_num}")

            return items_in_range

        else:
            # Single item
            normalized_id = normalize_scp_id(args.item_or_range)
            if normalized_id in all_items:
                return [normalized_id]
            else:
                print(f"ERROR: Item {normalized_id} not found in dataset")
                return []

    else:
        # Import all items
        return all_items


def strip_yaml_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from markdown content."""
    lines = content.split('\n')

    # Check if content starts with YAML frontmatter
    if lines and lines[0].strip() == '---':
        # Find the closing ---
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                # Return content after the frontmatter
                return '\n'.join(lines[i+1:]).strip()

    # No frontmatter found, return as-is
    return content.strip()


def read_staging_content(scp_data: dict, staging_base_dir: Path, content_type: str) -> Optional[str]:  # noqa: UP045
    """Read content from staging directory (markdown or summary).

    Args:
        scp_data: SCP item data dictionary
        staging_base_dir: Base staging directory path
        content_type: 'markdown' or 'summary'

    Returns:
        Content string with YAML frontmatter stripped, or None if not found
    """
    try:
        # Generate debug folder path
        debug_folder = get_debug_folder_path(scp_data)

        # Generate filename (use link field if available)
        link = scp_data.get('link', scp_data.get('scp', '').lower())
        if not link.startswith('scp-'):
            # Ensure filename starts with scp-
            if link.upper().startswith('SCP-'):
                link = link.lower()
            else:
                link = f"scp-{link.lower()}"

        # Construct file path
        content_dir = staging_base_dir / content_type / debug_folder
        content_file = content_dir / f"{link}.md"

        if content_file.exists():
            with open(content_file, 'r', encoding='utf-8') as f:  # noqa: UP015
                content = f.read()

            # Strip YAML frontmatter
            return strip_yaml_frontmatter(content)
        else:
            return None

    except Exception as e:
        print(f"WARNING: Failed to read {content_type} for {scp_data.get('scp', 'unknown')}: {e}")
        return None


def compute_content_sha1(content: str) -> str:
    """Compute SHA-1 hash of content."""
    return hashlib.sha1(content.encode('utf-8')).hexdigest()


def create_scp_item(scp_data: dict, staging_base_dir: Path) -> SCPItem:
    """Create SCPItem from raw data and staging content.

    Args:
        scp_data: Raw SCP data from data loader
        staging_base_dir: Base staging directory path

    Returns:
        SCPItem instance ready for database insertion
    """
    # Read additional content from staging
    markdown_content = read_staging_content(scp_data, staging_base_dir, 'markdown')
    summary_content = read_staging_content(scp_data, staging_base_dir, 'summary')

    # Update content fields
    if markdown_content:
        scp_data['markdown'] = markdown_content
    if summary_content:
        scp_data['summary'] = summary_content

    # Compute content hash if we have content
    raw_content = scp_data.get('raw_content')
    if raw_content:
        scp_data['content_sha1'] = compute_content_sha1(raw_content)

    # Convert history entries to HistoryEntry objects
    history = scp_data.get('history', [])
    if history:
        history_entries = []
        for entry in history:
            if isinstance(entry, dict):
                # Parse date if it's a string
                date_val = entry.get('date')
                if isinstance(date_val, str):
                    try:
                        entry['date'] = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        entry['date'] = None

                history_entries.append(HistoryEntry(**entry))
            else:
                history_entries.append(entry)
        scp_data['history'] = history_entries

    # Parse created_at if it's a string
    created_at = scp_data.get('created_at')
    if isinstance(created_at, str):
        try:
            scp_data['created_at'] = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            scp_data['created_at'] = None

    # Ensure required fields have defaults
    scp_data.setdefault('tags', [])
    scp_data.setdefault('rating', 0)
    scp_data.setdefault('images', [])
    scp_data.setdefault('hubs', [])
    scp_data.setdefault('references', [])
    scp_data.setdefault('history', [])
    scp_data.setdefault('domain', 'scp-wiki.wikidot.com')

    return SCPItem(**scp_data)


def get_lancedb_schema() -> pa.Schema:
    """Get PyArrow schema for LanceDB table based on AGENTS.md schema specification."""
    return pa.schema([
        # Primary identification (required fields)
        pa.field("link", pa.string()),  # Primary key - canonical page slug
        pa.field("scp", pa.string()),   # Full SCP identifier (e.g., "SCP-002")
        pa.field("scp_number", pa.int64()),  # Numeric ID (e.g., 2, 173)

        # Core metadata (required fields)
        pa.field("title", pa.string()),  # Item title (often same as scp field)
        pa.field("series", pa.string()), # Series identifier ("series-1", "joke", etc.)
        pa.field("tags", pa.list_(pa.string())),  # Categorization tags
        pa.field("rating", pa.int64()),  # Wikidot community votes

        # Publication info
        pa.field("created_at", pa.timestamp('us', tz=None)),  # Original publication date (ISO format)
        pa.field("creator", pa.string()),  # Original author username (optional, but STRING type per schema)

        # URLs and references (required STRING fields per schema)
        pa.field("url", pa.string()),     # Canonical wiki URL
        pa.field("domain", pa.string()),  # Source domain ("scp-wiki.wikidot.com")
        pa.field("page_id", pa.string()), # Wikidot internal page ID (optional, but STRING type)

        # Content fields (all STRING type per schema)
        pa.field("raw_source", pa.string()),   # Original wikitext/markup (content files only)
        pa.field("raw_content", pa.string()),  # Cleaned text body (content files only)
        pa.field("markdown", pa.string()),     # AI-friendly markdown generated from raw_content
        pa.field("summary", pa.string()),      # AI-generated concise summary (optional)

        # Cross-references (all LIST<STRING> per schema)
        pa.field("images", pa.list_(pa.string())),     # Image URLs
        pa.field("hubs", pa.list_(pa.string())),       # Hub page references
        pa.field("references", pa.list_(pa.string())), # Cross-referenced items

        # Edit history (LIST<OBJECT> - stored as JSON string for LanceDB compatibility)
        pa.field("history", pa.string()),  # Edit history with author/date/comment

        # Processing metadata (all STRING type per schema)
        pa.field("content_file", pa.string()),   # Source file reference (index.json only)
        pa.field("content_sha1", pa.string()),   # SHA-1 hash for change detection (generated)
        pa.field("dataset_commit", pa.string()), # Upstream scp-data Git commit SHA (generated)
    ])


def scp_item_to_dict(item: SCPItem) -> dict:
    """Convert SCPItem to dictionary suitable for LanceDB insertion."""
    data = item.model_dump()

    # Convert datetime objects to timestamps
    if data.get('created_at'):
        data['created_at'] = data['created_at']

    # Convert history to JSON string (LanceDB doesn't handle complex nested objects well)
    if data.get('history'):
        history_data = []
        for entry in data['history']:
            if hasattr(entry, 'model_dump'):
                entry_dict = entry.model_dump()
                # Convert datetime objects to ISO strings for JSON serialization
                if entry_dict.get('date') and hasattr(entry_dict['date'], 'isoformat'):
                    entry_dict['date'] = entry_dict['date'].isoformat()
                history_data.append(entry_dict)
            else:
                # Handle dict entries directly
                entry_dict = dict(entry) if not isinstance(entry, dict) else entry
                if entry_dict.get('date') and hasattr(entry_dict['date'], 'isoformat'):
                    entry_dict['date'] = entry_dict['date'].isoformat()
                history_data.append(entry_dict)
        data['history'] = json.dumps(history_data)
    else:
        data['history'] = json.dumps([])

    # Ensure all fields are present (LanceDB requires consistent schema)
    # Extract field names from the schema to ensure consistency
    schema = get_lancedb_schema()
    schema_fields = [field.name for field in schema]

    for field in schema_fields:
        if field not in data:
            if field in ['tags', 'images', 'hubs', 'references']:
                data[field] = []
            elif field == 'history':
                data[field] = json.dumps([])
            elif field in ['rating', 'scp_number']:
                data[field] = 0
            else:
                data[field] = None

    return data


async def import_items(
    item_ids: List[str],  # noqa: UP006
    db_name: str = "items",
    staging_base_dir: Path = None,
    dry_run: bool = False
) -> None:
    """Import SCP items into LanceDB database.

    Args:
        item_ids: List of SCP item IDs to import
        db_name: Database name (default: "items")
        staging_base_dir: Base staging directory (default: ./data/staging/)
        dry_run: If True, don't create database, just show what would be imported
    """
    if staging_base_dir is None:
        staging_base_dir = Path(__file__).parent.parent / "data" / "staging"

    # Database path
    db_path = Path(__file__).parent.parent / "data" / "lancedb" / db_name

    if dry_run:
        print(f"DRY RUN: Would import {len(item_ids)} items into LanceDB database")
        print(f"Database path: {db_path}")
        print(f"Staging directory: {staging_base_dir}")
        print("No database will be created. Showing items to be imported...")
    else:
        print(f"Importing {len(item_ids)} items into LanceDB database...")
        print(f"Database path: {db_path}")
        print(f"Staging directory: {staging_base_dir}")

        # Ensure database directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to LanceDB
        db = lancedb.connect(str(db_path))

    imported_count = 0
    skipped_count = 0
    error_count = 0
    items_to_insert = []

    for item_id in item_ids:
        try:
            # Load the SCP data
            scp_data = load_scp_data(item_id)
            if not scp_data:
                print(f"WARNING: Could not load data for {item_id}")
                skipped_count += 1
                continue

            if dry_run:
                # In dry run, just show what would be processed
                markdown_file = staging_base_dir / "markdown" / get_debug_folder_path(scp_data) / f"{scp_data.get('link', item_id.lower())}.md"
                summary_file = staging_base_dir / "summary" / get_debug_folder_path(scp_data) / f"{scp_data.get('link', item_id.lower())}.md"

                print(f"Would import: {item_id}")
                print("  Raw data: Available")
                print(f"  Markdown: {'Available' if markdown_file.exists() else 'Not found'} ({markdown_file})")
                print(f"  Summary: {'Available' if summary_file.exists() else 'Not found'} ({summary_file})")
                imported_count += 1
            else:
                # Create SCPItem with staging content
                scp_item = create_scp_item(scp_data, staging_base_dir)

                # Convert to dict for LanceDB
                item_dict = scp_item_to_dict(scp_item)
                items_to_insert.append(item_dict)

                imported_count += 1
                if len(item_ids) > 10 and imported_count % 100 == 0:
                    print(f"Processed {imported_count} items...")

        except Exception as e:
            print(f"ERROR: Failed to import {item_id}: {e}")
            error_count += 1

    if not dry_run and items_to_insert:
        try:
            # Create or replace table with the items
            print(f"Creating LanceDB table with {len(items_to_insert)} items...")

            # Create table with explicit schema (will overwrite if exists)
            schema = get_lancedb_schema()
            table = db.create_table("items", items_to_insert, schema=schema, mode="overwrite")

            print(f"Successfully created table with {len(items_to_insert)} items")
            print(f"Table schema: {table.schema}")

        except Exception as e:
            print(f"ERROR: Failed to create LanceDB table: {e}")
            error_count += len(items_to_insert)
            imported_count = 0

    # Print summary
    if dry_run:
        print("\nDry run completed:")
        print(f"  Would import: {imported_count}")
        print(f"  Would skip: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Target database: {db_path}")
    else:
        print("\nImport completed:")
        print(f"  Imported: {imported_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Database: {db_path}")


def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Import SCP items into LanceDB database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Import all items into default database
  %(prog)s SCP-173           # Import single item
  %(prog)s 173               # Import single item (short form)
  %(prog)s 100-200           # Import range of items
  %(prog)s --random 10       # Import 10 random items
  %(prog)s --random 5 --seed 42    # Import 5 random items (deterministic)
  %(prog)s --db-name test    # Import into custom database name
  %(prog)s --dry-run --random 5    # Show what would be imported (dry run)

Database Structure:
  ./data/lancedb/{db-name}/  # LanceDB database directory

Content Sources:
  - Raw data: Latest data/raw/scp-{timestamp}-{commit}/ directory
  - Markdown: data/staging/markdown/ (YAML frontmatter stripped)
  - Summaries: data/staging/summary/ (YAML frontmatter stripped)
        """
    )

    parser.add_argument(
        'item_or_range',
        nargs='?',
        help='Single SCP item (e.g., SCP-173, 173) or range (e.g., 100-200)'
    )

    parser.add_argument(
        '--random', '-r',
        type=int,
        metavar='N',
        help='Import N random items'
    )

    parser.add_argument(
        '--seed', '-s',
        type=int,
        metavar='N',
        help='Random seed for deterministic sampling (use with --random)'
    )

    parser.add_argument(
        '--db-name', '--db',
        type=str,
        default='items',
        metavar='NAME',
        help='Database name (default: items)'
    )

    parser.add_argument(
        '--dry-run', '--dry',
        action='store_true',
        help='Show what would be imported without creating database'
    )

    return parser


async def main_async():
    """Async main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    print("SCP Items LanceDB Import Script")
    print("=" * 40)

    try:
        # Get items to import based on arguments
        item_ids = get_items_to_import(args)
        if not item_ids:
            print("No items to import")
            sys.exit(1)

        # Import the items
        await import_items(item_ids, args.db_name, dry_run=getattr(args, 'dry_run', False))

    except KeyboardInterrupt:
        print("\nImport interrupted by user")
    except Exception as e:
        print(f"ERROR: Import failed: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    # Check if we're in an async context already
    try:
        import asyncio
        asyncio.get_running_loop()
        # If we get here, we're already in an async context
        # This shouldn't happen in a script, but just in case
        print("ERROR: Cannot run in existing async context")
        sys.exit(1)
    except RuntimeError:
        # No running loop, we can create one
        import asyncio
        asyncio.run(main_async())


if __name__ == "__main__":
    main()
