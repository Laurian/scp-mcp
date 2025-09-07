"""Data models for SCP items and search results."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SCPItem(BaseModel):
    """Model representing an SCP item."""

    item_id: str = Field(..., description="The SCP item ID (e.g., 'SCP-001')")
    title: str = Field(..., description="The title of the SCP item")
    content: str = Field(..., description="The full content of the SCP item")
    object_class: Optional[str] = Field(None, description="The object class (Safe, Euclid, Keter, etc.)")
    containment_procedures: Optional[str] = Field(None, description="Containment procedures")
    description: Optional[str] = Field(None, description="Description of the SCP")
    additional_notes: Optional[str] = Field(None, description="Additional notes")
    tags: List[str] = Field(default_factory=list, description="Tags associated with the SCP")
    series: Optional[str] = Field(None, description="The series this SCP belongs to")
    category: Optional[str] = Field(None, description="Category (e.g., '001', 'joke', 'explained')")
    url: Optional[str] = Field(None, description="URL to the SCP wiki page")
    created_date: Optional[datetime] = Field(None, description="Date when the SCP was created")
    last_updated: Optional[datetime] = Field(None, description="Date when the SCP was last updated")
    rating: Optional[int] = Field(None, description="Community rating")
    votes: Optional[int] = Field(None, description="Number of votes")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SearchResult(BaseModel):
    """Model representing a search result."""

    item: SCPItem = Field(..., description="The SCP item")
    score: float = Field(..., description="Similarity score (higher is better)")
    rank: int = Field(..., description="Rank in search results")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SearchQuery(BaseModel):
    """Model for search queries."""

    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")


class VectorSearchResult(BaseModel):
    """Model for vector search results."""

    item_id: str = Field(..., description="The SCP item ID")
    title: str = Field(..., description="The title of the SCP item")
    content_snippet: str = Field(..., description="Snippet of the content")
    score: float = Field(..., description="Vector similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
