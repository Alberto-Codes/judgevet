"""Inbound adapters that accept user input.

This package holds adapters that pull data into the domain. Currently
this includes the CLI (typer) and the MCP stdio server. Both take a
SystemOnePort and call its methods to fulfill requests.

Examples:
    ```python
    from judgevet.adapters.inbound.cli import app, cli_main

    # Run the CLI
    # cli_main() or: uv run jev "state" '{"q1": {"type": "noul", "instructions": "?"}}'
    ```

See Also:
    - [judgevet.ports.SystemOnePort][]: Protocol definition
    - [judgevet.adapters.outbound.http][]: HTTP adapter
    - [judgevet.domain.response][]: Response types
    - [judgevet.domain.answers][]: Answer types

Attributes:
    app (typer.Typer): Typer CLI application instance.
    cli_main (callable): CLI entry point function.
"""
