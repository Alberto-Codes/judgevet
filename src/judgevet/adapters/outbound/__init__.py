"""Outbound adapters that call external APIs.

This package holds adapters that push data out to external services.
For this project, the only outbound adapter is the HTTP adapter that
calls the TypeSafe Jev System One API.

Examples:
    ```python
    from judgevet.adapters.outbound.http import HTTPSystemOneAdapter
    from judgevet.domain.response import SystemOneResponse

    adapter = HTTPSystemOneAdapter(api_key="your-api-key")
    try:
        response: SystemOneResponse = adapter.system_one(
            state="Your content here",
            questions={"q1": {"type": "noul", "instructions": "Is this correct?"}},
        )
        print(response)
    finally:
        adapter.close()
    ```

See Also:
    - [judgevet.ports.SystemOnePort][]: Protocol definition
    - [judgevet.domain.response][]: Response types
    - [judgevet.domain.errors][]: Error types
    - [judgevet.adapters.inbound.cli][]: CLI adapter

Attributes:
    HTTPSystemOneAdapter (type): HTTP implementation of SystemOnePort.
"""
