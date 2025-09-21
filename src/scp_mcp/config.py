"""Configuration management for SCP MCP Server.

Handles environment-based configuration with layered loading:
1. .env.template (base defaults)
2. .env.local (personal overrides)
3. Environment variables (highest priority)
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with environment variable support."""

    model_config = SettingsConfigDict(
        # Load from multiple env files in order
        env_file=[".env.template", ".env.local"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Settings
    app_name: str = Field(default="SCP MCP Server", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")

    # MCP Server Settings
    mcp_server_name: str = Field(default="scp-foundation", description="MCP server identifier")
    mcp_server_version: str = Field(default="1.0.0", description="MCP protocol version")

    # Database Settings
    lancedb_path: Path = Field(default=Path("./data/lancedb"), description="LanceDB storage path")
    lancedb_table_name: str = Field(default="items", description="Primary table name")

    # Data Settings
    scp_data_path: Path = Field(default=Path("./data/raw"), description="SCP raw data storage path")
    processed_data_path: Path = Field(default=Path("./data/processed"), description="Processed data path")
    staging_data_path: Path = Field(default=Path("./data/staging"), description="Staging data path")

    # Content Processing
    markdown_generation: bool = Field(default=True, description="Generate AI-friendly markdown")
    content_fallback: bool = Field(default=True, description="Fall back to raw_source if raw_content missing")

    # Search & Pagination
    default_search_limit: int = Field(default=25, description="Default search results limit")
    max_search_limit: int = Field(default=100, description="Maximum search results limit")
    pagination_enabled: bool = Field(default=True, description="Enable cursor-based pagination")

    # Performance Settings
    batch_size: int = Field(default=1000, description="Batch size for bulk operations")
    max_concurrent_requests: int = Field(default=50, description="Maximum concurrent requests")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")

    # Version Management
    version_retention_enabled: bool = Field(default=True, description="Enable version retention policies")
    version_retention_count: int = Field(default=20, description="Number of versions to retain")
    version_cleanup_schedule: str = Field(default="daily", description="Version cleanup schedule")

    # Attribution & Licensing
    attribution_enabled: bool = Field(default=True, description="Include CC BY-SA attribution")
    attribution_min_content_length: int = Field(default=100, description="Minimum content length for attribution")
    license_compliance_strict: bool = Field(default=True, description="Strict license compliance mode")

    # Model & AI Settings
    huggingface_cache_dir: Path = Field(default=Path("./models"), description="HuggingFace models cache directory")
    transformers_cache_dir: Path | None = Field(default=None, description="Transformers cache directory override")

    # API Keys (optional, loaded from .env.local)
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    openai_api_base: str | None = Field(default=None, description="OpenAI API base URL (for alternative endpoints)")
    openai_model: str | None = Field(default=None, description="OpenAI model name (default: gpt-3.5-turbo)")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    huggingface_token: str | None = Field(default=None, description="HuggingFace API token")

    # HTTP Server Settings (for HTTP transport)
    http_host: str = Field(default="127.0.0.1", description="HTTP server host")
    http_port: int = Field(default=8000, description="HTTP server port")
    http_cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    log_include_payloads: bool = Field(default=False, description="Include request/response payloads in logs")

    @field_validator("lancedb_path", "scp_data_path", "processed_data_path", "staging_data_path", "huggingface_cache_dir")
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Ensure directory paths exist."""
        if v:
            v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("version_cleanup_schedule")
    @classmethod
    def validate_cleanup_schedule(cls, v: str) -> str:
        """Validate cleanup schedule."""
        valid_schedules = {"never", "hourly", "daily", "weekly", "monthly"}
        if v.lower() not in valid_schedules:
            raise ValueError(f"version_cleanup_schedule must be one of {valid_schedules}")
        return v.lower()

    def get_latest_scp_data_dir(self) -> Path | None:
        """Get the most recent SCP data directory."""
        scp_dirs = list(self.scp_data_path.glob("scp-*"))
        if not scp_dirs:
            return None
        # Sort by directory name (timestamp is first part)
        return max(scp_dirs)

    def get_scp_items_path(self) -> Path | None:
        """Get the path to SCP items data."""
        latest_dir = self.get_latest_scp_data_dir()
        if not latest_dir:
            return None
        return latest_dir / "items"



# Global settings instance
settings = Settings()
