#!/usr/bin/env uv run python
"""
Export AI-generated summaries of SCP items to individual Markdown files.

This script reads SCP items from the dataset, converts them to markdown,
uses OpenAI to generate concise summaries, and exports them as individual
Markdown files organized in a hierarchical folder structure.

Usage:
    python scripts/export_summary.py                    # Export all items
    python scripts/export_summary.py SCP-173           # Export single item
    python scripts/export_summary.py 173-682           # Export range
    python scripts/export_summary.py --random 10       # Export 10 random items

Output structure:
    ./data/staging/summary/{debug-folder}/scp-number.md

Example:
    SCP-1234 -> ./data/staging/summary/1/2/3/4/scp-1234.md
    SCP-173 -> ./data/staging/summary/1/7/3/scp-173.md

Requirements:
    - OPENAI_API_KEY must be set in .env.local
    - Optional: OPENAI_API_BASE for custom endpoints (e.g., OpenRouter)
    - Optional: OPENAI_MODEL to specify model (default: gpt-3.5-turbo)
    - OpenAI dependency: pip install openai>=1.0.0 or uv add openai
"""

import argparse
import asyncio
import os
import random
import re
import sys
from pathlib import Path
from typing import List, Optional  # noqa: UP035

# Add src to path so we can import our modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    import openai

    from scp_mcp.config import settings
    from scp_mcp.utils.content_converter import html_to_markdown
    from scp_mcp.utils.data_loader import (
        get_all_item_ids,
        get_debug_folder_path,
        load_scp_data,
    )
except ImportError as e:
    print(f"ERROR: Could not import required modules: {e}")
    print("Please make sure you have installed the required dependencies:")
    print("  pip install openai>=1.0.0 pydantic python-dotenv")
    print("Or run: uv sync --extra ai")
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


def setup_openai_client() -> openai.OpenAI:
    """Set up OpenAI client with API key and optional custom endpoint from environment."""
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    api_base = settings.openai_api_base or os.getenv("OPENAI_API_BASE")

    if not api_key:
        print("ERROR: OpenAI API key not found!")
        print("Please set OPENAI_API_KEY in your .env.local file or environment variables.")
        print("Example: OPENAI_API_KEY=sk-your-key-here")
        sys.exit(1)

    # Set up client with optional custom base URL
    client_kwargs = {"api_key": api_key}
    if api_base:
        client_kwargs["base_url"] = api_base
        print(f"Using custom OpenAI endpoint: {api_base}")

    return openai.OpenAI(**client_kwargs)


async def generate_summary(client: openai.OpenAI, scp_data: dict, markdown_content: str) -> str | None:
    """Generate AI summary of SCP item using OpenAI.

    Returns:
        str: The generated summary if successful
        None: If summary generation failed
    """
    scp_id = scp_data.get('scp', 'Unknown')
    title = scp_data.get('title', scp_id)

    # Get model from settings or use default
    model = settings.openai_model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    # Prepare prompt for OpenAI
    prompt = f"""Please provide a concise, informative summary of this SCP Foundation item. Focus on:
1. What the object/entity is
2. Its key anomalous properties
3. Its containment class and basic containment procedures
4. Any notable risks or special characteristics

Keep the summary between 100-200 words and write it in a clear, accessible style.

SCP Item: {scp_id} - {title}

Content:
{markdown_content[:102000]}
"""
# Limit content ^^^ to avoid token limits (approx. 256k tokens context window, reserving ~8k for response)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert at summarizing SCP Foundation documents. Provide clear, concise summaries that capture the essential nature and properties of anomalous objects."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8000,
            temperature=0.3,  # Lower temperature for more consistent summaries
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"WARNING: Failed to generate summary for {scp_id}: {e}")
        return None  # Return None instead of error message


def convert_to_markdown(scp_data: dict) -> Optional[str]:  # noqa: UP045
    """Convert SCP data to markdown format (without metadata)."""
    # Try to get markdown content first, then fall back to raw content
    content = None

    if scp_data.get('markdown'):
        content = scp_data['markdown']
    elif scp_data.get('raw_content'):
        # Try to convert HTML to markdown
        html_content = scp_data['raw_content']
        converted_md = html_to_markdown(html_content)
        if converted_md and converted_md.strip():
            content = converted_md
        else:
            # Fall back to raw content as-is
            content = html_content
    elif scp_data.get('raw_source'):
        # Fall back to raw source
        content = scp_data['raw_source']

    return content


async def export_items(item_ids: List[str], output_base_dir: Path = None, max_concurrent: int = 5, force: bool = False, dry_run: bool = False) -> None:  # noqa: UP006
    """Export SCP items with AI-generated summaries to individual Markdown files.

    Args:
        item_ids: List of SCP item IDs to export
        output_base_dir: Base directory for output (default: ./data/staging/summary/)
        max_concurrent: Maximum concurrent OpenAI API calls
        force: If True, overwrite existing files; if False, skip existing files
        dry_run: If True, don't write files, just show destinations
    """
    if output_base_dir is None:
        output_base_dir = Path(__file__).parent.parent / "data" / "staging" / "summary"

    if dry_run:
        print(f"DRY RUN: Would export {len(item_ids)} items with AI summaries to {output_base_dir}")
        print("No files will be written. Showing destination paths only...")
        print("No OpenAI API calls will be made during dry run.")
    else:
        # Ensure output directory exists
        output_base_dir.mkdir(parents=True, exist_ok=True)

        print(f"Exporting {len(item_ids)} items with AI summaries...")
        print(f"Max concurrent API calls: {max_concurrent}")

        # Set up OpenAI client
        client = setup_openai_client()

        # Show which model will be used
        model = settings.openai_model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        print(f"Using model: {model}")

    # Initialize client variable for dry run (won't be used)
    if dry_run:
        client = None

    exported_count = 0
    skipped_count = 0
    error_count = 0

    # Process items in batches to respect rate limits
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_item(item_id: str):
        nonlocal exported_count, skipped_count, error_count

        async with semaphore:
            try:
                # Load the SCP data
                scp_data = load_scp_data(item_id)
                if not scp_data:
                    print(f"WARNING: Could not load data for {item_id}")
                    skipped_count += 1
                    return

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
                    exported_count += 1
                    return

                # Check if file already exists and skip if it does (unless force is enabled)
                if output_file.exists() and not force:
                    print(f"Skipping {item_id} - file already exists: {output_file}")
                    skipped_count += 1
                    return

                # Convert content to markdown
                markdown_content = convert_to_markdown(scp_data)
                if not markdown_content:
                    print(f"WARNING: No content available for {item_id}")
                    skipped_count += 1
                    return

                # Generate AI summary
                print(f"Generating summary for {item_id}...")
                summary = await generate_summary(client, scp_data, markdown_content)

                # Only create file if summary generation was successful
                if summary is not None:
                    # Create final markdown content
                    final_content = generate_summary_markdown(scp_data, summary)

                    # Write Markdown file
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(final_content)

                    exported_count += 1
                    if len(item_ids) > 10 and exported_count % 10 == 0:
                        print(f"Exported {exported_count} items...")
                else:
                    # Summary generation failed, count as skipped
                    skipped_count += 1

                # Add small delay to respect rate limits (skip in dry run)
                if not dry_run:
                    await asyncio.sleep(0.1)

            except Exception as e:
                print(f"ERROR: Failed to export {item_id}: {e}")
                error_count += 1

    # Process all items concurrently (with semaphore limiting)
    tasks = [process_item(item_id) for item_id in item_ids]
    await asyncio.gather(*tasks, return_exceptions=True)

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


def generate_summary_markdown(scp_data: dict, summary: str) -> str:
    """Generate markdown content with AI summary and YAML frontmatter metadata."""
    lines = []

    scp_id = scp_data.get('scp', 'Unknown')
    title = scp_data.get('title', scp_id)

    # YAML frontmatter metadata
    lines.append("---")

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

    # License information
    lines.append("license: \"CC BY-SA 3.0\"")
    lines.append("license_url: \"https://creativecommons.org/licenses/by-sa/3.0/\"")
    lines.append("license_note: \"This summary was generated using AI and is based on content from the SCP Wiki, which is licensed under CC BY-SA 3.0. Derivatives must be shared under the same license.\"")
    lines.append("ai_generated: true")
    lines.append("content_type: \"ai_summary\"")

    lines.append("---")
    lines.append("")

    # AI-generated summary content
    lines.append(summary)

    return "\n".join(lines)


def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Export AI-generated summaries of SCP items to individual Markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Export all items with summaries (skip existing)
  %(prog)s SCP-173           # Export single item summary (skip if exists)
  %(prog)s 173               # Export single item (short form)
  %(prog)s 100-200           # Export range of item summaries
  %(prog)s --random 10       # Export 10 random item summaries
  %(prog)s --force --random 5 # Force regenerate 5 random summaries
  %(prog)s --dry-run --random 3  # Show what would be exported (dry run)

Requirements:
  - OPENAI_API_KEY must be set in .env.local
  - Optional: OPENAI_API_BASE for custom endpoints (e.g., OpenRouter)
  - Optional: OPENAI_MODEL to specify model (default: gpt-3.5-turbo)
  - OpenAI Python library: pip install openai>=1.0.0
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
        help='Output directory (default: ./data/staging/summary/)'
    )

    parser.add_argument(
        '--max-concurrent', '-c',
        type=int,
        default=5,
        metavar='N',
        help='Maximum concurrent OpenAI API calls (default: 5)'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force regeneration of existing files (overwrite existing summaries)'
    )

    parser.add_argument(
        '--dry-run', '--dry',
        action='store_true',
        help='Show what would be exported without writing any files or calling OpenAI API'
    )

    return parser


async def main_async():
    """Async main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    print("SCP Items AI Summary Export Script")
    print("=" * 40)

    try:
        # Get items to export based on arguments
        item_ids = get_items_to_export(args)
        if not item_ids:
            print("No items to export")
            sys.exit(1)

        # Export the items with AI summaries
        await export_items(item_ids, args.output, args.max_concurrent, args.force, getattr(args, 'dry_run', False))

    except KeyboardInterrupt:
        print("\nExport interrupted by user")
    except Exception as e:
        print(f"ERROR: Export failed: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    # Check if we're in an async context already
    try:
        asyncio.get_running_loop()
        # If we get here, we're already in an async context
        # This shouldn't happen in a script, but just in case
        print("ERROR: Cannot run in existing async context")
        sys.exit(1)
    except RuntimeError:
        # No running loop, we can create one
        asyncio.run(main_async())


if __name__ == "__main__":
    main()
