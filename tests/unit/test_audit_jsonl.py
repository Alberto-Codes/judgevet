"""Behavioural acceptance tests for the JSONL audit sink (#54 slice 2)."""

import asyncio
import dataclasses
import json
import os
import stat
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import structlog
from structlog.testing import capture_logs

from judgevet import (
    AsyncHTTPSystemOneAdapter,
    HTTPSystemOneAdapter,
    JevRequestError,
    JsonlAuditSink,
    JudgmentRecord,
    Noul,
    NoulAnswer,
    RetryPolicy,
    ScoreAnswer,
    SystemOneResponse,
)
from judgevet.domain.media_audit import MediaProvenance

STATE = "state-sentinel-5c1e"
QUESTIONS = {"q1": Noul(instructions="Is it valid?"), "q2": {"type": "choice"}}
RETRY = RetryPolicy(max_attempts=1, retry_base_delay=0)
FIELDS = [field.name for field in dataclasses.fields(JudgmentRecord)]
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


def replies(response: httpx.Response) -> Callable[[httpx.Request], httpx.Response]:
    """Return a handler that answers every attempt with one response."""

    def handle(request: httpx.Request) -> httpx.Response:
        return response

    return handle


def sync_call(sink: JsonlAuditSink, response: httpx.Response) -> object:
    """Run one sync call and return its answer or error."""
    with HTTPSystemOneAdapter(
        api_key="synthetic",
        transport=httpx.MockTransport(replies(response)),
        retry=RETRY,
        audit=sink,
    ) as adapter:
        try:
            return adapter.system_one(STATE, QUESTIONS)
        except JevRequestError as exc:
            return exc


def async_call(sink: JsonlAuditSink, response: httpx.Response) -> object:
    """Run one async call and return its answer or error."""

    async def run() -> object:
        async with AsyncHTTPSystemOneAdapter(
            api_key="synthetic",
            transport=httpx.MockTransport(replies(response)),
            retry=RETRY,
            audit=sink,
        ) as adapter:
            return await adapter.system_one(STATE, QUESTIONS)

    return asyncio.run(run())


def lines(path: Path) -> list[dict[str, object]]:
    """Parse every line of the file as one JSON object."""
    data = path.read_bytes()
    assert data.endswith(b"\n")
    return [json.loads(line) for line in data.decode("utf-8").splitlines()]


BARE = JudgmentRecord(
    timestamp=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
    outcome="success",
    requested_model="jev-latest",
    questions={"q1": "noul"},
)


def bare_record(**changes: object) -> JudgmentRecord:
    """Build a minimal success record with optional field overrides."""
    return dataclasses.replace(BARE, **changes)


def test_success_record_round_trips(tmp_path: Path) -> None:
    """A success call writes one line with every field in order."""
    path = tmp_path / "audit.jsonl"
    before = datetime.now(UTC)
    with JsonlAuditSink(path) as sink:
        answer = sync_call(sink, httpx.Response(200, json=SUCCESS))
    after = datetime.now(UTC)
    assert isinstance(answer, SystemOneResponse)
    assert STATE.encode() not in path.read_bytes()
    assert b"Is it valid?" not in path.read_bytes()
    [line] = lines(path)
    assert list(line) == FIELDS
    assert len(FIELDS) == 13
    assert line["schema_version"] == 1
    assert line["outcome"] == "success"
    assert line["status_code"] == 200
    assert line["resolved_model"] == "jev-1.13.0"
    assert line["questions"] == {"q1": "noul", "q2": "choice"}
    assert line["answers"] == SUCCESS["answers"]
    assert line["usage"] == {"input_tokens": 7, "output_tokens": 3}
    assert line["error_type"] is None
    stamp = datetime.fromisoformat(str(line["timestamp"]))
    assert stamp.utcoffset() == timedelta(0)
    assert before <= stamp <= after


def test_timestamp_round_trips_exactly(tmp_path: Path) -> None:
    """The written timestamp parses back to the record's value."""
    path = tmp_path / "audit.jsonl"
    record = bare_record(timestamp=datetime(2026, 9, 30, 1, 2, 3, 456789, tzinfo=UTC))
    with JsonlAuditSink(path) as sink:
        sink.record(record)
    [line] = lines(path)
    assert line["timestamp"] == "2026-09-30T01:02:03.456789+00:00"
    assert datetime.fromisoformat(str(line["timestamp"])) == record.timestamp
    assert line["answers"] is None
    assert line["state_fingerprint"] is None
    assert line["media_provenance"] is None


def test_error_record_round_trips(tmp_path: Path) -> None:
    """A rejected call writes one error line with null answers."""
    path = tmp_path / "audit.jsonl"
    with JsonlAuditSink(path) as sink:
        error = sync_call(sink, httpx.Response(422, json=INVALID))
    assert isinstance(error, JevRequestError)
    assert STATE.encode() not in path.read_bytes()
    [line] = lines(path)
    assert list(line) == FIELDS
    assert line["outcome"] == "error"
    assert line["error_type"] == "JevRequestError"
    assert line["status_code"] == 422
    assert line["answers"] is None
    assert line["usage"] is None


def test_async_adapter_writes_one_line(tmp_path: Path) -> None:
    """The async adapter writes through the same sink."""
    path = tmp_path / "audit.jsonl"
    with JsonlAuditSink(path) as sink:
        answer = async_call(sink, httpx.Response(200, json=SUCCESS))
    assert isinstance(answer, SystemOneResponse)
    [line] = lines(path)
    assert line["outcome"] == "success"
    assert line["answers"] == SUCCESS["answers"]


def test_threads_interleave_no_lines(tmp_path: Path) -> None:
    """Eight threads of fifty records each yield four hundred whole lines."""
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(path)
    barrier = threading.Barrier(8)

    def write(worker: int) -> None:
        barrier.wait()
        for index in range(50):
            sink.record(bare_record(request_id=f"{worker}-{index}"))

    threads = [threading.Thread(target=write, args=(n,)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    sink.close()
    parsed = lines(path)
    assert len(parsed) == 400
    expected = {f"{w}-{i}" for w in range(8) for i in range(50)}
    assert {line["request_id"] for line in parsed} == expected


def test_missing_directory_fails_at_construction(tmp_path: Path) -> None:
    """The constructor opens the file, so a missing directory raises there."""
    with pytest.raises(FileNotFoundError):
        JsonlAuditSink(tmp_path / "absent" / "audit.jsonl")


def test_closed_sink_raises(tmp_path: Path) -> None:
    """A record after close raises ValueError, and close is idempotent."""
    sink = JsonlAuditSink(tmp_path / "audit.jsonl")
    sink.close()
    sink.close()
    with pytest.raises(ValueError, match=r"^audit sink is closed$"):
        sink.record(bare_record())


def test_closed_sink_keeps_the_adapter_answer(tmp_path: Path) -> None:
    """The adapter contains the closed sink's error and returns the answer."""
    sink = JsonlAuditSink(tmp_path / "audit.jsonl")
    sink.close()
    previous = structlog.get_config()
    was_configured = structlog.is_configured()
    try:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(10),
            cache_logger_on_first_use=False,
        )
        with capture_logs() as events:
            answer = sync_call(sink, httpx.Response(200, json=SUCCESS))
    finally:
        if was_configured:
            structlog.configure(**previous)
        else:
            structlog.reset_defaults()
    assert isinstance(answer, SystemOneResponse)
    calls = [entry for entry in events if entry["event"] == "http.call"]
    assert [entry["audit_error"] for entry in calls] == ["ValueError"]
    assert (tmp_path / "audit.jsonl").read_bytes() == b""


def test_new_file_is_owner_only(tmp_path: Path) -> None:
    """The sink requests mode 0o600 for a new file under a zero umask."""
    path = tmp_path / "audit.jsonl"
    previous = os.umask(0)
    try:
        JsonlAuditSink(path).close()
    finally:
        os.umask(previous)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_fsync_option_writes(tmp_path: Path) -> None:
    """With fsync enabled the record still lands as one line."""
    path = tmp_path / "audit.jsonl"
    with JsonlAuditSink(path, fsync=True) as sink:
        sink.record(bare_record())
        sink.record(bare_record())
    assert len(lines(path)) == 2


def test_append_keeps_existing_lines(tmp_path: Path) -> None:
    """A second sink on the same path appends rather than truncates."""
    path = tmp_path / "audit.jsonl"
    for _ in range(2):
        with JsonlAuditSink(str(path)) as sink:
            sink.record(bare_record())
    assert len(lines(path)) == 2


def test_score_keys_become_strings(tmp_path: Path) -> None:
    """A Score answer's integer keys come back as JSON strings."""
    path = tmp_path / "audit.jsonl"
    score = ScoreAnswer(
        score=2,
        confidence=0.7,
        legend={1: "low", 2: "high"},
        probabilities={1: 0.3, 2: 0.7},
    )
    with JsonlAuditSink(path) as sink:
        sink.record(bare_record(questions={"s": "score"}, answers={"s": score}))
    [line] = lines(path)
    assert line["answers"] == {
        "s": {
            "type": "score",
            "score": 2,
            "confidence": 0.7,
            "legend": {"1": "low", "2": "high"},
            "probabilities": {"1": 0.3, "2": 0.7},
        }
    }


def test_fingerprint_and_provenance_serialise(tmp_path: Path) -> None:
    """Optional provenance fields serialise when present."""
    path = tmp_path / "audit.jsonl"
    provenance = MediaProvenance(
        attachments=[("img-1", "c" * 64)],
        by_question={"q1": ["img-1"]},
        evidence_fingerprint="a" * 64,
        request_fingerprint="b" * 64,
        prompt_revision="p1",
    )
    record = bare_record(
        answers={"q1": NoulAnswer(noul=0.25)},
        state_fingerprint="d" * 64,
        media_provenance=provenance,
    )
    with JsonlAuditSink(path) as sink:
        sink.record(record)
    [line] = lines(path)
    assert line["state_fingerprint"] == "d" * 64
    assert line["media_provenance"] == {
        "attachments": [["img-1", "c" * 64]],
        "by_question": {"q1": ["img-1"]},
        "evidence_fingerprint": "a" * 64,
        "request_fingerprint": "b" * 64,
        "prompt_revision": "p1",
        "provider_identity": None,
        "preprocessing_revision": None,
    }
    assert line["answers"] == {"q1": {"type": "noul", "noul": 0.25}}


def test_non_ascii_is_written_as_utf8(tmp_path: Path) -> None:
    """Non-ASCII text is written as UTF-8, not escaped."""
    path = tmp_path / "audit.jsonl"
    with JsonlAuditSink(path) as sink:
        sink.record(bare_record(questions={"preguntá": "noul"}))
    assert "preguntá".encode() in path.read_bytes()
