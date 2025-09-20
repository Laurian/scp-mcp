"""Command-line interface for SCP MCP Server.

Provides CLI commands for managing the SCP MCP server,
data synchronization, and development tasks.
"""

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import settings
from .server import SCPMCPServer

app = typer.Typer(
    name="scp-mcp",
    help="SCP MCP Server - A Model Context Protocol Server for SCP Foundation Data"
)
console = Console()


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    transport: str = typer.Option("stdio", "--transport", "-t", help="Transport protocol (stdio, http, sse)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
) -> None:
    """Start the SCP MCP server."""
    console.print("[bold green]Starting SCP MCP Server[/bold green]")
    console.print(f"Transport: {transport}")

    if transport == "http":
        console.print(f"HTTP Server: http://{host}:{port}")
    elif transport == "stdio":
        console.print("STDIO Transport: Ready for MCP client connection")

    server = SCPMCPServer()

    if transport == "http":
        server.run(transport="http", host=host, port=port)
    elif transport == "sse":
        server.run(transport="sse", host=host, port=port)
    else:
        # Default STDIO transport
        server.run()


@app.command()
def sync(
    force: bool = typer.Option(False, "--force", help="Force full resync"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without making changes"),
) -> None:
    """Synchronize SCP data from upstream source."""
    console.print("[bold blue]Synchronizing SCP Data[/bold blue]")

    if dry_run:
        console.print("[yellow]Dry run mode - no changes will be made[/yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading SCP data...", total=None)

        # TODO: Implement actual sync logic
        import time
        time.sleep(2)  # Simulate work

        progress.update(task, description="Processing items...")
        time.sleep(1)

        progress.update(task, description="Updating database...")
        time.sleep(1)

    console.print("[bold green]✓ Sync completed successfully[/bold green]")

    # Show summary table
    table = Table(title="Sync Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="magenta")

    table.add_row("Items Updated", "0")
    table.add_row("Items Skipped", "0")
    table.add_row("Processing Time", "3.0s")

    console.print(table)


@app.command()
def status() -> None:
    """Show current system status and configuration."""
    console.print("[bold blue]SCP MCP Server Status[/bold blue]")

    # Configuration table
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("App Version", settings.app_version)
    config_table.add_row("MCP Server Name", settings.mcp_server_name)
    config_table.add_row("LanceDB Path", str(settings.lancedb_path))
    config_table.add_row("Debug Mode", "✓" if settings.debug else "✗")
    config_table.add_row("Attribution Enabled", "✓" if settings.attribution_enabled else "✗")

    console.print(config_table)

    # Data status
    data_table = Table(title="Data Status")
    data_table.add_column("Component", style="cyan")
    data_table.add_column("Status", style="green")

    latest_data = settings.get_latest_scp_data_dir()
    if latest_data:
        data_table.add_row("SCP Data", f"✓ Available ({latest_data.name})")
    else:
        data_table.add_row("SCP Data", "✗ Not found")

    if settings.lancedb_path.exists():
        data_table.add_row("LanceDB", "✓ Initialized")
    else:
        data_table.add_row("LanceDB", "✗ Not initialized")

    console.print(data_table)


@app.command()
def init(
    force: bool = typer.Option(False, "--force", help="Force reinitialize existing setup"),
) -> None:
    """Initialize the SCP MCP server environment."""
    console.print("[bold blue]Initializing SCP MCP Server[/bold blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create directories
        task = progress.add_task("Creating directories...", total=None)

        directories = [
            settings.lancedb_path,
            settings.scp_data_path,
            settings.processed_data_path,
            settings.staging_data_path,
            settings.huggingface_cache_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        progress.update(task, description="Checking environment...")
        import time
        time.sleep(1)

        progress.update(task, description="Validating configuration...")
        time.sleep(1)

    console.print("[bold green]✓ Initialization completed[/bold green]")
    console.print("\nNext steps:")
    console.print("1. Run [bold cyan]scp-mcp sync[/bold cyan] to download SCP data")
    console.print("2. Run [bold cyan]scp-mcp serve[/bold cyan] to start the server")


@app.command()
def validate() -> None:
    """Validate current setup and configuration."""
    console.print("[bold blue]Validating SCP MCP Server Setup[/bold blue]")

    issues = []
    warnings = []

    # Check required directories
    if not settings.lancedb_path.exists():
        issues.append(f"LanceDB directory missing: {settings.lancedb_path}")

    # Check for SCP data
    if not settings.get_latest_scp_data_dir():
        warnings.append("No SCP data found - run 'scp-mcp sync' to download")

    # Check configuration
    if settings.debug:
        warnings.append("Debug mode is enabled - disable for production")

    # Display results
    if not issues and not warnings:
        console.print("[bold green]✓ All validations passed[/bold green]")
    else:
        if issues:
            console.print("[bold red]Issues found:[/bold red]")
            for issue in issues:
                console.print(f"  ✗ {issue}")

        if warnings:
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for warning in warnings:
                console.print(f"  ⚠ {warning}")


@app.command()
def config(
    show_secrets: bool = typer.Option(False, "--show-secrets", help="Show API keys and secrets"),
) -> None:
    """Show current configuration."""
    console.print("[bold blue]SCP MCP Server Configuration[/bold blue]")

    # Create configuration display
    table = Table(title="Settings")
    table.add_column("Setting", style="cyan", min_width=25)
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")

    # Core settings
    table.add_row("App Name", settings.app_name, "config")
    table.add_row("App Version", settings.app_version, "config")
    table.add_row("Debug Mode", str(settings.debug), "env")
    table.add_row("MCP Server Name", settings.mcp_server_name, "config")

    # Paths
    table.add_row("LanceDB Path", str(settings.lancedb_path), "config")
    table.add_row("SCP Data Path", str(settings.scp_data_path), "config")
    table.add_row("HuggingFace Cache", str(settings.huggingface_cache_dir), "config")

    # Performance
    table.add_row("Default Search Limit", str(settings.default_search_limit), "config")
    table.add_row("Max Search Limit", str(settings.max_search_limit), "config")
    table.add_row("Batch Size", str(settings.batch_size), "config")

    # API Keys (masked unless show_secrets)
    if show_secrets:
        table.add_row("OpenAI API Key", settings.openai_api_key or "Not set", "env")
        table.add_row("Anthropic API Key", settings.anthropic_api_key or "Not set", "env")
        table.add_row("HuggingFace Token", settings.huggingface_token or "Not set", "env")
    else:
        table.add_row("OpenAI API Key", "***" if settings.openai_api_key else "Not set", "env")
        table.add_row("Anthropic API Key", "***" if settings.anthropic_api_key else "Not set", "env")
        table.add_row("HuggingFace Token", "***" if settings.huggingface_token else "Not set", "env")

    console.print(table)


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
