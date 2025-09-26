#!/usr/bin/env uv run python
"""
Dump LanceDB table to stdout as JSONL.

This script reads a LanceDB table and outputs each row as a JSON line to stdout.
Useful for inspecting database contents, exporting data, or piping to other tools.

Usage:
    python scripts/dump_table.py items                    # Dump all rows from 'items' table in default db
    python scripts/dump_table.py items --db-name test     # Dump from custom database
    python scripts/dump_table.py items --limit 10         # Dump only first 10 rows
    python scripts/dump_table.py items --limit 5 --offset 100  # Skip 100 rows, dump next 5

Output format:
    Each row is output as a single JSON line (JSONL format)
    Perfect for piping to jq, grep, or other JSON processing tools

Examples:
    # Inspect first 5 items
    python scripts/dump_table.py items --limit 5

    # Extract just SCP identifiers
    python scripts/dump_table.py items --limit 10 | jq -r '.scp'

    # Find items with specific tags
    python scripts/dump_table.py items | jq 'select(.tags | contains(["euclid"]))'

    # Count total items
    python scripts/dump_table.py items | wc -l
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional  # noqa: UP035

# Add src to path so we can import our modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    import lancedb
    import pyarrow as pa  # noqa: F401
except ImportError as e:
    print(f"ERROR: Could not import required modules: {e}", file=sys.stderr)
    print("Please make sure you have installed the required dependencies:", file=sys.stderr)
    print("  pip install lancedb pyarrow", file=sys.stderr)
    print("Or run: uv sync", file=sys.stderr)
    sys.exit(1)


def dump_table(
    table_name: str,
    db_name: str = "items",
    limit: Optional[int] = None,  # noqa: UP045
    offset: int = 0
) -> None:
    """Dump LanceDB table to stdout as JSONL.

    Args:
        table_name: Name of the table to dump
        db_name: Database name (default: "items")
        limit: Maximum number of rows to dump (None for all)
        offset: Number of rows to skip from the beginning
    """
    # Database path
    db_path = Path(__file__).parent.parent / "data" / "lancedb" / db_name

    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        print("Available databases in data/lancedb/:", file=sys.stderr)
        lancedb_dir = db_path.parent
        if lancedb_dir.exists():
            for item in lancedb_dir.iterdir():
                if item.is_dir() and item.name != ".gitkeep":
                    print(f"  - {item.name}", file=sys.stderr)
        sys.exit(1)

    try:
        # Connect to LanceDB
        db = lancedb.connect(str(db_path))

        # Check if table exists
        table_names = db.table_names()
        if table_name not in table_names:
            print(f"ERROR: Table '{table_name}' not found in database '{db_name}'", file=sys.stderr)
            print("Available tables:", file=sys.stderr)
            for name in table_names:
                print(f"  - {name}", file=sys.stderr)
            sys.exit(1)

        # Open table
        table = db.open_table(table_name)

        # Convert to PyArrow table
        arrow_table = table.to_arrow()

        # Apply offset and limit manually on the arrow table
        total_rows = len(arrow_table)

        if offset > 0:
            arrow_table = arrow_table.slice(offset)

        if limit is not None:
            arrow_table = arrow_table.slice(0, limit)

        # Print metadata to stderr
        print(f"# Database: {db_name}", file=sys.stderr)
        print(f"# Table: {table_name}", file=sys.stderr)
        versions = table.list_versions()
        print(f"# Number of versions after creation: {len(versions)}", file=sys.stderr)
        for v in versions:
            print(f"# Version {v['version']}, created at {v['timestamp']}", file=sys.stderr)
        print(f"# Current version: {table.version}", file=sys.stderr)
        print(f"# Total rows in table: {total_rows}", file=sys.stderr)
        print(f"# Offset: {offset}", file=sys.stderr)
        print(f"# Limit: {limit if limit is not None else 'none'}", file=sys.stderr)
        print(f"# Dumping {len(arrow_table)} rows", file=sys.stderr)
        print(f"# Schema: {arrow_table.schema}", file=sys.stderr)
        print("# ---", file=sys.stderr)

        # Convert to python objects and dump each row as JSON line
        for i in range(len(arrow_table)):
            # Get row as dict
            row_dict = {}
            for j, column_name in enumerate(arrow_table.column_names):
                value = arrow_table.column(j)[i].as_py()

                # Handle special conversions
                if value is None:
                    row_dict[column_name] = None
                # Parse JSON strings (like history field)
                elif column_name == 'history' and isinstance(value, str):
                    try:
                        row_dict[column_name] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        # Keep as string if not valid JSON
                        row_dict[column_name] = value
                # Convert timestamps to ISO strings
                elif hasattr(value, 'isoformat'):
                    row_dict[column_name] = value.isoformat()
                else:
                    row_dict[column_name] = value

            # Output as JSON line
            print(json.dumps(row_dict, ensure_ascii=False))

    except Exception as e:
        print(f"ERROR: Failed to dump table: {e}", file=sys.stderr)
        sys.exit(1)


def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Dump LanceDB table to stdout as JSONL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s items                    # Dump all rows from 'items' table
  %(prog)s items --limit 10         # Dump first 10 rows
  %(prog)s items --offset 100 --limit 5  # Skip 100, dump next 5
  %(prog)s items --db-name test     # Dump from 'test' database

Output Processing:
  # Extract SCP identifiers
  %(prog)s items --limit 10 | jq -r '.scp'

  # Find items with specific tags
  %(prog)s items | jq 'select(.tags | contains(["euclid"]))'

  # Count total items
  %(prog)s items | wc -l

  # Pretty print first item
  %(prog)s items --limit 1 | jq '.'

Database Location:
  ./data/lancedb/{db-name}/         # LanceDB database directory
        """
    )

    parser.add_argument(
        'table_name',
        help='Name of the table to dump (e.g., "items")'
    )

    parser.add_argument(
        '--db-name', '--db',
        type=str,
        default='items',
        metavar='NAME',
        help='Database name (default: items)'
    )

    parser.add_argument(
        '--limit', '-l',
        type=int,
        metavar='N',
        help='Maximum number of rows to dump (default: all rows)'
    )

    parser.add_argument(
        '--offset', '-o',
        type=int,
        default=0,
        metavar='N',
        help='Number of rows to skip from the beginning (default: 0)'
    )

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Dump the table
        dump_table(
            table_name=args.table_name,
            db_name=args.db_name,
            limit=args.limit,
            offset=args.offset
        )

    except KeyboardInterrupt:
        print("\nDump interrupted by user", file=sys.stderr)
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"ERROR: Dump failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
