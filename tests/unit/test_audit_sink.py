"""Behavioural acceptance tests for the opt-in audit sink (#54 slice 1)."""

import asyncio
import dataclasses
import io
import json
from collections.abc import Callable, Iterator
from datetime import UTC, timedelta
from types import MappingProxyType

import httpx
import pytest
import structlog
from structlog.testing import capture_logs

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    AuditSink,
    ChoiceAnswer,
    HTTPSystemOneAdapter,
    JevRequestError,
    JudgmentRecord,
    Noul,
    NoulAnswer,
    RetryPolicy,
    SystemOneResponse,
    Usage,
)
from judgevet.adapters.inbound.logs import LogSettings, configure

STATE = "state-sentinel-7f3a"
QUESTIONS = {"q1": Noul(instructions="Is it valid?"), "q2": {"type": "choice"}}
RETRY = RetryPolicy(max_attempts=3, retry_base_delay=0)
SUCCESS = {
    "model": "jev-1.13.0",
    "usage": {"input_tokens": 7, "output_tokens": 3},
    "answers": {
        "q1": {"type": "noul", "noul": 0.8},
        "q2": {
            "type": "choice",
            "choice": "a",
            "confidence": 0.9,
            "probabilities": {"a": 0.9, "b": 0.1},
        },
    },
}
INVALID = {"detail": [{"type": "missing", "loc": ["body"], "msg": "x", "input": STATE}]}


class RecordingSink:
    """Collect every record the adapter writes."""

    def __init__(self) -> None:
        """Start with no records."""
        self.records: list[JudgmentRecord] = []

    def record(self, record: JudgmentRecord) -> None:
        """Store one record.

        Args:
            record: The record written by the adapter.
        """
        self.records.append(record)


class FailingSink:
    """Raise on every write, as a full disk would."""

    def record(self, record: JudgmentRecord) -> None:
        """Refuse the record.

        Args:
            record: The record written by the adapter.

        Raises:
            OSError: Always.
        """
        raise OSError("sink-failure-canary")


Outcome = SystemOneResponse | JevRequestError


def replies(*responses: httpx.Response) -> Callable[[httpx.Request], httpx.Response]:
    """Return a handler that answers each attempt with the next response."""
    queue = list(responses)

    def handle(request: httpx.Request) -> httpx.Response:
        return queue.pop(0)

    return handle


def sync_adapter(
    sink: AuditSink | None, *responses: httpx.Response
) -> HTTPSystemOneAdapter:
    """Build a sync adapter, passing the sink only when one is given."""
    transport = httpx.MockTransport(replies(*responses))
    if sink is None:
        return HTTPSystemOneAdapter(
            api_key="synthetic", transport=transport, retry=RETRY
        )
    return HTTPSystemOneAdapter(
        api_key="synthetic", transport=transport, retry=RETRY, audit=sink
    )


def sync_call(sink: AuditSink | None, *responses: httpx.Response) -> Outcome:
    """Run one sync call over a mock transport and return its result or error."""
    with sync_adapter(sink, *responses) as adapter:
        try:
            return adapter.system_one(STATE, QUESTIONS)
        except JevRequestError as exc:
            return exc


def async_call(sink: AuditSink, *responses: httpx.Response) -> Outcome:
    """Run one async call over a mock transport and return its result or error."""

    async def run() -> Outcome:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(replies(*responses)),
            retry=RETRY,
            audit=sink,
        ) as adapter:
            try:
                return await adapter.system_one(STATE, QUESTIONS)
            except JevRequestError as exc:
                return exc

    return asyncio.run(run())


def answered(outcome: Outcome) -> SystemOneResponse:
    """Require a typed answer rather than an error."""
    assert isinstance(outcome, SystemOneResponse)
    return outcome


CALLERS = pytest.mark.parametrize("caller", [sync_call, async_call])


def assert_success_record(record: JudgmentRecord) -> None:
    """Check every field of a record for a successful call."""
    assert record.schema_version == 1
    assert record.outcome == "success"
    assert record.timestamp.utcoffset() == timedelta(0)
    assert record.timestamp.tzinfo is UTC
    assert record.error_type is None
    assert record.status_code == 200
    assert record.requested_model == "jev-latest"
    assert record.resolved_model == "jev-1.13.0"
    assert dict(record.questions) == {"q1": "noul", "q2": "choice"}
    assert record.answers is not None
    noul, choice = record.answers["q1"], record.answers["q2"]
    assert isinstance(noul, NoulAnswer)
    assert noul.noul == 0.8
    assert isinstance(choice, ChoiceAnswer)
    assert choice.choice == "a"
    assert record.usage == Usage(input_tokens=7, output_tokens=3)
    assert record.request_id is None


@CALLERS
def test_success_writes_one_complete_record(caller) -> None:
    """A successful call writes exactly one record with the typed answers."""
    sink = RecordingSink()
    answer = answered(caller(sink, httpx.Response(200, json=SUCCESS)))
    assert answer.model == "jev-1.13.0"
    assert len(sink.records) == 1
    assert_success_record(sink.records[0])


def test_retried_call_writes_one_record() -> None:
    """A rate limit followed by success writes one record, not one per attempt."""
    sink = RecordingSink()
    sync_call(sink, httpx.Response(429), httpx.Response(200, json=SUCCESS))
    assert len(sink.records) == 1
    assert_success_record(sink.records[0])


@CALLERS
def test_rejected_call_writes_one_error_record(caller) -> None:
    """A 422 writes one error record with the class name and no answers."""
    sink = RecordingSink()
    error = caller(sink, httpx.Response(422, json=INVALID))
    assert isinstance(error, JevRequestError)
    assert len(sink.records) == 1
    record = sink.records[0]
    assert record.outcome == "error"
    assert record.error_type == "JevRequestError"
    assert record.status_code == 422
    assert record.answers is None
    assert record.usage is None
    assert record.resolved_model is None


@pytest.mark.parametrize(
    "response",
    [httpx.Response(200, json=SUCCESS), httpx.Response(422, json=INVALID)],
)
def test_state_never_enters_the_record(response: httpx.Response) -> None:
    """The state sentinel appears in no field and not in the representation."""
    sink = RecordingSink()
    sync_call(sink, response)
    record = sink.records[0]
    assert STATE not in repr(record)
    for field in dataclasses.fields(record):
        assert STATE not in repr(getattr(record, field.name))


def test_record_is_frozen() -> None:
    """A written record cannot be reassigned or have its mappings edited."""
    sink = RecordingSink()
    sync_call(sink, httpx.Response(200, json=SUCCESS))
    record = sink.records[0]
    field = "outcome"
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(record, field, "error")
    assert isinstance(record.questions, MappingProxyType)
    assert isinstance(record.answers, MappingProxyType)


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    """Install the real JSON processor chain and restore the caller's setup."""
    previous = structlog.get_config()
    was_configured = structlog.is_configured()
    output = io.StringIO()
    configure(LogSettings(format="json", level="debug"), output)
    try:
        yield output
    finally:
        if was_configured:
            structlog.configure(**previous)
        else:
            structlog.reset_defaults()


@CALLERS
def test_failing_sink_keeps_the_answer_and_reports(caller, stream) -> None:
    """A sink failure returns the answer and the rendered event names the failure."""
    answer = answered(caller(FailingSink(), httpx.Response(200, json=SUCCESS)))
    assert answer.model == "jev-1.13.0"
    line = stream.getvalue().splitlines()[-1]
    event = json.loads(line)
    assert event["event"] == "http.call"
    assert event["outcome"] == "success"
    assert event["audit_error"] == "OSError"
    assert "sink-failure-canary" not in line


def test_failing_sink_keeps_the_original_error(stream) -> None:
    """A sink failure after a rejected call re-raises the original error."""
    error = sync_call(FailingSink(), httpx.Response(422, json=INVALID))
    assert isinstance(error, JevRequestError)
    event = json.loads(stream.getvalue().splitlines()[-1])
    assert event["audit_error"] == "OSError"


def test_without_audit_nothing_is_written(stream) -> None:
    """Omitting the option leaves the answer and the event unchanged."""
    answer = answered(sync_call(None, httpx.Response(200, json=SUCCESS)))
    assert answer.model == "jev-1.13.0"
    event = json.loads(stream.getvalue().splitlines()[-1])
    assert "audit_error" not in event


def test_failing_sink_is_logged_once_with_its_traceback() -> None:
    """The contained sink failure produces one configured log entry with exc_info."""
    previous = structlog.get_config()
    was_configured = structlog.is_configured()
    try:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10),
            cache_logger_on_first_use=False,
        )
        with capture_logs() as events:
            sync_call(FailingSink(), httpx.Response(200, json=SUCCESS))
    finally:
        if was_configured:
            structlog.configure(**previous)
        else:
            structlog.reset_defaults()
    failures = [entry for entry in events if entry["event"] == "audit sink failed"]
    assert failures == [
        {
            "event": "audit sink failed",
            "sink": "FailingSink",
            "exc_info": True,
            "log_level": "error",
        }
    ]
    calls = [entry for entry in events if entry["event"] == "http.call"]
    assert [entry["audit_error"] for entry in calls] == ["OSError"]
