"""An application-owned provider fixture for the installed provider proof (#205).

The application keeps its own question and finding classes and translates them
into public judgevet types. The recording provider observes exact calls and
answers deterministically from what it received, so a dropped image, a changed
binding or an ignored selection changes the observed result. Events go to an
optional JSON-lines file named by ``PROVIDER_FIXTURE_EVENTS``, never to
protocol output. Nothing here performs inference or network access. The
runner starts every child through the network-guarding bootstrap; importing
this module installs no guard.
"""

import json
import os
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from judgevet import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
    SystemOneResponse,
    Usage,
)
from judgevet.media import ImageAttachment, ImageEvidence, MediaCapabilities
from judgevet.providers import ProviderTransportError, ProviderUnavailableError

EVENTS_VARIABLE = "PROVIDER_FIXTURE_EVENTS"
ORIGINS_VARIABLE = "PROVIDER_FIXTURE_ORIGINS"
BOOTSTRAP = "provider_artifact_check.py"
REQUESTED_MODEL = "app-model"
STATE = {"claim": "Invoice 7 was paid", "ticket": 7}
PNG = b"\x89PNG\r\n\x1a\nfixture-page-1"
JPEG = b"\xff\xd8\xfffixture-page-2"
IMAGES = (("page-1", PNG, "image/png"), ("page-2", JPEG, "image/jpeg"))
BINDINGS = {"support": ("page-2", "page-1"), "legible": ("page-1",)}
POLICY = {
    "rules": [
        {
            "question": "support",
            "pass": {"choice": "supported", "confidence": {"min": 0.8}},
        },
        {"question": "legible", "pass": {"noul": {"min": 0.9}}},
    ]
}
_TEXT_USAGE = Usage(input_tokens=17, output_tokens=5)
_EVENTS: list[dict[str, Any]] = []


@dataclass(frozen=True)
class ReviewQuestion:
    """One application review question, independent of judgevet types.

    Attributes:
        key: Application question identity.
        prompt: Instructions shown to the provider.
        outcomes: Declared outcomes; empty for a yes-or-no likelihood.
        graded: Whether the outcomes are an ordered grade.
    """

    key: str
    prompt: str
    outcomes: tuple[str, ...] = ()
    graded: bool = False


@dataclass(frozen=True)
class ReviewFinding:
    """One application finding translated back from a judgevet answer.

    Attributes:
        key: Application question identity.
        outcome: Selected outcome, grade or ``likely``/``unlikely``.
        strength: Confidence, grade position or likelihood.
    """

    key: str
    outcome: str
    strength: float


REVIEW = (
    ReviewQuestion(
        "support",
        "Does the attached page support the claim?",
        ("supported", "contradicted", "insufficient_evidence"),
    ),
    ReviewQuestion("legible", "Is the attached page legible?"),
    ReviewQuestion("quality", "Rate the scan quality.", ("poor", "fair", "good"), True),
)


def to_questions(review: Sequence[ReviewQuestion]) -> dict[str, Question]:
    """Translate application questions into public judgevet questions.

    Args:
        review: Application questions in order.

    Returns:
        Typed judgevet questions keyed by application identity.
    """
    result: dict[str, Question] = {}
    for item in review:
        if item.graded:
            result[item.key] = Score(
                criteria=list(item.outcomes), instructions=item.prompt
            )
        elif item.outcomes:
            criteria = {name: name.replace("_", " ") for name in item.outcomes}
            result[item.key] = Choice(criteria=criteria, instructions=item.prompt)
        else:
            result[item.key] = Noul(instructions=item.prompt)
    return result


def to_findings(response: SystemOneResponse) -> list[list[Any]]:
    """Translate typed answers back into application findings.

    Args:
        response: Typed judgevet response.

    Returns:
        ``[key, outcome, strength]`` lists in application question order.
    """
    findings = []
    for item in REVIEW:
        answer = response.answers[item.key]
        if isinstance(answer, ChoiceAnswer):
            finding = ReviewFinding(item.key, answer.choice, answer.confidence)
        elif isinstance(answer, ScoreAnswer):
            grade = item.outcomes[round(answer.score * (len(item.outcomes) - 1))]
            finding = ReviewFinding(item.key, grade, answer.score)
        else:
            outcome = "likely" if answer.noul >= 0.5 else "unlikely"
            finding = ReviewFinding(item.key, outcome, answer.noul)
        findings.append([finding.key, finding.outcome, finding.strength])
    return findings


def evidence(
    bindings: Mapping[str, Sequence[str]] = BINDINGS,
    images: Sequence[tuple[str, bytes, str]] = IMAGES,
    required: Sequence[str] = ("support",),
) -> ImageEvidence:
    """Build the fixture's ordered image evidence.

    Args:
        bindings: Question identities mapped to ordered attachment identities.
        images: ``(id, bytes, media type)`` triples in global order.
        required: Questions that must carry evidence.

    Returns:
        Immutable evidence snapshot.
    """
    attachments = [ImageAttachment(name, data, kind) for name, data, kind in images]
    return ImageEvidence(attachments, bindings, required)


def record(event: dict[str, Any]) -> None:
    """Record one fixture event in memory and in the optional events file.

    Args:
        event: JSON-serializable event.
    """
    _EVENTS.append(event)
    path = os.environ.get(EVENTS_VARIABLE)
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")


def drain() -> list[dict[str, Any]]:
    """Return and clear in-memory events.

    Returns:
        Events recorded since the last drain.
    """
    events = list(_EVENTS)
    _EVENTS.clear()
    return events


def describe(questions: Mapping[str, Question | Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize question identities, variants, instructions and criteria.

    Args:
        questions: Questions exactly as the provider received them.

    Returns:
        ``{id: [type, instructions, criteria]}`` in received order.
    """
    result = {}
    for name, question in questions.items():
        if isinstance(question, Mapping):
            fields = [question.get("type"), question.get("instructions")]
            result[name] = [*fields, question.get("criteria")]
            continue
        kind = type(question).__name__.lower()
        criteria = question.criteria
        result[name] = [kind, question.instructions, criteria]
    return json.loads(json.dumps(result))


def _answers(bound: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """Answer deterministically from which questions carry images.

    Args:
        bound: Question identities mapped to their received attachment IDs.

    Returns:
        Typed answers for the three fixture questions.
    """
    supported = bool(bound.get("support"))
    choice = "supported" if supported else "insufficient_evidence"
    probabilities = {
        "supported": 0.1,
        "contradicted": 0.1,
        "insufficient_evidence": 0.8,
    }
    if supported:
        probabilities = {"supported": 0.9, "contradicted": 0.05}
        probabilities["insufficient_evidence"] = 0.05
    grade = 1.0 if bound.get("quality") else 0.5
    return {
        "support": ChoiceAnswer(choice, probabilities[choice], probabilities),
        "legible": NoulAnswer(0.95 if bound.get("legible") else 0.25),
        "quality": ScoreAnswer(
            score=grade,
            confidence=0.6,
            legend={0: "poor", 1: "fair", 2: "good"},
            probabilities={0: 0.2, 1: 0.6, 2: 0.2},
        ),
    }


class RecordingProvider:
    """Observe exact calls and answer from the received inputs.

    Attributes:
        name: Provider identity reported in the resolved model.
        image_types: Declared media types for capability checks.
        fail: Whether every judgment raises a transport failure.
        calls: Summaries of every received call.
        closed: Number of close calls.
    """

    def __init__(
        self,
        name: str,
        *,
        image_types: Sequence[str] = ("image/png", "image/jpeg"),
        fail: bool = False,
    ) -> None:
        """Create an open provider.

        Args:
            name: Provider identity.
            image_types: Declared media types.
            fail: Raise a transport failure from every judgment.
        """
        self.name = name
        self.image_types = tuple(image_types)
        self.fail = fail
        self.calls: list[dict[str, Any]] = []
        self.closed = 0

    def _observe(
        self,
        operation: str,
        state: Any,
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        media: ImageEvidence | None,
    ) -> dict[str, Any]:
        """Record one call and raise the configured failure.

        Args:
            operation: ``text`` or ``media``.
            state: Received state.
            questions: Received questions.
            model: Received model.
            media: Received evidence, if any.

        Returns:
            Received bindings for answer selection.

        Raises:
            ProviderTransportError: The provider is configured to fail.
        """
        images = [] if media is None else media.images
        bindings = (
            {} if media is None else {k: list(v) for k, v in media.by_question.items()}
        )
        call = {
            "provider": self.name,
            "operation": operation,
            "state": state,
            "questions": describe(questions),
            "model": model,
            "images": [[i.id, i.media_type, i.data.hex()] for i in images],
            "bindings": bindings,
        }
        self.calls.append(call)
        record({"event": "call", **call})
        if self.fail:
            raise ProviderTransportError("fixture transport failure")
        return bindings

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str = "jev-latest",
    ) -> SystemOneResponse:
        """Answer a text call with known usage.

        Args:
            state: Received state.
            questions: Received questions.
            model: Received model.

        Returns:
            Deterministic typed answers.
        """
        bound = self._observe("text", state, questions, model, None)
        return SystemOneResponse(f"{model}@{self.name}", _TEXT_USAGE, _answers(bound))

    def capabilities(self, model: str) -> MediaCapabilities:
        """Declare static media support.

        Args:
            model: Requested model.

        Returns:
            Declared media types.
        """
        return MediaCapabilities(self.image_types)

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Answer a media call with unknown usage.

        Args:
            state: Received state.
            questions: Received questions.
            model: Received model.
            evidence: Received ordered evidence.

        Returns:
            Deterministic typed answers.
        """
        bound = self._observe("media", state, questions, model, evidence)
        return SystemOneResponse(f"{model}@{self.name}", Usage(), _answers(bound))

    def close(self) -> None:
        """Record provider cleanup."""
        self.closed += 1
        record({"event": "close", "provider": self.name})


class TextOnlyProvider:
    """A provider without media support.

    Attributes:
        inner: Recording text provider.
    """

    def __init__(self, name: str) -> None:
        """Create a text-only provider.

        Args:
            name: Provider identity.
        """
        self.inner = RecordingProvider(name)

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str = "jev-latest",
    ) -> SystemOneResponse:
        """Answer a text call.

        Args:
            state: Received state.
            questions: Received questions.
            model: Received model.

        Returns:
            Deterministic typed answers.
        """
        return self.inner.system_one(state, questions, model)


@contextmanager
def owned(name: str, *, fail: bool = False) -> Iterator[RecordingProvider]:
    """Acquire and close one provider the application owns.

    Args:
        name: Provider identity.
        fail: Raise a transport failure from every judgment.

    Yields:
        The acquired provider.
    """
    record({"event": "acquire", "provider": name})
    provider = RecordingProvider(name, fail=fail)
    try:
        yield provider
    finally:
        provider.close()


@contextmanager
def failing_setup(name: str) -> Iterator[RecordingProvider]:
    """Roll back a partial acquisition and report the provider unavailable.

    Args:
        name: Provider identity.

    Yields:
        Nothing; acquisition always fails.

    Raises:
        ProviderUnavailableError: Always, after rollback.
    """
    record({"event": "acquire", "provider": name})
    record({"event": "rollback", "provider": name})
    raise ProviderUnavailableError("fixture setup failed")
    yield RecordingProvider(name)


@contextmanager
def invalid_port(name: str) -> Iterator[Any]:
    """Yield an object without a judgment method and record cleanup.

    Args:
        name: Provider identity.

    Yields:
        An object that is not a judgment port.
    """
    record({"event": "acquire", "provider": name})
    try:
        yield object()
    finally:
        record({"event": "close", "provider": name})
