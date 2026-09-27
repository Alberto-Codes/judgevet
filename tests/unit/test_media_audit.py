"""Exercise explicit media fingerprints through existing public audit records."""

import hashlib
import hmac
import json
import struct
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from judgevet import (
    Choice,
    ChoiceAnswer,
    JevBudgetExceededError,
    JudgmentRecord,
    Noul,
    NoulAnswer,
    Score,
    SpendCap,
    Usage,
)
from judgevet.media import (
    ImageAttachment,
    ImageEvidence,
    MediaCapabilities,
    judge_with_images,
)
from judgevet.media_audit import MediaProvenance, media_provenance
from judgevet.testing import FakeSystemOnePort

KEY = b"synthetic-media-test-key"
QUESTIONS = {
    "claim": Noul(
        instructions={"prompt": ["PROMPT_CANARY", "/synthetic/PATH_CANARY"]},
        criteria={"custom": 17},
    ),
    "choice": Choice(
        criteria={"yes": "GOLD_LABEL_CANARY", "insufficient_evidence": "unclear"},
        instructions=["preserve order"],
    ),
}


def evidence() -> ImageEvidence:
    """Return opaque bytes with shared, differently ordered associations."""
    return ImageEvidence(
        [
            ImageAttachment("first", b"\x00IMAGE_CANARY_A\xff", "image/png"),
            ImageAttachment("second", b"\xffIMAGE_CANARY_B\x00", "image/jpeg"),
        ],
        {"claim": ["second", "first"], "choice": ["first"]},
        {"claim"},
    )


def oracle(label: bytes, parts: list[bytes], key: bytes = KEY) -> str:
    """Calculate the accepted framing independently of the production helper."""
    framed = b"".join(struct.pack(">Q", len(part)) + part for part in parts)
    return hmac.new(key, label + framed, hashlib.sha256).hexdigest()


def test_fingerprints_match_independent_framing() -> None:
    """Bind every image part, both orders and the normalized question snapshot."""
    submitted = evidence()
    result = media_provenance(submitted, QUESTIONS, fingerprint_key=KEY)
    first = [b"first", b"image/png", b"\x00IMAGE_CANARY_A\xff"]
    second = [b"second", b"image/jpeg", b"\xffIMAGE_CANARY_B\x00"]
    assert result.attachments == (
        ("first", oracle(b"judgevet-media-attachment-v1\0", first)),
        ("second", oracle(b"judgevet-media-attachment-v1\0", second)),
    )
    assert result.evidence_fingerprint == oracle(
        b"judgevet-media-evidence-v1\0",
        [
            *first,
            *second,
            b'{"choice":["first"],"claim":["second","first"]}',
            b'["claim"]',
        ],
    )
    raw = {
        "claim": {
            "type": "noul",
            "instructions": {"prompt": ["PROMPT_CANARY", "/synthetic/PATH_CANARY"]},
            "criteria": {"custom": 17},
        },
        "choice": {
            "type": "choice",
            "instructions": ["preserve order"],
            "criteria": {
                "yes": "GOLD_LABEL_CANARY",
                "insufficient_evidence": "unclear",
            },
        },
    }
    expected = json.dumps(
        raw, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    assert result.request_fingerprint == oracle(
        b"judgevet-media-request-v1\0", [expected]
    )
    assert dict(result.by_question) == {
        "claim": ("second", "first"),
        "choice": ("first",),
    }
    assert result.prompt_revision is None
    assert result.provider_identity is None
    assert result.preprocessing_revision is None


@pytest.mark.parametrize("change", ["bytes", "mime", "order", "binding", "required"])
def test_evidence_changes_are_detected(change: str) -> None:
    """Make evidence mutations visible without inventing changed question content."""
    original = evidence()
    images = list(original.images)
    bindings = dict(original.by_question)
    required = original.required
    if change == "bytes":
        images[0] = ImageAttachment("first", b"different", "image/png")
    elif change == "mime":
        images[0] = ImageAttachment("first", images[0].data, "image/webp")
    elif change == "order":
        images.reverse()
    elif change == "binding":
        bindings["claim"] = ("first", "second")
    else:
        required = frozenset()
    before = media_provenance(original, QUESTIONS, fingerprint_key=KEY)
    after = media_provenance(
        ImageEvidence(images, bindings, required), QUESTIONS, fingerprint_key=KEY
    )
    assert after.evidence_fingerprint != before.evidence_fingerprint
    assert after.request_fingerprint == before.request_fingerprint


def test_question_snapshot_and_key_are_independent_inputs() -> None:
    """Detect prompt changes and key rotation while keeping equal images stable."""
    submitted = evidence()
    first = media_provenance(submitted, QUESTIONS, fingerprint_key=KEY)
    again = media_provenance(submitted, QUESTIONS, fingerprint_key=KEY)
    changed = dict(QUESTIONS)
    changed["claim"] = Noul(instructions="different prompt", criteria={"custom": 17})
    prompt = media_provenance(submitted, changed, fingerprint_key=KEY)
    rotated = media_provenance(
        submitted, QUESTIONS, fingerprint_key=b"different-synthetic-key"
    )
    assert again == first
    assert prompt.request_fingerprint != first.request_fingerprint
    assert prompt.attachments == first.attachments
    assert prompt.evidence_fingerprint == first.evidence_fingerprint
    assert rotated.attachments != first.attachments
    assert rotated.evidence_fingerprint != first.evidence_fingerprint
    assert rotated.request_fingerprint != first.request_fingerprint


@pytest.mark.parametrize("field", ["attachments", "by_question"])
def test_opt_in_record_contains_only_declared_metadata_and_digests(field: str) -> None:
    """Keep raw content and keys out of the record and leave defaults absent."""
    plain = JudgmentRecord(datetime.now(UTC), "success", "requested", {"claim": "noul"})
    assert plain.media_provenance is None
    provenance = media_provenance(
        evidence(),
        QUESTIONS,
        fingerprint_key=KEY,
        prompt_revision="r1",
        provider_identity="fixture",
        preprocessing_revision="p2",
    )
    record = replace(
        plain, media_provenance=provenance, resolved_model="reported-model"
    )
    assert record.schema_version == 1
    assert record.resolved_model == "reported-model"
    assert record.media_provenance is provenance
    assert (
        provenance.prompt_revision,
        provenance.provider_identity,
        provenance.preprocessing_revision,
    ) == ("r1", "fixture", "p2")
    for sentinel in [
        "IMAGE_CANARY",
        "PROMPT_CANARY",
        "PATH_CANARY",
        "GOLD_LABEL_CANARY",
        KEY.decode(),
    ]:
        assert sentinel not in repr(record)
    with pytest.raises((AttributeError, TypeError)):
        setattr(provenance, field, ())
    assert getattr(provenance, field) == getattr(
        media_provenance(evidence(), QUESTIONS, fingerprint_key=KEY), field
    )


class Sink:
    """Record terminal calls or exercise existing sink-failure containment."""

    def __init__(self, *, fail: bool = False) -> None:
        """Select successful recording or a synthetic sink failure."""
        self.records: list[JudgmentRecord] = []
        self.attempts = 0
        self.fail = fail

    def record(self, record: JudgmentRecord) -> None:
        self.attempts += 1
        if self.fail:
            raise RuntimeError("SINK_FAILURE_CANARY")
        self.records.append(record)


class EnrichedSink:
    """Attach provenance without adding another terminal event or accounting path."""

    def __init__(self, sink: Sink, provenance: MediaProvenance) -> None:
        """Bind an immutable provenance value to the existing sink."""
        self.sink = sink
        self.provenance = provenance

    def record(self, record: JudgmentRecord) -> None:
        self.sink.record(replace(record, media_provenance=self.provenance))


class AuditedMediaProvider:
    """Use the existing fake backend's audit and cap after a simulated retry."""

    def __init__(self, sink: Sink, cap: SpendCap, tokens: int | None = None) -> None:
        """Retain existing accounting and terminal-record collaborators."""
        self.sink = sink
        self.cap = cap
        self.tokens = tokens
        self.calls: list[ImageEvidence] = []
        self.provenance: MediaProvenance | None = None

    def capabilities(self, model: str) -> MediaCapabilities:
        return MediaCapabilities({"image/png", "image/jpeg"})

    def system_one(self, state, questions, model):
        pytest.fail("media request converted to text")

    def system_one_media(self, state, questions, model, *, evidence: ImageEvidence):
        self.calls.append(evidence)
        self.provenance = media_provenance(evidence, questions, fingerprint_key=KEY)
        backend = FakeSystemOnePort(
            answers={
                "claim": NoulAnswer(0.9),
                "choice": ChoiceAnswer("yes", 1, {"yes": 1}),
            },
            usage=Usage(self.tokens, None),
            spend_cap=self.cap,
            audit=EnrichedSink(self.sink, self.provenance),
        )
        self.cap.claim()  # Application-owned failed physical attempt before retry.
        return backend.system_one(state, questions, model)


@pytest.mark.parametrize("tokens", [None, 0, 7])
def test_existing_audit_and_spend_contract_survives_provenance(
    tokens: int | None,
) -> None:
    """Keep one logical record and count simulated physical attempts explicitly."""
    sink = Sink()
    cap = SpendCap(max_attempts=2)
    provider = AuditedMediaProvider(sink, cap, tokens)
    submitted = evidence()
    response = judge_with_images(
        provider, "text", QUESTIONS, "selected", evidence=submitted
    )
    assert provider.calls == [submitted]
    assert cap.attempts == 2
    assert cap.input_tokens == (0 if tokens is None else tokens)
    assert len(sink.records) == 1
    assert sink.records[0].media_provenance is provider.provenance
    assert sink.records[0].usage == Usage(tokens, None)
    assert sink.records[0].resolved_model == response.model
    assert sink.records[0].outcome == "success"


def test_sink_failure_does_not_replace_success() -> None:
    """Reuse the existing audit sink containment contract with enriched records."""
    sink = Sink(fail=True)
    provider = AuditedMediaProvider(sink, SpendCap(max_attempts=2))
    response = judge_with_images(
        provider, "text", QUESTIONS, "selected", evidence=evidence()
    )
    assert sink.attempts == 1
    assert sink.records == []
    assert isinstance(response.answers["claim"], NoulAnswer)


def test_retry_budget_failure_keeps_one_terminal_record() -> None:
    """Keep a rejected retry distinct from a judgment or invented usage."""
    sink = Sink()
    cap = SpendCap(max_attempts=1)
    provider = AuditedMediaProvider(sink, cap)
    with pytest.raises(JevBudgetExceededError):
        judge_with_images(provider, "text", QUESTIONS, "selected", evidence=evidence())
    assert cap.attempts == 1
    assert cap.input_tokens == 0
    assert len(sink.records) == 1
    assert sink.records[0].outcome == "error"
    assert sink.records[0].usage is None
    assert sink.records[0].resolved_model is None
    assert sink.records[0].media_provenance is provider.provenance


@pytest.mark.parametrize("field", ["attachments", "by_question"])
def test_provenance_constructor_freezes_caller_collections(field: str) -> None:
    """Prevent aliases from changing a recorded attachment order or association."""
    original = media_provenance(evidence(), QUESTIONS, fingerprint_key=KEY)
    attachments = list(original.attachments)
    bindings = {name: list(refs) for name, refs in original.by_question.items()}
    frozen = MediaProvenance(
        attachments=attachments,
        by_question=bindings,
        evidence_fingerprint=original.evidence_fingerprint,
        request_fingerprint=original.request_fingerprint,
    )
    attachments.reverse()
    bindings["claim"].reverse()
    bindings.clear()
    assert frozen.attachments == original.attachments
    assert dict(frozen.by_question) == dict(original.by_question)
    with pytest.raises((AttributeError, TypeError)):
        setattr(frozen, field, {})
    assert frozen.attachments == original.attachments
    assert dict(frozen.by_question) == dict(original.by_question)


def test_equivalent_raw_optional_fields_have_same_request_fingerprint() -> None:
    """Normalize absent optional fields without discarding actual content."""
    submitted = ImageEvidence([evidence().images[0]], {"claim": ["first"]})
    typed = media_provenance(submitted, {"claim": Noul()}, fingerprint_key=KEY)
    raw = media_provenance(submitted, {"claim": {"type": "noul"}}, fingerprint_key=KEY)
    assert typed == raw
    with pytest.raises((TypeError, ValueError)):
        media_provenance(
            submitted,
            {"claim": {"type": "noul", "extra": "must-not-drop"}},
            fingerprint_key=KEY,
        )


def test_fingerprints_require_an_explicit_nonempty_key() -> None:
    """Avoid a default unkeyed linkage mechanism."""
    with pytest.raises(ValueError):
        media_provenance(evidence(), QUESTIONS, fingerprint_key=b"")


@pytest.mark.parametrize(
    ("defect", "metadata"),
    [
        ("pair", None),
        ("duplicate", None),
        ("digest", None),
        ("unknown", None),
        ("unbound", None),
        ("refs", None),
        ("metadata", b"CANARY"),
    ],
)
def test_invalid_provenance_shapes_are_rejected(defect: str, metadata: Any) -> None:
    """Reject malformed or ambiguous provenance without exposing caller values."""
    attachments = [("a", "a" * 64)]
    bindings = {"q": ["a"]}
    if defect == "pair":
        attachments = [("a", "CANARY")]
    elif defect == "duplicate":
        attachments *= 2
    elif defect == "digest":
        attachments = [("a", "A" * 64)]
    elif defect == "unknown":
        bindings = {"q": ["CANARY"]}
    elif defect == "unbound":
        bindings = {}
    elif defect == "refs":
        bindings = {"q": ["a", "a"]}
    else:
        assert metadata == b"CANARY"
    with pytest.raises((TypeError, ValueError)) as caught:
        MediaProvenance(
            attachments, bindings, "b" * 64, "c" * 64, provider_identity=metadata
        )
    assert "CANARY" not in str(caught.value)


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), b"CONTENT_CANARY", {1: "CONTENT_CANARY"}, "\ud800"],
)
def test_invalid_question_json_has_safe_errors(value: Any) -> None:
    """Reject non-JSON content instead of silently changing the fingerprint input."""
    with pytest.raises((TypeError, ValueError)) as caught:
        media_provenance(
            evidence(), {"q": Noul(criteria={"custom": value})}, fingerprint_key=KEY
        )
    assert "CONTENT_CANARY" not in str(caught.value)
    assert KEY.decode() not in str(caught.value)


def test_empty_choice_label_and_score_normalize_without_content_loss() -> None:
    """Keep supported empty labels and ordered score criteria in canonical JSON."""
    typed = {
        "choice": Choice(criteria={"": "empty label"}),
        "score": Score(criteria=["low", "high"]),
    }
    raw = {
        "choice": {"type": "choice", "criteria": {"": "empty label"}},
        "score": {"type": "score", "criteria": ["low", "high"]},
    }
    assert media_provenance(evidence(), typed, fingerprint_key=KEY) == media_provenance(
        evidence(), raw, fingerprint_key=KEY
    )


def test_provenance_mappings_are_immutable() -> None:
    """Expose detached tuples and a mapping that has no mutation operation."""
    value = media_provenance(evidence(), QUESTIONS, fingerprint_key=KEY)
    assert isinstance(value.attachments, tuple)
    assert all(isinstance(pair, tuple) for pair in value.attachments)
    assert all(isinstance(refs, tuple) for refs in value.by_question.values())
    assert not hasattr(value.by_question, "__setitem__")


@pytest.mark.parametrize("key", [None, "KEY_CANARY", bytearray(b"KEY_CANARY")])
def test_key_type_is_explicit_and_errors_are_safe(key: Any) -> None:
    """Reject implicit key conversions without echoing supplied secret values."""
    with pytest.raises(TypeError) as caught:
        media_provenance(evidence(), QUESTIONS, fingerprint_key=key)
    assert "KEY_CANARY" not in str(caught.value)


@pytest.mark.parametrize("pairs", [None, "CANARY", [("a",)], [("a", "b", "CANARY")]])
def test_attachment_pair_shapes_are_checked(pairs: Any) -> None:
    """Reject malformed pair containers without unpacking arbitrary content."""
    with pytest.raises((TypeError, ValueError)) as caught:
        MediaProvenance(pairs, {}, "a" * 64, "b" * 64)
    assert "CANARY" not in str(caught.value)
