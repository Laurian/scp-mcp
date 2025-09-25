#!/usr/bin/env uv run python
"""
Export SCP items to individual Markdown files.

This script reads all SCP items from the dataset and exports them as individual
Markdown files organized in a hierarchical folder structure based on their identifiers.

Usage:
    python scripts/export_markdown.py                    # Export all items
    python scripts/export_markdown.py SCP-173           # Export single item
    python scripts/export_markdown.py 173-682           # Export range
    python scripts/export_markdown.py --random 10       # Export 10 random items

Output structure:
    ./data/staging/markdown/{debug-folder}/scp-number.md

Example:
    SCP-1234 -> ./data/staging/markdown/1/2/3/4/scp-1234.md
    SCP-173 -> ./data/staging/markdown/1/7/3/scp-173.md
"""

import argparse
import random
import re
import sys
from pathlib import Path
from typing import List  # noqa: UP035

# Add src to path so we can import our modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from scp_mcp.utils.content_converter import html_to_markdown
    from scp_mcp.utils.data_loader import (
        get_all_item_ids,
        get_debug_folder_path,
        load_scp_data,
    )
except ImportError as e:
    print(f"ERROR: Could not import required modules: {e}")
    print("Please make sure you have installed the required dependencies:")
    print("  pip install pydantic python-dotenv")
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


def get_items_to_export(args) -> List[str]:  # noqa: UP006
    """Get list of item IDs to export based on command line arguments."""
    all_items = get_all_item_ids()
    if not all_items:
        print("ERROR: Could not load item IDs from index.json")
        return []

    if args.random:
        # Export random items
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
        # Export all items
        return all_items


def export_items(item_ids: List[str], output_base_dir: Path = None, dry_run: bool = False) -> None:  # noqa: UP006
    """Export SCP items to individual Markdown files.

    Args:
        item_ids: List of SCP item IDs to export
        output_base_dir: Base directory for output (default: ./data/staging/markdown/)
        dry_run: If True, don't write files, just show destinations
    """
    if output_base_dir is None:
        output_base_dir = Path(__file__).parent.parent / "data" / "staging" / "markdown"

    if dry_run:
        print(f"DRY RUN: Would export {len(item_ids)} items to {output_base_dir}")
        print("No files will be written. Showing destination paths only...")
    else:
        # Ensure output directory exists
        output_base_dir.mkdir(parents=True, exist_ok=True)
        print(f"Exporting {len(item_ids)} items...")

    exported_count = 0
    skipped_count = 0
    error_count = 0

    for item_id in item_ids:
        try:
            # Load the SCP data
            scp_data = load_scp_data(item_id)
            if not scp_data:
                print(f"WARNING: Could not load data for {item_id}")
                skipped_count += 1
                continue

            # Generate debug folder path
            debug_folder = get_debug_folder_path(scp_data)

            # Create output directory structure
            output_dir = output_base_dir / debug_folder
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename (use link field if available, otherwise use item_id)
            link = scp_data.get('link', item_id.lower())
            if not link.startswith('scp-'):
                # Ensure filename starts with scp-
                if link.upper().startswith('SCP-'):
                    link = link.lower()
                else:
                    link = f"scp-{link.lower()}"

            output_file = output_dir / f"{link}.md"

            if dry_run:
                print(f"Would write: {output_file}")
            else:
                # Convert content to markdown
                markdown_content = generate_markdown_content(scp_data)

                # Write Markdown file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

            exported_count += 1
            if len(item_ids) > 10 and exported_count % 100 == 0:
                action = "Would export" if dry_run else "Exported"
                print(f"{action} {exported_count} items...")

        except Exception as e:
            print(f"ERROR: Failed to export {item_id}: {e}")
            error_count += 1

    if dry_run:
        print("\nDry run completed:")
        print(f"  Would export: {exported_count}")
        print(f"  Would skip: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Target directory: {output_base_dir}")
    else:
        print("\nExport completed:")
        print(f"  Exported: {exported_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Output directory: {output_base_dir}")


def generate_markdown_content(scp_data: dict) -> str:
    """Generate markdown content from SCP data."""
    lines = []

    # YAML frontmatter metadata
    lines.append("---")

    scp_id = scp_data.get('scp', 'Unknown')
    title = scp_data.get('title', scp_id)

    lines.append(f"scp_id: \"{scp_id}\"")
    lines.append(f"title: \"{title}\"")

    if scp_data.get('link'):
        lines.append(f"link: \"{scp_data['link']}\"")

    if scp_data.get('scp_number') is not None:
        lines.append(f"scp_number: {scp_data['scp_number']}")

    if scp_data.get('series'):
        lines.append(f"series: \"{scp_data['series']}\"")

    if scp_data.get('rating') is not None:
        lines.append(f"rating: {scp_data['rating']}")

    if scp_data.get('creator'):
        lines.append(f"author: \"{scp_data['creator']}\"")

    if scp_data.get('created_at'):
        lines.append(f"created_at: \"{scp_data['created_at']}\"")

    if scp_data.get('url'):
        lines.append(f"source_url: \"{scp_data['url']}\"")

    if scp_data.get('domain'):
        lines.append(f"domain: \"{scp_data['domain']}\"")

    if scp_data.get('tags'):
        lines.append("tags:")
        for tag in scp_data['tags']:
            lines.append(f"  - \"{tag}\"")

    if scp_data.get('references'):
        lines.append("references:")
        for ref in scp_data['references']:
            lines.append(f"  - \"{ref}\"")

    if scp_data.get('images'):
        lines.append("images:")
        for img in scp_data['images']:
            lines.append(f"  - \"{img}\"")

    # Dataset versioning information
    if scp_data.get('dataset_commit'):
        lines.append(f"dataset_commit: \"{scp_data['dataset_commit']}\"")

    if scp_data.get('content_sha1'):
        lines.append(f"content_sha1: \"{scp_data['content_sha1']}\"")

    # # AI-generated summary if available
    # if scp_data.get('summary'):
    #    lines.append(f"ai_summary: \"{scp_data['summary']}\"")

    # License information
    lines.append("license: \"CC BY-SA 3.0\"")
    lines.append("license_url: \"https://creativecommons.org/licenses/by-sa/3.0/\"")

    lines.append("---")
    lines.append("")

    # Title
    lines.append(f"# {title}")
    lines.append("")

    # Content
    lines.append("## Content")
    lines.append("")

    # Try to get markdown content first, then fall back to raw content
    content = None
    content_source = None

    if scp_data.get('markdown'):
        content = scp_data['markdown']
        content_source = "markdown"
    elif scp_data.get('raw_content'):
        # Try to convert HTML to markdown
        html_content = scp_data['raw_content']
        converted_md = html_to_markdown(html_content)
        if converted_md and converted_md.strip():
            content = converted_md
            content_source = "converted"
        else:
            # Fall back to raw content wrapped in code block
            content = f"```html\n{html_content}\n```"
            content_source = "raw_html"
    elif scp_data.get('raw_source'):
        # Fall back to raw source
        content = f"```\n{scp_data['raw_source']}\n```"
        content_source = "raw_source"

    if content:
        if content_source == "converted":
            lines.append("*Note: Content converted from HTML to Markdown*")
            lines.append("")
        elif content_source == "raw_html":
            lines.append("*Note: Content displayed as raw HTML*")
            lines.append("")
        elif content_source == "raw_source":
            lines.append("*Note: Content displayed as raw source*")
            lines.append("")

        lines.append(content)
    else:
        lines.append("*No content available*")

    lines.append("")

    return "\n".join(lines)


def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Export SCP items to individual Markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Export all items
  %(prog)s SCP-173           # Export single item
  %(prog)s 173               # Export single item (short form)
  %(prog)s 100-200           # Export range of items
  %(prog)s --random 10       # Export 10 random items
  %(prog)s --random 5 --seed 42    # Export 5 random items (deterministic)
  %(prog)s --dry-run --random 5 --seed 123  # Show what would be exported (dry run)
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
        help='Export N random items'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        metavar='DIR',
        help='Output directory (default: ./data/staging/markdown/)'
    )

    parser.add_argument(
        '--dry-run', '--dry',
        action='store_true',
        help='Show what would be exported without writing any files'
    )

    parser.add_argument(
        '--seed', '-s',
        type=int,
        metavar='N',
        help='Random seed for deterministic sampling (use with --random)'
    )

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    print("SCP Items Markdown Export Script")
    print("=" * 40)

    try:
        # Get items to export based on arguments
        item_ids = get_items_to_export(args)
        if not item_ids:
            print("No items to export")
            sys.exit(1)

        # Export the items
        export_items(item_ids, args.output, getattr(args, 'dry_run', False))

    except KeyboardInterrupt:
        print("\nExport interrupted by user")
    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
