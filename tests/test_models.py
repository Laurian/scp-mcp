"""Tests for SCP MCP Server data models."""


from scp_mcp.models import (
    ContentResponse,
    ItemHit,
    SCPItem,
    SearchResult,
    SyncResult,
    VersionInfo,
)


class TestSCPItem:
    """Test SCPItem model."""

    def test_scp_item_creation(self, sample_scp_item):
        """Test creating a valid SCP item."""
        item = SCPItem(**sample_scp_item)

        assert item.link == "scp-173"
        assert item.scp == "SCP-173"
        assert item.scp_number == 173
        assert item.title == "The Sculpture"
        assert item.series == "series-1"
        assert "euclid" in item.tags

    def test_scp_number_parsing(self):
        """Test SCP number parsing from various formats."""
        # Test with SCP-XXX format
        item1 = SCPItem(
            link="scp-002",
            scp="SCP-002",
            scp_number="SCP-002",  # Should parse to 2
            title="Test",
            series="series-1",
            url="https://example.com"
        )
        assert item1.scp_number == 2

        # Test with string number
        item2 = SCPItem(
            link="scp-173",
            scp="SCP-173",
            scp_number="173",  # Should parse to 173
            title="Test",
            series="series-1",
            url="https://example.com"
        )
        assert item2.scp_number == 173

    def test_has_content(self, sample_scp_item):
        """Test content detection."""
        item = SCPItem(**sample_scp_item)
        assert item.has_content()

        # Item without content
        item_no_content = SCPItem(
            link="scp-test",
            scp="SCP-TEST",
            scp_number=999,
            title="Test",
            series="test",
            url="https://example.com"
        )
        assert not item_no_content.has_content()

    def test_get_primary_content(self, sample_scp_item):
        """Test primary content selection."""
        item = SCPItem(**sample_scp_item)
        content = item.get_primary_content()
        assert content.startswith("# SCP-173")  # Should prefer markdown

        # Test fallback to raw_content
        item_no_markdown = SCPItem(
            **{**sample_scp_item, "markdown": None}
        )
        content = item_no_markdown.get_primary_content()
        assert content.startswith("Item #: SCP-173")  # Should use raw_content

    def test_identifier_variants(self, sample_scp_item):
        """Test identifier variant generation."""
        item = SCPItem(**sample_scp_item)
        variants = item.get_identifier_variants()

        assert "SCP-173" in variants
        assert "173" in variants
        assert "scp-173" in variants
        # Should include zero-padded for numbers < 1000
        assert "SCP-173" in variants  # Already padded


class TestItemHit:
    """Test ItemHit model."""

    def test_from_scp_item(self, sample_scp_item):
        """Test creating ItemHit from SCPItem."""
        item = SCPItem(**sample_scp_item)
        hit = ItemHit.from_scp_item(item)

        assert hit.link == item.link
        assert hit.scp == item.scp
        assert hit.scp_number == item.scp_number
        assert hit.title == item.title
        assert hit.rating == item.rating
        assert hit.series == item.series
        assert hit.tags == item.tags


class TestSearchResult:
    """Test SearchResult model."""

    def test_search_result_creation(self, sample_search_results):
        """Test creating search results."""
        hits = [ItemHit(**item) for item in sample_search_results]
        result = SearchResult(
            items=hits,
            next_cursor="cursor123",
            dataset_commit="commit456",
            total_count=100
        )

        assert len(result.items) == 2
        assert result.next_cursor == "cursor123"
        assert result.dataset_commit == "commit456"
        assert result.total_count == 100

    def test_empty_search_result(self):
        """Test empty search results."""
        result = SearchResult(items=[])

        assert len(result.items) == 0
        assert result.next_cursor is None
        assert result.dataset_commit is None
        assert result.total_count is None


class TestContentResponse:
    """Test ContentResponse model."""

    def test_content_response_creation(self):
        """Test creating content response."""
        response = ContentResponse(
            markdown="# Test Content",
            raw_content="Test Content Raw",
            url="https://example.com",
            content_sha1="abc123",
            dataset_commit="commit123"
        )

        assert response.markdown == "# Test Content"
        assert response.raw_content == "Test Content Raw"
        assert not response.fallback

    def test_get_best_content(self):
        """Test best content selection."""
        # Prefer markdown
        response1 = ContentResponse(
            markdown="# Markdown",
            raw_content="Raw",
            raw_source="Source",
            url="https://example.com"
        )
        assert response1.get_best_content() == "# Markdown"

        # Fallback to raw_content
        response2 = ContentResponse(
            raw_content="Raw Content",
            raw_source="Source",
            url="https://example.com"
        )
        assert response2.get_best_content() == "Raw Content"

        # Fallback to raw_source
        response3 = ContentResponse(
            raw_source="Source Content",
            url="https://example.com"
        )
        assert response3.get_best_content() == "Source Content"


class TestVersionInfo:
    """Test VersionInfo model."""

    def test_version_info_creation(self):
        """Test creating version info."""
        info = VersionInfo(
            dataset_commit="commit123",
            current_lancedb_version=42,
            retention={"enabled": True, "count": 20},
            server_info={"version": "1.0.0"}
        )

        assert info.dataset_commit == "commit123"
        assert info.current_lancedb_version == 42
        assert info.retention["enabled"] is True


class TestSyncResult:
    """Test SyncResult model."""

    def test_sync_result_creation(self):
        """Test creating sync result."""
        result = SyncResult(
            dataset_commit="new-commit",
            lancedb_version=43,
            updated=150,
            skipped=850,
            processing_time_ms=5000,
            errors=["Minor error 1"]
        )

        assert result.dataset_commit == "new-commit"
        assert result.lancedb_version == 43
        assert result.updated == 150
        assert result.skipped == 850
        assert result.processing_time_ms == 5000
        assert len(result.errors) == 1
