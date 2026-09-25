"""Emit one terminal HTTP diagnostic and write one audit record per logical call.

Unconfigured library calls stay silent. Composition roots configure the existing
logging adapter; this module never changes global configuration. An audit sink
failure never changes the call's result. The diagnostic event reports the
failure's class name and the call returns its answer or re-raises its error.
Source: https://opentelemetry.io/docs/specs/otel/error-handling/.
Source: https://docs.python.org/3/library/logging.html#logging.Handler.handleError.
The record's question type names come from `judgevet.domain.questions`.

Examples:
    ```python
    from judgevet.adapters.outbound.http_events import call_event

    with call_event("jev-latest", {"q1": {"type": "noul"}}) as event:
        event.status_code = 200
        event.outcome = "success"
    ```

See Also:
    - [judgevet.adapters.outbound.http][]: Sync and async call sites.
    - [judgevet.adapters.inbound.logs][]: Application logging configuration.
    - [judgevet.domain.audit.JudgmentRecord][]: The record each call writes.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from judgevet.diagnostics import current_request_id, diagnostic_model
from judgevet.domain.audit import JudgmentRecord
from judgevet.domain.questions import question_types
from judgevet.domain.response import SystemOneResponse
from judgevet.ports import AuditSink


@dataclass
class CallEvent:
    """Hold terminal status and successful response metadata, never customer content.

    Attributes:
        status_code (int | None): HTTP status, or None when no answer arrived.
        outcome (str): Error until typed parsing succeeds.
        resolved_model (str | None): Model from a successful typed response.
        input_tokens (int | None): Successful typed input token count.
        output_tokens (int | None): Successful typed output token count.
        answer (SystemOneResponse | None): Successful typed response for the audit record.
        state_fingerprint (str | None): Keyed state fingerprint the adapter
            computed, or None when no key is configured.

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
    answer: SystemOneResponse | None = None
    state_fingerprint: str | None = None

    def succeed(self, answer: SystemOneResponse) -> SystemOneResponse:
        """Record a successful typed response and return it unchanged.

        Args:
            answer: The parsed response of the final attempt.

        Returns:
            The same response, for the caller to return.
        """
        self.answer = answer
        self.resolved_model = answer.model
        self.input_tokens = answer.usage.input_tokens
        self.output_tokens = answer.usage.output_tokens
        self.outcome = "success"
        return answer


def _record(
    model: str,
    questions: Mapping[str, Any],
    event: CallEvent,
    failure: BaseException | None,
) -> JudgmentRecord:
    """Build the audit record from terminal metadata, never from the state.

    The keyed state fingerprint arrives precomputed on the event.

    Args:
        model: Effective requested model identifier.
        questions: Question objects or raw wire dictionaries keyed by id.
        event: Terminal metadata populated by the adapter.
        failure: The exception that ended the call, or None on success.

    Returns:
        A frozen record of the logical call.
    """
    answer = event.answer if failure is None else None
    if failure is None:
        outcome = event.outcome
    else:
        outcome = "error" if isinstance(failure, Exception) else "cancelled"
    return JudgmentRecord(
        timestamp=datetime.now(UTC),
        outcome=outcome,
        requested_model=model,
        questions=question_types(questions),
        error_type=None if failure is None else type(failure).__name__,
        status_code=event.status_code,
        resolved_model=None if answer is None else answer.model,
        answers=None if answer is None else answer.answers,
        usage=None if answer is None else answer.usage,
        request_id=current_request_id(),
        state_fingerprint=event.state_fingerprint,
    )


def _write(
    audit: AuditSink | None,
    model: str,
    questions: Mapping[str, Any],
    event: CallEvent,
    failure: BaseException | None,
) -> str | None:
    """Write one record and contain any failure of the build or the sink.

    A contained failure is logged with its traceback when logging is configured.

    Args:
        audit: Configured sink, or None when auditing is off.
        model: Effective requested model identifier.
        questions: Question objects or raw wire dictionaries keyed by id.
        event: Terminal metadata populated by the adapter.
        failure: The exception that ended the call, or None on success.

    Returns:
        The class name of a contained failure, or None when the write succeeded.
    """
    if audit is None:
        return None
    try:
        audit.record(_record(model, questions, event, failure))
    except Exception as exc:
        if structlog.is_configured():
            logger = structlog.get_logger()
            logger.exception("audit sink failed", sink=type(audit).__name__)
        return type(exc).__name__
    return None


@contextmanager
def call_event(
    model: str, questions: Mapping[str, Any], audit: AuditSink | None = None
) -> Iterator[CallEvent]:
    """Write the audit record, then emit filtered terminal metadata when configured.

    Args:
        model: Effective requested model identifier.
        questions: Question objects or raw wire dictionaries keyed by id.
        audit: Optional sink receiving one record when the call ends.

    Yields:
        Mutable terminal metadata populated by the adapter.

    Raises:
        BaseException: The call's own failure, unchanged, after the record is written.
    """
    event = CallEvent()
    failure: BaseException | None = None
    try:
        yield event
    except BaseException as exc:
        failure = exc
        raise
    finally:
        audit_error = _write(audit, model, questions, event, failure)
        extra = {} if audit_error is None else {"audit_error": audit_error}
        if structlog.is_configured():
            structlog.get_logger().debug(
                "http.call",
                model=diagnostic_model(model),
                question_count=len(questions),
                status_code=event.status_code,
                outcome=event.outcome,
                resolved_model=diagnostic_model(event.resolved_model),
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                request_id=current_request_id(),
                **extra,
            )
