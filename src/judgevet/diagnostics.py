"""Scope caller correlation and filter built-in diagnostic metadata.

Context tokens restore previous bindings, including after exceptions and task
cancellation. Importing this module does not configure logging.
The `http.call` event carries `audit_error` when an audit sink fails.
See https://docs.python.org/3/library/contextvars.html for context inheritance.

Examples:
    ```python
    from judgevet.diagnostics import bind_request_id, current_request_id

    with bind_request_id("request-123"):
        assert current_request_id() == "request-123"
    assert current_request_id() is None
    ```

See Also:
    - [judgevet.adapters.outbound.http_events][]: Terminal HTTP events.
    - [judgevet.adapters.inbound.logs][]: Configured event rendering.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_REQUEST_ID: ContextVar[str | None] = ContextVar("judgevet_request_id", default=None)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_MODEL = re.compile(r"jev-(?:latest|[0-9]+\.[0-9]+\.[0-9]+)")
_MAX_MODEL_LENGTH = 64
_EVENT_FIELDS = {
    "http.call": frozenset(
        {
            "event",
            "model",
            "question_count",
            "status_code",
            "outcome",
            "resolved_model",
            "input_tokens",
            "output_tokens",
            "request_id",
            "audit_error",
        }
    ),
    "mcp.runtime": frozenset({"event", "request_id"}),
}


@contextmanager
def bind_request_id(request_id: str | None) -> Iterator[None]:
    """Bind a non-sensitive caller identifier until this scope exits.

    None temporarily clears correlation. Nested scopes restore the outer value.
    New asyncio tasks inherit their creation context; sibling bindings stay isolated.
    The identifier stays local unless GatewayConfig opts into HTTP propagation.

    Args:
        request_id: None or an ASCII identifier of at most 128 characters.

    Yields:
        None while the binding is active.

    Raises:
        ValueError: If the identifier has an invalid type, length or character.

    Examples:
        ```python
        with bind_request_id("gateway-123"):
            assert current_request_id() == "gateway-123"
        ```
    """
    if request_id is not None and (
        not isinstance(request_id, str) or _IDENTIFIER.fullmatch(request_id) is None
    ):
        raise ValueError("Invalid request identifier")
    token = _REQUEST_ID.set(request_id)
    try:
        yield
    finally:
        _REQUEST_ID.reset(token)


def current_request_id() -> str | None:
    """Read the dedicated correlation binding without arbitrary logging context.

    Returns:
        The current caller identifier, or None outside a binding.
    """
    return _REQUEST_ID.get()


def diagnostic_model(model: str | None) -> str | None:
    """Keep bounded Jev-shaped identifiers without changing API model values.

    This is a logging filter, not upstream model validation. Callers must still
    keep sensitive values out of version-shaped identifiers.

    Args:
        model: Requested or successfully resolved model value.

    Returns:
        The bounded identifier, or None for any other value.
    """
    if (
        model is not None
        and len(model) <= _MAX_MODEL_LENGTH
        and _MODEL.fullmatch(model)
    ):
        return model
    return None


def filter_event_fields(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Restrict built-in events after context merge; preserve application events.

    Args:
        _logger: Unused wrapped logger.
        _method: Unused severity method.
        event_dict: Event after configured context merging.

    Returns:
        Allowed built-in metadata, or the unchanged application event.
    """
    name = event_dict.get("event")
    fields = _EVENT_FIELDS.get(name) if isinstance(name, str) else None
    if fields is None:
        return event_dict
    return {key: value for key, value in event_dict.items() if key in fields}
