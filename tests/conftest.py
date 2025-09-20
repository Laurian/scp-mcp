"""Pytest configuration and shared fixtures for SCP MCP Server tests."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock

import pytest

from scp_mcp.config import Settings
from scp_mcp.server import SCPMCPServer


@pytest.fixture
def test_settings() -> Settings:
    """Create test configuration settings."""
    return Settings(
        debug=True,
        lancedb_path=Path("./test_data/lancedb"),
        scp_data_path=Path("./test_data/raw"),
        processed_data_path=Path("./test_data/processed"),
        staging_data_path=Path("./test_data/staging"),
        default_search_limit=10,
        max_search_limit=50,
        batch_size=100,
        version_retention_count=3,
        log_level="DEBUG",
    )


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create temporary test data directory."""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()

    # Create subdirectories
    (test_dir / "raw").mkdir()
    (test_dir / "processed").mkdir()
    (test_dir / "staging").mkdir()
    (test_dir / "lancedb").mkdir()

    return test_dir


@pytest.fixture
def mock_lancedb_table() -> Mock:
    """Mock LanceDB table for testing."""
    table = Mock()
    table.search.return_value = []
    table.to_pandas.return_value.to_dict.return_value = []
    return table


@pytest.fixture
def scp_server(test_settings: Settings) -> Generator[SCPMCPServer, None, None]:
    """Create SCP MCP server instance for testing."""
    server = SCPMCPServer()
    # Override settings for testing
    server._settings = test_settings
    yield server


@pytest.fixture
def sample_scp_item() -> dict:
    """Sample SCP item data for testing."""
    return {
        "link": "scp-173",
        "scp": "SCP-173",
        "scp_number": 173,
        "title": "The Sculpture",
        "series": "series-1",
        "tags": ["euclid", "statue", "hostile"],
        "rating": 1234,
        "url": "https://scp-wiki.wikidot.com/scp-173",
        "domain": "scp-wiki.wikidot.com",
        "raw_content": "Item #: SCP-173\n\nObject Class: Euclid\n\nSpecial Containment Procedures: ...",
        "markdown": "# SCP-173 - The Sculpture\n\n**Object Class:** Euclid\n\n**Special Containment Procedures:** ...",
        "content_sha1": "abc123def456",
        "dataset_commit": "commit-hash-123",
    }


@pytest.fixture
def sample_search_results() -> list:
    """Sample search results for testing."""
    return [
        {
            "link": "scp-173",
            "scp": "SCP-173",
            "scp_number": 173,
            "title": "The Sculpture",
            "rating": 1234,
            "series": "series-1",
        },
        {
            "link": "scp-096",
            "scp": "SCP-096",
            "scp_number": 96,
            "title": "The \"Shy Guy\"",
            "rating": 987,
            "series": "series-1",
        },
    ]
