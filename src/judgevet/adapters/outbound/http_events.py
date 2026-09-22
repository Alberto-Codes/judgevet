"""Emit one terminal HTTP diagnostic through application-owned logging.

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


@dataclass
class CallEvent:
    """Hold only terminal status and outcome, never caller data.

    Attributes:
        status_code (int | None): HTTP status, or None when no answer arrived.
        outcome (str): Error until typed parsing succeeds.

    Examples:
        ```python
        assert CallEvent().outcome == "error"
        ```
    """

    status_code: int | None = None
    outcome: str = "error"


@contextmanager
def call_event(model: str, question_count: int) -> Iterator[CallEvent]:
    """Emit allowlisted metadata at debug when the application configured logging.

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
                model=model,
                question_count=question_count,
                status_code=event.status_code,
                outcome=event.outcome,
            )
