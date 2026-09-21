"""Structured logging, configured once by the composition root.

Logs are diagnostics, not evidence. Telemetry is evidence: append-only,
raw responses, every row stamped (ADR-0006). A verdict never reads a log
line. The two carry the same ids, so they join.

Logging is a cross-cutting concern, not a port. The composition root calls
``configure`` once, and adapters call ``structlog.get_logger()`` directly.
The domain may not import ``structlog`` at all (ADR-0001).

Every line goes to stderr, so ``--json`` output on stdout keeps piping.
A TTY gets the console renderer, anything else gets JSON lines. A
traceback prints its frames without their locals in both formats, so a
secret held in a failing frame never reaches the line.

Attributes:
    LogSettings: The ``log`` branch of the root ``Settings``.
    REDACTED: What a masked value is replaced with.
    SECRET_KEYS: Field names whose values never reach the output.

Examples:
    ```python
    configure(LogSettings(format="json", level="debug"))
    bind_invocation(command="jev call", run_id=new_run_id())
    structlog.get_logger().info("call.start", questions=5)
    ```

See Also:
    - [judgevet.adapters.inbound.cli][]: Calls ``configure`` once.
"""

from __future__ import annotations

import logging
import sys
import uuid
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict
from structlog.tracebacks import ExceptionDictTransformer

REDACTED = "***"
SECRET_KEYS = frozenset(
    {
        "api_key",
        "api_key_id",
        "authorization",
        "private_key",
        "private_key_pem",
        "signature",
        "TYPESAFE_API_KEY",
    }
)
LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}
_SCALARS = (bool, int, float)
_EXC_INFO = "exc_info"
_DICT_TRACEBACKS = structlog.processors.ExceptionRenderer(
    ExceptionDictTransformer(show_locals=False)
)


class LogSettings(BaseModel):
    """How the lines are rendered and which ones are kept.

    Attributes:
        format (str): ``auto``, ``json`` or ``console``. Default ``auto``.
        level (str): ``debug``, ``info``, ``warning``, ``error`` or
            ``critical``. Default ``info``.

    Examples:
        ```python
        assert LogSettings().format == "auto"
        assert LogSettings(level="debug").level == "debug"
        ```
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    format: str = "auto"
    level: str = "info"


def _mask(value: Any) -> Any:
    """Replace a secret-looking value, walking every container.

    A string, a number, a boolean and None pass through. A dict is
    walked by key. A list, a tuple and a set are walked by item and
    render as a list. Any other object is replaced by its type name, so
    no ``repr`` reaches the renderer.

    Args:
        value: Any bound value.

    Returns:
        The value with secrets masked, or the type name of an object.
    """
    if isinstance(value, str):
        return REDACTED if _is_pem(value) else value
    if value is None or isinstance(value, _SCALARS):
        return value
    if isinstance(value, dict):
        return {k: _redact_pair(k, v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_mask(item) for item in value]
    return type(value).__name__


def _is_pem(value: str) -> bool:
    """Check if a string contains a PEM block.

    Args:
        value: The string to check.

    Returns:
        True if the string contains a PEM marker.
    """
    return "-----BEGIN" in value


def _redact_pair(key: Any, value: Any) -> Any:
    """Mask one key-value pair by name, else walk the value.

    Args:
        key: The field name.
        value: The bound value.

    Returns:
        ``REDACTED`` when the name is a secret, else the masked value.
    """
    if isinstance(key, str) and key.lower() in {k.lower() for k in SECRET_KEYS}:
        return REDACTED
    return _mask(value)


def redact(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Processor: mask every secret before the line is rendered.

    Masks by field name at any depth of a dict, a list, a tuple or a
    set. Masks any string carrying a PEM header, whatever its field is
    called. Renders any other object as its type name. Passes the
    ``exc_info`` tuple untouched: the renderer consumes it, and the
    frames it prints carry no locals.

    Args:
        _logger: The wrapped logger. Unused.
        _method: The level method name. Unused.
        event_dict: The event being rendered.

    Returns:
        The event with secrets replaced by ``REDACTED``.

    Examples:
        ```python
        assert redact(None, "info", {"api_key": "k"})["api_key"] == "***"
        ```
    """
    return {
        k: v if k == _EXC_INFO else _redact_pair(k, v) for k, v in event_dict.items()
    }


def wants_json(settings: LogSettings, stream: Any) -> bool:
    """Decide the renderer: JSON lines unless a terminal is watching.

    ``json`` and ``console`` force the choice. ``auto`` renders for a
    person at a TTY and for a machine everywhere else.

    Args:
        settings: The log settings.
        stream: Where lines are written.

    Returns:
        True for JSON lines, False for the console renderer.

    Examples:
        ```python
        assert wants_json(LogSettings(format="json"), sys.stderr)
        ```
    """
    if settings.format != "auto":
        return settings.format == "json"
    return not (hasattr(stream, "isatty") and stream.isatty())


def configure(settings: LogSettings, stream: Any = None) -> None:
    """Wire the processor chain. The composition root calls this once.

    Lines go to ``stream``, which defaults to stderr so ``--json`` output
    on stdout keeps piping. Calling it again replaces the configuration,
    which is what a test needs.

    A traceback renders without frame locals in both formats. The JSON
    path transforms the exception into a dict before ``redact`` runs, so
    a PEM in an exception message is masked too.

    Args:
        settings: Format and level.
        stream: Where to write. Default stderr.

    Examples:
        ```python
        configure(LogSettings(format="json"))
        ```
    """
    target = sys.stderr if stream is None else stream
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    if wants_json(settings, target):
        processors += [_DICT_TRACEBACKS, redact, structlog.processors.JSONRenderer()]
    else:
        processors += [
            redact,
            structlog.dev.ConsoleRenderer(
                exception_formatter=structlog.dev.plain_traceback
            ),
        ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(LEVELS[settings.level]),
        logger_factory=structlog.PrintLoggerFactory(target),
        cache_logger_on_first_use=False,
    )


def new_run_id() -> str:
    """Identify one CLI invocation, so its lines join to each other.

    Returns:
        Twelve hex characters.

    Examples:
        ```python
        assert len(new_run_id()) == 12
        ```
    """
    return uuid.uuid4().hex[:12]


def bind_command(command: str) -> None:
    """Name the command, keeping this invocation's ``run_id``.

    A sub-application calls this from its own callback, where the
    sub-command's name is finally known.

    Args:
        command: For example ``jev call``.

    Examples:
        ```python
        bind_command("jev call")
        ```
    """
    structlog.contextvars.bind_contextvars(command=command)


def bind_invocation(command: str, run_id: str) -> None:
    """Bind what every line of this invocation carries.

    Args:
        command: For example ``jev``.
        run_id: From ``new_run_id``.

    Examples:
        ```python
        bind_invocation("jev", new_run_id())
        ```
    """
    structlog.contextvars.bind_contextvars(command=command, run_id=run_id)
