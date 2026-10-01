"""Append each audit record to a local file as one JSON line.

`JsonlAuditSink` is the reference `AuditSink`. It writes one compact UTF-8
JSON object per `JudgmentRecord`, terminated by a newline, with no byte order
mark.
Source: https://jsonlines.org/.
Source: https://github.com/ndjson/ndjson-spec.
Keys follow the record's field order, and every field appears on every line.
A `None` field is written as JSON `null`. The timestamp is RFC 3339 text from
`datetime.isoformat()`, with a `+00:00` offset.
Source: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md.
Answers use the API wire shape. JSON object keys are strings, so a Score
answer's `legend` and `probabilities` read back with string keys.
The encoder refuses `NaN` and infinity, because neither is JSON.
Source: https://docs.python.org/3/library/json.html.

The sink opens the file at construction with `O_APPEND` and mode `0o600`.
Each line reaches the file in one `os.write` call under a lock. On a local
POSIX file, `O_APPEND` makes the seek and the write one atomic step.
That guarantee does not hold on NFS with several appenders.
Source: https://man7.org/linux/man-pages/man2/open.2.html.
Rotation and retention belong to the caller.

Examples:
    ```python
    import tempfile
    from datetime import UTC, datetime
    from pathlib import Path

    from judgevet.adapters.outbound.audit_jsonl import JsonlAuditSink
    from judgevet.domain.audit import JudgmentRecord

    record = JudgmentRecord(
        timestamp=datetime(2026, 9, 30, tzinfo=UTC),
        outcome="error",
        requested_model="jev-latest",
        questions={"q1": "noul"},
    )
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "audit.jsonl"
        with JsonlAuditSink(path) as sink:
            sink.record(record)
        assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    ```

See Also:
    - [judgevet.ports.AuditSink][]: The protocol this sink satisfies.
    - [judgevet.domain.audit][]: The record each line encodes.
    - [judgevet.adapters.outbound.http_events][]: Contains a sink failure.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import fields
from types import TracebackType
from typing import Any, Self

from judgevet.domain.answers import Answer, ChoiceAnswer, NoulAnswer, ScoreAnswer
from judgevet.domain.audit import JudgmentRecord
from judgevet.domain.media_audit import MediaProvenance
from judgevet.domain.usage import Usage

_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_APPEND
_MODE = 0o600
_CLOSED = "audit sink is closed"


def _answer(answer: Answer) -> dict[str, Any]:
    """Encode one typed answer in the API wire shape.

    Args:
        answer: A typed answer from a success record.

    Returns:
        The answer as the API response body carries it.

    Raises:
        TypeError: If the answer type is unknown.
    """
    if isinstance(answer, NoulAnswer):
        return {"type": "noul", "noul": answer.noul}
    if isinstance(answer, ChoiceAnswer):
        return {
            "type": "choice",
            "choice": answer.choice,
            "confidence": answer.confidence,
            "probabilities": dict(answer.probabilities),
        }
    if isinstance(answer, ScoreAnswer):
        return {
            "type": "score",
            "score": answer.score,
            "confidence": answer.confidence,
            "legend": {str(key): value for key, value in answer.legend.items()},
            "probabilities": {
                str(key): value for key, value in answer.probabilities.items()
            },
        }
    raise TypeError(f"unknown answer type {type(answer).__name__}")


def _provenance(value: MediaProvenance) -> dict[str, Any]:
    """Encode media provenance as plain JSON data.

    Args:
        value: Caller-built media provenance.

    Returns:
        Every provenance field in declaration order.
    """
    return {
        "attachments": [list(pair) for pair in value.attachments],
        "by_question": {key: list(ids) for key, ids in value.by_question.items()},
        "evidence_fingerprint": value.evidence_fingerprint,
        "request_fingerprint": value.request_fingerprint,
        "prompt_revision": value.prompt_revision,
        "provider_identity": value.provider_identity,
        "preprocessing_revision": value.preprocessing_revision,
    }


def _value(value: object) -> object:
    """Encode one record field value as JSON data.

    Args:
        value: A field value of a `JudgmentRecord`.

    Returns:
        JSON-ready data with field values in a stable shape.
    """
    if isinstance(value, Usage):
        return {
            "input_tokens": value.input_tokens,
            "output_tokens": value.output_tokens,
        }
    if isinstance(value, MediaProvenance):
        return _provenance(value)
    return value


def _encode_record(record: JudgmentRecord) -> bytes:
    """Encode one record as a compact UTF-8 JSON line.

    Args:
        record: The record to encode.

    Returns:
        The JSON object followed by a newline, as UTF-8 bytes.

    Raises:
        ValueError: If a number is `NaN` or infinite.
        TypeError: If an answer type is unknown.
    """
    data: dict[str, object] = {}
    for field in fields(record):
        data[field.name] = _value(getattr(record, field.name))
    data["timestamp"] = record.timestamp.isoformat()
    data["questions"] = dict(record.questions)
    if record.answers is not None:
        data["answers"] = {key: _answer(item) for key, item in record.answers.items()}
    text = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return (text + "\n").encode("utf-8")


class JsonlAuditSink:
    """Thread-safe append-only JSON Lines file sink for audit records.

    The constructor opens the file, so a missing directory or a denied path
    raises there. A record error propagates to the caller; the HTTP adapters
    catch it and report `audit_error` on the `http.call` event. With `fsync`
    set, each write is flushed to storage before `record` returns. That
    blocks the event loop when the async adapter calls the sink.
    Source: https://docs.python.org/3/library/logging.handlers.html.

    Attributes:
        path (str): Filesystem path the sink appends to.
        fsync (bool): Whether each write is followed by `os.fsync`.

    Examples:
        ```python
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as folder:
            sink = JsonlAuditSink(Path(folder) / "audit.jsonl", fsync=True)
            sink.close()
            assert sink.fsync
        ```
    """

    def __init__(self, path: str | os.PathLike[str], *, fsync: bool = False) -> None:
        """Open the file for appending, creating it with mode `0o600`.

        Args:
            path: File to append to. Its directory must exist.
            fsync: Flush each line to storage before returning.

        Raises:
            FileNotFoundError: If the parent directory does not exist.
            OSError: If the file cannot be opened for appending.
        """
        self.path = os.fspath(path)
        self.fsync = fsync
        self._lock = threading.Lock()
        self._fd: int | None = os.open(self.path, _FLAGS, _MODE)

    def record(self, record: JudgmentRecord) -> None:
        """Append one record as one JSON line.

        Args:
            record: The record to append.

        Raises:
            ValueError: If the sink is closed, with the message
                `audit sink is closed`, or a number is not finite.
            OSError: If the write or the flush fails.
        """
        line = _encode_record(record)
        with self._lock:
            if self._fd is None:
                raise ValueError(_CLOSED)
            view = memoryview(line)
            while view:
                written = os.write(self._fd, view)
                view = view[written:]
            if self.fsync:
                os.fsync(self._fd)

    def close(self) -> None:
        """Close the file descriptor once; later calls do nothing."""
        with self._lock:
            if self._fd is not None:
                fd, self._fd = self._fd, None
                os.close(fd)

    def __enter__(self) -> Self:
        """Return the open sink.

        Returns:
            This sink.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the sink on leaving the block.

        Args:
            exc_type: Exception class raised in the block, if any.
            exc: Exception raised in the block, if any.
            traceback: Traceback of that exception, if any.
        """
        self.close()
