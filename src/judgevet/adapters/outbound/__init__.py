"""Outbound adapters that call external APIs.

This package holds adapters that push data out to external services.
The HTTP adapter calls the TypeSafe Jev System One API. The JSONL audit
sink appends audit records to a local file.

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
    - [judgevet.adapters.outbound.audit_jsonl][]: JSONL audit sink

Attributes:
    HTTPSystemOneAdapter (type): HTTP adapter for SystemOnePort.
"""
