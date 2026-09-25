"""Acceptance tests for the keyed state fingerprint on audit records (#191)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest
import structlog
from structlog.testing import capture_logs

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
    JudgmentRecord,
    Noul,
)
from judgevet._fingerprint import state_fingerprint

pytestmark = pytest.mark.unit

KEY = b"\x00" * 32
VECTOR = "ddc817f8d4f77bdd497151cf4c4614acaa49f4e151da3ff948f4d8f32d6a1212"
QUESTIONS = {"q1": Noul(instructions="Is it valid?")}
SUCCESS = {
    "model": "jev-1.13.0",
    "usage": {"input_tokens": 7, "output_tokens": 3},
    "answers": {"q1": {"type": "noul", "noul": 0.8}},
}


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


class ReplacingRedactor:
    """Replace every state with a fixed redacted string."""

    def redact(self, state: Any) -> Any:
        """Return the redacted form, whatever came in.

        Args:
            state: The copied caller state.

        Returns:
            A fixed replacement string.
        """
        return "redacted"


def _transport() -> httpx.MockTransport:
    """Answer every attempt with the same success body."""
    return httpx.MockTransport(lambda request: httpx.Response(200, json=SUCCESS))


def sync_record(state: Any, **options: Any) -> JudgmentRecord:
    """Run one sync call and return the single record it wrote."""
    sink = RecordingSink()
    with HTTPSystemOneAdapter(
        api_key="synthetic", transport=_transport(), audit=sink, **options
    ) as adapter:
        adapter.system_one(state, QUESTIONS)
    [record] = sink.records
    return record


def async_record(state: Any, **options: Any) -> JudgmentRecord:
    """Run one async call and return the single record it wrote."""
    sink = RecordingSink()

    async def run() -> None:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic", transport=_transport(), audit=sink, **options
        ) as adapter:
            await adapter.system_one(state, QUESTIONS)

    asyncio.run(run())
    [record] = sink.records
    return record


RECORDERS = pytest.mark.parametrize(
    "recorder", [sync_record, async_record], ids=["sync", "async"]
)
Recorder = Callable[..., JudgmentRecord]


def test_same_key_same_fingerprint() -> None:
    """One key and one state give one value, key order aside."""
    first = state_fingerprint(KEY, {"a": 1, "b": [1, 2]})
    second = state_fingerprint(KEY, {"b": [1, 2], "a": 1})
    assert first == second
    assert len(first) == 64
    assert first == first.lower()


def test_other_key_differs() -> None:
    """A different key gives a different value for the same state."""
    assert state_fingerprint(KEY, "synthetic") != state_fingerprint(
        b"\x01" * 32, "synthetic"
    )


def test_vector_matches() -> None:
    """The published test vector holds."""
    assert state_fingerprint(KEY, "synthetic") == VECTOR


def test_dict_and_string_states_differ() -> None:
    """A list and its JSON text are different states."""
    assert state_fingerprint(KEY, []) != state_fingerprint(KEY, "[]")


@RECORDERS
def test_no_key_is_none(recorder: Recorder) -> None:
    """Without a key the record carries no fingerprint."""
    assert recorder("synthetic").state_fingerprint is None


@RECORDERS
def test_sink_record_carries_fingerprint(recorder: Recorder) -> None:
    """With a key the record carries the fingerprint of the state."""
    assert recorder("synthetic", fingerprint_key=KEY).state_fingerprint == VECTOR


@RECORDERS
def test_fingerprint_is_pre_redaction(recorder: Recorder) -> None:
    """The fingerprint hashes the caller's state, not the redacted one."""
    record = recorder("synthetic", fingerprint_key=KEY, redactor=ReplacingRedactor())
    assert record.state_fingerprint == VECTOR
    assert record.state_fingerprint != state_fingerprint(KEY, "redacted")


@RECORDERS
def test_key_absent_from_record_and_events(recorder: Recorder) -> None:
    """Neither the record nor the call event carries the key."""
    key = bytes(range(32))
    previous = structlog.get_config()
    was_configured = structlog.is_configured()
    try:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10),
            cache_logger_on_first_use=False,
        )
        with capture_logs() as events:
            record = recorder("synthetic", fingerprint_key=key)
    finally:
        if was_configured:
            structlog.configure(**previous)
        else:
            structlog.reset_defaults()
    assert record.state_fingerprint == state_fingerprint(key, "synthetic")
    [event] = [entry for entry in events if entry["event"] == "http.call"]
    for text in (repr(record), repr(event)):
        assert repr(key) not in text
        assert key.hex() not in text
