"""Audit record of one logical judgment call, written after the call ends.

A record says what came back from a call, never what was sent. It holds no
state, no instructions, no headers and no exception text. Those exclusions
follow the OWASP list of data a log must never hold.
Source: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html.
An opt-in keyed fingerprint links records of equal state without holding it.

The typed answers stay in the record. They are labels, booleans and
probabilities, not generated prose, and the record never carries the state
they were judged against. OpenTelemetry gates generated text behind an
opt-in; these answers are not generated text.
Source: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/.

Examples:
    ```python
    from datetime import UTC, datetime

    from judgevet.domain.answers import NoulAnswer
    from judgevet.domain.audit import JudgmentRecord
    from judgevet.domain.usage import Usage

    record = JudgmentRecord(
        timestamp=datetime.now(UTC),
        outcome="success",
        status_code=200,
        requested_model="jev-latest",
        resolved_model="jev-1.13.0",
        questions={"q1": "noul"},
        answers={"q1": NoulAnswer(noul=0.8)},
        usage=Usage(input_tokens=7, output_tokens=3),
    )
    assert record.schema_version == 1
    assert record.questions["q1"] == "noul"
    ```

See Also:
    - [judgevet.ports.AuditSink][]: Caller-owned destination for records.
    - [judgevet.adapters.outbound.http_events][]: Builds and writes one record per call.
    - [judgevet.domain.answers][]: Typed answers carried on success.
    - [judgevet.domain.usage][]: Token usage carried on success.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import MappingProxyType

from judgevet.domain.answers import Answer
from judgevet.domain.usage import Usage

OUTCOMES = frozenset({"success", "error", "cancelled"})
"""Closed set of terminal outcomes a record may carry."""


@dataclass(frozen=True)
class JudgmentRecord:
    """Frozen record of one logical call, with no state and no exception text.

    The timestamp comes from the client clock at the end of the call, in UTC.
    Source: https://github.com/OWASP/ASVS/blob/master/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md.
    The schema marker follows the CloudEvents `specversion` attribute.
    Source: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md.
    Field names follow the OpenTelemetry GenAI attributes where one exists.
    Source: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/.

    Attributes:
        timestamp (datetime): Timezone-aware UTC end time of the call.
        outcome (str): `success`, `error` or `cancelled`.
        requested_model (str): Effective requested model; OpenTelemetry
            `gen_ai.request.model`.
        questions (Mapping[str, str | None]): Question id to question type name.
            The type is None when a raw question carries no string type.
        error_type (str | None): Exception class name; OpenTelemetry `error.type`.
            None on success.
        status_code (int | None): Final attempt's HTTP status, or None when no
            response arrived.
        resolved_model (str | None): Model the service reported; OpenTelemetry
            `gen_ai.response.model`. None unless the call succeeded.
        answers (Mapping[str, Answer] | None): Typed answers on success, else None.
        usage (Usage | None): Token counts on success; OpenTelemetry
            `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`.
        request_id (str | None): Client-bound correlation identifier from
            `bind_request_id` (#63), or None outside a binding. No service
            response identifier is read, because none has been observed.
        schema_version (int): Record layout version, starting at 1.
        state_fingerprint (str | None): Lowercase hex HMAC-SHA-256, under the
            caller's `fingerprint_key`, of `b"judgevet-state-v1"`, a zero byte
            and the pre-redaction state as compact sorted-key UTF-8 JSON; None
            unless a key is configured.
            Source: https://arxiv.org/pdf/1802.07975.
            Source: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-108r1-upd1.pdf.

    Examples:
        ```python
        from datetime import UTC, datetime

        record = JudgmentRecord(
            timestamp=datetime.now(UTC),
            outcome="error",
            error_type="JevRequestError",
            status_code=422,
            requested_model="jev-latest",
            questions={"q1": "noul"},
        )
        assert record.answers is None
        ```

    See Also:
        - [judgevet.ports.AuditSink][]: Receives each record.
    """

    timestamp: datetime
    outcome: str
    requested_model: str
    questions: Mapping[str, str | None]
    error_type: str | None = None
    status_code: int | None = None
    resolved_model: str | None = None
    answers: Mapping[str, Answer] | None = None
    usage: Usage | None = None
    request_id: str | None = None
    schema_version: int = 1
    state_fingerprint: str | None = None

    def __post_init__(self) -> None:
        """Validate the outcome and timestamp and freeze both mappings.

        Raises:
            ValueError: If the outcome is unknown or the timestamp is not UTC.
        """
        if self.outcome not in OUTCOMES:
            raise ValueError("outcome must be success, error or cancelled")
        if self.timestamp.utcoffset() != timedelta(0):
            raise ValueError("timestamp must be timezone-aware UTC")
        object.__setattr__(self, "questions", MappingProxyType(dict(self.questions)))
        if self.answers is not None:
            object.__setattr__(self, "answers", MappingProxyType(dict(self.answers)))
