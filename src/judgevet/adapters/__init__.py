"""Adapters that sit between the domain and the outside world.

This package is the parent of both inbound and outbound adapters.
In hexagonal architecture, adapters translate between the domain
(core) and external frameworks (APIs, CLI, databases, etc.).

Examples:
    ```python
    # Inbound adapter example
    from judgevet.adapters.inbound.cli import cli_main

    # Outbound adapter example
    from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
    ```

See Also:
    - [judgevet.adapters.inbound][]: Inbound adapters (CLI, MCP)
    - [judgevet.adapters.outbound][]: Outbound adapters (HTTP)
    - [judgevet.ports][]: Port protocols defining the boundary
    - [judgevet.domain][]: Core domain logic

Attributes:
    None: This package provides organizational structure only.
"""
