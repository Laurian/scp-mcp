"""Data models for SCP MCP Server.

Pydantic models representing SCP Foundation data structures,
API responses, and internal data types.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class HistoryEntry(BaseModel):
    """Single edit history entry."""
    author: str | None = Field(None, description="Author username")
    date: datetime | None = Field(None, description="Edit timestamp")
    comment: str | None = Field(None, description="Edit comment")


class SCPItem(BaseModel):
    """Complete SCP item data model matching LanceDB schema."""

    # Primary identification
    link: str = Field(..., description="Canonical page slug (primary key)")
    scp: str = Field(..., description="Full SCP identifier (e.g., 'SCP-002')")
    scp_number: int = Field(..., description="Numeric ID (e.g., 2, 173)")

    # Core metadata
    title: str = Field(..., description="Item title")
    series: str = Field(..., description="Series identifier (e.g., 'series-1', 'joke')")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    rating: int = Field(default=0, description="Wikidot community votes")

    # Publication info
    created_at: datetime | None = Field(None, description="Original publication date")
    creator: str | None = Field(None, description="Original author username")

    # URLs and references
    url: str = Field(..., description="Canonical wiki URL")
    domain: str = Field(default="scp-wiki.wikidot.com", description="Source domain")
    page_id: str | None = Field(None, description="Wikidot internal page ID")

    # Content (optional - heavy fields)
    raw_source: str | None = Field(None, description="Original wikitext/markup")
    raw_content: str | None = Field(None, description="Cleaned text body")
    markdown: str | None = Field(None, description="AI-friendly markdown")

    # Cross-references
    images: list[str] = Field(default_factory=list, description="Image URLs")
    hubs: list[str] = Field(default_factory=list, description="Hub page references")
    references: list[str] = Field(default_factory=list, description="Cross-referenced items")

    # Edit history
    history: list[HistoryEntry] = Field(default_factory=list, description="Edit history")

    # Processing metadata
    content_file: str | None = Field(None, description="Source file reference")
    content_sha1: str | None = Field(None, description="SHA-1 hash for change detection")
    dataset_commit: str | None = Field(None, description="Upstream scp-data Git commit SHA")

    @field_validator("scp_number", mode="before")
    @classmethod
    def parse_scp_number(cls, v: int | str) -> int:
        """Parse SCP number from various formats."""
        if isinstance(v, str):
            # Handle formats like "SCP-002" -> 2
            if v.upper().startswith("SCP-"):
                return int(v[4:])
            return int(v)
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def ensure_tags_list(cls, v: list[str] | str | None) -> list[str]:
        """Ensure tags is always a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    def has_content(self) -> bool:
        """Check if item has any content fields."""
        return bool(self.raw_content or self.raw_source or self.markdown)

    def get_primary_content(self) -> str | None:
        """Get the primary content field for display."""
        return self.markdown or self.raw_content or self.raw_source

    def get_identifier_variants(self) -> list[str]:
        """Get all possible identifier variants for this item."""
        variants = [
            self.scp,  # SCP-002
            str(self.scp_number),  # 2
            self.link,  # scp-002
        ]
        # Add zero-padded variants
        if self.scp_number < 1000:
            padded_scp = f"SCP-{self.scp_number:03d}"
            if padded_scp not in variants:
                variants.append(padded_scp)

        return variants


class ItemHit(BaseModel):
    """Lightweight item representation for search results and lists."""

    link: str = Field(..., description="Canonical page slug")
    scp: str = Field(..., description="Full SCP identifier")
    scp_number: int = Field(..., description="Numeric ID")
    title: str = Field(..., description="Item title")
    rating: int = Field(default=0, description="Community rating")
    series: str = Field(..., description="Series identifier")

    # Optional metadata for enhanced results
    tags: list[str] | None = Field(None, description="Item tags")
    created_at: datetime | None = Field(None, description="Publication date")
    creator: str | None = Field(None, description="Author")

    @classmethod
    def from_scp_item(cls, item: SCPItem) -> "ItemHit":
        """Create ItemHit from full SCPItem."""
        return cls(
            link=item.link,
            scp=item.scp,
            scp_number=item.scp_number,
            title=item.title,
            rating=item.rating,
            series=item.series,
            tags=item.tags if item.tags else None,
            created_at=item.created_at,
            creator=item.creator,
        )


class SearchResult(BaseModel):
    """Search results with pagination support."""

    items: list[ItemHit] = Field(..., description="Search result items")
    next_cursor: str | None = Field(None, description="Pagination cursor for next page")
    dataset_commit: str | None = Field(None, description="Dataset version for reproducibility")
    total_count: int | None = Field(None, description="Total matching items (if available)")

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        }
    }


class ContentResponse(BaseModel):
    """Response for content-specific requests."""

    markdown: str | None = Field(None, description="AI-optimized markdown content")
    raw_content: str | None = Field(None, description="Cleaned text content")
    raw_source: str | None = Field(None, description="Original wikitext/markup")
    url: str = Field(..., description="Canonical wiki URL")
    content_sha1: str | None = Field(None, description="Content hash")
    dataset_commit: str | None = Field(None, description="Dataset version")
    fallback: bool = Field(default=False, description="True if using fallback content")

    def get_best_content(self) -> str | None:
        """Get the best available content for AI processing."""
        return self.markdown or self.raw_content or self.raw_source


class Attribution(BaseModel):
    """CC BY-SA 3.0 attribution information."""

    title: str = Field(..., description="Content title")
    url: str = Field(..., description="Canonical URL")
    authors: list[str] = Field(default_factory=list, description="Content authors")
    license: str = Field(default="CC BY-SA 3.0", description="License identifier")
    notice: str = Field(
        default="Content from the SCP Wiki is licensed under CC BY-SA 3.0. "
                "Derivatives must be shared under the same license.",
        description="License notice"
    )


class VersionInfo(BaseModel):
    """System version and state information."""

    dataset_commit: str | None = Field(None, description="Current dataset commit SHA")
    current_lancedb_version: int | None = Field(None, description="Current LanceDB table version")
    retention: dict[str, Any] = Field(default_factory=dict, description="Version retention settings")
    server_info: dict[str, str] = Field(default_factory=dict, description="Server version information")


class SyncResult(BaseModel):
    """Result of data synchronization operation."""

    dataset_commit: str = Field(..., description="New dataset commit SHA")
    lancedb_version: int = Field(..., description="New LanceDB table version")
    updated: int = Field(default=0, description="Number of items updated")
    skipped: int = Field(default=0, description="Number of items skipped (unchanged)")
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    errors: list[str] = Field(default_factory=list, description="Processing errors")


class ErrorResponse(BaseModel):
    """Structured error response for AI agents."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    suggestions: list[str] = Field(default_factory=list, description="Suggested alternatives")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional error context")


# Type aliases for common unions
IdentifierType = str | int  # SCP-XXXX, 682, scp-682
ContentType = SCPItem | ItemHit | ContentResponse
