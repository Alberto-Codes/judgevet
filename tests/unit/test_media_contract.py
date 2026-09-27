"""Exercise immutable evidence and the public media dispatch boundary offline.

Examples:
    Run the focused pytest module from the repository root.

See Also:
    - [judgevet.media][]: Public media contract.
"""

from collections.abc import Mapping
from typing import Any

import pytest

from judgevet import (
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    SystemOneResponse,
    Usage,
)
from judgevet.media import (
    ImageAttachment,
    ImageEvidence,
    MediaCapabilities,
    MissingEvidenceError,
    judge_with_images,
)
from judgevet.policy import ChoiceRule, Policy, evaluate_policy, validate_policy
from judgevet.providers import (
    ProviderCapabilityError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTransportError,
)

FIRST = ImageAttachment("first", b"opaque-encoded-image-A", "image/png")
SECOND = ImageAttachment("second", b"opaque-encoded-image-B", "image/png")
QUESTIONS = {
    "claim": Noul(instructions={"rule": "check exact evidence"}),
    "decision": Choice(
        criteria={"yes": "supported", "insufficient_evidence": "insufficient"},
        instructions=["preserve attachment order"],
    ),
}


def evidence() -> ImageEvidence:
    """Use shared images with different global and question-specific orders.

    Returns:
        The offline fixture value.
    """
    return ImageEvidence(
        [FIRST, SECOND],
        {"claim": ["second", "first"], "decision": ["first"]},
        {"claim"},
    )


class RecordingMediaProvider:
    """Record capability lookup, exact media submission and text fallback.

    Attributes:
        calls (list): Captured media calls.
        models (list[str]): Capability lookups.
        text_calls (int): Text dispatch count.
        fail (bool): Inject transport failure.
        response (SystemOneResponse): Returned fixture.

    Examples:
        Exercise this offline fixture through the tests in this module.
    """

    def __init__(self, *, fail: bool = False, insufficient: bool = False) -> None:
        """Initialize the repository-owned offline fixture."""
        self.calls: list[tuple[object, object, str, ImageEvidence]] = []
        self.models: list[str] = []
        self.text_calls = 0
        self.fail = fail
        self.response = SystemOneResponse(
            model="fixture-resolved",
            usage=Usage(0, None),
            answers={
                "claim": NoulAnswer(0.9),
                "decision": ChoiceAnswer(
                    "insufficient_evidence" if insufficient else "yes",
                    0.8,
                    {"yes": 0.2, "insufficient_evidence": 0.8}
                    if insufficient
                    else {"yes": 0.8, "insufficient_evidence": 0.2},
                ),
            },
        )

    def capabilities(self, model: str) -> MediaCapabilities:
        """Return a static declaration without acquisition or inference.

        Returns:
            The offline fixture value.
        """
        self.models.append(model)
        return MediaCapabilities({"image/png"}, 16, 8 * 1024 * 1024, 32 * 1024 * 1024)

    def system_one(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
    ) -> SystemOneResponse:
        """Keep the existing text route observable.

        Returns:
            The offline fixture value.
        """
        self.text_calls += 1
        return self.response

    def system_one_media(
        self,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, Question | Mapping[str, Any]],
        model: str,
        *,
        evidence: ImageEvidence,
    ) -> SystemOneResponse:
        """Record exact inputs and return typed answers or declared failure.

        Returns:
            The offline fixture value.

        Raises:
            ProviderTransportError: The fixture injects a transport failure.
        """
        self.calls.append((state, questions, model, evidence))
        if self.fail:
            raise ProviderTransportError("fixture transport failed")
        return self.response


def test_exact_media_request_and_response() -> None:
    """Preserve bytes, both orders, bindings, question values, model and usage."""
    provider = RecordingMediaProvider()
    submitted = evidence()
    state = {"record": ["exact", "state"]}
    response = judge_with_images(
        provider, state, QUESTIONS, "fixture-selected", evidence=submitted
    )
    assert response is provider.response
    assert response.model == "fixture-resolved"
    assert response.usage == Usage(0, None)
    assert provider.models == ["fixture-selected"]
    assert provider.text_calls == 0
    assert len(provider.calls) == 1
    seen_state, seen_questions, model, seen = provider.calls[0]
    assert seen_state == state
    assert seen_questions == QUESTIONS
    assert model == "fixture-selected"
    assert [(i.id, i.data, i.media_type) for i in seen.images] == [
        ("first", b"opaque-encoded-image-A", "image/png"),
        ("second", b"opaque-encoded-image-B", "image/png"),
    ]
    assert dict(seen.by_question) == {
        "claim": ("second", "first"),
        "decision": ("first",),
    }
    assert seen.required == frozenset({"claim"})


def test_evidence_defensive_snapshots() -> None:
    """Prevent caller aliases from changing attachment and binding order."""
    images = [FIRST, SECOND]
    names = ["second", "first"]
    bindings = {"claim": names}
    required = {"claim"}
    submitted = ImageEvidence(images, bindings, required)
    images.clear()
    names.reverse()
    bindings.clear()
    required.clear()
    assert submitted.images == (FIRST, SECOND)
    assert dict(submitted.by_question) == {"claim": ("second", "first")}
    assert submitted.required == frozenset({"claim"})
    with pytest.raises((AttributeError, TypeError)):
        submitted.__setattr__("images", ())


def test_empty_optional_evidence_keeps_text_route() -> None:
    """Avoid capability lookup or media calls for valid empty evidence."""
    provider = RecordingMediaProvider()
    result = judge_with_images(
        provider, "text", QUESTIONS, "selected", evidence=ImageEvidence([], {})
    )
    assert result is provider.response
    assert provider.text_calls == 1
    assert provider.models == []
    assert provider.calls == []


def test_missing_required_evidence_never_dispatches() -> None:
    """Keep missing evidence distinct from unsupported capability and transport."""
    provider = RecordingMediaProvider()
    submitted = ImageEvidence([], {}, {"claim"})
    with pytest.raises(MissingEvidenceError):
        judge_with_images(provider, "text", QUESTIONS, "selected", evidence=submitted)
    assert provider.text_calls == 0
    assert provider.models == []
    assert provider.calls == []


def test_text_only_port_rejects_media() -> None:
    """Never convert images to text or silently drop them for a text-only port."""

    class TextOnly:
        """Declare an offline provider variant.

        Examples:
            Exercise this offline fixture through the tests in this module.
        """

        def system_one(self, state, questions, model) -> SystemOneResponse:
            """Exercise the selected offline operation."""
            pytest.fail("unsupported evidence dispatched as text")

    with pytest.raises(ProviderCapabilityError):
        judge_with_images(
            TextOnly(), "text", QUESTIONS, "selected", evidence=evidence()
        )


def test_declared_transport_error_is_not_abstention() -> None:
    """Retain the transport error class without creating a semantic answer."""
    provider = RecordingMediaProvider(fail=True)
    with pytest.raises(ProviderTransportError, match="fixture transport failed"):
        judge_with_images(provider, "text", QUESTIONS, "selected", evidence=evidence())
    assert len(provider.calls) == 1
    assert provider.text_calls == 0


def test_explicit_insufficient_evidence_is_an_unmet_policy() -> None:
    """Treat an explicit abstention criterion as a successful typed Choice answer."""
    provider = RecordingMediaProvider(insufficient=True)
    response = judge_with_images(
        provider, "text", QUESTIONS, "selected", evidence=evidence()
    )
    answer = response.answers["decision"]
    assert isinstance(answer, ChoiceAnswer)
    assert answer.choice == "insufficient_evidence"
    policy = validate_policy(Policy((ChoiceRule("decision", "yes"),)), QUESTIONS)
    assert not evaluate_policy(policy, response.answers).passed


@pytest.mark.parametrize(
    "defect", ["missing", "extra", "variant", "choice", "probability"]
)
def test_invalid_media_response_is_provider_error(defect: str) -> None:
    """Require exact answer identities, variants and declared Choice options."""
    provider = RecordingMediaProvider()
    if defect == "missing":
        provider.response.answers.pop("claim")
    elif defect == "extra":
        provider.response.answers["extra"] = NoulAnswer(0.9)
    elif defect == "variant":
        provider.response.answers["claim"] = ChoiceAnswer("yes", 1, {"yes": 1})
    elif defect == "choice":
        provider.response.answers["decision"] = ChoiceAnswer(
            "unknown", 1, {"unknown": 1}
        )
    else:
        answer = ChoiceAnswer("yes", 1, {"yes": 1})
        answer.probabilities["unknown"] = 0
        provider.response.answers["decision"] = answer
    with pytest.raises(ProviderResponseError):
        judge_with_images(provider, "text", QUESTIONS, "selected", evidence=evidence())


@pytest.mark.parametrize("case", ["duplicate", "unknown", "repeated", "unused"])
def test_invalid_association_structure_is_rejected(case: str) -> None:
    """Reject ambiguous or unbound attachments at construction."""
    with pytest.raises(ValueError):
        if case == "duplicate":
            ImageEvidence([FIRST, FIRST], {"claim": ["first"]})
        elif case == "unknown":
            ImageEvidence([FIRST], {"claim": ["absent"]})
        elif case == "repeated":
            ImageEvidence([FIRST], {"claim": ["first", "first"]})
        else:
            ImageEvidence([FIRST, SECOND], {"claim": ["first"]})


@pytest.mark.parametrize("required", [False, True])
def test_unknown_question_reference_never_reaches_provider(required: bool) -> None:
    """Reject unknown association and required IDs before capability lookup."""
    submitted = (
        ImageEvidence([], {}, {"absent"})
        if required
        else ImageEvidence([FIRST], {"absent": ["first"]})
    )
    provider = RecordingMediaProvider()
    with pytest.raises(ProviderRequestError):
        judge_with_images(provider, "text", QUESTIONS, "selected", evidence=submitted)
    assert provider.models == []
    assert provider.calls == []
    assert provider.text_calls == 0


@pytest.mark.parametrize("bound", ["mime", "count", "individual", "total"])
def test_provider_limits_reject_before_inference(bound: str) -> None:
    """Honor each model-specific limit without a text fallback."""
    declarations = {
        "mime": MediaCapabilities({"image/jpeg"}),
        "count": MediaCapabilities({"image/png"}, 1),
        "individual": MediaCapabilities({"image/png"}, max_image_bytes=1),
        "total": MediaCapabilities({"image/png"}, max_total_bytes=len(FIRST.data)),
    }

    class LimitedProvider(RecordingMediaProvider):
        """Declare an offline provider variant.

        Examples:
            Exercise this offline fixture through the tests in this module.
        """

        def capabilities(self, model: str) -> MediaCapabilities:
            """Exercise the selected offline operation.

            Returns:
                Static fixture capabilities.
            """
            self.models.append(model)
            return declarations[bound]

    provider = LimitedProvider()
    with pytest.raises(ProviderCapabilityError):
        judge_with_images(provider, "text", QUESTIONS, "selected", evidence=evidence())
    assert provider.models == ["selected"]
    assert provider.calls == []
    assert provider.text_calls == 0


@pytest.mark.parametrize("bound", ["mime", "count", "individual", "total"])
def test_provider_cannot_relax_local_ceilings(bound: str) -> None:
    """Enforce the local media contract even for a permissive provider."""

    class PermissiveProvider(RecordingMediaProvider):
        """Declare an offline provider variant.

        Examples:
            Exercise this offline fixture through the tests in this module.
        """

        def capabilities(self, model: str) -> MediaCapabilities:
            """Exercise the selected offline operation.

            Returns:
                Static fixture capabilities.
            """
            self.models.append(model)
            return MediaCapabilities(
                {"image/png", "image/gif"}, 100, 64 * 1024 * 1024, 128 * 1024 * 1024
            )

    if bound == "mime":
        images = [ImageAttachment("bad", b"gif", "image/gif")]
    elif bound == "count":
        images = [
            ImageAttachment(str(index), b"data", "image/png") for index in range(17)
        ]
    elif bound == "individual":
        images = [ImageAttachment("big", b"x" * (8 * 1024 * 1024 + 1), "image/png")]
    else:
        images = [
            ImageAttachment(str(index), b"x" * (8 * 1024 * 1024), "image/png")
            for index in range(5)
        ]
    submitted = ImageEvidence(images, {"claim": [item.id for item in images]})
    provider = PermissiveProvider()
    with pytest.raises(ProviderCapabilityError):
        judge_with_images(provider, "text", QUESTIONS, "selected", evidence=submitted)
    assert provider.calls == []
    assert provider.text_calls == 0


@pytest.mark.parametrize(
    "kind", ["unknown", "empty-choice", "empty-score", "extra-field"]
)
def test_invalid_raw_question_never_reaches_inference(kind: str) -> None:
    """Reject malformed media question definitions rather than discarding fields."""
    definitions: dict[str, Mapping[str, Any]] = {
        "unknown": {"type": "other"},
        "empty-choice": {"type": "choice", "criteria": {}},
        "empty-score": {"type": "score", "criteria": []},
        "extra-field": {"type": "noul", "unsupported": "must-not-drop"},
    }
    provider = RecordingMediaProvider()
    with pytest.raises(ProviderRequestError):
        judge_with_images(
            provider,
            "text",
            {"claim": definitions[kind]},
            "selected",
            evidence=ImageEvidence([FIRST], {"claim": ["first"]}),
        )
    assert provider.calls == []
    assert provider.text_calls == 0


@pytest.mark.parametrize("value", [0, -1, True])
def test_capability_bounds_require_positive_integers(value: int) -> None:
    """Reject meaningless ceilings instead of treating booleans as byte counts."""
    with pytest.raises(ValueError):
        MediaCapabilities({"image/png"}, max_images=value)
    with pytest.raises(ValueError):
        MediaCapabilities({"image/png"}, max_image_bytes=value)
    with pytest.raises(ValueError):
        MediaCapabilities({"image/png"}, max_total_bytes=value)


def test_attachment_and_capability_are_immutable() -> None:
    """Protect snapshots from source-set and attribute changes."""
    declared = {"image/png"}
    caps = MediaCapabilities(declared)
    declared.clear()
    assert caps.image_types == frozenset({"image/png"})
    with pytest.raises((AttributeError, TypeError)):
        FIRST.__setattr__("data", b"replacement")
    with pytest.raises((AttributeError, TypeError)):
        caps.__setattr__("max_images", 999)


@pytest.mark.parametrize("field", ["id", "data", "media_type"])
def test_empty_attachment_values_are_rejected(field: str) -> None:
    """Require meaningful declarations without decoding the encoded image bytes."""
    with pytest.raises(ValueError):
        ImageAttachment(
            "" if field == "id" else "valid",
            b"" if field == "data" else b"opaque",
            "" if field == "media_type" else "image/png",
        )


@pytest.mark.parametrize(
    "images, bindings, required",
    [
        (None, {}, ()),
        ([object()], {}, ()),
        ([FIRST], None, ()),
        ([FIRST], {"claim": {"first"}}, ()),
        ([FIRST], {"claim": "first"}, ()),
        ([FIRST], {"": ["first"]}, ()),
        ([FIRST], {"claim": [1]}, ()),
        ([], {}, "claim"),
        ([], {}, [None]),
    ],
)
def test_invalid_evidence_shapes(images: Any, bindings: Any, required: Any) -> None:
    """Reject malformed containers and identifiers with local value errors."""
    with pytest.raises(ValueError):
        ImageEvidence(images, bindings, required)


@pytest.mark.parametrize("formats", [None, "image/png", [None], [""]])
def test_invalid_capability_format_shapes(formats: Any) -> None:
    """Reject malformed MIME collections before provider dispatch."""
    with pytest.raises(ValueError):
        MediaCapabilities(formats)


@pytest.mark.parametrize(
    "definition",
    [
        None,
        {"type": "noul", "instructions": 3},
        {"type": "noul", "criteria": ["wrong mapping shape"]},
        {"type": "choice", "criteria": {1: "bad"}},
        {"type": "choice", "criteria": {"yes": 3}},
        {"type": "score", "criteria": [None]},
    ],
)
def test_malformed_question_shapes(definition: Any) -> None:
    """Reject invalid typed-contract shapes before capability lookup."""
    provider = RecordingMediaProvider()
    with pytest.raises(ProviderRequestError):
        judge_with_images(
            provider,
            "state",
            {"claim": definition},
            "selected",
            evidence=ImageEvidence([FIRST], {"claim": ["first"]}),
        )
    assert provider.models == []
    assert provider.calls == []


def test_empty_evidence_preserves_unrestricted_text_response() -> None:
    """Keep text responses unchanged even when media checks would reject them."""
    provider = RecordingMediaProvider()
    provider.response.answers.clear()
    assert (
        judge_with_images(
            provider, "state", QUESTIONS, "selected", evidence=ImageEvidence([], {})
        )
        is provider.response
    )
    assert provider.text_calls == 1
    assert provider.models == []


@pytest.mark.parametrize("declaration", [None, {}, {"image_types": ["image/png"]}])
def test_invalid_capability_declaration_never_dispatches(declaration: Any) -> None:
    """Require the immutable declaration type before media inference."""

    class InvalidDeclaration(RecordingMediaProvider):
        """Return malformed capability declarations.

        Examples:
            Exercise this fixture through the enclosing parametrized test.
        """

        def capabilities(self, model: str) -> Any:
            """Return the selected malformed declaration.

            Returns:
                An intentionally invalid declaration.
            """
            self.models.append(model)
            return declaration

    provider = InvalidDeclaration()
    with pytest.raises(ProviderCapabilityError):
        judge_with_images(provider, "state", QUESTIONS, "selected", evidence=evidence())
    assert provider.calls == []
    assert provider.text_calls == 0


def test_raw_noul_and_choice_preserve_structured_values() -> None:
    """Keep optional Noul criteria and raw structured instructions intact."""
    questions: dict[str, Question | Mapping[str, Any]] = {
        "claim": {
            "type": "noul",
            "criteria": {"true": "present", "false": "absent"},
            "instructions": {"nested": ["check"]},
        },
        "decision": {
            "type": "choice",
            "criteria": {"yes": ["present"], "insufficient_evidence": None},
            "instructions": ["select"],
        },
    }
    provider = RecordingMediaProvider()
    result = judge_with_images(
        provider, "state", questions, "selected", evidence=evidence()
    )
    assert result is provider.response
    assert provider.calls[0][1] is questions


@pytest.mark.parametrize("criteria", [{"custom": "meaning"}, {"true": 1}])
@pytest.mark.parametrize("raw", [False, True])
def test_existing_noul_criteria_are_preserved(
    criteria: dict[str, Any], raw: bool
) -> None:
    """Retain the existing typed Noul criteria mapping without new restrictions."""
    provider = RecordingMediaProvider()
    provider.response = SystemOneResponse(
        "fixture-resolved", Usage(0, None), {"claim": NoulAnswer(0.9)}
    )
    question: Question | Mapping[str, Any] = (
        {
            "type": "noul",
            "instructions": {"check": "exact criteria"},
            "criteria": criteria,
        }
        if raw
        else Noul(instructions={"check": "exact criteria"}, criteria=criteria)
    )
    submitted = ImageEvidence([FIRST], {"claim": ["first"]})
    response = judge_with_images(
        provider, "state", {"claim": question}, "selected", evidence=submitted
    )
    assert response is provider.response
    assert provider.calls[0][1] == {"claim": question}
    assert (
        question["criteria"] if isinstance(question, Mapping) else question.criteria
    ) == criteria


@pytest.mark.parametrize("raw", [False, True])
def test_existing_choice_label_is_preserved(raw: bool) -> None:
    """Retain an explicitly declared string label without inventing content rules."""
    provider = RecordingMediaProvider()
    provider.response = SystemOneResponse(
        "fixture-resolved", Usage(0, None), {"claim": ChoiceAnswer("", 1, {"": 1})}
    )
    question: Question | Mapping[str, Any] = (
        {"type": "choice", "criteria": {"": "blank label"}}
        if raw
        else Choice(criteria={"": "blank label"})
    )
    response = judge_with_images(
        provider,
        "state",
        {"claim": question},
        "selected",
        evidence=ImageEvidence([FIRST], {"claim": ["first"]}),
    )
    assert response is provider.response
    assert provider.calls[0][1] == {"claim": question}
