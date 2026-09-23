"""Emit one terminal HTTP diagnostic with scoped correlation and typed metadata.

Unconfigured library calls stay silent. Composition roots configure the existing
logging adapter; this module never changes global configuration.

Examples:
    ```python
    from judgevet.adapters.outbound.http_events import call_event

    with call_event("jev-latest", 1) as event:
        event.status_code = 200
        event.outcome = "success"
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: Sync and async call sites.
    - [judgevet.adapters.inbound.logs][]: Application logging configuration.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import structlog

from judgevet.diagnostics import current_request_id, diagnostic_model


@dataclass
class CallEvent:
    """Hold terminal status and successful response metadata, never customer content.

    Attributes:
        status_code (int | None): HTTP status, or None when no answer arrived.
        outcome (str): Error until typed parsing succeeds.
        resolved_model (str | None): Model from a successful typed response.
        input_tokens (int | None): Successful typed input token count.
        output_tokens (int | None): Successful typed output token count.

    Examples:
        ```python
        assert CallEvent().outcome == "error"
        ```
    """

    status_code: int | None = None
    outcome: str = "error"
    resolved_model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


@contextmanager
def call_event(model: str, question_count: int) -> Iterator[CallEvent]:
    """Emit filtered model, correlation and terminal metadata when logging is configured.

    Args:
        model: Effective requested model identifier.
        question_count: Number of questions in the call.

    Yields:
        Mutable terminal metadata populated by the adapter.
    """
    event = CallEvent()
    try:
        yield event
    finally:
        if structlog.is_configured():
            structlog.get_logger().debug(
                "http.call",
                model=diagnostic_model(model),
                question_count=question_count,
                status_code=event.status_code,
                outcome=event.outcome,
                resolved_model=diagnostic_model(event.resolved_model),
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                request_id=current_request_id(),
            )
